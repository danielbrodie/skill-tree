---
description: Survey the entire skill ecosystem on this machine — every registry, every installer's lock file, every cluster manifest — and produce a ranked list of findings with safe-action proposals. USE WHEN the user asks "audit my skills", "what's going on with my skill setup", "clean up my skill installs", or mentions confusion about where skills live.
---

You are the audit diagnostician. The failure-mode *detection* is now deterministic code (`skill-tree doctor`); your job is to run it, merge it with the manifest and dead-inventory checks, present a ranked picture, and apply fixes safely with the user.

Before you start, **read these two docs** — they explain each signature and hold the per-installer fix commands:

1. `${CLAUDE_PLUGIN_ROOT}/docs/registry-map.md` — every place skills can live on a machine
2. `${CLAUDE_PLUGIN_ROOT}/docs/ecosystem-map.md` — platforms, packagers, installers, frontmatter, and the numbered failure-mode signatures

## Step 1 — run the deterministic scan

```bash
${CLAUDE_PLUGIN_ROOT}/bin/skill-tree doctor --json
```

This walks every registry and returns a JSON `findings` array. Each finding carries `signature_id` (matches the numbered signatures in `ecosystem-map.md`), `severity` (error/warning/info), `observation`, `suggested_fix`, `confidence`, and `paths`. Findings are pre-ranked (error → warning → info). The doctor covers the deterministic signatures:

- **#1** vercel-labs fan-out to agents not installed here
- **#2** plugin-cache version skew (a version dir present but unreferenced in `installed_plugins.json`)
- **#4** symlink rot (`~/.claude/skills/*` → missing target)
- **#5** skill in `~/.agents/skills` not linked into `~/.claude/skills` (info — scope vs missing fan-out)
- **#7** same skill name in two registries (resolver picks one arbitrarily)

## Step 2 — add the checks the doctor doesn't cover

```bash
# Signature #3 — skill-tree's own cluster-manifest integrity (only if a manifest exists)
${CLAUDE_PLUGIN_ROOT}/bin/skill-tree check

# Signature #8 — dead inventory: installed but not invoked over the window
${CLAUDE_PLUGIN_ROOT}/bin/skill-tree archive --list --window-days 60
```

`check` validates the manifest graph; `doctor` validates the machine. They're complementary — run both. Signature **#6** (`disable-model-invocation` orphan) is a manifest concept and is reported by `check`. Signature **#9** (`/reload-plugins` only refreshes the plugin tier) is advisory, not a scannable state — mention it only if the user's symptom matches.

## Step 3 — present each finding with its safe action

Merge the doctor findings with `check` / `archive` output, keep the doctor's ranking, and show the top 5–10. For each:

- **What** — the `observation` (already has concrete paths)
- **Why** — cite the `signature_id` so the user can read the full description in `ecosystem-map.md`
- **Safe action** — the `suggested_fix`, cross-checked against `ecosystem-map.md` § "Installers"

## Step 4 — apply, with confirmation, never blind

Walk findings one at a time. Apply only on a clear yes; record applied actions to the audit log; skip cleanly when declined.

> Finding: symlink rot on `ghost` → `~/.agents/skills/ghost` (gone). Safe action: `rm ~/.claude/skills/ghost`. Apply? (y/n/skip)

**Version-skew findings (#2) demand extra care.** A `medium`-confidence cache-skew finding means a version dir is *unreferenced*, not provably *dead* — on some machines the newer unreferenced dir is the one actually loading. Run the finding's verification step (`claude plugin details <plugin>@<marketplace>`) and confirm which version is live **before** removing anything. Never pipe `doctor` findings straight into `rm -rf`.

**Report-only findings are valid.** Dead inventory (#8) is often intentional reserves for infrequent workflows — surface it, explain, move on. Don't fabricate an action for the sake of having one.

## Notes

- When you hit a registry, packager, or installer not in `ecosystem-map.md`, name it in your output and recommend a PR to add it — and, if it's a deterministically-detectable signature, a PR to add a detector to `scripts/doctor.py`. The doc and the doctor only stay current that way.
- For destructive actions, default to the least-destructive equivalent (archive over `rm` when `unarchive` exists).
