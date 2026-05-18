"""Tests for the unused-skill archiver (BRO-188)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from archive import (  # noqa: E402
    archive_skills,
    find_latest_archive,
    last_invocation_by_skill,
    list_unused_personal_skills,
    unarchive,
)
from measure import CorpusRecord  # noqa: E402


def _make_skill(skills_dir: Path, name: str) -> None:
    sd = skills_dir / name
    sd.mkdir(parents=True, exist_ok=True)
    (sd / "SKILL.md").write_text(f"---\nname: {name}\ndescription: x\n---\nbody\n")


def _rec(skill: str, ts: str) -> CorpusRecord:
    return CorpusRecord(
        session_id="s", timestamp=ts, project_dir="/p", user_prompt="", skill=skill
    )


class TestLastInvocationBySkill:
    def test_picks_most_recent(self):
        records = [
            _rec("tdd", "2026-05-01T00:00:00+00:00"),
            _rec("tdd", "2026-05-10T00:00:00+00:00"),
            _rec("tdd", "2026-05-05T00:00:00+00:00"),
            _rec("diagnose", "2026-05-08T00:00:00+00:00"),
        ]
        out = last_invocation_by_skill(records)
        assert out == {
            "tdd": "2026-05-10T00:00:00+00:00",
            "diagnose": "2026-05-08T00:00:00+00:00",
        }

    def test_empty_corpus(self):
        assert last_invocation_by_skill([]) == {}


class TestListUnused:
    def test_returns_skills_with_no_recent_use(self, tmp_path):
        skills = tmp_path / "skills"
        skills.mkdir()
        for name in ["used-recently", "unused", "used-long-ago"]:
            _make_skill(skills, name)

        now = datetime.now(tz=timezone.utc)
        last_used = {
            "used-recently": (now - timedelta(days=5)).isoformat(),
            "used-long-ago": (now - timedelta(days=120)).isoformat(),
        }
        candidates = list_unused_personal_skills(skills, last_used, window_days=60)
        names = {n for n, _ in candidates}
        assert names == {"unused", "used-long-ago"}

    def test_handles_missing_skills_dir(self, tmp_path):
        candidates = list_unused_personal_skills(
            tmp_path / "absent", {}, window_days=60
        )
        assert candidates == []

    def test_skips_dirs_without_skill_md(self, tmp_path):
        skills = tmp_path / "skills"
        skills.mkdir()
        _make_skill(skills, "real")
        (skills / "not-a-skill").mkdir()  # no SKILL.md
        candidates = list_unused_personal_skills(skills, {}, window_days=60)
        names = {n for n, _ in candidates}
        assert names == {"real"}


class TestArchiveSkills:
    def test_moves_skills_to_archive_root(self, tmp_path):
        skills = tmp_path / "skills"
        skills.mkdir()
        _make_skill(skills, "alpha")
        _make_skill(skills, "beta")
        archive = tmp_path / "skills-archive-2026-05-18"

        moved = archive_skills(skills, ["alpha"], archive)

        assert moved == ["alpha"]
        assert (archive / "alpha" / "SKILL.md").exists()
        assert not (skills / "alpha").exists()
        assert (skills / "beta").exists()  # untouched

    def test_skips_missing_skills(self, tmp_path):
        skills = tmp_path / "skills"
        skills.mkdir()
        archive = tmp_path / "archive"
        moved = archive_skills(skills, ["nonexistent"], archive)
        assert moved == []

    def test_replaces_prior_archive_entry(self, tmp_path):
        skills = tmp_path / "skills"
        skills.mkdir()
        _make_skill(skills, "alpha")
        archive = tmp_path / "archive"
        archive.mkdir()
        (archive / "alpha").mkdir()
        (archive / "alpha" / "stale").write_text("old")

        archive_skills(skills, ["alpha"], archive)
        assert (archive / "alpha" / "SKILL.md").exists()
        assert not (archive / "alpha" / "stale").exists()


class TestUnarchive:
    def test_restores_from_latest_archive(self, tmp_path):
        skills = tmp_path / "skills"
        skills.mkdir()
        archive = tmp_path / "skills-archive-2026-05-18"
        archive.mkdir()
        _make_skill(archive, "tdd")

        ok = unarchive("tdd", skills)
        assert ok
        assert (skills / "tdd" / "SKILL.md").exists()
        assert not (archive / "tdd").exists()

    def test_falls_back_to_older_archive(self, tmp_path):
        skills = tmp_path / "skills"
        skills.mkdir()
        # newer archive — doesn't have the skill
        newer = tmp_path / "skills-archive-2026-05-18"
        newer.mkdir()
        # older archive — does
        older = tmp_path / "skills-archive-2026-05-17"
        older.mkdir()
        _make_skill(older, "tdd")
        # Touch order so newer is more recent
        import os, time
        time.sleep(0.01)
        os.utime(newer, None)

        ok = unarchive("tdd", skills)
        assert ok
        assert (skills / "tdd" / "SKILL.md").exists()

    def test_returns_false_when_not_found(self, tmp_path):
        skills = tmp_path / "skills"
        skills.mkdir()
        assert unarchive("nonexistent", skills) is False

    def test_does_not_clobber_existing(self, tmp_path):
        skills = tmp_path / "skills"
        skills.mkdir()
        _make_skill(skills, "tdd")
        archive = tmp_path / "skills-archive-2026-05-18"
        archive.mkdir()
        _make_skill(archive, "tdd")

        ok = unarchive("tdd", skills)
        assert ok is False
        # Both copies should still exist
        assert (skills / "tdd").exists()
        assert (archive / "tdd").exists()


class TestFindLatestArchive:
    def test_returns_none_when_no_archives(self, tmp_path):
        skills = tmp_path / "skills"
        skills.mkdir()
        assert find_latest_archive(tmp_path) is None

    def test_returns_most_recent(self, tmp_path):
        a = tmp_path / "skills-archive-2026-05-17"
        b = tmp_path / "skills-archive-2026-05-18"
        a.mkdir()
        b.mkdir()
        import os, time
        time.sleep(0.01)
        os.utime(b, None)
        latest = find_latest_archive(tmp_path)
        assert latest == b
