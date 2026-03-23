---
name: setup
description: Set up or rebuild the skill graph — bootstrap, cluster, and generate routing files
metadata: { "openclaw": { "emoji": "🌳", "requires": { "bins": ["uv"] } } }
---

This command handles the full setup pipeline. Run each step and present results between them.

**Step 1: Bootstrap** — detect existing skills and create/update the manifest:

```bash
uv run {baseDir}/../scripts/init.py --skills-dir ~/.openclaw/skills --library-dir ~/.openclaw/skills
```

**Step 2: Cluster** — get a rough grouping proposal:

```bash
uv run {baseDir}/../scripts/scan.py --skills-dir ~/.openclaw/skills --library-dir ~/.openclaw/skills --full
```

This produces a preview manifest. Read it:

```bash
cat ~/.openclaw/skills/skill-tree/preview/manifest.json
```

**Step 3: Review and improve the clusters.** This is the critical step. The scan uses TF-IDF which groups by word overlap, not meaning. You are smarter than it. Review every cluster and fix problems:

- **Rename unclear labels.** `mcporter-comfyui` is useless — name it `media-tools` or `creative-pipeline`. Every cluster name must be a routing signal, not a member name. Test: could a model read just this name and know whether to enter this cluster?
- **Rewrite descriptions.** Each description must be a routing instruction: "USE WHEN: the user asks about X, Y, or Z." Not a member list. Not a description repeat. A decision rule.
- **Fix routing hints per leaf.** Each leaf's `routingHint` should say "use this when X, not Y" — distinguish it from siblings in the same cluster. If two leaves have the same hint, the model can't route between them.
- **Move misplaced skills.** If a skill landed in the wrong cluster, move it. No cluster should span domains that wouldn't co-occur in a real user request.
- **Merge small clusters.** Clusters under 3 skills should be merged with neighbors or made standalones.
- **Split incoherent clusters.** If a cluster mixes unrelated skills, break it up.
- **Decide standalones.** Some skills genuinely don't belong in any cluster — that's fine.

Use the Edit tool to fix the preview manifest directly. When you're satisfied, copy it to the real manifest path:

```bash
cp ~/.openclaw/skills/skill-tree/preview/manifest.json ~/.openclaw/skills/skill-tree/manifest.json
```

**Step 4: Sync** — generate cluster routing files from the improved manifest:

First preview:

```bash
uv run {baseDir}/../scripts/sync.py --dry-run --skills-dir ~/.openclaw/skills --library-dir ~/.openclaw/skills
```

If the user confirms, apply:

```bash
uv run {baseDir}/../scripts/sync.py --skills-dir ~/.openclaw/skills --library-dir ~/.openclaw/skills
```

**Step 5: Verify** — confirm everything is clean:

```bash
uv run {baseDir}/../scripts/status.py --skills-dir ~/.openclaw/skills --library-dir ~/.openclaw/skills
```

Present the final status with token savings.
