---
description: One-time setup or rebuild of the optional cluster-routing manifest — groups your installed skills into 15-30 semantic clusters with visible router skills + hidden leaves so the prelude carries one router-description per cluster instead of one description per skill. Mostly useful past ~150 installed skills, when the per-description prelude budget overflows. USE WHEN the user explicitly wants cluster routing set up or rebuilt; skip otherwise — the default management surface is `/skill-tree:provision`.
---

This command sets up the skill-tree manifest. You are the clustering algorithm.

**Step 1: Scan** — collect all skill names and descriptions:

```bash
${CLAUDE_PLUGIN_ROOT}/bin/skill-tree scan --format json
```

Read the JSON output. This is every skill on disk with its name and description.

**Step 2: Cluster the skills.** Read all the descriptions and group them into 15-30 clusters based on semantic similarity — skills that would co-occur in a real user request belong together.

For each cluster, produce:
- **name**: a clear routing signal (2-3 words). Test: could a model read just this name and know whether to enter this cluster? Bad: `asc-app-app_id`. Good: `app-store-connect`.
- **description**: a USE WHEN decision rule. "USE WHEN: the user asks about X, Y, or Z." Not a member list.
- **leaves**: each with a `routingHint` that distinguishes it from siblings. "Use this when X, not Y."

Skills that don't fit any cluster stay as standalones. That's fine — not everything clusters.

**Step 3: Present the proposed clustering before writing.** Output a table to the user with cluster names, member counts, and descriptions. Ask for confirmation. Only after confirmation, write the manifest directly to `~/.claude/skills-library/skill-tree/manifest.json` using this schema:

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

If a manifest already exists, read it first and preserve `hotPath`, `referenceNodes`, `deprecated`, and any `customInstructions` on existing clusters. Only change the clustering. Concretely: load the existing manifest, build a name→old-cluster map, and for each leaf in your new proposal, if its old cluster had a `customInstructions` field or a routing hint you'd weaken, preserve the old version.

`skill-tree sync --dry-run` in Step 4 is the real preview gate — it shows exactly what routing files would change before any disk writes happen.

**Step 4: Sync** — generate cluster routing files:

```bash
${CLAUDE_PLUGIN_ROOT}/bin/skill-tree sync --dry-run
```

Show preview. If confirmed:

```bash
${CLAUDE_PLUGIN_ROOT}/bin/skill-tree sync
```

**Step 5: Verify:**

```bash
${CLAUDE_PLUGIN_ROOT}/bin/skill-tree status
```

Present the final status with token savings.
