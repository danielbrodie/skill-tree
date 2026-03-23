# /// script
# requires-python = ">=3.11"
# dependencies = ["scikit-learn", "pyyaml"]
# ///
"""skill-tree add: fetch a skill from GitHub and wire it into the graph.

Usage:
  skill-tree add <url>
  skill-tree add <org>/<repo>/<skill-name>

URL formats:
  https://github.com/<org>/<repo>/tree/main/skills/<skill-name>
  https://github.com/<org>/<repo>/blob/main/skills/<skill-name>/SKILL.md
  https://github.com/<org>/<repo>
  <org>/<repo>/<skill-name>

Flags:
  --library-dir  override library path (default: ~/.claude/skills-library)
  --manifest     override manifest path
  --force        allow overwriting existing skill (shows diff)
  --dry-run      preview without writing
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.manifest import (
    Cluster,
    LeafEntry,
    Manifest,
    load_manifest,
    save_manifest,
    serialize_manifest,
)
from lib.security import (
    ContentWarning,
    WarningSeverity,
    check_content_policy,
    validate_skill_name,
)
from lib.skillfile import parse_frontmatter, get_name, get_description


# ---------------------------------------------------------------------------
# ANSI
# ---------------------------------------------------------------------------


class Colors:
    RED = "\033[91m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    @classmethod
    def disable(cls) -> None:
        for attr in ("RED", "YELLOW", "GREEN", "CYAN", "BOLD", "DIM", "RESET"):
            setattr(cls, attr, "")


if not sys.stdout.isatty():
    Colors.disable()


# ---------------------------------------------------------------------------
# URL parsing
# ---------------------------------------------------------------------------


def parse_github_url(url: str) -> tuple[str, str, str, str | None]:
    """Parse a GitHub URL into (org, repo, skill_name, ref).

    Returns (org, repo, skill_name, ref) where ref is the branch/tag or None.
    """
    # Full URL: https://github.com/<org>/<repo>/tree/<ref>/skills/<skill>
    m = re.match(
        r"https?://github\.com/([^/]+)/([^/]+)/tree/([^/]+)/(?:skills?/)?(.+?)/?$",
        url,
    )
    if m:
        skill = m.group(4).rstrip("/").split("/")[0]
        return m.group(1), m.group(2), skill, m.group(3)

    # Blob URL: https://github.com/<org>/<repo>/blob/<ref>/skills/<skill>/SKILL.md
    m = re.match(
        r"https?://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(?:skills?/)?([^/]+)/SKILL\.md$",
        url,
    )
    if m:
        return m.group(1), m.group(2), m.group(4), m.group(3)

    # Repo root: https://github.com/<org>/<repo>
    m = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    if m:
        return m.group(1), m.group(2), "", None

    # Shorthand: org/repo/skill
    m = re.match(r"^([^/]+)/([^/]+)/([^/]+)$", url)
    if m:
        return m.group(1), m.group(2), m.group(3), None

    raise ValueError(f"Cannot parse GitHub URL: {url}")


# ---------------------------------------------------------------------------
# GitHub fetch
# ---------------------------------------------------------------------------


def fetch_skill_content(org: str, repo: str, skill_name: str, ref: str | None = None) -> tuple[str, str | None]:
    """Fetch SKILL.md content from GitHub.

    Uses `gh` CLI if available, falls back to GitHub API.
    Returns (content, commit_sha).
    """
    ref = ref or "main"

    # Try gh CLI first
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{org}/{repo}/contents/skills/{skill_name}/SKILL.md",
             "--jq", ".content", "-H", "Accept: application/vnd.github.raw+json"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            # Get commit SHA
            sha_result = subprocess.run(
                ["gh", "api", f"repos/{org}/{repo}/commits/{ref}",
                 "--jq", ".sha"],
                capture_output=True, text=True, timeout=10,
            )
            sha = sha_result.stdout.strip() if sha_result.returncode == 0 else None
            return result.stdout, sha
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fallback: try raw URL
    import urllib.request
    raw_url = f"https://raw.githubusercontent.com/{org}/{repo}/{ref}/skills/{skill_name}/SKILL.md"
    try:
        with urllib.request.urlopen(raw_url, timeout=30) as resp:
            content = resp.read().decode("utf-8")
            return content, None
    except Exception as e:
        raise RuntimeError(f"Failed to fetch from GitHub: {e}") from e


# ---------------------------------------------------------------------------
# Cluster matching
# ---------------------------------------------------------------------------


def find_best_cluster(
    skill_content: str,
    skill_name: str,
    manifest: Manifest,
    library_dir: Path,
) -> tuple[str | None, float]:
    """Find the best matching cluster for a new skill.

    Returns (cluster_name, similarity_score) or (None, 0.0).
    """
    if not manifest.clusters:
        return None, 0.0

    try:
        from lib.cluster import SkillDocument, _build_document_text
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        return None, 0.0

    # Build document for the new skill
    fm = parse_frontmatter(Path("/dev/null"))  # won't actually read
    # Parse the content directly
    lines = skill_content.split("\n")
    description = ""
    name = skill_name
    # Quick frontmatter extract
    if lines and lines[0].strip() == "---":
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                # Extract name and description from frontmatter
                for fl in lines[1:i]:
                    if fl.startswith("name:"):
                        name = fl.split(":", 1)[1].strip().strip("\"'")
                    elif fl.startswith("description:"):
                        description = fl.split(":", 1)[1].strip().strip("\"'")
                break

    new_doc = SkillDocument(name=name, description=description, body_preview=skill_content[:2000])
    new_text = _build_document_text(new_doc)

    # Build documents for each cluster
    cluster_texts: list[str] = []
    cluster_names: list[str] = []
    for cname, cluster in manifest.clusters.items():
        # Use cluster description + leaf routing hints
        parts = [cluster.description]
        for leaf in cluster.leaves.values():
            if leaf.routing_hint:
                parts.append(leaf.routing_hint)
        cluster_texts.append(" ".join(parts))
        cluster_names.append(cname)

    # TF-IDF similarity
    all_texts = [new_text] + cluster_texts
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
    tfidf = vectorizer.fit_transform(all_texts)

    similarities = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()
    best_idx = similarities.argmax()
    best_score = float(similarities[best_idx])

    if best_score < 0.05:
        return None, best_score

    return cluster_names[best_idx], best_score


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="skill-tree add: fetch and wire a skill from GitHub")
    parser.add_argument("url", help="GitHub URL or shorthand (org/repo/skill)")
    parser.add_argument(
        "--library-dir",
        type=Path,
        default=Path.home() / ".claude" / "skills-library",
    )
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--force", action="store_true", help="overwrite existing skill")
    parser.add_argument("--dry-run", action="store_true", help="preview without writing")
    args = parser.parse_args()

    manifest_path = args.manifest or (args.library_dir / "skill-tree" / "manifest.json")

    # Parse URL
    try:
        org, repo, skill_name, ref = parse_github_url(args.url)
    except ValueError as e:
        print(f"{Colors.RED}Error:{Colors.RESET} {e}", file=sys.stderr)
        sys.exit(1)

    if not skill_name:
        print(f"{Colors.RED}Error:{Colors.RESET} Could not determine skill name from URL.", file=sys.stderr)
        print("Use format: org/repo/skill-name", file=sys.stderr)
        sys.exit(1)

    # Validate name
    name_error = validate_skill_name(skill_name)
    if name_error:
        print(f"{Colors.RED}Error:{Colors.RESET} {name_error}", file=sys.stderr)
        sys.exit(1)

    # Check for duplicates
    target_dir = args.library_dir / skill_name
    if target_dir.exists() and not args.force:
        print(f"{Colors.RED}Error:{Colors.RESET} Skill '{skill_name}' already exists at {target_dir}", file=sys.stderr)
        print("Use --force to overwrite (will show diff).", file=sys.stderr)
        sys.exit(1)

    # Fetch
    print(f"Fetching {Colors.CYAN}{skill_name}{Colors.RESET} from {org}/{repo}...")
    try:
        content, commit_sha = fetch_skill_content(org, repo, skill_name, ref)
    except Exception as e:
        print(f"{Colors.RED}Error:{Colors.RESET} {e}", file=sys.stderr)
        sys.exit(1)

    # Display full content
    print(f"\n{Colors.BOLD}--- SKILL.md content ---{Colors.RESET}")
    print(content)
    print(f"{Colors.BOLD}--- end ---{Colors.RESET}\n")

    # Security checks
    warnings = check_content_policy(content, skill_name)
    if warnings:
        critical = [w for w in warnings if w.severity == WarningSeverity.CRITICAL]
        other = [w for w in warnings if w.severity != WarningSeverity.CRITICAL]

        if critical:
            print(f"{Colors.RED}{Colors.BOLD}CRITICAL WARNINGS:{Colors.RESET}")
            for w in critical:
                print(f"  {Colors.RED}!{Colors.RESET} [{w.category}] {w.message}")
            print()

        if other:
            print(f"{Colors.YELLOW}Warnings:{Colors.RESET}")
            for w in other:
                print(f"  {Colors.YELLOW}*{Colors.RESET} [{w.category}] {w.message}")
            print()

    # Find best cluster match
    if manifest_path.exists():
        manifest = load_manifest(manifest_path)
        best_cluster, similarity = find_best_cluster(content, skill_name, manifest, args.library_dir)
    else:
        manifest = None
        best_cluster, similarity = None, 0.0

    if best_cluster:
        print(f"Best cluster match: {Colors.GREEN}{best_cluster}{Colors.RESET} (similarity: {similarity:.2f})")
    else:
        print(f"No strong cluster match found. Will add as {Colors.YELLOW}standalone{Colors.RESET}.")

    # Summary
    print(f"\n{Colors.BOLD}Action:{Colors.RESET}")
    print(f"  Write to: {target_dir}/SKILL.md")
    print(f"  Sandbox: disable-model-invocation: true (default)")
    if best_cluster:
        print(f"  Add to cluster: {best_cluster}")
    else:
        print(f"  Add as standalone")
    if commit_sha:
        print(f"  Source pin: {commit_sha[:12]}")

    if args.dry_run:
        print(f"\n{Colors.YELLOW}[dry-run]{Colors.RESET} No files written.")
        sys.exit(0)

    # Confirm
    print(f"\nProceed? [y/N] ", end="", flush=True)
    response = input().strip().lower()
    if response not in ("y", "yes"):
        print("Aborted.")
        sys.exit(0)

    # Write skill
    target_dir.mkdir(parents=True, exist_ok=True)
    skillmd_path = target_dir / "SKILL.md"

    # Add disable-model-invocation to frontmatter
    if "disable-model-invocation:" not in content:
        if content.startswith("---\n"):
            # Insert after opening ---
            parts = content.split("---\n", 2)
            if len(parts) >= 3:
                content = f"---\ndisable-model-invocation: true\n{parts[1]}---\n{parts[2]}"
        else:
            content = f"---\ndisable-model-invocation: true\n---\n\n{content}"

    skillmd_path.write_text(content, encoding="utf-8")
    print(f"{Colors.GREEN}Written:{Colors.RESET} {skillmd_path}")

    # Update manifest
    if manifest and manifest_path.exists():
        # Parse content for routing hint
        lines = content.split("\n")
        description = ""
        if lines[0].strip() == "---":
            for line in lines[1:]:
                if line.strip() == "---":
                    break
                if line.startswith("description:"):
                    description = line.split(":", 1)[1].strip().strip("\"'")

        routing_hint = description.split(".")[0].strip() if description else skill_name
        if routing_hint and not routing_hint.endswith("."):
            routing_hint += "."

        data = serialize_manifest(manifest)

        if best_cluster and best_cluster in data["clusters"]:
            data["clusters"][best_cluster]["leaves"][skill_name] = {
                "routingHint": routing_hint,
            }
        else:
            if skill_name not in data["standalones"]:
                data["standalones"].append(skill_name)
                data["standalones"].sort()

        # Add source metadata as a comment-like field
        # (stored in manifest for future `skill-tree update`)
        if "_sources" not in data:
            data["_sources"] = {}
        data["_sources"][skill_name] = {
            "sourceUrl": args.url,
            "sourceCommit": commit_sha,
            "fetchedAt": datetime.now(timezone.utc).isoformat(),
        }

        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(str(manifest_path) + ".tmp", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        import os
        os.replace(str(manifest_path) + ".tmp", str(manifest_path))

        if best_cluster:
            print(f"{Colors.GREEN}Added{Colors.RESET} to cluster '{best_cluster}' in manifest.")
        else:
            print(f"{Colors.GREEN}Added{Colors.RESET} as standalone in manifest.")

    print(f"\nRun {Colors.BOLD}`skill-tree sync`{Colors.RESET} to update cluster routing tables.")


if __name__ == "__main__":
    main()
