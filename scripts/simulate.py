"""Simulate skill routing modes against the corpus from measure.py.

For each (prompt, invoked_skill) record, ask: was the right skill REACHABLE under
each mode? Reachability is binary — the skill was either visible/findable in the
mode's prelude assembly, or it wasn't.

This is a coarser proxy than "did the model pick the right skill?" — that would
require running the model. Reachability is the necessary condition: if a skill
is unreachable, the model can't pick it regardless of how good its routing is.

Modes:
- flat:        every skill is always visible. Reachability == always 1.0. Cost: full prelude.
- cluster:     skill is reachable iff it's in a cluster (then the model navigates) or it's
               a standalone in the manifest. Cost: ~cluster-descriptions sum.
- per-project (naive): skill is reachable iff it's among the project's top-N invoked skills,
               where N is the per-project budget. Cost: ~N skill descriptions per project.

Outputs a markdown table.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Reuse measure.py's corpus builder.
from measure import build_corpus, CorpusRecord  # noqa: E402
from provision import collect_global_catalog  # noqa: E402


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text())


def cluster_membership(manifest: dict) -> dict[str, str]:
    """name -> cluster name (or '' if unclustered)."""
    out: dict[str, str] = {}
    for cluster_name, cluster in manifest.get("clusters", {}).items():
        for leaf in cluster.get("leaves", {}):
            out[leaf] = cluster_name
    for s in manifest.get("standalones", []):
        out[s] = ""
    return out


def normalize_skill_name(skill: str) -> str:
    """Strip plugin-namespace prefix: `superpowers:writing-plans` -> `writing-plans`."""
    return skill.split(":", 1)[-1]


def cluster_reach(records: list[CorpusRecord], manifest: dict) -> float:
    """% of records whose invoked skill is reachable via the cluster manifest."""
    membership = cluster_membership(manifest)
    hits = 0
    for r in records:
        name = normalize_skill_name(r.skill)
        if name in membership:
            hits += 1
    return hits / len(records) if records else 0.0


def per_project_naive_reach(records: list[CorpusRecord], budget: int) -> float:
    """% reachable if each project provisions its top-`budget` historically-invoked skills.

    Uses leave-one-out: for each record, build the project's top-N from the OTHER
    records in that project, then check if the held-out record's skill is in the top-N.
    This avoids the trivial "everything ever invoked is reachable" tautology.
    """
    by_project: dict[str, list[CorpusRecord]] = defaultdict(list)
    for r in records:
        by_project[r.project_dir].append(r)

    hits = 0
    total = 0
    for project, recs in by_project.items():
        for i, held_out in enumerate(recs):
            others = recs[:i] + recs[i + 1 :]
            top_n = {s for s, _ in Counter(o.skill for o in others).most_common(budget)}
            total += 1
            if held_out.skill in top_n:
                hits += 1
    return hits / total if total else 0.0


def estimate_prelude_tokens(manifest: dict, skill_descriptions: dict[str, str]) -> dict[str, int]:
    """Rough token estimate (chars/4) for each mode's prelude."""

    def tok(s: str) -> int:
        return max(1, len(s) // 4)

    # flat = sum of all skill descriptions
    flat = sum(tok(desc) for desc in skill_descriptions.values())
    # cluster = sum of cluster descriptions + standalones' descriptions
    cluster = 0
    for c in manifest.get("clusters", {}).values():
        cluster += tok(c.get("description", ""))
    for s in manifest.get("standalones", []):
        cluster += tok(skill_descriptions.get(s, ""))
    # per-project (naive top-N) = N skill descriptions, average per project
    return {"flat": flat, "cluster": cluster}


def scan_skill_descriptions(skills_dir: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for skill_dir in skills_dir.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        try:
            text = skill_md.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        in_fm = False
        for line in text.splitlines():
            if line.strip() == "---":
                if not in_fm:
                    in_fm = True
                    continue
                break
            if in_fm and line.startswith("description:"):
                out[skill_dir.name] = line.split(":", 1)[1].strip().strip('"')
                break
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument(
        "--manifest",
        default=str(Path.home() / ".claude" / "skills-library" / "skill-tree" / "manifest.json"),
    )
    parser.add_argument(
        "--projects-root", default=str(Path.home() / ".claude" / "projects")
    )
    parser.add_argument(
        "--skills-dir", default=str(Path.home() / ".claude" / "skills")
    )
    parser.add_argument("--budget", type=int, default=5, help="Per-project provisioning N")
    args = parser.parse_args()

    records = build_corpus(Path(args.projects_root), args.days)
    manifest = load_manifest(Path(args.manifest))
    descriptions = scan_skill_descriptions(Path(args.skills_dir))

    # Expanded catalog: personal + plugin (BRO-184). A "flat" mode that doesn't
    # include plugin skills can't reach 100% of invocations — that was the
    # artifact in BRO-180's first baseline.
    catalog = collect_global_catalog(Path(args.skills_dir))
    catalog_names = {c["name"] for c in catalog}

    flat_reach = sum(1 for r in records if r.skill in catalog_names) / len(records) if records else 0.0
    cluster_r = cluster_reach(records, manifest)
    pp_reach = per_project_naive_reach(records, args.budget)

    tokens = estimate_prelude_tokens(manifest, descriptions)

    # Recompute flat-mode prelude token cost from the expanded catalog
    flat_full = sum(max(1, len(c.get("description", "")) // 4) for c in catalog)

    print(f"# Baseline — {len(records)} records, last {args.days} days\n")
    print(f"Catalog: {len(catalog_names)} skills ({sum(1 for c in catalog if c.get('origin') == 'personal')} personal, {sum(1 for c in catalog if (c.get('origin') or '').startswith('plugin:'))} plugin)\n")
    print(f"Per-project budget N = {args.budget}\n")
    print("| Mode | Reach@catalog | Prelude tokens |")
    print("|---|---|---|")
    print(f"| flat (full catalog) | {flat_reach:.2%} | ~{flat_full:,} |")
    print(f"| cluster (current global manifest) | {cluster_r:.2%} | ~{tokens['cluster']:,} |")
    print(f"| per-project naive top-{args.budget} (LOO) | {pp_reach:.2%} | ~{args.budget * (flat_full // max(1, len(catalog_names))):,} (per project avg) |")
    print()
    print("Reach@catalog = fraction of invocations whose skill was in the mode's catalog.")
    print("Prelude tokens = chars/4 of always-on prompt fragments.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
