from agent.contracts.errors import AgentRuntimeError, RuntimeErrorCode

from agent_integrations.openai_agents_sdk.tool_args import tool_input_error_result


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
