from sqlalchemy.orm import Session

from agent_runtime.sessions.models import AgentRun


MAX_SUBRUN_DEPTH = 1


class DelegationDepthError(RuntimeError):
    """The persisted run tree is invalid or cannot accept another child."""


def resolve_run_chain(
    db: Session,
    workspace_id: int,
    run_id: int,
) -> list[AgentRun]:
    """Resolve a tenant-safe parent chain, ordered from root to current run."""
    chain: list[AgentRun] = []
    visited: set[int] = set()
    current_id: int | None = run_id

    while current_id is not None:
        if current_id in visited:
            raise DelegationDepthError(
                f"Agent run parent cycle detected at run {current_id}"
            )
        visited.add(current_id)

        current = db.query(AgentRun).filter(AgentRun.id == current_id).first()
        if current is None:
            raise DelegationDepthError(
                f"Agent run parent chain is orphaned at run {current_id}"
            )
        if current.workspace_id != workspace_id:
            raise DelegationDepthError(
                f"Agent run {current.id} crosses workspace boundary "
                f"({current.workspace_id} != {workspace_id})"
            )

        chain.append(current)
        current_id = current.parent_run_id

    chain.reverse()
    depth = len(chain) - 1
    if depth > MAX_SUBRUN_DEPTH:
        raise DelegationDepthError(
            f"Agent run chain depth {depth} exceeds maximum depth {MAX_SUBRUN_DEPTH}"
        )
    return chain


def assert_can_delegate(
    db: Session,
    workspace_id: int,
    parent_run_id: int,
) -> int:
    """Validate the full chain and return the depth of the proposed child."""
    chain = resolve_run_chain(db, workspace_id, parent_run_id)
    child_depth = len(chain)
    if child_depth > MAX_SUBRUN_DEPTH:
        raise DelegationDepthError(
            f"Delegation would exceed maximum depth {MAX_SUBRUN_DEPTH} "
            f"(proposed depth: {child_depth})"
        )
    return child_depth
