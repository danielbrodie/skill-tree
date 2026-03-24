---
description: Set up or rebuild the skill graph — scan skills, cluster them, generate routing files
---

This command sets up the skill-tree manifest. You are the clustering algorithm.

**Step 1: Scan** — collect all skill names and descriptions:

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/scan.py --format json
```

Read the JSON output. This is every skill on disk with its name and description.

**Step 2: Cluster the skills.** Read all the descriptions and group them into 15-30 clusters based on semantic similarity — skills that would co-occur in a real user request belong together.

For each cluster, produce:
- **name**: a clear routing signal (2-3 words). Test: could a model read just this name and know whether to enter this cluster? Bad: `asc-app-app_id`. Good: `app-store-connect`.
- **description**: a USE WHEN decision rule. "USE WHEN: the user asks about X, Y, or Z." Not a member list.
- **leaves**: each with a `routingHint` that distinguishes it from siblings. "Use this when X, not Y."

Skills that don't fit any cluster stay as standalones. That's fine — not everything clusters.

**Step 3: Write the manifest.** Write the result as JSON to `~/.claude/skills-library/skill-tree/manifest.json` using this schema:

```json
{
  "version": "1.0",
  "unclusteredBudget": 25,
  "clusters": {
    "cluster-name": {
      "description": "USE WHEN: ...",
      "crossReferences": [],
      "leaves": {
        "skill-name": { "routingHint": "Use this when ..." }
      }
    }
  },
  "standalones": ["skill-a", "skill-b"],
  "hotPath": [],
  "referenceNodes": [],
  "deprecated": []
}
```

If a manifest already exists, read it first and preserve `hotPath`, `referenceNodes`, `deprecated`, and any `customInstructions` on existing clusters. Only change the clustering.

Present the proposed clusters to the user before writing. Show cluster names, member counts, and descriptions. Ask for confirmation.

**Step 4: Sync** — generate cluster routing files:

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/sync.py --dry-run
```

Show preview. If confirmed:

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/sync.py
```

**Step 5: Verify:**

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/status.py
```

Present the final status with token savings.
