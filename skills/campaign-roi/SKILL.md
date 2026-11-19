---
name: campaign-roi
description: Rank saved campaigns by expected dollars per hour of work. Use when the user asks which campaign to clip for, 'what pays best', or after saving campaign pages.
---

# Campaign roi

Run `python "${CLAUDE_PLUGIN_ROOT}/moneyprinter.py" campaigns rank` (add `--views 20000` if the user has no results yet; otherwise the median views from their own ledger is used; `--clips-per-hour 3` is the work-speed assumption).

Show the table as is: $/1K, budget left, max per clip, $/hour, platforms. Exhausted budgets sink to the bottom.
- Unknown values print "n/a". Never fill them in.
- $/hour = rate x views/1000 x clips/hour, capped by max payout and budget left. Say it is an estimate based on the user's own numbers, not a promise.
Recommend the top campaign and its key rule (length, required tag) in one line.

Nothing is uploaded automatically. The user approves every post.
