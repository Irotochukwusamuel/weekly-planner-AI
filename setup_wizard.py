"""
Setup wizard for initial configuration.
"""
import json
from .config import CONFIG_PATH, save_config
from .utils import to_mins, fmt_time

DAY_NAMES_FULL = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]
DAY_ALIASES = {
    "mon": 1,
    "tue": 2,
    "wed": 3,
    "thu": 4,
    "fri": 5,
    "sat": 6,
    "sun": 7,
    "monday": 1,
    "tuesday": 2,
    "wednesday": 3,
    "thursday": 4,
    "friday": 5,
    "saturday": 6,
    "sunday": 7,
    "1": 1,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
}


def _parse_days(raw: str) -> list:
    """Parse a day string like 'Mon Tue Wed Thu Fri' → list of bools."""
    raw = raw.strip().lower()
    if raw in ("all",):
        return [True] * 7
    if raw in ("weekdays", "weekday"):
        return [True, True, True, True, True, False, False]
    if raw in ("weekends", "weekend"):
        return [False, False, False, False, False, True, True]
    tokens = raw.replace(",", " ").split()
    days = [False] * 7
    for tok in tokens:
        idx = DAY_ALIASES.get(tok.lower())
        if idx:
            days[idx - 1] = True
    return days


def _ask_time(prompt: str, default: str) -> str:
    """Prompt for HH:MM format time."""
    while True:
        raw = input(f"  {prompt} [{default}]: ").strip() or default
        try:
            h, m = raw.split(":")
            if 0 <= int(h) <= 23 and 0 <= int(m) <= 59:
                return f"{int(h):02d}:{int(m):02d}"
        except ValueError:
            pass
        print("    ↳ Enter time as HH:MM (24-hour), e.g. 08:00")


def _ask_mins(prompt: str, default: int) -> int:
    """Prompt for duration in minutes."""
    while True:
        raw = input(f"  {prompt} [{default} min]: ").strip()
        if not raw:
            return default
        try:
            val = int(raw)
            if 0 <= val <= 240:
                return val
        except ValueError:
            pass
        print("    ↳ Enter a number of minutes (0–240)")


def _ask_days(prompt: str, default: str) -> list:
    """Prompt for day selection."""
    while True:
        raw = input(f"  {prompt} [{default}]: ").strip() or default
        result = _parse_days(raw)
        if any(result):
            return result
        print(
            "    ↳ Enter day names like: Mon Tue Wed Thu Fri  (or: weekdays / weekends / all)"
        )


def setup_wizard():
    """Interactive setup wizard for initial config."""
    W = 58
    print()
    print("=" * W)
    print("  WEEKLY PLANNER  —  FIRST-TIME SETUP".center(W))
    print("=" * W)
    print("  Answer the prompts. Press Enter to keep the default.")
    print()

    cfg = {}

    for job, jkey, defaults in [
        (
            "Job 1",
            "j1",
            {
                "start": "08:00",
                "end": "13:00",
                "before": 30,
                "after": 30,
                "days": "Mon Tue Wed Thu Fri",
            },
        ),
        (
            "Job 2",
            "j2",
            {
                "start": "15:00",
                "end": "20:00",
                "before": 30,
                "after": 30,
                "days": "Mon Tue Wed Thu Fri",
            },
        ),
    ]:
        print(f"  {'─' * 52}")
        print(f"  {job.upper()}")
        print(f"  {'─' * 52}")
        cfg[f"{jkey}_start"] = to_mins(
            _ask_time("Shift start (HH:MM, 24-hr)", defaults["start"])
        )
        cfg[f"{jkey}_end"] = to_mins(
            _ask_time("Shift end   (HH:MM, 24-hr)", defaults["end"])
        )
        cfg[f"{jkey}_before"] = _ask_mins(
            "Travel TO work (minutes)", defaults["before"]
        )
        cfg[f"{jkey}_after"] = _ask_mins(
            "Travel FROM work (minutes)", defaults["after"]
        )
        cfg[f"{jkey}_days"] = _ask_days(
            "Days you work (e.g. Mon Tue Wed Thu Fri)", defaults["days"]
        )
        working = " ".join(
            d
            for d, on in zip(
                ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], cfg[f"{jkey}_days"]
            )
            if on
        )
        print(
            f"  ✓ {job}: {fmt_time(cfg[f'{jkey}_start'])} – {fmt_time(cfg[f'{jkey}_end'])} on {working}"
        )
        print()

    print(f"  {'─' * 52}")
    print("  PREFERENCES")
    print(f"  {'─' * 52}")

    while True:
        sp = (
            input("  Study preference [morning/afternoon/evening/auto]: ")
            .strip()
            .lower()
            or "evening"
        )
        if sp in ("morning", "afternoon", "evening", "auto"):
            cfg["study_pref"] = sp
            break
        print("    ↳ Choose: morning, afternoon, evening, or auto")

    gym_drive = _ask_mins("Gym drive each way (minutes)", 20)
    cfg["gym_drive"] = gym_drive

    print()
    print(f"  {'─' * 52}")
    print("  PREVIEW")
    print(f"  {'─' * 52}")
    for jn, jk in [("Job 1", "j1"), ("Job 2", "j2")]:
        wd = " ".join(
            d
            for d, on in zip(
                ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], cfg[f"{jk}_days"]
            )
            if on
        )
        print(
            f"  {jn}: {fmt_time(cfg[f'{jk}_start'])}–{fmt_time(cfg[f'{jk}_end'])}  "
            f"({cfg[f'{jk}_before']}min to / {cfg[f'{jk}_after']}min from)  →  {wd}"
        )
    print(f"  Study: {cfg['study_pref']}  |  Gym drive: {gym_drive} min each way")
    print()

    save = input("  Save this config? [Y/n]: ").strip().lower()
    if save in ("", "y", "yes"):
        save_config(cfg)
        print(f"\n  ✓ Config saved to planner_config.json\n")
        print("  Run `python -m weekly_planner plan` to plan your week.\n")
    else:
        print("  Config not saved.\n")
