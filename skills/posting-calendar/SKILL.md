---
name: posting-calendar
description: Export a posting calendar (CSV + .ics) with launch-week cadence. Use when the user asks when to post, wants a schedule, or has several PASS clips.
---

# Posting calendar

Run `python "${CLAUDE_PLUGIN_ROOT}/moneyprinter.py" calendar [clip folders] --start 2026-11-19T08:00`.

Cadence: launch day and day 2 every 2 hours (08:00-22:00), rest of launch week 4/day, then 2/day. Each clip goes to X first, then TikTok, Reels, Shorts 30 min apart. Every slot says NEEDS APPROVAL: nothing is uploaded automatically. Tell the user to import `calendar.ics` into their calendar app.

Nothing is uploaded automatically. The user approves every post.
