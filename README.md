<p align="center">
  <img src="assets/header-final.png" alt="skill-tree" width="100%">
</p>

# skill-tree

Agent skill platforms load every skill description into context at session start. Claude Code caps this at ~16K characters. At ~160 skills, descriptions get **silently dropped** — the model doesn't know they exist.

skill-tree fixes this. It groups your skills into clusters with routing tables. Instead of 160 skill descriptions in context, you get ~20 cluster descriptions. The model picks a cluster, then loads the right skill on demand.

```
Before: 163 skills × ~100 tokens = ~16,300 tokens (over budget, skills dropped)
After:   22 clusters × ~85 tokens =  ~1,876 tokens (88% reduction, nothing dropped)
```

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
Or from a clone: `git clone` the repo, then `openclaw plugins install ./skill-tree/openclaw`.

**Codex CLI** — no plugin system, use scripts directly:
```bash
git clone https://github.com/danielbrodie/skill-tree.git
cd skill-tree
uv run scripts/init.py --skills-dir ~/.codex/skills
uv run scripts/scan.py --skills-dir ~/.codex/skills
uv run scripts/sync.py --skills-dir ~/.codex/skills --codex
```

## Usage

Three commands:

| Command | What it does |
|---------|-------------|
| `/setup` | Detect your skills, cluster them, generate routing files |
| `/check` | Show health, clusters, and token savings |
| `/fetch <url>` | Add a skill from GitHub |

Run `/setup` after install. Run `/check` anytime to see status:

```
skill-tree — 163 skills managed

  Flat catalog:    ~16,300 tokens
  With skill-tree: ~1,876 tokens (88% reduction)

Clusters (22):
  research-index       5 leaves   Research — web search, deep research...
  dev-tools            8 leaves   Developer tools — GitHub, coding agents...
  ...

No errors.
```

A SessionStart hook runs `/check` automatically and alerts you if anything is wrong.

## How it works

skill-tree keeps skills in two directories:

```
~/.claude/skills/           ← cluster routers (what the model sees)
  research-index/SKILL.md   ← routing table: "use librarium for X, notebooklm for Y"
  dev-tools/SKILL.md

~/.claude/skills-library/   ← leaf skills (hidden from catalog, loaded on demand)
  librarium/SKILL.md
  github-ops/SKILL.md
  skill-tree/manifest.json  ← source of truth
```

**manifest.json** defines the graph. `/setup` creates it, `/check` validates it. Cluster SKILL.md files are generated — edit the manifest, not the clusters.

`/fetch` downloads skills from GitHub, shows you the full content, runs security checks (prompt injection, zero-width unicode, path traversal), and sandboxes new skills by default.

## Cross-platform

Works on Claude Code, Gemini CLI, and Codex CLI. The two-directory split is portable — all scripts accept `--skills-dir` and `--library-dir` to target any platform's paths. The `--codex` flag on sync generates `agents/openai.yaml` files for Codex compatibility.

## License

Apache 2.0
