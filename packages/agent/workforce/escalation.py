"""Bộ phân giải leo thang (Dự án C). Hàm thuần: org chart chỉ là đường leo thang, không
bao giờ nới capability hay autonomy của ai."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from agent.workforce.reporting import ReportingNodes, manager_chain

__all__ = ["DEFAULT_HOP_CAP", "EscalationTarget", "next_escalation_target"]

DEFAULT_HOP_CAP = 3


@dataclass(frozen=True)
class EscalationTarget:
    kind: Literal["manager", "operator"]
    assignment_id: UUID | None
    hop: int
    reason: str


def next_escalation_target(
    *,
    nodes: ReportingNodes,
    assignment_id: UUID,
    hop: int,
    hop_cap: int = DEFAULT_HOP_CAP,
) -> EscalationTarget:
    if hop >= hop_cap:
        return EscalationTarget("operator", None, hop, "hop_cap_reached")
    chain = manager_chain(nodes, assignment_id, max_hops=1)
    if not chain:
        return EscalationTarget("operator", None, hop, "no_manager")
    return EscalationTarget("manager", chain[0], hop + 1, "escalated_to_manager")
