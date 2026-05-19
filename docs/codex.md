# skill-tree on Codex CLI

skill-tree's surfaces — `provision`, `audit`, `diagnose`, `sync`, `fetch`, `check` — work on Codex CLI alongside Claude Code and Gemini CLI. The Python scripts in `scripts/` are the engine; the per-platform manifest is a thin wrapper.

## Where Codex actually looks for skills

Per the official [Codex Skills docs § Where to save skills](https://developers.openai.com/codex/skills#where-to-save-skills):

| Scope | Path |
|---|---|
| Repository | `$CWD/.agents/skills`, `$CWD/../.agents/skills`, `$REPO_ROOT/.agents/skills` |
| User | `$HOME/.agents/skills` |
| Admin | `/etc/codex/skills` |
| System | Bundled with Codex by OpenAI |

Note: `$HOME/.agents/skills` is the same directory the [vercel-labs/skills](https://github.com/vercel-labs/skills) CLI writes to for its multi-agent fan-out. A single `npx skills add` install is therefore readable by Codex natively.

skill-tree's per-project provisioner copies into `<project>/.claude/skills/` rather than `<project>/.agents/skills/` for cross-platform consistency. If you want the project-scope set picked up by Codex specifically, point Codex at it or use one of Codex's repo-scope paths.

## Installing as a Codex plugin

Verified against codex-cli 0.130.0 on 2026-05-19.

```bash
# 1. Clone somewhere stable
git clone https://github.com/danielbrodie/skill-tree ~/.codex/marketplaces/skill-tree

# 2. Register as a local Codex marketplace — point at the REPO ROOT, not .codex-plugin/
codex plugin marketplace add ~/.codex/marketplaces/skill-tree

# 3. Enable the plugin in ~/.codex/config.toml
echo '[plugins."skill-tree@danielbrodie"]' >> ~/.codex/config.toml
```

**There is no `codex plugin install` subcommand.** As of 0.130.0, `codex plugin` only has `marketplace add/upgrade/remove`. The `[plugins."<name>@<marketplace>"]` block in `~/.codex/config.toml` is the activation — that's what flips the plugin on.

Codex's marketplace convention: it looks for `<root>/.agents/plugins/marketplace.json` to enumerate plugins, then for each plugin entry looks at `<plugin-path>/.codex-plugin/plugin.json` for the manifest. For skill-tree, `<plugin-path>` is the repo root itself (single-plugin marketplace).

After enabling, restart Codex. The bundled `skills/` directory becomes available: `provision`, `audit`, `diagnose`, `sync`, `fetch`, `check`, `setup`, `skill-analysis`.

## Known caveats

1. **No SessionStart hook surface in Codex.** The "you have N errors in skill-tree" status nudge from Claude Code doesn't have a Codex equivalent yet. Workaround: run `/skill-tree:check` manually after `codex` opens, or wire it into your shell's prompt.

2. **Codex marketplaces are local-path-based today.** Once Codex supports remote marketplaces (analogous to `claude plugin marketplace add <github-url>`), the install simplifies. Until then, clone-then-register is the pattern.

3. **`disable-model-invocation` has a Codex equivalent but it's separate.** Per the [Codex docs § Optional metadata](https://developers.openai.com/codex/skills#optional-metadata), `allow_implicit_invocation: false` in `agents/openai.yaml` is Codex's way of hiding a skill from automatic selection while keeping explicit `$skill` invocation. skill-tree's library uses the Claude-Code-style `disable-model-invocation: true` in SKILL.md frontmatter; Codex will not honor that field directly. For mixed setups, add an `agents/openai.yaml` next to the SKILL.md with the Codex-flavored opt-out.

## How SKILL.md commands find the scripts cross-platform

`CLAUDE_PLUGIN_ROOT` is Claude Code-specific — on Codex (and Gemini CLI) it's undefined, so SKILL.md commands that referenced `uv run ${CLAUDE_PLUGIN_ROOT}/scripts/foo.py` silently failed elsewhere.

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

The plugin manifest exists and is validated by the test suite (`tests/test_codex_plugin.py`). End-to-end install requires Codex to support local-path marketplaces, which the current Codex CLI does. I haven't end-to-end validated every skill on Codex from scratch — `provision`, `audit`, `check`, `sync` should be straightforward; `diagnose` and `fetch` may surface platform-specific quirks. Report any.
