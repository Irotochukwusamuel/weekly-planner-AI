"""
Terminal display functions for weekly plans.
"""

try:
    from .utils import fmt_time, fmt_dur
except ImportError:
    from utils import fmt_time, fmt_dur

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
ICONS = {
    "work": "💼",
    "travel": "🚗",
    "gym": "🏋️ ",
    "study": "📖",
    "personal": "🌤",
    "free": "  ",
}
W = 66


def print_week(plans: list, week_id=None, ml_active=False):
    """Print a week's schedule in a formatted table."""
    total_work = sum(p["total_work"] for p in plans)
    total_travel = sum(p["total_travel"] for p in plans)
    gym_days = sum(1 for p in plans if p["gym"])
    study_days = sum(1 for p in plans if p["study"])

    print()
    print("=" * W)
    title = "WEEKLY SCHEDULE" + ("  ✦ ML ACTIVE" if ml_active else "")
    print(title.center(W))
    if week_id:
        print(f"Week ID: {week_id}".center(W))
    print("=" * W)
    print(
        f"  💼 Work    {fmt_dur(total_work):>12}   🚗 Commute  {fmt_dur(total_travel):>10}"
    )
    print(
        f"  🏋️  Gym     {str(gym_days) + '/7':>12}   📖 Study    {str(study_days) + '/7':>10}"
    )
    print("=" * W)

    # Mini grid
    col = 8
    print()
    print("  " + "".join(s.center(col) for s in SHORT))
    print("  " + "─" * (col * 7))
    rows = {"work": "  ", "gym": "  ", "study": "  "}
    for p in plans:
        if p["is_off"]:
            rows["work"] += "  off   "
            rows["gym"] += " " * col
            rows["study"] += " " * col
        else:
            rows["work"] += fmt_dur(p["total_work"]).center(col)
            rows["gym"] += "🏋️ ".center(col - 1) + " " if p["gym"] else " " * col
            rows["study"] += "📖 ".center(col - 1) + " " if p["study"] else " " * col
    for row in rows.values():
        print(row)

    # Day timelines
    for i, p in enumerate(plans):
        print()
        print("─" * W)
        header = f"  {DAYS[i].upper()}"
        if p["is_off"]:
            header += "  (rest day)"
        elif p.get("gym_label"):
            header += f"  ·  {p['gym_label']}"
        print(header)
        print("─" * W)

        if p["is_off"]:
            print("  No shifts — good for recovery, errands, or extra study.")
            continue

        for slot in p["timeline"]:
            icon = ICONS.get(slot["type"], "  ")
            time_range = f"{fmt_time(slot['s'])} – {fmt_time(slot['e'])}"
            if slot["type"] == "free":
                print(
                    f"\033[2m  {time_range:<20} {slot['label']:<24} {slot['detail']}\033[0m"
                )
            else:
                print(f"  {icon} {time_range:<18} {slot['label']:<24} {slot['detail']}")

        if not p["gym"]:
            print("  ⚠  No gym slot today — schedule too packed.")
        if not p["study"]:
            print("  ⚠  No study block — try two 45-min chunks in free gaps.")

    print()
    print("=" * W)
    print()
