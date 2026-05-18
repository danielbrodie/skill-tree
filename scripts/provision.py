"""Per-project skill provisioning — the BRO-182 implementation.

The shape mirrors `setup.py`'s "the model is the algorithm" pattern:
- `--list-candidates` emits machine-readable project signals + global skill catalog
- `--apply --skills=a,b,c [--reason '...']` does the file operations
- `--show` prints the current project manifest

Project manifest location: `<cwd>/.claude/.skilltree.json`
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_MANIFEST_REL = ".claude/.skilltree.json"
PROJECT_SKILLS_REL = ".claude/skills"


def find_project_root(start: Path) -> Path:
    """Find the project root from start dir. Looks for .git/, .claude/, or common manifests.

    Falls back to cwd if no marker found.
    """
    markers = {".git", ".claude", "package.json", "pyproject.toml", "Cargo.toml", "go.mod"}
    cur = start.resolve()
    while cur != cur.parent:
        if any((cur / m).exists() for m in markers):
            return cur
        cur = cur.parent
    return start.resolve()


def collect_project_signals(root: Path) -> dict:
    """Read project signals: CLAUDE.md content + manifest filenames + language hints."""
    signals: dict = {"root": str(root), "files": [], "claudeMd": None, "languages": set()}

    interesting_names = {
        "CLAUDE.md", "AGENTS.md", "README.md", "README",
        "package.json", "pyproject.toml", "Cargo.toml", "go.mod",
        "Gemfile", "build.gradle", "build.gradle.kts", "Podfile",
        "requirements.txt", "Pipfile", "deno.json", "bun.lockb",
    }
    lang_map = {
        "package.json": "javascript", "deno.json": "typescript", "bun.lockb": "typescript",
        "pyproject.toml": "python", "requirements.txt": "python", "Pipfile": "python",
        "Cargo.toml": "rust", "go.mod": "go", "Gemfile": "ruby",
        "build.gradle": "kotlin", "build.gradle.kts": "kotlin", "Podfile": "swift",
    }

    for name in interesting_names:
        p = root / name
        if not p.exists():
            continue
        signals["files"].append(name)
        if name in lang_map:
            signals["languages"].add(lang_map[name])
        if name == "CLAUDE.md":
            try:
                signals["claudeMd"] = p.read_text()[:4000]
            except (OSError, UnicodeDecodeError):
                pass

    # Detect language by file extension (light pass — top-level only)
    ext_to_lang = {".swift": "swift", ".ts": "typescript", ".tsx": "typescript",
                   ".py": "python", ".rs": "rust", ".go": "go", ".rb": "ruby"}
    for child in root.iterdir():
        if child.is_file() and child.suffix in ext_to_lang:
            signals["languages"].add(ext_to_lang[child.suffix])

    signals["languages"] = sorted(signals["languages"])
    return signals


def collect_global_catalog(skills_dir: Path) -> list[dict]:
    """List every skill in the global library with its name+description."""
    out: list[dict] = []
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        try:
            text = skill_md.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        name = skill_dir.name
        desc = ""
        in_fm = False
        for line in text.splitlines():
            if line.strip() == "---":
                if not in_fm:
                    in_fm = True
                    continue
                break
            if in_fm and line.startswith("description:"):
                desc = line.split(":", 1)[1].strip().strip('"')
        out.append({"name": name, "description": desc, "path": str(skill_dir)})
    return out


def load_project_manifest(root: Path) -> dict | None:
    p = root / PROJECT_MANIFEST_REL
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def write_project_manifest(root: Path, manifest: dict) -> None:
    p = root / PROJECT_MANIFEST_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(manifest, indent=2) + "\n")


def apply_skills(
    root: Path, skill_names: list[str], reason: str, skills_dir: Path
) -> dict:
    """Copy each named skill into the project's .claude/skills/, update manifest."""
    now = datetime.now(timezone.utc).isoformat()
    manifest = load_project_manifest(root) or {
        "version": "1.0",
        "sourceLibrary": str(skills_dir),
        "skills": {},
        "auditLog": [],
    }
    manifest["syncedAt"] = now

    project_skills_dir = root / PROJECT_SKILLS_REL
    project_skills_dir.mkdir(parents=True, exist_ok=True)

    added: list[str] = []
    for name in skill_names:
        src = skills_dir / name
        if not src.is_dir():
            print(f"warn: skill not found in library: {name}", file=sys.stderr)
            continue
        dst = project_skills_dir / name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, symlinks=False)
        manifest["skills"][name] = {
            "source": str(src),
            "reason": reason,
            "syncedAt": now,
        }
        manifest["auditLog"].append(
            {"at": now, "action": "added", "skill": name, "reason": reason}
        )
        added.append(name)

    write_project_manifest(root, manifest)
    return {"added": added, "manifest": manifest}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-root",
        default=None,
        help="Override the auto-detected project root",
    )
    parser.add_argument(
        "--skills-library",
        default=str(Path.home() / ".claude" / "skills"),
    )

    sub = parser.add_mutually_exclusive_group(required=True)
    sub.add_argument(
        "--list-candidates",
        action="store_true",
        help="Emit project signals + global catalog as JSON for the model to read",
    )
    sub.add_argument(
        "--apply",
        action="store_true",
        help="Copy --skills into the project's .claude/skills/",
    )
    sub.add_argument(
        "--show",
        action="store_true",
        help="Print the current project manifest",
    )

    parser.add_argument(
        "--skills",
        default="",
        help="Comma-separated skill names (with --apply)",
    )
    parser.add_argument(
        "--reason",
        default="",
        help="Why these skills (with --apply, recorded in manifest)",
    )

    args = parser.parse_args()

    root = Path(args.project_root) if args.project_root else find_project_root(Path.cwd())
    skills_dir = Path(args.skills_library)

    if args.list_candidates:
        signals = collect_project_signals(root)
        catalog = collect_global_catalog(skills_dir)
        existing = load_project_manifest(root)
        print(json.dumps({
            "project": signals,
            "catalog": catalog,
            "existing": existing,
        }, indent=2))
        return 0

    if args.apply:
        names = [s.strip() for s in args.skills.split(",") if s.strip()]
        if not names:
            print("error: --apply requires --skills", file=sys.stderr)
            return 2
        result = apply_skills(root, names, args.reason, skills_dir)
        print(json.dumps(result, indent=2))
        return 0

    if args.show:
        m = load_project_manifest(root)
        if not m:
            print(f"(no manifest at {root / PROJECT_MANIFEST_REL})")
            return 1
        print(json.dumps(m, indent=2))
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
