# Setup guide

This guide takes you from nothing to a working bot in your Slack. It takes about 15 minutes.

**What you need**
- A Mac, Linux, or Windows computer with **Python 3.10 or newer**. Check with `python3 --version`.
- Permission to install apps in your Slack workspace. If you don't have it, a workspace admin can approve the app for you.

That's it. There's no roster to build: anyone who posts or gets tagged in #ktsnipes is on the board automatically.

---

## 1. Create the Slack app

1. Open <https://api.slack.com/apps> and click **Create New App** → **From a manifest**.
2. Pick your workspace and click **Next**.
3. Choose the **YAML** tab. Delete what's there and paste in the entire contents of [`manifest.yaml`](../manifest.yaml).
4. Click **Next**, then **Create**.
   - Slack may warn that *"Socket Mode … requires additional setup in App Settings."* That's expected; click **Create** anyway. The extra setup is the app-level token you'll make in the next step.

The manifest sets up everything the bot needs: its name, the `/snipes` commands, Socket Mode, the message events, and these permissions:

| Permission | Why the bot needs it |
|---|---|
| `channels:history`, `groups:history` | To read posts in #ktsnipes (public or private) |
| `channels:read`, `groups:read` | To find the channel by name |
| `files:read` | To see that a post has a photo attached |
| `users:read` | To tell people apart from bots, so tagging a bot doesn't count |
| `reactions:write` | To react 🎯 to snipes it counted |
| `chat:write` | To post the weekly report |
| `commands` | For `/snipes`, `/snipes-week`, `/snipes-month`, `/snipes-alltime`, and `/snipes-rivals` |

It also subscribes to the `message.channels` and `message.groups` events, so the bot hears about new, edited, and deleted posts the moment they happen.

## 2. Get the two tokens

The bot needs two secret tokens. Treat them like passwords, and never commit them or paste them in Slack.

**App token (`xapp-…`)**
1. In your app's settings, go to **Basic Information**, scroll to **App-Level Tokens**, and click **Generate Token and Scopes**.
2. Name it anything (for example, `socket`), add the `connections:write` scope, and click **Generate**.
3. Copy the token.

**Bot token (`xoxb-…`)**
1. Go to **Install App** → **Install to Workspace** → **Allow**.
   - If Slack says the app needs approval, ask a workspace admin to approve it, then come back to this step.
2. Copy the **Bot User OAuth Token**.

## 3. Invite the bot to #ktsnipes

In Slack, run this in #ktsnipes:

```
/invite @KTsnipes 2.0
```

The bot can only see posts in channels it's a member of. If you send the report somewhere else (`REPORT_CHANNEL`), invite it there too.

## 4. Install the code

```bash
git clone https://github.com/Adi-Kaul/KTsnipes-2.0.git
cd KTsnipes-2.0

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Next, save your tokens:

```bash
cp .env.example .env
```

Open `.env` and paste in your tokens:

```
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_APP_TOKEN=xapp-your-token
```

`.env` is gitignored, so it won't be committed. Everything else in `.env.example` is optional and commented out, so the defaults apply: watch `#ktsnipes`, report Sundays at 8pm Detroit time. See [configuration.md](configuration.md) to change any of it.

## 5. Count the snipes already in the channel

If #ktsnipes already has history (hello, KTsnipes 1.0), count it first:

```bash
python -m bot.main --backfill
```

```
Counted 214 snipe posts from the channel's full history.
```

This reads every post ever made in the channel. It doesn't react to or post anything. You can skip this step: the bot does the same thing on its own the first time it starts with an empty database.

## 6. Test it

Pick whichever test you like. Options A and B don't bother anyone.

### Option A: preview the report (sends nothing)

This prints this week's report so far, exactly as it would be posted:

```bash
python -m bot.main --preview
```

Use `--preview month` or `--preview all` for the monthly or all-time version.

### Option B: dry run (sends nothing)

This runs the bot for real, but the weekly report goes to the logs instead of Slack:

```bash
DRY_RUN=1 python -m bot.main
```

Dry run also turns off the 🎯 reaction.

### Option C: the whole thing in a test channel

This is the best way to see exactly what everyone will get, without touching #ktsnipes.

1. Create `#bot-test` and `/invite @KTsnipes 2.0` to it.
2. Pick a report time **a few minutes from now** in 24-hour time, and run the bot pointed at the test channel with its own database:
   ```bash
   SNIPES_CHANNEL=bot-test DB_PATH=test.db REPORT_DAY=$(date +%A) REPORT_TIME=21:05 python -m bot.main
   ```
   (Replace `21:05` with your time. `REPORT_DAY=$(date +%A)` sets it to today.)
3. In `#bot-test`, post a photo and tag a friend (or two). Within a second you'll see the bot react 🎯.
4. Try `/snipes-week`, `/snipes-month`, `/snipes-alltime`, `/snipes @friend`, and `/snipes-rivals @you @friend`.
5. Edit the post to remove the tag. On the next `/snipes-week`, it's off the board.
6. When the report time hits, the report shows up in `#bot-test` (within a minute).

Press `Ctrl+C` to stop the bot, then `rm test.db`.

## 7. Go live

```bash
python -m bot.main
```

The bot works for as long as this command keeps running. If you close the terminal or your laptop goes to sleep, the bot stops. To keep it running all the time, see [deployment.md](deployment.md). Railway is the easiest.
