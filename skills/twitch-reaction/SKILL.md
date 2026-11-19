---
name: twitch-reaction
description: Reaction clip layout: streamer's face on top, gameplay below, hook on the seam. Use for streamer clips with a webcam overlay, 'reaction style', or 'face on top'.
---

# Twitch reaction

Run `python "${CLAUDE_PLUGIN_ROOT}/moneyprinter.py" run "<vod url>" --layout reaction --face tr`.

`--face` picks the webcam box: `tl`, `tr`, `bl`, `br` presets, or exact fractions `x,y,w,h` (e.g. `0.74,0.02,0.24,0.3`). Open `cover_1.jpg`: if the face is cut off, adjust `--face` and re-run (signals are cached, so it is fast). The hook sits on the seam between face and game. The reaction layout counts as a transformation for `originality-guard`.

Nothing is uploaded automatically. The user approves every post.
