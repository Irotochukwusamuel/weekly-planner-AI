"""
Weekly Shift Planner — ML Edition
Main CLI entry point
"""

import sys
import json
import os
from datetime import date

try:
    from .config import make_config, DAY_START, DAY_END, STUDY_PREFERENCE, CONFIG_PATH
    from .utils import to_mins
    from .database import (
        open_db,
        save_week,
        pending_feedback,
        all_feedback,
        get_latest_week,
        get_latest_week_bundle,
        get_week_bundle,
        update_week,
        delete_week,
    )
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
except ImportError:
    from config import make_config, DAY_START, DAY_END, STUDY_PREFERENCE, CONFIG_PATH
    from utils import to_mins
    from database import (
        open_db,
        save_week,
        pending_feedback,
        all_feedback,
        get_latest_week,
        get_latest_week_bundle,
        get_week_bundle,
        update_week,
        delete_week,
    )
    from scheduler import plan_day
    from display import print_week
    from html_export import export_html
    from calendar_integration import run_calendar_export
    from feedback import collect_feedback, show_history, show_insights
    from setup_wizard import setup_wizard
    from ml_model import (
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
    view        Open the latest saved week or a live preview in HTML
    edit        Regenerate a saved week after changing config
    delete      Remove a saved week and its generated files
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
    args = sys.argv[2:]

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

    def build_plans(cfg: dict, bundle, study_pref: str):
        """Build a seven-day plan list for the current config."""
        ml_active = bundle is not None and bool(bundle.get("models"))
        ds, de = to_mins(DAY_START), to_mins(DAY_END)
        plans = []
        for i in range(7):
            scorer = make_gym_scorer(bundle, i, cfg) if ml_active else None
            plans.append(plan_day(i, cfg, study_pref, ds, de, score_fn=scorer))
        return plans, ml_active

    def show_current_schedule():
        """Open the latest saved schedule as HTML, or a preview if none exists."""
        latest = get_latest_week_bundle(con)
        if latest:
            week, rows = latest
            plans = [json.loads(row["plan_json"]) for row in rows]
            cfg = json.loads(week["config"])
            bundle = load_model()
            ml_active = bundle is not None and bool(bundle.get("models"))
            out = export_html(plans, week["week_start"], ml_active)
            print(f"\n  ✓ Schedule opened in your browser → {out}\n")
            return

        cfg = make_config()
        bundle = load_model()
        plans, ml_active = build_plans(
            cfg, bundle, cfg.get("study_pref", STUDY_PREFERENCE)
        )
        out = export_html(plans, date.today().isoformat(), ml_active)
        print(f"\n  ✓ Schedule preview opened in your browser → {out}\n")

    def build_plans_for_cfg(cfg: dict):
        """Build plans for the current config."""
        bundle = load_model()
        plans, ml_active = build_plans(
            cfg, bundle, cfg.get("study_pref", STUDY_PREFERENCE)
        )
        return plans, ml_active

    def choose_week_id(preferred_id: int | None = None):
        """Resolve a saved week id, defaulting to the latest saved week."""
        latest = get_latest_week_bundle(con)
        if not latest:
            return None

        latest_week, _ = latest
        if preferred_id is not None:
            return preferred_id
        return latest_week["id"]

    def remove_generated_files(week_start: str):
        """Delete generated HTML and ICS files for a week if present."""
        for suffix in (".html", ".ics"):
            path = os.path.join(os.path.dirname(CONFIG_PATH), f"schedule_{week_start}{suffix}")
            if os.path.exists(path):
                os.remove(path)

    def edit_saved_schedule():
        """Regenerate a saved week after updating configuration."""
        week_id = int(args[0]) if args and args[0].isdigit() else choose_week_id()
        if week_id is None:
            print("\n  No saved schedules found. Run `plan` first.\n")
            return

        bundle = get_week_bundle(con, week_id)
        if not bundle:
            print("\n  That schedule no longer exists.\n")
            return

        week, _ = bundle
        print("\n  Editing saved schedule")
        print("  ─────────────────────────────────────────────────")
        print(f"  Week ID: {week_id}")
        print(f"  Week start: {week['week_start']}")
        answer = input("  Open setup wizard to change config? [y/N]: ").strip().lower()
        cfg = json.loads(week["config"])
        if answer in ("y", "yes"):
            setup_wizard()
            if not os.path.exists(CONFIG_PATH):
                print("  Setup was not saved. Edit cancelled.\n")
                return
            cfg = make_config()

        plans, ml_active = build_plans_for_cfg(cfg)
        update_week(con, week_id, week["week_start"], cfg, plans)
        out = export_html(plans, week["week_start"], ml_active)
        print(f"\n  ✓ Schedule updated and opened → {out}\n")

    def delete_saved_schedule():
        """Delete a saved schedule and its generated files."""
        week_id = int(args[0]) if args and args[0].isdigit() else choose_week_id()
        if week_id is None:
            print("\n  No saved schedules found.\n")
            return

        bundle = get_week_bundle(con, week_id)
        if not bundle:
            print("\n  That schedule no longer exists.\n")
            return

        week, _ = bundle
        answer = input(
            f"  Delete week {week_id} ({week['week_start']}) and its files? [y/N]: "
        ).strip().lower()
        if answer not in ("y", "yes"):
            print("  Delete cancelled.\n")
            return

        deleted = delete_week(con, week_id)
        if deleted:
            remove_generated_files(deleted)
            print(f"\n  ✓ Deleted week {week_id} and its generated files.\n")
        else:
            print("\n  Nothing deleted.\n")

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
        plans, ml_active = build_plans(
            cfg, bundle, cfg.get("study_pref", STUDY_PREFERENCE)
        )

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

    elif cmd in ("view", "schedule"):
        show_current_schedule()

    elif cmd == "edit":
        edit_saved_schedule()

    elif cmd == "delete":
        delete_saved_schedule()

    elif cmd == "calendar":
        cfg = make_config()
        bundle = load_model()
        ml_active = bundle is not None and bool(bundle.get("models"))

        week_start = get_latest_week(con) or date.today().isoformat()

        plans, _ = build_plans(cfg, bundle, cfg.get("study_pref", STUDY_PREFERENCE))

        run_calendar_export(plans, week_start)

    elif cmd == "insights":
        show_insights(con)

    elif cmd == "export":
        cfg = make_config()
        bundle = load_model()
        ml_active = bundle is not None and bool(bundle.get("models"))

        week_start = get_latest_week(con) or date.today().isoformat()

        plans, _ = build_plans(cfg, bundle, cfg.get("study_pref", STUDY_PREFERENCE))

        out = export_html(plans, week_start, ml_active)
        print(f"\n  ✓ Schedule saved → {out}")
        print("  Opening in your browser...\n")

    else:
        print(HELP)

    con.close()


if __name__ == "__main__":
    main()
