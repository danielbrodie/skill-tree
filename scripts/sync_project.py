"""Reconcile project manifest drift.

For each skill in `<project>/.claude/.skilltree.json`, compare three hashes:

  - stored_source_hash: SHA256 of the source SKILL.md at copy time, recorded
    in the manifest.
  - source_current_hash: SHA256 of the source SKILL.md right now.
  - project_copy_hash: SHA256 of the project's copy right now.

States and actions:

  - source missing → ORPHAN. --prune removes the project copy; --apply leaves it.
  - project_copy_hash != stored_source_hash → LOCAL_EDIT. Skip unless --overwrite.
  - project_copy_hash == stored_source_hash AND source_current_hash != stored
    → STALE. --apply re-copies; --dry-run lists.
  - All three match → CLEAN. No action.

Usage:
    uv run scripts/sync_project.py --dry-run
    uv run scripts/sync_project.py --apply
    uv run scripts/sync_project.py --apply --prune
    uv run scripts/sync_project.py --apply --overwrite   # clobber local edits (dangerous)
"""

from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from provision import (  # noqa: E402
    find_project_root,
    load_project_manifest,
    write_project_manifest,
    sha256_of_skill_md,
    PROJECT_SKILLS_REL,
)


class DriftState(str, Enum):
    CLEAN = "clean"
    STALE = "stale"
    LOCAL_EDIT = "local_edit"
    ORPHAN = "orphan"
    MISSING_PROJECT_COPY = "missing_project_copy"


@dataclass(frozen=True)
class DriftEntry:
    skill: str
    state: DriftState
    detail: str


def detect_drift(project_root: Path, library: Path) -> list[DriftEntry]:
    manifest = load_project_manifest(project_root)
    if not manifest:
        return []
    out: list[DriftEntry] = []
    project_skills = project_root / PROJECT_SKILLS_REL
    for name, entry in manifest.get("skills", {}).items():
        stored_hash = entry.get("sourceHash")
        source_dir = library / name
        project_copy_dir = project_skills / name

        if not source_dir.is_dir():
            out.append(DriftEntry(name, DriftState.ORPHAN, "source removed from library"))
            continue
        # Treat a source dir without a SKILL.md as ORPHAN-equivalent — without
        # this guard, sha256_of_skill_md returns None below, the missing-source
        # state propagates as STALE, and apply_sync would delete the valid
        # project copy and replace it with an empty source dir.
        if not (source_dir / "SKILL.md").is_file():
            out.append(
                DriftEntry(name, DriftState.ORPHAN, "source SKILL.md missing")
            )
            continue
        if not project_copy_dir.is_dir():
            out.append(
                DriftEntry(name, DriftState.MISSING_PROJECT_COPY, "project copy is gone")
            )
            continue

        source_now = sha256_of_skill_md(source_dir)
        project_now = sha256_of_skill_md(project_copy_dir)

        if stored_hash and project_now != stored_hash:
            out.append(
                DriftEntry(
                    name,
                    DriftState.LOCAL_EDIT,
                    "project copy modified since provision",
                )
            )
            continue

        if source_now != stored_hash:
            out.append(
                DriftEntry(name, DriftState.STALE, "source updated since provision")
            )
            continue

        out.append(DriftEntry(name, DriftState.CLEAN, "matches stored hash"))
    return out


def apply_sync(
    project_root: Path,
    library: Path,
    *,
    prune: bool = False,
    overwrite_local: bool = False,
) -> dict[str, list[str]]:
    """Reconcile drift. Returns {action: [skill_names]}."""
    manifest = load_project_manifest(project_root) or {}
    drift = detect_drift(project_root, library)
    now = datetime.now(timezone.utc).isoformat()
    project_skills = project_root / PROJECT_SKILLS_REL

    actions: dict[str, list[str]] = {
        "re-copied": [],
        "pruned": [],
        "skipped-local-edit": [],
        "restored-missing": [],
    }
    skills = manifest.setdefault("skills", {})
    audit = manifest.setdefault("auditLog", [])

    for d in drift:
        entry = skills.get(d.skill, {})
        src = library / d.skill
        dst = project_skills / d.skill

        if d.state is DriftState.ORPHAN:
            if prune:
                if dst.is_dir():
                    shutil.rmtree(dst)
                skills.pop(d.skill, None)
                audit.append({"at": now, "action": "pruned", "skill": d.skill})
                actions["pruned"].append(d.skill)
            continue

        if d.state is DriftState.LOCAL_EDIT:
            if not overwrite_local:
                actions["skipped-local-edit"].append(d.skill)
                continue
            # Fall through to re-copy

        if d.state in {
            DriftState.STALE,
            DriftState.MISSING_PROJECT_COPY,
        } or (d.state is DriftState.LOCAL_EDIT and overwrite_local):
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst, symlinks=False)
            new_hash = sha256_of_skill_md(src)
            entry["sourceHash"] = new_hash
            entry["syncedAt"] = now
            audit.append({"at": now, "action": "synced", "skill": d.skill})
            if d.state is DriftState.MISSING_PROJECT_COPY:
                actions["restored-missing"].append(d.skill)
            else:
                actions["re-copied"].append(d.skill)

    manifest["syncedAt"] = now
    write_project_manifest(project_root, manifest)
    return actions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=None)
    parser.add_argument(
        "--skills-library", default=str(Path.home() / ".claude" / "skills")
    )

    sub = parser.add_mutually_exclusive_group(required=True)
    sub.add_argument("--dry-run", action="store_true", help="Show drift, do nothing")
    sub.add_argument("--apply", action="store_true", help="Reconcile drift")

    parser.add_argument(
        "--prune",
        action="store_true",
        help="With --apply, also remove project copies whose source is gone",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="With --apply, clobber project-local edits (dangerous)",
    )

    args = parser.parse_args()
    project_root = (
        Path(args.project_root) if args.project_root else find_project_root(Path.cwd())
    )
    library = Path(args.skills_library)

    manifest = load_project_manifest(project_root)
    if not manifest:
        print(
            f"(no .claude/.skilltree.json under {project_root} — nothing to sync)",
            file=sys.stderr,
        )
        return 1

    drift = detect_drift(project_root, library)

    if args.dry_run:
        print(f"# Sync preview — project: {project_root}\n")
        print(f"Source library: {library}\n")
        if not drift:
            print("(manifest empty)")
            return 0
        print(f"| Skill | State | Detail |")
        print(f"|---|---|---|")
        for d in drift:
            print(f"| `{d.skill}` | {d.state.value} | {d.detail} |")
        print()
        non_clean = [d for d in drift if d.state is not DriftState.CLEAN]
        print(f"Total skills: {len(drift)}. Drifted: {len(non_clean)}.")
        if non_clean:
            print(
                "Run with --apply to reconcile. Use --prune to remove orphans, "
                "--overwrite to clobber local edits."
            )
        return 0

    if args.apply:
        result = apply_sync(
            project_root,
            library,
            prune=args.prune,
            overwrite_local=args.overwrite,
        )
        for action, names in result.items():
            if names:
                print(f"## {action} ({len(names)})")
                for n in names:
                    print(f"  - {n}")
        print()
        print(f"Project manifest updated at {project_root / '.claude' / '.skilltree.json'}")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
