# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""skill-tree sync: regenerate all cluster SKILL.md files from manifest.

Also sets disable-model-invocation: true on all leaves, referenceNodes,
and deprecated skills.

Flags:
  --dry-run     show what would change without writing
  --skills-dir  override scan path (default: ~/.claude/skills)
  --library-dir override library path (default: ~/.claude/skills-library)
  --manifest    override manifest path
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.codex import generate_openai_yaml, write_openai_yaml
from lib.generator import generate_cluster_skillmd, write_cluster_skillmd
from lib.manifest import (
    Manifest,
    load_manifest,
    save_manifest,
)
from lib.skillfile import (
    get_description,
    is_disabled,
    parse_frontmatter,
    set_disable_model_invocation,
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
# Sync logic
# ---------------------------------------------------------------------------


def sync_cluster_files(
    manifest: Manifest,
    skills_dir: Path,
    library_dir: str,
    dry_run: bool = False,
) -> list[str]:
    """Regenerate cluster SKILL.md files. Returns list of actions taken."""
    actions: list[str] = []

    for cluster in manifest.clusters.values():
        target = skills_dir / cluster.name / "SKILL.md"
        new_content = generate_cluster_skillmd(cluster, library_dir)

        # Check if content differs
        if target.exists():
            existing = target.read_text(encoding="utf-8")
            if existing == new_content:
                continue
            action = f"update cluster: {cluster.name}"
        else:
            action = f"create cluster: {cluster.name}"

        actions.append(action)
        if not dry_run:
            write_cluster_skillmd(cluster, skills_dir, library_dir)

    return actions


def sync_disable_flags(
    manifest: Manifest,
    library_dir: Path,
    dry_run: bool = False,
) -> list[str]:
    """Set disable-model-invocation: true on all leaves, referenceNodes, deprecated."""
    actions: list[str] = []
    names_to_disable: set[str] = set()

    for cluster in manifest.clusters.values():
        names_to_disable.update(cluster.leaves.keys())
    names_to_disable.update(manifest.reference_nodes)
    names_to_disable.update(manifest.deprecated)

    for name in sorted(names_to_disable):
        path = library_dir / name / "SKILL.md"
        if not path.exists():
            continue
        fm = parse_frontmatter(path)
        if not is_disabled(fm):
            actions.append(f"set disable-model-invocation: {name}")
            if not dry_run:
                set_disable_model_invocation(path, True)

    return actions


def sync_codex_yaml(
    manifest: Manifest,
    library_dir: Path,
    dry_run: bool = False,
) -> list[str]:
    """Generate agents/openai.yaml for all leaves, referenceNodes, deprecated.

    Codex CLI uses this file to control invocation policy. Leaves get
    allow_implicit_invocation: false so they're only invoked via cluster routing.
    """
    actions: list[str] = []

    # Collect all skills that need Codex YAML + their display info
    skills_to_process: list[tuple[str, str, str]] = []  # (name, display_name, description)

    for cluster in manifest.clusters.values():
        for leaf_name, leaf in cluster.leaves.items():
            hint = leaf.routing_hint
            if not hint:
                # Fall back to SKILL.md frontmatter description
                path = library_dir / leaf_name / "SKILL.md"
                if path.exists():
                    fm = parse_frontmatter(path)
                    hint = get_description(fm) or leaf_name
                else:
                    hint = leaf_name
            display = leaf_name.replace("-", " ").title()
            skills_to_process.append((leaf_name, display, hint))

    for name in manifest.reference_nodes:
        path = library_dir / name / "SKILL.md"
        desc = name
        if path.exists():
            fm = parse_frontmatter(path)
            desc = get_description(fm) or name
        display = name.replace("-", " ").title()
        skills_to_process.append((name, display, desc))

    for name in manifest.deprecated:
        path = library_dir / name / "SKILL.md"
        desc = name
        if path.exists():
            fm = parse_frontmatter(path)
            desc = get_description(fm) or name
        display = name.replace("-", " ").title()
        skills_to_process.append((name, display, desc))

    for skill_name, display_name, description in skills_to_process:
        skill_dir = library_dir / skill_name
        if not skill_dir.exists():
            continue

        yaml_path = skill_dir / "agents" / "openai.yaml"
        new_content = generate_openai_yaml(
            display_name=display_name,
            short_description=description,
            allow_implicit_invocation=False,
        )

        if yaml_path.exists():
            existing = yaml_path.read_text(encoding="utf-8")
            if existing == new_content:
                continue

        action = f"codex yaml: {skill_name}"
        actions.append(action)
        if not dry_run:
            write_openai_yaml(
                skill_dir,
                display_name=display_name,
                short_description=description,
                allow_implicit_invocation=False,
            )

    return actions


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="skill-tree sync: regenerate cluster files from manifest")
    parser.add_argument("--dry-run", action="store_true", help="preview changes")
    parser.add_argument("--codex", action="store_true", help="also generate Codex agents/openai.yaml files")
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
    library_dir_str = str(args.library_dir).replace(str(Path.home()), "~")

    if not manifest_path.exists():
        print(f"Manifest not found: {manifest_path}", file=sys.stderr)
        print("Run `skill-tree init` first.", file=sys.stderr)
        sys.exit(1)

    manifest = load_manifest(manifest_path)

    prefix = f"{Colors.YELLOW}[dry-run]{Colors.RESET} " if args.dry_run else ""

    # Sync cluster files
    cluster_actions = sync_cluster_files(
        manifest, args.skills_dir, library_dir_str, dry_run=args.dry_run
    )
    for action in cluster_actions:
        print(f"  {prefix}{Colors.GREEN}+{Colors.RESET} {action}")

    # Sync disable flags (Claude Code)
    flag_actions = sync_disable_flags(manifest, args.library_dir, dry_run=args.dry_run)
    for action in flag_actions:
        print(f"  {prefix}{Colors.CYAN}~{Colors.RESET} {action}")

    # Sync Codex YAML (optional)
    codex_actions: list[str] = []
    if args.codex:
        codex_actions = sync_codex_yaml(manifest, args.library_dir, dry_run=args.dry_run)
        for action in codex_actions:
            print(f"  {prefix}{Colors.CYAN}~{Colors.RESET} {action}")

    total = len(cluster_actions) + len(flag_actions) + len(codex_actions)
    if total == 0:
        print(f"{Colors.GREEN}Everything in sync.{Colors.RESET}")
    else:
        verb = "would apply" if args.dry_run else "applied"
        print(f"\n{total} action(s) {verb}.")


if __name__ == "__main__":
    main()
