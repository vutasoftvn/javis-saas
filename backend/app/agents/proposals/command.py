"""Typed, immutable commands embedded in agent proposal payloads."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ProposalCommand(BaseModel):
    """The allowlisted command an approved proposal may execute."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    command_type: Literal["okr_objective.create", "strategy_task.create"]
    idempotency_key: str = Field(min_length=1)
    arguments: dict[str, Any]


def parse_proposal_command(payload: dict[str, Any]) -> ProposalCommand:
    """Validate and return the typed command from a proposal payload."""

    if not isinstance(payload, dict) or "command" not in payload:
        raise ValueError("Proposal payload must contain a command")

    try:
        return ProposalCommand.model_validate(payload["command"])
    except ValidationError:
        raise
