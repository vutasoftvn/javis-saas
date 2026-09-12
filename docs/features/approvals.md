# Unified Approvals & Governance Ledger

## 1. Mục đích

Sổ cái phê duyệt hợp nhất (Unified Governance Ledger) cho cả 2 loại phê duyệt:
1. **`TOOL_CALL` (Run-bound)**: Gắn chặt với bộ ba bất biến `(run_id, tool_call_id, checkpoint_ref)` — không lookup theo tên action, không dùng token bypass vĩnh viễn.
2. **`CHANGE_REQUEST` (Hash-bound)**: Phê duyệt thay đổi tài nguyên không phụ thuộc run cụ thể (vd. thăng hạng Custom Skill Candidate lên catalog sản xuất). Gắn chặt với `(workspace_id, action, subject_kind, subject_ref, subject_hash)` và thẩm quyền Founder.

## 2. Khi nào sử dụng

- **`TOOL_CALL`**: Khi `CapabilityGateway`/kernel đánh giá governance = `REQUIRE_APPROVAL` trong quá trình thực thi run. Reviewer gọi `POST /agent/approvals/{id}/decision`.
- **`CHANGE_REQUEST`**: Khi người dùng đề xuất thay đổi cấu hình hoặc thăng cấp candidate (vd. `POST /agent/skills/{id}/promote`), trả về 202 `PENDING_APPROVAL` với `requirement={"role": "founder"}`.

## 3. Không dùng cho việc gì

- Không dùng approval cũ cho invocation mới (mỗi tool_call_id có approval riêng, không tái sử dụng qua tên action).
- Không tự động kích hoạt publication ngay trong request approval: `APPROVED` **tuyệt đối không đồng nghĩa với `PUBLISHED`**.
- Quyết định phê duyệt chỉ chuyển bản ghi sang trạng thái sẵn sàng để worker kéo qua hàng đợi outbox bền vững (`agent.approval_action_outbox`).

## 4. Kiến trúc và luồng dữ liệu

### 4.1 State Machine của Change Request / Skill Promotion

```text
PENDING_APPROVAL -> APPROVED_DISPATCH_PENDING -> ACTION_RUNNING -> PUBLISHED
PENDING_APPROVAL -> REJECTED
APPROVED_DISPATCH_PENDING | ACTION_RUNNING -> FAILED_REQUIRES_ATTENTION
```

### 4.2 Luồng xử lý Change Request

1. **Request Promotion**: Client gọi `POST /agent/skills/{id}/promote`. Hệ thống kiểm tra candidate đạt `EVALUATED` với điểm >= 0.70 và capabilities hợp lệ, tính canonical definition hash, lưu `CHANGE_REQUEST` approval ở trạng thái `pending`.
2. **Founder Decision**: Founder gọi `POST /agent/approvals/{id}/decision`. Hệ thống thực hiện CAS nguyên tử (`decide_change_approval_and_enqueue`), cập nhật status=`approved`, ghi nhận event `approval.decided`, và đẩy 1 bản ghi vào `agent.approval_action_outbox`.
3. **Durable Relay**: Worker định kỳ chạy `relay_approved_actions`, claim các outbox rows hợp lệ (`FOR UPDATE SKIP LOCKED`) và lập lịch tác vụ `approval_action` vào queue.
4. **Idempotent Execution**: Worker handler `execute_skill_candidate_promotion` kiểm tra an toàn qua `verify_change_execution`, xác minh candidate definition hash không bị trôi (stale check), và thực hiện CAS `publish_candidate_if_approved` để đưa candidate sang `PUBLISHED`. Bất kỳ lần retry/chạy lại nào đều là idempotent.

## 5. Public contracts & Data Models

- `agent.capabilities.approval_service.DurableApprovalService` (alias `ApprovalService`)
- `ApprovalSubject(kind, ref, definition_hash)`
- `RunApprovalRecord` với các trường mở rộng: `workspace_id`, `binding_kind` (`TOOL_CALL` | `CHANGE_REQUEST`), `subject_kind`, `subject_ref`, `subject_hash`.
- `SkillCandidate` với CAS metadata: `definition_hash`, `promotion_approval_id`, `promotion_definition_hash`.
- `ApprovalActionResult(success, reason_code, candidate)`.

## 6. Database / Schema liên quan

- `agent.approvals`: Lưu trữ toàn bộ phê duyệt (migration 004 & 006).
- `agent.approval_events`: Audit log append-only cho mọi sự kiện phê duyệt (migration 006).
- `agent.approval_action_outbox`: Hàng đợi transactional outbox để worker thực thi sau phê duyệt (migration 006).
- `agent.agent_skill_candidates`: Bảng candidate với partial unique index trên `promotion_approval_id` và CAS update (migration 007).
- `agent.agent_skill_feedback`: Đánh giá phản hồi người dùng cho custom skills (migration 007).

## 7. Security & Governance

- Phân quyền Founder bắt buộc cho mọi custom skill promotion (`requirement={"role": "founder"}`).
- Chống trôi đối tượng (Stale Subject Attack): Nếu proposed skill bị chỉnh sửa sau khi tạo approval, worker từ chối thực thi với mã lỗi `APPROVAL_SUBJECT_STALE`.
- Cách ly Workspace (Tenant Isolation): Approval của workspace A không thể áp dụng cho workspace B (`CANDIDATE_NOT_FOUND` / 403 Forbidden).
- Opaque Audit Payloads: Event log và audit stream không bao giờ chứa raw instructions, candidate code, hoặc secrets.

## 8. Troubleshooting & Vận hành

Khi tra cứu sự cố trong sổ cái:
- Chỉ truy vấn các cột an toàn: `approval_id`, `workspace_id`, `action`, `status`, `subject_hash`, `reason_code`.
- Kiểm tra outbox bị kẹt:
  ```sql
  SELECT outbox_id, approval_id, state, attempt_count, next_attempt_at
  FROM agent.approval_action_outbox
  WHERE state != 'delivered';
  ```
- Kiểm tra candidate đã được publish bởi approval nào:
  ```sql
  SELECT candidate_id, status, definition_hash, promotion_approval_id, published_at
  FROM agent.agent_skill_candidates
  WHERE workspace_id = :workspace_id AND candidate_id = :candidate_id;
  ```

## 9. Verification Suite

Chạy bộ kiểm thử phê duyệt hợp nhất (bao gồm cả cross-process PostgreSQL recovery E2E):
```bash
make unified-approval-verify
```
