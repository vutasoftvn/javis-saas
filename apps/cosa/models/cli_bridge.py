"""Task 3 (plan 2026-09-07-local-first-model-routing) — constrained
subprocess bridge cho CLI provider (`claude`/`codex`/`gemini`) — thay thế
`NotImplementedError` mà `ModelProviderFactory` (Task 2) raise cho
`ProviderType.CLAUDE_CLI`/`CODEX_CLI`/`GEMINI_CLI`.

Ràng buộc toàn cục (BẮT BUỘC, xem plan §Global Constraints):
- KHÔNG BAO GIỜ dùng shell string (`asyncio.create_subprocess_shell`) — chỉ
  `asyncio.create_subprocess_exec` với argv list tường minh.
- Absolute-path executable allowlist: bất kỳ `executable` nào KHÔNG có mặt
  trong allowlist (kể cả path tương đối, hay 1 absolute path hợp lệ nhưng
  không thuộc allowlist — vd `/bin/sh`) đều bị từ chối TRƯỚC khi spawn.
- Argument template CỐ ĐỊNH mỗi CLI — caller KHÔNG được truyền flag tuỳ ý qua
  `ModelInvocation` (chỉ có prompt/model_id/timeout/profile_id).
- Environment tối giản, dựng tường minh — KHÔNG BAO GIỜ `os.environ.copy()`
  hay kế thừa nguyên vẹn môi trường tiến trình cha (rò browser/session token,
  `$HOME`, biến provider khác). Mặc định chỉ có `PATH` (subprocess cần resolve
  dynamic linker/thư viện hệ thống) — caller có thể thêm override tường minh
  (vd `LANG` để output ổn định) qua `env_overrides`, không phải qua env cha.
- Prompt truyền qua stdin — không qua argv (lộ vào process listing `ps aux`),
  không qua env (lộ vào `/proc/<pid>/environ` hay tool đọc env của con).
- stdout bị giới hạn kích thước bằng bounded reader (đọc theo chunk, không
  dùng `process.communicate()` không giới hạn) — chặn CLI in ra vô hạn làm
  tràn bộ nhớ worker.
- Semaphore theo `profile_id` — giới hạn concurrency cho từng profile, không
  để 1 profile spawn vô hạn tiến trình song song.
- Timeout: SIGKILL CẢ process group (không chỉ tiến trình con trực tiếp) —
  `start_new_session=True` khi spawn (tiến trình con + mọi cháu nó tự fork mà
  không gọi setsid() lại đều nằm chung group mới), sau đó `os.killpg(pgid,
  SIGKILL)`. Dùng SIGKILL (không phải SIGTERM trước) vì CLI có thể cố tình
  hoặc vô tình bỏ qua SIGTERM — timeout ở đây là hard bound, không phải
  graceful-shutdown request.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import re
import shutil
import signal
import tempfile
import uuid
from typing import Any

from agents.items import ModelResponse as SdkModelResponse
from agents.models.interface import Model as SdkModel
from agents.usage import Usage
from openai.types.responses import (
    ResponseFunctionToolCall,
    ResponseOutputMessage,
    ResponseOutputText,
)
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

__all__ = [
    "CliBridge",
    "CliBridgeDenied",
    "CliBridgeExecutionError",
    "CliBridgeModel",
    "CliBridgeUnsupportedCapability",
    "ModelInvocation",
    "ModelProviderTimeout",
    "ModelResponse",
    "cli_env_overrides_from_environment",
]


class CliBridgeDenied(Exception):
    """`executable` không có trong allowlist tuyệt đối — từ chối spawn TRƯỚC
    khi gọi `asyncio.create_subprocess_exec` (không tạo tiến trình nào)."""


class ModelProviderTimeout(Exception):
    """Subprocess vượt quá `timeout_seconds` — process group đã bị SIGKILL."""


class CliBridgeExecutionError(Exception):
    """Subprocess thoát với returncode khác 0 — message chỉ chứa returncode +
    stderr đã cắt ngắn (stderr của CLI cục bộ, không phải payload provider
    API nên không cần đi qua `redact_provider_payload`; vẫn cắt để tránh log
    phình to nếu CLI in traceback dài)."""


class CliBridgeUnsupportedCapability(Exception):
    """CLI bridge là text-in/text-out — handoffs/structured-output của OpenAI
    Agents SDK không dịch được nên raise rõ ràng. Tool-calling thì CÓ hỗ trợ
    qua giao thức JSON (`_render_tool_protocol`/`_parse_tool_call`): model chỉ
    *yêu cầu* gọi tool, việc thực thi + policy/approval vẫn do `FunctionTool`
    của kernel đảm nhiệm (rule 8, CLAUDE.md), không bao giờ bỏ qua tool âm
    thầm."""


class ModelInvocation(BaseModel):
    """1 lần gọi CLI bridge — `extra="forbid"` chặn caller nhét thêm field lạ
    (vd 1 flag tuỳ ý nào đó cải trang thành field mới)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    executable: str
    prompt: str
    model_id: str | None = None
    timeout_seconds: float = 60.0
    profile_id: str = "default"


class ModelResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str


# ── Allowlist mặc định cho 3 CLI thật — path/flag là placeholder hợp lý cho
# non-interactive/print-mode của từng CLI; PHẢI xác nhận lại đúng flag thật
# (vd `claude --print`, `codex exec`, `gemini` non-interactive) khi cấu hình
# CLI thật trên 1 máy cụ thể trước khi bật provider này ở production — path
# override qua `COSA_CLI_<ROLE>_PATH` env (đọc lúc dựng allowlist, không phải
# lúc import module, để test/composition monkeypatch được).
_DEFAULT_ROLE_PATH: dict[str, str] = {
    "claude": "/usr/local/bin/claude",
    "codex": "/usr/local/bin/codex",
    "gemini": "/usr/local/bin/gemini",
}
_DEFAULT_ROLE_ARGV: dict[str, tuple[str, ...]] = {
    # Claude Code chỉ được làm "bộ não" trả lời chữ: tắt mọi tool built-in
    # (Bash/đọc-ghi file/web...) — tool nghiệp vụ đi qua giao thức JSON của
    # `CliBridgeModel` để vẫn qua Capability Gateway + Governance của COSA.
    "claude": (
        "--print",
        "--output-format",
        "text",
        "--disallowedTools",
        "Bash",
        "Edit",
        "Write",
        "Read",
        "Glob",
        "Grep",
        "NotebookEdit",
        "WebFetch",
        "WebSearch",
        "Task",
    ),
    "codex": ("exec", "--skip-git-repo-check"),
    "gemini": ("--prompt", "-"),
}
_ROLE_PATH_ENV: dict[str, str] = {
    "claude": "COSA_CLI_CLAUDE_PATH",
    "codex": "COSA_CLI_CODEX_PATH",
    "gemini": "COSA_CLI_GEMINI_PATH",
}

_BASE_PATH_ENTRIES = ("/usr/bin", "/bin", "/usr/local/bin", "/opt/homebrew/bin")

_MAX_STDOUT_BYTES = 1_000_000  # 1 MiB — đủ cho 1 câu trả lời text, chặn tràn bộ nhớ.
_READ_CHUNK_BYTES = 65536


def cli_env_overrides_from_environment() -> dict[str, str]:
    """Env tường minh cho CLI provider, do OPERATOR bật (không kế thừa ngầm).

    CLI như Claude Code xác thực bằng phiên đăng nhập cục bộ nằm dưới `$HOME`
    (`~/.claude`, hoặc Keychain trên macOS) — không có HOME thì `claude
    --print` báo chưa đăng nhập. Chỉ khi `COSA_CLI_HOME` được đặt mới truyền
    HOME (nên trỏ tới 1 home riêng chỉ chứa phiên đăng nhập CLI; dev máy cá
    nhân có thể đặt = $HOME) + USER/LOGNAME (Keychain macOS cần). Không đặt
    -> giữ nguyên env tối giản như trước."""
    cli_home = os.environ.get("COSA_CLI_HOME", "").strip()
    if not cli_home:
        return {}
    overrides = {"HOME": cli_home}
    for key in ("USER", "LOGNAME"):
        value = os.environ.get(key)
        if value:
            overrides[key] = value
    return overrides


class CliBridge:
    """Bridge subprocess CLI dùng chung cho `claude_cli`/`codex_cli`/
    `gemini_cli`. Không biết gì về `ProviderType`/`ResolvedModelRoute` (Task 1)
    — nhận thẳng `executable` tuyệt đối trong `ModelInvocation`, giữ module
    này độc lập/dễ test (composition layer ở `providers.py` mới biết map
    provider_type -> role -> executable)."""

    def __init__(
        self,
        *,
        allowlist: dict[str, tuple[str, ...]] | None = None,
        max_concurrency_per_profile: int = 2,
        env_overrides: dict[str, str] | None = None,
    ) -> None:
        self._allowlist: dict[str, tuple[str, ...]] = (
            dict(allowlist) if allowlist is not None else self._default_allowlist()
        )
        self._role_paths: dict[str, str] = self._resolve_role_paths()
        self._max_concurrency = max_concurrency_per_profile
        self._semaphores: dict[str, asyncio.Semaphore] = {}
        self._env_overrides = dict(env_overrides or {})

    @staticmethod
    def _resolve_role_paths() -> dict[str, str]:
        paths: dict[str, str] = {}
        for role, default_path in _DEFAULT_ROLE_PATH.items():
            configured = os.environ.get(_ROLE_PATH_ENV[role])
            if configured:
                paths[role] = configured
                continue
            # Default `/usr/local/bin/<cli>` thường không đúng trên macOS
            # (Homebrew `/opt/homebrew/bin`, installer native `~/.local/bin`).
            # Chỉ khi default không tồn tại mới dò `PATH` của tiến trình
            # worker (do operator cấu hình, không phải input người dùng) và
            # CHỐT thành path tuyệt đối — allowlist vẫn là path tuyệt đối cố
            # định lúc dựng bridge.
            discovered = None if os.path.exists(default_path) else shutil.which(role)
            paths[role] = os.path.abspath(discovered) if discovered else default_path
        return paths

    @classmethod
    def _default_allowlist(cls) -> dict[str, tuple[str, ...]]:
        role_paths = cls._resolve_role_paths()
        return {role_paths[role]: _DEFAULT_ROLE_ARGV[role] for role in role_paths}

    def executable_for_role(self, role: str) -> str:
        """Trả path tuyệt đối đã cấu hình (env override hoặc default) cho 1
        role ("claude"/"codex"/"gemini"). Path này LUÔN có mặt trong
        allowlist mặc định — nếu caller tự truyền `allowlist=` khác lúc dựng
        bridge (vd test) mà không chứa role này, `invoke()` vẫn sẽ từ chối
        đúng như thiết kế (fail-closed), `executable_for_role` chỉ trả path
        cấu hình, không tự đảm bảo nó nằm trong allowlist hiện tại."""
        try:
            return self._role_paths[role]
        except KeyError as exc:
            raise CliBridgeDenied(f"role CLI '{role}' không được hỗ trợ.") from exc

    def _semaphore_for(self, profile_id: str) -> asyncio.Semaphore:
        sem = self._semaphores.get(profile_id)
        if sem is None:
            sem = asyncio.Semaphore(self._max_concurrency)
            self._semaphores[profile_id] = sem
        return sem

    def _build_env(self, executable: str) -> dict[str, str]:
        # KHÔNG bao giờ os.environ.copy() ở đây — xem module docstring.
        # Thêm thư mục chứa chính executable (đã qua allowlist) vào PATH: CLI
        # cài qua npm/Homebrew là script `#!/usr/bin/env node`, cần tìm thấy
        # `node` nằm cùng thư mục đó.
        path_entries = [os.path.dirname(executable), *_BASE_PATH_ENTRIES]
        env = {"PATH": ":".join(dict.fromkeys(p for p in path_entries if p))}
        env.update(self._env_overrides)
        return env

    async def invoke(self, request: ModelInvocation) -> ModelResponse:
        if request.executable not in self._allowlist:
            raise CliBridgeDenied(
                f"executable '{request.executable}' không nằm trong allowlist CLI "
                "bridge — từ chối spawn (không tạo tiến trình nào)."
            )
        argv = [request.executable, *self._allowlist[request.executable]]

        semaphore = self._semaphore_for(request.profile_id)
        async with semaphore:
            return await self._run_subprocess(argv, request)

    async def _run_subprocess(self, argv: list[str], request: ModelInvocation) -> ModelResponse:
        env = self._build_env(argv[0])
        # cwd là thư mục tạm rỗng: CLI agent (vd Claude Code) tự nạp
        # `CLAUDE.md`/file dự án từ cwd — không được để nó thấy mã nguồn/cấu
        # hình của worker rồi trộn vào câu trả lời cho founder.
        with tempfile.TemporaryDirectory(prefix="cosa-cli-") as workdir:
            return await self._spawn_and_collect(argv, request, env, workdir)

    async def _spawn_and_collect(
        self,
        argv: list[str],
        request: ModelInvocation,
        env: dict[str, str],
        workdir: str,
    ) -> ModelResponse:
        process = await asyncio.create_subprocess_exec(
            *argv,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=workdir,
            start_new_session=True,  # tiến trình con + cháu nó vào 1 process group riêng
        )
        # `start_new_session=True` -> process.pid CHÍNH LÀ pgid của group mới.
        pgid = process.pid
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                self._communicate_bounded(process, request.prompt),
                timeout=request.timeout_seconds,
            )
        except TimeoutError:
            await self._kill_process_group(pgid, process)
            raise ModelProviderTimeout(
                f"CLI '{request.executable}' vượt quá timeout "
                f"{request.timeout_seconds}s — đã SIGKILL cả process group."
            ) from None
        except BaseException:
            await self._kill_process_group(pgid, process)
            raise

        if process.returncode not in (0, None):
            stderr_preview = stderr_bytes.decode("utf-8", errors="replace")[:2000]
            raise CliBridgeExecutionError(
                f"CLI '{request.executable}' thoát với returncode="
                f"{process.returncode}: {stderr_preview}"
            )

        return ModelResponse(text=stdout_bytes.decode("utf-8", errors="replace").strip())

    async def _communicate_bounded(
        self, process: asyncio.subprocess.Process, prompt: str
    ) -> tuple[bytes, bytes]:
        assert process.stdin is not None
        assert process.stdout is not None
        assert process.stderr is not None

        # CLI có thể thoát (hoặc đóng stdin) trước khi đọc hết prompt — giống
        # `communicate()`, bỏ qua broken pipe và vẫn đọc stdout/exit code thật;
        # nếu không, race này làm invoke fail dù CLI chạy thành công.
        with contextlib.suppress(BrokenPipeError, ConnectionResetError):
            process.stdin.write(prompt.encode("utf-8"))
            await process.stdin.drain()
        process.stdin.close()

        stdout_chunks: list[bytes] = []
        total = 0
        while True:
            chunk = await process.stdout.read(_READ_CHUNK_BYTES)
            if not chunk:
                break
            total += len(chunk)
            if total > _MAX_STDOUT_BYTES:
                overflow = total - _MAX_STDOUT_BYTES
                stdout_chunks.append(chunk[: len(chunk) - overflow])
                # Xả nốt phần còn lại (không giữ trong bộ nhớ) để tránh CLI bị
                # block ghi (broken pipe nếu ta đóng fd sớm trong lúc nó vẫn in).
                while await process.stdout.read(_READ_CHUNK_BYTES):
                    pass
                break
            stdout_chunks.append(chunk)

        stderr_bytes = await process.stderr.read()
        await process.wait()
        return b"".join(stdout_chunks), stderr_bytes

    async def _kill_process_group(self, pgid: int, process: asyncio.subprocess.Process) -> None:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(pgid, signal.SIGKILL)
        with contextlib.suppress(TimeoutError, ProcessLookupError):
            await asyncio.wait_for(process.wait(), timeout=2.0)


# ── Adapter cho OpenAI Agents SDK `agents.models.interface.Model` ──
#
# `Agent.__post_init__` (packages agents SDK, `agents/agent.py`) raise
# TypeError nếu `model` không phải str/None/instance của
# `agents.models.interface.Model` — bắt buộc subclass thật, không thể chỉ duck-
# type `ModelClient = Any` như factory hiện tại làm với LitellmModel. Xem ghi
# chú giới hạn ở `CliBridgeUnsupportedCapability` — đây là 1 adapter TỐI THIỂU
# (text-only), KHÔNG dịch được tool-calling/handoffs/structured-output sang
# giao thức của CLI subprocess; xem task-3-report.md phần "SDK model-interface
# fit" để biết lý do và rủi ro đã cân nhắc.


def _extract_text(item: Any) -> str:
    if isinstance(item, str):
        return item
    content = item.get("content") if isinstance(item, dict) else getattr(item, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts: list[str] = []
        for part in content:
            text = part.get("text") if isinstance(part, dict) else getattr(part, "text", None)
            if text:
                texts.append(str(text))
        return "\n".join(texts)
    return ""


def _item_field(item: Any, key: str) -> Any:
    return item.get(key) if isinstance(item, dict) else getattr(item, key, None)


def _render_prompt(system_instructions: str | None, input_items: Any, tools: Any = None) -> str:
    parts: list[str] = []
    if system_instructions:
        parts.append(f"[system]\n{system_instructions}")
    if tools:
        parts.append(_render_tool_protocol(tools))
    if isinstance(input_items, str):
        parts.append(input_items)
    else:
        for item in input_items or []:
            item_type = _item_field(item, "type")
            if item_type == "function_call":
                parts.append(
                    "[assistant tool_call]\n"
                    + json.dumps(
                        {
                            "tool_call": {
                                "name": _item_field(item, "name"),
                                "arguments": _safe_json(_item_field(item, "arguments")),
                            }
                        },
                        ensure_ascii=False,
                    )
                )
                continue
            if item_type == "function_call_output":
                parts.append(f"[tool_result]\n{_item_field(item, 'output')}")
                continue
            role = _item_field(item, "role") or "user"
            text = _extract_text(item)
            if text:
                parts.append(f"[{role}]\n{text}")
    return "\n\n".join(parts)


def _safe_json(raw: Any) -> Any:
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except ValueError:
            return raw
    return raw


def _render_tool_protocol(tools: Any) -> str:
    """CLI là text-in/text-out — mô tả tool + giao thức JSON trong prompt để
    model yêu cầu gọi tool. Tool KHÔNG chạy ở đây: `get_response` trả
    `ResponseFunctionToolCall`, SDK gọi đúng `FunctionTool` (Capability
    Gateway + policy/approval của kernel), rồi trả `[tool_result]` ở lượt sau."""
    catalog = [
        {
            "name": getattr(tool, "name", ""),
            "description": getattr(tool, "description", "") or "",
            "parameters": getattr(tool, "params_json_schema", None) or {"type": "object"},
        }
        for tool in tools
    ]
    return (
        "[tools]\n"
        "You can call the following tools. To call one, reply with ONLY a JSON object "
        'of the form {"tool_call": {"name": "<tool name>", "arguments": {...}}} and '
        "nothing else. Call at most one tool per reply. After a [tool_result] you may "
        "call another tool or give your final answer. If no tool is needed, reply with "
        "the final answer as plain text (never claim an action happened unless a "
        "[tool_result] confirms it).\n" + json.dumps(catalog, ensure_ascii=False)
    )


_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


def _parse_tool_call(text: str, tool_names: set[str]) -> tuple[str, str] | None:
    """Trả (name, arguments_json) nếu toàn bộ câu trả lời là 1 yêu cầu gọi
    tool hợp lệ; None nếu là câu trả lời chữ. Chỉ chấp nhận tool có trong
    danh sách của agent — tên lạ không bao giờ thành tool call."""
    candidate = text.strip()
    fence = _CODE_FENCE_RE.match(candidate)
    if fence:
        candidate = fence.group(1).strip()
    if not (candidate.startswith("{") and candidate.endswith("}")):
        return None
    try:
        payload = json.loads(candidate)
    except ValueError:
        return None
    call = payload.get("tool_call") if isinstance(payload, dict) else None
    if not isinstance(call, dict):
        return None
    name = call.get("name")
    if not isinstance(name, str) or name not in tool_names:
        return None
    arguments = call.get("arguments") or {}
    if isinstance(arguments, str):
        arguments = _safe_json(arguments)
    if not isinstance(arguments, dict):
        return None
    return name, json.dumps(arguments, ensure_ascii=False)


class CliBridgeModel(SdkModel):
    """Bọc `CliBridge` để dùng làm `model=` cho `agents.Agent` — bắt buộc
    subclass `agents.models.interface.Model` thật (không chỉ duck-type):
    `Agent.__post_init__` (agents SDK) raise TypeError nếu `model` không phải
    str/None/instance của class này."""

    def __init__(
        self,
        bridge: CliBridge,
        *,
        executable: str,
        model_id: str | None,
        profile_id: str,
        timeout_seconds: float = 120.0,
    ) -> None:
        self._bridge = bridge
        self._executable = executable
        self._model_id = model_id
        self._profile_id = profile_id
        self._timeout_seconds = timeout_seconds

    async def get_response(
        self,
        system_instructions: str | None,
        input: Any,
        model_settings: Any,
        tools: Any,
        output_schema: Any,
        handoffs: Any,
        tracing: Any,
        *,
        previous_response_id: str | None = None,
        conversation_id: str | None = None,
        prompt: Any = None,
    ) -> Any:
        if handoffs:
            raise CliBridgeUnsupportedCapability(
                "CLI bridge model không hỗ trợ handoffs giữa các agent."
            )
        if output_schema is not None:
            raise CliBridgeUnsupportedCapability(
                "CLI bridge model không hỗ trợ structured output_schema."
            )

        rendered_prompt = _render_prompt(system_instructions, input, tools)
        response = await self._bridge.invoke(
            ModelInvocation(
                executable=self._executable,
                prompt=rendered_prompt,
                model_id=self._model_id,
                timeout_seconds=self._timeout_seconds,
                profile_id=self._profile_id,
            )
        )

        response_id = f"cli_bridge_resp_{uuid.uuid4().hex[:12]}"
        tool_names = {getattr(tool, "name", "") for tool in tools or []}
        tool_call = _parse_tool_call(response.text, tool_names) if tool_names else None
        if tool_call is not None:
            name, arguments = tool_call
            output: list[Any] = [
                ResponseFunctionToolCall(
                    type="function_call",
                    id=f"cli_bridge_fc_{uuid.uuid4().hex[:12]}",
                    call_id=f"call_{uuid.uuid4().hex[:16]}",
                    name=name,
                    arguments=arguments,
                    status="completed",
                )
            ]
        else:
            output = [
                ResponseOutputMessage(
                    id=f"cli_bridge_msg_{uuid.uuid4().hex[:12]}",
                    role="assistant",
                    status="completed",
                    type="message",
                    content=[
                        ResponseOutputText(text=response.text, type="output_text", annotations=[])
                    ],
                )
            ]

        return SdkModelResponse(output=output, usage=Usage(), response_id=response_id)

    def stream_response(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("CliBridgeModel chưa hỗ trợ streaming — ngoài phạm vi Task 3.")
