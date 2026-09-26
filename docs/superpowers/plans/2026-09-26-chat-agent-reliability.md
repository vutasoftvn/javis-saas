# Chat agent reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Chat Co-Founder báo lỗi provider dễ hiểu theo ngôn ngữ người dùng, tool `workspace.context.read` không còn làm run thất bại vì sai biến, và agent biết `workspace_id`/`project_id` hiện tại mà không hỏi lại người dùng.

**Architecture:** (1) Một hàm dịch lỗi ở biên `apps/cosa/worker/handlers.py` (điểm duy nhất emit `run.failed` `{"error": ...}` cho mọi kernel) thêm `error_code` + `user_message` theo locale. (2) Kernel Agents SDK trả lỗi validate đầu vào của tool về cho model dưới dạng kết quả tool thay vì ném exception, và tự điền `project_id` từ run scope. (3) `PromptBundle` nhận `session_context` dựng từ dữ liệu backend đã verify. (4) Flutter ưu tiên `user_message`.

**Tech Stack:** Python 3.11 (pytest, FastAPI, OpenAI Agents SDK, LiteLLM), Flutter/Dart (flutter_test).

## Global Constraints

- Comment/docstring tiếng Việt, code identifier tiếng Anh (theo code hiện có).
- Python chạy qua venv: `source .venv/bin/activate && PYTHONPATH=. python -m pytest <path> -q` (cwd `javis-saas`).
- Flutter test: `cd frontend && flutter test <path>`; sau cùng `flutter analyze`.
- Commit thẳng lên `main`, KHÔNG tạo nhánh; commit message tiếng Việt kiểu `fix(chat): ...`, kết thúc bằng `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`. Lệnh `git commit` cần chạy ngoài sandbox (sandbox chặn ghi `.git`).
- Chỉ `git add` đúng file của task. Working tree đang có sửa dở ở `frontend/lib/modules/hologram_hub/widgets/chat_panel_content.dart` và test tương ứng — KHÔNG stage/sửa chúng.
- Thông báo lỗi hiển thị cho người dùng phải theo ngôn ngữ người dùng đang dùng (locale của run, mặc định `vi-VN`); chuỗi thô của provider chỉ ghi log, không gửi xuống client.
- Không nhận `workspace_id`/`project_id` từ input của model để ghi đè scope của run.

## Phạm vi và điều chỉnh so với spec

Spec: `docs/superpowers/specs/2026-09-26-chat-agent-reliability-design.md`. Plan này phủ hạng mục 1, 3, 4, 5. Hai hạng mục tách ra kế hoạch riêng (ghi ở cuối file):
- Hạng mục 2 (fallback lúc chạy): route đã chọn profile ACTIVE đầu tiên trong `primary + fallback_profile_ids` lúc bind (`resolver._validate`). Fallback giữa chừng khi provider hết tiền cần bọc `agents.models.interface.Model` hoặc chạy lại cùng `run_id` — rủi ro cao, cần thiết kế riêng.
- Hạng mục 6 (HTTP 500): chưa có stack trace, cần log server.
- Điều chỉnh: phân loại lỗi đặt ở `handlers.py` (1 điểm) thay vì trong từng kernel như spec ghi.

## File Structure

| File | Trách nhiệm |
|---|---|
| `apps/cosa/worker/provider_errors.py` (mới) | `classify_run_error(message, locale) -> ClassifiedError(code, user_message)` |
| `apps/cosa/worker/handlers.py` (sửa ~L660-680) | Emit `run.failed` kèm `error_code`/`user_message`; truyền `project_id` vào `extra_md` |
| `apps/cosa/graphql/persisted_operations.py` (sửa L31-35) | 422 nêu biến hợp lệ |
| `apps/cosa/capabilities/workspace_context_read.py` (sửa L23-45) | Schema `oneOf` + mô tả |
| `packages/agent_integrations/openai_agents_sdk/tool_args.py` (mới) | `apply_run_scope`, `tool_input_error_result` |
| `packages/agent_integrations/openai_agents_sdk/kernel.py` (sửa `_on_invoke` ~L180, prompt ~L417) | Dùng 2 helper trên; truyền `session_context` |
| `packages/agent/prompts/bundle.py` (sửa) | Trường `session_context` |
| `frontend/lib/modules/hologram_hub/controllers/founder_command_center_controller.dart` (sửa ~L1121) | Ưu tiên `user_message` |
| `frontend/lib/modules/hologram_hub/controllers/direct_agent_chat_controller.dart` (sửa L50-56, L168-183) | `conversationId` + `user_message` |

---

### Task 1: Phân loại lỗi run + `user_message` theo locale

**Files:**
- Create: `apps/cosa/worker/provider_errors.py`
- Modify: `apps/cosa/worker/handlers.py` (khối `else:` sau `record_run_outcome("failed", ...)`, ~L660-680)
- Test: `tests/apps/cosa/worker/test_provider_errors.py` (tạo `tests/apps/cosa/worker/__init__.py` nếu thư mục chưa có)

**Interfaces:**
- Produces: `classify_run_error(message: str, locale: str = "vi-VN") -> ClassifiedError`; `ClassifiedError` là `NamedTuple(code: str, user_message: str)`. Mã: `provider_insufficient_balance`, `provider_auth`, `provider_rate_limited`, `provider_unavailable`, `tool_input_invalid`, `unknown`.

- [ ] **Step 1: Viết test lỗi**

```python
# tests/apps/cosa/worker/test_provider_errors.py
import pytest

from apps.cosa.worker.provider_errors import classify_run_error

DEEPSEEK_MSG = (
    'litellm.BadRequestError: DeepseekException - {"error":{"message":"Insufficient '
    'Balance (request_id: x)","type":"unknown_error","param":null,"code":"invalid_request_error"}}'
)


def test_insufficient_balance_vi() -> None:
    r = classify_run_error(DEEPSEEK_MSG, "vi-VN")
    assert r.code == "provider_insufficient_balance"
    assert "hết hạn mức" in r.user_message
    assert "litellm" not in r.user_message and "request_id" not in r.user_message


def test_insufficient_balance_en() -> None:
    r = classify_run_error(DEEPSEEK_MSG, "en-US")
    assert r.code == "provider_insufficient_balance"
    assert "quota" in r.user_message.lower()


@pytest.mark.parametrize(
    ("msg", "code"),
    [
        ("litellm.AuthenticationError: invalid api key", "provider_auth"),
        ("litellm.RateLimitError: 429 too many requests", "provider_rate_limited"),
        ("litellm.ServiceUnavailableError: 503", "provider_unavailable"),
        ("litellm.Timeout: request timed out", "provider_unavailable"),
        ("Error running tool x: 422: unknown variables: ['query']", "tool_input_invalid"),
        ("something else entirely", "unknown"),
    ],
)
def test_codes(msg: str, code: str) -> None:
    assert classify_run_error(msg, "vi-VN").code == code


def test_unknown_locale_defaults_to_vi() -> None:
    assert "hết hạn mức" in classify_run_error(DEEPSEEK_MSG, "").user_message


def test_unknown_error_message_does_not_echo_raw_text() -> None:
    r = classify_run_error("secret-path /etc/x leaked", "vi-VN")
    assert "secret-path" not in r.user_message
```

- [ ] **Step 2: Chạy, xác nhận FAIL**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/worker/test_provider_errors.py -q`
Expected: FAIL `ModuleNotFoundError: apps.cosa.worker.provider_errors`

- [ ] **Step 3: Cài đặt**

```python
# apps/cosa/worker/provider_errors.py
"""Dịch lỗi run thô (chuỗi từ LiteLLM/SDK/tool) sang mã + thông báo cho người
dùng theo locale. Đây là bộ dịch Ở BIÊN (chỉ dùng để hiển thị) — không dùng để
điều khiển workflow (xem packages/agent/contracts/errors.py). Chuỗi thô luôn
ở lại log server, không bao giờ vào `user_message`."""

from __future__ import annotations

from typing import NamedTuple

__all__ = ["ClassifiedError", "classify_run_error"]


class ClassifiedError(NamedTuple):
    code: str
    user_message: str


# (code, các mẫu nhận diện — so khớp lowercase, theo thứ tự ưu tiên)
_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("provider_insufficient_balance", ("insufficient balance", "insufficient_quota", "quota exceeded")),
    ("provider_auth", ("authenticationerror", "invalid api key", "incorrect api key", "401")),
    ("provider_rate_limited", ("ratelimiterror", "rate limit", "429", "too many requests")),
    (
        "provider_unavailable",
        ("serviceunavailable", "timeout", "timed out", "503", "502", "connection error", "apiconnectionerror"),
    ),
    ("tool_input_invalid", ("error running tool", "unknown variables")),
)

_MESSAGES: dict[str, dict[str, str]] = {
    "vi": {
        "provider_insufficient_balance": "Dịch vụ AI tạm thời không khả dụng do nhà cung cấp model đã hết hạn mức. Vui lòng liên hệ quản trị viên để nạp thêm hoặc đổi model.",
        "provider_auth": "Không xác thực được với nhà cung cấp model. Vui lòng kiểm tra API key trong Cài đặt → Model Providers.",
        "provider_rate_limited": "Nhà cung cấp model đang giới hạn tốc độ. Vui lòng thử lại sau ít phút.",
        "provider_unavailable": "Nhà cung cấp model tạm thời không phản hồi. Vui lòng thử lại sau.",
        "tool_input_invalid": "Agent gọi công cụ với tham số không hợp lệ. Vui lòng thử lại.",
        "unknown": "Đã xảy ra lỗi khi xử lý yêu cầu. Vui lòng thử lại hoặc liên hệ hỗ trợ.",
    },
    "en": {
        "provider_insufficient_balance": "The AI service is temporarily unavailable because the model provider quota is exhausted. Please contact an administrator to top up or switch model.",
        "provider_auth": "Could not authenticate with the model provider. Please check the API key in Settings → Model Providers.",
        "provider_rate_limited": "The model provider is rate limiting requests. Please try again in a few minutes.",
        "provider_unavailable": "The model provider is temporarily not responding. Please try again later.",
        "tool_input_invalid": "The agent called a tool with invalid parameters. Please try again.",
        "unknown": "An error occurred while processing your request. Please try again or contact support.",
    },
}


def classify_run_error(message: str, locale: str = "vi-VN") -> ClassifiedError:
    lowered = (message or "").lower()
    code = "unknown"
    for rule_code, patterns in _RULES:
        if any(p in lowered for p in patterns):
            code = rule_code
            break
    lang = "en" if (locale or "").lower().startswith("en") else "vi"
    return ClassifiedError(code, _MESSAGES[lang][code])
```

- [ ] **Step 4: Chạy, xác nhận PASS**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/worker/test_provider_errors.py -q`
Expected: PASS

- [ ] **Step 5: Nối vào handlers.py**

Trong `apps/cosa/worker/handlers.py`, thêm `from apps.cosa.worker.provider_errors import classify_run_error` cùng nhóm import đầu file. Tại khối `else:` (sau `record_run_outcome("failed", ...)`, ~L661) thay:

```python
            err_msg = run_result.errors[0] if run_result.errors else "Run failed"
```
bằng:
```python
            err_msg = run_result.errors[0] if run_result.errors else "Run failed"
            classified = classify_run_error(err_msg, locale)
            logger.warning(
                "agent run failed",
                extra={"run_id": run_id, "error_code": classified.code, "error_raw": err_msg},
            )
```
Sửa `content=f"Error: {err_msg}"` thành `content=classified.user_message`, và payload emit thành:
```python
                payload={
                    "error": err_msg,
                    "error_code": classified.code,
                    "user_message": classified.user_message,
                },
```
(`locale` đã có ở L460 trong cùng hàm; nếu khối này nằm ngoài phạm vi biến, dùng `payload.get("locale") or "vi-VN"`.) Giữ nguyên khoá `error` để client cũ vẫn hoạt động.

- [ ] **Step 6: Chạy test handlers hiện có**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa -q -k "handlers or worker"`
Expected: PASS. Nếu test cũ assert `content == "Error: ..."`, cập nhật assert sang `user_message` tương ứng (thông báo có chủ đích đổi).

- [ ] **Step 7: Commit**

```bash
git add apps/cosa/worker/provider_errors.py apps/cosa/worker/handlers.py tests/apps/cosa/worker/
git commit -m "fix(chat): run.failed kèm error_code và user_message theo locale"
```

---

### Task 2: Flutter dùng `user_message` + direct chat truyền `conversationId`

**Files:**
- Modify: `frontend/lib/modules/hologram_hub/controllers/founder_command_center_controller.dart:1120-1130`
- Modify: `frontend/lib/modules/hologram_hub/controllers/direct_agent_chat_controller.dart:50-56,168-183`
- Test: `frontend/test/modules/hologram_hub/direct_agent_chat_controller_test.dart`

**Interfaces:**
- Consumes: payload `run.failed` có `user_message` (Task 1).
- Produces: `DirectAgentChatController` nhận `runEvents` kiểu `Stream<Map<String, dynamic>> Function(String runId, {String? conversationId})`.

- [ ] **Step 1: Đọc test hiện có**

Run: `sed -n 95,140p frontend/test/modules/hologram_hub/direct_agent_chat_controller_test.dart`
Ghi lại kiểu tham số `events` của helper dựng controller (~L113) để sửa chữ ký ở Step 3.

- [ ] **Step 2: Viết test lỗi** (thêm vào file test, dùng đúng helper dựng controller và helper `_delta/_completed` sẵn có; đặt tên helper dựng controller đúng như file)

```dart
test('run.failed hiển thị user_message thay vì chuỗi thô', () async {
  final controller = _buildController(
    events: (_, {conversationId}) => Stream.fromIterable([
      {
        'event_type': 'run.failed',
        'payload': {'error': 'litellm.BadRequestError raw', 'user_message': 'Hết hạn mức nhà cung cấp.'},
      },
    ]),
  );
  await controller.send('hi');
  expect(controller.errorMessage, 'Hết hạn mức nhà cung cấp.');
});

test('mở SSE kèm conversationId của cuộc trò chuyện', () async {
  String? seen;
  final controller = _buildController(
    events: (runId, {conversationId}) {
      seen = conversationId;
      return Stream.fromIterable([_delta('ok'), _completed()]);
    },
  );
  await controller.send('hi');
  expect(seen, isNotNull);
  expect(seen, controller.conversationId);
});
```
(`_buildController`/`send`/`errorMessage` — dùng đúng tên trong file hiện có; nếu tên khác, đổi theo file.)

- [ ] **Step 3: Chạy, xác nhận FAIL**

Run: `cd frontend && flutter test test/modules/hologram_hub/direct_agent_chat_controller_test.dart`
Expected: FAIL (lỗi kiểu chữ ký / assert).

- [ ] **Step 4: Cài đặt**

`direct_agent_chat_controller.dart`: đổi field ở L56 thành
```dart
  final Stream<Map<String, dynamic>> Function(String runId, {String? conversationId}) _runEvents;
```
(kiểu tham số constructor `runEvents` ở ~L45-50 đổi tương ứng). Tại L168 đổi thành
```dart
    _subscription = _runEvents(runId, conversationId: _conversationId).listen(
```
Tại `case 'run.failed':` (~L182) đổi thành
```dart
          case 'run.failed':
            fail(payload['user_message']?.toString() ?? payload['error']?.toString() ?? 'Run failed');
```
Sửa mọi lambda `runEvents:`/`events` trong test cũ từ `(_) => ...` thành `(_, {conversationId}) => ...`.

`founder_command_center_controller.dart` (~L1121): thay dòng
```dart
                  final reason = payload['error']?.toString() ?? payload['reason']?.toString();
```
bằng
```dart
                  final friendly = payload['user_message']?.toString();
                  final reason = payload['error']?.toString() ?? payload['reason']?.toString();
```
và thay khối gán `assistantMsg['content']` bằng
```dart
                  assistantMsg['content'] =
                      (assistantMsg['content'] ?? '').isEmpty
                      ? (friendly != null && friendly.isNotEmpty
                          ? friendly
                          : (reason == null || reason.isEmpty
                              ? 'Mission thất bại hoặc bị huỷ.'
                              : 'Mission thất bại: $reason'))
                      : assistantMsg['content']!;
```

- [ ] **Step 5: Chạy test + analyze**

Run: `cd frontend && flutter test test/modules/hologram_hub/ && flutter analyze lib/modules/hologram_hub`
Expected: PASS, không lỗi analyze mới.

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/modules/hologram_hub/controllers/founder_command_center_controller.dart frontend/lib/modules/hologram_hub/controllers/direct_agent_chat_controller.dart frontend/test/modules/hologram_hub/direct_agent_chat_controller_test.dart
git commit -m "fix(chat): hiển thị user_message và truyền conversationId ở direct chat"
```

---

### Task 3: Tool `workspace.context.read` — schema rõ, 422 có gợi ý, lỗi đầu vào trả về cho model

**Files:**
- Modify: `apps/cosa/graphql/persisted_operations.py:31-35`
- Modify: `apps/cosa/capabilities/workspace_context_read.py:23-45`
- Create: `packages/agent_integrations/openai_agents_sdk/tool_args.py`
- Modify: `packages/agent_integrations/openai_agents_sdk/kernel.py` (`_on_invoke`, ~L180-191)
- Test: `tests/apps/cosa/graphql/test_persisted_operations_hint.py`, `tests/agent_integrations/openai_agents_sdk/test_tool_args.py` (kiểm tra thư mục test tương ứng của package; tạo `__init__.py` nếu cần)

**Interfaces:**
- Produces: `tool_input_error_result(exc: Exception) -> dict[str, Any] | None` — trả `{"error": <chuỗi>, "hint": "Fix the arguments and call the tool again."}` nếu `exc` là lỗi validate đầu vào (có `status_code` 400..499 hoặc là `ValueError`), ngược lại `None` (caller ném lại).

- [ ] **Step 1: Test lỗi cho 422 có gợi ý**

```python
# tests/apps/cosa/graphql/test_persisted_operations_hint.py
import pytest
from fastapi import HTTPException

from apps.cosa.graphql.persisted_operations import execute_persisted_operation


@pytest.mark.asyncio
async def test_unknown_variable_lists_allowed_ones() -> None:
    with pytest.raises(HTTPException) as ei:
        await execute_persisted_operation("workspaceContext", {"query": "x"}, object(), object())
    assert ei.value.status_code == 422
    assert "['query']" in ei.value.detail
    assert "question" in ei.value.detail  # biến hợp lệ được nêu
```

- [ ] **Step 2: Chạy, xác nhận FAIL**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/graphql/test_persisted_operations_hint.py -q`
Expected: FAIL (`question` không có trong detail)

- [ ] **Step 3: Cài đặt gợi ý**

Trong `persisted_operations.py` đổi detail:
```python
            detail=(
                f"unknown variables: {sorted(unknown)}; "
                f"allowed for '{operation_id}': {sorted(operation.allowed_variables)}"
            ),
```
Test cũ assert `detail == "unknown variables: [...]"` (nếu có) → đổi sang `startswith`.

- [ ] **Step 4: Schema `oneOf` cho capability**

Trong `workspace_context_read.py` thay `input_schema` bằng:
```python
    input_schema={
        "type": "object",
        "required": ["operation_id"],
        "properties": {
            "operation_id": {
                "type": "string",
                "enum": ["workspaceContext", "enterpriseKnowledgeSearch"],
            },
            "variables": {
                "type": "object",
                "description": (
                    "workspaceContext -> {question: string}; "
                    "enterpriseKnowledgeSearch -> {query: string, limit?: integer}. "
                    "Không dùng biến của operation này cho operation kia."
                ),
                "properties": {
                    "question": {"type": "string"},
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "additionalProperties": False,
            },
        },
    },
```
Và thêm vào cuối `description` của spec: `" Biến hợp lệ: workspaceContext nhận 'question'; enterpriseKnowledgeSearch nhận 'query' (+ 'limit' tuỳ chọn)."` Chạy `PYTHONPATH=. python -m pytest tests/apps/cosa/capabilities -q`; nếu có test snapshot/hash schema (contract), cập nhật theo quy trình repo (`make` target sinh lại contract nếu test báo lệch).

- [ ] **Step 5: Test lỗi cho helper tool**

```python
# tests/agent_integrations/openai_agents_sdk/test_tool_args.py
import pytest

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
```

- [ ] **Step 6: Chạy, xác nhận FAIL** (`ModuleNotFoundError`)

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent_integrations/openai_agents_sdk/test_tool_args.py -q`

- [ ] **Step 7: Cài đặt helper + nối vào kernel**

```python
# packages/agent_integrations/openai_agents_sdk/tool_args.py
"""Xử lý đầu vào tool ở biên kernel: (1) lỗi validate đầu vào (4xx/ValueError)
trả về cho model như kết quả tool để nó tự sửa và gọi lại — không làm cả run
thất bại; (2) lỗi runtime có kiểu (AgentRuntimeError: denied, waiting_approval,
...) và 5xx vẫn phải ném ra như cũ."""

from __future__ import annotations

from typing import Any

from agent.contracts.errors import AgentRuntimeError

__all__ = ["tool_input_error_result"]


def tool_input_error_result(exc: Exception) -> dict[str, Any] | None:
    if isinstance(exc, AgentRuntimeError):
        return None
    status = getattr(exc, "status_code", None)
    if isinstance(exc, ValueError) or (isinstance(status, int) and 400 <= status < 500):
        detail = getattr(exc, "detail", None) or str(exc)
        return {
            "error": str(detail),
            "hint": "Fix the arguments and call the tool again.",
        }
    return None
```

Trong `kernel.py` `_on_invoke`, bọc lời gọi `_execute_tool`:
```python
            try:
                result = await self._execute_tool(
                    cap_spec.id,
                    args,
                    run_id=run_id,
                    tool_call_id=call_id,
                    context=context,
                    cap_spec=cap_spec,
                )
            except Exception as exc:
                recoverable = tool_input_error_result(exc)
                if recoverable is None:
                    raise
                result = recoverable
```
và thêm `from agent_integrations.openai_agents_sdk.tool_args import tool_input_error_result` ở đầu file. (Event `tool.completed` phía dưới vẫn chạy với `result` này; hash không lộ nội dung.)

- [ ] **Step 8: Chạy test**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent_integrations/openai_agents_sdk tests/apps/cosa/graphql tests/apps/cosa/capabilities -q`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add apps/cosa/graphql/persisted_operations.py apps/cosa/capabilities/workspace_context_read.py packages/agent_integrations/openai_agents_sdk/tool_args.py packages/agent_integrations/openai_agents_sdk/kernel.py tests/apps/cosa/graphql/test_persisted_operations_hint.py tests/agent_integrations/openai_agents_sdk/test_tool_args.py
git commit -m "fix(chat): tool workspace.context.read — schema rõ, 422 có gợi ý, lỗi đầu vào trả về cho model"
```

---

### Task 4: Ngữ cảnh phiên trong prompt + tự điền `project_id` cho tool

**Files:**
- Modify: `packages/agent/prompts/bundle.py`
- Modify: `packages/agent_integrations/openai_agents_sdk/tool_args.py` (thêm `apply_run_scope`)
- Modify: `packages/agent_integrations/openai_agents_sdk/kernel.py` (~L417 prompt; `_on_invoke`)
- Modify: `apps/cosa/worker/handlers.py` (~L440-455: thêm `project_id` vào `extra_md`)
- Test: `tests/agent/prompts/test_bundle.py`, `tests/agent_integrations/openai_agents_sdk/test_tool_args.py`

**Interfaces:**
- Consumes: `tool_input_error_result` (Task 3), `context` dict của kernel có `workspace_id`, và (sau task này) `project_id`.
- Produces: `PromptBundle.session_context: dict[str, str]` (mặc định `{}`); `apply_run_scope(args: dict[str, Any], input_schema: dict[str, Any] | None, context: dict[str, Any]) -> dict[str, Any]` — điền `project_id` từ context nếu schema có thuộc tính đó và args bỏ trống; nếu args mang `project_id` khác context → `raise ValueError("project_id không khớp project của phiên hiện tại")`.

- [ ] **Step 1: Test lỗi cho PromptBundle**

Thêm vào `tests/agent/prompts/test_bundle.py`:
```python
def test_session_context_rendered_with_no_ask_rule() -> None:
    text = PromptBundle(
        agent_instructions="A",
        session_context={"workspace_id": "w1", "project_id": "p9"},
    ).render()
    assert "workspace_id: w1" in text and "project_id: p9" in text
    assert "Do not ask the user" in text


def test_no_session_context_renders_like_before() -> None:
    assert "Session context" not in PromptBundle(agent_instructions="A").render()
```

- [ ] **Step 2: Chạy, xác nhận FAIL** (`session_context` chưa có)

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/prompts/test_bundle.py -q`

- [ ] **Step 3: Cài đặt PromptBundle**

Trong `bundle.py` thêm field `session_context: dict[str, str] = Field(default_factory=dict)` và trong `render()`, sau skill instructions, trước locale:
```python
        if self.session_context:
            lines = [f"- {k}: {v}" for k, v in self.session_context.items() if v]
            sections.append(
                "Session context (verified by the platform):\n"
                + "\n".join(lines)
                + "\nDo not ask the user for these values; use them when calling tools."
            )
```

- [ ] **Step 4: Test lỗi cho `apply_run_scope`** (thêm vào `test_tool_args.py`)

```python
from agent_integrations.openai_agents_sdk.tool_args import apply_run_scope

SCHEMA = {"type": "object", "properties": {"project_id": {"type": "string"}}}


def test_fills_project_id_from_context() -> None:
    assert apply_run_scope({}, SCHEMA, {"project_id": "p1"}) == {"project_id": "p1"}


def test_keeps_matching_project_id() -> None:
    assert apply_run_scope({"project_id": "p1"}, SCHEMA, {"project_id": "p1"})["project_id"] == "p1"


def test_rejects_other_project() -> None:
    with pytest.raises(ValueError, match="project_id"):
        apply_run_scope({"project_id": "p2"}, SCHEMA, {"project_id": "p1"})


def test_no_change_when_schema_has_no_project_id_or_no_context() -> None:
    assert apply_run_scope({"a": 1}, {"properties": {}}, {"project_id": "p1"}) == {"a": 1}
    assert apply_run_scope({}, SCHEMA, {}) == {}
```

- [ ] **Step 4b: Chạy, xác nhận FAIL** (`ImportError apply_run_scope`)

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent_integrations/openai_agents_sdk/test_tool_args.py -q`

- [ ] **Step 5: Cài đặt `apply_run_scope`** (thêm vào `tool_args.py`, và vào `__all__`)

```python
def apply_run_scope(
    args: dict[str, Any], input_schema: dict[str, Any] | None, context: dict[str, Any]
) -> dict[str, Any]:
    """Tự điền `project_id` từ scope của run (đã verify ở backend) để model
    không phải chép/bịa ID; ID khác project của run bị chặn (không đọc chéo
    project)."""
    scoped = context.get("project_id")
    props = (input_schema or {}).get("properties") or {}
    if not scoped or "project_id" not in props:
        return args
    given = args.get("project_id")
    if given in (None, ""):
        return {**args, "project_id": scoped}
    if str(given) != str(scoped):
        raise ValueError("project_id không khớp project của phiên hiện tại")
    return args
```
Trong `kernel.py` `_on_invoke`, ngay sau `args = json.loads(...)`, thêm vào bên trong `try` của Task 3 (trước `_execute_tool`): `args = apply_run_scope(args, cap_spec.input_schema, context or {})` (`context` là đối số của hàm dựng tool, đã được `_on_invoke` dùng ở lời gọi `_execute_tool`). `ValueError` sẽ được `tool_input_error_result` trả về model.

- [ ] **Step 6: Truyền `session_context` vào prompt (SDK kernel)**

Tại `kernel.py` ~L417:
```python
        system_prompt = PromptBundle(
            agent_instructions=spec.instructions,
            skill_instructions=skill_texts,
            session_context={
                "workspace_id": str(request.workspace_id or ""),
                "project_id": str((request.metadata or {}).get("project_id") or ""),
            },
            locale=request.locale,
        ).render()
```

- [ ] **Step 7: Đưa `project_id` vào metadata của run**

Trong `handlers.py` (~L446, cạnh `direct_message_data_access`): 
```python
    run_project_id = payload.get("project_id")
    if run_project_id:
        extra_md["project_id"] = str(run_project_id)
```
`payload["project_id"]` do `conversation_routes.py:414` đặt từ `verified_project.project_id` (đã verify), không lấy từ client.

- [ ] **Step 8: Chạy test**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/prompts tests/agent_integrations/openai_agents_sdk tests/apps/cosa -q`
Expected: PASS. Nếu test kernel snapshot system prompt lệch do khối mới, cập nhật theo thay đổi có chủ đích.

- [ ] **Step 9: Commit**

```bash
git add packages/agent/prompts/bundle.py packages/agent_integrations/openai_agents_sdk/ apps/cosa/worker/handlers.py tests/agent/prompts/test_bundle.py tests/agent_integrations/openai_agents_sdk/test_tool_args.py
git commit -m "feat(chat): ngữ cảnh phiên trong prompt và tự điền project_id cho tool"
```

---

### Task 5: Kiểm chứng end-to-end

- [ ] **Step 1:** `make agent-test` và `make apps-cosa-test` — Expected: PASS, coverage gate giữ nguyên.
- [ ] **Step 2:** `make lint && make typecheck-py` — Expected: sạch.
- [ ] **Step 3:** `make frontend-test && make frontend-analyze` — Expected: PASS (bỏ qua lỗi có sẵn từ file sửa dở của người dùng nếu có, ghi rõ trong báo cáo).
- [ ] **Step 4 (thủ công, người dùng):** restart `make dev-stack`, hot restart Flutter; chat "kiểm tra project hiện tại có object chưa". Expected: agent không hỏi `workspace_id`/`project_id`; nếu model gọi sai biến, nó nhận gợi ý và tự sửa; nếu provider hết hạn mức, UI hiện thông báo tiếng Việt thân thiện.

## Kế hoạch riêng cần làm sau

1. **Fallback lúc chạy (spec hạng mục 2):** thiết kế wrapper `agents.models.interface.Model` (chữ ký `get_response`/`stream_response` đã xác minh) chuyển sang profile trong `fallback_profile_ids` khi lỗi thuộc `provider_insufficient_balance | provider_auth | provider_unavailable`, cần `resolver.resolve_route(..., exclude_profile_ids=...)` và credential từng profile qua `factory.create(route)`.
2. **HTTP 500 (spec hạng mục 6):** cần log server COSA của `listEscalations`, `getDashboardSummary`, work products, project activity, agent runs; dùng systematic-debugging, viết test tái hiện rồi mới sửa.
