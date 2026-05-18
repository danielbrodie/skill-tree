# ADR 0001 — Global clusters vs per-project provisioning

- **Status:** Accepted
- **Date:** 2026-05-18
- **Tracking issue:** [BRO-181](https://linear.app/brodiegraphics/issue/BRO-181)
- **Supersedes:** the implicit "global clustering is the right shape" assumption from skill-tree v0.5.

## Context

skill-tree v0–v0.5 routed via a global manifest at `~/.claude/skills-library/skill-tree/manifest.json`. Clusters describe ~20 themed groups; leaves are hidden behind `disable-model-invocation: true`. The model sees cluster descriptions in its prelude, picks one, then reads a routing table to find a leaf.

The premise was: at ~160+ skills, descriptions overflow the system-prompt budget and get silently dropped, so you cluster to compress. **That premise is the right diagnosis of the wrong problem.**

The actual user-felt problem, in the author's own words on 2026-05-18:

> There's just no reason to even suggest that thing exists in my iPhone app coding project. (re: a `flight-rewards` skill appearing while writing iOS code)

That's *contextual irrelevance*, not catalog overflow. Clustering compresses the overflow but doesn't fix the irrelevance — if every cluster description is in every prelude, the iPhone project still sees the `flight-rewards` cluster.

BRO-180 (`docs/measurement.md`) measured both problems empirically:

| Mode | Reach@catalog | Prelude tokens |
|---|---|---|
| flat (no skill-tree) | 100.00% | ~2,721 |
| cluster (current global) | 6.82% | ~976 |
| per-project naive top-5 (LOO) | 74.24% | ~280 / project |

The cluster's 6.82% is partly an artifact — plugin-namespaced skills (`superpowers:*`) dominate invocations but aren't manifest-tracked. Even so, the **per-project naive floor at 74% / ~280 tokens beats every other configuration** on both axes that matter.

## Decision

**Pivot skill-tree's primary mode from global clustering to per-project provisioning.** Specifically:

1. **Default install behaviour** becomes: when `/skill-tree:setup` is invoked from a project root, write a provisioned `.claude/skills/` *into that project*. Source of truth is `~/.claude/skills-library/` (no change). Project copies are derived artifacts.
2. **Global cluster mode is kept** as `--global` opt-in, for users with shared home-directory work (e.g. one-off scripting in `~/`) and as a fallback for sessions started outside any project root.
3. **AI categorization stays the durable USP.** The naive Counter floor already wins at 74% — but a categorizer that reads project signals (`CLAUDE.md`, package manifests, language/framework detection from repo files) should push reach toward 90% on the seen-this-project case while gracefully handling first-time invocations.
4. **First-time-invocation fallback:** if the model tries to invoke a skill not provisioned to the project, surface it as a one-click "add to this project's manifest." Closes the 25.76% miss tail surfaced in BRO-180.
5. **Manifest scope expands** to include plugin-namespaced skills (the artifact behind cluster's 6.82%). Either index plugin SKILL.md files during scan, or document that skill-tree's reach metric applies to personal skills only.

## Why this beats the alternatives

**Why not status quo (global clusters only):**
The metric says it doesn't work at this scale (6.82% reach), and even adjusting for the plugin-skill artifact, clustering compresses a problem the user didn't have ("too many descriptions in prelude") rather than the one they did ("wrong descriptions in *this* prelude"). The author's own framing on 2026-05-18: "I haven't actually done the work of figuring out if outcomes are better." The data now exists, and they aren't.

**Why not per-project only:**
Home-directory sessions are real and need *some* catalog. The 25.76% cross-project miss tail also needs a recovery path. Keeping global mode as an opt-in fallback is cheap and matches Anthropic's "per-project plus global" architecture from [how-claude-code-works-in-large-codebases](https://claude.com/blog/how-claude-code-works-in-large-codebases-best-practices-and-where-to-start) (2026-05-15).

**Why not "both, gated by a flag":**
That's the literal decision, but the framing matters. "Per-project default + global fallback" treats per-project as the right answer and global as the exception. "Both modes equally" preserves the false equivalence the data has now disproven.

## Consequences

### Good

- The architecture matches the Anthropic best-practices post (per-project `.claude/skills/`, project-scoped plugins/MCP, master memory in PARA-style vault).
- AI-driven categorization becomes the differentiator vs every script-based sync alternative — a clear USP.
- Token cost per project drops from ~2,721 (flat) to ~280 (per-project N=5), a ~90% reduction in prelude budget. Compounds with cache hit rate.
- Solves the "iPhone skills in JavaScript project" pain directly.

### Bad

- `/skill-tree:setup` becomes a state-changing operation on every project, not a one-shot global config. Drift between project manifests and the global library is now a problem to design for.
- Per-project `.claude/skills/` directories proliferate. Cleanup story matters (e.g. `/skill-tree:sync --prune` to remove no-longer-relevant provisions).
- The "first-time invocation" fallback path is a new UX surface that doesn't exist today.
- Cross-platform parity (Claude Code / Codex / Gemini CLI / OpenClaw) gets more complex because each platform's per-project conventions differ. Already partially captured in BRO-183.

### Neutral

- Global cluster mode is retained but de-emphasized. Existing users who like it can stay.
- The `manifest.json` format extends rather than breaks — clusters and standalones still describe the global library; per-project provisioning is an additional surface, not a replacement.

## Open follow-ups (not blocking this ADR)

- **BRO-182** carries the implementation work.
- **Plugin-skill indexing** is a sub-task of BRO-182 (or its own issue if it grows).
- **Cross-project promotion UI/UX** for the 25.76% miss tail — design pass needed before BRO-182 lands.
- **BRO-183** (Codex port) needs to know about the per-project-default decision so it doesn't ship a global-only Codex plugin.

## Decision-makers

- Daniel Brodie (author, 2026-05-18)

## Decision-review trigger

Revisit if any of:
- Per-project reach drops below 60% in production over a 30-day window.
- A version of Claude Code lifts the system-prompt budget above 50K chars (would restore flat mode as viable).
- A new pain point emerges that neither mode addresses.
