---
description: Set up or rebuild the skill graph — bootstrap, cluster, and generate routing files
---

This command handles the full setup pipeline. Run each step and present results between them.

**Step 1: Bootstrap** — detect existing skills and create/update the manifest:

```bash
uv run scripts/init.py
```

**Step 2: Cluster** — propose a cluster structure from your skills:

```bash
uv run scripts/scan.py
```

Present the proposed clusters. If the user approves, continue. The `--threshold` flag (0-1) controls tightness.

**Step 3: Sync** — regenerate cluster routing files and set disable flags:

First preview:

```bash
uv run scripts/sync.py --dry-run
```

If the user confirms, apply:

```bash
uv run scripts/sync.py
```

**Step 4: Verify** — confirm everything is clean:

```bash
uv run scripts/status.py
```

Present the final status with token savings.
