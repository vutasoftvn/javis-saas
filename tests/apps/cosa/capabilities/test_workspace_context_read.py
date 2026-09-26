"""Schema `workspace.context.read` phải dùng được dưới strict mode của Agents SDK
(FunctionTool mặc định strict_json_schema=True -> mọi property thành required):
model gọi mỗi operation chỉ với biến của nó (biến còn lại = null) và handler
bỏ các biến null trước khi gọi persisted operation."""

from __future__ import annotations

import copy
from typing import Any

import pytest

pytest.importorskip("agents")
jsonschema = pytest.importorskip("jsonschema")

from agents.strict_schema import ensure_strict_json_schema

from apps.cosa.capabilities import workspace_context_read as mod
from apps.cosa.capabilities.workspace_context_read import (
    WORKSPACE_CONTEXT_READ_SPEC,
    create_workspace_context_read_handler,
)

_CTX = {"workspace_id": "w1", "principal": "u1", "role_id": "member"}


def _strict_schema() -> dict[str, Any]:
    return ensure_strict_json_schema(copy.deepcopy(WORKSPACE_CONTEXT_READ_SPEC.input_schema))


@pytest.mark.parametrize(
    ("operation_id", "variables", "expected"),
    [
        (
            "workspaceContext",
            {"question": "q", "query": None, "limit": None},
            {"question": "q"},
        ),
        (
            "enterpriseKnowledgeSearch",
            {"question": None, "query": "k", "limit": None},
            {"query": "k"},
        ),
        (
            "enterpriseKnowledgeSearch",
            {"question": None, "query": "k", "limit": 5},
            {"query": "k", "limit": 5},
        ),
    ],
)
@pytest.mark.asyncio
async def test_strict_schema_call_with_only_own_variables_reaches_operation(
    monkeypatch: pytest.MonkeyPatch,
    operation_id: str,
    variables: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    args = {"operation_id": operation_id, "variables": variables}
    # Model sinh args theo schema strict mà SDK gửi đi — phải hợp lệ.
    jsonschema.validate(args, _strict_schema())

    seen: dict[str, Any] = {}

    async def fake_execute(op: str, vars_: dict[str, Any], identity: Any, plane: Any) -> Any:
        seen.update(op=op, variables=vars_)
        return {"ok": True}

    monkeypatch.setattr(mod, "execute_persisted_operation", fake_execute)
    handler = create_workspace_context_read_handler(object())
    assert await handler(args, _CTX) == {"ok": True}
    assert seen == {"op": operation_id, "variables": expected}
