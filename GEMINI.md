# skill-tree

Two-tier routing architecture for agent skills at scale. Clusters skills into routers, validates graph integrity, and keeps catalog budgets under control.

## Architecture

- **Scan path** (`~/.gemini/skills/`): Contains cluster routing skills only. These are what the model sees at session start.
- **Library** (`~/.claude/skills-library/`): Contains leaf skills. These are loaded on demand when a cluster routes to them.
- **Manifest** (`~/.claude/skills-library/skill-tree/manifest.json`): Single source of truth for the graph structure.

## Available commands

| Command | Purpose |
|---------|---------|
| `/check` | Health check — validation, clusters, token savings |
| `/setup` | Bootstrap, cluster, and generate routing files |
| `/fetch` | Fetch a skill from GitHub and wire it in |

## Note on cross-platform paths

skill-tree scripts accept `--skills-dir` and `--library-dir` flags. For Gemini CLI, pass `--skills-dir ~/.gemini/skills` when running commands.
