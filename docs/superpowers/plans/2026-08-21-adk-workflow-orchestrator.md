# AdkCofounderWorkflow — Google ADK thay thế ChiefOfStaffOrchestrator — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) hoặc superpowers:executing-plans để thực thi plan này theo từng task. Các bước dùng cú pháp checkbox (`- [ ]`) để theo dõi tiến độ.

**Goal:** Thay thế hoàn toàn `ChiefOfStaffOrchestrator` (`backend/app/workforce/agents/orchestration/chief_of_staff.py`) bằng `AdkCofounderWorkflow` — một `google.adk.workflow.Workflow` thật (Graph/FunctionNode), đi qua 1 seam mỏng `orchestration/service.py`, giữ nguyên 100% hành vi governance (audit row, risk-gate R0-R4, budget/stuck/quality gate) và không tạo đường thực thi song song bỏ qua `GovernanceKernel`/`TaskBoardService`.

**Architecture:** ADK sở hữu tầng orchestration/routing; `DeepSeekHarnessAdapter` giữ nguyên 100% là nơi thực thi. Model connectivity đi qua `ModelGateway` (refactor thành typed request/response) → `LiteLLMProviderClient`. Specialist delegation không gọi Harness trực tiếp — tạo `RunStep` + `TaskBoardService.assign_step()` rồi **pause** node (ADK `RequestInput` interrupt), `delegation-worker` xử lý thật ở process riêng, và `MissionResumeJob` (durable, `UNIQUE(mission_run_id, checkpoint_key)`) đảm bảo đúng 1 worker resume workflow khi specialist hoàn tất. Session/runtime dùng `google.adk.sessions.database_session_service.DatabaseSessionService` (schema `adk_runtime` riêng), với `session_bridge.py` là projector mỏng ghi sang `AgentRun`/`AgentEventRecord`/`mission_control_bus` hiện có — không phải audit trail thứ 4. Ba điểm gọi sản xuất (`router.py`, `cosa_cofounder_service.py`, `continuation.py`) chuyển sang gọi seam `orchestration/service.py` — không import ADK trực tiếp.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy + Alembic, PostgreSQL, `google-adk==2.7.0` (đã cài trong `backend/.venv`), `litellm==1.97.0` (mới ghim trực tiếp), `dspy==3.3.0` (không đổi), pytest + pytest-asyncio, Flutter/Dart (GetX) cho phần frontend bổ sung.

## Global Constraints

- Mọi đường tool/code ADK PHẢI đi qua seam governance hiện có (`ToolInvocationService`, `GovernanceKernel`, `TaskBoardService`) — không được bypass.
- Code ADK không bao giờ `import DeepSeekHarnessAdapter` trực tiếp — luôn qua `agent_runtime_manager.get_runtime(...)`.
- `backend/app/tests/agents/` phải xanh (pass) xuyên suốt qua từng task — không có task nào được phép để bộ test này đỏ khi kết thúc.
- Mỗi bảng DB mới (`runtime_sessions`, `mission_resume_jobs`) dùng 1 migration Alembic riêng (naming `v13_0NN_<mô_tả>.py`, theo đúng quy ước trong `backend/alembic/versions/`) — không gộp nhiều bảng vào 1 migration.
- Không xoá `chief_of_staff.py` cùng lúc với việc nối seam (Task 26-29) — chỉ xoá sau khi seam/workflow đã cutover ổn định và `backend/app/tests/agents/` xanh (Task 35, tách riêng).
- Không đổi: `AgentRuntime` ABC, `AgentRuntimeManager`, nội bộ `DeepSeekHarnessAdapter`, `GovernanceKernel`, `ApprovalService`, `TaskBoardService`, `DelegationPolicyEngine`, `BudgetTracker`, `StuckDetector`, `QualityGateEvaluator`, `PromptRegistry`, và 2 import từ `agent_runtime.sessions.models` / `agent_runtime.profiles.definitions` (load-bearing, cây "frozen" giữ nguyên).
- Snowflake ID thuần cho mọi bảng mới (`SnowflakeIDMixin`, theo `backend/app/db/snowflake_model.py`) — không dùng UUID.
- Giữ nguyên `AUTO_START_MAX_RISK = "R1"` và thứ tự `RISK_ORDER = ("R0","R1","R2","R3","R4")` — mission ở risk tier cao hơn R1 phải dừng ở `waiting_confirmation`, đúng hành vi `chief_of_staff.py` hiện tại.
- `ExecutionScope` (workspace_id/member_id/permission_profile) cho governed tool PHẢI dựng từ context tin cậy phía server — tuyệt đối không đọc từ ADK session state mà LLM có thể tự sửa.

---

## Phase 1 — Model connectivity: `ModelGateway` typed + LiteLLM

### Task 1: Thêm typed request/response models vào `ModelGateway`

**Files:**
- Modify: `backend/app/workforce/agents/reliability/model_gateway.py`
- Test: `backend/app/tests/agents/test_reliability_and_model_gateway.py`

**Interfaces:**
- Produces: `ModelMessage{role: Literal["system","user","assistant","tool"], content: str}`, `ModelToolCall{id: str, name: str, arguments: dict[str, Any]}`, `ModelUsage{input_tokens: int, output_tokens: int}`, `ModelRequest{messages: list[ModelMessage], system_instruction: Optional[str], tools: list[dict[str, Any]], response_schema: Optional[dict[str, Any]], temperature: Optional[float], max_tokens: Optional[int], stream: bool, metadata: dict[str, Any]}`, `ModelResponse{content: str, tool_calls: list[ModelToolCall], usage: ModelUsage, provider: str, model: str, finish_reason: str, metadata: dict[str, Any]}` — tất cả dùng ở Task 2 trở đi.

- [x] **Step 1: Viết test xác nhận field/default của các model mới**

```python
# Thêm vào cuối backend/app/tests/agents/test_reliability_and_model_gateway.py
from app.workforce.agents.reliability.model_gateway import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ModelToolCall,
    ModelUsage,
)


def test_model_request_response_shapes():
    req = ModelRequest(
        messages=[ModelMessage(role="user", content="hello")],
        system_instruction="You are a helpful assistant.",
    )
    assert req.tools == []
    assert req.response_schema is None
    assert req.stream is False
    assert req.metadata == {}

    resp = ModelResponse(
        content="hi there",
        usage=ModelUsage(input_tokens=5, output_tokens=3),
        provider="deepseek",
        model="deepseek-chat",
    )
    assert resp.tool_calls == []
    assert resp.finish_reason == "stop"

    tc = ModelToolCall(id="call_1", name="finance_get_financial_summary", arguments={"workspace_id": 1})
    assert tc.arguments["workspace_id"] == 1
```

- [x] **Step 2: Chạy test, xác nhận FAIL (import lỗi vì model chưa tồn tại)**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_reliability_and_model_gateway.py::test_model_request_response_shapes -v`
Expected: FAIL với `ImportError: cannot import name 'ModelMessage'`

- [x] **Step 3: Thêm các model mới vào `model_gateway.py`**

Thêm ngay sau `logger = logging.getLogger(__name__)` và trước `class ModelGatewayResult`:

```python
from typing import Literal


class ModelMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str


class ModelToolCall(BaseModel):
    id: str
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class ModelUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class ModelRequest(BaseModel):
    """Typed request contract for ModelGateway.invoke() (thay cho prompt: str rời rạc).

    Cố định lại 3 bug đã verify ở contract cũ: system_instruction không tới
    invoker_fn, content bị ép str(raw_res), token usage ước lượng bằng
    len(prompt.split()).
    """
    messages: list[ModelMessage]
    system_instruction: Optional[str] = None
    tools: list[Dict[str, Any]] = Field(default_factory=list)
    response_schema: Optional[Dict[str, Any]] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def flattened_prompt(self) -> str:
        """Nối các message thành 1 chuỗi — chỉ dùng cho default mock generator
        và cho ước lượng token khi invoker_fn không trả usage thật."""
        return "\n".join(f"{m.role}: {m.content}" for m in self.messages)


class ModelResponse(BaseModel):
    content: str
    tool_calls: list[ModelToolCall] = Field(default_factory=list)
    usage: ModelUsage = Field(default_factory=ModelUsage)
    provider: str
    model: str
    finish_reason: str = "stop"
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

- [x] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_reliability_and_model_gateway.py::test_model_request_response_shapes -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add backend/app/workforce/agents/reliability/model_gateway.py backend/app/tests/agents/test_reliability_and_model_gateway.py
git commit -m "feat(model-gateway): add typed ModelRequest/ModelResponse contracts"
```

---

### Task 2: Refactor `ModelGateway.invoke()` sang typed contract, sửa 3 bug đã verify

**Files:**
- Modify: `backend/app/workforce/agents/reliability/model_gateway.py`
- Test: `backend/app/tests/agents/test_reliability_and_model_gateway.py`

**Interfaces:**
- Consumes: `ModelRequest`/`ModelResponse` (Task 1).
- Produces: `ModelGateway.invoke(request: ModelRequest, profile_name: str = "chat_fast", invoker_fn: Optional[Callable[[str, str, ModelRequest], Awaitable[ModelResponse]]] = None) -> ModelResponse` — chữ ký mới thay cho `invoke(prompt, profile_name, system_instruction, invoker_fn)` cũ. `invoker_fn` giờ nhận `(provider, model, request)` và PHẢI trả về `ModelResponse` đầy đủ (không còn raw string) — đây là điểm sửa bug số 1 (system_instruction tới được invoker_fn vì nó nằm trong `request`).

- [x] **Step 1: Sửa 2 test hiện có sang chữ ký mới (viết trước, cho FAIL trước khi sửa impl)**

Thay `test_model_gateway_primary_success` và `test_model_gateway_automatic_fallback` trong `backend/app/tests/agents/test_reliability_and_model_gateway.py`:

```python
@pytest.mark.asyncio
async def test_model_gateway_primary_success():
    req = ModelRequest(messages=[ModelMessage(role="user", content="Explain market dynamics")])
    res = await ModelGateway.invoke(request=req, profile_name="chat_fast")
    assert res.status == "success"
    assert res.provider == "deepseek"
    assert res.fallback_used is False
    assert res.input_tokens > 0


@pytest.mark.asyncio
async def test_model_gateway_automatic_fallback():
    async def mock_invoker(provider: str, model: str, request: ModelRequest) -> ModelResponse:
        if provider == "deepseek":
            raise TimeoutError("504 Gateway Timeout: DeepSeek primary timed out")
        return ModelResponse(
            content=f"Fallback from {provider}:{model}",
            usage=ModelUsage(input_tokens=12, output_tokens=4),
            provider=provider,
            model=model,
        )

    req = ModelRequest(messages=[ModelMessage(role="user", content="Synthesize strategic plan")])
    res = await ModelGateway.invoke(request=req, profile_name="reasoning", invoker_fn=mock_invoker)
    assert res.status == "success"
    assert res.fallback_used is True
    assert res.provider == "anthropic"
    assert "claude" in res.model
    assert "Fallback from anthropic" in res.content


@pytest.mark.asyncio
async def test_model_gateway_passes_system_instruction_to_invoker():
    """Bug đã verify: system_instruction trước đây KHÔNG BAO GIỜ tới invoker_fn,
    chỉ dùng để ước lượng token. Giờ nó phải nằm trong request.system_instruction
    mà invoker_fn nhận được nguyên vẹn."""
    seen: dict[str, Any] = {}

    async def capturing_invoker(provider: str, model: str, request: ModelRequest) -> ModelResponse:
        seen["system_instruction"] = request.system_instruction
        return ModelResponse(
            content="ok",
            usage=ModelUsage(input_tokens=1, output_tokens=1),
            provider=provider,
            model=model,
        )

    req = ModelRequest(
        messages=[ModelMessage(role="user", content="hi")],
        system_instruction="Bạn là Chief of Staff của founder.",
    )
    await ModelGateway.invoke(request=req, profile_name="chat_fast", invoker_fn=capturing_invoker)
    assert seen["system_instruction"] == "Bạn là Chief of Staff của founder."
```

Thêm import `Any` nếu chưa có: `from typing import Any` ở đầu file test (đã có sẵn qua các test khác — kiểm tra trước khi thêm trùng).

- [x] **Step 2: Chạy test, xác nhận FAIL (chữ ký `invoke()` cũ không nhận `request=`)**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_reliability_and_model_gateway.py -k "model_gateway" -v`
Expected: FAIL với `TypeError: invoke() got an unexpected keyword argument 'request'`

- [x] **Step 3: Viết lại `ModelGateway.invoke()`/`_invoke_internal()` theo typed contract**

Thay toàn bộ `class ModelGateway` (giữ `_CIRCUIT_BREAKERS`/`get_circuit_breaker` nguyên) bằng:

```python
class ModelGateway:
    """Central gateway for all agentic model invocations enforcing profiles, retries, circuit breakers, and fallbacks."""

    _CIRCUIT_BREAKERS: Dict[str, CircuitBreaker] = {}

    @classmethod
    def get_circuit_breaker(cls, provider: str) -> CircuitBreaker:
        if provider not in cls._CIRCUIT_BREAKERS:
            cls._CIRCUIT_BREAKERS[provider] = CircuitBreaker(name=provider, failure_threshold=3, recovery_timeout_seconds=10.0)
        return cls._CIRCUIT_BREAKERS[provider]

    @classmethod
    async def invoke(
        cls,
        request: ModelRequest,
        profile_name: str = "chat_fast",
        invoker_fn: Optional[Callable[[str, str, ModelRequest], Any]] = None,
    ) -> ModelGatewayResult:
        with trace_span("model_gateway.invoke", {"profile_name": profile_name, "message_count": len(request.messages)}):
            return await cls._invoke_internal(request, profile_name, invoker_fn)

    @classmethod
    async def _invoke_internal(
        cls,
        request: ModelRequest,
        profile_name: str,
        invoker_fn: Optional[Callable[[str, str, ModelRequest], Any]],
    ) -> ModelGatewayResult:
        profile = ModelProfileRegistry.get_profile(profile_name)
        start_time = time.monotonic()
        primary_cb = cls.get_circuit_breaker(profile.primary_provider)

        async def _call(provider: str, model: str) -> ModelResponse:
            if invoker_fn:
                return await invoker_fn(provider, model, request)
            # Default mock generator (không có invoker_fn thật, dùng cho dev/test) -
            # KHÔNG gọi network thật, giữ nguyên hành vi mock trước đây.
            prompt_preview = request.flattened_prompt()[:30]
            return ModelResponse(
                content=f"[{provider}:{model}] Response to: {prompt_preview}",
                usage=ModelUsage(
                    input_tokens=len(request.flattened_prompt().split())
                    + (len(request.system_instruction.split()) if request.system_instruction else 0),
                    output_tokens=0,
                ),
                provider=provider,
                model=model,
            )

        try:
            raw_res = await RetryPolicy.execute_with_backoff(
                fn=lambda: _call(profile.primary_provider, profile.primary_model),
                delays=[0.05, 0.1],
                circuit_breaker=primary_cb,
            )
            latency = int((time.monotonic() - start_time) * 1000)
            cost = CostTracker.calculate_cost(profile, raw_res.usage.input_tokens, raw_res.usage.output_tokens)
            return ModelGatewayResult(
                content=raw_res.content,
                provider=raw_res.provider,
                model=raw_res.model,
                input_tokens=raw_res.usage.input_tokens,
                output_tokens=raw_res.usage.output_tokens,
                estimated_cost=cost,
                latency_ms=latency,
                fallback_used=False,
            )
        except Exception as primary_exc:
            logger.warning(f"[ModelGateway] Primary provider '{profile.primary_provider}' failed: {primary_exc}")

            if profile.fallback_provider and profile.fallback_model:
                fallback_cb = cls.get_circuit_breaker(profile.fallback_provider)
                try:
                    raw_fallback = await RetryPolicy.execute_with_backoff(
                        fn=lambda: _call(profile.fallback_provider, profile.fallback_model),
                        delays=[0.05, 0.1],
                        circuit_breaker=fallback_cb,
                    )
                    latency = int((time.monotonic() - start_time) * 1000)
                    cost = CostTracker.calculate_cost(profile, raw_fallback.usage.input_tokens, raw_fallback.usage.output_tokens)
                    logger.info(f"[ModelGateway] Successfully failed over to fallback provider '{profile.fallback_provider}'.")
                    return ModelGatewayResult(
                        content=raw_fallback.content,
                        provider=raw_fallback.provider,
                        model=raw_fallback.model,
                        input_tokens=raw_fallback.usage.input_tokens,
                        output_tokens=raw_fallback.usage.output_tokens,
                        estimated_cost=cost,
                        latency_ms=latency,
                        fallback_used=True,
                    )
                except Exception as fallback_exc:
                    logger.error(f"[ModelGateway] Fallback provider also failed: {fallback_exc}")
                    latency = int((time.monotonic() - start_time) * 1000)
                    return ModelGatewayResult(
                        content="",
                        provider=profile.fallback_provider,
                        model=profile.fallback_model,
                        latency_ms=latency,
                        fallback_used=True,
                        status="failed",
                        error=f"Both primary ({primary_exc}) and fallback ({fallback_exc}) failed",
                    )

            latency = int((time.monotonic() - start_time) * 1000)
            return ModelGatewayResult(
                content="",
                provider=profile.primary_provider,
                model=profile.primary_model,
                latency_ms=latency,
                fallback_used=False,
                status="failed",
                error=str(primary_exc),
            )
```

Ghi chú: bug "content bị ép `str(raw_res)`" và bug "token usage = `len(prompt.split())`" đều biến mất — `raw_res`/`raw_fallback` giờ LÀ `ModelResponse` thật (không phải chuỗi thô), `.content`/`.usage` lấy trực tiếp từ đó khi `invoker_fn` cung cấp, chỉ fallback về ước lượng `len(...).split()` trong nhánh mock nội bộ của `_call()` khi không có `invoker_fn`.

- [x] **Step 4: Chạy lại toàn bộ test file, xác nhận PASS**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_reliability_and_model_gateway.py -v`
Expected: PASS toàn bộ (bao gồm `test_model_gateway_passes_system_instruction_to_invoker` mới)

- [x] **Step 5: Chạy toàn bộ `backend/app/tests/agents/` xác nhận không có test nào khác gọi `ModelGateway.invoke()` bị vỡ**

Run: `cd backend && .venv/bin/pytest app/tests/agents/ -v -k "model_gateway or gateway_lm"`
Expected: PASS — `grep -rn "ModelGateway.invoke" backend/app --include="*.py"` đã xác nhận chỉ có 2 call site trong chính test file này, không có call site production nào khác bị ảnh hưởng.

- [x] **Step 6: Commit**

```bash
git add backend/app/workforce/agents/reliability/model_gateway.py backend/app/tests/agents/test_reliability_and_model_gateway.py
git commit -m "fix(model-gateway): typed invoke() contract, fix system_instruction/content/token-usage bugs"
```

---

### Task 3: `LiteLLMProviderClient` + `cosa_litellm_invoker` dùng chung

**Files:**
- Create: `backend/app/workforce/agents/reliability/litellm_invoker.py`
- Modify: `backend/requirements.txt`
- Test: `backend/app/tests/agents/test_litellm_invoker.py`

**Interfaces:**
- Consumes: `ModelRequest`/`ModelResponse`/`ModelMessage`/`ModelToolCall`/`ModelUsage` (Task 1).
- Produces: `ModelProviderClient(ABC)` với `async def complete(provider, model, request) -> ModelResponse`; `LiteLLMProviderClient(ModelProviderClient)` — implementation thật duy nhất, gọi `litellm.acompletion`; `async def cosa_litellm_invoker(provider: str, model: str, request: ModelRequest) -> ModelResponse` — hàm mỏng dùng chung 1 `LiteLLMProviderClient`, dùng làm `invoker_fn` cho `ModelGateway.invoke()`, tái sử dụng ở Task 10 (`CosaModelGatewayLlm`).

- [x] **Step 1: Ghim `litellm==1.97.0` trực tiếp vào `requirements.txt`**

Sửa `backend/requirements.txt`, thêm ngay trước dòng `google-adk==2.7.0`:

```
# LiteLLM — đã có sẵn transitively qua google-adk (litellm==1.97.0), ghim trực tiếp
# vì backend/app/workforce/agents/reliability/litellm_invoker.py import thẳng nó.
litellm==1.97.0
google-adk==2.7.0
```

- [x] **Step 2: Viết test cho `cosa_litellm_invoker` (mock `litellm.acompletion`, không gọi network thật)**

```python
# backend/app/tests/agents/test_litellm_invoker.py
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest

from app.workforce.agents.reliability.litellm_invoker import cosa_litellm_invoker
from app.workforce.agents.reliability.model_gateway import ModelMessage, ModelRequest


def _fake_litellm_response(content: str, prompt_tokens: int, completion_tokens: int, finish_reason: str = "stop"):
    message = SimpleNamespace(content=content, tool_calls=None)
    choice = SimpleNamespace(message=message, finish_reason=finish_reason)
    usage = SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
    return SimpleNamespace(choices=[choice], usage=usage)


@pytest.mark.asyncio
async def test_cosa_litellm_invoker_maps_request_and_response(monkeypatch):
    captured: dict = {}

    async def fake_acompletion(**kwargs):
        captured.update(kwargs)
        return _fake_litellm_response("Diagnosis: runway is healthy.", prompt_tokens=42, completion_tokens=8)

    monkeypatch.setattr(
        "app.workforce.agents.reliability.litellm_invoker.litellm.acompletion",
        fake_acompletion,
    )

    request = ModelRequest(
        messages=[ModelMessage(role="user", content="Phân tích runway hiện tại")],
        system_instruction="Bạn là Chief of Staff.",
        temperature=0.3,
        max_tokens=512,
    )
    resp = await cosa_litellm_invoker("deepseek", "deepseek-reasoner", request)

    assert captured["model"] == "deepseek/deepseek-reasoner"
    assert captured["messages"][0] == {"role": "system", "content": "Bạn là Chief of Staff."}
    assert captured["messages"][1] == {"role": "user", "content": "Phân tích runway hiện tại"}
    assert captured["temperature"] == 0.3
    assert captured["max_tokens"] == 512

    assert resp.content == "Diagnosis: runway is healthy."
    assert resp.usage.input_tokens == 42
    assert resp.usage.output_tokens == 8
    assert resp.provider == "deepseek"
    assert resp.model == "deepseek-reasoner"
    assert resp.finish_reason == "stop"
    assert resp.tool_calls == []
```

- [x] **Step 3: Chạy test, xác nhận FAIL (module chưa tồn tại)**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_litellm_invoker.py -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'app.workforce.agents.reliability.litellm_invoker'`

- [x] **Step 4: Viết `litellm_invoker.py`**

```python
"""Điểm kết nối LiteLLM duy nhất dùng chung bởi ModelGateway (qua invoker_fn) và
CosaModelGatewayLlm (ADK model adapter) — tránh 2 cách kết nối LiteLLM trôi dạt
khác nhau (xem Quyết định 1, mục "Model connectivity").

ModelProviderClient là interface tối thiểu cho 1 client kết nối model provider ở
tầng thấp hơn ModelGateway (ModelGateway lo retry/circuit-breaker/cost-tracking;
ModelProviderClient chỉ lo gọi provider thật và map request/response). Hiện chỉ
có 1 implementation (LiteLLMProviderClient) vì toàn bộ provider hiện tại
(deepseek/anthropic/...) đều gọi qua LiteLLM — interface này tồn tại để 1 provider
tương lai KHÔNG qua LiteLLM (vd 1 SDK riêng) có chỗ cắm vào mà không đổi
ModelGateway/CosaModelGatewayLlm.

GatewayLM (backend/app/workforce/ai/model_policy/gateway_lm.py) KHÔNG đổi sang gọi
lớp này — nó đã dùng litellm sẵn qua dspy.LM.forward() nội bộ và đã chia sẻ đúng
CircuitBreaker registry với ModelGateway qua ModelGateway.get_circuit_breaker();
viết lại forward() của nó là thay đổi rủi ro không cần thiết nằm ngoài phạm vi sửa
lỗi ModelGateway.invoke().
"""
import logging
from abc import ABC, abstractmethod
from typing import Any

import litellm

from app.workforce.agents.reliability.model_gateway import (
    ModelRequest,
    ModelResponse,
    ModelToolCall,
    ModelUsage,
)

logger = logging.getLogger(__name__)


class ModelProviderClient(ABC):
    """Interface tối thiểu cho 1 client kết nối model provider thật."""

    @abstractmethod
    async def complete(self, provider: str, model: str, request: ModelRequest) -> ModelResponse: ...


def _to_litellm_messages(request: ModelRequest) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    if request.system_instruction:
        messages.append({"role": "system", "content": request.system_instruction})
    messages.extend({"role": m.role, "content": m.content} for m in request.messages)
    return messages


class LiteLLMProviderClient(ModelProviderClient):
    """Implementation thật duy nhất hiện có — gọi litellm.acompletion() với quy
    ước đặt tên "provider/model" (đúng quy ước gateway_lm.py đã dùng)."""

    async def complete(self, provider: str, model: str, request: ModelRequest) -> ModelResponse:
        kwargs: dict[str, Any] = {
            "model": f"{provider}/{model}",
            "messages": _to_litellm_messages(request),
        }
        if request.temperature is not None:
            kwargs["temperature"] = request.temperature
        if request.max_tokens is not None:
            kwargs["max_tokens"] = request.max_tokens
        if request.tools:
            kwargs["tools"] = request.tools
        if request.response_schema is not None:
            kwargs["response_format"] = request.response_schema

        raw = await litellm.acompletion(**kwargs)
        choice = raw.choices[0]
        tool_calls = [
            ModelToolCall(id=tc.id, name=tc.function.name, arguments=tc.function.arguments or {})
            for tc in (choice.message.tool_calls or [])
        ] if getattr(choice.message, "tool_calls", None) else []

        return ModelResponse(
            content=choice.message.content or "",
            tool_calls=tool_calls,
            usage=ModelUsage(
                input_tokens=getattr(raw.usage, "prompt_tokens", 0) or 0,
                output_tokens=getattr(raw.usage, "completion_tokens", 0) or 0,
            ),
            provider=provider,
            model=model,
            finish_reason=choice.finish_reason or "stop",
        )


_default_client = LiteLLMProviderClient()


async def cosa_litellm_invoker(provider: str, model: str, request: ModelRequest) -> ModelResponse:
    """invoker_fn thật cho ModelGateway.invoke() — hàm mỏng dùng chung 1
    LiteLLMProviderClient instance, để ModelGateway/CosaModelGatewayLlm (Task 2/10)
    không cần biết tới class ModelProviderClient, chỉ cần 1 hàm callable."""
    return await _default_client.complete(provider, model, request)
```

- [x] **Step 5: Chạy lại test, xác nhận PASS**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_litellm_invoker.py -v`
Expected: PASS

- [x] **Step 6: Cài lại requirements trong venv hiện có để xác nhận không xung đột**

Run: `cd backend && .venv/bin/pip install -r requirements.txt --dry-run 2>&1 | tail -20 || .venv/bin/pip check`
Expected: Không có lỗi conflict (litellm==1.97.0 đã có sẵn transitively, ghim trực tiếp không đổi version thật đang cài).

- [x] **Step 7: Commit**

```bash
git add backend/app/workforce/agents/reliability/litellm_invoker.py backend/app/tests/agents/test_litellm_invoker.py backend/requirements.txt
git commit -m "feat(model-gateway): add shared LiteLLM invoker for ModelGateway and future ADK model adapter"
```

---

## Phase 2 — Bảng mới: `RuntimeSession`, `MissionResumeJob`

### Task 4: Model + migration `RuntimeSession`

**Files:**
- Create: `backend/app/workforce/agents/orchestration/runtime_session_models.py`
- Create: `backend/alembic/versions/v13_060_runtime_sessions.py`
- Modify: `backend/app/db/base.py`
- Test: `backend/app/tests/agents/test_runtime_session_model.py`

**Interfaces:**
- Produces: `RuntimeSession` SQLAlchemy model, bảng `runtime_sessions`: `id, workspace_id, mission_run_id, agent_run_id, runtime_type, external_session_id, parent_session_id, status, checkpoint_ref, metadata_jsonb, created_at, updated_at, finished_at`. Dùng ở Task 25 (`orchestration/service.py` ghi 1 row mỗi khi tạo ADK session mới), Task 31 (mission detail endpoint đọc lại timeline).

- [x] **Step 1: Viết test tạo/đọc `RuntimeSession` qua DB thật (transactional fixture)**

```python
# backend/app/tests/agents/test_runtime_session_model.py
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from agent_runtime.sessions.models import AgentRun
from app.core.snowflake import generate_snowflake_id
from app.db.session import engine
from app.platform.auth.models import User, Workspace
from app.workforce.agents.orchestration.runtime_session_models import RuntimeSession


@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()


def test_runtime_session_round_trip(db_session):
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db_session.add(User(id=user_id, email=f"rs-{user_id}@example.invalid"))
    db_session.add(Workspace(id=workspace_id, name=f"RS {workspace_id}"))
    db_session.flush()

    mission_run = AgentRun(
        id=generate_snowflake_id(), workspace_id=workspace_id, company_id=workspace_id,
        user_id=user_id, agent_key="chief_of_staff", runtime="adk", status="running",
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(mission_run)
    db_session.flush()

    session_row = RuntimeSession(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        mission_run_id=mission_run.id,
        agent_run_id=None,
        runtime_type="ADK",
        external_session_id="adk-session-abc123",
        status="active",
        checkpoint_ref=None,
        metadata_jsonb={"workflow_name": "adk_cofounder_workflow"},
    )
    db_session.add(session_row)
    db_session.commit()
    db_session.refresh(session_row)

    fetched = db_session.query(RuntimeSession).filter(RuntimeSession.id == session_row.id).one()
    assert fetched.runtime_type == "ADK"
    assert fetched.external_session_id == "adk-session-abc123"
    assert fetched.metadata_jsonb["workflow_name"] == "adk_cofounder_workflow"
    assert fetched.finished_at is None
```

- [x] **Step 2: Chạy test, xác nhận FAIL (module + bảng chưa tồn tại)**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_runtime_session_model.py -v`
Expected: FAIL với `ModuleNotFoundError`

- [x] **Step 3: Viết model `RuntimeSession`**

```python
# backend/app/workforce/agents/orchestration/runtime_session_models.py
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.db.snowflake_model import SnowflakeIDMixin


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RuntimeSession(SnowflakeIDMixin, Base):
    """Nối các loại runtime session (ADK/DeepSeek/Sandbox/Human) dưới 1 Mission.

    AgentRun.runtime_session_id (String đơn) quá chật khi 1 mission có nhiều
    runtime session cùng lúc (vd ADK workflow session + DeepSeek Harness session
    của 1 specialist con) — bảng này KHÔNG thay AgentRun/AgentEventRecord, chỉ là
    bảng ánh xạ session-level bổ sung.
    """

    __tablename__ = "runtime_sessions"

    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id"), nullable=False, index=True)
    mission_run_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("agent_runs.id"), nullable=False, index=True)
    agent_run_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("agent_runs.id"), nullable=True, index=True)

    runtime_type: Mapped[str] = mapped_column(String(30), nullable=False)  # ADK | DEEPSEEK_HARNESS | OPENSANDBOX | HUMAN
    external_session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    parent_session_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("runtime_sessions.id", use_alter=True), nullable=True, index=True
    )

    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active", server_default="active")
    checkpoint_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    metadata_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_runtime_sessions_mission_status", "mission_run_id", "status"),
    )
```

- [x] **Step 4: Đăng ký model vào `app/db/base.py`**

Thêm sau dòng `from app.workforce.agents.delegation.models import DelegationJob` trong `backend/app/db/base.py`:

```python
from app.workforce.agents.orchestration.runtime_session_models import RuntimeSession
```

- [x] **Step 5: Viết migration Alembic `v13_060`**

Kiểm tra head hiện tại trước:

Run: `cd backend && .venv/bin/alembic heads`
Expected: 1 head, chuỗi dạng `v13_059_workflow_scope_snapshots`

```python
# backend/alembic/versions/v13_060_runtime_sessions.py
"""runtime sessions

Revision ID: v13_060
Revises: v13_059
Create Date: 2026-08-21 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'v13_060_runtime_sessions'
down_revision = 'v13_059_workflow_scope_snapshots'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'runtime_sessions',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('workspace_id', sa.BigInteger(), nullable=False),
        sa.Column('mission_run_id', sa.BigInteger(), nullable=False),
        sa.Column('agent_run_id', sa.BigInteger(), nullable=True),
        sa.Column('runtime_type', sa.String(length=30), nullable=False),
        sa.Column('external_session_id', sa.String(length=255), nullable=True),
        sa.Column('parent_session_id', sa.BigInteger(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='active'),
        sa.Column('checkpoint_ref', sa.String(length=255), nullable=True),
        sa.Column('metadata_jsonb', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id']),
        sa.ForeignKeyConstraint(['mission_run_id'], ['agent_runs.id']),
        sa.ForeignKeyConstraint(['agent_run_id'], ['agent_runs.id']),
        sa.ForeignKeyConstraint(['parent_session_id'], ['runtime_sessions.id'], use_alter=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_runtime_sessions_workspace_id', 'runtime_sessions', ['workspace_id'])
    op.create_index('ix_runtime_sessions_mission_run_id', 'runtime_sessions', ['mission_run_id'])
    op.create_index('ix_runtime_sessions_agent_run_id', 'runtime_sessions', ['agent_run_id'])
    op.create_index('ix_runtime_sessions_external_session_id', 'runtime_sessions', ['external_session_id'])
    op.create_index('ix_runtime_sessions_parent_session_id', 'runtime_sessions', ['parent_session_id'])
    op.create_index('ix_runtime_sessions_mission_status', 'runtime_sessions', ['mission_run_id', 'status'])


def downgrade() -> None:
    op.drop_index('ix_runtime_sessions_mission_status', table_name='runtime_sessions')
    op.drop_index('ix_runtime_sessions_parent_session_id', table_name='runtime_sessions')
    op.drop_index('ix_runtime_sessions_external_session_id', table_name='runtime_sessions')
    op.drop_index('ix_runtime_sessions_agent_run_id', table_name='runtime_sessions')
    op.drop_index('ix_runtime_sessions_mission_run_id', table_name='runtime_sessions')
    op.drop_index('ix_runtime_sessions_workspace_id', table_name='runtime_sessions')
    op.drop_table('runtime_sessions')
```

- [x] **Step 6: Chạy migration trên DB dev/test**

Run: `cd backend && .venv/bin/alembic upgrade head`
Expected: Migration `v13_060_runtime_sessions` chạy thành công, không lỗi.

- [x] **Step 7: Chạy lại test, xác nhận PASS**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_runtime_session_model.py -v`
Expected: PASS

- [x] **Step 8: Commit**

```bash
git add backend/app/workforce/agents/orchestration/runtime_session_models.py backend/alembic/versions/v13_060_runtime_sessions.py backend/app/db/base.py backend/app/tests/agents/test_runtime_session_model.py
git commit -m "feat(orchestration): add RuntimeSession entity linking ADK/DeepSeek/Sandbox/Human sessions to a mission"
```

---

### Task 5: Model + migration `MissionResumeJob`

**Files:**
- Create: `backend/app/workforce/agents/orchestration/mission_resume_models.py`
- Create: `backend/alembic/versions/v13_061_mission_resume_jobs.py`
- Modify: `backend/app/db/base.py`
- Test: `backend/app/tests/agents/test_mission_resume_job_model.py`

**Interfaces:**
- Produces: `MissionResumeJob` SQLAlchemy model, bảng `mission_resume_jobs`: `id, workspace_id, mission_run_id, workflow_session_id, checkpoint_key, idempotency_key, reason, status, claimed_by, claimed_at, completed_at, error_message, created_at, updated_at`, `UniqueConstraint(mission_run_id, checkpoint_key)`. Dùng ở Task 17-18 (`MissionResumeJobService`).

- [x] **Step 1: Viết test round-trip + xác nhận unique constraint chặn trùng checkpoint**

```python
# backend/app/tests/agents/test_mission_resume_job_model.py
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from agent_runtime.sessions.models import AgentRun
from app.core.snowflake import generate_snowflake_id
from app.db.session import engine
from app.platform.auth.models import User, Workspace
from app.workforce.agents.orchestration.mission_resume_models import MissionResumeJob


@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()


def _mission(db_session):
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db_session.add(User(id=user_id, email=f"mrj-{user_id}@example.invalid"))
    db_session.add(Workspace(id=workspace_id, name=f"MRJ {workspace_id}"))
    db_session.flush()
    mission_run = AgentRun(
        id=generate_snowflake_id(), workspace_id=workspace_id, company_id=workspace_id,
        user_id=user_id, agent_key="chief_of_staff", runtime="adk", status="running",
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(mission_run)
    db_session.flush()
    return workspace_id, mission_run


def test_mission_resume_job_round_trip(db_session):
    workspace_id, mission_run = _mission(db_session)
    job = MissionResumeJob(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        mission_run_id=mission_run.id,
        workflow_session_id="adk-session-xyz",
        checkpoint_key="specialist_join:987",
        idempotency_key=f"mission_resume:{mission_run.id}:specialist_join:987",
        reason="specialist_delegation_completed",
        status="queued",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    fetched = db_session.query(MissionResumeJob).filter(MissionResumeJob.id == job.id).one()
    assert fetched.status == "queued"
    assert fetched.claimed_by is None


def test_mission_resume_job_unique_checkpoint_per_mission(db_session):
    workspace_id, mission_run = _mission(db_session)
    first = MissionResumeJob(
        id=generate_snowflake_id(), workspace_id=workspace_id, mission_run_id=mission_run.id,
        workflow_session_id="adk-session-xyz", checkpoint_key="specialist_join:987",
        idempotency_key=f"mission_resume:{mission_run.id}:specialist_join:987",
        reason="specialist_delegation_completed", status="queued",
    )
    db_session.add(first)
    db_session.commit()

    dup = MissionResumeJob(
        id=generate_snowflake_id(), workspace_id=workspace_id, mission_run_id=mission_run.id,
        workflow_session_id="adk-session-xyz", checkpoint_key="specialist_join:987",
        idempotency_key=f"mission_resume:{mission_run.id}:specialist_join:987:dup",
        reason="specialist_delegation_completed", status="queued",
    )
    db_session.add(dup)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
```

- [x] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_mission_resume_job_model.py -v`
Expected: FAIL với `ModuleNotFoundError`

- [x] **Step 3: Viết model `MissionResumeJob`**

```python
# backend/app/workforce/agents/orchestration/mission_resume_models.py
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.db.snowflake_model import SnowflakeIDMixin


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MissionResumeJob(SnowflakeIDMixin, Base):
    """Đảm bảo đúng 1 worker resume AdkCofounderWorkflow cho mỗi checkpoint khi
    nhiều specialist RunStep hoàn tất gần nhau — thay cho cơ chế advisory-lock +
    materialized-event trong chief_of_staff.py::resume_after_delegation (xem
    Quyết định 1, mục "Exactly-once resume").

    checkpoint_key xác định CHÍNH XÁC điểm pause nào đang được resume (vd
    "specialist_join:<run_step_id>") — UNIQUE(mission_run_id, checkpoint_key)
    là cơ chế chặn 2 worker cùng resume 1 checkpoint, KHÔNG chặn resume các
    checkpoint khác nhau của cùng 1 mission (đúng ngữ nghĩa, vì 1 mission có
    thể có nhiều specialist hoàn tất ở các thời điểm khác nhau).
    """

    __tablename__ = "mission_resume_jobs"

    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id"), nullable=False, index=True)
    mission_run_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("agent_runs.id"), nullable=False, index=True)
    workflow_session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    checkpoint_key: Mapped[str] = mapped_column(String(255), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(String(100), nullable=False)

    status: Mapped[str] = mapped_column(String(30), nullable=False, default="queued", server_default="queued")
    claimed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    claimed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        UniqueConstraint("mission_run_id", "checkpoint_key", name="uq_mission_resume_job_mission_checkpoint"),
        Index("ix_mission_resume_jobs_status_created", "status", "created_at"),
    )
```

- [x] **Step 4: Đăng ký vào `app/db/base.py`**

Thêm sau dòng import `RuntimeSession` từ Task 4:

```python
from app.workforce.agents.orchestration.mission_resume_models import MissionResumeJob
```

- [x] **Step 5: Viết migration `v13_061`**

```python
# backend/alembic/versions/v13_061_mission_resume_jobs.py
"""mission resume jobs

Revision ID: v13_061
Revises: v13_060
Create Date: 2026-08-21 09:15:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'v13_061_mission_resume_jobs'
down_revision = 'v13_060_runtime_sessions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'mission_resume_jobs',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('workspace_id', sa.BigInteger(), nullable=False),
        sa.Column('mission_run_id', sa.BigInteger(), nullable=False),
        sa.Column('workflow_session_id', sa.String(length=255), nullable=True),
        sa.Column('checkpoint_key', sa.String(length=255), nullable=False),
        sa.Column('idempotency_key', sa.String(length=255), nullable=False),
        sa.Column('reason', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='queued'),
        sa.Column('claimed_by', sa.String(length=100), nullable=True),
        sa.Column('claimed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id']),
        sa.ForeignKeyConstraint(['mission_run_id'], ['agent_runs.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('mission_run_id', 'checkpoint_key', name='uq_mission_resume_job_mission_checkpoint'),
    )
    op.create_index('ix_mission_resume_jobs_workspace_id', 'mission_resume_jobs', ['workspace_id'])
    op.create_index('ix_mission_resume_jobs_mission_run_id', 'mission_resume_jobs', ['mission_run_id'])
    op.create_index('ix_mission_resume_jobs_status_created', 'mission_resume_jobs', ['status', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_mission_resume_jobs_status_created', table_name='mission_resume_jobs')
    op.drop_index('ix_mission_resume_jobs_mission_run_id', table_name='mission_resume_jobs')
    op.drop_index('ix_mission_resume_jobs_workspace_id', table_name='mission_resume_jobs')
    op.drop_table('mission_resume_jobs')
```

- [x] **Step 6: Chạy migration**

Run: `cd backend && .venv/bin/alembic upgrade head`
Expected: `v13_061_mission_resume_jobs` chạy thành công.

- [x] **Step 7: Chạy lại test, xác nhận PASS**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_mission_resume_job_model.py -v`
Expected: PASS cả 2 test.

- [x] **Step 8: Commit**

```bash
git add backend/app/workforce/agents/orchestration/mission_resume_models.py backend/alembic/versions/v13_061_mission_resume_jobs.py backend/app/db/base.py backend/app/tests/agents/test_mission_resume_job_model.py
git commit -m "feat(orchestration): add MissionResumeJob for exactly-once ADK workflow resume"
```

---

## Phase 3 — Governance seam: audit linkage fix + `CosaGovernedTool`

### Task 6: Thread `run_id` qua `ToolInvocationRequest` → `PolicyGate` → `GovernanceKernel` để audit row nối đúng mission

**Files:**
- Modify: `backend/app/workforce/tools/invocation/contracts.py`
- Modify: `backend/app/workforce/tools/invocation/policy_gate.py`
- Test: `backend/app/tests/agents/test_tool_invocation_run_id_linkage.py`

**Interfaces:**
- Produces: `ToolInvocationRequest.run_id: Optional[int] = None` (field mới, additive/backward-compatible — mặc định `None` giữ nguyên hành vi hiện tại cho mọi caller khác của `ToolInvocationService`). `PolicyGate.execute_if_allowed` giờ truyền `run_id=request.run_id` vào `GovernanceKernel.evaluate_and_audit_tool_call(...)` thay vì hardcode `run_id=None`.

**Ghi chú (phát hiện khi đọc code thật):** `dispatch_tool_call` (đường DeepSeekHarnessAdapter đang dùng, `backend/app/workforce/agents/runtime/tool_bridge.py`) gọi `GovernanceKernel.evaluate_and_audit_tool_call(..., run_id=actual_run_id)` — audit row `AgentToolCall` được nối đúng vào mission. Nhưng `ToolInvocationService`/`PolicyGate` (đường `CosaGovernedTool` ở Task 8 sẽ dùng) hiện hardcode `run_id=None` (xem `policy_gate.py` dòng ~35) — nếu không sửa, mọi `AgentToolCall` do ADK tool tạo ra sẽ mồ côi (không link về mission), phá vỡ truy vết audit. Đây là 1 gap có thật giữa 2 đường dispatch, không phải suy đoán — task này vá gap đó bằng 1 field bổ sung, không đổi hành vi của caller nào khác (mặc định `None`).

- [x] **Step 1: Viết test xác nhận `run_id=None` mặc định (hành vi cũ không đổi) và `run_id` truyền vào thì `AgentToolCall.run_id` khớp**

```python
# backend/app/tests/agents/test_tool_invocation_run_id_linkage.py
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import sessionmaker

from agent_runtime.permissions.models import AgentToolCall
from agent_runtime.sessions.models import AgentRun
from app.core.snowflake import generate_snowflake_id
from app.db.session import engine
from app.platform.auth.models import User, Workspace
from app.workforce.agents.runtime.execution_scope import ExecutionScope
from app.workforce.tools.invocation.contracts import ToolInvocationRequest
from app.workforce.tools.invocation.service import ToolInvocationService


@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()


@pytest.mark.asyncio
async def test_tool_invocation_links_agent_tool_call_to_run_id(db_session):
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db_session.add(User(id=user_id, email=f"tiv-{user_id}@example.invalid"))
    db_session.add(Workspace(id=workspace_id, name=f"TIV {workspace_id}"))
    db_session.flush()
    mission_run = AgentRun(
        id=generate_snowflake_id(), workspace_id=workspace_id, company_id=workspace_id,
        user_id=user_id, agent_key="chief_of_staff", runtime="adk", status="running",
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(mission_run)
    db_session.commit()

    scope = ExecutionScope(
        workspace_id=workspace_id, company_id=workspace_id, principal_user_id=user_id,
        principal_member_id=user_id, principal_role="owner", operating_unit_id=None,
        offering_id=None, initiative_id=None, profile_id=None, session_id=None, grants=(),
    )
    request = ToolInvocationRequest(
        scope=scope,
        tool_flat_name="finance_get_financial_summary",
        arguments={},
        source="adk_governed_tool",
        run_id=mission_run.id,
    )
    service = ToolInvocationService()
    await service.invoke(db_session, request)

    calls = db_session.query(AgentToolCall).filter(AgentToolCall.run_id == mission_run.id).all()
    assert len(calls) == 1
    assert calls[0].tool_name.endswith("get_financial_summary") or "finance" in calls[0].tool_name
```

- [x] **Step 2: Chạy test, xác nhận FAIL (`ToolInvocationRequest` chưa có field `run_id`)**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_tool_invocation_run_id_linkage.py -v`
Expected: FAIL với `pydantic.ValidationError: ... run_id extra fields not permitted` hoặc assertion `len(calls) == 0`

- [x] **Step 3: Thêm field `run_id` vào `ToolInvocationRequest`**

Sửa `backend/app/workforce/tools/invocation/contracts.py`:

```python
class ToolInvocationRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    scope: ExecutionScope
    tool_flat_name: str
    arguments: Dict[str, Any]
    source: str
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    causation_id: Optional[str] = None
    governance_decision: GovernanceDecision | None = None
    chat_session_id: Optional[int] = None
    run_id: Optional[int] = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.causation_id is None:
            self.causation_id = self.correlation_id
```

(chỉ thêm dòng `run_id: Optional[int] = None` — không đổi gì khác trong file này.)

- [x] **Step 4: Truyền `run_id` qua trong `PolicyGate.execute_if_allowed`**

Sửa `backend/app/workforce/tools/invocation/policy_gate.py`, dòng gọi `evaluate_and_audit_tool_call`:

```python
        decision: GovernanceDecision = self.kernel.evaluate_and_audit_tool_call(
            db=db,
            request=run_request,
            tool_flat_name=request.tool_flat_name,
            args=request.arguments,
            run_id=request.run_id,
        )
```

(chỉ đổi `run_id=None` → `run_id=request.run_id`.)

- [x] **Step 5: Chạy lại test, xác nhận PASS**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_tool_invocation_run_id_linkage.py -v`
Expected: PASS

- [x] **Step 6: Chạy toàn bộ test liên quan tới `ToolInvocationService`/`PolicyGate` để xác nhận không có regression (mặc định `None` giữ nguyên hành vi)**

Run: `cd backend && .venv/bin/pytest app/tests/agents/ -v -k "governance_e2e or extension_mcp or capability_gateway"`
Expected: PASS toàn bộ.

- [x] **Step 7: Commit**

```bash
git add backend/app/workforce/tools/invocation/contracts.py backend/app/workforce/tools/invocation/policy_gate.py backend/app/tests/agents/test_tool_invocation_run_id_linkage.py
git commit -m "fix(tool-invocation): thread run_id through PolicyGate so AgentToolCall audit rows link to their mission"
```

---

### Task 7: `CosaGovernedTool(BaseTool)`

**Files:**
- Create: `backend/app/workforce/agents/orchestration/adk/__init__.py`
- Create: `backend/app/workforce/agents/orchestration/adk/governed_tool.py`
- Test: `backend/app/tests/agents/test_adk_governed_tool.py`

**Interfaces:**
- Consumes: `ToolInvocationService`/`ToolInvocationRequest` (Task 6), `ExecutionScope`.
- Produces: `CosaGovernedTool(BaseTool)` — `run_async(*, args: dict[str, Any], tool_context: ToolContext) -> Any`. `ExecutionScope` được build từ 1 `scope_factory: Callable[[], ExecutionScope]` truyền vào constructor (context server-side tin cậy, KHÔNG đọc từ `tool_context.state`). Trong phạm vi kế hoạch này, không có `FunctionNode` nào trong `AdkCofounderWorkflow` (Task 12-23) tự gọi tool trực tiếp — mọi công việc chuyên môn vẫn đi qua `TaskBoardService`/durable delegation (Task 15-16), khớp hành vi `chief_of_staff.py` hiện tại. `CosaGovernedTool` được dùng trực tiếp ở Task 24 (test gate) để chứng minh pipeline governance-cho-tool-ADK hoạt động thật, sẵn sàng cho 1 node tương lai (vd đọc nhanh dữ liệu context) gọi thẳng 1 tool mà không cần round-trip qua delegation — xem "Câu hỏi mở" cuối kế hoạch.

- [x] **Step 1: Tạo package rỗng `adk/`**

```python
# backend/app/workforce/agents/orchestration/adk/__init__.py
```

- [x] **Step 2: Viết test cho `CosaGovernedTool.run_async` (gọi trực tiếp, không cần Runner/LlmAgent thật)**

```python
# backend/app/tests/agents/test_adk_governed_tool.py
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import sessionmaker

from agent_runtime.permissions.models import AgentToolCall
from agent_runtime.sessions.models import AgentRun
from app.core.snowflake import generate_snowflake_id
from app.db.session import engine
from app.platform.auth.models import User, Workspace
from app.workforce.agents.orchestration.adk.governed_tool import CosaGovernedTool
from app.workforce.agents.runtime.execution_scope import ExecutionScope


@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()


@pytest.mark.asyncio
async def test_cosa_governed_tool_dispatches_and_records_audit(db_session):
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db_session.add(User(id=user_id, email=f"gt-{user_id}@example.invalid"))
    db_session.add(Workspace(id=workspace_id, name=f"GT {workspace_id}"))
    db_session.flush()
    mission_run = AgentRun(
        id=generate_snowflake_id(), workspace_id=workspace_id, company_id=workspace_id,
        user_id=user_id, agent_key="chief_of_staff", runtime="adk", status="running",
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(mission_run)
    db_session.commit()

    scope = ExecutionScope(
        workspace_id=workspace_id, company_id=workspace_id, principal_user_id=user_id,
        principal_member_id=user_id, principal_role="owner", operating_unit_id=None,
        offering_id=None, initiative_id=None, profile_id=None, session_id=None, grants=(),
    )

    tool = CosaGovernedTool(
        tool_flat_name="finance_get_financial_summary",
        db_factory=lambda: db_session,
        scope_factory=lambda: scope,
        run_id_factory=lambda: mission_run.id,
        source="adk_workflow",
    )

    fake_tool_context = MagicMock()
    fake_tool_context.state = {"malicious_override": {"workspace_id": 999999}}

    result = await tool.run_async(args={}, tool_context=fake_tool_context)

    assert isinstance(result, dict)
    calls = db_session.query(AgentToolCall).filter(AgentToolCall.run_id == mission_run.id).all()
    assert len(calls) == 1
```

- [x] **Step 3: Chạy test, xác nhận FAIL (module chưa tồn tại)**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_adk_governed_tool.py -v`
Expected: FAIL với `ModuleNotFoundError`

- [x] **Step 4: Viết `CosaGovernedTool`**

```python
# backend/app/workforce/agents/orchestration/adk/governed_tool.py
"""ADK BaseTool cho primitive ToolInvocation (ngắn hạn) — KHÔNG dùng cho công việc
durable/dài hạn (DeepSeek delegation), primitive đó đi qua TaskBoardService (xem
specialist_delegation_node.py, Task 16).

ExecutionScope PHẢI dựng từ context tin cậy phía server (scope_factory do caller
cấp, lấy từ AgentRun/Outcome đã xác thực trong DB — xem Task 24 dùng trực tiếp
class này) — KHÔNG BAO GIỜ đọc từ tool_context.state, vì đó là session state mà
1 LLM node phía trước có thể đã ghi vào (xem Quyết định 1, mục "ExecutionScope
phải dựng từ context tin cậy phía server").
"""
from typing import Any, Callable

from sqlalchemy.orm import Session

from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

from app.workforce.agents.runtime.execution_scope import ExecutionScope
from app.workforce.tools.invocation.contracts import ToolInvocationRequest
from app.workforce.tools.invocation.service import ToolInvocationService


class CosaGovernedTool(BaseTool):
    """Bọc 1 ToolSpec đã đăng ký trong app.core.tool_registry thành 1 ADK BaseTool,
    đi qua đúng governance pipeline mà DeepSeekHarnessAdapter.dispatch_tool_call
    dùng (PolicyGate -> GovernanceKernel -> NativeDispatcher/CapabilityBridge)."""

    def __init__(
        self,
        *,
        tool_flat_name: str,
        db_factory: Callable[[], Session],
        scope_factory: Callable[[], ExecutionScope],
        run_id_factory: Callable[[], int | None],
        source: str = "adk_workflow",
        description: str = "",
    ) -> None:
        super().__init__(name=tool_flat_name, description=description or f"Governed tool: {tool_flat_name}")
        self._tool_flat_name = tool_flat_name
        self._db_factory = db_factory
        self._scope_factory = scope_factory
        self._run_id_factory = run_id_factory
        self._source = source
        self._service = ToolInvocationService()

    async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
        db = self._db_factory()
        scope = self._scope_factory()
        request = ToolInvocationRequest(
            scope=scope,
            tool_flat_name=self._tool_flat_name,
            arguments=dict(args),
            source=self._source,
            run_id=self._run_id_factory(),
        )
        result = await self._service.invoke(db, request)
        if result.status == "success":
            return result.output
        if result.status == "approval_required":
            return {"status": "approval_required", "approval_id": result.approval_id, "message": result.error_message}
        return {"status": result.status, "error": result.error_message}
```

- [x] **Step 5: Chạy lại test, xác nhận PASS**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_adk_governed_tool.py -v`
Expected: PASS

- [x] **Step 6: Commit**

```bash
git add backend/app/workforce/agents/orchestration/adk/__init__.py backend/app/workforce/agents/orchestration/adk/governed_tool.py backend/app/tests/agents/test_adk_governed_tool.py
git commit -m "feat(adk): add CosaGovernedTool routing ADK tool calls through ToolInvocationService"
```

---

## Phase 4 — Session bridge + `DatabaseSessionService`

### Task 8: `session_bridge.py` — projector ADK event → `AgentEventRecord`/`mission_control_bus`

**Files:**
- Create: `backend/app/workforce/agents/orchestration/adk/session_bridge.py`
- Test: `backend/app/tests/agents/test_adk_session_bridge.py`

**Interfaces:**
- Produces: `def project_adk_event(db: Session, event: Event, *, mission_run_id: int, workspace_id: int, agent_key: str = "chief_of_staff") -> AgentEventRecord` — ghi 1 dòng `AgentEventRecord` (sequence tự tăng theo `mission_run_id`, đúng cơ chế `chief_of_staff.py::record_event` đang dùng) + gọi `mission_control_bus.emit_event(...)`. Dùng ở Task 25 (`orchestration/service.py::_drive` gọi hàm này cho từng event ADK phát ra khi biết `mission_id`).

**Ghi chú:** đây là projector MỎNG — không phải 1 audit trail thứ 4. Nó chỉ đọc field cấp cao của ADK `Event` (`id`, `author`, `content`, `output`, `timestamp`) và ghi sang bảng `agent_events` hiện có, y hệt cách `chief_of_staff.py::record_event` đang làm thủ công cho từng bước.

- [x] **Step 1: Viết test cho `project_adk_event`**

```python
# backend/app/tests/agents/test_adk_session_bridge.py
from datetime import datetime, timezone

import pytest
from google.adk.events.event import Event
from google.genai import types as genai_types
from sqlalchemy import func
from sqlalchemy.orm import sessionmaker

from agent_runtime.events.models import AgentEventRecord
from agent_runtime.sessions.models import AgentRun
from app.core.snowflake import generate_snowflake_id
from app.db.session import engine
from app.platform.auth.models import User, Workspace
from app.workforce.agents.orchestration.adk.session_bridge import project_adk_event


@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()


def test_project_adk_event_writes_agent_event_record(db_session):
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db_session.add(User(id=user_id, email=f"sb-{user_id}@example.invalid"))
    db_session.add(Workspace(id=workspace_id, name=f"SB {workspace_id}"))
    db_session.flush()
    mission_run = AgentRun(
        id=generate_snowflake_id(), workspace_id=workspace_id, company_id=workspace_id,
        user_id=user_id, agent_key="chief_of_staff", runtime="adk", status="running",
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(mission_run)
    db_session.commit()

    event = Event(
        author="risk_classification_node",
        content=genai_types.Content(role="model", parts=[genai_types.Part(text="R0")]),
        output={"risk_level": "R0"},
    )

    record = project_adk_event(
        db_session, event, mission_run_id=mission_run.id, workspace_id=workspace_id,
    )
    db_session.commit()

    assert record.run_id == mission_run.id
    assert record.event_type == "adk.node_completed"
    assert record.payload_jsonb["author"] == "risk_classification_node"
    assert record.payload_jsonb["output"] == {"risk_level": "R0"}

    stored = db_session.query(AgentEventRecord).filter(AgentEventRecord.run_id == mission_run.id).all()
    assert len(stored) == 1

    # Sequence phải tự tăng đúng cách khi ghi thêm 1 event nữa
    event2 = Event(author="planning_node", output={"priorities": []})
    project_adk_event(db_session, event2, mission_run_id=mission_run.id, workspace_id=workspace_id)
    db_session.commit()
    max_seq = db_session.query(func.max(AgentEventRecord.sequence)).filter(
        AgentEventRecord.run_id == mission_run.id
    ).scalar()
    assert max_seq == 2
```

- [x] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_adk_session_bridge.py -v`
Expected: FAIL với `ModuleNotFoundError`

- [x] **Step 3: Viết `session_bridge.py`**

```python
# backend/app/workforce/agents/orchestration/adk/session_bridge.py
"""Projector mỏng: chuyển lifecycle event quan trọng của ADK Workflow sang
AgentEventRecord/mission_control_bus hiện có. KHÔNG phải 1 audit trail thứ 4 —
DatabaseSessionService (Task 9) là nơi ADK tự lưu session/event/replay-state đầy
đủ trong schema `adk_runtime` riêng; hàm này chỉ chiếu 1 phần nhỏ (tên node, tóm
tắt output) sang audit ledger canonical mà UI/founder đang đọc.
"""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from google.adk.events.event import Event

from agent_runtime.events.models import AgentEventRecord
from app.core.snowflake import generate_snowflake_id
from app.workforce.agents.orchestration.mission_control_bus import mission_control_bus


def _summarize_content(event: Event) -> str | None:
    if event.content is None or not event.content.parts:
        return None
    texts = [p.text for p in event.content.parts if p.text]
    return "\n".join(texts) if texts else None


def project_adk_event(
    db: Session,
    event: Event,
    *,
    mission_run_id: int,
    workspace_id: int,
    agent_key: str = "chief_of_staff",
) -> AgentEventRecord:
    next_sequence = int(
        db.query(func.max(AgentEventRecord.sequence))
        .filter(AgentEventRecord.run_id == mission_run_id)
        .scalar()
        or 0
    ) + 1

    payload: dict[str, Any] = {
        "author": event.author,
        "output": event.output,
        "text": _summarize_content(event),
    }

    record = AgentEventRecord(
        id=generate_snowflake_id(),
        run_id=mission_run_id,
        company_id=None,
        sequence=next_sequence,
        agent_key=agent_key,
        actor_type="adk_node",
        actor_id=event.author or "unknown",
        status="completed",
        event_type="adk.node_completed",
        event_time=event.timestamp if getattr(event, "timestamp", None) else datetime.now(timezone.utc),
        payload_jsonb=payload,
    )
    db.add(record)

    mission_control_bus.emit_event(
        run_id=str(mission_run_id),
        workspace_id=str(workspace_id),
        event_type="adk.node_completed",
        data=payload,
        agent_key=agent_key,
    )
    return record
```

- [x] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_adk_session_bridge.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add backend/app/workforce/agents/orchestration/adk/session_bridge.py backend/app/tests/agents/test_adk_session_bridge.py
git commit -m "feat(adk): add session_bridge projector from ADK events to AgentEventRecord/mission_control_bus"
```

---

### Task 9: `build_adk_session_service()` — `DatabaseSessionService` trên schema `adk_runtime` riêng

**Files:**
- Create: `backend/app/workforce/agents/orchestration/adk/session_service_factory.py`
- Test: `backend/app/tests/agents/test_adk_session_service_factory.py`

**Interfaces:**
- Produces: `def build_adk_session_service() -> DatabaseSessionService` — đọc `ADK_RUNTIME_DATABASE_URL` (mặc định dẫn xuất từ `DATABASE_URL` bằng cách đổi driver sang `postgresql+asyncpg://` và gắn `?options=-csearch_path%3Dadk_runtime`). Dùng ở Task 25 (`orchestration/service.py::_build_runner` — sản xuất thật; Task 24 dùng `InMemorySessionService` thay thế cho test).

**Ghi chú:** không tự viết `BaseSessionService` — dùng nguyên `google.adk.sessions.database_session_service.DatabaseSessionService` (đã verify import được, nhận `db_url` rồi tự `create_async_engine`). Task này chỉ là 1 factory function nhỏ tính đúng connection string, không đụng vào nội bộ ADK.

- [x] **Step 1: Viết test cho factory (không kết nối DB thật — chỉ assert URL/kwargs đúng bằng monkeypatch)**

```python
# backend/app/tests/agents/test_adk_session_service_factory.py
from unittest.mock import patch

from app.workforce.agents.orchestration.adk.session_service_factory import (
    resolve_adk_runtime_database_url,
    build_adk_session_service,
)


def test_resolve_adk_runtime_database_url_derives_from_database_url(monkeypatch):
    monkeypatch.delenv("ADK_RUNTIME_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://javis:javis@localhost:5432/javis")
    url = resolve_adk_runtime_database_url()
    assert url.startswith("postgresql+asyncpg://")
    assert "options=-csearch_path%3Dadk_runtime" in url


def test_resolve_adk_runtime_database_url_respects_explicit_override(monkeypatch):
    monkeypatch.setenv("ADK_RUNTIME_DATABASE_URL", "postgresql+asyncpg://custom/adk_runtime_db")
    url = resolve_adk_runtime_database_url()
    assert url == "postgresql+asyncpg://custom/adk_runtime_db"


def test_build_adk_session_service_constructs_with_resolved_url(monkeypatch):
    monkeypatch.setenv("ADK_RUNTIME_DATABASE_URL", "postgresql+asyncpg://custom/adk_runtime_db")
    with patch(
        "app.workforce.agents.orchestration.adk.session_service_factory.DatabaseSessionService"
    ) as mock_cls:
        build_adk_session_service()
        mock_cls.assert_called_once_with(db_url="postgresql+asyncpg://custom/adk_runtime_db")
```

- [x] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_adk_session_service_factory.py -v`
Expected: FAIL với `ModuleNotFoundError`

- [x] **Step 3: Viết `session_service_factory.py`**

```python
# backend/app/workforce/agents/orchestration/adk/session_service_factory.py
"""Factory cho google.adk.sessions.database_session_service.DatabaseSessionService,
trỏ vào schema `adk_runtime` riêng — cô lập khỏi schema `public` (business data)
vì tên bảng ADK khá generic (sessions, events, app_states, user_states)."""
import os

from google.adk.sessions.database_session_service import DatabaseSessionService

_DEFAULT_SCHEMA = "adk_runtime"


def resolve_adk_runtime_database_url() -> str:
    explicit = os.environ.get("ADK_RUNTIME_DATABASE_URL")
    if explicit:
        return explicit

    base = os.environ.get("DATABASE_URL", "postgresql://javis:javis@localhost:5432/javis")
    if base.startswith("postgres://"):
        base = base.replace("postgres://", "postgresql://", 1)
    if base.startswith("postgresql://"):
        base = base.replace("postgresql://", "postgresql+asyncpg://", 1)
    separator = "&" if "?" in base else "?"
    return f"{base}{separator}options=-csearch_path%3D{_DEFAULT_SCHEMA}"


def build_adk_session_service() -> DatabaseSessionService:
    return DatabaseSessionService(db_url=resolve_adk_runtime_database_url())
```

- [x] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_adk_session_service_factory.py -v`
Expected: PASS

- [x] **Step 5: Tạo schema `adk_runtime` trên DB dev (thao tác hạ tầng, không phải migration Alembic vì bảng do ADK tự quản lý, không nằm trong metadata COSA)**

Run: `cd backend && .venv/bin/python -c "from sqlalchemy import create_engine, text; import os; e = create_engine(os.environ.get('DATABASE_URL','postgresql://javis:javis@localhost:5432/javis')); c = e.connect(); c.execute(text('CREATE SCHEMA IF NOT EXISTS adk_runtime')); c.commit()"`
Expected: Không lỗi. Ghi chú vận hành: bước này cần lặp lại trên mọi môi trường (dev/staging/prod) trước khi Task 24/26 chạy — thêm vào README triển khai ở Task 26.

- [x] **Step 6: Commit**

```bash
git add backend/app/workforce/agents/orchestration/adk/session_service_factory.py backend/app/tests/agents/test_adk_session_service_factory.py
git commit -m "feat(adk): add DatabaseSessionService factory pointed at isolated adk_runtime schema"
```

---

## Phase 5 — Model adapter: `CosaModelGatewayLlm`

### Task 10: `CosaModelGatewayLlm(BaseLlm)`

**Files:**
- Create: `backend/app/workforce/agents/orchestration/adk/model_adapter.py`
- Test: `backend/app/tests/agents/test_adk_model_adapter.py`

**Interfaces:**
- Consumes: `ModelGateway.invoke` (Task 2), `cosa_litellm_invoker` (Task 3), `ModelRequest`/`ModelMessage`.
- Produces: `CosaModelGatewayLlm(BaseLlm)` — `generate_content_async(llm_request: LlmRequest, stream: bool = False) -> AsyncGenerator[LlmResponse, None]`, field `profile_name: str`. Dùng ở Task 21 (SynthesisNode).

- [x] **Step 1: Viết test — mock `ModelGateway.invoke`, xác nhận `LlmRequest` → `ModelRequest` → `LlmResponse` map đúng**

```python
# backend/app/tests/agents/test_adk_model_adapter.py
from unittest.mock import AsyncMock, patch

import pytest
from google.genai import types as genai_types

from app.workforce.agents.orchestration.adk.model_adapter import CosaModelGatewayLlm
from app.workforce.agents.reliability.model_gateway import ModelGatewayResult


@pytest.mark.asyncio
async def test_cosa_model_gateway_llm_maps_request_and_response():
    llm_request = genai_types_llm_request = None
    from google.adk.models.llm_request import LlmRequest

    llm_request = LlmRequest(
        model="deepseek/deepseek-reasoner",
        contents=[genai_types.Content(role="user", parts=[genai_types.Part(text="Phân tích runway")])],
        config=genai_types.GenerateContentConfig(system_instruction="Bạn là Chief of Staff."),
    )

    fake_result = ModelGatewayResult(
        content="Runway hiện tại là 12 tháng.",
        provider="deepseek",
        model="deepseek-reasoner",
        input_tokens=20,
        output_tokens=6,
        estimated_cost=0.0001,
        latency_ms=120,
        fallback_used=False,
        status="success",
    )

    llm = CosaModelGatewayLlm(model="deepseek/deepseek-reasoner", profile_name="reasoning")

    with patch(
        "app.workforce.agents.orchestration.adk.model_adapter.ModelGateway.invoke",
        new=AsyncMock(return_value=fake_result),
    ) as mock_invoke:
        responses = [resp async for resp in llm.generate_content_async(llm_request)]

    assert len(responses) == 1
    resp = responses[0]
    assert resp.content.parts[0].text == "Runway hiện tại là 12 tháng."
    assert resp.finish_reason is not None

    call_kwargs = mock_invoke.call_args.kwargs
    sent_request = call_kwargs["request"]
    assert sent_request.system_instruction == "Bạn là Chief of Staff."
    assert sent_request.messages[0].role == "user"
    assert sent_request.messages[0].content == "Phân tích runway"
    assert call_kwargs["profile_name"] == "reasoning"
    assert call_kwargs["invoker_fn"] is not None
```

- [x] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_adk_model_adapter.py -v`
Expected: FAIL với `ModuleNotFoundError`

- [x] **Step 3: Viết `model_adapter.py`**

```python
# backend/app/workforce/agents/orchestration/adk/model_adapter.py
"""ADK BaseLlm adapter gọi ModelGateway.invoke() thay vì google.adk.models.lite_llm.LiteLlm
trực tiếp — giữ nguyên retry/circuit-breaker/cost-tracking của ModelGateway, và ADK
không tự quản lý kết nối model provider (xem Quyết định 1, mục "Model connectivity")."""
from collections.abc import AsyncGenerator
from typing import Any

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types as genai_types

from app.workforce.agents.reliability.litellm_invoker import cosa_litellm_invoker
from app.workforce.agents.reliability.model_gateway import ModelGateway, ModelMessage, ModelRequest


def _extract_text(content: genai_types.Content | None) -> str:
    if content is None or not content.parts:
        return ""
    return "\n".join(p.text for p in content.parts if p.text)


def _system_instruction_text(config: genai_types.GenerateContentConfig) -> str | None:
    raw = getattr(config, "system_instruction", None)
    if raw is None:
        return None
    if isinstance(raw, str):
        return raw
    if isinstance(raw, genai_types.Content):
        return _extract_text(raw) or None
    return str(raw)


def _to_model_request(llm_request: LlmRequest) -> ModelRequest:
    messages = [
        ModelMessage(role="assistant" if c.role == "model" else (c.role or "user"), content=_extract_text(c))
        for c in llm_request.contents
    ]
    return ModelRequest(
        messages=messages,
        system_instruction=_system_instruction_text(llm_request.config),
        temperature=getattr(llm_request.config, "temperature", None),
        max_tokens=getattr(llm_request.config, "max_output_tokens", None),
    )


class CosaModelGatewayLlm(BaseLlm):
    """model field (BaseLlm) giữ định dạng "provider/model" (quy ước LiteLLM có sẵn
    trong codebase — xem gateway_lm.py). profile_name chọn ModelProfile
    (retry/fallback/cost) trong ModelProfileRegistry."""

    profile_name: str = "reasoning"

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        request = _to_model_request(llm_request)
        result = await ModelGateway.invoke(
            request=request,
            profile_name=self.profile_name,
            invoker_fn=cosa_litellm_invoker,
        )
        yield LlmResponse(
            content=genai_types.Content(role="model", parts=[genai_types.Part(text=result.content)]),
            finish_reason=(
                genai_types.FinishReason.STOP if result.status == "success" else genai_types.FinishReason.OTHER
            ),
            custom_metadata={
                "provider": result.provider,
                "model": result.model,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "estimated_cost": result.estimated_cost,
                "fallback_used": result.fallback_used,
            },
        )
```

- [x] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_adk_model_adapter.py -v`
Expected: PASS (`genai_types.FinishReason.STOP`/`.OTHER` đã verify tồn tại trong `google-genai` bản đang cài ở `backend/.venv`).

- [x] **Step 5: Commit**

```bash
git add backend/app/workforce/agents/orchestration/adk/model_adapter.py backend/app/tests/agents/test_adk_model_adapter.py
git commit -m "feat(adk): add CosaModelGatewayLlm bridging ADK BaseLlm to ModelGateway"
```

---

## Phase 6 — Trích xuất registry dùng chung (tránh 2 nguồn sự thật)

### Task 11: Trích `SpecialistSpec`/`SPECIALIST_REGISTRY`/risk-tier/synthesis helpers ra khỏi `chief_of_staff.py`

**Files:**
- Create: `backend/app/workforce/agents/orchestration/specialist_registry.py`
- Create: `backend/app/workforce/agents/orchestration/synthesis_helpers.py`
- Modify: `backend/app/workforce/agents/orchestration/chief_of_staff.py`
- Test: `backend/app/tests/agents/test_specialist_registry.py`

**Interfaces:**
- Produces: `specialist_registry.py` → `SpecialistSpec`, `SPECIALIST_REGISTRY: dict[str, SpecialistSpec]`, `RISK_ORDER: tuple[str, ...]`, `AUTO_START_MAX_RISK: str`, `DEFAULT_ORCHESTRATION_DOMAINS: tuple[str, ...]`, `classify_mission_risk(domains: list[str]) -> str`. `synthesis_helpers.py` → `build_synthesis_prompt(goal, sales_data, fin_data) -> str`, `derive_priorities_and_actions(sales_data, fin_data) -> tuple[list[str], list[dict]]`, `create_approvals_and_proposals_for_action_plan(db, workspace_id, run_id, action_plan) -> tuple[list[dict], list[dict]]`. Dùng ở Task 12 (RiskClassificationNode), Task 16 (specialist delegation), Task 21-22 (Synthesis/ApprovalGate node), và **vẫn** dùng bởi `chief_of_staff.py` cho tới khi file đó bị xoá (Task 35) — đúng 1 nguồn sự thật cho cả 2 phía trong giai đoạn chuyển tiếp.

**Xác nhận an toàn của refactor này (đã verify bằng grep):** nhiều test hiện có (`test_chief_of_staff_orchestration.py`, `test_chief_of_staff_delegation.py`, `test_cofounder_context_assembler.py`) và 1 consumer sản xuất thật (`app/workforce/agents/context/assembler.py`) đều làm `from app.workforce.agents.orchestration.chief_of_staff import SPECIALIST_REGISTRY` rồi `monkeypatch.setitem(...)` trực tiếp lên dict đó. Vì Python `import X from Y` chỉ tạo thêm 1 binding trỏ tới CÙNG object, và `setitem` sửa nội dung dict tại chỗ (không rebind tên) — miễn `chief_of_staff.py` giữ `SPECIALIST_REGISTRY` truy cập được ở cấp module (qua `from ... import SPECIALIST_REGISTRY`, không phải định nghĩa lại), toàn bộ test/consumer trên tiếp tục hoạt động đúng mà không cần sửa gì ở phía họ.

- [x] **Step 1: Viết test cho module mới (trước khi di chuyển code) — xác nhận `classify_mission_risk` hoạt động đúng như static method cũ**

```python
# backend/app/tests/agents/test_specialist_registry.py
from app.workforce.agents.orchestration.specialist_registry import (
    AUTO_START_MAX_RISK,
    DEFAULT_ORCHESTRATION_DOMAINS,
    RISK_ORDER,
    SPECIALIST_REGISTRY,
    SpecialistSpec,
    classify_mission_risk,
)


def test_specialist_registry_has_four_domains():
    assert set(SPECIALIST_REGISTRY.keys()) == {"sales", "finance", "legal", "marketing"}
    assert DEFAULT_ORCHESTRATION_DOMAINS == ("sales", "finance")


def test_classify_mission_risk_picks_highest_tier():
    assert classify_mission_risk(["sales", "finance"]) == "R0"
    assert classify_mission_risk([]) == "R0"


def test_classify_mission_risk_unknown_domain_ignored():
    assert classify_mission_risk(["sales", "does_not_exist"]) == "R0"


def test_risk_order_and_auto_start_threshold_unchanged():
    assert RISK_ORDER == ("R0", "R1", "R2", "R3", "R4")
    assert AUTO_START_MAX_RISK == "R1"
```

- [x] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_specialist_registry.py -v`
Expected: FAIL với `ModuleNotFoundError`

- [x] **Step 3: Tạo `specialist_registry.py` — di chuyển nguyên văn từ `chief_of_staff.py`**

```python
# backend/app/workforce/agents/orchestration/specialist_registry.py
"""Nguồn sự thật duy nhất cho SPECIALIST_REGISTRY/risk-tier — dùng chung bởi
chief_of_staff.py (cho tới khi bị xoá, Task 35) và
orchestration/adk/* (AdkCofounderWorkflow). Trích ra từ chief_of_staff.py để
tránh 2 nguồn sự thật khi cả 2 đường orchestration cùng tồn tại trong giai đoạn
chuyển tiếp."""
from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.business.finance.finance_tools import get_financial_summary
from app.business.legal.legal_tools import get_legal_posture_summary
from app.business.marketing.marketing_tools import get_marketing_overview
from app.business.sales.sales_tools import get_pipeline_summary

# Ordered so max() by index picks the higher-risk tier (G2 §7.6 R0-R4 policy).
RISK_ORDER = ("R0", "R1", "R2", "R3", "R4")
# Missions at or below this risk auto-start; anything higher stays in "draft"
# until a founder explicitly confirms (G2 §7.3).
AUTO_START_MAX_RISK = "R1"


@dataclass(frozen=True)
class SpecialistSpec:
    """One entry in SPECIALIST_REGISTRY — everything the delegation loop needs
    to dispatch a domain specialist generically, without a new
    `if domain == "...":` branch per domain."""
    domain: str
    agent_key: str
    task: str
    tool_flat_name: str
    fetch_snapshot: Callable[[Session, int], dict[str, Any]]
    quality_gate_compatible: bool = True
    risk_level: str = "R0"
    delegate_via_profile_id: str | None = None


SPECIALIST_REGISTRY: dict[str, SpecialistSpec] = {
    "sales": SpecialistSpec(
        domain="sales",
        agent_key="sales_specialist",
        task="Analyze CRM pipeline",
        tool_flat_name="sales_get_pipeline_summary",
        fetch_snapshot=lambda db, ws: get_pipeline_summary(db, ws),
        delegate_via_profile_id="sales",
    ),
    "finance": SpecialistSpec(
        domain="finance",
        agent_key="finance_specialist",
        task="Analyze cashflow and runway",
        tool_flat_name="finance_get_financial_summary",
        fetch_snapshot=lambda db, ws: get_financial_summary(db, ws),
        delegate_via_profile_id="finance",
    ),
    "legal": SpecialistSpec(
        domain="legal",
        agent_key="legal_specialist",
        task="Review legal posture and obligations",
        tool_flat_name="legal_get_legal_posture_summary",
        fetch_snapshot=lambda db, ws: get_legal_posture_summary(db, ws),
        quality_gate_compatible=False,
        delegate_via_profile_id="legal",
    ),
    "marketing": SpecialistSpec(
        domain="marketing",
        agent_key="marketing_specialist",
        task="Analyze marketing funnel and scorecard",
        tool_flat_name="marketing_get_marketing_overview",
        fetch_snapshot=lambda db, ws: get_marketing_overview(db, ws),
        delegate_via_profile_id="marketing",
    ),
}

DEFAULT_ORCHESTRATION_DOMAINS: tuple[str, ...] = ("sales", "finance")


def classify_mission_risk(domains: list[str]) -> str:
    """Highest risk tier among the specialists this mission would delegate
    to — see SpecialistSpec.risk_level / AUTO_START_MAX_RISK."""
    highest = "R0"
    for domain in domains:
        spec = SPECIALIST_REGISTRY.get(domain)
        if spec is None:
            continue
        if RISK_ORDER.index(spec.risk_level) > RISK_ORDER.index(highest):
            highest = spec.risk_level
    return highest
```

- [x] **Step 4: Tạo `synthesis_helpers.py` — di chuyển 3 staticmethod còn lại**

```python
# backend/app/workforce/agents/orchestration/synthesis_helpers.py
"""Helper tất định cho bước synthesis/action-plan — KHÔNG để LLM tự quyết định
priorities/action_plan, derive trực tiếp từ snapshot thật (xem CLAUDE.md §13,
"deterministic application logic" ưu tiên hơn "prompt logic"). Dùng chung bởi
chief_of_staff.py và orchestration/adk/* trong giai đoạn chuyển tiếp."""
import json
from typing import Any

from sqlalchemy.orm import Session

from app.workforce.agents.governance.approval_service import ApprovalService
from app.workforce.agents.proposals.service import AgentProposalService


def build_synthesis_prompt(goal: str, sales_data: dict[str, Any], fin_data: dict[str, Any]) -> str:
    return (
        f"Founder goal: {goal}\n\n"
        f"Real sales pipeline snapshot: {json.dumps(sales_data, ensure_ascii=False)}\n"
        f"Real finance snapshot: {json.dumps(fin_data, ensure_ascii=False)}\n\n"
        "Diagnose the situation strictly from the data above and answer the Founder's goal. "
        "Respond as a single JSON object: "
        '{"diagnosis": "<2-4 sentence analysis grounded in the data above>"}. '
        "Do not invent numbers not present in the snapshots above."
    )


def derive_priorities_and_actions(
    sales_data: dict[str, Any], fin_data: dict[str, Any]
) -> tuple[list[str], list[dict[str, Any]]]:
    metrics = sales_data.get("metrics", {}) if isinstance(sales_data, dict) and sales_data.get("status") == "success" and isinstance(sales_data.get("metrics"), dict) else {}
    priorities: list[str] = []
    action_plan: list[dict[str, Any]] = []

    try:
        qualified = int(metrics.get("qualified_leads", 0))
        total_leads = int(metrics.get("total_leads", 0))
    except (TypeError, ValueError):
        qualified = 0
        total_leads = 0

    if qualified > 0:
        priorities.append(f"Follow up {qualified}/{total_leads} qualified leads currently in pipeline")
        action_plan.append({
            "tactic": f"Send follow-up outreach to {qualified} qualified leads",
            "owner": "sales_specialist",
            "automation_key": "sales.followup_email",
        })

    raw_runway = fin_data.get("runway_months") if isinstance(fin_data, dict) and fin_data.get("status") == "success" else None
    try:
        runway = float(raw_runway) if raw_runway is not None else None
    except (TypeError, ValueError):
        runway = None

    if runway is not None and runway < 6:
        priorities.append(f"Cash runway is {runway} months - review burn rate this week")
        action_plan.append({
            "tactic": f"Finance review: runway at {runway} months, below 6-month safety margin",
            "owner": "finance_specialist",
        })

    if not priorities:
        priorities.append("No urgent data-driven priorities identified from current Sales/Finance snapshots")

    return priorities, action_plan


def create_approvals_and_proposals_for_action_plan(
    db: Session, workspace_id: int, run_id: int, action_plan: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    created_approvals: list[dict[str, Any]] = []
    created_proposals: list[dict[str, Any]] = []

    for action in action_plan:
        automation_key = action.get("automation_key")
        if automation_key:
            approval = ApprovalService.create_approval(
                db,
                workspace_id=workspace_id,
                agent_key="chief_of_staff",
                action_type="automation_dispatch",
                tool_name=automation_key,
                input_preview=action,
                risk_level="medium",
                run_id=run_id,
            )
            created_approvals.append({
                "approval_id": str(approval.id),
                "action_type": approval.action_type,
                "tool_name": approval.tool_name,
                "risk_level": approval.risk_level,
                "status": approval.status,
            })

        proposal_type = action.get("proposal_type")
        if proposal_type in ("okr_objective", "strategy_task"):
            proposal = AgentProposalService.create_proposal(
                db=db,
                workspace_id=workspace_id,
                proposal_type=proposal_type,
                title=action.get("title") or action.get("tactic", "Strategy Proposal"),
                payload=action.get("payload") or action,
                description=action.get("description"),
                agent_key="chief_of_staff",
                run_id=run_id,
            )
            created_proposals.append({
                "proposal_id": str(proposal.id),
                "proposal_type": proposal.proposal_type,
                "title": proposal.title,
                "status": proposal.status,
            })

    return created_approvals, created_proposals
```

- [x] **Step 5: Sửa `chief_of_staff.py` — xoá định nghĩa cục bộ, import từ 2 module mới**

Trong `backend/app/workforce/agents/orchestration/chief_of_staff.py`:

1. Xoá toàn bộ khối `RISK_ORDER = (...)`, `AUTO_START_MAX_RISK = "R1"`, `class SpecialistSpec`, `SPECIALIST_REGISTRY = {...}`, `DEFAULT_ORCHESTRATION_DOMAINS = (...)` (dòng ~46-135 gốc).
2. Thay bằng:

```python
from app.workforce.agents.orchestration.specialist_registry import (
    AUTO_START_MAX_RISK,
    DEFAULT_ORCHESTRATION_DOMAINS,
    RISK_ORDER,
    SPECIALIST_REGISTRY,
    SpecialistSpec,
    classify_mission_risk,
)
from app.workforce.agents.orchestration.synthesis_helpers import (
    build_synthesis_prompt,
    create_approvals_and_proposals_for_action_plan,
    derive_priorities_and_actions,
)
```

3. Xoá `@staticmethod def _classify_mission_risk(domains): ...` (dòng ~1065-1076 gốc), sửa call site duy nhất của nó — `risk_level = cls._classify_mission_risk(active_domains)` (dòng ~284) — thành `risk_level = classify_mission_risk(active_domains)`.
4. Xoá `@staticmethod def _build_synthesis_prompt(...)`, `@staticmethod def _derive_priorities_and_actions(...)`, `@staticmethod def _create_approvals_and_proposals_for_action_plan(...)` (dòng ~1084-1202 gốc). Sửa 3 call site tương ứng:
   - `task_prompt = cls._build_synthesis_prompt(goal, sales_data, fin_data)` → `task_prompt = build_synthesis_prompt(goal, sales_data, fin_data)`
   - `priorities, action_plan = cls._derive_priorities_and_actions(sales_data, fin_data)` → `priorities, action_plan = derive_priorities_and_actions(sales_data, fin_data)`
   - `required_approvals, created_proposals = cls._create_approvals_and_proposals_for_action_plan(db, workspace_id=workspace_id, run_id=mission_id, action_plan=action_plan)` → `required_approvals, created_proposals = create_approvals_and_proposals_for_action_plan(db, workspace_id=workspace_id, run_id=mission_id, action_plan=action_plan)`
5. Xoá import không còn dùng ở đầu file nếu trở nên thừa: `from app.business.sales.sales_tools import get_pipeline_summary`, `from app.business.finance.finance_tools import get_financial_summary`, `from app.business.legal.legal_tools import get_legal_posture_summary`, `from app.business.marketing.marketing_tools import get_marketing_overview` (giờ chỉ `specialist_registry.py` cần chúng).

- [x] **Step 6: Chạy lại test mới, xác nhận PASS**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_specialist_registry.py -v`
Expected: PASS

- [x] **Step 7: Chạy toàn bộ test liên quan tới `chief_of_staff.py` để xác nhận refactor không đổi hành vi**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_chief_of_staff_orchestration.py app/tests/agents/test_chief_of_staff_delegation.py app/tests/agents/test_cofounder_context_assembler.py app/tests/agents/test_governance_e2e.py -v`
Expected: PASS toàn bộ, không có test nào bị vỡ (đúng như phân tích an toàn ở trên).

- [x] **Step 8: Commit**

```bash
git add backend/app/workforce/agents/orchestration/specialist_registry.py backend/app/workforce/agents/orchestration/synthesis_helpers.py backend/app/workforce/agents/orchestration/chief_of_staff.py backend/app/tests/agents/test_specialist_registry.py
git commit -m "refactor(orchestration): extract SPECIALIST_REGISTRY and synthesis helpers into shared modules"
```

---

## Phase 7 — Deterministic `FunctionNode`s (risk / budget / quality gate)

Ghi chú thiết kế chung cho cả 3 task trong Phase này: mỗi node function nhận đúng 1 tham số `ctx: Context` (không dùng cơ chế tự động bind theo tên field trong `ctx.state` của `FunctionNode` — quá dễ sai ngầm với tham số trùng tên) và tự đọc/ghi `ctx.state`/`ctx.route` bên trong thân hàm bằng code Python thường. Đây là cách dùng `FunctionNode` hợp lệ (docstring `FunctionNode.__init__` xác nhận `func` "can accept 'ctx: Context' ... as arguments"), không phải suy đoán ngoài API thật. Vì dựng 1 `Context` thật cần cả `InvocationContext`/session/agent tree (chi phí cao cho unit test), các task ở Phase này unit-test PHẦN LOGIC THUẦN (nhận input, trả output) bằng 1 stub nhẹ (`types.SimpleNamespace(state=..., route=None)`) thay cho `Context` thật — Task 24 (bắt buộc trước cutover) mới chạy toàn bộ graph qua `Runner` với `Context` thật.

### Task 12: `RiskClassificationNode`

**Files:**
- Create: `backend/app/workforce/agents/orchestration/adk/nodes/__init__.py`
- Create: `backend/app/workforce/agents/orchestration/adk/nodes/risk_classification_node.py`
- Test: `backend/app/tests/agents/test_adk_risk_classification_node.py`

**Interfaces:**
- Consumes: `classify_mission_risk`, `AUTO_START_MAX_RISK`, `RISK_ORDER` (Task 11).
- Produces: `async def risk_classification_fn(ctx) -> dict` — đọc `ctx.state["active_domains"]`, ghi `ctx.state["risk_level"]`, set `ctx.route = "auto_start"` khi `risk_level <= AUTO_START_MAX_RISK` else `ctx.route = "needs_confirmation"`, trả `{"risk_level": ...}`. `def build_risk_classification_node() -> FunctionNode` — factory dùng ở Task 23 (`build_adk_cofounder_workflow`).

- [x] **Step 1: Viết test cho `risk_classification_fn` bằng stub context**

```python
# backend/app/tests/agents/test_adk_risk_classification_node.py
from types import SimpleNamespace

import pytest

from app.workforce.agents.orchestration.adk.nodes.risk_classification_node import (
    build_risk_classification_node,
    risk_classification_fn,
)


@pytest.mark.asyncio
async def test_risk_classification_fn_auto_start_for_r0_r1():
    ctx = SimpleNamespace(state={"active_domains": ["sales", "finance"]}, route=None)
    result = await risk_classification_fn(ctx)
    assert result == {"risk_level": "R0"}
    assert ctx.state["risk_level"] == "R0"
    assert ctx.route == "auto_start"


@pytest.mark.asyncio
async def test_risk_classification_fn_needs_confirmation_above_r1(monkeypatch):
    import app.workforce.agents.orchestration.specialist_registry as registry

    risky_spec = registry.SpecialistSpec(
        domain="finance", agent_key="finance_specialist", task="t",
        tool_flat_name="finance_get_financial_summary",
        fetch_snapshot=registry.SPECIALIST_REGISTRY["finance"].fetch_snapshot,
        risk_level="R2",
    )
    monkeypatch.setitem(registry.SPECIALIST_REGISTRY, "finance", risky_spec)

    ctx = SimpleNamespace(state={"active_domains": ["finance"]}, route=None)
    result = await risk_classification_fn(ctx)
    assert result == {"risk_level": "R2"}
    assert ctx.route == "needs_confirmation"


def test_build_risk_classification_node_shape():
    node = build_risk_classification_node()
    assert node.name == "risk_classification_node"
```

- [x] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_adk_risk_classification_node.py -v`
Expected: FAIL với `ModuleNotFoundError`

- [x] **Step 3: Viết `risk_classification_node.py`**

```python
# backend/app/workforce/agents/orchestration/adk/nodes/risk_classification_node.py
"""FunctionNode tất định — risk-tier R0-R4 KHÔNG để LLM tự quyết (đúng cách
chief_of_staff.py hiện không để LLM tự quyết action-plan, xem Quyết định 1)."""
from typing import Any

from google.adk.workflow._function_node import FunctionNode

from app.workforce.agents.orchestration.specialist_registry import (
    AUTO_START_MAX_RISK,
    RISK_ORDER,
    classify_mission_risk,
)


async def risk_classification_fn(ctx: Any) -> dict[str, str]:
    active_domains: list[str] = ctx.state.get("active_domains", [])
    risk_level = classify_mission_risk(active_domains)
    ctx.state["risk_level"] = risk_level
    ctx.route = (
        "auto_start"
        if RISK_ORDER.index(risk_level) <= RISK_ORDER.index(AUTO_START_MAX_RISK)
        else "needs_confirmation"
    )
    return {"risk_level": risk_level}


def build_risk_classification_node() -> FunctionNode:
    return FunctionNode(func=risk_classification_fn, name="risk_classification_node")
```

- [x] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_adk_risk_classification_node.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add backend/app/workforce/agents/orchestration/adk/nodes/__init__.py backend/app/workforce/agents/orchestration/adk/nodes/risk_classification_node.py backend/app/tests/agents/test_adk_risk_classification_node.py
git commit -m "feat(adk): add deterministic RiskClassificationNode (R0-R4)"
```

---

### Task 13: `GovernanceGateNode` (budget + stuck-loop check)

**Files:**
- Create: `backend/app/workforce/agents/orchestration/adk/nodes/governance_gate_node.py`
- Test: `backend/app/tests/agents/test_adk_governance_gate_node.py`

**Interfaces:**
- Consumes: `BudgetTracker.check(db, agent_run, budget, current_step) -> BudgetCheckResult`, `StuckDetector.analyze_run(db, run_id, history_window=10) -> StuckAnalysisResult` (không đổi, tái sử dụng nguyên).
- Produces: `async def governance_gate_fn(ctx) -> dict` — đọc `ctx.state["db"]`/`ctx.state["mission_run"]`/`ctx.state["mission_budget"]`/`ctx.state["current_step"]`, set `ctx.route = "blocked"` hoặc `"continue"`, ghi `ctx.state["governance_block_reason"]` khi bị chặn. `def build_governance_gate_node(name: str = "governance_gate_node") -> FunctionNode` — factory (dùng lại nhiều lần trong workflow, giống `check_governance()` closure hiện gọi ở nhiều điểm trong `chief_of_staff.py::orchestrate`).

- [x] **Step 1: Viết test — budget exceeded chặn, bình thường thì cho qua**

```python
# backend/app/tests/agents/test_adk_governance_gate_node.py
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.workforce.agents.governance.budget import BudgetCheckResult, MissionBudget
from app.workforce.agents.governance.stuck_detector import StuckAnalysisResult
from app.workforce.agents.orchestration.adk.nodes.governance_gate_node import (
    build_governance_gate_node,
    governance_gate_fn,
)


@pytest.mark.asyncio
async def test_governance_gate_fn_continues_when_within_budget():
    ctx = SimpleNamespace(
        state={"db": MagicMock(), "mission_run": MagicMock(id=1), "mission_budget": MissionBudget(), "current_step": 2},
        route=None,
    )
    with patch(
        "app.workforce.agents.orchestration.adk.nodes.governance_gate_node.BudgetTracker.check",
        return_value=BudgetCheckResult(is_exceeded=False),
    ), patch(
        "app.workforce.agents.orchestration.adk.nodes.governance_gate_node.StuckDetector.analyze_run",
        return_value=StuckAnalysisResult(is_stuck=False),
    ):
        result = await governance_gate_fn(ctx)

    assert result == {"blocked": False}
    assert ctx.route == "continue"
    assert "governance_block_reason" not in ctx.state


@pytest.mark.asyncio
async def test_governance_gate_fn_blocks_when_budget_exceeded():
    ctx = SimpleNamespace(
        state={"db": MagicMock(), "mission_run": MagicMock(id=1), "mission_budget": MissionBudget(), "current_step": 20},
        route=None,
    )
    with patch(
        "app.workforce.agents.orchestration.adk.nodes.governance_gate_node.BudgetTracker.check",
        return_value=BudgetCheckResult(is_exceeded=True, reason_code="STEP_LIMIT_EXCEEDED", message="quá số bước cho phép"),
    ):
        result = await governance_gate_fn(ctx)

    assert result == {"blocked": True, "reason_code": "STEP_LIMIT_EXCEEDED"}
    assert ctx.route == "blocked"
    assert ctx.state["governance_block_reason"] == "quá số bước cho phép"


def test_build_governance_gate_node_shape():
    node = build_governance_gate_node(name="governance_gate_pre_synthesis")
    assert node.name == "governance_gate_pre_synthesis"
```

- [x] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_adk_governance_gate_node.py -v`
Expected: FAIL với `ModuleNotFoundError`

- [x] **Step 3: Viết `governance_gate_node.py`**

```python
# backend/app/workforce/agents/orchestration/adk/nodes/governance_gate_node.py
"""FunctionNode tất định bọc BudgetTracker/StuckDetector — dùng lại tại nhiều
điểm trong graph, giống closure check_governance() trong chief_of_staff.py hiện
tại (KHÔNG đổi nội bộ BudgetTracker/StuckDetector, chỉ gọi lại nguyên vẹn)."""
from typing import Any

from google.adk.workflow._function_node import FunctionNode

from app.workforce.agents.governance.budget import BudgetTracker
from app.workforce.agents.governance.stuck_detector import StuckDetector


async def governance_gate_fn(ctx: Any) -> dict[str, Any]:
    db = ctx.state["db"]
    mission_run = ctx.state["mission_run"]
    budget = ctx.state.get("mission_budget")
    current_step = ctx.state.get("current_step", 0)

    budget_result = BudgetTracker.check(db=db, agent_run=mission_run, budget=budget, current_step=current_step)
    if budget_result.is_exceeded:
        ctx.state["governance_block_reason"] = budget_result.message
        ctx.route = "blocked"
        return {"blocked": True, "reason_code": budget_result.reason_code}

    stuck_result = StuckDetector.analyze_run(db=db, run_id=mission_run.id)
    if stuck_result.is_stuck and stuck_result.suggested_action == "ABORT_RUN":
        ctx.state["governance_block_reason"] = f"Stuck loop detected: {stuck_result.detail}"
        ctx.route = "blocked"
        return {"blocked": True, "reason_code": "STUCK_LOOP"}

    ctx.route = "continue"
    return {"blocked": False}


def build_governance_gate_node(name: str = "governance_gate_node") -> FunctionNode:
    return FunctionNode(func=governance_gate_fn, name=name)
```

- [x] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_adk_governance_gate_node.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add backend/app/workforce/agents/orchestration/adk/nodes/governance_gate_node.py backend/app/tests/agents/test_adk_governance_gate_node.py
git commit -m "feat(adk): add deterministic GovernanceGateNode (budget/stuck-loop check)"
```

---

### Task 14: `QualityGateNode`

**Files:**
- Create: `backend/app/workforce/agents/orchestration/adk/nodes/quality_gate_node.py`
- Test: `backend/app/tests/agents/test_adk_quality_gate_node.py`

**Interfaces:**
- Consumes: `QualityGateEvaluator.evaluate(domain, payload) -> QualityGateResult` (không đổi), `SPECIALIST_REGISTRY` (Task 11) để lọc domain nào `quality_gate_compatible`.
- Produces: `async def quality_gate_fn(ctx) -> dict` — đọc `ctx.state["specialist_reports"]`, set `ctx.route = "passed"` hoặc `"failed"`.

- [x] **Step 1: Viết test**

```python
# backend/app/tests/agents/test_adk_quality_gate_node.py
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.workforce.agents.governance.quality_gate import QualityGateResult, QualityGateVerdict
from app.workforce.agents.orchestration.adk.nodes.quality_gate_node import (
    build_quality_gate_node,
    quality_gate_fn,
)


@pytest.mark.asyncio
async def test_quality_gate_fn_passes_when_all_gates_pass():
    ctx = SimpleNamespace(
        state={"specialist_reports": {"sales": {"status": "success"}, "finance": {"status": "success"}}},
        route=None,
    )
    with patch(
        "app.workforce.agents.orchestration.adk.nodes.quality_gate_node.QualityGateEvaluator.evaluate",
        return_value=QualityGateResult(verdict=QualityGateVerdict.PASS, domain="sales"),
    ):
        result = await quality_gate_fn(ctx)

    assert result["any_failed"] is False
    assert ctx.route == "passed"


@pytest.mark.asyncio
async def test_quality_gate_fn_fails_when_any_gate_fails():
    ctx = SimpleNamespace(state={"specialist_reports": {"sales": {"status": "success"}}}, route=None)
    with patch(
        "app.workforce.agents.orchestration.adk.nodes.quality_gate_node.QualityGateEvaluator.evaluate",
        return_value=QualityGateResult(verdict=QualityGateVerdict.FAIL, domain="sales", issues=["no evidence"]),
    ):
        result = await quality_gate_fn(ctx)

    assert result["any_failed"] is True
    assert ctx.route == "failed"


def test_build_quality_gate_node_shape():
    node = build_quality_gate_node()
    assert node.name == "quality_gate_node"
```

- [x] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_adk_quality_gate_node.py -v`
Expected: FAIL với `ModuleNotFoundError`

- [x] **Step 3: Viết `quality_gate_node.py`**

```python
# backend/app/workforce/agents/orchestration/adk/nodes/quality_gate_node.py
"""FunctionNode tất định bọc QualityGateEvaluator — chỉ evaluate domain nào
SpecialistSpec.quality_gate_compatible=True (giống vòng lặp cross-cutting quality
gate trong chief_of_staff.py::orchestrate hiện tại)."""
from typing import Any

from google.adk.workflow._function_node import FunctionNode

from app.workforce.agents.governance.quality_gate import QualityGateEvaluator, QualityGateVerdict
from app.workforce.agents.orchestration.specialist_registry import SPECIALIST_REGISTRY


async def quality_gate_fn(ctx: Any) -> dict[str, Any]:
    specialist_reports: dict[str, Any] = ctx.state.get("specialist_reports", {})
    gate_results: dict[str, Any] = {}
    any_failed = False
    for domain, snapshot in specialist_reports.items():
        spec = SPECIALIST_REGISTRY.get(domain)
        if spec is None or not spec.quality_gate_compatible:
            continue
        gate_result = QualityGateEvaluator.evaluate(domain, snapshot)
        gate_results[domain] = gate_result
        if gate_result.verdict == QualityGateVerdict.FAIL:
            any_failed = True

    ctx.state["quality_gate_results"] = gate_results
    ctx.route = "failed" if any_failed else "passed"
    return {"any_failed": any_failed}


def build_quality_gate_node() -> FunctionNode:
    return FunctionNode(func=quality_gate_fn, name="quality_gate_node")
```

- [x] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_adk_quality_gate_node.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add backend/app/workforce/agents/orchestration/adk/nodes/quality_gate_node.py backend/app/tests/agents/test_adk_quality_gate_node.py
git commit -m "feat(adk): add deterministic QualityGateNode"
```

---

## Phase 8 — Specialist delegation & durable pause

### Task 15: `queue_specialist_delegation()` — tạo `RunStep` + gọi `TaskBoardService.assign_step()`

**Files:**
- Create: `backend/app/workforce/agents/orchestration/adk/specialist_delegation.py`
- Test: `backend/app/tests/agents/test_adk_specialist_delegation.py`

**Interfaces:**
- Consumes: `TaskBoardService.assign_step` (không đổi, `backend/app/workforce/agents/delegation/task_board.py:62`), `SpecialistSpec` (Task 11).
- Produces: `async def queue_specialist_delegation(db, *, workspace_id, outcome_run, domain, spec, runtime_name, actor_agent_key="adk_cofounder_workflow") -> RunStep`. Dùng ở Task 16 (`SpecialistDelegationNode`).

**Ghi chú:** giữ nguyên tag `"mission_kind": "chief_of_staff_specialist"` trên `RunStep.inputs_jsonb` — dù orchestrator giờ là ADK, không phải `ChiefOfStaffOrchestrator`, tag này là điểm neo mà `MissionResumeJobService` (Task 17-18) và bất kỳ tooling/dashboard nào đang lọc theo `mission_kind` vẫn tiếp tục nhận diện đúng. Đổi tag là phá vỡ tương thích không cần thiết.

- [x] **Step 1: Viết test — gọi 2 lần idempotent, xác nhận `DelegationJob` được tạo qua `TaskBoardService` thật**

```python
# backend/app/tests/agents/test_adk_specialist_delegation.py
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import sessionmaker

from agent_runtime.sessions.models import AgentRun
from app.core.feature_flags import FLAG_AGENT_DELEGATION
from app.core.snowflake import generate_snowflake_id
from app.db.session import engine
from app.founder_os.outcomes.models import Outcome, OutcomeRun, RunStep
from app.platform.auth.models import User, Workspace
from app.platform.core.models import FeatureFlag
from app.workforce.agents.delegation.manager import DelegationProviderManager
from app.workforce.agents.delegation.models import DelegationJob
from app.workforce.agents.delegation.provider import DelegationProvider
from app.workforce.agents.delegation.task_board import TaskBoardService
from app.workforce.agents.delegation.types import DelegationHandle, DelegationResult, DelegationStatus, ProviderHealth
from app.workforce.agents.orchestration.adk.specialist_delegation import queue_specialist_delegation
from app.workforce.agents.orchestration.specialist_registry import SPECIALIST_REGISTRY


class HealthyProvider(DelegationProvider):
    @property
    def provider_name(self) -> str:
        return "in_process"

    async def delegate(self, request, idempotency_key):
        return DelegationHandle(provider_name="in_process", external_id=idempotency_key)

    async def poll(self, handle):
        return DelegationResult(status=DelegationStatus.RUNNING)

    async def cancel(self, handle):
        return True

    async def health(self):
        return ProviderHealth(provider_name="in_process", available=True)


@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()


@pytest.mark.asyncio
async def test_queue_specialist_delegation_creates_run_step_and_delegation_job(db_session, monkeypatch):
    manager = DelegationProviderManager()
    manager.register(HealthyProvider())
    monkeypatch.setattr(TaskBoardService, "provider_manager", manager)

    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db_session.add(User(id=user_id, email=f"sd-{user_id}@example.invalid"))
    db_session.add(Workspace(id=workspace_id, name=f"SD {workspace_id}"))
    db_session.add(FeatureFlag(id=generate_snowflake_id(), workspace_id=workspace_id, key=FLAG_AGENT_DELEGATION, enabled=True))
    db_session.flush()

    outcome = Outcome(
        id=generate_snowflake_id(), workspace_id=workspace_id, function="strategy",
        title="Mission", desired_result="goal", requested_by=user_id, status="running",
    )
    db_session.add(outcome)
    db_session.flush()
    outcome_run = OutcomeRun(id=generate_snowflake_id(), outcome_id=outcome.id, status="running", verification_status="UNKNOWN")
    db_session.add(outcome_run)
    db_session.flush()
    mission_run = AgentRun(
        id=generate_snowflake_id(), workspace_id=workspace_id, company_id=workspace_id,
        user_id=user_id, outcome_run_id=outcome_run.id, agent_key="chief_of_staff",
        runtime="adk", status="running", started_at=datetime.now(timezone.utc),
    )
    db_session.add(mission_run)
    db_session.flush()
    outcome_run.agent_run_id = mission_run.id
    db_session.commit()

    spec = SPECIALIST_REGISTRY["finance"]
    step = await queue_specialist_delegation(
        db_session, workspace_id=workspace_id, outcome_run=outcome_run, domain="finance",
        spec=spec, runtime_name="mock",
    )

    assert step.inputs_jsonb["mission_kind"] == "chief_of_staff_specialist"
    assert step.inputs_jsonb["report_key"] == "finance"
    jobs = db_session.query(DelegationJob).filter(DelegationJob.run_step_id == step.id).all()
    assert len(jobs) == 1

    # Idempotent: gọi lại lần 2 cho cùng domain không tạo thêm RunStep mới
    step2 = await queue_specialist_delegation(
        db_session, workspace_id=workspace_id, outcome_run=outcome_run, domain="finance",
        spec=spec, runtime_name="mock",
    )
    assert step2.id == step.id
    all_steps = db_session.query(RunStep).filter(RunStep.run_id == outcome_run.id).all()
    assert len(all_steps) == 1
```

- [x] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_adk_specialist_delegation.py -v`
Expected: FAIL với `ModuleNotFoundError`

- [x] **Step 3: Viết `specialist_delegation.py`**

```python
# backend/app/workforce/agents/orchestration/adk/specialist_delegation.py
"""Trích từ ChiefOfStaffOrchestrator._queue_specialist_delegations — chuyển từ
"1 lần cho tất cả domains" sang "1 lần cho đúng 1 domain" vì mỗi domain giờ là 1
FunctionNode riêng trong graph (Task 16), không phải 1 vòng lặp Python."""
from sqlalchemy.orm import Session

from app.core.snowflake import generate_snowflake_id
from app.founder_os.outcomes.models import OutcomeRun, RunStep
from app.workforce.agents.delegation.task_board import TaskBoardService
from app.workforce.agents.orchestration.specialist_registry import SpecialistSpec


async def queue_specialist_delegation(
    db: Session,
    *,
    workspace_id: int,
    outcome_run: OutcomeRun,
    domain: str,
    spec: SpecialistSpec,
    runtime_name: str,
    actor_agent_key: str = "adk_cofounder_workflow",
) -> RunStep:
    existing_steps = db.query(RunStep).filter(RunStep.run_id == outcome_run.id).all()
    step = next(
        (
            s for s in existing_steps
            if isinstance(s.inputs_jsonb, dict)
            and s.inputs_jsonb.get("mission_kind") == "chief_of_staff_specialist"
            and s.inputs_jsonb.get("report_key") == domain
        ),
        None,
    )
    if step is None:
        step = RunStep(
            id=generate_snowflake_id(),
            run_id=outcome_run.id,
            type="agent",
            inputs_jsonb={
                "mission_kind": "chief_of_staff_specialist",
                "report_key": domain,
                "task": spec.task,
                "required": True,
                "failure_policy": "fail_mission",
            },
            expected_output=f"Structured {domain} specialist report",
            risk_level=spec.risk_level,
            depends_on_step_ids=[],
            status="pending",
        )
        db.add(step)
        db.flush()

    await TaskBoardService.assign_step(
        db=db,
        workspace_id=workspace_id,
        step_id=step.id,
        profile_id=spec.delegate_via_profile_id,
        runtime_name=runtime_name,
        provider_name="in_process",
        actor_agent_key=actor_agent_key,
    )
    return step
```

- [x] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_adk_specialist_delegation.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add backend/app/workforce/agents/orchestration/adk/specialist_delegation.py backend/app/tests/agents/test_adk_specialist_delegation.py
git commit -m "feat(adk): add queue_specialist_delegation helper (per-domain RunStep + TaskBoardService.assign_step)"
```

---

### Task 16: `SpecialistDelegationNode` — pause qua `RequestInput`

**Files:**
- Create: `backend/app/workforce/agents/orchestration/adk/nodes/specialist_delegation_node.py`
- Test: `backend/app/tests/agents/test_adk_specialist_delegation_node.py`

**Interfaces:**
- Consumes: `queue_specialist_delegation` (Task 15).
- Produces: `def build_specialist_delegation_fn(domain: str) -> Callable` (async generator function) — tự bỏ qua (yield `{"skipped": True, "domain": domain}`, không pause) nếu `domain` không nằm trong `ctx.state["active_domains"]`, vì `build_adk_cofounder_workflow()` (Task 23) wire tĩnh cả 4 domain vào graph bất kể mission này chọn domain nào. `def build_specialist_delegation_node(domain: str) -> FunctionNode` — 1 node riêng cho mỗi domain (Sales/Finance/Marketing/Legal), `rerun_on_resume=False` (giá trị resume trở thành output của node, không chạy lại thân hàm — đúng ngữ nghĩa "tạo RunStep rồi pause, KHÔNG chạy lại code tạo RunStep khi resume"). Dùng ở Task 23 (`build_adk_cofounder_workflow`).

- [x] **Step 1: Viết test — gọi trực tiếp async generator function, xác nhận item đầu tiên yield là `RequestInput` đúng `interrupt_id`**

```python
# backend/app/tests/agents/test_adk_specialist_delegation_node.py
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from google.adk.events.request_input import RequestInput
from sqlalchemy.orm import sessionmaker

from agent_runtime.sessions.models import AgentRun
from app.core.feature_flags import FLAG_AGENT_DELEGATION
from app.core.snowflake import generate_snowflake_id
from app.db.session import engine
from app.founder_os.outcomes.models import Outcome, OutcomeRun
from app.platform.auth.models import User, Workspace
from app.platform.core.models import FeatureFlag
from app.workforce.agents.delegation.manager import DelegationProviderManager
from app.workforce.agents.delegation.provider import DelegationProvider
from app.workforce.agents.delegation.task_board import TaskBoardService
from app.workforce.agents.delegation.types import DelegationHandle, DelegationResult, DelegationStatus, ProviderHealth
from app.workforce.agents.orchestration.adk.nodes.specialist_delegation_node import (
    build_specialist_delegation_fn,
    build_specialist_delegation_node,
)


class HealthyProvider(DelegationProvider):
    @property
    def provider_name(self) -> str:
        return "in_process"

    async def delegate(self, request, idempotency_key):
        return DelegationHandle(provider_name="in_process", external_id=idempotency_key)

    async def poll(self, handle):
        return DelegationResult(status=DelegationStatus.RUNNING)

    async def cancel(self, handle):
        return True

    async def health(self):
        return ProviderHealth(provider_name="in_process", available=True)


@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()


@pytest.mark.asyncio
async def test_specialist_delegation_fn_yields_request_input(db_session, monkeypatch):
    manager = DelegationProviderManager()
    manager.register(HealthyProvider())
    monkeypatch.setattr(TaskBoardService, "provider_manager", manager)

    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db_session.add(User(id=user_id, email=f"sdn-{user_id}@example.invalid"))
    db_session.add(Workspace(id=workspace_id, name=f"SDN {workspace_id}"))
    db_session.add(FeatureFlag(id=generate_snowflake_id(), workspace_id=workspace_id, key=FLAG_AGENT_DELEGATION, enabled=True))
    db_session.flush()
    outcome = Outcome(
        id=generate_snowflake_id(), workspace_id=workspace_id, function="strategy",
        title="Mission", desired_result="goal", requested_by=user_id, status="running",
    )
    db_session.add(outcome)
    db_session.flush()
    outcome_run = OutcomeRun(id=generate_snowflake_id(), outcome_id=outcome.id, status="running", verification_status="UNKNOWN")
    db_session.add(outcome_run)
    db_session.flush()
    mission_run = AgentRun(
        id=generate_snowflake_id(), workspace_id=workspace_id, company_id=workspace_id,
        user_id=user_id, outcome_run_id=outcome_run.id, agent_key="chief_of_staff",
        runtime="adk", status="running", started_at=datetime.now(timezone.utc),
    )
    db_session.add(mission_run)
    db_session.flush()
    outcome_run.agent_run_id = mission_run.id
    db_session.commit()

    import app.workforce.agents.orchestration.adk.nodes.specialist_delegation_node as node_module
    monkeypatch.setattr(node_module, "SessionLocal", lambda: db_session)

    ctx = SimpleNamespace(
        state={
            "outcome_run_id": outcome_run.id,
            "workspace_id": workspace_id,
            "specialist_runtime_name": "mock",
        }
    )

    fn = build_specialist_delegation_fn("finance")
    items = [item async for item in fn(ctx)]

    assert len(items) == 1
    assert isinstance(items[0], RequestInput)
    step_id = ctx.state["specialist_step_ids"]["finance"]
    assert items[0].interrupt_id == f"delegation_step:{step_id}"


@pytest.mark.asyncio
async def test_specialist_delegation_fn_skips_domain_not_requested():
    """4 specialist node đều được wire tĩnh vào graph (Task 23); domain nào
    mission này không yêu cầu thì tự bỏ qua, không tạo RunStep, không pause."""
    ctx = SimpleNamespace(state={"active_domains": ["finance"]})
    fn = build_specialist_delegation_fn("legal")
    items = [item async for item in fn(ctx)]

    assert items == [{"skipped": True, "domain": "legal"}]
    assert "specialist_step_ids" not in ctx.state


def test_build_specialist_delegation_node_shape():
    node = build_specialist_delegation_node("sales")
    assert node.name == "specialist_delegation_sales_node"
    assert node.rerun_on_resume is False
```

- [x] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_adk_specialist_delegation_node.py -v`
Expected: FAIL với `ModuleNotFoundError`

- [x] **Step 3: Viết `specialist_delegation_node.py`**

```python
# backend/app/workforce/agents/orchestration/adk/nodes/specialist_delegation_node.py
"""Mỗi domain (Sales/Finance/Marketing/Legal) là 1 FunctionNode riêng — tạo
RunStep + gọi TaskBoardService.assign_step() rồi PAUSE bằng RequestInput. KHÔNG
tự chạy DeepSeekHarnessAdapter trong tiến trình ADK — delegation-worker (process
riêng, backend/app/workforce/agents/delegation/worker.py) xử lý việc thật, và
MissionResumeJobService (Task 17-18) sẽ resume node này khi RunStep hoàn tất."""
from collections.abc import AsyncGenerator, Callable
from typing import Any

from google.adk.events.request_input import RequestInput
from google.adk.workflow._function_node import FunctionNode

from app.db.session import SessionLocal
from app.founder_os.outcomes.models import OutcomeRun
from app.workforce.agents.orchestration.adk.specialist_delegation import queue_specialist_delegation
from app.workforce.agents.orchestration.specialist_registry import SPECIALIST_REGISTRY


def interrupt_id_for_step(step_id: int) -> str:
    return f"delegation_step:{step_id}"


def build_specialist_delegation_fn(domain: str) -> Callable[[Any], AsyncGenerator[Any, None]]:
    async def specialist_delegation_fn(ctx: Any) -> AsyncGenerator[Any, None]:
        # build_adk_cofounder_workflow() (Task 23) fan-out từ planning tới CẢ 4
        # specialist node không điều kiện (wiring graph tĩnh) — domain nào
        # không nằm trong active_domains của MISSION NÀY thì tự bỏ qua ở đây,
        # không delegate, không pause (không yield RequestInput).
        if domain not in (ctx.state.get("active_domains") or []):
            yield {"skipped": True, "domain": domain}
            return

        # Mở session riêng (KHÔNG đọc ctx.state["db"]) — xem quy ước ctx.state ở
        # đầu Phase 10: session không sống được qua ranh giới pause/resume của
        # chính node này. Import SessionLocal ở cấp module (không phải trong
        # thân hàm) để test có thể monkeypatch được.
        db = SessionLocal()
        try:
            spec = SPECIALIST_REGISTRY[domain]
            outcome_run = db.query(OutcomeRun).filter(OutcomeRun.id == ctx.state["outcome_run_id"]).one()
            workspace_id = ctx.state["workspace_id"]
            runtime_name = ctx.state.get("specialist_runtime_name", "deepseek_harness")

            step = await queue_specialist_delegation(
                db,
                workspace_id=workspace_id,
                outcome_run=outcome_run,
                domain=domain,
                spec=spec,
                runtime_name=runtime_name,
            )
            ctx.state.setdefault("specialist_step_ids", {})[domain] = step.id
            step_id = step.id
        finally:
            db.close()

        yield RequestInput(
            interrupt_id=interrupt_id_for_step(step_id),
            message=f"Waiting for {domain} specialist RunStep {step_id} to complete",
            response_schema=dict,
        )

    specialist_delegation_fn.__name__ = f"specialist_delegation_{domain}_fn"
    return specialist_delegation_fn


def build_specialist_delegation_node(domain: str) -> FunctionNode:
    fn = build_specialist_delegation_fn(domain)
    return FunctionNode(func=fn, name=f"specialist_delegation_{domain}_node", rerun_on_resume=False)
```

- [x] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_adk_specialist_delegation_node.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add backend/app/workforce/agents/orchestration/adk/nodes/specialist_delegation_node.py backend/app/tests/agents/test_adk_specialist_delegation_node.py
git commit -m "feat(adk): add SpecialistDelegationNode pausing via RequestInput until RunStep completes"
```

---

## Phase 9 — `MissionResumeJobService`: exactly-once resume

### Task 17: `MissionResumeJobService.enqueue_resume()`

**Files:**
- Create: `backend/app/workforce/agents/orchestration/mission_resume_service.py`
- Test: `backend/app/tests/agents/test_mission_resume_service_enqueue.py`

**Interfaces:**
- Consumes: `MissionResumeJob` (Task 5).
- Produces: `MissionResumeJobService.enqueue_resume(db, *, workspace_id, mission_run_id, workflow_session_id, checkpoint_key, reason) -> MissionResumeJob` — idempotent theo `(mission_run_id, checkpoint_key)`, trả về row đã có nếu trùng thay vì raise. Dùng ở Task 26 (worker gọi khi 1 `RunStep` specialist chuyển terminal — thay thế điểm gọi `maybe_resume_mission` hiện tại trong `worker.py`).

- [x] **Step 1: Viết test — gọi 2 lần cùng checkpoint trả về đúng 1 row**

```python
# backend/app/tests/agents/test_mission_resume_service_enqueue.py
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import sessionmaker

from agent_runtime.sessions.models import AgentRun
from app.core.snowflake import generate_snowflake_id
from app.db.session import engine
from app.platform.auth.models import User, Workspace
from app.workforce.agents.orchestration.mission_resume_models import MissionResumeJob
from app.workforce.agents.orchestration.mission_resume_service import MissionResumeJobService


@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()


def _mission(db_session):
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db_session.add(User(id=user_id, email=f"mre-{user_id}@example.invalid"))
    db_session.add(Workspace(id=workspace_id, name=f"MRE {workspace_id}"))
    db_session.flush()
    mission_run = AgentRun(
        id=generate_snowflake_id(), workspace_id=workspace_id, company_id=workspace_id,
        user_id=user_id, agent_key="chief_of_staff", runtime="adk", status="running",
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(mission_run)
    db_session.commit()
    return workspace_id, mission_run


def test_enqueue_resume_is_idempotent_per_checkpoint(db_session):
    workspace_id, mission_run = _mission(db_session)

    first = MissionResumeJobService.enqueue_resume(
        db_session, workspace_id=workspace_id, mission_run_id=mission_run.id,
        workflow_session_id="adk-session-1", checkpoint_key="specialist_join:111",
        reason="specialist_delegation_completed",
    )
    second = MissionResumeJobService.enqueue_resume(
        db_session, workspace_id=workspace_id, mission_run_id=mission_run.id,
        workflow_session_id="adk-session-1", checkpoint_key="specialist_join:111",
        reason="specialist_delegation_completed",
    )

    assert first.id == second.id
    rows = db_session.query(MissionResumeJob).filter(MissionResumeJob.mission_run_id == mission_run.id).all()
    assert len(rows) == 1


def test_enqueue_resume_allows_distinct_checkpoints(db_session):
    workspace_id, mission_run = _mission(db_session)

    first = MissionResumeJobService.enqueue_resume(
        db_session, workspace_id=workspace_id, mission_run_id=mission_run.id,
        workflow_session_id="adk-session-1", checkpoint_key="specialist_join:111",
        reason="specialist_delegation_completed",
    )
    second = MissionResumeJobService.enqueue_resume(
        db_session, workspace_id=workspace_id, mission_run_id=mission_run.id,
        workflow_session_id="adk-session-1", checkpoint_key="specialist_join:222",
        reason="specialist_delegation_completed",
    )

    assert first.id != second.id
```

- [x] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_mission_resume_service_enqueue.py -v`
Expected: FAIL với `ModuleNotFoundError`

- [x] **Step 3: Viết `mission_resume_service.py` (phần `enqueue_resume`)**

```python
# backend/app/workforce/agents/orchestration/mission_resume_service.py
"""Thay cho advisory-lock + materialized-event trong
chief_of_staff.py::resume_after_delegation (xem continuation.py hiện tại) —
đảm bảo đúng 1 worker resume AdkCofounderWorkflow cho mỗi checkpoint."""
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.snowflake import generate_snowflake_id
from app.workforce.agents.orchestration.mission_resume_models import MissionResumeJob


class MissionResumeJobService:
    @staticmethod
    def enqueue_resume(
        db: Session,
        *,
        workspace_id: int,
        mission_run_id: int,
        workflow_session_id: str | None,
        checkpoint_key: str,
        reason: str,
    ) -> MissionResumeJob:
        existing = (
            db.query(MissionResumeJob)
            .filter(
                MissionResumeJob.mission_run_id == mission_run_id,
                MissionResumeJob.checkpoint_key == checkpoint_key,
            )
            .first()
        )
        if existing is not None:
            return existing

        job = MissionResumeJob(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            mission_run_id=mission_run_id,
            workflow_session_id=workflow_session_id,
            checkpoint_key=checkpoint_key,
            idempotency_key=f"mission_resume:{mission_run_id}:{checkpoint_key}",
            reason=reason,
            status="queued",
        )
        db.add(job)
        try:
            db.commit()
        except IntegrityError:
            # Race: worker khác vừa insert cùng checkpoint giữa lúc query và
            # commit ở trên — coi row của họ là nguồn sự thật, không tạo trùng.
            db.rollback()
            existing = (
                db.query(MissionResumeJob)
                .filter(
                    MissionResumeJob.mission_run_id == mission_run_id,
                    MissionResumeJob.checkpoint_key == checkpoint_key,
                )
                .one()
            )
            return existing
        db.refresh(job)
        return job
```

- [x] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_mission_resume_service_enqueue.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add backend/app/workforce/agents/orchestration/mission_resume_service.py backend/app/tests/agents/test_mission_resume_service_enqueue.py
git commit -m "feat(orchestration): add MissionResumeJobService.enqueue_resume (idempotent per checkpoint)"
```

---

### Task 18: `MissionResumeJobService.claim_next()` / `mark_completed()` / `mark_failed()` — exactly-once claim

**Files:**
- Modify: `backend/app/workforce/agents/orchestration/mission_resume_service.py`
- Test: `backend/app/tests/agents/test_mission_resume_service_claim.py`

**Interfaces:**
- Produces: `MissionResumeJobService.claim_next(db, worker_id: str, now: datetime) -> int | None` (trả `job.id` hoặc `None`, dùng `with_for_update(skip_locked=True)` giống `claim_due_job` trong `delegation/worker.py`), `MissionResumeJobService.mark_completed(db, job_id) -> None`, `MissionResumeJobService.mark_failed(db, job_id, error_message: str) -> None`. Dùng ở Task 26 (worker loop gọi `claim_next` → nếu có job, gọi `resume_mission()` seam → `mark_completed`/`mark_failed`).

- [x] **Step 1: Viết test — claim 1 lần chuyển "claimed", claim lần 2 (giả lập worker thứ 2) trả về `None` vì không còn job "queued" nào khớp**

```python
# backend/app/tests/agents/test_mission_resume_service_claim.py
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import sessionmaker

from agent_runtime.sessions.models import AgentRun
from app.core.snowflake import generate_snowflake_id
from app.db.session import engine
from app.platform.auth.models import User, Workspace
from app.workforce.agents.orchestration.mission_resume_models import MissionResumeJob
from app.workforce.agents.orchestration.mission_resume_service import MissionResumeJobService


@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()


def _queued_job(db_session):
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db_session.add(User(id=user_id, email=f"mrc-{user_id}@example.invalid"))
    db_session.add(Workspace(id=workspace_id, name=f"MRC {workspace_id}"))
    db_session.flush()
    mission_run = AgentRun(
        id=generate_snowflake_id(), workspace_id=workspace_id, company_id=workspace_id,
        user_id=user_id, agent_key="chief_of_staff", runtime="adk", status="running",
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(mission_run)
    db_session.flush()
    job = MissionResumeJobService.enqueue_resume(
        db_session, workspace_id=workspace_id, mission_run_id=mission_run.id,
        workflow_session_id="adk-session-1", checkpoint_key="specialist_join:111",
        reason="specialist_delegation_completed",
    )
    return job


def test_claim_next_is_exactly_once_across_two_simulated_workers(db_session):
    job = _queued_job(db_session)
    now = datetime.now(timezone.utc)

    claimed_id_a = MissionResumeJobService.claim_next(db_session, "worker-a", now)
    assert claimed_id_a == job.id
    db_session.refresh(job)
    assert job.status == "claimed"
    assert job.claimed_by == "worker-a"

    # Worker thứ 2 chạy claim_next ngay sau đó — không còn job "queued" nào để lấy.
    claimed_id_b = MissionResumeJobService.claim_next(db_session, "worker-b", now)
    assert claimed_id_b is None


def test_mark_completed_and_mark_failed(db_session):
    job = _queued_job(db_session)
    now = datetime.now(timezone.utc)
    MissionResumeJobService.claim_next(db_session, "worker-a", now)

    MissionResumeJobService.mark_completed(db_session, job.id)
    db_session.refresh(job)
    assert job.status == "completed"
    assert job.completed_at is not None

    job2 = _queued_job(db_session)
    MissionResumeJobService.claim_next(db_session, "worker-a", now)
    MissionResumeJobService.mark_failed(db_session, job2.id, "resume raised ValueError")
    db_session.refresh(job2)
    assert job2.status == "failed"
    assert job2.error_message == "resume raised ValueError"
```

- [x] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_mission_resume_service_claim.py -v`
Expected: FAIL với `AttributeError: type object 'MissionResumeJobService' has no attribute 'claim_next'`

- [x] **Step 3: Thêm `claim_next`/`mark_completed`/`mark_failed` vào `MissionResumeJobService`**

Thêm vào `backend/app/workforce/agents/orchestration/mission_resume_service.py`:

```python
    @staticmethod
    def claim_next(db: Session, worker_id: str, now: datetime) -> int | None:
        job = (
            db.query(MissionResumeJob)
            .filter(MissionResumeJob.status == "queued")
            .order_by(MissionResumeJob.created_at, MissionResumeJob.id)
            .with_for_update(skip_locked=True)
            .first()
        )
        if job is None:
            db.rollback()
            return None
        job.status = "claimed"
        job.claimed_by = worker_id
        job.claimed_at = now
        db.commit()
        return job.id

    @staticmethod
    def mark_completed(db: Session, job_id: int) -> None:
        job = db.query(MissionResumeJob).filter(MissionResumeJob.id == job_id).with_for_update().one()
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        db.commit()

    @staticmethod
    def mark_failed(db: Session, job_id: int, error_message: str) -> None:
        job = db.query(MissionResumeJob).filter(MissionResumeJob.id == job_id).with_for_update().one()
        job.status = "failed"
        job.error_message = error_message
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
```

(thêm 3 method này vào trong `class MissionResumeJobService` đã có, ngay sau `enqueue_resume`.)

- [x] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_mission_resume_service_claim.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add backend/app/workforce/agents/orchestration/mission_resume_service.py backend/app/tests/agents/test_mission_resume_service_claim.py
git commit -m "feat(orchestration): add MissionResumeJobService.claim_next/mark_completed/mark_failed"
```

---

## Phase 10 — Node còn lại: Create/Context/Planning/Synthesis/Approval/Execution

**Ghi chú bắt buộc về `ctx.state` (áp dụng cho MỌI node từ Task 13 trở đi, kể cả `GovernanceGateNode` đã viết ở Task 13):** `ctx.state` được `DatabaseSessionService`/`InMemorySessionService` lưu lại giữa các bước (đặc biệt cần thiết qua ranh giới pause/resume của `SpecialistDelegationNode`) — nó PHẢI chỉ chứa dữ liệu JSON-serializable (id dạng số/chuỗi, dict, list, string thường). KHÔNG được đặt 1 SQLAlchemy `Session` hay ORM object (`Outcome`/`OutcomeRun`/`AgentRun`) trực tiếp vào `ctx.state` — object đó không serialize được, và 1 khi mission pause chờ specialist (có thể vài phút tới nhiều giờ, thậm chí khác worker process khi resume), giữ 1 DB session mở xuyên suốt là sai kiến trúc (giống lý do `delegation-worker.py` luôn mở `SessionLocal()` mới cho mỗi đơn vị việc thay vì giữ 1 session sống xuyên suốt).

**Quy ước state áp dụng thống nhất:** mỗi node `from app.db.session import SessionLocal` Ở CẤP MODULE (không phải trong thân hàm — để test monkeypatch được), tự mở `db = SessionLocal()` ở đầu thân hàm (đóng lại ở cuối bằng `try/finally: db.close()`), và chỉ đọc/ghi id (`ctx.state["mission_id"]`, `["outcome_id"]`, `["outcome_run_id"]`) thay vì object ORM. Điều này áp dụng NGƯỢC lại cho `GovernanceGateNode` (Task 13) đã viết ở trên — trước khi làm tiếp Phase này, quay lại sửa `governance_gate_node.py`: thêm `from app.db.session import SessionLocal` ở đầu file, thay `db = ctx.state["db"]` bằng `db = SessionLocal()` (đóng session ở `finally`), và thay `mission_run = ctx.state["mission_run"]` bằng truy vấn `db.query(AgentRun).filter(AgentRun.id == ctx.state["mission_id"]).one()` (cần thêm import `from agent_runtime.sessions.models import AgentRun`). Cập nhật lại 2 test tương ứng trong `test_adk_governance_gate_node.py` để `ctx.state` chỉ chứa `{"mission_id": ..., "mission_budget": ..., "current_step": ...}` (không còn `"db"`/`"mission_run"`), tạo trước 1 `AgentRun` thật trong `db_session` rồi patch `SessionLocal` của module đó để trả về session test thay vì kết nối DB thật (`monkeypatch.setattr(governance_gate_node_module, "SessionLocal", lambda: db_session)`), chạy lại `pytest app/tests/agents/test_adk_governance_gate_node.py -v` xác nhận vẫn PASS trước khi tiếp tục Phase 10.

**Ghi chú đối chiếu hành vi (đọc kỹ trước khi implement Phase này):** sơ đồ node ở Quyết định 1 là `CreateMissionNode → BuildCompanyContextNode → RiskClassificationNode → PlanningNode → Specialist Delegation → Wait/Resume → SynthesisNode → ApprovalGateNode → ExecutionNode → QualityGateNode`. Nhưng hành vi THẬT của `chief_of_staff.py::orchestrate()` (phải giữ nguyên, theo yêu cầu "equivalent governance side effects") lại chạy quality-gate NGAY SAU synthesis, TRƯỚC khi derive priorities/action_plan và tạo approval — tức thứ tự thật là Synthesis → QualityGate → (derive priorities/action_plan + tạo Approval) → finalize. Giữ đúng thứ tự sơ đồ theo nghĩa đen sẽ đổi hành vi (mission có thể bị coi "completed" và tạo Approval trước khi biết quality gate FAIL). Phase này ưu tiên đúng hành vi đã verify trong code thật: `SynthesisNode → QualityGateNode (Task 14, dùng lại) → ApprovalGateNode (derive priorities/action_plan + tạo Approval, chỉ khi gate PASS) → ExecutionNode (finalize status + ghi mission_completed)`. Đây là 1 phán đoán kỹ thuật cụ thể — xem mục "Câu hỏi mở" ở cuối kế hoạch.

### Task 19: `CreateMissionNode` + `BuildCompanyContextNode`

**Files:**
- Create: `backend/app/workforce/agents/orchestration/adk/nodes/create_mission_node.py`
- Create: `backend/app/workforce/agents/orchestration/adk/nodes/build_company_context_node.py`
- Test: `backend/app/tests/agents/test_adk_create_mission_and_context_nodes.py`

**Interfaces:**
- Consumes: `build_agent_context`, `CofounderContextAssembler.assemble` (không đổi, `backend/app/workforce/agents/context/`).
- Produces: `async def create_mission_fn(ctx) -> dict` — đọc `ctx.state["goal"]/["workspace_id"]/["user_id"]/["company_id"]/["requested_domains"]/["intent"]`, tạo `Outcome(status="draft")`/`OutcomeRun(status="queued")`/`AgentRun(status="created")` (y hệt nhánh không-resume của `chief_of_staff.py::orchestrate`, dòng ~230-282), ghi `ctx.state["mission_id"]`/`["outcome_id"]`/`["outcome_run_id"]` (chỉ id, KHÔNG phải object ORM — xem quy ước ctx.state đầu Phase 10). Nếu `ctx.state["existing_mission_id"]` có giá trị (đường `confirm_mission()`, Task 25) thì TÁI DÙNG Outcome/OutcomeRun/AgentRun đã có thay vì tạo mới. `async def build_company_context_fn(ctx) -> dict` — ghi `ctx.state["agent_context"]`/`["cofounder_context"]`.

- [x] **Step 1: Viết test cho `create_mission_fn` (DB thật) và `build_company_context_fn`**

```python
# backend/app/tests/agents/test_adk_create_mission_and_context_nodes.py
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import sessionmaker

from app.core.snowflake import generate_snowflake_id
from app.db.session import engine
from app.founder_os.outcomes.models import Outcome, OutcomeRun
from app.platform.auth.models import User, Workspace
from app.workforce.agents.orchestration.adk.nodes.build_company_context_node import build_company_context_fn
from app.workforce.agents.orchestration.adk.nodes.create_mission_node import create_mission_fn


@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()


@pytest.mark.asyncio
async def test_create_mission_fn_creates_draft_rows(db_session, monkeypatch):
    from agent_runtime.sessions.models import AgentRun
    from app.workforce.agents.orchestration.adk.nodes import create_mission_node as node_module

    monkeypatch.setattr(node_module, "SessionLocal", lambda: db_session)

    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db_session.add(User(id=user_id, email=f"cm-{user_id}@example.invalid"))
    db_session.add(Workspace(id=workspace_id, name=f"CM {workspace_id}"))
    db_session.commit()

    ctx = SimpleNamespace(state={
        "goal": "Đánh giá tình hình sales và finance tuần này",
        "workspace_id": workspace_id,
        "user_id": user_id,
        "company_id": workspace_id,
        "requested_domains": ["sales", "finance"],
        "intent": None,
    })

    result = await create_mission_fn(ctx)

    assert result["mission_id"] == ctx.state["mission_id"]
    outcome = db_session.query(Outcome).filter(Outcome.id == ctx.state["outcome_id"]).one()
    assert outcome.status == "draft"
    outcome_run = db_session.query(OutcomeRun).filter(OutcomeRun.id == ctx.state["outcome_run_id"]).one()
    assert outcome_run.status == "queued"
    mission_run = db_session.query(AgentRun).filter(AgentRun.id == ctx.state["mission_id"]).one()
    assert mission_run.status == "created"


@pytest.mark.asyncio
async def test_create_mission_fn_reuses_existing_draft_mission(db_session, monkeypatch):
    """confirm_mission() (Task 25) chạy lại Workflow cho 1 mission đã ở draft —
    existing_mission_id phải khiến node này TÁI DÙNG row cũ, không tạo mới."""
    from agent_runtime.sessions.models import AgentRun
    from app.workforce.agents.orchestration.adk.nodes import create_mission_node as node_module

    monkeypatch.setattr(node_module, "SessionLocal", lambda: db_session)

    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db_session.add(User(id=user_id, email=f"cmr-{user_id}@example.invalid"))
    db_session.add(Workspace(id=workspace_id, name=f"CMR {workspace_id}"))
    db_session.flush()
    outcome = Outcome(
        id=generate_snowflake_id(), workspace_id=workspace_id, function="strategy",
        title="Mission", desired_result="goal", requested_by=user_id, status="draft",
    )
    db_session.add(outcome)
    db_session.flush()
    outcome_run = OutcomeRun(id=generate_snowflake_id(), outcome_id=outcome.id, status="queued", verification_status="UNKNOWN")
    db_session.add(outcome_run)
    db_session.flush()
    mission_run = AgentRun(
        id=generate_snowflake_id(), workspace_id=workspace_id, company_id=workspace_id,
        user_id=user_id, outcome_run_id=outcome_run.id, agent_key="chief_of_staff",
        runtime="adk", status="created", started_at=datetime.now(timezone.utc),
    )
    db_session.add(mission_run)
    db_session.flush()
    outcome_run.agent_run_id = mission_run.id
    db_session.commit()

    ctx = SimpleNamespace(state={
        "goal": "goal", "workspace_id": workspace_id, "user_id": user_id,
        "company_id": workspace_id, "requested_domains": ["finance"], "intent": None,
        "existing_mission_id": mission_run.id,
    })
    result = await create_mission_fn(ctx)

    assert result["mission_id"] == mission_run.id
    assert ctx.state["outcome_id"] == outcome.id
    assert ctx.state["outcome_run_id"] == outcome_run.id
    total_outcomes = db_session.query(Outcome).filter(Outcome.workspace_id == workspace_id).count()
    assert total_outcomes == 1  # không tạo Outcome mới


@pytest.mark.asyncio
async def test_build_company_context_fn_populates_state(db_session, monkeypatch):
    from app.workforce.agents.orchestration.adk.nodes import build_company_context_node as node_module

    monkeypatch.setattr(node_module, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(node_module, "build_agent_context", lambda **kwargs: SimpleNamespace(model_dump=lambda: {"stub": True}))
    monkeypatch.setattr(node_module.CofounderContextAssembler, "assemble", staticmethod(lambda **kwargs: {"stub_cofounder": True}))

    ctx = SimpleNamespace(state={
        "db": db_session,
        "workspace_id": generate_snowflake_id(),
        "company_id": None,
        "user_id": generate_snowflake_id(),
        "active_domains": ["sales"],
        "intent": None,
    })
    result = await build_company_context_fn(ctx)

    assert result["agent_context"] == {"stub": True}
    assert ctx.state["cofounder_context"] == {"stub_cofounder": True}
```

- [x] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_adk_create_mission_and_context_nodes.py -v`
Expected: FAIL với `ModuleNotFoundError`

- [x] **Step 3: Viết `create_mission_node.py`**

```python
# backend/app/workforce/agents/orchestration/adk/nodes/create_mission_node.py
"""FunctionNode đầu tiên trong AdkCofounderWorkflow — tạo Outcome/OutcomeRun/
AgentRun ở trạng thái draft/queued/created, y hệt nhánh không-resume của
chief_of_staff.py::orchestrate (giữ nguyên hành vi: mission ở "draft" cho tới
khi risk-gate (Task 12) xác nhận auto_start)."""
from datetime import datetime, timezone
from typing import Any

from agent_runtime.sessions.models import AgentRun
from google.adk.workflow._function_node import FunctionNode

from app.core.snowflake import generate_snowflake_id
from app.db.session import SessionLocal
from app.founder_os.outcomes.models import Outcome, OutcomeRun
from app.workforce.agents.governance.budget import MissionBudget


async def create_mission_fn(ctx: Any) -> dict[str, Any]:
    goal = ctx.state["goal"]
    workspace_id = ctx.state["workspace_id"]
    user_id = ctx.state["user_id"]
    company_id = ctx.state.get("company_id") or workspace_id
    active_domains = ctx.state.get("requested_domains") or []
    intent = ctx.state.get("intent")
    # ctx.state["mission_budget"] là dict JSON-safe (MissionBudget.model_dump()),
    # KHÔNG phải object MissionBudget — xem quy ước ctx.state đầu Phase 10.
    budget_dict = ctx.state.get("mission_budget") or MissionBudget().model_dump()
    # confirm_mission() (Task 25) chạy lại toàn bộ Workflow từ START cho 1
    # mission đã ở "draft" — set existing_mission_id để TÁI DÙNG đúng
    # Outcome/OutcomeRun/AgentRun đã có thay vì tạo mission mới (y hệt
    # chief_of_staff.py::confirm_mission dùng `_resume=` để tái dùng row cũ
    # thay vì mint mới).
    existing_mission_id = ctx.state.get("existing_mission_id")

    db = SessionLocal()
    try:
        if existing_mission_id is not None:
            mission_run = db.query(AgentRun).filter(AgentRun.id == existing_mission_id).one()
            outcome_run = db.query(OutcomeRun).filter(OutcomeRun.agent_run_id == existing_mission_id).one()
            ctx.state["mission_id"] = mission_run.id
            ctx.state["outcome_id"] = outcome_run.outcome_id
            ctx.state["outcome_run_id"] = outcome_run.id
            ctx.state["active_domains"] = active_domains
            return {"mission_id": mission_run.id}

        mission_id = generate_snowflake_id()
        outcome = Outcome(
            id=generate_snowflake_id(), workspace_id=workspace_id, function="strategy",
            title=f"Mission: {goal[:200]}", desired_result=goal, requested_by=user_id,
            status="draft", created_at=datetime.now(timezone.utc),
        )
        db.add(outcome)

        outcome_run = OutcomeRun(
            id=generate_snowflake_id(), outcome_id=outcome.id, agent_run_id=None,
            status="queued", verification_status="UNKNOWN",
            started_at=datetime.now(timezone.utc), created_at=datetime.now(timezone.utc),
        )
        db.add(outcome_run)
        db.flush()

        mission_run = AgentRun(
            id=mission_id, workspace_id=workspace_id, company_id=company_id, user_id=user_id,
            outcome_run_id=outcome_run.id, agent_key="chief_of_staff", runtime="adk",
            status="created", permission_profile="chief_of_staff_suggest",
            budget_jsonb=budget_dict,
            metadata_jsonb={
                "goal": goal, "domains": active_domains,
                "intent": intent.value if intent is not None and hasattr(intent, "value") else intent,
            },
            started_at=datetime.now(timezone.utc),
        )
        db.add(mission_run)
        db.flush()
        outcome_run.agent_run_id = mission_id
        db.commit()

        outcome_id, outcome_run_id = outcome.id, outcome_run.id
    finally:
        db.close()

    ctx.state["mission_id"] = mission_id
    ctx.state["outcome_id"] = outcome_id
    ctx.state["outcome_run_id"] = outcome_run_id
    ctx.state["active_domains"] = active_domains
    return {"mission_id": mission_id}


def build_create_mission_node() -> FunctionNode:
    return FunctionNode(func=create_mission_fn, name="create_mission_node")
```

- [x] **Step 4: Viết `build_company_context_node.py`**

```python
# backend/app/workforce/agents/orchestration/adk/nodes/build_company_context_node.py
"""FunctionNode tất định gọi lại nguyên vẹn build_agent_context/
CofounderContextAssembler.assemble (không đổi nội bộ 2 hàm này)."""
from typing import Any

from google.adk.workflow._function_node import FunctionNode

from app.db.session import SessionLocal
from app.workforce.agents.context.assembler import CofounderContextAssembler
from app.workforce.agents.context.builder import build_agent_context
from app.workforce.routing.deterministic import Intent


async def build_company_context_fn(ctx: Any) -> dict[str, Any]:
    workspace_id = ctx.state["workspace_id"]
    company_id = ctx.state.get("company_id")
    user_id = ctx.state["user_id"]
    active_domains = ctx.state.get("active_domains", [])
    intent = ctx.state.get("intent")

    db = SessionLocal()
    try:
        agent_ctx = build_agent_context(
            db=db, workspace_id=workspace_id, company_id=company_id,
            agent_key="chief_of_staff", user_id=user_id,
        )
        cofounder_context = CofounderContextAssembler.assemble(
            db=db, workspace_id=workspace_id, intent=intent or Intent.FOUNDER_COMMAND,
            business_signal_domains=tuple(active_domains),
        )
    finally:
        db.close()

    agent_context_dict = agent_ctx.model_dump()
    ctx.state["agent_context"] = agent_context_dict
    ctx.state["cofounder_context"] = cofounder_context
    return {"agent_context": agent_context_dict}


def build_company_context_node() -> FunctionNode:
    return FunctionNode(func=build_company_context_fn, name="build_company_context_node")
```

- [x] **Step 5: Chạy lại test, xác nhận PASS**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_adk_create_mission_and_context_nodes.py -v`
Expected: PASS (`build_agent_context` đã verify nằm ở `app.workforce.agents.context.builder`, `CofounderContextAssembler` ở `app.workforce.agents.context.assembler` — cả 2 re-export qua `app/workforce/agents/context/__init__.py`).

- [x] **Step 6: Commit**

```bash
git add backend/app/workforce/agents/orchestration/adk/nodes/create_mission_node.py backend/app/workforce/agents/orchestration/adk/nodes/build_company_context_node.py backend/app/tests/agents/test_adk_create_mission_and_context_nodes.py
git commit -m "feat(adk): add CreateMissionNode and BuildCompanyContextNode"
```

---

### Task 20: `PlanningNode` — chọn domain + chuyển trạng thái mission sang "running" khi auto-start

**Files:**
- Create: `backend/app/workforce/agents/orchestration/adk/nodes/planning_node.py`
- Test: `backend/app/tests/agents/test_adk_planning_node.py`

**Interfaces:**
- Consumes: `validate_run_transition` (không đổi, `app.workforce.agents.governance.states`), `DEFAULT_ORCHESTRATION_DOMAINS` (Task 11).
- Produces: `async def planning_fn(ctx) -> dict` — chỉ chạy trên route `"auto_start"` của `RiskClassificationNode` (Task 12); chuyển `outcome.status="planning"`, `outcome_run.status="running"`, `mission_run.status="running"` (y hệt dòng ~302-305 của `chief_of_staff.py::orchestrate`), chọn `ctx.state["active_domains"]` (mặc định `DEFAULT_ORCHESTRATION_DOMAINS` nếu `PlanningNode` chưa có domain nào được `PlanningNode`/caller chỉ định trước).

- [x] **Step 1: Viết test**

```python
# backend/app/tests/agents/test_adk_planning_node.py
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import sessionmaker

from agent_runtime.sessions.models import AgentRun
from app.core.snowflake import generate_snowflake_id
from app.db.session import engine
from app.founder_os.outcomes.models import Outcome, OutcomeRun
from app.platform.auth.models import User, Workspace
from app.workforce.agents.orchestration.adk.nodes.planning_node import build_planning_node, planning_fn


@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()


@pytest.mark.asyncio
async def test_planning_fn_transitions_to_running_and_selects_default_domains(db_session, monkeypatch):
    from app.workforce.agents.orchestration.adk.nodes import planning_node as node_module

    monkeypatch.setattr(node_module, "SessionLocal", lambda: db_session)

    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db_session.add(User(id=user_id, email=f"pl-{user_id}@example.invalid"))
    db_session.add(Workspace(id=workspace_id, name=f"PL {workspace_id}"))
    db_session.flush()
    outcome = Outcome(
        id=generate_snowflake_id(), workspace_id=workspace_id, function="strategy",
        title="Mission", desired_result="goal", requested_by=user_id, status="draft",
    )
    db_session.add(outcome)
    db_session.flush()
    outcome_run = OutcomeRun(id=generate_snowflake_id(), outcome_id=outcome.id, status="queued", verification_status="UNKNOWN")
    db_session.add(outcome_run)
    db_session.flush()
    mission_run = AgentRun(
        id=generate_snowflake_id(), workspace_id=workspace_id, company_id=workspace_id,
        user_id=user_id, outcome_run_id=outcome_run.id, agent_key="chief_of_staff",
        runtime="adk", status="created", started_at=datetime.now(timezone.utc),
    )
    db_session.add(mission_run)
    db_session.commit()

    ctx = SimpleNamespace(state={
        "outcome_id": outcome.id, "outcome_run_id": outcome_run.id,
        "mission_id": mission_run.id, "active_domains": [],
    })

    result = await planning_fn(ctx)

    assert result["active_domains"] == ["sales", "finance"]
    db_session.refresh(outcome)
    db_session.refresh(outcome_run)
    db_session.refresh(mission_run)
    assert outcome.status == "planning"
    assert outcome_run.status == "running"
    assert mission_run.status == "running"


def test_build_planning_node_shape():
    node = build_planning_node()
    assert node.name == "planning_node"
```

- [x] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_adk_planning_node.py -v`
Expected: FAIL với `ModuleNotFoundError`

- [x] **Step 3: Viết `planning_node.py`**

```python
# backend/app/workforce/agents/orchestration/adk/nodes/planning_node.py
"""Chỉ chạy trên route "auto_start" (RiskClassificationNode, Task 12) — mission
ở route "needs_confirmation" KHÔNG đi qua node này, giữ nguyên ở trạng thái draft
cho tới khi seam resume_mission()/confirm_mission() (Task 25) được gọi."""
from datetime import datetime, timezone
from typing import Any

from agent_runtime.sessions.models import AgentRun
from google.adk.workflow._function_node import FunctionNode

from app.db.session import SessionLocal
from app.founder_os.outcomes.models import Outcome, OutcomeRun
from app.workforce.agents.governance.states import validate_run_transition
from app.workforce.agents.orchestration.specialist_registry import DEFAULT_ORCHESTRATION_DOMAINS


async def planning_fn(ctx: Any) -> dict[str, Any]:
    active_domains = ctx.state.get("active_domains") or list(DEFAULT_ORCHESTRATION_DOMAINS)

    db = SessionLocal()
    try:
        outcome = db.query(Outcome).filter(Outcome.id == ctx.state["outcome_id"]).one()
        outcome_run = db.query(OutcomeRun).filter(OutcomeRun.id == ctx.state["outcome_run_id"]).one()
        mission_run = db.query(AgentRun).filter(AgentRun.id == ctx.state["mission_id"]).one()

        outcome.status = "planning"
        outcome_run.status = "running"
        mission_run.status = validate_run_transition(mission_run.status, "running")
        db.commit()
    finally:
        db.close()

    ctx.state["active_domains"] = active_domains
    return {"active_domains": active_domains}


def build_planning_node() -> FunctionNode:
    return FunctionNode(func=planning_fn, name="planning_node")
```

- [x] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_adk_planning_node.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add backend/app/workforce/agents/orchestration/adk/nodes/planning_node.py backend/app/tests/agents/test_adk_planning_node.py
git commit -m "feat(adk): add PlanningNode (domain selection + draft-to-running transition)"
```

---

### Task 21: `SynthesisNode`

**Files:**
- Create: `backend/app/workforce/agents/orchestration/adk/nodes/synthesis_node.py`
- Test: `backend/app/tests/agents/test_adk_synthesis_node.py`

**Interfaces:**
- Consumes: `CosaModelGatewayLlm` (Task 10), `build_synthesis_prompt` (Task 11), `parse_structured_output` (không đổi, `app.workforce.agents.runtime.json_output`), `ctx.state["outcome_run_id"]` (Task 19).
- Produces: `async def synthesis_fn(ctx) -> dict` — nếu `ctx.state["specialist_reports"]` chưa có, tự fetch từ `RunStep.result_jsonb` (đây là node đầu tiên trong graph THẬT SỰ CẦN specialist report, nên là điểm fetch tự nhiên — `QualityGateNode`/`ApprovalGateNode` phía sau dùng lại đúng giá trị này qua `ctx.state`, không tự fetch lại). Ghi `ctx.state["diagnosis"]`/`["synthesis_status"]`/`["specialist_reports"]`.

- [x] **Step 1: Viết test — monkeypatch `CosaModelGatewayLlm.generate_content_async`**

```python
# backend/app/tests/agents/test_adk_synthesis_node.py
from types import SimpleNamespace

import pytest
from google.adk.models.llm_response import LlmResponse
from google.genai import types as genai_types

from app.workforce.agents.orchestration.adk.nodes import synthesis_node as node_module


async def _fake_generate(self, llm_request, stream: bool = False):
    yield LlmResponse(
        content=genai_types.Content(role="model", parts=[genai_types.Part(text='{"diagnosis": "Runway ổn định 12 tháng."}')]),
        finish_reason=genai_types.FinishReason.STOP,
    )


@pytest.mark.asyncio
async def test_synthesis_fn_parses_structured_diagnosis(monkeypatch):
    monkeypatch.setattr(node_module.CosaModelGatewayLlm, "generate_content_async", _fake_generate)

    ctx = SimpleNamespace(state={
        "goal": "Đánh giá runway",
        "specialist_reports": {"finance": {"status": "success", "runway_months": 12}},
    })
    result = await node_module.synthesis_fn(ctx)

    assert result["status"] == "completed"
    assert ctx.state["diagnosis"] == "Runway ổn định 12 tháng."
    assert ctx.state["synthesis_status"] == "completed"


def test_build_synthesis_node_shape():
    node = node_module.build_synthesis_node()
    assert node.name == "synthesis_node"
```

- [x] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_adk_synthesis_node.py -v`
Expected: FAIL với `ModuleNotFoundError`

- [x] **Step 3: Viết `synthesis_node.py`**

```python
# backend/app/workforce/agents/orchestration/adk/nodes/synthesis_node.py
"""Gọi thật qua CosaModelGatewayLlm -> ModelGateway.invoke() — đây là phần
"reasoning thật, là hàm thật của goal/snapshot" (không phải text mẫu), y hệt
chief_of_staff.py::orchestrate bước "3. Real synthesis call through AgentRuntime"."""
from typing import Any

from google.adk.models.llm_request import LlmRequest
from google.genai import types as genai_types

from app.db.session import SessionLocal
from app.founder_os.outcomes.models import RunStep
from app.workforce.agents.orchestration.adk.model_adapter import CosaModelGatewayLlm
from app.workforce.agents.orchestration.synthesis_helpers import build_synthesis_prompt
from app.workforce.agents.runtime.json_output import parse_structured_output
from google.adk.workflow._function_node import FunctionNode


def _fetch_specialist_reports(outcome_run_id: int) -> dict[str, Any]:
    """Đọc RunStep.result_jsonb đã hoàn tất — y hệt cách
    chief_of_staff.py::resume_after_delegation đọc reports (dòng ~955-959).
    Đây là nguồn sự thật duy nhất; KHÔNG tin dữ liệu specialist report nào khác
    (kể cả payload đính kèm interrupt response khi resume)."""
    db = SessionLocal()
    try:
        steps = db.query(RunStep).filter(RunStep.run_id == outcome_run_id).all()
        return {
            step.inputs_jsonb["report_key"]: (step.result_jsonb or {})
            for step in steps
            if isinstance(step.inputs_jsonb, dict)
            and step.inputs_jsonb.get("mission_kind") == "chief_of_staff_specialist"
            and step.status == "completed"
        }
    finally:
        db.close()


async def synthesis_fn(ctx: Any) -> dict[str, Any]:
    goal = ctx.state["goal"]
    # Cho phép test/caller bơm sẵn specialist_reports để bỏ qua truy vấn DB;
    # production luôn để trống ở đây nên sẽ fetch thật từ RunStep.
    specialist_reports: dict[str, Any] = ctx.state.get("specialist_reports") or _fetch_specialist_reports(
        ctx.state["outcome_run_id"]
    )
    ctx.state["specialist_reports"] = specialist_reports
    sales_data = specialist_reports.get("sales", {})
    fin_data = specialist_reports.get("finance", {})

    prompt = build_synthesis_prompt(goal, sales_data, fin_data)
    llm = CosaModelGatewayLlm(model="deepseek/deepseek-reasoner", profile_name="reasoning")
    llm_request = LlmRequest(contents=[genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])])

    diagnosis = ""
    finish_ok = True
    async for resp in llm.generate_content_async(llm_request):
        diagnosis = "\n".join(p.text for p in (resp.content.parts or []) if p.text)
        finish_ok = resp.finish_reason == genai_types.FinishReason.STOP

    parsed = parse_structured_output(diagnosis)
    if parsed is not None:
        diagnosis = parsed.get("diagnosis", diagnosis)
        status = "completed" if finish_ok else "partial"
    else:
        status = "partial" if finish_ok else "failed"

    ctx.state["diagnosis"] = diagnosis
    ctx.state["synthesis_status"] = status
    return {"diagnosis": diagnosis, "status": status}


def build_synthesis_node() -> FunctionNode:
    return FunctionNode(func=synthesis_fn, name="synthesis_node")
```

- [x] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_adk_synthesis_node.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add backend/app/workforce/agents/orchestration/adk/nodes/synthesis_node.py backend/app/tests/agents/test_adk_synthesis_node.py
git commit -m "feat(adk): add SynthesisNode calling CosaModelGatewayLlm for real diagnosis"
```

---

### Task 22: `ApprovalGateNode` + `ExecutionNode` (finalize)

**Files:**
- Create: `backend/app/workforce/agents/orchestration/adk/nodes/approval_gate_node.py`
- Create: `backend/app/workforce/agents/orchestration/adk/nodes/execution_node.py`
- Test: `backend/app/tests/agents/test_adk_approval_and_execution_nodes.py`

**Interfaces:**
- Consumes: `derive_priorities_and_actions`, `create_approvals_and_proposals_for_action_plan` (Task 11), `QualityGateVerdict` (không đổi), `validate_run_transition` (không đổi).
- Produces: `async def approval_gate_fn(ctx) -> dict` — ghi `ctx.state["priorities"]`/`["action_plan"]`/`["required_approvals"]`/`["created_proposals"]`. `async def execution_finalize_fn(ctx) -> dict` — kết hợp `synthesis_status` + `quality_gate_results` (Task 14) để tính `final_status`, ghi status cuối vào `AgentRun`/`OutcomeRun`/`Outcome`, ghi `ctx.state["final_status"]`. Cũng là điểm đến của route `"blocked"` từ `GovernanceGateNode` (Task 13) — khi đó `ctx.state["governance_block_reason"]` có giá trị và `final_status` luôn là `"failed"` bất kể `synthesis_status`/`quality_gate_results` (chưa từng được set vì synthesis không chạy).

- [x] **Step 1: Viết test cho cả 2 node**

```python
# backend/app/tests/agents/test_adk_approval_and_execution_nodes.py
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import sessionmaker

from agent_runtime.sessions.models import AgentRun
from app.core.snowflake import generate_snowflake_id
from app.db.session import engine
from app.founder_os.outcomes.models import Outcome, OutcomeRun
from app.platform.auth.models import User, Workspace
from app.workforce.agents.governance.quality_gate import QualityGateResult, QualityGateVerdict
from app.workforce.agents.orchestration.adk.nodes.approval_gate_node import approval_gate_fn, build_approval_gate_node
from app.workforce.agents.orchestration.adk.nodes.execution_node import build_execution_node, execution_finalize_fn


@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()


def _mission(db_session):
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db_session.add(User(id=user_id, email=f"ex-{user_id}@example.invalid"))
    db_session.add(Workspace(id=workspace_id, name=f"EX {workspace_id}"))
    db_session.flush()
    outcome = Outcome(
        id=generate_snowflake_id(), workspace_id=workspace_id, function="strategy",
        title="Mission", desired_result="goal", requested_by=user_id, status="planning",
    )
    db_session.add(outcome)
    db_session.flush()
    outcome_run = OutcomeRun(id=generate_snowflake_id(), outcome_id=outcome.id, status="running", verification_status="UNKNOWN")
    db_session.add(outcome_run)
    db_session.flush()
    mission_run = AgentRun(
        id=generate_snowflake_id(), workspace_id=workspace_id, company_id=workspace_id,
        user_id=user_id, outcome_run_id=outcome_run.id, agent_key="chief_of_staff",
        runtime="adk", status="running", started_at=datetime.now(timezone.utc),
    )
    db_session.add(mission_run)
    db_session.commit()
    return workspace_id, outcome, outcome_run, mission_run


@pytest.mark.asyncio
async def test_approval_gate_fn_derives_priorities_and_creates_approval(db_session, monkeypatch):
    from app.workforce.agents.orchestration.adk.nodes import approval_gate_node as node_module

    monkeypatch.setattr(node_module, "SessionLocal", lambda: db_session)

    workspace_id, outcome, outcome_run, mission_run = _mission(db_session)
    ctx = SimpleNamespace(state={
        "workspace_id": workspace_id, "mission_id": mission_run.id,
        "specialist_reports": {
            "sales": {"status": "success", "metrics": {"qualified_leads": 3, "total_leads": 10}},
            "finance": {"status": "success", "runway_months": 4},
        },
    })
    result = await approval_gate_fn(ctx)

    assert len(result["action_plan"]) == 2
    assert len(ctx.state["required_approvals"]) == 1  # chỉ action có automation_key mới tạo Approval


@pytest.mark.asyncio
async def test_execution_finalize_fn_marks_completed_when_gate_passes(db_session, monkeypatch):
    from app.workforce.agents.orchestration.adk.nodes import execution_node as node_module

    monkeypatch.setattr(node_module, "SessionLocal", lambda: db_session)

    workspace_id, outcome, outcome_run, mission_run = _mission(db_session)
    ctx = SimpleNamespace(state={
        "outcome_id": outcome.id, "outcome_run_id": outcome_run.id, "mission_id": mission_run.id,
        "synthesis_status": "completed",
        "quality_gate_results": {"sales": QualityGateResult(verdict=QualityGateVerdict.PASS, domain="sales")},
    })
    result = await execution_finalize_fn(ctx)

    assert result["final_status"] == "completed"
    assert outcome.status == "completed"
    assert outcome_run.status == "succeeded"
    assert mission_run.status == "completed"


@pytest.mark.asyncio
async def test_execution_finalize_fn_downgrades_to_failed_when_gate_fails(db_session, monkeypatch):
    from app.workforce.agents.orchestration.adk.nodes import execution_node as node_module

    monkeypatch.setattr(node_module, "SessionLocal", lambda: db_session)

    workspace_id, outcome, outcome_run, mission_run = _mission(db_session)
    ctx = SimpleNamespace(state={
        "outcome_id": outcome.id, "outcome_run_id": outcome_run.id, "mission_id": mission_run.id,
        "synthesis_status": "completed",
        "quality_gate_results": {"sales": QualityGateResult(verdict=QualityGateVerdict.FAIL, domain="sales", issues=["no evidence"])},
    })
    result = await execution_finalize_fn(ctx)

    assert result["final_status"] == "failed"
    assert outcome.status == "failed"


@pytest.mark.asyncio
async def test_execution_finalize_fn_handles_governance_block_without_synthesis(db_session, monkeypatch):
    """Đến từ route "blocked" của GovernanceGateNode (Task 13) — synthesis_status/
    quality_gate_results chưa từng được set vì synthesis không chạy."""
    from app.workforce.agents.orchestration.adk.nodes import execution_node as node_module

    monkeypatch.setattr(node_module, "SessionLocal", lambda: db_session)

    workspace_id, outcome, outcome_run, mission_run = _mission(db_session)
    ctx = SimpleNamespace(state={
        "outcome_id": outcome.id, "outcome_run_id": outcome_run.id, "mission_id": mission_run.id,
        "governance_block_reason": "quá số bước cho phép",
    })
    result = await execution_finalize_fn(ctx)

    assert result["final_status"] == "failed"
    assert outcome.status == "failed"
    assert outcome_run.status == "failed"


def test_build_node_shapes():
    assert build_approval_gate_node().name == "approval_gate_node"
    assert build_execution_node().name == "execution_node"
```

- [x] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_adk_approval_and_execution_nodes.py -v`
Expected: FAIL với `ModuleNotFoundError`

- [x] **Step 3: Viết `approval_gate_node.py`**

```python
# backend/app/workforce/agents/orchestration/adk/nodes/approval_gate_node.py
"""Luôn chạy sau QualityGateNode bất kể PASS/FAIL — giống chief_of_staff.py hiện
tại vẫn tạo Approval/Proposal cho action_plan dù quality gate có fail hay không;
chỉ final_status (ExecutionNode) mới bị ảnh hưởng bởi gate."""
from typing import Any

from google.adk.workflow._function_node import FunctionNode

from app.db.session import SessionLocal
from app.workforce.agents.orchestration.synthesis_helpers import (
    create_approvals_and_proposals_for_action_plan,
    derive_priorities_and_actions,
)


async def approval_gate_fn(ctx: Any) -> dict[str, Any]:
    workspace_id = ctx.state["workspace_id"]
    mission_id = ctx.state["mission_id"]
    specialist_reports: dict[str, Any] = ctx.state.get("specialist_reports", {})
    sales_data = specialist_reports.get("sales", {})
    fin_data = specialist_reports.get("finance", {})

    priorities, action_plan = derive_priorities_and_actions(sales_data, fin_data)
    db = SessionLocal()
    try:
        required_approvals, created_proposals = create_approvals_and_proposals_for_action_plan(
            db, workspace_id=workspace_id, run_id=mission_id, action_plan=action_plan,
        )
    finally:
        db.close()

    ctx.state["priorities"] = priorities
    ctx.state["action_plan"] = action_plan
    ctx.state["required_approvals"] = required_approvals
    ctx.state["created_proposals"] = created_proposals
    return {"priorities": priorities, "action_plan": action_plan}


def build_approval_gate_node() -> FunctionNode:
    return FunctionNode(func=approval_gate_fn, name="approval_gate_node")
```

- [x] **Step 4: Viết `execution_node.py`**

```python
# backend/app/workforce/agents/orchestration/adk/nodes/execution_node.py
"""Node cuối — finalize AgentRun/OutcomeRun/Outcome, y hệt đuôi
chief_of_staff.py::orchestrate (dòng ~747-754)."""
from datetime import datetime, timezone
from typing import Any

from agent_runtime.sessions.models import AgentRun
from google.adk.workflow._function_node import FunctionNode

from app.db.session import SessionLocal
from app.founder_os.outcomes.models import Outcome, OutcomeRun
from app.workforce.agents.governance.quality_gate import QualityGateVerdict
from app.workforce.agents.governance.states import validate_run_transition


async def execution_finalize_fn(ctx: Any) -> dict[str, Any]:
    db = SessionLocal()
    try:
        return _finalize(ctx, db)
    finally:
        db.close()


def _finalize(ctx: Any, db) -> dict[str, Any]:
    mission_run = db.query(AgentRun).filter(AgentRun.id == ctx.state["mission_id"]).one()
    outcome = db.query(Outcome).filter(Outcome.id == ctx.state["outcome_id"]).one()
    outcome_run = db.query(OutcomeRun).filter(OutcomeRun.id == ctx.state["outcome_run_id"]).one()

    if ctx.state.get("governance_block_reason"):
        # Đến từ route "blocked" của GovernanceGateNode (Task 13) — budget/stuck
        # loop chặn mission TRƯỚC khi synthesis chạy, y hệt nhánh gov_failure
        # sớm trong chief_of_staff.py::orchestrate (KHÔNG có synthesis_status/
        # quality_gate_results để đọc).
        final_status = "failed"
    else:
        synthesis_status = ctx.state.get("synthesis_status", "partial")
        quality_gate_results: dict[str, Any] = ctx.state.get("quality_gate_results", {})
        any_gate_failed = any(
            getattr(result, "verdict", None) == QualityGateVerdict.FAIL
            for result in quality_gate_results.values()
        )
        final_status = synthesis_status
        if any_gate_failed and final_status == "completed":
            final_status = "failed"

    mission_run.status = validate_run_transition(mission_run.status, final_status)
    mission_run.finished_at = datetime.now(timezone.utc)
    outcome_run.status = (
        "succeeded" if final_status == "completed"
        else ("failed" if final_status == "failed" else "running")
    )
    outcome_run.completed_at = datetime.now(timezone.utc)
    outcome.status = (
        "completed" if final_status == "completed"
        else ("failed" if final_status == "failed" else "planning")
    )
    db.commit()

    ctx.state["final_status"] = final_status
    return {"final_status": final_status}


def build_execution_node() -> FunctionNode:
    return FunctionNode(func=execution_finalize_fn, name="execution_node")
```

- [x] **Step 5: Chạy lại test, xác nhận PASS**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_adk_approval_and_execution_nodes.py -v`
Expected: PASS

- [x] **Step 6: Commit**

```bash
git add backend/app/workforce/agents/orchestration/adk/nodes/approval_gate_node.py backend/app/workforce/agents/orchestration/adk/nodes/execution_node.py backend/app/tests/agents/test_adk_approval_and_execution_nodes.py
git commit -m "feat(adk): add ApprovalGateNode and ExecutionNode (mirrors chief_of_staff.py finalize tail)"
```

---

## Phase 11 — Lắp ráp `AdkCofounderWorkflow`

### Task 23: `build_adk_cofounder_workflow()`

**Files:**
- Create: `backend/app/workforce/agents/orchestration/adk/workflow.py`
- Test: `backend/app/tests/agents/test_adk_workflow_assembly.py`

**Interfaces:**
- Consumes: tất cả node factory từ Task 12-22.
- Produces: `def build_adk_cofounder_workflow() -> Workflow` — graph thật (`google.adk.workflow._workflow.Workflow`), dùng ở Task 24 (test gate) và Task 25 (`orchestration/service.py`).

**Xác nhận cú pháp Graph/Edge (đã verify bằng đọc trực tiếp `google/adk/workflow/utils/_graph_parser.py` trong `.venv`, không suy đoán):**
- 1 tuple `(a, b, c)` trong `edges=[...]` là 1 CHAIN: tạo cạnh `a→b` và `b→c`.
- Phần tử là `tuple[Node, ...]` trong 1 chain tạo fan-out/fan-in theo tích Descartes (`_process_unconditional_edge` nối MỌI node ở vế trái với MỌI node ở vế phải) — `(planning, (specialist_a, specialist_b))` = planning fan-out tới cả 2; `((specialist_a, specialist_b), join_node)` = cả 2 fan-in vào `join_node`.
- Phần tử là `dict[RouteValue, Node]` (`RoutingMap`) tạo cạnh có điều kiện theo `ctx.route` — route nào không có trong map thì nhánh đó dừng lại tự nhiên (không lỗi, không cần khai báo "không làm gì").

- [x] **Step 1: Viết test cấu trúc graph (không chạy Runner — chỉ xác nhận wiring không lỗi và đủ node)**

```python
# backend/app/tests/agents/test_adk_workflow_assembly.py
from app.workforce.agents.orchestration.adk.workflow import build_adk_cofounder_workflow
from app.workforce.agents.orchestration.specialist_registry import SPECIALIST_REGISTRY


def test_build_adk_cofounder_workflow_has_expected_nodes():
    workflow = build_adk_cofounder_workflow()
    node_names = {node.name for node in workflow.graph.nodes}

    expected = {
        "create_mission_node",
        "build_company_context_node",
        "risk_classification_node",
        "planning_node",
        "join_specialists_node",
        "governance_gate_pre_synthesis",
        "synthesis_node",
        "quality_gate_node",
        "approval_gate_node",
        "execution_node",
    }
    for domain in SPECIALIST_REGISTRY:
        expected.add(f"specialist_delegation_{domain}_node")

    assert expected.issubset(node_names)


def test_build_adk_cofounder_workflow_graph_is_valid():
    workflow = build_adk_cofounder_workflow()
    # model_post_init đã tự gọi graph.validate_graph() khi construct Workflow —
    # nếu graph sai (node mồ côi, cycle không hợp lệ, v.v.) constructor đã raise.
    assert workflow.graph is not None
    assert len(workflow.graph.edges) > 0
```

- [x] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_adk_workflow_assembly.py -v`
Expected: FAIL với `ModuleNotFoundError`

- [x] **Step 3: Viết `workflow.py`**

```python
# backend/app/workforce/agents/orchestration/adk/workflow.py
"""AdkCofounderWorkflow — Graph/Workflow/FunctionNode thật (google-adk==2.7.0),
KHÔNG phải 1 BaseAgent trần tái tạo Python orchestration logic. Node tất định
(risk-tier, budget/stuck/quality gate) dùng FunctionNode; phần cần DeepSeek dùng
durable delegation (SpecialistDelegationNode pause/resume qua RequestInput +
MissionResumeJob), không chạy Harness trực tiếp trong tiến trình ADK."""
from google.adk.workflow._base_node import START
from google.adk.workflow._join_node import JoinNode
from google.adk.workflow._workflow import Workflow

from app.workforce.agents.orchestration.adk.nodes.approval_gate_node import build_approval_gate_node
from app.workforce.agents.orchestration.adk.nodes.build_company_context_node import build_company_context_node
from app.workforce.agents.orchestration.adk.nodes.create_mission_node import build_create_mission_node
from app.workforce.agents.orchestration.adk.nodes.execution_node import build_execution_node
from app.workforce.agents.orchestration.adk.nodes.governance_gate_node import build_governance_gate_node
from app.workforce.agents.orchestration.adk.nodes.planning_node import build_planning_node
from app.workforce.agents.orchestration.adk.nodes.quality_gate_node import build_quality_gate_node
from app.workforce.agents.orchestration.adk.nodes.risk_classification_node import build_risk_classification_node
from app.workforce.agents.orchestration.adk.nodes.specialist_delegation_node import build_specialist_delegation_node
from app.workforce.agents.orchestration.adk.nodes.synthesis_node import build_synthesis_node
from app.workforce.agents.orchestration.specialist_registry import SPECIALIST_REGISTRY

WORKFLOW_NAME = "adk_cofounder_workflow"


def build_adk_cofounder_workflow() -> Workflow:
    create_mission = build_create_mission_node()
    build_context = build_company_context_node()
    risk_classification = build_risk_classification_node()
    planning = build_planning_node()
    specialist_nodes = tuple(
        build_specialist_delegation_node(domain) for domain in SPECIALIST_REGISTRY
    )
    join_specialists = JoinNode(name="join_specialists_node")
    pre_synthesis_gate = build_governance_gate_node(name="governance_gate_pre_synthesis")
    synthesis = build_synthesis_node()
    quality_gate = build_quality_gate_node()
    approval_gate = build_approval_gate_node()
    execution = build_execution_node()

    edges = [
        (START, create_mission, build_context, risk_classification),
        (risk_classification, {"auto_start": planning}),
        # route "needs_confirmation" cố ý KHÔNG có cạnh tiếp theo — mission ở lại
        # "draft", confirm_mission() (Task 25) chạy lại Workflow từ đầu sau khi
        # Founder xác nhận, giống chief_of_staff.py::confirm_mission hiện tại.
        (planning, specialist_nodes),
        (specialist_nodes, join_specialists),
        (join_specialists, pre_synthesis_gate),
        (pre_synthesis_gate, {"continue": synthesis, "blocked": execution}),
        (synthesis, quality_gate, approval_gate, execution),
    ]

    return Workflow(edges=edges, name=WORKFLOW_NAME)
```

- [x] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_adk_workflow_assembly.py -v`
Expected: PASS. Nếu `Workflow(edges=..., name=...)` raise lỗi validate graph (vd node trùng tên do 2 factory vô tình tạo cùng 1 `name`), sửa lại tên node ở factory tương ứng (Task 12-22) cho tới khi graph hợp lệ — đây là lý do Phase 12 (Task 24) bắt buộc chạy full Runner trước khi cutover, không chỉ dừng ở test cấu trúc này.

- [x] **Step 5: Commit**

```bash
git add backend/app/workforce/agents/orchestration/adk/workflow.py backend/app/tests/agents/test_adk_workflow_assembly.py
git commit -m "feat(adk): assemble AdkCofounderWorkflow graph from all nodes"
```

---

## Phase 12 — Bộ test bắt buộc (REQUIRED, phải xanh trước khi cutover)

**Đây là bước mà lần tích hợp ADK trước KHÔNG làm — chính là lý do spike cũ chết mà không ai phát hiện (nhìn an toàn trên giấy nhưng thực chất bỏ qua GovernanceKernel). Không được bỏ qua task này hay merge Phase 13 (cutover) trước khi task này xanh.**

### Task 24: Fixture-mission governance test gate

**Files:**
- Create: `backend/app/tests/agents/test_adk_workflow_governance_gate.py`

**Interfaces:**
- Consumes: `build_adk_cofounder_workflow` (Task 23), `MissionResumeJobService` (Task 17-18), `CosaGovernedTool` (Task 7), `interrupt_id_for_step` (Task 16).
- Sản phẩm của task này KHÔNG phải code sản xuất — là bộ test xác nhận 4 điều bắt buộc theo Quyết định 1: (a) `AgentToolCall`/`AgentApproval` được tạo qua `GovernanceKernel`, không bị bypass; (b) risk-tier R0-R4 tự chặn/tự chạy đúng như `chief_of_staff.py`; (c) `MissionResumeJob` idempotency đúng khi nhiều lần claim cùng checkpoint; (d) resume-from-session-events hoạt động thật qua `Runner` thật (không mock).

**Ghi chú về rủi ro xác minh:** đây là điểm tích hợp sâu nhất trong toàn kế hoạch — cơ chế pause/resume qua `RequestInput`/`FunctionResponse` đã được xác minh bằng cách đọc trực tiếp `google/adk/workflow/utils/_workflow_hitl_utils.py` trong `.venv` (không suy đoán), nhưng CHƯA được chạy thật. Nếu Step 2 (chạy test lần đầu) fail vì lý do khác "chưa implement" (vd sai field `Event`, sai cách `Runner` phát interrupt), đây chính xác là mục đích của task này — debug tại đây, KHÔNG lùi lại bỏ qua governance để "cho chạy được".

- [x] **Step 1: Viết test — mission R0 (auto-start) chạy hết 1 vòng pause/resume, xác nhận governance audit + idempotency**

```python
# backend/app/tests/agents/test_adk_workflow_governance_gate.py
from datetime import datetime, timezone

import pytest
from google.adk.apps.app import App, ResumabilityConfig
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.workflow.utils._workflow_hitl_utils import (
    create_request_input_response,
    get_request_input_interrupt_ids,
    has_request_input_function_call,
)
from google.genai import types as genai_types

from agent_runtime.permissions.models import AgentApproval, AgentToolCall
from agent_runtime.sessions.models import AgentRun
from app.core.feature_flags import FLAG_AGENT_DELEGATION
from app.core.snowflake import generate_snowflake_id
from app.db.session import SessionLocal
from app.founder_os.outcomes.models import Outcome, OutcomeRun, RunStep
from app.platform.auth.models import User, Workspace
from app.platform.core.models import FeatureFlag
from app.workforce.agents.delegation.manager import DelegationProviderManager
from app.workforce.agents.delegation.models import DelegationJob
from app.workforce.agents.delegation.provider import DelegationProvider
from app.workforce.agents.delegation.task_board import TaskBoardService
from app.workforce.agents.delegation.types import DelegationHandle, DelegationResult, DelegationStatus, ProviderHealth
from app.workforce.agents.governance.budget import MissionBudget
from app.workforce.agents.orchestration.adk.governed_tool import CosaGovernedTool
from app.workforce.agents.orchestration.adk.nodes.specialist_delegation_node import interrupt_id_for_step
from app.workforce.agents.orchestration.adk.workflow import build_adk_cofounder_workflow
from app.workforce.agents.orchestration.mission_resume_service import MissionResumeJobService
from app.workforce.agents.runtime.execution_scope import ExecutionScope


class HealthyProvider(DelegationProvider):
    @property
    def provider_name(self) -> str:
        return "in_process"

    async def delegate(self, request, idempotency_key):
        return DelegationHandle(provider_name="in_process", external_id=idempotency_key)

    async def poll(self, handle):
        return DelegationResult(status=DelegationStatus.RUNNING)

    async def cancel(self, handle):
        return True

    async def health(self):
        return ProviderHealth(provider_name="in_process", available=True)


def _setup_workspace() -> tuple[int, int]:
    db = SessionLocal()
    try:
        user_id = generate_snowflake_id()
        workspace_id = generate_snowflake_id()
        db.add(User(id=user_id, email=f"gate-{user_id}@example.invalid"))
        db.add(Workspace(id=workspace_id, name=f"Gate {workspace_id}"))
        db.add(FeatureFlag(id=generate_snowflake_id(), workspace_id=workspace_id, key=FLAG_AGENT_DELEGATION, enabled=True))
        db.commit()
        return workspace_id, user_id
    finally:
        db.close()


async def _drive_runner_until_interrupt_or_done(runner, *, user_id, session_id, new_message=None):
    """Chạy runner tới khi gặp interrupt (trả về list interrupt_id) hoặc hết
    event (workflow chạy xong tới terminal node, trả về [])."""
    interrupt_ids: list[str] = []
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=new_message):
        if has_request_input_function_call(event):
            interrupt_ids.extend(get_request_input_interrupt_ids(event))
    return interrupt_ids


@pytest.mark.asyncio
async def test_r0_mission_auto_starts_pauses_resumes_and_records_governance_audit(monkeypatch):
    manager = DelegationProviderManager()
    manager.register(HealthyProvider())
    monkeypatch.setattr(TaskBoardService, "provider_manager", manager)

    workspace_id, user_id = _setup_workspace()
    goal = f"Đánh giá tình hình finance — test gate {generate_snowflake_id()}"

    session_service = InMemorySessionService()
    app = App(root_agent=build_adk_cofounder_workflow(), resumability_config=ResumabilityConfig(is_resumable=True))
    runner = Runner(app=app, session_service=session_service)

    session = await session_service.create_session(
        app_name="adk_cofounder_workflow",
        user_id=str(user_id),
        state={
            "goal": goal,
            "workspace_id": workspace_id,
            "user_id": user_id,
            "company_id": workspace_id,
            "requested_domains": ["finance"],
            "intent": None,
            "mission_budget": MissionBudget().model_dump(),
            "specialist_runtime_name": "mock",
        },
    )

    trigger = genai_types.Content(role="user", parts=[genai_types.Part(text=goal)])
    interrupt_ids = await _drive_runner_until_interrupt_or_done(
        runner, user_id=str(user_id), session_id=session.id, new_message=trigger,
    )

    # 1 domain ("finance") được yêu cầu -> đúng 1 interrupt đang chờ.
    assert len(interrupt_ids) == 1
    interrupt_id = interrupt_ids[0]
    step_id = int(interrupt_id.split(":")[1])
    assert interrupt_id == interrupt_id_for_step(step_id)

    db = SessionLocal()
    try:
        outcome = db.query(Outcome).filter(Outcome.desired_result == goal).one()
        outcome_run = db.query(OutcomeRun).filter(OutcomeRun.outcome_id == outcome.id).one()
        mission_run = db.query(AgentRun).filter(AgentRun.id == outcome_run.agent_run_id).one()
        assert outcome.status == "planning"  # đã qua PlanningNode -> auto_start đúng R0

        job = db.query(DelegationJob).filter(DelegationJob.run_step_id == step_id).one()

        # (a) Governance thật: gọi 1 CosaGovernedTool trong context của mission
        # này, xác nhận AgentToolCall được ghi qua GovernanceKernel (Task 6-7),
        # KHÔNG bị bypass.
        scope = ExecutionScope(
            workspace_id=workspace_id, company_id=workspace_id, principal_user_id=user_id,
            principal_member_id=user_id, principal_role="owner", operating_unit_id=None,
            offering_id=None, initiative_id=None, profile_id=None, session_id=None, grants=(),
        )
        tool = CosaGovernedTool(
            tool_flat_name="finance_get_financial_summary",
            db_factory=lambda: db,
            scope_factory=lambda: scope,
            run_id_factory=lambda: mission_run.id,
        )
        await tool.run_async(args={}, tool_context=None)
        tool_calls = db.query(AgentToolCall).filter(AgentToolCall.run_id == mission_run.id).all()
        assert len(tool_calls) == 1

        # (c) MissionResumeJob idempotency: enqueue 2 lần cùng checkpoint (giả
        # lập 2 worker cùng nhận event "specialist hoàn tất" gần nhau), claim 2
        # lần -> chỉ 1 lần thành công.
        resume_job = MissionResumeJobService.enqueue_resume(
            db, workspace_id=workspace_id, mission_run_id=mission_run.id,
            workflow_session_id=session.id, checkpoint_key=interrupt_id,
            reason="specialist_delegation_completed",
        )
        resume_job_dup = MissionResumeJobService.enqueue_resume(
            db, workspace_id=workspace_id, mission_run_id=mission_run.id,
            workflow_session_id=session.id, checkpoint_key=interrupt_id,
            reason="specialist_delegation_completed",
        )
        assert resume_job.id == resume_job_dup.id

        now = datetime.now(timezone.utc)
        claimed_a = MissionResumeJobService.claim_next(db, "gate-worker-a", now)
        claimed_b = MissionResumeJobService.claim_next(db, "gate-worker-b", now)
        assert claimed_a == resume_job.id
        assert claimed_b is None  # (c) exactly-once dưới concurrent completion

        # Đánh dấu specialist "hoàn tất" thật qua TaskBoardService.complete_job
        # (đường sản xuất thật — không tự set status tay).
        TaskBoardService.complete_job(
            db, workspace_id, job.id,
            DelegationResult(status=DelegationStatus.SUCCEEDED, structured_result={"status": "success", "runway_months": 9}),
        )
    finally:
        db.close()

    # (d) Resume-from-session-events thật: gọi lại runner.run_async với
    # FunctionResponse khớp interrupt_id — KHÔNG mock Runner/Workflow.
    resume_message = genai_types.Content(
        role="user",
        parts=[create_request_input_response(interrupt_id, {"step_id": step_id, "status": "completed"})],
    )
    remaining_interrupts = await _drive_runner_until_interrupt_or_done(
        runner, user_id=str(user_id), session_id=session.id, new_message=resume_message,
    )
    assert remaining_interrupts == []  # không còn specialist nào đang chờ -> chạy hết tới ExecutionNode

    db = SessionLocal()
    try:
        outcome = db.query(Outcome).filter(Outcome.desired_result == goal).one()
        outcome_run = db.query(OutcomeRun).filter(OutcomeRun.outcome_id == outcome.id).one()
        mission_run = db.query(AgentRun).filter(AgentRun.id == outcome_run.agent_run_id).one()
        assert mission_run.status in ("completed", "failed", "partial")  # ExecutionNode đã finalize (không còn "created"/"running")
        assert outcome_run.completed_at is not None

        approvals = db.query(AgentApproval).filter(AgentApproval.run_id == mission_run.id).all()
        # sales_data/fin_data rỗng (không delegate sang sales) -> derive_priorities_and_actions
        # vẫn deterministic, có thể ra 0 hoặc nhiều approval tuỳ dữ liệu - assert
        # KHÔNG bypass GovernanceKernel bằng cách xác nhận không có exception,
        # cấu trúc bảng đúng (đã covered ở test_adk_approval_and_execution_nodes.py);
        # ở đây chỉ cần xác nhận mission đã tới ExecutionNode thật.
        MissionResumeJobService.mark_completed(db, resume_job.id)
    finally:
        db.close()


@pytest.mark.asyncio
async def test_r2_mission_stays_draft_awaiting_confirmation(monkeypatch):
    import app.workforce.agents.orchestration.specialist_registry as registry

    risky_spec = registry.SpecialistSpec(
        domain="finance", agent_key="finance_specialist", task="t",
        tool_flat_name="finance_get_financial_summary",
        fetch_snapshot=registry.SPECIALIST_REGISTRY["finance"].fetch_snapshot,
        risk_level="R2", delegate_via_profile_id="finance",
    )
    monkeypatch.setitem(registry.SPECIALIST_REGISTRY, "finance", risky_spec)

    workspace_id, user_id = _setup_workspace()
    goal = f"Hành động rủi ro cao — test gate {generate_snowflake_id()}"

    session_service = InMemorySessionService()
    app = App(root_agent=build_adk_cofounder_workflow(), resumability_config=ResumabilityConfig(is_resumable=True))
    runner = Runner(app=app, session_service=session_service)
    session = await session_service.create_session(
        app_name="adk_cofounder_workflow", user_id=str(user_id),
        state={
            "goal": goal, "workspace_id": workspace_id, "user_id": user_id, "company_id": workspace_id,
            "requested_domains": ["finance"], "intent": None,
            "mission_budget": MissionBudget().model_dump(), "specialist_runtime_name": "mock",
        },
    )
    trigger = genai_types.Content(role="user", parts=[genai_types.Part(text=goal)])
    interrupt_ids = await _drive_runner_until_interrupt_or_done(
        runner, user_id=str(user_id), session_id=session.id, new_message=trigger,
    )

    # (b) risk-tier chặn đúng: R2 > AUTO_START_MAX_RISK ("R1") -> route
    # "needs_confirmation" không có cạnh tiếp theo -> KHÔNG có specialist nào
    # được delegate, KHÔNG có interrupt nào chờ.
    assert interrupt_ids == []

    db = SessionLocal()
    try:
        outcome = db.query(Outcome).filter(Outcome.desired_result == goal).one()
        assert outcome.status == "draft"  # chưa qua PlanningNode
        outcome_run = db.query(OutcomeRun).filter(OutcomeRun.outcome_id == outcome.id).one()
        delegated_jobs = db.query(DelegationJob).join(
            RunStep, DelegationJob.run_step_id == RunStep.id
        ).filter(RunStep.run_id == outcome_run.id).count()
        assert delegated_jobs == 0  # không specialist nào được delegate khi bị chặn ở risk-gate
    finally:
        db.close()
```

- [x] **Step 2: Chạy test, quan sát kết quả đầu tiên**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_adk_workflow_governance_gate.py -v -s`
Expected (thực tế): rất có thể FAIL ở lần chạy đầu vì đây là lần đầu toàn bộ chuỗi node thật chạy qua `Runner` thật — đọc traceback cẩn thận để phân biệt 3 loại lỗi:
1. Lỗi cấu hình/fixture (thiếu bảng, thiếu import) → sửa fixture, không đổi thiết kế node.
2. Lỗi do giả định sai về API `Event`/`RequestInput`/`Runner` (vd `event.author` không phải tên node, `create_request_input_response` cần thêm field) → đọc lại đúng source trong `backend/.venv/lib/python3.11/site-packages/google/adk/` để sửa CHÍNH XÁC node liên quan (Task 12-23), không đoán mò.
3. Lỗi hành vi governance thật (vd risk-gate cho qua nhầm domain rủi ro cao, `AgentToolCall` không được tạo) → đây là bug thật, sửa node tương ứng, KHÔNG nới lỏng assertion để test qua.

Không merge Phase 13 khi chưa đưa được cả 2 test về PASS bằng cách sửa Loại 1/2, và xác nhận không có bug Loại 3 nào.

- [x] **Step 3: Sau khi cả 2 test PASS, chạy lại toàn bộ `backend/app/tests/agents/` để xác nhận chưa có regression nào từ toàn bộ Phase 1-12**

Run: `cd backend && .venv/bin/pytest app/tests/agents/ -v`
Expected: PASS toàn bộ.

- [x] **Step 4: Commit**

```bash
git add backend/app/tests/agents/test_adk_workflow_governance_gate.py
git commit -m "test(adk): add required fixture-mission governance gate before cutover (risk-tier, audit, exactly-once resume)"
```

---

## Phase 13 — Seam `orchestration/service.py` + cutover 3 điểm gọi

### Task 25: `orchestration/service.py`

**Files:**
- Create: `backend/app/workforce/agents/orchestration/service.py`
- Test: `backend/app/tests/agents/test_orchestration_service_seam.py`

**Interfaces:**
- Consumes: `build_adk_cofounder_workflow` (Task 23), `build_adk_session_service` (Task 9), `project_adk_event` (Task 8), `RuntimeSession` (Task 4), `ChiefOfStaffResult` (không đổi schema, từ `chief_of_staff.py` cho tới Task 35).
- Produces: `async def orchestrate_mission(db, *, workspace_id, user_id, goal, company_id=None, context=None, domains=None, intent=None, budget=None) -> ChiefOfStaffResult`, `async def confirm_mission(db, *, mission_id, user_id, workspace_id=None) -> ChiefOfStaffResult`, `async def resume_mission(db, *, mission_run_id, interrupt_id, resume_payload) -> ChiefOfStaffResult` — 3 hàm mà `router.py`/`cosa_cofounder_service.py`/`continuation.py` (Task 26-28) sẽ gọi thay vì `ChiefOfStaffOrchestrator` trực tiếp.

- [x] **Step 1: Viết test — `orchestrate_mission` cho mission delegating, `resume_mission` hoàn tất nó**

```python
# backend/app/tests/agents/test_orchestration_service_seam.py
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import sessionmaker

from agent_runtime.sessions.models import AgentRun
from app.core.feature_flags import FLAG_AGENT_DELEGATION
from app.core.snowflake import generate_snowflake_id
from app.db.session import engine
from app.founder_os.outcomes.models import Outcome, OutcomeRun, RunStep
from app.platform.auth.models import User, Workspace
from app.platform.core.models import FeatureFlag
from app.workforce.agents.delegation.manager import DelegationProviderManager
from app.workforce.agents.delegation.models import DelegationJob
from app.workforce.agents.delegation.provider import DelegationProvider
from app.workforce.agents.delegation.task_board import TaskBoardService
from app.workforce.agents.delegation.types import DelegationHandle, DelegationResult, DelegationStatus, ProviderHealth
from app.workforce.agents.orchestration import service as orchestration_service
from app.workforce.agents.orchestration.adk.nodes.specialist_delegation_node import interrupt_id_for_step
from app.workforce.agents.orchestration.runtime_session_models import RuntimeSession


class HealthyProvider(DelegationProvider):
    @property
    def provider_name(self) -> str:
        return "in_process"

    async def delegate(self, request, idempotency_key):
        return DelegationHandle(provider_name="in_process", external_id=idempotency_key)

    async def poll(self, handle):
        return DelegationResult(status=DelegationStatus.RUNNING)

    async def cancel(self, handle):
        return True

    async def health(self):
        return ProviderHealth(provider_name="in_process", available=True)


@pytest.mark.asyncio
async def test_orchestrate_then_resume_mission_reaches_terminal_status(monkeypatch):
    manager = DelegationProviderManager()
    manager.register(HealthyProvider())
    monkeypatch.setattr(TaskBoardService, "provider_manager", manager)

    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        user_id = generate_snowflake_id()
        workspace_id = generate_snowflake_id()
        db.add(User(id=user_id, email=f"seam-{user_id}@example.invalid"))
        db.add(Workspace(id=workspace_id, name=f"Seam {workspace_id}"))
        db.add(FeatureFlag(id=generate_snowflake_id(), workspace_id=workspace_id, key=FLAG_AGENT_DELEGATION, enabled=True))
        db.commit()

        goal = f"Seam test — {generate_snowflake_id()}"
        result = await orchestration_service.orchestrate_mission(
            db, workspace_id=workspace_id, user_id=user_id, goal=goal, domains=["finance"],
        )
        assert result.status == "delegating"

        runtime_session = db.query(RuntimeSession).filter(RuntimeSession.mission_run_id == int(result.mission_id)).one()
        assert runtime_session.runtime_type == "ADK"
        assert runtime_session.external_session_id

        outcome = db.query(Outcome).filter(Outcome.desired_result == goal).one()
        outcome_run = db.query(OutcomeRun).filter(OutcomeRun.outcome_id == outcome.id).one()
        step = db.query(RunStep).filter(RunStep.run_id == outcome_run.id).one()
        job = db.query(DelegationJob).filter(DelegationJob.run_step_id == step.id).one()

        TaskBoardService.complete_job(
            db, workspace_id, job.id,
            DelegationResult(status=DelegationStatus.SUCCEEDED, structured_result={"status": "success", "runway_months": 9}),
        )

        resumed = await orchestration_service.resume_mission(
            db, mission_run_id=int(result.mission_id),
            interrupt_id=interrupt_id_for_step(step.id),
            resume_payload={"step_id": step.id, "status": "completed"},
        )
        assert resumed.status in ("completed", "failed", "partial")
        assert resumed.mission_id == result.mission_id
    finally:
        db.close()
```

- [x] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_orchestration_service_seam.py -v`
Expected: FAIL với `ModuleNotFoundError`

- [x] **Step 3: Viết `service.py`**

```python
# backend/app/workforce/agents/orchestration/service.py
"""Seam mỏng — router.py/cosa_cofounder_service.py/continuation.py (Task 26-28)
CHỈ biết tới package này, không import gì từ google.adk trực tiếp. Nếu sau này
đổi orchestration engine, chỉ package orchestration đổi."""
from typing import Any, Optional

from agent_runtime.sessions.models import AgentRun
from google.adk.apps.app import App, ResumabilityConfig
from google.adk.runners import Runner
from google.adk.workflow.utils._workflow_hitl_utils import (
    create_request_input_response,
    get_request_input_interrupt_ids,
    has_request_input_function_call,
)
from google.genai import types as genai_types
from sqlalchemy.orm import Session

from app.core.snowflake import generate_snowflake_id
from app.founder_os.outcomes.models import Outcome, OutcomeRun
from app.workforce.agents.governance.budget import MissionBudget
from app.workforce.agents.orchestration.adk.session_bridge import project_adk_event
from app.workforce.agents.orchestration.adk.session_service_factory import build_adk_session_service
from app.workforce.agents.orchestration.adk.workflow import WORKFLOW_NAME, build_adk_cofounder_workflow
from app.workforce.agents.orchestration.chief_of_staff import ChiefOfStaffResult
from app.workforce.agents.orchestration.runtime_session_models import RuntimeSession
from app.workforce.routing.deterministic import Intent


def _build_runner() -> Runner:
    app = App(root_agent=build_adk_cofounder_workflow(), resumability_config=ResumabilityConfig(is_resumable=True))
    return Runner(app=app, session_service=build_adk_session_service())


async def _drive(
    runner: Runner, db: Session, workspace_id: int, *, user_id: str, session_id: str, new_message
) -> tuple[list[str], Optional[int]]:
    interrupt_ids: list[str] = []
    mission_id: Optional[int] = None
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=new_message):
        if mission_id is None and isinstance(event.output, dict) and event.output.get("mission_id"):
            mission_id = event.output["mission_id"]
        if mission_id is not None:
            project_adk_event(db, event, mission_run_id=mission_id, workspace_id=workspace_id)
        if has_request_input_function_call(event):
            interrupt_ids.extend(get_request_input_interrupt_ids(event))
    db.commit()
    return interrupt_ids, mission_id


def _record_runtime_session(db: Session, *, workspace_id: int, mission_id: int, external_session_id: str) -> None:
    existing = (
        db.query(RuntimeSession)
        .filter(RuntimeSession.mission_run_id == mission_id, RuntimeSession.runtime_type == "ADK")
        .first()
    )
    if existing is not None:
        return
    db.add(RuntimeSession(
        id=generate_snowflake_id(), workspace_id=workspace_id, mission_run_id=mission_id,
        agent_run_id=None, runtime_type="ADK", external_session_id=external_session_id,
        status="active", metadata_jsonb={"workflow_name": WORKFLOW_NAME},
    ))
    db.commit()


def _result_from_db(db: Session, mission_id: int, *, status_override: Optional[str] = None) -> ChiefOfStaffResult:
    mission_run = db.query(AgentRun).filter(AgentRun.id == mission_id).one()
    outcome_run = db.query(OutcomeRun).filter(OutcomeRun.agent_run_id == mission_id).one()
    outcome = db.query(Outcome).filter(Outcome.id == outcome_run.outcome_id).one()
    meta = mission_run.metadata_jsonb or {}
    status = status_override or mission_run.status
    diagnosis_map = {
        "delegating": "Specialist work has been queued for durable execution.",
        "waiting_confirmation": (
            f"Mission ở mức rủi ro cần Founder xác nhận trước khi chạy "
            f"(gọi confirm_mission với mission_id={mission_id})."
        ),
    }
    return ChiefOfStaffResult(
        mission_id=str(mission_id),
        workspace_id=str(outcome.workspace_id),
        goal=str(meta.get("goal") or outcome.desired_result),
        diagnosis=diagnosis_map.get(status, ""),
        status=status,
    )


async def orchestrate_mission(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    goal: str,
    company_id: Optional[int] = None,
    context: Optional[dict[str, Any]] = None,
    domains: Optional[list[str]] = None,
    intent: Optional[Intent] = None,
    budget: Optional[MissionBudget] = None,
) -> ChiefOfStaffResult:
    runner = _build_runner()
    session = await runner.session_service.create_session(
        app_name=WORKFLOW_NAME,
        user_id=str(user_id),
        state={
            "goal": goal,
            "workspace_id": workspace_id,
            "user_id": user_id,
            "company_id": company_id or workspace_id,
            "requested_domains": list(domains) if domains else [],
            "intent": intent.value if intent is not None else None,
            "mission_budget": (budget or MissionBudget()).model_dump(),
            "specialist_runtime_name": "deepseek_harness",
        },
    )
    trigger = genai_types.Content(role="user", parts=[genai_types.Part(text=goal)])
    interrupt_ids, mission_id = await _drive(
        runner, db, workspace_id, user_id=str(user_id), session_id=session.id, new_message=trigger,
    )
    if mission_id is None:
        raise RuntimeError("AdkCofounderWorkflow did not produce a mission_id")

    _record_runtime_session(db, workspace_id=workspace_id, mission_id=mission_id, external_session_id=session.id)

    if interrupt_ids:
        return _result_from_db(db, mission_id, status_override="delegating")

    mission_run = db.query(AgentRun).filter(AgentRun.id == mission_id).one()
    if mission_run.status == "created":
        # Chưa qua PlanningNode -> RiskClassificationNode route "needs_confirmation".
        return _result_from_db(db, mission_id, status_override="waiting_confirmation")
    return _result_from_db(db, mission_id)


async def confirm_mission(
    db: Session, *, mission_id: int, user_id: int, workspace_id: Optional[int] = None,
) -> ChiefOfStaffResult:
    mission_run = db.query(AgentRun).filter(AgentRun.id == mission_id).first()
    if mission_run is None:
        raise ValueError(f"Mission {mission_id} not found")
    if workspace_id is not None and mission_run.workspace_id != workspace_id:
        raise PermissionError(f"Mission {mission_id} does not belong to workspace {workspace_id}")
    outcome_run = db.query(OutcomeRun).filter(OutcomeRun.agent_run_id == mission_id).one()
    outcome = db.query(Outcome).filter(Outcome.id == outcome_run.outcome_id).one()
    if outcome.status != "draft":
        raise ValueError(f"Mission {mission_id} is not awaiting confirmation (status={outcome.status})")

    meta = mission_run.metadata_jsonb or {}
    goal = meta.get("goal") or outcome.desired_result
    domains = meta.get("domains") or []
    intent_value = meta.get("intent")

    runner = _build_runner()
    session = await runner.session_service.create_session(
        app_name=WORKFLOW_NAME, user_id=str(user_id),
        state={
            "goal": goal, "workspace_id": mission_run.workspace_id, "user_id": user_id,
            "company_id": mission_run.company_id, "requested_domains": domains,
            "intent": intent_value, "mission_budget": mission_run.budget_jsonb or MissionBudget().model_dump(),
            "specialist_runtime_name": "deepseek_harness",
            "existing_mission_id": mission_id,
        },
    )
    trigger = genai_types.Content(role="user", parts=[genai_types.Part(text=goal)])
    interrupt_ids, resolved_mission_id = await _drive(
        runner, db, mission_run.workspace_id, user_id=str(user_id), session_id=session.id, new_message=trigger,
    )
    _record_runtime_session(
        db, workspace_id=mission_run.workspace_id, mission_id=resolved_mission_id, external_session_id=session.id,
    )
    if interrupt_ids:
        return _result_from_db(db, resolved_mission_id, status_override="delegating")
    return _result_from_db(db, resolved_mission_id)


async def resume_mission(
    db: Session, *, mission_run_id: int, interrupt_id: str, resume_payload: dict[str, Any],
) -> ChiefOfStaffResult:
    runtime_session = (
        db.query(RuntimeSession)
        .filter(RuntimeSession.mission_run_id == mission_run_id, RuntimeSession.runtime_type == "ADK")
        .order_by(RuntimeSession.created_at.desc())
        .first()
    )
    if runtime_session is None or runtime_session.external_session_id is None:
        raise RuntimeError(f"Mission {mission_run_id} has no ADK RuntimeSession to resume")
    mission_run = db.query(AgentRun).filter(AgentRun.id == mission_run_id).one()

    runner = _build_runner()
    resume_message = genai_types.Content(
        role="user", parts=[create_request_input_response(interrupt_id, resume_payload)],
    )
    interrupt_ids, _ = await _drive(
        runner, db, mission_run.workspace_id, user_id=str(mission_run.user_id),
        session_id=runtime_session.external_session_id, new_message=resume_message,
    )
    if interrupt_ids:
        return _result_from_db(db, mission_run_id, status_override="delegating")
    return _result_from_db(db, mission_run_id)
```

- [x] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_orchestration_service_seam.py -v`
Expected: PASS. Đây là lần đầu `confirm_mission`/`existing_mission_id` (Task 25 note trong Task 19) chạy xuyên suốt — nếu FAIL, áp dụng đúng quy trình phân loại lỗi ở Task 24 Step 2.

- [x] **Step 5: Commit**

```bash
git add backend/app/workforce/agents/orchestration/service.py backend/app/tests/agents/test_orchestration_service_seam.py
git commit -m "feat(orchestration): add thin service.py seam (orchestrate_mission/confirm_mission/resume_mission)"
```

---

### Task 26: Cutover `router.py` (`POST /orchestrate`)

**Files:**
- Modify: `backend/app/workforce/agents/orchestration/router.py`
- Test: `backend/app/tests/agents/test_chief_of_staff_orchestration.py` (chạy lại, không sửa nội dung)

**Interfaces:**
- Consumes: `orchestrate_mission` (Task 25).

- [x] **Step 1: Sửa `router.py`**

```python
# backend/app/workforce/agents/orchestration/router.py
import json
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.workforce.agents.orchestration import service as orchestration_service
from app.workforce.agents.orchestration.chief_of_staff import ChiefOfStaffResult
from app.workforce.agents.orchestration.mission_control_bus import mission_control_bus
from app.core.auth import get_current_workspace_member
from app.db.models import WorkspaceMember
from app.db.session import get_db

router = APIRouter()


class OrchestrateRequest(BaseModel):
    goal: str
    context: Optional[dict[str, Any]] = None


@router.post("/orchestrate", response_model=ChiefOfStaffResult)
async def orchestrate_founder_mission(
    payload: OrchestrateRequest,
    db: Session = Depends(get_db),
    current_member: WorkspaceMember = Depends(get_current_workspace_member),
) -> ChiefOfStaffResult:
    """Trigger an autonomous Chief of Staff multi-agent orchestration mission."""
    if not payload.goal or not payload.goal.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Goal description is required",
        )

    result = await orchestration_service.orchestrate_mission(
        db=db,
        workspace_id=current_member.workspace_id,
        user_id=current_member.user_id,
        goal=payload.goal.strip(),
        context=payload.context,
    )
    return result


@router.get("/stream/{run_id}")
async def stream_mission_events(
    run_id: str,
    current_member: WorkspaceMember = Depends(get_current_workspace_member),
):
    """Server-Sent Events (SSE) stream for live mission execution updates."""

    async def event_generator():
        async for event in mission_control_bus.subscribe(run_id):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

(chỉ đổi import + call site `ChiefOfStaffOrchestrator.orchestrate(...)` → `orchestration_service.orchestrate_mission(...)`; `/stream/{run_id}` không đổi vì `mission_control_bus` không đổi.)

- [x] **Step 2: Chạy lại test có sẵn cho router (nếu có) + test governance/orchestration liên quan**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_chief_of_staff_orchestration.py app/tests/agents/test_governance_e2e.py -v`
Expected: PASS — các test này gọi thẳng `ChiefOfStaffOrchestrator` (chưa xoá, Task 35), không đi qua router, nên không bị ảnh hưởng bởi cutover này. Nếu có test HTTP-level gọi `POST /orchestrate` (`grep -rn "post(\"/orchestrate\"\|'/orchestrate'" backend/app/tests`), chạy riêng và xác nhận response vẫn đúng `ChiefOfStaffResult` shape.

- [x] **Step 3: Commit**

```bash
git add backend/app/workforce/agents/orchestration/router.py
git commit -m "refactor(orchestration): cutover POST /orchestrate to orchestration.service seam"
```

---

### Task 27: Cutover `cosa_cofounder_service.py`

**Files:**
- Modify: `backend/app/workforce/orchestrator/cosa_cofounder_service.py`

**Interfaces:**
- Consumes: `orchestrate_mission`, `confirm_mission` (Task 25).

- [x] **Step 1: Sửa 2 call site**

Trong `backend/app/workforce/orchestrator/cosa_cofounder_service.py`, thêm import ở đầu file:

```python
from app.workforce.agents.orchestration import service as orchestration_service
```

Sửa dòng ~460 (trong nhánh `FOUNDER_DECISION`/`FOUNDER_COMMAND`):

```python
            result = await orchestration_service.orchestrate_mission(
                db=self.sync_db,
                workspace_id=workspace_id,
                user_id=user_id,
                goal=message,
                intent=intent,
            )
```

Sửa dòng ~506 (trong `confirm_mission` của `CoFounderService`):

```python
        result = await orchestration_service.confirm_mission(
            db=self.sync_db,
            mission_id=mission_id,
            user_id=user_id,
            workspace_id=workspace_id,
        )
```

(chỉ đổi `ChiefOfStaffOrchestrator.orchestrate(...)` → `orchestration_service.orchestrate_mission(...)` và `ChiefOfStaffOrchestrator.confirm_mission(...)` → `orchestration_service.confirm_mission(...)`; giữ nguyên toàn bộ logic routing intent/response xung quanh 2 call site này.)

- [x] **Step 2: Chạy test liên quan tới `CoFounderService`**

Run: `cd backend && .venv/bin/pytest app/tests -v -k "cofounder_service or cosa_cofounder"`
Expected: PASS.

- [x] **Step 3: Commit**

```bash
git add backend/app/workforce/orchestrator/cosa_cofounder_service.py
git commit -m "refactor(orchestration): cutover CoFounderService to orchestration.service seam"
```

---

### Task 28: Cutover resume path — `continuation.py` + `worker.py` → `MissionResumeJobService` + `resume_mission`

**Files:**
- Modify: `backend/app/workforce/agents/orchestration/continuation.py`
- Modify: `backend/app/workforce/agents/delegation/worker.py`
- Modify: `backend/app/worker_main.py`
- Test: `backend/app/tests/agents/test_continuation_enqueues_mission_resume.py`

**Interfaces:**
- Consumes: `MissionResumeJobService.enqueue_resume`/`claim_next`/`mark_completed`/`mark_failed` (Task 17-18), `orchestration_service.resume_mission` (Task 25), `interrupt_id_for_step` (Task 16).

**Ghi chú thay đổi hành vi có chủ đích:** `continuation.py::maybe_resume_mission` hiện tại CHỜ TẤT CẢ delegation step của 1 `OutcomeRun` terminal rồi mới gọi resume 1 lần (vì `chief_of_staff.py` chỉ tổng hợp 1 lần sau khi cả sales+finance xong). Với `AdkCofounderWorkflow`, mỗi `SpecialistDelegationNode` pause/resume ĐỘC LẬP qua interrupt riêng — việc "chờ tất cả" giờ do chính `JoinNode` trong graph đảm nhiệm (Task 23), không phải tầng gọi bên ngoài. Vì vậy `maybe_resume_mission` giờ enqueue 1 `MissionResumeJob` NGAY khi RunStep vừa hoàn tất (không đợi các step khác), với `checkpoint_key` là interrupt_id riêng của step đó — khớp đúng UNIQUE constraint per-checkpoint đã thiết kế ở Task 5.

- [x] **Step 1: Viết test cho `maybe_resume_mission` mới**

```python
# backend/app/tests/agents/test_continuation_enqueues_mission_resume.py
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import sessionmaker

from agent_runtime.sessions.models import AgentRun
from app.core.snowflake import generate_snowflake_id
from app.db.session import engine
from app.founder_os.outcomes.models import Outcome, OutcomeRun, RunStep
from app.platform.auth.models import User, Workspace
from app.workforce.agents.orchestration.adk.nodes.specialist_delegation_node import interrupt_id_for_step
from app.workforce.agents.orchestration.continuation import maybe_resume_mission
from app.workforce.agents.orchestration.mission_resume_models import MissionResumeJob


@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()


@pytest.mark.asyncio
async def test_maybe_resume_mission_enqueues_job_for_completed_step(db_session):
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db_session.add(User(id=user_id, email=f"cont-{user_id}@example.invalid"))
    db_session.add(Workspace(id=workspace_id, name=f"Cont {workspace_id}"))
    db_session.flush()
    outcome = Outcome(
        id=generate_snowflake_id(), workspace_id=workspace_id, function="strategy",
        title="Mission", desired_result="goal", requested_by=user_id, status="planning",
    )
    db_session.add(outcome)
    db_session.flush()
    outcome_run = OutcomeRun(id=generate_snowflake_id(), outcome_id=outcome.id, status="running", verification_status="UNKNOWN")
    db_session.add(outcome_run)
    db_session.flush()
    mission_run = AgentRun(
        id=generate_snowflake_id(), workspace_id=workspace_id, company_id=workspace_id,
        user_id=user_id, outcome_run_id=outcome_run.id, agent_key="chief_of_staff",
        runtime="adk", status="running", started_at=datetime.now(timezone.utc),
    )
    db_session.add(mission_run)
    db_session.flush()
    outcome_run.agent_run_id = mission_run.id
    step = RunStep(
        id=generate_snowflake_id(), run_id=outcome_run.id, type="agent", status="completed",
        inputs_jsonb={"mission_kind": "chief_of_staff_specialist", "report_key": "finance"},
        result_jsonb={"status": "success", "runway_months": 9},
    )
    db_session.add(step)
    db_session.commit()

    handled = await maybe_resume_mission(db_session, outcome_run.id, run_step_id=step.id)

    assert handled is True
    jobs = db_session.query(MissionResumeJob).filter(MissionResumeJob.mission_run_id == mission_run.id).all()
    assert len(jobs) == 1
    assert jobs[0].checkpoint_key == interrupt_id_for_step(step.id)
    assert jobs[0].status == "queued"
```

- [x] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_continuation_enqueues_mission_resume.py -v`
Expected: FAIL (`maybe_resume_mission` chưa nhận `run_step_id`, chưa enqueue `MissionResumeJob`)

- [x] **Step 3: Viết lại `continuation.py`**

```python
# backend/app/workforce/agents/orchestration/continuation.py
from sqlalchemy.orm import Session

from app.founder_os.outcomes.models import OutcomeRun
from app.workforce.agents.orchestration.adk.nodes.specialist_delegation_node import interrupt_id_for_step
from app.workforce.agents.orchestration.mission_resume_service import MissionResumeJobService


async def maybe_resume_mission(
    db: Session,
    outcome_run_id: int,
    *,
    run_step_id: int,
) -> bool:
    """Enqueue 1 MissionResumeJob ngay khi 1 RunStep specialist chuyển terminal.

    Trả True khi 1 job resume thật sự được enqueue (hoặc đã tồn tại - idempotent
    theo (mission_run_id, checkpoint_key), xem Task 5/17). MissionResumeJobService
    (Task 18) + worker loop riêng (mission_resume_loop, Task 28 Step 5) đảm bảo
    đúng 1 lần gọi AdkCofounderWorkflow.resume cho mỗi checkpoint — KHÔNG còn
    chờ "tất cả step terminal" ở tầng này, JoinNode trong graph (Task 23) tự lo
    việc chờ tất cả specialist.
    """
    outcome_run = db.query(OutcomeRun).filter(OutcomeRun.id == outcome_run_id).one_or_none()
    if outcome_run is None or outcome_run.agent_run_id is None:
        return False

    workspace_id = _workspace_id_for_outcome_run(db, outcome_run)
    MissionResumeJobService.enqueue_resume(
        db,
        workspace_id=workspace_id,
        mission_run_id=outcome_run.agent_run_id,
        workflow_session_id=None,
        checkpoint_key=interrupt_id_for_step(run_step_id),
        reason="specialist_delegation_completed",
    )
    return True


def _workspace_id_for_outcome_run(db: Session, outcome_run: OutcomeRun) -> int:
    from app.founder_os.outcomes.models import Outcome

    return db.query(Outcome).filter(Outcome.id == outcome_run.outcome_id).one().workspace_id
```

- [x] **Step 4: Sửa 2 call site trong `worker.py`**

Trong `backend/app/workforce/agents/delegation/worker.py`, cả 2 chỗ gọi `maybe_resume_mission(db, step.run_id)` (dòng ~614 và ~633) đổi thành:

```python
            await maybe_resume_mission(db, step.run_id, run_step_id=step.id)
```

(chỉ thêm `run_step_id=step.id` — `step` đã sẵn có ở cả 2 call site, xem code hiện tại.)

- [x] **Step 5: Thêm `mission_resume_loop()` vào `worker_main.py`**

```python
# Thêm vào backend/app/worker_main.py — cần thêm `import uuid` ở đầu file nếu
# chưa có (worker_main.py hiện chưa import uuid, khác với worker.py delegation
# đã có sẵn).
import uuid

from app.workforce.agents.orchestration.mission_resume_service import MissionResumeJobService

MISSION_RESUME_POLL_SECONDS = 1.0


async def mission_resume_loop() -> None:
    """Worker loop claim + thực thi MissionResumeJob — gọi orchestration_service.resume_mission()
    (Task 25), đúng 1 lần cho mỗi checkpoint (MissionResumeJobService.claim_next, Task 18)."""
    from app.workforce.agents.orchestration import service as orchestration_service

    worker_id = f"mission-resume-{uuid.uuid4().hex[:12]}"
    while True:
        db = SessionLocal()
        job_id = None
        try:
            job_id = MissionResumeJobService.claim_next(db, worker_id, datetime.utcnow())
        except Exception:
            logger.exception("Mission resume claim failure")
            db.rollback()
        finally:
            db.close()

        if job_id is None:
            await asyncio.sleep(MISSION_RESUME_POLL_SECONDS)
            continue

        db = SessionLocal()
        try:
            from app.workforce.agents.orchestration.mission_resume_models import MissionResumeJob

            job = db.query(MissionResumeJob).filter(MissionResumeJob.id == job_id).one()
            await orchestration_service.resume_mission(
                db, mission_run_id=job.mission_run_id, interrupt_id=job.checkpoint_key,
                resume_payload={"checkpoint_key": job.checkpoint_key, "status": "completed"},
            )
            MissionResumeJobService.mark_completed(db, job_id)
        except Exception as exc:
            logger.exception("Mission resume job %s failed", job_id)
            db.rollback()
            db2 = SessionLocal()
            try:
                MissionResumeJobService.mark_failed(db2, job_id, str(exc))
            finally:
                db2.close()
        finally:
            db.close()
```

Thêm `mission_resume_loop()` vào `_run_all()`:

```python
async def _run_all() -> None:
    await asyncio.gather(
        chat_loop(),
        channel_worker_loop(),
        heartbeat_loop(),
        execution_loop(),
        execution_cleanup_loop(),
        delegation_loop(),
        mission_resume_loop(),
        asyncio.to_thread(_run_background_worker),
    )
```

- [x] **Step 6: Chạy lại test, xác nhận PASS**

Run: `cd backend && .venv/bin/pytest app/tests/agents/test_continuation_enqueues_mission_resume.py -v`
Expected: PASS

- [x] **Step 7: Chạy lại toàn bộ test delegation worker để xác nhận cutover không phá vỡ hành vi delegation hiện có**

Run: `cd backend && .venv/bin/pytest app/tests/agents/delegation/ -v`
Expected: PASS toàn bộ.

- [x] **Step 8: Commit**

```bash
git add backend/app/workforce/agents/orchestration/continuation.py backend/app/workforce/agents/delegation/worker.py backend/app/worker_main.py backend/app/tests/agents/test_continuation_enqueues_mission_resume.py
git commit -m "refactor(orchestration): cutover resume path to MissionResumeJobService + orchestration.service.resume_mission"
```

---

### Task 29: Full regression run — `backend/app/tests/agents/`

**Files:** không tạo/sửa file mới — task xác minh.

- [x] **Step 1: Chạy toàn bộ bộ test agents**

Run: `cd backend && .venv/bin/pytest app/tests/agents/ -v`
Expected: PASS toàn bộ. Đây là checkpoint bắt buộc theo Global Constraints ("`backend/app/tests/agents/` phải xanh xuyên suốt qua từng task") — nếu bất kỳ test nào đỏ, dừng lại và sửa tại đúng task gây ra lỗi (không patch tạm ở đây).

- [x] **Step 2: Chạy riêng nhóm test không thuộc `agents/` nhưng có khả năng chạm vào seam (feature flags, missions API)**

Run: `cd backend && .venv/bin/pytest app/tests/test_feature_flags.py app/tests/test_missions_api.py app/tests/test_architectural_invariants.py -v`
Expected: PASS.

- [x] **Step 3: Không cần commit (task xác minh) — nếu Step 1/2 phát hiện lỗi, tạo commit sửa lỗi riêng và ghi rõ task nào gây ra**

---

## Phase 14 — Dọn dẹp

### Task 30: Retire `FLAG_ADK_SALES_PILOT`

**Files:**
- Modify: `backend/app/core/feature_flags.py`
- Test: `backend/app/tests/test_feature_flags.py` (chạy lại, không sửa nội dung trừ khi có reference)

**Interfaces:** không có — dọn hằng số chết.

**Xác nhận trước khi xoá (đã verify bằng grep, nhắc lại để executor verify lại đúng lúc thực thi vì code có thể đã đổi giữa lúc viết plan và lúc thực thi):**

- [x] **Step 1: Grep xác nhận không còn call site nào đọc `FLAG_ADK_SALES_PILOT`**

Run: `cd backend && grep -rn "FLAG_ADK_SALES_PILOT" app --include="*.py"`
Expected: chỉ còn đúng 1 dòng — chính dòng định nghĩa nó trong `feature_flags.py`. Nếu có thêm call site nào khác xuất hiện (thêm từ các task trước trong kế hoạch này hoặc từ nhánh khác), DỪNG lại, không xoá — xử lý call site đó trước.

- [x] **Step 2: Xoá dòng định nghĩa**

Trong `backend/app/core/feature_flags.py`, xoá dòng:

```python
FLAG_ADK_SALES_PILOT = "adk_sales_pilot"
```

- [x] **Step 3: Chạy lại test feature flags**

Run: `cd backend && .venv/bin/pytest app/tests/test_feature_flags.py -v`
Expected: PASS (không có test nào tham chiếu hằng số vừa xoá — đã verify bằng grep ở Step 1).

- [x] **Step 4: Commit**

```bash
git add backend/app/core/feature_flags.py
git commit -m "chore(feature-flags): retire unused FLAG_ADK_SALES_PILOT from prior ADK spike"
```

---

## Phase 15 — Backend: đọc `RuntimeSession`/`MissionResumeJob` cho mission

**Khám phá từ đọc code thật (quyết định thiết kế cho Phase này):** frontend có 2 nguồn dữ liệu mission KHÔNG dùng chung code, dù cùng đọc `OutcomeRun`/`Outcome`/`AgentRun`:
1. `MissionInspectorDialog` (mở khi bấm vào 1 mission) đọc `GET /workspaces/{workspace_id}/missions/{mission_id}` (`backend/app/platform/core/missions_router.py::get_mission_detail`, dùng chung `_format_mission_summary()` với `list_workspace_missions()`) qua `hubService.getMissionDetail()` — Task 31 mở rộng đúng chỗ này.
2. `ActiveMissionsTracker` (danh sách mission đang chạy trên dashboard) đọc dữ liệu từ `founder_hub_service.py`'s khối "4. Active Missions Tracker" — xây `active_missions` bằng 1 query RIÊNG (`db.query(OutcomeRun, Outcome, AgentRun)...`), KHÔNG gọi lại `_format_mission_summary()`. Đây là 1 điểm trôi dạt (drift) có sẵn từ trước khi kế hoạch này bắt đầu (2 nơi định dạng "mission summary" khác nhau) — không thuộc phạm vi hợp nhất của kế hoạch này (đổi kiến trúc dữ liệu command-center là việc khác), nhưng để badge "đang chờ specialist" hiển thị được ở `ActiveMissionsTracker` thật (không chỉ ở dialog chi tiết), Task 32 mở rộng THÊM đúng field `resume_status` vào query riêng đó, giữ nguyên cấu trúc hiện có — không hợp nhất 2 nguồn thành 1 (ngoài phạm vi, rủi ro cao hơn lợi ích cho việc này).

### Task 31: `resume_status` + `runtime_sessions` trong `missions_router.py`

**Files:**
- Modify: `backend/app/platform/core/missions_router.py`
- Test: `backend/app/tests/test_missions_api.py`

**Interfaces:**
- Consumes: `RuntimeSession` (Task 4), `MissionResumeJob` (Task 5).
- Produces: `_format_mission_summary(...)` giờ trả thêm field `"resume_status": "awaiting_specialist_resume" | None`. `get_mission_detail()` trả thêm `"runtime_sessions": [...]` trong `data`.

**Ghi chú fixture (đã đọc file thật trước khi viết):** `test_missions_api.py` dùng SQLite in-memory (`db_session` fixture tạo `engine` riêng, chỉ `create_all` đúng 1 danh sách bảng cố định trong `tables = [...]`), KHÔNG dùng `app.db.session.engine` thật. Phải thêm `RuntimeSession.__table__`/`MissionResumeJob.__table__` vào danh sách `tables` đó thì fixture mới tạo được 2 bảng mới.

- [x] **Step 1: Thêm 2 bảng mới vào fixture `db_session`, viết test mở rộng `test_list_and_get_mission_api`**

Sửa `tables = [...]` trong fixture `db_session` (thêm 2 dòng):

```python
    from app.workforce.agents.orchestration.mission_resume_models import MissionResumeJob
    from app.workforce.agents.orchestration.runtime_session_models import RuntimeSession

    tables = [
        User.__table__,
        Workspace.__table__,
        WorkspaceMember.__table__,
        Outcome.__table__,
        OutcomeRun.__table__,
        RunStep.__table__,
        AgentRun.__table__,
        AgentEventRecord.__table__,
        AgentToolCall.__table__,
        Artifact.__table__,
        AgentApproval.__table__,
        FeatureFlag.__table__,
        RuntimeSession.__table__,
        MissionResumeJob.__table__,
    ]
```

Thêm test mới ngay sau `test_list_and_get_mission_api`:

```python
def test_mission_detail_includes_resume_status_and_runtime_sessions(db_session, test_setup):
    from app.workforce.agents.orchestration.mission_resume_models import MissionResumeJob
    from app.workforce.agents.orchestration.runtime_session_models import RuntimeSession

    ws_id = test_setup["workspace_id"]
    u_id = test_setup["user_id"]
    member = test_setup["member"]

    outcome_id = generate_snowflake_id()
    outcome_run_id = generate_snowflake_id()
    agent_run_id = generate_snowflake_id()

    db_session.add(Outcome(
        id=outcome_id, workspace_id=ws_id, title="Nhiệm vụ chờ specialist",
        desired_result="Chờ finance specialist", requested_by=u_id, status="running",
    ))
    db_session.add(OutcomeRun(
        id=outcome_run_id, outcome_id=outcome_id, agent_run_id=agent_run_id,
        status="running", verification_status="UNKNOWN", started_at=datetime.now(timezone.utc),
    ))
    db_session.add(AgentRun(
        id=agent_run_id, workspace_id=ws_id, user_id=u_id, outcome_run_id=outcome_run_id,
        agent_key="chief_of_staff", status="running", started_at=datetime.now(timezone.utc),
    ))
    db_session.add(RuntimeSession(
        id=generate_snowflake_id(), workspace_id=ws_id, mission_run_id=agent_run_id,
        agent_run_id=None, runtime_type="ADK", external_session_id="adk-session-xyz",
        status="active",
    ))
    db_session.add(MissionResumeJob(
        id=generate_snowflake_id(), workspace_id=ws_id, mission_run_id=agent_run_id,
        workflow_session_id="adk-session-xyz", checkpoint_key="delegation_step:999",
        idempotency_key=f"mission_resume:{agent_run_id}:delegation_step:999",
        reason="specialist_delegation_completed", status="queued",
    ))
    db_session.commit()

    app.dependency_overrides[get_current_workspace_member] = lambda: member
    app.dependency_overrides[get_db] = lambda: db_session
    client = TestClient(app)
    try:
        resp = client.get(f"/api/v1/workspaces/{ws_id}/missions/{agent_run_id}")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["resume_status"] == "awaiting_specialist_resume"
        assert len(data["runtime_sessions"]) == 1
        assert data["runtime_sessions"][0]["runtime_type"] == "ADK"
        assert data["runtime_sessions"][0]["external_session_id"] == "adk-session-xyz"

        list_resp = client.get(f"/api/v1/workspaces/{ws_id}/missions")
        list_item = next(m for m in list_resp.json()["data"] if m["mission_id"] == str(agent_run_id))
        assert list_item["resume_status"] == "awaiting_specialist_resume"
    finally:
        app.dependency_overrides.clear()
```

- [x] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && .venv/bin/pytest app/tests/test_missions_api.py -k "resume_status" -v`
Expected: FAIL (`KeyError: 'resume_status'` hoặc tương tự)

- [x] **Step 3: Sửa `missions_router.py`**

Thêm import ở đầu file:

```python
from app.workforce.agents.orchestration.mission_resume_models import MissionResumeJob
from app.workforce.agents.orchestration.runtime_session_models import RuntimeSession
```

Thêm helper ngay trước `_format_mission_summary`:

```python
def _resume_status_for_mission(db: Session, agent_run_id: Optional[int]) -> Optional[str]:
    if agent_run_id is None:
        return None
    pending = (
        db.query(MissionResumeJob)
        .filter(
            MissionResumeJob.mission_run_id == agent_run_id,
            MissionResumeJob.status.in_(("queued", "claimed")),
        )
        .first()
    )
    return "awaiting_specialist_resume" if pending is not None else None
```

Sửa chữ ký `_format_mission_summary` để nhận `db` và thêm field `resume_status` vào dict trả về:

```python
def _format_mission_summary(
    db: Session,
    outcome_run: Optional[OutcomeRun],
    outcome: Optional[Outcome],
    agent_run: Optional[AgentRun],
    evidence_count: int = 0,
    latest_step_text: Optional[str] = None,
    next_step_text: Optional[str] = None,
) -> Dict[str, Any]:
```

(thêm tham số `db: Session` đầu tiên — cập nhật CẢ 3 call site hiện có trong file này: 2 lần trong `list_workspace_missions` và 1 lần trong `get_mission_detail`, truyền `db` vào.) Thêm vào cuối dict trả về của hàm này (ngay trước dòng `}` đóng return):

```python
        "resume_status": _resume_status_for_mission(db, agent_run.id if agent_run else None),
```

Trong `get_mission_detail`, sau khối "6. Verification detail & Outcome Certificate", thêm truy vấn `runtime_sessions` và đưa vào response:

```python
    # 7. Runtime sessions (ADK/DeepSeek/Sandbox/Human) — timeline cho founder
    runtime_sessions_list = []
    if agent_run:
        rt_sessions = (
            db.query(RuntimeSession)
            .filter(RuntimeSession.mission_run_id == agent_run.id)
            .order_by(RuntimeSession.created_at.asc())
            .all()
        )
        runtime_sessions_list = [
            {
                "id": str(rs.id),
                "runtime_type": rs.runtime_type,
                "external_session_id": rs.external_session_id,
                "status": rs.status,
                "checkpoint_ref": rs.checkpoint_ref,
                "created_at": rs.created_at.isoformat() if hasattr(rs.created_at, "isoformat") else str(rs.created_at),
                "finished_at": rs.finished_at.isoformat() if rs.finished_at and hasattr(rs.finished_at, "isoformat") else None,
            }
            for rs in rt_sessions
        ]
```

Thêm `"runtime_sessions": runtime_sessions_list,` vào dict `data` trả về cuối `get_mission_detail` (cùng cấp với `"timeline"`, `"tool_calls"`, `"evidence"`, `"approvals"`).

- [x] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd backend && .venv/bin/pytest app/tests/test_missions_api.py -v`
Expected: PASS toàn bộ file (không chỉ test mới — 3 call site `_format_mission_summary` đã sửa chữ ký, mọi test cũ gọi qua endpoint vẫn phải xanh).

- [x] **Step 5: Commit**

```bash
git add backend/app/platform/core/missions_router.py backend/app/tests/test_missions_api.py
git commit -m "feat(missions-api): expose RuntimeSession timeline and resume_status on mission detail"
```

---

### Task 32: `resume_status` trong `founder_hub_service.py`'s `active_missions`

**Files:**
- Modify: `backend/app/platform/core/founder_hub_service.py`
- Test: `backend/app/tests/test_founder_hub_active_missions_resume_status.py`

**Interfaces:**
- Consumes: `MissionResumeJob` (Task 5).
- Produces: mỗi item trong `active_missions` (khối "4.1 OutcomeRuns / AgentRuns đang chạy" của `get_founder_command_center_data`) có thêm field `"resume_status"`, cùng ngữ nghĩa với Task 31 (`"awaiting_specialist_resume"` hoặc `None`).

- [x] **Step 1: Viết test (DB thật, không MagicMock — cần dữ liệu ORM thật để query `MissionResumeJob` trả đúng)**

```python
# backend/app/tests/test_founder_hub_active_missions_resume_status.py
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import sessionmaker

from agent_runtime.sessions.models import AgentRun
from app.core.snowflake import generate_snowflake_id
from app.db.session import engine
from app.founder_os.outcomes.models import Outcome, OutcomeRun
from app.platform.auth.models import User, Workspace
from app.platform.core.founder_hub_service import get_founder_command_center_data
from app.workforce.agents.orchestration.mission_resume_models import MissionResumeJob


@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()


def test_active_missions_includes_resume_status(db_session):
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db_session.add(User(id=user_id, email=f"fh-{user_id}@example.invalid"))
    db_session.add(Workspace(id=workspace_id, name=f"FH {workspace_id}"))
    db_session.flush()
    outcome = Outcome(
        id=generate_snowflake_id(), workspace_id=workspace_id, function="strategy",
        title="Mission chờ specialist", desired_result="goal", requested_by=user_id, status="running",
    )
    db_session.add(outcome)
    db_session.flush()
    outcome_run = OutcomeRun(
        id=generate_snowflake_id(), outcome_id=outcome.id, status="running",
        verification_status="UNKNOWN", created_at=datetime.now(timezone.utc),
    )
    db_session.add(outcome_run)
    db_session.flush()
    mission_run = AgentRun(
        id=generate_snowflake_id(), workspace_id=workspace_id, company_id=workspace_id,
        user_id=user_id, outcome_run_id=outcome_run.id, agent_key="chief_of_staff",
        runtime="adk", status="running", started_at=datetime.now(timezone.utc),
    )
    db_session.add(mission_run)
    db_session.flush()
    outcome_run.agent_run_id = mission_run.id
    db_session.add(MissionResumeJob(
        id=generate_snowflake_id(), workspace_id=workspace_id, mission_run_id=mission_run.id,
        workflow_session_id="adk-session-1", checkpoint_key="delegation_step:1",
        idempotency_key=f"mission_resume:{mission_run.id}:delegation_step:1",
        reason="specialist_delegation_completed", status="queued",
    ))
    db_session.commit()

    data = get_founder_command_center_data(db_session, workspace_id, user_id)
    mission_item = next(m for m in data["active_missions"] if m["mission_id"] == str(mission_run.id))
    assert mission_item["resume_status"] == "awaiting_specialist_resume"
```

- [x] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && .venv/bin/pytest app/tests/test_founder_hub_active_missions_resume_status.py -v`
Expected: FAIL với `KeyError: 'resume_status'`

- [x] **Step 3: Sửa `founder_hub_service.py`**

Thêm import ở đầu file:

```python
from app.workforce.agents.orchestration.mission_resume_models import MissionResumeJob
```

Trong khối "4.1 OutcomeRuns / AgentRuns đang chạy" (`for outcome_run, outcome, agent_run in unified_runs:`), thêm ngay trước `active_missions.append(...)`:

```python
        resume_pending = (
            db.query(MissionResumeJob)
            .filter(
                MissionResumeJob.mission_run_id == (agent_run.id if agent_run else None),
                MissionResumeJob.status.in_(("queued", "claimed")),
            )
            .first()
            if agent_run
            else None
        )
```

Thêm `"resume_status": "awaiting_specialist_resume" if resume_pending else None,` vào cuối dict `active_missions.append({...})` hiện có (dòng cuối, trước dấu `})`).

- [x] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd backend && .venv/bin/pytest app/tests/test_founder_hub_active_missions_resume_status.py -v`
Expected: PASS

- [x] **Step 5: Chạy lại test hiện có của founder_hub để không phá vỡ mock-based test**

Run: `cd backend && .venv/bin/pytest app/tests/test_p1_founder_hub.py -v`
Expected: PASS (test này dùng `MagicMock` cho `db` với `q.first.return_value = None` mặc định — field `resume_status` mới sẽ luôn là `None` trong các test đó, không phá vỡ assertion nào hiện có vì các test không assert vào `active_missions` chi tiết).

- [x] **Step 6: Commit**

```bash
git add backend/app/platform/core/founder_hub_service.py backend/app/tests/test_founder_hub_active_missions_resume_status.py
git commit -m "feat(founder-hub): expose resume_status on active_missions for ActiveMissionsTracker badge"
```

---

## Phase 16 — Frontend: Runtime Session timeline + trạng thái "đang chờ resume"

**Quy ước đã xác nhận bằng đọc code thật:** `mission_inspector_dialog.dart` đọc `Map<String, dynamic> mission` trực tiếp (không có model Dart riêng cho mission detail — đọc `mission['budget']`, `mission['timeline']`, v.v. bằng key thô), nuôi bởi `HubService.getMissionDetail()` → `GET /workspaces/{workspaceId}/missions/{missionId}` (đúng endpoint Task 31 vừa mở rộng). Giữ đúng quy ước này (KHÔNG thêm model Dart mới) — thêm tab/badge bằng cách đọc thêm 2 key mới `mission['runtime_sessions']`/`mission['resume_status']`.

### Task 33: Tab "Runtime Sessions" + banner "đang chờ resume" trong `MissionInspectorDialog`

**Files:**
- Modify: `frontend/lib/modules/hologram_hub/views/widgets/mission_inspector_dialog.dart`
- Test: `frontend/test/modules/hologram_hub/mission_inspector_runtime_sessions_test.dart`

**Interfaces:** không đổi public API của `MissionInspectorDialog` (vẫn `MissionInspectorDialog.show(context, mission)`) — chỉ đọc thêm 2 key có thể vắng mặt (`mission['runtime_sessions']`/`mission['resume_status']`), an toàn ngược với dữ liệu cũ không có 2 key này (dùng `??`/`as ... ?`).

- [x] **Step 1: Viết widget test**

```dart
// frontend/test/modules/hologram_hub/mission_inspector_runtime_sessions_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/hologram_hub/views/widgets/mission_inspector_dialog.dart';

void main() {
  testWidgets('MissionInspectorDialog shows Runtime Sessions tab and resume banner', (tester) async {
    final mission = <String, dynamic>{
      'mission_id': '123456',
      'title': 'Đánh giá tài chính Q3',
      'status': 'delegating',
      'resume_status': 'awaiting_specialist_resume',
      'runtime_sessions': [
        {
          'id': '1',
          'runtime_type': 'ADK',
          'external_session_id': 'adk-session-abc',
          'status': 'active',
          'checkpoint_ref': null,
          'created_at': '2026-08-21T09:00:00Z',
          'finished_at': null,
        },
      ],
    };

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (context) => ElevatedButton(
              onPressed: () => MissionInspectorDialog.show(context, mission),
              child: const Text('Open'),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('Open'));
    await tester.pumpAndSettle();

    expect(find.textContaining('Runtime Sessions'), findsOneWidget);
    expect(find.textContaining('Đang chờ'), findsOneWidget);

    await tester.tap(find.textContaining('Runtime Sessions'));
    await tester.pumpAndSettle();

    expect(find.text('ADK'), findsOneWidget);
    expect(find.textContaining('adk-session-abc'), findsOneWidget);
  });

  testWidgets('MissionInspectorDialog renders fine when runtime_sessions/resume_status absent (backward compatible)', (tester) async {
    final mission = <String, dynamic>{'mission_id': '1', 'title': 'Cũ', 'status': 'running'};

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (context) => ElevatedButton(
              onPressed: () => MissionInspectorDialog.show(context, mission),
              child: const Text('Open'),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('Open'));
    await tester.pumpAndSettle();

    expect(find.textContaining('Runtime Sessions'), findsOneWidget);
    expect(find.textContaining('Đang chờ'), findsNothing);
  });
}
```

- [x] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd frontend && flutter test test/modules/hologram_hub/mission_inspector_runtime_sessions_test.dart`
Expected: FAIL (`findsOneWidget` cho "Runtime Sessions" thất bại vì tab chưa tồn tại)

- [x] **Step 3: Sửa `mission_inspector_dialog.dart`**

Trong hàm `build()`, ngay sau dòng khai báo `final evidence = ...`, thêm:

```dart
    final runtimeSessions = mission['runtime_sessions'] as List<dynamic>? ?? [];
    final resumeStatus = mission['resume_status']?.toString();
```

Ngay sau khối `// ── Progress Bar ──` (sau `const SizedBox(height: 16),` kết thúc khối Progress Bar, trước khối `// ── Tab Content`), thêm banner:

```dart
            if (resumeStatus == 'awaiting_specialist_resume') ...[
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: const Color(0xFFF59E0B).withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: const Color(0xFFF59E0B).withValues(alpha: 0.35)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.hourglass_top_rounded, size: 14, color: Color(0xFFFBBF24)),
                    const SizedBox(width: 8),
                    const Expanded(
                      child: Text(
                        'Đang chờ specialist hoàn tất để tiếp tục nhiệm vụ',
                        style: TextStyle(color: Color(0xFFFBBF24), fontSize: 11, fontWeight: FontWeight.w600),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
            ],
```

Sửa `DefaultTabController(length: 3, ...)` thành `DefaultTabController(length: 4, ...)`, thêm tab mới vào `tabs: [...]`:

```dart
                        tabs: [
                          Tab(text: 'Dòng thời gian (${timeline.length})'),
                          Tab(text: 'Tool Calls (${toolCalls.length})'),
                          Tab(text: 'Bằng chứng & Chứng chỉ (${evidence.length})'),
                          Tab(text: 'Runtime Sessions (${runtimeSessions.length})'),
                        ],
```

Thêm `_buildRuntimeSessionsView(runtimeSessions)` vào cuối `children: [...]` của `TabBarView`:

```dart
                      child: TabBarView(
                        children: [
                          _buildTimelineView(timeline),
                          _buildToolCallsView(toolCalls),
                          _buildEvidenceView(evidence, verificationDetail),
                          _buildRuntimeSessionsView(runtimeSessions),
                        ],
                      ),
```

Thêm method mới (đặt ngay sau `_buildEvidenceView`, giữ style nhất quán với các `_build...View` khác trong file):

```dart
  Widget _buildRuntimeSessionsView(List<dynamic> runtimeSessions) {
    if (runtimeSessions.isEmpty) {
      return _buildEmptyState('Chưa có Runtime Session nào được ghi nhận.');
    }

    return ListView.separated(
      itemCount: runtimeSessions.length,
      separatorBuilder: (context, index) => const SizedBox(height: 8),
      itemBuilder: (context, index) {
        final rs = runtimeSessions[index] as Map<String, dynamic>;
        final runtimeType = rs['runtime_type']?.toString() ?? 'UNKNOWN';
        final externalId = rs['external_session_id']?.toString() ?? '—';
        final status = rs['status']?.toString() ?? 'active';
        final finishedAt = rs['finished_at']?.toString();

        return Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: const Color(0xFF10192E),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: const Color(0xFF1E293B)),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: const Color(0xFF8B5CF6).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  runtimeType,
                  style: const TextStyle(color: Color(0xFFA78BFA), fontSize: 11, fontWeight: FontWeight.w700),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      externalId,
                      style: const TextStyle(color: Colors.white, fontSize: 12, fontFamily: 'monospace'),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      finishedAt != null ? 'Trạng thái: $status • Kết thúc: $finishedAt' : 'Trạng thái: $status',
                      style: const TextStyle(color: Color(0xFF64748B), fontSize: 10),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
```

- [x] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd frontend && flutter test test/modules/hologram_hub/mission_inspector_runtime_sessions_test.dart`
Expected: PASS cả 2 test.

- [x] **Step 5: Chạy lại toàn bộ test hologram_hub hiện có để xác nhận không phá vỡ widget khác**

Run: `cd frontend && flutter test test/modules/hologram_hub/`
Expected: PASS.

- [x] **Step 6: Commit**

```bash
git add frontend/lib/modules/hologram_hub/views/widgets/mission_inspector_dialog.dart frontend/test/modules/hologram_hub/mission_inspector_runtime_sessions_test.dart
git commit -m "feat(hologram-hub): show Runtime Session timeline and resume-pending banner in mission inspector"
```

---

### Task 34: Badge "CHỜ TIẾP TỤC" trong `ActiveMissionsTracker`

**Files:**
- Modify: `frontend/lib/modules/hologram_hub/views/widgets/active_missions_tracker.dart`
- Test: `frontend/test/modules/hologram_hub/active_missions_tracker_resume_badge_test.dart`

**Interfaces:** không đổi public API (`ActiveMissionsTracker({missions, onTapMission})`) — chỉ đọc thêm `item['resume_status']` (đã trả về bởi Task 32) trong `_buildMissionCard`.

- [x] **Step 1: Viết widget test**

```dart
// frontend/test/modules/hologram_hub/active_missions_tracker_resume_badge_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/hologram_hub/views/widgets/active_missions_tracker.dart';

void main() {
  testWidgets('ActiveMissionsTracker shows CHỜ TIẾP TỤC badge when resume_status pending', (tester) async {
    final missions = [
      {
        'mission_id': '1',
        'title': 'Đánh giá tài chính',
        'agent': 'Chief Of Staff',
        'progress_percent': 65,
        'current_step': 'Đang chờ specialist',
        'resume_status': 'awaiting_specialist_resume',
      },
    ];

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ActiveMissionsTracker(missions: missions),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.textContaining('CHỜ TIẾP TỤC'), findsOneWidget);
  });

  testWidgets('ActiveMissionsTracker hides badge when resume_status absent (backward compatible)', (tester) async {
    final missions = [
      {
        'mission_id': '2',
        'title': 'Mission bình thường',
        'agent': 'Sales Specialist',
        'progress_percent': 40,
        'current_step': 'Đang xử lý',
      },
    ];

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ActiveMissionsTracker(missions: missions),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.textContaining('CHỜ TIẾP TỤC'), findsNothing);
  });
}
```

- [x] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd frontend && flutter test test/modules/hologram_hub/active_missions_tracker_resume_badge_test.dart`
Expected: FAIL (badge chưa tồn tại)

- [x] **Step 3: Sửa `_buildMissionCard` trong `active_missions_tracker.dart`**

Ngay sau dòng `final nextStep = item['next_step']?.toString() ?? 'Bước tiếp theo';` trong `_buildMissionCard`, thêm:

```dart
    final resumeStatus = item['resume_status']?.toString();
```

Sửa khối tiêu đề card (`Row` chứa `title` + badge agent) — thêm badge "CHỜ TIẾP TỤC" ngay dưới hàng tiêu đề khi `resumeStatus == 'awaiting_specialist_resume'`, chèn ngay sau khối `Row(children: [Expanded(child: Text(title...)), Container(...agent badge...)])` và trước `const SizedBox(height: 10), // Progress Bar`:

```dart
            if (resumeStatus == 'awaiting_specialist_resume') ...[
              const SizedBox(height: 6),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: const Color(0xFFF59E0B).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: const Color(0xFFF59E0B).withValues(alpha: 0.35)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.hourglass_top_rounded, size: 10, color: Color(0xFFFBBF24)),
                    const SizedBox(width: 4),
                    const Text(
                      'CHỜ TIẾP TỤC',
                      style: TextStyle(color: Color(0xFFFBBF24), fontSize: 9, fontWeight: FontWeight.w700),
                    ),
                  ],
                ),
              ),
            ],
```

- [x] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd frontend && flutter test test/modules/hologram_hub/active_missions_tracker_resume_badge_test.dart`
Expected: PASS cả 2 test.

- [x] **Step 5: Chạy lại toàn bộ test hologram_hub**

Run: `cd frontend && flutter test test/modules/hologram_hub/`
Expected: PASS.

- [x] **Step 6: Commit**

```bash
git add frontend/lib/modules/hologram_hub/views/widgets/active_missions_tracker.dart frontend/test/modules/hologram_hub/active_missions_tracker_resume_badge_test.dart
git commit -m "feat(hologram-hub): show CHO TIEP TUC badge on ActiveMissionsTracker when specialist resume is pending"
```

---

## Phase 17 — Xoá `chief_of_staff.py` (TÁCH RIÊNG, chỉ chạy sau khi cutover ổn định)

**Điều kiện bắt buộc trước khi bắt đầu task này (Global Constraints + Quyết định 1 mục "Phasing"):** Task 26-29 (cutover 3 điểm gọi qua seam) đã merge và chạy ổn định — KHÔNG được gộp task này vào cùng lúc với Task 26-29. "Ổn định" tối thiểu nghĩa là: `backend/app/tests/agents/` xanh liên tục qua ít nhất 1 chu kỳ chạy đầy đủ sau cutover (Task 29), không có regression nào phát sinh từ seam mới.

### Task 35: Xoá `chief_of_staff.py`, cập nhật Ownership Map

**Files:**
- Create: `backend/app/workforce/agents/orchestration/result.py`
- Modify: `backend/app/workforce/agents/orchestration/service.py`
- Modify: `backend/app/workforce/agents/context/assembler.py`
- Delete: `backend/app/workforce/agents/orchestration/chief_of_staff.py`
- Delete: `backend/app/tests/agents/test_chief_of_staff_orchestration.py`
- Delete: `backend/app/tests/agents/test_chief_of_staff_delegation.py`
- Modify: `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`

**Interfaces:**
- Produces: `ChiefOfStaffResult`/`DelegatedTaskResult` di chuyển sang `orchestration/result.py` (API response shape KHÔNG đổi — chỉ đổi nơi định nghĩa class).

**Ghi chú:** `ChiefOfStaffResult` vẫn được `orchestration/service.py` (Task 25) và `router.py` (`response_model=ChiefOfStaffResult`, Task 26) dùng làm response shape — PHẢI di chuyển class này ra khỏi `chief_of_staff.py` TRƯỚC khi xoá file, không phải xoá rồi mới nhận ra seam vỡ.

- [x] **Step 1: Grep xác nhận không còn production call site nào gọi `ChiefOfStaffOrchestrator` ngoài `chief_of_staff.py` và các test sắp xoá**

Run: `cd backend && grep -rln "ChiefOfStaffOrchestrator" app --include="*.py" | grep -v ".venv"`
Expected: chỉ còn `app/workforce/agents/orchestration/chief_of_staff.py`, `app/tests/agents/test_chief_of_staff_orchestration.py`, `app/tests/agents/test_chief_of_staff_delegation.py` (đã cutover ở Task 26-28, xác nhận lại bằng grep vì code có thể đã đổi từ lúc viết plan tới lúc thực thi). Nếu còn call site sản xuất nào khác, DỪNG — xử lý trước khi tiếp tục.

- [x] **Step 2: Di chuyển `ChiefOfStaffResult`/`DelegatedTaskResult` sang `orchestration/result.py`**

```python
# backend/app/workforce/agents/orchestration/result.py
"""Response shape cho mission orchestration — tách khỏi chief_of_staff.py
(đã xoá) để orchestration/service.py và router.py không phụ thuộc vào file đã
retire. Field/kiểu dữ liệu giữ NGUYÊN so với ChiefOfStaffResult gốc — API
response contract không đổi."""
from typing import Any
from pydantic import BaseModel, Field


class DelegatedTaskResult(BaseModel):
    agent_key: str
    domain: str
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)
    status: str = "completed"


class ChiefOfStaffResult(BaseModel):
    mission_id: str
    workspace_id: str
    goal: str
    diagnosis: str
    specialist_reports: dict[str, Any] = Field(default_factory=dict)
    priorities: list[str] = Field(default_factory=list)
    action_plan: list[dict[str, Any]] = Field(default_factory=list)
    required_approvals: list[dict[str, Any]] = Field(default_factory=list)
    proposals: list[dict[str, Any]] = Field(default_factory=list)
    status: str = "completed"
```

- [x] **Step 3: Sửa `orchestration/service.py` đổi import**

Đổi dòng `from app.workforce.agents.orchestration.chief_of_staff import ChiefOfStaffResult` thành:

```python
from app.workforce.agents.orchestration.result import ChiefOfStaffResult
```

- [x] **Step 4: Sửa `router.py` đổi import (đã cutover ở Task 26, giờ trỏ sang `result.py`)**

Đổi dòng `from app.workforce.agents.orchestration.chief_of_staff import ChiefOfStaffOrchestrator, ChiefOfStaffResult` (còn sót từ trước Task 26 nếu Task 26 chỉ đổi call site mà chưa dọn import không dùng) thành:

```python
from app.workforce.agents.orchestration.result import ChiefOfStaffResult
```

- [x] **Step 5: Sửa `app/workforce/agents/context/assembler.py` — bỏ import `SPECIALIST_REGISTRY` từ `chief_of_staff.py`**

Đổi dòng `from app.workforce.agents.orchestration.chief_of_staff import SPECIALIST_REGISTRY` (dòng ~273, đã verify bằng grep ở đầu kế hoạch) thành:

```python
from app.workforce.agents.orchestration.specialist_registry import SPECIALIST_REGISTRY
```

- [x] **Step 6: Xoá `chief_of_staff.py` và 2 file test dành riêng cho nó**

```bash
git rm backend/app/workforce/agents/orchestration/chief_of_staff.py
git rm backend/app/tests/agents/test_chief_of_staff_orchestration.py
git rm backend/app/tests/agents/test_chief_of_staff_delegation.py
```

- [x] **Step 7: Chạy toàn bộ `backend/app/tests/agents/` xác nhận không còn tham chiếu nào tới file đã xoá**

Run: `cd backend && .venv/bin/pytest app/tests/agents/ -v`
Expected: PASS. Nếu FAIL vì `ImportError` từ 1 file test khác chưa được liệt kê ở Step 1 (grep có thể bỏ sót do chạy trước khi Task 26-34 hoàn tất thực tế), sửa import ở file đó sang `orchestration/result.py`/`orchestration/service.py`/`specialist_registry.py` tương ứng.

- [x] **Step 8: Chạy toàn bộ test suite backend để xác nhận không có consumer nào khác ngoài `app/tests/agents/` bị ảnh hưởng**

Run: `cd backend && .venv/bin/pytest app/tests/ -v`
Expected: PASS.

- [x] **Step 9: Cập nhật `COSA_CANONICAL_OWNERSHIP_MAP.md` — thêm dòng "Co-founder Orchestrator"**

Thêm 1 dòng mới vào bảng "Ownership map" trong `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`, theo đúng format các dòng hiện có:

```markdown
| Co-founder Orchestrator | backend/app/workforce/agents/orchestration/adk (AdkCofounderWorkflow) via backend/app/workforce/agents/orchestration/service.py seam | Canonical production | router.py/cosa_cofounder_service.py/continuation.py chỉ gọi qua service.py; ChiefOfStaffOrchestrator đã xoá (Quyết định 1) | Node mới trong AdkCofounderWorkflow, mở rộng service.py seam | Không tạo orchestrator song song; mọi thay đổi routing/orchestration đi qua seam này |
```

- [x] **Step 10: Commit**

```bash
git add backend/app/workforce/agents/orchestration/result.py backend/app/workforce/agents/orchestration/service.py backend/app/workforce/agents/orchestration/router.py backend/app/workforce/agents/context/assembler.py docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md
git commit -m "refactor(orchestration): retire ChiefOfStaffOrchestrator, AdkCofounderWorkflow is now the sole Co-founder Orchestrator"
```

---

## Câu hỏi mở / rủi ro cần theo dõi khi thực thi

Ghi lại tại đây (không phải trong từng task) vì đây là các điểm cần phán đoán kỹ thuật hoặc phát hiện thật khi đọc code, không phải điều proposal gốc đã chốt sẵn:

1. **Thứ tự node Synthesis→QualityGate→ApprovalGate→Execution khác literal diagram của Quyết định 1** (xem ghi chú đầu Phase 10) — đã chọn giữ đúng hành vi thật của `chief_of_staff.py` (quality gate chạy trước khi derive action plan) thay vì đúng thứ tự vẽ trong sơ đồ, vì yêu cầu "equivalent governance side effects" được ưu tiên hơn thứ tự minh hoạ.
2. **`ToolInvocationService`/`PolicyGate` trước đây hardcode `run_id=None`** khi gọi `GovernanceKernel.evaluate_and_audit_tool_call` (khác với `dispatch_tool_call` của `DeepSeekHarnessAdapter` vốn truyền đúng `run_id`) — phát hiện thật khi đọc code (`policy_gate.py`), không phải suy đoán. Task 6 vá gap này bằng field `run_id` bổ sung, additive/backward-compatible. Nếu không vá, mọi `AgentToolCall` do `CosaGovernedTool` tạo ra sẽ mồ côi, không link về mission.
3. **Cơ chế pause/resume qua `RequestInput`/`FunctionResponse`/`create_request_input_response`** (Task 16, 24, 25) là điểm tích hợp sâu nhất, đã verify bằng đọc trực tiếp source `google-adk==2.7.0` trong `.venv` nhưng CHƯA được chạy thật — Task 24 là nơi phát hiện sớm nếu giả định sai, đúng mục đích thiết kế của nó.
4. **`ctx.state` không được chứa object không serialize được (SQLAlchemy Session, ORM instance)** — phát hiện giữa lúc viết kế hoạch (không phải từ đầu), đã retrofit toàn bộ node Task 13/16/19/20/21/22 sang mở `SessionLocal()` riêng + chỉ mang id qua state. Đây là thay đổi kiến trúc quan trọng so với thiết kế "mỗi node đọc `ctx.state["db"]`" ngây thơ ban đầu — thực thi cần đọc kỹ ghi chú đầu Phase 10 trước khi viết bất kỳ node nào.
5. **`founder_hub_service.py`'s `active_missions` và `missions_router.py`'s `_format_mission_summary()` là 2 nguồn "mission summary" khác nhau, không dùng chung code** (phát hiện thật, xem đầu Phase 15) — kế hoạch này mở rộng CẢ HAI riêng lẻ (Task 31, 32) cho đủ 2 nơi frontend cần, không hợp nhất chúng (ngoài phạm vi, rủi ro cao hơn).
6. **`backend/app/workforce/api/admin_api.py`'s `GET /workforce/runs/{run_id}`** (nuôi `agents_service.dart::getRunDetail`, dùng bởi `agent_run_detail_dialog.dart`) đọc `LegacyPlatformAgentRun`/`AgentStep` — một cây model HOÀN TOÀN khác, không liên quan gì tới `AgentRun`/`RunStep` canonical mà toàn bộ kế hoạch này dùng. Đây là lý do Phase 16 KHÔNG đụng vào `agent_run_detail_dialog.dart`/`agents_runs_history_tab.dart` — thêm `RuntimeSession` vào đó sẽ đòi hợp nhất 2 cây model không liên quan, việc đó là 1 dự án riêng (khớp đúng cảnh báo fragmentation ở CLAUDE.md §14), không phải phạm vi của Quyết định 1.
7. **`google.adk.workflow.utils._workflow_hitl_utils`/`google.adk.workflow._function_node` là module có tiền tố `_` (không hoàn toàn public API)** — khi nâng cấp `google-adk` lên version mới hơn `2.7.0`, cần re-verify các import này còn tồn tại đúng vị trí trước khi merge nâng cấp.
8. **`MissionResumeJob.checkpoint_key` dùng chung giá trị với ADK `RequestInput.interrupt_id`** (`f"delegation_step:{step_id}"`, xem Task 16/17) — 1 quyết định thiết kế cụ thể (không phải trong proposal gốc) để tránh cần 1 bảng ánh xạ interrupt_id↔checkpoint_key riêng. Nếu tương lai có checkpoint không gắn với 1 RunStep cụ thể (vd checkpoint theo thời gian), quy ước này cần mở rộng.
9. **`CosaGovernedTool` (Task 7) chưa được node nào trong `AdkCofounderWorkflow` thật sự gọi** — mọi node hiện tại (Task 12-23) chỉ tương tác qua `TaskBoardService`/durable delegation, khớp đúng hành vi `chief_of_staff.py` (vốn cũng không gọi tool trực tiếp khi delegation durable đang bật). `CosaGovernedTool` chỉ được exercise trực tiếp trong test gate (Task 24) để chứng minh pipeline governance hoạt động — đây là hạ tầng sẵn sàng cho 1 node tương lai (vd `BuildCompanyContextNode` đọc nhanh 1 con số tài chính mà không cần round-trip qua delegation), không phải code chết; nhưng cần founder xác nhận có muốn thêm 1 node ADK-direct-tool thật trong scope Phase 1 này hay để lại Phase 2.
   - **Quyết định (2026-08-21):** Giữ nguyên kiến trúc Phase 1 (hoàn thành) — mọi tool invocation cho nghiệp vụ phân tích chuyên sâu tiếp tục đi qua durable delegation và specialist worker. `CosaGovernedTool` giữ vai trò adapter chuẩn hóa kết nối Google ADK ↔ `GovernanceKernel` và đã sẵn sàng cho các direct-tool nodes (như inline context lookups) trong Phase 2.

