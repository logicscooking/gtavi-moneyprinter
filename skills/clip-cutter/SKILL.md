---
name: clip-cutter
description: Cut one picked moment into a 1080x1920 clip with captions, hook, punch-ins and credit. Use after `moment-scorer`, or to re-cut with a different hook or layout.
---

# Clip cutter

Run `python "${CLAUDE_PLUGIN_ROOT}/moneyprinter.py" cut "<url|file>" --pick 2 --layout blur|fill|facecam|reaction [--hook "Nobody noticed this"] [--commentary "..."]`.

Output: word-chunk captions in the safe area, hook box, zoom punch-ins on the peak seconds, "via @creator" overlay, -14 LUFS audio, H.264. Layouts: `blur` (full frame on blurred background), `fill` (centre crop), `facecam`/`reaction` (webcam on top).

Nothing is uploaded automatically. The user approves every post.
