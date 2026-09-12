from __future__ import annotations

import os
from pathlib import Path
import uuid
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agent.skills.candidate_store import (
    InMemorySkillCandidateStore,
    PostgresSkillCandidateStore,
)
from agent.skills import (
    SkillCandidate,
    SkillFeedbackRecord,
    SkillSpec,
    SkillStatus,
)
from agent.skills.improvement_repository import (
    InMemorySkillImprovementRepository,
    PostgresSkillImprovementRepository,
    SkillUsageObservation,
    FeedbackAggregate,
    SkillImprovementRequest,
    ImprovementOutcome,
    SkillImprovementPolicyConfig,
)

_MIGRATOR_URL = os.environ.get("AGENT_TEST_MIGRATOR_DATABASE_URL")
if not _MIGRATOR_URL and os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            if line.startswith("AGENT_TEST_MIGRATOR_DATABASE_URL="):
                _MIGRATOR_URL = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

_DB_URL = os.environ.get("AGENT_TEST_DATABASE_URL")
if not _DB_URL and os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            if line.startswith("AGENT_TEST_DATABASE_URL="):
                _DB_URL = line.split("=", 1)[1].strip().strip('"').strip("'")
                break


def _candidate_policy(
    mode: str = "CANDIDATE",
    allowed_identities: frozenset[tuple[str, str, str]] | None = None,
) -> SkillImprovementPolicyConfig:
    return SkillImprovementPolicyConfig(
        mode=mode,
        allowed_identities=allowed_identities or frozenset(),
        min_feedback_samples=3,
        feedback_window_size=10,
        low_score_threshold=0.60,
        minimum_degradation_delta=0.15,
        cooldown_days=7,
        max_rounds=2,
        max_candidates_per_request=1,
    )


def _make_candidate(
    workspace_id: str = "ws-a",
    candidate_id: str = "cand-1",
    eval_score: float = 0.91,
    status: SkillStatus = SkillStatus.EVALUATED,
) -> SkillCandidate:
    spec = SkillSpec(
        id=f"skill_{candidate_id}",
        version="1.0.0",
        name="Custom Analyzer",
        description="Analyzes custom data",
        instructions="Do the analysis accurately.",
        required_capabilities=["workspace.read"],
    )
    return SkillCandidate(
        candidate_id=candidate_id,
        parent_run_id=f"run_{uuid.uuid4().hex[:8]}",
        proposed_skill=spec,
        eval_score=eval_score,
        status=status,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("repo_type", ["in_memory", "postgres"])
async def test_feedback_never_changes_candidate_evaluation_or_status(repo_type: str) -> None:
    if repo_type == "postgres" and not _DB_URL:
        pytest.skip("AGENT_TEST_DATABASE_URL not set")

    if repo_type == "in_memory":
        candidate_store = InMemorySkillCandidateStore()
        repo = InMemorySkillImprovementRepository(candidate_store=candidate_store)
    else:
        engine = create_async_engine(_DB_URL)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        candidate_store = PostgresSkillCandidateStore(session_factory)
        repo = PostgresSkillImprovementRepository(session_factory, candidate_store=candidate_store)

    candidate = _make_candidate(workspace_id="ws-a", candidate_id=f"cand_{uuid.uuid4().hex[:8]}", eval_score=0.91)
    saved_candidate = await candidate_store.save_candidate("ws-a", candidate)
    skill_id = saved_candidate.proposed_skill.id
    definition_hash = saved_candidate.definition_hash or "sha256:dummy"

    # Record observation
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    obs = SkillUsageObservation(
        observation_id=f"obs_{uuid.uuid4().hex[:8]}",
        workspace_id="ws-a",
        run_id=run_id,
        skill_id=skill_id,
        skill_version="1.0.0",
        definition_hash=definition_hash,
        root_spec_id="root_spec_1",
        root_definition_hash="sha256:root_dummy",
        created_at=datetime.now(timezone.utc),
    )
    if repo_type == "postgres":
        # We need a run row for FK in postgres if FK is enforced
        async with repo._session_factory() as session:
            from sqlalchemy import text
            await session.execute(
                text("INSERT INTO agent.runs (run_id, workspace_id, principal, root_executable_id, status) VALUES (:r, 'ws-a', 'user:test', 'exec-1', 'COMPLETED') ON CONFLICT DO NOTHING"),
                {"r": run_id}
            )
            await session.commit()

    await repo.record_resolved_skill_use(obs)

    policy = _candidate_policy(
        mode="CANDIDATE",
        allowed_identities=frozenset([(skill_id, "1.0.0", definition_hash)]),
    )

    fb = SkillFeedbackRecord(
        feedback_id=f"fb_{uuid.uuid4().hex[:8]}",
        workspace_id="ws-a",
        skill_id=skill_id,
        version="1.0.0",
        definition_hash=definition_hash,
        run_id=run_id,
        idempotency_key=f"idem_{uuid.uuid4().hex[:8]}",
        success=False,
        rating=1,
    )

    result = await repo.record_feedback_and_maybe_enqueue(feedback=fb, policy=policy)

    saved = await candidate_store.get_candidate("ws-a", candidate.candidate_id)
    assert saved is not None
    assert saved.eval_score == 0.91
    assert saved.status is SkillStatus.EVALUATED
    assert result.feedback_health in {"INSUFFICIENT_SAMPLES", "STABLE", "DEGRADING"}


@pytest.mark.asyncio
@pytest.mark.parametrize("repo_type", ["in_memory", "postgres"])
async def test_same_feedback_key_creates_one_aggregate_revision_and_one_request(repo_type: str) -> None:
    if repo_type == "postgres" and not _DB_URL:
        pytest.skip("AGENT_TEST_DATABASE_URL not set")

    if repo_type == "in_memory":
        candidate_store = InMemorySkillCandidateStore()
        repo = InMemorySkillImprovementRepository(candidate_store=candidate_store)
    else:
        engine = create_async_engine(_DB_URL)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        candidate_store = PostgresSkillCandidateStore(session_factory)
        repo = PostgresSkillImprovementRepository(session_factory, candidate_store=candidate_store)

    skill_id = f"skill_degrade_{uuid.uuid4().hex[:6]}"
    definition_hash = "sha256:degrade_hash"
    policy = _candidate_policy(
        mode="CANDIDATE",
        allowed_identities=frozenset([(skill_id, "1.0.0", definition_hash)]),
    )

    # Seed observations and 2 good feedbacks (rating=5, score=1.0)
    for i in range(2):
        run_id = f"run_seed_good_{i}_{uuid.uuid4().hex[:6]}"
        if repo_type == "postgres":
            async with repo._session_factory() as session:
                from sqlalchemy import text
                await session.execute(
                    text("INSERT INTO agent.runs (run_id, workspace_id, principal, root_executable_id, status) VALUES (:r, 'ws-a', 'user:test', 'exec-1', 'COMPLETED') ON CONFLICT DO NOTHING"),
                    {"r": run_id}
                )
                await session.commit()

        obs = SkillUsageObservation(
            observation_id=f"obs_seed_good_{i}_{uuid.uuid4().hex[:6]}",
            workspace_id="ws-a",
            run_id=run_id,
            skill_id=skill_id,
            skill_version="1.0.0",
            definition_hash=definition_hash,
            root_spec_id="root_spec_1",
            root_definition_hash="sha256:root_dummy",
            created_at=datetime.now(timezone.utc),
        )
        await repo.record_resolved_skill_use(obs)

        fb = SkillFeedbackRecord(
            feedback_id=f"fb_seed_good_{i}_{uuid.uuid4().hex[:6]}",
            workspace_id="ws-a",
            skill_id=skill_id,
            version="1.0.0",
            definition_hash=definition_hash,
            run_id=run_id,
            idempotency_key=f"idem_seed_good_{i}_{uuid.uuid4().hex[:6]}",
            success=True,
            rating=5,
        )
        await repo.record_feedback_and_maybe_enqueue(feedback=fb, policy=policy)

    # Seed 1 low feedback (rating=1, score=0.20)
    run_id_low_1 = f"run_seed_low_1_{uuid.uuid4().hex[:6]}"
    if repo_type == "postgres":
        async with repo._session_factory() as session:
            from sqlalchemy import text
            await session.execute(
                text("INSERT INTO agent.runs (run_id, workspace_id, principal, root_executable_id, status) VALUES (:r, 'ws-a', 'user:test', 'exec-1', 'COMPLETED') ON CONFLICT DO NOTHING"),
                {"r": run_id_low_1}
            )
            await session.commit()

    obs_low_1 = SkillUsageObservation(
        observation_id=f"obs_seed_low_1_{uuid.uuid4().hex[:6]}",
        workspace_id="ws-a",
        run_id=run_id_low_1,
        skill_id=skill_id,
        skill_version="1.0.0",
        definition_hash=definition_hash,
        root_spec_id="root_spec_1",
        root_definition_hash="sha256:root_dummy",
        created_at=datetime.now(timezone.utc),
    )
    await repo.record_resolved_skill_use(obs_low_1)

    fb_low_1 = SkillFeedbackRecord(
        feedback_id=f"fb_seed_low_1_{uuid.uuid4().hex[:6]}",
        workspace_id="ws-a",
        skill_id=skill_id,
        version="1.0.0",
        definition_hash=definition_hash,
        run_id=run_id_low_1,
        idempotency_key=f"idem_seed_low_1_{uuid.uuid4().hex[:6]}",
        success=False,
        rating=None,
    )
    await repo.record_feedback_and_maybe_enqueue(feedback=fb_low_1, policy=policy)

    # Now 4th feedback (score=0.0) crossing threshold: avg 0.50 <= 0.60 and delta = 0.667 - 0.50 = 0.167 >= 0.15
    run_id_low_2 = f"run_seed_low_2_{uuid.uuid4().hex[:6]}"
    if repo_type == "postgres":
        async with repo._session_factory() as session:
            from sqlalchemy import text
            await session.execute(
                text("INSERT INTO agent.runs (run_id, workspace_id, principal, root_executable_id, status) VALUES (:r, 'ws-a', 'user:test', 'exec-1', 'COMPLETED') ON CONFLICT DO NOTHING"),
                {"r": run_id_low_2}
            )
            await session.commit()

    obs_low_2 = SkillUsageObservation(
        observation_id=f"obs_seed_low_2_{uuid.uuid4().hex[:6]}",
        workspace_id="ws-a",
        run_id=run_id_low_2,
        skill_id=skill_id,
        skill_version="1.0.0",
        definition_hash=definition_hash,
        root_spec_id="root_spec_1",
        root_definition_hash="sha256:root_dummy",
        created_at=datetime.now(timezone.utc),
    )
    await repo.record_resolved_skill_use(obs_low_2)

    idem_key = f"fb-degrade-{uuid.uuid4().hex[:6]}"
    fb_degrade = SkillFeedbackRecord(
        feedback_id=f"fb_degrade_{uuid.uuid4().hex[:6]}",
        workspace_id="ws-a",
        skill_id=skill_id,
        version="1.0.0",
        definition_hash=definition_hash,
        run_id=run_id_low_2,
        idempotency_key=idem_key,
        success=False,
        rating=None,
    )

    first = await repo.record_feedback_and_maybe_enqueue(feedback=fb_degrade, policy=policy)
    assert first.feedback_health == "DEGRADING"
    assert first.improvement_disposition == "QUEUED"
    assert first.request_id is not None

    # Repeat exact same feedback with same idempotency_key
    second = await repo.record_feedback_and_maybe_enqueue(feedback=fb_degrade, policy=policy)
    assert first.feedback_id == second.feedback_id
    assert first.request_id == second.request_id

    # Verify counts
    req_count = await repo.count_requests("ws-a", skill_id=skill_id, version="1.0.0", definition_hash=definition_hash)
    assert req_count == 1
    outbox_count = await repo.count_outbox("ws-a", request_id=first.request_id)
    assert outbox_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("repo_type", ["in_memory", "postgres"])
async def test_claim_and_finish_request_fencing(repo_type: str) -> None:
    if repo_type == "postgres" and not _DB_URL:
        pytest.skip("AGENT_TEST_DATABASE_URL not set")

    if repo_type == "in_memory":
        candidate_store = InMemorySkillCandidateStore()
        repo = InMemorySkillImprovementRepository(candidate_store=candidate_store)
    else:
        engine = create_async_engine(_DB_URL)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        candidate_store = PostgresSkillCandidateStore(session_factory)
        repo = PostgresSkillImprovementRepository(session_factory, candidate_store=candidate_store)

    skill_id = f"skill_claim_{uuid.uuid4().hex[:6]}"
    definition_hash = "sha256:claim_hash"
    req_id = f"req_{uuid.uuid4().hex[:8]}"

    await repo.create_improvement_request(
        SkillImprovementRequest(
            request_id=req_id,
            workspace_id="ws-a",
            skill_id=skill_id,
            skill_version="1.0.0",
            definition_hash=definition_hash,
            trigger="feedback_degradation",
            feedback_aggregate_revision=1,
            policy_hash="sha256:policy_1",
            status="PENDING",
        )
    )

    claimed = await repo.claim_improvement_requests(worker_id="worker-1", limit=10, now=datetime.now(timezone.utc))
    matching = [c for c in claimed if c.request.request_id == req_id]
    assert len(matching) == 1
    claim_token = matching[0].claim_token

    # Finishing with wrong token must fail
    wrong_finished = await repo.finish_improvement_request(
        request_id=req_id,
        claim_token="wrong-token",
        outcome=ImprovementOutcome(status="CANDIDATE_CREATED"),
    )
    assert wrong_finished is False

    # Finishing with valid token succeeds
    ok_finished = await repo.finish_improvement_request(
        request_id=req_id,
        claim_token=claim_token,
        outcome=ImprovementOutcome(status="CANDIDATE_CREATED", candidate_id="cand-new"),
    )
    assert ok_finished is True


@pytest.mark.asyncio
@pytest.mark.parametrize("repo_type", ["in_memory", "postgres"])
async def test_workspace_idempotency_isolation(repo_type: str) -> None:
    if repo_type == "postgres" and not _DB_URL:
        pytest.skip("AGENT_TEST_DATABASE_URL not set")

    if repo_type == "in_memory":
        candidate_store = InMemorySkillCandidateStore()
        repo = InMemorySkillImprovementRepository(candidate_store=candidate_store)
    else:
        engine = create_async_engine(_DB_URL)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        candidate_store = PostgresSkillCandidateStore(session_factory)
        repo = PostgresSkillImprovementRepository(session_factory, candidate_store=candidate_store)

    skill_id = f"skill_iso_{uuid.uuid4().hex[:6]}"
    shared_key = f"shared-key-{uuid.uuid4().hex[:6]}"
    policy = _candidate_policy(mode="OBSERVE")

    # Workspace A
    run_a = f"run_a_{uuid.uuid4().hex[:6]}"
    if repo_type == "postgres":
        async with repo._session_factory() as session:
            from sqlalchemy import text
            await session.execute(
                text("INSERT INTO agent.runs (run_id, workspace_id, principal, root_executable_id, status) VALUES (:r, 'ws-a', 'user:test', 'exec-1', 'COMPLETED') ON CONFLICT DO NOTHING"),
                {"r": run_a}
            )
            await session.commit()
    await repo.record_resolved_skill_use(
        SkillUsageObservation(
            observation_id=f"obs_a_{uuid.uuid4().hex[:6]}",
            workspace_id="ws-a",
            run_id=run_a,
            skill_id=skill_id,
            skill_version="1.0.0",
            definition_hash="sha256:def_iso",
            root_spec_id="root_1",
            root_definition_hash="sha256:root_1",
        )
    )
    fb_a = SkillFeedbackRecord(
        workspace_id="ws-a",
        skill_id=skill_id,
        version="1.0.0",
        definition_hash="sha256:def_iso",
        run_id=run_a,
        idempotency_key=shared_key,
        success=True,
    )
    res_a = await repo.record_feedback_and_maybe_enqueue(feedback=fb_a, policy=policy)

    # Workspace B with same idempotency key
    run_b = f"run_b_{uuid.uuid4().hex[:6]}"
    if repo_type == "postgres":
        async with repo._session_factory() as session:
            from sqlalchemy import text
            await session.execute(
                text("INSERT INTO agent.runs (run_id, workspace_id, principal, root_executable_id, status) VALUES (:r, 'ws-b', 'user:test', 'exec-1', 'COMPLETED') ON CONFLICT DO NOTHING"),
                {"r": run_b}
            )
            await session.commit()
    await repo.record_resolved_skill_use(
        SkillUsageObservation(
            observation_id=f"obs_b_{uuid.uuid4().hex[:6]}",
            workspace_id="ws-b",
            run_id=run_b,
            skill_id=skill_id,
            skill_version="1.0.0",
            definition_hash="sha256:def_iso",
            root_spec_id="root_1",
            root_definition_hash="sha256:root_1",
        )
    )
    fb_b = SkillFeedbackRecord(
        workspace_id="ws-b",
        skill_id=skill_id,
        version="1.0.0",
        definition_hash="sha256:def_iso",
        run_id=run_b,
        idempotency_key=shared_key,
        success=True,
    )
    res_b = await repo.record_feedback_and_maybe_enqueue(feedback=fb_b, policy=policy)

    assert res_a.workspace_id == "ws-a"
    assert res_b.workspace_id == "ws-b"
    assert res_a.feedback_id != res_b.feedback_id


@pytest.mark.asyncio
@pytest.mark.parametrize("repo_type", ["in_memory", "postgres"])
async def test_current_window_calculation(repo_type: str) -> None:
    if repo_type == "postgres" and not _DB_URL:
        pytest.skip("AGENT_TEST_DATABASE_URL not set")

    if repo_type == "in_memory":
        candidate_store = InMemorySkillCandidateStore()
        repo = InMemorySkillImprovementRepository(candidate_store=candidate_store)
    else:
        engine = create_async_engine(_DB_URL)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        candidate_store = PostgresSkillCandidateStore(session_factory)
        repo = PostgresSkillImprovementRepository(session_factory, candidate_store=candidate_store)

    skill_id = f"skill_window_{uuid.uuid4().hex[:6]}"
    def_hash = "sha256:def_window"
    # window size = 3
    policy = SkillImprovementPolicyConfig(
        mode="OBSERVE",
        feedback_window_size=3,
        min_feedback_samples=2,
    )

    # Insert 5 feedbacks: first 2 are low (0.0), last 3 are high (1.0)
    for i in range(5):
        run_id = f"run_win_{i}_{uuid.uuid4().hex[:6]}"
        if repo_type == "postgres":
            async with repo._session_factory() as session:
                from sqlalchemy import text
                await session.execute(
                    text("INSERT INTO agent.runs (run_id, workspace_id, principal, root_executable_id, status) VALUES (:r, 'ws-win', 'user:test', 'exec-1', 'COMPLETED') ON CONFLICT DO NOTHING"),
                    {"r": run_id}
                )
                await session.commit()
        await repo.record_resolved_skill_use(
            SkillUsageObservation(
                observation_id=f"obs_win_{i}_{uuid.uuid4().hex[:6]}",
                workspace_id="ws-win",
                run_id=run_id,
                skill_id=skill_id,
                skill_version="1.0.0",
                definition_hash=def_hash,
                root_spec_id="root_1",
                root_definition_hash="sha256:root_1",
            )
        )
        # Ratings: first 2 are 1 (0.2), last 3 are 5 (1.0)
        rating = 1 if i < 2 else 5
        fb = SkillFeedbackRecord(
            workspace_id="ws-win",
            skill_id=skill_id,
            version="1.0.0",
            definition_hash=def_hash,
            run_id=run_id,
            idempotency_key=f"idem_win_{i}_{uuid.uuid4().hex[:6]}",
            success=(rating == 5),
            rating=rating,
        )
        res = await repo.record_feedback_and_maybe_enqueue(feedback=fb, policy=policy)

    # The latest window of 3 elements must be all rating=5 (score 1.0), excluding the old rating=1
    assert res.aggregate_score == 1.0


@pytest.mark.asyncio
@pytest.mark.parametrize("repo_type", ["in_memory", "postgres"])
async def test_outbox_claim_and_mark_delivered(repo_type: str) -> None:
    if repo_type == "postgres" and not _DB_URL:
        pytest.skip("AGENT_TEST_DATABASE_URL not set")

    if repo_type == "in_memory":
        candidate_store = InMemorySkillCandidateStore()
        repo = InMemorySkillImprovementRepository(candidate_store=candidate_store)
    else:
        engine = create_async_engine(_DB_URL)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        candidate_store = PostgresSkillCandidateStore(session_factory)
        repo = PostgresSkillImprovementRepository(session_factory, candidate_store=candidate_store)

    ws_id = f"ws_ob_{uuid.uuid4().hex[:6]}"
    req_id = f"req_ob_{uuid.uuid4().hex[:8]}"
    await repo.create_improvement_request(
        SkillImprovementRequest(
            request_id=req_id,
            workspace_id=ws_id,
            skill_id="skill-1",
            skill_version="1.0.0",
            definition_hash="sha256:def",
            trigger="feedback_degradation",
            feedback_aggregate_revision=1,
            policy_hash="sha256:p",
            status="PENDING",
        )
    )

    outbox_id = f"ob_{uuid.uuid4().hex[:8]}"
    if repo_type == "in_memory":
        from agent.skills.improvement_repository import SkillImprovementOutbox
        repo._outbox[outbox_id] = SkillImprovementOutbox(
            outbox_id=outbox_id,
            request_id=req_id,
            workspace_id=ws_id,
            state="PENDING",
            next_attempt_at=datetime.now(timezone.utc),
        )
    else:
        async with repo._session_factory() as session:
            from sqlalchemy import text
            await session.execute(
                text(
                    """
                    INSERT INTO agent.skill_improvement_outbox (
                        outbox_id, request_id, workspace_id, state, attempt_count, next_attempt_at, created_at
                    ) VALUES (
                        :ob_id, :req_id, :ws_id, 'PENDING', 0, NOW(), NOW()
                    )
                    """
                ),
                {"ob_id": outbox_id, "req_id": req_id, "ws_id": ws_id},
            )
            await session.commit()

    claimed = await repo.claim_improvement_outbox(worker_id="w-1", limit=10, now=datetime.now(timezone.utc) + timedelta(minutes=1))
    matching = [c for c in claimed if c.outbox.outbox_id == outbox_id]
    assert len(matching) == 1
    token = matching[0].claim_token

    # Marking with wrong token fails
    assert await repo.mark_outbox_delivered(outbox_id=outbox_id, claim_token="wrong", delivered_at=datetime.now(timezone.utc)) is False

    # Marking with correct token succeeds
    assert await repo.mark_outbox_delivered(outbox_id=outbox_id, claim_token=token, delivered_at=datetime.now(timezone.utc)) is True

