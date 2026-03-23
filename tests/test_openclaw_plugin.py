"""Tests for OpenClaw plugin structure validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
OPENCLAW_ROOT = REPO_ROOT / "openclaw"


class TestOpenClawPluginJson:
    def test_exists(self):
        assert (OPENCLAW_ROOT / "openclaw.plugin.json").exists()

    def test_valid_json(self):
        data = json.loads((OPENCLAW_ROOT / "openclaw.plugin.json").read_text())
        assert isinstance(data, dict)

    def test_required_fields(self):
        data = json.loads((OPENCLAW_ROOT / "openclaw.plugin.json").read_text())
        assert data["id"] == "skill-tree"
        assert "configSchema" in data
        assert "skills" in data

    def test_skills_path_exists(self):
        data = json.loads((OPENCLAW_ROOT / "openclaw.plugin.json").read_text())
        for skill_path in data["skills"]:
            resolved = OPENCLAW_ROOT / skill_path
            assert resolved.is_dir(), f"Skills path {skill_path} does not exist"


class TestOpenClawPackageJson:
    def test_exists(self):
        assert (OPENCLAW_ROOT / "package.json").exists()

    def test_has_openclaw_extensions(self):
        data = json.loads((OPENCLAW_ROOT / "package.json").read_text())
        assert "openclaw" in data
        assert "extensions" in data["openclaw"]
        assert len(data["openclaw"]["extensions"]) > 0

    def test_extension_entry_exists(self):
        data = json.loads((OPENCLAW_ROOT / "package.json").read_text())
        for entry in data["openclaw"]["extensions"]:
            assert (OPENCLAW_ROOT / entry).exists(), f"Extension entry {entry} not found"


class TestOpenClawIndexTs:
    def test_exists(self):
        assert (OPENCLAW_ROOT / "index.ts").exists()

    def test_exports_function(self):
        content = (OPENCLAW_ROOT / "index.ts").read_text()
        assert "export default" in content


class TestOpenClawSkills:
    EXPECTED_SKILLS = ["check", "setup", "fetch", "skill-analysis"]

    def test_skill_directories_exist(self):
        for skill in self.EXPECTED_SKILLS:
            skill_dir = OPENCLAW_ROOT / "skills" / skill
            assert skill_dir.is_dir(), f"Missing skill directory: {skill}"

    def test_skill_md_files_exist(self):
        for skill in self.EXPECTED_SKILLS:
            skill_md = OPENCLAW_ROOT / "skills" / skill / "SKILL.md"
            assert skill_md.exists(), f"Missing SKILL.md for {skill}"

    def test_skills_reference_openclaw_paths(self):
        """Command skills should use ~/.openclaw/skills paths."""
        for skill in ["check", "setup", "fetch"]:
            content = (OPENCLAW_ROOT / "skills" / skill / "SKILL.md").read_text()
            assert "~/.openclaw/skills" in content, f"{skill} missing ~/.openclaw/skills reference"

    def test_skills_use_basedir_interpolation(self):
        """Command skills should use {baseDir} for script paths."""
        for skill in ["check", "setup", "fetch"]:
            content = (OPENCLAW_ROOT / "skills" / skill / "SKILL.md").read_text()
            assert "{baseDir}" in content, f"{skill} missing {{baseDir}} interpolation"

    def test_scripts_ship_with_plugin(self):
        """Scripts must be inside the openclaw/ package (not referenced externally)."""
        scripts_dir = OPENCLAW_ROOT / "scripts"
        assert scripts_dir.is_dir(), "scripts/ directory missing from openclaw package"
        for script in ["status.py", "init.py", "scan.py", "sync.py", "add.py"]:
            assert (scripts_dir / script).exists(), f"Missing {script} in openclaw/scripts/"
        assert (scripts_dir / "lib").is_dir(), "scripts/lib/ missing from openclaw package"

    def test_skills_have_uv_requirement(self):
        """Command skills should gate on uv being available."""
        for skill in ["check", "setup", "fetch"]:
            content = (OPENCLAW_ROOT / "skills" / skill / "SKILL.md").read_text()
            assert '"bins": ["uv"]' in content, f"{skill} missing uv bin requirement"

    def test_skill_analysis_mentions_commands(self):
        content = (OPENCLAW_ROOT / "skills" / "skill-analysis" / "SKILL.md").read_text()
        assert "/check" in content
        assert "/setup" in content
        assert "/fetch" in content

    def test_parity_with_claude_code_skills(self):
        """Every OpenClaw skill should have a matching Claude Code skill."""
        for skill in self.EXPECTED_SKILLS:
            cc_skill = REPO_ROOT / "skills" / skill / "SKILL.md"
            assert cc_skill.exists(), f"No Claude Code parity for {skill}"


class TestSameDirectoryCompatibility:
    """Verify scripts work when skills-dir and library-dir are the same path."""

    def test_sync_cluster_to_same_dir(self, populated_dirs, write_skill):
        from scripts.lib.manifest import Cluster, LeafEntry, Manifest
        from scripts.sync import sync_cluster_files, sync_disable_flags

        # Use library_dir for both (same directory)
        _, library_dir, _ = populated_dirs
        manifest = Manifest(
            clusters={
                "test-cluster": Cluster(
                    name="test-cluster",
                    description="Test",
                    leaves={"librarium": LeafEntry(routing_hint="hint")},
                ),
            },
        )

        # Write leaf in same dir
        write_skill(library_dir, "librarium", "---\nname: librarium\ndescription: test\n---\n")

        # Sync routers to same dir
        actions = sync_cluster_files(manifest, library_dir, str(library_dir))
        assert any("test-cluster" in a for a in actions)
        assert (library_dir / "test-cluster" / "SKILL.md").exists()

        # Sync disable flags in same dir
        actions = sync_disable_flags(manifest, library_dir)
        assert any("librarium" in a for a in actions)

    def test_status_same_dir(self, tmp_path, write_skill):
        import json
        from scripts.lib.manifest import Cluster, LeafEntry, Manifest, save_manifest
        from scripts.status import run_checks

        base = tmp_path / "skills"
        base.mkdir()

        manifest = Manifest(
            clusters={
                "test": Cluster(
                    name="test",
                    description="Test",
                    leaves={"leaf1": LeafEntry(routing_hint="hint")},
                ),
            },
        )

        # Write manifest
        manifest_dir = base / "skill-tree"
        manifest_dir.mkdir()
        save_manifest(manifest, manifest_dir / "manifest.json")

        # Write leaf with disable flag
        write_skill(base, "leaf1", "---\nname: leaf1\ndescription: test\ndisable-model-invocation: true\n---\n")

        # Check with same dir for both
        errors, warnings = run_checks(manifest, base, base)
        assert errors == []
