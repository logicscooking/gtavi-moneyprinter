---
name: stream-finder
description: Who is streaming GTA 6 right now on Twitch and YouTube, ranked by viewers. Use for 'who's live', launch day, or before `live-mode`.
---

# Stream finder

Run `python "${CLAUDE_PLUGIN_ROOT}/moneyprinter.py" streams`. Twitch uses the public web endpoint, no account needed; YouTube uses yt-dlp's live search.

Show the top 8. Prefer streamers named in the user's campaigns. On launch day (Nov 19) prioritize New Zealand/Australia streamers: they unlock first. Next: `live-mode` or `twitch-reaction`.

Nothing is uploaded automatically. The user approves every post.
