---
description: Reconcile a project's .claude/skills/ with the global library after upstream changes. USE WHEN the user mentions skill drift, wants to update project-provisioned skills, asks about /skill-tree:sync, or after they've made changes to ~/.claude/skills/ that should propagate to projects.
---

This command reconciles drift between a project's `.claude/skills/` and the source library at `~/.claude/skills/`.

**Step 1 — show what's drifted:**

```bash
${CLAUDE_PLUGIN_ROOT}/bin/skill-tree sync-project --dry-run
```

The output is a table with one row per skill in the project manifest:

- `clean` — source and project copy match. No action.
- `stale` — source has been updated since provisioning. Safe to re-copy.
- `local_edit` — the project's copy has been edited locally. Skip by default to preserve the user's work.
- `orphan` — source no longer exists in the global library. Candidate for prune.
- `missing_project_copy` — manifest references a skill but the project copy is gone. Will be restored.

**Step 2 — show the user the table, ask how to proceed.** Three options:

- **Apply only safe changes** — re-copy stale, restore missing, leave local edits alone:
  ```bash
  ${CLAUDE_PLUGIN_ROOT}/bin/skill-tree sync-project --apply
  ```

- **Also prune orphans** — additionally remove project copies whose source is gone:
  ```bash
  ${CLAUDE_PLUGIN_ROOT}/bin/skill-tree sync-project --apply --prune
  ```

- **Force overwrite local edits** — dangerous, clobbers user changes:
  ```bash
  ${CLAUDE_PLUGIN_ROOT}/bin/skill-tree sync-project --apply --overwrite
  ```

Default to `--apply` (option 1) unless the user explicitly asks for orphan removal or overwrite. The audit log in `.claude/.skilltree.json` records every action.

**Step 3 — verify:**

```bash
${CLAUDE_PLUGIN_ROOT}/bin/skill-tree sync-project --dry-run
```

If everything is clean, sync is done.
