"""Settings come from environment variables (or a .env file locally), so Railway needs no config file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import time as dtime
from zoneinfo import ZoneInfo

MENTIONS = {"channel": "<!channel>", "here": "<!here>", "none": ""}
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


@dataclass
class Config:
    bot_token: str = ""
    app_token: str = ""

    # Where snipes are posted. Name ("ktsnipes") or ID ("C0123...").
    snipes_channel: str = "ktsnipes"
    # Where the weekly report goes. Empty = the snipes channel.
    report_channel: str = ""

    timezone: str = "America/Detroit"
    report_day: int = 6  # 0 = Monday ... 6 = Sunday
    report_time: dtime = dtime(20, 0)
    # Also post a monthly report on the last day of each month at report_time.
    monthly_report: bool = True
    # Prefix for posted reports: "<!channel>", "<!here>", or "" for no mention.
    report_mention: str = "<!channel>"

    # Emoji the bot reacts with when it counts a snipe. Empty (the default) = don't react.
    confirm_emoji: str = ""
    # How often to re-read the channel to catch edits, deletions, reaction counts, and anything missed while offline.
    sweep_minutes: float = 10
    # How far back each sweep looks.
    sweep_days: float = 8

    db_path: str = "snipes.db"
    dry_run: bool = False

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()  # pasted values often carry a trailing newline


def load_config() -> Config:
    day = _env("REPORT_DAY", "sunday").lower()
    if day not in DAYS:
        raise ValueError(f"REPORT_DAY must be a day of the week, got {day!r}")
    try:
        hh, mm = _env("REPORT_TIME", "20:00").split(":")
        report_time = dtime(int(hh), int(mm))
    except ValueError:
        raise ValueError("REPORT_TIME must look like 20:00 (24-hour)") from None
    mention = _env("REPORT_MENTION", "channel").lower().lstrip("@") or "none"
    if mention not in MENTIONS:
        raise ValueError(f"REPORT_MENTION must be channel, here, or none, got {mention!r}")

    cfg = Config(
        bot_token=_env("SLACK_BOT_TOKEN"),
        app_token=_env("SLACK_APP_TOKEN"),
        snipes_channel=_env("SNIPES_CHANNEL", "ktsnipes").lstrip("#"),
        report_channel=_env("REPORT_CHANNEL").lstrip("#"),
        timezone=_env("TIMEZONE", "America/Detroit"),
        report_day=DAYS.index(day),
        report_time=report_time,
        monthly_report=_env("MONTHLY_REPORT", "1").lower() not in ("0", "false", "no"),
        report_mention=MENTIONS[mention],
        confirm_emoji=_env("CONFIRM_EMOJI", "").strip(":"),
        sweep_minutes=float(_env("SWEEP_MINUTES", "10")),
        sweep_days=float(_env("SWEEP_DAYS", "8")),
        db_path=_env("DB_PATH", "snipes.db"),
        dry_run=_env("DRY_RUN").lower() in ("1", "true", "yes"),
    )
    cfg.tz  # fail fast on a bad TIMEZONE
    return cfg
