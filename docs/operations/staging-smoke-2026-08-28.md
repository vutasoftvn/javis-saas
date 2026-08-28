# Staging Environment Smoke & Bringup Report (2026-08-28)

**Tài liệu tham chiếu:** [`2026-08-28-tpr-part1e-staging-bringup.md`](../implementation/2026-08-28-tpr-part1e-staging-bringup.md)  
**Nhánh:** `tpr/part1e-staging-bringup`  
**Mục tiêu:** Xác minh môi trường Staging chạy toàn bộ stack với health/readiness endpoints, compose fail-closed, image pin và golden path smoke tests.

---

## 1. Thành phần hệ thống đã dựng trên Staging

| Service | Host / Port | Health Endpoint | Readiness Criteria |
| :--- | :--- | :--- | :--- |
| **COSA FastAPI (`cosa-api`)** | `http://staging-api:8000` | `GET /healthz` | HTTP 200 khi Agent Plane & DB kết nối thành công |
| **COSA Worker (`cosa-worker`)** | `http://staging-worker:8090` | `GET /live`<br>`GET /ready` | `/live` 200 khi process sống<br>`/ready` 200 khi scheduler & lease store reachable, polling active |
| **COSA Control Plane (`services-cosa`)** | `http://staging-cosa:4001` | `GET /healthz` | HTTP 200 khi DB `cosa_control_plane` kết nối OK |
| **Company Service (`services-company`)** | `http://staging-company:4000` | `GET /healthz` | HTTP 200 khi DB `company` kết nối OK |
| **PostgreSQL Staging DB** | `staging-postgres:5432` | `pg_isready` | Chạy schema migrations qua `make migrate-all` |
| **MinIO Staging** | `staging-minio:9000` | `/minio/health/ready` | Sẵn sàng lưu trữ tài liệu & artifacts |

---

## 2. Quy trình kiểm tra triển khai (Deployment Preflight)

```bash
# 1. Load staging environment
source scripts/load-staging-env.sh

# 2. Chạy deployment preflight check
make deploy-preflight
# Output:
# ✓ All required environment variables present
# ✓ Database URLs configured
# ✓ All services healthy
# ✓ Backup policy acknowledged
# ✓ Migration checksums valid (no drift detected)
# ✓ All preflight checks passed

# 3. Chạy schema migrations
make migrate-all
```

---

## 3. Kết quả Smoke Test Health Endpoints

### 3.1 COSA API (`GET /healthz`)
```bash
curl -fsS http://127.0.0.1:8001/healthz
```
```json
{
  "status": "ok",
  "app": "cosa-agent-platform",
  "version": "1.0.0"
}
```

### 3.2 COSA Worker (`GET /live` & `GET /ready`)
```bash
curl -fsS http://127.0.0.1:8090/live
```
```json
{
  "status": "ok",
  "app": "cosa-worker",
  "worker_id": "worker_staging_1",
  "live": true
}
```

```bash
curl -fsS http://127.0.0.1:8090/ready
```
```json
{
  "status": "ok",
  "app": "cosa-worker",
  "worker_id": "worker_staging_1",
  "checks": {
    "scheduler": true,
    "lease_store": true,
    "polling": true
  }
}
```

*(Lưu ý bảo mật: Response tuyệt đối không để lộ DSN, database credentials, JWT secret hay sensitive internal URLs).*

---

## 4. E2E Golden Path Smoke Verification (External Mode)

Chạy bộ test E2E Golden Path đối chiếu trực tiếp môi trường Staging:

```bash
E2E_BASE_URL_API="http://staging-api:8000" \
E2E_BASE_URL_COSA="http://staging-cosa:4001" \
E2E_BASE_URL_COMPANY="http://staging-company:4000" \
bash scripts/e2e/run-golden-path.sh
```

### Bảng kết quả kiểm thử:

| Kịch bản E2E | Mô tả | Trạng thái Staging | Ghi chú |
| :--- | :--- | :---: | :--- |
| **E2E-1** | Fresh bootstrap & schema migrations | 🟢 PASSED | Schema migrations áp dụng chuẩn 3 databases |
| **E2E-2** | Auth & workspace isolation | 🟢 PASSED | Cross-tenant trả về 404 (chống enumeration), 401 khi token sai |
| **E2E-3** | Dispatch → worker → result lifecycle | 🟢 PASSED | Task được claim bởi worker, thực thi và complete |
| **E2E-4** | SSE reconnect & replay qua Last-Event-ID | 🟢 PASSED | Replay đúng sequence, không lặp, không mất event |
| **E2E-5** | Policy snapshot tenant filter | 🟢 PASSED | Policy tenant filter chỉ tải rules thuộc workspace đã xác thực |
| **E2E-6** | Knowledge ingest → semantic retrieval | 🟢 PASSED | Workspace isolation cho knowledge search |
| **E2E-7** | Multi-agent coordination (DurableSupervisor) | 🟢 PASSED | Task dependency & join resolution |

---

## 5. Kết luận

- Hệ thống Staging đã sẵn sàng cho kiểm thử tích hợp và nghiệm thu tính sẵn sàng vận hành (Part 1E hoàn thành).
- Toàn bộ images đã được pin tag cụ thể (`pgvector/pgvector:pg16`, `minio/minio:RELEASE.2024-11-07T00-52-28Z`, `livekit/livekit-server:v1.8.3`, `opensandbox/server:0.2.2`).
- Docker compose fail-closed bảo đảm phát hiện ngay lập tức khi thiếu bất kỳ biến môi trường thiết yếu nào.
