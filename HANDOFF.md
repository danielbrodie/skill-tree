# Session Handoff — 2026-03-23

## What Was Built

skill-tree plugin — Phases 1-3 of a 4-phase plan. Repo at `~/Projects/skill-tree/`, pushed to https://github.com/danielbrodie/skill-tree.

### Completed

- **Phase 1 (Core):** manifest.py, skillfile.py, generator.py, check.py, sync.py, init.py, list.py, plugin shell, slash commands, SessionStart hook, auto-invoked skill
- **Phase 2 (Clustering):** TF-IDF + agglomerative clustering via scikit-learn, scan.py, recursive subdivision for oversized clusters
- **Phase 3 (Add):** GitHub fetch (gh CLI + raw fallback), security checks (prompt injection, zero-width chars, path traversal), sandbox-by-default, source pinning, TF-IDF cluster matching

104 tests, all passing. Run: `cd ~/Projects/skill-tree && uv run --with pytest --with scikit-learn --with pyyaml pytest tests/ -v`

## What To Do Immediately

### 1. Phase 4 — Cross-Platform + Distribution (from the plan)

The plan is at `~/vault/10-projects/skill-graph-architecture/docs/plans/2026-03-23-feat-skill-tree-cli-plan.md`. Phase 4 checklist:

- [x] Gemini extension wrapper (`gemini-extension.json` + same scripts + commands as TOML)
- [x] Codex compatibility docs
- [x] Per-platform leaf hiding (Claude Code frontmatter, Codex `agents/openai.yaml` generation, Gemini docs)
- [x] GitHub repo README polish, example cluster templates
- [ ] Submit to Claude Code plugin marketplace
- [ ] Submit to Gemini extension registry

### 2. Fix plugin.json homepage URL

Currently points to `https://github.com/brodieG/skill-tree` — should be `https://github.com/danielbrodie/skill-tree`.

### 3. Install and test as a real plugin

```bash
cd ~/Projects/skill-tree
claude plugin install .
```

Then test `/skill-tree:check`, `/skill-tree:list`, `/skill-tree:sync` in a live session.

### 4. Migrate existing manifest

The existing manifest is at `~/.claude/skills-library/skill-graph/manifest.json`. The new plugin expects it at `~/.claude/skills-library/skill-tree/manifest.json`. Either:
- Copy/symlink the existing one
- Or run `/skill-tree:init` and then manually merge

### 5. Consider: apply scan to old path convention

The existing sync.py at `~/.claude/skills-library/skill-graph/sync.py` uses `~/.openclaw/workspace/skills` as its base path (legacy). The new skill-tree uses `~/.claude/skills/` and `~/.claude/skills-library/`. The old sync.py is now superseded — can be retired once skill-tree is validated.

## Decisions Made

1. **Plugin-first, not standalone CLI.** The brainstorm said Go binary; the deepened plan corrected to Python scripts via `uv run` with PEP 723 inline deps. No compilation, no `brew install`.

2. **Two-directory split as primary hiding.** `~/.claude/skills/` (scan path) vs `~/.claude/skills-library/` (library). This is the only approach portable across Claude Code, Codex, and Gemini.

3. **manifest.json is source of truth.** Cluster SKILL.md files are generated artifacts. `sync` regenerates them. `customInstructions` field for human-authored content in clusters.

4. **Immutable dataclasses.** `frozen=True` on Manifest, Cluster, LeafEntry, CrossReference. Tuples for list fields. Follows Daniel's coding style.

5. **`_sources` field in manifest.** Non-standard field to track where skills were fetched from (URL, commit SHA, timestamp). Enables future `skill-tree update` with diff.

6. **No `--yes` on add.** Intentional friction for untrusted content. Full content display before confirmation.

7. **Default threshold 0.7 for scan.** But 1.0 works better for Daniel's real 224-skill corpus (produced 24 coherent clusters, 81% reduction). Threshold is configurable.

## What Worked

- **TF-IDF clustering against real skills:** 224 skills → 24 clusters, 205 clustered, 19 standalones, 81% token reduction at threshold 1.0. Groupings are semantically coherent.
- **Recursive subdivision:** Clusters over 15 leaves get split automatically. Fixed a bug where subdivision produced duplicate labels.
- **check.py against real manifest:** Found real issues (1 leaf missing `disable-model-invocation`, 14 orphaned disabled skills, 1 oversized cluster).
- **Frontmatter parser without pyyaml:** Handles quoted strings, folded/literal scalars, comments. Ported from existing sync.py.

## What Didn't Work

1. **Small-sample clustering tests.** TF-IDF with 6-8 documents doesn't have enough vocabulary diversity to separate domains. Fixed by making test use 12 docs with longer, more distinctive content. The algorithm works well at scale but not with toy inputs.

2. **Original subdivision logic.** `n_target = max(2, len(members) // 10)` was too conservative for clusters of 30+. Fixed by also considering `ceil(len / MAX_CLUSTER_SIZE)`. Added recursive subdivision for cases where sub-clusters are still too large.

3. **Duplicate labels in subdivision.** `_generate_label` produced the same label for multiple sub-clusters from the same parent. `build_proposed_manifest` used label as dict key, so later clusters overwrote earlier ones. Fixed with `seen_labels` set and counter suffix.

## Architecture Notes

```
scripts/lib/
  manifest.py    — Data layer. Parse/serialize/validate manifest.json. Immutable dataclasses.
  skillfile.py   — File layer. SKILL.md frontmatter parse/write. No YAML library needed.
  generator.py   — Template layer. Cluster SKILL.md generation from manifest entries.
  cluster.py     — ML layer. TF-IDF + agglomerative clustering. Only module needing scikit-learn.
  security.py    — Security layer. Content policy checks for untrusted SKILL.md files.

scripts/
  init.py        — Bootstrap. Creates empty manifest, detects existing skills.
  check.py       — Validation. 9 checks, exit codes 0/1/2.
  sync.py        — Sync. Regenerates cluster files + sets disable flags.
  scan.py        — Clustering. Proposes new structure from flat skills.
  add.py         — Fetch. GitHub download + security + cluster matching.
  list.py        — Display. Graph summary with token estimates.
```

All scripts accept `--skills-dir` and `--library-dir` to override defaults. All mutating scripts support `--dry-run`.

## Token Budget

This session used approximately 200K tokens across research, coding, testing, and debugging.
