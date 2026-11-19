---
name: learning-loop
description: Record real results and bias future hooks toward winners. Use after the user posts, shares views or payouts, or asks 'what's working'.
---

# Learning loop

After each post: `python "${CLAUDE_PLUGIN_ROOT}/moneyprinter.py" learn <clip-folder> --hook 1 --cover 1 --platform tiktok --url <post url>`.
After 24-72 h: `python "${CLAUDE_PLUGIN_ROOT}/moneyprinter.py" learn <clip-folder> --views 18400 --earned 12.50` (earnings only from the campaign dashboard).

A hook style wins when its clip beats the user's median views. Win rates use a Beta(1,1) prior, so one lucky post doesn't take over. Run one test per day, wait 24 h before judging, prefer 72 h numbers.

Nothing is uploaded automatically. The user approves every post.
