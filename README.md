<div align="center">

<img src="docs/logo.png" width="300" alt="gtavi-moneyprinter logo: pixel bot in sunglasses holding cash in front of a neon VI sunset">

<h1 align="center">gtavi-moneyprinter</h1>

<h2 align="center">Rockstar built the game.<br>Grok Bot prints you the money.</h2>

<p align="center">GTA 6 is the biggest launch the internet has ever clipped. Send this repo to Grok Bot or Claude Code and it ranks the paid campaigns by dollars per hour, finds the moments chat lost it over, cuts 9:16 clips with 3 hooks and 3 covers each, blocks anything a campaign would reject, and learns which hooks actually win. One command, a folder per clip, you hit post.</p>

<p align="center"><img src="https://img.shields.io/badge/Grok_Bot_+_Claude_Code-ready-ff3e8a" alt="Grok Bot + Claude Code: ready"> <img src="https://img.shields.io/badge/skills-21-8b3dff" alt="skills: 21"> <img src="https://img.shields.io/badge/clips-1080x1920-ff8a3d" alt="clips: 1080x1920"> <img src="https://img.shields.io/badge/languages-6-ff3e8a" alt="languages: 6"> <img src="https://img.shields.io/badge/GTA_6-Nov_19-8b3dff" alt="GTA 6: Nov 19"> <img src="https://img.shields.io/badge/license-MIT-ff8a3d" alt="license: MIT"></p>

<p align="center"><img src="docs/skills-badge.svg" width="380" alt="21 skills in one install"></p>

<p align="center"><a href="#first-run-paste-this-into-grok-bot-or-claude-code">Quick start</a> · <a href="#ways-to-make-money">Make money</a> · <a href="#whats-inside">Skills</a> · <a href="#why-this-beats-other-clipping-repos">Why it's better</a> · <a href="#clip-rules">Clip rules</a> · <a href="#scripts">Scripts</a></p>

<p align="center"><sub>Unofficial fan project. Not affiliated with Rockstar Games, Take-Two, xAI or Anthropic.</sub></p>

</div>

## Install

**Claude Code**
```
/plugin marketplace add logicscooking/gtavi-moneyprinter
/plugin install gtavi-moneyprinter@gtavi-moneyprinter
```

**Grok Bot, Codex or any agent**: send it the repo link `https://github.com/logicscooking/gtavi-moneyprinter`. It reads [`AGENTS.md`](AGENTS.md), the same playbook as plain instructions.

**By hand**
```
git clone https://github.com/logicscooking/gtavi-moneyprinter && cd gtavi-moneyprinter
pip install -r requirements.txt
python moneyprinter.py doctor
```

## First run: paste this into Grok Bot or Claude Code

```
Use gtavi-moneyprinter. Run doctor and fix what's missing. Ask me your 4 setup questions
in one message. Then, after one "yes": rank the campaign pages I paste by $/hour, show
today's trending GTA 6 videos and who's live, run the top source end to end, show me the
WHY table, and give me 3 clips that pass the rule check with hooks, covers and a posting
calendar. Upload nothing; I post by hand.
```

## Ways to make money

**1. Paid clipping campaigns.** Streamers and brands on Whop Content Rewards pay per 1,000 approved views. `campaign-roi` reads the pages you paste and ranks them by expected $ per hour using your own view history. It never invents a rate: if the page doesn't show it, it's `n/a`.

**2. Your own GTA 6 page.** Credited clips, verified secrets, sourced cheat carousels and HOW TO posts from real questions grow a page that earns through campaigns and partnerships.

**3. Foreign-language pages.** One clip, six more languages (ES, PT, DE, RU, FR, JA). Non-English GTA feeds are nearly empty.

No income is promised. Platforms don't pay for reposts. Results depend on speed, picks and hooks, and the dashboard shows only what you actually earned.

## Clip rules

- Hook in the first second, under 8 words, a reason to keep watching.
- 7 to 35 seconds. Open just before the action, end on the payoff.
- Big captions in the safe area; most people watch muted.
- At least 2 transformations and a `via @creator` overlay. `check` fails plain re-uploads.
- Launch day: NZ/AU players unlock first. X first, then TikTok, Reels, Shorts, every 2 hours for 48 hours.
- One test per day. Judge at 24 h, trust 72 h.

## What's inside

| Skill | What you get |
|---|---|
| `setup` | `doctor` checks ffmpeg, yt-dlp, faster-whisper; 4 questions; your profile |
| `clip-run` | **One command**: URL or search query to ready clip folders |
| `campaign-finder` | Save the Whop campaign pages you paste, exactly as shown |
| `campaign-roi` | Campaigns ranked by expected $/hour; unknown = `n/a` |
| `trend-radar` | Last-24 h GTA 6 videos ranked by views per hour |
| `stream-finder` | Who's live on Twitch and YouTube, by viewers, no account |
| `moment-scorer` | 5 fused signals with a per-pick WHY table |
| `live-mode` | Records a live stream, reads chat, clips the explosions |
| `twitch-reaction` | Face on top, game below, hook on the seam |
| `clip-cutter` | 1080x1920, captions, hook box, zoom punch-ins, credit, -14 LUFS |
| `hook-lab` | 3 hooks + 3 covers per clip, biased by what won before |
| `originality-guard` | Fails clips with fewer than 2 transformations or no credit |
| `rule-check` | Format, length, campaign tags and banned claims |
| `multilang` | Re-renders a clip in ES, PT, DE, RU, FR, JA |
| `posting-calendar` | CSV + .ics with launch-week cadence, every slot needs approval |
| `dashboard` | One static HTML page: clips, posts, views, $, best hooks |
| `learning-loop` | Real results in, hook-style win rates out |
| `questions-to-posts` | Repeated Reddit/comment questions into HOW TO posts |
| `secrets-map` | Hidden spots database with timestamps, credit, status |
| `cheat-codes` | Reported codes with a source column, 4-slide carousel |
| `playbook` | Daily routine and launch-week plan |

Every clip folder:
```
clip.mp4       1080x1920, captions, hook, punch-ins, via @creator
cover.jpg      best frame + hook (cover_1..3.jpg for A/B)
captions.srt   word-chunk captions
post.txt       3 hooks, caption, credit line, hashtags per platform
manifest.json  score breakdown, transformations, check results
```

## Why this beats other clipping repos

| | Typical clipping repo | gtavi-moneyprinter |
|---|---|---|
| End to end | Separate scripts, you glue them | `run "<url or query>"`, one folder per clip |
| Moment picking | Loudness or transcript only | Loudness + hype words + most replayed + chat rate + scene cuts, fused |
| Explains picks | No | Score breakdown table per moment |
| Hooks | One title | 3 hooks + 3 covers, learning loop picks the winner style |
| Re-upload risk | Not checked | Originality guard: 2+ transformations + credit overlay required |
| Campaign choice | Lists rates | Ranks by expected $/hour from your own numbers, never invents rates |
| Scheduling | None | CSV + .ics calendar, launch-week cadence |
| Results | Spreadsheet | Static dashboard from real numbers |
| Agents | One | Claude Code plugin + `AGENTS.md` for Grok Bot, Codex, any agent |
| Tests | None | Offline pytest + GitHub Actions on Linux, macOS, Windows |

## Hard rules

No leaks, no "play early" or "free download" posts, no piracy, no GTA Online money glitches, mod menus or AFK bots, no fake news, never pretends to be Rockstar. Cheat codes are `reported` with a source until tested. Every fact needs a source. Nothing is uploaded automatically; you approve every post. Not affiliated with Rockstar Games, Take-Two Interactive, xAI or Anthropic.

## Scripts

```
python moneyprinter.py doctor
python moneyprinter.py run "https://www.youtube.com/watch?v=..." --top 3
python moneyprinter.py run "gta 6 police chase" --layout reaction --face tr --campaign campaigns/streamer.md
python moneyprinter.py moments "<url>" --top 8
python moneyprinter.py campaigns save --name streamer < page.txt
python moneyprinter.py campaigns rank --views 20000
python moneyprinter.py trends --hours 24
python moneyprinter.py streams
python moneyprinter.py live "https://www.twitch.tv/<channel>" --minutes 30
python moneyprinter.py check moneyprinter-work/clips/<clip>
python moneyprinter.py learn moneyprinter-work/clips/<clip> --hook 2 --views 18400 --earned 12.5
python moneyprinter.py calendar --start 2026-11-19T08:00
python moneyprinter.py dashboard
python moneyprinter.py multilang moneyprinter-work/clips/<clip> --langs es,pt,de,ru,fr,ja
python moneyprinter.py questions --subs GTA6,GTA
python moneyprinter.py secrets add --name "Hidden yacht" --area "Vice Beach" --credit @finder
python moneyprinter.py cheats carousel --handle @yourpage
```

Python 3.10+, Windows, macOS or Linux. Needs ffmpeg and yt-dlp; faster-whisper is optional (without it, captions come from YouTube subtitles). Work files go to `./moneyprinter-work` (set `MONEYPRINTER_HOME` to change). Tests: `python -m pytest -q`.

MIT license © logicscooking.
