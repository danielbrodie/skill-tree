---
description: Given a skill or plugin reference (name@marketplace, GitHub URL, user/repo shorthand, bare name, or Reddit/blog URL for workflow plugins), look up `docs/ecosystem-map.md` for the right installer and run it. Handles Claude Code plugin marketplace, Codex plugin marketplace, Gemini CLI extensions, vercel-labs/skills CLI, and hand-install. USE WHEN the user says "install X", "add the X skill", "set up <plugin>", or hands you a GitHub repo URL and wants it installed.
---

You are the install skill — a **cross-installer dispatcher.** Given a reference, pick the right installer per `ecosystem-map.md` § "Installers" and run it.

## Step 1 — read the docs

Read the relevant sections of:

1. `${CLAUDE_PLUGIN_ROOT}/docs/ecosystem-map.md` § "Skill packagers" + "Installers" + "Claude Code workflow plugins"
2. `${CLAUDE_PLUGIN_ROOT}/docs/registry-map.md` § "Installers"

These tables are the dispatch logic. If the user's ref appears in any of them, the documented install command is authoritative — don't improvise.

## Step 2 — classify the reference

Map the user's ref to one of these forms:

| Ref form | Example | Implied installer |
|---|---|---|
| **`name@marketplace`** | `superpowers@claude-plugins-official` | Claude Code or Codex plugin install — check `claude plugin marketplace list` and `codex plugin marketplace list` to disambiguate |
| **GitHub `user/repo` shorthand** | `rudrankriyam/asc-skills` | Look up in ecosystem-map.md packagers table → use documented command. If unknown, inspect repo. |
| **Full GitHub URL** | `https://github.com/itsribbZ/Godspeed` | Same as shorthand. Strip to `user/repo` and dispatch. |
| **Bare name** | `superpowers`, `nelson`, `asc-skills` | Search ecosystem-map.md packagers + workflow-plugins tables. If exactly one match, use it; if multiple, disambiguate with one question. Example for `asc-skills`: "Did you mean the packager `rudrankriyam/asc-skills` (the whole 19-skill bundle) or one of the individual `asc-*` skills already installed?" |
| **Reddit / blog URL** | `https://www.reddit.com/r/ClaudeCode/comments/.../nelson_v223/` | These are typical for workflow plugins documented only via post. Read ecosystem-map.md to see if the post references a canonical repo. If not, ask the user where the install path is. |
| **Local path** | `~/Projects/my-skill` or `./my-skill` | Hand-install. `cp -r <path> ~/.claude/skills/<name>/` for personal scope, or coordinate with skill-tree's `/skill-tree:fetch` for the library. |

## Step 3 — detect the user's agent

Same rule as catalog and diagnose:

- `${CLAUDE_PLUGIN_ROOT}` resolves → Claude Code (default)
- `${extensionPath}` resolves → Gemini CLI
- `$CODEX_HOME` set → Codex
- Otherwise ask once

The agent matters because the same skill repo can install differently per agent (e.g., `rudrankriyam/asc-skills` goes to `~/.agents/skills/` via vercel-labs/skills regardless of agent, but a Claude Code marketplace plugin goes to `~/.claude/plugins/cache/...` only for Claude Code).

## Step 4 — pre-flight checks

Before running any install command:

1. **Is it already installed?** Inline the catalog scan:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/bin/skill-tree provision --list-candidates --project-root /tmp 2>/dev/null | python3 -c "
   import json, sys, re
   keyword = sys.argv[1]
   d = json.load(sys.stdin)
   pat = re.compile(keyword, re.IGNORECASE)
   for c in d['catalog']:
       if pat.search(c['name']):
           print(f' {c[\"origin\"]:>16}: {c[\"name\"]} -> {c[\"path\"]}')
   " TARGET_KEYWORD
   ```
   If a skill of the same name exists, surface that and ask whether the user wants to reinstall, update, or do nothing.

2. **Will it conflict with an existing install path?** Check for the duplicate-registry failure mode (registry-map.md #3 / ecosystem-map.md #7): if `rudrankriyam/asc-skills` is already in `~/.agents/skills/` via vercel-labs and the user is now asking for the Claude Code plugin marketplace version, that's parallel-registries-with-version-skew waiting to happen. Flag it.

3. **For workflow plugins (Nelson, Godspeed, AI Sorcery, OpenSwarm, Glyphh AI):** Warn explicitly per the catalog SKILL.md "opinionated bundles" note. These bundle skills + hooks + multi-agent orchestration and can conflict with existing workflow. Don't push silently.

4. **For vercel-labs/skills installs:** Verify the CLI is installed (`which npx && npx skills --help 2>&1 | head -3`). If absent, the dispatch path itself is blocked — say so plainly. Then check `~/.agents/.skill-lock.json` `lastSelectedAgents`. The install will fan out to every agent in that list. If the list is stale (includes agents not installed locally — failure-mode #1), recommend `npx skills config` before running the add.

5. **For `claude plugin install` references:** Verify the marketplace is configured:
   ```bash
   claude plugin marketplace list 2>&1 | grep -F "TARGET_MARKETPLACE" || echo "MISSING — add with: claude plugin marketplace add <owner>/<repo>"
   ```
   If missing, prepend a `claude plugin marketplace add <owner>/<repo>` step to the install plan. The plugin install will fail otherwise. Same logic applies to `codex plugin install` with `codex plugin marketplace list`.

6. **Surface unrelated failure modes that the pre-flight stumbles on, but don't block on them.** If checking the catalog reveals e.g. a symlink-rot finding on a skill unrelated to the install ref, name it as a side-finding and offer to address it before or after the install. Pre-flight is also a free chance to spot ecosystem drift; don't waste the signal.

## Step 5 — present the plan, then run

State the install plan in full *before* executing it, with the matching ecosystem-map row as the citation:

```
Install plan
  Reference: rudrankriyam/asc-skills
  Resolved as: skill packager from ecosystem-map.md § "Skill packagers"
               (row: rudrankriyam/asc-skills, 19 asc-* skills)
  Installer: vercel-labs/skills CLI (npx skills add)
  Target agents (per ~/.agents/.skill-lock.json lastSelectedAgents):
    claude-code, codex, gemini-cli, antigravity
  Symlinks will land at:
    ~/.agents/skills/asc-* → originals
    ~/.claude/skills/asc-* → ~/.agents/skills/asc-*
    ~/.codex/skills/asc-*  → ~/.agents/skills/asc-*
    (etc. for each agent above)
  Caveats:
    - failure-mode #1 watch: if lastSelectedAgents has agents not present,
      symlinks will be wasted effort. Pre-flight already checked this.
  Command:
    npx skills add rudrankriyam/asc-skills

  Proceed? (y/n)
```

Run the command only after the user confirms. Don't auto-apply.

## Step 6 — post-install verification

After the install command returns, verify:

```bash
# Did the install actually create files?
ls -la <expected install path>

# For Claude Code plugin installs, check installed_plugins.json
cat ~/.claude/plugins/installed_plugins.json | python3 -c "
import json, sys
d = json.load(sys.stdin)
print([k for k in d['plugins'] if 'TARGET_NAME' in k.lower()])
"

# For vercel-labs/skills, check the lock file
test -f ~/.agents/.skill-lock.json && python3 -c "
import json
d = json.load(open('/Users/$USER/.agents/.skill-lock.json'))
print({k: v for k, v in d.get('skills', {}).items() if 'TARGET_NAME' in k.lower()})
"
```

## Step 7 — surface what the user must do to actually invoke

For **Claude Code plugin installs**, the user needs:

1. The plugin's cache dir at `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/` (just created).
2. **A Claude Code restart** for the available-skills list to pick up the new SKILL.md files. Per `ecosystem-map.md` failure-mode #4 sub-finding (2026-05-18): `/reload-plugins` re-reads existing on-disk state but the available-skills list only refreshes at process start. Tell the user to restart.

For **vercel-labs/skills installs**, the symlinks are live immediately — but for agents that cache their skill lists at process start (Claude Code, Codex), the same restart-or-reload rule applies. State this explicitly.

For **Gemini CLI extensions**, follow `gemini extensions install <name>` — Gemini reloads on demand.

For **hand-install**, the skill appears wherever you put it but you may need to set `disable-model-invocation: true` and add it to a cluster manifest (per `ecosystem-map.md` failure-mode #6 cluster orphan) before it routes correctly.

## Step 8 — record the install

skill-tree's `~/.claude/skills-library/skill-tree/manifest.json` is the source of truth only when `/skill-tree:fetch` previously brought the skill into the library. In every other case the installer's own bookkeeping is authoritative:

- `claude plugin install` → `~/.claude/plugins/installed_plugins.json`
- `codex plugin install` → Codex's installed-plugins file
- `gemini extensions install` → Gemini's extensions registry
- `npx skills add` → `~/.agents/.skill-lock.json`
- Hand-install → no bookkeeping; the file system *is* the truth

Don't write to the skill-tree manifest for installs that didn't go through `/skill-tree:fetch`. That double-bookkeeping is its own failure mode.

## Step 9 — gap report

If the ref doesn't match anything in `ecosystem-map.md` AND inspecting the repo doesn't reveal a known shape (no `.claude-plugin/`, no `gemini-extension.json`, no `skills/` dir), say so plainly:

> "Couldn't dispatch this ref. The repo doesn't match any documented packager pattern and ecosystem-map.md doesn't list it. Options: (a) hand-install with `git clone`, (b) ask the maintainer for the canonical install command, (c) PR it to `ecosystem-map.md` once you've worked out the right install path."

## Notes

- **Don't auto-apply.** State the plan, get confirmation, then run.
- **Cite the dispatch source.** Saying "ecosystem-map.md § Skill packagers row X" gives the user (and future agents) a traceable decision.
- **Workflow plugins (Nelson, Godspeed, etc.) get an extra warning.** They're opinionated bundles, not atomic skills. Make sure the user wants the whole bundle.
- **Post-install restart messages are part of the install, not a follow-up.** Saying "I installed it" without "you need to restart for it to appear" leaves the user confused — exactly the symptom diagnose now walks. Don't recreate the problem.
- **Failure-mode #4 (cache staleness) is the most common post-install confusion.** When in doubt about whether a restart is needed, say yes and explain the loader behavior. Better to over-inform than to ship the user into the same symptom diagnose was built to handle.
- For Codex installs, the marketplace system is local-path-only as of mid-2026 (per ecosystem-map.md agent-platforms row). If the user is on Codex and the ref is a GitHub repo, the path may need to go via vercel-labs/skills instead.
