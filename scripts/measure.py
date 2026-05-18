"""Build a labelled corpus of (user prompt → invoked skill) pairs from Claude Code session logs.

Output: JSON list of records to stdout, or a markdown summary with --report.

This is the first half of BRO-180. The simulation half (recall@k under each routing
mode) lands in a follow-up once we have the corpus pinned down.

Usage:
    uv run scripts/measure.py --days 60                  # emit JSONL records
    uv run scripts/measure.py --days 60 --report         # human-readable summary
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


@dataclass(frozen=True)
class CorpusRecord:
    session_id: str
    timestamp: str
    project_dir: str
    user_prompt: str
    skill: str


def decode_project_dir(jsonl_path: Path) -> str:
    """Project directory names are slug-encoded — restore the original path."""
    slug = jsonl_path.parent.name
    if not slug.startswith("-"):
        return slug
    return "/" + slug[1:].replace("-", "/")


def iter_messages(jsonl_path: Path):
    """Yield parsed JSONL message dicts, skipping malformed lines."""
    with jsonl_path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def extract_skill_invocations(jsonl_path: Path, cutoff_iso: str) -> list[CorpusRecord]:
    """Walk a session file, emit a record for every Skill tool_use."""
    records: list[CorpusRecord] = []
    messages_by_uuid: dict[str, dict] = {}
    # First pass: index by uuid so we can resolve parent pointers.
    all_messages = list(iter_messages(jsonl_path))
    for msg in all_messages:
        if uuid := msg.get("uuid"):
            messages_by_uuid[uuid] = msg

    project_dir = decode_project_dir(jsonl_path)
    session_id = jsonl_path.stem

    for msg in all_messages:
        ts = msg.get("timestamp", "")
        if ts and ts < cutoff_iso:
            continue
        if msg.get("message", {}).get("role") != "assistant":
            continue
        for block in msg.get("message", {}).get("content", []) or []:
            if not isinstance(block, dict):
                continue
            if block.get("type") != "tool_use" or block.get("name") != "Skill":
                continue
            skill = block.get("input", {}).get("skill")
            if not skill:
                continue
            user_prompt = walk_back_for_user_prompt(msg, messages_by_uuid)
            records.append(
                CorpusRecord(
                    session_id=session_id,
                    timestamp=ts,
                    project_dir=project_dir,
                    user_prompt=user_prompt or "",
                    skill=skill,
                )
            )
    return records


def walk_back_for_user_prompt(
    msg: dict, index: dict[str, dict], max_hops: int = 20
) -> str | None:
    """Walk parent pointers until we find the most recent user text message."""
    current = msg
    for _ in range(max_hops):
        parent_uuid = current.get("parentUuid")
        if not parent_uuid:
            return None
        parent = index.get(parent_uuid)
        if parent is None:
            return None
        if parent.get("message", {}).get("role") == "user":
            content = parent.get("message", {}).get("content")
            if isinstance(content, str):
                return content[:500]
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        return (block.get("text") or "")[:500]
                    if isinstance(block, str):
                        return block[:500]
        current = parent
    return None


def build_corpus(projects_root: Path, days: int) -> list[CorpusRecord]:
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    cutoff_iso = cutoff.isoformat()
    all_records: list[CorpusRecord] = []
    for jsonl in projects_root.rglob("*.jsonl"):
        try:
            all_records.extend(extract_skill_invocations(jsonl, cutoff_iso))
        except OSError:
            continue
    return all_records


def report(records: list[CorpusRecord]) -> str:
    if not records:
        return "(no Skill invocations found in window)"
    by_skill: Counter[str] = Counter(r.skill for r in records)
    by_project: Counter[str] = Counter(r.project_dir for r in records)
    lines = [
        f"# skill-tree corpus — {len(records)} records",
        "",
        f"Unique skills invoked: {len(by_skill)}",
        f"Unique projects: {len(by_project)}",
        "",
        "## Top skills (count)",
        "",
    ]
    for name, n in by_skill.most_common(20):
        lines.append(f"- `{name}` — {n}")
    lines += ["", "## Top projects (invocation count)", ""]
    for path, n in by_project.most_common(10):
        lines.append(f"- `{path}` — {n}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--projects-root",
        default=str(Path.home() / ".claude" / "projects"),
        help="Root of Claude Code session JSONL files",
    )
    parser.add_argument("--days", type=int, default=60, help="Lookback window")
    parser.add_argument(
        "--report",
        action="store_true",
        help="Print human-readable summary instead of JSONL records",
    )
    args = parser.parse_args()

    records = build_corpus(Path(args.projects_root), args.days)
    if args.report:
        print(report(records))
    else:
        for r in records:
            print(json.dumps(asdict(r), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
