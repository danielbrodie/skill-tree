# Measuring skill-tree

> The reason this doc exists: "I haven't actually done the work of figuring out how to objectively measure if outcomes are better." — 2026-05-18

Every architectural decision in skill-tree has been made without a ground-truth signal. This is the answer to "how would we know?"

## Primary metric: skill-recall@k on a real-task corpus

For each (user prompt, invoked-skill) pair in the user's session history, ask: under routing mode X, would that skill have been visible to the model within the first k slots of the prompt assembly?

- **recall@1** — the right skill was *the* obvious one (highest-priority slot in cluster routing, or in the project provision)
- **recall@3** — the right skill was in the top 3 candidates
- **recall@∞** — the right skill was reachable at all (flat: always 1.0; cluster: 1.0 if not silently dropped; per-project: <1.0 because some skills aren't provisioned)

The point of comparing modes is the **recall vs cost tradeoff**: per-project provisioning sacrifices some recall@∞ to win recall@1, plus saves tokens.

**Ground truth source:** `~/.claude/projects/**/*.jsonl`. Filter to invocations where `tool="Skill"` and join with the user prompt that preceded each invocation. That gives a labelled corpus of "this prompt → this skill is the right answer."

**Why this is the right primary metric:**
- It is directly falsifiable. No subjective judgement.
- It measures the actual user-felt problem ("when I need a skill, can the model find it?")
- It distinguishes the three architectures without ambiguity: flat (high recall@∞, low recall@1, high token cost), global cluster (medium recall@1, lower token cost, occasional silent drops at scale), per-project (high recall@1, lowest token cost, low recall@∞ on cross-project work).

## Secondary metric: prompt-prelude token cost

Sum of skill descriptions (and cluster router descriptions in cluster mode) that the model sees on every turn, before user input. Easy to compute statically from the manifest + skill scan. Reported alongside the primary so we can see if the recall win is worth the token cost, or vice versa.

## Not chosen — and why

- **Time-to-first-tool-call.** Confounded by every other harness change. Hard to attribute.
- **Wrong-skill invocations.** "Wrong" requires a judgement call. We can instead infer it from the inverse of recall@1 — if the right skill wasn't easily reachable but a similar-named one was, the model is more likely to mis-pick.
- **Feel test.** Useful as a sanity check after the numbers move, not as a decision-driver.

## Methodology — how to compute

1. **Corpus build.** Walk `~/.claude/projects/**/*.jsonl`, last 60 days. For each `Skill` tool invocation, emit a record: `(session_id, timestamp, project_path, preceding_user_prompt, invoked_skill)`. Drop sessions where the prompt context is missing.
2. **Routing simulation.** For each record, simulate three modes:
   - **flat:** all skills visible. Recall@1 is 1.0 iff `invoked_skill` is named in the model's first guess at top-of-prompt; recall@k similar.
   - **cluster (current):** the model first sees ~20 cluster routers. To "reach" `invoked_skill`, it must (a) pick the right cluster — match against the cluster description, and (b) read the leaf routing table.
   - **per-project (proposed v2):** for each `project_path`, an AI categorizer (run offline, not at session start) decides which ~5 skills get provisioned to that project's `.claude/skills/`. Did `invoked_skill` make the cut?
3. **Score.** Compute recall@1, recall@3, recall@∞ for each mode across the corpus. Compute prompt-prelude token cost from the same data.
4. **Report.** Single markdown table per mode.

## Baseline — 132 records, 27 unique skills, 14 projects, 60-day window

Run via `uv run scripts/simulate.py --days 60`.

| Mode | Reach@catalog | Prelude tokens | Note |
|---|---|---|---|
| flat (no skill-tree) | 100.00% | ~2,721 | always-on baseline |
| cluster (current global) | 6.82% | ~976 | manifest doesn't track plugin-namespaced skills |
| per-project naive top-5 (LOO) | 74.24% | ~280 / project | dumbest possible categorizer; floor for v2 |

**Reach@catalog** = was the invoked skill listed in the mode's catalog at all? Necessary condition for the model to pick it. Coarser than recall@k against ranked candidates, but model-free and cheap to compute.

**Leave-one-out** for the per-project mode: for each (project, invoked-skill) record, take that project's *other* records, compute top-5 most-invoked, ask if the held-out skill is in it. Avoids the trivial "everything that ever happened is reachable" tautology.

### What this means

1. **Cluster mode's 6.82% reachability is a measurement artifact, not a real result.** Plugin-namespaced skills (`superpowers:writing-plans`, `last30days:last30days`, etc.) drive ~80% of invocations but aren't in `manifest.json`. Either the manifest must expand to track plugin skills, or skill-tree's value applies only to personal skills (a much narrower claim than the README makes).
2. **Per-project naive top-5 already beats cluster by ~11x at <30% the per-project token cost.** That's with the dumbest possible "categorizer" (a Counter). A real AI categorizer using project signals (CLAUDE.md, package manifest, repo metadata) should beat that ceiling — but even the floor wins.
3. **The 25.76% miss rate on per-project mode is the cross-project tail.** First-time invocations in a project always miss under LOO. Real product needs a fallback path for novel project/skill pairs — e.g. "promote a globally-popular skill into a new project on first invocation."

### Caveats for interpretation

- **Sample size:** 132 records is small. Bootstrap CIs would widen the per-project number by ±5%. Don't make decisions on a 2% reach delta — but a 67-percentage-point gap (cluster 6.82% vs per-project 74.24%) is well outside noise.
- **Plugin skill coverage:** cluster mode is unfairly penalised because plugin skills aren't manifest-tracked. The decision should either (a) include plugin skills in the manifest scan, or (b) measure cluster mode against personal-skill invocations only. Both are short follow-ups.
- **Reach@catalog vs recall@1:** reach is necessary not sufficient. A skill being *in* the prelude doesn't mean the model picks it correctly. The recall@k upgrade requires running the model on the corpus — defer until we have signal that reach numbers don't already settle ## Sample-size considerations

The 60-day corpus has ~138 `Skill` tool invocations (per 2026-05-18 audit). Heavily Pareto-skewed: 4 superpowers skills account for ~70%. That means:
- The corpus is small enough that recall scores have wide CIs. Report bootstrap 95% intervals, not just point estimates.
- Some skills appear zero times in the corpus. They contribute to prelude-token-cost but not to recall numerator. That's correct — if you never invoke a skill, having it in the catalog is pure overhead.

## Open questions

- Should "wrong-skill mis-pick" be measured? Would need a manual label of "the model picked X but should have picked Y." Defer until the recall numbers tell us if it's worth the labeling effort.
- Cross-platform: do we measure separately for Claude Code, Codex, OpenClaw? Probably yes once lands — the prelude assembly differs.

## Next step

Implement `scripts/measure.py` that walks the JSONL corpus, runs the three simulations, and writes the baseline table back into this doc. Tracked separately.
