"""Auto-archive unused personal skills.

ADR 0002 says the global base layer should hold the top-N most-invoked skills.
Skills with zero invocations over a configurable window are dead weight in every
session's prelude. This script identifies them and offers to archive them out.

Non-destructive: archived skills are moved to ~/.claude/skills-archive-<date>/,
not deleted. Restore with --unarchive <name>.

Usage:
    uv run scripts/archive.py --list                       # show candidates + last-use date
    uv run scripts/archive.py --apply --window-days 60     # archive skills unused in 60d
    uv run scripts/archive.py --unarchive <name>           # restore from latest archive
"""

from __future__ import annotations

import argparse
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from measure import build_corpus  # noqa: E402


def last_invocation_by_skill(records) -> dict[str, str]:
    """For each skill, return the most recent invocation timestamp."""
    out: dict[str, str] = {}
    for r in records:
        cur = out.get(r.skill)
        if cur is None or r.timestamp > cur:
            out[r.skill] = r.timestamp
    return out


def manifest_referenced_skills(manifest_path: Path) -> set[str]:
    """Return the set of skill names that appear anywhere in the skill-tree manifest.

    Archiving a manifest-referenced skill would break cluster routing. The archive
    command treats these as off-limits even if they have zero invocations.
    """
    import json
    if not manifest_path.exists():
        return set()
    try:
        m = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError):
        return set()
    referenced: set[str] = set()
    # Cluster keys themselves are router-skill names that live in ~/.claude/skills/.
    # Archiving the router breaks the whole cluster.
    referenced.update(m.get("clusters", {}).keys())
    for cluster in m.get("clusters", {}).values():
        referenced.update(cluster.get("leaves", {}).keys())
    referenced.update(m.get("standalones", []))
    referenced.update(m.get("hotPath", []))
    referenced.update(m.get("referenceNodes", []))
    return referenced


def list_unused_personal_skills(
    skills_dir: Path,
    last_used: dict[str, str],
    window_days: int,
    manifest_referenced: set[str] | None = None,
) -> list[tuple[str, str | None, bool]]:
    """Return [(skill_name, last_iso_or_None, is_manifest_referenced)] for personal
    skills not invoked in window. The third element flags skills the archive command
    should refuse to move because they're load-bearing in the skill-tree manifest.
    """
    if not skills_dir.exists():
        return []
    now = datetime.now(tz=timezone.utc)
    cutoff = (now - __import__("datetime").timedelta(days=window_days)).isoformat()
    refs = manifest_referenced or set()

    out: list[tuple[str, str | None, bool]] = []
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        if not (skill_dir / "SKILL.md").exists():
            continue
        name = skill_dir.name
        ts = last_used.get(name)
        if ts is None or ts < cutoff:
            out.append((name, ts, name in refs))
    return out


def archive_skills(skills_dir: Path, names: list[str], archive_root: Path) -> list[str]:
    archive_root.mkdir(parents=True, exist_ok=True)
    moved: list[str] = []
    for name in names:
        src = skills_dir / name
        if not src.is_dir():
            continue
        dst = archive_root / name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.move(str(src), str(dst))
        moved.append(name)
    return moved


def find_latest_archive(skills_dir_parent: Path) -> Path | None:
    """Find the most recently-created skills-archive-* directory."""
    candidates = sorted(
        (p for p in skills_dir_parent.iterdir() if p.is_dir() and p.name.startswith("skills-archive-")),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def unarchive(skill_name: str, skills_dir: Path) -> bool:
    """Restore a skill from the latest archive. Returns True on success."""
    archive = find_latest_archive(skills_dir.parent)
    if archive is None:
        return False
    src = archive / skill_name
    if not src.is_dir():
        # Maybe in an older archive
        for older in skills_dir.parent.iterdir():
            if older.is_dir() and older.name.startswith("skills-archive-"):
                candidate = older / skill_name
                if candidate.is_dir():
                    src = candidate
                    break
        else:
            return False
    dst = skills_dir / skill_name
    if dst.exists():
        return False  # don't clobber
    shutil.move(str(src), str(dst))
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skills-dir",
        default=str(Path.home() / ".claude" / "skills"),
    )
    parser.add_argument("--days", type=int, default=60, help="Lookback for usage")
    parser.add_argument("--window-days", type=int, default=60, help="Archive threshold")

    sub = parser.add_mutually_exclusive_group(required=True)
    sub.add_argument("--list", action="store_true", help="Show archive candidates")
    sub.add_argument("--apply", action="store_true", help="Move unused skills to archive")
    sub.add_argument("--unarchive", metavar="NAME", help="Restore a skill from archive")

    parser.add_argument(
        "--force-manifest-referenced",
        action="store_true",
        help="Archive even skills referenced in the skill-tree manifest (will break routing)",
    )

    args = parser.parse_args()
    skills_dir = Path(args.skills_dir)

    if args.unarchive:
        ok = unarchive(args.unarchive, skills_dir)
        if ok:
            print(f"Restored {args.unarchive} to {skills_dir}/")
            return 0
        else:
            print(f"error: could not restore {args.unarchive}", file=sys.stderr)
            return 1

    projects_root = Path.home() / ".claude" / "projects"
    records = build_corpus(projects_root, args.days)
    last_used = last_invocation_by_skill(records)
    manifest_path = (
        Path.home() / ".claude" / "skills-library" / "skill-tree" / "manifest.json"
    )
    manifest_refs = manifest_referenced_skills(manifest_path)
    candidates = list_unused_personal_skills(
        skills_dir, last_used, args.window_days, manifest_refs
    )

    if args.list:
        print(f"# Personal-skill archive candidates — unused in last {args.window_days} days\n")
        print(f"Corpus: {len(records)} records, {len(last_used)} skills with at least one invocation\n")
        print(f"Skills directory: {skills_dir}")
        print(f"Manifest: {manifest_path} ({len(manifest_refs)} referenced skills)\n")
        print(f"| Skill | Last invocation | Manifest-referenced? |")
        print(f"|---|---|---|")
        for name, ts, ref in candidates:
            ts_str = ts[:10] if ts else "never (in last %dd)" % args.days
            ref_str = "**yes — protected**" if ref else "no"
            print(f"| `{name}` | {ts_str} | {ref_str} |")
        print()
        archivable = [c for c in candidates if not c[2]]
        protected = [c for c in candidates if c[2]]
        print(f"Total candidates: {len(candidates)} ({len(archivable)} archivable, {len(protected)} protected by manifest)")
        print()
        print("Protected skills are leaves of clusters or otherwise tracked in")
        print("~/.claude/skills-library/skill-tree/manifest.json. Archiving them would")
        print("break the routing graph. Use `--force-manifest-referenced` to override.")
        return 0

    if args.apply:
        archive_root = skills_dir.parent / f"skills-archive-{datetime.now().strftime('%Y-%m-%d-%H%M')}"
        if args.force_manifest_referenced:
            names = [n for n, _, _ in candidates]
        else:
            names = [n for n, _, ref in candidates if not ref]
            protected = [n for n, _, ref in candidates if ref]
            if protected:
                print(
                    f"Skipping {len(protected)} manifest-referenced skills "
                    "(use --force-manifest-referenced to override):",
                    file=sys.stderr,
                )
                for n in protected:
                    print(f"  - {n}", file=sys.stderr)
        if not names:
            print("(no unarchivable skills — everything is either invoked or manifest-protected)")
            return 0
        moved = archive_skills(skills_dir, names, archive_root)
        print(f"Archived {len(moved)} skills to {archive_root}/")
        for name in moved:
            print(f"  - {name}")
        print()
        print(f"To restore any one: `uv run scripts/archive.py --unarchive <name>`")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
