# Part 1B — Đóng gap test coverage

**Master:** [`2026-08-28-test-prod-readiness.md`](./2026-08-28-test-prod-readiness.md)
**Phụ thuộc:** Part 0; song song được với 1A/1C
**Ước lượng:** 2–3 ngày
**Nhánh:** `tpr/part1b-test-coverage-gaps`

## Mục tiêu

Đóng 2 gap coverage có rủi ro cao nhất trước prod:

1. `packages/agent_integrations/*` (≈15 adapter) — hiện **0 unit test**.
2. Kernel **checkpoint/resume với tool schema thật** — Phase 7 known gap: `RealOpenAIAgentsSDKKernel` chưa truyền `tools` cho model API nên tool call không sinh, checkpoint/approval-wait không bao giờ kích hoạt trong test.

Phụ: unit test isolated cho `apps/cosa/{workflows,capabilities,config}`.

## Trạng thái hiện tại (verify bằng code)

- `packages/agent_integrations/` chứa adapter: `openai_agents_sdk` (production kernel), `litellm`, `langchain`, `langgraph`, `google_adk`, `pydantic_ai`, `a2a`, `mcp`, `ag_ui`… — không có `tests/` cạnh chúng; chỉ `packages/agent_testkit/` có 10 conformance test.
- `packages/agent_testkit/fake_sdk_model.py` cung cấp `FakeSDKModel` (phản hồi deterministic); có `MockToolLoopModelClient`.
- `RealOpenAIAgentsSDKKernel` tại `packages/agent_integrations/openai_agents_sdk/kernel.py`; dùng `LiteLLMModel` từ `agents.extensions.models.litellm_model`.
- Approval binding đã có: `RunApprovalRecord` (`packages/agent/runs/models.py`), `ApprovalGateCoordinator` (`packages/agent/coordination/approval_gate.py`), `approval_id = f"appr_{run_id}_{tool_call_id}"`.
- 2 conformance test DeepSeek thật đã pass (single-turn + model policy) nhưng **không** có tool call.

## Thay đổi cụ thể

### 1B.1 Adapter contract/smoke tests

Tạo `tests/agent_integrations/<adapter>/test_contract.py` cho từng adapter. Mỗi test dùng `FakeSDKModel` (không gọi mạng), assert:

- Adapter khởi tạo được từ config tối thiểu, không side effect.
- `kernel.run(RunRequest)` → `RunResult` với event stream đúng vocabulary (`run.started`, `tool.called`, `tool.result`, `run.completed`).
- Tool call round-trip: model yêu cầu tool → adapter gọi handler → kết quả quay lại model.
- Lỗi provider → map sang lỗi contract, không rò exception thô.

**Bắt buộc milestone này:** `openai_agents_sdk`, `litellm`, `langchain`.
**Best-effort (skip nếu dep nặng/không cài):** phần còn lại — đánh dấu `@pytest.mark.skipif(importlib.util.find_spec(...) is None)`.

Chạy trong CI job `quality-unit` (không cần DB). Thêm `tests/agent_integrations` vào `testpaths`.

### 1B.2 Kernel checkpoint/resume với tools thật

Trong `packages/agent_integrations/openai_agents_sdk/kernel.py`:

- Map `spec.capabilities` → danh sách tool schema (name, JSON schema params) truyền vào model API của OpenAI Agents SDK (`tools=`/`Agent(tools=…)` tuỳ API).
- Khi model sinh tool call cho capability `REQUIRE_APPROVAL`: kernel tạo checkpoint + `WaitDescriptor(checkpoint_ref, approval_id)`, dừng run ở trạng thái `waiting_approval`.
- `kernel.resume(run_id, approval_decision)` đọc checkpoint, tiếp tục từ đúng chỗ.

Test:
- `tests/agent_integrations/openai_agents_sdk/test_checkpoint_resume.py` (`@pytest.mark.integration`, `FakeSDKModel` được cấu hình để phát tool call): run → dừng ở `waiting_approval`, `RunApprovalRecord` ghi Postgres với `approval_id` đúng format → `resume` với `approved` → run `completed`; `resume` với `rejected` → run `failed`/`blocked` (structured, không suy từ text — CLAUDE.md #7).
- 1 test `live_provider` tuỳ chọn: DeepSeek thật sinh 1 tool call đơn giản (chi phí ~$0.01), chỉ chạy trên `main`.

### 1B.3 Unit test isolated cho apps/cosa

- `tests/apps/cosa/workflows/` — load + validate workflow spec (`COSA_PAYOUT_APPROVAL_WORKFLOW_SPEC`), reject spec sai.
- `tests/apps/cosa/capabilities/` — mỗi handler ops/finance/marketing/web-search với `CompanyServiceClient` mock (httpx `MockTransport`), assert idempotency key + payload hash.
- `tests/apps/cosa/config/` — plane resolver: loopback pass, remote VPS cho execution plane → `RuntimeError`.

## Reuse

- `packages/agent_testkit/fake_sdk_model.py` (`FakeSDKModel`, `MockToolLoopModelClient`).
- Conformance harness `packages/agent_testkit/` (kernel/protocol/model/workflow).
- `ApprovalGateCoordinator`, `RunApprovalRecord`, `WaitDescriptor` — không viết lại state machine approval.
- httpx `MockTransport` pattern đã dùng trong `tests/apps/cosa/`.

## Test / verify

- `pytest tests/agent_integrations -m "not integration and not live_provider" -q` xanh trong `quality-unit`.
- `pytest tests/agent_integrations/openai_agents_sdk -m integration -q` xanh trong `quality-integration` (Postgres có sẵn).
- Coverage `packages/agent_integrations` từ 0% → có số đo; nâng floor tương ứng trong `pyproject.toml`.
- `apps/cosa` coverage tăng; ghi vào coverage doc.

## Definition of Done

- [x] 3 adapter bắt buộc có `test_contract.py` xanh; các adapter khác có test sk-gated.
- [x] Kernel truyền `tools` cho model API; test checkpoint/resume xanh (approved + rejected path).
- [x] `apps/cosa/{workflows,capabilities,config}` có unit test isolated.
- [x] `testpaths` cập nhật; CI xanh; coverage floor nâng.
- [x] Cập nhật execution-status: Phase 7 "checkpoint/resume" chuyển ACCEPTED → VERIFIED.

## Rủi ro

- OpenAI Agents SDK API cho `tools` có thể khác giữa version → pin version trong `requirements.txt`, ghi rõ API dùng.
- Một số adapter (`google_adk`, `a2a`) có dep không cài trong CI → skip-gate, không để CI đỏ vì thiếu dep.
- Checkpoint/resume đụng schema DB (`agent_conversation.run_stream_events`, approval records) → chạy migration trước test (job đã làm điều này cho `agent`).
