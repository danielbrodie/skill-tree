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
