"""Tests for manifest parsing, serialization, and queries."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.lib.manifest import (
    Cluster,
    CrossReference,
    LeafEntry,
    Manifest,
    all_managed_skills,
    empty_manifest,
    estimate_catalog_tokens,
    load_manifest,
    parse_manifest,
    save_manifest,
    serialize_manifest,
    total_skill_count,
    validate_skill_name,
)


class TestValidateSkillName:
    def test_valid_names(self):
        assert validate_skill_name("research-index") is None
        assert validate_skill_name("dev-tools") is None
        assert validate_skill_name("a1") is None
        assert validate_skill_name("skill-tree") is None

    def test_empty(self):
        assert validate_skill_name("") is not None

    def test_uppercase(self):
        assert validate_skill_name("Research-Index") is not None

    def test_leading_hyphen(self):
        assert validate_skill_name("-bad") is not None

    def test_trailing_hyphen(self):
        assert validate_skill_name("bad-") is not None

    def test_dots(self):
        assert validate_skill_name("bad.name") is not None

    def test_path_separator(self):
        assert validate_skill_name("bad/name") is not None

    def test_single_char(self):
        # Single char doesn't match — needs at least 2 chars
        assert validate_skill_name("a") is not None


class TestParseSerializeRoundtrip:
    def test_roundtrip(self, sample_manifest: Manifest, sample_manifest_json: dict):
        """Serialize then parse should produce equivalent data."""
        serialized = serialize_manifest(sample_manifest)
        reparsed = parse_manifest(serialized)

        assert reparsed.version == sample_manifest.version
        assert reparsed.unclustered_budget == sample_manifest.unclustered_budget
        assert set(reparsed.clusters.keys()) == set(sample_manifest.clusters.keys())
        assert reparsed.standalones == sample_manifest.standalones
        assert reparsed.hot_path == sample_manifest.hot_path
        assert reparsed.reference_nodes == sample_manifest.reference_nodes
        assert reparsed.deprecated == sample_manifest.deprecated

    def test_cluster_leaves_preserved(self, sample_manifest: Manifest):
        serialized = serialize_manifest(sample_manifest)
        reparsed = parse_manifest(serialized)

        research = reparsed.clusters["research-index"]
        assert "librarium" in research.leaves
        assert research.leaves["librarium"].routing_hint == "Multi-provider fan-out research."

    def test_cross_references_preserved(self, sample_manifest: Manifest):
        serialized = serialize_manifest(sample_manifest)
        reparsed = parse_manifest(serialized)

        research = reparsed.clusters["research-index"]
        assert len(research.cross_references) == 1
        assert research.cross_references[0].skill == "obsidian-index"

    def test_custom_instructions_preserved(self, sample_manifest: Manifest):
        serialized = serialize_manifest(sample_manifest)
        reparsed = parse_manifest(serialized)

        research = reparsed.clusters["research-index"]
        assert "Quick decision tree" in research.custom_instructions


class TestLoadSave:
    def test_save_and_load(self, tmp_path: Path, sample_manifest: Manifest):
        path = tmp_path / "manifest.json"
        save_manifest(sample_manifest, path)

        assert path.exists()
        loaded = load_manifest(path)
        assert loaded.version == sample_manifest.version
        assert set(loaded.clusters.keys()) == set(sample_manifest.clusters.keys())

    def test_atomic_write(self, tmp_path: Path, sample_manifest: Manifest):
        """No .tmp file should remain after save."""
        path = tmp_path / "manifest.json"
        save_manifest(sample_manifest, path)
        assert not (tmp_path / "manifest.json.tmp").exists()

    def test_valid_json(self, tmp_path: Path, sample_manifest: Manifest):
        path = tmp_path / "manifest.json"
        save_manifest(sample_manifest, path)
        data = json.loads(path.read_text())
        assert data["version"] == "1.0"
        assert "clusters" in data


class TestQueries:
    def test_all_managed_skills(self, sample_manifest: Manifest):
        managed = all_managed_skills(sample_manifest)
        # Leaves
        assert "librarium" in managed
        assert "github-ops" in managed
        # Standalones
        assert "weather" in managed
        # Hot path
        assert "flowdeck" in managed
        # Reference nodes
        assert "agent-cli-tools" in managed
        # Deprecated
        assert "old-skill" in managed
        # Cluster routers
        assert "research-index" in managed

    def test_total_skill_count(self, sample_manifest: Manifest):
        count = total_skill_count(sample_manifest)
        # 5 leaves + 2 standalones + 1 hot_path + 1 ref + 1 deprecated = 10
        assert count == 10

    def test_estimate_catalog_tokens(self, sample_manifest: Manifest):
        tokens = estimate_catalog_tokens(sample_manifest)
        assert tokens > 0

    def test_uniqueness_detection(self):
        """A skill in two places should show both locations."""
        manifest = Manifest(
            clusters={
                "c1": Cluster(
                    name="c1",
                    description="test",
                    leaves={"dupe": LeafEntry()},
                ),
            },
            standalones=("dupe",),
        )
        managed = all_managed_skills(manifest)
        assert len(managed["dupe"]) == 2


class TestEmptyManifest:
    def test_defaults(self):
        m = empty_manifest()
        assert m.version == "1.0"
        assert m.unclustered_budget == 25
        assert len(m.clusters) == 0
        assert len(m.standalones) == 0
