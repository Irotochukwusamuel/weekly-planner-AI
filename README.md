# Weekly Planner — ML Edition

A modular weekly schedule planner that learns from your feedback to optimize gym times using machine learning.

## Structure

The planner is now organized into clean, focused modules:

### Core Modules

- **`utils.py`** — Time formatting, gap calculations, preference scoring
- **`config.py`** — Configuration management (loads from `planner_config.json`)
- **`database.py`** — SQLite database operations (weeks, plans, feedback)
- **`scheduler.py`** — Core scheduling logic (plan days around work/preferences)
- **`ml_model.py`** — ML model training and gym completion prediction
- **`display.py`** — Terminal output formatting
- **`html_export.py`** — Beautiful HTML schedule generation
- **`calendar_integration.py`** — ICS export, macOS Calendar & Reminders
- **`feedback.py`** — Feedback collection, history, and insights
- **`setup_wizard.py`** — Interactive first-time configuration

### Entry Points

- **`main.py`** — Main CLI logic and command router
- **`__main__.py`** — Python module entry point
- **`../weekly_planner.py`** — Wrapper script (one level up)

## Usage

```bash
# As a module
python -m weekly_planner [command]

# Or as a script (if in parent directory)
python weekly_planner.py [command]
```

### Commands

- `setup` — First-time configuration wizard
- `plan` — Generate this week's schedule
- `export` — Save schedule as HTML
- `calendar` — Add to Google Calendar, Apple Calendar, or macOS Reminders
- `feedback` — Log how your days went
- `history` — View past weeks
- `insights` — See what the ML model has learned

## Recommended Workflow

1. **Sunday**: Run `setup` (first time only) then `plan`
2. **Daily**: Follow your schedule
3. **End of week**: Run `feedback` to rate each day
4. **After 7+ rated days**: ML activates and improves gym time placement
5. **Anytime**: Run `export` for a beautiful HTML view

## Files Generated

- `planner_config.json` — Your schedule configuration
- `planner_data.db` — SQLite database of plans and feedback
- `planner_model.pkl` — Trained ML model
- `schedule_YYYY-MM-DD.html` — Beautiful weekly schedule export
- `schedule_YYYY-MM-DD.ics` — Calendar import file

## ML Features

The system learns from your feedback to predict which times you're most likely to complete gym sessions. Features tracked:

- Day of week
- Total work hours
- Work schedule gaps
- Time-of-day preferences
- Whether you have both jobs scheduled

After 7+ rated days with variety (some completed, some missed), the model activates and refines gym slot placement.

## Dependencies

- **Required**: Python 3.9+
- **Optional**: `scikit-learn`, `numpy` (for ML features)

Install ML support:
```bash
pip install scikit-learn numpy
```

## Notes

- All times are in 24-hour format (HH:MM)
- All durations in minutes
- Database is local SQLite — no cloud sync
- macOS Calendar integration uses AppleScript (Mac only)
