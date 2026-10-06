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
| INCONCLUSIVE | có tiêu chí bắt buộc không kiểm được (thẩm phán lỗi, hết ngân sách, `metric_gte`, tiêu chí hỏng, lỗi hạ tầng) | giữ `in_progress`, note `verification_inconclusive: ...` |

Mọi lỗi của verifier đều thành INCONCLUSIVE, không bao giờ làm task đóng nhầm hay làm sweep bị ngắt. Founder xác nhận thủ công bằng đường sẵn có.

## Phạm vi kiểm

- Chỉ lần chạy đầu của task **AUTO**. Task `NEEDS_APPROVAL` và đường resume sau duyệt **không** kiểm (quyết định có chủ đích).

## Hỗ trợ tiêu chí

| Tiêu chí | Ngữ nghĩa |
|---|---|
| `artifact_exists` (`kind?`, `display_name_contains?`) | chỉ tính artifact do **công cụ của agent** tạo ra; artifact "WGA task output" tự động của nền tảng không bao giờ được tính |
| `field_present` (`path` dạng `a.b.c`) | cần đầu ra dạng dict có cấu trúc; đầu ra chỉ có `{"response": ...}` thì INCONCLUSIVE |
| `metric_gte` | v1 chưa đánh giá được, luôn INCONCLUSIVE |
| `rubric` | chấm bởi thẩm phán độc lập `cosa.agents.verifier` (một lần gọi cho mọi tiêu chí rubric) |

Tiêu chí `required: false` được ghi lại nhưng không chặn.

## Hiển thị

- Note founder thấy chỉ chứa **mã** (id tiêu chí và mã cố định), ví dụ `verification_fail: 0/1 tiêu chí bắt buộc đạt cb1(fail)`; không có lời giải thích tự do của thẩm phán.
- Chi tiết đầy đủ: bảng `agent.verification_reports` và `GET /agent/workforce/verification-reports?taskId=...` hoặc `?runId=...` (`limit` bị bỏ qua khi có `runId`). Endpoint **chưa** nằm trong `shared/contracts/mvp-surface.json` cho tới khi có màn hình Flutter dùng.
- Run event `verification.completed` trên run của producer, payload chỉ có id/mã: `verdict`, `report_id`, `mode`, `failed`, `unclear`.

## Chi phí

Thẩm phán chạy qua kernel với run id `<task_run_id>__verify` (retry: `__verify_retry1`); chi phí ghi ở `models.run_usage` và tính vào hạn mức workspace. Hết hạn mức ⇒ INCONCLUSIVE.

## Giới hạn độc lập mô hình

Thẩm phán dùng route mặc định (có thể cùng mô hình với producer) trừ khi workspace có policy cho scope `AGENT_PROFILE` với key `cosa.agents.verifier`. REST model-policy chưa nhắm được id này; dùng `set_policy` của repository.

## Triển khai và rollback

1. Bật `WGA_VERIFY_ON_COMPLETE=1` ở workspace dev trước, chạy sweep, xem báo cáo qua endpoint và log.
2. Theo dõi tỉ lệ FAIL/INCONCLUSIVE bất thường (nhiều INCONCLUSIVE thường là lỗi route/ngân sách thẩm phán).
3. Rollback: tắt cờ; task mới trở lại hành vi cũ. Báo cáo đã lưu giữ nguyên.

## Giới hạn đã biết

- `reason` trong báo cáo là văn bản tự do của thẩm phán đã làm sạch (bỏ ký tự điều khiển, cắt độ dài), không đưa vào note.
- Nếu mọi tiêu chí đều `required: false` thì kết quả là PASS và task tự đóng.
- Báo cáo idempotent theo `(workspace, run_id)`; chạy lại cùng run không tạo báo cáo mới.
