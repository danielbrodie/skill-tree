"""Tests for bin/skill-tree dispatcher."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
WRAPPER = REPO_ROOT / "bin" / "skill-tree"


def _run(args, env_extra=None):
    env = dict(os.environ)
    env.pop("CLAUDE_PLUGIN_ROOT", None)
    env.pop("SKILL_TREE_ROOT", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [str(WRAPPER), *args],
        capture_output=True, text=True, env=env,
    )


class TestHelp:
    def test_no_args_prints_usage(self):
        r = _run([])
        assert r.returncode == 0
        assert "Usage: skill-tree" in r.stdout
        assert "check" in r.stdout
        assert "provision" in r.stdout

    def test_help_flag(self):
        r = _run(["--help"])
        assert r.returncode == 0
        assert "Subcommands" in r.stdout

    def test_unknown_subcommand_exits_2(self):
        r = _run(["totally-not-a-real-command"])
        assert r.returncode == 2
        assert "unknown subcommand" in r.stderr


class TestDispatch:
    def test_known_subcommand_runs(self):
        # `list` is a simple subcommand. Asserting only that returncode is in
        # {0, 2} would silently accept the wrapper's unknown-subcommand failure
        # path (also returncode 2) — a regression where `list` stopped being
        # recognized would still pass. Require evidence that dispatch
        # succeeded: stderr must not contain the unknown-subcommand marker.
        r = _run(["list", "--help"], env_extra={"SKILL_TREE_ROOT": str(REPO_ROOT)})
        combined = (r.stdout + r.stderr).lower()
        assert "unknown subcommand" not in combined, (
            f"dispatch failed: {r.stderr}"
        )
        assert r.returncode in {0, 2}, f"stderr: {r.stderr}"

    def test_hyphen_alias_for_underscore_script(self):
        # sync-project (hyphen) should dispatch to sync_project.py
        r = _run(
            ["sync-project", "--dry-run", "--project-root", "/tmp/sk-test-nonexistent"],
            env_extra={"SKILL_TREE_ROOT": str(REPO_ROOT)},
        )
        # Either runs (returncode 0 or 1 — depending on whether the path exists)
        # or fails with a script-level error, but should NOT be "unknown subcommand"
        combined = (r.stdout + r.stderr).lower()
        assert "unknown subcommand" not in combined


class TestRootResolution:
    def test_skill_tree_root_env_var_takes_priority(self, tmp_path):
        # Build a fake plugin root with a unique scripts/ subdir
        fake_root = tmp_path / "fake-plugin"
        fake_scripts = fake_root / "scripts"
        fake_scripts.mkdir(parents=True)
        (fake_scripts / "marker.py").write_text("print('from fake root')")

        r = _run(["marker"], env_extra={"SKILL_TREE_ROOT": str(fake_root)})
        assert r.returncode == 0
        assert "from fake root" in r.stdout

    def test_claude_plugin_root_fallback(self, tmp_path):
        fake_root = tmp_path / "fake-plugin"
        fake_scripts = fake_root / "scripts"
        fake_scripts.mkdir(parents=True)
        (fake_scripts / "marker.py").write_text("print('from claude root')")

        r = _run(["marker"], env_extra={"CLAUDE_PLUGIN_ROOT": str(fake_root)})
        assert r.returncode == 0
        assert "from claude root" in r.stdout

    def test_skill_tree_root_wins_over_claude_plugin_root(self, tmp_path):
        skill_root = tmp_path / "skill-root"
        (skill_root / "scripts").mkdir(parents=True)
        (skill_root / "scripts" / "marker.py").write_text("print('skill wins')")

        claude_root = tmp_path / "claude-root"
        (claude_root / "scripts").mkdir(parents=True)
        (claude_root / "scripts" / "marker.py").write_text("print('claude loses')")

        r = _run(
            ["marker"],
            env_extra={
                "SKILL_TREE_ROOT": str(skill_root),
                "CLAUDE_PLUGIN_ROOT": str(claude_root),
            },
        )
        assert r.returncode == 0
        assert "skill wins" in r.stdout
        assert "claude loses" not in r.stdout

    def test_self_location_fallback_when_no_env(self):
        # No env vars set — wrapper should resolve via its own location
        r = _run(["check"])
        # `check` exists at REPO_ROOT/scripts/check.py so this should work
        assert r.returncode == 0, f"stderr: {r.stderr}"
        # Output is the manifest check result
        assert "All checks passed" in r.stdout or "errors" in r.stdout
