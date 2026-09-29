"""SQLite tally of every snipe, plus which weekly and monthly reports have already gone out."""

from __future__ import annotations

import sqlite3
import threading

from .snipes import Snipe


class Store:
    def __init__(self, path: str):
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.executescript(
            """CREATE TABLE IF NOT EXISTS snipes (
                ts TEXT PRIMARY KEY,          -- Slack message timestamp (also the post time)
                sniper TEXT NOT NULL,
                reactions INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS targets (
                ts TEXT NOT NULL REFERENCES snipes (ts) ON DELETE CASCADE,
                target TEXT NOT NULL,
                position INTEGER NOT NULL,
                PRIMARY KEY (ts, target)
            );
            CREATE TABLE IF NOT EXISTS reports (
                week_key TEXT PRIMARY KEY,    -- weekly: date it was due, e.g. 2026-10-04; monthly: month:2026-09
                posted_at REAL NOT NULL
            );
            PRAGMA foreign_keys = ON;"""
        )

    def save(self, snipe: Snipe) -> bool:
        """Adds or updates a snipe (edits can change who was tagged). Returns True if it's new."""
        with self._lock:
            new = self._db.execute("SELECT 1 FROM snipes WHERE ts = ?", (snipe.ts,)).fetchone() is None
            self._db.execute(
                """INSERT INTO snipes (ts, sniper, reactions) VALUES (?, ?, ?)
                   ON CONFLICT (ts) DO UPDATE SET sniper = excluded.sniper, reactions = excluded.reactions""",
                (snipe.ts, snipe.sniper, snipe.reactions),
            )
            self._db.execute("DELETE FROM targets WHERE ts = ?", (snipe.ts,))
            self._db.executemany(
                "INSERT INTO targets (ts, target, position) VALUES (?, ?, ?)",
                [(snipe.ts, t, i) for i, t in enumerate(snipe.targets)],
            )
            self._db.commit()
            return new

    def delete(self, ts: str) -> bool:
        with self._lock:
            n = self._db.execute("DELETE FROM snipes WHERE ts = ?", (ts,)).rowcount
            self._db.commit()
            return n > 0

    def snipes(self, start: float = 0, end: float = float("inf")) -> list[Snipe]:
        """Snipes posted in [start, end), oldest first."""
        with self._lock:
            rows = self._db.execute(
                "SELECT ts, sniper, reactions FROM snipes WHERE CAST(ts AS REAL) >= ? AND CAST(ts AS REAL) < ?",
                (start, min(end, 1e12)),
            ).fetchall()
            targets: dict[str, list[str]] = {}
            for ts, target in self._db.execute(
                """SELECT t.ts, t.target FROM targets t JOIN snipes s ON s.ts = t.ts
                   WHERE CAST(s.ts AS REAL) >= ? AND CAST(s.ts AS REAL) < ? ORDER BY t.ts, t.position""",
                (start, min(end, 1e12)),
            ):
                targets.setdefault(ts, []).append(target)
        return sorted((Snipe(ts, sniper, targets.get(ts, []), r) for ts, sniper, r in rows),
                      key=lambda s: float(s.ts))

    def report_sent(self, week_key: str) -> bool:
        with self._lock:
            return self._db.execute("SELECT 1 FROM reports WHERE week_key = ?", (week_key,)).fetchone() is not None

    def mark_report_sent(self, week_key: str, at: float) -> None:
        with self._lock:
            self._db.execute("INSERT OR IGNORE INTO reports (week_key, posted_at) VALUES (?, ?)", (week_key, at))
            self._db.commit()
