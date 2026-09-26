import pytest
from agent.contracts.errors import AgentRuntimeError, RuntimeErrorCode
from agent_integrations.openai_agents_sdk.tool_args import (
    apply_run_scope,
    tool_input_error_result,
)


class _Http422(Exception):
    status_code = 422
    detail = "unknown variables: ['query']; allowed for 'workspaceContext': ['question']"


class _Http500(Exception):
    status_code = 500


def test_4xx_becomes_error_result() -> None:
    r = tool_input_error_result(_Http422())
    assert r is not None and "unknown variables" in r["error"] and "hint" in r


def test_value_error_becomes_error_result() -> None:
    r = tool_input_error_result(ValueError("variables phải là object"))
    assert r is not None and "variables" in r["error"]


def test_5xx_and_runtime_errors_are_not_swallowed() -> None:
    assert tool_input_error_result(_Http500()) is None
    err = AgentRuntimeError(RuntimeErrorCode.TENANT_UNAUTHORIZED, "denied")
    assert tool_input_error_result(err) is None


SCOPE_SCHEMA = {"type": "object", "properties": {"project_id": {"type": "string"}}}


def test_fills_project_id_from_context() -> None:
    assert apply_run_scope({}, SCOPE_SCHEMA, {"project_id": "p1"}) == {"project_id": "p1"}


def test_keeps_matching_project_id() -> None:
    assert (
        apply_run_scope({"project_id": "p1"}, SCOPE_SCHEMA, {"project_id": "p1"})["project_id"]
        == "p1"
    )


def test_rejects_other_project() -> None:
    with pytest.raises(ValueError, match="project_id"):
        apply_run_scope({"project_id": "p2"}, SCOPE_SCHEMA, {"project_id": "p1"})


def test_no_change_when_schema_has_no_project_id_or_no_context() -> None:
    assert apply_run_scope({"a": 1}, {"properties": {}}, {"project_id": "p1"}) == {"a": 1}
    assert apply_run_scope({}, SCOPE_SCHEMA, {}) == {}
