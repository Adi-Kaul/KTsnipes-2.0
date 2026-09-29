from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

from slack_sdk.errors import SlackApiError

from bot.config import Config
from bot.snipes import Snipe, parse_snipe
from bot.stats import (best_day, last_report_due, player_card, ranked, sniped_counts, snipe_counts,
                       top_rivalry, week_window, weekly_report)
from bot.store import Store
from bot.tracker import SnipeTracker

TZ = ZoneInfo("America/Detroit")
IMG = [{"mimetype": "image/jpeg"}]


def ts(y, mo, d, h=12, mi=0):
    return f"{datetime(y, mo, d, h, mi, tzinfo=TZ).timestamp():.6f}"


def post(t, user="U1", text="<@U2> gotcha", files=IMG, **kw):
    return {"ts": t, "user": user, "text": text, "files": files, **kw}


# ---- what counts as a snipe ----

def test_image_plus_tag_is_a_snipe():
    s = parse_snipe(post("1.0", text="<@U2> and <@U3|sam> caught lacking"))
    assert s.sniper == "U1" and s.targets == ["U2", "U3"]


def test_needs_an_image():
    assert parse_snipe(post("1.0", files=None)) is None
    assert parse_snipe(post("1.0", files=[{"mimetype": "application/pdf"}])) is None


def test_needs_a_tag_and_self_tags_and_bots_dont_count():
    assert parse_snipe(post("1.0", text="no tag")) is None
    assert parse_snipe(post("1.0", text="<@U1> selfie")) is None
    assert parse_snipe(post("1.0", text="<@UBOT>"), is_person=lambda u: u != "UBOT") is None


def test_thread_replies_dont_count_unless_broadcast():
    assert parse_snipe(post("2.0", thread_ts="1.0")) is None
    assert parse_snipe(post("2.0", thread_ts="1.0", subtype="thread_broadcast")) is not None


def test_bot_confirmation_reaction_isnt_counted():
    msg = post("1.0", reactions=[{"name": "dart", "count": 1, "users": ["UB"]},
                                 {"name": "joy", "count": 3, "users": ["U4", "U5", "U6"]}])
    assert parse_snipe(msg, bot_user="UB").reactions == 3


def test_duplicate_tags_count_once():
    assert parse_snipe(post("1.0", text="<@U2> <@U2>")).targets == ["U2"]


# ---- tallies ----

WEEK = [
    Snipe(ts(2026, 9, 28, 10), "A", ["B", "C"], 2),
    Snipe(ts(2026, 9, 28, 15), "A", ["B"], 9),
    Snipe(ts(2026, 9, 30, 9), "B", ["A"], 1),
    Snipe(ts(2026, 10, 1, 9), "C", ["B"], 0),
]


def test_snipe_vs_sniped():
    assert snipe_counts(WEEK) == {"A": 3, "B": 1, "C": 1}
    assert sniped_counts(WEEK) == {"B": 3, "C": 1, "A": 1}


def test_ranked_shares_ties():
    assert ranked(snipe_counts(WEEK)) == [(1, "A", 3), (2, "B", 1), (2, "C", 1)]


def test_best_day_and_rivalry():
    user, day, n = best_day(WEEK, TZ)
    assert (user, day.isoformat(), n) == ("A", "2026-09-28", 3)
    assert top_rivalry(WEEK) == ("A", "B", 2)


def test_weekly_report_contents():
    text = weekly_report(WEEK, 0, 1e10, TZ, permalink=lambda t: f"https://x/{t}")
    assert "*5 snipes* this week" in text
    assert ":first_place_medal: <@A> — 3" in text   # top sniper
    assert ":first_place_medal: <@B> — 3" in text   # most sniped
    assert "Best day:* <@A> got 3 snipes on Monday" in text
    assert f"<https://x/{WEEK[1].ts}|this shot>" in text and "9 reactions" in text
    assert "<@A> sniped <@B> 2 times" in text


def test_empty_week():
    assert "Zero snipes" in weekly_report([], 0, 1e10, TZ)


def test_player_card():
    card = player_card("B", WEEK[2:], WEEK)
    assert "*This week:* 1 snipe · sniped 1 time" in card
    assert "*All time:* 1 snipe · sniped 3 times" in card
    assert "Nemesis: <@A> (2)" in card


# ---- schedule ----

def test_last_report_due_is_most_recent_sunday_8pm():
    sun_8pm = datetime(2026, 10, 4, 20, 0, tzinfo=TZ)
    assert last_report_due(sun_8pm.timestamp(), 6, dtime(20), TZ) == sun_8pm
    assert last_report_due(sun_8pm.timestamp() - 1, 6, dtime(20), TZ) == datetime(2026, 9, 27, 20, tzinfo=TZ)
    wed = datetime(2026, 10, 7, 9, tzinfo=TZ).timestamp()
    assert last_report_due(wed, 6, dtime(20), TZ) == sun_8pm


def test_week_window_is_seven_days_across_dst():
    due = datetime(2026, 11, 8, 20, tzinfo=TZ)  # DST ended Nov 1
    start, end = week_window(due)
    assert datetime.fromtimestamp(start, TZ) == datetime(2026, 11, 1, 20, tzinfo=TZ)


# ---- tracker against a fake Slack ----

class FakeClient:
    def __init__(self, messages=()):
        self.messages = list(messages)
        self.posted, self.reacted = [], []

    def conversations_history(self, channel, oldest, limit, cursor=None):
        return {"messages": [m for m in self.messages if float(m["ts"]) >= float(oldest)]}

    def users_info(self, user):
        return {"user": {"id": user, "is_bot": user.startswith("UBOT")}}

    def reactions_add(self, channel, timestamp, name):
        if (timestamp, name) in self.reacted:
            raise SlackApiError("dup", {"ok": False, "error": "already_reacted"})
        self.reacted.append((timestamp, name))

    def chat_getPermalink(self, channel, message_ts):
        return {"permalink": f"https://slack/{message_ts}"}

    def chat_postMessage(self, channel, text, **_):
        self.posted.append((channel, text))


def make(client, now):
    return SnipeTracker(client, Config(), Store(":memory:"), "CSNIPE", "CSNIPE", "UB", clock=lambda: now[0])


def test_events_add_edit_delete():
    now = [float(ts(2026, 10, 1))]
    client = FakeClient()
    tr = make(client, now)
    t = ts(2026, 10, 1, 11)
    tr.on_message_event({**post(t), "channel": "CSNIPE"})
    tr.on_message_event({**post(t), "channel": "COTHER"})
    assert snipe_counts(tr.store.snipes()) == {"U1": 1}
    assert client.reacted == [(t, "dart")]

    # edited to tag two people: still one post, now two snipes, no second reaction
    tr.on_message_event({"channel": "CSNIPE", "subtype": "message_changed",
                         "message": post(t, text="<@U2> <@U3>")})
    assert snipe_counts(tr.store.snipes()) == {"U1": 2} and len(client.reacted) == 1

    # edited to remove the tag: no longer a snipe
    tr.on_message_event({"channel": "CSNIPE", "subtype": "message_changed", "message": post(t, text="nvm")})
    assert tr.store.snipes() == []

    tr.on_message_event({**post(t), "channel": "CSNIPE"})
    tr.on_message_event({"channel": "CSNIPE", "subtype": "message_deleted", "deleted_ts": t})
    assert tr.store.snipes() == []


def test_sweep_catches_missed_posts_and_deletions():
    now = [float(ts(2026, 10, 1))]
    a, b = ts(2026, 9, 30), ts(2026, 9, 30, 13)
    client = FakeClient([post(a), post(b, user="U3", text="<@U1>"), post(ts(2026, 9, 30, 14), text="hi")])
    tr = make(client, now)
    assert tr.sweep() == 2
    client.messages = [m for m in client.messages if m["ts"] != b]  # deleted while bot was offline
    assert tr.sweep() == 1
    assert [s.ts for s in tr.store.snipes()] == [a]


def test_backfill_doesnt_react():
    client = FakeClient([post(ts(2025, 1, 5))])
    tr = make(client, [float(ts(2026, 10, 1))])
    assert tr.sweep(days=0, confirm=False) == 1 and client.reacted == []


def test_weekly_report_posts_once_and_skips_stale():
    due = datetime(2026, 10, 4, 20, tzinfo=TZ).timestamp()
    client = FakeClient([post(ts(2026, 9, 30)), post(ts(2026, 9, 26), text="<@U9>")])  # 2nd is last week
    now = [due - 60]
    tr = make(client, now)
    tr.sweep()
    tr.store.mark_report_sent("2026-09-27", 0)
    assert not tr.maybe_report()                 # not Sunday 8pm yet
    now[0] = due + 30
    assert tr.maybe_report() and not tr.maybe_report()
    assert len(client.posted) == 1
    text = client.posted[0][1]
    assert "Sep 27 – Oct 4" in text and "*1 snipe* this week" in text and "<@U9>" not in text

    now[0] = due + 7 * 86400 + 13 * 3600         # bot was down for next week's report
    assert not tr.maybe_report() and len(client.posted) == 1
