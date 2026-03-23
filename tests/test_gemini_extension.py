"""Tests for Gemini CLI extension structure validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestGeminiExtensionJson:
    def test_exists(self):
        assert (REPO_ROOT / "gemini-extension.json").exists()

    def test_valid_json(self):
        data = json.loads((REPO_ROOT / "gemini-extension.json").read_text())
        assert isinstance(data, dict)

    def test_required_fields(self):
        data = json.loads((REPO_ROOT / "gemini-extension.json").read_text())
        assert "name" in data
        assert "version" in data
        assert data["name"] == "skill-tree"

    def test_context_file_exists(self):
        data = json.loads((REPO_ROOT / "gemini-extension.json").read_text())
        context_file = data.get("contextFileName", "GEMINI.md")
        assert (REPO_ROOT / context_file).exists()


class TestGeminiCommands:
    """Verify TOML command files exist alongside Claude Code .md commands."""

    EXPECTED_COMMANDS = ["check", "setup", "fetch"]

    def test_toml_files_exist(self):
        commands_dir = REPO_ROOT / "commands"
        for cmd in self.EXPECTED_COMMANDS:
            toml_path = commands_dir / f"{cmd}.toml"
            assert toml_path.exists(), f"Missing {cmd}.toml"

    def test_toml_files_have_prompt(self):
        """Each TOML must have a prompt field (Gemini requirement)."""
        commands_dir = REPO_ROOT / "commands"
        for cmd in self.EXPECTED_COMMANDS:
            content = (commands_dir / f"{cmd}.toml").read_text()
            assert "prompt" in content, f"{cmd}.toml missing prompt field"

    def test_toml_files_have_description(self):
        commands_dir = REPO_ROOT / "commands"
        for cmd in self.EXPECTED_COMMANDS:
            content = (commands_dir / f"{cmd}.toml").read_text()
            assert "description" in content, f"{cmd}.toml missing description"

    def test_claude_skills_exist(self):
        """Each command should have a corresponding Claude Code skill."""
        skills_dir = REPO_ROOT / "skills"
        for cmd in self.EXPECTED_COMMANDS:
            skill_path = skills_dir / cmd / "SKILL.md"
            assert skill_path.exists(), f"Missing skills/{cmd}/SKILL.md"


class TestGeminiContextFile:
    def test_mentions_gemini_skills_dir(self):
        content = (REPO_ROOT / "GEMINI.md").read_text()
        assert "~/.gemini/skills" in content

    def test_mentions_available_commands(self):
        content = (REPO_ROOT / "GEMINI.md").read_text()
        assert "/check" in content
        assert "/setup" in content
        assert "/fetch" in content
