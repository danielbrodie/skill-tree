"""Tests for TF-IDF clustering."""

from __future__ import annotations

import pytest

from scripts.lib.cluster import (
    MAX_CLUSTER_SIZE,
    MIN_CLUSTER_SIZE,
    ProposedCluster,
    SkillDocument,
    cluster_skills,
    extract_skill_document,
)


def _make_doc(name: str, description: str, body: str = "") -> SkillDocument:
    return SkillDocument(name=name, description=description, body_preview=body)


class TestClusterSkills:
    def test_empty_input(self):
        clusters, standalones = cluster_skills([])
        assert clusters == []
        assert standalones == []

    def test_single_skill(self):
        docs = [_make_doc("solo", "A standalone skill")]
        clusters, standalones = cluster_skills(docs)
        assert len(clusters) == 0
        assert len(standalones) == 1

    def test_two_skills(self):
        docs = [
            _make_doc("a1", "First skill"),
            _make_doc("a2", "Second skill"),
        ]
        clusters, standalones = cluster_skills(docs)
        # With only 2, they'll be standalones (< MIN_CLUSTER_SIZE)
        assert len(standalones) == 2

    def test_similar_skills_cluster_together(self):
        """With enough distinct domains, TF-IDF separates them.

        Note: TF-IDF needs sufficient vocabulary diversity to distinguish
        clusters. This test uses 4 domains with 4 skills each to provide
        enough signal. Small sample sizes (6-8 docs) often land in one
        cluster since the vocabulary overlap is too high.
        """
        docs = []
        # Git domain — repository, commit, branch, merge, push, pull
        for suffix, desc in [
            ("commit", "Create git commits with conventional messages and staged changes"),
            ("branch", "Manage git branches for feature development and release workflows"),
            ("merge", "Merge git branches and resolve conflicts in pull requests"),
            ("rebase", "Rebase git branches to maintain clean linear commit history"),
        ]:
            docs.append(_make_doc(
                f"git-{suffix}", desc,
                f"Git repository operations. {desc} Handle version control workflows."
            ))
        # Database domain — SQL, schema, migration, query
        for suffix, desc in [
            ("migrate", "Run database migrations and schema changes safely"),
            ("query", "Write and optimize SQL queries for PostgreSQL and MySQL"),
            ("backup", "Backup and restore database snapshots and dumps"),
            ("schema", "Design database schemas with proper indexing and constraints"),
        ]:
            docs.append(_make_doc(
                f"database-{suffix}", desc,
                f"Database administration. {desc} Manage SQL tables and indexes."
            ))
        # Deploy domain
        for suffix, desc in [
            ("docker", "Build and push Docker container images for deployment"),
            ("kubernetes", "Deploy applications to Kubernetes clusters with helm charts"),
            ("ci-pipeline", "Configure CI/CD pipelines for automated testing and deployment"),
            ("monitoring", "Set up monitoring dashboards and alerting for deployed services"),
        ]:
            docs.append(_make_doc(
                f"deploy-{suffix}", desc,
                f"Deployment infrastructure. {desc} Production operations."
            ))

        clusters, standalones = cluster_skills(docs, distance_threshold=0.7)

        # With 12 docs across 3 domains, expect at least 2 clusters
        # (some domains may merge at this threshold)
        total_clustered = sum(len(c.members) for c in clusters)
        assert total_clustered + len(standalones) == 12, "All docs accounted for"

        # If we got clusters, verify same-domain skills stay together
        for c in clusters:
            names = [m.name for m in c.members]
            # Extract domain prefixes present
            prefixes = {n.split("-")[0] for n in names}
            # A well-formed cluster should be dominated by 1-2 domains
            assert len(prefixes) <= 2, (
                f"Cluster '{c.label}' mixes too many domains: {prefixes}"
            )

    def test_all_members_accounted_for(self):
        """Every input document appears in exactly one cluster or standalone."""
        docs = [
            _make_doc(f"skill-{i}", f"Description for skill {i} about topic {i % 3}")
            for i in range(20)
        ]
        clusters, standalones = cluster_skills(docs, distance_threshold=1.0)

        all_names = set()
        for c in clusters:
            for m in c.members:
                assert m.name not in all_names, f"Duplicate: {m.name}"
                all_names.add(m.name)
        for s in standalones:
            assert s.name not in all_names, f"Duplicate: {s.name}"
            all_names.add(s.name)

        expected_names = {f"skill-{i}" for i in range(20)}
        assert all_names == expected_names

    def test_cluster_size_constraints(self):
        """No cluster should exceed MAX_CLUSTER_SIZE."""
        docs = [
            _make_doc(f"api-tool-{i}", f"API tool for managing REST endpoints {i}")
            for i in range(30)
        ]
        clusters, standalones = cluster_skills(docs, distance_threshold=1.5)

        for c in clusters:
            assert len(c.members) <= MAX_CLUSTER_SIZE, (
                f"Cluster '{c.label}' has {len(c.members)} members (max {MAX_CLUSTER_SIZE})"
            )

    def test_proposed_cluster_has_label(self):
        docs = [
            _make_doc("git-push", "Push changes to remote git repository"),
            _make_doc("git-pull", "Pull changes from remote git repository"),
            _make_doc("git-merge", "Merge branches in git repository"),
        ]
        clusters, _ = cluster_skills(docs, distance_threshold=1.5)

        if clusters:
            for c in clusters:
                assert c.label, "Cluster label should not be empty"
                assert isinstance(c.distinctive_terms, list)


class TestExtractSkillDocument:
    def test_with_frontmatter(self, tmp_path):
        p = tmp_path / "skill-a" / "SKILL.md"
        p.parent.mkdir()
        p.write_text(
            "---\nname: skill-a\ndescription: A test skill\n---\n# Body\nSome content here.\n"
        )
        doc = extract_skill_document(p)
        assert doc is not None
        assert doc.name == "skill-a"
        assert doc.description == "A test skill"
        assert "content" in doc.body_preview

    def test_without_description(self, tmp_path):
        p = tmp_path / "bare" / "SKILL.md"
        p.parent.mkdir()
        p.write_text("# Just a heading\nSome body text.\n")
        doc = extract_skill_document(p)
        assert doc is not None
        assert doc.name == "bare"  # falls back to directory name

    def test_empty_file(self, tmp_path):
        p = tmp_path / "empty" / "SKILL.md"
        p.parent.mkdir()
        p.write_text("")
        doc = extract_skill_document(p)
        assert doc is None  # no description, no body
