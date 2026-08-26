from __future__ import annotations

from agent_core.governance.contracts import PinnedSpecIdentity
from agent_core.knowledge.snapshot import KnowledgeSnapshot


def _base_kwargs() -> dict:
    return dict(
        id="workspace-abc.default_kb",
        workspace_id="workspace-abc",
        embedding_model="text-embedding-3-small",
        embedding_version="1",
        source_refs=[{"source_id": "src_1", "version": 2, "content_hash": "a" * 64}],
    )


def test_knowledge_snapshot_has_sensible_defaults():
    snapshot = KnowledgeSnapshot(**_base_kwargs())

    assert snapshot.version == "1.0.0"
    assert snapshot.chunking_recipe_version == "1.0"
    assert snapshot.index_recipe_version == "1.0"
    assert snapshot.retrieval_eval_run_id is None
    assert snapshot.definition_hash is None


def test_knowledge_snapshot_compute_hash_is_deterministic():
    a = KnowledgeSnapshot(**_base_kwargs())
    b = KnowledgeSnapshot(**_base_kwargs())

    assert a.compute_hash() == b.compute_hash()


def test_knowledge_snapshot_compute_hash_ignores_source_refs_order():
    kwargs = _base_kwargs()
    kwargs["source_refs"] = [
        {"source_id": "src_1", "version": 1, "content_hash": "a" * 64},
        {"source_id": "src_2", "version": 1, "content_hash": "b" * 64},
    ]
    a = KnowledgeSnapshot(**kwargs)

    kwargs_reordered = dict(kwargs)
    kwargs_reordered["source_refs"] = list(reversed(kwargs["source_refs"]))
    b = KnowledgeSnapshot(**kwargs_reordered)

    assert a.compute_hash() == b.compute_hash()


def test_knowledge_snapshot_compute_hash_changes_when_source_content_hash_changes():
    kwargs_a = _base_kwargs()
    kwargs_b = _base_kwargs()
    kwargs_b["source_refs"] = [{"source_id": "src_1", "version": 2, "content_hash": "f" * 64}]

    a = KnowledgeSnapshot(**kwargs_a)
    b = KnowledgeSnapshot(**kwargs_b)

    assert a.compute_hash() != b.compute_hash()


def test_knowledge_snapshot_compute_hash_changes_when_embedding_version_changes():
    kwargs_a = _base_kwargs()
    kwargs_b = _base_kwargs()
    kwargs_b["embedding_version"] = "2"

    a = KnowledgeSnapshot(**kwargs_a)
    b = KnowledgeSnapshot(**kwargs_b)

    assert a.compute_hash() != b.compute_hash()


def test_knowledge_snapshot_with_hash_returns_a_copy_with_definition_hash_set():
    snapshot = KnowledgeSnapshot(**_base_kwargs())

    pinned = snapshot.with_hash()

    assert snapshot.definition_hash is None
    assert pinned.definition_hash == snapshot.compute_hash()


def test_knowledge_snapshot_to_pinned_identity_uses_knowledge_snapshot_kind():
    snapshot = KnowledgeSnapshot(version="3", **_base_kwargs()).with_hash()

    identity = snapshot.to_pinned_identity()

    assert identity == PinnedSpecIdentity(
        spec_kind="knowledge_snapshot",
        spec_id="workspace-abc.default_kb",
        spec_version="3",
        definition_hash=snapshot.definition_hash,
    )
