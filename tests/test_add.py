"""Tests for the add command — URL parsing and cluster matching."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.add import main, parse_github_url


class TestParseGithubUrl:
    def test_tree_url(self):
        org, repo, skill, ref, path = parse_github_url(
            "https://github.com/anthropics/skills/tree/main/skills/hugging-face-paper-pages"
        )
        assert org == "anthropics"
        assert repo == "skills"
        assert skill == "hugging-face-paper-pages"
        assert ref == "main"
        assert path == "skills/hugging-face-paper-pages"

    def test_blob_url(self):
        org, repo, skill, ref, path = parse_github_url(
            "https://github.com/huggingface/skills/blob/main/skills/paper-search/SKILL.md"
        )
        assert org == "huggingface"
        assert repo == "skills"
        assert skill == "paper-search"
        assert ref == "main"
        assert path == "skills/paper-search"

    def test_repo_root(self):
        org, repo, skill, ref, path = parse_github_url(
            "https://github.com/anthropics/skills"
        )
        assert org == "anthropics"
        assert repo == "skills"
        assert skill == ""
        assert ref is None
        assert path == ""

    def test_repo_root_with_git(self):
        org, repo, skill, ref, path = parse_github_url(
            "https://github.com/anthropics/skills.git"
        )
        assert org == "anthropics"
        assert repo == "skills"
        assert skill == ""

    def test_shorthand(self):
        org, repo, skill, ref, path = parse_github_url(
            "anthropics/skills/hugging-face-paper-pages"
        )
        assert org == "anthropics"
        assert repo == "skills"
        assert skill == "hugging-face-paper-pages"
        assert ref is None
        assert path == "skills/hugging-face-paper-pages"

    def test_non_main_branch(self):
        org, repo, skill, ref, path = parse_github_url(
            "https://github.com/org/repo/tree/develop/skills/my-skill"
        )
        assert ref == "develop"
        assert skill == "my-skill"

    def test_trailing_slash(self):
        org, repo, skill, ref, path = parse_github_url(
            "https://github.com/org/repo/tree/main/skills/my-skill/"
        )
        assert skill == "my-skill"

    def test_invalid_url(self):
        with pytest.raises(ValueError):
            parse_github_url("not-a-url")

    def test_non_github_url(self):
        with pytest.raises(ValueError):
            parse_github_url("https://gitlab.com/org/repo")

    def test_nested_skills_layout_mattpocock_style(self):
        # Regression: parser used to split on / and take [0], so
        # 'skills/engineering/zoom-out' became 'engineering' (a category)
        # and fetch_skill_content built a 404-ing URL.
        org, repo, skill, ref, path = parse_github_url(
            "https://github.com/mattpocock/skills/tree/main/skills/engineering/zoom-out"
        )
        assert org == "mattpocock"
        assert repo == "skills"
        assert skill == "zoom-out"
        assert path == "skills/engineering/zoom-out"

    def test_plugin_nested_layout_anthropic_official_marketplace(self):
        # Regression: anthropics/claude-plugins-official uses
        # plugins/<plugin>/skills/<skill>, which the old parser also botched.
        org, repo, skill, ref, path = parse_github_url(
            "https://github.com/anthropics/claude-plugins-official/tree/main/plugins/superpowers/skills/tdd"
        )
        assert org == "anthropics"
        assert repo == "claude-plugins-official"
        assert skill == "tdd"
        assert path == "plugins/superpowers/skills/tdd"


class TestFetchSkillContentRef:
    """Regression: when gh is on PATH, the contents API call previously did
    not pass `?ref=<ref>`, so requesting `ref='develop'` silently fetched the
    default branch — wrong content with the correct ref's commit SHA pinned."""

    def test_gh_path_passes_ref_to_contents_api(self, monkeypatch):
        from scripts import add

        calls = []

        class FakeCompleted:
            def __init__(self, returncode, stdout):
                self.returncode = returncode
                self.stdout = stdout

        def fake_run(cmd, **kw):
            calls.append(cmd)
            if "contents/" in cmd[2]:
                return FakeCompleted(0, "SKILL.md body bytes\n")
            if "commits/" in cmd[2]:
                return FakeCompleted(0, "deadbeefcafebabe\n")
            return FakeCompleted(1, "")

        monkeypatch.setattr(add.subprocess, "run", fake_run)
        content, sha = add.fetch_skill_content("org", "repo", "my-skill", "develop")
        assert content.startswith("SKILL.md body")
        assert sha == "deadbeefcafebabe"
        # The contents API request MUST carry ?ref=develop.
        contents_call = next(c for c in calls if "contents/" in c[2])
        assert "?ref=develop" in contents_call[2]
        # And the commits-API call must use the same ref so source-pin matches.
        commits_call = next(c for c in calls if "commits/" in c[2])
        assert commits_call[2].endswith("/commits/develop")


class TestAddManifestUpdate:
    """Regression: the success path with an existing manifest used to raise
    NameError because best_cluster was referenced but never assigned, leaving
    a partially-added skill (SKILL.md written, manifest not updated)."""

    def test_success_path_with_existing_manifest_adds_to_standalones(self, tmp_path, monkeypatch, capsys):
        library_dir = tmp_path / "library"
        library_dir.mkdir()
        manifest_path = library_dir / "skill-tree" / "manifest.json"
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text(json.dumps({
            "version": "1.0",
            "unclusteredBudget": 25,
            "clusters": {},
            "standalones": [],
            "hotPath": [],
            "referenceNodes": [],
            "deprecated": [],
        }))

        skill_md_content = "---\nname: my-skill\ndescription: A test skill.\n---\n\nBody.\n"

        monkeypatch.setattr(
            "scripts.add.fetch_skill_content",
            lambda org, repo, skill, ref, path_in_repo: (skill_md_content, "abc123def456"),
        )
        monkeypatch.setattr("builtins.input", lambda *a, **kw: "y")
        monkeypatch.setattr(sys, "argv", [
            "skill-tree",
            "anthropics/skills/my-skill",
            "--library-dir", str(library_dir),
        ])

        # Used to raise NameError before this regression test was added.
        main()

        manifest = json.loads(manifest_path.read_text())
        assert "my-skill" in manifest["standalones"]
        assert (library_dir / "my-skill" / "SKILL.md").exists()
        assert manifest["_sources"]["my-skill"]["sourceCommit"] == "abc123def456"
