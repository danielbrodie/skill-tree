---
name: skill-analysis
description: "Auto-invoked when users ask about skill organization, routing, catalog budget, or skill graph management. Provides context about the two-tier skill architecture."
---

# Skill Analysis

You are helping manage a two-tier skill routing architecture via the skill-tree plugin.

## Architecture

- **Scan path** (`~/.claude/skills/`): Contains cluster routing skills only (~12-25 clusters). These are what the model sees at session start.
- **Library** (`~/.claude/skills-library/`): Contains leaf skills (~180+). These are loaded on demand when a cluster routes to them.
- **Manifest** (`~/.claude/skills-library/skill-tree/manifest.json`): Single source of truth for the graph structure.

## Available commands

| Command | Purpose |
|---------|---------|
| `/skill-tree:init` | Bootstrap manifest from existing skills |
| `/skill-tree:check` | Validate graph integrity (9 checks) |
| `/skill-tree:sync` | Regenerate cluster files from manifest |
| `/skill-tree:list` | Show graph state with token estimate |

## Key concepts

- **Cluster**: A routing skill in the scan path that points to leaf skills via a routing table
- **Leaf**: An implementation skill in the library, hidden from catalog via `disable-model-invocation: true`
- **Standalone**: A skill that stays in the scan path without clustering
- **Hot path**: Always-loaded skills (e.g., flowdeck)
- **Reference node**: Utility skills with `disable-model-invocation` (not routed, loaded explicitly)

## When to suggest actions

- User asks "how many skills do I have" → run `/skill-tree:list`
- User says "check my skills" → run `/skill-tree:check`
- User says "something broke" about skills → run `/skill-tree:check`
- User edited the manifest → suggest `/skill-tree:sync`
