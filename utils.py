"""
Time utilities, gap calculations, and preference scoring.
"""


def to_mins(t: str) -> int:
    """Convert HH:MM time string to minutes since midnight."""
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def fmt_time(m: int) -> str:
    """Format minutes since midnight as 12-hour time string."""
    m = round(m) % 1440
    h, mn = divmod(m, 60)
    return f"{h % 12 or 12}:{mn:02d} {'AM' if h < 12 else 'PM'}"


def fmt_dur(m: int) -> str:
    """Format duration in minutes as human-readable string."""
    m = abs(round(m))
    if not m:
        return "—"
    if m < 60:
        return f"{m} min"
    h, mn = divmod(m, 60)
    return f"{h} hr {mn} min" if mn else f"{h} hr"


def get_gaps(busy: list, day_start: int, day_end: int) -> list:
    """Find free time gaps between busy blocks."""
    gaps, cur = [], day_start
    for b in sorted(busy, key=lambda x: x["s"]):
        bs, be = max(b["s"], day_start), min(b["e"], day_end)
        if bs > cur:
            gaps.append({"s": cur, "e": bs})
        if be > cur:
            cur = be
    if cur < day_end:
        gaps.append({"s": cur, "e": day_end})
    return gaps


def get_free_slots(gaps: list, placed: list, need: int) -> list:
    """Find free slots that can fit a duration of `need` minutes."""
    result = []
    for g in gaps:
        cuts = sorted(
            [p for p in placed if p["s"] < g["e"] and p["e"] > g["s"]],
            key=lambda x: x["s"],
        )
        cur = g["s"]
        for c in cuts:
            if c["s"] > cur and c["s"] - cur >= need:
                result.append({"s": cur, "e": c["s"]})
            cur = max(cur, c["e"])
        if g["e"] - cur >= need:
            result.append({"s": cur, "e": g["e"]})
    return result


def pref_score(s: int, e: int, pref: str) -> float:
    """Score a time slot based on time-of-day preference."""
    mid = (s + e) / 2
    if pref == "morning":
        return -mid
    if pref == "afternoon":
        return -abs(mid - 13 * 60)
    if pref == "evening":
        return -abs(mid - 19 * 60)
    return float(e - s)
