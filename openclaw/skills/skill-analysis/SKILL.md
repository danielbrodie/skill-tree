---
name: skill-analysis
description: "Auto-invoked when users ask about skill organization, routing, catalog budget, or skill graph management. Provides context about the two-tier skill architecture."
metadata: { "openclaw": { "emoji": "🌳" } }
---

# Skill Analysis

You are helping manage a two-tier skill routing architecture via the skill-tree plugin.

## Architecture

- **Skills path** (`~/.openclaw/skills/`): Contains both cluster routers and leaf skills. Routers are visible in the prompt; leaves are hidden via `disable-model-invocation: true`.
- **Manifest** (`~/.openclaw/skills/skill-tree/manifest.json`): Single source of truth for the graph structure.

## Commands

| Command | Purpose |
|---------|---------|
| `/check` | Health check — validation, clusters, token savings |
| `/setup` | Bootstrap, cluster, and generate routing files |
| `/fetch` | Fetch a skill from GitHub and wire it in |

## Key concepts

- **Cluster**: A routing skill that points to leaf skills via a routing table
- **Leaf**: An implementation skill, hidden from prompt via `disable-model-invocation: true`
- **Standalone**: A skill that stays visible without clustering
- **Hot path**: Always-loaded skills
- **Reference node**: Utility skills with `disable-model-invocation` (not routed, loaded explicitly)

## When to suggest actions

- User asks "how many skills do I have" → run `/check`
- User says "check my skills" → run `/check`
- User says "something broke" about skills → run `/check`
- User edited the manifest → suggest `/setup`
