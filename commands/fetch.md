---
name: fetch
description: Fetch a skill from GitHub and wire it into the skill graph
user-invocable: true
---

Fetch and install a skill from GitHub. Run:

```bash
uv run scripts/add.py "<url>"
```

**Security flow:**
1. The script fetches the SKILL.md and displays its FULL content
2. It runs content policy checks and shows any warnings
3. It finds the best cluster match via TF-IDF similarity
4. It asks for confirmation before writing anything

**Important:** New skills are sandboxed by default (`disable-model-invocation: true`). The user must explicitly enable them by editing the manifest and running `/skill-tree:regen`.

URL formats supported:
- `https://github.com/<org>/<repo>/tree/main/skills/<skill-name>`
- `https://github.com/<org>/<repo>/blob/main/skills/<skill-name>/SKILL.md`
- `<org>/<repo>/<skill-name>` (shorthand)

After adding, suggest running `/skill-tree:regen` to update cluster routing tables.
