# /// script
# requires-python = ">=3.11"
# dependencies = ["scikit-learn", "pyyaml"]
# ///
"""skill-tree scan: analyze skills directory and propose cluster structure.

Reads all SKILL.md files, clusters them using TF-IDF + agglomerative
clustering, and writes a preview to the preview directory.

Flags:
  --skills-dir    override scan path (default: ~/.claude/skills)
  --library-dir   override library path (default: ~/.claude/skills-library)
  --threshold     clustering distance threshold (default: 0.7)
  --preview-dir   where to write preview (default: <library-dir>/skill-tree/preview)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.cluster import (
    ProposedCluster,
    SkillDocument,
    cluster_skills,
    extract_skill_document,
)
from lib.manifest import (
    Cluster,
    LeafEntry,
    Manifest,
    all_managed_skills,
    load_manifest,
    save_manifest,
    serialize_manifest,
)
from lib.skillfile import scan_skills_dir


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
# Scan
# ---------------------------------------------------------------------------


def collect_all_skills(
    skills_dir: Path, library_dir: Path
) -> dict[str, SkillDocument]:
    """Collect SkillDocuments from both scan path and library."""
    documents: dict[str, SkillDocument] = {}

    for dir_path in (skills_dir, library_dir):
        skills = scan_skills_dir(dir_path)
        for name, path in skills.items():
            if name in documents:
                continue  # scan path takes precedence
            doc = extract_skill_document(path)
            if doc:
                documents[name] = doc

    return documents


def build_proposed_manifest(
    clusters: list[ProposedCluster],
    standalones: list[SkillDocument],
) -> Manifest:
    """Convert clustering results into a proposed manifest."""
    manifest_clusters: dict[str, Cluster] = {}

    for proposed in clusters:
        leaves: dict[str, LeafEntry] = {}
        for member in proposed.members:
            # Use first sentence of description as routing hint
            hint = member.description.split(".")[0].strip() if member.description else None
            if hint and not hint.endswith("."):
                hint += "."
            leaves[member.name] = LeafEntry(routing_hint=hint)

        # Ensure unique label in manifest
        label = proposed.label
        counter = 2
        while label in manifest_clusters:
            label = f"{proposed.label}-{counter}"
            counter += 1

        manifest_clusters[label] = Cluster(
            name=label,
            description=proposed.description,
            leaves=leaves,
        )

    standalone_names = tuple(sorted(doc.name for doc in standalones))

    return Manifest(
        clusters=manifest_clusters,
        standalones=standalone_names,
    )


def write_preview(
    manifest: Manifest,
    preview_dir: Path,
    total_scanned: int,
) -> None:
    """Write preview files for user review."""
    preview_dir.mkdir(parents=True, exist_ok=True)

    # Write proposed manifest
    manifest_path = preview_dir / "manifest.json"
    save_manifest(manifest, manifest_path)

    # Write human-readable summary
    summary_lines: list[str] = []
    summary_lines.append(f"Scanned {total_scanned} skills. Proposed structure:")
    summary_lines.append("")

    total_clustered = 0
    for name, cluster in sorted(manifest.clusters.items()):
        leaf_names = ", ".join(list(cluster.leaves.keys())[:5])
        if len(cluster.leaves) > 5:
            leaf_names += ", ..."
        summary_lines.append(f"  {name} ({len(cluster.leaves)} skills): {leaf_names}")
        total_clustered += len(cluster.leaves)

    summary_lines.append("")
    summary_lines.append(
        f"  {len(manifest.clusters)} clusters, "
        f"{total_clustered} clustered skills, "
        f"{len(manifest.standalones)} standalones"
    )

    # Token estimate
    old_tokens = total_scanned * 100  # ~100 tokens per flat skill
    new_tokens = len(manifest.clusters) * 100 + len(manifest.standalones) * 100
    if old_tokens > 0:
        reduction = (1 - new_tokens / old_tokens) * 100
        summary_lines.append("")
        summary_lines.append(
            f"  Catalog: {total_scanned} x ~100 tokens -> "
            f"{len(manifest.clusters) + len(manifest.standalones)} x ~100 tokens"
        )
        summary_lines.append(
            f"  Estimated reduction: ~{old_tokens:,} -> ~{new_tokens:,} tokens ({reduction:.0f}%)"
        )

    summary_lines.append("")
    summary_lines.append(f"Preview written to {preview_dir}")
    summary_lines.append("Edit the preview, then run `skill-tree apply` to apply.")

    summary_text = "\n".join(summary_lines) + "\n"
    (preview_dir / "summary.txt").write_text(summary_text, encoding="utf-8")

    return summary_text


# ---------------------------------------------------------------------------
# Additive merge (when manifest already exists)
# ---------------------------------------------------------------------------


def merge_into_existing(
    existing: Manifest | None,
    skills_dir: Path,
    library_dir: Path,
    return_new: bool = False,
) -> Manifest | tuple[Manifest, list[str]] | None:
    """Merge newly discovered skills into an existing manifest.

    Preserves all existing clusters, standalones, hotPath, referenceNodes,
    deprecated, and customInstructions. Only adds new/untracked skills as
    standalones.

    Returns None if existing is None (caller should fall back to full scan).
    If return_new=True, returns (manifest, new_skill_names).
    """
    if existing is None:
        return None

    # Find all skills on disk
    all_on_disk: set[str] = set()
    for dir_path in {skills_dir, library_dir}:
        all_on_disk.update(scan_skills_dir(dir_path).keys())

    # Find all skills already tracked in manifest
    managed = all_managed_skills(existing)
    tracked: set[str] = set(managed.keys())

    # New = on disk but not tracked (excluding cluster router names)
    new_skills = sorted(all_on_disk - tracked)

    # Build updated standalones tuple with new skills appended
    updated_standalones = tuple(list(existing.standalones) + new_skills)

    # Create new manifest preserving everything, only adding standalones
    merged = Manifest(
        version=existing.version,
        unclustered_budget=existing.unclustered_budget,
        clusters=existing.clusters,
        standalones=updated_standalones,
        hot_path=existing.hot_path,
        reference_nodes=existing.reference_nodes,
        deprecated=existing.deprecated,
    )

    if return_new:
        return merged, new_skills
    return merged


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="skill-tree scan: propose cluster structure")
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
        "--threshold",
        type=float,
        default=0.7,
        help="clustering distance threshold (0-1, lower = tighter clusters)",
    )
    parser.add_argument("--preview-dir", type=Path, default=None)
    parser.add_argument(
        "--full",
        action="store_true",
        help="regenerate entire cluster structure (ignores existing manifest)",
    )
    args = parser.parse_args()

    preview_dir = args.preview_dir or (args.library_dir / "skill-tree" / "preview")
    manifest_path = args.library_dir / "skill-tree" / "manifest.json"

    # Check for existing manifest → additive mode
    if manifest_path.exists() and not args.full:
        existing = load_manifest(manifest_path)
        result = merge_into_existing(
            existing, args.skills_dir, args.library_dir, return_new=True
        )
        if result is not None:
            merged, new_skills = result
            if not new_skills:
                print(f"{Colors.GREEN}No new skills found.{Colors.RESET} All skills are tracked in the manifest.")
                print(f"Use --full to regenerate the entire cluster structure.")
                sys.exit(0)

            print(f"Found {Colors.BOLD}{len(new_skills)} new skill(s){Colors.RESET} not in manifest:")
            for name in new_skills:
                print(f"  {Colors.CYAN}+{Colors.RESET} {name}")
            print(f"\nAdded as standalones. Run /setup to re-cluster if needed.")
            print(f"Use --full to regenerate the entire cluster structure.\n")

            # Write preview with merged manifest
            write_preview(merged, preview_dir, len(new_skills))
            sys.exit(0)

    # Full scan mode (no manifest or --full flag)
    all_docs = collect_all_skills(args.skills_dir, args.library_dir)
    if not all_docs:
        print("No skills found.", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning {len(all_docs)} skills...")

    # Cluster
    documents = list(all_docs.values())
    clusters, standalones = cluster_skills(documents, distance_threshold=args.threshold)

    # Build proposed manifest
    proposed = build_proposed_manifest(clusters, standalones)

    # Write preview
    summary = write_preview(proposed, preview_dir, len(all_docs))
    print(summary)


if __name__ == "__main__":
    main()
