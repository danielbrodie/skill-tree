"""Security checks for untrusted SKILL.md content."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


# ---------------------------------------------------------------------------
# Skill name validation
# ---------------------------------------------------------------------------

SKILL_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")

MAX_SKILL_FILE_SIZE = 64 * 1024  # 64KB


def validate_skill_name(name: str) -> str | None:
    """Return error message if name is invalid, else None."""
    if not name:
        return "skill name is empty"
    if not SKILL_NAME_RE.match(name):
        return (
            f"invalid skill name '{name}' — "
            "must match ^[a-z0-9][a-z0-9-]*[a-z0-9]$ "
            "(lowercase alphanumeric and hyphens, no leading/trailing hyphen)"
        )
    return None


# ---------------------------------------------------------------------------
# Content policy warnings
# ---------------------------------------------------------------------------


class WarningSeverity(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class ContentWarning:
    severity: WarningSeverity
    category: str
    message: str
    line_number: int | None = None


def check_content_policy(content: str, name: str = "") -> list[ContentWarning]:
    """Check SKILL.md content for suspicious patterns.

    Returns warnings (not blocks). The user makes the final decision
    after seeing the full content.
    """
    warnings: list[ContentWarning] = []
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        # Prompt injection patterns
        if re.search(r"ignore\s+(all\s+)?(previous|prior)\s+(instructions?|prompts?)", line, re.IGNORECASE):
            warnings.append(ContentWarning(
                WarningSeverity.CRITICAL,
                "prompt-injection",
                f"Line {i}: potential prompt injection — 'ignore previous instructions'",
                i,
            ))

        if re.search(r"you\s+are\s+now\s+", line, re.IGNORECASE):
            warnings.append(ContentWarning(
                WarningSeverity.WARNING,
                "prompt-injection",
                f"Line {i}: potential role override — 'you are now'",
                i,
            ))

        # Path references outside skills directories
        if re.search(r"(?:/etc/|/var/|/tmp/|/usr/|/root/|C:\\)", line):
            warnings.append(ContentWarning(
                WarningSeverity.WARNING,
                "path-reference",
                f"Line {i}: references system path outside skills directory",
                i,
            ))

        # Hidden text: zero-width characters
        if re.search(r"[\u200b\u200c\u200d\u2060\ufeff]", line):
            warnings.append(ContentWarning(
                WarningSeverity.CRITICAL,
                "hidden-text",
                f"Line {i}: contains zero-width unicode characters",
                i,
            ))

    # HTML comments with content (could hide instructions)
    html_comments = re.findall(r"<!--(.+?)-->", content, re.DOTALL)
    for comment in html_comments:
        stripped = comment.strip()
        if len(stripped) > 20:  # ignore trivial comments
            warnings.append(ContentWarning(
                WarningSeverity.WARNING,
                "hidden-text",
                f"HTML comment with content ({len(stripped)} chars): {stripped[:60]}...",
            ))

    # File size
    if len(content.encode("utf-8")) > MAX_SKILL_FILE_SIZE:
        warnings.append(ContentWarning(
            WarningSeverity.WARNING,
            "file-size",
            f"File is {len(content.encode('utf-8')):,} bytes (max {MAX_SKILL_FILE_SIZE:,})",
        ))

    return warnings
