# Runbook: Rollout & Rollback Quy Trình Khởi Tạo Đội Ngũ Khởi Nghiệp (Project Startup Team)

**Kế hoạch triển khai:** `docs/superpowers/plans/2026-09-11-default-project-and-startup-team.md`  
**Thiết kế kỹ thuật:** `docs/superpowers/specs/2026-09-11-startup-default-context-and-workforce-design.md`  
**Mục đích:** Hướng dẫn vận hành, kiểm tra tiền điều kiện, thực thi migration 005, giám sát sau triển khai và quy trình rollback an toàn cho tính năng Đội ngũ khởi nghiệp theo Dự án (Project Startup Team).

---

## 1. Nguyên Tắc & Giới Hạn Bất Biến

> [!IMPORTANT]
> - **Chân lý kinh doanh (Business Truth):** Company service là nguồn sự thật duy nhất cho `strategy.projects`, `operating.project_agent_assignments`, và `operating.project_agent_assignment_events`. Flutter và Agent Platform không tự ý suy diễn hoặc bỏ qua phân quyền.
> - **Lập trình (`coding`):** Luôn ở trạng thái `DEFERRED_CODING`. Không được phép kích hoạt trong giai đoạn này.
> - **CRM & Bán hàng (`crm`, `sales`):** Ở trạng thái `PENDING_CRM_FOUNDATION`. Chỉ kích hoạt khi có nền tảng CRM.
> - **Hỗ trợ khách hàng (`customer_support`):** Ở trạng thái `PENDING_PROJECT_KNOWLEDGE`. Chỉ kích hoạt khi có tri thức dự án.
> - **Rollback an toàn:** Rollback tuyệt đối **KHÔNG xoá lịch sử sự kiện** (`project_agent_assignment_events`) và **KHÔNG tự động bật lại** các agent đã bị Founder tạm dừng (`PAUSED`).

---

## 2. Tiền Kiểm Tra Trước Triển Khai (Pre-flight Checks)

### 2.1. Kiểm tra tính toàn vẹn của Catalog Contract Generator
Xác nhận catalog profiles và các file sinh khớp nhau 100%:
```bash
node scripts/gen-startup-team-profiles.mjs
git diff --exit-code shared/contracts/
```

### 2.2. Kiểm tra sao lưu và khôi phục trên môi trường dùng một lần (Disposable Backup/Restore)
Trước khi chạy migration trên production:
1. Tạo bản sao lưu snapshot cơ sở dữ liệu `workspace`:
   ```bash
   pg_dump -h $DB_HOST -U $DB_USER -d workspace -F c -b -v -f /tmp/workspace_pre_migration_005.dump
   ```
2. Khôi phục thử nghiệm trên database tạm thời để chứng minh tính toàn vẹn:
   ```bash
   createdb -h $DB_HOST -U $DB_USER workspace_restore_verify
   pg_restore -h $DB_HOST -U $DB_USER -d workspace_restore_verify -v /tmp/workspace_pre_migration_005.dump
   dropdb -h $DB_HOST -U $DB_USER workspace_restore_verify
   ```

### 2.3. Kiểm tra tiền điều kiện Schema Database
Xác nhận bảng `strategy.projects` tồn tại và enum trạng thái đã sẵn sàng:
```sql
SELECT count(*) FROM information_schema.tables 
WHERE table_schema = 'strategy' AND table_name = 'projects';
```

---

## 3. Quy Trình Triển Khai Migration (Rollout Steps)

### 3.1. Áp dụng Migration 005
Chạy migration Encore trên Company service:
```bash
cd services/company
encore db migrate
```
Migration sẽ thực thi:
1. Tạo kiểu enum `operating.project_agent_assignment_state` ('TEMPLATE', 'ACTIVE', 'PAUSED', 'RETIRED').
2. Tạo bảng `operating.project_agent_assignments`.
3. Tạo bảng `operating.project_agent_assignment_events`.
4. Khởi tạo hàng loạt template cho tất cả dự án hiện hữu với 9 catalog profiles (`INSERT INTO operating.project_agent_assignments ... ON CONFLICT DO NOTHING`).

### 3.2. Đối soát số lượng bản ghi (Row-count Verification)
Xác nhận công thức: `Tổng số bản ghi assignments = Tổng số projects hiện hữu × 9 catalog profiles`:
```sql
WITH project_count AS (
  SELECT count(*) as total_projects FROM strategy.projects
),
assignment_count AS (
  SELECT count(*) as total_assignments FROM operating.project_agent_assignments
)
SELECT 
  p.total_projects,
  a.total_assignments,
  (p.total_projects * 9) as expected_assignments,
  CASE 
    WHEN a.total_assignments = (p.total_projects * 9) THEN 'MATCH'
    ELSE 'MISMATCH'
  END as validation_status
FROM project_count p, assignment_count a;
```

### 3.3. Kiểm tra sức khỏe Outbox Consumer & Event Relay
Đảm bảo worker tiêu thụ event outbox đang hoạt động bình thường:
```sql
SELECT 
  count(*) FILTER (WHERE status = 'PENDING') as pending_events,
  count(*) FILTER (WHERE status = 'FAILED') as failed_events,
  count(*) FILTER (WHERE status = 'PROCESSED') as processed_events
FROM integration.event_outbox
WHERE created_at > now() - interval '1 hour';
```

### 3.4. Kiểm tra mẫu chuyển trạng thái (Sampled Transition Trace)
1. Thử nghiệm trên 1 project test:
   - Kích hoạt profile `marketing` qua endpoint Founder:
     `POST /operations/projects/{projectId}/startup-team/marketing/activate` với `expectedVersion = 1`.
   - Kiểm tra `state = 'ACTIVE'` và `version = 2`.
   - Kiểm tra ghi nhận event `ASSIGNMENT_ACTIVATED` trong `operating.project_agent_assignment_events`.
   - Gọi endpoint run-authority:
     `GET /internal/operations/projects/{projectId}/startup-team/marketing/run-authority` với `x-service-token`.
     Phản hồi trả về mã 200 kèm `spec.hash`.
   - Tạm dừng profile `marketing`:
     `POST /operations/projects/{projectId}/startup-team/marketing/pause` với `expectedVersion = 2`.
   - Kiểm tra `state = 'PAUSED'` và `version = 3`.
   - Gọi lại endpoint run-authority: nhận phản hồi 404 (bị từ chối).

---

## 4. Quy Trình Rollback Khẩn Cấp (Emergency Rollback Plan)

> [!CAUTION]
> Tuyệt đối không `DROP TABLE` hoặc xoá bảng sự kiện `operating.project_agent_assignment_events` nếu sự cố phát sinh sau khi hệ thống đã đi vào hoạt động. Cần tuân thủ quy trình rollback 3 giai đoạn:

### Giai Đoạn 1: Chặn Kích Hoạt Mới (Stop New Activations)
Nếu phát hiện lỗi nghiêm trọng:
1. Đặt cờ tính năng hoặc cập nhật API gateway để từ chối các request tới:
   - `POST /operations/projects/:projectId/startup-team/:profileKey/activate`
2. Tất cả agent đang chạy giữ nguyên trạng thái hoặc có thể chuyển sang `PAUSED` nếu có rủi ro bảo mật:
   ```sql
   UPDATE operating.project_agent_assignments
   SET state = 'PAUSED',
       disabled_reason = 'Khẩn cấp tạm dừng do quy trình rollback hệ thống',
       version = version + 1,
       updated_at = now()
   WHERE state = 'ACTIVE';
   ```

### Giai Đoạn 2: Vô hiệu hóa phân quyền Agent Platform (Revoke Run Authorities)
Agent Platform sẽ tự động từ chối chạy cho các agent không ở trạng thái `ACTIVE` (fail-closed).
Xác nhận không còn agent nào có thể claim quyền chạy:
```bash
curl -s -H "X-Service-Token: $COSA_WORKER_SERVICE_TOKEN" \
  -H "X-Workspace-Id: $WS_ID" \
  "http://$COMPANY_HOST/internal/operations/projects/$PROJ_ID/startup-team/marketing/run-authority"
# Kết quả phải trả về 404
```

### Giai Đoạn 3: Rollback Schema (Chỉ khi cần phục hồi hoàn toàn trước khi có traffic thật)
Nếu rollback ngay trong cửa sổ bảo trì (chưa có traffic production):
```bash
cd services/company
encore db rollback
```
Script `005_project_startup_team.down.sql` sẽ thu hồi bảng `project_agent_assignment_events`, `project_agent_assignments` và enum `project_agent_assignment_state`.

---

## 5. Danh Mục Kiểm Tra Sau Triển Khai (Post-Release Verification Checklist)

- [ ] `make mvp-contracts-check` thành công.
- [ ] `make frontend-api-contract-check` thành công.
- [ ] `make company-boundary-check` thành công.
- [ ] `make encore-handler-boundary-check` thành công.
- [ ] Tất cả unit và integration test Flutter module `hologram_hub` đạt 100% pass.
- [ ] Bộ kiểm thử E2E `pytest tests/e2e/test_default_project_startup_team.py` đạt 5/5 pass.
- [ ] Không có exception liên quan đến `ProjectTeamAuthorityError` hoặc `409 Conflict` bất thường trong log của Worker.
