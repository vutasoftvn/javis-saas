from __future__ import annotations

from typing import Any
from pydantic import BaseModel


class ToolEvalResult(BaseModel):
    tool_name: str
    expected_tool: str
    tool_matched: bool
    schema_valid: bool
    score: float


def evaluate_tool_selection(
    actual_tool_name: str,
    actual_arguments: dict[str, Any],
    *,
    expected_tool_name: str,
    required_keys: list[str] | None = None,
) -> ToolEvalResult:
    """Tool Eval (§20.4): evaluates whether the agent chose the correct tool and
    passed all required argument schema keys."""
    tool_matched = actual_tool_name == expected_tool_name
    keys = required_keys or []
    schema_valid = all(k in actual_arguments for k in keys) if tool_matched else False

    score = (1.0 if tool_matched else 0.0) * 0.6 + (1.0 if schema_valid else 0.0) * 0.4
    return ToolEvalResult(
        tool_name=actual_tool_name,
        expected_tool=expected_tool_name,
        tool_matched=tool_matched,
        schema_valid=schema_valid,
        score=score,
    )
