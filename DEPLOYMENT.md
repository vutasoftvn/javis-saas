# Triển khai COSA

Từ thư mục gốc repository, cấu hình `.env` với kết nối PostgreSQL, MinIO/S3
và một allowlist origin rõ ràng. Ngoài development, phải đặt
`COSA_ALLOWED_ORIGINS` thành danh sách URL phân tách bằng dấu phẩy; không dùng
wildcard khi credentials được bật.

Khởi tạo schema trước khi chạy API và worker:

```bash
docker compose up --build -d migrate
docker compose up -d brain-api agent-worker
```

`brain-api` và `agent-worker` phụ thuộc vào migration hoàn tất. API sẽ kiểm tra
database, object storage, migration và worker heartbeat tại `/ready`; `/live`
chỉ là liveness probe. Schema chỉ được quản lý bằng Alembic migration.
