# skill-tree

Two-tier routing architecture for agent skills at scale. Clusters skills into routers, validates graph integrity, and keeps catalog budgets under control.

## Architecture

- **Scan path** (`~/.gemini/skills/`): Contains cluster routing skills only. These are what the model sees at session start.
- **Library** (`~/.claude/skills-library/`): Contains leaf skills. These are loaded on demand when a cluster routes to them.
- **Manifest** (`~/.claude/skills-library/skill-tree/manifest.json`): Single source of truth for the graph structure.

## Available commands

| Command | Purpose |
|---------|---------|
| `/skill-tree init` | Bootstrap manifest from existing skills |
| `/skill-tree check` | Validate graph integrity (9 checks) |
| `/skill-tree sync` | Regenerate cluster files from manifest |
| `/skill-tree list` | Show graph state with token estimate |
| `/skill-tree scan` | Propose cluster structure from flat skills |
| `/skill-tree add` | Fetch a skill from GitHub and wire it in |

## Note on cross-platform paths

skill-tree scripts accept `--skills-dir` and `--library-dir` flags. For Gemini CLI, pass `--skills-dir ~/.gemini/skills` when running commands.
