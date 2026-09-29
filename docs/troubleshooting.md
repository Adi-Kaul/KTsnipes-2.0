# Troubleshooting

Start with the bot's logs. Locally, they're in the terminal where the bot is running. On a host, check its log viewer (see [deployment.md](deployment.md)). Most problems show up there with a clear error.

## Startup errors

**`SLACK_BOT_TOKEN is not set`**
The bot didn't find a `.env` file in the folder you ran it from, or the variable isn't set on your host. Run the bot from the repo folder, or set the variable.

**`SLACK_APP_TOKEN is not set`**
You need the `xapp-…` token to run the bot continuously. See step 2 of [setup.md](setup.md#2-get-the-two-tokens).

**`Slack rejected the startup checks: invalid_auth`**
The bot token is wrong or was revoked. Copy the token again from **Install App** in your app's settings. Make sure you used the `xoxb-` token there, not the `xapp-` one.

**`Slack rejected the startup checks: missing_scope`**
The app is missing a permission. Usually the manifest was changed after the app was installed. Go to **Install App** → **Reinstall to Workspace**.

**`Channel #something not found`**
- Check the spelling of `SNIPES_CHANNEL` / `REPORT_CHANNEL`. Leave out the `#`, or keep it; both work.
- For **private** channels, the bot has to be invited before it can see them. Run `/invite @KTsnipes 2.0` in the channel.
- If you still can't find the problem, use the channel ID instead. In Slack, open the channel details and the ID (`C…`) is at the bottom.

**`REPORT_DAY must be a day of the week`** / **`REPORT_TIME must look like 20:00`**
Use a full day name (`sunday`) and 24-hour time (`20:00`, not `8pm`). See [configuration.md](configuration.md).

**`ZoneInfoNotFoundError`**
`TIMEZONE` isn't a real timezone name. Use something like `America/Detroit`, not `EST` or `Eastern`.

## Runtime problems

**`Slack API error: not_in_channel`**
The bot isn't a member of #ktsnipes. Run `/invite @KTsnipes 2.0` there.

**Someone posted a snipe and the bot didn't react 🎯**
Check each of these in order:
1. Is the bot running? Look for `Bolt app is running!` in the logs.
2. Is there a **real** @tag? The name has to turn blue. Typing `@alex` without picking Alex from the popup is just text.
3. Is the attachment an **image**? Videos, GIF links, and other files don't count.
4. Was it posted **in a thread**? Thread replies only count with "Also send to channel" checked.
5. Did they tag **themselves** or a **bot**? Those don't count.
6. Is `DRY_RUN` on, or `CONFIRM_EMOJI` empty? Then the snipe is counted but the bot doesn't react. Check `/snipes-week`.

If none of those apply, look in the logs for a `Snipe …: U… sniped U…` line. If it's there, the snipe counted and only the reaction failed; the log line after it says why.

**The bot reacted, but the snipe isn't on `/snipes-week`**
The post was edited to remove the tag or photo, or deleted, since then. The 🎯 stays but the snipe doesn't count.

**The weekly report didn't post**
1. Is it past `REPORT_TIME` on `REPORT_DAY` in `TIMEZONE`? The default is Sunday 8pm **Detroit** time. Check the host's logs for `Posted the weekly report`.
2. Was the bot offline at report time? If it came back more than 12 hours late, it skips that week. The log says `Missed the report due …`.
3. Is `DRY_RUN` on? The report goes to the logs instead.
4. Is the bot a member of `REPORT_CHANNEL`, if you set one?

**The weekly report posted twice**
Two copies of the bot are running (for example, your laptop and Railway), or the database was wiped between the two posts because there's no volume. Stop the extra copy, and attach a volume at `/data` (see [deployment.md](deployment.md#keeping-the-tally-across-redeploys)).

**`/snipes` or `/snipes-week` says "dispatch_failed" or "didn't respond"**
The bot isn't running, or it's connected with an `xapp-` token from a different app. Start the bot and check that `SLACK_APP_TOKEN` belongs to this app.

**`/snipes-week` (or `-month`, `-alltime`, `-rivals`) isn't in Slack's autocomplete**
The app was installed from an older manifest. Paste the current [`manifest.yaml`](../manifest.yaml) into **App Manifest** in your app's settings, save, and **Reinstall to Workspace**.

**All-time numbers reset after a redeploy**
The host wiped the database. Attach a volume at `/data`. The bot will recount the channel's history on its next start, so nothing is lost for good.

**"Most reacted" looks off**
Reaction counts are refreshed every `SWEEP_MINUTES` (10 by default) and again right before the report posts. The bot's own 🎯 is never counted.

## Still stuck?

Print what the bot sees without posting anything:

```bash
python -m bot.main --preview          # this week
python -m bot.main --preview month    # this month
python -m bot.main --preview all      # all time
```

The first one is this week's report exactly as it would go out. If the numbers look wrong, compare them against the channel, and see [usage.md](usage.md#what-counts) for what counts.
