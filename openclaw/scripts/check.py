# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""skill-tree check: validate graph integrity against manifest + filesystem.

9 checks, 3 exit codes:
  0 = clean
  1 = warnings only
  2 = errors found

Flags:
  --quiet       suppress per-check detail, only print summary
  --notify      one-line stderr message if issues found (for SessionStart hook)
  --skills-dir  override scan path (default: ~/.claude/skills)
  --library-dir override library path (default: ~/.claude/skills-library)
  --manifest    override manifest path
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Allow running as script from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.manifest import (
    Manifest,
    all_managed_skills,
    load_manifest,
)
from lib.skillfile import (
    has_always_true,
    is_disabled,
    parse_frontmatter,
    scan_skills_dir,
)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class Severity(Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"


@dataclass
class Issue:
    severity: Severity
    check: str
    message: str
    skill: str = ""


# ---------------------------------------------------------------------------
# ANSI
# ---------------------------------------------------------------------------


class Colors:
    RED = "\033[91m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    @classmethod
    def disable(cls) -> None:
        for attr in ("RED", "YELLOW", "GREEN", "BOLD", "DIM", "RESET"):
            setattr(cls, attr, "")


if not sys.stdout.isatty():
    Colors.disable()


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_dead_references(
    manifest: Manifest, library_dir: Path, skills_dir: Path
) -> list[Issue]:
    """ERROR: Leaf in manifest but no SKILL.md on disk."""
    issues: list[Issue] = []
    for cluster in manifest.clusters.values():
        for leaf_name in cluster.leaves:
            lib_path = library_dir / leaf_name / "SKILL.md"
            scan_path = skills_dir / leaf_name / "SKILL.md"
            if not lib_path.exists() and not scan_path.exists():
                issues.append(
                    Issue(
                        Severity.ERROR,
                        "dead-reference",
                        f"leaf '{leaf_name}' in cluster '{cluster.name}' has no SKILL.md on disk",
                        leaf_name,
                    )
                )
    return issues


def check_uniqueness(manifest: Manifest) -> list[Issue]:
    """ERROR: Skill appears in multiple manifest arrays."""
    issues: list[Issue] = []
    locations = all_managed_skills(manifest)
    for name, locs in locations.items():
        # Filter out "clusters (router)" — a cluster name appearing as a router is fine
        non_router = [loc for loc in locs if loc != "clusters (router)"]
        if len(non_router) > 1:
            issues.append(
                Issue(
                    Severity.ERROR,
                    "uniqueness-violation",
                    f"'{name}' appears in multiple locations: {', '.join(non_router)}",
                    name,
                )
            )
    return issues


def check_leaf_not_disabled(
    manifest: Manifest, library_dir: Path
) -> list[Issue]:
    """ERROR: Clustered leaf without disable-model-invocation: true."""
    issues: list[Issue] = []
    for cluster in manifest.clusters.values():
        for leaf_name in cluster.leaves:
            path = library_dir / leaf_name / "SKILL.md"
            if not path.exists():
                continue  # caught by dead-reference
            fm = parse_frontmatter(path)
            if not is_disabled(fm):
                issues.append(
                    Issue(
                        Severity.ERROR,
                        "leaf-not-disabled",
                        f"leaf '{leaf_name}' missing disable-model-invocation: true",
                        leaf_name,
                    )
                )
    return issues


def check_always_on_leaf(
    manifest: Manifest, library_dir: Path
) -> list[Issue]:
    """ERROR: Leaf with always: true (bypasses architecture)."""
    issues: list[Issue] = []
    for cluster in manifest.clusters.values():
        for leaf_name in cluster.leaves:
            path = library_dir / leaf_name / "SKILL.md"
            if not path.exists():
                continue
            fm = parse_frontmatter(path)
            if has_always_true(fm):
                issues.append(
                    Issue(
                        Severity.ERROR,
                        "always-on-leaf",
                        f"leaf '{leaf_name}' has always: true — bypasses cluster routing",
                        leaf_name,
                    )
                )
    return issues


def check_orphaned_disabled(
    manifest: Manifest, library_dir: Path, skills_dir: Path
) -> list[Issue]:
    """WARNING: Has disable-model-invocation but not in manifest."""
    issues: list[Issue] = []
    managed = all_managed_skills(manifest)

    for dir_path in (skills_dir, library_dir):
        skills = scan_skills_dir(dir_path)
        for name, skillmd_path in skills.items():
            if name in managed:
                continue
            fm = parse_frontmatter(skillmd_path)
            if is_disabled(fm):
                issues.append(
                    Issue(
                        Severity.WARNING,
                        "orphaned-disabled",
                        f"'{name}' has disable-model-invocation but is not in manifest",
                        name,
                    )
                )
    return issues


def check_unclustered_budget(
    manifest: Manifest, skills_dir: Path
) -> list[Issue]:
    """WARNING: More than unclusteredBudget visible skills in scan path."""
    issues: list[Issue] = []
    visible_count = 0
    skills = scan_skills_dir(skills_dir)
    for name, path in skills.items():
        fm = parse_frontmatter(path)
        if not is_disabled(fm):
            visible_count += 1

    budget = manifest.unclustered_budget
    # Clusters + standalones + hot_path = visible skills
    expected_visible = len(manifest.clusters) + len(manifest.standalones) + len(manifest.hot_path)
    if visible_count > budget:
        issues.append(
            Issue(
                Severity.WARNING,
                "unclustered-over-budget",
                f"{visible_count} visible skills in scan path (budget: {budget})",
            )
        )
    return issues


def check_cluster_too_large(manifest: Manifest) -> list[Issue]:
    """WARNING: Cluster has more than 15 leaves."""
    issues: list[Issue] = []
    for cluster in manifest.clusters.values():
        if len(cluster.leaves) > 15:
            issues.append(
                Issue(
                    Severity.WARNING,
                    "cluster-too-large",
                    f"cluster '{cluster.name}' has {len(cluster.leaves)} leaves (max 15)",
                    cluster.name,
                )
            )
    return issues


def check_crossref_missing(
    manifest: Manifest, library_dir: Path, skills_dir: Path
) -> list[Issue]:
    """WARNING: Cross-referenced skill doesn't exist."""
    issues: list[Issue] = []
    for cluster in manifest.clusters.values():
        for ref in cluster.cross_references:
            lib_path = library_dir / ref.skill / "SKILL.md"
            scan_path = skills_dir / ref.skill / "SKILL.md"
            if not lib_path.exists() and not scan_path.exists():
                issues.append(
                    Issue(
                        Severity.WARNING,
                        "crossref-missing",
                        f"cross-reference '{ref.skill}' in cluster '{cluster.name}' not found on disk",
                        ref.skill,
                    )
                )
    return issues


def check_no_description(manifest: Manifest) -> list[Issue]:
    """WARNING: Leaf with no description and no routingHint."""
    issues: list[Issue] = []
    for cluster in manifest.clusters.values():
        for leaf_name, leaf in cluster.leaves.items():
            if not leaf.routing_hint:
                issues.append(
                    Issue(
                        Severity.WARNING,
                        "no-description",
                        f"leaf '{leaf_name}' in cluster '{cluster.name}' has no routingHint",
                        leaf_name,
                    )
                )
    return issues


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_all_checks(
    manifest: Manifest,
    skills_dir: Path,
    library_dir: Path,
) -> list[Issue]:
    """Run all 9 checks and return issues."""
    issues: list[Issue] = []
    issues.extend(check_dead_references(manifest, library_dir, skills_dir))
    issues.extend(check_uniqueness(manifest))
    issues.extend(check_leaf_not_disabled(manifest, library_dir))
    issues.extend(check_always_on_leaf(manifest, library_dir))
    issues.extend(check_orphaned_disabled(manifest, library_dir, skills_dir))
    issues.extend(check_unclustered_budget(manifest, skills_dir))
    issues.extend(check_cluster_too_large(manifest))
    issues.extend(check_crossref_missing(manifest, library_dir, skills_dir))
    issues.extend(check_no_description(manifest))
    return issues


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


CHECK_NAMES = [
    "dead-reference",
    "uniqueness-violation",
    "leaf-not-disabled",
    "always-on-leaf",
    "orphaned-disabled",
    "unclustered-over-budget",
    "cluster-too-large",
    "crossref-missing",
    "no-description",
]


def print_results(issues: list[Issue], quiet: bool = False) -> None:
    """Print check results to stdout."""
    errors = [i for i in issues if i.severity == Severity.ERROR]
    warnings = [i for i in issues if i.severity == Severity.WARNING]

    if not quiet:
        # Group by check name
        by_check: dict[str, list[Issue]] = {}
        for issue in issues:
            by_check.setdefault(issue.check, []).append(issue)

        for check_name in CHECK_NAMES:
            check_issues = by_check.get(check_name, [])
            if not check_issues:
                print(f"  {Colors.GREEN}\u2713{Colors.RESET} {check_name}")
            else:
                severity = check_issues[0].severity
                icon = f"{Colors.RED}\u2717" if severity == Severity.ERROR else f"{Colors.YELLOW}\u26a0"
                print(f"  {icon}{Colors.RESET} {check_name} ({len(check_issues)} issues)")
                for issue in check_issues:
                    print(f"    - {issue.message}")

        print()

    if errors:
        print(
            f"{Colors.RED}{Colors.BOLD}{len(errors)} error(s){Colors.RESET}, "
            f"{len(warnings)} warning(s)"
        )
    elif warnings:
        print(f"{Colors.YELLOW}{len(warnings)} warning(s){Colors.RESET}, 0 errors")
    else:
        print(f"{Colors.GREEN}All checks passed.{Colors.RESET}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="skill-tree check: validate graph integrity")
    parser.add_argument("--quiet", action="store_true", help="summary only")
    parser.add_argument("--notify", action="store_true", help="one-line stderr on issues")
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
        "--manifest",
        type=Path,
        default=None,
        help="path to manifest.json (default: <library-dir>/skill-tree/manifest.json)",
    )
    args = parser.parse_args()

    manifest_path = args.manifest or (args.library_dir / "skill-tree" / "manifest.json")

    if not manifest_path.exists():
        print(f"Manifest not found: {manifest_path}", file=sys.stderr)
        print("Run `skill-tree init` first.", file=sys.stderr)
        sys.exit(2)

    manifest = load_manifest(manifest_path)
    issues = run_all_checks(manifest, args.skills_dir, args.library_dir)

    print_results(issues, quiet=args.quiet)

    errors = sum(1 for i in issues if i.severity == Severity.ERROR)
    warnings = sum(1 for i in issues if i.severity == Severity.WARNING)

    if args.notify and issues:
        msg_parts: list[str] = []
        if errors:
            msg_parts.append(f"{errors} error(s)")
        if warnings:
            msg_parts.append(f"{warnings} warning(s)")
        print(
            f"skill-tree: {', '.join(msg_parts)}. Run `/skill-tree:check` for details.",
            file=sys.stderr,
        )

    if errors:
        sys.exit(2)
    elif warnings:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
