<p align="center">
  <img src="assets/header-final.png" alt="skill-tree" width="100%">
</p>

# skill-tree

Two-tier routing architecture for agent skills at scale. When your flat skills directory hits 100+ skills, catalog budgets overflow and the model picks poorly. skill-tree clusters skills into routers, validates graph integrity, and keeps token budgets under control.

Ships as a **Claude Code plugin** and **Gemini CLI extension**, with Codex CLI compatibility via `agents/openai.yaml` generation.

## The Problem

Agent skill platforms (Claude Code, Codex CLI, Gemini CLI) load skill descriptions into context at session start. Claude Code caps this at 2% of the context window (~16K characters). At ~100 tokens per skill, descriptions start getting **silently dropped around 160 skills** — the model never knows those skills exist.

Even below the cap, routing accuracy degrades as the flat list grows. The model must choose among hundreds of undifferentiated descriptions and picks poorly.

## The Solution

Replace a flat catalog of 180 skill descriptions with ~20 cluster-level descriptions. Two-hop routing: the model selects a cluster, then routes within 7-12 leaf skills.

```
~/.claude/skills/              ← scan path: cluster routers ONLY (~20)
  research-index/SKILL.md      ← routing table pointing to leaf skills
  dev-tools/SKILL.md
  video-design/SKILL.md

~/.claude/skills-library/      ← library: leaf skills (~180), invisible to catalog
  librarium/SKILL.md
  github-ops/SKILL.md
  skill-tree/
    manifest.json              ← source of truth for the entire graph
```

**manifest.json** is the single source of truth. Cluster SKILL.md files are generated artifacts — `skill-tree sync` regenerates them deterministically from the manifest.

## Install

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

### Claude Code

```bash
claude plugin marketplace add danielbrodie/skill-tree
claude plugin install skill-tree@skill-tree
```

Then run `/setup` to get started.

### Gemini CLI

```bash
gemini extensions install https://github.com/danielbrodie/skill-tree
```

Then run `/setup` to get started.

### Codex CLI

Codex CLI has no plugin system. Copy cluster routers to `~/.codex/skills/` (or `~/.agents/skills/`):

```bash
git clone https://github.com/danielbrodie/skill-tree.git
cd skill-tree

# Bootstrap manifest from existing skills
uv run scripts/init.py --skills-dir ~/.codex/skills

# Propose cluster structure
uv run scripts/scan.py --skills-dir ~/.codex/skills

# Sync cluster files + generate agents/openai.yaml
uv run scripts/sync.py --skills-dir ~/.codex/skills --codex
```

The `--codex` flag generates `agents/openai.yaml` in each leaf skill with `allow_implicit_invocation: false`, preventing Codex from invoking leaves directly — routing goes through cluster skills instead.

## Commands

| Command | Purpose |
|---------|---------|
| `/check` | Health check — validation, cluster overview, token savings |
| `/setup` | Bootstrap, cluster, and generate routing files |
| `/fetch <url>` | Fetch a skill from GitHub and wire it in |

## Quick Start

```bash
# First time: detect skills, cluster, generate routing files
/setup

# Anytime: see health, token savings, and cluster overview
/check

# Add a new skill from GitHub
/fetch https://github.com/org/repo/tree/main/skills/skill-name
```

## How It Works

### `/check`

Shows everything in one view: validation results (9 checks), cluster overview, and token savings comparison.

```
skill-tree — 163 skills managed

  Flat catalog:    ~16,300 tokens
  With skill-tree: ~1,876 tokens (88% reduction)

Clusters (22):
  research-index       5 leaves   Research — web search, deep research...
  dev-tools            8 leaves   Developer tools — GitHub, coding agents...
  ...

No errors. 16 warnings.
```

A **SessionStart hook** runs this automatically and prints a one-liner if issues are found.

### `/setup`

Runs the full pipeline with confirmation between steps:

1. **Bootstrap** — detect existing skills, create manifest
2. **Cluster** — propose structure via TF-IDF + agglomerative clustering (scikit-learn). Configurable `--threshold` (0-1)
3. **Sync** — preview changes, then generate cluster routing files and set disable flags
4. **Verify** — run `/check` to confirm

### `/fetch`

Fetches a skill from GitHub, displays the **full content** for review, runs security checks, matches to the best cluster, and sandboxes by default (`disable-model-invocation: true`).

Security: full content display, no `--yes` flag, content policy warnings (prompt injection, zero-width unicode, path traversal), source pinning with Git SHA.

## Manifest Schema

```json
{
  "version": "1.0",
  "unclusteredBudget": 25,
  "clusters": {
    "research-index": {
      "description": "Research — web search, deep research, notebooks.",
      "customInstructions": "## Decision tree\n...",
      "crossReferences": [
        { "skill": "obsidian-index", "note": "write output to vault" }
      ],
      "leaves": {
        "librarium": {
          "routingHint": "Multi-provider fan-out research."
        }
      }
    }
  },
  "standalones": ["weather", "ebay"],
  "hotPath": ["flowdeck"],
  "referenceNodes": ["agent-cli-tools"],
  "deprecated": ["old-skill"]
}
```

## Project Structure

```
skill-tree/
  .claude-plugin/                Claude Code plugin + marketplace manifests
  gemini-extension.json          Gemini CLI extension manifest
  GEMINI.md                      Gemini CLI context file
  skills/
    check/SKILL.md               /check command
    setup/SKILL.md               /setup command
    fetch/SKILL.md               /fetch command
    skill-analysis/SKILL.md      Auto-invoked for skill organization questions
  commands/*.toml                Gemini CLI slash commands
  hooks/hooks.json               SessionStart hook
  scripts/
    status.py                    Combined health check + graph overview
    init.py                      Bootstrap manifest
    check.py                     9 validation checks
    sync.py                      Regenerate cluster files + Codex YAML
    scan.py                      TF-IDF clustering
    add.py                       GitHub fetch + auto-route
    list.py                      Graph summary
    lib/                         Shared libraries
  tests/                         135+ unit tests
```

Scripts use `uv run` with PEP 723 inline dependencies — no separate install step.

## Cross-Platform

The two-directory split (scan path vs library) is the primary hiding mechanism. It works portably across all three platforms:

| Platform | Scan path | Library | Leaf hiding |
|----------|-----------|---------|-------------|
| Claude Code | `~/.claude/skills/` | `~/.claude/skills-library/` | `disable-model-invocation: true` in frontmatter |
| Codex CLI | `~/.codex/skills/` | `~/.claude/skills-library/` | `agents/openai.yaml` with `allow_implicit_invocation: false` |
| Gemini CLI | `~/.gemini/skills/` | `~/.claude/skills-library/` | Directory separation only (no file-based mechanism) |

All scripts accept `--skills-dir` and `--library-dir` flags to override defaults.

### Per-platform leaf hiding (belt-and-suspenders)

Directory separation is the universal mechanism — leaves in the library are never in any scan path. As redundant protection, `sync` applies per-platform flags:

- **Claude Code:** Sets `disable-model-invocation: true` in leaf SKILL.md frontmatter (always applied)
- **Codex CLI:** Generates `agents/openai.yaml` with `allow_implicit_invocation: false` (opt-in via `--codex`)
- **Gemini CLI:** No file-based mechanism exists. Directory separation is the only option. If users symlink leaves into Gemini's scan path, they can manually run `gemini skills disable <name>`

### Example `agents/openai.yaml` (generated by `--codex`)

```yaml
interface:
  display_name: "Librarium"
  short_description: "Multi-provider fan-out research."

policy:
  allow_implicit_invocation: false
```

## Example Cluster Template

When `sync` generates a cluster SKILL.md, it uses this template:

```markdown
---
name: research-index
description: "Research — web search, deep research, notebooks."
version: 1.0.0
---

## How to use this cluster
1. Read the routing table below
2. Select the sub-skill that matches the request
3. Load it: use the `read` tool on `~/.claude/skills-library/<skill-name>/SKILL.md`

If the user or task explicitly names a skill, load it directly.

## Routing table

| Skill | When to use |
|-------|-------------|
| `librarium` | Multi-provider fan-out research. |
| `notebooklm-research` | Deep research via NotebookLM. |
| `context-research` | Targeted context gathering. |

## Cross-references
- `obsidian-index`: write research output to vault — load directly: `~/.claude/skills-library/obsidian-index/SKILL.md`
```

The `customInstructions` field in the manifest lets you inject additional guidance between the header and routing table (e.g., decision trees, priority rules).

## Migrating from skill-graph

If you were using the earlier `skill-graph` sync tool (`~/.claude/skills-library/skill-graph/sync.py`):

1. Copy your manifest: `cp ~/.claude/skills-library/skill-graph/manifest.json ~/.claude/skills-library/skill-tree/manifest.json`
2. Install skill-tree as a plugin (see Install above)
3. Run `/check` to validate
4. Run `/setup` to regenerate cluster files

The old `skill-graph/sync.py` is superseded and can be retired.

## Academic Grounding

- [AgentSkillOS](https://arxiv.org/abs/2603.02176) — Tree retrieval at 200K scale, DAG orchestration outperforms flat invocation
- [SkillOrchestra](https://arxiv.org/abs/2602.19672) — Skills-as-routing-primitive, 700x cheaper than RL
- [ToolACE-MCP](https://arxiv.org/abs/2601.08276) — 8B router beats GPT-4o at tool selection
- [Agent READMEs](https://arxiv.org/abs/2511.12884) — Context debt in agent instruction files

## License

Apache 2.0
