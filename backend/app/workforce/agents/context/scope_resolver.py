"""Scope Resolver for COSA Agents.

Computes the bounded ScopeSet (token budget, allowed namespaces, domain & project bounds)
before initiating Agent runs or Chat turns to enforce "No Job -> No Heavy Priming".
"""

from dataclasses import dataclass
from typing import FrozenSet, Optional

from app.workforce.chat.conversation_gate import GateDecision, GateIntent


@dataclass(frozen=True)
class ScopeSet:
    workspace_id: int
    project_id: Optional[int] = None
    job_type: Optional[str] = None
    domain: Optional[str] = None
    allowed_namespaces: FrozenSet[str] = frozenset()
    token_budget: int = 1024
    needs_heavy_priming: bool = False

    @classmethod
    def minimal_conversation(cls, workspace_id: int) -> "ScopeSet":
        return cls(
            workspace_id=workspace_id,
            allowed_namespaces=frozenset(),
            token_budget=1024,
            needs_heavy_priming=False,
        )

    @classmethod
    def for_project(
        cls,
        workspace_id: int,
        project_id: Optional[int] = None,
        job_type: Optional[str] = None,
        domain: Optional[str] = None,
        allowed_namespaces: FrozenSet[str] = frozenset({"strategy", "tasks"}),
        token_budget: int = 4096,
    ) -> "ScopeSet":
        return cls(
            workspace_id=workspace_id,
            project_id=project_id,
            job_type=job_type,
            domain=domain,
            allowed_namespaces=allowed_namespaces,
            token_budget=token_budget,
            needs_heavy_priming=True,
        )


class ScopeResolver:
    """Resolves ScopeSet dynamically according to GateDecision and execution targets."""

    @classmethod
    def resolve(
        cls,
        workspace_id: int,
        gate_decision: Optional[GateDecision] = None,
        project_id: Optional[int] = None,
        job_type: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> ScopeSet:
        if gate_decision is not None and not gate_decision.needs_project and not gate_decision.needs_job:
            return ScopeSet.minimal_conversation(workspace_id=workspace_id)

        namespaces = gate_decision.allowed_namespaces if gate_decision else frozenset({"strategy", "tasks"})
        budget = 4096 if (gate_decision and gate_decision.needs_job) else 2048

        return ScopeSet(
            workspace_id=workspace_id,
            project_id=project_id,
            job_type=job_type,
            domain=domain,
            allowed_namespaces=namespaces,
            token_budget=budget,
            needs_heavy_priming=gate_decision.needs_project if gate_decision else True,
        )
