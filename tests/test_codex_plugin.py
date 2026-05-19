"""Validate the Codex plugin manifest.

The Codex plugin format mirrors the example bundled with the Codex runtime:
    .codex-plugin/plugin.json — the manifest
    .agents/plugins/marketplace.json — registers this plugin in a local marketplace
        (path is Codex convention; marketplace root resolves to the repo root)
    skills/<name>/SKILL.md — the actual skills (shared with other platforms)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CODEX_PLUGIN_DIR = REPO_ROOT / ".codex-plugin"
PLUGIN_JSON = CODEX_PLUGIN_DIR / "plugin.json"
MARKETPLACE_JSON = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"
CLAUDE_PLUGIN_JSON = REPO_ROOT / ".claude-plugin" / "plugin.json"


class TestCodexPluginManifest:
    def test_plugin_json_exists(self):
        assert PLUGIN_JSON.exists(), f"Missing {PLUGIN_JSON}"

    def test_plugin_json_is_valid(self):
        data = json.loads(PLUGIN_JSON.read_text())
        assert data["name"] == "skill-tree"
        assert "version" in data
        assert "description" in data
        assert "license" in data

    def test_skills_path_points_to_skills_dir(self):
        data = json.loads(PLUGIN_JSON.read_text())
        skills_path = data.get("skills")
        assert skills_path is not None
        assert skills_path.rstrip("/").endswith("skills")
        assert (REPO_ROOT / skills_path.lstrip("./").rstrip("/")).is_dir()

    def test_interface_block_complete(self):
        """interface{} controls how Codex displays the plugin to the user."""
        data = json.loads(PLUGIN_JSON.read_text())
        iface = data.get("interface", {})
        for key in ("displayName", "shortDescription", "longDescription"):
            assert iface.get(key), f"interface.{key} missing or empty"

    def test_version_matches_claude_plugin(self):
        """Codex and Claude Code plugin versions should stay in lockstep."""
        codex = json.loads(PLUGIN_JSON.read_text())
        claude = json.loads(CLAUDE_PLUGIN_JSON.read_text())
        assert codex["version"] == claude["version"], (
            "Codex and Claude Code plugin versions diverged — bump both together."
        )

    def test_metadata_matches_claude_plugin(self):
        codex = json.loads(PLUGIN_JSON.read_text())
        claude = json.loads(CLAUDE_PLUGIN_JSON.read_text())
        assert codex["name"] == claude["name"]
        assert codex["license"] == claude["license"]
        assert codex["repository"] == claude["repository"]


class TestCodexMarketplace:
    def test_marketplace_json_exists(self):
        assert MARKETPLACE_JSON.exists()

    def test_marketplace_lists_skill_tree(self):
        data = json.loads(MARKETPLACE_JSON.read_text())
        names = {p["name"] for p in data.get("plugins", [])}
        assert "skill-tree" in names

    def test_marketplace_source_is_resolvable(self):
        data = json.loads(MARKETPLACE_JSON.read_text())
        entry = next(p for p in data["plugins"] if p["name"] == "skill-tree")
        src = entry["source"]
        assert src["source"] == "local"
        # Codex convention: path is relative to the MARKETPLACE ROOT (= REPO_ROOT here),
        # not to the marketplace.json file. Marketplace root is the dir Codex was pointed at
        # via `codex plugin marketplace add <dir>`.
        resolved = (REPO_ROOT / src["path"]).resolve()
        # The plugin manifest lives at <plugin_root>/.codex-plugin/plugin.json
        assert (resolved / ".codex-plugin" / "plugin.json").exists()

    def test_marketplace_policy_authentication_value(self):
        """Codex requires authentication to be ON_INSTALL or ON_USE (not NONE).
        Verified empirically — `codex plugin marketplace add` rejects unknown variants.
        """
        data = json.loads(MARKETPLACE_JSON.read_text())
        entry = next(p for p in data["plugins"] if p["name"] == "skill-tree")
        assert entry["policy"]["authentication"] in {"ON_INSTALL", "ON_USE"}
