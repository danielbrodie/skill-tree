---
description: Provision the right skills into THIS project's .claude/skills/. Reads project signals (CLAUDE.md, package manifest, languages) and the global catalog, then picks 5-10 skills that fit. USE WHEN the user is in a project root and wants per-project skills instead of the global catalog.
---

This command provisions a per-project skill set into the current project. You are the categorizer.

**Step 1 — list candidates**:

```bash
${CLAUDE_PLUGIN_ROOT}/bin/skill-tree provision --list-candidates
```

Read the JSON output. It has three top-level keys:

- `project` — signals from the project root: detected `languages`, `files` found, and the first 4KB of `CLAUDE.md` if present.
- `catalog` — every skill skill-tree can see, each with a `name`, `description`, and `origin`. **Only entries with `origin: personal` can be provisioned.** Entries with `origin: plugin:...` or `origin: bundled` are managed by their own installer (the plugin marketplace, or Claude Desktop) and `--apply` will reject them — don't pick those.
- `existing` — the project's current `.claude/.skilltree.json` if it already exists, otherwise `null`.

**Step 2 — pick the skills.** Choose 5–10 `origin: personal` skills from `catalog` that match THIS project's signals. Be opinionated. Examples of good reasoning:

- iOS Swift project → `swiftui-pro`, `asc-release-flow`, `asc-xcode-build`, `asc-metadata-sync`. NOT `pp-shopify`, NOT generic web tools.
- Python CLI tool repo → `tdd`, `diagnose`, `improve-codebase-architecture`, `prototype`. Maybe `code-craft` cluster as a meta-skill.
- Plain documentation repo → `caveman`, `write-a-skill`, maybe nothing else.
- The user's own `~/Projects/skill-tree` (THIS repo) → `tdd`, `diagnose`, `improve-codebase-architecture`, `code-craft`, `write-a-skill`, `prototype`.

Skills you **never** want in a project that doesn't need them: large suites of unrelated CLI skills (the `asc-*` set, the `pp-*` set, etc.). Provision the index/root skill of a suite instead of every leaf — e.g. `asc-release-flow` instead of all 17 `asc-*` skills.

If `existing` is non-null, treat it as a starting point. Preserve skills already provisioned unless they no longer fit. Show the user what's being added/removed/kept.

If the project already has a `.claude/skills/` directory with skills in it but no `.skilltree.json` (hand-curated, not skill-tree-managed), `--apply` will warn and add its picks *alongside* the existing skills — it does not replace or remove them. Surface that to the user: after provisioning, `.claude/skills/` will hold both the hand-curated skills and skill-tree's, and only the skill-tree subset is tracked in `.skilltree.json`. `/skill-tree:sync` only ever touches the tracked subset.

**Step 3 — present and confirm.** Output a markdown table:

| Skill | Reason |
|---|---|
| `tdd` | This is a Python repo with pytest in CLAUDE.md — TDD pattern fits |
| `diagnose` | Repo has test-failure debugging in its history |
| ... | ... |

Ask the user to confirm or edit the list.

**Step 4 — apply:**

```bash
${CLAUDE_PLUGIN_ROOT}/bin/skill-tree provision --apply --skills=tdd,diagnose,improve-codebase-architecture --reason="Python+pytest repo; CLAUDE.md emphasizes red-green-refactor"
```

The script copies each chosen skill from `~/.claude/skills/<name>/` into `<project-root>/.claude/skills/<name>/` and writes the manifest at `<project-root>/.claude/.skilltree.json`.

**Step 5 — verify:**

```bash
${CLAUDE_PLUGIN_ROOT}/bin/skill-tree provision --show
```

Confirm the manifest reflects what was applied. Stop.

## Notes

- Copies, not symlinks: this means project-local edits won't fight upstream library changes. Drift is the tradeoff — `/skill-tree:sync` reconciles when you want it.
- This is the new default per-project behavior. The legacy global `/skill-tree:setup` still works for users who want the home-directory cluster mode.
- If invoked from a directory with no project markers (`.git`, `.claude`, `package.json`, `pyproject.toml`, etc.), `provision.py` falls back to the current working directory. Run from the actual project root.
