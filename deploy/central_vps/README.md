# Hướng Dẫn Triển Khai COSA Central Control Plane trên VPS (Hostinger)

Bộ cấu hình triển khai **COSA Central Control Plane** sử dụng **Pure PostgreSQL 16 + FastAPI + Caddy Reverse Proxy (Auto SSL)** trực tiếp trên VPS.

---

## 1. Cấu trúc thư mục

```text
deploy/central_vps/
├── docker-compose.yml          # Quản lý 3 services: caddy, central_api, central_postgres
├── Caddyfile                   # Cấu hình Reverse Proxy & cấp phát SSL Let's Encrypt
├── init_central_postgres.sql   # DDL khởi tạo database Central & Seed data
├── .env.example                # Template biến môi trường
└── README.md                   # Tài liệu hướng dẫn này
```

---

## 2. Các bước triển khai lên VPS Hostinger (Từng bước)

### Bước 1: Kết nối SSH vào VPS
```bash
ssh root@<IP_VPS_HOSTINGER>
```

### Bước 2: Cài đặt Docker & Docker Compose (nếu chưa có)
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
```

### Bước 3: Đưa mã nguồn lên VPS
```bash
mkdir -p /opt/cosa
cd /opt/cosa
git clone <URL_REPO_JAVIS_SAAS> .
cd deploy/central_vps
```

### Bước 4: Thiết lập biến môi trường
```bash
cp .env.example .env
nano .env
```
*Cập nhật `POSTGRES_PASSWORD`, `COSA_PLATFORM_SIGNING_SECRET`, và `CENTRAL_API_DOMAIN`.*

### Bước 5: Cấu hình bản ghi DNS (Domain)
Trỏ các bản ghi DNS tại nhà cung cấp tên miền về IP của VPS:
- `A` `api.cosa.vn` $\rightarrow$ `<IP_VPS>`
- `A` `*.cosa.vn` $\rightarrow$ `<IP_VPS>`

### Bước 6: Khởi chạy toàn bộ hệ thống
```bash
docker compose up -d --build
```

### Bước 7: Kiểm tra trạng thái hoạt động
```bash
# Kiểm tra containers đang chạy
docker compose ps

# Xem log hoạt động
docker compose logs -f central_api
```

Truy cập kiểm tra API qua trình duyệt:
`https://api.cosa.vn/api/v1/platform/sync/status`

---

## 3. Lợi ích so với Supabase Self-Hosted
- **Tiêu thụ RAM chỉ ~300MB** (thay vì 2.5GB của Supabase).
- **100% Python/FastAPI**, không phụ thuộc GoTrue hay PostgREST.
- **Tự động cấp phát chứng chỉ SSL** cho tất cả các subdomain công ty qua Caddy.
