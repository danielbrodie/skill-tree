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
| `/bootstrap` | Bootstrap manifest from existing skills |
| `/validate` | Validate graph integrity (9 checks) |
| `/regen` | Regenerate cluster files from manifest |
| `/graph` | Show graph state with token estimate |
| `/scan` | Propose cluster structure from flat skills |
| `/fetch` | Fetch a skill from GitHub and wire it in |

## Key concepts

- **Cluster**: A routing skill in the scan path that points to leaf skills via a routing table
- **Leaf**: An implementation skill in the library, hidden from catalog via `disable-model-invocation: true`
- **Standalone**: A skill that stays in the scan path without clustering
- **Hot path**: Always-loaded skills (e.g., flowdeck)
- **Reference node**: Utility skills with `disable-model-invocation` (not routed, loaded explicitly)

## When to suggest actions

- User asks "how many skills do I have" → run `/graph`
- User says "check my skills" → run `/validate`
- User says "something broke" about skills → run `/validate`
- User edited the manifest → suggest `/regen`
