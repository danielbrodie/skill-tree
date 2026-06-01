"""Tests for the deterministic cross-ecosystem doctor.

Each detector is a pure function over filesystem state / parsed registry data,
so every test builds a fixture that reproduces exactly one failure-mode
signature from docs/ecosystem-map.md (cited by number) and asserts the detector
fires — plus a clean-state test asserting no false positive.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.doctor import (
    DoctorReport,
    Finding,
    detect_cross_registry_duplicates,
    detect_fanout_absent_agents,
    detect_stale_plugin_cache,
    detect_symlink_rot,
    detect_unlinked_agent_skills,
    findings_to_dicts,
    load_environment,
    run_doctor,
)

# ---------------------------------------------------------------------------
# Signature #4 — symlink rot
# ---------------------------------------------------------------------------


def test_detects_rotted_symlink(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    skills.mkdir()
    missing_target = tmp_path / "gone"  # never created
    (skills / "ghost").symlink_to(missing_target)

    findings = detect_symlink_rot(skills)

    assert len(findings) == 1
    f = findings[0]
    assert isinstance(f, Finding)
    assert f.signature_id == 4
    assert "ghost" in f.observation


def test_healthy_symlink_not_flagged(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    skills.mkdir()
    target = tmp_path / "real-skill"
    target.mkdir()
    (target / "SKILL.md").write_text("---\nname: real\n---\n", encoding="utf-8")
    (skills / "real").symlink_to(target)

    assert detect_symlink_rot(skills) == []


def test_plain_directory_not_flagged_as_rot(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    skills.mkdir()
    real = skills / "local-skill"
    real.mkdir()
    (real / "SKILL.md").write_text("---\nname: local\n---\n", encoding="utf-8")

    assert detect_symlink_rot(skills) == []


def test_missing_skills_dir_is_empty(tmp_path: Path) -> None:
    assert detect_symlink_rot(tmp_path / "does-not-exist") == []


# ---------------------------------------------------------------------------
# Signature #2 — stale plugin-cache version dirs
# ---------------------------------------------------------------------------


def test_detects_stale_plugin_cache_version(tmp_path: Path) -> None:
    plugin = tmp_path / "cache" / "mkt" / "plug"
    live = plugin / "2.0.0"
    live.mkdir(parents=True)
    stale = plugin / "1.0.0"
    stale.mkdir()
    installed = {
        "plugins": {"plug@mkt": [{"installPath": str(live), "version": "2.0.0"}]}
    }

    findings = detect_stale_plugin_cache(installed)

    assert len(findings) == 1
    f = findings[0]
    assert f.signature_id == 2
    assert "1.0.0" in f.observation
    assert str(stale) in f.paths


def test_single_installed_version_not_flagged(tmp_path: Path) -> None:
    plugin = tmp_path / "cache" / "mkt" / "plug"
    live = plugin / "2.0.0"
    live.mkdir(parents=True)
    installed = {
        "plugins": {"plug@mkt": [{"installPath": str(live), "version": "2.0.0"}]}
    }

    assert detect_stale_plugin_cache(installed) == []


def test_two_install_records_keep_both_versions(tmp_path: Path) -> None:
    # A plugin installed at two scopes references two version dirs — neither is stale.
    plugin = tmp_path / "cache" / "mkt" / "plug"
    v1 = plugin / "1.0.0"
    v1.mkdir(parents=True)
    v2 = plugin / "2.0.0"
    v2.mkdir()
    installed = {
        "plugins": {
            "plug@mkt": [
                {"installPath": str(v1), "version": "1.0.0"},
                {"installPath": str(v2), "version": "2.0.0"},
            ]
        }
    }

    assert detect_stale_plugin_cache(installed) == []


def test_empty_installed_plugins_no_findings() -> None:
    assert detect_stale_plugin_cache({"plugins": {}}) == []


# ---------------------------------------------------------------------------
# Signature #1 — vercel-labs fan-out targets agents that aren't installed
# ---------------------------------------------------------------------------


def test_detects_fanout_to_absent_agent(tmp_path: Path) -> None:
    home = tmp_path
    (home / ".claude").mkdir()  # claude-code present
    # ~/.cursor intentionally absent
    skill_lock = {"lastSelectedAgents": ["claude-code", "cursor"]}

    findings = detect_fanout_absent_agents(skill_lock, home)

    assert len(findings) == 1
    f = findings[0]
    assert f.signature_id == 1
    assert "cursor" in f.observation


def test_all_selected_agents_present_no_finding(tmp_path: Path) -> None:
    home = tmp_path
    (home / ".claude").mkdir()
    (home / ".codex").mkdir()
    skill_lock = {"lastSelectedAgents": ["claude-code", "codex"]}

    assert detect_fanout_absent_agents(skill_lock, home) == []


def test_unknown_agent_skipped_not_flagged(tmp_path: Path) -> None:
    # An agent we don't have a home-dir mapping for can't be verified — skip it
    # rather than emit a false positive.
    skill_lock = {"lastSelectedAgents": ["some-future-agent"]}

    assert detect_fanout_absent_agents(skill_lock, tmp_path) == []


def test_null_last_selected_agents_does_not_crash(tmp_path: Path) -> None:
    # Explicit JSON null: .get(key, []) returns None, not [] — must not raise.
    assert detect_fanout_absent_agents({"lastSelectedAgents": None}, tmp_path) == []


# ---------------------------------------------------------------------------
# Signature #2 — version-aware: stale manifest vs duplicate vs real skew
# ---------------------------------------------------------------------------


def _version_dir(plugin_dir: Path, name: str, version: str | None = None) -> Path:
    d = plugin_dir / name
    d.mkdir(parents=True, exist_ok=True)
    if version is not None:
        cp = d / ".claude-plugin"
        cp.mkdir()
        (cp / "plugin.json").write_text(
            json.dumps({"version": version}), encoding="utf-8"
        )
    return d


def test_referenced_dir_absent_is_stale_manifest_do_not_delete(tmp_path: Path) -> None:
    # installed_plugins points at 1.0.0 (gone); 2.0.0 is the only dir present.
    plugin = tmp_path / "cache" / "mkt" / "plug"
    present = _version_dir(plugin, "2.0.0", version="2.0.0")
    installed = {
        "plugins": {
            "plug@mkt": [{"installPath": str(plugin / "1.0.0"), "version": "1.0.0"}]
        }
    }

    findings = detect_stale_plugin_cache(installed)

    assert len(findings) == 1
    f = findings[0]
    assert f.signature_id == 2
    assert "1.0.0" in f.observation and "2.0.0" in f.observation
    assert "stale" in f.observation.lower()
    assert "do not delete" in f.suggested_fix.lower()
    # must not be present.name being recommended for rm
    assert str(present) not in f.suggested_fix


def test_same_version_reextraction_labeled_duplicate_not_skew(tmp_path: Path) -> None:
    plugin = tmp_path / "cache" / "mkt" / "plug"
    _version_dir(plugin, "5.1.0", version="5.1.0")  # referenced
    extra = _version_dir(
        plugin, "abc123sha", version="5.1.0"
    )  # same version, unreferenced
    installed = {
        "plugins": {
            "plug@mkt": [{"installPath": str(plugin / "5.1.0"), "version": "5.1.0"}]
        }
    }

    findings = detect_stale_plugin_cache(installed)

    assert len(findings) == 1
    f = findings[0]
    assert f.signature_id == 2
    assert (
        "duplicate" in f.observation.lower() or "same version" in f.observation.lower()
    )
    assert (
        "version skew" not in f.observation.lower()
    )  # must not mislabel a same-version dup
    assert str(extra) in f.paths


def test_different_versions_labeled_skew(tmp_path: Path) -> None:
    plugin = tmp_path / "cache" / "mkt" / "plug"
    _version_dir(plugin, "2.0.0", version="2.0.0")  # referenced
    _version_dir(plugin, "1.0.0", version="1.0.0")  # older, unreferenced
    installed = {
        "plugins": {
            "plug@mkt": [{"installPath": str(plugin / "2.0.0"), "version": "2.0.0"}]
        }
    }

    findings = detect_stale_plugin_cache(installed)

    assert len(findings) == 1
    assert findings[0].signature_id == 2
    assert "1.0.0" in findings[0].observation


# ---------------------------------------------------------------------------
# Signature #7 — same skill name in two registries (parallel-registry skew)
# ---------------------------------------------------------------------------


def _write_skill(dir_: Path, name: str) -> None:
    d = dir_ / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(f"---\nname: {name}\n---\n", encoding="utf-8")


def test_detects_cross_registry_duplicate(tmp_path: Path) -> None:
    agents = tmp_path / "agents-skills"
    _write_skill(agents, "dup")
    _write_skill(tmp_path / "cache" / "mkt" / "plug" / "1.0.0" / "skills", "dup")

    findings = detect_cross_registry_duplicates(agents, tmp_path / "cache")

    assert len(findings) == 1
    assert findings[0].signature_id == 7
    assert "dup" in findings[0].observation


def test_distinct_names_across_registries_not_flagged(tmp_path: Path) -> None:
    agents = tmp_path / "agents-skills"
    _write_skill(agents, "only-personal")
    _write_skill(
        tmp_path / "cache" / "mkt" / "plug" / "1.0.0" / "skills", "only-plugin"
    )

    assert detect_cross_registry_duplicates(agents, tmp_path / "cache") == []


# ---------------------------------------------------------------------------
# Signature #5 — skill present in ~/.agents/skills but not linked into ~/.claude/skills
# ---------------------------------------------------------------------------


def test_detects_unlinked_agent_skill(tmp_path: Path) -> None:
    agents = tmp_path / "agents-skills"
    _write_skill(agents, "orphan")
    claude_skills = tmp_path / "claude-skills"
    claude_skills.mkdir()

    findings = detect_unlinked_agent_skills(agents, claude_skills)

    assert len(findings) == 1
    assert findings[0].signature_id == 5
    assert "orphan" in findings[0].observation


def test_linked_agent_skill_not_flagged(tmp_path: Path) -> None:
    agents = tmp_path / "agents-skills"
    _write_skill(agents, "linked")
    claude_skills = tmp_path / "claude-skills"
    claude_skills.mkdir()
    (claude_skills / "linked").symlink_to(agents / "linked")

    assert detect_unlinked_agent_skills(agents, claude_skills) == []


# ---------------------------------------------------------------------------
# Aggregator + report + JSON
# ---------------------------------------------------------------------------


def _empty_env(tmp_path: Path) -> dict:
    claude_skills = tmp_path / ".claude" / "skills"
    claude_skills.mkdir(parents=True)
    agents = tmp_path / ".agents" / "skills"
    agents.mkdir(parents=True)
    return {
        "home": tmp_path,
        "claude_skills_dir": claude_skills,
        "agents_skills_dir": agents,
        "plugin_cache_dir": tmp_path / ".claude" / "plugins" / "cache",
        "installed_plugins": {"plugins": {}},
        "skill_lock": {},
    }


def test_run_doctor_aggregates_findings_and_warns(tmp_path: Path) -> None:
    env = _empty_env(tmp_path)
    (env["claude_skills_dir"] / "ghost").symlink_to(tmp_path / "gone")  # rot → warning

    report = run_doctor(**env)

    assert isinstance(report, DoctorReport)
    assert any(f.signature_id == 4 for f in report.findings)
    assert report.exit_code() == 1  # warnings only


def test_clean_environment_exit_zero(tmp_path: Path) -> None:
    report = run_doctor(**_empty_env(tmp_path))
    assert report.findings == ()
    assert report.exit_code() == 0


def test_info_only_does_not_escalate_exit_code(tmp_path: Path) -> None:
    env = _empty_env(tmp_path)
    _write_skill(env["agents_skills_dir"], "unlinked")  # signature #5 → info

    report = run_doctor(**env)

    assert all(f.severity == "info" for f in report.findings)
    assert report.exit_code() == 0  # info never escalates


def test_run_doctor_scans_symlink_rot_beyond_claude_skills(tmp_path: Path) -> None:
    # A dead symlink in ~/.agents/skills (not just ~/.claude/skills) must be caught.
    env = _empty_env(tmp_path)
    (env["agents_skills_dir"] / "ghost").symlink_to(tmp_path / "gone")

    report = run_doctor(**env)

    assert any(f.signature_id == 4 for f in report.findings)


def test_findings_to_dicts_is_json_serializable(tmp_path: Path) -> None:
    env = _empty_env(tmp_path)
    (env["claude_skills_dir"] / "ghost").symlink_to(tmp_path / "gone")

    report = run_doctor(**env)
    dicts = findings_to_dicts(report.findings)

    import json

    json.dumps(dicts)  # must not raise
    assert dicts[0]["signature_id"] == 4
    assert "observation" in dicts[0]


# ---------------------------------------------------------------------------
# Environment loader
# ---------------------------------------------------------------------------


def test_load_environment_reads_registries(tmp_path: Path) -> None:
    home = tmp_path
    plugins_dir = home / ".claude" / "plugins"
    plugins_dir.mkdir(parents=True)
    (plugins_dir / "installed_plugins.json").write_text(
        '{"plugins": {"p@m": []}}', encoding="utf-8"
    )
    agents = home / ".agents"
    agents.mkdir()
    (agents / ".skill-lock.json").write_text(
        '{"lastSelectedAgents": ["claude-code"]}', encoding="utf-8"
    )

    env = load_environment(home)

    assert env["installed_plugins"] == {"plugins": {"p@m": []}}
    assert env["skill_lock"]["lastSelectedAgents"] == ["claude-code"]
    assert env["claude_skills_dir"] == home / ".claude" / "skills"
    assert env["agents_skills_dir"] == home / ".agents" / "skills"
    assert env["plugin_cache_dir"] == home / ".claude" / "plugins" / "cache"


def test_load_environment_missing_files_default_empty(tmp_path: Path) -> None:
    env = load_environment(tmp_path)
    assert env["installed_plugins"] == {"plugins": {}}
    assert env["skill_lock"] == {}


def test_load_environment_malformed_json_is_safe(tmp_path: Path) -> None:
    plugins_dir = tmp_path / ".claude" / "plugins"
    plugins_dir.mkdir(parents=True)
    (plugins_dir / "installed_plugins.json").write_text(
        "{not valid json", encoding="utf-8"
    )

    env = load_environment(tmp_path)

    assert env["installed_plugins"] == {"plugins": {}}
