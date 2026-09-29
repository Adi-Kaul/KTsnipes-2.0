# KTsnipes 2.0 🎯

A Slack bot that keeps the tally for **#ktsnipes**.

Post a photo in #ktsnipes and **@tag** who's in it. That's a snipe. The bot reacts with 🎯 so you know it counted, keeps a running tally, every **Sunday at 8pm** posts the week's snipe report, and on the **last day of each month** posts the month's.

**Snipe vs. sniped** are two separate tallies:

| | Who | Gets |
|---|---|---|
| **Sniper** | Whoever posted the photo | +1 **snipe** per person tagged |
| **Sniped** | Everyone tagged | +1 **sniped** each |

The Sunday report looks like this:

> 🎯 **KTsnipes Weekly Report** · Sep 27 – Oct 4
> **23 snipes** this week · 9 snipers · 14 victims
>
> 🔫 **Top Snipers**
> 🥇 @alex — 7  🥈 @sam — 5  🥉 @jordan — 3
>
> 💀 **Most Sniped**
> 🥇 @taylor — 6  🥈 @riley — 4  🥈 @casey — 4
>
> 🔥 **Best day:** @alex got 4 snipes on Wednesday
> 📈 **Most efficient:** @jordan — 3.00 K/D (3 snipes, sniped 1 time)
> 🤩 **Most reacted:** [this shot] by @sam on @taylor (18 reactions)
> ⚔️ **Rivalry of the week:** @alex **3–1** @taylor
> 📅 **Busiest day:** Friday (8 snipes)

It also adds five slash commands. Only you see the replies.
- `/snipes-week` shows this week's leaderboard and highlights so far.
- `/snipes-month` shows the same for this month.
- `/snipes-alltime` shows the same for all time.
- `/snipes-rivals` shows the biggest rivalries. Tag one person to see their rivals, or two for a head-to-head.
- `/snipes @person` shows someone's record and K/D, favorite target, and nemesis.

## Quick start

```bash
git clone https://github.com/Adi-Kaul/KTsnipes-2.0.git && cd KTsnipes-2.0
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env              # add your Slack tokens
python -m bot.main --backfill     # count every snipe already in #ktsnipes
python -m bot.main --preview      # see this week's report without posting it
python -m bot.main                # run it
```

You'll need to create the Slack app first. It takes a few minutes with the included manifest. See the **[setup guide](docs/setup.md)**.

## Documentation

| Guide | For |
|---|---|
| **[Setup](docs/setup.md)** | Creating the Slack app, getting tokens, counting past snipes, testing in a private channel |
| **[Using the bot](docs/usage.md)** | What counts as a snipe, the Sunday report, the slash commands, and an FAQ for members |
| **[Configuration](docs/configuration.md)** | Every setting: channel, report day and time, timezone, the 🎯 reaction, and more |
| **[Deployment](docs/deployment.md)** | Running it 24/7 on Railway, Fly.io, a Mac, a Raspberry Pi, or Docker |
| **[Troubleshooting](docs/troubleshooting.md)** | Error messages, snipes that didn't count, and what to do about them |
| **[How it works](docs/how-it-works.md)** | Architecture, code layout, tests, changing what counts, and ideas for extending it |

## Features

- **Counts on its own.** No commands to log a snipe. Post the photo, tag the person, done.
- **Confirms every snipe.** The 🎯 reaction tells you it counted. No 🎯 means something's off (usually a missing tag).
- **Keeps up with edits.** Add a tag later and it counts. Delete the post and it comes off the board.
- **Weekly and monthly reports, plus an all-time board.** Top snipers, most sniped, best single day, most efficient (K/D), most reacted-to snipe, rivalry of the week, and busiest day.
- **Rivalries.** Every pair who's traded snipes gets a head-to-head score (`@alex 7–5 @sam`), with first blood and the latest hit.
- **Counts the old stuff.** On first start it reads the channel's entire history, so KTsnipes 1.0-era snipes are on the all-time board.
- **Survives restarts.** The tally is stored in SQLite. If the bot was offline, it catches up on anything it missed, and posts a late report if it's back within 12 hours.
- **No web server.** It runs in Socket Mode, so it works on Railway, a laptop, or a Raspberry Pi. A `Dockerfile` and `railway.toml` are included.

## Development

```bash
pip install pytest && pytest
```

The tests run without Slack, using a fake Slack client and a fake clock. See [how it works](docs/how-it-works.md).
