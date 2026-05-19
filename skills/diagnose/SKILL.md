---
description: Given a user-reported skill-ecosystem symptom ("my skill X isn't appearing", "I get 'skill not found' for Y", "I shipped a new version but my agents don't see it", "things feel slow / cluttered"), match it to a known failure-mode signature, run the targeted diagnostic, and surface the root cause plus the safe fix command per installer. USE WHEN the user describes a specific symptom — for a broad sweep with no single symptom, use `/skill-tree:audit` instead.
---

You are the diagnose skill. Audit is a broad survey; you are a **targeted probe** triggered by a specific user-reported symptom. The failure-mode tables in `ecosystem-map.md` and `registry-map.md` are the diagnostic playbook.

## Step 1 — read the docs

Read the two failure-mode tables:

1. `${CLAUDE_PLUGIN_ROOT}/docs/ecosystem-map.md` § "Recognized failure-mode signatures" (9 numbered signatures, current source of truth)
2. `${CLAUDE_PLUGIN_ROOT}/docs/registry-map.md` § "Common failure modes" (8 closely-related entries with registry-specific context)

These two tables are the diagnostic playbook. Read both before pattern-matching the user's symptom — the same root cause often shows up in both, with slightly different framings.

## Step 2 — classify the symptom

Map the user's words to a symptom family. If it doesn't fit cleanly, ask one clarifying question (Step 4) — don't guess.

| Symptom family | Pattern in user's words | Likely signatures |
|---|---|---|
| **Skill not visible** | "isn't appearing", "don't see", "shipped a new version but agents don't see it" | #4 plugin cache staleness (incl. reload-vs-update sub-finding); #6 cluster orphan; disable-model-invocation orphan |
| **Skill invocation fails** | "skill not found", "errors when I call it", "Read fails on SKILL.md" | #5 symlink rot; registry-map #2 dead symlink |
| **Wrong version invoked** | "doing the old behavior", "updated but running the old code" | #7 parallel registries / version skew; #4 plugin cache staleness |
| **Skill list bloat** | "feels slow", "cluttered", "agent confused about which skill" | catalog overflow (best-practices canon); #8 dead inventory |
| **Multi-agent fan-out wrong** | "after npx skills sync something broke", "appeared in agents I don't use", "removed an agent but skills still listed" | #1 vercel-labs fan-out to absent agents; registry-map #7 lock-file drift |
| **Unknown registry** | "what is ~/.openclaw?", "why is there a thing in ~/.gemini/skills/?" | #2 OpenClaw dev artifact; or legitimate — check `registry-map.md` § Registries |
| **Manifest references missing skill** | "manifest says X but I can't find it", "audit says drift" | #3 manifest-vs-filesystem drift |
| **Cross-host residue** | "session log shows a skill not on this machine" | #9 cross-host invocation residue |

## Step 3 — run the targeted diagnostic

Pick the *minimum* set of commands needed to confirm or rule out the matched signatures. Don't run the full audit sweep — that's `/skill-tree:audit`'s job. The diagnose pattern is: read the symptom, run one or two targeted probes, confirm root cause.

Examples — keyed to the symptom families. **Replace `ALL_CAPS_PLACEHOLDERS` with concrete values from the user's case before running.**

```bash
# Skill not visible after a plugin update — check installed version vs cache vs running
cat ~/.claude/plugins/installed_plugins.json | python3 -c "
import json, sys
d = json.load(sys.stdin)
for k, v in d['plugins'].items():
    if 'TARGET_PLUGIN' in k.lower():
        print(k, '->', v[0].get('version'), '@', v[0].get('installPath'))
"
ls ~/.claude/plugins/cache/TARGET_MARKETPLACE/TARGET_PLUGIN/ 2>/dev/null
# If installed_plugins.json shows v0.6.1 but the available-skills list at session start
# only had skills from v0.6.0, the user ran /reload-plugins but never `claude plugin update`,
# OR they ran update but haven't restarted Claude Code yet. See ecosystem-map.md
# failure-mode #4 sub-finding.
```

```bash
# Symlink rot — find broken symlinks under skill registries
find ~/.claude/skills ~/.agents/skills -maxdepth 2 -type l ! -exec test -e {} \; -print 2>/dev/null
```

```bash
# Parallel registries / version skew — same name in two places
comm -12 \
  <(ls ~/.claude/skills 2>/dev/null | sort) \
  <(ls ~/.agents/skills 2>/dev/null | sort)
# Each line is a candidate for version skew. Check SKILL.md mtimes or git SHAs.
```

```bash
# Cluster orphan — skill is hidden but isn't referenced anywhere
${CLAUDE_PLUGIN_ROOT}/bin/skill-tree check
# Surfaces "leaf not in any cluster" findings already.
```

```bash
# vercel-labs fan-out vs installed-agent reality
test -f ~/.agents/.skill-lock.json && cat ~/.agents/.skill-lock.json | python3 -c "
import json, sys, os
d = json.load(sys.stdin)
agents = d.get('lastSelectedAgents', [])
agent_dirs = {
  'claude-code': '~/.claude', 'codex': '~/.codex',
  'gemini-cli': '~/.gemini', 'cursor': '~/.cursor',
  'amp': '~/.amp', 'warp': '~/.warp', 'antigravity': '~/.antigravity',
}
present = [a for a in agents if os.path.exists(os.path.expanduser(agent_dirs.get(a, '')))]
absent = [a for a in agents if not os.path.exists(os.path.expanduser(agent_dirs.get(a, '')))]
print(f'Configured: {agents}')
print(f'Present:    {present}')
print(f'Absent:     {absent}  ← fix with: npx skills config')
"
```

Pick the matching block; **don't run all of them** unless the symptom is genuinely ambiguous.

## Step 4 — for ambiguous symptoms, ask one clarifying question

Don't guess. If the user said "my skills are broken," you need a concrete observable.

Examples:
- "What specifically happens — does the skill not appear in the list, or does it appear but error when invoked?"
- "Did this start after a specific action (plugin update, npx skills sync, agent uninstall)?"
- "Which agent is showing the problem — Claude Code, Codex, Gemini CLI?"

One question, then proceed.

## Step 5 — present the finding

For each confirmed root cause, name:

- **What I see** — the concrete evidence with file paths, version numbers, command output
- **Why it matches** — which failure-mode signature it corresponds to (cite by number from `ecosystem-map.md`)
- **Requires host-agent restart?** — Y/N. Cache-staleness fixes often need Claude Code / Codex / Gemini CLI to restart before the new state is visible to the running process. Surface this loudly when it applies; don't bury it in the safe-fix block.
- **Safe fix** — the right tool's command per `ecosystem-map.md` § "Installers" or `registry-map.md` § "How to remove a skill cleanly"
- **What changes after the fix** — so the user can verify
- **If partially applied:** if the evidence shows the user has already done part of the fix, name what's done and what remains. Don't pretend the diagnostic is starting from a clean slate.

Example:

```
Finding: Plugin cache staleness for skill-tree
  What I see:
    - installed_plugins.json shows skill-tree@skill-tree at v0.6.1
    - ~/.claude/plugins/cache/skill-tree/skill-tree/ contains both 0.6.0/ and 0.6.1/
    - Available-skills list at session start shows skills from 0.6.0/ only

  Why it matches:
    Failure-mode signature #4 (ecosystem-map.md). Specifically the sub-finding:
    /reload-plugins reloads existing state but doesn't re-fetch the marketplace,
    and even after `claude plugin update` runs, the available-skills list won't
    refresh until Claude Code restarts.

  Safe fix:
    1. (Already done if you see 0.6.1/ in the cache.) If not:
         claude plugin marketplace update skill-tree
         claude plugin update skill-tree@skill-tree
    2. Restart Claude Code.
    3. Optional cleanup: rm -rf ~/.claude/plugins/cache/skill-tree/skill-tree/0.6.0
       (dead disk, the loader prefers the newest dir per installed_plugins.json)

  After the fix:
    The 0.6.1 catalog skill appears in your available-skills list and is
    invokable via Skill(skill="catalog").
```

## Step 6 — gap report

If the symptom doesn't match any known signature, say so plainly and walk the user toward better evidence:

> "This symptom doesn't match any of the 9 signatures in `ecosystem-map.md`. Worth running `/skill-tree:audit` for a broad sweep, or `/last30days "<your symptom>"` to check whether other users are seeing the same thing. If the symptom turns out to be a real, reproducible failure mode, PR it back to `ecosystem-map.md` § 'Recognized failure-mode signatures' — that's how the diagnostic playbook stays current."

## Notes

- **Audit vs. diagnose:** audit is a sweep — it surveys everything and ranks findings. Diagnose is a probe — it takes a symptom and narrows to one root cause. If the user said "audit my skills" or "what's going on with my setup," they want audit. If they said "X is broken / X isn't working," they want diagnose.
- **Don't auto-apply fixes.** Walk the user through the safe action. Some "fixes" — especially `rm -rf` on registry dirs — should be the user's explicit call.
- **Cite the signature by number.** Says "failure-mode #4" gives the user (and any future agent reading the conversation) a stable handle they can look up in the doc.
- **Restart-required findings are legitimate.** Sometimes the root cause is "you need to restart the host agent for the new cache to take effect." That's a real fix; surface it explicitly instead of pretending the problem is on-disk only.
- **If the symptom turns out to span two registries (e.g., vercel-labs + Claude Code plugin cache), name both findings.** Don't pick one for the user.
