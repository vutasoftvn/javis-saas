# Vận hành: Deployment

## Trạng thái: CHƯA verify trong phiên Wave 0-11

Không có deploy pipeline nào được chạy thử trong phiên này — môi trường phát triển không có Encore CLI, không có quyền truy cập hạ tầng deploy thật. Nội dung dưới đây mô tả kiến trúc deploy DỰ KIẾN dựa trên cấu trúc 4 vùng kiến trúc (CLAUDE.md), không phải quy trình đã kiểm chứng.

## 4 vùng cần deploy riêng

1. **Experience Plane** (Flutter) — build/deploy client app, ngoài phạm vi phiên này.
2. **`services/cosa`** (Encore/TypeScript) — deploy qua Encore platform (`encore deploy` hoặc self-host), có `control_plane` schema mới từ Wave 7 cần migration chạy trước khi deploy code mới dùng bảng đó (xem `migrations.md`).
3. **`services/company`** (Encore/TypeScript) — không đổi trong phiên này.
4. **`packages/agent_core` + `apps/cosa`** (Python) — deploy như service Python độc lập (chưa xác nhận containerization cụ thể trong repo hiện tại), cần `AGENT_CORE_DATABASE_URL` bắt buộc (no-silent-fallback — thiếu biến này sẽ raise `RuntimeError` khi khởi động, đây là hành vi ĐÚNG, không phải bug).

## Rủi ro deploy Wave 7 (control-plane mới)

Thêm network hop Python↔Encore TS vào hot path resume run (`packages/agent_core/runs/control_plane_client.py::HttpControlPlaneLeaseClient`). Trước khi deploy production:
- Đo latency thật (chưa làm — cần Encore CLI).
- Xác nhận retry/circuit breaker trong `control_plane_client.py` đủ chịu lỗi khi `services/cosa` restart/deploy giữa lúc `agent_core` đang gọi.
- Cân nhắc thứ tự deploy: `services/cosa` (có control-plane endpoint mới) nên deploy TRƯỚC `agent_core` phiên bản dùng client mới, để tránh gọi endpoint chưa tồn tại.

## Không được làm

- Không tự ý chạy lệnh deploy/push tới hạ tầng chia sẻ mà không xác nhận với người dùng trước (CLAUDE.md #10, nguyên tắc "hành động rủi ro cao").
