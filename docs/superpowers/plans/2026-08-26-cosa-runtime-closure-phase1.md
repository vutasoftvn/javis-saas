# COSA Runtime Closure — Phase 1 (Runtime Closure) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop COSA production agent runs from silently returning fake (keyword-matched mock) responses, and promote `RealOpenAIAgentsSDKKernel` (real `agents.Runner`, real DeepSeek via LiteLLM) as the actual kernel behind `runtime="openai_agents"`, per `ADR-RUNTIME-002` and `docs/implementation/production-runtime-closure.md` §Phase 1.

**Architecture:** `packages/agent_core/kernel/openai_agents_kernel.py::OpenAIAgentsKernel` (manual reasoning loop) is renamed to `ManualToolLoopKernel` and its implicit mock-fallback in `_call_model()` is removed — model behavior in tests now comes from an explicit test double (`MockToolLoopModelClient`), never from an implicit `None` check. `apps/cosa/composition/agent_plane.py::build_cosa_agent_plane(runtime="openai_agents")` (the default) now constructs `RealOpenAIAgentsSDKKernel` from `packages/agent_integrations/openai_agents_sdk/kernel.py`, wired to a real DeepSeek model built from `DEEPSEEK_API_KEY/DEEPSEEK_BASE_URL/DEEPSEEK_DEFAULT_MODEL` via a new `apps/cosa/composition/model_provider.py::build_deepseek_model()` factory (fail-fast if `DEEPSEEK_API_KEY` missing). The old manual kernel is still reachable via the new explicit `runtime="manual_tool_loop"` value. A latent governance-context bug in `RealOpenAIAgentsSDKKernel.run()` (building policy context from `request.input` instead of `request.metadata`) is fixed as part of this promotion, mirroring a fix already applied to the manual kernel.

**Tech Stack:** Python 3.11, `openai-agents>=0.20` SDK (`agents.Runner`, `agents.extensions.models.litellm_model.LitellmModel`), `litellm>=1.97.0`, pytest/pytest-asyncio.

## Global Constraints

- Comment mới giải thích *why* viết bằng tiếng Việt; tên định danh/thông báo lỗi hệ thống giữ tiếng Anh (CLAUDE.md "Comment code").
- `pytest.ini` đã set `pythonpath = . packages apps` — `agent_core`, `agent_integrations`, `agent_testkit`, `apps.cosa` đều import trực tiếp được, không cần sys.path hack.
- Không đổi API/schema bên ngoài `apps/cosa` trong plan này.
- `DEEPSEEK_API_KEY` / `DEEPSEEK_BASE_URL` (default `https://api.deepseek.com`) / `DEEPSEEK_DEFAULT_MODEL` (default `deepseek-chat`) là canonical env var names — đã khai trong `docker-compose.yml:99-101`, không đổi tên.
- Model identifier truyền cho `LitellmModel(model=...)` phải có prefix `deepseek/` (litellm provider convention) — đã verify bằng conformance test thật `packages/agent_testkit/kernel_conformance/test_openai_agents_sdk_kernel_deepseek_live.py:31-35`.
- Không xoá `packages/agent_integrations/langchain/` hay đổi hành vi `runtime="langchain"` (ngoài phạm vi plan này).
- Chạy `pytest tests/agent_core tests/apps/cosa packages/agent_testkit` sau mỗi task có sửa test — không tuyên bố "xong" khi chưa chạy (CLAUDE.md #11).
- Never dùng `--no-verify`/`git commit --amend` trừ khi được yêu cầu rõ.

---

### Task 1: Rename `OpenAIAgentsKernel` → `ManualToolLoopKernel` (mechanical, behavior-preserving)

**Files:**
- Modify: `packages/agent_core/kernel/openai_agents_kernel.py`
- Modify: `apps/cosa/composition/agent_plane.py:18` (import only — kernel wiring itself changes in Task 6)
- Modify (rename references only, no logic change): `tests/agent_core/kernel/test_openai_agents_kernel.py`, `tests/agent_core/kernel/test_deepseek_compatibility_matrix.py`, `tests/agent_core/kernel/test_deepseek_conformance.py`, `tests/agent_core/drift/test_case_b_agent_spec_privilege_widening.py`, `tests/agent_core/registry/test_publisher.py`, `tests/agent_core/registry/test_skill_optimization_lab.py`, `tests/agent_core/registry/test_skill_resolution.py`, `packages/agent_testkit/model_conformance/test_litellm_gateway.py`, `packages/agent_testkit/protocol_conformance/test_ag_ui_event_mapper.py`

**Interfaces:**
- Produces: `agent_core.kernel.openai_agents_kernel.ManualToolLoopKernel` (same constructor signature as old `OpenAIAgentsKernel`: `repository`, `spec_registry`, `model_client`, `capability_executor`, `policy_evaluator`, all keyword-only). Later tasks (2, 6) build on this name.

- [ ] **Step 1: Rename the class and update its `__all__`/docstring**

In `packages/agent_core/kernel/openai_agents_kernel.py`, change line 28:
```python
__all__ = ["OpenAIAgentsKernel", "KernelRunState"]
```
to:
```python
__all__ = ["ManualToolLoopKernel", "KernelRunState"]
```

Change line 79 (`class OpenAIAgentsKernel:`) to:
```python
class ManualToolLoopKernel:
    """Cài đặt Canonical ExecutionKernel dựa trên vòng lặp reasoning/tool-call
    THỦ CÔNG (manual), tương thích OpenAI/DeepSeek qua interface
    `.chat.completions.create(...)`. KHÔNG dùng `agents.Runner` thật — kernel
    dùng SDK thật là `RealOpenAIAgentsSDKKernel`
    (packages/agent_integrations/openai_agents_sdk/kernel.py), kernel mặc
    định production cho `runtime="openai_agents"` kể từ
    COSA_PRODUCTION_RUNTIME_CLOSURE_ADJUSTMENT_2026-08-25.md Phase 1. Lớp
    này vẫn dùng được qua `runtime="manual_tool_loop"` tường minh.
```
(Keep the rest of the original docstring's bullet list about checkpointing/approval/cancellation — only the opening paragraph changes.)

- [ ] **Step 2: Mechanical rename across all remaining references**

Run from repo root:
```bash
grep -rl "OpenAIAgentsKernel" packages/agent_core/kernel/openai_agents_kernel.py apps/cosa/composition/agent_plane.py tests/agent_core packages/agent_testkit | xargs sed -i '' 's/OpenAIAgentsKernel/ManualToolLoopKernel/g'
```
(On Linux/CI runners without BSD sed, use `sed -i 's/OpenAIAgentsKernel/ManualToolLoopKernel/g'` — no `''` after `-i`.)

This is safe: the string `OpenAIAgentsKernel` (mixed case, no underscores) never matches the module path `openai_agents_kernel` (snake_case) or the file name, so no unintended renames occur. Verify with:
```bash
grep -rn "OpenAIAgentsKernel" packages apps tests 2>/dev/null
```
Expected: no output (all occurrences renamed).

- [ ] **Step 3: Run affected tests to confirm the rename alone is behavior-preserving**

```bash
pytest tests/agent_core/kernel/test_openai_agents_kernel.py tests/agent_core/kernel/test_deepseek_compatibility_matrix.py tests/agent_core/kernel/test_deepseek_conformance.py tests/agent_core/drift/test_case_b_agent_spec_privilege_widening.py tests/agent_core/registry/test_publisher.py tests/agent_core/registry/test_skill_optimization_lab.py tests/agent_core/registry/test_skill_resolution.py packages/agent_testkit/model_conformance/test_litellm_gateway.py packages/agent_testkit/protocol_conformance/test_ag_ui_event_mapper.py -v
```
Expected: all pass (no behavior changed yet, only the class name).

- [ ] **Step 4: Commit**

```bash
git add packages/agent_core/kernel/openai_agents_kernel.py apps/cosa/composition/agent_plane.py tests/agent_core packages/agent_testkit
git commit -m "refactor(agent_core): rename OpenAIAgentsKernel to ManualToolLoopKernel"
```

---

### Task 2: Remove implicit mock fallback from `ManualToolLoopKernel._call_model`; extract it into an explicit test double

**Files:**
- Create: `packages/agent_testkit/mock_tool_loop_model_client.py`
- Modify: `packages/agent_core/kernel/openai_agents_kernel.py` (the `_call_model` method, currently lines 452-540 after Task 1's rename)
- Modify: `tests/agent_core/kernel/test_openai_agents_kernel.py` (add import + `model_client=` to 3 call sites: lines 19, 93, 251; add 1 new test)
- Modify: `tests/agent_core/drift/test_case_b_agent_spec_privilege_widening.py` (line 34)
- Modify: `tests/agent_core/registry/test_publisher.py` (line 53)
- Modify: `tests/agent_core/registry/test_skill_resolution.py` (lines 79, 117)
- Modify: `packages/agent_testkit/protocol_conformance/test_ag_ui_event_mapper.py` (line 29)

**Interfaces:**
- Consumes: `ManualToolLoopKernel(model_client=...)` from Task 1 (unchanged signature).
- Produces: `agent_testkit.mock_tool_loop_model_client.MockToolLoopModelClient` — a `.chat.completions.create(...)`-shaped test double, importable as `from agent_testkit.mock_tool_loop_model_client import MockToolLoopModelClient`.

- [ ] **Step 1: Create the test double, moving the mock logic verbatim**

Write `packages/agent_testkit/mock_tool_loop_model_client.py`:

```python
from __future__ import annotations

import json
import uuid
from typing import Any

__all__ = ["MockToolLoopModelClient"]


class _FakeUsage:
    def __init__(self, total_tokens: int) -> None:
        self.total_tokens = total_tokens


class _FakeFunction:
    def __init__(self, name: str, arguments: str) -> None:
        self.name = name
        self.arguments = arguments


class _FakeToolCall:
    def __init__(self, call_id: str, name: str, arguments: str) -> None:
        self.id = call_id
        self.function = _FakeFunction(name, arguments)


class _FakeMessage:
    def __init__(self, content: str, tool_calls: list[_FakeToolCall]) -> None:
        self.content = content
        self.tool_calls = tool_calls


class _FakeChoice:
    def __init__(self, message: _FakeMessage) -> None:
        self.message = message


class _FakeResponse:
    def __init__(self, choices: list[_FakeChoice], usage: _FakeUsage | None) -> None:
        self.choices = choices
        self.usage = usage


class _MockCompletions:
    async def create(
        self, *, model: str, messages: list[dict[str, Any]], temperature: float = 0.0, **kwargs: Any
    ) -> _FakeResponse:
        has_tool_message = any(m.get("role") == "tool" for m in messages)
        if has_tool_message:
            return _FakeResponse(
                choices=[
                    _FakeChoice(
                        _FakeMessage(
                            f"Completed execution after tool call: {messages[-1].get('content')}", []
                        )
                    )
                ],
                usage=_FakeUsage(50),
            )

        last_msg = messages[-1]["content"] if messages else ""
        lower = last_msg.lower()

        if "task" in lower or "operations" in lower:
            tc = _FakeToolCall(
                f"call_{uuid.uuid4().hex[:8]}",
                "operations.task.list",
                json.dumps({"workspace_id": 1, "status": "in_progress"}),
            )
            return _FakeResponse(
                choices=[_FakeChoice(_FakeMessage("Listing operations tasks.", [tc]))], usage=None
            )

        if "payout" in lower or "wire" in lower or "transfer" in lower or "pay" in lower:
            tc = _FakeToolCall(
                f"call_{uuid.uuid4().hex[:8]}",
                "finance.payout.execute",
                json.dumps(
                    {
                        "amount": 20000,
                        "vendor": "Acme Corp",
                        "currency": "USD",
                        "idempotency_key": "idem_slice2",
                    }
                ),
            )
            return _FakeResponse(
                choices=[_FakeChoice(_FakeMessage("Initiating transfer request.", [tc]))], usage=None
            )

        if "weather" in lower:
            tc = _FakeToolCall(f"call_{uuid.uuid4().hex[:8]}", "weather.get", json.dumps({"city": "Hanoi"}))
            return _FakeResponse(
                choices=[_FakeChoice(_FakeMessage("Checking weather.", [tc]))], usage=None
            )

        return _FakeResponse(
            choices=[_FakeChoice(_FakeMessage(f"Processed: {last_msg}", []))], usage=_FakeUsage(100)
        )


class _MockChat:
    def __init__(self) -> None:
        self.completions = _MockCompletions()


class MockToolLoopModelClient:
    """Test double thay cho model provider thật — cùng interface
    `.chat.completions.create(...)` mà `ManualToolLoopKernel` mong đợi từ
    client thật (OpenAI/DeepSeek/LiteLLM), để test kernel mà không cần API
    key thật.

    Logic branching theo keyword trong last user message được chuyển NGUYÊN
    VẸN từ nhánh mock cũ trong `ManualToolLoopKernel._call_model()` — nhánh
    đó bị xoá khỏi production path vì production giờ PHẢI raise nếu thiếu
    model_client thật, không còn silent mock fallback
    (COSA_PRODUCTION_RUNTIME_CLOSURE_ADJUSTMENT_2026-08-25.md §3.2)."""

    @property
    def chat(self) -> _MockChat:
        return _MockChat()
```

- [ ] **Step 2: Run a smoke test for the new module in isolation**

```bash
python3 -c "
import asyncio
from agent_testkit.mock_tool_loop_model_client import MockToolLoopModelClient

async def main():
    client = MockToolLoopModelClient()
    resp = await client.chat.completions.create(model='deepseek-chat', messages=[{'role': 'user', 'content': 'Hello world'}])
    assert resp.choices[0].message.content == 'Processed: Hello world', resp.choices[0].message.content
    print('ok')

asyncio.run(main())
"
```
(Run with `packages` and `.` on `PYTHONPATH`, e.g. `PYTHONPATH=.:packages:apps python3 -c "..."` if not run through pytest.)
Expected: prints `ok`.

- [ ] **Step 3: Make `_call_model` fail fast instead of silently mocking**

In `packages/agent_core/kernel/openai_agents_kernel.py`, replace the method body (the `if self._client and hasattr(...)` guard plus the entire `# Mock / Fallback logic cho test` block through the final `return {"content": f"Processed: {last_msg}", ...}`) with:

```python
    async def _call_model(self, messages: list[dict[str, Any]], spec: AgentSpec) -> dict[str, Any]:
        if not (self._client and hasattr(self._client, "chat") and hasattr(self._client.chat, "completions")):
            # Production KHÔNG được silently mock khi model_client chưa cấu
            # hình — đây từng là nguồn của lỗi correctness nghiêm trọng: mọi
            # agent run production trả kết quả giả (keyword-matched), kể cả
            # khi DEEPSEEK_API_KEY đã set đúng, vì composition mặc định
            # không bao giờ inject model_client (COSA_PRODUCTION_RUNTIME_
            # CLOSURE_ADJUSTMENT_2026-08-25.md §3.2). Test dùng
            # agent_testkit.mock_tool_loop_model_client.MockToolLoopModelClient
            # tường minh thay vì dựa vào fallback ngầm.
            raise AgentRuntimeError(
                RuntimeErrorCode.MODEL_PROVIDER_ERROR,
                "ManualToolLoopKernel requires an explicit model_client "
                "(e.g. LiteLLMModelClient) — no implicit mock fallback in "
                "production. Tests must pass "
                "model_client=agent_testkit.mock_tool_loop_model_client.MockToolLoopModelClient() "
                "explicitly.",
                retryable=False,
            )

        # Gọi real OpenAI / DeepSeek client
        try:
            resp = await self._client.chat.completions.create(
                model=spec.model_policy.get("model", "deepseek-chat"),
                messages=messages,
                temperature=spec.model_policy.get("temperature", 0.0),
            )
            choice = resp.choices[0]
            tool_calls = []
            if choice.message.tool_calls:
                for tc in choice.message.tool_calls:
                    tool_calls.append(
                        {
                            "id": tc.id,
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    )
            return {
                "content": choice.message.content or "",
                "tool_calls": tool_calls,
                "usage": {"total_tokens": getattr(resp.usage, "total_tokens", 0)} if resp.usage else {},
            }
        except AgentRuntimeError:
            # `self._client` (vd LiteLLMModelClient) đã tự phân loại đúng
            # RuntimeErrorCode (MODEL_RATE_LIMIT, CONTEXT_LIMIT_EXCEEDED...) —
            # không re-wrap thành MODEL_PROVIDER_ERROR chung chung, mất thông tin.
            raise
        except Exception as exc:
            # Provider/runtime failure phải là typed error, không phải assistant
            # content thành công (Blueprint V2 §56 anti-pattern; ADR-RUNTIME-001).
            raise AgentRuntimeError(
                RuntimeErrorCode.MODEL_PROVIDER_ERROR,
                f"Model provider call failed: {exc}",
                retryable=True,
                cause=exc,
            ) from exc
```

- [ ] **Step 4: Update the 8 call sites that relied on the implicit fallback**

In `tests/agent_core/kernel/test_openai_agents_kernel.py`:
- Add import after the existing `from agent_core.kernel.openai_agents_kernel import ManualToolLoopKernel` line:
  ```python
  from agent_testkit.mock_tool_loop_model_client import MockToolLoopModelClient
  ```
- Line 19: `kernel = ManualToolLoopKernel(repository=repo)` → `kernel = ManualToolLoopKernel(repository=repo, model_client=MockToolLoopModelClient())`
- Line 93: `kernel = ManualToolLoopKernel(repository=repo)` → `kernel = ManualToolLoopKernel(repository=repo, model_client=MockToolLoopModelClient())`
- Line 251: `kernel = ManualToolLoopKernel(repository=repo, capability_executor=gateway.execute)` → `kernel = ManualToolLoopKernel(repository=repo, capability_executor=gateway.execute, model_client=MockToolLoopModelClient())`

In `tests/agent_core/drift/test_case_b_agent_spec_privilege_widening.py`:
- Add import: `from agent_testkit.mock_tool_loop_model_client import MockToolLoopModelClient`
- Line 34: `kernel = ManualToolLoopKernel(repository=repo)` → `kernel = ManualToolLoopKernel(repository=repo, model_client=MockToolLoopModelClient())`

In `tests/agent_core/registry/test_publisher.py`:
- Add import: `from agent_testkit.mock_tool_loop_model_client import MockToolLoopModelClient`
- Line 53: `kernel = ManualToolLoopKernel(repository=repo, spec_registry=registry)` → `kernel = ManualToolLoopKernel(repository=repo, spec_registry=registry, model_client=MockToolLoopModelClient())`

In `tests/agent_core/registry/test_skill_resolution.py`:
- Add import: `from agent_testkit.mock_tool_loop_model_client import MockToolLoopModelClient`
- Line 79: `kernel = ManualToolLoopKernel(repository=repo, spec_registry=registry)` → `kernel = ManualToolLoopKernel(repository=repo, spec_registry=registry, model_client=MockToolLoopModelClient())`
- Line 117: same change as line 79.

In `packages/agent_testkit/protocol_conformance/test_ag_ui_event_mapper.py`:
- Add import: `from agent_testkit.mock_tool_loop_model_client import MockToolLoopModelClient`
- Line 29: `kernel = ManualToolLoopKernel(repository=repo)` → `kernel = ManualToolLoopKernel(repository=repo, model_client=MockToolLoopModelClient())`

- [ ] **Step 5: Add a new test proving the fail-fast behavior**

Append to `tests/agent_core/kernel/test_openai_agents_kernel.py`:

```python
@pytest.mark.asyncio
async def test_kernel_raises_typed_error_when_model_client_not_configured():
    """Không còn silent mock fallback — thiếu model_client phải là RunResult
    FAILED có structured error, không phải response giả (COSA_PRODUCTION_
    RUNTIME_CLOSURE_ADJUSTMENT_2026-08-25.md §3.2)."""
    repo = InMemoryRunRepository()
    kernel = ManualToolLoopKernel(repository=repo)

    spec = AgentSpec(id="general_assistant")
    request = RunRequest(
        principal="test_user",
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": "Hello world"},
    )

    result = await kernel.run(request, spec)

    assert result.status == RunStatus.FAILED
    assert result.errors and "model_client" in result.errors[0]

    run_rec = await repo.get_run(result.run_id)
    assert run_rec.error_details["code"] == RuntimeErrorCode.MODEL_PROVIDER_ERROR.value
```

- [ ] **Step 6: Run the full affected test set**

```bash
pytest tests/agent_core/kernel/test_openai_agents_kernel.py tests/agent_core/drift/test_case_b_agent_spec_privilege_widening.py tests/agent_core/registry/test_publisher.py tests/agent_core/registry/test_skill_resolution.py packages/agent_testkit/protocol_conformance/test_ag_ui_event_mapper.py -v
```
Expected: all pass, including the new `test_kernel_raises_typed_error_when_model_client_not_configured`.

- [ ] **Step 7: Commit**

```bash
git add packages/agent_testkit/mock_tool_loop_model_client.py packages/agent_core/kernel/openai_agents_kernel.py tests/agent_core/kernel/test_openai_agents_kernel.py tests/agent_core/drift/test_case_b_agent_spec_privilege_widening.py tests/agent_core/registry/test_publisher.py tests/agent_core/registry/test_skill_resolution.py packages/agent_testkit/protocol_conformance/test_ag_ui_event_mapper.py
git commit -m "fix(agent_core): remove silent mock fallback from ManualToolLoopKernel, require explicit test double"
```

---

### Task 3: Fix governance-context bug in `RealOpenAIAgentsSDKKernel.run()`

**Files:**
- Modify: `packages/agent_integrations/openai_agents_sdk/kernel.py:209`
- Modify: `packages/agent_testkit/kernel_conformance/test_openai_agents_sdk_kernel.py` (add 1 new test)

**Interfaces:**
- Consumes: `RealOpenAIAgentsSDKKernel(policy_evaluator=...)` (existing constructor, unchanged).

- [ ] **Step 1: Write the failing test**

Append to `packages/agent_testkit/kernel_conformance/test_openai_agents_sdk_kernel.py`:

```python
@pytest.mark.asyncio
async def test_openai_agents_sdk_kernel_builds_policy_context_from_metadata_not_input():
    """`request.metadata` (không phải `request.input` — đó là literal prompt
    text) phải là nguồn context cho policy_evaluator — cùng bug đã fix ở
    ManualToolLoopKernel (packages/agent_core/kernel/openai_agents_kernel.py),
    xem COSA_PRODUCTION_RUNTIME_CLOSURE_ADJUSTMENT_2026-08-25.md §5.3."""
    registry = CapabilityRegistry()
    cap = CapabilitySpec(id="weather.get", description="Get weather", input_schema={"type": "object", "properties": {}})
    registry.register(cap, lambda args: {})

    captured_context: dict = {}

    def policy_evaluator(name: str, args: dict, ctx: dict) -> str:
        captured_context.update(ctx)
        return "ALLOW"

    call_id = "call_ctx_check"
    model = FakeSDKModel(
        responses=[
            _tool_call_response(call_id, "weather.get"),
            _text_response("done"),
        ]
    )
    kernel = RealOpenAIAgentsSDKKernel(
        model=model,
        capability_registry=registry,
        capability_executor=lambda name, args: {},
        policy_evaluator=policy_evaluator,
    )
    spec = _make_spec(capability_refs=["weather.get"])
    request = RunRequest(
        input={"prompt": "what is the weather"},
        principal="test-suite",
        root_executable_ref=spec.to_pinned_identity(),
        execution_mode=ExecutionMode.HUMAN_IN_THE_LOOP,
        workspace_id="ws_test",
        metadata={"policy_snapshot": {"company_status": "active", "principal_status": "active"}},
    )

    await kernel.run(request, spec)

    assert "policy_snapshot" in captured_context
    assert "prompt" not in captured_context
```

- [ ] **Step 2: Run it to confirm it fails**

```bash
pytest packages/agent_testkit/kernel_conformance/test_openai_agents_sdk_kernel.py::test_openai_agents_sdk_kernel_builds_policy_context_from_metadata_not_input -v
```
Expected: FAIL — `"policy_snapshot" in captured_context` is false (current code builds context from `request.input`, which only has `"prompt"`).

- [ ] **Step 3: Fix the bug**

In `packages/agent_integrations/openai_agents_sdk/kernel.py`, change line 209 from:
```python
        context: dict[str, Any] = dict(request.input)
```
to:
```python
        # request.metadata (không phải request.input — đó là literal prompt
        # text/args) là nơi đúng để mang ambient governance context (vd.
        # policy_snapshot) cho policy_evaluator — cùng fix đã áp dụng cho
        # ManualToolLoopKernel (packages/agent_core/kernel/openai_agents_kernel.py),
        # theo COSA_PRODUCTION_RUNTIME_CLOSURE_ADJUSTMENT_2026-08-25.md §5.3.
        context: dict[str, Any] = dict(request.metadata)
```

- [ ] **Step 4: Run it to confirm it passes, plus the rest of the file**

```bash
pytest packages/agent_testkit/kernel_conformance/test_openai_agents_sdk_kernel.py -v
```
Expected: all pass, including the new test.

- [ ] **Step 5: Commit**

```bash
git add packages/agent_integrations/openai_agents_sdk/kernel.py packages/agent_testkit/kernel_conformance/test_openai_agents_sdk_kernel.py
git commit -m "fix(agent_integrations): build RealOpenAIAgentsSDKKernel policy context from request.metadata, not request.input"
```

---

### Task 4: Extract `FakeSDKModel` into a reusable `agent_testkit` module

**Files:**
- Create: `packages/agent_testkit/fake_sdk_model.py`
- Modify: `packages/agent_testkit/kernel_conformance/test_openai_agents_sdk_kernel.py`

**Interfaces:**
- Produces: `agent_testkit.fake_sdk_model.FakeSDKModel`, `agent_testkit.fake_sdk_model.text_response`, `agent_testkit.fake_sdk_model.tool_call_response`, `agent_testkit.fake_sdk_model.usage` — reused by Task 6 to fake the SDK model in `apps/cosa` integration tests.

- [ ] **Step 1: Create the shared module**

Write `packages/agent_testkit/fake_sdk_model.py` (content moved verbatim from `packages/agent_testkit/kernel_conformance/test_openai_agents_sdk_kernel.py` lines 15-77, renaming the three private helpers to public names):

```python
from __future__ import annotations

from agents.models.interface import Model, ModelResponse
from agents.usage import Usage
from openai.types.responses import ResponseFunctionToolCall, ResponseOutputMessage, ResponseOutputText

__all__ = ["FakeSDKModel", "usage", "text_response", "tool_call_response"]


def usage() -> Usage:
    return Usage(input_tokens=10, output_tokens=5, total_tokens=15)


def text_response(text: str) -> ModelResponse:
    return ModelResponse(
        output=[
            ResponseOutputMessage(
                id="msg_1",
                role="assistant",
                status="completed",
                type="message",
                content=[ResponseOutputText(text=text, type="output_text", annotations=[])],
            )
        ],
        usage=usage(),
        response_id="resp_1",
    )


def tool_call_response(call_id: str, tool_name: str, arguments: str = "{}") -> ModelResponse:
    return ModelResponse(
        output=[
            ResponseFunctionToolCall(
                id="fc_1", call_id=call_id, name=tool_name, arguments=arguments, type="function_call", status="completed"
            )
        ],
        usage=usage(),
        response_id="resp_2",
    )


class FakeSDKModel(Model):
    """Model fake điều khiển bằng hàng đợi response, duck-typed đúng
    `agents.models.interface.Model` Protocol — không gọi API thật. Dùng
    trong conformance test của `RealOpenAIAgentsSDKKernel` VÀ trong
    `apps/cosa` integration test (Task 6) để không cần DEEPSEEK_API_KEY."""

    def __init__(self, responses: list[ModelResponse] | None = None, error: Exception | None = None) -> None:
        self._responses = list(responses or [])
        self._error = error
        self.call_count = 0

    async def get_response(self, *args, **kwargs) -> ModelResponse:
        self.call_count += 1
        if self._error:
            raise self._error
        if not self._responses:
            return text_response("no more responses configured")
        return self._responses.pop(0)

    def stream_response(self, *args, **kwargs):  # pragma: no cover - unused ở conformance này
        raise NotImplementedError
```

- [ ] **Step 2: Update the conformance test to import from the shared module instead of defining locally**

In `packages/agent_testkit/kernel_conformance/test_openai_agents_sdk_kernel.py`, replace lines 15-77 (the `from agents.models.interface import ...` through the end of the `FakeSDKModel` class) with:

```python
from agent_testkit.fake_sdk_model import (
    FakeSDKModel,
    text_response as _text_response,
    tool_call_response as _tool_call_response,
    usage as _usage,
)
```

Leave every test function body below unchanged — they already call `_text_response(...)`, `_tool_call_response(...)`, `_usage()`, `FakeSDKModel(...)`, which now resolve via the aliased imports.

- [ ] **Step 3: Run the conformance test file**

```bash
pytest packages/agent_testkit/kernel_conformance/test_openai_agents_sdk_kernel.py -v
```
Expected: all pass, unchanged behavior.

- [ ] **Step 4: Commit**

```bash
git add packages/agent_testkit/fake_sdk_model.py packages/agent_testkit/kernel_conformance/test_openai_agents_sdk_kernel.py
git commit -m "refactor(agent_testkit): extract FakeSDKModel into a reusable module"
```

---

### Task 5: `build_deepseek_model()` — canonical DeepSeek provider factory

**Files:**
- Create: `apps/cosa/composition/model_provider.py`
- Create: `tests/apps/cosa/composition/test_model_provider.py`

**Interfaces:**
- Produces: `apps.cosa.composition.model_provider.build_deepseek_model() -> agents.extensions.models.litellm_model.LitellmModel`. Consumed by Task 6.

- [ ] **Step 1: Write the failing tests**

Create `tests/apps/cosa/composition/test_model_provider.py`:

```python
from __future__ import annotations

import pytest


def test_build_deepseek_model_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    from apps.cosa.composition.model_provider import build_deepseek_model

    with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
        build_deepseek_model()


def test_build_deepseek_model_returns_litellm_model_with_env_config(monkeypatch):
    pytest.importorskip("agents")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-123")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://custom.deepseek.example")
    monkeypatch.setenv("DEEPSEEK_DEFAULT_MODEL", "deepseek-reasoner")
    from agents.extensions.models.litellm_model import LitellmModel
    from apps.cosa.composition.model_provider import build_deepseek_model

    model = build_deepseek_model()

    assert isinstance(model, LitellmModel)


def test_build_deepseek_model_defaults_base_url_and_model(monkeypatch):
    pytest.importorskip("agents")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-123")
    monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)
    monkeypatch.delenv("DEEPSEEK_DEFAULT_MODEL", raising=False)
    from agents.extensions.models.litellm_model import LitellmModel
    from apps.cosa.composition.model_provider import build_deepseek_model

    model = build_deepseek_model()

    assert isinstance(model, LitellmModel)
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/apps/cosa/composition/test_model_provider.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'apps.cosa.composition.model_provider'`.

- [ ] **Step 3: Implement**

Create `apps/cosa/composition/model_provider.py`:

```python
from __future__ import annotations

import os
from typing import Any

__all__ = ["build_deepseek_model"]


def build_deepseek_model() -> Any:
    """Dựng `agents.extensions.models.litellm_model.LitellmModel` trỏ tới
    DeepSeek THẬT từ `DEEPSEEK_API_KEY`/`DEEPSEEK_BASE_URL`/
    `DEEPSEEK_DEFAULT_MODEL` — đọc env một chỗ duy nhất tại composition root
    (COSA_PRODUCTION_RUNTIME_CLOSURE_ADJUSTMENT_2026-08-25.md §5.2), không
    rải rác trong kernel.

    Raise RuntimeError rõ ràng nếu thiếu DEEPSEEK_API_KEY — production
    không được silently chạy với model provider chưa cấu hình (§3.2/§5.1).
    """
    from agents.extensions.models.litellm_model import LitellmModel

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError(
            "build_deepseek_model() requires DEEPSEEK_API_KEY to be set — "
            "production must not silently run with an unconfigured model "
            "provider. For tests, pass model=<FakeSDKModel instance> "
            "explicitly to build_cosa_agent_plane()."
        )
    base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    default_model = os.environ.get("DEEPSEEK_DEFAULT_MODEL", "deepseek-chat")

    return LitellmModel(
        model=f"deepseek/{default_model}",
        base_url=base_url,
        api_key=api_key,
    )
```

- [ ] **Step 4: Run to confirm it passes**

```bash
pytest tests/apps/cosa/composition/test_model_provider.py -v
```
Expected: all 3 pass (the 2 env-dependent tests skip cleanly via `pytest.importorskip("agents")` if the SDK isn't installed yet in the current environment — that's fixed by Task 7).

- [ ] **Step 5: Commit**

```bash
git add apps/cosa/composition/model_provider.py tests/apps/cosa/composition/test_model_provider.py
git commit -m "feat(cosa): add build_deepseek_model() canonical provider factory"
```

---

### Task 6: Promote `RealOpenAIAgentsSDKKernel` as the default `runtime="openai_agents"` kernel

**Files:**
- Modify: `apps/cosa/composition/agent_plane.py`
- Modify: `tests/apps/cosa/composition/test_agent_plane.py` (5 call sites + 1 assertion type)
- Modify: `tests/apps/cosa/test_cosa_plane.py` (2 call sites)
- Modify: `tests/apps/cosa/test_tenant_isolation.py` (1 call site)
- Modify: `tests/apps/cosa/test_vertical_slice_1_read_path.py` (1 call site)
- Modify: `tests/apps/cosa/test_vertical_slice_2_write_approval.py` (1 call site)
- Modify: `tests/apps/cosa/worker/test_main.py` (1 call site, in the shared `_plane()` helper)

**Interfaces:**
- Consumes: `RealOpenAIAgentsSDKKernel` (Task 3's bugfix already applied), `build_deepseek_model()` (Task 5), `agent_testkit.fake_sdk_model.FakeSDKModel` (Task 4).
- Produces: `build_cosa_agent_plane(..., model: Optional[Any] = None, runtime: str = "openai_agents")` — new `model=` kwarg follows the exact same override pattern already used for `repository=`/`conversation_repository=`/etc. in this function: explicit param wins, else derived (here: `build_deepseek_model()`), and for `model=` there is no database-derived path — an unconfigured `DEEPSEEK_API_KEY` always raises from `build_deepseek_model()` unless `model=` is passed explicitly.

- [ ] **Step 1: Wire the new kernel and provider into composition**

In `apps/cosa/composition/agent_plane.py`, add an import near the top (after the `agent_core.kernel.openai_agents_kernel` import):
```python
from agent_integrations.openai_agents_sdk.kernel import RealOpenAIAgentsSDKKernel
```

Add `model: Optional[Any] = None` to the `build_cosa_agent_plane(...)` signature, right after `lease_client: Optional[Any] = None,`:
```python
    lease_client: Optional[Any] = None,
    model: Optional[Any] = None,
```

Replace the `# 4. Execution Kernel` block (the `if runtime == "langchain": ... elif runtime == "openai_agents": ... else: raise ValueError(...)`) with:

```python
    # 4. Execution Kernel
    if runtime == "langchain":
        # Import lazy — chỉ nhánh này mới yêu cầu langchain-core/langchain-deepseek.
        from agent_integrations.langchain.kernel import LangChainKernel

        kernel: Any = LangChainKernel(
            repository=repo,
            spec_registry=registry_repo,
            capability_registry=cap_registry,
            capability_executor=gateway.execute,
            policy_evaluator=policy_engine.evaluate,
        )
    elif runtime == "openai_agents":
        # Kernel mặc định production — agents.Runner THẬT qua
        # RealOpenAIAgentsSDKKernel, không phải ManualToolLoopKernel (đổi tên
        # từ OpenAIAgentsKernel) — theo ADR-RUNTIME-002 và
        # COSA_PRODUCTION_RUNTIME_CLOSURE_ADJUSTMENT_2026-08-25.md Phase 1.
        # `model=` override tường minh dùng cho test (vd.
        # agent_testkit.fake_sdk_model.FakeSDKModel) — nếu không truyền,
        # bắt buộc build từ DEEPSEEK_API_KEY thật, fail-fast nếu thiếu.
        if model is not None:
            resolved_model: Any = model
        else:
            from apps.cosa.composition.model_provider import build_deepseek_model

            resolved_model = build_deepseek_model()

        kernel = RealOpenAIAgentsSDKKernel(
            repository=repo,
            spec_registry=registry_repo,
            capability_registry=cap_registry,
            model=resolved_model,
            capability_executor=gateway.execute,
            policy_evaluator=policy_engine.evaluate,
        )
    elif runtime == "manual_tool_loop":
        # Kernel manual-loop cũ (đổi tên từ OpenAIAgentsKernel) — vẫn dùng
        # được qua opt-in tường minh, không còn là default.
        kernel = ManualToolLoopKernel(
            repository=repo,
            spec_registry=registry_repo,
            capability_executor=gateway.execute,
            policy_evaluator=policy_engine.evaluate,
        )
    else:
        raise ValueError(
            f"Unknown runtime '{runtime}' — expected 'openai_agents', 'manual_tool_loop', or 'langchain'"
        )
```

Update the function's docstring paragraph about `runtime` (currently describing only `"openai_agents"`/`"langchain"`) to also mention `"manual_tool_loop"`:
```python
    `runtime`: "openai_agents" (mặc định, production — RealOpenAIAgentsSDKKernel
    thật qua agents.Runner, ADR-RUNTIME-002), "manual_tool_loop" (kernel loop
    thủ công cũ, opt-in cho dev/test không cần model provider config sẵn),
    hoặc "langchain" (optional adapter, không trên cutover path — xem
    docs/architecture/adr/ADR-RUNTIME-002-openai-agents-sdk-primary-deepseek-provider.md).
```

- [ ] **Step 2: Update `tests/apps/cosa/composition/test_agent_plane.py`**

Add `from agent_testkit.fake_sdk_model import FakeSDKModel` near the top of the file (module-level import, since it is used in most test functions).

- `test_build_cosa_agent_plane_uses_postgres_when_database_url_given` (line 21): change
  ```python
  plane = build_cosa_agent_plane(database_url="postgresql+asyncpg://x:x@localhost/x")
  ```
  to
  ```python
  plane = build_cosa_agent_plane(database_url="postgresql+asyncpg://x:x@localhost/x", model=FakeSDKModel())
  ```

- `test_build_cosa_agent_plane_uses_postgres_from_env_var` (line 37): change
  ```python
  plane = build_cosa_agent_plane()
  ```
  to
  ```python
  plane = build_cosa_agent_plane(model=FakeSDKModel())
  ```

- `test_build_cosa_agent_plane_still_accepts_explicit_in_memory_repositories_for_tests` (lines 137-143): add `model=FakeSDKModel(),` to the `build_cosa_agent_plane(...)` call's kwargs.

- `test_build_cosa_agent_plane_defaults_to_openai_agents_kernel` (lines 152-171): this test's whole point — asserting the default kernel type — is exactly the bug this plan fixes. Replace the entire function with:
  ```python
  def test_build_cosa_agent_plane_defaults_to_real_openai_agents_sdk_kernel():
      """Runtime mặc định là RealOpenAIAgentsSDKKernel (agents.Runner thật) —
      ADR-RUNTIME-002 (2026-08-25) chốt OpenAI Agents SDK làm primary execution
      runtime; trước Phase 1 (COSA_PRODUCTION_RUNTIME_CLOSURE_ADJUSTMENT_2026-
      08-25.md) mặc định này trỏ nhầm vào ManualToolLoopKernel (khi đó còn tên
      OpenAIAgentsKernel) — một manual reasoning loop, không phải SDK thật."""
      from agent_core.conversations.repository import InMemoryConversationRepository
      from agent_core.governance.providers.in_memory import InMemoryGovernanceStateStore
      from agent_integrations.openai_agents_sdk.kernel import RealOpenAIAgentsSDKKernel
      from agent_core.registry.repository import InMemorySpecRegistryRepository
      from agent_core.runs.repository import InMemoryRunRepository
      from agent_core.runs.stream_events import InMemoryRunStreamEventRepository
      from apps.cosa.composition.agent_plane import build_cosa_agent_plane

      plane = build_cosa_agent_plane(
          repository=InMemoryRunRepository(),
          conversation_repository=InMemoryConversationRepository(),
          spec_registry=InMemorySpecRegistryRepository(),
          governance_store=InMemoryGovernanceStateStore(),
          stream_event_repository=InMemoryRunStreamEventRepository(),
          model=FakeSDKModel(),
      )
      assert isinstance(plane.kernel, RealOpenAIAgentsSDKKernel)
  ```

- Add a new test right after it, proving the old name still works as an explicit opt-in:
  ```python
  def test_build_cosa_agent_plane_can_opt_into_manual_tool_loop_kernel():
      """`runtime="manual_tool_loop"` phải wire đúng ManualToolLoopKernel —
      opt-in tường minh, không phải default (thay thế test cũ đã khẳng định
      nhầm đây là default trước Phase 1)."""
      from agent_core.conversations.repository import InMemoryConversationRepository
      from agent_core.governance.providers.in_memory import InMemoryGovernanceStateStore
      from agent_core.kernel.openai_agents_kernel import ManualToolLoopKernel
      from agent_core.registry.repository import InMemorySpecRegistryRepository
      from agent_core.runs.repository import InMemoryRunRepository
      from agent_core.runs.stream_events import InMemoryRunStreamEventRepository
      from apps.cosa.composition.agent_plane import build_cosa_agent_plane

      plane = build_cosa_agent_plane(
          repository=InMemoryRunRepository(),
          conversation_repository=InMemoryConversationRepository(),
          spec_registry=InMemorySpecRegistryRepository(),
          governance_store=InMemoryGovernanceStateStore(),
          stream_event_repository=InMemoryRunStreamEventRepository(),
          runtime="manual_tool_loop",
      )
      assert isinstance(plane.kernel, ManualToolLoopKernel)
  ```

- `test_build_cosa_agent_plane_rejects_unknown_runtime` (lines 196-212): no change needed — `runtime="not_a_real_runtime"` still hits the `else: raise ValueError(...)` branch before any model resolution.

- `test_build_cosa_agent_plane_wires_governance_store_into_gateway` (lines 226-231): add `model=FakeSDKModel(),` to the `build_cosa_agent_plane(...)` call's kwargs.

- [ ] **Step 3: Update `tests/apps/cosa/test_cosa_plane.py`**

Add `from agent_testkit.fake_sdk_model import FakeSDKModel` to the imports.

Both `build_cosa_agent_plane(...)` calls (lines 38-45 and 68-75) neither call `plane.kernel.run(...)` — they call `plane.gateway.execute(req)` directly, bypassing the kernel. Add `model=FakeSDKModel(),` to each call's kwargs so construction succeeds; it will never actually be invoked.

- [ ] **Step 4: Update `tests/apps/cosa/test_tenant_isolation.py`**

Add `from agent_testkit.fake_sdk_model import FakeSDKModel` to the imports.

In the `test_app` fixture (lines 30-40), add `model=FakeSDKModel(),` to the `build_cosa_agent_plane(...)` kwargs. The one test that exercises the kernel (`test_tenant_b_cannot_cancel_or_read_events_of_tenant_a_run`, prompt `"list tasks"`) doesn't assert on response content — `FakeSDKModel()`'s no-responses-configured fallback (`text_response("no more responses configured")`) is sufficient.

- [ ] **Step 5: Update `tests/apps/cosa/test_vertical_slice_1_read_path.py`**

Add `from agent_testkit.fake_sdk_model import FakeSDKModel` to the imports.

In the `test_app` fixture (lines 30-43), add `model=FakeSDKModel(),` to the `build_cosa_agent_plane(...)` kwargs. The test only asserts the assistant message status is `"completed"` and that `run.started`/`reasoning.status`/`message.delta`/`run.completed` events appear — it does not assert tool-call content, so `FakeSDKModel()`'s default fallback response is sufficient (no queued responses needed).

- [ ] **Step 6: Update `tests/apps/cosa/test_vertical_slice_2_write_approval.py`**

Add to the imports:
```python
from agent_testkit.fake_sdk_model import FakeSDKModel, text_response, tool_call_response
```

In the `test_app` fixture (lines 31-41), add a queued `model=` so the flow produces a tool call gated by policy, then completes after resume:
```python
    plane = build_cosa_agent_plane(
        company_client=mock_client,
        tenant_policy_client=fake_active_tenant_policy_client(),
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        scheduler=RunScheduler(),
        lease_client=RunLeaseManager(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(
            responses=[
                tool_call_response(
                    "call_slice2_payout",
                    "finance.payout.execute",
                    arguments='{"workspace_id": 1, "amount": 20000, "vendor": "Acme Corp", "currency": "USD", "idempotency_key": "idem_po_slice2"}',
                ),
                text_response("Payout complete"),
            ]
        ),
    )
```
`CosaPolicyEngine.evaluate` (`apps/cosa/policies/evaluator.py`) already classifies `finance.payout.execute` as `REQUIRE_APPROVAL` via its hardcoded `'payout'`-keyword rule (step 3 of its evaluate order) independent of `policy_snapshot` presence, so the first queued response triggers the same approval-then-resume flow the test already expects.

- [ ] **Step 7: Update `tests/apps/cosa/worker/test_main.py`**

Add `from agent_testkit.fake_sdk_model import FakeSDKModel` to the imports.

In the `_plane()` helper (lines 28-38), add `model=FakeSDKModel(),` to the `build_cosa_agent_plane(...)` kwargs. Confirmed none of this file's 5 tests reach `kernel.run()`: `test_unknown_task_type_marked_failed_not_silently_dropped` uses `task_type="bogus"` (rejected before kernel involvement), `test_missing_run_id_marked_failed` fails on missing `run_id` before kernel involvement, `test_lease_blocks_a_different_worker_id_for_same_run_id` calls `plane.lease_client` directly (never `dispatch_one_task`), `test_dispatch_one_task_acquires_and_releases_lease_around_execution` monkeypatches `worker_main.execute_run_task` itself (bypasses the kernel entirely), and `test_run_worker_loop_stops_after_max_iterations` has no scheduled tasks to dispatch. The bare `FakeSDKModel()` (no queued responses) is sufficient — it is never invoked.

- [ ] **Step 8: Run the full affected test set**

```bash
pytest tests/apps/cosa -v
```
Expected: all pass. Pay particular attention to `test_vertical_slice_2_write_with_approval_and_resume` (Step 6) and `test_build_cosa_agent_plane_defaults_to_real_openai_agents_sdk_kernel` (Step 2) — these are the two places where SDK-Runner-specific behavior (tool-call matching against `agent.tools`, interruption/resume semantics) is exercised for the first time inside `apps/cosa`'s own test suite rather than only in `packages/agent_testkit/kernel_conformance/`. If `Runner.run()` raises a "tool not found" style error, verify `capability_registry=cap_registry` was actually passed to `RealOpenAIAgentsSDKKernel(...)` in Step 1 and that `COSA_FINANCE_AGENT_SPEC.capability_refs` (`apps/cosa/agents/specs.py:28`) includes `"finance.payout.execute"` (it already does).

- [ ] **Step 9: Commit**

```bash
git add apps/cosa/composition/agent_plane.py tests/apps/cosa
git commit -m "feat(cosa): promote RealOpenAIAgentsSDKKernel as the default openai_agents runtime kernel"
```

---

### Task 7: Install the SDK + LiteLLM dependencies in the worker/API images

**Files:**
- Modify: `apps/cosa/requirements.txt`
- Modify: `apps/cosa/Dockerfile.worker`
- Modify: `apps/cosa/Dockerfile.api`

**Interfaces:**
- Produces: `agents` and `agent_integrations.*` importable inside both built images.

- [ ] **Step 1: Add the two new dependencies**

In `apps/cosa/requirements.txt`, append:
```
openai-agents>=0.20
litellm>=1.97.0
```

- [ ] **Step 2: Update both Dockerfiles to install and copy `packages/agent_integrations`**

In `apps/cosa/Dockerfile.worker`, change:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY packages/agent_core/requirements.txt /app/packages/agent_core/requirements.txt
COPY apps/cosa/requirements.txt /app/apps/cosa/requirements.txt
RUN pip install --no-cache-dir -r /app/packages/agent_core/requirements.txt -r /app/apps/cosa/requirements.txt
COPY packages/agent_core /app/agent_core
COPY apps/cosa /app/apps/cosa
ENV PYTHONPATH=/app
CMD ["python", "-m", "apps.cosa.worker.main"]
```
to:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY packages/agent_core/requirements.txt /app/packages/agent_core/requirements.txt
COPY apps/cosa/requirements.txt /app/apps/cosa/requirements.txt
RUN pip install --no-cache-dir -r /app/packages/agent_core/requirements.txt -r /app/apps/cosa/requirements.txt
COPY packages/agent_core /app/agent_core
COPY packages/agent_integrations /app/agent_integrations
COPY apps/cosa /app/apps/cosa
ENV PYTHONPATH=/app
CMD ["python", "-m", "apps.cosa.worker.main"]
```
(Same edit — replace the two `COPY packages/agent_core /app/agent_core` / `COPY apps/cosa /app/apps/cosa` lines with the three-line version above, inserting `COPY packages/agent_integrations /app/agent_integrations` between them — in `apps/cosa/Dockerfile.api` as well, keeping its existing `CMD` line unchanged.)

- [ ] **Step 3: Verify the image builds and the new imports resolve**

```bash
docker build -f apps/cosa/Dockerfile.worker -t cosa-worker-test .
docker run --rm cosa-worker-test python -c "import agents; from agent_integrations.openai_agents_sdk.kernel import RealOpenAIAgentsSDKKernel; from agent_integrations.litellm.gateway import LiteLLMModelClient; print('ok')"
```
Expected: prints `ok`. If Docker is unavailable in this environment, instead verify the dependency resolves locally:
```bash
pip install openai-agents>=0.20 litellm>=1.97.0
python3 -c "import agents; from agents.extensions.models.litellm_model import LitellmModel; print('ok')"
```
and note in the task report that the Docker build itself was not exercised, so the human partner or CI (`apps-cosa` job) should verify the image build separately.

- [ ] **Step 4: Commit**

```bash
git add apps/cosa/requirements.txt apps/cosa/Dockerfile.worker apps/cosa/Dockerfile.api
git commit -m "build(cosa): install openai-agents and litellm in worker/api images"
```

---

## Out of scope for this plan (tracked separately)

- Fail-fast `/healthz` reflecting provider readiness and moving `apps/cosa/api/app.py` off the lazy `_plane_instance` singleton — this is Phase 5 (Composition Lifecycle) of `docs/implementation/production-runtime-closure.md`, deliberately deferred because it requires a FastAPI `lifespan` rewrite, not a Phase 1 concern.
- Tenant/security closure (workspace verification, bearer token in queue, Flutter secure storage) — Phase 2 of the same document, separate plan.
- Durable queue recovery, local capability hardening, CI green gate — Phases 3, 4, 6 of the same document, separate plans.

## Verification (end of Phase 1)

```bash
pytest tests/agent_core tests/apps/cosa packages/agent_testkit -v
```
Expected: full suite green. Then, with a real `DEEPSEEK_API_KEY` set in the environment, run the live conformance test to prove an actual DeepSeek call succeeds through the now-default path:
```bash
DEEPSEEK_API_KEY=<real key> pytest packages/agent_testkit/kernel_conformance/test_openai_agents_sdk_kernel_deepseek_live.py -v
```
Expected: pass (was already passing before this plan — this run confirms nothing in Task 1-7 broke the live path). Finally, confirm the fail-fast: `unset DEEPSEEK_API_KEY` and run `python -m apps.cosa.worker.main --once` against a real `AGENT_CORE_DATABASE_URL` — expect a `RuntimeError` mentioning `DEEPSEEK_API_KEY`, not a hang or a silent mock response.
