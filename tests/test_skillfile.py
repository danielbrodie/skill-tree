"""Tests for SKILL.md frontmatter parsing and writing."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.lib.skillfile import (
    get_description,
    get_name,
    has_always_true,
    is_disabled,
    parse_frontmatter,
    scan_skills_dir,
    set_disable_model_invocation,
    set_field,
)


class TestParseFrontmatter:
    def test_basic(self, tmp_path: Path):
        p = tmp_path / "SKILL.md"
        p.write_text("---\nname: test-skill\ndescription: A test skill\n---\n# Body\n")

        fm = parse_frontmatter(p)
        assert fm.has_frontmatter
        assert fm.fields["name"] == "test-skill"
        assert fm.fields["description"] == "A test skill"

    def test_quoted_description(self, tmp_path: Path):
        p = tmp_path / "SKILL.md"
        p.write_text('---\nname: test\ndescription: "A quoted desc"\n---\n')

        fm = parse_frontmatter(p)
        assert fm.fields["description"] == "A quoted desc"

    def test_single_quoted(self, tmp_path: Path):
        p = tmp_path / "SKILL.md"
        p.write_text("---\nname: test\ndescription: 'Single quoted'\n---\n")

        fm = parse_frontmatter(p)
        assert fm.fields["description"] == "Single quoted"

    def test_folded_scalar(self, tmp_path: Path):
        p = tmp_path / "SKILL.md"
        p.write_text("---\nname: test\ndescription: >\n  Line one\n  Line two\n---\n")

        fm = parse_frontmatter(p)
        assert fm.fields["description"] == "Line one Line two"

    def test_literal_scalar(self, tmp_path: Path):
        p = tmp_path / "SKILL.md"
        p.write_text("---\nname: test\ndescription: |\n  Line one\n  Line two\n---\n")

        fm = parse_frontmatter(p)
        assert "Line one\nLine two" == fm.fields["description"]

    def test_no_frontmatter(self, tmp_path: Path):
        p = tmp_path / "SKILL.md"
        p.write_text("# Just a heading\nNo frontmatter here.\n")

        fm = parse_frontmatter(p)
        assert not fm.has_frontmatter

    def test_missing_file(self, tmp_path: Path):
        p = tmp_path / "nonexistent.md"
        fm = parse_frontmatter(p)
        assert not fm.has_frontmatter

    def test_disable_model_invocation(self, tmp_path: Path):
        p = tmp_path / "SKILL.md"
        p.write_text("---\nname: test\ndisable-model-invocation: true\n---\n")

        fm = parse_frontmatter(p)
        assert is_disabled(fm)

    def test_not_disabled(self, tmp_path: Path):
        p = tmp_path / "SKILL.md"
        p.write_text("---\nname: test\n---\n")

        fm = parse_frontmatter(p)
        assert not is_disabled(fm)

    def test_always_true(self, tmp_path: Path):
        p = tmp_path / "SKILL.md"
        p.write_text("---\nname: test\nalways: true\n---\n")

        fm = parse_frontmatter(p)
        assert has_always_true(fm)

    def test_comments_skipped(self, tmp_path: Path):
        p = tmp_path / "SKILL.md"
        p.write_text("---\n# comment\nname: test\n---\n")

        fm = parse_frontmatter(p)
        assert fm.fields["name"] == "test"


class TestSetField:
    def test_update_existing(self, tmp_path: Path):
        p = tmp_path / "SKILL.md"
        p.write_text("---\nname: test\nversion: 1.0.0\n---\n# Body\n")

        fm = parse_frontmatter(p)
        new_lines = set_field(fm, "version", "2.0.0")
        content = "\n".join(new_lines)
        assert "version: 2.0.0" in content

    def test_add_new_field(self, tmp_path: Path):
        p = tmp_path / "SKILL.md"
        p.write_text("---\nname: test\n---\n# Body\n")

        fm = parse_frontmatter(p)
        new_lines = set_field(fm, "disable-model-invocation", "true")
        content = "\n".join(new_lines)
        assert "disable-model-invocation: true" in content

    def test_add_frontmatter_to_bare_file(self, tmp_path: Path):
        p = tmp_path / "SKILL.md"
        p.write_text("# Just content\n")

        fm = parse_frontmatter(p)
        new_lines = set_field(fm, "name", "test")
        content = "\n".join(new_lines)
        assert content.startswith("---\nname: test\n---")


class TestSetDisableModelInvocation:
    def test_set_on_file(self, tmp_path: Path):
        p = tmp_path / "SKILL.md"
        p.write_text("---\nname: test\n---\n# Body\n")

        set_disable_model_invocation(p, True)

        fm = parse_frontmatter(p)
        assert is_disabled(fm)

    def test_idempotent(self, tmp_path: Path):
        p = tmp_path / "SKILL.md"
        p.write_text("---\nname: test\ndisable-model-invocation: true\n---\n# Body\n")

        set_disable_model_invocation(p, True)

        content = p.read_text()
        assert content.count("disable-model-invocation") == 1


class TestScanSkillsDir:
    def test_finds_skills(self, tmp_path: Path):
        (tmp_path / "skill-a").mkdir()
        (tmp_path / "skill-a" / "SKILL.md").write_text("---\nname: skill-a\n---\n")
        (tmp_path / "skill-b").mkdir()
        (tmp_path / "skill-b" / "SKILL.md").write_text("---\nname: skill-b\n---\n")
        (tmp_path / "not-a-skill").mkdir()  # no SKILL.md

        result = scan_skills_dir(tmp_path)
        assert set(result.keys()) == {"skill-a", "skill-b"}

    def test_empty_dir(self, tmp_path: Path):
        result = scan_skills_dir(tmp_path)
        assert len(result) == 0

    def test_nonexistent_dir(self, tmp_path: Path):
        result = scan_skills_dir(tmp_path / "nope")
        assert len(result) == 0
