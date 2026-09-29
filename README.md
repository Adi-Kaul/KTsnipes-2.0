# KTsnipes 2.0 🎯

A Slack bot that keeps the tally for **#ktsnipes**.

**What counts as a snipe:** a post in #ktsnipes with a photo that @tags at least one person.

- The person who **posted the photo sniped** someone. They get +1 snipe for each person they tagged.
- Each person **tagged got sniped**. They get +1 sniped.

When the bot counts a snipe, it reacts with 🎯 so you know it counted. Edits and deletions are picked up too: if you add a tag later, it counts, and if you delete the post, it comes off the tally.

It doesn't count thread replies (unless you check "Also send to channel"), tagging yourself, or tagging a bot.

## The Sunday report

Every **Sunday at 8pm** (Detroit time), the bot posts the week's report in #ktsnipes:

> 🎯 **KTsnipes Weekly Report** · Sep 27 – Oct 4
> **23 snipes** this week · 9 snipers · 14 victims
>
> 🔫 **Top Snipers**
> 🥇 @alex — 7  🥈 @sam — 5  🥉 @jordan — 3
>
> 💀 **Most Sniped**
> 🥇 @taylor — 6 …
>
> 🔥 **Best day:** @alex got 4 snipes on Wednesday
> 🤩 **Most reacted:** this shot by @sam on @taylor (18 reactions)
> ⚔️ **Rivalry of the week:** @alex sniped @taylor 3 times
> 📅 **Busiest day:** Friday (8 snipes)

The week runs from last Sunday 8pm to this Sunday 8pm.

## Slash commands

Only you see the replies.

- `/snipes` shows the leaderboard (snipers and sniped) for this week and all time.
- `/snipes @person` shows someone's record: snipes, times sniped, favorite target, and nemesis.
- `/snipes-report` previews this week's report so far.

## Setup

### 1. Create the Slack app

1. Go to <https://api.slack.com/apps> → **Create New App** → **From a manifest**, pick the workspace, and paste in [`manifest.yaml`](manifest.yaml).
2. **Install to Workspace**. Copy the **Bot User OAuth Token** (`xoxb-…`) from **OAuth & Permissions**.
3. **Basic Information** → **App-Level Tokens** → **Generate**, and add the `connections:write` scope. Copy the token (`xapp-…`).
4. In Slack, run `/invite @KTsnipes 2.0` in #ktsnipes.

### 2. Run it locally (optional, to test)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # paste in the two tokens
python -m bot.main --preview   # prints this week's report without posting anything
python -m bot.main             # runs the bot
```

The first time it runs with an empty database, it reads the channel's whole history and counts every past snipe. It doesn't react to old ones.

### 3. Deploy on Railway

1. Push this repo to GitHub.
2. On <https://railway.com>: **New Project** → **Deploy from GitHub repo** → pick this repo. It builds from the `Dockerfile`.
3. **Variables**: add `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN`. Add any settings below you want to change.
4. **Add a Volume** to the service, mounted at **`/data`**. This is where the tally lives (`/data/snipes.db`). Without it, the bot re-counts from channel history on every redeploy, which works but is slower and forgets reports it already posted.
5. Check **Deployments** → **View logs** for:
   ```
   Watching #ktsnipes; weekly report goes to the same channel
   ⚡️ Bolt app is running!
   ```

Only run **one copy** of the bot at a time (`railway.toml` pins it to one replica). Two copies would post the report twice.

## Settings

All are environment variables, and all are optional.

| Variable | Default | What it does |
|---|---|---|
| `SNIPES_CHANNEL` | `ktsnipes` | Channel to watch (name or ID) |
| `REPORT_CHANNEL` | same as above | Where the weekly report goes |
| `TIMEZONE` | `America/Detroit` | Used for the report time and for "best day" |
| `REPORT_DAY` | `sunday` | Day the report goes out |
| `REPORT_TIME` | `20:00` | Time the report goes out (24-hour) |
| `CONFIRM_EMOJI` | `dart` | Emoji the bot reacts with when it counts a snipe. Leave blank to turn off. |
| `SWEEP_MINUTES` | `10` | How often it re-reads the channel to pick up edits, deletions, reaction counts, and anything posted while it was down |
| `SWEEP_DAYS` | `8` | How far back each re-read looks |
| `DB_PATH` | `/data/snipes.db` in Docker | Where the tally is stored |
| `DRY_RUN` | `false` | Log the weekly report instead of posting it |

If the bot is offline when the report is due, it posts it when it comes back, as long as that's within 12 hours. After that, it skips that week.

## Development

```bash
pip install pytest && pytest
```

Tests run without Slack, using a fake Slack client and a fake clock.

| File | What's in it |
|---|---|
| `bot/snipes.py` | What counts as a snipe |
| `bot/store.py` | SQLite tally |
| `bot/stats.py` | Leaderboards and the weekly report text |
| `bot/tracker.py` | Keeps the tally in sync with the channel and posts the report |
| `bot/main.py` | Slack wiring, slash commands, background loop |
