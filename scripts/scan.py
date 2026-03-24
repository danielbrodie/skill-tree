# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""skill-tree scan: collect all skill descriptions for clustering.

Reads all SKILL.md files and outputs their names and descriptions.
The model reading this output does the actual clustering.

Flags:
  --skills-dir    override scan path (default: ~/.claude/skills)
  --library-dir   override library path (default: ~/.claude/skills-library)
  --format        output format: text (default) or json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.manifest import (
    Manifest,
    all_managed_skills,
    load_manifest,
)
from lib.skillfile import get_description, get_name, parse_frontmatter, scan_skills_dir


# ---------------------------------------------------------------------------
# ANSI
# ---------------------------------------------------------------------------


class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    @classmethod
    def disable(cls) -> None:
        for attr in ("GREEN", "YELLOW", "CYAN", "BOLD", "DIM", "RESET"):
            setattr(cls, attr, "")


if not sys.stdout.isatty():
    Colors.disable()


# ---------------------------------------------------------------------------
# Collect
# ---------------------------------------------------------------------------


def collect_skill_descriptions(
    skills_dir: Path, library_dir: Path
) -> list[dict[str, str]]:
    """Collect name + description for every skill on disk."""
    skills: list[dict[str, str]] = []
    seen: set[str] = set()

    for dir_path in (skills_dir, library_dir):
        if not dir_path.is_dir():
            continue
        for name, path in sorted(scan_skills_dir(dir_path).items()):
            if name in seen:
                continue
            seen.add(name)
            fm = parse_frontmatter(path)
            desc = get_description(fm) or ""
            skills.append({"name": name, "description": desc})

    return skills


def find_new_skills(
    all_skills: list[dict[str, str]],
    manifest: Manifest,
) -> list[dict[str, str]]:
    """Return skills not tracked in the manifest."""
    managed = set(all_managed_skills(manifest).keys())
    return [s for s in all_skills if s["name"] not in managed]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="skill-tree scan: collect skill descriptions")
    parser.add_argument(
        "--skills-dir",
        type=Path,
        default=Path.home() / ".claude" / "skills",
    )
    parser.add_argument(
        "--library-dir",
        type=Path,
        default=Path.home() / ".claude" / "skills-library",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="output format",
    )
    args = parser.parse_args()

    manifest_path = args.library_dir / "skill-tree" / "manifest.json"

    # Collect all skills
    all_skills = collect_skill_descriptions(args.skills_dir, args.library_dir)
    if not all_skills:
        print("No skills found.", file=sys.stderr)
        sys.exit(1)

    # If manifest exists, show what's new vs tracked
    new_only = []
    if manifest_path.exists():
        manifest = load_manifest(manifest_path)
        new_only = find_new_skills(all_skills, manifest)

    if args.format == "json":
        output = {
            "total": len(all_skills),
            "new": len(new_only),
            "skills": all_skills,
        }
        if new_only:
            output["new_skills"] = new_only
        print(json.dumps(output, indent=2))
    else:
        print(f"{Colors.BOLD}{len(all_skills)} skills found.{Colors.RESET}")
        if manifest_path.exists() and new_only:
            print(f"{Colors.CYAN}{len(new_only)} new (not in manifest).{Colors.RESET}\n")
        elif manifest_path.exists():
            print(f"{Colors.GREEN}All skills are tracked in the manifest.{Colors.RESET}\n")
        print()
        for s in all_skills:
            desc = s["description"][:80] + "..." if len(s["description"]) > 80 else s["description"]
            print(f"  {Colors.CYAN}{s['name']:<30}{Colors.RESET} {Colors.DIM}{desc}{Colors.RESET}")


if __name__ == "__main__":
    main()
