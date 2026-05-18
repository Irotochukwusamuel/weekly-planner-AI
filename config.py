"""
Configuration management — loads from JSON, provides defaults.
"""
import os
import json

# Defaults
JOB1_START = "08:00"
JOB1_END = "13:00"
JOB1_TRAVEL_TO = 30
JOB1_TRAVEL_HOME = 30
JOB1_DAYS = [True, True, True, True, True, False, False]

JOB2_START = "15:00"
JOB2_END = "20:00"
JOB2_TRAVEL_TO = 30
JOB2_TRAVEL_HOME = 30
JOB2_DAYS = [True, True, True, True, True, False, False]

STUDY_PREFERENCE = "evening"
GYM_DRIVE = 20
GYM_WORKOUT = 60
DAY_START = "06:00"
DAY_END = "23:00"

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "planner_config.json")
DB_PATH = os.path.join(HERE, "planner_data.db")
MODEL_PATH = os.path.join(HERE, "planner_model.pkl")


def make_config() -> dict:
    """Load config from saved JSON, falling back to hardcoded defaults."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    # Hardcoded defaults
    from .utils import to_mins
    return {
        "j1_start": to_mins(JOB1_START),
        "j1_end": to_mins(JOB1_END),
        "j1_before": JOB1_TRAVEL_TO,
        "j1_after": JOB1_TRAVEL_HOME,
        "j1_days": JOB1_DAYS,
        "j2_start": to_mins(JOB2_START),
        "j2_end": to_mins(JOB2_END),
        "j2_before": JOB2_TRAVEL_TO,
        "j2_after": JOB2_TRAVEL_HOME,
        "j2_days": JOB2_DAYS,
    }


def save_config(cfg: dict):
    """Save config to JSON file."""
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
