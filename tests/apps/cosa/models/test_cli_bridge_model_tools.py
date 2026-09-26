"""`CliBridgeModel` — giao thức tool-call JSON cho CLI provider (Claude Code).

Trước đây agent có tool (vd `operations`) route sang `claude_cli` luôn fail
`CliBridgeUnsupportedCapability`, nên chat không thể chạy bằng Claude Code.
Giờ model chỉ *yêu cầu* gọi tool; việc thực thi vẫn do `FunctionTool` của SDK
(Capability Gateway + approval) — test dùng CLI subprocess thật."""

from __future__ import annotations

import json
import os
import stat

import pytest
from agents import Agent, FunctionTool, Runner
from openai.types.responses import ResponseFunctionToolCall, ResponseOutputMessage

from apps.cosa.models.cli_bridge import (
    CliBridge,
    CliBridgeModel,
    CliBridgeUnsupportedCapability,
    ModelInvocation,
    cli_env_overrides_from_environment,
)


def _make_executable(path, content: str) -> str:
    path.write_text(content)
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
    return str(path)


def _tool(name: str, calls: list[dict]) -> FunctionTool:
    async def _invoke(_ctx, args: str) -> str:
        calls.append(json.loads(args))
        return "3 tasks open"

    return FunctionTool(
        name=name,
        description="List open tasks",
        params_json_schema={"type": "object", "properties": {"limit": {"type": "integer"}}},
        on_invoke_tool=_invoke,
    )


@pytest.mark.asyncio
async def test_tool_call_json_becomes_function_call_item(tmp_path) -> None:
    cli = _make_executable(
        tmp_path / "fake-claude",
        "#!/bin/sh\ncat > /dev/null\n"
        'printf \'```json\\n{"tool_call": {"name": "operations_task_list", '
        '"arguments": {"limit": 3}}}\\n```\'\n',
    )
    model = CliBridgeModel(
        CliBridge(allowlist={cli: ()}), executable=cli, model_id=None, profile_id="p"
    )

    response = await model.get_response(
        "sys", "hi", None, [_tool("operations_task_list", [])], None, [], None
    )

    item = response.output[0]
    assert isinstance(item, ResponseFunctionToolCall)
    assert item.name == "operations_task_list"
    assert json.loads(item.arguments) == {"limit": 3}


@pytest.mark.asyncio
async def test_unknown_tool_name_is_never_turned_into_a_tool_call(tmp_path) -> None:
    cli = _make_executable(
        tmp_path / "fake-claude",
        "#!/bin/sh\ncat > /dev/null\n"
        'printf \'{"tool_call": {"name": "delete_everything", "arguments": {}}}\'\n',
    )
    model = CliBridgeModel(
        CliBridge(allowlist={cli: ()}), executable=cli, model_id=None, profile_id="p"
    )

    response = await model.get_response(
        None, "hi", None, [_tool("operations_task_list", [])], None, [], None
    )

    assert isinstance(response.output[0], ResponseOutputMessage)


@pytest.mark.asyncio
async def test_runner_executes_tool_via_function_tool_then_returns_text(tmp_path) -> None:
    """Vòng đầy đủ qua `agents.Runner`: lượt 1 CLI yêu cầu tool, SDK chạy
    đúng FunctionTool, lượt 2 prompt chứa `[tool_result]` và CLI trả chữ."""
    cli = _make_executable(
        tmp_path / "fake-claude",
        "#!/bin/sh\n"
        "input=$(cat)\n"
        'case "$input" in\n'
        '  *"3 tasks open"*) printf "Bạn có 3 task đang mở." ;;\n'
        '  *) printf \'{"tool_call": {"name": "operations_task_list", "arguments": {"limit": 5}}}\' ;;\n'
        "esac\n",
    )
    calls: list[dict] = []
    agent = Agent(
        name="ops",
        instructions="be helpful",
        tools=[_tool("operations_task_list", calls)],
        model=CliBridgeModel(
            CliBridge(allowlist={cli: ()}), executable=cli, model_id=None, profile_id="p"
        ),
    )

    result = await Runner.run(agent, "Tôi còn bao nhiêu task?")

    assert calls == [{"limit": 5}]
    assert result.final_output == "Bạn có 3 task đang mở."


@pytest.mark.asyncio
async def test_handoffs_still_rejected(tmp_path) -> None:
    cli = _make_executable(tmp_path / "fake-claude", "#!/bin/sh\necho ok\n")
    model = CliBridgeModel(
        CliBridge(allowlist={cli: ()}), executable=cli, model_id=None, profile_id="p"
    )
    with pytest.raises(CliBridgeUnsupportedCapability):
        await model.get_response(None, "hi", None, [], None, [object()], None)


@pytest.mark.asyncio
async def test_cli_runs_in_empty_temp_dir_with_executable_dir_on_path(tmp_path) -> None:
    """cwd tạm rỗng (CLI không nạp CLAUDE.md/mã nguồn của worker) và PATH có
    thư mục của executable (script npm `#!/usr/bin/env node`)."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    cli = _make_executable(
        bin_dir / "fake-claude",
        '#!/bin/sh\ncat > /dev/null\nprintf "%s|%s|%s" "$(pwd)" "$(ls -A | wc -l)" "$PATH"\n',
    )
    response = await CliBridge(allowlist={cli: ()}).invoke(
        ModelInvocation(executable=cli, prompt="x")
    )
    cwd, entries, path = response.text.split("|")
    assert cwd != os.getcwd()
    assert entries.strip() == "0"
    assert path.split(":")[0] == str(bin_dir)


def test_cli_home_is_opt_in(monkeypatch) -> None:
    monkeypatch.delenv("COSA_CLI_HOME", raising=False)
    assert cli_env_overrides_from_environment() == {}

    monkeypatch.setenv("COSA_CLI_HOME", "/srv/cosa-cli-home")
    monkeypatch.setenv("USER", "cosa")
    overrides = cli_env_overrides_from_environment()
    assert overrides["HOME"] == "/srv/cosa-cli-home"
    assert overrides["USER"] == "cosa"
