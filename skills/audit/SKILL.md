---
description: Survey the entire skill ecosystem on this machine — every registry, every installer's lock file, every cluster manifest — and produce a ranked list of findings with safe-action proposals. USE WHEN the user asks "audit my skills", "what's going on with my skill setup", "clean up my skill installs", or mentions confusion about where skills live.
---

You are the audit diagnostician. Survey every skill registry on this machine, recognize failure modes, propose safe fixes.

Before you start, **read these two docs**:

1. `${CLAUDE_PLUGIN_ROOT}/docs/registry-map.md` — every place skills can live on a machine
2. `${CLAUDE_PLUGIN_ROOT}/docs/ecosystem-map.md` — agent platforms, packagers, installers, frontmatter conventions, failure-mode signatures

Your job: read state, match patterns from those docs, propose the right action per match.

## Step 1 — survey local state

Run each of these to get the raw inventory. Each emits JSON or text; you read all of them.

```bash
# Personal skills + plugin-namespaced skills (the expanded catalog)
${CLAUDE_PLUGIN_ROOT}/bin/skill-tree provision --list-candidates --project-root /tmp 2>/dev/null
```

```bash
# skill-tree's own manifest health
${CLAUDE_PLUGIN_ROOT}/bin/skill-tree check
```

```bash
# Per-skill last-invocation window + manifest-protected flag for the dead-
# inventory signature (#8). Covers what `skill-tree measure` exposes for
# this purpose; no need to run both.
${CLAUDE_PLUGIN_ROOT}/bin/skill-tree archive --list --window-days 60
```

```bash
# vercel-labs/skills lock file (if present)
test -f ~/.agents/.skill-lock.json && cat ~/.agents/.skill-lock.json | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'vercel-labs/skills: {len(d.get(\"skills\", {}))} skills tracked')
print(f'lastSelectedAgents: {d.get(\"lastSelectedAgents\", [])}')
print(f'format version: {d.get(\"version\")}')
"
```

```bash
# Other registry inventory
test -d ~/.openclaw && echo "~/.openclaw exists; contents:" && ls ~/.openclaw/
test -d ~/.codex/plugins && echo "~/.codex/plugins exists; contents:" && ls ~/.codex/plugins/
test -d ~/.gemini/skills && echo "~/.gemini/skills exists; contents:" && ls ~/.gemini/skills/

# Claude plugin install state
cat ~/.claude/plugins/installed_plugins.json 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'Claude Code plugins: {len(d.get(\"plugins\", {}))} installed')
"
```

## Step 2 — pattern-match against known failure-mode signatures

Walk through the nine numbered signatures in `docs/ecosystem-map.md` § "Recognized failure-mode signatures" and check each one against the inventory above. The numbers here match the doc exactly — cite them by number in your output so users can look up the full description.

1. **vercel-labs fan-out targets agents that aren't installed.** Check `lastSelectedAgents` against actual dir presence (`~/.cursor`, `~/.amp`, `~/.warp`, etc.).
2. **Plugin cache staleness.** Walk `~/.claude/plugins/cache/<plugin>/`; if multiple version dirs exist, the older ones are likely dead.
3. **Manifest-vs-filesystem drift in skill-tree.** From `/skill-tree:check` output: any skill in the manifest but missing from disk?
4. **Symlink rot.** Find `~/.claude/skills/*` symlinks pointing at missing targets.
5. **Partial-fan-out scoping.** `~/.agents/skills/X/SKILL.md` exists, `~/.claude/skills/X` doesn't — but `npx skills list -g` shows X was scoped to a non-Claude-Code agent. (Distinct from #4 — see ecosystem-map.md.)
6. **`disable-model-invocation: true` orphan.** Hidden via frontmatter, not routed in any cluster, effectively invisible. (Already flagged by `/skill-tree:check`.)
7. **Parallel registries with version skew.** Same skill name in `~/.agents/skills/` and `~/.claude/plugins/cache/`. The model resolves whichever it finds first.
8. **Dead inventory.** Skills with zero invocations over the window (already flagged by `/skill-tree:archive --list`).
9. **`/reload-plugins` only refreshes the plugin tier.** After running it, Desktop-provided skills disappear from the available-skills list until restart.

## Step 3 — rank the findings

Order by:

- **Severity** — broken cluster routing > stale fan-out > dead inventory > housekeeping
- **Effort to fix** — single command beats multi-step
- **Confidence** — clear failures rank above maybe-issues

Top 5–10 is enough. Don't overwhelm.

## Step 4 — present each finding with its safe action

For each finding, name:

- **What you see** (the concrete observation, with file paths)
- **Why it matters** (which failure mode signature it matches)
- **Safe action** (the right tool's command for fixing it, from `docs/ecosystem-map.md` § "Installers")

Example output:

```
1. Plugin cache staleness for cli-printing-press
   Path: ~/.claude/plugins/cache/cli-printing-press/cli-printing-press/
   Why: Two version dirs side-by-side (4.0.6 and 4.9.0). The loader uses
        the newer; the older is dead disk. Matches failure-mode #2a.
   Safe action: rm -rf ~/.claude/plugins/cache/cli-printing-press/cli-printing-press/4.0.6

2. vercel-labs lock file fans out to agents that aren't installed
   File: ~/.agents/.skill-lock.json — lastSelectedAgents
   Why: lastSelectedAgents lists an agent whose home dir doesn't exist
        (e.g. ~/.cursor when cursor isn't installed locally). Each sync
        wastes effort symlinking into a missing target. Matches signature #1.
   Safe action: npx skills config  # then deselect absent agents
```

(The agent names above are illustrative — check the user's actual
`lastSelectedAgents` and present whichever absent agents you find.)

## Step 5 — ask the user what to do

Don't auto-apply. Walk the user through findings one at a time:

> Finding #1: cli-printing-press has two version dirs in the plugin cache. Safe action is `rm -rf .../cli-printing-press/4.0.6`. Apply? (y/n/skip)

Record each action to the audit log when applied. Skip cleanly when declined.

**Report-only findings are valid.** Not every finding has a clean action. Dead inventory (signature #8) often resolves to "these are intentional reserves for a workflow the user doesn't do every month" — no local action needed. Surface it, explain, move on. Don't fabricate an action for the sake of having one.

## Notes

- When you encounter a registry, packager, or installer that isn't in `ecosystem-map.md`, name it in your output and recommend a PR to add it. The doc only stays current that way.
- For destructive actions, default to the least-destructive equivalent. Archive a symlink rather than `rm` it when `unarchive` exists.
