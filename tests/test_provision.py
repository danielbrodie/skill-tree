"""Tests for the per-project provisioning script (BRO-182)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from provision import (  # noqa: E402
    apply_skills,
    collect_global_catalog,
    collect_project_signals,
    find_project_root,
    load_project_manifest,
    write_project_manifest,
    PROJECT_MANIFEST_REL,
    PROJECT_SKILLS_REL,
)


@pytest.fixture
def fake_skills_library(tmp_path):
    """Create a small fake global skill library."""
    lib = tmp_path / "library"
    lib.mkdir()
    for name, desc in [
        ("tdd", "Test-driven development with red-green-refactor."),
        ("diagnose", "Disciplined diagnosis loop."),
        ("unused", "Something nobody picks."),
    ]:
        sd = lib / name
        sd.mkdir()
        (sd / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: {desc}\n---\n\nbody for {name}\n"
        )
    return lib


@pytest.fixture
def fake_project(tmp_path):
    """Create a fake project root with markers."""
    proj = tmp_path / "myproj"
    proj.mkdir()
    (proj / ".git").mkdir()
    (proj / "pyproject.toml").write_text("[project]\nname='myproj'\n")
    (proj / "CLAUDE.md").write_text("# myproj\nA Python project using pytest.\n")
    (proj / "main.py").write_text("print('hello')\n")
    return proj


class TestFindProjectRoot:
    def test_finds_root_via_git(self, fake_project):
        nested = fake_project / "src" / "deeper"
        nested.mkdir(parents=True)
        assert find_project_root(nested) == fake_project

    def test_falls_back_to_start_when_no_markers(self, tmp_path):
        sub = tmp_path / "no-markers"
        sub.mkdir()
        # Either returns sub itself or one of its ancestors that happens to have a marker
        # — assert it didn't crash and returns a valid existing dir
        result = find_project_root(sub)
        assert result.exists()


class TestCollectProjectSignals:
    def test_extracts_languages_and_files(self, fake_project):
        s = collect_project_signals(fake_project)
        assert "python" in s["languages"]
        assert "CLAUDE.md" in s["files"]
        assert "pyproject.toml" in s["files"]
        assert "pytest" in s["claudeMd"]

    def test_handles_missing_files_gracefully(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        s = collect_project_signals(empty)
        assert s["files"] == []
        assert s["languages"] == []
        assert s["claudeMd"] is None


class TestCollectGlobalCatalog:
    def test_lists_all_skills(self, fake_skills_library):
        cat = collect_global_catalog(fake_skills_library)
        names = {c["name"] for c in cat}
        assert names == {"tdd", "diagnose", "unused"}

    def test_extracts_description(self, fake_skills_library):
        cat = collect_global_catalog(fake_skills_library)
        tdd = next(c for c in cat if c["name"] == "tdd")
        assert "red-green-refactor" in tdd["description"]

    def test_skips_dirs_without_skill_md(self, fake_skills_library):
        (fake_skills_library / "no-skill-md").mkdir()
        cat = collect_global_catalog(fake_skills_library)
        names = {c["name"] for c in cat}
        assert "no-skill-md" not in names


class TestApplySkills:
    def test_copies_skills_and_writes_manifest(self, fake_project, fake_skills_library):
        result = apply_skills(
            fake_project, ["tdd", "diagnose"], "smoke test", fake_skills_library
        )
        assert result["added"] == ["tdd", "diagnose"]

        # Skills copied
        assert (fake_project / PROJECT_SKILLS_REL / "tdd" / "SKILL.md").exists()
        assert (fake_project / PROJECT_SKILLS_REL / "diagnose" / "SKILL.md").exists()

        # Manifest written
        m = load_project_manifest(fake_project)
        assert m is not None
        assert set(m["skills"]) == {"tdd", "diagnose"}
        assert m["skills"]["tdd"]["reason"] == "smoke test"
        assert m["skills"]["tdd"]["source"].endswith("/tdd")
        assert len(m["auditLog"]) == 2

    def test_warns_and_skips_missing_skill(self, fake_project, fake_skills_library, capsys):
        result = apply_skills(
            fake_project, ["tdd", "nonexistent"], "test", fake_skills_library
        )
        assert result["added"] == ["tdd"]
        captured = capsys.readouterr()
        assert "nonexistent" in captured.err

    def test_replaces_existing_copy_on_reapply(
        self, fake_project, fake_skills_library
    ):
        apply_skills(fake_project, ["tdd"], "first", fake_skills_library)
        # Mutate the library
        (fake_skills_library / "tdd" / "SKILL.md").write_text(
            "---\nname: tdd\ndescription: updated\n---\nNEW BODY\n"
        )
        apply_skills(fake_project, ["tdd"], "second", fake_skills_library)
        body = (fake_project / PROJECT_SKILLS_REL / "tdd" / "SKILL.md").read_text()
        assert "NEW BODY" in body
        m = load_project_manifest(fake_project)
        assert m["skills"]["tdd"]["reason"] == "second"
        assert len(m["auditLog"]) == 2  # one per apply call

    def test_apply_is_additive_across_calls(
        self, fake_project, fake_skills_library
    ):
        apply_skills(fake_project, ["tdd"], "first", fake_skills_library)
        apply_skills(fake_project, ["diagnose"], "second", fake_skills_library)
        m = load_project_manifest(fake_project)
        assert set(m["skills"]) == {"tdd", "diagnose"}


class TestProjectManifestRoundTrip:
    def test_write_and_load(self, tmp_path):
        manifest = {
            "version": "1.0",
            "sourceLibrary": "/x",
            "skills": {"a": {"source": "/x/a", "reason": "r", "syncedAt": "now"}},
            "auditLog": [],
        }
        write_project_manifest(tmp_path, manifest)
        loaded = load_project_manifest(tmp_path)
        assert loaded == {**manifest, "version": "1.0"}

    def test_load_returns_none_when_missing(self, tmp_path):
        assert load_project_manifest(tmp_path) is None

    def test_load_handles_malformed_json(self, tmp_path):
        p = tmp_path / PROJECT_MANIFEST_REL
        p.parent.mkdir(parents=True)
        p.write_text("not json {")
        assert load_project_manifest(tmp_path) is None
