"""Tests for Codex CLI compatibility (agents/openai.yaml generation)."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.lib.codex import generate_openai_yaml, write_openai_yaml


class TestGenerateOpenaiYaml:
    def test_basic_output(self):
        content = generate_openai_yaml(
            display_name="Research Tools",
            short_description="Multi-provider fan-out research",
        )
        assert 'display_name: "Research Tools"' in content
        assert 'short_description: "Multi-provider fan-out research"' in content
        assert "allow_implicit_invocation: false" in content

    def test_allow_implicit(self):
        content = generate_openai_yaml(
            display_name="Test",
            short_description="A short description for testing",
            allow_implicit_invocation=True,
        )
        assert "allow_implicit_invocation: true" in content

    def test_truncates_long_description(self):
        long_desc = "x" * 100
        content = generate_openai_yaml(
            display_name="Test",
            short_description=long_desc,
        )
        # Should contain exactly 64 x's, not 100
        assert ("x" * 64) in content
        assert ("x" * 65) not in content

    def test_escapes_quotes_in_display_name(self):
        content = generate_openai_yaml(
            display_name='Has "quotes"',
            short_description="A short description for testing",
        )
        assert 'Has \\"quotes\\"' in content

    def test_escapes_quotes_in_description(self):
        content = generate_openai_yaml(
            display_name="Test",
            short_description='Desc with "quotes" inside it',
        )
        assert 'Desc with \\"quotes\\" inside it' in content


class TestWriteOpenaiYaml:
    def test_creates_agents_dir_and_file(self, tmp_path: Path):
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()

        result = write_openai_yaml(
            skill_dir,
            display_name="My Skill",
            short_description="Does something useful for you",
        )

        assert result == skill_dir / "agents" / "openai.yaml"
        assert result.exists()
        content = result.read_text()
        assert 'display_name: "My Skill"' in content

    def test_overwrites_existing(self, tmp_path: Path):
        skill_dir = tmp_path / "my-skill"
        agents_dir = skill_dir / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "openai.yaml").write_text("old content")

        write_openai_yaml(
            skill_dir,
            display_name="New Name",
            short_description="New description for the skill",
        )

        content = (agents_dir / "openai.yaml").read_text()
        assert "New Name" in content
        assert "old content" not in content

    def test_implicit_false_by_default(self, tmp_path: Path):
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()

        write_openai_yaml(
            skill_dir,
            display_name="Test",
            short_description="Testing default invocation policy",
        )

        content = (skill_dir / "agents" / "openai.yaml").read_text()
        assert "allow_implicit_invocation: false" in content
