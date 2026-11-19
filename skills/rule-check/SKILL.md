---
name: rule-check
description: Check clips against platform and campaign rules before posting. Use before every post, or when the user pastes campaign rules.
---

# Rule check

Run `python "${CLAUDE_PLUGIN_ROOT}/moneyprinter.py" check <clip-folder> [more folders] --campaign moneyprinter-work/campaigns/<page>.md`.

Checks: 1080x1920, length (campaign limits or 7-60 s), audio, H.264, originality guard, credit line in post.txt, campaign-required hashtags and @mentions, banned claims (leaks, "free download", "play early", mod menus, money glitches, fake "official Rockstar"). Report each FAIL with the one-line fix. Only PASS clips go to `posting-calendar`.

Nothing is uploaded automatically. The user approves every post.
