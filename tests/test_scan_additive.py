"""Tests for additive scan behavior — preserving existing manifest when adding new skills."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.lib.manifest import Cluster, LeafEntry, Manifest, save_manifest, load_manifest
from scripts.scan import collect_all_skills, build_proposed_manifest, merge_into_existing


class TestMergeIntoExisting:
    """When a manifest exists, scan should propose additions only."""

    def test_preserves_existing_clusters(self, tmp_path, write_skill):
        """Existing clusters should not be modified."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        existing = Manifest(
            clusters={
                "research": Cluster(
                    name="research",
                    description="Research tools",
                    custom_instructions="## My custom instructions",
                    leaves={
                        "librarium": LeafEntry(routing_hint="Fan-out research."),
                        "notebooklm": LeafEntry(routing_hint="Deep research."),
                    },
                ),
            },
            standalones=("weather",),
            hot_path=("flowdeck",),
            reference_nodes=("agent-cli-tools",),
            deprecated=("old-skill",),
        )

        # Write existing skills
        for name in ["librarium", "notebooklm", "weather", "flowdeck", "agent-cli-tools", "old-skill"]:
            write_skill(skills_dir, name, f"---\nname: {name}\ndescription: {name} skill\n---\n")

        # Write one NEW skill not in manifest
        write_skill(skills_dir, "new-tool", "---\nname: new-tool\ndescription: A brand new tool for testing\n---\n")

        # Write cluster router
        write_skill(skills_dir, "research", "---\nname: research\ndescription: Research tools\n---\n")

        merged = merge_into_existing(existing, skills_dir, skills_dir)

        # Existing cluster preserved with custom instructions
        assert "research" in merged.clusters
        assert merged.clusters["research"].custom_instructions == "## My custom instructions"
        assert "librarium" in merged.clusters["research"].leaves
        assert "notebooklm" in merged.clusters["research"].leaves

        # Other arrays preserved
        assert "weather" in merged.standalones
        assert "flowdeck" in merged.hot_path
        assert "agent-cli-tools" in merged.reference_nodes
        assert "old-skill" in merged.deprecated

    def test_new_skill_added_as_standalone(self, tmp_path, write_skill):
        """New skills should be proposed as standalones (safe default)."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        existing = Manifest(
            clusters={
                "research": Cluster(
                    name="research",
                    description="Research tools",
                    leaves={"librarium": LeafEntry(routing_hint="Research.")},
                ),
            },
            standalones=("weather",),
        )

        for name in ["librarium", "weather", "research"]:
            write_skill(skills_dir, name, f"---\nname: {name}\ndescription: {name}\n---\n")

        write_skill(skills_dir, "brand-new", "---\nname: brand-new\ndescription: Something totally new\n---\n")

        merged = merge_into_existing(existing, skills_dir, skills_dir)

        assert "brand-new" in merged.standalones

    def test_does_not_duplicate_existing_skills(self, tmp_path, write_skill):
        """Skills already in manifest should not be re-added."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        existing = Manifest(
            clusters={
                "research": Cluster(
                    name="research",
                    description="Research tools",
                    leaves={"librarium": LeafEntry(routing_hint="Research.")},
                ),
            },
            standalones=("weather",),
        )

        for name in ["librarium", "weather", "research"]:
            write_skill(skills_dir, name, f"---\nname: {name}\ndescription: {name}\n---\n")

        merged = merge_into_existing(existing, skills_dir, skills_dir)

        # No new standalones beyond what existed
        assert merged.standalones == ("weather",)

    def test_reports_new_skills(self, tmp_path, write_skill):
        """merge_into_existing should return info about what's new."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        existing = Manifest(
            standalones=("weather",),
        )

        write_skill(skills_dir, "weather", "---\nname: weather\ndescription: weather\n---\n")
        write_skill(skills_dir, "new-a", "---\nname: new-a\ndescription: New A\n---\n")
        write_skill(skills_dir, "new-b", "---\nname: new-b\ndescription: New B\n---\n")

        merged, new_skills = merge_into_existing(existing, skills_dir, skills_dir, return_new=True)

        assert "new-a" in new_skills
        assert "new-b" in new_skills
        assert "weather" not in new_skills

    def test_no_manifest_falls_back_to_full_scan(self, tmp_path, write_skill):
        """When no manifest exists, merge_into_existing should return None so caller does full scan."""
        result = merge_into_existing(None, tmp_path, tmp_path)
        assert result is None
