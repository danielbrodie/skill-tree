"""Generate cluster SKILL.md routing files from manifest entries."""

from __future__ import annotations

from pathlib import Path

from .manifest import Cluster


# ---------------------------------------------------------------------------
# Template
# ---------------------------------------------------------------------------

CLUSTER_TEMPLATE = """\
---
name: {name}
description: "{description}"
version: 1.0.0
---

Output skill name only. Load it: `read {library_dir}/<skill-name>/SKILL.md`
"""

CROSSREF_HEADER = """
## Cross-references
"""


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def generate_cluster_skillmd(
    cluster: Cluster,
    library_dir: str = "~/.claude/skills-library",
) -> str:
    """Generate the full SKILL.md content for a cluster router."""
    # Escape double quotes in description for frontmatter
    escaped_desc = cluster.description.replace('"', '\\"')

    parts: list[str] = []

    # Frontmatter + routing instruction
    parts.append(
        CLUSTER_TEMPLATE.format(
            name=cluster.name,
            description=escaped_desc,
            library_dir=library_dir,
        )
    )

    # Custom instructions (between header and routing list)
    if cluster.custom_instructions:
        parts.append(cluster.custom_instructions)
        parts.append("")

    # Arrow-list routing
    if cluster.leaves:
        for leaf_name, leaf in cluster.leaves.items():
            hint = leaf.routing_hint or "(no routing hint)"
            parts.append(f"- {hint} → `{leaf_name}`")
        parts.append("")

    # Cross-references
    if cluster.cross_references:
        parts.append(CROSSREF_HEADER.rstrip("\n"))
        for ref in cluster.cross_references:
            parts.append(
                f"- `{ref.skill}`: {ref.note} "
                f"— load directly: `{library_dir}/{ref.skill}/SKILL.md`"
            )
        parts.append("")

    return "\n".join(parts) + "\n"


def write_cluster_skillmd(
    cluster: Cluster,
    skills_dir: Path,
    library_dir: str = "~/.claude/skills-library",
) -> Path:
    """Write a cluster SKILL.md to the scan path directory.

    Creates the cluster directory if it doesn't exist.
    Returns the path to the written file.
    """
    cluster_dir = skills_dir / cluster.name
    cluster_dir.mkdir(parents=True, exist_ok=True)
    skillmd_path = cluster_dir / "SKILL.md"

    content = generate_cluster_skillmd(cluster, library_dir)
    skillmd_path.write_text(content, encoding="utf-8")
    return skillmd_path
