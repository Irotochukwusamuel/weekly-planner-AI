"""
Feedback collection and history display.
"""
from .database import DAY_NAMES
from .utils import fmt_dur, fmt_time, to_mins
from .ml_model import FEATURE_NAMES

DAYS = DAY_NAMES
SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def collect_feedback(con) -> bool:
    """Collect feedback for past days."""
    from .database import pending_feedback
    
    days = pending_feedback(con)
    if not days:
        print("\n  ✓ All past days are logged — no feedback needed.\n")
        return False

    print(f"\n  Logging feedback for {len(days)} day(s)...\n")
    for row in days:
        day_id = row["id"]
        day_name = row["day_name"]
        week_start = row["week_start"]

        print(f"  ── {day_name}  (week of {week_start}) ─────────────────────────")
        gym_done = _ask_yn("  Did you complete your gym session?")
        study_done = _ask_yn("  Did you complete your study session?")
        rating = _ask_int("  Rate the schedule (1 terrible → 5 perfect): ", 1, 5)
        notes = input("  Notes? (Enter to skip): ").strip() or None
        print()

        con.execute(
            """
            UPDATE day_plans
            SET completed_gym=?, completed_study=?, satisfaction=?, notes=?
            WHERE id=?
        """,
            (int(gym_done), int(study_done), rating, notes, day_id),
        )
        con.commit()
        print("  ✓ Saved.\n")
    return True


def show_history(con):
    """Display week history."""
    from .database import get_week_history, get_week_feedback
    
    weeks = get_week_history(con, 12)
    if not weeks:
        print("\n  No history yet — run `plan` first.\n")
        return

    print(
        f"\n  {'ID':>4}  {'Week start':>12}  {'Gym':>5}  {'Study':>6}  {'Avg ⭐':>8}  Feedback"
    )
    print("  " + "─" * 52)
    for w in weeks:
        days = get_week_feedback(con, w["id"])
        gym_done = sum(1 for d in days if d["completed_gym"] == 1)
        study_done = sum(1 for d in days if d["completed_study"] == 1)
        ratings = [d["satisfaction"] for d in days if d["satisfaction"] is not None]
        rated = len(ratings)
        total_days = len(days)
        avg_str = f"{sum(ratings) / rated:.1f}" if ratings else "—"
        feedback_str = f"{rated}/{total_days} days rated"
        print(
            f"  {w['id']:>4}  {w['week_start']:>12}  {gym_done:>5}  {study_done:>6}  {avg_str:>8}  {feedback_str}"
        )
    print()


def show_insights(con):
    """Display ML model insights."""
    from .database import all_feedback
    from .ml_model import load_model, ML_AVAILABLE, MIN_DAYS_TO_TRAIN
    from .utils import fmt_time, to_mins
    
    rows = all_feedback(con)
    bundle = load_model()

    print(f"\n  {'─' * 56}")
    print("  WHAT THE SYSTEM HAS LEARNED")
    print(f"  {'─' * 56}")
    print(f"  Feedback collected: {len(rows)} days\n")

    if not rows:
        print("  No data yet. Use `plan` then `feedback` to get started.\n")
        return

    # Gym completion rate by time-of-day bucket
    buckets = {}
    for row in rows:
        g = row["gym_start"]
        c = row["completed_gym"]
        if g is None or c is None:
            continue
        label = fmt_time(g)
        if label not in buckets:
            buckets[label] = {"done": 0, "total": 0}
        buckets[label]["total"] += 1
        buckets[label]["done"] += int(c)

    if buckets:
        print("  Gym completion by scheduled time:")
        for time_label in sorted(
            buckets, key=lambda t: to_mins(t) if "AM" not in t or t[:1].isdigit() else 0
        ):
            d = buckets[time_label]
            pct = d["done"] / d["total"] * 100
            bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
            print(
                f"    {time_label:>9}  {bar}  {pct:4.0f}%  ({d['done']}/{d['total']} sessions)"
            )
        print()

    # Avg satisfaction by day of week
    sat = {i: [] for i in range(7)}
    for row in rows:
        s = row["satisfaction"]
        if s:
            sat[row["day_index"]].append(s)

    print("  Average satisfaction by day:")
    for i, day in enumerate(DAYS):
        ratings = sat[i]
        if ratings:
            avg = sum(ratings) / len(ratings)
            stars = "★" * round(avg) + "☆" * (5 - round(avg))
            print(f"    {day:<12}  {stars}  {avg:.1f}/5")
        else:
            print(f"    {day:<12}  (no data yet)")
    print()

    # Feature importance from model
    if bundle and "gym" in bundle.get("models", {}):
        clf = bundle["models"]["gym"]
        importances = clf.feature_importances_
        print("  Most influential factors (gym model):")
        ranked = sorted(zip(FEATURE_NAMES, importances), key=lambda x: -x[1])
        for name, imp in ranked[:5]:
            bar = "█" * int(imp * 50)
            print(f"    {name:<22}  {bar}  {imp:.3f}")
        print()
        print(
            f"  ✦ ML model trained on {bundle['trained_on']} days  ({bundle['trained_at'][:10]})"
        )
        print(
            "  ✦ Gym slot times are now ML-optimised based on your completion history."
        )
    else:
        needed = max(0, MIN_DAYS_TO_TRAIN - len(rows))
        if needed:
            print(
                f"  ⏳ {needed} more rated day(s) needed to activate ML optimisation."
            )
        elif not ML_AVAILABLE:
            print("  ⚠  Run: pip install scikit-learn numpy  to enable ML.")
        else:
            print("  ⏳ Model not yet trained — run `feedback` then `plan` again.")
    print()


def _ask_yn(prompt: str) -> bool:
    """Prompt for yes/no input."""
    while True:
        ans = input(f"{prompt} (y/n): ").strip().lower()
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False


def _ask_int(prompt: str, lo: int, hi: int) -> int:
    """Prompt for integer input within range."""
    while True:
        try:
            val = int(input(prompt).strip())
            if lo <= val <= hi:
                return val
        except ValueError:
            pass
        print(f"  Enter a number {lo}–{hi}.")
