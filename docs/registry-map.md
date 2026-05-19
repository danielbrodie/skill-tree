# Where agent skills actually live

Where skills end up on macOS, by installer. Updated 2026-05-18.

Read by skill-tree's audit / diagnose / install skills at runtime. When one of those needs to answer "where would a Codex plugin's skills live?" or "what's the safe-removal command for vercel-labs/skills?", it pulls the answer from here.

## Registries

| Path | What's there | Who manages it | When it's present |
|---|---|---|---|
| `~/.claude/skills/` | Personal skills installed for Claude Code only | The user (direct install) OR a skill installer like vercel-labs/skills via symlink | Always (Claude Code creates the dir) |
| `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/skills/` | Plugin-bundled skills | Claude Code plugin loader. Updated by `claude plugin install/update` | Whenever a Claude Code plugin is installed |
| `~/Library/Application Support/Claude/local-agent-mode-sessions/skills-plugin/<uuid>/<uuid>/skills/` (macOS) | **Anthropic-bundled skills** that ship with Claude Code — `schedule`, `mcp-builder`, `skill-creator`, `pdf`, `docx`, `pptx`, `xlsx`, `algorithmic-art`, `canvas-design`, `consolidate-memory`, `humanizer`, `return-interview`, `setup-cowork`, etc. (~23 verified 2026-05-18) | Anthropic's Claude Code desktop app, per session | Always on macOS once Claude Code has run at least once |
| **Compiled into the Claude Code binary** at `~/.local/share/claude/versions/<version>` | Built-in skills with no on-disk SKILL.md — e.g. `loop` | Anthropic, shipped inside the executable | Always (visible in available-skills list, but not enumerable by file-system scanners) |
| `~/.agents/skills/` | Multi-agent skill installs | [vercel-labs/skills](https://github.com/vercel-labs/skills) CLI. Lock file at `~/.agents/.skill-lock.json` tracks `skillFolderHash` (GitHub tree SHA) for drift detection | Whenever the user has run `npx skills add ...` |
| `~/.openclaw/skills/` | OpenClaw-resident skills | OpenClaw runtime. Config at `~/.openclaw/openclaw.json`. **Often a stale dev artifact if OpenClaw isn't actually deployed locally.** | Only if OpenClaw is installed (Felix-style personal-AI runtime) |
| `<project>/.claude/skills/` | Per-project provisioned skills | Either skill-tree's `/skill-tree:provision` or hand-curated. Manifest at `<project>/.claude/.skilltree.json` if skill-tree-managed | When a project genuinely needs project-specific skills |
| `~/.codex/plugins/` | Codex CLI plugins (each with own `skills/`) | Codex CLI plugin loader. Config in `~/.codex/config.toml` `[plugins."..."]` blocks | Whenever a Codex plugin is installed |
| `~/.gemini/skills/` or `~/.gemini/extensions/<name>/skills/` | Gemini CLI extensions | Gemini CLI extensions system | Whenever a Gemini extension is installed |

## Installers

| Tool | Verb | What it does | Where it writes |
|---|---|---|---|
| Claude Code plugin marketplace | `claude plugin install <name>@<marketplace>` | Fetches plugin source, copies into `~/.claude/plugins/cache/...` | `~/.claude/plugins/cache/` and updates `~/.claude/plugins/installed_plugins.json` |
| vercel-labs/skills CLI | `npx skills add <repo>` | Clones the skills out of `<repo>`, places them in `~/.agents/skills/`, and creates symlinks into every configured agent's skill dir | `~/.agents/skills/` + symlinks into `~/.claude/skills/`, `~/.codex/skills/`, etc. per the `lastSelectedAgents` config |
| `setup-matt-pocock-skills` (a skill itself) | `/setup-matt-pocock-skills` from inside any agent | Scaffolds an `## Agent skills` block in the repo's `AGENTS.md` or `CLAUDE.md` and `docs/agents/` so downstream skills know the project's issue tracker, label vocabulary, and doc layout | The current repo |
| skill-tree | `/skill-tree:provision`, `/skill-tree:fetch`, `/skill-tree:setup` | Per-project provisioning, GitHub-direct fetch with security checks, global cluster manifest. Source of truth: `~/.claude/skills-library/skill-tree/manifest.json` | `<project>/.claude/skills/`, `~/.claude/skills-library/`, plus the manifest |
| Hand install | `git clone` or direct file copy | Whatever the user does | Anywhere |

## How to remove a skill cleanly (depending on its installer)

| Installer | Removal command |
|---|---|
| vercel-labs/skills | `npx skills remove <name>` (updates `.skill-lock.json`, removes all agent symlinks in one shot) |
| Claude Code plugin marketplace | `claude plugin uninstall <name>@<marketplace>` |
| Codex plugin | `codex plugin uninstall <name>@<marketplace>` |
| Gemini extension | `gemini extensions uninstall <name>` |
| Hand-installed | `rm -rf <skill-dir>` (this is the only case where rm is safe; everything else has a tool that should be used) |
| skill-tree-provisioned (project) | `/skill-tree:sync --apply --prune` after removing the source from the library, OR edit `<project>/.claude/.skilltree.json` and re-run `/skill-tree:sync` |

## Common failure modes

1. **Manifest references a missing skill.** `~/.claude/skills-library/skill-tree/manifest.json` lists `asc-notarization` as a leaf of the `app-store-release` cluster, but `~/.claude/skills/asc-notarization` doesn't exist. The cluster's routing breaks for that path.
2. **Dead symlink.** `~/.claude/skills/X` is a symlink, but the target was removed. Listing the dir shows X, but reading the SKILL.md fails.
3. **Two registries, same skill.** `~/.agents/skills/tdd` (from vercel-labs install) AND `~/.claude/skills/tdd` as a directory (not a symlink). The model sees whichever its loader finds first.
4. **Dev artifact.** `~/.openclaw/skills/` populated by symlinks, but no OpenClaw process is running and the `openclaw.json` shows a `sourcePath` to a local dev repo. Looks like a deployment, isn't.
5. **Stale plugin cache.** `~/.claude/plugins/cache/<plugin>/<version>/` for a version that's no longer the latest. The plugin loader prefers the newer cached version; old versions are dead inventory.
6. **`disable-model-invocation: true` orphan.** A skill is hidden via this frontmatter flag but isn't a leaf of any cluster — so nothing routes to it. Effectively invisible.
7. **Lock-file fan-out drift.** vercel-labs/skills installed a skill last month into 5 agent dirs. The user uninstalled one agent. The lock file still claims the skill is installed there; next `sync` may try to recreate the dir.
8. **Per-project skill never invoked, never archived.** A project has `<project>/.claude/skills/foo/` but the project hasn't been touched in months. Nothing's wrong, but the skill is dead weight.

## What skill-tree's `/skill-tree:audit` should detect

For each registry above, scan for the corresponding failure mode. Surface findings with the safe removal/sync command for the relevant installer. Don't act — let the model walk the user through each finding interactively.

## What skill-tree doesn't try to do

- **Reimplement** any of the installers. It calls out to them.
- **Manage cross-host registries.** If skills live on a separate machine (Felix), skill-tree on the local Mac just reports "this invocation references a skill not present locally; check your remote machines."
- **Be a substitute for `claude plugin`, `codex plugin`, `gemini extensions`, or `npx skills`.** It coordinates them.
