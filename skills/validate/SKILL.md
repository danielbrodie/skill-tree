---
description: Validate skill graph integrity against manifest and filesystem
---

Validate the skill graph. Run:

```bash
uv run scripts/check.py
```

Present the results. If errors are found, suggest running `/regen` to fix disable-model-invocation issues, or manual manifest edits for structural problems.
