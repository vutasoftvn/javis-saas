# Approvals

## 1. Mục đích

Human-in-the-loop approval bind chính xác vào `(run_id, tool_call_id, checkpoint_ref)` — không lookup theo tên action, không dùng `{"approved": true}` làm bypass token vĩnh viễn.

## 2. Khi nào sử dụng

Khi `CapabilityGateway`/kernel đánh giá governance = `REQUIRE_APPROVAL`. Reviewer gọi `POST /agent/approvals/{id}/decision` (`apps/cosa/api/routes.py`).

## 3. Không dùng cho việc gì

Không dùng approval cũ cho invocation mới (mỗi tool_call_id có approval riêng, không tái sử dụng qua tên action).

## 4. Kiến trúc và luồng dữ liệu

```
submit_decision(approval_id, reviewer, approved)
  → repo.get_approval() [đọc, không CAS]
  → repo.decide_approval() [CAS: WHERE status='pending', tăng decision_version]
  → nếu CAS fail (đã tồn tại nhưng không còn pending) → ApprovalAlreadyDecidedError
  → append event approval.decided
```

Trước khi resume (`verify_and_prepare_resume`): kiểm tra tồn tại Run/ToolCall/Checkpoint/Approval khớp đúng identity → kiểm tra `status == 'approved'` → kiểm tra ambient governance tươi (tenant/principal/emergency lock) → kiểm tra target drift (connector/schema đổi) → re-evaluate policy hiện tại.

## 5. Public contracts/API

`agent_core.capabilities.approval_service.DurableApprovalService`, `ApprovalAlreadyDecidedError` (409, phân biệt với "not found" 404).

## 6. Database/schema liên quan

`agent_core.approvals` (FK composite `(run_id, tool_call_id)`, cột `decision_version` cho CAS — migration `004_harden_exact_invocation_and_approval.sql`).

## 7. Cấu hình

Không có config riêng — dùng chung `RunRepository`.

## 8. Ví dụ sử dụng

```python
try:
    decided = await approval_service.submit_decision(approval_id=..., reviewer=..., approved=True)
except ApprovalAlreadyDecidedError as exc:
    # 409 — đã có quyết định khác thắng cuộc đua CAS
    ...
```

## 9. Cách bổ sung implementation mới

Không cần — `DurableApprovalService` là implementation duy nhất, dùng qua `RunRepository` Protocol nên tự động hoạt động với cả InMemory/Postgres.

## 10. Security/governance

CAS (`decision_version`) chặn double-decision race — 2 request cùng quyết định 1 approval, đúng 1 cái thắng.

## 11. Error handling

`ApprovalAlreadyDecidedError` — route handler map sang HTTP 409, không phải 404 (approval TỒN TẠI, chỉ là đã bị quyết định).

## 12. Observability

Event `approval.required`/`approval.decided`/`approval.resolved`.

## 13. Testing

`tests/agent_core/capabilities/test_approval_service.py` (bao gồm `test_decide_approval_is_atomic_cas_exactly_one_decision_wins`).

## 14. Migration/backward compatibility

`decision_version` column additive (migration 004), default 0.

## 15. Troubleshooting

Approval "biến mất" (404) khi resubmit: kiểm tra đã bị quyết định trước đó chưa — response cũ (trước fix) coi double-submit là "not found" sai nghĩa, giờ trả đúng 409.

## 16. Definition of Done

- [x] CAS, typed exception, test, HTTP status code đúng nghĩa
- [ ] Chạy trên Postgres thật với concurrency thật (InMemory test không chứng minh interleaving thật)
