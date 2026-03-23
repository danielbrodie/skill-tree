"""Parse and write SKILL.md frontmatter without external YAML dependencies."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


@dataclass
class SkillFrontmatter:
    """Parsed SKILL.md file with frontmatter fields and raw lines."""

    raw_lines: list[str]
    fields: dict[str, str]
    start_line: int  # index of opening ---
    end_line: int  # index of closing ---
    has_frontmatter: bool


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_frontmatter(file_path: Path) -> SkillFrontmatter:
    """Parse SKILL.md frontmatter without a YAML library.

    Handles: quoted/unquoted values, folded (>) and literal (|) scalars,
    comment lines, files with no frontmatter.
    """
    try:
        text = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return SkillFrontmatter([], {}, 0, 0, False)

    lines = text.split("\n")

    if not lines or lines[0].rstrip() != "---":
        return SkillFrontmatter(lines, {}, 0, 0, False)

    # Find closing ---
    end_line = -1
    for i in range(1, len(lines)):
        if re.match(r"^---\s*$", lines[i]):
            end_line = i
            break

    if end_line == -1:
        return SkillFrontmatter(lines, {}, 0, 0, False)

    fm_lines = lines[1:end_line]
    fields: dict[str, str] = {}
    i = 0
    while i < len(fm_lines):
        line = fm_lines[i]

        # Skip comments and blank lines
        if line.lstrip().startswith("#") or not line.strip():
            i += 1
            continue

        # Match key: value
        m = re.match(r"^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*(.*)", line)
        if not m:
            i += 1
            continue

        key = m.group(1)
        value = m.group(2).strip()

        # Folded scalar (> or >-)
        if value in (">", ">-"):
            continuation = _collect_continuation(fm_lines, i + 1)
            fields[key] = " ".join(part for part in continuation if part)
            i += 1 + len(continuation)
            continue

        # Literal scalar (| or |-)
        if value in ("|", "|-"):
            continuation = _collect_continuation(fm_lines, i + 1)
            fields[key] = "\n".join(continuation).strip()
            i += 1 + len(continuation)
            continue

        # Strip surrounding quotes
        if len(value) >= 2 and (
            (value[0] == '"' and value[-1] == '"')
            or (value[0] == "'" and value[-1] == "'")
        ):
            value = value[1:-1]

        fields[key] = value
        i += 1

    return SkillFrontmatter(lines, fields, 0, end_line, True)


def _collect_continuation(lines: list[str], start: int) -> list[str]:
    """Collect indented continuation lines for folded/literal scalars."""
    result: list[str] = []
    i = start
    while i < len(lines):
        line = lines[i]
        if line and (line[0] == " " or line[0] == "\t"):
            result.append(line.strip())
        elif not line.strip():
            result.append("")
        else:
            break
        i += 1
    return result


# ---------------------------------------------------------------------------
# Field extraction helpers
# ---------------------------------------------------------------------------


def get_name(fm: SkillFrontmatter) -> str | None:
    return fm.fields.get("name")


def get_description(fm: SkillFrontmatter) -> str | None:
    return fm.fields.get("description")


def is_disabled(fm: SkillFrontmatter) -> bool:
    return fm.fields.get("disable-model-invocation", "").lower() == "true"


def has_always_true(fm: SkillFrontmatter) -> bool:
    return fm.fields.get("always", "").lower() == "true"


# ---------------------------------------------------------------------------
# Writing / modification
# ---------------------------------------------------------------------------


def set_field(fm: SkillFrontmatter, key: str, value: str) -> list[str]:
    """Return new lines with the field set/updated in frontmatter.

    If the field exists, replaces its value. If not, inserts before closing ---.
    If no frontmatter exists, wraps content in new frontmatter.
    """
    if not fm.has_frontmatter:
        # Add frontmatter around existing content
        body = "\n".join(fm.raw_lines)
        return ["---", f"{key}: {value}", "---", "", body.rstrip()]

    new_lines = list(fm.raw_lines)

    # Look for existing key in frontmatter
    for i in range(fm.start_line + 1, fm.end_line):
        line = new_lines[i]
        m = re.match(rf"^{re.escape(key)}\s*:\s*", line)
        if m:
            new_lines[i] = f"{key}: {value}"
            return new_lines

    # Key not found — insert before closing ---
    new_lines.insert(fm.end_line, f"{key}: {value}")
    return new_lines


def write_skillmd(path: Path, lines: list[str]) -> None:
    """Write lines to a SKILL.md file, ensuring trailing newline."""
    content = "\n".join(lines)
    if not content.endswith("\n"):
        content += "\n"
    path.write_text(content, encoding="utf-8")


def set_disable_model_invocation(file_path: Path, disabled: bool = True) -> None:
    """Set disable-model-invocation on a SKILL.md file."""
    fm = parse_frontmatter(file_path)
    new_lines = set_field(fm, "disable-model-invocation", str(disabled).lower())
    write_skillmd(file_path, new_lines)


# ---------------------------------------------------------------------------
# Scanning
# ---------------------------------------------------------------------------


def scan_skills_dir(skills_dir: Path) -> dict[str, Path]:
    """Scan a directory for skill folders containing SKILL.md.

    Returns {skill_name: path_to_SKILL.md}.
    """
    skills: dict[str, Path] = {}
    if not skills_dir.is_dir():
        return skills
    for entry in sorted(skills_dir.iterdir()):
        if entry.is_dir():
            skillmd = entry / "SKILL.md"
            if skillmd.exists():
                skills[entry.name] = skillmd
    return skills
