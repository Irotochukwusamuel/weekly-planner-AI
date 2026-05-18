"""
Weekly Shift Planner — ML Edition
Main CLI entry point
"""
import sys
from datetime import date

from .config import make_config, DAY_START, DAY_END, STUDY_PREFERENCE, CONFIG_PATH
from .utils import to_mins
from .database import open_db, save_week, pending_feedback, all_feedback, get_latest_week
from .scheduler import plan_day
from .display import print_week
from .html_export import export_html
from .calendar_integration import run_calendar_export
from .feedback import collect_feedback, show_history, show_insights
from .setup_wizard import setup_wizard
from .ml_model import (
    train_model,
    load_model,
    make_gym_scorer,
    ML_AVAILABLE,
    MIN_DAYS_TO_TRAIN,
)
import os

HELP = """
  Weekly Shift Planner — ML Edition
  ────────────────────────────────────────────────────────
  Commands:
    setup       First-time config wizard (no file editing!)
    plan        Plan this week (uses ML if enough history)
    export      Save this week as a beautiful HTML file
    calendar    Add schedule to Google / Apple Calendar
                or macOS Reminders (.ics or AppleScript)
    feedback    Log how each day actually went
    history     View all stored weeks
    insights    See what the system has learned about you

  Recommended weekly workflow:
    1. Run `setup` once (or whenever jobs change)
    2. Run `plan` every Sunday
    3. Run `export` to get your HTML schedule
    4. Run `calendar` to push events to your calendar
    5. Run `feedback` during/end of the week
    6. After 7+ rated days, ML improves your gym times
  ────────────────────────────────────────────────────────
"""


def main():
    """Main CLI entry point."""
    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else "help"

    # setup doesn't need DB
    if cmd == "setup":
        setup_wizard()
        return

    con = open_db()

    # Prompt setup if no config saved yet
    if not os.path.exists(CONFIG_PATH) and cmd not in ("help",):
        print("\n  No config found. Running setup wizard first...\n")
        setup_wizard()
        if not os.path.exists(CONFIG_PATH):
            return

    if cmd == "plan":
        cfg = make_config()

        # Retrain on latest feedback, then load
        bundle = train_model(con) or load_model()
        ml_active = bundle is not None and bool(bundle.get("models"))

        if not ML_AVAILABLE:
            print("\n  ⚠  scikit-learn not installed — running rule-based mode.")
            print("     pip install scikit-learn numpy\n")
        elif not ml_active:
            rated = len(all_feedback(con))
            needed = max(0, MIN_DAYS_TO_TRAIN - rated)
            if needed:
                print(
                    f"\n  ⏳ ML activates after {MIN_DAYS_TO_TRAIN} rated days "
                    f"({rated} so far — {needed} more needed).\n"
                )

        # Build week — inject ML scorer per day if model is ready
        ds, de = to_mins(DAY_START), to_mins(DAY_END)
        study_pref = cfg.get("study_pref", STUDY_PREFERENCE)
        plans = []
        for i in range(7):
            scorer = make_gym_scorer(bundle, i, cfg) if ml_active else None
            plans.append(plan_day(i, cfg, study_pref, ds, de, score_fn=scorer))

        week_id = save_week(con, date.today().isoformat(), cfg, plans)
        print_week(plans, week_id=week_id, ml_active=ml_active)

        pending = len(pending_feedback(con))
        if pending:
            print(
                f"  💬 {pending} past day(s) need feedback → python -m weekly_planner feedback\n"
            )

    elif cmd == "feedback":
        updated = collect_feedback(con)
        if updated:
            print("  Retraining model on updated data...")
            bundle = train_model(con)
            if bundle and bundle.get("models"):
                print(f"  ✦ Model retrained on {bundle['trained_on']} days.\n")
            else:
                rated = len(all_feedback(con))
                needed = max(0, MIN_DAYS_TO_TRAIN - rated)
                if needed:
                    print(
                        f"  ({rated}/{MIN_DAYS_TO_TRAIN} days rated — {needed} more to activate ML)\n"
                    )
                elif not ML_AVAILABLE:
                    print(
                        "  Install scikit-learn to enable ML: pip install scikit-learn numpy\n"
                    )

    elif cmd == "history":
        show_history(con)

    elif cmd == "calendar":
        cfg = make_config()
        bundle = load_model()
        ml_active = bundle is not None and bool(bundle.get("models"))

        week_start = get_latest_week(con) or date.today().isoformat()

        ds, de = to_mins(DAY_START), to_mins(DAY_END)
        plans = []
        for i in range(7):
            scorer = make_gym_scorer(bundle, i, cfg) if ml_active else None
            plans.append(
                plan_day(
                    i,
                    cfg,
                    cfg.get("study_pref", STUDY_PREFERENCE),
                    ds,
                    de,
                    score_fn=scorer,
                )
            )

        run_calendar_export(plans, week_start)

    elif cmd == "insights":
        show_insights(con)

    elif cmd == "export":
        cfg = make_config()
        bundle = load_model()
        ml_active = bundle is not None and bool(bundle.get("models"))

        week_start = get_latest_week(con) or date.today().isoformat()

        ds, de = to_mins(DAY_START), to_mins(DAY_END)
        plans = []
        for i in range(7):
            scorer = make_gym_scorer(bundle, i, cfg) if ml_active else None
            plans.append(plan_day(i, cfg, STUDY_PREFERENCE, ds, de, score_fn=scorer))

        out = export_html(plans, week_start, ml_active)
        print(f"\n  ✓ Schedule saved → {out}")
        print("  Opening in your browser...\n")

    else:
        print(HELP)

    con.close()


if __name__ == "__main__":
    main()
