# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""skill-tree doctor: deterministic cross-ecosystem skill-health scanner.

Where `check` validates skill-tree's own cluster manifest, `doctor` scans the
whole machine's skill ecosystem — every registry, every installer — and detects
the failure-mode signatures catalogued in docs/ecosystem-map.md, citing each by
its signature number. Works with no manifest at all.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

# Allow running as a script from the repo root (mirrors check.py).
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.skillfile import scan_skills_dir  # noqa: E402

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """One detected ecosystem-health issue, tied to an ecosystem-map signature."""

    signature_id: int
    severity: str  # "error" | "warning" | "info"
    observation: str
    suggested_fix: str = ""
    paths: tuple[str, ...] = ()
    confidence: str = "high"


_SEVERITY_RANK = {"error": 0, "warning": 1, "info": 2}


@dataclass(frozen=True)
class DoctorReport:
    """Aggregated findings from a doctor run, ordered error → warning → info."""

    findings: tuple[Finding, ...]

    @property
    def errors(self) -> int:
        return sum(1 for f in self.findings if f.severity == "error")

    @property
    def warnings(self) -> int:
        return sum(1 for f in self.findings if f.severity == "warning")

    def exit_code(self) -> int:
        """2 on any error, 1 on any warning, else 0 (info never escalates)."""
        if self.errors:
            return 2
        if self.warnings:
            return 1
        return 0


# ---------------------------------------------------------------------------
# Detectors
# ---------------------------------------------------------------------------


# Agent name (as written in ~/.agents/.skill-lock.json lastSelectedAgents) -> the
# home-relative dir whose presence proves the agent is installed locally. Conservative
# on purpose: an agent we can't map is skipped, never flagged, to avoid false positives.
AGENT_HOME_DIRS: dict[str, str] = {
    "claude-code": ".claude",
    "codex": ".codex",
    "gemini-cli": ".gemini",
    "cursor": ".cursor",
    "amp": ".amp",
    "warp": ".warp",
    "windsurf": ".windsurf",
}


def detect_fanout_absent_agents(skill_lock: dict, home: Path) -> list[Finding]:
    """Signature #1: vercel-labs/skills fans out to agents not installed on this machine."""
    findings: list[Finding] = []
    for agent in skill_lock.get("lastSelectedAgents", []):
        dir_name = AGENT_HOME_DIRS.get(agent)
        if dir_name is None:
            continue  # unknown agent — can't verify, don't false-positive
        if not (home / dir_name).exists():
            findings.append(
                Finding(
                    signature_id=1,
                    severity="warning",
                    observation=f"skill fan-out targets agent '{agent}' but '{home / dir_name}' does not exist",
                    suggested_fix="npx skills config  # deselect agents you don't use here",
                    paths=(str(home / dir_name),),
                )
            )
    return findings


def _live_install_dirs(installed_plugins: dict) -> set[Path]:
    """Resolved version-dir paths Claude Code actually loads, from installed_plugins.json."""
    live: set[Path] = set()
    for records in installed_plugins.get("plugins", {}).values():
        if not isinstance(records, list):
            continue
        for rec in records:
            install_path = rec.get("installPath")
            if install_path:
                live.add(Path(install_path))
    return live


def detect_stale_plugin_cache(installed_plugins: dict) -> list[Finding]:
    """Signature #2a: an old version dir left beside the installed one in the plugin cache.

    Anchored on the version dirs `installed_plugins.json` actually references, so we
    only inspect directories we know are plugin installs (no false positives on
    marketplace-metadata dirs like `.git` / `.claude-plugin`).
    """
    findings: list[Finding] = []
    live = _live_install_dirs(installed_plugins)

    live_versions_by_plugin: dict[Path, set[str]] = {}
    for path in live:
        live_versions_by_plugin.setdefault(path.parent, set()).add(path.name)

    for plugin_dir, live_versions in sorted(live_versions_by_plugin.items()):
        if not plugin_dir.is_dir():
            continue
        plugin_ref = f"{plugin_dir.name}@{plugin_dir.parent.name}"
        live_list = ", ".join(sorted(live_versions))
        for version_dir in sorted(plugin_dir.iterdir()):
            if version_dir.is_dir() and version_dir.name not in live_versions:
                label = f"{plugin_dir.parent.name}/{plugin_dir.name}/{version_dir.name}"
                findings.append(
                    Finding(
                        signature_id=2,
                        severity="warning",
                        # Deterministic fact: this dir isn't referenced. Whether it's *dead*
                        # depends on the loader, and machines exist where a newer unreferenced
                        # dir is the one actually in use — so verify before deleting.
                        observation=(
                            f"plugin cache version skew: '{label}' is present but not referenced "
                            f"in installed_plugins.json (it references {live_list})"
                        ),
                        suggested_fix=(
                            f"confirm the live version first: claude plugin details {plugin_ref}; "
                            "then `rm -rf` whichever dir is truly unused"
                        ),
                        confidence="medium",
                        paths=(str(version_dir),),
                    )
                )
    return findings


def _plugin_skill_names(plugin_cache_dir: Path) -> dict[str, Path]:
    """Map skill name -> SKILL.md path across every plugin in the cache.

    Layout: cache/<marketplace>/<plugin>/<version>/skills/<name>/SKILL.md.
    """
    found: dict[str, Path] = {}
    if not plugin_cache_dir.is_dir():
        return found
    for skills_dir in sorted(plugin_cache_dir.glob("*/*/*/skills")):
        for name, path in scan_skills_dir(skills_dir).items():
            found.setdefault(name, path)
    return found


def detect_cross_registry_duplicates(
    agents_skills_dir: Path, plugin_cache_dir: Path
) -> list[Finding]:
    """Signature #7: the same skill name lives in `~/.agents/skills` and the plugin cache.

    The resolver loads whichever it finds first, so the two copies can silently diverge.
    """
    findings: list[Finding] = []
    agents = scan_skills_dir(agents_skills_dir)
    plugins = _plugin_skill_names(plugin_cache_dir)
    for name in sorted(set(agents) & set(plugins)):
        findings.append(
            Finding(
                signature_id=7,
                severity="warning",
                observation=(
                    f"'{name}' exists in two registries: {agents[name].parent} and "
                    f"{plugins[name].parent} — the resolver picks one arbitrarily"
                ),
                suggested_fix=f"keep one copy of '{name}'; uninstall it from the registry you don't want",
                paths=(str(agents[name].parent), str(plugins[name].parent)),
            )
        )
    return findings


def detect_unlinked_agent_skills(
    agents_skills_dir: Path, claude_skills_dir: Path
) -> list[Finding]:
    """Signature #5: a skill installed in `~/.agents/skills` with no entry in `~/.claude/skills`.

    Either it was scoped to a non-Claude-Code agent (intentional) or a fan-out symlink was
    never created. The file state alone can't tell which, so this is reported as info with the
    disambiguation command rather than asserting a fault.
    """
    findings: list[Finding] = []
    agents = scan_skills_dir(agents_skills_dir)
    for name in sorted(agents):
        if not (claude_skills_dir / name).exists():
            findings.append(
                Finding(
                    signature_id=5,
                    severity="info",
                    observation=(
                        f"'{name}' is in {agents_skills_dir} but not linked into {claude_skills_dir} "
                        "— scoped to another agent, or a missing fan-out"
                    ),
                    suggested_fix=(
                        f"npx skills list -g  # confirm scope; "
                        f"npx skills add <pkg> --skill {name} --agent claude-code -g -y  # if it should be here"
                    ),
                    confidence="medium",
                    paths=(str(agents_skills_dir / name),),
                )
            )
    return findings


def detect_symlink_rot(claude_skills_dir: Path) -> list[Finding]:
    """Signature #4: a `~/.claude/skills/*` symlink whose target no longer exists."""
    findings: list[Finding] = []
    if not claude_skills_dir.is_dir():
        return findings
    for entry in sorted(claude_skills_dir.iterdir()):
        # exists() follows the symlink, so it's False when the target is gone.
        if entry.is_symlink() and not entry.exists():
            target = entry.readlink()
            findings.append(
                Finding(
                    signature_id=4,
                    severity="warning",
                    observation=f"symlink '{entry.name}' points at missing target '{target}'",
                    suggested_fix=f"remove the dead symlink: rm {entry}",
                    paths=(str(entry),),
                )
            )
    return findings


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def run_doctor(
    *,
    home: Path,
    claude_skills_dir: Path,
    agents_skills_dir: Path,
    plugin_cache_dir: Path,
    installed_plugins: dict,
    skill_lock: dict,
) -> DoctorReport:
    """Run every deterministic cross-ecosystem detector and aggregate the findings."""
    findings: list[Finding] = []
    findings.extend(detect_symlink_rot(claude_skills_dir))
    findings.extend(detect_stale_plugin_cache(installed_plugins))
    findings.extend(detect_fanout_absent_agents(skill_lock, home))
    findings.extend(
        detect_cross_registry_duplicates(agents_skills_dir, plugin_cache_dir)
    )
    findings.extend(detect_unlinked_agent_skills(agents_skills_dir, claude_skills_dir))

    findings.sort(key=lambda f: (_SEVERITY_RANK.get(f.severity, 9), f.signature_id))
    return DoctorReport(findings=tuple(findings))


def findings_to_dicts(findings: tuple[Finding, ...]) -> list[dict]:
    """Serialize findings for `--json` output."""
    return [
        {
            "signature_id": f.signature_id,
            "severity": f.severity,
            "observation": f.observation,
            "suggested_fix": f.suggested_fix,
            "paths": list(f.paths),
            "confidence": f.confidence,
        }
        for f in findings
    ]


def _read_json(path: Path, default: dict) -> dict:
    """Read a JSON file, returning `default` on missing/unreadable/malformed."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return default


def load_environment(home: Path) -> dict:
    """Resolve the standard registry paths + parse installed_plugins.json / .skill-lock.json.

    Missing or malformed files degrade to safe empty defaults so the doctor still runs.
    """
    return {
        "home": home,
        "claude_skills_dir": home / ".claude" / "skills",
        "agents_skills_dir": home / ".agents" / "skills",
        "plugin_cache_dir": home / ".claude" / "plugins" / "cache",
        "installed_plugins": _read_json(
            home / ".claude" / "plugins" / "installed_plugins.json", {"plugins": {}}
        ),
        "skill_lock": _read_json(home / ".agents" / ".skill-lock.json", {}),
    }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class Colors:
    RED = "\033[91m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    @classmethod
    def disable(cls) -> None:
        for attr in ("RED", "YELLOW", "GREEN", "DIM", "BOLD", "RESET"):
            setattr(cls, attr, "")


_ICONS = {"error": ("RED", "✗"), "warning": ("YELLOW", "⚠"), "info": ("DIM", "•")}


def print_report(report: DoctorReport) -> None:
    """Human-readable ranked findings + summary line."""
    for f in report.findings:
        color_attr, icon = _ICONS.get(f.severity, ("RESET", "-"))
        color = getattr(Colors, color_attr)
        print(f"  {color}{icon}{Colors.RESET} [#{f.signature_id}] {f.observation}")
        if f.suggested_fix:
            print(f"      {Colors.DIM}fix:{Colors.RESET} {f.suggested_fix}")

    info = sum(1 for f in report.findings if f.severity == "info")
    if report.errors or report.warnings or info:
        print()
        print(
            f"{Colors.BOLD}{report.errors} error(s){Colors.RESET}, "
            f"{report.warnings} warning(s), {info} info"
        )
    else:
        print(
            f"{Colors.GREEN}Ecosystem clean — no known failure-mode signatures found.{Colors.RESET}"
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="skill-tree doctor: deterministic cross-ecosystem skill-health scan"
    )
    parser.add_argument("--json", action="store_true", help="emit findings as JSON")
    parser.add_argument(
        "--home", type=Path, default=Path.home(), help="home dir to scan (default: ~)"
    )
    parser.add_argument(
        "--notify", action="store_true", help="one-line stderr message if issues found"
    )
    args = parser.parse_args()

    if not sys.stdout.isatty():
        Colors.disable()

    report = run_doctor(**load_environment(args.home))

    if args.json:
        print(json.dumps({"findings": findings_to_dicts(report.findings)}, indent=2))
    else:
        print_report(report)

    if args.notify and (report.errors or report.warnings):
        print(
            f"skill-tree doctor: {report.errors} error(s), {report.warnings} warning(s). "
            "Run `/skill-tree:audit` for details.",
            file=sys.stderr,
        )

    sys.exit(report.exit_code())


if __name__ == "__main__":
    main()
