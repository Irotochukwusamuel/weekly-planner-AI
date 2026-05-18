"""
Core scheduling logic — planning days around work and preferences.
"""

try:
    from .utils import fmt_time, fmt_dur, get_gaps, get_free_slots, pref_score
    from .config import GYM_DRIVE, GYM_WORKOUT
except ImportError:
    from utils import fmt_time, fmt_dur, get_gaps, get_free_slots, pref_score
    from config import GYM_DRIVE, GYM_WORKOUT


def build_work_blocks(day_idx: int, cfg: dict) -> list:
    """Build work and travel blocks for a day based on config."""
    blocks = []
    for job in ("j1", "j2"):
        if not cfg[f"{job}_days"][day_idx]:
            continue
        s, e = cfg[f"{job}_start"], cfg[f"{job}_end"]
        before = cfg[f"{job}_before"]
        after = cfg[f"{job}_after"]
        if e <= s:
            continue
        if before:
            blocks.append(
                {
                    "s": s - before,
                    "e": s,
                    "type": "travel",
                    "label": f"Travel to {job.upper().replace('J', 'Job ')}",
                    "detail": fmt_dur(before) + " commute",
                }
            )
        blocks.append(
            {
                "s": s,
                "e": e,
                "type": "work",
                "label": job.upper().replace("J", "Job "),
                "detail": fmt_dur(e - s) + " shift",
            }
        )
        if after:
            blocks.append(
                {
                    "s": e,
                    "e": e + after,
                    "type": "travel",
                    "label": f"Travel from {job.upper().replace('J', 'Job ')}",
                    "detail": fmt_dur(after) + " commute",
                }
            )
    return blocks


def rule_gym_target(day_idx: int, cfg: dict) -> dict:
    """Baseline gym time based on day type (refined by ML later)."""
    j1_on = cfg["j1_days"][day_idx]
    j2_on = cfg["j2_days"][day_idx]
    if day_idx >= 5:
        return {"t": 16 * 60, "label": "Weekend (4:00 PM)"}
    if not j1_on and not j2_on:
        return {"t": 15 * 60, "label": "Full day off (3:00 PM)"}
    earliest = min(
        cfg["j1_start"] if j1_on else 1440, cfg["j2_start"] if j2_on else 1440
    )
    if earliest >= 12 * 60:
        return {"t": 10 * 60, "label": "Free morning (10:00 AM)"}
    return {"t": None, "label": "Best gap (auto)"}


def plan_day(
    day_idx: int,
    cfg: dict,
    study_pref: str,
    day_start: int,
    day_end: int,
    score_fn=None,
) -> dict:
    """
    Plan one day. `score_fn(candidate_gym_start) -> float` is the ML scorer;
    if None, falls back to rule-based placement.
    """
    gym_need = GYM_DRIVE + GYM_WORKOUT + GYM_DRIVE

    work_blocks = build_work_blocks(day_idx, cfg)
    is_off = not cfg["j1_days"][day_idx] and not cfg["j2_days"][day_idx]
    gaps = get_gaps(work_blocks, day_start, day_end)
    placed = []
    extra = []

    # ── Gym ───────────────────────────────────────────────────────────────────
    gym_slots = get_free_slots(gaps, placed, gym_need)
    did_gym = False
    gym_label = None

    if gym_slots:
        gt = rule_gym_target(day_idx, cfg)

        # Build candidate start times: rule-based target ± offsets + slot starts
        candidates = set()
        if gt["t"] is not None:
            ideal = gt["t"] - GYM_DRIVE
            for offset in range(-120, 121, 30):
                candidates.add(ideal + offset)
        for sl in gym_slots:
            candidates.add(sl["s"])

        # Keep only candidates that fit within a free slot
        valid = [
            c
            for c in candidates
            if day_start <= c
            and c + gym_need <= day_end
            and any(sl["s"] <= c and sl["e"] >= c + gym_need for sl in gym_slots)
        ]
        if not valid:
            valid = [sl["s"] for sl in gym_slots]

        # Choose best candidate
        if score_fn:
            best = max(valid, key=score_fn)
        elif gt["t"] is not None:
            ideal = gt["t"] - GYM_DRIVE
            best = min(valid, key=lambda c: abs(c - ideal))
        else:
            # Largest gap
            best = max(
                valid,
                key=lambda c: next(
                    (sl["e"] - sl["s"] for sl in gym_slots if sl["s"] <= c), 0
                ),
            )

        end = best + gym_need
        placed.append({"s": best, "e": end})
        extra += [
            {
                "s": best,
                "e": best + GYM_DRIVE,
                "type": "travel",
                "label": "Drive to gym",
                "detail": "20 min",
            },
            {
                "s": best + GYM_DRIVE,
                "e": best + GYM_DRIVE + GYM_WORKOUT,
                "type": "gym",
                "label": "Gym",
                "detail": "1 hr workout",
            },
            {
                "s": best + GYM_DRIVE + GYM_WORKOUT,
                "e": end,
                "type": "travel",
                "label": "Drive home from gym",
                "detail": "20 min",
            },
        ]
        did_gym = True
        gym_label = gt["label"] + (" ✦ ML" if score_fn else "")

    # ── Study (90 min) ────────────────────────────────────────────────────────
    study_slots = get_free_slots(gaps, placed, 90)
    did_study = False
    if study_slots:
        study_slots.sort(
            key=lambda sl: pref_score(sl["s"], sl["e"], study_pref), reverse=True
        )
        sl = {"s": study_slots[0]["s"], "e": study_slots[0]["s"] + 90}
        placed.append(sl)
        extra.append(
            {
                **sl,
                "type": "study",
                "label": "Study session",
                "detail": "90 min focused study",
            }
        )
        did_study = True

    # ── Personal time (45 min) ────────────────────────────────────────────────
    personal_slots = get_free_slots(gaps, placed, 45)
    if personal_slots:
        personal_slots.sort(key=lambda sl: sl["e"] - sl["s"], reverse=True)
        sl = {"s": personal_slots[0]["s"], "e": personal_slots[0]["s"] + 45}
        placed.append(sl)
        extra.append(
            {
                **sl,
                "type": "personal",
                "label": "Personal time",
                "detail": "Rest, hobbies, recharge",
            }
        )

    # ── Build timeline ────────────────────────────────────────────────────────
    all_blocks = sorted(work_blocks + extra, key=lambda b: b["s"])
    timeline, cur = [], day_start
    for b in all_blocks:
        bs, be = max(b["s"], day_start), min(b["e"], day_end)
        if be <= day_start or bs >= day_end:
            continue
        if bs > cur and bs - cur >= 10:
            timeline.append(
                {
                    "s": cur,
                    "e": bs,
                    "type": "free",
                    "label": "Free time",
                    "detail": fmt_dur(bs - cur),
                }
            )
        if bs >= cur:
            timeline.append(
                {
                    "s": bs,
                    "e": be,
                    "type": b["type"],
                    "label": b["label"],
                    "detail": b["detail"],
                }
            )
            cur = be
    if cur < day_end:
        timeline.append(
            {
                "s": cur,
                "e": day_end,
                "type": "free",
                "label": "Free time",
                "detail": fmt_dur(day_end - cur),
            }
        )

    total_work = sum(b["e"] - b["s"] for b in work_blocks if b["type"] == "work")
    total_travel = sum(b["e"] - b["s"] for b in work_blocks if b["type"] == "travel")

    return {
        "timeline": timeline,
        "gym": did_gym,
        "gym_label": gym_label,
        "study": did_study,
        "total_work": total_work,
        "total_travel": total_travel,
        "is_off": is_off,
    }
