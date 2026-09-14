from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from agent.skills.contracts import SkillCandidate, SkillStatus

__all__ = [
    "InMemorySkillCandidateStore",
    "PostgresSkillCandidateStore",
    "SkillCandidateStore",
    "SkillFeedbackRecord",
]


class SkillFeedbackRecord(BaseModel):
    """Runtime or user feedback for a skill execution."""

    feedback_id: str = Field(default_factory=lambda: f"fb_{uuid.uuid4().hex[:12]}")
    workspace_id: str
    skill_id: str
    version: str | None = None
    definition_hash: str | None = None
    run_id: str | None = None
    idempotency_key: str | None = None
    source_kind: str = "user"
    success: bool = True
    rating: int | None = None
    notes: str | None = None
    project_id: str | None = None
    manifest_hash: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


@runtime_checkable
class SkillCandidateStore(Protocol):
    """Protocol for managing skill candidates and feedback across workspaces."""

    async def save_candidate(
        self, workspace_id: str, candidate: SkillCandidate
    ) -> SkillCandidate: ...
    async def get_candidate(
        self, workspace_id: str, candidate_id: str
    ) -> SkillCandidate | None: ...
    async def list_candidates(
        self, workspace_id: str, status: str | None = None
    ) -> list[SkillCandidate]: ...
    async def update_candidate_status(
        self,
        workspace_id: str,
        candidate_id: str,
        status: SkillStatus,
        eval_score: float | None = None,
    ) -> SkillCandidate | None: ...
    async def save_feedback(self, feedback: SkillFeedbackRecord) -> SkillFeedbackRecord: ...
    async def list_feedback(
        self, workspace_id: str, skill_id: str
    ) -> list[SkillFeedbackRecord]: ...
    async def compute_aggregate_feedback_score(
        self, workspace_id: str, skill_id: str
    ) -> float | None: ...
    async def publish_candidate_if_approved(
        self,
        workspace_id: str,
        candidate_id: str,
        approval_id: str,
        expected_definition_hash: str,
    ) -> tuple[bool, str, SkillCandidate | None]: ...


class InMemorySkillCandidateStore:
    """In-memory candidate and feedback store for development, testing, and sandbox."""

    def __init__(self) -> None:
        self._candidates: dict[tuple[str, str], SkillCandidate] = {}
        self._feedback: list[SkillFeedbackRecord] = []

    async def save_candidate(self, workspace_id: str, candidate: SkillCandidate) -> SkillCandidate:
        cand = candidate.model_copy(deep=True)
        if not cand.definition_hash:
            computed = f"sha256:{cand.proposed_skill.compute_hash()}"
            cand.definition_hash = computed
        if (
            hasattr(cand.proposed_skill, "definition_hash")
            and not cand.proposed_skill.definition_hash
        ):
            cand.proposed_skill.definition_hash = cand.definition_hash
        key = (str(workspace_id), cand.candidate_id)
        self._candidates[key] = cand.model_copy(deep=True)
        return cand.model_copy(deep=True)

    async def get_candidate(self, workspace_id: str, candidate_id: str) -> SkillCandidate | None:
        key = (str(workspace_id), candidate_id)
        cand = self._candidates.get(key)
        if cand is not None:
            c = cand.model_copy(deep=True)
            if not c.definition_hash:
                c.definition_hash = f"sha256:{c.proposed_skill.compute_hash()}"
            return c
        for (ws, _), c in self._candidates.items():
            if ws == str(workspace_id) and c.proposed_skill.id == candidate_id:
                res = c.model_copy(deep=True)
                if not res.definition_hash:
                    res.definition_hash = f"sha256:{res.proposed_skill.compute_hash()}"
                return res
        return None

    async def list_candidates(
        self, workspace_id: str, status: str | None = None
    ) -> list[SkillCandidate]:
        results: list[SkillCandidate] = []
        for (ws, _), c in self._candidates.items():
            if ws != str(workspace_id):
                continue
            if status is not None and c.status.value.lower() != status.lower():
                continue
            item = c.model_copy(deep=True)
            if not item.definition_hash:
                item.definition_hash = f"sha256:{item.proposed_skill.compute_hash()}"
            results.append(item)
        return results

    async def update_candidate_status(
        self,
        workspace_id: str,
        candidate_id: str,
        status: SkillStatus,
        eval_score: float | None = None,
    ) -> SkillCandidate | None:
        cand = await self.get_candidate(workspace_id, candidate_id)
        if cand is None:
            return None
        key = (str(workspace_id), cand.candidate_id)
        cand.status = status
        if eval_score is not None:
            cand.eval_score = eval_score
        self._candidates[key] = cand.model_copy(deep=True)
        return cand.model_copy(deep=True)

    async def publish_candidate_if_approved(
        self,
        workspace_id: str,
        candidate_id: str,
        approval_id: str,
        expected_definition_hash: str,
    ) -> tuple[bool, str, SkillCandidate | None]:
        cand = await self.get_candidate(workspace_id, candidate_id)
        if cand is None:
            return False, "CANDIDATE_NOT_FOUND", None

        # Idempotent replay: already published with same approval and hash
        if cand.status == SkillStatus.PUBLISHED:
            if cand.promotion_approval_id == approval_id and (
                expected_definition_hash in (cand.promotion_definition_hash, cand.definition_hash)
            ):
                return True, "ALREADY_PUBLISHED", cand.model_copy(deep=True)
            return False, "ALREADY_PUBLISHED_DIFFERENT_APPROVAL", cand.model_copy(deep=True)

        # Stale definition check
        if cand.definition_hash != expected_definition_hash:
            return False, "APPROVAL_SUBJECT_STALE", cand.model_copy(deep=True)

        if cand.status != SkillStatus.EVALUATED:
            return False, "CANDIDATE_NOT_EVALUATED", cand.model_copy(deep=True)

        if cand.promotion_approval_id is not None:
            return False, "PROMOTION_ALREADY_CLAIMED", cand.model_copy(deep=True)

        key = (str(workspace_id), cand.candidate_id)
        cand.status = SkillStatus.PUBLISHED
        cand.proposed_skill.status = SkillStatus.PUBLISHED
        cand.promotion_approval_id = approval_id
        cand.promotion_definition_hash = expected_definition_hash
        self._candidates[key] = cand.model_copy(deep=True)
        return True, "PUBLISHED", cand.model_copy(deep=True)

    async def save_feedback(self, feedback: SkillFeedbackRecord) -> SkillFeedbackRecord:
        self._feedback.append(feedback.model_copy(deep=True))
        return feedback.model_copy(deep=True)

    async def list_feedback(self, workspace_id: str, skill_id: str) -> list[SkillFeedbackRecord]:
        return [
            f.model_copy(deep=True)
            for f in self._feedback
            if f.workspace_id == str(workspace_id) and f.skill_id == skill_id
        ]

    async def compute_aggregate_feedback_score(
        self, workspace_id: str, skill_id: str
    ) -> float | None:
        """Tính điểm tổng hợp trung bình (normalized 0.0 - 1.0) từ feedback."""
        feedbacks = await self.list_feedback(workspace_id, skill_id)
        if not feedbacks:
            return None
        scores: list[float] = []
        for fb in feedbacks:
            if fb.rating is not None:
                scores.append(max(0.0, min(1.0, float(fb.rating) / 5.0)))
            elif fb.success is not None:
                scores.append(1.0 if fb.success else 0.0)
        return round(sum(scores) / len(scores), 3) if scores else None


class PostgresSkillCandidateStore:
    """PostgreSQL-backed candidate and feedback store for production persistence."""

    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory

    async def save_candidate(self, workspace_id: str, candidate: SkillCandidate) -> SkillCandidate:
        from sqlalchemy import text

        cand = candidate.model_copy(deep=True)
        if not cand.definition_hash:
            computed = f"sha256:{cand.proposed_skill.compute_hash()}"
            cand.definition_hash = computed
        if (
            hasattr(cand.proposed_skill, "definition_hash")
            and not cand.proposed_skill.definition_hash
        ):
            cand.proposed_skill.definition_hash = cand.definition_hash

        async with self._session_factory() as session, session.begin():
            query = text(
                """
                    INSERT INTO agent.agent_skill_candidates (
                        candidate_id, workspace_id, parent_run_id, skill_id,
                        proposed_skill, evidence_refs, eval_score, status,
                        definition_hash, promotion_approval_id, promotion_definition_hash,
                        updated_at
                    ) VALUES (
                        :candidate_id, :workspace_id, :parent_run_id, :skill_id,
                        CAST(:proposed_skill AS jsonb), CAST(:evidence_refs AS jsonb),
                        :eval_score, :status,
                        :definition_hash, :promotion_approval_id, :promotion_definition_hash,
                        now()
                    )
                    ON CONFLICT (candidate_id) DO UPDATE SET
                        proposed_skill = EXCLUDED.proposed_skill,
                        evidence_refs = EXCLUDED.evidence_refs,
                        eval_score = EXCLUDED.eval_score,
                        status = EXCLUDED.status,
                        definition_hash = EXCLUDED.definition_hash,
                        promotion_approval_id = COALESCE(EXCLUDED.promotion_approval_id, agent.agent_skill_candidates.promotion_approval_id),
                        promotion_definition_hash = COALESCE(EXCLUDED.promotion_definition_hash, agent.agent_skill_candidates.promotion_definition_hash),
                        updated_at = now()
                    """
            )
            import json

            await session.execute(
                query,
                {
                    "candidate_id": cand.candidate_id,
                    "workspace_id": str(workspace_id),
                    "parent_run_id": cand.parent_run_id,
                    "skill_id": cand.proposed_skill.id,
                    "proposed_skill": json.dumps(cand.proposed_skill.model_dump(mode="json")),
                    "evidence_refs": json.dumps(cand.evidence_refs),
                    "eval_score": cand.eval_score,
                    "status": cand.status.value,
                    "definition_hash": cand.definition_hash,
                    "promotion_approval_id": cand.promotion_approval_id,
                    "promotion_definition_hash": cand.promotion_definition_hash,
                },
            )
        return cand.model_copy(deep=True)

    async def get_candidate(self, workspace_id: str, candidate_id: str) -> SkillCandidate | None:
        from sqlalchemy import text

        async with self._session_factory() as session:
            query = text(
                """
                SELECT candidate_id, parent_run_id, proposed_skill, evidence_refs, eval_score, status,
                       definition_hash, promotion_approval_id, promotion_definition_hash
                FROM agent.agent_skill_candidates
                WHERE workspace_id = :workspace_id AND (candidate_id = :candidate_id OR skill_id = :candidate_id)
                LIMIT 1
                """
            )
            result = await session.execute(
                query, {"workspace_id": str(workspace_id), "candidate_id": candidate_id}
            )
            row = result.mappings().first()
            if not row:
                return None
            from agent.skills.contracts import SkillSpec

            spec = SkillSpec.model_validate(row["proposed_skill"])
            def_hash = row["definition_hash"] or f"sha256:{spec.compute_hash()}"

            return SkillCandidate(
                candidate_id=row["candidate_id"],
                parent_run_id=row["parent_run_id"],
                proposed_skill=spec,
                evidence_refs=row["evidence_refs"] or [],
                eval_score=row["eval_score"],
                status=SkillStatus(row["status"]),
                definition_hash=def_hash,
                promotion_approval_id=row["promotion_approval_id"],
                promotion_definition_hash=row["promotion_definition_hash"],
            )

    async def list_candidates(
        self, workspace_id: str, status: str | None = None
    ) -> list[SkillCandidate]:
        from sqlalchemy import text

        async with self._session_factory() as session:
            if status is not None:
                query = text(
                    """
                    SELECT candidate_id, parent_run_id, proposed_skill, evidence_refs, eval_score, status,
                           definition_hash, promotion_approval_id, promotion_definition_hash
                    FROM agent.agent_skill_candidates
                    WHERE workspace_id = :workspace_id AND lower(status) = lower(:status)
                    ORDER BY created_at DESC
                    """
                )
                result = await session.execute(
                    query, {"workspace_id": str(workspace_id), "status": status}
                )
            else:
                query = text(
                    """
                    SELECT candidate_id, parent_run_id, proposed_skill, evidence_refs, eval_score, status,
                           definition_hash, promotion_approval_id, promotion_definition_hash
                    FROM agent.agent_skill_candidates
                    WHERE workspace_id = :workspace_id
                    ORDER BY created_at DESC
                    """
                )
                result = await session.execute(query, {"workspace_id": str(workspace_id)})

            from agent.skills.contracts import SkillSpec

            items: list[SkillCandidate] = []
            for row in result.mappings().all():
                spec = SkillSpec.model_validate(row["proposed_skill"])
                def_hash = row["definition_hash"] or f"sha256:{spec.compute_hash()}"
                items.append(
                    SkillCandidate(
                        candidate_id=row["candidate_id"],
                        parent_run_id=row["parent_run_id"],
                        proposed_skill=spec,
                        evidence_refs=row["evidence_refs"] or [],
                        eval_score=row["eval_score"],
                        status=SkillStatus(row["status"]),
                        definition_hash=def_hash,
                        promotion_approval_id=row["promotion_approval_id"],
                        promotion_definition_hash=row["promotion_definition_hash"],
                    )
                )
            return items

    async def update_candidate_status(
        self,
        workspace_id: str,
        candidate_id: str,
        status: SkillStatus,
        eval_score: float | None = None,
    ) -> SkillCandidate | None:
        from sqlalchemy import text

        async with self._session_factory() as session, session.begin():
            if eval_score is not None:
                query = text(
                    """
                    UPDATE agent.agent_skill_candidates
                    SET status = :status, eval_score = :eval_score, updated_at = now()
                    WHERE workspace_id = :workspace_id AND (candidate_id = :candidate_id OR skill_id = :candidate_id)
                    """
                )
                await session.execute(
                    query,
                    {
                        "workspace_id": str(workspace_id),
                        "candidate_id": candidate_id,
                        "status": status.value,
                        "eval_score": eval_score,
                    },
                )
            else:
                query = text(
                    """
                    UPDATE agent.agent_skill_candidates
                    SET status = :status, updated_at = now()
                    WHERE workspace_id = :workspace_id AND (candidate_id = :candidate_id OR skill_id = :candidate_id)
                    """
                )
                await session.execute(
                    query,
                    {
                        "workspace_id": str(workspace_id),
                        "candidate_id": candidate_id,
                        "status": status.value,
                    },
                )
        return await self.get_candidate(workspace_id, candidate_id)

    async def publish_candidate_if_approved(
        self,
        workspace_id: str,
        candidate_id: str,
        approval_id: str,
        expected_definition_hash: str,
    ) -> tuple[bool, str, SkillCandidate | None]:
        from sqlalchemy import text

        from agent.skills.contracts import SkillSpec

        async with self._session_factory() as session, session.begin():
            fetch_query = text(
                """
                SELECT candidate_id, parent_run_id, proposed_skill, evidence_refs, eval_score,
                       status, definition_hash, promotion_approval_id, promotion_definition_hash
                FROM agent.agent_skill_candidates
                WHERE workspace_id = :workspace_id AND (candidate_id = :candidate_id OR skill_id = :candidate_id)
                LIMIT 1
                FOR UPDATE
                """
            )
            result = await session.execute(
                fetch_query, {"workspace_id": str(workspace_id), "candidate_id": candidate_id}
            )
            row = result.mappings().first()
            if not row:
                return False, "CANDIDATE_NOT_FOUND", None

            spec = SkillSpec.model_validate(row["proposed_skill"])
            current_def_hash = row["definition_hash"] or f"sha256:{spec.compute_hash()}"

            cand = SkillCandidate(
                candidate_id=row["candidate_id"],
                parent_run_id=row["parent_run_id"],
                proposed_skill=spec,
                evidence_refs=row["evidence_refs"] or [],
                eval_score=row["eval_score"],
                status=SkillStatus(row["status"]),
                definition_hash=current_def_hash,
                promotion_approval_id=row["promotion_approval_id"],
                promotion_definition_hash=row["promotion_definition_hash"],
            )

            # Idempotent replay: already published with same approval and hash
            if cand.status == SkillStatus.PUBLISHED:
                if cand.promotion_approval_id == approval_id and (
                    expected_definition_hash
                    in (cand.promotion_definition_hash, cand.definition_hash)
                ):
                    return True, "ALREADY_PUBLISHED", cand
                return False, "ALREADY_PUBLISHED_DIFFERENT_APPROVAL", cand

            # Stale subject check
            if cand.definition_hash != expected_definition_hash:
                return False, "APPROVAL_SUBJECT_STALE", cand

            if cand.status != SkillStatus.EVALUATED:
                return False, "CANDIDATE_NOT_EVALUATED", cand

            if cand.promotion_approval_id is not None:
                return False, "PROMOTION_ALREADY_CLAIMED", cand

            import json

            updated_proposed_skill = cand.proposed_skill.model_dump(mode="json")
            updated_proposed_skill["status"] = SkillStatus.PUBLISHED.value

            cas_query = text(
                """
                UPDATE agent.agent_skill_candidates
                SET status = 'PUBLISHED',
                    promotion_approval_id = :approval_id,
                    promotion_definition_hash = :expected_definition_hash,
                    published_at = now(),
                    updated_at = now(),
                    proposed_skill = CAST(:proposed_skill AS jsonb)
                WHERE workspace_id = :workspace_id
                  AND (candidate_id = :candidate_id OR skill_id = :candidate_id)
                  AND status = 'EVALUATED'
                  AND (definition_hash = :expected_definition_hash OR definition_hash IS NULL)
                  AND promotion_approval_id IS NULL
                RETURNING candidate_id, parent_run_id, proposed_skill, evidence_refs, eval_score,
                          status, definition_hash, promotion_approval_id, promotion_definition_hash
                """
            )
            cas_result = await session.execute(
                cas_query,
                {
                    "workspace_id": str(workspace_id),
                    "candidate_id": candidate_id,
                    "approval_id": approval_id,
                    "expected_definition_hash": expected_definition_hash,
                    "proposed_skill": json.dumps(updated_proposed_skill),
                },
            )
            updated_row = cas_result.mappings().first()
            if not updated_row:
                return False, "CONCURRENT_MODIFICATION", cand

            published_cand = SkillCandidate(
                candidate_id=updated_row["candidate_id"],
                parent_run_id=updated_row["parent_run_id"],
                proposed_skill=SkillSpec.model_validate(updated_row["proposed_skill"]),
                evidence_refs=updated_row["evidence_refs"] or [],
                eval_score=updated_row["eval_score"],
                status=SkillStatus(updated_row["status"]),
                definition_hash=updated_row["definition_hash"] or expected_definition_hash,
                promotion_approval_id=updated_row["promotion_approval_id"],
                promotion_definition_hash=updated_row["promotion_definition_hash"],
            )
            return True, "PUBLISHED", published_cand

    async def save_feedback(self, feedback: SkillFeedbackRecord) -> SkillFeedbackRecord:
        from sqlalchemy import text

        async with self._session_factory() as session, session.begin():
            query = text(
                """
                INSERT INTO agent_skill_feedback (
                    feedback_id, workspace_id, skill_id, version, success, rating, notes,
                    project_id, manifest_hash, created_at
                ) VALUES (
                    :feedback_id, :workspace_id, :skill_id, :version, :success, :rating, :notes,
                    :project_id, :manifest_hash, :created_at
                )
                """
            )
            await session.execute(
                query,
                {
                    "feedback_id": feedback.feedback_id,
                    "workspace_id": feedback.workspace_id,
                    "skill_id": feedback.skill_id,
                    "version": feedback.version,
                    "success": feedback.success,
                    "rating": feedback.rating,
                    "notes": feedback.notes,
                    "project_id": feedback.project_id,
                    "manifest_hash": feedback.manifest_hash,
                    "created_at": feedback.created_at,
                },
            )
        return feedback.model_copy(deep=True)

    async def list_feedback(self, workspace_id: str, skill_id: str) -> list[SkillFeedbackRecord]:
        from sqlalchemy import text

        async with self._session_factory() as session:
            query = text(
                """
                SELECT feedback_id, workspace_id, skill_id, version, success, rating, notes,
                       project_id, manifest_hash, created_at
                FROM agent_skill_feedback
                WHERE workspace_id = :workspace_id AND skill_id = :skill_id
                ORDER BY created_at DESC
                """
            )
            result = await session.execute(
                query, {"workspace_id": str(workspace_id), "skill_id": skill_id}
            )
            return [
                SkillFeedbackRecord(
                    feedback_id=row["feedback_id"],
                    workspace_id=row["workspace_id"],
                    skill_id=row["skill_id"],
                    version=row["version"],
                    success=row["success"],
                    rating=row["rating"],
                    notes=row["notes"],
                    project_id=row.get("project_id"),
                    manifest_hash=row.get("manifest_hash"),
                    created_at=row["created_at"],
                )
                for row in result.mappings().all()
            ]

    async def compute_aggregate_feedback_score(
        self, workspace_id: str, skill_id: str
    ) -> float | None:
        feedbacks = await self.list_feedback(workspace_id, skill_id)
        if not feedbacks:
            return None
        scores: list[float] = []
        for fb in feedbacks:
            if fb.rating is not None:
                scores.append(max(0.0, min(1.0, float(fb.rating) / 5.0)))
            elif fb.success is not None:
                scores.append(1.0 if fb.success else 0.0)
        return round(sum(scores) / len(scores), 3) if scores else None
