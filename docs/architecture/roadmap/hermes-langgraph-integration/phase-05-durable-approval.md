# Phase 5 — Durable Approval

> Nguồn gốc: `COSA_AGENT_PLATFORM_PROMOTION_IMPLEMENTATION_PLAN_2026-08-23.md` §"Phase 5" (P0.7). Bổ sung Hermes/LangGraph theo `COSA_HERMES_LANGGRAPH_INTEGRATION_PLAN_2026-08-23.md` §3.

## Mục tiêu

Approval sống được qua restart, bind đúng invocation cụ thể chứ không phải action name — và (mới, nếu spike LangGraph tiếp diễn) chứng minh `interrupt()` của LangGraph chỉ là control primitive, không thay thế approval authority của COSA.

## Điều kiện tiên quyết

Phase 2 (bảng `approvals`), Phase 4 (invocation identity + gateway + readiness).

## Việc cụ thể (gốc)

1. Viết `packages/agent/capabilities/approval_service.py` thay thế hoàn toàn cách lookup `(run_id, action)` của `agentos/core/approval.py` — lookup bắt buộc qua `run_id + tool_call_id + checkpoint_ref`.
2. Implement lifecycle đầy đủ:
   - kernel/workflow đề xuất exact invocation → ghi `run_tool_calls` row → fresh policy evaluation → cập nhật invocation governance accumulator → nếu `REQUIRE_APPROVAL` → persist checkpoint chính xác → tạo `approvals` row bind `run_id/tool_call_id/checkpoint_ref/requirement` → set trạng thái `WAITING_APPROVAL`.
   - reviewer: load approval → trình bày đúng target/payload/risk/context (dùng `ExecutionTargetSnapshot` Phase 4) → ghi `ApprovalEvidence`.
   - resume: load run + approval + invocation + checkpoint → verify identity → verify approval evidence → verify target snapshot/drift → fresh current governance → conjoin → verify effective requirement → idempotency check → resume checkpoint → execute nếu allowed.
3. Đảm bảo APPROVED không phải bypass vĩnh viễn — mọi resume phải re-evaluate governance hiện tại trước khi dùng evidence cũ.

## Bổ sung Hermes/LangGraph — LangGraph Interrupt ↔ Approval Thật

**Chỉ áp dụng nếu spike Phase 3 (branch `experiment/langgraph-spike`) vẫn đang tiếp diễn.** Đây là lần đầu tiên spike chạm vào approval thật (Phase 3 chỉ dùng approval giả lập).

**Việc cụ thể:**

1. Trong branch spike, thay approval giả lập bằng `packages/agent/capabilities/approval_service.py` thật vừa hoàn thành ở phase này.
2. Chứng minh bằng test: khi LangGraph node gọi `interrupt()`, nó **chỉ** tạm dừng graph execution (control primitive) — approval identity thật (`run_id + tool_call_id + checkpoint_ref`) vẫn hoàn toàn do COSA governance quyết định, không bị LangGraph resume logic ghi đè hay bypass.
3. Test cụ thể: gọi node cần approval → `interrupt()` → LangGraph resume state persisted → nhưng nếu governance hiện tại đã revoke quyền principal trước khi resume → resume phải DENY đúng như Phase 5 case gốc (case C tương tự), KHÔNG được LangGraph tự động resume vì đã có "interrupt value" persisted.
4. Ghi kết quả vào `docs/architecture/langgraph_spike_results.md` (tiếp tục file đã tạo ở Phase 3) — đây là 1 trong các item của acceptance matrix HL-01→HL-18 sẽ được tổng hợp và quyết định ở Phase 6.

**Không làm ở Phase 5:** không quyết định adopt/reject LangGraph — vẫn là Phase 6.

## Definition of Done — Phase 5

**Gốc:**
- Test: 2 lời gọi cùng 1 tool trong cùng Run (vd. `send_email` gọi 2 lần) có 2 approval độc lập, evidence không cross lẫn nhau.
- Test: sau khi approve rồi tenant bị suspend trước khi resume → resume phải DENY, không dùng lại evidence cũ mù quáng.
- Approval survive qua test process-thật (kill process giữa lúc `WAITING_APPROVAL`, subprocess mới load lại đúng approval).

**Bổ sung:**
- (Nếu spike tiếp diễn) test `interrupt()` không bypass governance re-evaluation — log trong `langgraph_spike_results.md`.

## Rủi ro/lưu ý

**Gốc:** Phase này phụ thuộc chặt vào chất lượng `ExecutionTargetSnapshot` và accumulator từ các phase trước — nếu phát hiện thiếu field khi implement, quay lại bổ sung Phase 1/4 thay vì patch tạm ở đây.

**Bổ sung:** Rủi ro riêng của phần LangGraph: dễ nhầm "graph đã resume đúng theo LangGraph checkpoint" với "approval đã hợp lệ theo COSA governance" — đây là 2 điều khác nhau, phải test riêng biệt, không suy diễn cái này từ cái kia.
