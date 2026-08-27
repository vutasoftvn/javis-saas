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

## Workspace-first tenancy: Migration 13–14 (services/cosa control-plane)

Migration `services/cosa/migrations/13_workspace_only_product_scope.up.sql` chứa một DELETE tự động dedup
các hàng từ `control_plane.workspace_connector_installations` — loại bỏ các hàng trùng lặp theo cặp
`(workspace_id, connector_key)`, giữ lại hàng mới nhất (id cao hơn).

Trước khi áp dụng migrations 13 + 14 lên database production/staging:
1. Chạy query kiểm tra trùng lặp (từ đầu tập tin `services/cosa/migrations/14_connector_dedup_guard.up.sql`):
   ```sql
   SELECT workspace_id, connector_key, COUNT(*) as count, array_agg(id ORDER BY created_at DESC) as ids
   FROM control_plane.workspace_connector_installations
   GROUP BY workspace_id, connector_key
   HAVING COUNT(*) > 1
   ORDER BY workspace_id, connector_key;
   ```
2. Giải quyết thủ công bất kỳ trùng lặp nào (giữ lại bản mới, xóa/lưu trữ bản cũ).
3. **Sau đó** áp dụng migration 13, rồi migration 14. Migration 14 sẽ RAISE nếu tồn tại trùng lặp sau khi 13 chạy xong.
