# ADR 0002 — Hybrid: global-popular base + per-project tail

- **Status:** Accepted (supersedes [ADR 0001](./0001-routing-vs-provisioning.md))
- **Date:** 2026-05-18 — ratified 2026-05-18
- **Tracking issue:** [BRO-185](https://linear.app/brodiegraphics/issue/BRO-185) (Done)
- **Supersedes:** ADR 0001 (per-project provisioning as primary mode)

## Context

ADR 0001 chose per-project provisioning as the primary mode based on a baseline comparison that turned out to be unfair: the cluster baseline was crippled by missing plugin-skill indexing (fixed in [BRO-184](https://linear.app/brodiegraphics/issue/BRO-184)) and there was no global-popular counterfactual.

After fixing both, the new measurement (`scripts/simulate.py --days 60`, post-BRO-184):

| N | Reach: global-popular (no project signal) | Reach: per-project naive (LOO) |
|---|---|---|
| 3 | 64.39% | 65.91% |
| 5 | **78.03%** | 74.24% |
| 7 | **80.30%** | 74.24% |
| 10 | **82.58%** | 75.76% |

At every budget ≥ 5, **a "just install the top-N most-globally-popular skills" baseline beats per-project history-based picking.** ADR 0001's central claim no longer holds against a fair comparison.

## Why global wins on this corpus

Daniel's invocation history is dominated by ~4 `superpowers:*` skills that appear in basically every project. Those four account for ~70% of all invocations. A global-popular top-5 captures them plus one more popular skill, accounting for ~78% of all invocations across all projects. Per-project history adds little because **the projects don't differ much in *what skills they invoke* — only in *what they're about*.**

That said: the metric — reach@N against a 132-record corpus — has known weaknesses:
- It treats all hits equally. Surfacing `pp-sentry` for a Sentry-using project (where it would otherwise never be reached) is weighted the same as surfacing `superpowers:writing-plans` (which the user invokes everywhere anyway).
- The corpus is small. 95% bootstrap CIs would put the global-vs-per-project gap inside the noise.
- It captures *what was invoked*, not *what the user would have liked to invoke if it had been visible*. There may be project-specific skills the user wanted but couldn't reach.

## Decision

**Ship a hybrid: a small global-popular base layer + the existing per-project mechanism for the tail.**

Concretely:
1. **Global base.** `~/.claude/skills/` should hold a curated set of the top-N most-invoked skills. skill-tree provides a `/skill-tree:provision --global-suggest` mode that *suggests* the top-N from corpus history; the user manually approves and either symlinks or removes skills accordingly. (Auto-pruning is too destructive for a default.)
2. **Per-project tail.** `/skill-tree:provision` (the BRO-182 implementation) keeps its current behavior — copies additional, project-specific skills into `<project>/.claude/skills/`. The categorizer's job is to spot the *project-specific* skills the global base doesn't carry (e.g. `pp-sentry` for a Sentry repo, `postmark` for vegasmatt's intake app). For projects where the global base already covers the workflow, per-project provisioning is a no-op.
3. **Plugin skills are loaded by Claude Code's plugin system, not by skill-tree.** skill-tree doesn't try to curate them — users install/uninstall plugins as their interests change. skill-tree's catalog *reads* them so the per-project categorizer can refer to them, but doesn't manage their visibility.

## Why this isn't a contradiction of ADR 0001

ADR 0001 said per-project is the *default* mode and global is the *fallback*. ADR 0002 inverts: **global-popular is the always-on default, per-project is an *additive* layer for projects with distinctive needs.** The per-project work from BRO-182 is preserved; its role narrows to "project-specific additions" rather than "the only thing that runs."

## Consequences

### Good
- The data supports it. The global-popular result is the strongest finding in the validation work — ignoring it would be exactly the unmeasured-pivot pattern that started this conversation.
- Implementation is mostly already done: `provision.py` exists, the global suggester is a small addition.
- The per-project tail addresses the user's actual articulated pain ("no reason for the iPhone skill to exist in my JavaScript project") without claiming an aggregate win that the data doesn't support.
- Plugin-skill management is correctly out of scope. skill-tree doesn't fight Claude Code's plugin loader; it just curates personal skills and project tails.

### Bad
- Two layers is more conceptual surface than one. Users have to understand both. README needs to make this clear.
- The decision on what counts as a "project-specific tail" skill becomes the categorizer's main job — and that's the part the validation didn't directly measure. Future work needs a metric that captures *rare-skill correctness*.
- "Manually approve symlinks/removals" sounds clunky. May want to revisit the UX.

### Neutral
- BRO-181's ADR stays in the repo, marked as superseded by this one. Useful as a record of "what we believed before the validation."

## What this means for existing PR #8

- BRO-179 (cleanup), BRO-180 (measurement), BRO-184 (plugin scan): keep, ship.
- BRO-181 (ADR 0001): keep in repo as historical record, but mark superseded.
- BRO-182 (per-project provisioner): keep, but reframe its purpose in README as the project-specific tail layer, not the default.
- BRO-183 (Codex port): keep — the manifest is right regardless of which layer wins.
- New work: `provision.py --global-suggest` (small), README rewrite (medium), revised metric definition for measuring project-specific correctness (research).

## Decision-makers

- Daniel Brodie (author)
- Proposed 2026-05-18, status: Proposed pending the BRO-185 review.

## Decision-review trigger

- If the corpus grows past ~500 records and includes more project-diverse work, re-run the comparison. Per-project might become competitive again if Daniel's workflow diversifies.
- If a project-specific-correctness metric (separate from reach@N) shows per-project beating global by ≥10 percentage points, revisit.
- If a future Claude Code version changes how plugin skills are surfaced (e.g. always-on visibility), the global base layer may become moot.
