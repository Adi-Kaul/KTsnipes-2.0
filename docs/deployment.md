# Deployment

The bot is a single long-running Python process. It connects out to Slack over a WebSocket (Socket Mode), so it doesn't need an open port, a domain, or a web server. Anything that can keep one command running 24/7 can host it.

> **Run only one copy at a time.** If two copies of the bot run at once, the weekly report gets posted twice. Stop your local copy before deploying, and don't scale past one instance.

## Which option?

| Option | Cost | Effort | Good for |
|---|---|---|---|
| [Railway](#railway) | ~$5/mo | Easiest | Set up once and forget about it |
| [Fly.io](#flyio) | ~$0–2/mo | Command line | Cheap, if you're comfortable in a terminal |
| [Always-on Mac](#always-on-mac-launchd) | Free | Medium | A computer that never sleeps |
| [Raspberry Pi / Linux box](#linux--raspberry-pi-systemd) | Free | Medium | A spare Pi or server |
| [Docker](#docker-any-host) | Varies | Medium | Anywhere else |

## Keeping the tally across redeploys

The tally lives in a small SQLite file (`DB_PATH`). Most hosts erase local files on every redeploy, so **attach a persistent volume mounted at `/data`**. The Docker image already sets `DB_PATH=/data/snipes.db`.

If you skip the volume, the bot still works: when it starts with an empty database, it recounts every snipe from the channel's history. But that takes longer each time, and it forgets which reports it already posted, so a redeploy on Sunday night could post the report twice.

---

## Railway

1. Sign in at <https://railway.com> with GitHub.
2. Click **New Project** → **Deploy from GitHub repo**, then pick `KTsnipes-2.0`. Railway finds [`railway.toml`](../railway.toml) and builds the `Dockerfile`.
3. Open the service's **Variables** tab and add `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN`. Add any [other settings](configuration.md) you want to change.
4. Right-click the service (or use the command palette, `⌘K`) → **Attach Volume**, and set the mount path to **`/data`**.
5. Railway redeploys. Open **Deployments** → **View logs** and look for:
   ```
   Watching #ktsnipes; weekly report goes to the same channel
   No snipes on record yet; backfilling from the channel's full history
   Backfill done: 214 snipe posts
   ⚡️ Bolt app is running!
   Sweep done: 18 snipes in the last 8 days
   ```
   The backfill lines only appear on the very first start.

To change a setting, edit it in **Variables**, and Railway restarts the bot automatically. When you push new code to GitHub, Railway redeploys on its own.

`railway.toml` pins the service to **one replica** and restarts it if it ever crashes.

## Fly.io

Install the CLI (`brew install flyctl`), then run `fly auth login`. From the repo folder:

```bash
fly launch --no-deploy
```

When `fly launch` asks about databases or other extras, say **no** to all of them. Then open the generated `fly.toml` and **delete the whole `[http_service]` section**, because the bot doesn't serve web traffic. Add a volume for the tally:

```bash
fly volumes create data --size 1
```

```toml
[mounts]
  source = "data"
  destination = "/data"
```

Set your secrets and deploy with a single machine:

```bash
fly secrets set SLACK_BOT_TOKEN=xoxb-... SLACK_APP_TOKEN=xapp-...
fly deploy --ha=false
fly logs
```

Other settings go in `fly.toml` under `[env]`, for example `REPORT_TIME = "21:00"`.

## Always-on Mac (launchd)

This runs the bot in the background, starts it when you log in, and restarts it if it crashes. First finish [setup.md](setup.md) so that `python -m bot.main` works in the repo folder.

Create `~/Library/LaunchAgents/com.ktp.ktsnipes.plist`, replacing `/Users/YOU/KTsnipes-2.0` with your actual path:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.ktp.ktsnipes</string>
  <key>WorkingDirectory</key><string>/Users/YOU/KTsnipes-2.0</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/YOU/KTsnipes-2.0/.venv/bin/python</string>
    <string>-m</string>
    <string>bot.main</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/Users/YOU/KTsnipes-2.0/bot.log</string>
  <key>StandardErrorPath</key><string>/Users/YOU/KTsnipes-2.0/bot.log</string>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.ktp.ktsnipes.plist     # start
tail -f ~/KTsnipes-2.0/bot.log                                    # watch logs
launchctl unload ~/Library/LaunchAgents/com.ktp.ktsnipes.plist   # stop
```

To restart after editing `.env`, run `unload` and then `load`.

The bot stops while your Mac is asleep. It catches up on missed snipes when it wakes, but a report due while it slept is only posted if it wakes within 12 hours. To keep it running, turn on **System Settings → Battery → Options → Prevent automatic sleeping when the display is off** (on a laptop, this only works while it's plugged in).

## Linux / Raspberry Pi (systemd)

After finishing [setup.md](setup.md) on the machine, create `/etc/systemd/system/ktsnipes.service`:

```ini
[Unit]
Description=KTsnipes 2.0 (Slack snipe tracker)
After=network-online.target
Wants=network-online.target

[Service]
User=pi
WorkingDirectory=/home/pi/KTsnipes-2.0
ExecStart=/home/pi/KTsnipes-2.0/.venv/bin/python -m bot.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ktsnipes   # start now and on every boot
journalctl -u ktsnipes -f              # watch logs
sudo systemctl restart ktsnipes        # after editing .env
```

## Docker (any host)

```bash
docker build -t ktsnipes .
docker run -d --restart unless-stopped --name ktsnipes \
  --env-file .env \
  -v ktsnipes-data:/data \
  ktsnipes
```

The image stores the tally at `/data/snipes.db`, so the `-v` volume keeps it across container rebuilds. Don't set `DB_PATH` in `.env` when using Docker, or the tally will live outside the volume.
