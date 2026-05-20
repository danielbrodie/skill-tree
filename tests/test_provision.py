"""Tests for the per-project provisioning script."""

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
    _portable_path,
    PROJECT_MANIFEST_REL,
    PROJECT_SKILLS_REL,
)


class TestPortablePath:
    """The manifest is meant to travel with the project's git repo, so the
    paths written into it must not bake in an absolute home dir."""

    def test_collapses_home_to_tilde(self):
        home = Path.home()
        assert _portable_path(home / ".claude" / "skills" / "tdd") == "~/.claude/skills/tdd"

    def test_bare_home_becomes_tilde(self):
        assert _portable_path(Path.home()) == "~"

    def test_non_home_path_unchanged(self):
        assert _portable_path(Path("/opt/shared/skills")) == "/opt/shared/skills"

    def test_does_not_collapse_a_homelike_prefix(self):
        # A sibling dir whose name merely starts with the home basename must
        # not be mangled.
        sibling = Path(str(Path.home()) + "-backup") / "skills"
        assert _portable_path(sibling) == str(sibling)


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

    def test_detects_python_via_scripts_and_tests_subdirs(self, tmp_path):
        # Regression: skill-tree itself is a Python project with all .py
        # files under scripts/ and tests/, no pyproject.toml at the root
        # (uv inline deps via PEP 723). Previously this produced
        # languages=[] because the scanner only walked the root directory.
        project = tmp_path / "py-repo-no-pyproject"
        (project / "scripts").mkdir(parents=True)
        (project / "tests").mkdir(parents=True)
        (project / "scripts" / "main.py").write_text("print('hi')\n")
        (project / "tests" / "test_main.py").write_text("def test_x(): pass\n")
        s = collect_project_signals(project)
        assert "python" in s["languages"], f"expected python in {s['languages']}"

    def test_detects_swift_via_app_subdir(self, tmp_path):
        # Common iOS layout: SwiftUI app code under `app/` or `src/`.
        project = tmp_path / "swift-app"
        (project / "app").mkdir(parents=True)
        (project / "app" / "ContentView.swift").write_text("// view\n")
        s = collect_project_signals(project)
        assert "swift" in s["languages"]


class TestCollectGlobalCatalog:
    def test_lists_all_skills(self, fake_skills_library, tmp_path):
        cat = collect_global_catalog(
            fake_skills_library,
            plugins_cache_dir=tmp_path / "no-plugins",
            bundled_root=tmp_path / "no-bundled",
        )
        names = {c["name"] for c in cat}
        assert names == {"tdd", "diagnose", "unused"}

    def test_extracts_description(self, fake_skills_library, tmp_path):
        cat = collect_global_catalog(
            fake_skills_library,
            plugins_cache_dir=tmp_path / "no-plugins",
            bundled_root=tmp_path / "no-bundled",
        )
        tdd = next(c for c in cat if c["name"] == "tdd")
        assert "red-green-refactor" in tdd["description"]

    def test_skips_dirs_without_skill_md(self, fake_skills_library, tmp_path):
        (fake_skills_library / "no-skill-md").mkdir()
        cat = collect_global_catalog(
            fake_skills_library,
            plugins_cache_dir=tmp_path / "no-plugins",
            bundled_root=tmp_path / "no-bundled",
        )
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

    def test_rejects_plugin_namespaced_skill_with_clear_message(
        self, fake_project, fake_skills_library, capsys
    ):
        # Regression: --list-candidates advertises plugin:skill entries via
        # collect_plugin_catalog, but --apply resolves names against the
        # personal skills_dir only. Previously, passing a plugin:skill name
        # produced a "skill not found in library" warning that looked like a
        # typo. Now it must produce a clear message explaining why plugin
        # skills can't be provisioned per-project.
        result = apply_skills(
            fake_project,
            ["tdd", "superpowers:writing-plans"],
            "test",
            fake_skills_library,
        )
        assert result["added"] == ["tdd"]
        captured = capsys.readouterr()
        # The message must call out the plugin-namespaced shape explicitly,
        # not just "skill not found".
        assert "superpowers:writing-plans" in captured.err
        assert "plugin" in captured.err.lower()

    def test_bundled_skill_name_gets_specific_rejection(
        self, fake_project, fake_skills_library, capsys
    ):
        # Regression from the 2026-05-20 dogfood: --list-candidates includes
        # Anthropic-bundled skills (origin "bundled", plain names, no colon).
        # A model picking one (e.g. `schedule`) and passing it to --apply used
        # to get a bare "skill not found in personal library" warning that
        # looked like a typo. The not-found message must now name the bundled
        # case explicitly.
        result = apply_skills(
            fake_project, ["tdd", "schedule"], "test", fake_skills_library
        )
        assert result["added"] == ["tdd"]
        captured = capsys.readouterr()
        assert "schedule" in captured.err
        assert "bundled" in captured.err.lower()

    def test_symlinked_project_skill_is_replaced_not_crashed(
        self, fake_project, fake_skills_library
    ):
        # Regression from the 2026-05-20 dogfood: vercel-labs/skills installs
        # project skills as symlinks. apply_skills did `shutil.rmtree(dst)`
        # which raises OSError on a symlink. A pre-existing symlink at the
        # target path must be unlinked (not followed) and replaced with the
        # copied skill.
        project_skills = fake_project / PROJECT_SKILLS_REL
        project_skills.mkdir(parents=True, exist_ok=True)
        # Stand up a symlink where `tdd` will be provisioned.
        external = fake_project.parent / "external-tdd"
        external.mkdir(parents=True, exist_ok=True)
        (external / "SKILL.md").write_text("---\nname: tdd\n---\nexternal\n")
        (project_skills / "tdd").symlink_to(external)

        result = apply_skills(fake_project, ["tdd"], "test", fake_skills_library)
        assert result["added"] == ["tdd"]
        # The target is now a real directory, not a symlink.
        assert not (project_skills / "tdd").is_symlink()
        assert (project_skills / "tdd" / "SKILL.md").exists()
        # The external symlink target must be untouched.
        assert (external / "SKILL.md").read_text() == "---\nname: tdd\n---\nexternal\n"

    def test_warns_when_merging_into_hand_curated_skills_dir(
        self, fake_project, fake_skills_library, capsys
    ):
        # Regression from the 2026-05-20 dogfood: provisioning into a project
        # whose .claude/skills/ was hand-curated (non-empty, no .skilltree.json)
        # silently merged skill-tree's picks alongside the user's own skills.
        # apply_skills must warn so the user knows the dir is now mixed.
        project_skills = fake_project / PROJECT_SKILLS_REL
        project_skills.mkdir(parents=True, exist_ok=True)
        (project_skills / "hand-curated-a").mkdir()
        (project_skills / "hand-curated-b").mkdir()

        apply_skills(fake_project, ["tdd"], "test", fake_skills_library)
        captured = capsys.readouterr()
        assert "not managed by skill-tree" in captured.err
        assert "hand-curated-a" in captured.err

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


class TestGlobalSuggest:
    """The --global-suggest CLI mode is the / ADR 0002 entry point.

    Behavior tested via subprocess so the argparse dispatch is also exercised.
    """

    def test_prints_top_n_table_when_corpus_has_data(self, tmp_path, monkeypatch):
        # Build a fake projects root with one session containing 3 Skill invocations
        projects = tmp_path / ".claude" / "projects" / "-Users-fake-proj"
        projects.mkdir(parents=True)
        from datetime import datetime, timezone, timedelta

        recent = (datetime.now(tz=timezone.utc) - timedelta(days=1)).isoformat()
        events = [
            {
                "uuid": "u1", "parentUuid": None, "timestamp": recent,
                "message": {"role": "user", "content": "do thing"},
            },
            {
                "uuid": "u2", "parentUuid": "u1", "timestamp": recent,
                "message": {
                    "role": "assistant",
                    "content": [{
                        "type": "tool_use", "name": "Skill",
                        "input": {"skill": "alpha"},
                    }],
                },
            },
            {
                "uuid": "u3", "parentUuid": "u2", "timestamp": recent,
                "message": {
                    "role": "assistant",
                    "content": [{
                        "type": "tool_use", "name": "Skill",
                        "input": {"skill": "alpha"},
                    }],
                },
            },
            {
                "uuid": "u4", "parentUuid": "u3", "timestamp": recent,
                "message": {
                    "role": "assistant",
                    "content": [{
                        "type": "tool_use", "name": "Skill",
                        "input": {"skill": "beta"},
                    }],
                },
            },
        ]
        (projects / "session.jsonl").write_text(
            "\n".join(json.dumps(e) for e in events) + "\n"
        )

        # Empty skills lib so neither alpha nor beta will be "in catalog"
        skills_lib = tmp_path / "skills"
        skills_lib.mkdir()

        monkeypatch.setenv("HOME", str(tmp_path))

        import subprocess
        result = subprocess.run(
            [
                "python3",
                str(Path(__file__).resolve().parent.parent / "scripts" / "provision.py"),
                "--global-suggest",
                "--top-n",
                "5",
                "--days",
                "30",
                "--skills-library",
                str(skills_lib),
            ],
            capture_output=True, text=True, env={**__import__("os").environ, "HOME": str(tmp_path)},
        )
        assert result.returncode == 0, result.stderr
        assert "alpha" in result.stdout
        assert "beta" in result.stdout
        # alpha got 2 invocations, beta got 1, so alpha should rank #1
        alpha_idx = result.stdout.index("alpha")
        beta_idx = result.stdout.index("beta")
        assert alpha_idx < beta_idx

    def test_handles_empty_corpus(self, tmp_path):
        projects = tmp_path / ".claude" / "projects"
        projects.mkdir(parents=True)
        skills_lib = tmp_path / "skills"
        skills_lib.mkdir()

        import subprocess
        result = subprocess.run(
            [
                "python3",
                str(Path(__file__).resolve().parent.parent / "scripts" / "provision.py"),
                "--global-suggest",
                "--top-n",
                "5",
                "--skills-library",
                str(skills_lib),
            ],
            capture_output=True, text=True,
            env={**__import__("os").environ, "HOME": str(tmp_path)},
        )
        assert result.returncode == 1
        # Message is "(no Skill invocations in last N days)" — match case-insensitively
        combined = (result.stdout + result.stderr).lower()
        assert "no skill invocations" in combined


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
