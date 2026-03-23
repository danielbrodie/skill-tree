"""Codex CLI compatibility: generate agents/openai.yaml for leaf skills."""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# YAML generation (hand-rolled to avoid pyyaml dependency in lib)
# ---------------------------------------------------------------------------

_OPENAI_YAML_TEMPLATE = """\
interface:
  display_name: "{display_name}"
  short_description: "{short_description}"

policy:
  allow_implicit_invocation: {allow_implicit}
"""


def generate_openai_yaml(
    display_name: str,
    short_description: str,
    allow_implicit_invocation: bool = False,
) -> str:
    """Generate an agents/openai.yaml for a Codex CLI skill.

    Args:
        display_name: Human-readable skill name.
        short_description: 25-64 character description for Codex UI.
        allow_implicit_invocation: If True, Codex can invoke without explicit $name.
    """
    # Codex validates short_description at 25-64 chars but it's soft —
    # we truncate silently rather than erroring
    truncated = short_description[:64] if len(short_description) > 64 else short_description

    return _OPENAI_YAML_TEMPLATE.format(
        display_name=display_name.replace('"', '\\"'),
        short_description=truncated.replace('"', '\\"'),
        allow_implicit=str(allow_implicit_invocation).lower(),
    )


def write_openai_yaml(
    skill_dir: Path,
    display_name: str,
    short_description: str,
    allow_implicit_invocation: bool = False,
) -> Path:
    """Write agents/openai.yaml inside a skill directory.

    Creates the agents/ subdirectory if needed.
    Returns the path to the written file.
    """
    agents_dir = skill_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = agents_dir / "openai.yaml"

    content = generate_openai_yaml(
        display_name=display_name,
        short_description=short_description,
        allow_implicit_invocation=allow_implicit_invocation,
    )
    yaml_path.write_text(content, encoding="utf-8")
    return yaml_path
