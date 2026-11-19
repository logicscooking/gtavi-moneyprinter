---
name: live-mode
description: Record a live stream and clip every chat explosion. Use when a big GTA 6 stream is live right now and the user wants clips while it happens.
---

# Live mode

Run `python "${CLAUDE_PLUGIN_ROOT}/moneyprinter.py" live <twitch-or-youtube-url> --minutes 30 --layout reaction --face tr`.

It records the stream with ffmpeg, reads Twitch chat anonymously over IRC in parallel, then runs the full pipeline with chat rate as a signal. Repeat in 15-30 minute blocks for long streams. Post the first clean clip to X fast; speed wins on live days. Only clip streamers whose campaign or license allows it.

Nothing is uploaded automatically. The user approves every post.
