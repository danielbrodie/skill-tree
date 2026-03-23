"""Tests for the add command — URL parsing and cluster matching."""

from __future__ import annotations

import pytest

from scripts.add import parse_github_url


class TestParseGithubUrl:
    def test_tree_url(self):
        org, repo, skill, ref = parse_github_url(
            "https://github.com/anthropics/skills/tree/main/skills/hugging-face-paper-pages"
        )
        assert org == "anthropics"
        assert repo == "skills"
        assert skill == "hugging-face-paper-pages"
        assert ref == "main"

    def test_blob_url(self):
        org, repo, skill, ref = parse_github_url(
            "https://github.com/huggingface/skills/blob/main/skills/paper-search/SKILL.md"
        )
        assert org == "huggingface"
        assert repo == "skills"
        assert skill == "paper-search"
        assert ref == "main"

    def test_repo_root(self):
        org, repo, skill, ref = parse_github_url(
            "https://github.com/anthropics/skills"
        )
        assert org == "anthropics"
        assert repo == "skills"
        assert skill == ""
        assert ref is None

    def test_repo_root_with_git(self):
        org, repo, skill, ref = parse_github_url(
            "https://github.com/anthropics/skills.git"
        )
        assert org == "anthropics"
        assert repo == "skills"
        assert skill == ""

    def test_shorthand(self):
        org, repo, skill, ref = parse_github_url(
            "anthropics/skills/hugging-face-paper-pages"
        )
        assert org == "anthropics"
        assert repo == "skills"
        assert skill == "hugging-face-paper-pages"
        assert ref is None

    def test_non_main_branch(self):
        org, repo, skill, ref = parse_github_url(
            "https://github.com/org/repo/tree/develop/skills/my-skill"
        )
        assert ref == "develop"
        assert skill == "my-skill"

    def test_trailing_slash(self):
        org, repo, skill, ref = parse_github_url(
            "https://github.com/org/repo/tree/main/skills/my-skill/"
        )
        assert skill == "my-skill"

    def test_invalid_url(self):
        with pytest.raises(ValueError):
            parse_github_url("not-a-url")

    def test_non_github_url(self):
        with pytest.raises(ValueError):
            parse_github_url("https://gitlab.com/org/repo")
