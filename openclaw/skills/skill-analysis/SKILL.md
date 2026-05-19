---
name: skill-analysis
description: Reference for what skill-tree's other skills do on OpenClaw and how to compose them. Loads when the user asks "how do I use skill-tree", "which skill-tree command does X", or wants help orienting around the management/diagnosis surface. NOT a discovery tool for finding new skills to install.
metadata: { "openclaw": { "emoji": "🌳" } }
---

# What skill-tree's skills do on OpenClaw

skill-tree manages skills already in `~/.openclaw/skills/` — narrowing what the model sees and surfacing breakage. For new-skill discovery, see [`anthropics/claude-plugins-official/claude-code-setup`](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/claude-code-setup) or [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills) (Claude-Code-flavored but most entries port).

## When to suggest each skill

| User says... | Use |
|---|---|
| "is the manifest OK" / "are there any orphans" | `/check` |
| Hands you a GitHub URL to a SKILL.md and wants it added safely | `/fetch` |
| "I have many skills and the prelude is overflowing" — wants cluster routing set up | `/setup` |

## OpenClaw vs Claude Code layout

OpenClaw keeps both routers and leaves in `~/.openclaw/skills/` (same directory). Leaves are hidden via `disable-model-invocation: true` so they don't show up in the prelude until a router loads them on demand. The manifest at `~/.openclaw/skills/skill-tree/manifest.json` is the source of truth for the graph.
