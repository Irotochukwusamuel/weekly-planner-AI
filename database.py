"""
Database operations — weeks, day plans, feedback, and history.
"""

import sqlite3
import json

try:
    from .config import DB_PATH
except ImportError:
    from config import DB_PATH

DAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def open_db() -> sqlite3.Connection:
    """Open or create the SQLite database."""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript("""
        CREATE TABLE IF NOT EXISTS weeks (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start TEXT NOT NULL,
            config     TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS day_plans (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            week_id         INTEGER NOT NULL REFERENCES weeks(id),
            day_index       INTEGER NOT NULL,
            day_name        TEXT NOT NULL,
            plan_json       TEXT NOT NULL,
            gym_start       INTEGER,
            study_start     INTEGER,
            completed_gym   INTEGER,
            completed_study INTEGER,
            satisfaction    INTEGER,
            notes           TEXT
        );
    """)
    con.commit()
    return con


def save_week(con, week_start: str, config: dict, plans: list) -> int:
    """Save a week's plan to the database."""
    cur = con.cursor()
    cur.execute(
        "INSERT INTO weeks (week_start, config) VALUES (?,?)",
        (week_start, json.dumps(config)),
    )
    week_id = cur.lastrowid
    for i, p in enumerate(plans):
        gym_start = next((s["s"] for s in p["timeline"] if s["type"] == "gym"), None)
        study_start = next(
            (s["s"] for s in p["timeline"] if s["type"] == "study"), None
        )
        cur.execute(
            """
            INSERT INTO day_plans (week_id, day_index, day_name, plan_json, gym_start, study_start)
            VALUES (?,?,?,?,?,?)
        """,
            (week_id, i, DAY_NAMES[i], json.dumps(p), gym_start, study_start),
        )
    con.commit()
    return week_id


def pending_feedback(con) -> list:
    """Days in the past that still need a feedback rating."""
    return con.execute("""
        SELECT dp.id, dp.day_name, dp.day_index, w.week_start,
               dp.completed_gym, dp.completed_study
        FROM day_plans dp
        JOIN weeks w ON dp.week_id = w.id
        WHERE dp.satisfaction IS NULL
          AND date(w.week_start, '+' || dp.day_index || ' days') <= date('now')
        ORDER BY w.week_start, dp.day_index
    """).fetchall()


def all_feedback(con) -> list:
    """All rated days — used for ML training."""
    return con.execute("""
        SELECT dp.day_index, dp.gym_start, dp.study_start,
               dp.completed_gym, dp.completed_study, dp.satisfaction,
               w.config
        FROM day_plans dp
        JOIN weeks w ON dp.week_id = w.id
        WHERE dp.satisfaction IS NOT NULL
        ORDER BY w.week_start, dp.day_index
    """).fetchall()


def get_week_history(con, limit: int = 12):
    """Get recent weeks for history display."""
    return con.execute(
        "SELECT id, week_start FROM weeks ORDER BY week_start DESC LIMIT ?",
        (limit,),
    ).fetchall()


def get_week_feedback(con, week_id: int):
    """Get all feedback for a specific week."""
    return con.execute(
        "SELECT completed_gym, completed_study, satisfaction FROM day_plans WHERE week_id=?",
        (week_id,),
    ).fetchall()


def get_latest_week(con) -> str | None:
    """Get the most recent week's start date."""
    row = con.execute(
        "SELECT week_start FROM weeks ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return row["week_start"] if row else None


def get_latest_week_bundle(con):
    """Get the most recently saved week config and plans."""
    week = con.execute(
        "SELECT id, week_start, config FROM weeks ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if not week:
        return None

    plans = con.execute(
        """
        SELECT day_index, day_name, plan_json, gym_start, study_start
        FROM day_plans
        WHERE week_id=?
        ORDER BY day_index
    """,
        (week["id"],),
    ).fetchall()
    return week, plans


def get_week_bundle(con, week_id: int):
    """Get a saved week config and plans by week id."""
    week = con.execute(
        "SELECT id, week_start, config FROM weeks WHERE id=?",
        (week_id,),
    ).fetchone()
    if not week:
        return None

    plans = con.execute(
        """
        SELECT day_index, day_name, plan_json, gym_start, study_start
        FROM day_plans
        WHERE week_id=?
        ORDER BY day_index
    """,
        (week_id,),
    ).fetchall()
    return week, plans


def update_week(con, week_id: int, week_start: str, config: dict, plans: list) -> None:
    """Replace a saved week in place."""
    cur = con.cursor()
    cur.execute(
        "UPDATE weeks SET week_start=?, config=? WHERE id=?",
        (week_start, json.dumps(config), week_id),
    )
    cur.execute("DELETE FROM day_plans WHERE week_id=?", (week_id,))
    for i, p in enumerate(plans):
        gym_start = next((s["s"] for s in p["timeline"] if s["type"] == "gym"), None)
        study_start = next(
            (s["s"] for s in p["timeline"] if s["type"] == "study"), None
        )
        cur.execute(
            """
            INSERT INTO day_plans (week_id, day_index, day_name, plan_json, gym_start, study_start)
            VALUES (?,?,?,?,?,?)
        """,
            (week_id, i, DAY_NAMES[i], json.dumps(p), gym_start, study_start),
        )
    con.commit()


def delete_week(con, week_id: int) -> str | None:
    """Delete a saved week and return its week_start if found."""
    row = con.execute("SELECT week_start FROM weeks WHERE id=?", (week_id,)).fetchone()
    if not row:
        return None
    con.execute("DELETE FROM day_plans WHERE week_id=?", (week_id,))
    con.execute("DELETE FROM weeks WHERE id=?", (week_id,))
    con.commit()
    return row["week_start"]
