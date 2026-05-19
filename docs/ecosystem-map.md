# How agent skills work

A reference for the mechanics — load paths, frontmatter, progressive disclosure, cache lifecycle, failure modes — across the three first-class skill consumers: Claude Code, OpenAI Codex CLI, and Google Gemini CLI. Read by skill-tree's audit and diagnose skills at runtime, and by the model when reasoning about "why isn't my skill loading?" or "how do I hide this one from the prompt?"

Everything below is sourced. If you find a claim without a citation, that's a bug — file an issue.

## What a skill is

A skill is a `SKILL.md` file with YAML frontmatter, in a directory whose name is the skill name. The frontmatter has at least a `name` and a `description`; the body is the prompt content loaded when the skill fires. All three consumer platforms converge on this shape. The differences are in load paths and which frontmatter fields are honored.

Sources:
- Claude Code: [code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills)
- Codex CLI: [developers.openai.com/codex/skills](https://developers.openai.com/codex/skills)
- Gemini CLI: [geminicli.com/docs/cli/skills](https://geminicli.com/docs/cli/skills/)

## Load paths per platform

Each platform searches a fixed list of locations in a fixed priority order.

### Claude Code

Per the [Skills doc](https://code.claude.com/docs/en/skills):

| Scope | Path | Precedence |
|---|---|---|
| Enterprise | Via managed settings (see [settings docs](https://code.claude.com/docs/en/settings#settings-files)) | Highest |
| Personal | `~/.claude/skills/<skill-name>/SKILL.md` | Next |
| Project | `<project>/.claude/skills/<skill-name>/SKILL.md` | Next |
| Plugin | `<plugin>/skills/<skill-name>/SKILL.md` (inside the plugin's cache dir under `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`) | Namespaced as `plugin-name:skill-name`, so no conflicts |

`~/.claude/skills/` and `<project>/.claude/skills/` are watched for changes — adding, editing, or removing a skill there takes effect within the current session without restarting. *Source: [Skills § Live change detection](https://code.claude.com/docs/en/skills#live-change-detection).*

Plugin skills are namespaced (`/plugin-name:skill-name`) and not hot-reloaded; they require `/reload-plugins` or a Claude Code restart. *Source: [Plugins reference § Skills](https://code.claude.com/docs/en/plugins-reference#skills).*

### Codex CLI

Per [developers.openai.com/codex/skills](https://developers.openai.com/codex/skills#where-to-save-skills):

| Scope | Path |
|---|---|
| Repository | `$CWD/.agents/skills`, `$CWD/../.agents/skills`, `$REPO_ROOT/.agents/skills` |
| User | `$HOME/.agents/skills` |
| Admin | `/etc/codex/skills` |
| System | Bundled with Codex by OpenAI |

Codex reads skills from all four levels. Note `$HOME/.agents/skills` — that's the same directory the [vercel-labs/skills](https://github.com/vercel-labs/skills) CLI populates for its multi-agent fan-out, so a single `npx skills add` install is readable by Codex natively.

### Gemini CLI

Per [geminicli.com/docs/cli/skills](https://geminicli.com/docs/cli/skills/):

| Scope | Path | Precedence |
|---|---|---|
| Built-in | Bundled with Gemini CLI | Highest |
| Extension | `<extension>/skills/<skill-name>/SKILL.md` (declared via [gemini-extension.json](https://geminicli.com/docs/extensions/reference/)) | Next |
| User | `~/.gemini/skills/<skill-name>/SKILL.md` | Next |
| Workspace | `<project>/.gemini/skills/<skill-name>/SKILL.md` | Last |

## Frontmatter that controls progressive disclosure

The shared problem: once you have more than a few dozen skills, listing every description in the prelude on every turn becomes noise. Each platform offers different levers.

### Claude Code

The full frontmatter reference is at [Skills § Frontmatter reference](https://code.claude.com/docs/en/skills#frontmatter-reference). The fields that matter for progressive disclosure:

- **`disable-model-invocation: true`** — the skill description is *not* listed in the prelude; only the user can invoke it via `/skill-name`. Claude can't load it automatically.
- **`user-invocable: false`** — the description IS listed in the prelude (so Claude can decide to load it), but `/skill-name` is hidden from the user's slash menu. For background-knowledge skills.
- **`allowed-tools`** — pre-approves tools while this skill is active, avoiding per-use prompts.
- **`paths`** — glob patterns that gate auto-invocation by file paths in scope.
- **`context: fork`** — the skill runs in a forked subagent with a clean context window.

Plus the [`skillOverrides` setting](https://code.claude.com/docs/en/skills#override-skill-visibility-from-settings) lets you control visibility from `settings.json` without editing the skill's own frontmatter. Four states: `"on"`, `"name-only"`, `"user-invocable-only"`, `"off"`.

There's a per-context budget for skill listings — Claude Code caps the total at ~1% of the model's context window. When it overflows, descriptions of least-recently-invoked skills are dropped first. Configurable via `skillListingBudgetFraction`. *Source: [Skills § Skill descriptions are cut short](https://code.claude.com/docs/en/skills#skill-descriptions-are-cut-short).*

### Codex CLI

The equivalent of `disable-model-invocation` is `allow_implicit_invocation: false` in `agents/openai.yaml` — explicit `$skill` invocation still works; implicit Claude-driven invocation is blocked. *Source: [Codex skills § Optional metadata](https://developers.openai.com/codex/skills#optional-metadata).*

Disable a skill entirely without uninstalling it by editing `~/.codex/config.toml` with `[[skills.config]]` entries setting `enabled = false`. *Source: [Codex skills § Enable or disable skills](https://developers.openai.com/codex/skills#enable-or-disable-skills).*

### Gemini CLI

Skills are described in [geminicli.com/docs/cli/skills](https://geminicli.com/docs/cli/skills/). The body and folder structure of `SKILL.md` is added to the conversation history when the skill is loaded; the skill's directory is added to the agent's allowed file paths so the skill can read bundled assets. The frontmatter `description` is the trigger signal — Gemini chooses based on it.

## Plugin cache lifecycle (Claude Code)

The plugin cache at `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/` is where `claude plugin install` writes a plugin's contents — including its `skills/` directory. The full lifecycle is documented at [Plugins reference § CLI commands](https://code.claude.com/docs/en/plugins-reference#cli-commands).

### `/reload-plugins`

What it does, per the [CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md):

- Originally added "to activate pending plugin changes without restarting."
- Later "improved to pick up plugin-provided skills without requiring a restart."

What it does NOT do:

- Re-fetch the marketplace. To get a new plugin version, run `claude plugin marketplace update <marketplace>` first, then `claude plugin update <plugin>@<marketplace>`, then either `/reload-plugins` or restart.
- Refresh skills outside the plugin tier. Personal / project skills hot-reload separately; built-ins and Desktop-provided skills (see Recognized failure modes below) don't refresh via `/reload-plugins`.

Two open issues that exercise the limits:

- [anthropics/claude-code#35641](https://github.com/anthropics/claude-code/issues/35641) — `/reload-plugins` reports success but skills from newly-installed marketplace plugins don't appear in the available-skills list until a full session restart.
- [anthropics/claude-code#57515](https://github.com/anthropics/claude-code/issues/57515) — skill descriptions silently dropped from the available-skills system reminder for some fraction of a plugin's skills at session start.

## Recognized failure-mode signatures

The model should recognize these patterns when running `/skill-tree:audit` or `/skill-tree:diagnose`:

1. **vercel-labs fan-out includes agents not installed locally.** `lastSelectedAgents` in `~/.agents/.skill-lock.json` lists agents (`cursor`, `amp`, `warp`, etc.) whose directories don't exist. Each sync wastes effort on unreachable targets. Fix: trim with `npx skills config`.

2. **Plugin cache staleness.** Two related sub-cases, both surface as "I shipped a new version and the available-skills list doesn't show it":

   **2a. Old version dirs left in the cache.** `~/.claude/plugins/cache/<plugin>/<old-version>/` and `<plugin>/<newer-version>/` both exist. The plugin loader uses the newest; the old dir is dead disk. Fix: `rm -rf` the older versions (`claude plugin gc` doesn't exist as a subcommand — verified 2026-05-19 against `claude plugin --help`).

   **2b. The marketplace was never re-fetched.** `/reload-plugins` reloads existing on-disk plugin state into the running process; it does NOT contact the marketplace to check for newer versions. If you ship a new version and the friend's cache still only has the old version dir, they ran `/reload-plugins` against state that's still old on disk. Fix: `claude plugin marketplace update <marketplace>`, then `claude plugin update <plugin>@<marketplace>`, then either `/reload-plugins` or restart. See § "Plugin cache lifecycle" below for the full lifecycle.

3. **Manifest-vs-filesystem drift in skill-tree.** `~/.claude/skills-library/skill-tree/manifest.json` references a skill that's not on disk. Fix: install via the right installer, or remove the manifest reference.

4. **Symlink rot.** `~/.claude/skills/X -> ~/.agents/skills/X` but the target was removed. Re-install via `npx skills add <package> --skill X --agent claude-code -g -y`, or remove the dead symlink. `~/.claude/skills/` is re-scanned each turn (per [Skills § Live change detection](https://code.claude.com/docs/en/skills#live-change-detection)) — no restart needed once the symlink exists.

   **`npx skills sync` doesn't exist** (verified 2026-05-19 against `npx skills --help`). The available verbs are `add`, `remove`, `list`, `find`, `update`, `experimental_install` (project skills from `skills-lock.json`), and `experimental_sync` (node_modules → agent dirs). When doc-text says "re-sync the installer," for `npx skills` it means `npx skills update <package>` or `npx skills add <package> --skill X --agent Y`.

5. **Partial-fan-out scoping (looks like symlink rot, isn't).** `~/.agents/skills/X/SKILL.md` exists; `~/.claude/skills/X` does not exist. If `npx skills list -g` shows `X` was scoped to only a non-Claude-Code agent at install time, the symlink was never created — there's nothing rotted. Extend the agent list: `npx skills add <package> --skill X --agent claude-code -g -y`.

6. **`disable-model-invocation: true` orphan.** A skill is hidden via the frontmatter flag but isn't referenced in any cluster or routed via the `Skill` tool. It's effectively invisible. Fix: add to a cluster, or remove the flag.

7. **Parallel registries with version skew.** `~/.agents/skills/foo` is at one version, `~/.claude/plugins/cache/.../foo/` is older. The model loads whichever the resolver finds first. Fix: update the older one or uninstall it.

8. **Dead inventory.** A skill is installed but never invoked over a long window. Not strictly a failure, but worth flagging for `/skill-tree:archive`.

9. **`/reload-plugins` only refreshes the plugin tier.** After running it, Claude Desktop-provided skills (at `~/Library/Application Support/Claude/local-agent-mode-sessions/skills-plugin/<uuid>/<uuid>/skills/`) can disappear from the available-skills list. The sibling directories `Cookies`, `Cache`, `DawnGraphiteCache` in that path confirm it's the Electron app's own data dir, not Claude-Code-distributed. Fix: restart Claude Code, or read the SKILL.md directly with the `Read` tool.

## Progressive-disclosure recommendations

Drawn from the platform docs and the failure modes above:

- **Past ~50 skills, hide most of them.** Per the [Skill descriptions are cut short](https://code.claude.com/docs/en/skills#skill-descriptions-are-cut-short) section, Claude Code's prelude budget is ~1% of context; once you overflow it, least-recently-invoked descriptions drop. Use `disable-model-invocation: true` or `skillOverrides: "name-only"` to keep the prelude lean.
- **Use project scope for project-specific skills.** Putting skills in `<project>/.claude/skills/` instead of `~/.claude/skills/` keeps them out of every-project preludes. Same applies to `<project>/.agents/skills/` for Codex and `<project>/.gemini/skills/` for Gemini.
- **Plugin marketplaces over hand-install** when both are available. Marketplaces give you uninstall paths and version tracking; hand-installs lose provenance.
- **One PreToolUse gate + one PostToolUse formatter** is the durable hook pattern. Heavier hook setups get noisy fast.

## What this doc isn't

Not a directory of skill repos. Discovering new skills to install is a separate problem — better served by the [Skills](https://code.claude.com/docs/en/skills) doc's curated examples, the [`claude plugin marketplace`](https://code.claude.com/docs/en/plugins-reference#cli-commands) browse interface, [Anthropic's official marketplace](https://github.com/anthropics/claude-plugins-official), or `claude-code-setup`'s recommendation skill. This doc covers how skills work once you have them.
