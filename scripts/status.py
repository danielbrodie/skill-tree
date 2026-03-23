# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""skill-tree status: combined health check + graph overview with token savings.

Shows validation results, graph summary, and token savings in one view.

Flags:
  --skills-dir  override scan path (default: ~/.claude/skills)
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
    all_managed_skills,
    estimate_catalog_tokens,
    load_manifest,
    total_skill_count,
)
from lib.skillfile import (
    get_description,
    has_always_true,
    is_disabled,
    parse_frontmatter,
    scan_skills_dir,
)


# ---------------------------------------------------------------------------
# ANSI
# ---------------------------------------------------------------------------


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    @classmethod
    def disable(cls) -> None:
        for attr in ("GREEN", "RED", "YELLOW", "CYAN", "BOLD", "DIM", "RESET"):
            setattr(cls, attr, "")


if not sys.stdout.isatty():
    Colors.disable()


# ---------------------------------------------------------------------------
# Validation (inlined from check.py)
# ---------------------------------------------------------------------------


def run_checks(
    manifest: Manifest,
    skills_dir: Path,
    library_dir: Path,
) -> tuple[list[str], list[str]]:
    """Run all validation checks. Returns (errors, warnings)."""
    errors: list[str] = []
    warnings: list[str] = []
    managed = all_managed_skills(manifest)

    # dead-reference
    for cluster in manifest.clusters.values():
        for leaf_name in cluster.leaves:
            path = library_dir / leaf_name / "SKILL.md"
            if not path.exists():
                errors.append(f"dead-reference: {leaf_name} in cluster {cluster.name}")

    # uniqueness-violation
    for name, locs in managed.items():
        if len(locs) > 1 and not (len(locs) == 2 and "clusters (router)" in locs):
            errors.append(f"uniqueness-violation: {name} in {', '.join(locs)}")

    # leaf-not-disabled
    for cluster in manifest.clusters.values():
        for leaf_name in cluster.leaves:
            path = library_dir / leaf_name / "SKILL.md"
            if path.exists():
                fm = parse_frontmatter(path)
                if not is_disabled(fm):
                    errors.append(f"leaf-not-disabled: {leaf_name}")

    # always-on-leaf
    for cluster in manifest.clusters.values():
        for leaf_name in cluster.leaves:
            path = library_dir / leaf_name / "SKILL.md"
            if path.exists():
                fm = parse_frontmatter(path)
                if has_always_true(fm):
                    errors.append(f"always-on-leaf: {leaf_name}")

    # orphaned-disabled
    library_skills = scan_skills_dir(library_dir)
    for name, path in library_skills.items():
        fm = parse_frontmatter(path)
        if is_disabled(fm) and name not in managed:
            warnings.append(f"orphaned-disabled: {name}")

    # unclustered-over-budget
    visible = len(manifest.clusters) + len(manifest.standalones) + len(manifest.hot_path)
    if visible > manifest.unclustered_budget:
        warnings.append(f"unclustered-over-budget: {visible} visible (budget: {manifest.unclustered_budget})")

    # cluster-too-large
    for cluster in manifest.clusters.values():
        if len(cluster.leaves) > 15:
            warnings.append(f"cluster-too-large: {cluster.name} ({len(cluster.leaves)} leaves)")

    # crossref-missing
    for cluster in manifest.clusters.values():
        for ref in cluster.cross_references:
            ref_path = library_dir / ref.skill / "SKILL.md"
            scan_path = skills_dir / ref.skill / "SKILL.md"
            if not ref_path.exists() and not scan_path.exists():
                warnings.append(f"crossref-missing: {ref.skill} in {cluster.name}")

    # no-description
    for cluster in manifest.clusters.values():
        for leaf_name, leaf in cluster.leaves.items():
            if not leaf.routing_hint:
                path = library_dir / leaf_name / "SKILL.md"
                if path.exists():
                    fm = parse_frontmatter(path)
                    if not get_description(fm):
                        warnings.append(f"no-description: {leaf_name}")

    return errors, warnings


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------


def display_status(
    manifest: Manifest,
    errors: list[str],
    warnings: list[str],
) -> None:
    total = total_skill_count(manifest)
    cluster_tokens = estimate_catalog_tokens(manifest)
    flat_tokens = total * 100  # ~100 tokens per skill description

    # Header
    print(f"{Colors.BOLD}skill-tree{Colors.RESET} — {total} skills managed\n")

    # Token savings
    if flat_tokens > 0:
        reduction = ((flat_tokens - cluster_tokens) / flat_tokens) * 100
        print(f"  Flat catalog:    ~{flat_tokens:,} tokens")
        print(f"  With skill-tree: ~{cluster_tokens:,} tokens ({Colors.GREEN}{reduction:.0f}% reduction{Colors.RESET})")
        print()

    # Clusters
    if manifest.clusters:
        print(f"{Colors.BOLD}Clusters ({len(manifest.clusters)}):{Colors.RESET}")
        for name, cluster in sorted(manifest.clusters.items()):
            leaf_count = len(cluster.leaves)
            desc_preview = cluster.description[:55]
            if len(cluster.description) > 55:
                desc_preview += "..."
            print(
                f"  {Colors.CYAN}{name:<22}{Colors.RESET} "
                f"{leaf_count:>2} leaves   {Colors.DIM}{desc_preview}{Colors.RESET}"
            )
        print()

    # Compact summary of other categories
    parts: list[str] = []
    if manifest.standalones:
        parts.append(f"{len(manifest.standalones)} standalones")
    if manifest.hot_path:
        parts.append(f"{len(manifest.hot_path)} hot path")
    if manifest.reference_nodes:
        parts.append(f"{len(manifest.reference_nodes)} reference")
    if manifest.deprecated:
        parts.append(f"{len(manifest.deprecated)} deprecated")
    if parts:
        print(f"{Colors.DIM}{' · '.join(parts)}{Colors.RESET}\n")

    # Health
    if errors:
        print(f"{Colors.RED}{Colors.BOLD}{len(errors)} error(s):{Colors.RESET}")
        for e in errors:
            print(f"  {Colors.RED}✗{Colors.RESET} {e}")
        print()

    if warnings:
        print(f"{Colors.YELLOW}{len(warnings)} warning(s):{Colors.RESET}")
        for w in warnings:
            print(f"  {Colors.YELLOW}⚠{Colors.RESET} {w}")
        print()

    if not errors and not warnings:
        print(f"{Colors.GREEN}No issues found.{Colors.RESET}\n")
    elif not errors:
        print(f"{Colors.GREEN}No errors.{Colors.RESET} Run /setup to address warnings.\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="skill-tree status: health check + graph overview")
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
    parser.add_argument("--manifest", type=Path, default=None)
    args = parser.parse_args()

    manifest_path = args.manifest or (args.library_dir / "skill-tree" / "manifest.json")

    if not manifest_path.exists():
        print(f"No manifest found at {manifest_path}", file=sys.stderr)
        print("Run /setup to get started.", file=sys.stderr)
        sys.exit(1)

    manifest = load_manifest(manifest_path)
    errors, warnings = run_checks(manifest, args.skills_dir, args.library_dir)
    display_status(manifest, errors, warnings)

    if errors:
        sys.exit(2)
    elif warnings:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
