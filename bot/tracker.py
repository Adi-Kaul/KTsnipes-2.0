"""Keeps the tally in sync with #ktsnipes and posts the weekly report."""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime

from slack_sdk.errors import SlackApiError

from .config import Config
from .snipes import parse_snipe
from .stats import last_report_due, month_start, player_card, report, week_window, weekly_report
from .store import Store

log = logging.getLogger(__name__)

# If the bot was down when a report was due, still post it if it comes back within this long.
REPORT_GRACE_HOURS = 12


class SnipeTracker:
    def __init__(self, client, cfg: Config, store: Store, channel: str, report_channel: str,
                 bot_user: str | None = None, clock=time.time):
        self.client = client
        self.cfg = cfg
        self.store = store
        self.channel = channel
        self.report_channel = report_channel
        self.bot_user = bot_user
        self.clock = clock
        self._people: dict[str, bool] = {}
        self._report_lock = threading.Lock()

    # ---- recognizing snipes ----

    def is_person(self, uid: str) -> bool:
        """Tagging a bot doesn't count as sniping it."""
        if uid not in self._people:
            try:
                user = self.client.users_info(user=uid)["user"]
                self._people[uid] = not user.get("is_bot") and uid != "USLACKBOT"
            except SlackApiError as e:
                log.warning("Couldn't look up %s (%s); counting them as a person", uid, e.response.get("error"))
                return True
        return self._people[uid]

    def record(self, msg: dict, confirm: bool = True) -> bool:
        """Adds, updates, or removes the snipe in one message. Returns True if it's a snipe."""
        snipe = parse_snipe(msg, self.is_person, self.bot_user)
        if snipe is None:
            if self.store.delete(msg["ts"]):
                log.info("Snipe %s no longer counts (edited)", msg["ts"])
            return False
        if self.store.save(snipe):
            log.info("Snipe %s: %s sniped %s", snipe.ts, snipe.sniper, ", ".join(snipe.targets))
            if confirm:
                self.confirm(msg)
        return True

    def confirm(self, msg: dict) -> None:
        emoji = self.cfg.confirm_emoji
        if not emoji or self.cfg.dry_run:
            return
        if any(r["name"] == emoji and self.bot_user in r.get("users", []) for r in msg.get("reactions") or []):
            return
        try:
            self.client.reactions_add(channel=self.channel, timestamp=msg["ts"], name=emoji)
        except SlackApiError as e:
            if e.response.get("error") != "already_reacted":
                log.warning("Couldn't react to snipe %s: %s", msg["ts"], e.response.get("error"))

    def on_message_event(self, event: dict) -> None:
        if event.get("channel") != self.channel:
            return
        subtype = event.get("subtype")
        if subtype == "message_deleted":
            if self.store.delete(event["deleted_ts"]):
                log.info("Snipe %s deleted", event["deleted_ts"])
        elif subtype == "message_changed":
            self.record(event["message"])
        else:
            self.record(event)

    # ---- catching up ----

    def history(self, oldest: float):
        cursor = None
        while True:
            resp = self.client.conversations_history(
                channel=self.channel, oldest=f"{oldest:.6f}", limit=200, cursor=cursor
            )
            yield from resp["messages"]
            cursor = (resp.get("response_metadata") or {}).get("next_cursor")
            if not cursor:
                return

    def sweep(self, days: float | None = None, confirm: bool = True) -> int:
        """Re-reads the channel so edits, deletions, reaction counts, and snipes posted while the
        bot was offline are all reflected. days=None uses SWEEP_DAYS; days=0 means all history.
        Returns how many snipes are in that window."""
        now = self.clock()
        if days is None:
            days = self.cfg.sweep_days
        oldest = now - days * 86400 if days else 0
        messages = list(self.history(oldest))  # read everything first, so a failed read never deletes anything
        found = {m["ts"] for m in messages if self.record(m, confirm)}
        for s in self.store.snipes(oldest, now):
            if s.ts not in found:
                self.store.delete(s.ts)
                log.info("Snipe %s is gone from the channel; removed it", s.ts)
        return len(found)

    # ---- reports ----

    def permalink(self, ts: str) -> str:
        return self.client.chat_getPermalink(channel=self.channel, message_ts=ts)["permalink"]

    def last_due(self) -> datetime:
        return last_report_due(self.clock(), self.cfg.report_day, self.cfg.report_time, self.cfg.tz)

    def report_for(self, due: datetime) -> str:
        start, end = week_window(due)
        return weekly_report(self.store.snipes(start, end), start, end, self.cfg.tz, self.permalink)

    def period_start(self, period: str) -> float:
        """Where "this week" (since the last report), "this month", and "all time" begin."""
        if period == "week":
            return self.last_due().timestamp()
        if period == "month":
            return month_start(self.clock(), self.cfg.tz).timestamp()
        return 0.0

    def period_report(self, period: str) -> str:
        """The report for this week, month, or all time, as it stands right now."""
        start, now = self.period_start(period), self.clock()
        return report(self.store.snipes(start, now + 1), period, start, now + 1, self.cfg.tz, self.permalink)

    def maybe_report(self) -> bool:
        """Posts the weekly report if one is due and hasn't gone out. Returns True if it posted."""
        with self._report_lock:
            due = self.last_due()
            key = due.date().isoformat()
            if self.store.report_sent(key):
                return False
            if self.clock() - due.timestamp() > REPORT_GRACE_HOURS * 3600:
                self.store.mark_report_sent(key, self.clock())  # too late; skip it rather than post days later
                log.warning("Missed the report due %s (bot was offline); skipping it", key)
                return False
            self.sweep()  # fresh reaction counts and edits right before posting
            text = self.report_for(due)
            if self.cfg.dry_run:
                log.info("[dry run] would post the weekly report to %s:\n%s", self.report_channel, text)
            else:
                self.client.chat_postMessage(channel=self.report_channel, text=text, unfurl_links=False)
            self.store.mark_report_sent(key, self.clock())
            log.info("Posted the weekly report for %s", key)
            return True

    # ---- slash command ----

    def player_card(self, uid: str) -> str:
        return player_card(uid, *(self.store.snipes(self.period_start(p)) for p in ("week", "month", "all")))
