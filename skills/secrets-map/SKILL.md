---
name: secrets-map
description: Database of hidden spots, cars, money and collectibles found in clips. Use when a clip shows a secret, or the user wants evergreen tip posts.
---

# Secrets map

Add: `python "${CLAUDE_PLUGIN_ROOT}/moneyprinter.py" secrets add --name "Hidden yacht" --category vehicle --area "Vice Beach" --how "Dive under the pier at night" --clip <url> --ts 4:12 --credit @finder`
Map: `python "${CLAUDE_PLUGIN_ROOT}/moneyprinter.py" secrets map` writes `moneyprinter-work/secrets_map.md` grouped by area.

Status starts `unverified`. Only `verified` entries (seen in two independent clips, or tested) become tip posts. Always credit the finder.

Nothing is uploaded automatically. The user approves every post.
