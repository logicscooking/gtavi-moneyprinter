---
name: multilang
description: One clip in 6 more languages: ES, PT, DE, RU, FR, JA. Use when the user wants foreign-language pages or 'translate this clip'.
---

# Multilang

Non-English GTA pages are nearly empty, so translated clips get reach cheaply.
1. Read `captions.srt` in the clip folder. Translate each line yourself into the target language; keep the numbering and timestamps unchanged, keep lines short and punchy. Save as `captions.<lang>.srt` (es, pt, de, ru, fr, ja).
2. Translate hook 1 into `hook.<lang>.txt`.
3. Run `python "${CLAUDE_PLUGIN_ROOT}/moneyprinter.py" multilang <clip-folder> --langs es,pt,de,ru,fr,ja` to render `clip.<lang>.mp4` with the same layout, punch-ins and credit.
4. Write a translated caption and local hashtags for each language. Never translate the creator handle.

Nothing is uploaded automatically. The user approves every post.
