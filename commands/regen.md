---
description: Regenerate cluster routing files from manifest
---

Regenerate all cluster SKILL.md files from the manifest. First preview with dry-run:

```bash
uv run scripts/sync.py --dry-run
```

Show the preview to the user. If they confirm, apply:

```bash
uv run scripts/sync.py
```

Report what changed.
