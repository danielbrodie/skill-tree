# skill-tree on Codex CLI

This is the per-project provisioning surface for OpenAI Codex CLI, paired with the existing Claude Code, Gemini CLI, and OpenClaw surfaces. Same engine (`scripts/`), platform-specific manifest.

## Install

```bash
# 1. Clone the repo somewhere stable
git clone https://github.com/danielbrodie/skill-tree ~/.codex/marketplaces/skill-tree

# 2. Register as a Codex marketplace
codex plugin marketplace add ~/.codex/marketplaces/skill-tree/.codex-plugin

# 3. Install the plugin
codex plugin install skill-tree@danielbrodie
```

After install, Codex will pick up `skills/` automatically and load `provision`, `setup`, `check`, `fetch`, and `skill-analysis`.

## Differences from Claude Code

| Aspect | Claude Code | Codex |
|---|---|---|
| Path variable in SKILL.md | `${CLAUDE_PLUGIN_ROOT}` | (TBD — use absolute paths or detect at runtime) |
| SessionStart hooks | Yes — runs `/check --quiet --notify` | No equivalent surface yet. Run `/skill-tree:check` manually. |
| Per-project skills location | `<project>/.claude/skills/` | Same — `<project>/.claude/skills/` (cross-CLI convention) |
| Slash command prefix | `/skill-tree:` | `/skill-tree:` (parity) |

## Known caveats (filed as follow-ups to BRO-183)

1. **No SessionStart hook surface in Codex.** The "you have 5 errors in skill-tree" status nudge from Claude Code doesn't have an equivalent. Workaround: run `/skill-tree:check` after `codex` opens.
2. **`${CLAUDE_PLUGIN_ROOT}` is Claude-specific.** Some bundled SKILL.md files reference it. For Codex parity, those skills will either need runtime path detection or per-platform substitution at install time. Filed as a follow-up; for now, copy them to absolute paths or use scripts via `uv run` from a known location.
3. **Codex marketplaces are local-path-based today.** Once Codex supports remote marketplaces (analogous to Claude Code's `plugin marketplace add <github-url>`), this install path simplifies. Until then, clone-then-register is the pattern.

## Status

The plugin manifest exists and is validated by the test suite (`test_codex_plugin.py`). End-to-end install requires Codex to support local-path marketplaces, which the current Codex CLI does.
