# skill-tree on Codex CLI

This is the per-project provisioning surface for OpenAI Codex CLI, paired with the existing Claude Code, Gemini CLI, and OpenClaw surfaces. Same engine (`scripts/`), platform-specific manifest.

## Install

```bash
# 1. Clone the repo somewhere stable
git clone https://github.com/danielbrodie/skill-tree ~/.codex/marketplaces/skill-tree

# 2. Register as a Codex marketplace — point at the REPO ROOT, not .codex-plugin/
codex plugin marketplace add ~/.codex/marketplaces/skill-tree

# 3. Enable the plugin in ~/.codex/config.toml
echo '[plugins."skill-tree@danielbrodie"]' >> ~/.codex/config.toml
```

Codex's marketplace convention: it looks for `<root>/.agents/plugins/marketplace.json` to enumerate plugins, then for each plugin entry it looks at `<plugin-path>/.codex-plugin/plugin.json` for the actual manifest. For skill-tree, `<plugin-path>` is the repo root itself (single-plugin marketplace).

After enabling, restart Codex. The bundled `skills/` directory becomes available: `provision`, `setup`, `check`, `fetch`, `audit`, `sync`, `skill-analysis`.

## Differences from Claude Code

| Aspect | Claude Code | Codex |
|---|---|---|
| Path variable in SKILL.md | `${CLAUDE_PLUGIN_ROOT}` | (TBD — use absolute paths or detect at runtime) |
| SessionStart hooks | Yes — runs `/check --quiet --notify` | No equivalent surface yet. Run `/skill-tree:check` manually. |
| Per-project skills location | `<project>/.claude/skills/` | Same — `<project>/.claude/skills/` (cross-CLI convention) |
| Slash command prefix | `/skill-tree:` | `/skill-tree:` (parity) |

## Known caveats

1. **No SessionStart hook surface in Codex.** The "you have 5 errors in skill-tree" status nudge from Claude Code doesn't have an equivalent. Workaround: run `/skill-tree:check` after `codex` opens.
2. **Codex marketplaces are local-path-based today.** Once Codex supports remote marketplaces (analogous to Claude Code's `plugin marketplace add <github-url>`), this install path simplifies. Until then, clone-then-register is the pattern.

## What got fixed under

Previously, SKILL.md files referenced `uv run ${CLAUDE_PLUGIN_ROOT}/scripts/foo.py`. The `CLAUDE_PLUGIN_ROOT` env var is Claude Code-specific — on Codex (and Gemini CLI) it's undefined, so those commands silently failed.

Replaced with `${CLAUDE_PLUGIN_ROOT}/bin/skill-tree foo` — a thin bash dispatcher at the plugin root. The wrapper resolves the plugin root in this priority order:

1. `SKILL_TREE_ROOT` env var (explicit override)
2. `CLAUDE_PLUGIN_ROOT` env var (set by Claude Code)
3. The wrapper's own location (`bin/../`) — works whenever bin/skill-tree sits at `<plugin-root>/bin/skill-tree`

Codex users only need to set `SKILL_TREE_ROOT` once if `CLAUDE_PLUGIN_ROOT` isn't set:

```bash
export SKILL_TREE_ROOT=~/.codex/marketplaces/skill-tree
```

Or invoke the wrapper by absolute path (`/path/to/skill-tree/bin/skill-tree provision --list-candidates`) — it self-resolves via its own location.

## Status

The plugin manifest exists and is validated by the test suite (`test_codex_plugin.py`). End-to-end install requires Codex to support local-path marketplaces, which the current Codex CLI does.
