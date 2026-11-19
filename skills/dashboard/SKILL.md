---
name: dashboard
description: Build the local results dashboard. Use when the user asks how they're doing, for stats, or for the best hooks.
---

# Dashboard

Run `python "${CLAUDE_PLUGIN_ROOT}/moneyprinter.py" dashboard`, then open `moneyprinter-work/dashboard.html`.

It shows clips made, posted, reported views, reported earnings, best hooks by views, and hook-style win rates. Only real numbers the user reported via `learning-loop`; missing values show "n/a". Never add estimates to it.

Nothing is uploaded automatically. The user approves every post.
