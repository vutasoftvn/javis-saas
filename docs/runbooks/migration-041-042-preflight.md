# Pre-flight migration 041 / 042 (ràng buộc bảng automation)

Áp dụng cho DB `workspace`, schema `operating`: `automation_definitions`, `automation_revisions`,
`automation_invocations`, `automation_invocation_events`.

## Vì sao có thể làm hỏng deploy

- `041_restore_automation_constraints` thêm 4 FK, 4 CHECK và 4 unique index; `042_automation_composite_tenancy`
  thêm 3 unique `(id, workspace_id)` và 4 FK composite. Các ràng buộc được thêm `NOT VALID` rồi `VALIDATE`.
- Nếu còn dòng mồ côi, dòng tham chiếu chéo workspace, dòng trùng khoá hoặc giá trị ngoài CHECK, câu lệnh
  `VALIDATE`/`CREATE UNIQUE INDEX` lỗi, **cả file migration bị huỷ** và `make migrate-all` dừng, chặn deploy.
- Bảng này được tạo lại không ràng buộc ở `002_restore_baseline_gaps` nên môi trường đã chạy thật có thể chứa dữ liệu vi phạm.

## Truy vấn pre-flight (chỉ đọc, chạy trước deploy)

Kết quả mong đợi: mọi dòng có count = 0. Đã chạy thử trên DB dev (`workspace`) và test (`javis_workspace_test`):
cả 16 dòng đều 0 (chạy sau khi đã áp 041/042 nên 0 là hiển nhiên); đã chứng minh truy vấn phát hiện được
vi phạm bằng cách chèn dòng xấu trong transaction rồi rollback (orphan = 2, trùng = 1, CHECK sai = 1).

```sql
-- orphans (FK 041)
SELECT 'orphan revisions->definition' AS check, count(*) FROM operating.automation_revisions r LEFT JOIN operating.automation_definitions d ON d.id = r.definition_id WHERE d.id IS NULL
UNION ALL SELECT 'orphan invocations->definition', count(*) FROM operating.automation_invocations i LEFT JOIN operating.automation_definitions d ON d.id = i.definition_id WHERE d.id IS NULL
UNION ALL SELECT 'orphan invocations->revision', count(*) FROM operating.automation_invocations i LEFT JOIN operating.automation_revisions r ON r.id = i.revision_id WHERE r.id IS NULL
UNION ALL SELECT 'orphan events->invocation', count(*) FROM operating.automation_invocation_events e LEFT JOIN operating.automation_invocations i ON i.id = e.invocation_id WHERE i.id IS NULL
-- cross-workspace (FK 042)
UNION ALL SELECT 'cross-ws revisions->definition', count(*) FROM operating.automation_revisions r JOIN operating.automation_definitions d ON d.id = r.definition_id WHERE d.workspace_id <> r.workspace_id
UNION ALL SELECT 'cross-ws invocations->definition', count(*) FROM operating.automation_invocations i JOIN operating.automation_definitions d ON d.id = i.definition_id WHERE d.workspace_id <> i.workspace_id
UNION ALL SELECT 'cross-ws invocations->revision', count(*) FROM operating.automation_invocations i JOIN operating.automation_revisions r ON r.id = i.revision_id WHERE r.workspace_id <> i.workspace_id
UNION ALL SELECT 'cross-ws events->invocation', count(*) FROM operating.automation_invocation_events e JOIN operating.automation_invocations i ON i.id = e.invocation_id WHERE i.workspace_id <> e.workspace_id
-- duplicates (unique indexes)
UNION ALL SELECT 'dup definitions (ws,key) live', count(*) FROM (SELECT 1 FROM operating.automation_definitions WHERE deleted_at IS NULL GROUP BY workspace_id, automation_key HAVING count(*) > 1) x
UNION ALL SELECT 'dup revisions (definition,no)', count(*) FROM (SELECT 1 FROM operating.automation_revisions GROUP BY definition_id, revision_no HAVING count(*) > 1) x
UNION ALL SELECT 'dup invocations (ws,revision,idem)', count(*) FROM (SELECT 1 FROM operating.automation_invocations GROUP BY workspace_id, revision_id, idempotency_key HAVING count(*) > 1) x
UNION ALL SELECT 'dup events (ws,invocation,seq)', count(*) FROM (SELECT 1 FROM operating.automation_invocation_events GROUP BY workspace_id, invocation_id, seq HAVING count(*) > 1) x
-- CHECK violations
UNION ALL SELECT 'bad lifecycle_state', count(*) FROM operating.automation_definitions WHERE lifecycle_state NOT IN ('DRAFT','PUBLISHED','SUSPENDED','RETIRED')
UNION ALL SELECT 'bad autonomy_class', count(*) FROM operating.automation_revisions WHERE autonomy_class NOT IN ('read_only','draft_only','gated_effect')
UNION ALL SELECT 'bad trigger_kind', count(*) FROM operating.automation_invocations WHERE trigger_kind NOT IN ('manual','schedule','business_event')
UNION ALL SELECT 'bad state', count(*) FROM operating.automation_invocations WHERE state NOT IN ('REQUESTED','QUEUED','LEASED','RUNNING','WAITING_APPROVAL','COMPLETED','FAILED','CANCELLED','BLOCKED','CANCEL_REQUESTED');
```

## Khi có dòng vi phạm

1. Dừng deploy. Không tự động xoá.
2. Liệt kê chi tiết dòng vi phạm (bỏ `count(*)`, chọn `id`, `workspace_id`, các cột khoá) và xác định nguồn gốc.
3. Với mồ côi/chéo workspace: xác định parent đúng hoặc archive dòng sang bảng sao lưu có chủ sở hữu duyệt, rồi mới xử lý.
4. Với trùng khoá: giữ bản có `created_at` sớm nhất (invocation: bản đã có `agent_run_id`), archive bản còn lại.
5. Với giá trị ngoài CHECK: sửa theo bảng trạng thái hợp lệ (xem `tests/contracts/test_automation_contract.py`).
6. Chạy lại truy vấn pre-flight cho tới khi tất cả bằng 0, rồi deploy.

## Khoá và thời điểm chạy

- `CREATE UNIQUE INDEX` (không `CONCURRENTLY`) chặn ghi vào bảng đó trong thời gian ngắn; `ADD CONSTRAINT ... NOT VALID`
  chỉ lấy khoá ngắn, `VALIDATE CONSTRAINT` không chặn ghi. Chạy trong khung giờ thấp tải.
- Bảng automation nhỏ nên thời gian khoá dự kiến tính bằng giây; kiểm tra `SELECT count(*)` mỗi bảng trước khi chạy.

## Rollback

- `042_automation_composite_tenancy.down.sql` gỡ 4 FK composite rồi 3 unique `(id, workspace_id)`.
- `041_restore_automation_constraints.down.sql` gỡ index, CHECK và FK của 041.
- Chạy 042 down trước, rồi 041 down. Cả hai idempotent (`IF EXISTS`); đã kiểm chứng down rồi up lại trong transaction rollback trên DB test.
- 042 là expand-only: FK `id` đơn của 041 được giữ nguyên; migration contract sau này mới được phép gỡ chúng.
