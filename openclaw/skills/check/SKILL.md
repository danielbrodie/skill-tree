---
name: check
description: Quick health check on skill-tree's manifest — finds dead references, leaf-not-in-cluster orphans, broken routing tables. Reports validation errors and (if cluster routing is set up) the token savings vs flat-catalog mode. USE WHEN the user says "check my skills", "is anything broken", or sees skill-related errors in a session.
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
