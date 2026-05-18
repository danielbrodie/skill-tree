<p align="center">
  <img src="assets/header-final.png" alt="skill-tree" width="100%">
</p>

# skill-tree

skill-tree is **the institutional-knowledge layer for the AI-skill ecosystem.** It runs inside your AI agent (Claude Code, Codex, Gemini CLI, OpenClaw) and uses that agent to navigate the multi-vendor, multi-tool reality of how skills are packaged, installed, organized, and removed across ~15 agent platforms.

**The product is the encoded expertise.** [`docs/ecosystem-map.md`](docs/ecosystem-map.md) catalogues every notable agent platform, every popular skill packager (obra/superpowers, mattpocock/skills, vercel-labs/skills, anthropics/claude-plugins-official, rudrankriyam/asc-skills, mvanhorn/printing-press-library, and more), every installer (`claude plugin`, `codex plugin`, `gemini extensions`, `npx skills`, hand-install), every frontmatter convention, and every common failure mode. [`docs/registry-map.md`](docs/registry-map.md) catalogues every place a skill can live on a single machine.

The Python scripts in `scripts/` are eyes and arms; the docs are the brain.

## What skill-tree does, concretely

- **`/skill-tree:audit`** — survey every skill registry on this machine, cross-reference with every installer's lock file, detect every failure-mode pattern, surface ranked findings with the safe-action command for each (Phase 1 of [BRO-190](https://linear.app/brodiegraphics/issue/BRO-190))
- **`/skill-tree:catalog <topic>`** — given a need ("I want a skill for Stripe webhooks"), search known skill repos and recommend installs (Phase 2)
- **`/skill-tree:diagnose <problem>`** — walk the failure-mode signatures to debug specific issues (Phase 3)
- **`/skill-tree:install <ref>`** — dispatch to the right installer based on the ref type (Phase 4)
- **`/skill-tree:provision`** — per-project skill provisioning (the ADR 0002 hybrid model)
- **`/skill-tree:sync`** — reconcile project manifest drift
- **`/skill-tree:archive`** — non-destructively move unused personal skills out of the always-on prelude
- **`/skill-tree:check`** — health check on the manifest graph

## Design history

- [ADR 0001](docs/adr/0001-routing-vs-provisioning.md) — original "pivot to per-project" decision (superseded same day by ADR 0002 after validation)
- [ADR 0002](docs/adr/0002-hybrid-global-base-plus-per-project-tail.md) — hybrid global-popular base + per-project tail
- [ADR 0003](docs/adr/0003-institutional-knowledge.md) — **skill-tree as institutional-knowledge layer** (the current product framing)
- [`docs/measurement.md`](docs/measurement.md) — outcome metric definition
- [`docs/validation-2026-05-18.md`](docs/validation-2026-05-18.md) — the validation that drove the pivots

## What it solves

> "There's just no reason to even suggest that thing exists in my iPhone app coding project." — the author, on a `flight-rewards` skill appearing while writing iOS code.

Claude Code shows every skill description in the prompt at session start. With ~150+ skills the prelude gets bloated, descriptions compete for attention, and irrelevant skills get suggested. skill-tree treats this as a **relevance** problem, not a compression problem — load the small set that actually fits the project.

## Measurement-first

skill-tree ships with the scripts that measured its own value:

- `scripts/measure.py` — walks `~/.claude/projects/**/*.jsonl` and emits a labelled corpus of `(project, prompt, invoked-skill)`.
- `scripts/simulate.py` — scores three modes (flat, cluster, per-project) against the corpus.
- `scripts/provision.py --global-suggest` — prints the top-N most-invoked skills from your own corpus, marks which are still installed locally.

The current baseline (132 records / 60 days from the author's setup):

| Mode | Reach@catalog | Prelude tokens |
|---|---|---|
| flat (every skill always visible) | 88.64% | ~13,563 |
| cluster (legacy global manifest) | 6.82% | ~976 |
| global-popular top-5 (no project signal) | 78.03% | ~250 |
| per-project naive top-5 (LOO) | 74.24% | ~250 / project |

`Reach@catalog` = fraction of historical invocations whose skill was in the prelude's catalog. See [`docs/measurement.md`](docs/measurement.md) for methodology and caveats.

The headline: the global-popular baseline beats per-project history-based picking at typical budgets. That's why ADR 0002 reframes the product as a hybrid rather than per-project-only.

## Install

Requires [Python 3.11+](https://www.python.org/) and [uv](https://docs.astral.sh/uv/).

**Claude Code:**
```bash
claude plugin marketplace add danielbrodie/skill-tree
claude plugin install skill-tree@skill-tree
```

**Gemini CLI:**
```bash
gemini extensions install https://github.com/danielbrodie/skill-tree
```

**OpenClaw:**
```bash
openclaw plugins install ./openclaw
```

**Codex CLI:**
```bash
git clone https://github.com/danielbrodie/skill-tree ~/.codex/marketplaces/skill-tree
codex plugin marketplace add ~/.codex/marketplaces/skill-tree/.codex-plugin
codex plugin install skill-tree@danielbrodie
```
See [`docs/codex.md`](docs/codex.md) for the full Codex story (known caveats: no SessionStart hook surface, `${CLAUDE_PLUGIN_ROOT}` is Claude-specific).

## Commands

| Command | Layer | What it does |
|---|---|---|
| `/skill-tree:provision --global-suggest` | global base | Print the top-N most-invoked skills from your session history. Non-destructive — you decide what to install or retire. |
| `/skill-tree:provision` | per-project tail | Read project signals (CLAUDE.md, package manifest, language detection), pick a small set of project-specific skills, copy them into `<project>/.claude/skills/`. |
| `/skill-tree:check` | both | Validate the manifest + project setup. Reports errors and warnings. |
| `/skill-tree:fetch <url>` | both | Download a skill from GitHub with security checks (prompt injection, zero-width unicode, path traversal). New skills are sandboxed (`disable-model-invocation: true`) until you add them to a cluster. |
| `/skill-tree:setup` | global cluster (legacy) | The original v0.5 cluster-routing mode. Kept for users with very large catalogs (~160+ skills). See ADR 0001 for the historical design. |

## Project manifest

Per-project state lives at `<project>/.claude/.skilltree.json`:

```json
{
  "version": "1.0",
  "sourceLibrary": "/Users/daniel/.claude/skills",
  "syncedAt": "2026-05-18T20:34:34Z",
  "skills": {
    "tdd": {
      "source": "/Users/daniel/.claude/skills/tdd",
      "reason": "Python+pytest repo; CLAUDE.md emphasizes red-green-refactor",
      "syncedAt": "2026-05-18T20:34:34Z"
    }
  },
  "auditLog": [
    {"at": "2026-05-18T20:34:34Z", "action": "added", "skill": "tdd", "reason": "..."}
  ]
}
```

Skills are **copied** from the global library, not symlinked — project-local edits won't fight upstream library changes. Drift is the tradeoff (a `sync` command will reconcile when needed).

## Cross-platform

| Platform | Plugin manifest | Per-project skills location | SessionStart `/check` hook |
|---|---|---|---|
| Claude Code | `.claude-plugin/plugin.json` | `<project>/.claude/skills/` | yes |
| Gemini CLI | `gemini-extension.json` | `<project>/.claude/skills/` | yes |
| OpenClaw | `openclaw/openclaw.plugin.json` | `~/.openclaw/skills/` | yes |
| Codex CLI | `.codex-plugin/plugin.json` | `<project>/.claude/skills/` | no (Codex doesn't expose hooks yet) |

Scripts under `scripts/` are the shared engine; each platform manifest is a thin wrapper.

## Upgrading

Upgrading never touches your manifest — cluster assignments, custom instructions, and manual edits are preserved.

| Platform | How to upgrade |
|---|---|
| Claude Code | `claude plugin update skill-tree@skill-tree` |
| Gemini CLI | `gemini extensions update skill-tree` |
| OpenClaw | `git pull` in the cloned repo, then restart the gateway |
| Codex CLI | `git pull` in the cloned marketplace, then `codex plugin update skill-tree@danielbrodie` |

## Design history

- [`docs/adr/0001-routing-vs-provisioning.md`](docs/adr/0001-routing-vs-provisioning.md) — original "pivot to per-project" decision (May 18, 2026). Superseded.
- [`docs/adr/0002-hybrid-global-base-plus-per-project-tail.md`](docs/adr/0002-hybrid-global-base-plus-per-project-tail.md) — current design (May 18, 2026). Based on the BRO-184 / BRO-185 validation finding that global-popular beats per-project alone.
- [`docs/measurement.md`](docs/measurement.md) — outcome metric definition, methodology.
- [`docs/validation-2026-05-18.md`](docs/validation-2026-05-18.md) — what the validation actually showed.

## License

Apache 2.0
