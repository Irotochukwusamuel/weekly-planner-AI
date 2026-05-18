"""
ML model training and inference for gym completion prediction.
"""
import os
import pickle
import json
from datetime import datetime

try:
    import numpy as np
    from sklearn.ensemble import GradientBoostingClassifier
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

from .config import MODEL_PATH
from .database import all_feedback
from .scheduler import build_work_blocks
from .utils import to_mins, get_gaps

MIN_DAYS_TO_TRAIN = 7

FEATURE_NAMES = [
    "day_of_week",
    "is_weekend",
    "total_work_hrs",
    "earliest_start_hr",
    "latest_end_hr",
    "total_free_hrs",
    "gym_hour",
    "gym_in_morning",
    "gym_in_evening",
    "free_hrs_before_gym",
    "free_hrs_after_gym",
    "both_jobs_on",
    "one_job_on",
]

GYM_DRIVE = 20
GYM_WORKOUT = 60


def extract_features(day_idx: int, cfg: dict, gym_start_mins) -> list:
    """Extract features from a day's configuration for ML."""
    j1_on = cfg["j1_days"][day_idx]
    j2_on = cfg["j2_days"][day_idx]
    work_blocks = build_work_blocks(day_idx, cfg)
    gaps = get_gaps(work_blocks, to_mins("06:00"), to_mins("23:00"))

    total_work = sum(b["e"] - b["s"] for b in work_blocks if b["type"] == "work") / 60
    total_free = sum(g["e"] - g["s"] for g in gaps) / 60

    j1s = cfg["j1_start"] if j1_on else 1440
    j2s = cfg["j2_start"] if j2_on else 1440
    j1e = cfg["j1_end"] if j1_on else 0
    j2e = cfg["j2_end"] if j2_on else 0
    earliest_start = min(j1s, j2s) / 60
    latest_end = max(j1e, j2e) / 60

    gym_hour = gym_start_mins / 60 if gym_start_mins is not None else -1
    gym_need = GYM_DRIVE + GYM_WORKOUT + GYM_DRIVE

    free_before = free_after = 0.0
    if gym_start_mins is not None:
        for g in gaps:
            if g["e"] <= gym_start_mins:
                free_before = (g["e"] - g["s"]) / 60
            if g["s"] >= gym_start_mins + gym_need and free_after == 0.0:
                free_after = (g["e"] - g["s"]) / 60

    return [
        day_idx,
        1 if day_idx >= 5 else 0,
        total_work,
        earliest_start,
        latest_end,
        total_free,
        gym_hour,
        1 if gym_hour < 12 else 0,
        1 if gym_hour >= 17 else 0,
        free_before,
        free_after,
        1 if (j1_on and j2_on) else 0,
        1 if (j1_on ^ j2_on) else 0,
    ]


def train_model(con) -> dict | None:
    """Train gym completion classifier from all rated days."""
    if not ML_AVAILABLE:
        return None

    rows = all_feedback(con)
    if len(rows) < MIN_DAYS_TO_TRAIN:
        return None

    X_gym, y_gym = [], []
    X_study, y_study = [], []

    for row in rows:
        day_idx = row["day_index"]
        gym_start = row["gym_start"]
        cfg = json.loads(row["config"])
        comp_gym = row["completed_gym"]
        comp_study = row["completed_study"]

        feats = extract_features(day_idx, cfg, gym_start)

        if comp_gym is not None:
            X_gym.append(feats)
            y_gym.append(int(comp_gym))
        if comp_study is not None:
            X_study.append(feats)
            y_study.append(int(comp_study))

    bundle = {
        "models": {},
        "trained_on": len(rows),
        "trained_at": datetime.now().isoformat(),
    }

    for name, X, y in [("gym", X_gym, y_gym), ("study", X_study, y_study)]:
        if len(X) < 5 or len(set(y)) < 2:
            continue
        clf = GradientBoostingClassifier(
            n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42
        )
        clf.fit(np.array(X), np.array(y))
        bundle["models"][name] = clf

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(bundle, f)
    return bundle


def load_model() -> dict | None:
    """Load trained model from disk."""
    if not ML_AVAILABLE or not os.path.exists(MODEL_PATH):
        return None
    try:
        with open(MODEL_PATH, "rb") as f:
            return pickle.load(f)
    except Exception:
        return None


def make_gym_scorer(bundle, day_idx: int, cfg: dict):
    """Return a scoring function for gym placement using ML."""
    if bundle is None or "gym" not in bundle.get("models", {}):
        return None

    clf = bundle["models"]["gym"]

    def score(gym_start_mins: int) -> float:
        feats = extract_features(day_idx, cfg, gym_start_mins)
        proba = clf.predict_proba([feats])[0]
        return float(proba[1]) if len(proba) > 1 else float(proba[0])

    return score
