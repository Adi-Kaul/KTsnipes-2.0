"""What /snipes-rivals shows: the top rivalries, one person's rivals, or a head-to-head."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from .snipes import Snipe
from .stats import at, hits, plural, rivalries, score


def _rows(rivals: list[tuple[str, str, int, int]], limit: int) -> str:
    return "\n".join(
        f"{i}. {score(a, b, x, y)} · {plural(x + y, 'snipe')}" + (" _(one-sided)_" if y == 0 else "")
        for i, (a, b, x, y) in enumerate(rivals[:limit], 1)
    )


def rivals_board(month: list[Snipe], all_time: list[Snipe]) -> str:
    """/snipes-rivals: the biggest rivalries of all time, and the hottest this month."""
    top = rivalries(all_time)
    if not top:
        return ("No rivalries yet. Two people become rivals once they've sniped each other "
                "(either direction) at least twice. :crossed_swords:")
    parts = [f":crossed_swords: *Top Rivalries* (all time)\n{_rows(top, 5)}"]
    if hot := rivalries(month):
        parts.append(f":fire: *Hottest this month*\n{_rows(hot, 3)}")
    return "\n\n".join(parts)


def person_rivals(uid: str, all_time: list[Snipe]) -> str:
    """/snipes-rivals @person: everyone they've traded snipes with, from their side."""
    h = hits(all_time)
    others = {t for s, t in h if s == uid} | {s for s, t in h if t == uid}
    if not others:
        return f"{at(uid)} hasn't sniped or been sniped by anyone yet."
    rows = sorted(((o, h[(uid, o)], h[(o, uid)]) for o in others),
                  key=lambda r: (-(r[1] + r[2]), abs(r[1] - r[2]), r[0]))
    lines = [f":crossed_swords: *{at(uid)}'s rivals* (all time)"]
    for other, mine, theirs in rows[:8]:
        verdict = "up" if mine > theirs else "down" if mine < theirs else "tied"
        lines.append(f"• {at(other)} — {verdict} *{mine}–{theirs}*")
    if len(rows) > 8:
        lines.append(f"_…and {len(rows) - 8} more_")
    return "\n".join(lines)


def head_to_head(a: str, b: str, week: list[Snipe], month: list[Snipe], all_time: list[Snipe],
                 tz: ZoneInfo, permalink=None) -> str:
    """/snipes-rivals @a @b: their record against each other."""
    if a == b:
        return "That's the same person. Tag two different people."
    between = [s for s in all_time if (s.sniper == a and b in s.targets) or (s.sniper == b and a in s.targets)]
    title = f":crossed_swords: *{at(a)} vs {at(b)}*"
    if not between:
        return f"{title}\n\nThey've never sniped each other. Somebody make a move."

    def record(snipes: list[Snipe]) -> str:
        h = hits(snipes)
        return score(a, b, h[(a, b)], h[(b, a)])

    h = hits(all_time)
    x, y = h[(a, b)], h[(b, a)]
    leader = f"{at(a)} leads by {x - y}" if x > y else f"{at(b)} leads by {y - x}" if y > x else "Dead even."
    first, last = between[0], between[-1]

    def describe(s: Snipe) -> str:
        victim = b if s.sniper == a else a
        shot = f"<{permalink(s.ts)}|{datetime.fromtimestamp(float(s.ts), tz):%b %-d, %Y}>" if permalink \
            else f"{datetime.fromtimestamp(float(s.ts), tz):%b %-d, %Y}"
        return f"{at(s.sniper)} got {at(victim)} on {shot}"

    lines = [
        title,
        f"*All time:* {record(all_time)} · {leader}",
        f"*This month:* {record(month)}",
        f"*This week:* {record(week)}",
        f":drop_of_blood: *First blood:* {describe(first)}",
    ]
    if last is not first:
        lines.append(f":stopwatch: *Latest:* {describe(last)}")
    return "\n".join(lines)
