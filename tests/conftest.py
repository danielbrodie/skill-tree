"""Shared fixtures for skill-tree tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.lib.manifest import Cluster, CrossReference, LeafEntry, Manifest


@pytest.fixture
def sample_manifest() -> Manifest:
    """A small but representative manifest for testing."""
    return Manifest(
        version="1.0",
        unclustered_budget=25,
        clusters={
            "research-index": Cluster(
                name="research-index",
                description="Research anything — web search, deep research, notebooks.",
                custom_instructions="## Quick decision tree\nUse librarium for broad searches.",
                cross_references=(
                    CrossReference(skill="obsidian-index", note="write research output to vault"),
                ),
                leaves={
                    "librarium": LeafEntry(routing_hint="Multi-provider fan-out research."),
                    "notebooklm-research": LeafEntry(routing_hint="Deep research via NotebookLM."),
                },
            ),
            "dev-tools": Cluster(
                name="dev-tools",
                description="Developer tools — GitHub, coding agents, library docs.",
                leaves={
                    "github-ops": LeafEntry(routing_hint="GitHub PRs, issues, CI."),
                    "coding-agents": LeafEntry(routing_hint="Delegate coding tasks."),
                    "library-docs": LeafEntry(routing_hint="Look up library docs."),
                },
            ),
        },
        standalones=("weather", "ebay"),
        hot_path=("flowdeck",),
        reference_nodes=("agent-cli-tools",),
        deprecated=("old-skill",),
    )


@pytest.fixture
def sample_manifest_json(sample_manifest: Manifest) -> dict:
    """The sample manifest as a JSON-serializable dict."""
    from scripts.lib.manifest import serialize_manifest
    return serialize_manifest(sample_manifest)


@pytest.fixture
def tmp_skills_dir(tmp_path: Path) -> Path:
    """Temporary skills scan directory."""
    d = tmp_path / "skills"
    d.mkdir()
    return d


@pytest.fixture
def tmp_library_dir(tmp_path: Path) -> Path:
    """Temporary skills library directory."""
    d = tmp_path / "skills-library"
    d.mkdir()
    return d


@pytest.fixture
def write_skill(tmp_path: Path):
    """Factory fixture to write a SKILL.md into a temp directory."""
    def _write(base_dir: Path, name: str, content: str) -> Path:
        skill_dir = base_dir / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        path = skill_dir / "SKILL.md"
        path.write_text(content, encoding="utf-8")
        return path
    return _write


@pytest.fixture
def populated_dirs(
    tmp_skills_dir: Path,
    tmp_library_dir: Path,
    write_skill,
    sample_manifest: Manifest,
    sample_manifest_json: dict,
) -> tuple[Path, Path, Path]:
    """Create a fully populated temp environment matching the sample manifest.

    Returns (skills_dir, library_dir, manifest_path).
    """
    # Write cluster routers to scan path
    for cluster_name in sample_manifest.clusters:
        write_skill(
            tmp_skills_dir,
            cluster_name,
            f"---\nname: {cluster_name}\ndescription: test cluster\n---\n# Router\n",
        )

    # Write leaves to library
    for cluster in sample_manifest.clusters.values():
        for leaf_name in cluster.leaves:
            write_skill(
                tmp_library_dir,
                leaf_name,
                f"---\nname: {leaf_name}\ndescription: test leaf\ndisable-model-invocation: true\n---\n# Leaf\n",
            )

    # Write standalones to scan path
    for name in sample_manifest.standalones:
        write_skill(
            tmp_skills_dir,
            name,
            f"---\nname: {name}\ndescription: standalone skill\n---\n# Standalone\n",
        )

    # Write hot path to scan path
    for name in sample_manifest.hot_path:
        write_skill(
            tmp_skills_dir,
            name,
            f"---\nname: {name}\ndescription: hot path skill\n---\n# Hot\n",
        )

    # Write reference nodes to library
    for name in sample_manifest.reference_nodes:
        write_skill(
            tmp_library_dir,
            name,
            f"---\nname: {name}\ndescription: reference\ndisable-model-invocation: true\n---\n# Ref\n",
        )

    # Write deprecated to library
    for name in sample_manifest.deprecated:
        write_skill(
            tmp_library_dir,
            name,
            f"---\nname: {name}\ndescription: deprecated\ndisable-model-invocation: true\n---\n# Dep\n",
        )

    # Write manifest
    manifest_dir = tmp_library_dir / "skill-tree"
    manifest_dir.mkdir()
    manifest_path = manifest_dir / "manifest.json"
    manifest_path.write_text(json.dumps(sample_manifest_json, indent=2), encoding="utf-8")

    return tmp_skills_dir, tmp_library_dir, manifest_path
