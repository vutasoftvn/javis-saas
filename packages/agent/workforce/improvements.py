"""Controlled improvement proposals + safe staged promotion (Task 7, spec §12).

Evaluation Owner tạo proposal và đổi rubric/tag/SLA guidance trong scope được
cấp. BẤT KỲ capability / autonomy / provider-model cost limit / external write
/ workspace-wide rollout nào cần founder approval. Canary tạo pinned
assignment/revision MỚI chỉ cho attempt được chọn; attribution run lịch sử
KHÔNG bao giờ bị sửa. Proposal revision/events append-only.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

ProposalStatus = Literal[
    "DRAFT", "PENDING_FOUNDER_REVIEW", "CANARY", "APPROVED", "REJECTED", "ROLLED_BACK"
]
ChangeClass = Literal[
    "rubric", "tag", "sla", "capability", "autonomy", "model_cost", "external_write", "rollout"
]

# Change class mà Evaluation Owner được tự thay trong delegated scope.
EVALUATION_OWNER_SELF_SERVICE: frozenset[str] = frozenset({"rubric", "tag", "sla"})

# Field bị cấm tuyệt đối trong proposed_revision / risk_cost_impact.
_FORBIDDEN_FIELDS = (
    "credential",
    "secret",
    "api_key",
    "password",
    "delegation_token",
    "raw_prompt",
)


class FounderApprovalRequired(PermissionError):
    """Change class cần founder approval nhưng actor không phải founder."""


class ForbiddenProposalField(ValueError):
    """proposed_revision chứa credential / raw delegation / prompt-secret."""


@dataclass
class ImprovementProposal:
    proposal_id: UUID
    workspace_id: str
    agent_instance_id: UUID
    created_by: str
    status: ProposalStatus
    change_class: str
    requires_founder: bool
    baseline_evidence_refs: list[str] = field(default_factory=list)
    hypothesis: str = ""
    proposed_revision: dict[str, object] = field(default_factory=dict)
    candidate_definition_hash: str | None = None
    baseline_definition_hash: str | None = None
    risk_cost_impact: dict[str, object] = field(default_factory=dict)
    canary_selection: dict[str, object] = field(default_factory=dict)
    rollback_plan: str | None = None
    version: int = 1


class ImprovementProposalRepository(Protocol):
    async def create_proposal(self, proposal: ImprovementProposal) -> ImprovementProposal: ...
    async def get_proposal(
        self, workspace_id: str, proposal_id: UUID | str
    ) -> ImprovementProposal | None: ...
    async def update_proposal(self, proposal: ImprovementProposal) -> ImprovementProposal: ...
    async def append_event(
        self, proposal_id: UUID | str, workspace_id: str, event_type: str, actor_id: str
    ) -> None: ...


def _scan_forbidden(payload: dict[str, object], path: str = "proposed_revision") -> None:
    for k, v in payload.items():
        low = k.lower()
        if any(f in low for f in _FORBIDDEN_FIELDS):
            raise ForbiddenProposalField(f"forbidden field {path}.{k}")
        if isinstance(v, dict):
            _scan_forbidden(v, f"{path}.{k}")


class InMemoryImprovementProposalRepository:
    def __init__(self) -> None:
        self._rows: dict[UUID, ImprovementProposal] = {}
        self.events: list[tuple[str, str, str]] = []

    async def create_proposal(self, proposal: ImprovementProposal) -> ImprovementProposal:
        self._rows[proposal.proposal_id] = proposal
        return proposal

    async def get_proposal(
        self, workspace_id: str, proposal_id: UUID | str
    ) -> ImprovementProposal | None:
        try:
            pid = UUID(str(proposal_id))
        except ValueError:
            return None
        rec = self._rows.get(pid)
        return rec if rec and rec.workspace_id == workspace_id else None

    async def update_proposal(self, proposal: ImprovementProposal) -> ImprovementProposal:
        self._rows[proposal.proposal_id] = proposal
        return proposal

    async def append_event(
        self, proposal_id: UUID | str, workspace_id: str, event_type: str, actor_id: str
    ) -> None:
        self.events.append((str(proposal_id), event_type, actor_id))


def _proposal_to_row_params(p: ImprovementProposal) -> dict[str, Any]:
    return {
        "proposal_id": str(p.proposal_id),
        "workspace_id": p.workspace_id,
        "agent_instance_id": str(p.agent_instance_id),
        "created_by": p.created_by,
        "status": p.status,
        "change_class": p.change_class,
        "requires_founder": p.requires_founder,
        "baseline_evidence_refs": json.dumps(p.baseline_evidence_refs),
        "hypothesis": p.hypothesis,
        "proposed_revision": json.dumps(p.proposed_revision),
        "candidate_definition_hash": p.candidate_definition_hash,
        "baseline_definition_hash": p.baseline_definition_hash,
        "risk_cost_impact": json.dumps(p.risk_cost_impact),
        "canary_selection": json.dumps(p.canary_selection),
        "rollback_plan": p.rollback_plan,
        "version": p.version,
    }


def _row_to_proposal(row: Any) -> ImprovementProposal:
    def _j(v: Any, default: Any) -> Any:
        if v is None:
            return default
        return v if isinstance(v, (dict, list)) else json.loads(v)

    return ImprovementProposal(
        proposal_id=UUID(str(row["proposal_id"])),
        workspace_id=row["workspace_id"],
        agent_instance_id=UUID(str(row["agent_instance_id"])),
        created_by=row["created_by"],
        status=row["status"],
        change_class=row["change_class"],
        requires_founder=row["requires_founder"],
        baseline_evidence_refs=_j(row["baseline_evidence_refs"], []),
        hypothesis=row["hypothesis"],
        proposed_revision=_j(row["proposed_revision"], {}),
        candidate_definition_hash=row["candidate_definition_hash"],
        baseline_definition_hash=row["baseline_definition_hash"],
        risk_cost_impact=_j(row["risk_cost_impact"], {}),
        canary_selection=_j(row["canary_selection"], {}),
        rollback_plan=row["rollback_plan"],
        version=row["version"],
    )


class PostgresImprovementProposalRepository:
    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create_proposal(self, proposal: ImprovementProposal) -> ImprovementProposal:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO agent.workforce_improvement_proposals (
                        proposal_id, workspace_id, agent_instance_id, created_by, status,
                        change_class, requires_founder, baseline_evidence_refs, hypothesis,
                        proposed_revision, candidate_definition_hash, baseline_definition_hash,
                        risk_cost_impact, canary_selection, rollback_plan, version
                    ) VALUES (
                        :proposal_id, :workspace_id, :agent_instance_id, :created_by, :status,
                        :change_class, :requires_founder, :baseline_evidence_refs, :hypothesis,
                        :proposed_revision, :candidate_definition_hash, :baseline_definition_hash,
                        :risk_cost_impact, :canary_selection, :rollback_plan, :version
                    )
                    """
                ),
                _proposal_to_row_params(proposal),
            )
            await session.commit()
        return proposal

    async def get_proposal(
        self, workspace_id: str, proposal_id: UUID | str
    ) -> ImprovementProposal | None:
        try:
            pid = UUID(str(proposal_id))
        except ValueError:
            return None
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    SELECT * FROM agent.workforce_improvement_proposals
                    WHERE workspace_id = :workspace_id AND proposal_id = :proposal_id
                    """
                ),
                {"workspace_id": workspace_id, "proposal_id": str(pid)},
            )
            row = res.mappings().first()
            return _row_to_proposal(row) if row else None

    async def update_proposal(self, proposal: ImprovementProposal) -> ImprovementProposal:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    UPDATE agent.workforce_improvement_proposals SET
                        status = :status,
                        candidate_definition_hash = :candidate_definition_hash,
                        canary_selection = :canary_selection,
                        version = :version,
                        updated_at = now()
                    WHERE workspace_id = :workspace_id AND proposal_id = :proposal_id
                    """
                ),
                _proposal_to_row_params(proposal),
            )
            await session.commit()
        return proposal

    async def append_event(
        self, proposal_id: UUID | str, workspace_id: str, event_type: str, actor_id: str
    ) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO agent.workforce_improvement_events (
                        event_id, proposal_id, workspace_id, event_type, actor_id, payload
                    ) VALUES (:event_id, :proposal_id, :workspace_id, :event_type, :actor_id, '{}'::jsonb)
                    """
                ),
                {
                    "event_id": str(uuid4()),
                    "proposal_id": str(proposal_id),
                    "workspace_id": workspace_id,
                    "event_type": event_type,
                    "actor_id": actor_id,
                },
            )
            await session.commit()


async def create_proposal(
    *,
    repository: ImprovementProposalRepository,
    workspace_id: str,
    agent_instance_id: UUID | str,
    created_by: str,
    change_class: str,
    hypothesis: str,
    proposed_revision: dict[str, object],
    baseline_definition_hash: str | None = None,
    baseline_evidence_refs: list[str] | None = None,
    risk_cost_impact: dict[str, object] | None = None,
    rollback_plan: str | None = None,
) -> ImprovementProposal:
    _scan_forbidden(proposed_revision)
    _scan_forbidden(risk_cost_impact or {}, "risk_cost_impact")

    requires_founder = change_class not in EVALUATION_OWNER_SELF_SERVICE
    proposal = ImprovementProposal(
        proposal_id=uuid4(),
        workspace_id=workspace_id,
        agent_instance_id=UUID(str(agent_instance_id)),
        created_by=created_by,
        status="DRAFT",
        change_class=change_class,
        requires_founder=requires_founder,
        baseline_evidence_refs=list(baseline_evidence_refs or []),
        hypothesis=hypothesis,
        proposed_revision=dict(proposed_revision),
        baseline_definition_hash=baseline_definition_hash,
        risk_cost_impact=dict(risk_cost_impact or {}),
        rollback_plan=rollback_plan,
    )
    await repository.create_proposal(proposal)
    await repository.append_event(proposal.proposal_id, workspace_id, "created", created_by)
    return proposal


async def promote_proposal(
    *,
    repository: ImprovementProposalRepository,
    workspace_id: str,
    proposal_id: UUID | str,
    actor_id: str,
    is_founder: bool,
) -> ImprovementProposal:
    """Đẩy proposal tiến trạng thái. Change class cần founder approval mà actor
    không phải founder -> FounderApprovalRequired."""
    proposal = await repository.get_proposal(workspace_id, proposal_id)
    if proposal is None:
        raise ValueError("proposal not found in workspace")

    if proposal.status == "DRAFT":
        # Ai cũng có thể submit; nhưng change class founder-scope chỉ dừng ở
        # PENDING_FOUNDER_REVIEW cho tới khi founder duyệt.
        proposal.status = "PENDING_FOUNDER_REVIEW" if proposal.requires_founder else "APPROVED"
        await repository.append_event(proposal.proposal_id, workspace_id, "submitted", actor_id)
    elif proposal.status == "PENDING_FOUNDER_REVIEW":
        if not is_founder:
            raise FounderApprovalRequired(
                f"change_class {proposal.change_class!r} requires founder approval"
            )
        proposal.status = "APPROVED"
        await repository.append_event(proposal.proposal_id, workspace_id, "approved", actor_id)
    else:
        raise ValueError(f"cannot promote from status {proposal.status}")

    proposal.version += 1
    await repository.update_proposal(proposal)
    return proposal


async def approve_canary(
    *,
    repository: ImprovementProposalRepository,
    workspace_id: str,
    proposal_id: UUID | str,
    founder_id: str,
    candidate_definition_hash: str,
    selected_attempt_ids: list[str],
) -> ImprovementProposal:
    """Founder bật canary: pin candidate revision CHỈ cho attempt được chọn.
    Không đổi assignment hiện hành cho attempt khác; không sửa run lịch sử."""
    proposal = await repository.get_proposal(workspace_id, proposal_id)
    if proposal is None:
        raise ValueError("proposal not found in workspace")
    proposal.status = "CANARY"
    proposal.candidate_definition_hash = candidate_definition_hash
    proposal.canary_selection = {"attempt_ids": list(selected_attempt_ids)}
    proposal.version += 1
    await repository.update_proposal(proposal)
    await repository.append_event(proposal.proposal_id, workspace_id, "canary_started", founder_id)
    return proposal


async def rollback(
    *,
    repository: ImprovementProposalRepository,
    workspace_id: str,
    proposal_id: UUID | str,
    founder_id: str,
) -> ImprovementProposal:
    """Rollback: vô hiệu candidate cho run mới, KHÔNG xóa evidence. Baseline
    definition hash được giữ nguyên để dùng lại."""
    proposal = await repository.get_proposal(workspace_id, proposal_id)
    if proposal is None:
        raise ValueError("proposal not found in workspace")
    proposal.status = "ROLLED_BACK"
    proposal.version += 1
    await repository.update_proposal(proposal)
    await repository.append_event(proposal.proposal_id, workspace_id, "rolled_back", founder_id)
    return proposal
