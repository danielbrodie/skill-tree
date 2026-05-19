---
name: fetch
description: Download a SKILL.md from a GitHub URL into the user's OpenClaw skill library with security checks (prompt injection, zero-width unicode, path traversal). The fetched skill is sandboxed via `disable-model-invocation: true` so it can't auto-fire until explicitly enabled. USE WHEN the user hands you a GitHub URL pointing at a SKILL.md and wants it pulled in safely.
metadata: { "openclaw": { "emoji": "🌳", "requires": { "bins": ["uv"] } } }
---

Fetch and install a skill from GitHub. Extract the URL from the user's message, then run:

```bash
uv run {baseDir}/../scripts/add.py "<url>" --library-dir ~/.openclaw/skills
```

**Security flow:**
1. The script fetches the SKILL.md and displays its FULL content
2. It runs content policy checks and shows any warnings
3. It adds the skill as a sandboxed standalone
4. It asks for confirmation before writing anything

**Important:** New skills are sandboxed by default (`disable-model-invocation: true`). The user must explicitly enable them by editing the manifest and running `/setup`.

URL formats supported:
- `https://github.com/<org>/<repo>/tree/main/skills/<skill-name>`
- `https://github.com/<org>/<repo>/blob/main/skills/<skill-name>/SKILL.md`
- `<org>/<repo>/<skill-name>` (shorthand)

After adding, suggest running `/setup` to update cluster routing tables.
