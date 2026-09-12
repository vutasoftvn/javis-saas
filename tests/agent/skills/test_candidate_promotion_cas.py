from __future__ import annotations

import os
from pathlib import Path
import uuid
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agent.skills.candidate_store import (
    InMemorySkillCandidateStore,
    PostgresSkillCandidateStore,
)
from agent.skills.contracts import (
    SkillCandidate,
    SkillSpec,
    SkillStatus,
)

_MIGRATOR_URL = os.environ.get("AGENT_TEST_MIGRATOR_DATABASE_URL")
if not _MIGRATOR_URL and os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            if line.startswith("AGENT_TEST_MIGRATOR_DATABASE_URL="):
                _MIGRATOR_URL = line.split("=", 1)[1].strip().strip('"').strip("'")
                break


def _make_candidate(
    workspace_id: str = "ws-1",
    candidate_id: str = "cand-1",
    status: SkillStatus = SkillStatus.EVALUATED,
    eval_score: float = 0.95,
) -> SkillCandidate:
    spec = SkillSpec(
        id=f"skill_{candidate_id}",
        version="1.0.0",
        name="Custom Analyzer",
        description="Analyzes custom data",
        instructions="Do the analysis accurately.",
        required_capabilities=["workspace.read"],
    )
    cand = SkillCandidate(
        candidate_id=candidate_id,
        parent_run_id=f"run_{uuid.uuid4().hex[:8]}",
        proposed_skill=spec,
        eval_score=eval_score,
        status=status,
    )
    return cand


@pytest.mark.asyncio
async def test_in_memory_save_computes_definition_hash() -> None:
    store = InMemorySkillCandidateStore()
    cand = _make_candidate()
    assert cand.definition_hash is None

    saved = await store.save_candidate("ws-1", cand)
    assert saved.definition_hash is not None
    assert saved.definition_hash.startswith("sha256:")
    assert saved.definition_hash == f"sha256:{cand.proposed_skill.compute_hash()}"


@pytest.mark.asyncio
async def test_in_memory_publish_candidate_cas_flow() -> None:
    store = InMemorySkillCandidateStore()
    cand = _make_candidate(status=SkillStatus.EVALUATED)
    saved = await store.save_candidate("ws-1", cand)
    def_hash = saved.definition_hash
    assert def_hash is not None

    approval_id = "appr_123"

    # 1. Success CAS publish
    ok, reason, published = await store.publish_candidate_if_approved(
        "ws-1", cand.candidate_id, approval_id, def_hash
    )
    assert ok is True
    assert reason == "PUBLISHED"
    assert published is not None
    assert published.status == SkillStatus.PUBLISHED
    assert published.promotion_approval_id == approval_id
    assert published.promotion_definition_hash == def_hash

    # 2. Idempotent replay with same approval and hash
    ok, reason, replayed = await store.publish_candidate_if_approved(
        "ws-1", cand.candidate_id, approval_id, def_hash
    )
    assert ok is True
    assert reason == "ALREADY_PUBLISHED"
    assert replayed is not None
    assert replayed.status == SkillStatus.PUBLISHED

    # 3. Refuses different approval when already published
    ok, reason, refused = await store.publish_candidate_if_approved(
        "ws-1", cand.candidate_id, "appr_DIFFERENT", def_hash
    )
    assert ok is False
    assert reason == "ALREADY_PUBLISHED_DIFFERENT_APPROVAL"


@pytest.mark.asyncio
async def test_in_memory_publish_refuses_stale_hash_or_unevaluated() -> None:
    store = InMemorySkillCandidateStore()

    # Stale hash
    cand = _make_candidate(status=SkillStatus.EVALUATED)
    saved = await store.save_candidate("ws-1", cand)
    ok, reason, _ = await store.publish_candidate_if_approved(
        "ws-1", cand.candidate_id, "appr_1", "sha256:stale_hash_value"
    )
    assert ok is False
    assert reason == "APPROVAL_SUBJECT_STALE"

    # Unevaluated candidate
    cand_uneval = _make_candidate(candidate_id="cand-2", status=SkillStatus.CANDIDATE)
    saved_uneval = await store.save_candidate("ws-1", cand_uneval)
    ok, reason, _ = await store.publish_candidate_if_approved(
        "ws-1", cand_uneval.candidate_id, "appr_1", saved_uneval.definition_hash
    )
    assert ok is False
    assert reason == "CANDIDATE_NOT_EVALUATED"


@pytest.mark.skipif(not _MIGRATOR_URL, reason="AGENT_TEST_MIGRATOR_DATABASE_URL not set")
@pytest.mark.asyncio
async def test_postgres_publish_candidate_cas_flow() -> None:
    engine = create_async_engine(_MIGRATOR_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    store = PostgresSkillCandidateStore(session_factory)

    cid = f"cand_{uuid.uuid4().hex[:8]}"
    cand = _make_candidate(candidate_id=cid, status=SkillStatus.EVALUATED)
    saved = await store.save_candidate("ws-pg-1", cand)
    assert saved.definition_hash is not None

    approval_id = f"appr_{uuid.uuid4().hex[:8]}"

    # Stale hash rejected
    ok, reason, _ = await store.publish_candidate_if_approved(
        "ws-pg-1", cid, approval_id, "sha256:wrong_hash"
    )
    assert ok is False
    assert reason == "APPROVAL_SUBJECT_STALE"

    # Successful CAS publish
    ok, reason, published = await store.publish_candidate_if_approved(
        "ws-pg-1", cid, approval_id, saved.definition_hash
    )
    assert ok is True
    assert reason == "PUBLISHED"
    assert published is not None
    assert published.status == SkillStatus.PUBLISHED
    assert published.promotion_approval_id == approval_id
    assert published.promotion_definition_hash == saved.definition_hash

    # Idempotent replay
    ok, reason, replayed = await store.publish_candidate_if_approved(
        "ws-pg-1", cid, approval_id, saved.definition_hash
    )
    assert ok is True
    assert reason == "ALREADY_PUBLISHED"

    # Different approval rejected
    ok, reason, diff = await store.publish_candidate_if_approved(
        "ws-pg-1", cid, "appr_DIFFERENT", saved.definition_hash
    )
    assert ok is False
    assert reason == "ALREADY_PUBLISHED_DIFFERENT_APPROVAL"

    await engine.dispose()
