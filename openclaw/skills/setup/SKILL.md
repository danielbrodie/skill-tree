---
name: setup
description: Set up or rebuild the skill graph — bootstrap, cluster, and generate routing files
metadata: { "openclaw": { "emoji": "🌳", "requires": { "bins": ["uv"] } } }
---

This command handles the full setup pipeline. Run each step and present results between them.

**Step 1: Bootstrap** — detect existing skills and create/update the manifest:

```bash
uv run {baseDir}/../../scripts/init.py --skills-dir ~/.openclaw/skills --library-dir ~/.openclaw/skills
```

**Step 2: Cluster** — propose a cluster structure from your skills:

```bash
uv run {baseDir}/../../scripts/scan.py --skills-dir ~/.openclaw/skills --library-dir ~/.openclaw/skills
```

Present the proposed clusters. If the user approves, continue. The `--threshold` flag (0-1) controls tightness.

**Step 3: Sync** — regenerate cluster routing files and set disable flags:

First preview:

```bash
uv run {baseDir}/../../scripts/sync.py --dry-run --skills-dir ~/.openclaw/skills --library-dir ~/.openclaw/skills
```

If the user confirms, apply:

```bash
uv run {baseDir}/../../scripts/sync.py --skills-dir ~/.openclaw/skills --library-dir ~/.openclaw/skills
```

**Step 4: Verify** — confirm everything is clean:

```bash
uv run {baseDir}/../../scripts/status.py --skills-dir ~/.openclaw/skills --library-dir ~/.openclaw/skills
```

Present the final status with token savings.
