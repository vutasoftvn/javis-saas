from __future__ import annotations

import pytest

from agent_core.evals.promotion import PromotionEvidence
from agent_core.evals.promotion_repository import InMemoryPromotionEvidenceRepository
from agent_core.governance.contracts import PinnedSpecIdentity


def _target_ref(hash_suffix: str = "a") -> PinnedSpecIdentity:
    return PinnedSpecIdentity(
        spec_kind="agent", spec_id="cofounder", spec_version="17", definition_hash=hash_suffix * 64
    )


@pytest.mark.asyncio
async def test_create_and_get_evidence_roundtrip():
    repo = InMemoryPromotionEvidenceRepository()
    evidence = PromotionEvidence(
        target_ref=_target_ref(),
        required_eval_run_ids=["evalrun_1"],
        observed_fingerprints={"cofounder": "a" * 64},
        policy_version="1",
        policy_checks_passed=True,
    )

    created = await repo.create(evidence)
    fetched = await repo.get(created.evidence_id)

    assert fetched is not None
    assert fetched.evidence_id == created.evidence_id
    assert fetched.observed_fingerprints == {"cofounder": "a" * 64}


@pytest.mark.asyncio
async def test_get_returns_none_when_not_found():
    repo = InMemoryPromotionEvidenceRepository()

    result = await repo.get("does_not_exist")

    assert result is None


@pytest.mark.asyncio
async def test_list_by_target_returns_only_matching_target():
    repo = InMemoryPromotionEvidenceRepository()
    matching = PromotionEvidence(target_ref=_target_ref("a"), policy_version="1", policy_checks_passed=True)
    other = PromotionEvidence(target_ref=_target_ref("f"), policy_version="1", policy_checks_passed=True)
    await repo.create(matching)
    await repo.create(other)

    results = await repo.list_by_target(_target_ref("a"))

    assert len(results) == 1
    assert results[0].evidence_id == matching.evidence_id


import os

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agent_core.evals.promotion_repository import PostgresPromotionEvidenceRepository


def _pg_session_factory():
    url = os.environ.get(
        "AGENT_CORE_DATABASE_URL",
        "postgresql+asyncpg://javis_app:CHANGE_ME@localhost:5432/javis",
    )
    engine = create_async_engine(url)
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.mark.asyncio
async def test_postgres_promotion_evidence_repository_roundtrip():
    repo = PostgresPromotionEvidenceRepository(_pg_session_factory())
    evidence = PromotionEvidence(
        target_ref=_target_ref("d"),
        required_eval_run_ids=["evalrun_pg_1"],
        observed_fingerprints={"cofounder": "d" * 64},
        policy_version="1",
        policy_checks_passed=True,
        check_details={"pass_rate_threshold": 0.8},
    )

    created = await repo.create(evidence)
    fetched = await repo.get(created.evidence_id)
    listed = await repo.list_by_target(_target_ref("d"))

    assert fetched is not None
    assert fetched.observed_fingerprints == {"cofounder": "d" * 64}
    assert fetched.required_eval_run_ids == ["evalrun_pg_1"]
    assert any(e.evidence_id == created.evidence_id for e in listed)

