---
name: check
description: Validate skill graph integrity against manifest and filesystem
user-invocable: true
---

Validate the skill graph. Run:

```bash
uv run scripts/check.py
```

Present the results. If errors are found, suggest running `/skill-tree:sync` to fix disable-model-invocation issues, or manual manifest edits for structural problems.
