# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""skill-tree init: bootstrap manifest.json and detect existing skills.

Creates manifest.json with empty clusters. Populates standalones from
skills already in the scan path. No-op if manifest already exists.

Flags:
  --skills-dir  override scan path (default: ~/.claude/skills)
  --library-dir override library path (default: ~/.claude/skills-library)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.manifest import (
    Manifest,
    empty_manifest,
    save_manifest,
)
from lib.skillfile import scan_skills_dir


# ---------------------------------------------------------------------------
# ANSI
# ---------------------------------------------------------------------------


class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    @classmethod
    def disable(cls) -> None:
        for attr in ("GREEN", "YELLOW", "BOLD", "RESET"):
            setattr(cls, attr, "")


if not sys.stdout.isatty():
    Colors.disable()


# ---------------------------------------------------------------------------
# Init logic
# ---------------------------------------------------------------------------


def init_manifest(
    skills_dir: Path,
    library_dir: Path,
    manifest_path: Path,
) -> None:
    if manifest_path.exists():
        print(f"{Colors.YELLOW}Manifest already exists:{Colors.RESET} {manifest_path}")
        print("No changes made.")
        return

    # Detect existing skills
    scan_skills = scan_skills_dir(skills_dir)
    lib_skills = scan_skills_dir(library_dir)

    # All scan-path skills become standalones initially
    standalones = tuple(sorted(scan_skills.keys()))

    manifest = Manifest(standalones=standalones)

    # Write
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    save_manifest(manifest, manifest_path)

    print(f"{Colors.GREEN}Created manifest.json{Colors.RESET} at {manifest_path}")
    print(f"Detected {len(scan_skills)} skills in {skills_dir} (added as standalones)")
    print(f"Detected {len(lib_skills)} skills in {library_dir}")
    print()
    print(f"Run {Colors.BOLD}`skill-tree scan`{Colors.RESET} to propose a cluster structure.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="skill-tree init: bootstrap manifest")
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
    args = parser.parse_args()

    manifest_path = args.library_dir / "skill-tree" / "manifest.json"
    init_manifest(args.skills_dir, args.library_dir, manifest_path)


if __name__ == "__main__":
    main()
