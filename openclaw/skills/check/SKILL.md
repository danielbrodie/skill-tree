---
name: check
description: Check skill graph health — validation, cluster overview, and token savings
metadata: { "openclaw": { "emoji": "🌳", "requires": { "bins": ["uv"] } } }
---

Run the status check:

```bash
uv run {baseDir}/../scripts/status.py --skills-dir ~/.openclaw/skills --library-dir ~/.openclaw/skills
```

Present the output. Highlight:
- Token savings (flat vs clustered)
- Any errors (suggest `/setup` to fix)
- Cluster overview
