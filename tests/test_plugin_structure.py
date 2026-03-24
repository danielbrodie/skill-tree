"""Tests for Claude Code plugin structure — manifest, paths, and conventions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestPluginManifest:
    def test_exists(self):
        assert (REPO_ROOT / ".claude-plugin" / "plugin.json").exists()

    def test_required_fields(self):
        data = json.loads((REPO_ROOT / ".claude-plugin" / "plugin.json").read_text())
        assert "name" in data
        assert data["name"] == "skill-tree"

    def test_has_author(self):
        data = json.loads((REPO_ROOT / ".claude-plugin" / "plugin.json").read_text())
        assert "author" in data
        assert "name" in data["author"]

    def test_has_metadata(self):
        data = json.loads((REPO_ROOT / ".claude-plugin" / "plugin.json").read_text())
        assert "version" in data
        assert "description" in data
        assert "license" in data
        assert "repository" in data
        assert "keywords" in data


class TestPluginRootVariable:
    """Skills and hooks must use ${CLAUDE_PLUGIN_ROOT} for portability after cache install."""

    COMMAND_SKILLS = ["check", "setup", "fetch"]

    def test_skills_use_plugin_root(self):
        for skill in self.COMMAND_SKILLS:
            content = (REPO_ROOT / "skills" / skill / "SKILL.md").read_text()
            assert "${CLAUDE_PLUGIN_ROOT}" in content, (
                f"skills/{skill}/SKILL.md must use ${{CLAUDE_PLUGIN_ROOT}} "
                f"for script paths — relative paths break after marketplace install"
            )

    def test_skills_no_bare_relative_scripts(self):
        """No skill should reference scripts/ without ${CLAUDE_PLUGIN_ROOT}."""
        for skill in self.COMMAND_SKILLS:
            content = (REPO_ROOT / "skills" / skill / "SKILL.md").read_text()
            lines = content.split("\n")
            for line in lines:
                if "uv run" in line and "scripts/" in line:
                    assert "${CLAUDE_PLUGIN_ROOT}" in line, (
                        f"skills/{skill}/SKILL.md has bare 'uv run scripts/' — "
                        f"must use ${{CLAUDE_PLUGIN_ROOT}}/scripts/"
                    )

    def test_hook_uses_plugin_root(self):
        content = (REPO_ROOT / "hooks" / "hooks.json").read_text()
        assert "${CLAUDE_PLUGIN_ROOT}" in content, (
            "hooks.json must use ${CLAUDE_PLUGIN_ROOT} for script paths"
        )


class TestMarketplaceManifest:
    def test_exists(self):
        assert (REPO_ROOT / ".claude-plugin" / "marketplace.json").exists()

    def test_version_matches_plugin(self):
        plugin = json.loads((REPO_ROOT / ".claude-plugin" / "plugin.json").read_text())
        marketplace = json.loads((REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text())
        mp_version = marketplace["plugins"][0].get("version")
        if mp_version:
            assert mp_version == plugin["version"], "marketplace.json version must match plugin.json"
