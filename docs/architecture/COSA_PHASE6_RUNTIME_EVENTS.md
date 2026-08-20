# COSA Phase 6: Runtime Events, Hologram Projections and Local-First Sessions

Tài liệu này mô tả chi tiết kiến trúc Event-Sourcing và cơ chế Projection trong Phase 6.

## Tổng quan
Mục tiêu là mang lại một bức tranh toàn cảnh (Operational Visibility) an toàn, deterministic, và có thể replay lại cho mọi Workflow Run mà không làm lộ các dữ liệu nhạy cảm hay luồng tư duy thô (raw reasoning) của Agent.

## 1. Single Canonical Authority (ADR-006)
- **PostgreSQL Event Store**: Đóng vai trò là nguồn dữ kiện duy nhất (Single Source of Truth). Mọi thay đổi trạng thái của Workflow (RunCreated, NodeStarted, ToolRequested, NodeCompleted) đều được append vào đây.
- **Tính bất biến (Immutability)**: Các Event không bao giờ được sửa đổi hoặc xoá sau khi ghi. Mọi sự thay đổi phải thông qua compensating event.
- **Redaction**: Hàm `redact_payload` đệ quy tự động quét và che giấu (redact) các dữ liệu nhạy cảm (API Key, password, token) trước khi ghi xuống Event Store. Điều này bảo vệ quyền riêng tư và an toàn bảo mật.

## 2. Deterministic Projections
Thay vì đọc trực tiếp event stream phức tạp, hệ thống sử dụng các Projection (bộ chiếu).
- **Ví dụ**: `WorkflowRunProjection` tính toán trạng thái hiện tại (running, paused, completed), các Node đã đi qua, và lưu lại `last_cursor` của lần cập nhật cuối cùng.
- **Reconnect/Resume**: Khi một Run bị paused (ví dụ chờ Approval), client có thể bị ngắt kết nối. Khi mở lại app, UI (Hologram/Run Inspector) chỉ cần truy vấn `after_cursor` mới nhất để backend trả về projection hiện tại mà không phải load lại toàn bộ log thô hay rebuild state phức tạp ở client.

## 3. Local Cache & Hologram UI
- **SQLite/Isar/Hive**: Đối với Local-First (mobile app, desktop), SQLite chỉ đóng vai trò là một Projection Cache.
- SQLite **không** là authority. Nó chỉ dùng để lưu offline state và cursor. Nếu có Gap trong event cursor hoặc database bị xoá, hệ thống tự động rebuild bằng cách fetch lại từ cursor 0 (hoặc Snapshot mới nhất) từ Server.
- **Hologram Run Inspector**: UI hiển thị hoàn toàn dựa trên Projection (VD: Timeline, Thẻ trạng thái Node, Artifact), tuyệt đối không parse raw model output hay raw HTTP response, đảm bảo trải nghiệm clean và professional.

## 4. Runbook: Xử lý sự cố (Operational)
- **Khi Workflow kẹt**: Kiểm tra bảng `protected_resource_revisions` để xác định version đang chạy, rồi truy xuất event bằng `correlation_id`.
- **Audit & OTel**: Log tuân thủ (Audit) và Tracing (OpenTelemetry) đều tham chiếu tới Event Log qua `correlation_id` và `causation_id`. Hệ thống không lưu trùng lặp payload. Đừng cố query Audit log để tìm debug flow, hãy dùng Event Store API với `after_cursor`.
