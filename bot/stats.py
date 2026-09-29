"""Turns a list of snipes into leaderboards and the weekly report. Pure functions, no Slack calls."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .snipes import Snipe


# ---- the report schedule ----

def last_report_due(now: float, day: int, at, tz: ZoneInfo) -> datetime:
    """The most recent scheduled report time at or before now (e.g. last Sunday 8pm)."""
    local = datetime.fromtimestamp(now, tz)
    due = datetime.combine(local.date(), at, tz) - timedelta(days=(local.weekday() - day) % 7)
    return due if due <= local else due - timedelta(days=7)


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


def top_rivalry(snipes: list[Snipe]) -> tuple[str, str, int] | None:
    """The sniper -> target pair that happened most, if anyone got the same person twice."""
    c = Counter((s.sniper, t) for s in snipes for t in s.targets)
    if not c:
        return None
    (sniper, target), n = min(c.items(), key=lambda kv: (-kv[1], kv[0]))
    return (sniper, target, n) if n >= 2 else None


# ---- formatting ----

MEDALS = {1: ":first_place_medal:", 2: ":second_place_medal:", 3: ":third_place_medal:"}


def at(uid: str) -> str:
    return f"<@{uid}>"


def plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def board(counter: Counter, limit: int = 3, cap: int = 5) -> str:
    return "\n".join(f"{MEDALS.get(rank, f'{rank}.')} {at(u)} — {n}" for rank, u, n in ranked(counter, limit, cap))


def weekly_report(snipes: list[Snipe], start: float, end: float, tz: ZoneInfo, permalink=None) -> str:
    """The Sunday report. permalink(ts) -> URL, used to link the most-reacted snipe."""
    first = datetime.fromtimestamp(start, tz)
    last = datetime.fromtimestamp(end, tz) - timedelta(seconds=1)
    span = f"{first:%b %-d} – {last:%b %-d}"
    head = f":dart: *KTsnipes Weekly Report* · {span}"
    if not snipes:
        return f"{head}\n\nZero snipes this week. Nobody's watching their back and nobody's taking the shot. :sleeping:"

    made, got = snipe_counts(snipes), sniped_counts(snipes)
    total = sum(made.values())
    parts = [
        head,
        f"*{plural(total, 'snipe')}* this week · {plural(len(made), 'sniper')} · {plural(len(got), 'victim')}",
        f":gun: *Top Snipers*\n{board(made)}",
        f":skull: *Most Sniped*\n{board(got)}",
    ]

    highlights = []
    if (bd := best_day(snipes, tz)) and bd[2] >= 2:
        user, day, n = bd
        highlights.append(f":fire: *Best day:* {at(user)} got {plural(n, 'snipe')} on {day:%A}")
    if mr := most_reacted(snipes):
        victims = " ".join(at(t) for t in mr.targets)
        shot = f"<{permalink(mr.ts)}|this shot>" if permalink else "this shot"
        highlights.append(f":star-struck: *Most reacted:* {shot} by {at(mr.sniper)} on {victims} "
                          f"({plural(mr.reactions, 'reaction')})")
    if rv := top_rivalry(snipes):
        sniper, target, n = rv
        highlights.append(f":crossed_swords: *Rivalry of the week:* {at(sniper)} sniped {at(target)} {n} times")
    if (busy := busiest_day(snipes, tz)) and busy[1] >= 2:
        highlights.append(f":calendar: *Busiest day:* {busy[0]:%A} ({plural(busy[1], 'snipe')})")
    if highlights:
        parts.append("\n".join(highlights))
    return "\n\n".join(parts)


def leaderboard(week: list[Snipe], all_time: list[Snipe]) -> str:
    """What /snipes shows: this week so far and all time."""
    def section(title: str, snipes: list[Snipe]) -> str:
        if not snipes:
            return f"*{title}*\nNo snipes yet."
        return (f"*{title}* ({plural(sum(snipe_counts(snipes).values()), 'snipe')})\n"
                f"_Snipers_\n{board(snipe_counts(snipes), 5, 5)}\n"
                f"_Sniped_\n{board(sniped_counts(snipes), 5, 5)}")
    return f"{section('This week so far', week)}\n\n{section('All time', all_time)}"


def player_card(uid: str, week: list[Snipe], all_time: list[Snipe]) -> str:
    """What /snipes @someone shows."""
    def line(label: str, snipes: list[Snipe]) -> str:
        return (f"*{label}:* {plural(snipe_counts(snipes)[uid], 'snipe')} · "
                f"sniped {plural(sniped_counts(snipes)[uid], 'time')}")

    lines = [f"{at(uid)}'s snipe record", line("This week", week), line("All time", all_time)]
    hits = Counter(t for s in all_time if s.sniper == uid for t in s.targets)
    by = Counter(s.sniper for s in all_time for t in s.targets if t == uid)
    if hits:
        fav, n = min(hits.items(), key=lambda kv: (-kv[1], kv[0]))
        lines.append(f":dart: Favorite target: {at(fav)} ({n})")
    if by:
        nem, n = min(by.items(), key=lambda kv: (-kv[1], kv[0]))
        lines.append(f":smiling_imp: Nemesis: {at(nem)} ({n})")
    return "\n".join(lines)
