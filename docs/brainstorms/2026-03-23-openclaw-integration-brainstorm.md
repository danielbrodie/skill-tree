---
date: 2026-03-23
topic: openclaw-integration
---

# OpenClaw Plugin Integration for skill-tree

## What We're Building

A native OpenClaw plugin (`openclaw.plugin.json` + TypeScript entry + skills) that brings skill-tree's clustering and routing to OpenClaw users. The plugin scans skills across all OpenClaw locations (workspace, managed, bundled, plugin-shipped), clusters them, writes cluster routers to the shared managed path, and hides leaves via `disable-model-invocation: true`.

The Python scripts stay as the engine. The TypeScript plugin is a thin shell that ships skills (slash commands) which invoke the scripts. Same pattern as the `open-prose` bundled plugin.

## Why This Approach

OpenClaw has the same scaling problem as Claude Code — flat skill list, per-skill token cost (~97 chars + metadata), truncation at 30K chars / 150 skills. No native clustering exists. The `acp-router` pattern (hand-rolled routing inside a SKILL.md) is exactly what skill-tree automates.

We chose to work WITH OpenClaw's skill system rather than around it:
- Cluster routers go in `~/.openclaw/skills/` (shared managed path) — visible to all agents
- Leaves stay wherever they already are — no file movement
- Hiding is via `disable-model-invocation: true` flag, not directory separation
- This is different from Claude Code where we use a two-directory split as the primary mechanism

## Key Decisions

- **Cluster router location**: `~/.openclaw/skills/` (shared managed path). Routers are visible to all agents on the machine. Leaves stay in their original locations.
- **Leaf hiding**: `disable-model-invocation: true` only (no directory separation). OpenClaw's `formatSkillsForPrompt` already filters these out. Belt-and-suspenders directory separation doesn't apply here since we're not moving files.
- **Manifest location**: `~/.openclaw/skills/skill-tree/manifest.json`. Same pattern as Claude Code (`~/.claude/skills-library/skill-tree/manifest.json`).
- **Manifest format**: Same `manifest.json` schema across all platforms. Scripts use `--skills-dir` and `--library-dir` flags to target OpenClaw paths.
- **Fetch strategy**: Parallel to ClawHub. OpenClaw users can use `clawhub install` for registry skills OR `/fetch` for arbitrary GitHub skills. Both get clustered on next `/setup`.
- **Plugin architecture**: `open-prose` pattern — `openclaw.plugin.json` with `"skills": ["./skills"]`, empty `register()`. Skills invoke Python scripts via bash. No TypeScript logic needed.
- **Script invocation**: Skills use `{baseDir}/../scripts/status.py` paths. Plugin requires `uv` on PATH (`metadata.openclaw.requires.bins: ["uv"]`).

## Platform Differences

| Aspect | Claude Code | OpenClaw |
|--------|------------|----------|
| Router location | `~/.claude/skills/` | `~/.openclaw/skills/` |
| Leaf hiding | Directory separation + `disable-model-invocation` | `disable-model-invocation` only |
| Manifest | `~/.claude/skills-library/skill-tree/manifest.json` | `~/.openclaw/skills/skill-tree/manifest.json` |
| Skill install | `/fetch` (GitHub) | `/fetch` (GitHub) + `clawhub install` (registry) |
| Scan sources | Two directories | All OpenClaw locations (workspace, managed, bundled, plugin) |

## Open Questions

None — all resolved during brainstorm.

## Next Steps

→ `/ce:plan` for implementation details
