# skill-tree

Cross-platform skill clustering plugin. Repo at `~/Projects/skill-tree/`.

## Architecture

- **Claude Code plugin** at repo root (`.claude-plugin/`, `skills/`, `hooks/`)
- **Gemini extension** (`gemini-extension.json`, `GEMINI.md`, `commands/*.toml`). The `name` field in the manifest must match the directory name.
- **OpenClaw plugin** in `openclaw/` subdirectory (separate package with its own scripts copy)
- **Codex CLI** uses scripts directly with `--codex` flag
- Python scripts in `scripts/` are the shared engine — all platforms invoke them via `uv run`

## Platform path variables

Each platform has its own variable for referencing plugin-bundled files:

- **Claude Code:** `${CLAUDE_PLUGIN_ROOT}` — required in skills, hooks, MCP configs. Plugins are copied to `~/.claude/plugins/cache/` so relative paths break.
- **Gemini CLI:** `${extensionPath}` — used in TOML command `prompt` fields and MCP configs.
- **OpenClaw:** `{baseDir}` — interpolated in SKILL.md content. Refers to the skill directory, not plugin root. Scripts are at `{baseDir}/../scripts/`.

Never use bare relative paths like `uv run scripts/foo.py` — they only work during development.

## Testing

```bash
uv run --with pytest --with scikit-learn --with pyyaml pytest tests/ -v
```

176+ tests. Key test files:
- `test_plugin_structure.py` — validates `${CLAUDE_PLUGIN_ROOT}` usage, manifest metadata
- `test_gemini_extension.py` — validates TOML commands, `${extensionPath}`, skill parity
- `test_openclaw_plugin.py` — validates OpenClaw package, `{baseDir}` paths, same-directory compat
- `test_scan_additive.py` — additive merge preserves existing manifest
- `test_status.py` — combined health check output
- `test_sync.py` — cluster file generation + Codex YAML
- `test_codex.py` — `agents/openai.yaml` generation

## Commands

Three slash commands across all platforms: `/check`, `/setup`, `/fetch`.

Command names were chosen to avoid collision with Claude Code built-ins (`init`, `check`, `sync`, `list` all collide). Skills live in `skills/<name>/SKILL.md` — not `commands/*.md` (which is legacy per Claude Code docs).

## OpenClaw differences

- Single directory (`~/.openclaw/skills/`) for both routers and leaves
- Leaf hiding via `disable-model-invocation: true` only (no directory separation)
- Scripts are copied into `openclaw/scripts/` (can't reference parent directory after plugin install)
- OpenClaw skills use `{baseDir}/../scripts/` to reach the bundled scripts

## Key design decisions

- Clustering is done by the model, not an algorithm. `scan.py` collects descriptions; the `/setup` skill instructs the model to group them semantically and write the manifest. No TF-IDF, no scikit-learn, no threshold.
- `scan.py` reports which skills are new (not in manifest) vs already tracked.
- `manifest.json` is the source of truth. Cluster SKILL.md files are generated artifacts. Never edit clusters directly.
- Fetched skills are sandboxed (`disable-model-invocation: true`) until explicitly added to a cluster.

## Operational lessons

- **`scripts/sync.py` defaults `--skills-dir` to `~/.claude/skills/` — always pass it explicitly.** Running `uv run sync.py` with no `--skills-dir` materializes ALL cluster routers there, clobbering the project-scoped (`~/vault/.claude/skills/`) and plugin-scoped (`~/Projects/skills/plugins/*/skills/`) setups — a bare run once dumped 24 routers globally and blew up token usage until they were `rm`'d back to the intended 6. For per-cluster edits (add a leaf, set `disable-model-invocation: true`, set a routing hint), edit `manifest.json` directly and hand-write the affected SKILL.md — don't reach for sync.py at all.
- **Read the platform docs before building, not after.** Copying other plugins' patterns instead of the official reference produced bare relative paths, missing manifest metadata (author/license/repository/keywords), legacy `commands/*.md` instead of `skills/<name>/SKILL.md`, and a fabricated `user-invocable: true` field that isn't real. Fetch `https://code.claude.com/docs/llms.txt` for the index, then read the reference page for the component you're building.
- **User-facing docs use the short command name.** Autocomplete fires on the command (`/check`), not the plugin-prefixed form (`/skill-tree:check`) — README and examples should show `/check`.

## Git

- Git email: `11337994+danielbrodie@users.noreply.github.com` (NOT `daniel@users...`)
- Branch protection enabled on main — no force pushes
- Never put internal names (agent names, private infrastructure) in public commits, PRs, or branches
