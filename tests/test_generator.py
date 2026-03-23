"""Tests for cluster SKILL.md generation."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.lib.generator import generate_cluster_skillmd, write_cluster_skillmd
from scripts.lib.manifest import Cluster, CrossReference, LeafEntry


class TestGenerateClusterSkillmd:
    def test_basic_output(self):
        cluster = Cluster(
            name="research-index",
            description="Research tools",
            leaves={
                "librarium": LeafEntry(routing_hint="Fan-out research."),
                "notebooklm": LeafEntry(routing_hint="Deep research."),
            },
        )
        content = generate_cluster_skillmd(cluster)

        assert "name: research-index" in content
        assert 'description: "Research tools"' in content
        assert "## Routing table" in content
        assert "| `librarium` | Fan-out research. |" in content
        assert "| `notebooklm` | Deep research. |" in content

    def test_custom_instructions(self):
        cluster = Cluster(
            name="test",
            description="Test",
            custom_instructions="## Decision tree\nUse X for Y.",
            leaves={"leaf1": LeafEntry(routing_hint="hint")},
        )
        content = generate_cluster_skillmd(cluster)

        assert "## Decision tree" in content
        assert "Use X for Y." in content
        # Custom instructions appear before routing table
        ci_pos = content.index("Decision tree")
        rt_pos = content.index("Routing table")
        assert ci_pos < rt_pos

    def test_cross_references(self):
        cluster = Cluster(
            name="test",
            description="Test",
            cross_references=(
                CrossReference(skill="obsidian-index", note="write output"),
            ),
            leaves={"leaf1": LeafEntry(routing_hint="hint")},
        )
        content = generate_cluster_skillmd(cluster)

        assert "## Cross-references" in content
        assert "`obsidian-index`" in content
        assert "write output" in content

    def test_library_dir_in_paths(self):
        cluster = Cluster(
            name="test",
            description="Test",
            leaves={"leaf1": LeafEntry(routing_hint="hint")},
        )
        content = generate_cluster_skillmd(cluster, library_dir="/custom/path")
        assert "/custom/path/" in content

    def test_no_routing_hint_fallback(self):
        cluster = Cluster(
            name="test",
            description="Test",
            leaves={"leaf1": LeafEntry(routing_hint=None)},
        )
        content = generate_cluster_skillmd(cluster)
        assert "(no routing hint)" in content

    def test_escaped_quotes_in_description(self):
        cluster = Cluster(
            name="test",
            description='Has "quotes" inside',
            leaves={"leaf1": LeafEntry(routing_hint="hint")},
        )
        content = generate_cluster_skillmd(cluster)
        assert 'Has \\"quotes\\" inside' in content


class TestWriteClusterSkillmd:
    def test_creates_directory_and_file(self, tmp_path: Path):
        cluster = Cluster(
            name="research",
            description="Research tools",
            leaves={"lib": LeafEntry(routing_hint="hint")},
        )
        result = write_cluster_skillmd(cluster, tmp_path)

        assert result == tmp_path / "research" / "SKILL.md"
        assert result.exists()
        content = result.read_text()
        assert "name: research" in content

    def test_overwrites_existing(self, tmp_path: Path):
        cluster_dir = tmp_path / "research"
        cluster_dir.mkdir()
        (cluster_dir / "SKILL.md").write_text("old content")

        cluster = Cluster(
            name="research",
            description="New description",
            leaves={"lib": LeafEntry(routing_hint="hint")},
        )
        write_cluster_skillmd(cluster, tmp_path)

        content = (cluster_dir / "SKILL.md").read_text()
        assert "New description" in content
        assert "old content" not in content
