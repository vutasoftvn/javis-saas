"""Typed, immutable commands embedded in agent proposal payloads."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class FrozenDict(dict):
    """A JSON-compatible dict that rejects mutation after validation."""

    def _immutable(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError("Proposal command arguments are immutable")

    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = _immutable


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return FrozenDict({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze(item) for item in value)
    return value


class ProposalCommand(BaseModel):
    """The allowlisted command an approved proposal may execute."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    command_type: Literal["okr_objective.create", "strategy_task.create", "project_cycle.setup"]
    idempotency_key: str = Field(min_length=1)
    arguments: dict[str, Any]

    @field_validator("arguments", mode="after")
    @classmethod
    def freeze_arguments(cls, arguments: dict[str, Any]) -> dict[str, Any]:
        return _freeze(arguments)


def parse_proposal_command(payload: dict[str, Any]) -> ProposalCommand:
    """Validate and return the typed command from a proposal payload."""

    if not isinstance(payload, dict) or "command" not in payload:
        raise ValueError("Proposal payload must contain a command")

    try:
        return ProposalCommand.model_validate(payload["command"])
    except ValidationError:
        raise
