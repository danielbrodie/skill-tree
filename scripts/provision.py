"""Per-project skill provisioning — the BRO-182 implementation.

The shape mirrors `setup.py`'s "the model is the algorithm" pattern:
- `--list-candidates` emits machine-readable project signals + global skill catalog
- `--apply --skills=a,b,c [--reason '...']` does the file operations
- `--show` prints the current project manifest

Project manifest location: `<cwd>/.claude/.skilltree.json`
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_MANIFEST_REL = ".claude/.skilltree.json"
PROJECT_SKILLS_REL = ".claude/skills"


def find_project_root(start: Path) -> Path:
    """Find the project root from start dir. Looks for .git/, .claude/, or common manifests.

    Falls back to cwd if no marker found.
    """
    markers = {".git", ".claude", "package.json", "pyproject.toml", "Cargo.toml", "go.mod"}
    cur = start.resolve()
    while cur != cur.parent:
        if any((cur / m).exists() for m in markers):
            return cur
        cur = cur.parent
    return start.resolve()


def collect_project_signals(root: Path) -> dict:
    """Read project signals: CLAUDE.md content + manifest filenames + language hints."""
    signals: dict = {"root": str(root), "files": [], "claudeMd": None, "languages": set()}

    interesting_names = {
        "CLAUDE.md", "AGENTS.md", "README.md", "README",
        "package.json", "pyproject.toml", "Cargo.toml", "go.mod",
        "Gemfile", "build.gradle", "build.gradle.kts", "Podfile",
        "requirements.txt", "Pipfile", "deno.json", "bun.lockb",
    }
    lang_map = {
        "package.json": "javascript", "deno.json": "typescript", "bun.lockb": "typescript",
        "pyproject.toml": "python", "requirements.txt": "python", "Pipfile": "python",
        "Cargo.toml": "rust", "go.mod": "go", "Gemfile": "ruby",
        "build.gradle": "kotlin", "build.gradle.kts": "kotlin", "Podfile": "swift",
    }

    for name in interesting_names:
        p = root / name
        if not p.exists():
            continue
        signals["files"].append(name)
        if name in lang_map:
            signals["languages"].add(lang_map[name])
        if name == "CLAUDE.md":
            try:
                signals["claudeMd"] = p.read_text()[:4000]
            except (OSError, UnicodeDecodeError):
                pass

    # Detect language by file extension (light pass — top-level only)
    ext_to_lang = {".swift": "swift", ".ts": "typescript", ".tsx": "typescript",
                   ".py": "python", ".rs": "rust", ".go": "go", ".rb": "ruby"}
    for child in root.iterdir():
        if child.is_file() and child.suffix in ext_to_lang:
            signals["languages"].add(ext_to_lang[child.suffix])

    signals["languages"] = sorted(signals["languages"])
    return signals


def _read_skill_md(skill_md: Path) -> tuple[str, str]:
    """Return (name, description) extracted from a SKILL.md's frontmatter."""
    try:
        text = skill_md.read_text()
    except (OSError, UnicodeDecodeError):
        return "", ""
    name, desc, in_fm = "", "", False
    for line in text.splitlines():
        if line.strip() == "---":
            if not in_fm:
                in_fm = True
                continue
            break
        if not in_fm:
            continue
        if line.startswith("name:"):
            name = line.split(":", 1)[1].strip().strip('"')
        elif line.startswith("description:"):
            desc = line.split(":", 1)[1].strip().strip('"')
    return name, desc


def collect_personal_catalog(skills_dir: Path) -> list[dict]:
    """Skills installed in ~/.claude/skills/."""
    out: list[dict] = []
    if not skills_dir.exists():
        return out
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        name, desc = _read_skill_md(skill_md)
        if not name:
            name = skill_dir.name
        out.append(
            {"name": name, "description": desc, "path": str(skill_dir), "origin": "personal"}
        )
    return out


def _semver_key(version: str) -> tuple:
    """Sort key for versions like '5.1.0' or 'unknown'. Unknown sorts last."""
    if version == "unknown":
        return (-1,)
    try:
        return tuple(int(p) for p in version.split("."))
    except ValueError:
        return (-1,)


def collect_plugin_catalog(plugins_cache_dir: Path) -> list[dict]:
    """Walk ~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/ for SKILL.md files.

    For each plugin, pick the highest semver version, then index every SKILL.md
    inside that version's tree (either at the plugin root or under skills/).
    Emits entries with a `plugin:skill` namespaced name matching the invocation form
    seen in Claude Code session logs (e.g. `superpowers:writing-plans`).
    """
    out: list[dict] = []
    if not plugins_cache_dir.exists():
        return out

    # marketplace/plugin/version path layout
    for marketplace_dir in sorted(plugins_cache_dir.iterdir()):
        if not marketplace_dir.is_dir():
            continue
        for plugin_dir in sorted(marketplace_dir.iterdir()):
            if not plugin_dir.is_dir():
                continue
            versions = [v for v in plugin_dir.iterdir() if v.is_dir()]
            if not versions:
                continue
            latest = max(versions, key=lambda v: _semver_key(v.name))
            plugin_name = plugin_dir.name

            # Option A: SKILL.md directly at version root
            root_skill = latest / "SKILL.md"
            if root_skill.exists():
                name, desc = _read_skill_md(root_skill)
                qualified = name if ":" in (name or "") else f"{plugin_name}:{name or plugin_name}"
                out.append({
                    "name": qualified,
                    "description": desc,
                    "path": str(latest),
                    "origin": f"plugin:{marketplace_dir.name}/{plugin_name}@{latest.name}",
                })

            # Option B: skills/<name>/SKILL.md
            skills_subdir = latest / "skills"
            if skills_subdir.is_dir():
                for sd in sorted(skills_subdir.iterdir()):
                    if not sd.is_dir():
                        continue
                    s_md = sd / "SKILL.md"
                    if not s_md.exists():
                        continue
                    name, desc = _read_skill_md(s_md)
                    if not name:
                        name = sd.name
                    qualified = name if ":" in name else f"{plugin_name}:{name}"
                    out.append({
                        "name": qualified,
                        "description": desc,
                        "path": str(sd),
                        "origin": f"plugin:{marketplace_dir.name}/{plugin_name}@{latest.name}",
                    })
    return out


def collect_global_catalog(
    skills_dir: Path,
    plugins_cache_dir: Path | None = None,
) -> list[dict]:
    """Personal skills (~/.claude/skills/) + plugin-namespaced skills (plugin cache).

    Per BRO-184: plugin skills drove ~88% of invocations in the corpus but were
    invisible to the per-project provisioner before this change.
    """
    catalog = collect_personal_catalog(skills_dir)
    if plugins_cache_dir is None:
        plugins_cache_dir = skills_dir.parent / "plugins" / "cache"
    catalog.extend(collect_plugin_catalog(plugins_cache_dir))
    return catalog


def load_project_manifest(root: Path) -> dict | None:
    p = root / PROJECT_MANIFEST_REL
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def write_project_manifest(root: Path, manifest: dict) -> None:
    p = root / PROJECT_MANIFEST_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(manifest, indent=2) + "\n")


def apply_skills(
    root: Path, skill_names: list[str], reason: str, skills_dir: Path
) -> dict:
    """Copy each named skill into the project's .claude/skills/, update manifest."""
    now = datetime.now(timezone.utc).isoformat()
    manifest = load_project_manifest(root) or {
        "version": "1.0",
        "sourceLibrary": str(skills_dir),
        "skills": {},
        "auditLog": [],
    }
    manifest["syncedAt"] = now

    project_skills_dir = root / PROJECT_SKILLS_REL
    project_skills_dir.mkdir(parents=True, exist_ok=True)

    added: list[str] = []
    for name in skill_names:
        src = skills_dir / name
        if not src.is_dir():
            print(f"warn: skill not found in library: {name}", file=sys.stderr)
            continue
        dst = project_skills_dir / name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, symlinks=False)
        manifest["skills"][name] = {
            "source": str(src),
            "reason": reason,
            "syncedAt": now,
        }
        manifest["auditLog"].append(
            {"at": now, "action": "added", "skill": name, "reason": reason}
        )
        added.append(name)

    write_project_manifest(root, manifest)
    return {"added": added, "manifest": manifest}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-root",
        default=None,
        help="Override the auto-detected project root",
    )
    parser.add_argument(
        "--skills-library",
        default=str(Path.home() / ".claude" / "skills"),
    )

    sub = parser.add_mutually_exclusive_group(required=True)
    sub.add_argument(
        "--list-candidates",
        action="store_true",
        help="Emit project signals + global catalog as JSON for the model to read",
    )
    sub.add_argument(
        "--apply",
        action="store_true",
        help="Copy --skills into the project's .claude/skills/",
    )
    sub.add_argument(
        "--show",
        action="store_true",
        help="Print the current project manifest",
    )
    sub.add_argument(
        "--global-suggest",
        action="store_true",
        help="Suggest the top-N most-invoked skills from session history for the global base layer (ADR 0002)",
    )

    parser.add_argument(
        "--skills",
        default="",
        help="Comma-separated skill names (with --apply)",
    )
    parser.add_argument(
        "--reason",
        default="",
        help="Why these skills (with --apply, recorded in manifest)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="N for --global-suggest (default 10)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=60,
        help="Lookback window for --global-suggest (default 60)",
    )

    args = parser.parse_args()

    root = Path(args.project_root) if args.project_root else find_project_root(Path.cwd())
    skills_dir = Path(args.skills_library)

    if args.list_candidates:
        signals = collect_project_signals(root)
        catalog = collect_global_catalog(skills_dir)
        existing = load_project_manifest(root)
        print(json.dumps({
            "project": signals,
            "catalog": catalog,
            "existing": existing,
        }, indent=2))
        return 0

    if args.apply:
        names = [s.strip() for s in args.skills.split(",") if s.strip()]
        if not names:
            print("error: --apply requires --skills", file=sys.stderr)
            return 2
        result = apply_skills(root, names, args.reason, skills_dir)
        print(json.dumps(result, indent=2))
        return 0

    if args.show:
        m = load_project_manifest(root)
        if not m:
            print(f"(no manifest at {root / PROJECT_MANIFEST_REL})")
            return 1
        print(json.dumps(m, indent=2))
        return 0

    if args.global_suggest:
        from measure import build_corpus  # local import to avoid cost on other paths
        from collections import Counter

        projects_root = Path.home() / ".claude" / "projects"
        records = build_corpus(projects_root, args.days)
        if not records:
            print(f"(no Skill invocations in last {args.days} days)")
            return 1
        catalog_names = {c["name"] for c in collect_global_catalog(skills_dir)}
        counter: Counter[str] = Counter(r.skill for r in records)
        top = counter.most_common(args.top_n)

        print(f"# Global base suggestion — top {args.top_n} skills, last {args.days} days\n")
        print(f"Corpus: {len(records)} records, {len(counter)} unique skills\n")
        print("| Rank | Skill | Invocations | In catalog? |")
        print("|---|---|---|---|")
        for rank, (skill, n) in enumerate(top, 1):
            in_cat = "yes" if skill in catalog_names else "**no — uninstalled?**"
            print(f"| {rank} | `{skill}` | {n} | {in_cat} |")
        print()
        print("Per ADR 0002, these are the skills that would make up the global-popular base layer.")
        print("Skills not in catalog are invoked but missing locally — review whether to install or retire.")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
