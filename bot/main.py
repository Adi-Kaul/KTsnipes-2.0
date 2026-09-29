"""Runs KTsnipes 2.0: listens to #ktsnipes, keeps the tally, and posts the Sunday report.

    python -m bot.main                  # run forever (Socket Mode)
    python -m bot.main --backfill       # count every snipe in the channel's history, then exit
    python -m bot.main --preview        # print this week's report so far, then exit
    python -m bot.main --preview month  # ...or this month's, or all

"""

from __future__ import annotations

import argparse
import logging
import re
import sys
import threading

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from .config import Config, load_config
from .store import Store
from .tracker import SnipeTracker

log = logging.getLogger("ktsnipes")

CHANNEL_ID_RE = re.compile(r"^[CG][A-Z0-9]{6,}$")
USER_RE = re.compile(r"<@([UW][A-Z0-9]+)(?:\|[^>]*)?>")


def resolve_channel(client: WebClient, name_or_id: str) -> str:
    if CHANNEL_ID_RE.match(name_or_id):
        return name_or_id
    cursor = None
    while True:
        resp = client.conversations_list(types="public_channel,private_channel", exclude_archived=True,
                                         limit=200, cursor=cursor)
        for ch in resp["channels"]:
            if ch["name"] == name_or_id:
                return ch["id"]
        cursor = (resp.get("response_metadata") or {}).get("next_cursor")
        if not cursor:
            raise ValueError(f"Channel #{name_or_id} not found. If it's private, /invite @KTsnipes 2.0 to it first.")


def build_tracker(cfg: Config, client: WebClient) -> SnipeTracker:
    channel = resolve_channel(client, cfg.snipes_channel)
    report = resolve_channel(client, cfg.report_channel) if cfg.report_channel else channel
    bot_user = client.auth_test()["user_id"]
    log.info("Watching #%s; weekly report goes to %s", cfg.snipes_channel, cfg.report_channel or "the same channel")
    return SnipeTracker(client, cfg, Store(cfg.db_path), channel, report, bot_user)


def background_loop(tracker: SnipeTracker, stop: threading.Event) -> None:
    """Sweeps the channel every SWEEP_MINUTES and checks once a minute whether the report is due."""
    last_sweep = 0.0
    while not stop.is_set():
        try:
            now = tracker.clock()
            if now - last_sweep >= tracker.cfg.sweep_minutes * 60:
                n = tracker.sweep()
                last_sweep = now
                log.info("Sweep done: %d snipes in the last %g days", n, tracker.cfg.sweep_days)
            tracker.maybe_report()
        except SlackApiError as e:
            err = e.response.get("error")
            hint = " (invite the bot to the channel with /invite)" if err == "not_in_channel" else ""
            log.error("Slack API error: %s%s", err, hint)
        except Exception:
            log.exception("Background check failed")
        stop.wait(60)


def register(app: App, tracker: SnipeTracker) -> None:
    @app.event("message")
    def on_message(event):
        tracker.on_message_event(event)

    @app.command("/snipes")
    def snipes(ack, command, respond):
        ack()
        m = USER_RE.search(command.get("text") or "")
        run(respond, "/snipes", lambda: tracker.player_card(m.group(1)) if m else USAGE)

    @app.command("/snipes-rivals")
    def snipes_rivals(ack, command, respond):
        ack()
        uids = list(dict.fromkeys(USER_RE.findall(command.get("text") or "")))  # dedupe, keep order
        run(respond, "/snipes-rivals", lambda: tracker.rivals(uids))

    # One command per period so each shows up in Slack's autocomplete.
    for period, name in PERIOD_COMMANDS.items():
        def handler(ack, respond, period=period, name=name):
            ack()
            run(respond, name, lambda: tracker.period_report(period))
        app.command(name)(handler)


PERIOD_COMMANDS = {"week": "/snipes-week", "month": "/snipes-month", "all": "/snipes-alltime"}
USAGE = ("Usage: `/snipes @person` (someone's record), `/snipes-week`, `/snipes-month`, or `/snipes-alltime` "
         "(leaderboards and highlights), or `/snipes-rivals [@person] [@person]` (rivalries and head-to-heads)")


def run(respond, name: str, build) -> None:
    try:
        respond(build())
    except Exception as e:
        log.exception("%s failed", name)
        respond(f"Something went wrong: {e}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--backfill", action="store_true", help="count every snipe in the channel's history and exit")
    parser.add_argument("--preview", nargs="?", const="week", choices=["week", "month", "all"],
                        help="print this week's (or month's, or all-time) report so far and exit")
    args = parser.parse_args(argv)

    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        cfg = load_config()
    except ValueError as e:
        sys.exit(str(e))
    if not cfg.bot_token:
        sys.exit("SLACK_BOT_TOKEN is not set (put it in .env)")

    client = WebClient(token=cfg.bot_token)
    try:
        tracker = build_tracker(cfg, client)
    except SlackApiError as e:
        sys.exit(f"Slack rejected the startup checks: {e.response.get('error')} "
                 "(check SLACK_BOT_TOKEN and that the app is installed with the manifest's scopes)")
    except ValueError as e:
        sys.exit(str(e))

    if args.backfill:
        n = tracker.sweep(days=0, confirm=False)
        print(f"Counted {n} snipe posts from the channel's full history.")
        return 0
    if args.preview:
        print(tracker.period_report(args.preview))
        return 0

    if not cfg.app_token:
        sys.exit("SLACK_APP_TOKEN is not set (needed for Socket Mode; put it in .env)")
    if not tracker.store.snipes():
        # Fresh database (first deploy, or no volume): count the channel's whole history quietly.
        log.info("No snipes on record yet; backfilling from the channel's full history")
        log.info("Backfill done: %d snipe posts", tracker.sweep(days=0, confirm=False))
    app = App(token=cfg.bot_token)
    register(app, tracker)

    stop = threading.Event()
    threading.Thread(target=background_loop, args=(tracker, stop), daemon=True).start()
    try:
        SocketModeHandler(app, cfg.app_token).start()
    finally:
        stop.set()
    return 0


if __name__ == "__main__":
    sys.exit(main())
