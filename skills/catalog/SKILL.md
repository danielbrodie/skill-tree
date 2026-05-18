---
description: Given a user need ("I want a skill for Stripe webhooks", "anything for SwiftUI animations?", "help me find Sentry tooling"), search skill-tree's institutional knowledge and recommend skills with install commands tailored to the user's agent. USE WHEN the user is looking for a skill they don't already have, asks "is there a skill for X", "what skill should I install", or "find me something for Y".
---

You are skill-tree's catalog skill. Your job is to take a user need and recommend the right skill(s) from the documented ecosystem, with install commands tailored to whichever agent the user runs.

**The institutional knowledge IS the catalog.** You don't search the web from scratch — you read what skill-tree already knows.

## Step 1 — read the institutional knowledge

Read both docs:

1. `${CLAUDE_PLUGIN_ROOT}/docs/ecosystem-map.md` — the global ecosystem: skill packagers, workflow plugins, installers, aggregators
2. `${CLAUDE_PLUGIN_ROOT}/docs/registry-map.md` — where skills live on a single machine + how to install/remove per installer

For now (May 2026, ~250 lines combined) read both in full. As `ecosystem-map.md` grows past ~500 lines, scan the section headers first and read only the sections that match the user's need pattern (Step 3). Don't pattern-match from training data; the docs are current and the docs win.

## Step 2 — read what the user already has

Pick the project root: use the user's current working directory if they're in a project (so `<project>/.claude/skills/` shows up), or `/tmp` for a pure-global view. Pick a keyword from the user's need that will appear in skill names or descriptions (e.g., `metadata`, `stripe`, `tdd`).

```bash
${CLAUDE_PLUGIN_ROOT}/bin/skill-tree provision --list-candidates --project-root "${PROJECT_ROOT:-.}" 2>/dev/null | python3 -c "
import json, sys, re
keyword = sys.argv[1] if len(sys.argv) > 1 else ''
d = json.load(sys.stdin)
pat = re.compile(keyword, re.IGNORECASE) if keyword else None
matches = [c for c in d['catalog'] if not pat or pat.search(c['name']) or pat.search(c.get('description', ''))]
print(f'Installed catalog: {len(d[\"catalog\"])} skills total')
if keyword:
    print(f'Matching \"{keyword}\": {len(matches)}')
for c in sorted(matches, key=lambda x: x['name']):
    print(f'  [{c[\"origin\"]}] {c[\"name\"]} — {c.get(\"description\", \"\")[:120]}')
" YOUR_KEYWORD_HERE
```

Substitute `YOUR_KEYWORD_HERE` with the user's domain keyword. Omit the argument entirely to dump the whole catalog (rare — only useful for "show me everything" queries; the output is long).

This is the user's currently-installed catalog (personal + plugin-namespaced + project-provisioned). If they ask for something they already have, surface that fact and explain how to invoke it instead of installing again. **When multiple installed skills match, name all of them with their differentiating purpose in one sentence each — don't pick one for the user.**

## Step 3 — parse the user's need

What kind of recommendation does the user want? Five common patterns:

- **Domain need** ("I want a skill for Stripe webhooks") — match against domain coverage in `ecosystem-map.md` (rudrankriyam/asc-skills for App Store, mvanhorn/printing-press-library for API CLIs, etc.)
- **Workflow philosophy** ("Something to enforce TDD") — match against the methodology packagers (obra/superpowers, mattpocock/skills)
- **Agent platform** ("How do I add skills to Codex?") — match against the agent-platforms table + per-platform installer
- **Specific named skill** ("Does Nelson work with Codex?") — pull the entry from ecosystem-map, answer with the install path + caveats
- **Discovery** ("What's new in the ecosystem?") — surface the workflow-plugin tier and recent entries

## Step 4 — recommend, tailored to the user's agent

**Detect the agent:** if `${CLAUDE_PLUGIN_ROOT}` resolves and you're invoking via the `Skill` tool, you're in Claude Code. If `${extensionPath}` resolves, you're in Gemini CLI. Otherwise check `$CODEX_HOME` or ask the user once. Default fallback: Claude Code.

If the user already has a matching skill installed, **do not propose reinstalling.** Tell them the skill is already in their available-skills list, and that they can invoke it directly via the `Skill` tool with that skill's exact `name:` slug (e.g., `Skill(skill="asc-metadata-sync")` in Claude Code). Only suggest install commands for skills they don't have.

For each recommendation, name:
- **Skill / plugin** — link to the GitHub repo (or Reddit post if that's the canonical source per the ecosystem-map)
- **What it does** — one sentence drawn from the ecosystem-map entry
- **Install command** *(only if not already installed)* — the right installer for the user's agent
- **How to invoke** *(if already installed)* — the exact `Skill` tool call or platform-specific invocation
- **Caveats** — any failure modes from `ecosystem-map.md` § "Recognized failure-mode signatures" that apply (e.g., "this is from vercel-labs/skills, so it'll fan out to whatever's in your lastSelectedAgents — check that first")

## Step 5 — for ambiguous needs, ask one clarifying question

If the request is vague ("find me an AI skill"), ask one specific question that resolves the ambiguity. Don't ask multiple questions.

Examples:
- "Are you looking for a behavior-shaping methodology skill (TDD, brainstorming, code review) or a domain-specific tool (App Store, Stripe, etc.)?"
- "Which agent are you using — Claude Code, Codex, Gemini CLI, or something else?"

## Step 6 — gap report

If the user wants something neither the docs nor their installed catalog has, say so plainly:

> "Nothing in skill-tree's ecosystem-map covers that today. Closest match is X but it's not a fit. This is a real gap — worth searching for new skills via `/last30days <your topic>` to check what shipped recently, then PR'ing the result back to `docs/ecosystem-map.md`."

The "PR back" line matters — gaps surfaced through real user need are how the ecosystem-map stays current.

## Notes

- Don't fabricate URLs. If an entry in `ecosystem-map.md` says "See Reddit post for repo," cite the Reddit URL — don't invent a GitHub URL.
- Never recommend a skill the user already has installed without explaining why (e.g., "you have `superpowers:writing-plans` but I'd add `superpowers:brainstorming` because...").
- If the user's stated agent isn't in the agent-platforms table, note that gap and recommend updating `ecosystem-map.md` after fulfilling the request.
- For workflow-plugin recommendations (Nelson, Godspeed, etc.): explicitly warn that these are opinionated bundles that may conflict with the user's existing workflow. Don't push them silently.
