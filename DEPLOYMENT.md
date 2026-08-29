# Triển khai COSA

> Topology production đã chốt tại [`ADR-DEPLOY-001`](docs/architecture/adr/ADR-DEPLOY-001-prod-topology.md):
> **Coolify + docker-compose** (`deploy/central_vps/docker-compose.prod.yaml`),
> K8s để sau. Chi tiết vận hành: [`docs/operations/deployment.md`](docs/operations/deployment.md).

Từ thư mục gốc repository, cấu hình `.env` (dev) hoặc
`deploy/central_vps/.env.prod` (prod, copy từ `.env.prod.example`) với kết nối
PostgreSQL, MinIO/S3 và một allowlist origin rõ ràng. Ngoài development, phải
đặt `CORS_ORIGINS` thành danh sách URL phân tách bằng dấu phẩy; không dùng
wildcard khi credentials được bật (guard trong `apps/cosa/api/app.py` sẽ
raise nếu vi phạm).

Khởi tạo schema trước khi chạy API và worker (đường prod — Migration Gate G,
xem [`docs/operations/migrations.md`](docs/operations/migrations.md)):

```bash
cd deploy/central_vps
docker compose -f docker-compose.prod.yaml --env-file .env.prod run --rm migrate
docker compose -f docker-compose.prod.yaml --env-file .env.prod up -d
```

`cosa-api` / `cosa-worker` / `services-cosa` / `services-company` phụ thuộc
migration hoàn tất (`condition: service_completed_successfully`). API kiểm tra
database, object storage, migration và worker heartbeat tại `/ready`; `/live`
chỉ là liveness probe.

**Migration:** KHÔNG dùng Alembic (đã xoá). Schema quản lý qua
`packages/agent/scripts/migrate.py` (Agent Core, Python) + `baseline_v1`
và `scripts/migrate.mjs` (`services/cosa`, `services/company` — Node). Chạy
gộp: `make migrate-all` (local) hoặc service `migrate` (prod).

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
