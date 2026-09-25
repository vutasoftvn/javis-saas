"""Task 3 (plan 2026-09-07-local-first-model-routing) — `CliBridge`: subprocess
bridge cho `claude`/`codex`/`gemini` CLI. Spawn thật (không mock
`asyncio.create_subprocess_exec`) qua 1 script fixture thật dưới `tmp_path` —
chứng minh allowlist/timeout/process-group-kill hoạt động với tiến trình thật,
không chỉ với assertion trên call args.
"""

from __future__ import annotations

import os
import stat
import time

import pytest

from apps.cosa.models.cli_bridge import (
    CliBridge,
    CliBridgeDenied,
    CliBridgeExecutionError,
    ModelInvocation,
    ModelProviderTimeout,
    ModelResponse,
)


def _make_executable(path, content: str) -> None:
    path.write_text(content)
    mode = os.stat(path).st_mode
    os.chmod(path, mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


@pytest.fixture
def echo_script(tmp_path):
    """CLI fixture thật: đọc stdin, in ngược lại kèm prefix — dùng để chứng
    minh prompt đi qua stdin (không phải argv/env) và output được nhận đúng."""
    path = tmp_path / "fake-echo-cli"
    _make_executable(
        path,
        '#!/bin/sh\nread -r line\nprintf "echo:%s" "$line"\n',
    )
    return str(path)


@pytest.fixture
def hang_script(tmp_path):
    """CLI fixture thật: bỏ qua SIGTERM, spawn 1 grandchild `sleep`, rồi tự
    ngủ vô hạn — dùng để chứng minh timeout kill CẢ process group (không chỉ
    tiến trình con trực tiếp) và không bị chặn bởi 1 process ignore SIGTERM."""
    pidfile = tmp_path / "grandchild.pid"
    path = tmp_path / "fake-hang-cli"
    _make_executable(
        path,
        "#!/bin/sh\ntrap '' TERM\nsleep 100 &\necho $! > '" + str(pidfile) + "'\nwait\n",
    )
    return str(path), pidfile


@pytest.fixture
def bridge(echo_script, hang_script):
    hang_path, _ = hang_script
    return CliBridge(
        allowlist={
            echo_script: (),
            hang_path: (),
        },
        max_concurrency_per_profile=2,
    )


@pytest.mark.asyncio
async def test_cli_bridge_rejects_shell_and_kills_timeout(bridge, hang_script) -> None:
    hang_path, pidfile = hang_script

    # 1) Executable KHÔNG nằm trong allowlist (kể cả 1 shell thật, tồn tại
    # trên máy) -> từ chối TRƯỚC khi spawn bất kỳ tiến trình nào.
    with pytest.raises(CliBridgeDenied):
        await bridge.invoke(ModelInvocation(executable="/bin/sh", prompt="x"))

    # 2) Executable ĐÃ allowlist nhưng chạy quá timeout -> ModelProviderTimeout,
    # cả process group (bao gồm grandchild) bị SIGKILL.
    with pytest.raises(ModelProviderTimeout):
        await bridge.invoke(ModelInvocation(executable=hang_path, prompt="x", timeout_seconds=0.6))

    # Chờ ngắn để hệ điều hành reap xong, rồi xác nhận grandchild đã chết —
    # chứng minh kill nhắm vào cả PROCESS GROUP, không chỉ tiến trình con
    # trực tiếp (script cha có "trap '' TERM" nên nếu chỉ SIGTERM tiến trình
    # cha, nó sẽ bỏ qua và grandchild vẫn sống).
    grandchild_pid: int | None = None
    for _ in range(50):
        if pidfile.exists():
            content = pidfile.read_text().strip()
            if content:
                grandchild_pid = int(content)
                break
        time.sleep(0.05)
    assert grandchild_pid is not None, "grandchild pid was never written by fixture script"

    for _ in range(50):
        try:
            os.kill(grandchild_pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.05)
    else:
        pytest.fail(f"grandchild pid {grandchild_pid} still alive after process-group kill")


@pytest.mark.asyncio
async def test_cli_bridge_denies_unlisted_absolute_path(bridge) -> None:
    with pytest.raises(CliBridgeDenied):
        await bridge.invoke(ModelInvocation(executable="/usr/bin/env", prompt="x"))


@pytest.mark.asyncio
async def test_cli_bridge_denies_relative_path(bridge) -> None:
    with pytest.raises(CliBridgeDenied):
        await bridge.invoke(ModelInvocation(executable="fake-echo-cli", prompt="x"))


@pytest.mark.asyncio
async def test_cli_bridge_sends_prompt_via_stdin_and_returns_stdout(bridge, echo_script) -> None:
    response = await bridge.invoke(
        ModelInvocation(executable=echo_script, prompt="hello-from-stdin\n")
    )
    assert isinstance(response, ModelResponse)
    assert response.text == "echo:hello-from-stdin"


@pytest.mark.asyncio
async def test_cli_bridge_does_not_inherit_parent_environment(tmp_path) -> None:
    """Rule bắt buộc của Task 3: KHÔNG kế thừa `$HOME`/session token của tiến
    trình cha — chỉ 1 env tối giản (PATH mặc định)."""
    path = tmp_path / "fake-env-cli"
    _make_executable(
        path,
        '#!/bin/sh\nprintf "HOME=%s SECRET_TOKEN=%s" "$HOME" "$SECRET_TOKEN"\n',
    )
    bridge_local = CliBridge(allowlist={str(path): ()})

    os.environ["SECRET_TOKEN"] = "must-not-leak-into-subprocess"
    try:
        response = await bridge_local.invoke(ModelInvocation(executable=str(path), prompt="x"))
    finally:
        del os.environ["SECRET_TOKEN"]

    assert "must-not-leak-into-subprocess" not in response.text
    assert response.text.startswith("HOME= ")


@pytest.mark.asyncio
async def test_cli_bridge_caps_stdout_size(tmp_path) -> None:
    path = tmp_path / "fake-flood-cli"
    _make_executable(
        path,
        "#!/bin/sh\nread -r line\nyes A | head -c 5000000\n",
    )
    bridge_local = CliBridge(allowlist={str(path): ()})

    response = await bridge_local.invoke(
        ModelInvocation(executable=str(path), prompt="x", timeout_seconds=10)
    )
    assert len(response.text.encode("utf-8")) <= 1_000_000


@pytest.mark.asyncio
async def test_cli_bridge_nonzero_exit_raises_execution_error(tmp_path) -> None:
    path = tmp_path / "fake-fail-cli"
    _make_executable(
        path,
        "#!/bin/sh\nread -r line\necho 'boom' 1>&2\nexit 3\n",
    )
    bridge_local = CliBridge(allowlist={str(path): ()})

    with pytest.raises(CliBridgeExecutionError):
        await bridge_local.invoke(ModelInvocation(executable=str(path), prompt="x"))


@pytest.mark.asyncio
async def test_cli_bridge_rejects_extra_fields_on_invocation() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ModelInvocation(executable="/bin/sh", prompt="x", extra_flag="--danger")  # type: ignore[call-arg]


@pytest.mark.asyncio
async def test_cli_bridge_tolerates_cli_that_exits_without_reading_stdin(tmp_path) -> None:
    # Prompt lớn hơn buffer pipe: CLI thoát mà không đọc stdin phải không làm
    # invoke fail vì broken pipe — kết quả vẫn lấy từ stdout/exit code thật.
    path = tmp_path / "fake-ignore-stdin-cli"
    _make_executable(path, '#!/bin/sh\nexec 0<&-\nsleep 0.3\nprintf "ok"\n')
    bridge_local = CliBridge(allowlist={str(path): ()})

    response = await bridge_local.invoke(
        ModelInvocation(executable=str(path), prompt="x" * 2_000_000)
    )
    assert response.text == "ok"
