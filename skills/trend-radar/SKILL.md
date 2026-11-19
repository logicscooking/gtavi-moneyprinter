---
name: trend-radar
description: GTA 6 videos from the last 24 hours ranked by views per hour. Use when the user asks what's trending, what to clip today, or wants fresh sources.
---

# Trend radar

Run `python "${CLAUDE_PLUGIN_ROOT}/moneyprinter.py" trends --query "gta 6" --hours 24`. Try variations the user cares about ("gta 6 funny", "gta 6 secret", "gta 6 live").

Show the top 5 with views/hour and why each is clippable. Skip official Rockstar trailers re-uploaded by others, leaks and "free download" bait. Hand the best URL to `clip-run`.

Nothing is uploaded automatically. The user approves every post.
