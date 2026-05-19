# The AI-skill ecosystem, mapped

Notes on the agent platforms, skill packagers, installers, and failure modes I've actually run into. Read by the catalog / diagnose / install skills at runtime. Last refreshed: 2026-05-18.

Companion to [`registry-map.md`](./registry-map.md), which covers where skills live on a single machine. This doc covers what exists in the wider world. PRs welcome.

## Agent platforms that consume skills

| Platform | Skill load path | Skill format | Notable |
|---|---|---|---|
| **Anthropic Claude Code** | `~/.claude/skills/`, `~/.claude/plugins/cache/<mp>/<plugin>/<version>/skills/`, **AND** `~/Library/Application Support/Claude/local-agent-mode-sessions/skills-plugin/<uuid>/<uuid>/skills/` for Anthropic-bundled skills (macOS) | SKILL.md w/ YAML frontmatter (`name`, `description`, optional `disable-model-invocation: true`). Some skills are compiled directly into the Claude Code binary at `~/.local/share/claude/versions/<version>` — e.g. `loop` — and have no SKILL.md anywhere on disk; file-system scanners can't enumerate them. | Plugin marketplace is the primary distribution path. |
| **OpenAI Codex CLI** | `~/.codex/skills/`, `~/.codex/plugins/<plugin>/skills/` | SKILL.md w/ YAML frontmatter. Plugin manifest at `.codex-plugin/plugin.json` | New plugin system. Marketplaces are local-path-only as of mid-2026. |
| **Google Gemini CLI** | `~/.gemini/extensions/<ext>/skills/` (or `~/.gemini/skills/`) | SKILL.md + extension manifest in `gemini-extension.json` + commands as `.toml` | Uses `${extensionPath}` in command TOML for path templating. |
| **Cursor** | Cursor Rules + skills via vercel-labs/skills fan-out | `.cursorrules` for legacy, SKILL.md for newer | Multi-format. The vercel-labs installer normalizes. |
| **Cline** | VSCode extension w/ rules dir | rules.md style | Older convention. |
| **Amp** | Sourcegraph's AI agent | proprietary install path | Targeted by vercel-labs/skills fan-out. |
| **Antigravity** | Google's agent platform | proprietary | Targeted by vercel-labs/skills fan-out. |
| **GitHub Copilot** | `.github/copilot-instructions.md` | Markdown, no frontmatter | Repo-scoped. Doesn't really have "skills" in the same sense. |
| **Warp** | Warp Drive workflows | YAML | Tangentially skill-like. |
| **Opencode** | Open-source agent | SKILL.md | Targeted by vercel-labs/skills fan-out. |
| **Firebender** | Android-focused agent | proprietary | Targeted by vercel-labs/skills fan-out. |
| **DeepAgents** | LangChain ecosystem | LangGraph-style | Out of standard skill format. |
| **Kimi-CLI** | Moonshot's CLI agent | similar to Claude Code | Targeted by vercel-labs/skills fan-out. |
| **OpenClaw** | `~/.openclaw/skills/` | SKILL.md + same-directory routers + leaves (no separate library dir) | Personal-AI runtime, often Felix-style remote-host deployment. |

## Skill packager repos

| Repo | Maintainer | Focus | Install |
|---|---|---|---|
| [obra/superpowers](https://github.com/obra/superpowers) | Jesse Vincent | Methodology skills: TDD red-green-refactor, brainstorming, subagent-driven development, finishing branches, systematic debugging. | `claude plugin install superpowers@claude-plugins-official` |
| [mattpocock/skills](https://github.com/mattpocock/skills) | Matt Pocock | Workflow skills: `to-issues`, `to-prd`, `triage`, `diagnose`, `tdd`, `improve-codebase-architecture`, `zoom-out`, `caveman`, `prototype`, `setup-matt-pocock-skills`. | `npx skills add mattpocock/skills` |
| [vercel-labs/skills](https://github.com/vercel-labs/skills) | Vercel Labs | Both a skill repo and the multi-agent installer CLI. Skills plus a small set of web-design-specific extras. | `npx skills add ...` |
| [rudrankriyam/asc-skills](https://github.com/rudrankriyam/asc-skills) | Rudrank Riyam | App Store Connect CLI workflow skills: ~19 `asc-*` skills covering release flow, TestFlight, screenshots, pricing, etc. | `npx skills add rudrankriyam/asc-skills` |
| [mvanhorn/printing-press-library](https://github.com/mvanhorn/printing-press-library) | Michael VanHorn | "Printing Press" CLI generators wrapped as skills: `pp-linear`, `pp-sentry`, `pp-shopify`, `pp-granola`. Each is an API → CLI → skill pipeline. | `npx skills add mvanhorn/printing-press-library` |
| [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) | Anthropic | Curated plugin directory: `superpowers`, `code-review`, `code-simplifier`, `frontend-design`, `skill-creator`, LSP plugins, more. | `claude plugin install <name>@claude-plugins-official` |
| [dimillian/skills](https://github.com/dimillian/skills) | Thomas Ricouard | iOS/Apple-focused agent skills. | `npx skills add dimillian/skills` |
| [charleswiltgen/axiom](https://github.com/charleswiltgen/axiom) | Charles Wiltgen | Axiom-specific developer skills. | `npx skills add charleswiltgen/axiom` |
| [gracefullight/stock-checker](https://github.com/gracefullight/stock-checker) | gracefullight | Stock-checking skill. | `npx skills add gracefullight/stock-checker` |
| [danielbrodie/skill-tree](https://github.com/danielbrodie/skill-tree) | Daniel Brodie | This repo. Meta: a tool for managing skills across agents. | See README. |
| [jscraik/Agent-Skills](https://github.com/jscraik/Agent-Skills) | jscraik | Large general-purpose agent-skill collection. | Hand-install or `npx skills add jscraik/Agent-Skills` |
| [rjmurillo/ai-agents](https://github.com/rjmurillo/ai-agents) | rjmurillo | Another large agent-skills monorepo. | `npx skills add rjmurillo/ai-agents` |
| [nexu-io/open-design](https://github.com/nexu-io/open-design) | nexu-io | Open-source local-first alternative to Anthropic's Claude Design. Shipped within days of Claude Design's launch ([r/PromptEngineering 2026-05-13](https://www.reddit.com/r/PromptEngineering/comments/1t6ssn5/claude_design_is_cool_but_the_opensource/)). | Hand-install |

### Claude Code workflow plugins

A category of opinionated Claude Code plugins that bundle skills + hooks + multi-agent orchestration, distinct from atomic-skill packagers above. Surfaced in the May 2026 survey.

| Plugin | Source | Focus | Install |
|---|---|---|---|
| Nelson | MIT, [r/ClaudeCode 2026-05-08](https://www.reddit.com/r/ClaudeCode/comments/1t7l60y/nelson_v223_shipped_and_a_benchmark_i_built/) | Multi-agent coordination using a Royal Navy metaphor (admiral/captains/ships/crew). Author ships a benchmark comparing 13 agent/harness/skill setups on a discrete-event simulation task. | See Reddit post for repo |
| [itsribbZ/Godspeed](https://github.com/itsribbZ/Godspeed) | MIT, [r/ClaudeAI 2026-05-12](https://www.reddit.com/r/ClaudeAI/) | Plugin adding S0-S5 tier routing + multi-agent orchestration. One-command install, 17 skills bundled. | `claude plugin install godspeed@itsribbZ/Godspeed` (or repo-direct) |
| AI Sorcery | [r/ClaudeWorkflows 2026-05-09](https://www.reddit.com/r/ClaudeWorkflows/comments/1t5w8zt/workflow_ai_sorcery_a_collection_of_claude_code/) | Claude Code skills bundle: VM sandboxing, git hooks, iterative-dev workflows. | See Reddit post |
| OpenSwarm | [r/AISEOInsider 2026-05-12](https://www.reddit.com/r/AISEOInsider/comments/1tb7ul7/i_used_openswarm_ai_for_parallel_workflows/) | Parallel workflows across multiple AI agents. | See Reddit post |
| Glyphh AI | [r/ClaudeCode 2026-05-11](https://www.reddit.com/r/ClaudeCode/comments/1t3zf7y/i_built_a_workspace_with_3500_mcp_apps_multimodel/) | Workspace combining MCP apps, multi-model AI, skills, automation, and dev tooling. | See Reddit post |

## Installers

| Installer | Scope | Strength | Removal |
|---|---|---|---|
| **Anthropic Claude Code plugin marketplace** (`claude plugin`) | Claude Code only | Official, curated, atomic install/uninstall. Maintains `~/.claude/plugins/installed_plugins.json`. | `claude plugin uninstall <name>@<marketplace>` |
| **OpenAI Codex CLI plugin system** (`codex plugin`) | Codex only | Similar to Claude Code. Local marketplaces today; remote may come. | `codex plugin uninstall <name>@<marketplace>` |
| **Google Gemini CLI extensions** (`gemini extensions`) | Gemini only | Built-in extension manager. | `gemini extensions uninstall <name>` |
| **vercel-labs/skills CLI** (`npx skills`) | Multi-agent fan-out | Installs one repo into N agents' skill dirs via symlinks. Lock file at `~/.agents/.skill-lock.json` tracks `skillFolderHash`. Configurable `lastSelectedAgents`. As of May 2026 the de-facto standard for multi-agent installs. | `npx skills remove <name>` |
| **[iflytek/skillhub](https://github.com/iflytek/skillhub)** (`skillhub` CLI) | Enterprise on-premise | Self-hosted, open-source agent skill registry for enterprises. Publish & version skill packages, govern with RBAC and audit logs, deploy on-premise with Docker/Kubernetes. Fills the "Enterprise / private skill repos" gap. Built by iFlytek (Chinese AI company). `skillhub install <name> --agent codex`. | `skillhub uninstall <name>` |
| **Verified Skill** (in-development) | Multi-platform (claimed 49) with security | Security checks + evals + package manager. Built during [Anthropic's Opus 4.7 hackathon, pushed publicly the week of 2026-05-15](https://www.reddit.com/r/ClaudeAI/comments/1srg22m/got_into_anthropics_opus_47_hackathon_pushing/). First installer with first-class security review baked in. Track for production-readiness. | TBD |
| **`sx`** (community installer) | Multi-agent versioned config | Versioned package management for AI Skills, Hooks, and Configurations across teams and AI clients. Smaller footprint than vercel-labs but explicit team-config support ([r/ClaudeWorkflows 2026-05-15](https://www.reddit.com/r/ClaudeWorkflows/comments/1te87t5/workflow_using_sx_for_versioned_package/)). | See post |
| **Matt Pocock bootstrap** (`/setup-matt-pocock-skills` from within an agent) | Per-repo | Scaffolds `AGENTS.md`/`CLAUDE.md` agent-skills block + `docs/agents/` so downstream skills know the repo's conventions. | Not really "uninstalled"; edit the repo's AGENTS.md directly. |
| **skill-tree** (`/skill-tree:provision`) | Per-project | AI-categorized provisioning into `<project>/.claude/skills/`. Manifest at `.claude/.skilltree.json`. | `/skill-tree:sync --apply --prune` |
| **Hand install** (`git clone`) | Anything | Maximum flexibility. | `rm -rf <dir>` |

## Awesome-list aggregators (discovery tier)

How new users find skills. Not packagers themselves — curated indexes of who's publishing what. Worth tracking because they're typically how skill-tree users will discover candidate skill repos.

| Aggregator | Focus |
|---|---|
| [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills) | General-purpose awesome-list for agent skills across platforms. |
| [GetBindu/awesome-claude-code-and-skills](https://github.com/GetBindu/awesome-claude-code-and-skills) | Claude Code-focused curated list of skills + best practices. |

## Skill evaluation

Public benchmarks for individual skill quality are rare. [Nelson v2.2.3](https://www.reddit.com/r/ClaudeCode/comments/1t7l60y/nelson_v223_shipped_and_a_benchmark_i_built/) (2026-05-08) shipped a comparison of 13 agent/harness/skill setups on a discrete-event simulation task — the most concrete benchmark I've seen so far. `docs/measurement.md` defines a `Reach@catalog` metric for skill-tree itself; it measures the catalog (did the right skill make it into the prelude?), not the skill (was the skill any good?).

## Frontmatter conventions

```yaml
---
name: my-skill                              # canonical identifier
description: USE WHEN ... <use case>        # one-line trigger description for the model
disable-model-invocation: true              # optional: hide from prompt, only loaded via Read
routingHint: "Use this when X, not Y"       # used by cluster routers, in the manifest
---
```

Key facts the model should know:
- `disable-model-invocation: true` is the **only** mechanism agents currently agree on for hiding a skill from the prompt while keeping it loadable on demand.
- Cluster routing in skill-tree's manifest depends on this — the cluster router is visible, the leaves are hidden.
- Some installers (like vercel-labs/skills) leave the frontmatter alone; the user has to add `disable-model-invocation` manually if they want progressive disclosure.

## Recognized failure-mode signatures

The model should recognize these patterns when running `/skill-tree:audit` or `/skill-tree:diagnose`:

1. **vercel-labs fan-out includes agents not installed locally.** `lastSelectedAgents` in `~/.agents/.skill-lock.json` lists 13 agents but `~/.cursor`, `~/.amp`, `~/.warp` are absent. Each sync run wastes effort on unreachable targets. Fix: trim the agent list with `npx skills config`.

2. **OpenClaw dev artifact.** `~/.openclaw/openclaw.json` references a `sourcePath` to a local development repo (not a real install) and no OpenClaw process is running. Fix: `rm -rf ~/.openclaw`.

3. **Manifest-vs-filesystem drift in skill-tree.** `~/.claude/skills-library/skill-tree/manifest.json` references a skill that's not on disk. Fix: install the missing skill via the appropriate installer, or remove the manifest reference.

4. **Plugin cache staleness.** `~/.claude/plugins/cache/<plugin>/<old-version>/` and `<plugin>/<newer-version>/` both exist. Fix: manually `rm -rf` the old version dirs (`claude plugin gc` doesn't currently exist as a CLI subcommand — verified 2026-05-18). The plugin loader uses the newest version automatically; old dirs are dead disk.

   **Sub-finding (2026-05-18):** `/reload-plugins` does **not** re-fetch from the marketplace. It reloads existing on-disk plugin state into the running CC process. To actually pull a new plugin version when the marketplace has updated, run:
   ```
   claude plugin marketplace update <marketplace>
   claude plugin update <plugin>@<marketplace>
   ```
   Then restart Claude Code (the loader caches plugin state at process start; `/reload-plugins` post-update reloads the new cache, but the available-skills list won't refresh until restart). Common symptom: user pushes a new version, runs `/reload-plugins`, and the new skill never appears in the available-skills list — that's because the marketplace fetch never happened.

   **Sub-finding (2026-05-18): three independent skill sources, only one refreshed by `/reload-plugins`.** Reading the leaked Claude Code source clarifies the structure:

   1. **CLI bundled skills** — compiled into the Claude Code binary, defined under `src/skills/bundled/`: `loop`, `schedule` (`scheduleRemoteAgents`), `simplify`, `claude-api`, `debug`, `batch`, `keybindings`, `remember`, `claudeInChrome`, `skillify`, `stuck`, `updateConfig`, `verify`, `loremIpsum`. The source's "bundled" term means *compiled in*. Registered via `BundledSkillDefinition` in `src/skills/bundledSkills.ts`. Reference files extract to `getClaudeTempDir()/bundled-skills/<version>/<nonce>/` on first invocation. `/reload-plugins` doesn't touch these.

   2. **CLI plugin skills** — `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/skills/`. Refreshed by `/reload-plugins` via `refreshActivePlugins()` in `src/utils/plugins/refresh.ts`. That function explicitly scopes its `setAppState` to the `plugins` sub-tree (`commands: pluginCommands` only) and calls `clearAllCaches()` for plugin caches. Known bugs: [anthropics/claude-code#35641](https://github.com/anthropics/claude-code/issues/35641) (refresh reports success but new plugin skills don't appear until restart); [anthropics/claude-code#57515](https://github.com/anthropics/claude-code/issues/57515) (skill descriptions silently dropped from the system reminder for a fraction of a plugin's skills).

   3. **Claude Desktop local-agent-mode skills** — `~/Library/Application Support/Claude/local-agent-mode-sessions/skills-plugin/<uuid>/<uuid>/skills/`. **This is Claude Desktop's artifact, not Claude Code's.** The dir is sibling to the Electron app's `Cookies`, `Cache`, `DawnGraphiteCache`, etc. The leaked Claude Code source doesn't reference this path. Contains `humanizer`, `pdf`, `pptx`, `xlsx`, `docx`, `mcp-builder`, `skill-creator`, `algorithmic-art`, `canvas-design`, `consolidate-memory`, `nano-banana-design-prompting`, `obsidian-crosslink`, `return-interview`, `setup-cowork`, `swiftui-pro`, etc. When Claude Code runs inside Claude Desktop, these skills appear in the session's available-skills list via some Desktop ↔ Code integration boundary.

   **Observed behavior:** after `/reload-plugins`, the source #3 set was absent from the available-skills list and `Skill(skill="humanizer")` returned `Unknown skill`, while source #1 (`loop`, `schedule`, etc.) and the surviving source #2 plugin skills continued to work. Best guess: the available-skills list reconstruction triggered by `refreshActivePlugins` doesn't re-merge in the Claude Desktop-provided skills, even though the underlying files on disk are untouched. Practical impact: if a Desktop-provided skill disappears after `/reload-plugins`, restart Claude Code; or read the `SKILL.md` from `~/Library/Application Support/Claude/local-agent-mode-sessions/skills-plugin/<uuid>/<uuid>/skills/<name>/SKILL.md` directly and follow it manually.

5. **Symlink rot.** `~/.claude/skills/X -> ~/.agents/skills/X` but the target was removed. Fix: re-install via `npx skills add <package> --skill X --agent claude-code -g -y`, or remove the dead symlink. Note: `~/.claude/skills/` is re-scanned each turn by the host agent (verified 2026-05-18) — no Claude Code restart needed for symlink fixes to become visible. The plugin cache (`~/.claude/plugins/cache/...`) is the registry that needs restart.

   **Important: there is no `npx skills sync` command (verified 2026-05-18 against vercel-labs/skills CLI).** The available verbs are `add`, `remove`, `list`, `find`, `update`, `experimental_install` (project skills from `skills-lock.json`), and `experimental_sync` (node_modules → agent dirs). When the doc-text says "re-sync the installer," for `npx skills` that means either `npx skills update <package>` (refresh from upstream) or `npx skills add <package> --skill X --agent Y` (re-create one specific symlink). Don't tell users to run a command that doesn't exist.

5a. **Partial-fan-out scoping (looks like symlink rot, isn't).** `~/.agents/skills/X/SKILL.md` exists; `~/.claude/skills/X` does not exist. This can look like #5 symlink rot, but if the entry in `~/.agents/.skill-lock.json` shows `X` was installed targeting only a specific agent list (e.g., `Antigravity` only, not `Claude Code`), then the symlink was never created — there's nothing rotted. The fix is to extend the target-agent list: `npx skills add <package> --skill X --agent claude-code -g -y`. Distinguish from #5 by checking `npx skills list -g` and seeing which agents are listed for that skill.

6. **Cluster orphan.** A skill has `disable-model-invocation: true` but isn't referenced in any cluster. It's effectively invisible. Fix: add to a cluster in the manifest, or remove the flag.

7. **Parallel registries with version skew.** `~/.agents/skills/foo` is at v1.2, `~/.claude/plugins/cache/.../foo/v1.0/` is older. The user might be invoking the wrong one. Fix: update the older one or uninstall it.

8. **Dead inventory.** A skill is installed but never invoked over a long window. Not a failure per se but worth flagging for `/skill-tree:archive`.

9. **Cross-host invocation residue.** Session logs reference a skill (`obsidian-vault`) not in any local registry. Fix: the user may be invoking a Felix-style remote agent; either install locally or document the bridge.

## Patterns that tend to work

Things I've seen consistently across Anthropic posts, community write-ups, and my own catalog tinkering:

- **Progressive disclosure beats catalog overflow.** Past ~50 skills, descriptions compete for attention. Hide via `disable-model-invocation: true`; route via cluster or `Skill` tool invocation.
- **Per-project beats global for distinctive needs; global-popular beats per-project for the workflow base layer.** See `docs/adr/0002-hybrid-global-base-plus-per-project-tail.md` for the validation.
- **Don't bundle every skill into every project.** The "iPhone skills in a JavaScript project" anti-pattern.
- **CLAUDE.md works best short, path-scoped, and per-project** per Anthropic's best-practices post.
- **Hooks tend toward one PreToolUse gate + one PostToolUse formatter.** Heavier hook setups get noisy fast.
- **Plugin install over hand-install when both are available.** Plugin metadata + uninstall path are clean; hand-installed skills lose their provenance.
- **`CLAUDE_CODE_SIMPLE=1`** is a useful starting point when you suspect your setup is over-customized.

## Where this map is incomplete

- **~~Less-popular installers~~** — May 2026 survey filled this gap: Verified Skill, `sx`, iflytek/skillhub are now covered.
- **~~Enterprise / private skill repos~~** — iflytek/skillhub fills this. Other enterprise registries likely exist but aren't public.
- **Cross-host / fleet skill management.** A meaningful pattern (Felix-style personal AI deployments, plus company-wide agent fleets) that no public tool addresses well. *Still open.*
- **The bleeding edge.** Agent platforms ship monthly. The list above lags by weeks.
- **VS Code's new "Agents window"** — local AI models in VS Code that still require a GitHub Copilot plan. Mentioned in [r/LocalLLaMA 2026-05-14](https://www.reddit.com/r/LocalLLaMA/) but not yet a first-class skill consumer. Track for first-class skill API.

PRs welcome to keep this current. The 2026-05-18 survey added 12 new entries — that's a normal monthly cadence.
