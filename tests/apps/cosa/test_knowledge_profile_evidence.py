from __future__ import annotations

import pytest
from agent.knowledge.snapshot import KnowledgeSnapshot
from agent.knowledge.snapshot_repository import InMemoryKnowledgeSnapshotRepository

from apps.cosa.capabilities.knowledge_read import create_knowledge_profile_read_handler


@pytest.fixture
def repo():
    return InMemoryKnowledgeSnapshotRepository()


@pytest.mark.asyncio
async def test_knowledge_profile_read_success_with_provenance(repo):
    snapshot = KnowledgeSnapshot(
        id="competitor_alpha",
        version="1.0.0",
        workspace_id="ws_1",
        embedding_model="text-embedding-3-small",
        embedding_version="1",
        source_refs=[
            {
                "source_id": "sec_1",
                "version": "1.0.0",
                "published_at": "2026-09-01T00:00:00Z",
                "fresh_until": "2026-10-01T00:00:00Z",
                "trust": "T0",
                "untrusted": False,
                "content": {"summary": "Alpha Corp is expanding SaaS."},
            }
        ],
        metadata={
            "status": "published",
            "sensitivity": "internal",
            "profile": {"company": "Alpha Corp"},
        },
    )
    await repo.publish(snapshot)

    handler = create_knowledge_profile_read_handler(snapshot_repo=repo)
    res = await handler(
        {"profile_id": "competitor_alpha", "profile_type": "competitor"},
        {"workspace_id": "ws_1"},
    )

    assert res["status"] == "AVAILABLE"
    assert res["workspace_id"] == "ws_1"
    assert res["profile_id"] == "competitor_alpha"
    assert res["sensitivity"] == "internal"
    assert res["untrusted"] is False
    assert len(res["sections"]) == 1

    sec = res["sections"][0]
    assert sec["sourceId"] == "sec_1"
    assert sec["version"] == "1.0.0"
    assert sec["publishedAt"] == "2026-09-01T00:00:00Z"
    assert sec["freshUntil"] == "2026-10-01T00:00:00Z"
    assert sec["trust"] == "T0"
    assert sec["untrusted"] is False


@pytest.mark.asyncio
async def test_knowledge_profile_preserves_untrusted_flag_when_included(repo):
    """R3 DoD Invariant: không đổi untrusted=false vì include_untrusted=true."""
    snapshot = KnowledgeSnapshot(
        id="competitor_untrusted",
        version="1.0.0",
        workspace_id="ws_1",
        embedding_model="text-embedding-3-small",
        embedding_version="1",
        source_refs=[
            {
                "source_id": "unverified_rumor",
                "version": "1.0.0",
                "published_at": "2026-09-01T00:00:00Z",
                "fresh_until": "2026-10-01T00:00:00Z",
                "trust": "untrusted",
                "untrusted": True,
                "content": {"summary": "Unverified rumor"},
            }
        ],
        metadata={"status": "published"},
    )
    await repo.publish(snapshot)

    handler = create_knowledge_profile_read_handler(snapshot_repo=repo)

    # 1. include_untrusted = False -> filtered out -> EMPTY
    res_filtered = await handler(
        {"profile_id": "competitor_untrusted", "include_untrusted": False},
        {"workspace_id": "ws_1"},
    )
    assert res_filtered["status"] == "EMPTY"
    assert len(res_filtered["sections"]) == 0

    # 2. include_untrusted = True -> included, BUT untrusted MUST REMAIN TRUE
    res_included = await handler(
        {"profile_id": "competitor_untrusted", "include_untrusted": True},
        {"workspace_id": "ws_1"},
    )
    assert res_included["status"] == "AVAILABLE"
    assert len(res_included["sections"]) == 1
    sec = res_included["sections"][0]
    assert sec["untrusted"] is True  # MUST NOT be flipped to False!
    assert res_included["untrusted"] is True


@pytest.mark.asyncio
async def test_knowledge_profile_cross_workspace_rejected(repo):
    snapshot = KnowledgeSnapshot(
        id="competitor_other_ws",
        version="1.0.0",
        workspace_id="ws_secret_other",
        embedding_model="text-embedding-3-small",
        embedding_version="1",
        source_refs=[{"source_id": "s1", "trust": "T0"}],
        metadata={"status": "published"},
    )
    await repo.publish(snapshot)

    handler = create_knowledge_profile_read_handler(snapshot_repo=repo)
    res = await handler(
        {"profile_id": "competitor_other_ws"},
        {"workspace_id": "ws_my_tenant"},
    )
    assert res["status"] == "UNAVAILABLE"
    assert "Cross-workspace" in res["message"]
    assert res["sections"] == []


@pytest.mark.asyncio
async def test_knowledge_profile_unpublished_and_expired(repo):
    # Unpublished
    unpub = KnowledgeSnapshot(
        id="competitor_draft",
        version="1.0.0",
        workspace_id="ws_1",
        embedding_model="text-embedding-3-small",
        embedding_version="1",
        source_refs=[{"source_id": "s1"}],
        metadata={"status": "unpublished"},
    )
    await repo.publish(unpub)

    # Expired
    exp = KnowledgeSnapshot(
        id="competitor_expired",
        version="1.0.0",
        workspace_id="ws_1",
        embedding_model="text-embedding-3-small",
        embedding_version="1",
        source_refs=[{"source_id": "s1"}],
        metadata={"status": "expired"},
    )
    await repo.publish(exp)

    handler = create_knowledge_profile_read_handler(snapshot_repo=repo)

    res_unpub = await handler({"profile_id": "competitor_draft"}, {"workspace_id": "ws_1"})
    assert res_unpub["status"] == "UNAVAILABLE"
    assert "not published" in res_unpub["message"]

    res_exp = await handler({"profile_id": "competitor_expired"}, {"workspace_id": "ws_1"})
    assert res_exp["status"] == "UNAVAILABLE"
    assert "expired" in res_exp["message"]


@pytest.mark.asyncio
async def test_knowledge_profile_not_found(repo):
    handler = create_knowledge_profile_read_handler(snapshot_repo=repo)
    res = await handler({"profile_id": "non_existent_id"}, {"workspace_id": "ws_1"})
    assert res["status"] == "UNAVAILABLE"
    assert "not found" in res["message"]
    assert "non_existent_id" in res["missing_sources"]


@pytest.mark.asyncio
async def test_knowledge_profile_missing_workspace_raises(repo):
    handler = create_knowledge_profile_read_handler(snapshot_repo=repo)
    with pytest.raises(ValueError, match="thiếu workspace_id"):
        await handler({"profile_id": "comp_1"}, {})
