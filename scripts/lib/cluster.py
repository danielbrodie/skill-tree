"""TF-IDF vectorization + agglomerative clustering for skill organization.

Uses scikit-learn for TF-IDF and hierarchical clustering.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .skillfile import get_description, get_name, parse_frontmatter


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MIN_CLUSTER_SIZE = 3
MAX_CLUSTER_SIZE = 15
DEFAULT_THRESHOLD = 0.7  # distance threshold (1 - similarity)


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SkillDocument:
    """A skill's text content for clustering."""

    name: str
    description: str
    body_preview: str  # first ~500 words of body


@dataclass
class ProposedCluster:
    """A cluster proposal from the clustering algorithm."""

    label: str
    description: str
    members: list[SkillDocument]
    distinctive_terms: list[str]


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------


def extract_skill_document(skillmd_path: Path) -> SkillDocument | None:
    """Extract text content from a SKILL.md for clustering."""
    fm = parse_frontmatter(skillmd_path)
    name = get_name(fm) or skillmd_path.parent.name
    description = get_description(fm) or ""

    # Extract body (after frontmatter)
    if fm.has_frontmatter and fm.end_line < len(fm.raw_lines):
        body_lines = fm.raw_lines[fm.end_line + 1 :]
    else:
        body_lines = fm.raw_lines

    # Take first ~500 words of body, skip empty lines
    body_words: list[str] = []
    for line in body_lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            # Keep headings as content (good signal)
            body_words.extend(stripped.lstrip("#").strip().split())
        elif stripped:
            body_words.extend(stripped.split())
        if len(body_words) >= 500:
            break

    body_preview = " ".join(body_words[:500])

    if not description and not body_preview:
        return None

    return SkillDocument(name=name, description=description, body_preview=body_preview)


def _build_document_text(doc: SkillDocument) -> str:
    """Combine skill fields into a single text for TF-IDF.

    Weight: name (3x), description (2x), body (1x).
    """
    parts: list[str] = []
    # Repeat name for higher weight
    name_text = doc.name.replace("-", " ")
    parts.extend([name_text] * 3)
    # Repeat description for moderate weight
    if doc.description:
        parts.extend([doc.description] * 2)
    # Body at base weight
    if doc.body_preview:
        parts.append(doc.body_preview)
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Clustering
# ---------------------------------------------------------------------------


def cluster_skills(
    documents: list[SkillDocument],
    distance_threshold: float = DEFAULT_THRESHOLD,
) -> tuple[list[ProposedCluster], list[SkillDocument]]:
    """Cluster skill documents using TF-IDF + agglomerative clustering.

    Returns (clusters, standalones).
    """
    if len(documents) < 2:
        return [], list(documents)

    # Build TF-IDF matrix
    texts = [_build_document_text(doc) for doc in documents]
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),  # unigrams + bigrams
        max_features=5000,
        stop_words="english",
        min_df=1,
        max_df=0.95,
    )
    tfidf_matrix = vectorizer.fit_transform(texts)
    feature_names = vectorizer.get_feature_names_out()

    # Agglomerative clustering
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=distance_threshold,
        metric="cosine",
        linkage="average",
    )
    labels = clustering.fit_predict(tfidf_matrix.toarray())

    # Group documents by label
    label_to_docs: dict[int, list[int]] = {}
    for idx, label in enumerate(labels):
        label_to_docs.setdefault(label, []).append(idx)

    clusters: list[ProposedCluster] = []
    standalones: list[SkillDocument] = []

    for label, indices in sorted(label_to_docs.items()):
        members = [documents[i] for i in indices]

        if len(members) < MIN_CLUSTER_SIZE:
            standalones.extend(members)
            continue

        # Handle oversized clusters by subdivision
        if len(members) > MAX_CLUSTER_SIZE:
            sub_clusters, sub_standalones = _subdivide(
                members, tfidf_matrix, indices, vectorizer, feature_names
            )
            clusters.extend(sub_clusters)
            standalones.extend(sub_standalones)
            continue

        # Extract distinctive terms for this cluster
        distinctive = _distinctive_terms(
            tfidf_matrix, indices, list(range(len(documents))), feature_names
        )

        # Generate label from distinctive terms
        cluster_label = _generate_label(members, distinctive)
        description = _generate_description(members, distinctive)

        clusters.append(
            ProposedCluster(
                label=cluster_label,
                description=description,
                members=members,
                distinctive_terms=distinctive[:5],
            )
        )

    return clusters, standalones


def _subdivide(
    members: list[SkillDocument],
    full_matrix,
    indices: list[int],
    vectorizer,
    feature_names,
) -> tuple[list[ProposedCluster], list[SkillDocument]]:
    """Subdivide an oversized cluster into smaller ones."""
    sub_texts = [_build_document_text(doc) for doc in members]
    sub_matrix = vectorizer.transform(sub_texts)

    # Target ~8-12 members per sub-cluster
    n_target = max(2, len(members) // 10)
    # But ensure we actually break it up enough
    n_target = max(n_target, (len(members) + MAX_CLUSTER_SIZE - 1) // MAX_CLUSTER_SIZE)

    sub_clustering = AgglomerativeClustering(
        n_clusters=n_target,
        metric="cosine",
        linkage="average",
    )
    sub_labels = sub_clustering.fit_predict(sub_matrix.toarray())

    sub_groups: dict[int, list[int]] = {}
    for idx, label in enumerate(sub_labels):
        sub_groups.setdefault(label, []).append(idx)

    clusters: list[ProposedCluster] = []
    standalones: list[SkillDocument] = []
    seen_labels: set[str] = set()

    for sub_label, sub_indices in sub_groups.items():
        sub_members = [members[i] for i in sub_indices]
        if len(sub_members) < MIN_CLUSTER_SIZE:
            standalones.extend(sub_members)
            continue

        # Recursively subdivide if still too large
        if len(sub_members) > MAX_CLUSTER_SIZE:
            deeper_clusters, deeper_standalones = _subdivide(
                sub_members, full_matrix,
                [indices[i] for i in sub_indices],
                vectorizer, feature_names,
            )
            clusters.extend(deeper_clusters)
            standalones.extend(deeper_standalones)
            continue

        distinctive = _distinctive_terms(
            sub_matrix, sub_indices, list(range(len(members))), feature_names
        )
        cluster_label = _generate_label(sub_members, distinctive)

        # Ensure unique labels
        base_label = cluster_label
        counter = 2
        while cluster_label in seen_labels:
            cluster_label = f"{base_label}-{counter}"
            counter += 1
        seen_labels.add(cluster_label)

        description = _generate_description(sub_members, distinctive)

        clusters.append(
            ProposedCluster(
                label=cluster_label,
                description=description,
                members=sub_members,
                distinctive_terms=distinctive[:5],
            )
        )

    return clusters, standalones


# ---------------------------------------------------------------------------
# Label & description generation
# ---------------------------------------------------------------------------


def _distinctive_terms(
    tfidf_matrix,
    cluster_indices: list[int],
    all_indices: list[int],
    feature_names,
    top_n: int = 10,
) -> list[str]:
    """Find terms most distinctive to this cluster vs all others."""
    cluster_mean = np.asarray(tfidf_matrix[cluster_indices].mean(axis=0)).flatten()
    other_indices = [i for i in all_indices if i not in cluster_indices]

    if other_indices:
        other_mean = np.asarray(tfidf_matrix[other_indices].mean(axis=0)).flatten()
    else:
        other_mean = np.zeros_like(cluster_mean)

    # Score = cluster frequency - global frequency (higher = more distinctive)
    scores = cluster_mean - other_mean
    top_indices = scores.argsort()[-top_n:][::-1]

    return [feature_names[i] for i in top_indices if scores[i] > 0]


def _generate_label(members: list[SkillDocument], distinctive_terms: list[str]) -> str:
    """Generate a kebab-case cluster label from distinctive terms."""
    if not distinctive_terms:
        # Fallback: use most common name component
        name_parts: list[str] = []
        for m in members:
            name_parts.extend(m.name.split("-"))
        if name_parts:
            from collections import Counter
            common = Counter(name_parts).most_common(2)
            return "-".join(w for w, _ in common)
        return "cluster"

    # Use first 1-2 distinctive terms
    label_parts = distinctive_terms[:2]
    label = "-".join(t.replace(" ", "-") for t in label_parts)
    # Clean up
    label = label.lower().strip("-")
    return label


def _generate_description(
    members: list[SkillDocument], distinctive_terms: list[str]
) -> str:
    """Generate a cluster description from member descriptions and distinctive terms."""
    # Collect key phrases from member descriptions
    desc_fragments: list[str] = []
    for m in members[:5]:  # sample first 5
        if m.description:
            # Take first sentence or phrase
            first_part = m.description.split(".")[0].split("—")[0].strip()
            if first_part and len(first_part) < 100:
                desc_fragments.append(first_part)

    if desc_fragments:
        summary = ", ".join(desc_fragments[:3])
    elif distinctive_terms:
        summary = ", ".join(distinctive_terms[:3])
    else:
        summary = "grouped skills"

    return summary
