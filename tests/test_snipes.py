from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

from slack_sdk.errors import SlackApiError

from bot.config import Config, load_config
from bot.snipes import Snipe, parse_snipe
from bot.stats import (best_day, kd, most_efficient, last_month_end_due, last_report_due, month_start, month_window, player_card, ranked, report, sniped_counts,
                       rivalries, snipe_counts, week_window, weekly_report)
from bot.rivals import head_to_head, person_rivals, rivals_board
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
    assert rivalries(WEEK) == [("A", "B", 2, 1)]  # A got B twice, B got A once; B–C is only 1 total


def test_weekly_report_contents():
    text = weekly_report(WEEK, 0, 1e10, TZ, permalink=lambda t: f"https://x/{t}")
    assert "*5 snipes* this week" in text
    assert ":first_place_medal: <@A> — 3" in text   # top sniper
    assert ":first_place_medal: <@B> — 3" in text   # most sniped
    assert "Best day:* <@A> got 3 snipes on Monday" in text
    assert f"<https://x/{WEEK[1].ts}|this shot>" in text and "9 reactions" in text
    assert "Rivalry of the week:* <@A> *2–1* <@B>" in text
    assert "Most efficient:* <@A> — 3.00 K/D (3 snipes, sniped 1 time)" in text


def test_most_efficient_needs_enough_snipes_and_breaks_ties_on_volume():
    assert kd(4, 0) == 4 and kd(3, 2) == 1.5
    lucky = [Snipe("1", "L", ["X"], 0)]                              # 1–0: not enough snipes to qualify
    steady = [Snipe(str(i), "S", ["X"], 0) for i in range(2, 8)]     # 6–1
    bigger = [Snipe(str(i), "B", ["X"], 0) for i in range(8, 20)]    # 12–2, same 6.00 K/D, more snipes
    back = [Snipe("20", "X", ["S"], 0), Snipe("21", "X", ["B", "B2"], 0), Snipe("22", "Y", ["B"], 0)]
    assert most_efficient(lucky + steady + back, 5) == ("S", 6, 1)
    assert most_efficient(lucky + steady + bigger + back, 5) == ("B", 12, 2)
    assert most_efficient(lucky, 5) is None
    hot = [Snipe(str(i), "H", ["X"], 0) for i in range(30, 34)]    # 4–0: under 5 snipes, but K/D 4.00 > 3
    assert most_efficient(lucky + steady + hot + back, 5) == ("S", 6, 1)
    assert most_efficient(lucky + hot, 5) == ("H", 4, 0)
    assert most_efficient(hot[:3], 5) is None                      # 3–0 is exactly 3.00, not above
    assert "Most efficient" not in report(lucky, "week", 0, 1e10, TZ)


def test_empty_week():
    assert "Zero snipes" in weekly_report([], 0, 1e10, TZ)


def test_player_card():
    card = player_card("B", WEEK[2:], WEEK[1:], WEEK)
    assert "*This week:* 1 snipe · sniped 1 time · K/D 1.00" in card
    assert "*This month:* 1 snipe · sniped 2 times · K/D 0.50" in card
    assert "*All time:* 1 snipe · sniped 3 times · K/D 0.33" in card
    assert "*This week:* 0 snipes · sniped 0 times · K/D —" in player_card("Z", [], [], WEEK)
    assert "Nemesis: <@A> (2)" in card
    assert "Top rival: <@A> (1–2)" in card


def test_month_and_all_time_reports():
    month = report(WEEK, "month", float(ts(2026, 9, 1, 0)), 1e10, TZ)
    assert "*KTsnipes Monthly Report* · September 2026" in month and "*5 snipes* this month" in month
    assert "on Mon Sep 28" in month and "Rivalry of the month" in month

    alltime = report(WEEK, "all", 0, 1e10, TZ)
    assert "*KTsnipes All-Time Report* · since Sep 28, 2026" in alltime and "all time" in alltime
    assert "*Biggest rivalry:*" in alltime and "Busiest day:* Sep 28, 2026" in alltime

    assert "No snipes on record yet" in report([], "all", 0, 1e10, TZ)


def test_month_boards_show_five_places():
    many = [Snipe(str(i), f"U{i}", ["X"] * 1, 0) for i in range(1, 8)]
    assert report(many, "week", 0, 1e10, TZ).count("<@U") == 5    # 7-way tie, capped at 5 rows
    lines = report(many, "month", 0, 1e10, TZ).split("*Most Sniped*")[0]
    assert lines.count("<@U") == 5


# ---- rivals ----

def _s(sniper, target, day):
    return Snipe(ts(2026, 10, day), sniper, [target], 0)


FEUD = [_s("A", "B", 1), _s("B", "A", 2), _s("A", "B", 3), _s("C", "D", 3), _s("C", "D", 4), _s("A", "C", 5)]


def test_rivalries_rank_by_total_then_closeness():
    assert rivalries(FEUD) == [("A", "B", 2, 1), ("C", "D", 2, 0)]


def test_rivals_board():
    board = rivals_board(FEUD[3:], FEUD)
    assert "1. <@A> *2–1* <@B> · 3 snipes" in board
    assert "2. <@C> *2–0* <@D> · 2 snipes _(one-sided)_" in board
    assert "Hottest this month*\n1. <@C> *2–0* <@D>" in board
    assert "No rivalries yet" in rivals_board([], [])


def test_person_rivals_from_their_side():
    text = person_rivals("B", FEUD)
    assert "<@A> — down *1–2*" in text
    assert "hasn't sniped" in person_rivals("Z", FEUD)


def test_head_to_head():
    text = head_to_head("B", "A", FEUD[2:], FEUD, FEUD, TZ, permalink=lambda t: f"https://x/{t}")
    assert "*All time:* <@B> *1–2* <@A> · <@A> leads by 1" in text
    assert "*This week:* <@B> *0–1* <@A>" in text
    assert f"First blood:* <@A> got <@B> on <https://x/{FEUD[0].ts}|Oct 1, 2026>" in text
    assert f"Latest:* <@A> got <@B> on <https://x/{FEUD[2].ts}|Oct 3, 2026>" in text
    assert "never sniped each other" in head_to_head("A", "D", [], [], FEUD, TZ)
    assert "same person" in head_to_head("A", "A", [], [], FEUD, TZ)


def test_tracker_rivals_routes_by_tag_count():
    now = [float(ts(2026, 10, 7, 9))]
    client = FakeClient([post(ts(2026, 10, 5)), post(ts(2026, 10, 6), user="U2", text="<@U1>")])
    tr = make(client, now)
    tr.sweep()
    assert "Top Rivalries" in tr.rivals([])
    assert "<@U1>'s rivals" in tr.rivals(["U1"])
    assert "Dead even." in tr.rivals(["U1", "U2"])


# ---- schedule ----

def test_month_start():
    assert month_start(float(ts(2026, 10, 17, 15)), TZ) == datetime(2026, 10, 1, tzinfo=TZ)


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



def test_monthly_report_is_due_on_the_last_evening_of_the_month():
    at = dtime(20, 0)
    assert last_month_end_due(float(ts(2026, 9, 30, 20, 1)), at, TZ) == datetime(2026, 9, 30, 20, tzinfo=TZ)
    assert last_month_end_due(float(ts(2026, 9, 30, 19)), at, TZ) == datetime(2026, 8, 31, 20, tzinfo=TZ)
    assert last_month_end_due(float(ts(2027, 3, 1)), at, TZ) == datetime(2027, 2, 28, 20, tzinfo=TZ)
    assert last_month_end_due(float(ts(2027, 1, 15)), at, TZ) == datetime(2026, 12, 31, 20, tzinfo=TZ)


def test_month_window_picks_up_where_last_month_left_off():
    start, end = month_window(datetime(2026, 9, 30, 20, tzinfo=TZ), dtime(20, 0), TZ)
    assert datetime.fromtimestamp(start, TZ) == datetime(2026, 8, 31, 20, tzinfo=TZ)
    assert datetime.fromtimestamp(end, TZ) == datetime(2026, 9, 30, 20, tzinfo=TZ)

# ---- tracker against a fake Slack ----

class FakeClient:
    def __init__(self, messages=()):
        self.messages = list(messages)
        self.posted, self.reacted = [], []

    def conversations_history(self, channel, limit, cursor=None, oldest="0"):
        assert float(oldest) > 0 or oldest == "0", "Slack rejects oldest=0.000000"
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


def test_period_reports_from_tracker():
    now = [float(ts(2026, 10, 7, 9))]                        # Wednesday Oct 7
    client = FakeClient([post(ts(2026, 10, 5)),                # this week
                         post(ts(2026, 10, 2), text="<@U3>"),  # this month, last week
                         post(ts(2026, 9, 20), text="<@U4>")]) # last month
    tr = make(client, now)
    tr.sweep(days=0)
    assert "*1 snipe* this week" in tr.period_report("week")
    assert "*2 snipes* this month" in tr.period_report("month")
    assert "*3 snipes* all time" in tr.period_report("all")
    assert "*This month:* 2 snipes" in tr.player_card("U1")


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


# ---- slash commands ----

def test_period_commands_reach_the_right_report(monkeypatch):
    """Goes through Bolt's real dispatch, which passes handler args by name."""
    from slack_bolt import App, BoltRequest
    from slack_bolt.authorization import AuthorizeResult
    import bot.main as main

    class Tracker:
        def period_report(self, period):
            return f"report:{period}"

    got = []
    monkeypatch.setattr(main, "run", lambda respond, name, build: got.append((name, build())))
    auth = AuthorizeResult(enterprise_id=None, team_id="T1", bot_token="xoxb-test", bot_user_id="UB", bot_id="B1")
    app = App(authorize=lambda **_: auth, signing_secret="x", request_verification_enabled=False)
    main.register(app, Tracker())
    for name in main.PERIOD_COMMANDS.values():
        body = f"command={name}&text=&team_id=T1&user_id=U1&channel_id=C1&response_url=https://example.com"
        assert app.dispatch(BoltRequest(body=body, mode="socket_mode")).status == 200
    assert got == [(name, f"report:{p}") for p, name in main.PERIOD_COMMANDS.items()]



def test_monthly_report_posts_once_with_a_channel_mention():
    due = datetime(2026, 9, 30, 20, tzinfo=TZ)  # a Wednesday, so no weekly report is due
    client = FakeClient([post(ts(2026, 8, 31, 21)),                 # after August's report: counts for September
                         post(ts(2026, 9, 15), text="<@U3>"),
                         post(ts(2026, 9, 30, 21), text="<@U9>")])  # after the report: October's
    now = [due.timestamp() - 60]
    tr = make(client, now)
    tr.sweep(days=0)
    assert not tr.maybe_report()
    now[0] = due.timestamp() + 30
    assert tr.maybe_report() and not tr.maybe_report()
    assert len(client.posted) == 1
    text = client.posted[0][1]
    assert text.startswith("<!channel> :dart: *KTsnipes Monthly Report* · September 2026")
    assert "*2 snipes* this month" in text and "<@U3>" in text and "<@U9>" not in text


def test_report_mention_and_monthly_can_be_turned_off(monkeypatch):
    monkeypatch.setenv("REPORT_MENTION", "none")
    monkeypatch.setenv("MONTHLY_REPORT", "0")
    cfg = load_config()
    assert cfg.report_mention == "" and not cfg.monthly_report
    monkeypatch.setenv("REPORT_MENTION", "@here")
    assert load_config().report_mention == "<!here>"

    due = datetime(2026, 9, 30, 20, tzinfo=TZ)
    client = FakeClient([post(ts(2026, 9, 15))])
    tr = SnipeTracker(client, cfg, Store(":memory:"), "CSNIPE", "CSNIPE", "UB", clock=lambda: due.timestamp() + 30)
    assert not tr.maybe_report() and client.posted == []
