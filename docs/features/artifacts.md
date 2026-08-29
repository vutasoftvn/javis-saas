# Artifacts

> **Lưu ý:** subsystem này tồn tại từ TRƯỚC phiên làm việc Blueprint V2 (2026-08-24) — tài liệu này viết lại dựa trên audit code hiện có.

## 1. Mục đích

Output artifact-first (không chỉ assistant text) — `ArtifactRecord`/`ArtifactReference` mô tả file/report/structured_data sinh ra từ 1 Run, có checksum + storage_uri.

## 2. Khi nào sử dụng

Khi Run sinh ra output không phải text thuần (report, chart_spec, file) — dùng `ArtifactReference` trong `RunResult`/event stream thay vì nhét raw content vào text.

## 3-16.

Chưa audit sâu trong phiên Wave 0-11 (không nằm trong phạm vi công việc chính, không có thay đổi nào tới subsystem này trong phiên) — xem `packages/agent/artifacts/{distribution.py,lifecycle.py}` trực tiếp cho chi tiết implementation. Cần 1 pass tài liệu hoá riêng theo template đầy đủ nếu cần.
