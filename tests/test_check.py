"""Tests for the 9 validation checks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.check import (
    Severity,
    check_always_on_leaf,
    check_cluster_too_large,
    check_crossref_missing,
    check_dead_references,
    check_leaf_not_disabled,
    check_no_description,
    check_orphaned_disabled,
    check_unclustered_budget,
    check_uniqueness,
    run_all_checks,
)
from scripts.lib.manifest import (
    Cluster,
    CrossReference,
    LeafEntry,
    Manifest,
    load_manifest,
)


class TestDeadReferences:
    def test_no_issues_when_files_exist(self, sample_manifest, populated_dirs):
        skills_dir, library_dir, _ = populated_dirs
        issues = check_dead_references(sample_manifest, library_dir, skills_dir)
        assert len(issues) == 0

    def test_detects_missing_leaf(self, sample_manifest, tmp_skills_dir, tmp_library_dir):
        # Don't create any leaf files
        issues = check_dead_references(sample_manifest, tmp_library_dir, tmp_skills_dir)
        assert len(issues) > 0
        assert all(i.severity == Severity.ERROR for i in issues)
        assert all(i.check == "dead-reference" for i in issues)


class TestUniqueness:
    def test_no_dupes(self, sample_manifest):
        issues = check_uniqueness(sample_manifest)
        assert len(issues) == 0

    def test_detects_dupe(self):
        manifest = Manifest(
            clusters={
                "c1": Cluster(name="c1", description="test", leaves={"dupe": LeafEntry()}),
            },
            standalones=("dupe",),
        )
        issues = check_uniqueness(manifest)
        assert len(issues) == 1
        assert issues[0].check == "uniqueness-violation"


class TestLeafNotDisabled:
    def test_all_disabled(self, sample_manifest, populated_dirs):
        _, library_dir, _ = populated_dirs
        issues = check_leaf_not_disabled(sample_manifest, library_dir)
        assert len(issues) == 0

    def test_detects_not_disabled(self, sample_manifest, tmp_library_dir, write_skill):
        # Write leaves WITHOUT disable-model-invocation
        for cluster in sample_manifest.clusters.values():
            for leaf_name in cluster.leaves:
                write_skill(
                    tmp_library_dir, leaf_name,
                    f"---\nname: {leaf_name}\n---\n"
                )
        issues = check_leaf_not_disabled(sample_manifest, tmp_library_dir)
        assert len(issues) == 5  # all 5 leaves


class TestAlwaysOnLeaf:
    def test_no_issues(self, sample_manifest, populated_dirs):
        _, library_dir, _ = populated_dirs
        issues = check_always_on_leaf(sample_manifest, library_dir)
        assert len(issues) == 0

    def test_detects_always_true(self, sample_manifest, tmp_library_dir, write_skill):
        write_skill(
            tmp_library_dir, "librarium",
            "---\nname: librarium\nalways: true\n---\n"
        )
        issues = check_always_on_leaf(sample_manifest, tmp_library_dir)
        assert len(issues) == 1
        assert issues[0].check == "always-on-leaf"


class TestOrphanedDisabled:
    def test_no_orphans(self, sample_manifest, populated_dirs):
        skills_dir, library_dir, _ = populated_dirs
        issues = check_orphaned_disabled(sample_manifest, library_dir, skills_dir)
        assert len(issues) == 0

    def test_detects_orphan(self, sample_manifest, populated_dirs, write_skill):
        skills_dir, library_dir, _ = populated_dirs
        write_skill(
            library_dir, "unknown-skill",
            "---\nname: unknown-skill\ndisable-model-invocation: true\n---\n"
        )
        issues = check_orphaned_disabled(sample_manifest, library_dir, skills_dir)
        assert len(issues) == 1
        assert issues[0].skill == "unknown-skill"


class TestUnclusteredBudget:
    def test_under_budget(self, sample_manifest, populated_dirs):
        skills_dir, _, _ = populated_dirs
        issues = check_unclustered_budget(sample_manifest, skills_dir)
        assert len(issues) == 0

    def test_over_budget(self, tmp_skills_dir, write_skill):
        # Create 30 visible skills
        for i in range(30):
            write_skill(
                tmp_skills_dir, f"skill-{i:02d}",
                f"---\nname: skill-{i:02d}\n---\n"
            )
        manifest = Manifest(unclustered_budget=5)
        issues = check_unclustered_budget(manifest, tmp_skills_dir)
        assert len(issues) == 1
        assert "30 visible" in issues[0].message


class TestClusterTooLarge:
    def test_normal_size(self, sample_manifest):
        issues = check_cluster_too_large(sample_manifest)
        assert len(issues) == 0

    def test_too_large(self):
        leaves = {f"leaf-{i:02d}": LeafEntry() for i in range(20)}
        manifest = Manifest(
            clusters={"big": Cluster(name="big", description="test", leaves=leaves)}
        )
        issues = check_cluster_too_large(manifest)
        assert len(issues) == 1
        assert "20 leaves" in issues[0].message


class TestCrossrefMissing:
    def test_crossref_exists(self, populated_dirs):
        skills_dir, library_dir, manifest_path = populated_dirs
        # Add the cross-referenced skill
        (library_dir / "obsidian-index").mkdir(exist_ok=True)
        (library_dir / "obsidian-index" / "SKILL.md").write_text("---\nname: obsidian-index\n---\n")

        manifest = load_manifest(manifest_path)
        issues = check_crossref_missing(manifest, library_dir, skills_dir)
        assert len(issues) == 0

    def test_crossref_missing(self, sample_manifest, tmp_skills_dir, tmp_library_dir):
        issues = check_crossref_missing(sample_manifest, tmp_library_dir, tmp_skills_dir)
        assert len(issues) == 1
        assert issues[0].skill == "obsidian-index"


class TestNoDescription:
    def test_all_have_hints(self, sample_manifest):
        issues = check_no_description(sample_manifest)
        assert len(issues) == 0

    def test_missing_hint(self):
        manifest = Manifest(
            clusters={
                "c1": Cluster(
                    name="c1",
                    description="test",
                    leaves={"no-hint": LeafEntry(routing_hint=None)},
                ),
            },
        )
        issues = check_no_description(manifest)
        assert len(issues) == 1


class TestRunAllChecks:
    def test_clean_environment(self, populated_dirs):
        skills_dir, library_dir, manifest_path = populated_dirs
        # Add cross-referenced skill
        (library_dir / "obsidian-index").mkdir(exist_ok=True)
        (library_dir / "obsidian-index" / "SKILL.md").write_text("---\nname: obsidian-index\n---\n")

        manifest = load_manifest(manifest_path)
        issues = run_all_checks(manifest, skills_dir, library_dir)
        # Should be clean (no errors, maybe warnings about budget)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert len(errors) == 0
