# Hướng Dẫn Triển Khai COSA Central Control Plane (Coolify & VPS)

Tài liệu hướng dẫn triển khai **COSA Central Control Plane** (FastAPI + PostgreSQL 16) lên hệ thống VPS thông qua **Coolify (GitHub App Integration)** với domain chính thức **`api.vutasoft.com`**.

---

## 1. Triển Khai Qua Coolify (Khuyên Dùng - Tự Động CI/CD & SSL)

Khi bạn đã kết nối **GitHub App** trên Coolify, việc triển khai sẽ tự động build lại mỗi khi push code lên nhánh `main`.

### Bước 1: Cấu hình DNS Domain (Nhà cung cấp tên miền)
Trỏ các bản ghi DNS của bạn về địa chỉ IP của VPS Coolify:
- `A` `api.vutasoft.com` $\rightarrow$ `<IP_VPS_COOLIFY>`
- `A` `*.vutasoft.com` $\rightarrow$ `<IP_VPS_COOLIFY>` *(dành cho subdomain các workspace)*

---

### Bước 2: Tạo Cơ Sở Dữ Liệu PostgreSQL trên Coolify
1. Trên Coolify Dashboard: Chọn Project $\rightarrow$ Environment (ví dụ `production`) $\rightarrow$ Click **+ New Resource**.
2. Chọn **PostgreSQL** (Managed Database).
3. Đặt cấu hình:
   - **Name**: `cosa-central-db`
   - **Database Name**: `cosa`
   - **Username**: `cosa_central_admin`
   - **Password**: `SecureCentralPass2026` *(Lưu ý: Đổi mật khẩu này trên Production)*
4. Click **Start** để khởi chạy Database.
5. **Khởi tạo dữ liệu (Migration)**:
   - Dữ liệu được quản lý theo kiến trúc migration thống nhất (`baseline_v1` trong `services/cosa/migrations/` và `packages/agent/migrations/`).
   - Chạy migration tự động thông qua `make migrate-all` (hoặc `make services-migrate-cosa` cho riêng control-plane database).
   - Tuyệt đối không dùng file `init_central_postgres.sql` thủ công hay legacy Alembic runner (đã xoá theo Sub-project D).

---

### Bước 3: Tạo Ứng Dụng Backend API (COSA API & Services)
1. Click **+ New Resource** $\rightarrow$ Chọn **Private Repository (GitHub App)**.
2. Chọn Repository: `vutasoftvn/javis-saas` (nhánh `main` hoặc `staging`).
3. Cấu hình thông số ứng dụng (**Configuration**):
   - **Name**: `cosa-api`
   - **Build Pack**: `Dockerfile`
   - **Dockerfile Path**: `apps/cosa/Dockerfile.api`
   - **Ports Exposes**: `8000`
   - **Domains**: `https://api.vutasoft.com`
     *(Coolify sẽ tự động đăng ký SSL Let's Encrypt và định tuyến traffic qua Reverse Proxy)*
4. Thiết lập Biến Môi Trường (**Environment Variables**):
   Dán trực tiếp URL PostgreSQL, các JWT secrets và API keys cần thiết:
   ```ini
   AGENT_DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>:5432/cosa
   COSA_DATABASE_URL=postgresql://<user>:<password>@<host>:5432/cosa?sslmode=disable
   WORKSPACE_DATABASE_URL=postgresql://<user>:<password>@<host>:5432/workspace?sslmode=disable
   COSA_CONTROL_PLANE_URL=http://<services-cosa-host>:4001
   COMPANY_SERVICE_URL=http://<services-company-host>:4000
   PLATFORM_JWT_SECRET=cosa_platform_master_signing_key_production_random_string_64chars
   WORKER_SERVICE_JWT_SECRET=cosa_worker_jwt_secret_min32chars
   ENVIRONMENT=production
   PYTHONUNBUFFERED=1

   # AI Provider (DeepSeek / OpenAI)
   DEEPSEEK_API_KEY=sk-xxxx_lay_tu_dashboard
   DEEPSEEK_BASE_URL=https://api.deepseek.com
   DEEPSEEK_DEFAULT_MODEL=deepseek-chat
   COSA_MODEL_PROVIDER=deepseek
   ```
   > **Lưu ý quan trọng:**
   > - Chuỗi kết nối internal `postgres://...@[container_id]:5432/...` là kết nối nội bộ siêu tốc qua Docker network của Coolify, an toàn tuyệt đối và không bị trễ mạng.
   > - Kira AI Gateway được tích hợp làm provider mặc định với model `deepseek-v4-pro-free`.
5. Click **Deploy**.



---

### Bước 4: Kiểm tra trạng thái hoạt động
Sau khi Coolify build và deploy thành công:
1. Mở trình duyệt truy cập:
   - `https://api.vutasoft.com/docs` (Swagger UI API Docs)
   - `https://api.vutasoft.com/api/v1/platform/sync/status` (Healthcheck)
2. Kiểm tra log realtime trực tiếp tại tab **Logs** của ứng dụng trên Coolify Dashboard.

---

## 2. Cách Triển Khai Bằng Docker Compose Trên VPS (Full stack — ADR-DEPLOY-001)

Chạy toàn bộ 4 unit + hạ tầng không qua Coolify UI:

```text
deploy/central_vps/
├── docker-compose.prod.yaml    # Full stack: postgres, minio, migrate (one-shot),
│                               #   services-company, services-cosa, cosa-api,
│                               #   cosa-worker, [cosa-ingestion-worker], caddy
├── docker-compose.yaml         # Chỉ postgres — dev/local trên VPS
├── Dockerfile.migrate          # Image one-shot migrate (python3 + node)
├── run-migrations.sh           # Entrypoint migrate: Agent Core → COSA → Company + fingerprint check
├── Caddyfile                   # Reverse proxy + SSL; /metrics khoá theo METRICS_ALLOW_CIDR
│                               #   (mount deploy/postgres/init/ để tạo app-role lúc initdb)
├── .env.prod.example           # Template biến môi trường prod (copy → .env.prod)
└── README.md
```

> `init_central_postgres.sql` cũ + legacy Alembic runner **đã bỏ** — schema
> quản lý qua `baseline_v1` + `scripts/migrate.mjs` (services) và
> `packages/agent/scripts/migrate.py` (Agent Core). Xem
> `docs/operations/migrations.md`.

### Các bước thực hiện:
```bash
# 1. SSH vào VPS, clone repo
ssh root@<IP_VPS>
git clone https://github.com/vutasoftvn/javis-saas.git /opt/cosa
cd /opt/cosa/deploy/central_vps

# 2. Cấu hình môi trường (secret quản lý qua Coolify ở prod — xem docs/operations/secrets.md)
cp .env.prod.example .env.prod
$EDITOR .env.prod

# 3. Xác nhận compose fail-closed khi thiếu biến
docker compose -f docker-compose.prod.yaml config --quiet

# 4. Migrate qua đường prod (Migration Gate G), rồi bring-up
docker compose -f docker-compose.prod.yaml --env-file .env.prod run --rm migrate
docker compose -f docker-compose.prod.yaml --env-file .env.prod up -d

# 5. Verify
curl -fsS https://$CENTRAL_API_DOMAIN/healthz
```

---

## 3. Lợi Ích Cốt Lõi Của Kiến Trúc Central Control Plane
- **Tiêu thụ RAM siêu nhẹ**: Chỉ tốn ~250MB - 300MB RAM cho toàn bộ stack (PostgreSQL + FastAPI), tối ưu chi phí VPS.
- **Tự động hóa hoàn toàn**: Coolify tự động lắng nghe GitHub push event để build và reload zero-downtime.
- **Offline-First & Hybrid Sync**: Các client offline ở local app (Local Postgres) chỉ đồng bộ dữ liệu cần thiết lên Central qua Outbox Sync API.
