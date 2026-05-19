# Where agent skills live on disk

A per-installer map of where each writes when you install a skill, what the on-disk layout looks like, and the safe removal command. macOS-specific paths. Updated 2026-05-19.

Read by skill-tree's audit and diagnose skills at runtime. When one of those needs to answer "where would a Codex plugin's skills live?" or "what's the safe-removal command for vercel-labs/skills?", it pulls the answer from here.

Every load-path claim cites the corresponding platform's official documentation, the same way `docs/ecosystem-map.md` does. If a row isn't cited, that's a bug.

## Registries (load paths)

| Path | What's there | Who manages it | Source |
|---|---|---|---|
| `~/.claude/skills/` | Personal Claude Code skills. | The user (direct install) or a multi-agent installer like vercel-labs/skills via symlink. | [Claude Code Skills § Where skills live](https://code.claude.com/docs/en/skills#where-skills-live) |
| `<project>/.claude/skills/` | Per-project Claude Code skills. Either skill-tree's `/skill-tree:provision` writes here or you hand-curate. | The user, or skill-tree's provisioner. Manifest at `<project>/.claude/.skilltree.json` if skill-tree-managed. | Same as above. |
| `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/skills/` | Plugin-bundled Claude Code skills, namespaced as `plugin-name:skill-name`. | Claude Code plugin loader. Updated by `claude plugin install/update`. | [Claude Code Plugins reference § Skills](https://code.claude.com/docs/en/plugins-reference#skills) |
| `~/Library/Application Support/Claude/local-agent-mode-sessions/skills-plugin/<uuid>/<uuid>/skills/` (macOS) | **Claude Desktop's** own bundled skills — `humanizer`, `mcp-builder`, `skill-creator`, `pdf`, `pptx`, `xlsx`, `docx`, `algorithmic-art`, `canvas-design`, `consolidate-memory`, `return-interview`, `setup-cowork`, etc. The sibling dirs `Cookies`, `Cache`, `DawnGraphiteCache`, etc. confirm this is the Electron app's own data dir, not Claude-Code-distributed. | The Claude Desktop application. When Claude Code runs inside Desktop, these appear in the available-skills list via the Desktop ↔ Code integration boundary. | Observed via `find` in 2026-05-18 dogfood. The path is not in the [Claude Code Skills doc](https://code.claude.com/docs/en/skills) because the skills are Desktop's, not Code's. |
| Compiled into the Claude Code binary at `~/.local/share/claude/versions/<version>` | Built-in skills with no on-disk SKILL.md — e.g. `loop`, `schedule`, `simplify`, `claude-api`. | Anthropic, shipped inside the executable. Bundled skills referenced under [Bundled skills](https://code.claude.com/docs/en/skills#bundled-skills) in the official docs. | [Claude Code Skills § Bundled skills](https://code.claude.com/docs/en/skills#bundled-skills) |
| `~/.agents/skills/` | Multi-agent skill installs from `npx skills add`. Also natively read by Codex CLI as the user-scope skill dir. | The [vercel-labs/skills](https://github.com/vercel-labs/skills) CLI. Lock file at `~/.agents/.skill-lock.json`. | vercel-labs/skills CLI documentation; cross-confirmed by [Codex skills § Where to save skills](https://developers.openai.com/codex/skills#where-to-save-skills) which lists `$HOME/.agents/skills` as Codex's user-scope path. |
| `$CWD/.agents/skills`, `$CWD/../.agents/skills`, `$REPO_ROOT/.agents/skills` | Per-repo Codex skills. | The user (direct edit), or `skill-installer`. | [Codex skills § Where to save skills](https://developers.openai.com/codex/skills#where-to-save-skills) |
| `/etc/codex/skills` | Admin-scope Codex skills. | System administrator (org-managed installs). | Same as above. |
| `~/.codex/plugins/<plugin>/skills/` | Codex plugin-bundled skills. | The Codex plugin system. Plugins have a `.codex-plugin/plugin.json` manifest. | [Codex Plugins doc](https://developers.openai.com/codex/plugins) |
| `~/.gemini/skills/<skill-name>/SKILL.md` | User-scope Gemini CLI skills. | The user (direct edit) or `gemini extensions install`. | [Gemini CLI Skills](https://geminicli.com/docs/cli/skills/) |
| `<project>/.gemini/skills/<skill-name>/SKILL.md` | Workspace-scope Gemini CLI skills. | The user. | Same as above. |
| `~/.gemini/extensions/<extension>/skills/` | Extension-bundled Gemini CLI skills. | Gemini CLI extension system. Extensions declare via `gemini-extension.json` per [Extension reference](https://geminicli.com/docs/extensions/reference/). | Same as above. |
| `~/.openclaw/skills/` | OpenClaw-resident skills. Often a stale dev artifact if OpenClaw isn't actually deployed locally. | OpenClaw runtime. Config at `~/.openclaw/openclaw.json`. | The OpenClaw plugin in this repo's `openclaw/` subdir. |

## Installers

| Tool | Install command | Where it writes | Removal |
|---|---|---|---|
| Claude Code plugin marketplace | `claude plugin install <name>@<marketplace>` | `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/` and updates `~/.claude/plugins/installed_plugins.json` | `claude plugin uninstall <name>@<marketplace>` |
| Codex CLI plugin system | `codex plugin install <name>@<marketplace>` | `~/.codex/plugins/<plugin>/`, with the manifest at `<plugin>/.codex-plugin/plugin.json` | `codex plugin uninstall <name>@<marketplace>` |
| Gemini CLI extensions | `gemini extensions install <source>` | `~/.gemini/extensions/<name>/` with `gemini-extension.json` at root | `gemini extensions uninstall <name>` |
| vercel-labs/skills CLI | `npx skills add <repo>` | `~/.agents/skills/<name>/` (and symlinks into every agent dir in `~/.agents/.skill-lock.json` `lastSelectedAgents`) | `npx skills remove <name>` |
| skill-installer (Codex-native) | `skill-installer <name>` | Per [Codex skills § Install curated skills](https://developers.openai.com/codex/skills#install-curated-skills-for-local-use) | Per the same doc |
| skill-tree (this project) | `/skill-tree:provision`, `/skill-tree:fetch <url>` | `<project>/.claude/skills/` (provision) or `~/.claude/skills-library/` (fetch) | `/skill-tree:sync --apply --prune` |
| Hand install | `git clone` or direct file copy | Wherever you point it | `rm -rf <skill-dir>` (the only case where `rm` is the safe-removal path; everything else has a tool that should be used instead) |

## How to remove a skill cleanly

Use the installer that wrote the skill, not `rm`:

| If the skill came from | Use |
|---|---|
| `npx skills add` | `npx skills remove <name>` (updates `.skill-lock.json`, removes all symlinks in one shot) |
| `claude plugin install` | `claude plugin uninstall <name>@<marketplace>` |
| `codex plugin install` | `codex plugin uninstall <name>@<marketplace>` |
| `gemini extensions install` | `gemini extensions uninstall <name>` |
| Hand-installed | `rm -rf <skill-dir>` |
| skill-tree provisioner (per-project) | `/skill-tree:sync --apply --prune` after removing the source, OR edit `<project>/.claude/.skilltree.json` and re-run `/skill-tree:sync` |

## Common failure modes

See [`ecosystem-map.md` § "Recognized failure-mode signatures"](./ecosystem-map.md#recognized-failure-mode-signatures) for the full list. The eight summarised here:

1. **Manifest references a missing skill.** `~/.claude/skills-library/skill-tree/manifest.json` lists a skill that isn't on disk. The cluster's routing breaks for that path.
2. **Dead symlink.** `~/.claude/skills/X` is a symlink; the target was removed.
3. **Two registries, same skill.** Same name in `~/.agents/skills/` and `~/.claude/plugins/cache/`. The loader picks whichever it finds first.
4. **Stale plugin cache.** `~/.claude/plugins/cache/<plugin>/<old-version>/` lingers alongside `<plugin>/<new-version>/`. Old dir is dead disk.
5. **`disable-model-invocation: true` orphan.** A skill is hidden via the frontmatter flag but isn't routed via any cluster — effectively invisible.
6. **Lock-file fan-out drift.** vercel-labs/skills installed into 5 agent dirs; the user uninstalled one agent. The lock still claims X is installed there.
7. **Partial-fan-out scoping.** Looks like symlink rot but isn't — see ecosystem-map.md signature #5.
8. **Per-project skill never invoked.** Dead weight; flag for `/skill-tree:archive`.

## What skill-tree doesn't try to do

- **Reimplement** any of the installers. It calls out to them.
- **Manage cross-host registries.** If skills live on a separate machine (a personal-AI deployment running off-machine), skill-tree on the local Mac reports "this invocation references a skill not present locally" but doesn't try to bridge.
- **Be a substitute for `claude plugin`, `codex plugin`, `gemini extensions`, or `npx skills`.** It coordinates them.
