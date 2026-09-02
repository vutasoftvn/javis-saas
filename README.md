# COSA OS - Create. Operate. Scale. Automate.

Descriptor
The AI operating system for startups.

Slogan
Build startups. Run companies. Power a nation.

Hệ điều hành doanh nghiệp AI tích hợp kiến trúc 3 Data Planes trên nền tảng **PostgreSQL (pgvector)**:
- **`agent`**: Agent Core Runtime (runs, memory, knowledge, evals, capabilities)
- **`cosa`**: COSA Control Plane (identity, licenses, policy, scheduler, leases)
- **`workspace`**: Company Business (identity, operations/strategy, commercial/CRM, finance-legal)

---

## ⚡ Cài Đặt Nhanh Local Data Plane (1-Click)

### Trên macOS / Linux / WSL:
```bash
./install.sh
```

### Trên Windows (PowerShell):
```powershell
.\install.ps1
```

---

## 📖 Kiến Trúc & Tài Liệu Vận Hành (Canonical Documentation)

- **Sổ tay vận hành (Runbook)**: [`docs/COSA_RUNBOOK.md`](docs/COSA_RUNBOOK.md)
- **Kiến trúc & Vận hành Database**: [`db.md`](db.md)

---

## 🛠️ Quản Trị Hệ Thống Nhanh (COSA CLI)

```bash
./cosa.sh start    # Khởi động dịch vụ
./cosa.sh stop     # Dừng dịch vụ
./cosa.sh status   # Kiểm tra trạng thái
./cosa.sh doctor   # Chẩn đoán sức khỏe hệ thống
./cosa.sh backup   # Sao lưu toàn bộ dữ liệu Local
./cosa.sh restore  # Khôi phục dữ liệu
```

---

## 🏗️ Local Development Stack (Task 3: Explicit Topology)

**Canonical host-based development topology:**

```
Host (macOS/Linux)                   Docker Containers
═════════════════════════════════════════════════════════
Company Service (port 4000)    ←→    PostgreSQL (port 5432 - db: workspace)
COSA Control Plane (port 4001) ←→    PostgreSQL (port 5432 - db: cosa)
FastAPI Server (port 8000)     ←→    PostgreSQL (port 5432 - db: agent)
Worker Daemon (background)     ←→    MinIO (port 9000/9001) & LiveKit (port 7880/7885)
```

**Khởi động development stack:**

```bash
# Step 1: Chuẩn bị file cấu hình môi trường
cp .env.example .env
source scripts/load-dev-env.sh  # Nạp biến môi trường

# Step 2: Khởi động container hạ tầng (PostgreSQL, MinIO, LiveKit)
make dev-infra

# Step 3: Chạy migrations cho 3 CSDL theo thứ tự canonical (Agent -> COSA -> Company)
make dev-migrate

# Step 4: Kiểm tra tiền điều kiện cấu hình và sức khỏe service
make dev-preflight

# Step 5: Khởi động toàn bộ stack hoặc từng service
make dev-stack   # hoặc chạy riêng: encore run, uvicorn, worker

# Step 6: Kiểm tra trạng thái toàn bộ dịch vụ
make dev-status
```

**Lệnh riêng lẻ thường dùng:**

```bash
make dev-infra       # Khởi động PostgreSQL, MinIO, LiveKit (Docker)
make dev-migrate     # Chạy migrations: Agent Core → COSA → Company
make dev-preflight   # Kiểm tra tính hợp lệ cấu hình và sức khỏe kết nối
make dev-status      # Hiển thị trạng thái các cổng và tiến trình
```

**Quy ước kết nối Database (Required Environment Variables):**

- `AGENT_DATABASE_URL` / `AGENT_MIGRATOR_DATABASE_URL`
- `COSA_DATABASE_URL` / `COSA_MIGRATOR_DATABASE_URL`
- `WORKSPACE_DATABASE_URL` / `WORKSPACE_MIGRATOR_DATABASE_URL`
- `COMPANY_SERVICE_URL` (`http://127.0.0.1:4000`)
- `COSA_CONTROL_PLANE_URL` (`http://127.0.0.1:4001`)
- `PLATFORM_JWT_SECRET` / `WORKER_SERVICE_JWT_SECRET`
- `COSA_WORKER_SERVICE_TOKEN`
- `DEEPSEEK_API_KEY`

**Health endpoints:**

```bash
# Company Service health (kiểm tra kết nối CSDL workspace)
curl http://localhost:4000/healthz
# Response: {"app":"company","status":"ok","version":"unknown"}

# COSA Control Plane health (kiểm tra kết nối CSDL cosa)
curl http://localhost:4001/healthz
# Response: {"app":"cosa","status":"ok","version":"unknown"}

# COSA FastAPI health
curl http://localhost:8000/healthz
# Response: {"status":"ok","app":"cosa-agent-platform","version":"1.0.0"}
```

---

## 🗄️ Hướng Dẫn Truy Cập & Quản Trị Database

Toàn bộ hệ thống chạy trên **1 cụm PostgreSQL (pgvector)** tại `127.0.0.1:5432`, được phân tách thành **3 CSDL độc lập** theo ranh giới sở hữu:

### 1. Thông tin kết nối 3 Database

| Database | Mục đích lưu trữ | App Role (`_app`) | Migrator Role (`_migrator`) | Connection URI (App) |
| :--- | :--- | :--- | :--- | :--- |
| **`agent`** | Runs, checkpoints, memory, knowledge, evals, capabilities | `agent_app` | `agent_migrator` | `postgresql+asyncpg://agent_app:change-me-agent-app@127.0.0.1:5432/agent` |
| **`cosa`** | Identity nền tảng, licenses, policies, scheduler, worker leases | `cosa_app` | `cosa_migrator` | `postgresql://cosa_app:change-me-cosa-app@127.0.0.1:5432/cosa?sslmode=disable` |
| **`workspace`** | Doanh nghiệp (identity, operations/strategy, CRM, finance-legal) | `workspace_app` | `workspace_migrator` | `postgresql://workspace_app:change-me-workspace-app@127.0.0.1:5432/workspace?sslmode=disable` |

- **Host**: `127.0.0.1` (hoặc `localhost`)
- **Port**: `5432`
- **Superuser**: `postgres` (Password: `dev-postgres-password` hoặc trong `.env`)

### 2. Kết nối bằng công cụ trực quan (TablePlus, DBeaver, DataGrip)
Tạo connection PostgreSQL tới `localhost:5432` với database name tương ứng (`workspace`, `cosa`, hoặc `agent`), sử dụng user `workspace_app`, `cosa_app`, hoặc `agent_app`.

### 3. Kết nối nhanh qua Terminal CLI
```bash
# Truy cập CSDL Workspace (Company Business)
docker compose exec -it postgres psql -U workspace_app -d workspace

# Truy cập CSDL COSA Control Plane
docker compose exec -it postgres psql -U cosa_app -d cosa

# Truy cập CSDL Agent Runtime
docker compose exec -it postgres psql -U agent_app -d agent

# Truy cập quyền Superuser (quản trị cấp cao)
docker compose exec -it postgres psql -U postgres -d postgres
```

### 4. Quy trình Reset CSDL về trạng thái sạch (Clean Reset)
Khi cần làm mới toàn bộ dữ liệu môi trường phát triển:

```bash
# Bước 1: Dừng và xóa volume PostgreSQL hiện tại
docker compose stop postgres && docker compose rm -f postgres && docker volume rm javis-saas_postgres_data

# Bước 2: Khởi tạo lại container với volume sạch
docker compose up -d postgres

# Bước 3: Nạp biến môi trường và chạy toàn bộ migrations
source scripts/load-dev-env.sh
make dev-migrate
```

---

## 🧪 Kiểm Thử (Unit Tests)

```bash
# Chạy toàn bộ 98 unit tests của 4 cluster:
make services-test
# Hoặc: cd services && encore test
```

---

## 🖥️ Khởi Động Ứng Dụng Frontend Desktop (Flutter macOS)

```bash
cd frontend
flutter run -d macos
```

Hoặc build bản đóng gói:
```bash
cd frontend
flutter build macos --debug
open build/macos/Build/Products/Debug/frontend.app
```

---

## 🌐 Cấu Hình Landing Page & Gửi Email Đăng Ký Sớm (Resend API)

Hệ thống Landing Page (thư mục `landing/`) hỗ trợ gửi email xác nhận cho khách hàng và gửi thông báo Lead mới về cho Ban Quản trị **MIVA Corp**.

Tạo file `landing/.env.local` với cấu hình sau:

```env
RESEND_API_KEY=re_xxxxxxxxx_khoá_api_của_bạn
ADMIN_NOTIFICATION_EMAIL=mivacorp.vn@gmail.com
RESEND_FROM_EMAIL="MIVA Corp <onboarding@resend.dev>"
```

### Chạy và Kiểm Thử Landing Page:
```bash
cd landing
npm install
npm run dev    # Chạy dev server tại http://localhost:3000
npm run test   # Chạy 31 unit tests kiểm tra form và API
npm run build  # Biên dịch bản production
```

