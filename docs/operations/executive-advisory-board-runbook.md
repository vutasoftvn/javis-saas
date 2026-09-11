# Executive Advisory Board Operations Runbook

Tài liệu vận hành, xử lý sự cố và kiểm toán an toàn cho Hội đồng Cố vấn Điều hành (Executive Advisory Board) theo Project.

---

## 1. Nguyên tắc Cốt lõi & Ranh giới Thẩm quyền

1. **Founder-Only Authority (`role_id == 'founder'`)**:
   - Chỉ người dùng mang vai trò Founder con người mới có quyền: chọn Preset, bật/tắt Advisor Role, khởi tạo/đóng khung Deliberation, và chốt Quyết định (`APPROVE`, `MODIFY`, `REJECT`, `TABLE`).
   - AI agent, Workspace Admin hoặc Member thông thường **không có quyền** thực hiện các thao tác trên.

2. **Advisory L1 Boundary (Read & Propose Only)**:
   - Các vai trò C-level (`cfo`, `cmo`, `cto`, `ciso`, ...) chỉ có thẩm quyền tư vấn (L1).
   - Tên vai trò **không cấp quyền thực thi** (Zero effectful tool access). Cố vấn không thể tự động chuyển tiền, duyệt chi, phát hành chiến dịch hoặc sửa đổi hạ tầng.
   - Mọi đề xuất hành động từ Cố vấn đều được gắn cờ `NOT_EXECUTED` và yêu cầu quy trình con người tách biệt để thực thi.

3. **Isolate Analysis Without Peer Contamination**:
   - Agent Platform chạy các advisor hoàn toàn độc lập (`ExecutiveBoardRunner`).
   - Cố vấn không nhìn thấy bản nháp của các cố vấn khác trong pha phân tích, ngăn chặn hiện tượng hội tụ sớm hoặc ảo giác dây chuyền.

4. **Company-Owned Deliberation Ledger**:
   - Company service là nguồn sự thật duy nhất cho sổ cái nghị sự (`project_executive_deliberations`, `project_executive_deliberation_frames`, `project_executive_deliberation_analyses`, `project_executive_deliberation_decisions`).
   - Tất cả chuyển đổi trạng thái dùng cơ chế Compare-And-Swap (CAS) với `version` và outbox event transactional.

---

## 2. Vòng đời Nghị sự (Deliberation Lifecycle)

```
[ DRAFT ]
    │
    ▼ (Founder frames question & pinned roles)
[ FRAMED / ANALYSIS_QUEUED ]
    │
    ▼ (Worker executes isolated analyses)
[ ANALYZING ] ──► (All analyses submitted via signed callback)
    │
    ▼
[ AWAITING_FOUNDER ] ──► (Founder records decision: APPROVE / MODIFY / REJECT / TABLE)
    │
    ▼
[ DECIDED ]

* Nhánh hủy: Tại bất kỳ thời điểm nào trước khi DECIDED, Founder có thể chuyển sang [ CANCELLED ].
* Nhánh quá hạn: Nếu quá deadline quy định, nghị sự chuyển sang [ EXPIRED ].
```

---

## 3. Quy trình Xử lý Sự cố (Troubleshooting)

### 3.1 Deliberation bị kẹt ở trạng thái `ANALYSIS_QUEUED` hoặc `ANALYZING`
**Hiện tượng**: Nghị sự không chuyển sang `AWAITING_FOUNDER` sau một khoảng thời gian dài.

**Nguyên nhân & Kiểm tra**:
1. **Kiểm tra Outbox Dispatcher**:
   ```sql
   SELECT id, event_type, status, retry_count, last_error
   FROM outbox_events
   WHERE event_type = 'executive.deliberation.framed.v1'
     AND status != 'DISPATCHED';
   ```
   Nếu sự kiện chưa được gửi đến worker, kiểm tra tiến trình `outbox-worker`.

2. **Kiểm tra Worker Logs**:
   Lọc log của `cosa-worker` theo `deliberation_id`:
   ```bash
   grep "executive_board" logs/cosa-worker.log | grep "<DELIBERATION_ID>"
   ```
   Kiểm tra lỗi gọi API authority hoặc model routing timeout.

3. **Advisor Role Bị Thu Hồi Giữa Chừng**:
   Nếu một vai trò cố vấn bị Founder tắt (`DISABLED`) hoặc phân công Startup Team bị thu hồi sau khi frame:
   - Worker khi gọi `GET /internal/operations/projects/:id/deliberations/:id/authority` sẽ nhận HTTP 400 (`failed_precondition: Role is no longer ACTIVE`).
   - Worker sẽ dừng phân tích cho role đó.

4. **Hủy Khẩn cấp (Emergency Cancellation)**:
   Nếu cần giải phóng nghị sự bị nghẽn:
   ```bash
   curl -X POST "$COMPANY_URL/operations/projects/$PROJECT_ID/deliberations/$DELIB_ID/cancel" \
     -H "Authorization: Bearer $FOUNDER_TOKEN" \
     -H "X-Workspace-Id: $WORKSPACE_ID" \
     -H "Content-Type: application/json" \
     -d '{"reason": "Cancelled due to worker timeout"}'
   ```

### 3.2 Xử lý Lỗi Từng phần (Partial Advisor Failure)
- Nếu một hoặc một số advisor gặp lỗi (ví dụ LLM rate limit hoặc model context length exceeded), worker gửi callback dạng `executive.analysis.failed.v1` với `error_reason`.
- Company service ghi nhận bản ghi phân tích trạng thái `FAILED`.
- Khi tất cả các role đã gửi kết quả (kể cả thành công hoặc thất bại), nghị sự vẫn chuyển sang `AWAITING_FOUNDER`.
- Giao diện Flutter hiển thị trung thực role nào phân tích thành công và role nào gặp sự cố, cho phép Founder đọc các ý kiến đã có hoặc frame lại vòng mới.

### 3.3 Trùng lặp Callback & Consumer Restart (Duplicate Callbacks & Replays)
- Endpoint callback `/internal/operations/projects/:id/deliberations/:id/callback` là **hoàn toàn idempotent**.
- Nếu worker bị crash và khởi động lại, việc gửi lại callback giống hệt sẽ trả về `200 OK` với ID bản ghi đã tồn tại mà không ghi đè hoặc nhảy bước trạng thái máy ảo.

---

## 4. Quy trình Quản trị Vai trò Cố vấn (Advisor Role Operations)

### 4.1 Kích hoạt Vai trò mới
Chỉ kích hoạt được khi vai trò ở trạng thái `AVAILABLE_NOT_ACTIVATED` (hồ sơ Startup Team tương ứng đã `ACTIVE` và có `specHash` hợp lệ):
```bash
curl -X POST "$COMPANY_URL/operations/projects/$PROJECT_ID/executive-roles/$ROLE_KEY/activate" \
  -H "Authorization: Bearer $FOUNDER_TOKEN" \
  -H "X-Workspace-Id: $WORKSPACE_ID" \
  -H "Content-Type: application/json" \
  -d '{"expectedVersion": 1}'
```

### 4.2 Tắt hoặc Tạm dừng Vai trò Khẩn cấp
Khi phát hiện nghi vấn chất lượng tư vấn hoặc cần tái cấu trúc:
```bash
curl -X POST "$COMPANY_URL/operations/projects/$PROJECT_ID/executive-roles/$ROLE_KEY/disable" \
  -H "Authorization: Bearer $FOUNDER_TOKEN" \
  -H "X-Workspace-Id: $WORKSPACE_ID" \
  -H "Content-Type: application/json" \
  -d '{"expectedVersion": 2, "reason": "Audit review required"}'
```
Ngay sau khi tắt:
- Giao diện chuyển sang trạng thái `DISABLED`.
- Vai trò không thể được chọn trong các phiên Deliberation mới.
- Các phiên đang phân tích của vai trò này sẽ bị từ chối quyền truy cập khi worker xác thực authority.

---

## 5. Danh mục Kiểm toán Cách ly & Bảo mật (Audit Checklist)

- [ ] **Catalog Code-Owned**: Xác nhận không có bản ghi role tùy tiện trong runtime database; mọi role phải thuộc `shared/contracts/executive-advisor-roles.json`.
- [ ] **Cross-Tenant Evidence Check**: Đảm bảo toàn bộ `evidenceSources` bắt đầu bằng `project://<CURRENT_PROJECT_ID>/` hoặc `workspace://<CURRENT_WORKSPACE_ID>/`. Tuyệt đối không chấp nhận tham chiếu tới project/workspace khác (được kiểm tra tự động và từ chối bằng HTTP 403).
- [ ] **Internal Token Verification**: Endpoint nội bộ `/internal/operations/...` yêu cầu đúng `X-Service-Token` hoặc `Authorization: Bearer <service-token>`.
- [ ] **UI Truthfulness**: Frontend Flutter không hiển thị nút "Kích hoạt" cho vai trò `UNAVAILABLE` (như `chief_of_staff`), không hiển thị thành công ảo khi API trả lỗi.
