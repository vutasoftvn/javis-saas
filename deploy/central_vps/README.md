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
   - **Database Name**: `cosa_central`
   - **Username**: `cosa_admin`
   - **Password**: *[Tạo mật khẩu an toàn]*
4. Click **Start** để khởi chạy Database.
5. **Khởi tạo dữ liệu (Init Script)**:
   - Mở tab **Terminal** của Database trên Coolify (hoặc kết nối qua DBeaver / `psql`).
   - Copy toàn bộ nội dung file [`init_central_postgres.sql`](file:///Volumes/SSD/javis-saas/deploy/central_vps/init_central_postgres.sql) và execute để tạo bảng và seed data.

---

### Bước 3: Tạo Ứng Dụng Backend API (Central API)
1. Click **+ New Resource** $\rightarrow$ Chọn **Private Repository (GitHub App)**.
2. Chọn Repository: `vutasoftvn/javis-saas` (nhánh `main`).
3. Cấu hình thông số ứng dụng (**Configuration**):
   - **Name**: `cosa-central-api`
   - **Build Pack**: `Dockerfile`
   - **Base Directory**: `/backend`
   - **Dockerfile Path**: `Dockerfile.api` (hoặc `/backend/Dockerfile.api`)
   - **Ports Exposes**: `8000`
   - **Domains**: `https://api.vutasoft.com`
     *(Coolify sẽ tự động đăng ký SSL Let's Encrypt và định tuyến traffic qua Reverse Proxy)*
4. Thiết lập Biến Môi Trường (**Environment Variables**):
   ```ini
   DATABASE_URL=postgresql://cosa_admin:<PASSWORD>@cosa-central-db:5432/cosa_central
   COSA_PLATFORM_SIGNING_SECRET=cosa_platform_master_signing_key_2026_production_vutasoft
   ENVIRONMENT=production
   PYTHONUNBUFFERED=1
   ```
   *(Lưu ý: `cosa-central-db` là hostname nội bộ Docker network của database bạn vừa tạo)*
5. Click **Deploy**.

---

### Bước 4: Kiểm tra trạng thái hoạt động
Sau khi Coolify build và deploy thành công:
1. Mở trình duyệt truy cập:
   - `https://api.vutasoft.com/docs` (Swagger UI API Docs)
   - `https://api.vutasoft.com/api/v1/platform/sync/status` (Healthcheck)
2. Kiểm tra log realtime trực tiếp tại tab **Logs** của ứng dụng trên Coolify Dashboard.

---

## 2. Cách Triển Khai Nhanh Bằng Docker Compose Trên VPS (Thay thế)

Nếu bạn muốn chạy độc lập bằng Docker Compose không qua Coolify UI:

```text
deploy/central_vps/
├── docker-compose.yaml         # Quản lý 3 services: caddy, central_api, central_postgres
├── Caddyfile                   # Cấu hình Caddy Proxy tự cấp SSL Let's Encrypt
├── init_central_postgres.sql   # DDL khởi tạo database Central & Seed data
├── .env.example                # Template biến môi trường
└── README.md
```

### Các bước thực hiện:
```bash
# 1. SSH vào VPS
ssh root@<IP_VPS>

# 2. Clone repo và chuyển vào thư mục deploy
git clone https://github.com/vutasoftvn/javis-saas.git /opt/cosa
cd /opt/cosa/deploy/central_vps

# 3. Tạo file cấu hình môi trường
cp .env.example .env
# Chỉnh sửa CENTRAL_API_DOMAIN=api.vutasoft.com trong .env

# 4. Khởi chạy
docker compose up -d --build
```

---

## 3. Lợi Ích Cốt Lõi Của Kiến Trúc Central Control Plane
- **Tiêu thụ RAM siêu nhẹ**: Chỉ tốn ~250MB - 300MB RAM cho toàn bộ stack (PostgreSQL + FastAPI), tối ưu chi phí VPS.
- **Tự động hóa hoàn toàn**: Coolify tự động lắng nghe GitHub push event để build và reload zero-downtime.
- **Offline-First & Hybrid Sync**: Các client offline ở local app (Local Postgres) chỉ đồng bộ dữ liệu cần thiết lên Central qua Outbox Sync API.

