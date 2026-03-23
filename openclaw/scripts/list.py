# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""skill-tree list: show current graph state with token estimate.

Flags:
  --library-dir override library path (default: ~/.claude/skills-library)
  --manifest    override manifest path
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.manifest import (
    Manifest,
    estimate_catalog_tokens,
    load_manifest,
    total_skill_count,
)


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
# Display
# ---------------------------------------------------------------------------


def display_graph(manifest: Manifest) -> None:
    total = total_skill_count(manifest)
    tokens = estimate_catalog_tokens(manifest)

    print(f"{Colors.BOLD}skill-tree{Colors.RESET} v{manifest.version} — {total} skills managed")
    print()

    # Clusters
    if manifest.clusters:
        print(f"{Colors.BOLD}Clusters ({len(manifest.clusters)}):{Colors.RESET}")
        for name, cluster in sorted(manifest.clusters.items()):
            leaf_count = len(cluster.leaves)
            # Extract key terms from description (first few words)
            desc_preview = cluster.description[:60]
            if len(cluster.description) > 60:
                desc_preview += "..."
            print(
                f"  {Colors.CYAN}{name:<24}{Colors.RESET} "
                f"{leaf_count:>2} leaves   {Colors.DIM}{desc_preview}{Colors.RESET}"
            )
        print()

    # Standalones
    if manifest.standalones:
        print(f"{Colors.BOLD}Standalones ({len(manifest.standalones)}):{Colors.RESET}")
        print(f"  {', '.join(manifest.standalones)}")
        print()

    # Hot path
    if manifest.hot_path:
        print(f"{Colors.BOLD}Hot path ({len(manifest.hot_path)}):{Colors.RESET} {', '.join(manifest.hot_path)}")

    # Reference nodes
    if manifest.reference_nodes:
        print(
            f"{Colors.BOLD}Reference nodes ({len(manifest.reference_nodes)}):{Colors.RESET} "
            f"{', '.join(manifest.reference_nodes)}"
        )

    # Deprecated
    if manifest.deprecated:
        print(
            f"{Colors.BOLD}Deprecated ({len(manifest.deprecated)}):{Colors.RESET} "
            f"{', '.join(manifest.deprecated)}"
        )

    print()
    print(f"Session token estimate: ~{tokens:,} tokens")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="skill-tree list: show graph state")
    parser.add_argument(
        "--library-dir",
        type=Path,
        default=Path.home() / ".claude" / "skills-library",
    )
    parser.add_argument("--manifest", type=Path, default=None)
    args = parser.parse_args()

    manifest_path = args.manifest or (args.library_dir / "skill-tree" / "manifest.json")

    if not manifest_path.exists():
        print(f"Manifest not found: {manifest_path}", file=sys.stderr)
        print("Run `skill-tree init` first.", file=sys.stderr)
        sys.exit(1)

    manifest = load_manifest(manifest_path)
    display_graph(manifest)


if __name__ == "__main__":
    main()
