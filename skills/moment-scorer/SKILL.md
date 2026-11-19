---
name: moment-scorer
description: Score a video's best moments and explain WHY. Use when the user wants candidates before cutting, or asks why a moment was picked.
---

# Moment scorer

Run `python "${CLAUDE_PLUGIN_ROOT}/moneyprinter.py" moments "<url|file>" --top 8` (`--chat chat.json` for a TwitchDownloader log).

Signals, fused per second (median/MAD normalised, missing ones skipped and their weight redistributed):
| signal | source |
|---|---|
| loudness | audio RMS spikes |
| hype | hype words in the transcript (faster-whisper, else YouTube captions) |
| replayed | YouTube "most replayed" heatmap via yt-dlp |
| chat | chat messages per second (YouTube replay, Twitch logs, live recorder) |
| scenes | scene-change density (ffmpeg scdet) |

Show the breakdown table from `jobs/<id>/moments.md`. Drop story spoilers in launch week and anything leak-like. Next: `clip-cutter --pick N`.

Nothing is uploaded automatically. The user approves every post.
