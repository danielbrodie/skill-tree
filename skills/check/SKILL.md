---
description: Check skill graph health — validation, cluster overview, and token savings
---

Run the status check:

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/status.py
```

Present the output. Highlight:
- Token savings (flat vs clustered)
- Any errors (suggest `/setup` to fix)
- Cluster overview
