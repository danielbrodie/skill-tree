"""Tests for scan.py — skill description collection."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.scan import collect_skill_descriptions, find_new_skills
from scripts.lib.manifest import Cluster, LeafEntry, Manifest


class TestCollectSkillDescriptions:
    def test_collects_from_single_dir(self, tmp_path, write_skill):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        write_skill(skills_dir, "alpha", "---\nname: alpha\ndescription: Alpha skill\n---\n")
        write_skill(skills_dir, "beta", "---\nname: beta\ndescription: Beta skill\n---\n")

        result = collect_skill_descriptions(skills_dir, tmp_path / "empty")
        assert len(result) == 2
        names = {s["name"] for s in result}
        assert names == {"alpha", "beta"}

    def test_deduplicates_across_dirs(self, tmp_path, write_skill):
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        dir_a.mkdir()
        dir_b.mkdir()
        write_skill(dir_a, "shared", "---\nname: shared\ndescription: From A\n---\n")
        write_skill(dir_b, "shared", "---\nname: shared\ndescription: From B\n---\n")

        result = collect_skill_descriptions(dir_a, dir_b)
        assert len(result) == 1
        assert result[0]["description"] == "From A"  # first dir wins

    def test_handles_missing_description(self, tmp_path, write_skill):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        write_skill(skills_dir, "nodesc", "---\nname: nodesc\n---\n# No description\n")

        result = collect_skill_descriptions(skills_dir, tmp_path / "empty")
        assert len(result) == 1
        assert result[0]["description"] == ""

    def test_empty_dir(self, tmp_path):
        result = collect_skill_descriptions(tmp_path, tmp_path)
        assert result == []


class TestFindNewSkills:
    def test_finds_untracked_skills(self):
        all_skills = [
            {"name": "alpha", "description": "A"},
            {"name": "beta", "description": "B"},
            {"name": "gamma", "description": "C"},
        ]
        manifest = Manifest(
            clusters={
                "test": Cluster(
                    name="test",
                    description="Test",
                    leaves={"alpha": LeafEntry(routing_hint="hint")},
                ),
            },
            standalones=("beta",),
        )

        new = find_new_skills(all_skills, manifest)
        assert len(new) == 1
        assert new[0]["name"] == "gamma"

    def test_no_new_skills(self):
        all_skills = [{"name": "alpha", "description": "A"}]
        manifest = Manifest(standalones=("alpha",))

        new = find_new_skills(all_skills, manifest)
        assert new == []
