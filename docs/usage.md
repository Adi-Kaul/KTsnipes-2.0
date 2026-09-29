# Using KTsnipes 2.0

This page is for everyone in #ktsnipes: what counts, how the tally works, and the commands.

## The short version

1. See a brother out in the wild. Take the photo.
2. Post it in **#ktsnipes** and **@tag** them.
3. The bot reacts with 🎯. That means it counted.
4. Every **Sunday at 8pm**, the bot posts the weekly snipe report, and on the **last day of each month** at 8pm, the monthly one.

## Snipe vs. sniped

These are two different tallies. Don't mix them up.

| | Who | What they get |
|---|---|---|
| **Sniper** | Whoever **posted the photo** | +1 **snipe** for each person they tagged |
| **Sniped** | Everyone **tagged** in the post | +1 **sniped** each |

So if Alex posts a photo tagging Sam and Jordan:
- Alex: **+2 snipes**
- Sam: **+1 sniped**
- Jordan: **+1 sniped**

Snipes are good. Getting sniped is not.

## What counts

A post counts as a snipe when **all** of these are true:
- It's posted in #ktsnipes, directly in the channel.
- It has at least one **image** attached.
- It **@tags** at least one person.

These don't count:
- **No photo.** Text-only posts, links, and non-image files (PDFs, etc.) are ignored. Videos don't count either.
- **No tag.** A photo with a caption like "look who it is" but no @tag doesn't count, because the bot can't tell who's in it. Edit the post to add the tag and it'll count.
- **Thread replies.** A photo posted inside a thread doesn't count, unless you check **"Also send to #ktsnipes"**.
- **Tagging yourself.** Nice try.
- **Tagging a bot.**
- **Tagging someone twice in one post.** They're counted once.

### The 🎯 reaction

When the bot counts a snipe, it reacts to the post with 🎯. If you don't see it within a few seconds, the post didn't count. Check the list above. The 🎯 doesn't count toward the post's reaction total in the report.

### Edits and deletions

The tally always matches what's in the channel right now:
- **Forgot the tag?** Edit the post to add it. It counts as soon as you save.
- **Tagged the wrong person?** Edit it. The old person comes off, the new person goes on.
- **Removed the tag or photo?** It stops counting.
- **Deleted the post?** It comes off the tally.

The bot hears about edits and deletions instantly. It also re-reads the last 8 days of the channel every 10 minutes as a safety net, so nothing slips through even if the bot was briefly offline.

## The Sunday report

Every Sunday at 8pm (Detroit time), the bot posts the week's report in #ktsnipes. The week runs from **last Sunday 8pm to this Sunday 8pm**.

> 🎯 **KTsnipes Weekly Report** · Sep 27 – Oct 4
> **23 snipes** this week · 9 snipers · 14 victims
>
> 🔫 **Top Snipers**
> 🥇 @alex — 7
> 🥈 @sam — 5
> 🥉 @jordan — 3
>
> 💀 **Most Sniped**
> 🥇 @taylor — 6
> 🥈 @riley — 4
> 🥈 @casey — 4
>
> 🔥 **Best day:** @alex got 4 snipes on Wednesday
> 🤩 **Most reacted:** [this shot] by @sam on @taylor (18 reactions)
> ⚔️ **Rivalry of the week:** @alex **3–1** @taylor
> 📅 **Busiest day:** Friday (8 snipes)

What each part means:

| Section | What it is |
|---|---|
| **Top Snipers** | Most snipes made this week. Top 3 places. |
| **Most Sniped** | Most times tagged this week. Top 3 places. |
| **Best day** | The most snipes one person made in a single day (midnight to midnight). Only shown if it's at least 2. |
| **Most reacted** | The snipe post with the most total reactions (not counting the bot's 🎯). Links to the post. |
| **Rivalry of the week** | The two people who sniped each other the most, counting both directions, with the score. Only shown if it's at least 2 total. See [Rivalries](#rivalries). |
| **Busiest day** | The day of the week with the most snipes overall. Only shown if it's at least 2. |

**Ties** share a place. If two people tie for second, they both get 🥈 and the next person is fourth. The boards show at most 5 people.

The report starts with an **@channel**, so everyone in #ktsnipes gets a ping, and it **@mentions** everyone on it.

If nobody sniped anyone all week, the report says so. Loudly.

## The monthly report

On the last day of each month at 8pm, the bot also posts a monthly report, in the same format as `/snipes-month`: the top 5 snipers and most sniped, plus the month's highlights. It covers everything since last month's report (8pm on the last day of the previous month), so a snipe posted at 11pm on the 31st shows up in next month's report.

## Commands

Anyone can use these in any channel. **Only you** see the reply, and it doesn't ping anyone.

| Command | Shows |
|---|---|
| `/snipes-week` | This week's leaderboard and highlights so far |
| `/snipes-month` | This month's leaderboard and highlights |
| `/snipes-alltime` | The all-time leaderboard and highlights |
| `/snipes @person` | Someone's record for the week, month, and all time |
| `/snipes-rivals` | The biggest rivalries. Tag one person for their rivals, or two for a head-to-head. |

### `/snipes-week`, `/snipes-month`, `/snipes-alltime`

Each one is a full report for its period, in the same format as the Sunday report: top snipers, most sniped, best day, most reacted, rivalry, and busiest day.

| Command | Covers | Boards show |
|---|---|---|
| `/snipes-week` | Since the last report (last Sunday 8pm) until now. This is exactly what Sunday's report will say if nothing changes. | Top 3 places |
| `/snipes-month` | Since the 1st of this month (midnight) until now | Top 5 places |
| `/snipes-alltime` | Every snipe the bot has on record, including the channel's history from before the bot | Top 5 places |

> 🎯 **KTsnipes Monthly Report** · October 2026
> **61 snipes** this month · 17 snipers · 24 victims
>
> 🔫 **Top Snipers**
> 🥇 @alex — 14
> 🥈 @sam — 11
> 🥉 @jordan — 8
> 4. @casey — 6
> 5. @riley — 5
>
> 💀 **Most Sniped**
> …
>
> 🔥 **Best day:** @alex got 5 snipes on Wed Oct 14
> 🤩 **Most reacted:** [this shot] by @sam on @taylor (31 reactions)
> ⚔️ **Rivalry of the month:** @alex **6–4** @taylor
> 📅 **Busiest day:** Fri Oct 9 (11 snipes)

In the all-time report, the header says when the first snipe on record was ("since Mar 3, 2025"), and the rivalry is called **Biggest rivalry**.

### `/snipes @person`

Someone's full record.

```
@alex's snipe record
This week: 5 snipes · sniped 1 time
This month: 14 snipes · sniped 3 times
All time: 41 snipes · sniped 12 times
🎯 Favorite target: @taylor (9)
😈 Nemesis: @sam (5)
⚔️ Top rival: @sam (7–5)
```

- **Favorite target:** who they've sniped the most, all time.
- **Nemesis:** who has sniped *them* the most, all time.
- **Top rival:** their biggest [rivalry](#rivalries), with the score from their side (their snipes first).

Works on yourself too: just tag yourself. `/snipes` with no one tagged shows a list of the commands.

## Rivalries

Any two people who've sniped each other become rivals. A rivalry counts **both directions**, so it has a score, like a game: if Alex has sniped Sam 7 times and Sam has sniped Alex 5 times, it's **@alex 7–5 @sam**.

- The person ahead is listed first.
- Rivalries are ranked by total snipes between the two (12 in that example). On a tie, the closer score ranks higher.
- A pair needs **at least 2** snipes between them to show up on the rivalry boards.
- If only one side has ever landed a shot, it's marked _(one-sided)_.

### `/snipes-rivals`

The top 5 rivalries of all time, and the 3 hottest this month.

```
⚔️ Top Rivalries (all time)
1. @alex 7–5 @sam · 12 snipes
2. @jordan 6–4 @taylor · 10 snipes
3. @casey 5–0 @riley · 5 snipes (one-sided)

🔥 Hottest this month
1. @jordan 3–2 @taylor · 5 snipes
```

### `/snipes-rivals @person`

Everyone that person has traded snipes with, biggest first, from their side. Up to 8 people are listed.

```
⚔️ @sam's rivals (all time)
• @alex — down 5–7
• @jordan — up 3–1
• @casey — tied 2–2
```

### `/snipes-rivals @person @person`

A head-to-head between two people. The first person you tag is listed first.

```
⚔️ @alex vs @sam
All time: @alex 7–5 @sam · @alex leads by 2
This month: @alex 2–2 @sam
This week: @alex 1–0 @sam
🩸 First blood: @sam got @alex on Mar 3, 2025
⏱️ Latest: @alex got @sam on Oct 5, 2026
```

The dates link to the posts. This works for any two people, even if they've only traded one snipe.

## FAQ

**I posted a snipe and the bot didn't react.**
It didn't count. The usual reasons: you didn't @tag anyone (typing a name without picking them from the popup doesn't make a real tag), the photo was posted in a thread, or it was a video. Fix it by editing the post to add a real @tag.

**Does a group photo count as multiple snipes?**
Yes. Tag everyone in it and you get one snipe per person.

**Can I snipe someone in a different channel?**
No, only #ktsnipes counts.

**Someone deleted my snipe. Do I lose it?**
Yes. The tally only counts posts that are still in the channel.

**Does a snipe from last week count toward this week if I edit it?**
No. A snipe always belongs to the week it was originally *posted*, even if you edit it later.

**What if I post at 7:59pm Sunday?**
It counts toward the week that's ending, and it'll be in that night's report. At 8:00pm it counts toward next week.

**What if the bot was down on Sunday night (or the last night of the month)?**
If it comes back within 12 hours, it posts the report late. After that, it skips that report. All the snipes are still counted and show up in `/snipes`.

**Do old snipes from before the bot count?**
Yes. The first time the bot starts, it reads the channel's entire history and counts every snipe ever posted. They show up in the all-time board.
