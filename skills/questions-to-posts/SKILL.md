---
name: questions-to-posts
description: Turn repeated GTA 6 questions into HOW TO posts. Use when the user needs post ideas, or pastes their comments.
---

# Questions to posts

Run `python "${CLAUDE_PLUGIN_ROOT}/moneyprinter.py" questions --subs GTA6,GTA [--comments my_comments.txt]`.

Take the top repeated questions. Answer only from official sources or footage you can cite; if unknown, skip it. Each answer becomes a post: hook = the question, 3-step answer, source credit. Never answer with leaked info.

Nothing is uploaded automatically. The user approves every post.
