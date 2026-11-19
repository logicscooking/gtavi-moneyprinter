# AGENTS.md: gtavi-moneyprinter playbook for any agent

You are running gtavi-moneyprinter for the user (Grok Bot, Claude Code, Codex or any agent with a shell).
Goal: turn GTA 6 streams, videos and trends into ready-to-post vertical clips that pass campaign rules.
All commands run from the repo root: `python moneyprinter.py <command>`.

## Ground rules
- Nothing is uploaded automatically. The user approves and posts every clip by hand.
- Never invent numbers: campaign rates, budgets, views and earnings come only from pages or the user. Unknown = "n/a".
- No leaks, no "play early"/"free download", no piracy, no GTA Online glitches/mod menus, no fake news, never pose as Rockstar.
- Cheat codes only from `data/cheats.csv`, always called "reported" until tested.
- Credit the creator on every clip ("via @creator" overlay + credit line in post.txt).

## First run
1. `python moneyprinter.py doctor`. Fix every MISS (ffmpeg, yt-dlp). faster-whisper is optional.
2. Ask in ONE message: page handle, platforms, campaign pages (paste them), daily time.
3. Save each pasted campaign: `python moneyprinter.py campaigns save --name <slug> < page.txt`.
4. `python moneyprinter.py campaigns rank` and recommend the top campaign.
5. `python moneyprinter.py trends` and `python moneyprinter.py streams`; pick a source the campaign allows.
6. `python moneyprinter.py run "<url or query>" --top 3 --campaign moneyprinter-work/campaigns/<slug>.md`.
7. Show the WHY table, PASS/FAIL per clip, and the 3 hooks. Offer only PASS clips.
8. `python moneyprinter.py calendar` and tell the user to import calendar.ics.

## Daily loop
- Morning: campaigns rank -> trends/streams -> run -> check.
- After each post: `learn <clip> --hook N --cover N --platform P --url U`.
- After 24-72 h: `learn <clip> --views V [--earned E]` (earnings only from the campaign dashboard).
- Evening: `dashboard`; one test per day; judge at 24 h, trust 72 h.

## Task -> command
| Task | Command |
|---|---|
| Clip a video end to end | `run "<url/file/query>" --top 3 [--layout reaction --face tr] [--commentary "..."]` |
| Explain moment picks | `moments "<url>" --top 8` (table in jobs/<id>/moments.md) |
| Re-cut one moment | `cut "<url>" --pick 2 --hook "..." --layout fill` |
| Rule + originality check | `check <clip folder> --campaign <page>` |
| Rank campaigns | `campaigns rank [--views N] [--clips-per-hour 3]` |
| Trending videos | `trends --hours 24` |
| Live now | `streams` |
| Clip a live stream | `live <url> --minutes 30` |
| Translate a clip | translate captions.srt -> captions.<lang>.srt and hook 1 -> hook.<lang>.txt yourself, then `multilang <clip> --langs es,pt,de,ru,fr,ja` |
| Posting calendar | `calendar [clips] --start 2026-11-19T08:00` |
| Dashboard | `dashboard` |
| Questions -> posts | `questions --subs GTA6,GTA [--comments file]` |
| Secrets map | `secrets add ...`, `secrets map` |
| Cheat carousel | `cheats carousel --handle @page` |

## Fixing a FAIL
- "transformations >= 2": add captions (install faster-whisper or use a video with subtitles), `--commentary "your take"`, or `--layout reaction`.
- "credit overlay": pass `--credit <handle>`.
- Length: `--min/--max` to fit the campaign.
Never edit manifest.json to force a PASS.

## Hooks
Each clip has 3 hooks from different styles: slot 1 best learned style, slot 2 signal-suggested, slot 3 exploration.
You may sharpen them: under 8 words, honest, no spoilers. Record which one was posted with `learn`.

The full skill text lives in `skills/*/SKILL.md`; the daily plan in `skills/playbook/references/playbook.md`.
