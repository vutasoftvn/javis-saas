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

### 4.3 Điều kiện Tiên quyết Vận hành cho COO và Chief of Staff (Operations Prerequisite for COO / Chief of Staff)

Hai vai trò điều hành cấp cao `chief_of_staff` và `coo` có ranh giới thẩm quyền gắn liền với hồ sơ `operations` trong Startup Team. Khác với `founder_assistant` (Co-Founder chat đồng hành mang tính hội thoại độc lập, không có thẩm quyền chạy tác vụ nền), `operations` là agent vận hành có thẩm quyền chạy được quản trị độc lập (`cosa.agents.operations`).

Quy trình kích hoạt và vận hành chuẩn gồm 5 bước:

1. **Đọc danh sách Startup Team và xác minh `operations`**:
   - Gọi `GET /operations/projects/:id/startup-team`.
   - Kiểm tra `operations` có `displayState == 'TEMPLATE'` và `runtimeReadiness == 'READY'`.
   - Lưu ý: Co-Founder (`founder_assistant`) là chat-only, không thể và không cần kích hoạt để mở khóa COO/Chief of Staff.
2. **Kích hoạt `operations` bằng version quan sát được**:
   - Gọi `POST /operations/projects/:id/startup-team/operations/activate` với `expectedVersion`.
   - `operations` chuyển sang `ACTIVE` và ghi nhận audit event `ASSIGNMENT_ACTIVATED`.
3. **Đọc lại danh sách Executive Roles, xác minh `AVAILABLE_NOT_ACTIVATED`**:
   - Gọi `GET /operations/projects/:id/executive-roles`.
   - Xác nhận `chief_of_staff` và `coo` chuyển từ `UNAVAILABLE` sang `AVAILABLE_NOT_ACTIVATED`.
   - **Tuyệt đối không tự động chuyển thành `ACTIVE`**: Việc kích hoạt hồ sơ vận hành không cấp quyền tư vấn mặc định cho bất kỳ vai trò cố vấn nào.
4. **Kích hoạt vai trò được chọn hoặc chọn preset bằng version quan sát được**:
   - Gọi `POST /operations/projects/:id/executive-roles/:roleKey/activate` với `expectedVersion` tương ứng của role, hoặc gọi chọn preset `startup-build-launch`.
   - Sau bước này, vai trò mới trở thành `ACTIVE` và sẵn sàng được đưa vào phiên Deliberation.
5. **Dừng vận hành an toàn (Stop work)**:
   - Trước tiên vô hiệu hóa vai trò cố vấn (`POST .../disable`).
   - Sau đó tạm dừng `operations` (`POST /operations/projects/:id/startup-team/operations/pause`).
   - Kiểm tra lại authority: mọi yêu cầu chạy mới đều bị từ chối (HTTP 404/409) trong khi toàn bộ sổ cái lịch sử (deliberation, analyses, audit events) vẫn được lưu giữ nguyên vẹn để kiểm toán.

> [!IMPORTANT]
> **Quy tắc Migration 007 Down**:
> File migration `007_operations_startup_profile.down.sql` được thiết kế **fail-closed**. Rollback migration 007 chỉ được phép thực hiện trong giai đoạn **trước khi sử dụng (pre-use)**. Nếu đã có bằng chứng kích hoạt, phân công hoặc sự kiện liên quan tới `operations`, migration down sẽ **từ chối thực thi**. Sau khi đã đưa vào sử dụng, chỉ được khắc phục tiến tới (remediate forward) hoặc tạm dừng/vô hiệu hóa (`PAUSED`/`DISABLED`), tuyệt đối không được cưỡng chế xóa dữ liệu.


---

## 5. Danh mục Kiểm toán Cách ly & Bảo mật (Audit Checklist)

- [ ] **Catalog Code-Owned**: Xác nhận không có bản ghi role tùy tiện trong runtime database; mọi role phải thuộc `shared/contracts/executive-advisor-roles.json`.
- [ ] **Cross-Tenant Evidence Check**: Đảm bảo toàn bộ `evidenceSources` bắt đầu bằng `project://<CURRENT_PROJECT_ID>/` hoặc `workspace://<CURRENT_WORKSPACE_ID>/`. Tuyệt đối không chấp nhận tham chiếu tới project/workspace khác (được kiểm tra tự động và từ chối bằng HTTP 403).
- [ ] **Internal Token Verification**: Endpoint nội bộ `/internal/operations/...` yêu cầu đúng `X-Service-Token` hoặc `Authorization: Bearer <service-token>`.
- [ ] **UI Truthfulness**: Frontend Flutter không hiển thị nút "Kích hoạt" cho vai trò `UNAVAILABLE` (như `chief_of_staff`), không hiển thị thành công ảo khi API trả lỗi.

---

## 6. Sổ cái Phê duyệt Hợp nhất & Thăng hạng Custom Skill Candidate

### 6.1 Mô hình Trạng thái Vận hành (Operator State Model)

```text
PENDING_APPROVAL -> APPROVED_DISPATCH_PENDING -> ACTION_RUNNING -> PUBLISHED
PENDING_APPROVAL -> REJECTED
APPROVED_DISPATCH_PENDING | ACTION_RUNNING -> FAILED_REQUIRES_ATTENTION
```

> **QUY TẮC BẤT DI BẤT DỊCH**: Trạng thái `APPROVED` **tuyệt đối không đồng nghĩa với `PUBLISHED`**.
> Việc Founder duyệt mới chỉ đưa yêu cầu vào trạng thái sẵn sàng (`APPROVED_DISPATCH_PENDING`). Worker tiến hành xác minh an toàn qua CAS nguyên tử trước khi chuyển sang `PUBLISHED`.

### 6.2 Truy vấn Kiểm toán & Giám sát An toàn (Safe Audit Queries)

Khi kiểm tra và xử lý sự cố trong sổ cái phê duyệt, **chỉ truy vấn các trường định danh, người phê duyệt, trạng thái, hash và lý do an toàn**. Tuyệt đối không đọc hoặc xuất thô instructions, candidate code, hay bí mật hệ thống.

1. **Kiểm tra các yêu cầu phê duyệt đang chờ hoặc mới quyết định**:
   ```sql
   SELECT approval_id, workspace_id, action, binding_kind, status, subject_kind, subject_ref, subject_hash, created_at
   FROM agent.approvals
   WHERE workspace_id = :workspace_id
   ORDER BY created_at DESC
   LIMIT 20;
   ```

2. **Kiểm tra hàng đợi Outbox của các hành động sau phê duyệt**:
   ```sql
   SELECT outbox_id, approval_id, action, subject_kind, subject_ref, state, attempt_count, next_attempt_at, delivered_at
   FROM agent.approval_action_outbox
   WHERE workspace_id = :workspace_id
   ORDER BY created_at DESC;
   ```

3. **Kiểm tra trạng thái Candidate và bằng chứng thăng hạng**:
   ```sql
   SELECT candidate_id, skill_id, status, eval_score, definition_hash, promotion_approval_id, promotion_definition_hash, published_at
   FROM agent.agent_skill_candidates
   WHERE workspace_id = :workspace_id AND candidate_id = :candidate_id;
   ```

4. **Sự cố Stale Subject / Lỗi Thăng hạng**:
   - Nếu worker ghi nhận lỗi `APPROVAL_SUBJECT_STALE`: Candidate đã bị chỉnh sửa nội dung sau khi Founder xem xét và tạo phê duyệt. Yêu cầu Founder kiểm tra lại và thực hiện quy trình đánh giá/phê duyệt mới.
   - Nếu hàng đợi outbox bị kẹt ở `pending`/`claimed` quá hạn: Kiểm tra tiến trình `cosa-worker` có đang chạy hàm `relay_approved_actions` hay không.

---

## 7. Vòng lặp Cải tiến Skill từ Phản hồi (Feedback-Driven Skill Improvement Loop)

### 7.1 Mô hình Trạng thái Vận hành (Operator State Model)

```text
Feedback Received:
[ RECORDED / INSUFFICIENT_SAMPLES / STABLE ] ── (Chỉ lưu trữ quan sát & telemetry; không hứa hẹn công việc)
     │ (nếu aggregate_score giảm >= delta & đủ mẫu tối thiểu)
     ▼
[ DEGRADING ] ──► Ghi nhận SkillImprovementRequest & Outbox Event

Asynchronous Worker Cycle:
[ QUEUED ] ── (Durable request & outbox sẵn sàng; chưa đánh giá, chưa tối ưu, chưa publish)
     │ (Worker claim outbox & request claim fence)
     ▼
[ RUNNING ] ── (Worker nắm giữ claim fence; có thể retry nếu hết hạn claim lease)
     ├─► [ CANDIDATE_CREATED ] ── (Đề xuất đã qua đánh giá nội bộ; BẮT BUỘC Founder duyệt mới publish)
     ├─► [ NOT_ELIGIBLE ] ────── (Không thỏa mãn baseline score / budget / cooldown; không tạo candidate)
     ├─► [ STALE ] ───────────── (Definition hash không còn khớp phiên bản ghim; hủy yêu cầu an toàn)
     └─► [ FAILED_REQUIRES_ATTENTION ] ── (Lỗi ngoại lệ/crash; kiểm tra safe reason code để điều tra)
```

### 7.2 Nguyên tắc Diễn giải An toàn (Safe Interpretation Rules)

1. **`aggregate_score` là Telemetry Sức khỏe, KHÔNG PHẢI `eval_score`**:
   - Điểm đánh giá phản hồi (`aggregate_score`) chỉ là tín hiệu giám sát cửa sổ trượt (windowed telemetry) từ người dùng.
   - Nó **tuyệt đối không bao giờ** được ghi đè trực tiếp vào `eval_score` hay làm thay đổi trực tiếp trạng thái của candidate.
   - `eval_score` của một candidate chỉ được tạo ra sau khi bộ tối ưu hóa độc lập (capability-empty, prompt/description-only) thực hiện đánh giá benchmark.

2. **`QUEUED`, `APPROVED`, `CANDIDATE_CREATED` KHÔNG BAO GIỜ có nghĩa là `PUBLISHED`**:
   - `QUEUED`: Yêu cầu đã được lưu bền vững vào DB và outbox, chưa hề có code hay prompt nào được tạo.
   - `CANDIDATE_CREATED`: Bộ tối ưu hóa đã đề xuất một candidate và vượt qua ngưỡng đánh giá nội bộ. Candidate này ở trạng thái `DRAFT` và **bắt buộc phải qua phê duyệt hợp nhất (Unified Approval / `CHANGE_REQUEST`) của Founder**.
   - `APPROVED`: Founder đã chấp thuận đề xuất nhưng worker chưa chạy bước CAS chuyển đổi nguyên tử sang `PUBLISHED`.

3. **Diễn giải Safe State & Safe Reason Codes**:
   - `RECORDED`, `INSUFFICIENT_SAMPLES`, `STABLE`: Phản hồi được lưu trữ thành công; không có tác vụ cải tiến nào được xếp lịch.
   - `DEGRADING`, `QUEUED`: Yêu cầu cải tiến bền vững đã tồn tại trong hàng đợi; chưa được đánh giá hay phát hành.
   - `RUNNING`: Worker đang giữ rào chắn claim (`claim_token` + `claimed_until`); nếu worker chết giữa chừng, scheduler sẽ cấp phát lại sau khi claim hết hạn.
   - `CANDIDATE_CREATED`: Đề xuất mới đã sẵn sàng cho Founder xem xét.
   - `NOT_ELIGIBLE`: Request không đạt tiêu chuẩn (ví dụ: cải thiện không vượt ngưỡng baseline tối thiểu, hết ngân sách lần thử, hoặc trong thời gian cooldown). Không gây ảnh hưởng tới runtime.
   - `STALE`: Hash định nghĩa skill hiện tại đã thay đổi so với khi tạo request; hệ thống hủy yêu cầu để tránh tối ưu hóa trên phiên bản cũ.
   - `FAILED_REQUIRES_ATTENTION`: Gặp lỗi runtime bất ngờ trong quá trình xử lý; operator cần kiểm tra `error_reason` trong DB.

### 7.3 Truy vấn Kiểm toán & Giám sát Vận hành (Audit Queries)

Chỉ truy vấn các trường định danh, hash, trạng thái và telemetry:

1. **Kiểm tra tình trạng phản hồi và điểm tích lũy theo Skill**:
   ```sql
   SELECT skill_id, skill_version, sample_count, positive_count, negative_count, aggregate_score, status, updated_at
   FROM agent.skill_feedback_aggregates
   WHERE workspace_id = :workspace_id
   ORDER BY updated_at DESC;
   ```

2. **Kiểm tra các yêu cầu cải tiến Skill (Requests & Fencing)**:
   ```sql
   SELECT request_id, skill_id, skill_version, definition_hash, status, trigger_kind, claim_token, claimed_until, updated_at
   FROM agent.skill_improvement_requests
   WHERE workspace_id = :workspace_id
   ORDER BY updated_at DESC
   LIMIT 20;
   ```

3. **Kiểm tra Outbox Dispatcher cho Skill Improvement**:
   ```sql
   SELECT outbox_id, request_id, event_type, status, attempt_count, next_attempt_at, updated_at
   FROM agent.skill_improvement_outbox
   WHERE workspace_id = :workspace_id
   ORDER BY created_at DESC;
   ```

4. **Kiểm tra lịch sử đánh giá đề xuất cải tiến (Evaluations & Mutations)**:
   ```sql
   SELECT evaluation_id, request_id, candidate_id, baseline_score, candidate_score, verdict, evaluation_hash, evaluated_at
   FROM agent.skill_improvement_evaluations
   WHERE workspace_id = :workspace_id
   ORDER BY evaluated_at DESC
   LIMIT 20;
   ```

5. **Xử lý sự cố Outbox bị kẹt hoặc Worker Crash**:
   - Nếu outbox có trạng thái `FAILED` hoặc `PENDING` nhưng không được dispatch: Đảm bảo `cosa-worker` đang gọi hàm `relay_skill_improvement_outbox`.
   - Nếu request ở trạng thái `RUNNING` nhưng worker đã chết: Sau khi `claimed_until` qua đi, worker loop kế tiếp hoặc task scheduler sẽ reclaim và thực thi lại an toàn nhờ tính lũy đẳng của request claim.

---

## 8. Runbook kiểm chứng E2E toàn Portfolio (8 role Executive Advisory Board)

Bổ sung 2026-09-13 (Task 5 — portfolio closeout gate, kế hoạch
`2026-09-12-caio-ai-governance-profile-and-executive-activation`). Mỗi role
trong 8 role mới (`cro/sales`, `vpe/coding`, `cpo/product`, `chro/people`,
`ciso/security`, `gc/legal`, `cdo/data`, `caio/ai_governance`) có 1 process E2E
riêng, chạy độc lập, không cần tham số bổ sung ngoài `.venv` đã cài. CAIO cần
disposable Postgres cluster thật (`PGPASSWORD` phải khớp `POSTGRES_PASSWORD`
thật trong `.env`, KHÔNG phải mặc định `"postgres"` của thư viện test).

```bash
source .venv/bin/activate

# 7 role không cần disposable Postgres cluster (dùng real_company_service fixture only)
PYTHONPATH=packages:. python -m pytest tests/e2e/test_cro_sales_profile.py -v
PYTHONPATH=packages:. python -m pytest tests/e2e/test_vpe_coding_profile.py -v
PYTHONPATH=packages:. python -m pytest tests/e2e/test_cpo_product_profile.py -v
PYTHONPATH=packages:. python -m pytest tests/e2e/test_chro_people_profile.py -v
PYTHONPATH=packages:. python -m pytest tests/e2e/test_ciso_security_profile.py -v
PYTHONPATH=packages:. python -m pytest tests/e2e/test_gc_legal_profile.py -v
PYTHONPATH=packages:. python -m pytest tests/e2e/test_cdo_data_profile.py -v

# CAIO — cần disposable Postgres cluster thật (boot services/cosa + Company)
export PGPASSWORD=dev-postgres-password   # khớp POSTGRES_PASSWORD thật trong .env, không phải "postgres"
PYTHONPATH=packages:. python -m pytest tests/e2e/test_caio_ai_governance_profile.py -v

# Portfolio-wide: không role/profile nào tự kích hoạt trên 1 Project mới tạo
PYTHONPATH=packages:. python -m pytest tests/e2e/test_executive_board_portfolio_closeout.py -v
```

Kỳ vọng: mỗi lệnh exit 0, không skip. Nếu CAIO báo lỗi
`password authentication failed for user "postgres"`, đó là do `PGPASSWORD`
chưa khớp `.env` thật — không phải lỗi code (xem
`docs/architecture/generated/` và memory `javis-saas-company-test-runner.md`).

### 8.1 Diễn giải kết quả gate rộng (`make verify`)

`make verify` chạy tuần tự (`lint typecheck-py boundary-check
skillpacks-validate tenancy-check contract-freeze-check agent-test
apps-cosa-test services-test frontend-test frontend-analyze check-docs`) và
**dừng ở target đỏ đầu tiên** — một target đỏ ở đầu chuỗi (vd. `lint`) không
có nghĩa các target sau nó cũng đỏ; phải chạy tách riêng từng target còn lại
để có bằng chứng đầy đủ. Xem
`## Portfolio Closeout Evidence (2026-09-13)` trong
`docs/superpowers/specs/2026-09-11-executive-advisory-board-completion-and-agent-platform-restructuring-design.md`
để biết baseline lỗi đã biết (pre-existing) tách bạch với phát hiện mới.
