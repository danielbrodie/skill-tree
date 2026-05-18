# ADR 0003 — skill-tree is the institutional-knowledge layer for the agent-skill ecosystem

- **Status:** Accepted
- **Date:** 2026-05-18
- **Tracking issue:** BRO-190 (umbrella)
- **Builds on:** [ADR 0002](./0002-hybrid-global-base-plus-per-project-tail.md)

## Context

The validation work in BRO-179..189 surfaced something bigger than the local Mac it audited:

**The agent-skill ecosystem is a multi-vendor, multi-tool, multi-platform mess.** A "skill" is consumed today by at least 13 agent runtimes (Claude Code, Codex, Cursor, Gemini CLI, Cline, Amp, Antigravity, GitHub Copilot, Warp, Opencode, Firebender, DeepAgents, Kimi-CLI — per the `lastSelectedAgents` list shipped by [vercel-labs/skills](https://github.com/vercel-labs/skills)). Skills are packaged by at least seven distinct organizations (Anthropic, Vercel Labs, Matt Pocock, mvanhorn, rudrankriyam, dimillian, charleswiltgen, gracefullight, obra/Prime Radiant, OpenAI). Installers don't agree on file layouts, lock formats, frontmatter conventions, or removal commands.

**No human user can hold the full picture.** Each user is running 3–5 of these tools and 20–100 skills and has to assemble institutional knowledge by trial and error. When something goes wrong (a skill is invoked but not reachable; a tool's lock file diverges from filesystem; symlinks point at dev artifacts), debugging requires understanding the whole stack.

**This is exactly the problem skill-tree is positioned to solve.** It runs *inside* an AI agent. It can read the ecosystem's documentation, scan the local state, reason about the user's intent, and act using the right tool's commands. The Python scripts are commodity — the value is the encoded knowledge of how the ecosystem works.

## Decision

**skill-tree is the institutional-knowledge layer for the AI-skill ecosystem.** Its primary product is documented, AI-consumable expertise about:

1. **Agent platforms.** Every major and minor agent runtime: Claude Code, Codex, Cursor, Gemini CLI, Cline, Amp, Antigravity, GitHub Copilot, Warp, Opencode, Firebender, DeepAgents, Kimi-CLI, OpenClaw. Where each loads skills from. What frontmatter each respects. What's unique about each install path.

2. **Skill packagers.** Every notable skill repo in the public ecosystem: `obra/superpowers`, `mattpocock/skills`, `vercel-labs/skills`, `rudrankriyam/asc-skills`, `mvanhorn/printing-press-library`, `anthropics/claude-plugins-official`, `dimillian/skills`, `charleswiltgen/axiom`, plus emerging ones. What each is about, who maintains it, how to install, how to remove.

3. **Installers.** Every tool that writes to a skill registry: `claude plugin`, `codex plugin`, `gemini extensions`, `npx skills` (vercel-labs), Matt Pocock's bootstrap, hand-install, skill-tree's own provisioner. Their commands, lock files, side effects.

4. **Failure modes.** Every common breakage: manifest-vs-filesystem drift, dead symlinks, dev-artifact directories that look like installs, parallel registries with the same skill at different versions, fan-out drift, plugin cache staleness, `disable-model-invocation` orphans, cross-host invocations referencing absent skills.

5. **Conventions.** Frontmatter formats (`name`, `description`, `disable-model-invocation`, `routing-hint`). Per-project `.claude/skills/` patterns. Cluster routing via `disable-model-invocation: true`. Progressive disclosure as Anthropic-recommended pattern. The Boris Cherny / Thariq best-practices canon.

This knowledge lives in `docs/` as prose (so it can be read by humans and AI alike) and is referenced in skill-tree's SKILL.md files (so the model loads it on invocation). The Python in `scripts/` is the execution layer; the knowledge in `docs/` is the durable product.

## Why this works

Three things are true at once and together they create the opportunity:

- skill-tree **runs inside an AI agent.** It can ask the model to read the docs, reason about user intent, and decide on actions. No traditional CLI gets to use AI as its router.
- The ecosystem is **complex but bounded.** ~15 agent platforms, ~10 popular skill repos, ~5 installers. Tractable to map in one repo's docs and keep current.
- Users **don't want to learn it.** They want to type "find a skill that does X" or "this isn't working, fix it" and have the right thing happen. AI + documented knowledge = that.

## What this means concretely (deliverables)

### Phase 1: the audit skill (BRO-190 first concrete output)

`/skill-tree:audit` surveys every registry skill-tree knows about, joins it with the lock files of every installer it knows about, and produces ranked findings:

> 1. **Dev artifact at `~/.openclaw/`** — `openclaw.json` references a local dev path, no process running, last touched 2 months ago. **Safe action:** `rm -rf ~/.openclaw` (no live deps).
> 2. **Stale fan-out in vercel-labs lock file** — `lastSelectedAgents` includes 13 agents, but `~/.cursor`, `~/.amp`, `~/.warp` don't exist on this machine. **Safe action:** `npx skills config set agents claude-code,codex,gemini-cli` to focus syncs.
> 3. **Manifest references missing skill** — `app-store-release` cluster lists `asc-notarization`, but `~/.claude/skills/asc-notarization` is absent. It's installed at `~/.agents/skills/asc-notarization` per the vercel-labs lock file. **Safe action:** Run `npx skills sync` to recreate symlinks.

The model walks the user through findings one at a time, executing the right installer's command per finding. Audit log records each action.

### Phase 2: the catalog skill

`/skill-tree:catalog <topic>` — given a user request ("I need a skill for working with Stripe webhooks"), skill-tree searches its knowledge of public skill repos and surfaces the candidates with install instructions per the user's chosen agent.

### Phase 3: the diagnose skill

`/skill-tree:diagnose "skill X isn't being invoked"` — the model reads the registry-map, surveys local state, and walks through the diagnosis tree: is X in the catalog? Is it `disable-model-invocation: true`? Is its description matching what the user typed? Etc.

### Phase 4: the install skill

`/skill-tree:install <github-url-or-name>` — knows whether to invoke `claude plugin install`, `npx skills add`, or `git clone` depending on the source. Records the install in skill-tree's own audit log alongside the installer's lock file.

## Consequences

### Good

- skill-tree's value proposition gets clear and large: it's the cross-vendor documentation + intelligent navigator. Nothing else fills this gap.
- The durable USP is the docs, not the code. Anyone can fork and contribute new packagers/agents/failure-modes; the codebase doesn't bloat.
- Solves a real, painful, recurring user problem (Daniel's own audit today).

### Bad

- Documentation maintenance becomes the critical path. New agent platforms ship every month; new skill repos appear weekly. Out-of-date docs are worse than no docs.
- Scope is larger than any individual; needs community contribution to scale. Plan for that: `docs/registry-map.md` and `docs/ecosystem-map.md` are explicit PR-friendly surfaces.
- Risk of becoming "the encyclopedia nobody reads" if not paired with concrete actions. Mitigation: every doc section anchors to a skill action.

### Neutral

- Existing skill-tree features (provision, sync, archive, check, setup, fetch) remain useful primitives. They become tools the audit/diagnose/install/catalog skills invoke.

## Open questions

- **How does skill-tree stay current?** Weekly scheduled scan of major skill-repo orgs? Or accept that the docs lag by weeks and rely on `--fetch-latest` runtime lookups? Probably both, with manual curation for "what's worth knowing."
- **Cross-host scope.** A user with Felix-style remote agents has skills on machines skill-tree can't see. Worth a "remote audit" mode? Or document the limit?
- **Trust boundary on `/skill-tree:install`.** Right now `fetch` runs security checks (prompt injection, zero-width unicode, path traversal). `install` would do the same plus install. Where does skill-tree stop and the user's own judgement start? Probably: skill-tree refuses install on obvious red flags, warns on yellow ones, lets the user override.
