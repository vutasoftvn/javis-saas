# OpenSandbox Server Infrastructure

Thư mục này chứa cấu hình mẫu cho `opensandbox-server` sử dụng trong môi trường phát triển (Docker Compose với profile `sandbox`).

## Môi trường phát triển (Dev)
Khởi động container OpenSandbox:
```bash
docker compose --profile sandbox up -d opensandbox
```

Kiểm tra trạng thái máy chủ:
```bash
curl -fsS http://127.0.0.1:8080/health
```

## Môi trường sản xuất (Production)
Theo `DEPLOYMENT.md` và `ADR-EXEC-003`:
- OpenSandbox server **phải** được chạy trên một máy chủ / VM riêng biệt.
- Chỉ mở cổng lắng nghe cho IP nội bộ của `agent-worker`.
- Bắt buộc bật `server.api_key` trong `sandbox.toml` và thiết lập biến môi trường `OPEN_SANDBOX_API_KEY` tương ứng trên worker.
