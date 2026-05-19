"""Tests for status.py — combined health check + graph overview."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.status import display_status, run_checks
from scripts.lib.manifest import Cluster, LeafEntry, Manifest


class TestRunChecks:
    def test_clean_manifest(self, populated_dirs):
        skills_dir, library_dir, manifest_path = populated_dirs
        from scripts.lib.manifest import load_manifest

        manifest = load_manifest(manifest_path)
        errors, warnings = run_checks(manifest, skills_dir, library_dir)
        assert errors == []

    def test_detects_dead_reference(self, populated_dirs, write_skill):
        skills_dir, library_dir, manifest_path = populated_dirs
        from scripts.lib.manifest import load_manifest

        manifest = load_manifest(manifest_path)
        # Delete a leaf file to create dead reference
        (library_dir / "librarium" / "SKILL.md").unlink()

        errors, warnings = run_checks(manifest, skills_dir, library_dir)
        assert any("dead-reference" in e and "librarium" in e for e in errors)

    def test_detects_leaf_not_disabled(self, populated_dirs, write_skill):
        skills_dir, library_dir, manifest_path = populated_dirs
        from scripts.lib.manifest import load_manifest

        manifest = load_manifest(manifest_path)
        # Rewrite a leaf WITHOUT disable flag
        write_skill(
            library_dir,
            "librarium",
            "---\nname: librarium\ndescription: test\n---\n",
        )

        errors, warnings = run_checks(manifest, skills_dir, library_dir)
        assert any("leaf-not-disabled" in e and "librarium" in e for e in errors)

    def test_parity_with_check_run_all_checks(self, populated_dirs):
        """Regression: status.run_checks used to duplicate check.run_all_checks
        and had drifted in three places (skills_dir fallback, unclustered budget
        counting, cluster-too-large threshold). Now delegating to the shared
        implementation, both must produce the same partition of issues."""
        skills_dir, library_dir, manifest_path = populated_dirs
        from scripts.lib.manifest import load_manifest
        from scripts.check import Severity, run_all_checks

        manifest = load_manifest(manifest_path)
        status_errors, status_warnings = run_checks(manifest, skills_dir, library_dir)
        check_issues = run_all_checks(manifest, skills_dir, library_dir)

        check_error_count = sum(1 for i in check_issues if i.severity is Severity.ERROR)
        check_warning_count = sum(1 for i in check_issues if i.severity is Severity.WARNING)
        assert len(status_errors) == check_error_count
        assert len(status_warnings) == check_warning_count


class TestDisplayStatus:
    def test_shows_token_savings(self, capsys):
        manifest = Manifest(
            clusters={
                "test": Cluster(
                    name="test",
                    description="Test cluster",
                    leaves={"a": LeafEntry(), "b": LeafEntry()},
                ),
            },
        )
        display_status(manifest, [], [])
        output = capsys.readouterr().out
        assert "reduction" in output

    def test_shows_errors(self, capsys):
        manifest = Manifest()
        display_status(manifest, ["dead-reference: foo"], [])
        output = capsys.readouterr().out
        assert "1 error" in output
        assert "dead-reference: foo" in output

    def test_shows_no_issues(self, capsys):
        manifest = Manifest()
        display_status(manifest, [], [])
        output = capsys.readouterr().out
        assert "No issues found" in output
