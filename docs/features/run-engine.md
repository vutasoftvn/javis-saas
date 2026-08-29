# Run Engine

## 1. Mục đích

Sở hữu vòng đời logic của 1 Run (lượt chạy agent) — tạo, checkpoint, ghi event, quản lý resume sau approval/restart. Là "durable substrate" mà mọi `ExecutionKernel` implementation (`OpenAIAgentsKernel`, `LangChainKernel`) đều dùng chung, không tự quản lý state riêng.

## 2. Khi nào sử dụng

Bất kỳ khi nào 1 kernel cần: tạo Run mới (`create_run`), lưu checkpoint trước khi pause (`save_checkpoint`), ghi audit event (`append_event`), hoặc load lại state để resume (`get_run`, `get_checkpoint`).

## 3. Không dùng cho việc gì

Không phải nơi thực thi side effect (đó là `capability-gateway`), không phải nơi quyết định governance/approval (đó là `governance`/`approvals`), không lưu private chain-of-thought.

## 4. Kiến trúc và luồng dữ liệu

```
ExecutionKernel.run(request, spec)
  → publish spec vào registry (xem docs/features/... registry — hardening Wave 3)
  → RunRepository.create_run()
  → vòng lặp reasoning: model call → tool call → checkpoint nếu REQUIRE_APPROVAL
  → RunRepository.update_run_status(COMPLETED/FAILED/WAITING_APPROVAL)
```

`RunRepository` là Protocol (`packages/agent/runs/repository.py`) với 2 implementation: `InMemoryRunRepository` (test/dev) và `PostgresRunRepository` (production, bắt buộc qua `AGENT_DATABASE_URL`, không silent fallback).

## 5. Public contracts/API

- `agent.runs.repository.RunRepository` (Protocol): `create_run`, `get_run`, `update_run_status`, `save_checkpoint`, `get_checkpoint`, `list_checkpoints`, `append_event`, `list_events`, `save_tool_call`, `get_tool_call`, `create_approval`, `decide_approval` (CAS), `claim_idempotency`/`complete_/fail_/retry_idempotency_claim`.
- `agent.runs.models`: `RunRecord`, `RunCheckpointRecord`, `RunEventRecord`, `RunToolCallRecord`, `RunApprovalRecord`, `IdempotencyClaimRecord`.

## 6. Database/schema liên quan

Schema `agent` (migration `001_canonical_agent_schema.sql`, hardened ở `004_harden_exact_invocation_and_approval.sql`, `005_idempotency_claims.sql`): bảng `runs`, `run_checkpoints`, `run_events`, `run_tool_calls` (PK composite `(run_id, tool_call_id)`), `approvals` (CAS `decision_version`), `idempotency_claims`.

## 7. Cấu hình

`AGENT_DATABASE_URL` — bắt buộc cho production, không có default silent fallback về in-memory.

## 8. Ví dụ sử dụng

```python
from agent.runs.repository import PostgresRunRepository
repo = PostgresRunRepository(session_factory)
kernel = OpenAIAgentsKernel(repository=repo, ...)
result = await kernel.run(request, spec)
```

## 9. Cách bổ sung implementation mới

Implement Protocol `RunRepository` đầy đủ (xem `InMemoryRunRepository` làm reference tối giản, `PostgresRunRepository` làm reference production). Không đổi PK/FK shape đã hardened (composite `(run_id, tool_call_id)`) khi thêm implementation mới.

## 10. Security/governance

Run substrate không tự quyết governance — chỉ lưu trữ. Approval CAS (`decision_version`) chặn double-decision race.

## 11. Error handling

`AgentRuntimeError` (typed, `packages/agent/contracts/errors.py`) cho model/runtime failure — không convert thành assistant content COMPLETED.

## 12. Observability

`run_events` là append-only audit ledger — mọi event lifecycle (`run.started`, `tool.requested`, `approval.required`, ...) ghi vào đây, AG-UI adapter (`docs/integrations/ag-ui.md`) đọc từ đây để stream cho client.

## 13. Testing

`tests/agent/runs/`, `tests/agent/kernel/test_openai_agents_kernel.py`, `packages/agent_testkit/kernel_conformance/`.

## 14. Migration/backward compatibility

Migration 004/005 additive, chưa chạy trên Postgres thật (môi trường phát triển 2026-08-24 không có Postgres) — cần verify staging trước production.

## 15. Troubleshooting

Run kẹt ở `RUNNING`: kiểm tra kernel có raise exception trước khi gọi `update_run_status` không (vd lỗi resolve pinned skill — cố ý raise TRƯỚC khi tạo RunRecord để tránh đúng tình huống này).

## 16. Definition of Done

- [x] Public contract (`RunRepository` Protocol)
- [x] Implementation (InMemory + Postgres)
- [x] Migration (001, 004, 005)
- [x] Unit + integration test
- [ ] Conformance test riêng cho run-engine (hiện gộp trong kernel_conformance)
- [ ] Chạy trên Postgres thật
