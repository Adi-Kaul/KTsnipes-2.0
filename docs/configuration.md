# Configuration reference

Every setting is an **environment variable**. There's no config file, so on Railway you set everything in the **Variables** tab, and locally you put it in `.env` (it loads automatically).

Only the two tokens are required. Everything else has a default that works for #ktsnipes out of the box.

Settings are checked at startup. A bad value like `REPORT_DAY=sundy` or `REPORT_TIME=8pm` stops the bot with an error instead of being silently ignored.

## Tokens

| Variable | Required | Description |
|---|---|---|
| `SLACK_BOT_TOKEN` | yes | The `xoxb-…` token from **Install App**. |
| `SLACK_APP_TOKEN` | yes, to run the bot continuously | The `xapp-…` token with the `connections:write` scope. It isn't needed for `--backfill` or `--preview`. |

## Channels

| Variable | Default | Description |
|---|---|---|
| `SNIPES_CHANNEL` | `ktsnipes` | The channel to watch. Use its name (`ktsnipes` or `#ktsnipes`) or its ID (`C0123ABCD`). |
| `REPORT_CHANNEL` | *(same as `SNIPES_CHANNEL`)* | Where the weekly report goes. Invite the bot there too. |

## Report schedule

| Variable | Default | Description |
|---|---|---|
| `REPORT_DAY` | `sunday` | Day of the week the report goes out. Full day name, any capitalization. |
| `REPORT_TIME` | `20:00` | Time the report goes out, 24-hour `HH:MM`. |
| `TIMEZONE` | `America/Detroit` | The timezone for `REPORT_TIME`, and for deciding which day a snipe happened on ("Best day", "Busiest day"). Any [tz database name](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones), like `America/New_York` or `America/Los_Angeles`. |

The report covers the 7 days leading up to it. With the defaults, that's Sunday 8:00pm to the next Sunday 7:59pm. Daylight saving changes are handled; the report always goes out at 8pm local time.

The bot checks whether the report is due once a minute, so it posts within a minute of `REPORT_TIME`. If it was offline at that time, it posts the report late as long as it's back within 12 hours, and skips that week otherwise.

## Tracking

| Variable | Default | Description |
|---|---|---|
| `CONFIRM_EMOJI` | `dart` | The emoji the bot reacts with when it counts a snipe, without colons. Set it to empty (`CONFIRM_EMOJI=`) to turn reactions off. The bot's own reaction never counts toward "Most reacted". |
| `SWEEP_MINUTES` | `10` | How often the bot re-reads the channel. Edits and deletions are picked up instantly through Slack events; the sweep is a safety net for anything missed while the bot was offline, and it's how reaction counts stay fresh. |
| `SWEEP_DAYS` | `8` | How far back each sweep reads. Keep it at 7 or more so the whole report week is re-checked. |

## Other options

| Variable | Default | Description |
|---|---|---|
| `DB_PATH` | `snipes.db` locally, `/data/snipes.db` in Docker | The SQLite file with the tally. On a host, put it on a persistent volume (see [deployment.md](deployment.md)). |
| `DRY_RUN` | `false` | `1`/`true` to log the weekly report instead of posting it, and skip the 🎯 reactions. Snipes are still counted. |

## Full example

This `.env` sets every option to its default:

```bash
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
SNIPES_CHANNEL=ktsnipes
REPORT_CHANNEL=
TIMEZONE=America/Detroit
REPORT_DAY=sunday
REPORT_TIME=20:00
CONFIRM_EMOJI=dart
SWEEP_MINUTES=10
SWEEP_DAYS=8
DB_PATH=snipes.db
DRY_RUN=false
```

## Changing the rules

What counts as a snipe isn't a setting; it's a few lines of code in [`bot/snipes.py`](../bot/snipes.py). See [how-it-works.md](how-it-works.md#changing-what-counts) for common tweaks, like counting videos or making a group photo count as one snipe.
