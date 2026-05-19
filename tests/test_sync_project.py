"""Tests for the project-manifest sync command."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from provision import apply_skills, load_project_manifest  # noqa: E402
from sync_project import DriftState, detect_drift, apply_sync  # noqa: E402


@pytest.fixture
def library(tmp_path):
    lib = tmp_path / "library"
    lib.mkdir()
    for name in ["alpha", "beta", "gamma"]:
        sd = lib / name
        sd.mkdir()
        (sd / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: d\n---\nv1 body\n"
        )
    return lib


@pytest.fixture
def project(tmp_path, library):
    """A project with alpha+beta provisioned."""
    p = tmp_path / "proj"
    p.mkdir()
    (p / ".git").mkdir()
    apply_skills(p, ["alpha", "beta"], "init", library)
    return p


def _state_for(drift, name):
    return next((d.state for d in drift if d.skill == name), None)


class TestDetectDrift:
    def test_clean_when_nothing_changed(self, project, library):
        drift = detect_drift(project, library)
        assert _state_for(drift, "alpha") is DriftState.CLEAN
        assert _state_for(drift, "beta") is DriftState.CLEAN

    def test_stale_when_source_updates(self, project, library):
        (library / "alpha" / "SKILL.md").write_text(
            "---\nname: alpha\ndescription: d\n---\nv2 body\n"
        )
        drift = detect_drift(project, library)
        assert _state_for(drift, "alpha") is DriftState.STALE
        assert _state_for(drift, "beta") is DriftState.CLEAN

    def test_local_edit_when_project_copy_changes(self, project, library):
        (project / ".claude" / "skills" / "beta" / "SKILL.md").write_text(
            "---\nname: beta\ndescription: d\n---\nlocally edited\n"
        )
        drift = detect_drift(project, library)
        assert _state_for(drift, "beta") is DriftState.LOCAL_EDIT
        assert _state_for(drift, "alpha") is DriftState.CLEAN

    def test_orphan_when_source_disappears(self, project, library):
        import shutil
        shutil.rmtree(library / "alpha")
        drift = detect_drift(project, library)
        assert _state_for(drift, "alpha") is DriftState.ORPHAN

    def test_missing_project_copy(self, project, library):
        import shutil
        shutil.rmtree(project / ".claude" / "skills" / "alpha")
        drift = detect_drift(project, library)
        assert _state_for(drift, "alpha") is DriftState.MISSING_PROJECT_COPY

    def test_orphan_when_source_dir_exists_but_skill_md_missing(self, project, library):
        # Regression: previously the missing-SKILL.md case classified as STALE,
        # which apply_sync then handled by deleting the valid project copy and
        # replacing it with the empty source dir — data loss.
        (library / "alpha" / "SKILL.md").unlink()
        drift = detect_drift(project, library)
        assert _state_for(drift, "alpha") is DriftState.ORPHAN

    def test_apply_sync_preserves_project_copy_when_source_skill_md_missing(self, project, library):
        # Same regression as above, exercised through apply_sync without --prune.
        (library / "alpha" / "SKILL.md").unlink()
        original = (project / ".claude" / "skills" / "alpha" / "SKILL.md").read_text()
        result = apply_sync(project, library)  # no prune
        # Project copy must still be intact and unmodified.
        still_there = (project / ".claude" / "skills" / "alpha" / "SKILL.md").read_text()
        assert still_there == original
        assert "alpha" not in result["re-copied"]
        assert "alpha" not in result["pruned"]


class TestApplySync:
    def test_re_copies_stale(self, project, library):
        (library / "alpha" / "SKILL.md").write_text(
            "---\nname: alpha\ndescription: d\n---\nv2 body\n"
        )
        result = apply_sync(project, library)
        assert "alpha" in result["re-copied"]
        # Project copy should now have v2
        proj_md = (project / ".claude" / "skills" / "alpha" / "SKILL.md").read_text()
        assert "v2 body" in proj_md

    def test_preserves_local_edit_by_default(self, project, library):
        (project / ".claude" / "skills" / "beta" / "SKILL.md").write_text(
            "---\nname: beta\ndescription: d\n---\nlocally edited\n"
        )
        result = apply_sync(project, library)
        assert "beta" in result["skipped-local-edit"]
        # Local copy preserved
        proj_md = (project / ".claude" / "skills" / "beta" / "SKILL.md").read_text()
        assert "locally edited" in proj_md

    def test_overwrites_local_edit_with_flag(self, project, library):
        (project / ".claude" / "skills" / "beta" / "SKILL.md").write_text(
            "---\nname: beta\ndescription: d\n---\nlocally edited\n"
        )
        result = apply_sync(project, library, overwrite_local=True)
        assert "beta" in result["re-copied"]
        proj_md = (project / ".claude" / "skills" / "beta" / "SKILL.md").read_text()
        assert "locally edited" not in proj_md
        assert "v1 body" in proj_md

    def test_prune_removes_orphans(self, project, library):
        import shutil
        shutil.rmtree(library / "alpha")
        result = apply_sync(project, library, prune=True)
        assert "alpha" in result["pruned"]
        assert not (project / ".claude" / "skills" / "alpha").exists()
        manifest = load_project_manifest(project)
        assert "alpha" not in manifest["skills"]

    def test_prune_off_by_default(self, project, library):
        import shutil
        shutil.rmtree(library / "alpha")
        result = apply_sync(project, library, prune=False)
        assert result["pruned"] == []
        # Project copy still there
        assert (project / ".claude" / "skills" / "alpha").exists()

    def test_restores_missing_project_copy(self, project, library):
        import shutil
        shutil.rmtree(project / ".claude" / "skills" / "alpha")
        result = apply_sync(project, library)
        assert "alpha" in result["restored-missing"]
        assert (project / ".claude" / "skills" / "alpha" / "SKILL.md").exists()

    def test_updates_synced_at_and_audit_log(self, project, library):
        (library / "alpha" / "SKILL.md").write_text(
            "---\nname: alpha\ndescription: d\n---\nv2\n"
        )
        apply_sync(project, library)
        manifest = load_project_manifest(project)
        audit_actions = [e["action"] for e in manifest["auditLog"]]
        assert "synced" in audit_actions

    def test_records_new_source_hash_after_sync(self, project, library):
        old_manifest = load_project_manifest(project)
        old_hash = old_manifest["skills"]["alpha"]["sourceHash"]
        (library / "alpha" / "SKILL.md").write_text(
            "---\nname: alpha\ndescription: d\n---\nv2 body\n"
        )
        apply_sync(project, library)
        new_manifest = load_project_manifest(project)
        new_hash = new_manifest["skills"]["alpha"]["sourceHash"]
        assert new_hash != old_hash
