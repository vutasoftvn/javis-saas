# Dự án B — Verifier: trạng thái và quyết định

Ngày: 2026-10-05, cập nhật 2026-10-06 · Trạng thái: **ĐÃ TRIỂN KHAI v1 (sau cờ, mặc định tắt)**

Bản thiết kế gốc (bắt buộc bước `VERIFIER` trong workflow trước cổng duyệt, ép lúc biên dịch DAG, hash verdict vào approval) đã được thay bằng thiết kế gắn vào việc hoàn thành task WGA. Kế hoạch triển khai: [2026-10-06-verifier-wga-completion-impl.md](2026-10-06-verifier-wga-completion-impl.md). Vận hành: [docs/runbooks/wga-verifier.md](../../runbooks/wga-verifier.md).

## Đã làm

- Logic thuần ở `packages/agent/verification/` (đánh giá tất định, prompt và phân tích đầu ra thẩm phán, `combine`), kho báo cáo `agent.verification_reports` (migration agent 020).
- Thẩm phán độc lập `cosa.agents.verifier` (`run_judge`), điều phối `verify_task_result` ở `apps/cosa/worker/wga_verify.py`.
- Hook trong `_execute_claimed_task` trước `finalize_wga_task_completion`, sau cờ `WGA_VERIFY_ON_COMPLETE`: PASS đóng `done` kèm `verification:<report_id>`; FAIL và INCONCLUSIVE giữ `in_progress` kèm note chỉ chứa mã.
- Sự kiện run `verification.completed` và API đọc `GET /agent/workforce/verification-reports`.

## Quyết định thay đổi so với thiết kế gốc

1. **Không có bước `VERIFIER` trong workflow engine:** không workflow production nào có cổng duyệt để ép.
2. **Không verify ở approval của gateway:** approval diễn ra trước khi thực thi nên chưa có kết quả để kiểm.
3. **Điểm gắn là việc hoàn thành task WGA** (task AUTO tự đóng `done` chỉ với văn bản không rỗng), đúng chỗ rủi ro "đóng giả" nằm.
4. Chỉ kiểm lần chạy đầu của task AUTO; `NEEDS_APPROVAL` và đường resume sau duyệt không kiểm.
5. Verdict không buộc vào hash duyệt và chưa đưa vào scorecard.

## Còn lại

- Verify đường resume và task `NEEDS_APPROVAL`.
- `metric_gte` cần capability đọc giá trị KR (hiện luôn INCONCLUSIVE).
- Cổng duyệt cho workflow (khi có workflow production dùng approval).
- Bật cờ mặc định sau khi quan sát ở workspace dev.
- UI Flutter hiển thị verdict (endpoint chưa vào `shared/contracts/mvp-surface.json` cho đến khi có màn hình dùng).
- `BudgetGate` vẫn chưa nối runtime.
- Ép mô hình thẩm phán khác producer: REST model-policy chưa nhận scope `cosa.agents.verifier`; hiện dùng `set_policy`.
