"""Read, write, and validate manifest.json — the single source of truth for the skill graph."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MANIFEST_FILENAME = "manifest.json"
MANIFEST_VERSION = "1.0"
SKILL_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
DEFAULT_UNCLUSTERED_BUDGET = 25


# ---------------------------------------------------------------------------
# Data classes (immutable representations)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CrossReference:
    skill: str
    note: str


@dataclass(frozen=True)
class LeafEntry:
    routing_hint: str | None = None


@dataclass(frozen=True)
class Cluster:
    name: str
    description: str
    custom_instructions: str | None = None
    cross_references: tuple[CrossReference, ...] = ()
    leaves: dict[str, LeafEntry] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # frozen=True prevents assignment, so we use object.__setattr__
        # to convert mutable default to the actual dict passed in
        pass


@dataclass(frozen=True)
class Manifest:
    version: str = MANIFEST_VERSION
    unclustered_budget: int = DEFAULT_UNCLUSTERED_BUDGET
    clusters: dict[str, Cluster] = field(default_factory=dict)
    standalones: tuple[str, ...] = ()
    hot_path: tuple[str, ...] = ()
    reference_nodes: tuple[str, ...] = ()
    deprecated: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_skill_name(name: str) -> str | None:
    """Return an error message if name is invalid, else None."""
    if not name:
        return "skill name is empty"
    if not SKILL_NAME_RE.match(name):
        return (
            f"invalid skill name '{name}' — "
            "must match ^[a-z0-9][a-z0-9-]*[a-z0-9]$ "
            "(lowercase alphanumeric and hyphens, no leading/trailing hyphen)"
        )
    return None


# ---------------------------------------------------------------------------
# Parsing (JSON dict -> dataclasses)
# ---------------------------------------------------------------------------


def _parse_cluster(name: str, data: dict[str, Any]) -> Cluster:
    cross_refs = tuple(
        CrossReference(skill=cr["skill"], note=cr["note"])
        for cr in data.get("crossReferences", [])
    )
    leaves = {
        leaf_name: LeafEntry(routing_hint=leaf_data.get("routingHint"))
        for leaf_name, leaf_data in data.get("leaves", {}).items()
    }
    return Cluster(
        name=name,
        description=data["description"],
        custom_instructions=data.get("customInstructions"),
        cross_references=cross_refs,
        leaves=leaves,
    )


def parse_manifest(data: dict[str, Any]) -> Manifest:
    """Parse a JSON-decoded dict into a Manifest."""
    clusters = {
        name: _parse_cluster(name, cdata)
        for name, cdata in data.get("clusters", {}).items()
    }
    return Manifest(
        version=data.get("version", MANIFEST_VERSION),
        unclustered_budget=data.get("unclusteredBudget", DEFAULT_UNCLUSTERED_BUDGET),
        clusters=clusters,
        standalones=tuple(data.get("standalones", [])),
        hot_path=tuple(data.get("hotPath", [])),
        reference_nodes=tuple(data.get("referenceNodes", [])),
        deprecated=tuple(data.get("deprecated", [])),
    )


def load_manifest(path: Path) -> Manifest:
    """Load manifest.json from disk."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return parse_manifest(data)


# ---------------------------------------------------------------------------
# Serialization (dataclasses -> JSON dict)
# ---------------------------------------------------------------------------


def _serialize_cluster(cluster: Cluster) -> dict[str, Any]:
    result: dict[str, Any] = {"description": cluster.description}
    if cluster.custom_instructions is not None:
        result["customInstructions"] = cluster.custom_instructions
    if cluster.cross_references:
        result["crossReferences"] = [
            {"skill": cr.skill, "note": cr.note}
            for cr in cluster.cross_references
        ]
    else:
        result["crossReferences"] = []
    result["leaves"] = {
        name: {"routingHint": leaf.routing_hint}
        for name, leaf in cluster.leaves.items()
    }
    return result


def serialize_manifest(manifest: Manifest) -> dict[str, Any]:
    """Convert Manifest to a JSON-serializable dict."""
    return {
        "version": manifest.version,
        "unclusteredBudget": manifest.unclustered_budget,
        "clusters": {
            name: _serialize_cluster(c) for name, c in manifest.clusters.items()
        },
        "standalones": list(manifest.standalones),
        "hotPath": list(manifest.hot_path),
        "referenceNodes": list(manifest.reference_nodes),
        "deprecated": list(manifest.deprecated),
    }


def save_manifest(manifest: Manifest, path: Path) -> None:
    """Atomically write manifest.json to disk."""
    data = serialize_manifest(manifest)
    content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(str(tmp_path), str(path))


# ---------------------------------------------------------------------------
# Manifest queries
# ---------------------------------------------------------------------------


def all_managed_skills(manifest: Manifest) -> dict[str, list[str]]:
    """Return mapping of skill_name -> [location, ...] across all manifest arrays."""
    locations: dict[str, list[str]] = {}

    for cluster_name, cluster in manifest.clusters.items():
        for leaf_name in cluster.leaves:
            locations.setdefault(leaf_name, []).append(
                f"clusters.{cluster_name}.leaves"
            )

    for name in manifest.standalones:
        locations.setdefault(name, []).append("standalones")

    for name in manifest.hot_path:
        locations.setdefault(name, []).append("hotPath")

    for name in manifest.reference_nodes:
        locations.setdefault(name, []).append("referenceNodes")

    for name in manifest.deprecated:
        locations.setdefault(name, []).append("deprecated")

    # Cluster names themselves are managed
    for cluster_name in manifest.clusters:
        locations.setdefault(cluster_name, []).append("clusters (router)")

    return locations


def total_skill_count(manifest: Manifest) -> int:
    """Count all unique skills in the manifest (leaves + standalones + hot_path + ref + deprecated)."""
    all_names: set[str] = set()
    for cluster in manifest.clusters.values():
        all_names.update(cluster.leaves.keys())
    all_names.update(manifest.standalones)
    all_names.update(manifest.hot_path)
    all_names.update(manifest.reference_nodes)
    all_names.update(manifest.deprecated)
    return len(all_names)


def estimate_catalog_tokens(manifest: Manifest) -> int:
    """Estimate tokens consumed by cluster descriptions in the scan path.

    Rough heuristic: 1 token ≈ 4 characters.
    """
    total_chars = 0
    for cluster in manifest.clusters.values():
        # name + description per cluster
        total_chars += len(cluster.name) + len(cluster.description) + 20  # overhead
    # Standalones also appear in catalog
    for name in manifest.standalones:
        total_chars += len(name) + 80  # name + estimated description
    for name in manifest.hot_path:
        total_chars += len(name) + 80
    return total_chars // 4


# ---------------------------------------------------------------------------
# Empty manifest for init
# ---------------------------------------------------------------------------


def empty_manifest() -> Manifest:
    """Create a new empty manifest."""
    return Manifest()
