from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

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
    success: bool = True
    rating: int | None = None
    notes: str | None = None
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


class InMemorySkillCandidateStore:
    """In-memory candidate and feedback store for development, testing, and sandbox."""

    def __init__(self) -> None:
        self._candidates: dict[tuple[str, str], SkillCandidate] = {}
        self._feedback: list[SkillFeedbackRecord] = []

    async def save_candidate(self, workspace_id: str, candidate: SkillCandidate) -> SkillCandidate:
        key = (str(workspace_id), candidate.candidate_id)
        self._candidates[key] = candidate.model_copy(deep=True)
        return candidate.model_copy(deep=True)

    async def get_candidate(self, workspace_id: str, candidate_id: str) -> SkillCandidate | None:
        key = (str(workspace_id), candidate_id)
        cand = self._candidates.get(key)
        if cand is not None:
            return cand.model_copy(deep=True)
        for (ws, _), c in self._candidates.items():
            if ws == str(workspace_id) and c.proposed_skill.id == candidate_id:
                return c.model_copy(deep=True)
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
            results.append(c.model_copy(deep=True))
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

        async with self._session_factory() as session:
            async with session.begin():
                query = text(
                    """
                    INSERT INTO agent_skill_candidates (
                        candidate_id, workspace_id, parent_run_id, skill_id,
                        proposed_skill, evidence_refs, eval_score, status, updated_at
                    ) VALUES (
                        :candidate_id, :workspace_id, :parent_run_id, :skill_id,
                        CAST(:proposed_skill AS jsonb), CAST(:evidence_refs AS jsonb),
                        :eval_score, :status, now()
                    )
                    ON CONFLICT (candidate_id) DO UPDATE SET
                        proposed_skill = EXCLUDED.proposed_skill,
                        evidence_refs = EXCLUDED.evidence_refs,
                        eval_score = EXCLUDED.eval_score,
                        status = EXCLUDED.status,
                        updated_at = now()
                    """
                )
                import json

                await session.execute(
                    query,
                    {
                        "candidate_id": candidate.candidate_id,
                        "workspace_id": str(workspace_id),
                        "parent_run_id": candidate.parent_run_id,
                        "skill_id": candidate.proposed_skill.id,
                        "proposed_skill": json.dumps(
                            candidate.proposed_skill.model_dump(mode="json")
                        ),
                        "evidence_refs": json.dumps(candidate.evidence_refs),
                        "eval_score": candidate.eval_score,
                        "status": candidate.status.value,
                    },
                )
        return candidate.model_copy(deep=True)

    async def get_candidate(self, workspace_id: str, candidate_id: str) -> SkillCandidate | None:
        from sqlalchemy import text

        async with self._session_factory() as session:
            query = text(
                """
                SELECT candidate_id, parent_run_id, proposed_skill, evidence_refs, eval_score, status
                FROM agent_skill_candidates
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

            return SkillCandidate(
                candidate_id=row["candidate_id"],
                parent_run_id=row["parent_run_id"],
                proposed_skill=SkillSpec.model_validate(row["proposed_skill"]),
                evidence_refs=row["evidence_refs"] or [],
                eval_score=row["eval_score"],
                status=SkillStatus(row["status"]),
            )

    async def list_candidates(
        self, workspace_id: str, status: str | None = None
    ) -> list[SkillCandidate]:
        from sqlalchemy import text

        async with self._session_factory() as session:
            if status is not None:
                query = text(
                    """
                    SELECT candidate_id, parent_run_id, proposed_skill, evidence_refs, eval_score, status
                    FROM agent_skill_candidates
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
                    SELECT candidate_id, parent_run_id, proposed_skill, evidence_refs, eval_score, status
                    FROM agent_skill_candidates
                    WHERE workspace_id = :workspace_id
                    ORDER BY created_at DESC
                    """
                )
                result = await session.execute(query, {"workspace_id": str(workspace_id)})

            from agent.skills.contracts import SkillSpec

            return [
                SkillCandidate(
                    candidate_id=row["candidate_id"],
                    parent_run_id=row["parent_run_id"],
                    proposed_skill=SkillSpec.model_validate(row["proposed_skill"]),
                    evidence_refs=row["evidence_refs"] or [],
                    eval_score=row["eval_score"],
                    status=SkillStatus(row["status"]),
                )
                for row in result.mappings().all()
            ]

    async def update_candidate_status(
        self,
        workspace_id: str,
        candidate_id: str,
        status: SkillStatus,
        eval_score: float | None = None,
    ) -> SkillCandidate | None:
        from sqlalchemy import text

        async with self._session_factory() as session:
            async with session.begin():
                if eval_score is not None:
                    query = text(
                        """
                        UPDATE agent_skill_candidates
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
                        UPDATE agent_skill_candidates
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

    async def save_feedback(self, feedback: SkillFeedbackRecord) -> SkillFeedbackRecord:
        from sqlalchemy import text

        async with self._session_factory() as session:
            async with session.begin():
                query = text(
                    """
                    INSERT INTO agent_skill_feedback (
                        feedback_id, workspace_id, skill_id, version, success, rating, notes, created_at
                    ) VALUES (
                        :feedback_id, :workspace_id, :skill_id, :version, :success, :rating, :notes, :created_at
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
                        "created_at": feedback.created_at,
                    },
                )
        return feedback.model_copy(deep=True)

    async def list_feedback(self, workspace_id: str, skill_id: str) -> list[SkillFeedbackRecord]:
        from sqlalchemy import text

        async with self._session_factory() as session:
            query = text(
                """
                SELECT feedback_id, workspace_id, skill_id, version, success, rating, notes, created_at
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

