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
import logging
import os
import signal
from typing import Any

from agents.items import ModelResponse as SdkModelResponse
from agents.models.interface import Model as SdkModel
from agents.usage import Usage
from openai.types.responses import ResponseOutputMessage, ResponseOutputText
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
    """CLI bridge là text-in/text-out thuần — không nói được giao thức
    function-calling/structured-output của OpenAI Agents SDK Responses API.
    Raise rõ ràng thay vì âm thầm bỏ qua tool: 1 agent có tool rủi ro cao
    (approval-gated) bị route sang CLI provider mà không gọi được tool đó
    PHẢI báo lỗi, không được coi là "chạy xong, chỉ trả lời chữ" (rule 8,
    CLAUDE.md — hành động rủi ro cao cần approval qua code, không qua prompt;
    im lặng bỏ qua khả năng gọi tool tương đương né luôn cả gate đó)."""


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
    "claude": ("--print", "--output-format", "text"),
    "codex": ("exec", "--skip-git-repo-check"),
    "gemini": ("--prompt", "-"),
}
_ROLE_PATH_ENV: dict[str, str] = {
    "claude": "COSA_CLI_CLAUDE_PATH",
    "codex": "COSA_CLI_CODEX_PATH",
    "gemini": "COSA_CLI_GEMINI_PATH",
}

_MAX_STDOUT_BYTES = 1_000_000  # 1 MiB — đủ cho 1 câu trả lời text, chặn tràn bộ nhớ.
_READ_CHUNK_BYTES = 65536


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
        return {
            role: os.environ.get(_ROLE_PATH_ENV[role], default_path)
            for role, default_path in _DEFAULT_ROLE_PATH.items()
        }

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

    def _build_env(self) -> dict[str, str]:
        # KHÔNG bao giờ os.environ.copy() ở đây — xem module docstring.
        env = {"PATH": "/usr/bin:/bin:/usr/local/bin"}
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
        env = self._build_env()
        process = await asyncio.create_subprocess_exec(
            *argv,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
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


def _render_prompt(system_instructions: str | None, input_items: Any) -> str:
    parts: list[str] = []
    if system_instructions:
        parts.append(f"[system]\n{system_instructions}")
    if isinstance(input_items, str):
        parts.append(input_items)
    else:
        for item in input_items or []:
            role = (
                item.get("role") if isinstance(item, dict) else getattr(item, "role", None)
            ) or "user"
            text = _extract_text(item)
            if text:
                parts.append(f"[{role}]\n{text}")
    return "\n\n".join(parts)


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
        if tools:
            raise CliBridgeUnsupportedCapability(
                f"CLI bridge model không hỗ trợ tool-calling — agent có "
                f"{len(tools)} tool đã cấu hình nhưng route đã resolve sang CLI "
                "provider (text-only). Không tự động bỏ qua tool."
            )
        if handoffs:
            raise CliBridgeUnsupportedCapability(
                "CLI bridge model không hỗ trợ handoffs giữa các agent."
            )
        if output_schema is not None:
            raise CliBridgeUnsupportedCapability(
                "CLI bridge model không hỗ trợ structured output_schema."
            )

        rendered_prompt = _render_prompt(system_instructions, input)
        response = await self._bridge.invoke(
            ModelInvocation(
                executable=self._executable,
                prompt=rendered_prompt,
                model_id=self._model_id,
                timeout_seconds=self._timeout_seconds,
                profile_id=self._profile_id,
            )
        )

        return SdkModelResponse(
            output=[
                ResponseOutputMessage(
                    id="cli_bridge_msg_1",
                    role="assistant",
                    status="completed",
                    type="message",
                    content=[
                        ResponseOutputText(text=response.text, type="output_text", annotations=[])
                    ],
                )
            ],
            usage=Usage(),
            response_id="cli_bridge_resp_1",
        )

    def stream_response(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("CliBridgeModel chưa hỗ trợ streaming — ngoài phạm vi Task 3.")
