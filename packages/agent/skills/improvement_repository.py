from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent.skills.candidate_store import SkillCandidateStore, SkillFeedbackRecord

SkillIdentity = tuple[str, str, str]  # (skill_id, version, definition_hash)


class SkillUsageObservation(BaseModel):
    observation_id: str = Field(default_factory=lambda: f"obs_{uuid.uuid4().hex[:12]}")
    workspace_id: str
    run_id: str
    skill_id: str
    skill_version: str
    definition_hash: str
    root_spec_id: str
    root_definition_hash: str
    project_id: str | None = None
    manifest_hash: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class FeedbackAggregate(BaseModel):
    workspace_id: str
    skill_id: str
    skill_version: str
    definition_hash: str
    revision: int
    sample_count: int
    aggregate_score: float
    previous_score: float | None = None
    degradation_delta: float | None = None
    window_started_at: datetime
    window_ended_at: datetime
    health: Literal["INSUFFICIENT_SAMPLES", "STABLE", "DEGRADING"]
    project_id: str | None = None
    manifest_hash: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SkillImprovementRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: f"sir_{uuid.uuid4().hex[:12]}")
    workspace_id: str
    skill_id: str
    skill_version: str
    definition_hash: str
    trigger: Literal["feedback_degradation"] = "feedback_degradation"
    feedback_aggregate_revision: int
    policy_hash: str
    status: str = "PENDING"
    attempt_count: int = 0
    claim_token: str | None = None
    claimed_by: str | None = None
    claimed_at: datetime | None = None
    safe_reason_code: str | None = None
    project_id: str | None = None
    manifest_hash: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ClaimedSkillImprovementRequest(BaseModel):
    request: SkillImprovementRequest
    claim_token: str


class SkillImprovementOutbox(BaseModel):
    outbox_id: str = Field(default_factory=lambda: f"outbox_{uuid.uuid4().hex[:12]}")
    request_id: str
    workspace_id: str
    state: str = "PENDING"
    attempt_count: int = 0
    next_attempt_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    claim_token: str | None = None
    claimed_by: str | None = None
    delivered_at: datetime | None = None
    project_id: str | None = None
    manifest_hash: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ClaimedSkillImprovementOutbox(BaseModel):
    outbox: SkillImprovementOutbox
    claim_token: str


class FeedbackWriteResult(BaseModel):
    feedback_id: str
    workspace_id: str
    skill_id: str
    skill_version: str
    definition_hash: str
    feedback_health: Literal["INSUFFICIENT_SAMPLES", "STABLE", "DEGRADING"]
    aggregate_score: float
    improvement_disposition: Literal[
        "INSUFFICIENT_SAMPLES", "STABLE", "DEFERRED_POLICY_DISABLED", "NOT_ELIGIBLE", "QUEUED"
    ]
    request_id: str | None = None


class ImprovementOutcome(BaseModel):
    status: str
    safe_reason_code: str | None = None
    candidate_id: str | None = None


class SkillImprovementEvaluationRecord(BaseModel):
    evaluation_id: str = Field(default_factory=lambda: f"eval_{uuid.uuid4().hex[:12]}")
    workspace_id: str
    request_id: str
    candidate_id: str | None = None
    suite_ref: str
    suite_hash: str
    baseline_score: float
    candidate_score: float
    delta: float
    passed_cases: list[str] = Field(default_factory=list)
    failed_cases: list[str] = Field(default_factory=list)
    safe_reason_code: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SkillImprovementMutationRecord(BaseModel):
    mutation_id: str = Field(default_factory=lambda: f"mut_{uuid.uuid4().hex[:12]}")
    workspace_id: str
    request_id: str
    candidate_id: str | None = None
    round_no: int
    mutator_name: str
    accepted: bool
    score_before: float
    score_after: float
    validation_passed: bool = True
    safe_reason_code: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SkillImprovementPolicyConfig(BaseModel):
    mode: Literal["OFF", "OBSERVE", "CANDIDATE"] = "OFF"
    allowed_identities: frozenset[SkillIdentity] = Field(default_factory=frozenset)
    min_feedback_samples: int = 3
    feedback_window_size: int = 10
    low_score_threshold: float = 0.60
    minimum_degradation_delta: float = 0.15
    cooldown_days: int = 7
    max_rounds: int = 2
    max_candidates_per_request: int = 1
    policy_hash: str = "sha256:policy_default"


@runtime_checkable
class SkillImprovementRepository(Protocol):
    async def record_resolved_skill_use(self, observation: SkillUsageObservation) -> bool: ...

    async def get_usage_observations(
        self, workspace_id: str, run_id: str, skill_id: str | None = None
    ) -> list[SkillUsageObservation]: ...

    async def record_feedback_and_maybe_enqueue(
        self, *, feedback: SkillFeedbackRecord, policy: Any
    ) -> FeedbackWriteResult: ...

    async def claim_improvement_requests(
        self, *, worker_id: str, limit: int, now: datetime
    ) -> list[ClaimedSkillImprovementRequest]: ...

    async def claim_improvement_request(
        self, *, request_id: str, worker_id: str, now: datetime
    ) -> ClaimedSkillImprovementRequest | None: ...

    async def finish_improvement_request(
        self, *, request_id: str, claim_token: str, outcome: ImprovementOutcome
    ) -> bool: ...

    async def claim_improvement_outbox(
        self, *, worker_id: str, limit: int, now: datetime
    ) -> list[ClaimedSkillImprovementOutbox]: ...

    async def mark_outbox_delivered(
        self, *, outbox_id: str, claim_token: str, delivered_at: datetime
    ) -> bool: ...

    async def mark_outbox_failed(
        self, *, outbox_id: str, claim_token: str, error: str | None = None
    ) -> bool: ...

    async def create_improvement_request(
        self, request: SkillImprovementRequest
    ) -> SkillImprovementRequest: ...

    async def get_improvement_request(
        self, request_id: str
    ) -> SkillImprovementRequest | None: ...

    async def count_requests(
        self, workspace_id: str, skill_id: str, version: str, definition_hash: str
    ) -> int: ...

    async def count_outbox(
        self, workspace_id: str, request_id: str | None = None
    ) -> int: ...

    async def record_evaluation(
        self, evaluation: SkillImprovementEvaluationRecord
    ) -> None: ...

    async def get_evaluations(
        self, workspace_id: str, request_id: str
    ) -> list[SkillImprovementEvaluationRecord]: ...

    async def record_mutation(
        self, mutation: SkillImprovementMutationRecord
    ) -> None: ...

    async def get_mutations(
        self, workspace_id: str, request_id: str
    ) -> list[SkillImprovementMutationRecord]: ...


class InMemorySkillImprovementRepository:
    def __init__(self, candidate_store: SkillCandidateStore | None = None) -> None:
        self._observations: dict[str, SkillUsageObservation] = {}
        self._feedbacks: list[SkillFeedbackRecord] = []
        self._feedback_by_key: dict[tuple[str, str], SkillFeedbackRecord] = {}
        self._aggregates: list[FeedbackAggregate] = []
        self._requests: dict[str, SkillImprovementRequest] = {}
        self._outbox: dict[str, SkillImprovementOutbox] = {}
        self._evaluations: list[dict[str, Any]] = []
        self._mutations: list[dict[str, Any]] = []
        self.candidate_store = candidate_store

    async def record_resolved_skill_use(self, observation: SkillUsageObservation) -> bool:
        key = f"{observation.run_id}:{observation.skill_id}:{observation.skill_version}:{observation.definition_hash}"
        if key in self._observations:
            return False
        self._observations[key] = observation
        return True

    async def get_usage_observations(
        self, workspace_id: str, run_id: str, skill_id: str | None = None
    ) -> list[SkillUsageObservation]:
        results = []
        for obs in self._observations.values():
            if obs.workspace_id == workspace_id and obs.run_id == run_id and (skill_id is None or obs.skill_id == skill_id):
                results.append(obs)
        return results

    async def record_feedback_and_maybe_enqueue(
        self, *, feedback: SkillFeedbackRecord, policy: Any
    ) -> FeedbackWriteResult:
        if policy is None:
            policy = SkillImprovementPolicyConfig()
        ws_id = feedback.workspace_id
        # 1. Resolve exact observation
        version = feedback.version
        def_hash = feedback.definition_hash
        project_id = feedback.project_id
        manifest_hash = feedback.manifest_hash

        if feedback.run_id:
            matching_obs = await self.get_usage_observations(ws_id, feedback.run_id, feedback.skill_id)
            if not matching_obs:
                raise ValueError(f"No observation found for run {feedback.run_id} and skill {feedback.skill_id}")
            # Ensure not ambiguous
            distinct_identities = {(o.skill_version, o.definition_hash) for o in matching_obs}
            if len(distinct_identities) > 1:
                raise ValueError(f"Ambiguous observations for run {feedback.run_id} and skill {feedback.skill_id}")
            obs = matching_obs[0]
            if feedback.project_id is not None and obs.project_id != feedback.project_id:
                raise ValueError(
                    f"No observation found matching project_id {feedback.project_id} for run {feedback.run_id}"
                )
            if feedback.manifest_hash is not None and obs.manifest_hash != feedback.manifest_hash:
                raise ValueError(
                    f"No observation found matching manifest_hash {feedback.manifest_hash} for run {feedback.run_id}"
                )
            version = obs.skill_version
            def_hash = obs.definition_hash
            project_id = feedback.project_id or obs.project_id
            manifest_hash = feedback.manifest_hash or obs.manifest_hash
        elif not version or not def_hash:
            raise ValueError("Skill version and definition hash required when run_id is omitted")

        # 2. Idempotency check
        idem_key = feedback.idempotency_key
        if idem_key:
            lookup_key = (ws_id, idem_key)
            if lookup_key in self._feedback_by_key:
                existing_fb = self._feedback_by_key[lookup_key]
                # Return current aggregate & request for this identity
                aggs = [
                    a for a in self._aggregates
                    if a.workspace_id == ws_id and a.skill_id == feedback.skill_id
                    and a.skill_version == version and a.definition_hash == def_hash
                ]
                latest_agg = max(aggs, key=lambda a: a.revision) if aggs else None
                reqs = [
                    r for r in self._requests.values()
                    if r.workspace_id == ws_id and r.skill_id == feedback.skill_id
                    and r.skill_version == version and r.definition_hash == def_hash
                ]
                live_req = next((r for r in reqs if r.status in ("PENDING", "RUNNING")), None)
                disposition: Literal["INSUFFICIENT_SAMPLES", "STABLE", "DEFERRED_POLICY_DISABLED", "NOT_ELIGIBLE", "QUEUED"]
                if live_req:
                    disposition = "QUEUED"
                elif latest_agg and latest_agg.health == "DEGRADING":
                    disposition = "DEFERRED_POLICY_DISABLED"
                elif latest_agg and latest_agg.health == "STABLE":
                    disposition = "STABLE"
                else:
                    disposition = "INSUFFICIENT_SAMPLES"

                return FeedbackWriteResult(
                    feedback_id=existing_fb.feedback_id,
                    workspace_id=ws_id,
                    skill_id=feedback.skill_id,
                    skill_version=version,
                    definition_hash=def_hash,
                    feedback_health=latest_agg.health if latest_agg else "INSUFFICIENT_SAMPLES",
                    aggregate_score=latest_agg.aggregate_score if latest_agg else 1.0,
                    improvement_disposition=disposition,
                    request_id=live_req.request_id if live_req else None,
                )

        # 3. Store feedback
        stored_fb = feedback.model_copy(update={
            "version": version,
            "definition_hash": def_hash,
            "project_id": project_id,
            "manifest_hash": manifest_hash,
        })
        self._feedbacks.append(stored_fb)
        if idem_key:
            self._feedback_by_key[(ws_id, idem_key)] = stored_fb

        # 4. Compute aggregate over window
        matching_fbs = [
            f for f in self._feedbacks
            if f.workspace_id == ws_id and f.skill_id == feedback.skill_id
            and f.version == version and f.definition_hash == def_hash
        ]
        # Sort descending by created_at
        matching_fbs.sort(key=lambda f: f.created_at, reverse=True)
        window = matching_fbs[: policy.feedback_window_size]
        sample_count = len(window)

        scores = []
        for fb in window:
            if fb.rating is not None:
                score = max(0.0, min(1.0, fb.rating / 5.0))
            else:
                score = 1.0 if fb.success else 0.0
            scores.append(score)
        agg_score = sum(scores) / sample_count if sample_count > 0 else 0.0

        existing_aggs = [
            a for a in self._aggregates
            if a.workspace_id == ws_id and a.skill_id == feedback.skill_id
            and a.skill_version == version and a.definition_hash == def_hash
        ]
        prev_agg = max(existing_aggs, key=lambda a: a.revision) if existing_aggs else None
        prev_score = prev_agg.aggregate_score if prev_agg else None
        revision = (prev_agg.revision + 1) if prev_agg else 1

        delta: float | None = None
        if prev_score is not None:
            delta = prev_score - agg_score

        health: Literal["INSUFFICIENT_SAMPLES", "STABLE", "DEGRADING"]
        if sample_count < policy.min_feedback_samples:
            health = "INSUFFICIENT_SAMPLES"
        else:
            is_low = agg_score <= policy.low_score_threshold
            is_dropping = (delta is not None and delta >= policy.minimum_degradation_delta)
            health = "DEGRADING" if (is_low and is_dropping) else "STABLE"

        now = datetime.now(UTC)
        agg = FeedbackAggregate(
            workspace_id=ws_id,
            skill_id=feedback.skill_id,
            skill_version=version,
            definition_hash=def_hash,
            revision=revision,
            sample_count=sample_count,
            aggregate_score=agg_score,
            previous_score=prev_score,
            degradation_delta=delta,
            window_started_at=min(f.created_at for f in window) if window else now,
            window_ended_at=max(f.created_at for f in window) if window else now,
            health=health,
            project_id=project_id,
            manifest_hash=manifest_hash,
            created_at=now,
        )
        self._aggregates.append(agg)

        # 5. Determine disposition and request/outbox
        req_id = None
        disposition: Literal["INSUFFICIENT_SAMPLES", "STABLE", "DEFERRED_POLICY_DISABLED", "NOT_ELIGIBLE", "QUEUED"]
        if health != "DEGRADING":
            disposition = health
        else:
            mode = getattr(policy, "mode", "OFF")
            if mode != "CANDIDATE":
                disposition = "DEFERRED_POLICY_DISABLED"
            else:
                identity = (feedback.skill_id, version, def_hash)
                allowed = getattr(policy, "allowed_identities", None)
                if allowed is not None and identity not in allowed:
                    disposition = "NOT_ELIGIBLE"
                else:
                    # Check for live request
                    live_req = next(
                        (r for r in self._requests.values()
                         if r.workspace_id == ws_id and r.skill_id == feedback.skill_id
                         and r.skill_version == version and r.definition_hash == def_hash
                         and r.status in ("PENDING", "RUNNING")),
                        None,
                    )
                    if live_req:
                        req_id = live_req.request_id
                        disposition = "QUEUED"
                    else:
                        req_id = f"sir_{uuid.uuid4().hex[:12]}"
                        policy_hash = getattr(policy, "policy_hash", "sha256:policy_default")
                        req = SkillImprovementRequest(
                            request_id=req_id,
                            workspace_id=ws_id,
                            skill_id=feedback.skill_id,
                            skill_version=version,
                            definition_hash=def_hash,
                            trigger="feedback_degradation",
                            feedback_aggregate_revision=revision,
                            policy_hash=policy_hash,
                            status="PENDING",
                            project_id=project_id,
                            manifest_hash=manifest_hash,
                            created_at=now,
                            updated_at=now,
                        )
                        self._requests[req_id] = req
                        outbox = SkillImprovementOutbox(
                            outbox_id=f"outbox_{uuid.uuid4().hex[:12]}",
                            request_id=req_id,
                            workspace_id=ws_id,
                            state="PENDING",
                            project_id=project_id,
                            manifest_hash=manifest_hash,
                            created_at=now,
                        )
                        self._outbox[outbox.outbox_id] = outbox
                        disposition = "QUEUED"

        return FeedbackWriteResult(
            feedback_id=stored_fb.feedback_id,
            workspace_id=ws_id,
            skill_id=feedback.skill_id,
            skill_version=version,
            definition_hash=def_hash,
            feedback_health=health,
            aggregate_score=agg_score,
            improvement_disposition=disposition,
            request_id=req_id,
        )

    async def claim_improvement_requests(
        self, *, worker_id: str, limit: int, now: datetime
    ) -> list[ClaimedSkillImprovementRequest]:
        claimed = []
        for req in self._requests.values():
            if req.status == "PENDING":
                token = f"token_{uuid.uuid4().hex[:16]}"
                req.status = "RUNNING"
                req.claim_token = token
                req.claimed_by = worker_id
                req.claimed_at = now
                req.attempt_count += 1
                claimed.append(ClaimedSkillImprovementRequest(request=req.model_copy(), claim_token=token))
                if len(claimed) >= limit:
                    break
        return claimed

    async def claim_improvement_request(
        self, *, request_id: str, worker_id: str, now: datetime
    ) -> ClaimedSkillImprovementRequest | None:
        req = self._requests.get(request_id)
        if not req or req.status != "PENDING":
            return None
        token = f"token_{uuid.uuid4().hex[:16]}"
        req.status = "RUNNING"
        req.claim_token = token
        req.claimed_by = worker_id
        req.claimed_at = now
        req.attempt_count += 1
        return ClaimedSkillImprovementRequest(request=req.model_copy(), claim_token=token)

    async def finish_improvement_request(
        self, *, request_id: str, claim_token: str, outcome: ImprovementOutcome
    ) -> bool:
        req = self._requests.get(request_id)
        if not req or req.claim_token != claim_token:
            return False
        req.status = outcome.status
        req.safe_reason_code = outcome.safe_reason_code
        req.claim_token = None
        req.updated_at = datetime.now(UTC)
        return True

    async def claim_improvement_outbox(
        self, *, worker_id: str, limit: int, now: datetime
    ) -> list[ClaimedSkillImprovementOutbox]:
        claimed = []
        for ob in self._outbox.values():
            if ob.state in ("PENDING", "RETRY") and ob.next_attempt_at <= now:
                token = f"claim_{uuid.uuid4().hex[:16]}"
                ob.state = "CLAIMED"
                ob.claim_token = token
                ob.claimed_by = worker_id
                ob.attempt_count += 1
                claimed.append(ClaimedSkillImprovementOutbox(outbox=ob.model_copy(), claim_token=token))
                if len(claimed) >= limit:
                    break
        return claimed

    async def mark_outbox_delivered(
        self, *, outbox_id: str, claim_token: str, delivered_at: datetime
    ) -> bool:
        ob = self._outbox.get(outbox_id)
        if not ob or ob.claim_token != claim_token:
            return False
        ob.state = "DELIVERED"
        ob.delivered_at = delivered_at
        ob.claim_token = None
        return True

    async def mark_outbox_failed(
        self, *, outbox_id: str, claim_token: str, error: str | None = None
    ) -> bool:
        ob = self._outbox.get(outbox_id)
        if not ob or ob.claim_token != claim_token:
            return False
        ob.claim_token = None
        if ob.attempt_count >= 5:
            ob.state = "FAILED_REQUIRES_ATTENTION"
        else:
            ob.state = "RETRY"
        return True

    async def create_improvement_request(
        self, request: SkillImprovementRequest
    ) -> SkillImprovementRequest:
        self._requests[request.request_id] = request.model_copy()
        return request

    async def get_improvement_request(
        self, request_id: str
    ) -> SkillImprovementRequest | None:
        req = self._requests.get(request_id)
        return req.model_copy() if req else None

    async def count_requests(
        self, workspace_id: str, skill_id: str, version: str, definition_hash: str
    ) -> int:
        return sum(
            1 for r in self._requests.values()
            if r.workspace_id == workspace_id and r.skill_id == skill_id
            and r.skill_version == version and r.definition_hash == definition_hash
        )

    async def count_outbox(
        self, workspace_id: str, request_id: str | None = None
    ) -> int:
        return sum(
            1 for ob in self._outbox.values()
            if ob.workspace_id == workspace_id and (request_id is None or ob.request_id == request_id)
        )

    async def record_evaluation(
        self, evaluation: SkillImprovementEvaluationRecord
    ) -> None:
        self._evaluations.append(evaluation.model_dump(mode="json"))

    async def get_evaluations(
        self, workspace_id: str, request_id: str
    ) -> list[SkillImprovementEvaluationRecord]:
        return [
            SkillImprovementEvaluationRecord(**e)
            for e in self._evaluations
            if e["workspace_id"] == workspace_id and e["request_id"] == request_id
        ]

    async def record_mutation(
        self, mutation: SkillImprovementMutationRecord
    ) -> None:
        self._mutations.append(mutation.model_dump(mode="json"))

    async def get_mutations(
        self, workspace_id: str, request_id: str
    ) -> list[SkillImprovementMutationRecord]:
        return [
            SkillImprovementMutationRecord(**m)
            for m in self._mutations
            if m["workspace_id"] == workspace_id and m["request_id"] == request_id
        ]


def _rowcount(res: Any) -> int:
    return int(getattr(res, "rowcount", 0) or 0)


class PostgresSkillImprovementRepository:
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession], candidate_store: SkillCandidateStore | None = None
    ) -> None:
        self._session_factory = session_factory
        self.candidate_store = candidate_store

    async def record_resolved_skill_use(self, observation: SkillUsageObservation) -> bool:
        async with self._session_factory() as session:
            stmt = text(
                """
                INSERT INTO agent.skill_usage_observations (
                    observation_id, workspace_id, run_id, skill_id, skill_version,
                    definition_hash, root_spec_id, root_definition_hash, project_id, manifest_hash, created_at
                ) VALUES (
                    :obs_id, :ws_id, :run_id, :skill_id, :skill_version,
                    :def_hash, :root_spec_id, :root_def_hash, :project_id, :manifest_hash, :created_at
                ) ON CONFLICT (run_id, skill_id, skill_version, definition_hash) DO NOTHING
                """
            )
            result = await session.execute(
                stmt,
                {
                    "obs_id": observation.observation_id,
                    "ws_id": observation.workspace_id,
                    "run_id": observation.run_id,
                    "skill_id": observation.skill_id,
                    "skill_version": observation.skill_version,
                    "def_hash": observation.definition_hash,
                    "root_spec_id": observation.root_spec_id,
                    "root_def_hash": observation.root_definition_hash,
                    "project_id": observation.project_id,
                    "manifest_hash": observation.manifest_hash,
                    "created_at": observation.created_at,
                },
            )
            await session.commit()
            return _rowcount(result) > 0

    async def get_usage_observations(
        self, workspace_id: str, run_id: str, skill_id: str | None = None
    ) -> list[SkillUsageObservation]:
        async with self._session_factory() as session:
            if skill_id:
                stmt = text(
                    """
                    SELECT observation_id, workspace_id, run_id, skill_id, skill_version,
                           definition_hash, root_spec_id, root_definition_hash, project_id, manifest_hash, created_at
                    FROM agent.skill_usage_observations
                    WHERE workspace_id = :ws_id AND run_id = :run_id AND skill_id = :skill_id
                    ORDER BY created_at ASC
                    """
                )
                rows = await session.execute(stmt, {"ws_id": workspace_id, "run_id": run_id, "skill_id": skill_id})
            else:
                stmt = text(
                    """
                    SELECT observation_id, workspace_id, run_id, skill_id, skill_version,
                           definition_hash, root_spec_id, root_definition_hash, project_id, manifest_hash, created_at
                    FROM agent.skill_usage_observations
                    WHERE workspace_id = :ws_id AND run_id = :run_id
                    ORDER BY created_at ASC
                    """
                )
                rows = await session.execute(stmt, {"ws_id": workspace_id, "run_id": run_id})

            return [
                SkillUsageObservation(
                    observation_id=r.observation_id,
                    workspace_id=r.workspace_id,
                    run_id=r.run_id,
                    skill_id=r.skill_id,
                    skill_version=r.skill_version,
                    definition_hash=r.definition_hash,
                    root_spec_id=r.root_spec_id,
                    root_definition_hash=r.root_definition_hash,
                    project_id=r.project_id,
                    manifest_hash=r.manifest_hash,
                    created_at=r.created_at,
                )
                for r in rows
            ]

    async def record_feedback_and_maybe_enqueue(
        self, *, feedback: SkillFeedbackRecord, policy: Any
    ) -> FeedbackWriteResult:
        if policy is None:
            policy = SkillImprovementPolicyConfig()
        ws_id = feedback.workspace_id
        async with self._session_factory() as session, session.begin():
            # 1. Resolve exact observation
                version = feedback.version
                def_hash = feedback.definition_hash
                project_id = feedback.project_id
                manifest_hash = feedback.manifest_hash

                if feedback.run_id:
                    stmt = text(
                        """
                        SELECT skill_version, definition_hash, project_id, manifest_hash
                        FROM agent.skill_usage_observations
                        WHERE workspace_id = :ws_id AND run_id = :run_id AND skill_id = :skill_id
                        """
                    )
                    obs_rows = (await session.execute(
                        stmt, {"ws_id": ws_id, "run_id": feedback.run_id, "skill_id": feedback.skill_id}
                    )).fetchall()
                    if not obs_rows:
                        raise ValueError(f"No observation found for run {feedback.run_id} and skill {feedback.skill_id}")
                    distinct_identities = {(r.skill_version, r.definition_hash) for r in obs_rows}
                    if len(distinct_identities) > 1:
                        raise ValueError(f"Ambiguous observations for run {feedback.run_id} and skill {feedback.skill_id}")
                    obs_row = obs_rows[0]
                    if feedback.project_id is not None and obs_row.project_id != feedback.project_id:
                        raise ValueError(
                            f"No observation found matching project_id {feedback.project_id} for run {feedback.run_id}"
                        )
                    if feedback.manifest_hash is not None and obs_row.manifest_hash != feedback.manifest_hash:
                        raise ValueError(
                            f"No observation found matching manifest_hash {feedback.manifest_hash} for run {feedback.run_id}"
                        )
                    version, def_hash = obs_row.skill_version, obs_row.definition_hash
                    project_id = feedback.project_id or obs_row.project_id
                    manifest_hash = feedback.manifest_hash or obs_row.manifest_hash
                elif not version or not def_hash:
                    raise ValueError("Skill version and definition hash required when run_id is omitted")

                # 2. Check idempotency
                idem_key = feedback.idempotency_key
                if idem_key:
                    stmt = text(
                        """
                        SELECT feedback_id, skill_version, definition_hash
                        FROM agent.agent_skill_feedback
                        WHERE workspace_id = :ws_id AND idempotency_key = :idem_key
                        """
                    )
                    existing = (await session.execute(stmt, {"ws_id": ws_id, "idem_key": idem_key})).fetchone()
                    if existing:
                        fb_id, v, h = existing
                        # Fetch latest aggregate
                        agg_stmt = text(
                            """
                            SELECT revision, aggregate_score, health
                            FROM agent.skill_feedback_aggregates
                            WHERE workspace_id = :ws_id AND skill_id = :skill_id
                              AND skill_version = :version AND definition_hash = :def_hash
                            ORDER BY revision DESC LIMIT 1
                            """
                        )
                        agg_row = (await session.execute(
                            agg_stmt, {"ws_id": ws_id, "skill_id": feedback.skill_id, "version": v, "def_hash": h}
                        )).fetchone()

                        # Fetch live request
                        req_stmt = text(
                            """
                            SELECT request_id FROM agent.skill_improvement_requests
                            WHERE workspace_id = :ws_id AND skill_id = :skill_id
                              AND skill_version = :version AND definition_hash = :def_hash
                              AND status IN ('PENDING', 'RUNNING')
                            LIMIT 1
                            """
                        )
                        req_row = (await session.execute(
                            req_stmt, {"ws_id": ws_id, "skill_id": feedback.skill_id, "version": v, "def_hash": h}
                        )).fetchone()

                        disposition: Literal["INSUFFICIENT_SAMPLES", "STABLE", "DEFERRED_POLICY_DISABLED", "NOT_ELIGIBLE", "QUEUED"]
                        if req_row:
                            disposition = "QUEUED"
                        elif agg_row and agg_row.health == "DEGRADING":
                            disposition = "DEFERRED_POLICY_DISABLED"
                        elif agg_row and agg_row.health == "STABLE":
                            disposition = "STABLE"
                        else:
                            disposition = "INSUFFICIENT_SAMPLES"

                        return FeedbackWriteResult(
                            feedback_id=fb_id,
                            workspace_id=ws_id,
                            skill_id=feedback.skill_id,
                            skill_version=v,
                            definition_hash=h,
                            feedback_health=agg_row.health if agg_row else "INSUFFICIENT_SAMPLES",
                            aggregate_score=agg_row.aggregate_score if agg_row else 1.0,
                            improvement_disposition=disposition,
                            request_id=req_row.request_id if req_row else None,
                        )

                # 3. Insert feedback
                fb_id = feedback.feedback_id or f"fb_{uuid.uuid4().hex[:12]}"
                ins_stmt = text(
                    """
                    INSERT INTO agent.agent_skill_feedback (
                        feedback_id, workspace_id, skill_id, version, skill_version,
                        definition_hash, run_id, idempotency_key, source_kind,
                        success, rating, notes, project_id, manifest_hash, created_at
                    ) VALUES (
                        :fb_id, :ws_id, :skill_id, :version, :version,
                        :def_hash, :run_id, :idem_key, :source_kind,
                        :success, :rating, :notes, :project_id, :manifest_hash, :created_at
                    )
                    """
                )
                now = datetime.now(UTC)
                await session.execute(
                    ins_stmt,
                    {
                        "fb_id": fb_id,
                        "ws_id": ws_id,
                        "skill_id": feedback.skill_id,
                        "version": version,
                        "def_hash": def_hash,
                        "run_id": feedback.run_id,
                        "idem_key": idem_key,
                        "source_kind": feedback.source_kind or "user",
                        "success": feedback.success,
                        "rating": feedback.rating,
                        "notes": feedback.notes,
                        "project_id": project_id,
                        "manifest_hash": manifest_hash,
                        "created_at": feedback.created_at or now,
                    },
                )

                # 4. Windowed aggregate calculation
                fbs_stmt = text(
                    """
                    SELECT success, rating, created_at
                    FROM agent.agent_skill_feedback
                    WHERE workspace_id = :ws_id AND skill_id = :skill_id
                      AND definition_hash = :def_hash
                    ORDER BY created_at DESC
                    LIMIT :limit
                    """
                )
                fb_rows = (await session.execute(
                    fbs_stmt,
                    {"ws_id": ws_id, "skill_id": feedback.skill_id, "def_hash": def_hash, "limit": policy.feedback_window_size}
                )).fetchall()

                sample_count = len(fb_rows)
                scores = []
                created_ats = []
                for r in fb_rows:
                    created_ats.append(r.created_at)
                    if r.rating is not None:
                        scores.append(max(0.0, min(1.0, r.rating / 5.0)))
                    else:
                        scores.append(1.0 if r.success else 0.0)

                agg_score = sum(scores) / sample_count if sample_count > 0 else 0.0

                latest_agg_stmt = text(
                    """
                    SELECT revision, aggregate_score
                    FROM agent.skill_feedback_aggregates
                    WHERE workspace_id = :ws_id AND skill_id = :skill_id
                      AND skill_version = :version AND definition_hash = :def_hash
                    ORDER BY revision DESC LIMIT 1
                    """
                )
                latest_agg_row = (await session.execute(
                    latest_agg_stmt, {"ws_id": ws_id, "skill_id": feedback.skill_id, "version": version, "def_hash": def_hash}
                )).fetchone()

                revision = (latest_agg_row.revision + 1) if latest_agg_row else 1
                prev_score = latest_agg_row.aggregate_score if latest_agg_row else None
                delta = (prev_score - agg_score) if prev_score is not None else None

                health: Literal["INSUFFICIENT_SAMPLES", "STABLE", "DEGRADING"]
                if sample_count < policy.min_feedback_samples:
                    health = "INSUFFICIENT_SAMPLES"
                else:
                    is_low = agg_score <= policy.low_score_threshold
                    is_dropping = (delta is not None and delta >= policy.minimum_degradation_delta)
                    health = "DEGRADING" if (is_low and is_dropping) else "STABLE"

                ins_agg_stmt = text(
                    """
                    INSERT INTO agent.skill_feedback_aggregates (
                        workspace_id, skill_id, skill_version, definition_hash, revision,
                        sample_count, aggregate_score, previous_score, degradation_delta,
                        window_started_at, window_ended_at, health, project_id, manifest_hash, created_at
                    ) VALUES (
                        :ws_id, :skill_id, :version, :def_hash, :rev,
                        :samples, :score, :prev_score, :delta,
                        :w_start, :w_end, :health, :project_id, :manifest_hash, :created_at
                    )
                    """
                )
                await session.execute(
                    ins_agg_stmt,
                    {
                        "ws_id": ws_id,
                        "skill_id": feedback.skill_id,
                        "version": version,
                        "def_hash": def_hash,
                        "rev": revision,
                        "samples": sample_count,
                        "score": agg_score,
                        "prev_score": prev_score,
                        "delta": delta,
                        "w_start": min(created_ats) if created_ats else now,
                        "w_end": max(created_ats) if created_ats else now,
                        "health": health,
                        "project_id": project_id,
                        "manifest_hash": manifest_hash,
                        "created_at": now,
                    },
                )

                # 5. Evaluate policy and enqueue
                req_id = None
                disposition: Literal["INSUFFICIENT_SAMPLES", "STABLE", "DEFERRED_POLICY_DISABLED", "NOT_ELIGIBLE", "QUEUED"]
                if health != "DEGRADING":
                    disposition = health
                else:
                    mode = getattr(policy, "mode", "OFF")
                    if mode != "CANDIDATE":
                        disposition = "DEFERRED_POLICY_DISABLED"
                    else:
                        identity = (feedback.skill_id, version, def_hash)
                        allowed = getattr(policy, "allowed_identities", None)
                        if allowed is not None and identity not in allowed:
                            disposition = "NOT_ELIGIBLE"
                        else:
                            # Check live request
                            live_stmt = text(
                                """
                                SELECT request_id FROM agent.skill_improvement_requests
                                WHERE workspace_id = :ws_id AND skill_id = :skill_id
                                  AND skill_version = :version AND definition_hash = :def_hash
                                  AND status IN ('PENDING', 'RUNNING')
                                FOR UPDATE
                                """
                            )
                            live_row = (await session.execute(
                                live_stmt, {"ws_id": ws_id, "skill_id": feedback.skill_id, "version": version, "def_hash": def_hash}
                            )).fetchone()

                            if live_row:
                                req_id = live_row.request_id
                                disposition = "QUEUED"
                            else:
                                req_id = f"sir_{uuid.uuid4().hex[:12]}"
                                policy_hash = getattr(policy, "policy_hash", "sha256:policy_default")
                                ins_req = text(
                                    """
                                    INSERT INTO agent.skill_improvement_requests (
                                        request_id, workspace_id, skill_id, skill_version,
                                        definition_hash, trigger, feedback_aggregate_revision,
                                        policy_hash, status, project_id, manifest_hash, created_at, updated_at
                                    ) VALUES (
                                        :req_id, :ws_id, :skill_id, :version,
                                        :def_hash, 'feedback_degradation', :rev,
                                        :policy_hash, 'PENDING', :project_id, :manifest_hash, :now, :now
                                    )
                                    """
                                )
                                await session.execute(
                                    ins_req,
                                    {
                                        "req_id": req_id,
                                        "ws_id": ws_id,
                                        "skill_id": feedback.skill_id,
                                        "version": version,
                                        "def_hash": def_hash,
                                        "rev": revision,
                                        "policy_hash": policy_hash,
                                        "project_id": project_id,
                                        "manifest_hash": manifest_hash,
                                        "now": now,
                                    }
                                )

                                outbox_id = f"outbox_{uuid.uuid4().hex[:12]}"
                                ins_outbox = text(
                                    """
                                    INSERT INTO agent.skill_improvement_outbox (
                                        outbox_id, request_id, workspace_id, state,
                                        project_id, manifest_hash, next_attempt_at, created_at
                                    ) VALUES (
                                        :outbox_id, :req_id, :ws_id, 'PENDING',
                                        :project_id, :manifest_hash, :now, :now
                                    )
                                    """
                                )
                                await session.execute(
                                    ins_outbox,
                                    {
                                        "outbox_id": outbox_id,
                                        "req_id": req_id,
                                        "ws_id": ws_id,
                                        "project_id": project_id,
                                        "manifest_hash": manifest_hash,
                                        "now": now,
                                    }
                                )
                                disposition = "QUEUED"

                return FeedbackWriteResult(
                    feedback_id=fb_id,
                    workspace_id=ws_id,
                    skill_id=feedback.skill_id,
                    skill_version=version,
                    definition_hash=def_hash,
                    feedback_health=health,
                    aggregate_score=agg_score,
                    improvement_disposition=disposition,
                    request_id=req_id,
                )

    async def claim_improvement_requests(
        self, *, worker_id: str, limit: int, now: datetime
    ) -> list[ClaimedSkillImprovementRequest]:
        async with self._session_factory() as session, session.begin():
            stmt = text(
                """
                    SELECT request_id, workspace_id, skill_id, skill_version, definition_hash,
                           trigger, feedback_aggregate_revision, policy_hash, status, attempt_count,
                           claim_token, claimed_by, claimed_at, safe_reason_code,
                           project_id, manifest_hash, created_at, updated_at
                    FROM agent.skill_improvement_requests
                    WHERE status = 'PENDING'
                    ORDER BY created_at ASC
                    LIMIT :limit
                    FOR UPDATE SKIP LOCKED
                    """
            )
            rows = (await session.execute(stmt, {"limit": limit})).fetchall()
            claimed = []
            for r in rows:
                token = f"token_{uuid.uuid4().hex[:16]}"
                upd = text(
                    """
                        UPDATE agent.skill_improvement_requests
                        SET status = 'RUNNING', claim_token = :token, claimed_by = :worker_id,
                            claimed_at = :now, attempt_count = attempt_count + 1, updated_at = :now
                        WHERE request_id = :req_id
                        """
                )
                await session.execute(
                    upd,
                    {"token": token, "worker_id": worker_id, "now": now, "req_id": r.request_id}
                )
                req = SkillImprovementRequest(
                    request_id=r.request_id,
                    workspace_id=r.workspace_id,
                    skill_id=r.skill_id,
                    skill_version=r.skill_version,
                    definition_hash=r.definition_hash,
                    trigger=r.trigger,
                    feedback_aggregate_revision=r.feedback_aggregate_revision,
                    policy_hash=r.policy_hash,
                    status="RUNNING",
                    attempt_count=r.attempt_count + 1,
                    claim_token=token,
                    claimed_by=worker_id,
                    claimed_at=now,
                    safe_reason_code=r.safe_reason_code,
                    project_id=r.project_id,
                    manifest_hash=r.manifest_hash,
                    created_at=r.created_at,
                    updated_at=now,
                )
                claimed.append(ClaimedSkillImprovementRequest(request=req, claim_token=token))
            return claimed

    async def claim_improvement_request(
        self, *, request_id: str, worker_id: str, now: datetime
    ) -> ClaimedSkillImprovementRequest | None:
        async with self._session_factory() as session, session.begin():
            stmt = text(
                """
                    SELECT request_id, workspace_id, skill_id, skill_version, definition_hash,
                           trigger, feedback_aggregate_revision, policy_hash, status, attempt_count,
                           claim_token, claimed_by, claimed_at, safe_reason_code,
                           project_id, manifest_hash, created_at, updated_at
                    FROM agent.skill_improvement_requests
                    WHERE request_id = :req_id AND status = 'PENDING'
                    FOR UPDATE SKIP LOCKED
                    """
            )
            r = (await session.execute(stmt, {"req_id": request_id})).fetchone()
            if not r:
                return None
            token = f"token_{uuid.uuid4().hex[:16]}"
            upd = text(
                """
                    UPDATE agent.skill_improvement_requests
                    SET status = 'RUNNING', claim_token = :token, claimed_by = :worker_id,
                        claimed_at = :now, attempt_count = attempt_count + 1, updated_at = :now
                    WHERE request_id = :req_id
                    """
            )
            await session.execute(
                upd,
                {"token": token, "worker_id": worker_id, "now": now, "req_id": r.request_id}
            )
            req = SkillImprovementRequest(
                request_id=r.request_id,
                workspace_id=r.workspace_id,
                skill_id=r.skill_id,
                skill_version=r.skill_version,
                definition_hash=r.definition_hash,
                trigger=r.trigger,
                feedback_aggregate_revision=r.feedback_aggregate_revision,
                policy_hash=r.policy_hash,
                status="RUNNING",
                attempt_count=r.attempt_count + 1,
                claim_token=token,
                claimed_by=worker_id,
                claimed_at=now,
                safe_reason_code=r.safe_reason_code,
                project_id=r.project_id,
                manifest_hash=r.manifest_hash,
                created_at=r.created_at,
                updated_at=now,
            )
            return ClaimedSkillImprovementRequest(request=req, claim_token=token)

    async def finish_improvement_request(
        self, *, request_id: str, claim_token: str, outcome: ImprovementOutcome
    ) -> bool:
        async with self._session_factory() as session, session.begin():
            upd = text(
                """
                UPDATE agent.skill_improvement_requests
                SET status = :status, safe_reason_code = :reason, claim_token = NULL, updated_at = :now
                WHERE request_id = :req_id AND claim_token = :token
                """
            )
            now = datetime.now(UTC)
            res = await session.execute(
                upd,
                {
                    "status": outcome.status,
                    "reason": outcome.safe_reason_code,
                    "now": now,
                    "req_id": request_id,
                    "token": claim_token,
                }
            )
            return _rowcount(res) > 0

    async def claim_improvement_outbox(
        self, *, worker_id: str, limit: int, now: datetime
    ) -> list[ClaimedSkillImprovementOutbox]:
        async with self._session_factory() as session, session.begin():
            stmt = text(
                """
                SELECT outbox_id, request_id, workspace_id, state, attempt_count,
                       project_id, manifest_hash, next_attempt_at, claim_token, claimed_by, delivered_at, created_at
                FROM agent.skill_improvement_outbox
                WHERE state IN ('PENDING', 'RETRY') AND next_attempt_at <= :now
                ORDER BY next_attempt_at ASC
                LIMIT :limit
                FOR UPDATE SKIP LOCKED
                """
            )
            rows = (await session.execute(stmt, {"limit": limit, "now": now})).fetchall()
            claimed = []
            for r in rows:
                token = f"claim_{uuid.uuid4().hex[:16]}"
                upd = text(
                    """
                    UPDATE agent.skill_improvement_outbox
                    SET state = 'CLAIMED', claim_token = :token, claimed_by = :worker_id,
                        attempt_count = attempt_count + 1
                    WHERE outbox_id = :ob_id
                    """
                )
                await session.execute(upd, {"token": token, "worker_id": worker_id, "ob_id": r.outbox_id})
                ob = SkillImprovementOutbox(
                    outbox_id=r.outbox_id,
                    request_id=r.request_id,
                    workspace_id=r.workspace_id,
                    state="CLAIMED",
                    attempt_count=r.attempt_count + 1,
                    project_id=r.project_id,
                    manifest_hash=r.manifest_hash,
                    next_attempt_at=r.next_attempt_at,
                    claim_token=token,
                    claimed_by=worker_id,
                    delivered_at=r.delivered_at,
                    created_at=r.created_at,
                )
                claimed.append(ClaimedSkillImprovementOutbox(outbox=ob, claim_token=token))
            return claimed

    async def mark_outbox_delivered(
        self, *, outbox_id: str, claim_token: str, delivered_at: datetime
    ) -> bool:
        async with self._session_factory() as session, session.begin():
            upd = text(
                """
                    UPDATE agent.skill_improvement_outbox
                    SET state = 'DELIVERED', delivered_at = :delivered_at, claim_token = NULL
                    WHERE outbox_id = :ob_id AND claim_token = :token
                    """
            )
            res = await session.execute(
                upd, {"delivered_at": delivered_at, "ob_id": outbox_id, "token": claim_token}
            )
            return _rowcount(res) > 0

    async def mark_outbox_failed(
        self, *, outbox_id: str, claim_token: str, error: str | None = None
    ) -> bool:
        async with self._session_factory() as session, session.begin():
            upd = text(
                """
                UPDATE agent.skill_improvement_outbox
                SET state = CASE WHEN attempt_count >= 5 THEN 'FAILED_REQUIRES_ATTENTION' ELSE 'RETRY' END,
                    claim_token = NULL,
                    next_attempt_at = NOW() + INTERVAL '1 minute'
                WHERE outbox_id = :ob_id AND claim_token = :token
                """
            )
            res = await session.execute(upd, {"ob_id": outbox_id, "token": claim_token})
            return _rowcount(res) > 0

    async def create_improvement_request(
        self, request: SkillImprovementRequest
    ) -> SkillImprovementRequest:
        async with self._session_factory() as session:
            stmt = text(
                """
                INSERT INTO agent.skill_improvement_requests (
                    request_id, workspace_id, skill_id, skill_version, definition_hash,
                    trigger, feedback_aggregate_revision, policy_hash, status,
                    project_id, manifest_hash, attempt_count, created_at, updated_at
                ) VALUES (
                    :req_id, :ws_id, :skill_id, :version, :def_hash,
                    :trigger, :rev, :policy_hash, :status,
                    :project_id, :manifest_hash, :attempt_count, :created_at, :updated_at
                )
                """
            )
            await session.execute(
                stmt,
                {
                    "req_id": request.request_id,
                    "ws_id": request.workspace_id,
                    "skill_id": request.skill_id,
                    "version": request.skill_version,
                    "def_hash": request.definition_hash,
                    "trigger": request.trigger,
                    "rev": request.feedback_aggregate_revision,
                    "policy_hash": request.policy_hash,
                    "status": request.status,
                    "project_id": request.project_id,
                    "manifest_hash": request.manifest_hash,
                    "attempt_count": request.attempt_count,
                    "created_at": request.created_at,
                    "updated_at": request.updated_at,
                },
            )
            await session.commit()
            return request

    async def get_improvement_request(
        self, request_id: str
    ) -> SkillImprovementRequest | None:
        async with self._session_factory() as session:
            stmt = text(
                """
                SELECT request_id, workspace_id, skill_id, skill_version, definition_hash,
                       trigger, feedback_aggregate_revision, policy_hash, status, attempt_count,
                       claim_token, claimed_by, claimed_at, safe_reason_code,
                       project_id, manifest_hash, created_at, updated_at
                FROM agent.skill_improvement_requests
                WHERE request_id = :req_id
                """
            )
            row = (await session.execute(stmt, {"req_id": request_id})).fetchone()
            if not row:
                return None
            return SkillImprovementRequest(
                request_id=row.request_id,
                workspace_id=row.workspace_id,
                skill_id=row.skill_id,
                skill_version=row.skill_version,
                definition_hash=row.definition_hash,
                trigger=row.trigger,
                feedback_aggregate_revision=row.feedback_aggregate_revision,
                policy_hash=row.policy_hash,
                status=row.status,
                attempt_count=row.attempt_count,
                claim_token=row.claim_token,
                claimed_by=row.claimed_by,
                claimed_at=row.claimed_at,
                safe_reason_code=row.safe_reason_code,
                project_id=row.project_id,
                manifest_hash=row.manifest_hash,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )

    async def count_requests(
        self, workspace_id: str, skill_id: str, version: str, definition_hash: str
    ) -> int:
        async with self._session_factory() as session:
            stmt = text(
                """
                SELECT count(*) FROM agent.skill_improvement_requests
                WHERE workspace_id = :ws_id AND skill_id = :skill_id
                  AND skill_version = :version AND definition_hash = :def_hash
                """
            )
            return (await session.execute(
                stmt, {"ws_id": workspace_id, "skill_id": skill_id, "version": version, "def_hash": definition_hash}
            )).scalar() or 0

    async def count_outbox(
        self, workspace_id: str, request_id: str | None = None
    ) -> int:
        async with self._session_factory() as session:
            if request_id:
                stmt = text(
                    """
                    SELECT count(*) FROM agent.skill_improvement_outbox
                    WHERE workspace_id = :ws_id AND request_id = :req_id
                    """
                )
                return (await session.execute(stmt, {"ws_id": workspace_id, "req_id": request_id})).scalar() or 0
            else:
                stmt = text(
                    """
                    SELECT count(*) FROM agent.skill_improvement_outbox
                    WHERE workspace_id = :ws_id
                    """
                )
                return (await session.execute(stmt, {"ws_id": workspace_id})).scalar() or 0

    async def record_evaluation(
        self, evaluation: SkillImprovementEvaluationRecord
    ) -> None:
        async with self._session_factory() as session:
            stmt = text(
                """
                INSERT INTO agent.skill_improvement_evaluations (
                    evaluation_id, workspace_id, request_id, candidate_id,
                    suite_ref, suite_hash, baseline_score, candidate_score,
                    delta, passed_cases, failed_cases, safe_reason_code, created_at
                ) VALUES (
                    :evaluation_id, :workspace_id, :request_id, :candidate_id,
                    :suite_ref, :suite_hash, :baseline_score, :candidate_score,
                    :delta, :passed_cases, :failed_cases, :safe_reason_code, :created_at
                )
                """
            )
            await session.execute(
                stmt,
                {
                    "evaluation_id": evaluation.evaluation_id,
                    "workspace_id": evaluation.workspace_id,
                    "request_id": evaluation.request_id,
                    "candidate_id": evaluation.candidate_id,
                    "suite_ref": evaluation.suite_ref,
                    "suite_hash": evaluation.suite_hash,
                    "baseline_score": evaluation.baseline_score,
                    "candidate_score": evaluation.candidate_score,
                    "delta": evaluation.delta,
                    "passed_cases": json.dumps(evaluation.passed_cases),
                    "failed_cases": json.dumps(evaluation.failed_cases),
                    "safe_reason_code": evaluation.safe_reason_code,
                    "created_at": evaluation.created_at,
                },
            )
            await session.commit()

    async def get_evaluations(
        self, workspace_id: str, request_id: str
    ) -> list[SkillImprovementEvaluationRecord]:
        async with self._session_factory() as session:
            stmt = text(
                """
                SELECT evaluation_id, workspace_id, request_id, candidate_id,
                       suite_ref, suite_hash, baseline_score, candidate_score,
                       delta, passed_cases, failed_cases, safe_reason_code, created_at
                FROM agent.skill_improvement_evaluations
                WHERE workspace_id = :workspace_id AND request_id = :request_id
                ORDER BY created_at ASC
                """
            )
            res = await session.execute(stmt, {"workspace_id": workspace_id, "request_id": request_id})
            rows = res.fetchall()
            results = []
            for r in rows:
                results.append(
                    SkillImprovementEvaluationRecord(
                        evaluation_id=r[0],
                        workspace_id=r[1],
                        request_id=r[2],
                        candidate_id=r[3],
                        suite_ref=r[4],
                        suite_hash=r[5],
                        baseline_score=r[6],
                        candidate_score=r[7],
                        delta=r[8],
                        passed_cases=r[9] if isinstance(r[9], list) else json.loads(r[9] or "[]"),
                        failed_cases=r[10] if isinstance(r[10], list) else json.loads(r[10] or "[]"),
                        safe_reason_code=r[11],
                        created_at=r[12],
                    )
                )
            return results

    async def record_mutation(
        self, mutation: SkillImprovementMutationRecord
    ) -> None:
        async with self._session_factory() as session:
            stmt = text(
                """
                INSERT INTO agent.skill_improvement_mutations (
                    mutation_id, workspace_id, request_id, candidate_id,
                    round_no, mutator_name, accepted, score_before,
                    score_after, validation_passed, safe_reason_code, created_at
                ) VALUES (
                    :mutation_id, :workspace_id, :request_id, :candidate_id,
                    :round_no, :mutator_name, :accepted, :score_before,
                    :score_after, :validation_passed, :safe_reason_code, :created_at
                )
                """
            )
            await session.execute(
                stmt,
                {
                    "mutation_id": mutation.mutation_id,
                    "workspace_id": mutation.workspace_id,
                    "request_id": mutation.request_id,
                    "candidate_id": mutation.candidate_id,
                    "round_no": mutation.round_no,
                    "mutator_name": mutation.mutator_name,
                    "accepted": mutation.accepted,
                    "score_before": mutation.score_before,
                    "score_after": mutation.score_after,
                    "validation_passed": mutation.validation_passed,
                    "safe_reason_code": mutation.safe_reason_code,
                    "created_at": mutation.created_at,
                },
            )
            await session.commit()

    async def get_mutations(
        self, workspace_id: str, request_id: str
    ) -> list[SkillImprovementMutationRecord]:
        async with self._session_factory() as session:
            stmt = text(
                """
                SELECT mutation_id, workspace_id, request_id, candidate_id,
                       round_no, mutator_name, accepted, score_before,
                       score_after, validation_passed, safe_reason_code, created_at
                FROM agent.skill_improvement_mutations
                WHERE workspace_id = :workspace_id AND request_id = :request_id
                ORDER BY round_no ASC, created_at ASC
                """
            )
            res = await session.execute(stmt, {"workspace_id": workspace_id, "request_id": request_id})
            rows = res.fetchall()
            results = []
            for r in rows:
                results.append(
                    SkillImprovementMutationRecord(
                        mutation_id=r[0],
                        workspace_id=r[1],
                        request_id=r[2],
                        candidate_id=r[3],
                        round_no=r[4],
                        mutator_name=r[5],
                        accepted=r[6],
                        score_before=r[7],
                        score_after=r[8],
                        validation_passed=r[9],
                        safe_reason_code=r[10],
                        created_at=r[11],
                    )
                )
            return results
