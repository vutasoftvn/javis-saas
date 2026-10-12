# Runbook: Verifier hoàn thành task WGA

Mục đích: task AUTO của WGA chỉ tự đóng `done` khi kết quả đạt các tiêu chí bắt buộc trong `doneCriteria`. Bối cảnh và quyết định: [Dự án B](../superpowers/plans/2026-10-05-agent-structure-B-verifier-gate.md), kế hoạch: [impl plan](../superpowers/plans/2026-10-06-verifier-wga-completion-impl.md).

## Cờ

- `WGA_VERIFY_ON_COMPLETE=1` bật xác minh. Mặc định **tắt**, đọc lúc gọi (đổi biến môi trường rồi khởi động lại worker).
- Đi cặp với `WGA_REQUIRE_DONE_CRITERIA` (buộc LLM sinh tiêu chí khi phân rã mục tiêu). Bật cả hai là chế độ đầy đủ; chỉ bật cờ verify thì chỉ kiểm task đã có `doneCriteria`.
- Task không có `doneCriteria` hoặc cờ tắt: hành vi cũ, không kiểm.

## Ngữ nghĩa verdict (fail-closed)

| Verdict | Khi nào | Kết quả |
|---|---|---|
| PASS | mọi tiêu chí bắt buộc đạt | đóng `done`, evidence thêm `verification:<report_id>` |
| FAIL | có tiêu chí bắt buộc không đạt | giữ `in_progress`, note `verification_fail: ...` |
| INCONCLUSIVE | có tiêu chí bắt buộc không kiểm được (thẩm phán lỗi, hết ngân sách, không đọc được KR, tiêu chí hỏng, lỗi hạ tầng) | giữ `in_progress`, note `verification_inconclusive: ...` |

Mọi lỗi của verifier đều thành INCONCLUSIVE, không bao giờ làm task đóng nhầm hay làm sweep bị ngắt. Founder xác nhận thủ công bằng đường sẵn có.

## Phạm vi kiểm

- Lần chạy đầu của task **AUTO**, đường **resume** sau duyệt và task **`NEEDS_APPROVAL`** đều được kiểm khi cờ bật (`apps/cosa/worker/wga_run.py`: `_verify_completed_run`, `advance_wga_task_after_resume`, `fetch_task_agent_context`).
- PASS ở task `NEEDS_APPROVAL` **không** tự đóng task; việc đóng vẫn do người duyệt.
- Bật cờ mà không lấy được agent-context của task: task giữ `in_progress`, note `verification_inconclusive: context_unavailable`.
- Ở đường resume không có ảnh chụp trước lần chạy, nên `must_change` của `metric_gte` luôn cho INCONCLUSIVE `baseline_unavailable`.

## Hỗ trợ tiêu chí

| Tiêu chí | Ngữ nghĩa |
|---|---|
| `artifact_exists` (`kind?`, `display_name_contains?`) | chỉ tính artifact do **công cụ của agent** tạo ra; artifact "WGA task output" tự động của nền tảng không bao giờ được tính |
| `field_present` (`path` dạng `a.b.c`) | cần đầu ra dạng dict có cấu trúc; đầu ra chỉ có `{"response": ...}` thì INCONCLUSIVE |
| `metric_gte` (`key_result_id` string, `threshold` số hữu hạn không phải bool, `must_change?` bool) | đọc `currentValue` của KR qua `GET /operations/key-results` (capability ủy quyền `okr.objective.list`) và so với `threshold`; endpoint này trả **mọi** KR của workspace ở mỗi lần xác minh. Mã lý do: `metric_met`, `metric_below_threshold`, `metric_unavailable`, `baseline_unavailable`, `metric_unchanged`, `invalid_args`. `must_change: true` cần ảnh chụp trước lần chạy, chỉ có ở đường sweep ban đầu (không có ở resume, xem trên). Rủi ro đạt rỗng: KR đã vượt ngưỡng từ trước thì không có `must_change` sẽ PASS dù agent không làm gì; KR kiểu giảm (scoring giảm dần) cần ngưỡng riêng, v1 không đảo chiều |
| `rubric` | chấm bởi thẩm phán độc lập `cosa.agents.verifier` (một lần gọi cho mọi tiêu chí rubric) |

Tiêu chí `required: false` được ghi lại nhưng không chặn.

## Hiển thị

- Note founder thấy chỉ chứa **mã** (id tiêu chí và mã cố định), ví dụ `verification_fail: 0/1 tiêu chí bắt buộc đạt cb1(fail)`; không có lời giải thích tự do của thẩm phán.
- Chi tiết đầy đủ: bảng `agent.verification_reports` và `GET /agent/workforce/verification-reports?taskId=...` hoặc `?runId=...` (`limit` bị bỏ qua khi có `runId`). Hợp đồng `workforce.verification_reports.list` đã nằm trong `shared/contracts/mvp-surface.json`.
- Flutter: thẻ kanban có huy hiệu verdict, chạm mở sheet chi tiết; sheet chỉ hiện **mã lý do** (lời giải thích tự do của thẩm phán bị bộ lọc mẫu ở UI ẩn đi).
- API gộp cho bảng: `GET /agent/workforce/verification-reports?taskIds=1,2,3` (tối đa 50 id, trả báo cáo mới nhất của mỗi task; 422 nếu dùng chung với `taskId`/`runId`).
- Run event `verification.completed` trên run của producer, payload chỉ có id/mã: `verdict`, `report_id`, `mode`, `failed`, `unclear`.

## Chi phí

Thẩm phán chạy qua kernel với run id `<task_run_id>__verify` (retry: `__verify_retry1`); chi phí ghi ở `models.run_usage` và tính vào hạn mức workspace. Hết hạn mức ⇒ INCONCLUSIVE.

## Ép mô hình thẩm phán độc lập

Mặc định thẩm phán dùng route mặc định (có thể cùng mô hình với producer). Để ép mô hình khác, đặt policy scope `verifier` (khóa lưu `cosa.agents.verifier`; không phải profile công khai) qua REST model-policy, prefix `/agent/settings`:

```bash
# 1) có sẵn provider profile (vd tạo mới)
curl -X POST "$API/agent/settings/model-providers" -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"provider_type": "openai_api", "profile_id": "judge-model", "api_key": "<key>"}'

# 2) đặt policy cho thẩm phán
curl -X PUT "$API/agent/settings/model-policies/verifier" -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"primary_profile_id": "judge-model", "fallback_profile_ids": []}'

# 3) kiểm: data.scope_key == "cosa.agents.verifier", data.resolved_profile_id == "judge-model"
curl "$API/agent/settings/model-policies/verifier" -H "Authorization: Bearer $TOKEN"
```

Ví dụ lấy từ `tests/apps/cosa/api/test_model_policy_verifier_scope.py`. Chưa đặt policy thì `is_system_default` là true và thẩm phán dùng chung route mặc định.

## Triển khai và rollback

1. Bật `WGA_VERIFY_ON_COMPLETE=1` ở workspace dev trước, chạy sweep, xem báo cáo qua endpoint và log.
2. Theo dõi tỉ lệ FAIL/INCONCLUSIVE bất thường (nhiều INCONCLUSIVE thường là lỗi route/ngân sách thẩm phán).
3. Rollback: tắt cờ; task mới trở lại hành vi cũ. Báo cáo đã lưu giữ nguyên.

## Cập nhật sau review cuối

- **Prompt phân rã** giờ yêu cầu LLM dùng tiêu chí `rubric`: ở v1 `field_present`/`metric_gte` luôn INCONCLUSIVE và `artifact_exists` gần như luôn FAIL (chỉ công cụ tạo file/web_search mới sinh artifact), nên tiêu chí tất định chỉ dành cho việc agent chứng minh được bằng công cụ. Parser vẫn chấp nhận tiêu chí tất định do founder/nguồn khác đặt.
- **Timeout thẩm phán:** `WGA_VERIFY_JUDGE_TIMEOUT_SEC` (đọc lúc gọi; mặc định 120, kẹp 5..600, giá trị sai => mặc định). Hết giờ => tiêu chí rubric `UNCLEAR` mã `judge_timeout` => INCONCLUSIVE.
- **Cấp lại token ủy quyền** (TTL 600 s) ngay sau xác minh, trước khi advance/finalize, để run dài + thẩm phán không làm advance bị Company từ chối âm thầm.
- **Mất dấu vết kiểm toán:** nếu verdict là PASS nhưng không lưu được báo cáo (`report_id` rỗng) thì kết quả là INCONCLUSIVE, note `verification_inconclusive: report_store_failed`, task không đóng (sự kiện vẫn ghi best-effort).
- Mã lỗi thẩm phán cố định: `judge_output_invalid`, `judge_run_failed:<reason_code>`, `judge_timeout`, `judge_omitted`.

## Ràng buộc cần lưu ý (compliance)

Producer WGA và thẩm phán đều khai `model_input_capability_ref` mà không có `direct_message_data_access`, nên ở production cổng data-model hiện ném `DATA_ACCESS_CLAIM_MISSING` cho cả hai. Ai sửa claim cho producer WGA **phải** thêm cùng metadata vào `extra_metadata` của `run_judge`, nếu không mọi task có rubric đều INCONCLUSIVE.

## Giới hạn đã biết

- `reason` trong báo cáo là văn bản tự do của thẩm phán đã làm sạch (bỏ ký tự điều khiển, cắt độ dài), không đưa vào note.
- Nếu mọi tiêu chí đều `required: false` thì kết quả là PASS và task tự đóng.
- Báo cáo idempotent theo `(workspace, run_id)`; chạy lại cùng run không tạo báo cáo mới.

## Quan sát trước khi bật mặc định

**Trạng thái: mặc định `WGA_VERIFY_ON_COMPLETE` vẫn TẮT.** Đổi mặc định là cổng của người, chỉ làm sau khi chủ dự án ghi kết quả quan sát bên dưới. Không đổi mặc định `WGA_REQUIRE_DONE_CRITERIA` trong đợt này.

Truy vấn chỉ-đọc (chạy trên DB agent, thay `<ws>`):

```sql
-- Phân bố verdict theo ngày (cửa sổ quan sát)
SELECT date_trunc('day', created_at) AS day, verdict, count(*)
FROM agent.verification_reports
WHERE workspace_id = '<ws>' AND created_at >= now() - interval '14 days'
GROUP BY 1, 2 ORDER BY 1, 2;

-- Tỷ lệ INCONCLUSIVE theo nguyên nhân (mã lý do trong từng tiêu chí)
SELECT c->>'reason' AS reason, c->>'verdict' AS verdict, count(*)
FROM agent.verification_reports r, jsonb_array_elements(r.criteria_results) c
WHERE r.workspace_id = '<ws>' AND r.verdict = 'INCONCLUSIVE'
  AND r.created_at >= now() - interval '14 days'
GROUP BY 1, 2 ORDER BY 3 DESC;

-- Mẫu để duyệt tay: 20 báo cáo PASS gần nhất kèm task
SELECT report_id, task_id, run_id, mode, created_at
FROM agent.verification_reports
WHERE workspace_id = '<ws>' AND verdict = 'PASS'
ORDER BY created_at DESC LIMIT 20;
```

Tiêu chí quyết định (người duyệt có thể chỉnh):

- (a) Quan sát tối thiểu 14 ngày trên workspace dev/staging với `WGA_VERIFY_ON_COMPLETE=1` và `WGA_REQUIRE_DONE_CRITERIA=1`.
- (b) Ít nhất 30 báo cáo.
- (c) Tỷ lệ INCONCLUSIVE <= 20% và nguyên nhân chủ yếu không phải lỗi hạ tầng (`judge_timeout`, `context_unavailable`, `usage_budget_exceeded`).
- (d) Duyệt tay 20 báo cáo PASS: 0 trường hợp đạt sai (nội dung rõ ràng không thỏa tiêu chí).
- (e) Thẩm phán đã có policy mô hình riêng (mục "Ép mô hình thẩm phán độc lập") hoặc chấp nhận có chủ đích dùng chung route mặc định.

Kết quả quan sát (người duyệt điền; chưa có):

| Ngày | Số báo cáo | Tỷ lệ INCONCLUSIVE | Người duyệt | Kết luận |
|---|---|---|---|---|
| (chưa ghi) | | | | |
