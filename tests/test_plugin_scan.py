"""Tests for the plugin-skill scanner (BRO-184)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from provision import (  # noqa: E402
    collect_plugin_catalog,
    collect_global_catalog,
    _semver_key,
)


def _write_skill(path: Path, name: str, description: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\nbody\n"
    )


class TestSemverKey:
    def test_orders_semvers_correctly(self):
        versions = ["2.9.6", "3.3.0", "3.10.1", "1.0.0", "unknown"]
        ordered = sorted(versions, key=_semver_key)
        assert ordered[0] == "unknown"  # unknown sorts first
        assert ordered[-1] == "3.10.1"  # highest

    def test_picks_latest_correctly(self):
        versions = ["3.10.1", "3.9.9", "3.10.0"]
        latest = max(versions, key=_semver_key)
        assert latest == "3.10.1"


class TestCollectPluginCatalog:
    def test_empty_when_no_plugins_dir(self, tmp_path):
        out = collect_plugin_catalog(tmp_path / "missing")
        assert out == []

    def test_indexes_a_plugin_with_skills_subdir(self, tmp_path):
        cache = tmp_path / "plugins" / "cache"
        _write_skill(
            cache / "official" / "superpowers" / "5.1.0" / "skills" / "writing-plans" / "SKILL.md",
            "writing-plans",
            "Plan-writing skill.",
        )
        _write_skill(
            cache / "official" / "superpowers" / "5.1.0" / "skills" / "brainstorming" / "SKILL.md",
            "brainstorming",
            "Socratic brainstorming.",
        )
        out = collect_plugin_catalog(cache)
        names = {c["name"] for c in out}
        assert names == {"superpowers:writing-plans", "superpowers:brainstorming"}

    def test_indexes_a_plugin_with_skill_md_at_root(self, tmp_path):
        cache = tmp_path / "plugins" / "cache"
        _write_skill(
            cache / "research" / "last30days" / "2.9.6" / "SKILL.md",
            "last30days",
            "Research from the last 30 days.",
        )
        out = collect_plugin_catalog(cache)
        names = {c["name"] for c in out}
        assert "last30days:last30days" in names

    def test_picks_latest_version_when_multiple_installed(self, tmp_path):
        cache = tmp_path / "plugins" / "cache"
        _write_skill(
            cache / "research" / "last30days" / "2.9.6" / "SKILL.md",
            "last30days",
            "old",
        )
        _write_skill(
            cache / "research" / "last30days" / "3.3.0" / "SKILL.md",
            "last30days",
            "new",
        )
        out = collect_plugin_catalog(cache)
        entries = [c for c in out if c["name"] == "last30days:last30days"]
        assert len(entries) == 1
        assert entries[0]["description"] == "new"
        assert "3.3.0" in entries[0]["origin"]

    def test_preserves_already_namespaced_skill_name(self, tmp_path):
        cache = tmp_path / "plugins" / "cache"
        _write_skill(
            cache / "ce" / "compound-engineering" / "2.60.0" / "skills" / "compound-refresh" / "SKILL.md",
            "ce:compound-refresh",
            "Refresh compound projects.",
        )
        out = collect_plugin_catalog(cache)
        names = {c["name"] for c in out}
        assert names == {"ce:compound-refresh"}

    def test_origin_records_marketplace_plugin_and_version(self, tmp_path):
        cache = tmp_path / "plugins" / "cache"
        _write_skill(
            cache / "ms1" / "plug" / "1.0.0" / "skills" / "x" / "SKILL.md", "x", "y"
        )
        out = collect_plugin_catalog(cache)
        assert out[0]["origin"] == "plugin:ms1/plug@1.0.0"


class TestCollectGlobalCatalog:
    def test_merges_personal_and_plugin(self, tmp_path):
        personal = tmp_path / "skills"
        cache = tmp_path / "plugins" / "cache"
        _write_skill(personal / "tdd" / "SKILL.md", "tdd", "TDD.")
        _write_skill(
            cache / "ms" / "superpowers" / "5.0.0" / "skills" / "plans" / "SKILL.md",
            "plans",
            "Plans.",
        )
        out = collect_global_catalog(personal, plugins_cache_dir=cache)
        names = {c["name"] for c in out}
        assert names == {"tdd", "superpowers:plans"}
        origins = {c["name"]: c.get("origin") for c in out}
        assert origins["tdd"] == "personal"
        assert origins["superpowers:plans"].startswith("plugin:")

    def test_handles_missing_plugins_cache(self, tmp_path):
        personal = tmp_path / "skills"
        _write_skill(personal / "tdd" / "SKILL.md", "tdd", "TDD.")
        out = collect_global_catalog(personal, plugins_cache_dir=tmp_path / "missing")
        names = {c["name"] for c in out}
        assert names == {"tdd"}
