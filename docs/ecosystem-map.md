# The AI-skill ecosystem, mapped

Living document. The model reads this when reasoning about user requests like "what skills exist for X" or "how do I install Y on Z?" Last refreshed: 2026-05-18 (post-survey).

This is companion to [`registry-map.md`](./registry-map.md) (which covers *where* skills live on a single machine). This doc covers *what* exists in the wider world.

## Agent platforms that consume skills

| Platform | Skill load path | Skill format | Notable |
|---|---|---|---|
| **Anthropic Claude Code** | `~/.claude/skills/`, `~/.claude/plugins/cache/<mp>/<plugin>/<version>/skills/` | SKILL.md w/ YAML frontmatter (`name`, `description`, optional `disable-model-invocation: true`) | Reference implementation. Plugin marketplace is the primary distribution. |
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

## Skill packagers (popular repos)

| Repo | Maintainer | Focus | Install |
|---|---|---|---|
| [obra/superpowers](https://github.com/obra/superpowers) | Jesse Vincent (Prime Radiant) | Methodology: TDD red-green-refactor, brainstorming, subagent-driven development, finishing branches, systematic debugging. The behavior-shaping skill set. | `claude plugin install superpowers@claude-plugins-official` |
| [mattpocock/skills](https://github.com/mattpocock/skills) | Matt Pocock (Total TypeScript) | Workflow skills: `to-issues`, `to-prd`, `triage`, `diagnose`, `tdd`, `improve-codebase-architecture`, `zoom-out`, `caveman`, `prototype`, `setup-matt-pocock-skills`. The "workflow enforcement" set. 53K+ stars. | `npx skills add mattpocock/skills` |
| [vercel-labs/skills](https://github.com/vercel-labs/skills) | Vercel Labs | Both a skill repo AND the multi-agent installer CLI. Skills + a small set of web-design-specific extras. | `npx skills add ...` |
| [rudrankriyam/asc-skills](https://github.com/rudrankriyam/asc-skills) | Rudrank Riyam | App Store Connect CLI workflow skills: 19 `asc-*` skills covering release flow, TestFlight, screenshots, pricing, etc. | `npx skills add rudrankriyam/asc-skills` |
| [mvanhorn/printing-press-library](https://github.com/mvanhorn/printing-press-library) | Michael VanHorn | "Printing Press" CLI generators wrapped as skills: `pp-linear`, `pp-sentry`, `pp-shopify`, `pp-granola`. Each is an API → CLI → skill pipeline. | `npx skills add mvanhorn/printing-press-library` |
| [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) | Anthropic | Official curated plugin directory: `superpowers`, `code-review`, `code-simplifier`, `frontend-design`, `skill-creator`, LSP plugins, more. | `claude plugin install <name>@claude-plugins-official` |
| [dimillian/skills](https://github.com/dimillian/skills) | Thomas Ricouard | iOS/Apple-focused agent skills. | `npx skills add dimillian/skills` |
| [charleswiltgen/axiom](https://github.com/charleswiltgen/axiom) | Charles Wiltgen | Axiom-specific developer skills. | `npx skills add charleswiltgen/axiom` |
| [gracefullight/stock-checker](https://github.com/gracefullight/stock-checker) | gracefullight | Stock-checking skill. | `npx skills add gracefullight/stock-checker` |
| [danielbrodie/skill-tree](https://github.com/danielbrodie/skill-tree) | Daniel Brodie | This repo. Meta: a tool for managing skills across agents. | See README. |
| [jscraik/Agent-Skills](https://github.com/jscraik/Agent-Skills) | jscraik | Large general-purpose agent-skill collection — top GitHub-search hit for "agent skills" in May 2026. PR-heavy contributor base. | Hand-install or `npx skills add jscraik/Agent-Skills` |
| [rjmurillo/ai-agents](https://github.com/rjmurillo/ai-agents) | rjmurillo | Another large agent-skills monorepo with active contributions. | `npx skills add rjmurillo/ai-agents` |
| [nexu-io/open-design](https://github.com/nexu-io/open-design) | nexu-io | Open-source local-first alternative to Anthropic's Claude Design. Shipped within days of Claude Design's launch ([r/PromptEngineering 2026-05-13](https://www.reddit.com/r/PromptEngineering/comments/1t6ssn5/claude_design_is_cool_but_the_opensource/)). | Hand-install |

### Claude Code workflow plugins (new category, May 2026)

A wave of opinionated Claude Code workflow plugins shipped in the last month. These bundle skills + hooks + multi-agent orchestration for a specific philosophy of how to work with Claude Code, distinct from atomic skills.

| Plugin | Source | Focus | Install |
|---|---|---|---|
| Nelson | ~300★ MIT, [r/ClaudeCode 2026-05-08](https://www.reddit.com/r/ClaudeCode/comments/1t7l60y/nelson_v223_shipped_and_a_benchmark_i_built/) | Multi-agent coordination skill for Claude Code using a Royal Navy metaphor (admiral/captains/ships/crew). Author ships a benchmark of 13 agent/harness/skill setups on a discrete-event simulation task; Nelson ranked 3rd. **First public skill benchmark in the corpus.** | See Reddit post for repo |
| [itsribbZ/Godspeed](https://github.com/itsribbZ/Godspeed) | MIT, [r/ClaudeAI 2026-05-12](https://www.reddit.com/r/ClaudeAI/) | Open-source plugin adds S0-S5 tier routing + multi-agent orchestration to Claude Code. One-command install, 17 skills bundled. | `claude plugin install godspeed@itsribbZ/Godspeed` (or repo-direct) |
| AI Sorcery | [r/ClaudeWorkflows 2026-05-09](https://www.reddit.com/r/ClaudeWorkflows/comments/1t5w8zt/workflow_ai_sorcery_a_collection_of_claude_code/) | Claude Code skills bundle: VM sandboxing, git hooks, iterative-dev workflows. | See Reddit post |
| OpenSwarm | [r/AISEOInsider 2026-05-12](https://www.reddit.com/r/AISEOInsider/comments/1tb7ul7/i_used_openswarm_ai_for_parallel_workflows/) | Parallel workflows across multiple AI agents. | See Reddit post |
| Glyphh AI | [r/ClaudeCode 2026-05-11](https://www.reddit.com/r/ClaudeCode/comments/1t3zf7y/i_built_a_workspace_with_3500_mcp_apps_multimodel/) | Workspace combining 3,500+ MCP apps, multi-model AI, skills, automation, and dev tooling — driven by Claude Code. | See Reddit post |

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

## How skills are being evaluated (emerging, May 2026)

For most of 2025-early 2026 there was no public benchmark of skill quality. [Nelson v2.2.3](https://www.reddit.com/r/ClaudeCode/comments/1t7l60y/nelson_v223_shipped_and_a_benchmark_i_built/) (2026-05-08) is the first public comparison: 13 agent/harness/skill setups on a discrete-event simulation task. Expect more skill benchmarks to emerge — this is a real gap in the ecosystem and someone's clearly going to fill it. skill-tree's own `docs/measurement.md` (the Reach@catalog metric) is a separate-but-related contribution; it measures the *catalog*, not the *skill*.

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

4. **Plugin cache staleness.** `~/.claude/plugins/cache/<plugin>/<old-version>/` and `<plugin>/<newer-version>/` both exist. Fix: `claude plugin gc` or remove the old version dir manually.

5. **Symlink rot.** `~/.claude/skills/X -> ~/.agents/skills/X` but the target was removed. Fix: re-sync the installer that created the symlink, or remove the dead symlink.

6. **Cluster orphan.** A skill has `disable-model-invocation: true` but isn't referenced in any cluster. It's effectively invisible. Fix: add to a cluster in the manifest, or remove the flag.

7. **Parallel registries with version skew.** `~/.agents/skills/foo` is at v1.2, `~/.claude/plugins/cache/.../foo/v1.0/` is older. The user might be invoking the wrong one. Fix: update the older one or uninstall it.

8. **Dead inventory.** A skill is installed but never invoked over a long window. Not a failure per se but worth flagging for `/skill-tree:archive`.

9. **Cross-host invocation residue.** Session logs reference a skill (`obsidian-vault`) not in any local registry. Fix: the user may be invoking a Felix-style remote agent; either install locally or document the bridge.

## Best-practices canon

The institutional consensus, as of May 2026, drawn from Anthropic's engineering blog, Boris Cherny's talks, Thariq's tips, the April 23 postmortem, and the community:

- **Progressive disclosure beats catalog overflow.** At >~50 skills, descriptions compete for attention. Hide via `disable-model-invocation: true`; route via cluster or `Skill` tool invocation.
- **Per-project beats global for distinctive needs, but global-popular beats per-project for the workflow base layer.** (See [ADR 0002](./adr/0002-hybrid-global-base-plus-per-project-tail.md).)
- **Don't bundle every skill into every project.** The "iPhone skills in a JavaScript project" anti-pattern.
- **CLAUDE.md should be short, path-scoped, and per-project.** Anthropic's May 15 best-practices post is explicit on this.
- **Hooks should be one PreToolUse gate + one PostToolUse formatter.** Per the "I tuned for 6 months" Medium write-up that several Anthropic engineers endorsed.
- **Plugin install over hand-install when both are available.** Plugin metadata + uninstall path are clean; hand-installed skills lose their provenance.
- **Use the harness Anthropic actually recommends.** `CLAUDE_CODE_SIMPLE=1` is a real lever for users who suspect over-customization. (The author's own setup audit started here.)

## Where this map is incomplete

- **~~Less-popular installers~~** — May 2026 survey filled this gap: Verified Skill, `sx`, iflytek/skillhub are now covered.
- **~~Enterprise / private skill repos~~** — iflytek/skillhub fills this. Other enterprise registries likely exist but aren't public.
- **Cross-host / fleet skill management.** A meaningful pattern (Felix-style personal AI deployments, plus company-wide agent fleets) that no public tool addresses well. *Still open.*
- **The bleeding edge.** Agent platforms ship monthly. The list above lags by weeks.
- **VS Code's new "Agents window"** — local AI models in VS Code that still require a GitHub Copilot plan. Mentioned in [r/LocalLLaMA 2026-05-14](https://www.reddit.com/r/LocalLLaMA/) but not yet a first-class skill consumer. Track for first-class skill API.

PRs welcome to keep this current. The 2026-05-18 survey added 12 new entries — that's a normal monthly cadence.
