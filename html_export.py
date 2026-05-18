"""
HTML schedule generation and export.
"""

import os
import webbrowser
from datetime import date, timedelta

try:
    from .utils import fmt_time, fmt_dur
    from .config import HERE
except ImportError:
    from utils import fmt_time, fmt_dur
    from config import HERE

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

SLOT_STYLES = {
    "work": {
        "bg": "#EBF4FF",
        "border": "#378ADD",
        "text": "#0C3D7A",
        "label_bg": "#C8E0F8",
    },
    "travel": {
        "bg": "#F4F3F0",
        "border": "#9B9890",
        "text": "#3D3C39",
        "label_bg": "#DDD9D1",
    },
    "gym": {
        "bg": "#EDF7E2",
        "border": "#5A9118",
        "text": "#244010",
        "label_bg": "#C4E2A0",
    },
    "study": {
        "bg": "#F0EFFE",
        "border": "#7F77DD",
        "text": "#2D2880",
        "label_bg": "#CCC9F5",
    },
    "personal": {
        "bg": "#FEF5E6",
        "border": "#C47B10",
        "text": "#5A3600",
        "label_bg": "#F8D99A",
    },
    "free": {
        "bg": "#F9F9F7",
        "border": "#D4D2CC",
        "text": "#9A9890",
        "label_bg": "#ECEAE4",
    },
}

SLOT_ICONS = {
    "work": "💼",
    "travel": "🚗",
    "gym": "🏋️",
    "study": "📖",
    "personal": "🌤",
    "free": "",
}


def _slot_html(slot: dict) -> str:
    """Generate HTML for a single time slot."""
    t = slot["type"]
    st = SLOT_STYLES.get(t, SLOT_STYLES["free"])
    icon = SLOT_ICONS.get(t, "")
    time_str = f"{fmt_time(slot['s'])} – {fmt_time(slot['e'])}"
    dur = fmt_dur(slot["e"] - slot["s"])
    is_free = t == "free"
    opacity = ' style="opacity:0.45"' if is_free else ""
    return f"""
        <div class="slot slot-{t}"{opacity} style="background:{st["bg"]};border-left:3px solid {st["border"]}">
          <div class="slot-time" style="color:{st["text"]}">{time_str}</div>
          <div class="slot-body">
            <div class="slot-label" style="color:{st["text"]}">{icon} {slot["label"]}</div>
            <div class="slot-detail">{slot["detail"]}</div>
          </div>
        </div>"""


def _day_card_html(day_name: str, plan: dict, day_idx: int) -> str:
    """Generate HTML for a single day card."""
    short = SHORT[day_idx]
    is_weekend = day_idx >= 5

    if plan["is_off"]:
        return f"""
      <div class="day-card day-off">
        <div class="day-header">
          <span class="day-short">{short}</span>
          <span class="day-full">{day_name}</span>
          <span class="day-tag tag-off">Rest</span>
        </div>
        <div class="day-off-msg">No shifts today — good for recovery&nbsp;&amp;&nbsp;study.</div>
      </div>"""

    slots_html = "".join(_slot_html(s) for s in plan["timeline"])
    work_hrs = fmt_dur(plan["total_work"])
    gym_tag = (
        f'<span class="day-tag tag-gym">🏋️ {plan["gym_label"] or "Gym"}</span>'
        if plan["gym"]
        else ""
    )
    study_tag = (
        '<span class="day-tag tag-study">📖 Study</span>' if plan["study"] else ""
    )

    return f"""
      <div class="day-card">
        <div class="day-header">
          <span class="day-short">{short}</span>
          <span class="day-full">{day_name}</span>
          <span class="work-hrs">{work_hrs} work</span>
        </div>
        <div class="day-tags">{gym_tag}{study_tag}</div>
        <div class="slots">{slots_html}</div>
      </div>"""


def generate_html(plans: list, week_start: str, ml_active: bool) -> str:
    """Generate complete HTML schedule."""
    ws = date.fromisoformat(week_start)
    we = ws + timedelta(days=6)
    date_range = f"{ws.strftime('%B %-d')} – {we.strftime('%-d, %Y')}"

    total_work = sum(p["total_work"] for p in plans)
    total_travel = sum(p["total_travel"] for p in plans)
    gym_days = sum(1 for p in plans if p["gym"])
    study_days = sum(1 for p in plans if p["study"])

    ml_badge = '<span class="ml-badge">✦ ML active</span>' if ml_active else ""
    days_html = "".join(_day_card_html(DAYS[i], plans[i], i) for i in range(7))

    # Overview row
    overview_cells = ""
    for i, p in enumerate(plans):
        badges = ""
        if p["is_off"]:
            badges = '<span class="ov-badge ov-off">off</span>'
        else:
            badges = f'<span class="ov-badge ov-work">{fmt_dur(p["total_work"])}</span>'
            if p["gym"]:
                badges += '<span class="ov-badge ov-gym">gym</span>'
            if p["study"]:
                badges += '<span class="ov-badge ov-study">study</span>'
        overview_cells += f"""
        <div class="ov-cell">
          <div class="ov-day">{SHORT[i]}</div>
          <div class="ov-badges">{badges}</div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Weekly Schedule — {date_range}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --bg:       #F2F0EB;
      --surface:  #FFFFFF;
      --ink:      #1A1917;
      --ink2:     #6B6860;
      --ink3:     #A8A59E;
      --accent:   #1A1917;
      --radius:   10px;
      --shadow:   0 1px 3px rgba(0,0,0,.07), 0 4px 16px rgba(0,0,0,.06);
    }}

    body {{
      font-family: 'DM Sans', sans-serif;
      background: var(--bg);
      color: var(--ink);
      padding: 2rem 1.5rem 4rem;
      min-height: 100vh;
    }}

    /* ── Header ── */
    .page-header {{
      max-width: 1100px;
      margin: 0 auto 2rem;
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 1rem;
    }}
    .header-left h1 {{
      font-size: clamp(1.6rem, 4vw, 2.4rem);
      font-weight: 600;
      letter-spacing: -0.03em;
      line-height: 1.1;
    }}
    .header-left .week-range {{
      font-size: 1rem;
      color: var(--ink2);
      margin-top: 4px;
      font-weight: 400;
    }}
    .ml-badge {{
      display: inline-block;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      background: var(--ink);
      color: #fff;
      padding: 3px 9px;
      border-radius: 20px;
      margin-left: 10px;
      vertical-align: middle;
    }}
    .stats {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .stat {{
      background: var(--surface);
      border-radius: var(--radius);
      padding: 10px 16px;
      box-shadow: var(--shadow);
      text-align: center;
      min-width: 90px;
    }}
    .stat-val {{
      font-size: 1.25rem;
      font-weight: 600;
      letter-spacing: -0.02em;
      line-height: 1;
    }}
    .stat-lbl {{
      font-size: 11px;
      color: var(--ink3);
      margin-top: 3px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}

    /* ── Overview strip ── */
    .overview {{
      max-width: 1100px;
      margin: 0 auto 2rem;
      background: var(--surface);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      display: grid;
      grid-template-columns: repeat(7, 1fr);
      overflow: hidden;
    }}
    .ov-cell {{
      padding: 12px 8px;
      text-align: center;
      border-right: 1px solid #EDECEA;
    }}
    .ov-cell:last-child {{ border-right: none; }}
    .ov-day {{
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: var(--ink2);
      margin-bottom: 7px;
    }}
    .ov-badges {{ display: flex; flex-direction: column; gap: 4px; align-items: center; }}
    .ov-badge {{
      font-size: 10px;
      font-weight: 500;
      padding: 2px 8px;
      border-radius: 20px;
      white-space: nowrap;
    }}
    .ov-work  {{ background: #C8E0F8; color: #0C3D7A; }}
    .ov-gym   {{ background: #C4E2A0; color: #244010; }}
    .ov-study {{ background: #CCC9F5; color: #2D2880; }}
    .ov-off   {{ background: #ECEAE4; color: #9A9890; }}

    /* ── Day grid ── */
    .days-grid {{
      max-width: 1100px;
      margin: 0 auto;
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 1rem;
    }}

    /* ── Day card ── */
    .day-card {{
      background: var(--surface);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      overflow: hidden;
    }}
    .day-header {{
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 14px 16px 10px;
      border-bottom: 1px solid #EDECEA;
    }}
    .day-short {{
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--ink3);
      min-width: 28px;
    }}
    .day-full {{
      font-size: 14px;
      font-weight: 600;
      flex: 1;
    }}
    .work-hrs {{
      font-size: 11px;
      color: var(--ink3);
      font-family: 'DM Mono', monospace;
    }}
    .day-tags {{
      display: flex;
      gap: 5px;
      flex-wrap: wrap;
      padding: 8px 16px 4px;
    }}
    .day-tag {{
      font-size: 10px;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: 20px;
      letter-spacing: 0.03em;
    }}
    .tag-gym   {{ background: #C4E2A0; color: #244010; }}
    .tag-study {{ background: #CCC9F5; color: #2D2880; }}
    .tag-off   {{ background: #ECEAE4; color: #9A9890; }}

    /* ── Slots ── */
    .slots {{ padding: 8px 12px 12px; display: flex; flex-direction: column; gap: 4px; }}
    .slot {{
      display: flex;
      align-items: flex-start;
      gap: 10px;
      padding: 7px 10px;
      border-radius: 7px;
    }}
    .slot-time {{
      font-family: 'DM Mono', monospace;
      font-size: 10px;
      font-weight: 500;
      white-space: nowrap;
      padding-top: 2px;
      min-width: 110px;
    }}
    .slot-label {{
      font-size: 12px;
      font-weight: 600;
    }}
    .slot-detail {{
      font-size: 11px;
      color: var(--ink3);
      margin-top: 1px;
    }}

    /* ── Off day ── */
    .day-off .day-header {{ background: #F9F8F5; }}
    .day-off-msg {{
      padding: 20px 16px;
      font-size: 13px;
      color: var(--ink3);
      text-align: center;
      font-style: italic;
    }}

    /* ── Print ── */
    .print-btn {{
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: var(--ink);
      color: #fff;
      border: none;
      border-radius: 24px;
      padding: 10px 20px;
      font-family: 'DM Sans', sans-serif;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      box-shadow: 0 4px 16px rgba(0,0,0,.2);
      transition: opacity .15s;
    }}
    .print-btn:hover {{ opacity: 0.85; }}

    @media print {{
      body {{ background: #fff; padding: 1rem; }}
      .print-btn {{ display: none; }}
      .day-card {{ break-inside: avoid; box-shadow: none; border: 1px solid #DDD; }}
      .overview {{ box-shadow: none; border: 1px solid #DDD; }}
    }}
    @media (max-width: 600px) {{
      .days-grid {{ grid-template-columns: 1fr; }}
      .page-header {{ flex-direction: column; align-items: flex-start; }}
    }}
  </style>
</head>
<body>

  <header class="page-header">
    <div class="header-left">
      <h1>Weekly Schedule {ml_badge}</h1>
      <p class="week-range">{date_range}</p>
    </div>
    <div class="stats">
      <div class="stat"><div class="stat-val">💼</div><div class="stat-lbl">{fmt_dur(total_work)}<br>work</div></div>
      <div class="stat"><div class="stat-val">🚗</div><div class="stat-lbl">{fmt_dur(total_travel)}<br>commute</div></div>
      <div class="stat"><div class="stat-val">{gym_days}/7</div><div class="stat-lbl">gym<br>days</div></div>
      <div class="stat"><div class="stat-val">{study_days}/7</div><div class="stat-lbl">study<br>days</div></div>
    </div>
  </header>

  <div class="overview">{overview_cells}
  </div>

  <div class="days-grid">{days_html}
  </div>

  <button class="print-btn" onclick="window.print()">🖨 Print / Save PDF</button>

</body>
</html>"""


def export_html(plans: list, week_start: str, ml_active: bool) -> str:
    """Generate HTML and save to file. Returns the output path."""
    html = generate_html(plans, week_start, ml_active)
    out_path = os.path.join(HERE, f"schedule_{week_start}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    webbrowser.open(f"file://{out_path}")
    return out_path
