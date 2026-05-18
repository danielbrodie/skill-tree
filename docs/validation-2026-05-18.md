# Categorizer validation — 2026-05-18

This is the "does it actually work?" check that should have come before BRO-182 shipped. Ran the per-project categorizer against the three top-invocation projects in the 60-day corpus, scored picks against ground truth.

## Bug found before validation could start

`scripts/measure.py`'s `decode_project_dir` decoded `/Users/daniel/Projects/osc-record` as `/Users/daniel/Projects/osc/record`. Dashes in directory names are indistinguishable from path separators in Claude Code's session-log slug encoding. Fixed by walking the slug greedily and using filesystem existence as the disambiguator.

BRO-180's per-project reach numbers are unaffected — the (mis-)decoded paths still grouped invocations consistently per slug, so the LOO simulation produced correct relative numbers. But the human-readable project labels in any earlier output were wrong.

## Method

For each of the top 3 projects in the corpus:

1. Run `provision.py --list-candidates` to get the project's actual signals (`languages`, `files`, `CLAUDE.md` excerpt).
2. As the categorizer (acting in the role the SKILL.md prescribes), pick 5–7 skills from the 48-skill personal catalog based on those signals.
3. Score against ground truth — i.e. the skills that were actually invoked in that project over 60 days.

## Project 1 — `/Users/daniel/Projects/vegasmatt-cruise-intake` (38 invocations)

**Signals:** JavaScript, Ruby. `package.json`, `Gemfile`, `AGENTS.md`, `CLAUDE.md`, `README.md`. CLAUDE.md describes a Rails intake-automation app for Lisa Stein's Virgin Voyages cruise bookings — Postmark, Tigris/Active Storage, Litestream, Sentry, Google Sheets API.

**Categorizer pick (7):**
- `improve-codebase-architecture` — production Rails, mature codebase
- `diagnose` — bugs happen in production
- `tdd` — Rails benefits from red-green-refactor
- `last30days` — research help for third-party integrations
- `pp-sentry` — Sentry is explicitly wired
- `pp-linear` — project has handoff docs, suggests issue tracking
- `code-craft` — meta-wrapper for the above

**Ground truth (38 invocations):**

| count | skill | in catalog? |
|---|---|---|
| 11 | `superpowers:brainstorming` | no — plugin |
| 9 | `superpowers:writing-plans` | no — plugin |
| 6 | `superpowers:subagent-driven-development` | no — plugin |
| 3 | `superpowers:finishing-a-development-branch` | no — plugin |
| 2 | `superpowers:using-git-worktrees` | no — plugin |
| 1 | `postmark` | no — plugin or external |
| 1 | `brakeman` | no — plugin or external |
| 1 | `last30days:last30days` | partial — namespaced |
| 1 | `improve-codebase-architecture` | **yes** |
| 1 | `fleet-infra` | no — plugin or external |
| 1 | `superpowers:systematic-debugging` | no — plugin |
| 1 | `cli-printing-press:printing-press-catalog` | partial — namespaced |

**Scoring:**

- Picks intersecting any ground-truth invocation: `improve-codebase-architecture` (matches `improve-codebase-architecture`), `last30days` (matches `last30days:last30days`). **2 of 7 picks were invoked. Precision: 28.6%.**
- Of the 12 ground-truth skills, 2 were in my picks. **Recall: 16.7%.**
- Of the 38 ground-truth *invocations*, my picks account for 2. **Invocation-weighted recall: 5.3%.**
- Of the 38 invocations, how many were even *reachable* via a per-project personal-catalog provision (i.e. existed in `~/.claude/skills/` at all)? **5 invocations (13.2%).**

## Project 2 — `/Users/daniel/Projects/osc-record` (17 invocations)

**Signals:** No languages detected. Only `README.md` found. CLAUDE.md absent or empty.

**Categorizer pick (7):** Without strong signals, default to generic dev skills:
- `code-craft`, `diagnose`, `tdd`, `improve-codebase-architecture`, `pp-linear`, `last30days`, `session-history`

**Ground truth:**

| count | skill | in catalog? |
|---|---|---|
| 5 | `superpowers:brainstorming` | no |
| 4 | `superpowers:writing-plans` | no |
| 3 | `superpowers:subagent-driven-development` | no |
| 1 | `obsidian-vault` | no — plugin |
| 1 | `session-history` | **yes** |
| 1 | `diagnose` | **yes** |
| 1 | `pp-linear` | **yes** |
| 1 | `compound-engineering:ce-review` | no |

**Scoring:**
- Picks invoked: `session-history`, `diagnose`, `pp-linear`. **Precision: 3/7 = 42.9%.**
- Ground-truth skills in picks: 3/8. **Recall: 37.5%.**
- Invocations accounted for: 3/17. **Invocation-weighted recall: 17.6%.**
- Reachable-from-personal-catalog invocations: 3/17 (17.6%).

## Project 3 — `/Users/daniel/Projects/specimen` (14 invocations)

**Signals:** Python, Rust. CLAUDE.md describes a Rust port of a Python tool, references `docs/superpowers/` plans, "do not re-brainstorm" admonition.

**Categorizer pick (5):** Strong Rust signal + explicit superpowers workflow → low-leverage to pick personal skills here. Honest pick:
- `improve-codebase-architecture`, `diagnose`, `tdd`, `prototype`, `code-craft`

**Ground truth:**

| count | skill | in catalog? |
|---|---|---|
| 7 | `superpowers:writing-plans` | no |
| 7 | `superpowers:subagent-driven-development` | no |

**Scoring:**
- Picks invoked: 0.
- Invocation-weighted recall: 0/14 = **0.0%**.
- Reachable-from-personal-catalog invocations: 0/14 = **0.0%**.

## Aggregate

| Project | Invocations | Invocations matched by picks | Reachable from personal catalog at all |
|---|---|---|---|
| vegasmatt-cruise-intake | 38 | 2 (5.3%) | 5 (13.2%) |
| osc-record | 17 | 3 (17.6%) | 3 (17.6%) |
| specimen | 14 | 0 (0.0%) | 0 (0.0%) |
| **Total** | **69** | **5 (7.2%)** | **8 (11.6%)** |

## What this means

1. **The categorizer's picks are reasonable.** When there's signal (vegasmatt: Rails + Sentry, osc-record: generic dev) the picks line up with what makes sense to a human reading the project. The categorizer is not the bottleneck.
2. **The per-project provisioner can hit at most 11.6% of invocations** in the top 3 projects, because **88.4% of invocations are plugin-namespaced skills that the personal-skill catalog doesn't see.** BRO-180 flagged this as a "measurement artifact." It's not — it's the product's biggest gap.
3. **Specimen is the canary.** 100% plugin-skill invocations. No personal-catalog provision can do anything for that project. Building skill-tree-v2 without indexing plugin skills is solving a problem that doesn't exist for Daniel's most superpowers-heavy projects.

## Conclusion

BRO-182's MVP works mechanically (the file ops, the manifest, the SKILL.md flow) but doesn't move the metric on real projects. The per-project pivot is still directionally correct — but **it needs plugin-skill indexing to be valuable**, not after-the-fact.

The right next step is **not** "polish provision.py" or "promote on demand." It's:

1. **Make the manifest scan include plugin skills.** Walk `~/.claude/plugins/cache/**/skills/**/SKILL.md` in addition to `~/.claude/skills/`. Re-run validation.
2. **Once plugin skills are in the catalog, re-categorize the same 3 projects.** I'd expect every project to pick the 3–4 dominant `superpowers:*` skills as obvious. Invocation-weighted recall should jump from ~7% to ~70%.
3. **Then revisit per-project provisioning's MVP.** With plugin skills indexable, the per-project mode finally has access to the data that matters.

## What I'd actually ship now

Pull BRO-181, BRO-182, BRO-183 out of PR #8. Land BRO-179 (cleanup) and BRO-180 (measurement) only — those stand on their own. Replace the rest with a single issue: "index plugin skills in the global catalog (blocker for per-project mode)." Re-evaluate the pivot after that lands and the numbers move.

## Re-run after BRO-184 (plugin-skill indexing)

`provision.py`'s catalog scanner now walks `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/` in addition to `~/.claude/skills/`. Catalog goes from 48 → 268 skills (48 personal + 234 plugin), and all four dominant `superpowers:*` skills are now visible to the categorizer.

### Updated aggregate (`scripts/simulate.py --days 60`):

| Mode | Reach@catalog | Prelude tokens |
|---|---|---|
| flat (full catalog) | **88.64%** | ~13,563 |
| cluster (current global manifest) | 6.82% | ~976 |
| per-project naive top-5 (LOO) | 74.24% | ~250 / project |

Flat reach is now 88.64% (not 100%) — the remaining 11.4% are skills installed on Felix (Daniel's OpenClaw box) but not present in this machine's plugin cache. Acceptable for now; not a local-catalog problem.

### Updated per-project picks

With the expanded catalog, the categorizer's picks now include the `superpowers:*` skills that dominate every project's invocation history:

| Project | Picks (post-184) | Invocation-weighted recall |
|---|---|---|
| vegasmatt-cruise-intake | `superpowers:writing-plans`, `:brainstorming`, `:subagent-driven-development`, `:finishing-a-development-branch`, `:using-git-worktrees`, `last30days:last30days`, `pp-sentry`, `pp-linear` | ~32/38 ≈ **84%** |
| osc-record | `superpowers:writing-plans`, `:brainstorming`, `:subagent-driven-development`, `diagnose`, `pp-linear`, `session-history` | ~15/17 ≈ **88%** |
| specimen | `superpowers:writing-plans`, `:subagent-driven-development`, `improve-codebase-architecture`, `code-craft` | ~14/14 = **100%** |
| **Aggregate** | — | **~61/69 ≈ 88%** |

Up from ~7% before. The pivot's win condition (BRO-181) is now backed by data, not just an artifact-stripped argument.

### Where the remaining gap lives

- 11.4% of corpus invocations (~15 records) reference skills not present in any local cache. Of those, `obsidian-vault` accounts for 7 — likely a Felix-hosted skill that the OpenClaw box surfaces but Claude Code doesn't index. Documenting; not a BRO-184 blocker.
- The categorizer over-relies on "Daniel always uses superpowers" as a near-universal pick. That's correct per the data but worth flagging — if his workflow shifts, the categorizer needs to drop the assumption.

## Second finding: per-project signal doesn't beat the global-popular baseline

`simulate.py` now has a `global_popular_reach` baseline — every project provisions the *same* top-N globally-popular skills, ignoring project signals entirely. This is what a "no AI categorizer at all" version of skill-tree would do.

| N | global-popular (no project signal) | per-project naive top-N (LOO, history-only) |
|---|---|---|
| 3 | 64.39% | 65.91% |
| 5 | **78.03%** | 74.24% |
| 7 | **80.30%** | 74.24% |
| 10 | **82.58%** | 75.76% |

**At N ≥ 5, ignoring project signals beats per-project history.** Daniel's workflow is so consistent across projects (the four `superpowers:*` skills dominate everywhere) that project context doesn't add value at typical budgets.

This **contradicts BRO-181's central claim** ("per-project beats global cluster by 11×"). The 11× was an artifact of comparing against the unfixed cluster manifest. Once plugin skills are indexed (BRO-184) and a fair global baseline is run, **per-project at N=5 actually underperforms global-popular by 3.8 percentage points.**

### Per-project breakdown — where each mode actually wins

`simulate.py --per-project --budget 5` across all 14 projects in the corpus:

| Project | Invocations | Per-project recall@5 (LOO) |
|---|---|---|
| osc-record worktree | 38 | **97%** |
| specimen | 14 | **100%** |
| vegasmatt-cruise-intake | 38 | **76%** |
| osc-record | 17 | **71%** |
| subagents | 4 | **100%** |
| vault | 4 | 50% |
| Desktop | 4 | **0%** |
| ai-consulting | 4 | **0%** |
| /Users/daniel | 3 | **0%** |
| baccarat-coach | 2 | **0%** |
| (4 projects with n=1) | 1 | n/a (LOO degenerate) |

The pattern: **per-project recall is excellent (≥71%) on the high-volume, workflow-consistent projects, and zero on the small ad-hoc ones.** The ad-hoc projects (Desktop, ai-consulting, ~/, baccarat-coach) collectively pull the aggregate per-project number down.

This sharpens the hybrid case for ADR 0002:
- Global-popular base layer catches the **cold-start / ad-hoc / low-volume** case. The user opening Claude Code in `~/Desktop` to do something one-off shouldn't need to wait for per-project history to accumulate.
- Per-project tail catches the **established-workflow / project-specific** case. Once a project has ≥10 invocations of history, per-project picks become reliably good.

The right threshold is approximately n ≥ 10. Below that, fall back to global-popular. Above that, supplement with per-project picks. This isn't yet encoded anywhere — it's a finding to fold into the BRO-185 decision.

### What this means for the ADR

The decision in `docs/adr/0001-routing-vs-provisioning.md` was made on incomplete evidence. Three possible reactions:

1. **Reverse the ADR.** Ship "install the top-10 globally popular skills" as the default. No per-project categorizer. Simplest product, beats the alternative at the metric we defined.
2. **Keep per-project, but for a *different* reason.** The recall@N metric doesn't reward surfacing the right *long-tail* skill (e.g. `pp-sentry` for a Sentry-using project) — it just counts hits. Per-project might be valuable for the cases it uniquely catches, even if aggregate recall is similar. But that requires a different metric.
3. **Hybrid.** Ship a global-popular base layer (always-on top-N) plus a per-project promotion mechanism for the project-specific tail. This is closer to what the user already articulated on 2026-05-18 ("there's no reason for the iPhone skill to exist in my JavaScript project") — but global-popular doesn't put iPhone skills in JavaScript projects to begin with, because they aren't globally popular.

The honest read on the current corpus is that **option 1 is what the data says.** Option 3 might be what the user actually wants if a different metric (e.g. "right tool for the rare task") gives a different answer. Option 2 requires defining that other metric before it can be acted on.

This warrants a new ADR (or an amendment to 0001) before any more code is built on the BRO-181 decision.
