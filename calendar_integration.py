"""
Calendar integration — ICS export, macOS Calendar & Reminders.
"""

import os
import subprocess
import platform
import uuid
from datetime import date, timedelta

try:
    from .config import HERE
    from .utils import fmt_dur
except ImportError:
    from config import HERE
    from utils import fmt_dur

ICS_TYPES = {"work", "travel", "gym", "study", "personal"}
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _ical_dt(week_start: str, day_idx: int, mins: int) -> str:
    """Format date+time as iCalendar format."""
    d = date.fromisoformat(week_start) + timedelta(days=day_idx)
    h, m = divmod(round(mins), 60)
    return f"{d.strftime('%Y%m%d')}T{h:02d}{m:02d}00"


def generate_ics(plans: list, week_start: str, include: set) -> str:
    """Generate iCalendar content."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Weekly Planner ML//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    for day_idx, plan in enumerate(plans):
        if plan["is_off"]:
            continue
        for slot in plan["timeline"]:
            if slot["type"] not in include:
                continue
            dtstart = _ical_dt(week_start, day_idx, slot["s"])
            dtend = _ical_dt(week_start, day_idx, slot["e"])
            summary = slot["label"].replace(",", "\\,")
            detail = slot["detail"].replace(",", "\\,")
            lines += [
                "BEGIN:VEVENT",
                f"UID:{uuid.uuid4()}@weeklyplanner",
                f"DTSTART:{dtstart}",
                f"DTEND:{dtend}",
                f"SUMMARY:{summary}",
                f"DESCRIPTION:{detail}",
            ]
            if slot["type"] in ("gym", "study"):
                lines += [
                    "BEGIN:VALARM",
                    "TRIGGER:-PT15M",
                    "ACTION:DISPLAY",
                    f"DESCRIPTION:Reminder: {summary}",
                    "END:VALARM",
                ]
            lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def _apple_date_str(week_start: str, day_idx: int, mins: int) -> str:
    """Format date+time for AppleScript."""
    d = date.fromisoformat(week_start) + timedelta(days=day_idx)
    h, m = divmod(round(mins), 60)
    return d.strftime(f"%-m/%-d/%Y") + f" {h:02d}:{m:02d}:00"


def add_to_apple_calendar(
    plans: list, week_start: str, include: set, calendar_name: str = "Home"
) -> int:
    """Add events to macOS Calendar via AppleScript."""
    if platform.system() != "Darwin":
        print("  ⚠  macOS Calendar is only available on Mac.")
        return 0

    # First, try to create the calendar if it doesn't exist
    create_script = f'''
tell application "Calendar"
    try
        calendar "{calendar_name}"
    on error
        make new calendar with properties {{name:"{calendar_name}"}}
    end try
end tell
'''
    subprocess.run(["osascript", "-e", create_script], capture_output=True, text=True)

    added = 0
    for day_idx, plan in enumerate(plans):
        if plan["is_off"]:
            continue
        for slot in plan["timeline"]:
            if slot["type"] not in include:
                continue
            start_str = _apple_date_str(week_start, day_idx, slot["s"])
            end_str = _apple_date_str(week_start, day_idx, slot["e"])
            label = slot["label"].replace('"', '\\"')
            detail = slot["detail"].replace('"', '\\"')
            script = f'''
tell application "Calendar"
    tell calendar "{calendar_name}"
        set startDate to date "{start_str}"
        set endDate to date "{end_str}"
        make new event with properties {{summary:"{label}", start date:startDate, end date:endDate, description:"{detail}"}}
    end tell
end tell
'''
            result = subprocess.run(
                ["osascript", "-e", script], capture_output=True, text=True
            )
            if result.returncode == 0:
                added += 1
            else:
                print(f"  ⚠  Could not add '{label}' — check calendar name.")
                if result.stderr:
                    print(f"     {result.stderr.strip()}")
    return added


def add_to_apple_reminders(
    plans: list, week_start: str, list_name: str = "Reminders"
) -> int:
    """Add gym and study sessions to macOS Reminders."""
    if platform.system() != "Darwin":
        print("  ⚠  macOS Reminders is only available on Mac.")
        return 0

    added = 0
    for day_idx, plan in enumerate(plans):
        if plan["is_off"]:
            continue
        for slot in plan["timeline"]:
            if slot["type"] not in ("gym", "study", "personal"):
                continue
            due_str = _apple_date_str(week_start, day_idx, slot["s"])
            remind_str = _apple_date_str(week_start, day_idx, max(slot["s"] - 15, 0))
            day_name = DAYS[day_idx]
            name = f"{slot['label']} — {day_name}".replace('"', '\\"')
            script = f'''
tell application "Reminders"
    tell list "{list_name}"
        set newItem to make new reminder with properties {{name:"{name}", due date:date "{due_str}", remind me date:date "{remind_str}"}}
    end tell
end tell
'''
            result = subprocess.run(
                ["osascript", "-e", script], capture_output=True, text=True
            )
            if result.returncode == 0:
                added += 1
            else:
                print(f"  ⚠  Could not add '{name}' — check list name.")
    return added


def run_calendar_export(plans: list, week_start: str):
    """Interactive router for calendar export options."""
    is_mac = platform.system() == "Darwin"
    W = 58

    print()
    print("  WHAT TO ADD TO YOUR CALENDAR")
    print("  ─────────────────────────────────────────────────")
    print("   [1] Everything  (gym, study, personal, work, travel)")
    print("   [2] Key sessions only  (gym + study + personal)")
    print("   [3] Gym sessions only")
    print("   [4] Work shifts only")
    choice = _ask_int("  Choose", 1, 4)
    include = {
        1: {"work", "travel", "gym", "study", "personal"},
        2: {"gym", "study", "personal"},
        3: {"gym"},
        4: {"work"},
    }[choice]

    print()
    print("  WHERE TO ADD THEM")
    print("  ─────────────────────────────────────────────────")
    print(
        "   [1] Export .ics file  (import to Google Calendar, Apple Calendar, Outlook)"
    )
    if is_mac:
        print("   [2] Add directly to macOS Calendar")
        print("   [3] Add to macOS Reminders  (gym + study + personal only)")
    else:
        print("   [2] macOS Calendar  (Mac only)")
        print("   [3] macOS Reminders  (Mac only)")
    dest = _ask_int("  Choose", 1, 3)

    print()

    if dest == 1:
        ics_content = generate_ics(plans, week_start, include)
        ics_path = os.path.join(HERE, f"schedule_{week_start}.ics")
        with open(ics_path, "w", encoding="utf-8") as f:
            f.write(ics_content)
        print(f"  ✓ Saved → {ics_path}")
        print()
        print("  HOW TO IMPORT:")
        print("  ┌ Google Calendar  → calendar.google.com → Settings → Import")
        print("  ├ Apple Calendar   → File → Import → select the .ics file")
        print("  └ Outlook          → File → Open & Export → Import/Export")
        print()

    elif dest == 2:
        if not is_mac:
            print("  ⚠  macOS Calendar is only available on Mac.\n")
            return
        cal_name = input("  Calendar name [Home]: ").strip() or "Home"
        print(f"  Adding events to '{cal_name}'...")
        n = add_to_apple_calendar(plans, week_start, include, cal_name)
        print(f"  ✓ Added {n} event(s) to macOS Calendar — '{cal_name}'\n")

    elif dest == 3:
        if not is_mac:
            print("  ⚠  macOS Reminders is only available on Mac.\n")
            return
        list_name = input("  Reminders list name [Reminders]: ").strip() or "Reminders"
        print(f"  Adding reminders to '{list_name}'...")
        n = add_to_apple_reminders(plans, week_start, list_name)
        print(f"  ✓ Added {n} reminder(s) to macOS Reminders — '{list_name}'\n")
        print("  Each reminder fires 15 minutes before the session.\n")


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
