---
name: scan
description: Analyze installed skills and propose a cluster structure
user-invocable: true
---

Scan all installed skills and propose a two-tier cluster structure. Run:

```bash
uv run scripts/scan.py
```

Present the summary to the user. Key things to highlight:
- Number of proposed clusters and their members
- Estimated token reduction
- Any skills that ended up as standalones (couldn't be clustered)

The preview is written to `~/.claude/skills-library/skill-tree/preview/`. The user can:
1. Review and edit `preview/manifest.json` before applying
2. Apply directly if the structure looks good

To apply, read the preview manifest and use it to update the real manifest, then run `/skill-tree:regen`.

The `--threshold` flag controls clustering tightness (0-1). Lower values produce tighter, smaller clusters. Default is 0.7.
