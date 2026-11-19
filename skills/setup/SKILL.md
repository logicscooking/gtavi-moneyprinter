---
name: setup
description: First-time setup for gtavi-moneyprinter. Use when the user installs the plugin, says 'set me up', or a command fails because ffmpeg/yt-dlp/whisper is missing.
---

# Setup

Run `python "${CLAUDE_PLUGIN_ROOT}/moneyprinter.py" doctor`. Fix every MISS line before anything else:
- ffmpeg: macOS `brew install ffmpeg`, Windows `winget install Gyan.FFmpeg`, Linux `sudo apt install ffmpeg`.
- yt-dlp: `pip install -U yt-dlp`.
- faster-whisper (optional, better captions): `pip install faster-whisper`. Without it, captions come from YouTube's own subtitles.

Then ask these 4 questions in ONE message: page handle, platforms (X/TikTok/Reels/Shorts), clipping campaigns joined (paste the pages), daily time budget.
Save the answers to `moneyprinter-work/profile.md`. Next: `clip-run`.

Nothing is uploaded automatically. The user approves every post.
