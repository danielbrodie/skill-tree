# Measuring skill-tree

How to tell whether skill-tree's per-project narrowing actually helps versus a flat catalog or a global-cluster manifest.

## Metric

**Reach@catalog.** For each historical `Skill` tool invocation in the user's session corpus, ask: was the invoked skill *in* the prelude under each routing mode? Necessary condition for the model to pick it. Cheap to compute (no model in the loop), good enough to distinguish the three architectures.

A finer metric — **recall@k** against ranked candidates — would catch the case where the right skill was in the prelude but the model didn't pick it. Not used here because computing it needs the model in the loop.

**Secondary: prompt-prelude token cost.** Sum of skill descriptions (and cluster-router descriptions in cluster mode) the model sees on every turn before user input. Static computation from the manifest + skill scan. Reported alongside Reach so you can see what the recall is costing.

## Methodology

1. Walk `~/.claude/projects/**/*.jsonl` for the last 60 days. For each `Skill` tool invocation, emit `(session_id, timestamp, project_path, preceding_user_prompt, invoked_skill)`.
2. For each record, simulate three modes:
   - **flat** — every skill is always visible.
   - **cluster** — the model first sees ~20 cluster routers, must pick the right one, then reads the leaf table.
   - **per-project (leave-one-out)** — for each project, take the *other* records to compute the top-5 most-invoked. Did the held-out skill make it?
3. Score Reach@catalog and prelude tokens for each mode.

Run via `uv run scripts/simulate.py --days 60`.

## Baseline — 132 records, 27 unique skills, 14 projects

| Mode | Reach@catalog | Prelude tokens | Note |
|---|---|---|---|
| flat (no skill-tree) | 100.00% | ~2,721 | always-on baseline |
| cluster (legacy global manifest) | 6.82% | ~976 | manifest doesn't track plugin-namespaced skills |
| per-project naive top-5 (LOO) | 74.24% | ~280 / project | dumbest possible categorizer; floor for the per-project mode |

What this means:

1. Cluster mode's 6.82% reachability is a measurement artifact. Plugin-namespaced skills (`superpowers:writing-plans`, `last30days:last30days`, etc.) drive ~80% of invocations but weren't in `manifest.json` in the legacy setup. The fix is to expand the manifest to track plugin skills, which the current `provision --list-candidates` does.
2. Per-project naive top-5 already beats cluster by ~11× at <30% the per-project token cost. That's with a Counter as the categorizer. A real AI categorizer using project signals (CLAUDE.md, package manifest, languages) should beat that floor.
3. The 25.76% miss rate on per-project is the cross-project tail. First-time invocations in a project always miss under LOO. The product needs a fallback for novel project/skill pairs — promoting a globally-popular skill into a new project on first invocation is the obvious move.

## Caveats

- **Sample size.** 132 records is small; bootstrap 95% CIs would widen the per-project number by ±5%. A 67-point gap (cluster 6.82% vs per-project 74.24%) is well outside noise, but a 2% delta in either direction wouldn't be.
- **Reach is necessary, not sufficient.** A skill being in the prelude doesn't mean the model picks it. Upgrading to recall@k requires running the model on the corpus; not done yet.
- **Cross-platform.** Numbers above are from a Claude Code corpus. Codex and Gemini CLI assemble the prelude differently; measure separately if the question matters.
