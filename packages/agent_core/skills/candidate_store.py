from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from agent_core.skills.contracts import SkillCandidate, SkillStatus

__all__ = [
    "InMemorySkillCandidateStore",
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
