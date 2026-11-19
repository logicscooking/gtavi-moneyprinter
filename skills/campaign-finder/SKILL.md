---
name: campaign-finder
description: Find and save paid Whop clipping campaigns. Use when the user asks 'where can I get paid for clips', mentions Whop / Content Rewards, or pastes a campaign page.
---

# Campaign finder

1. Ask the user to open Whop Content Rewards (whop.com, Discover -> Content Rewards) and paste each GTA 6 campaign page, or save it as a file. If you can browse, read the pages yourself.
2. Save each page: `python "${CLAUDE_PLUGIN_ROOT}/moneyprinter.py" campaigns save --name <slug> < page.txt` (stores it in `moneyprinter-work/campaigns/`).
3. Run `campaign-roi` to rank them.

Rules: copy the rate, budget and rules exactly as the page shows them. Never estimate a rate. A campaign with no visible rate is "n/a" and stays that way. Clip only the creators each campaign allows.

Nothing is uploaded automatically. The user approves every post.
