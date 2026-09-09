"""Outcome Analysis binding + deterministic resolver (Task 4A).

Router server (apps/cosa/events/router.py) resolve EXACT analyst employee /
assignment / spec / skill snapshot cho một analysis kind TRƯỚC khi queue —
KHÔNG có rule "agent thấy task thì tự chạy analysis" (spec §9.1). MANUAL policy
=> resolver trả về binding với policy MANUAL, caller không tạo request tự động.
Binding thiếu / lệch => trả None, caller đánh dấu BLOCKED_CONFIGURATION.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol
from uuid import UUID

AnalysisKind = Literal["TASK_OUTCOME", "PROJECT_OUTCOME_SYNTHESIS"]
AnalysisPolicy = Literal["AUTO_ALL_TASKS", "AUTO_BY_RULE", "MANUAL"]

OUTCOME_ANALYSIS_SKILL_ID = "operations/task-outcome-analysis"

# Đúng sáu capability Outcome Analyst được phép — read-only + narrow record.
OUTCOME_ANALYST_CAPABILITY_REFS: frozenset[str] = frozenset(
    {
        "operations.task.read",
        "operations.task-result.read",
        "operations.work-package.read",
        "operations.evidence.read",
        "agent.artifact.read",
        "operations.outcome-assessment.record",
    }
)


@dataclass(frozen=True)
class OutcomeAnalysisBinding:
    workspace_id: str
    analysis_kind: str
    agent_instance_id: str
    assignment_id: str
    policy: str
    skill_id: str
    skill_version: str
    definition_hash: str
    version: int


class OutcomeAnalysisBindingRepository(Protocol):
    async def get_outcome_analysis_binding(
        self, workspace_id: str, analysis_kind: str
    ) -> OutcomeAnalysisBinding | None: ...

    async def upsert_outcome_analysis_binding(
        self,
        workspace_id: str,
        analysis_kind: str,
        analyst_employee_id: UUID | str,
        analyst_assignment_id: UUID | str,
        policy: str,
        skill_id: str,
        skill_version: str,
        definition_hash: str,
        updated_by: str,
    ) -> OutcomeAnalysisBinding: ...


async def resolve_outcome_analysis_binding(
    repository: OutcomeAnalysisBindingRepository,
    workspace_id: str,
    task_result_id: str,
    analysis_kind: str,
) -> OutcomeAnalysisBinding | None:
    """Trả về đúng MỘT binding hoặc None. Không bao giờ chọn một employee
    operations generic — sai binding phải fail closed."""
    binding = await repository.get_outcome_analysis_binding(workspace_id, analysis_kind)
    if binding is None:
        return None
    if binding.skill_id != OUTCOME_ANALYSIS_SKILL_ID:
        return None
    return binding
