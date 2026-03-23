"""Tests for sync.py — cluster file regeneration and disable flag management."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.lib.manifest import Cluster, LeafEntry, Manifest, serialize_manifest
from scripts.sync import sync_cluster_files, sync_codex_yaml, sync_disable_flags


class TestSyncClusterFiles:
    def test_creates_new_cluster(self, populated_dirs):
        skills_dir, library_dir, manifest_path = populated_dirs
        from scripts.lib.manifest import load_manifest

        manifest = load_manifest(manifest_path)

        # Delete one cluster file to test creation
        (skills_dir / "dev-tools" / "SKILL.md").unlink()

        actions = sync_cluster_files(manifest, skills_dir, str(library_dir))
        assert any("create cluster: dev-tools" in a for a in actions)
        assert (skills_dir / "dev-tools" / "SKILL.md").exists()

    def test_updates_changed_cluster(self, populated_dirs):
        skills_dir, library_dir, manifest_path = populated_dirs
        from scripts.lib.manifest import load_manifest

        manifest = load_manifest(manifest_path)

        # Write different content to force update
        (skills_dir / "research-index" / "SKILL.md").write_text("old content")

        actions = sync_cluster_files(manifest, skills_dir, str(library_dir))
        assert any("update cluster: research-index" in a for a in actions)

    def test_no_action_when_in_sync(self, populated_dirs):
        skills_dir, library_dir, manifest_path = populated_dirs
        from scripts.lib.manifest import load_manifest

        manifest = load_manifest(manifest_path)

        # First sync to get files in canonical state
        sync_cluster_files(manifest, skills_dir, str(library_dir))
        # Second sync should be no-op
        actions = sync_cluster_files(manifest, skills_dir, str(library_dir))
        assert actions == []

    def test_dry_run_does_not_write(self, populated_dirs):
        skills_dir, library_dir, manifest_path = populated_dirs
        from scripts.lib.manifest import load_manifest

        manifest = load_manifest(manifest_path)
        (skills_dir / "dev-tools" / "SKILL.md").unlink()

        actions = sync_cluster_files(manifest, skills_dir, str(library_dir), dry_run=True)
        assert len(actions) > 0
        assert not (skills_dir / "dev-tools" / "SKILL.md").exists()


class TestSyncDisableFlags:
    def test_disables_non_disabled_leaf(self, populated_dirs, write_skill):
        skills_dir, library_dir, manifest_path = populated_dirs
        from scripts.lib.manifest import load_manifest

        manifest = load_manifest(manifest_path)

        # Write a leaf WITHOUT disable flag
        write_skill(
            library_dir,
            "librarium",
            "---\nname: librarium\ndescription: test\n---\n# Content\n",
        )

        actions = sync_disable_flags(manifest, library_dir)
        assert any("librarium" in a for a in actions)

        # Verify the flag was set
        content = (library_dir / "librarium" / "SKILL.md").read_text()
        assert "disable-model-invocation: true" in content

    def test_skips_already_disabled(self, populated_dirs):
        skills_dir, library_dir, manifest_path = populated_dirs
        from scripts.lib.manifest import load_manifest

        manifest = load_manifest(manifest_path)

        # All leaves in populated_dirs already have disable flag
        actions = sync_disable_flags(manifest, library_dir)
        assert actions == []


class TestSyncCodexYaml:
    def test_generates_yaml_for_leaves(self, populated_dirs):
        skills_dir, library_dir, manifest_path = populated_dirs
        from scripts.lib.manifest import load_manifest

        manifest = load_manifest(manifest_path)

        actions = sync_codex_yaml(manifest, library_dir)
        assert len(actions) > 0

        # Check that agents/openai.yaml was created for each leaf
        yaml_path = library_dir / "librarium" / "agents" / "openai.yaml"
        assert yaml_path.exists()
        content = yaml_path.read_text()
        assert "allow_implicit_invocation: false" in content

    def test_generates_yaml_for_reference_nodes(self, populated_dirs):
        skills_dir, library_dir, manifest_path = populated_dirs
        from scripts.lib.manifest import load_manifest

        manifest = load_manifest(manifest_path)
        sync_codex_yaml(manifest, library_dir)

        yaml_path = library_dir / "agent-cli-tools" / "agents" / "openai.yaml"
        assert yaml_path.exists()
        content = yaml_path.read_text()
        assert "allow_implicit_invocation: false" in content

    def test_generates_yaml_for_deprecated(self, populated_dirs):
        skills_dir, library_dir, manifest_path = populated_dirs
        from scripts.lib.manifest import load_manifest

        manifest = load_manifest(manifest_path)
        sync_codex_yaml(manifest, library_dir)

        yaml_path = library_dir / "old-skill" / "agents" / "openai.yaml"
        assert yaml_path.exists()

    def test_dry_run_does_not_write(self, populated_dirs):
        skills_dir, library_dir, manifest_path = populated_dirs
        from scripts.lib.manifest import load_manifest

        manifest = load_manifest(manifest_path)

        actions = sync_codex_yaml(manifest, library_dir, dry_run=True)
        assert len(actions) > 0
        # No YAML file should exist
        assert not (library_dir / "librarium" / "agents" / "openai.yaml").exists()

    def test_skips_when_yaml_exists_and_matches(self, populated_dirs):
        skills_dir, library_dir, manifest_path = populated_dirs
        from scripts.lib.manifest import load_manifest

        manifest = load_manifest(manifest_path)

        # First sync generates files
        sync_codex_yaml(manifest, library_dir)
        # Second sync should be no-op
        actions = sync_codex_yaml(manifest, library_dir)
        assert actions == []

    def test_uses_routing_hint_as_description(self, populated_dirs):
        skills_dir, library_dir, manifest_path = populated_dirs
        from scripts.lib.manifest import load_manifest

        manifest = load_manifest(manifest_path)
        sync_codex_yaml(manifest, library_dir)

        content = (library_dir / "librarium" / "agents" / "openai.yaml").read_text()
        assert "Multi-provider fan-out research" in content

    def test_falls_back_to_frontmatter_description(self, populated_dirs, write_skill):
        skills_dir, library_dir, manifest_path = populated_dirs

        # Create a manifest with a leaf that has no routing hint
        manifest = Manifest(
            clusters={
                "test-cluster": Cluster(
                    name="test-cluster",
                    description="Test cluster",
                    leaves={"no-hint-leaf": LeafEntry(routing_hint=None)},
                ),
            },
        )

        # Write the leaf with a description in frontmatter
        write_skill(
            library_dir,
            "no-hint-leaf",
            "---\nname: no-hint-leaf\ndescription: Leaf from frontmatter desc\ndisable-model-invocation: true\n---\n",
        )

        actions = sync_codex_yaml(manifest, library_dir)
        assert len(actions) > 0

        content = (library_dir / "no-hint-leaf" / "agents" / "openai.yaml").read_text()
        assert "Leaf from frontmatter desc" in content
