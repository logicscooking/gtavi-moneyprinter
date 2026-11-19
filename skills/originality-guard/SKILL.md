---
name: originality-guard
description: Block plain re-uploads before they get rejected. Use when a clip FAILs originality, or the user asks 'will this get approved'.
---

# Originality guard

Campaigns and platforms reject re-uploads. `check` requires:
- at least 2 transformations from: hook_overlay, captions, zoom_punch_ins, facecam_layout / reaction_layout, commentary_slot;
- a visible credit overlay starting with "via @".
No `manifest.json` = treated as a re-upload.

To fix a FAIL: add captions (install faster-whisper or use a video with subtitles), add `--commentary "your take"`, or use `--layout reaction`. Re-run and confirm PASS. Never bypass the guard by editing manifest.json.

Nothing is uploaded automatically. The user approves every post.
