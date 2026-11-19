---
name: clip-run
description: One command from a URL or search query to ready-to-post clip folders. Use when the user says 'clip this', gives a GTA 6 video/VOD link, or a query like 'gta 6 police chase'.
---

# Clip run

Run `python "${CLAUDE_PLUGIN_ROOT}/moneyprinter.py" run "<url | file | query>" --top 3` (add `--layout reaction --face tr` for streamers with a webcam, `--campaign <page.md>` to check campaign rules, `--commentary "my take"` to add the commentary slot).

It does find -> score -> cut -> check -> package. Each clip folder holds: `clip.mp4` (1080x1920), `cover.jpg` + `cover_1..3.jpg`, `captions.srt`, `post.txt` (3 hooks, caption, credit line, hashtags per platform), `manifest.json`.

Then:
1. Show the WHY table it printed (score breakdown per signal) in one short block.
2. Show each clip's PASS/FAIL. Never offer a FAIL clip for posting; fix it (see `originality-guard`).
3. Recommend hook 1 vs 2 vs 3 per clip in one line each. The user posts by hand.

Nothing is uploaded automatically. The user approves every post.
