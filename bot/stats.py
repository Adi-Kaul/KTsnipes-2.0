"""Turns a list of snipes into leaderboards and the weekly and monthly reports. Pure functions, no Slack calls."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, time as dtime, timedelta
from zoneinfo import ZoneInfo

from .snipes import Snipe


# ---- the report schedule ----

def last_report_due(now: float, day: int, at, tz: ZoneInfo) -> datetime:
    """The most recent scheduled report time at or before now (e.g. last Sunday 8pm)."""
    local = datetime.fromtimestamp(now, tz)
    due = datetime.combine(local.date(), at, tz) - timedelta(days=(local.weekday() - day) % 7)
    return due if due <= local else due - timedelta(days=7)


def last_month_end_due(now: float, at, tz: ZoneInfo) -> datetime:
    """The most recent monthly report time at or before now (e.g. Sep 30 at 8pm)."""
    local = datetime.fromtimestamp(now, tz)
    next_first = (local.date().replace(day=28) + timedelta(days=4)).replace(day=1)
    due = datetime.combine(next_first - timedelta(days=1), at, tz)
    return due if due <= local else datetime.combine(local.date().replace(day=1) - timedelta(days=1), at, tz)


def month_window(due: datetime, at, tz: ZoneInfo) -> tuple[float, float]:
    """The month a report covers: since the previous month's report, so no snipe falls between two."""
    first = datetime.combine(due.date().replace(day=1), dtime(0), tz)
    return last_month_end_due(first.timestamp() - 1, at, tz).timestamp(), due.timestamp()


def week_window(due: datetime) -> tuple[float, float]:
    """The week a report covers: the 7 days leading up to when it's due."""
    return (due - timedelta(days=7)).timestamp(), due.timestamp()


# ---- tallies ----

def snipe_counts(snipes: list[Snipe]) -> Counter:
    """Snipes each person made. Tagging three people in one post is three snipes."""
    c = Counter()
    for s in snipes:
        c[s.sniper] += len(s.targets)
    return c


def sniped_counts(snipes: list[Snipe]) -> Counter:
    """Times each person got sniped."""
    return Counter(t for s in snipes for t in s.targets)


def ranked(counter: Counter, limit: int = 3, cap: int = 5) -> list[tuple[int, str, int]]:
    """(rank, user, count) for the top `limit` ranks. Ties share a rank; never more than `cap` rows."""
    rows, rank, prev = [], 0, None
    for i, (user, n) in enumerate(sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))):
        if n != prev:
            rank, prev = i + 1, n
        if rank > limit or len(rows) >= cap:
            break
        rows.append((rank, user, n))
    return rows


def best_day(snipes: list[Snipe], tz: ZoneInfo) -> tuple[str, datetime, int] | None:
    """(sniper, day, count) for the most snipes anyone made in a single day."""
    c = Counter()
    for s in snipes:
        c[(s.sniper, datetime.fromtimestamp(float(s.ts), tz).date())] += len(s.targets)
    if not c:
        return None
    (user, day), n = min(c.items(), key=lambda kv: (-kv[1], kv[0][1], kv[0][0]))
    return user, day, n


def busiest_day(snipes: list[Snipe], tz: ZoneInfo) -> tuple[datetime, int] | None:
    c = Counter()
    for s in snipes:
        c[datetime.fromtimestamp(float(s.ts), tz).date()] += len(s.targets)
    if not c:
        return None
    day, n = min(c.items(), key=lambda kv: (-kv[1], kv[0]))
    return day, n


def most_reacted(snipes: list[Snipe]) -> Snipe | None:
    best = max(snipes, key=lambda s: (s.reactions, -float(s.ts)), default=None)
    return best if best and best.reactions > 0 else None


def hits(snipes: list[Snipe]) -> Counter:
    """(sniper, target) -> how many times the sniper got that target."""
    return Counter((s.sniper, t) for s in snipes for t in s.targets)


def rivalries(snipes: list[Snipe], min_total: int = 2) -> list[tuple[str, str, int, int]]:
    """Every pair of people who've sniped each other (in either direction) at least min_total times,
    as (leader, trailer, leader's snipes on trailer, trailer's snipes on leader).
    Most snipes between them first; on a tie, the closer score first."""
    h = hits(snipes)
    out = []
    for a, b in {tuple(sorted(pair)) for pair in h}:
        x, y = h[(a, b)], h[(b, a)]
        if y > x:
            a, b, x, y = b, a, y, x
        if x + y >= min_total:
            out.append((a, b, x, y))
    return sorted(out, key=lambda r: (-(r[2] + r[3]), r[2] - r[3], r[0], r[1]))


# ---- formatting ----

MEDALS = {1: ":first_place_medal:", 2: ":second_place_medal:", 3: ":third_place_medal:"}


def at(uid: str) -> str:
    return f"<@{uid}>"


def score(a: str, b: str, x: int, y: int) -> str:
    """@a 7–5 @b"""
    return f"{at(a)} *{x}–{y}* {at(b)}"


def plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def board(counter: Counter, limit: int = 3, cap: int = 5) -> str:
    return "\n".join(f"{MEDALS.get(rank, f'{rank}.')} {at(u)} — {n}" for rank, u, n in ranked(counter, limit, cap))


# Per period: title, how to say the period in a sentence, how to write a day, top N places on each board.
PERIODS = {
    "week": ("Weekly Report", "this week", "%A", 3),
    "month": ("Monthly Report", "this month", "%a %b %-d", 5),
    "all": ("All-Time Report", "all time", "%b %-d, %Y", 5),
}
EMPTY = {
    "week": "Zero snipes this week. Nobody's watching their back and nobody's taking the shot. :sleeping:",
    "month": "Zero snipes this month so far. :sleeping:",
    "all": "No snipes on record yet. Somebody take the first shot. :camera_with_flash:",
}


def month_start(now: float, tz: ZoneInfo) -> datetime:
    return datetime.fromtimestamp(now, tz).replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def report(snipes: list[Snipe], period: str, start: float, end: float, tz: ZoneInfo, permalink=None) -> str:
    """A report for snipes posted in [start, end). period is "week", "month", or "all".
    permalink(ts) -> URL, used to link the most-reacted snipe."""
    title, phrase, day_fmt, places = PERIODS[period]
    first = datetime.fromtimestamp(start, tz)
    last = datetime.fromtimestamp(end, tz) - timedelta(seconds=1)
    if period == "week":
        span = f" · {first:%b %-d} – {last:%b %-d}"
    elif period == "month":
        # A posted monthly report's window starts the evening before the 1st, so name the month a day in.
        span = f" · {first + timedelta(days=1):%B %Y}"
    else:
        span = f" · since {datetime.fromtimestamp(float(snipes[0].ts), tz):%b %-d, %Y}" if snipes else ""
    head = f":dart: *KTsnipes {title}*{span}"
    if not snipes:
        return f"{head}\n\n{EMPTY[period]}"

    made, got = snipe_counts(snipes), sniped_counts(snipes)
    total = sum(made.values())
    parts = [
        head,
        f"*{plural(total, 'snipe')}* {phrase} · {plural(len(made), 'sniper')} · {plural(len(got), 'victim')}",
        f":gun: *Top Snipers*\n{board(made, places, 5)}",
        f":skull: *Most Sniped*\n{board(got, places, 5)}",
    ]

    highlights = []
    if (bd := best_day(snipes, tz)) and bd[2] >= 2:
        user, day, n = bd
        highlights.append(f":fire: *Best day:* {at(user)} got {plural(n, 'snipe')} on {day:{day_fmt}}")
    if mr := most_reacted(snipes):
        victims = " ".join(at(t) for t in mr.targets)
        shot = f"<{permalink(mr.ts)}|this shot>" if permalink else "this shot"
        highlights.append(f":star-struck: *Most reacted:* {shot} by {at(mr.sniper)} on {victims} "
                          f"({plural(mr.reactions, 'reaction')})")
    if rv := rivalries(snipes):
        label = "Biggest rivalry" if period == "all" else f"Rivalry of the {period}"
        highlights.append(f":crossed_swords: *{label}:* {score(*rv[0])}")
    if (busy := busiest_day(snipes, tz)) and busy[1] >= 2:
        highlights.append(f":calendar: *Busiest day:* {busy[0]:{day_fmt}} ({plural(busy[1], 'snipe')})")
    if highlights:
        parts.append("\n".join(highlights))
    return "\n\n".join(parts)


def weekly_report(snipes: list[Snipe], start: float, end: float, tz: ZoneInfo, permalink=None) -> str:
    """The Sunday report."""
    return report(snipes, "week", start, end, tz, permalink)


def player_card(uid: str, week: list[Snipe], month: list[Snipe], all_time: list[Snipe]) -> str:
    """What /snipes @someone shows."""
    def line(label: str, snipes: list[Snipe]) -> str:
        return (f"*{label}:* {plural(snipe_counts(snipes)[uid], 'snipe')} · "
                f"sniped {plural(sniped_counts(snipes)[uid], 'time')}")

    lines = [f"{at(uid)}'s snipe record", line("This week", week), line("This month", month),
             line("All time", all_time)]
    hits = Counter(t for s in all_time if s.sniper == uid for t in s.targets)
    by = Counter(s.sniper for s in all_time for t in s.targets if t == uid)
    if hits:
        fav, n = min(hits.items(), key=lambda kv: (-kv[1], kv[0]))
        lines.append(f":dart: Favorite target: {at(fav)} ({n})")
    if by:
        nem, n = min(by.items(), key=lambda kv: (-kv[1], kv[0]))
        lines.append(f":smiling_imp: Nemesis: {at(nem)} ({n})")
    if mine := [r for r in rivalries(all_time) if uid in r[:2]]:
        a, b, x, y = mine[0]
        other, mine_n, theirs = (b, x, y) if a == uid else (a, y, x)
        lines.append(f":crossed_swords: Top rival: {at(other)} ({mine_n}–{theirs})")
    return "\n".join(lines)
