# Phase 2 — Durable Run Substrate

> Nguồn gốc: `COSA_AGENT_PLATFORM_PROMOTION_IMPLEMENTATION_PLAN_2026-08-23.md` §"Phase 2" (Step 6, P0.2–P0.3). Bổ sung Hermes/LangGraph theo `COSA_HERMES_LANGGRAPH_INTEGRATION_PLAN_2026-08-23.md` §3.

## Mục tiêu

5 bảng canonical `agent_core.*` tồn tại, có model/repository trong `packages/agent_core/runs/`, và test resume xuyên qua process thật (không phải giả lập cùng process).

## Điều kiện tiên quyết

Phase 1 xong (cần `contracts/` để định nghĩa row shape khớp `RunRequest`/`RunResult`/`InvocationIdentity`).

## Việc cụ thể (gốc)

1. Viết migration SQL mới (không đụng `agentos/migrations/002_governance_temporal_model.sql` — frozen) tạo schema `agent_core` với 5 bảng:
   - `agent_core.runs`: `run_id`, tenant/company/workspace scope, principal, root executable, status, correlation, created/updated, terminal result/error refs.
   - `agent_core.run_checkpoints`: `checkpoint_ref`, `run_id`, sequence, serialized kernel/workflow state, `SpecResolutionManifest` snapshot/ref, resume metadata, `created_at`.
   - `agent_core.run_events`: append-only, event type theo vocabulary (`run.started`, `message.delta`, `tool.requested`, `policy.evaluated`, `approval.required`, `approval.decided`, `tool.started`, `tool.completed`, `checkpoint.created`, `run.waiting`, `run.resumed`, `run.completed`, `run.failed`).
   - `agent_core.run_tool_calls`: exact invocation ledger — `run_id`, `tool_call_id`, `capability_id`, `payload_hash`, payload/summary safe representation, status, `idempotency_key`, `checkpoint_ref`, result hash/ref, error, timestamps; recommend thêm `execution_target_snapshot`, policy observation refs, connector identity, risk at request.
   - `agent_core.approvals`: `approval_id`, `run_id`, `tool_call_id`, `checkpoint_ref`, status, requirement, reviewer/evidence refs, created/decided, expiry, reason.
2. Viết `packages/agent_core/runs/models.py` (ORM/dataclass mapping 5 bảng) và `packages/agent_core/runs/repository.py` (CRUD + query theo `run_id`, theo `tool_call_id`, không theo `(run_id, action)`).
3. Viết mapping tường minh (bảng markdown trong `docs/architecture/agentos_salvage_inventory.md` mục Phase 2) từ 4 bảng prototype `agent_core_governance.*` sang 5 bảng canonical mới — quyết định rõ: giữ song song tối đa hết Phase 6, sau đó `agent_core_governance.*` chỉ còn đọc lịch sử, không ghi mới.
4. Viết test resume qua process thật: subprocess Python riêng (không dùng threading/asyncio task giả lập), subprocess mới đọc `run_checkpoints` từ Postgres bằng `run_id` truyền qua argv/env, resume, assert kết quả đúng.

## Definition of Done — Phase 2 (gốc)

- 5 bảng tồn tại trong Postgres dev environment, có migration file review được.
- `packages/agent_core/runs/repository.py` có test coverage: tạo run, ghi checkpoint tuần tự, đọc `run_tool_calls` theo `tool_call_id`, ghi/đọc approval theo `checkpoint_ref`.
- **Test process-thật pass**: subprocess con độc lập đọc checkpoint và resume đúng — điều kiện bắt buộc để khép gap "Serving = No test yếu hơn tên gọi" đã phát hiện trong audit gốc. Không coi Phase 2 xong nếu chỉ có test tạo instance thứ hai cùng process.
- Mapping tài liệu từ `agent_core_governance.*` → `agent_core.*` đã viết, có ít nhất 1 script/test đọc dữ liệu cũ và insert tương đương vào bảng mới.

## Bổ sung Hermes/LangGraph

**Quyết định: KHÔNG đổi gì ở Phase 2.**

Không thêm cột/migration cho LangGraph checkpoint ở giai đoạn này — quá sớm khi chưa qua 2 gate ở Phase 3 (technical spike) và Phase 6 (adoption decision). Nếu Phase 6 quyết định **Adopt** LangGraph, migration riêng (cột `workflow_runtime_state: JSONB` hoặc bảng LangGraph checkpoint Postgres-native) sẽ được thêm lúc đó, không trước.

Lý do reject thêm cột "phòng hờ" ngay bây giờ (rejected alternative, xem Integration Plan §5): forward-compatibility column không có consumer thật là abstraction-first, và tạo ảo giác quyết định adoption đã ngầm định trước khi Phase 6 thật sự chạy acceptance matrix HL-01→HL-18.

## Rủi ro/lưu ý (gốc)

Đây là phase rủi ro kỹ thuật cao nhất về durability — process-thật test cần môi trường CI/dev hỗ trợ subprocess + Postgres thật, không chỉ SQLite/mock.
