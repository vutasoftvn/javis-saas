# COSA Services Cluster (Local Microservices)

Cụm Microservices nền tảng xây dựng trên **Encore.ts** (TypeScript) kết hợp cùng **Realtime Agent** (Python/LiveKit).

## Kiến trúc Cụm Microservices

Cụm Microservices được tổ chức phân định rõ ràng giữa **Central Control Plane** và **Company Business Node**:

### 1. Central Control Plane (COSA Platform Domain)
- **`control-plane/`**: Quản lý danh tính toàn cầu (Platform Identity / Users / Roles), Quản lý Công ty (Companies / Tenants), Bản quyền (Licenses), và Gói dịch vụ (Plans / Entitlements). Tự sở hữu database schema riêng (`cosa`).

### 2. Company Business Node (Company Self-Host Domain)
Nằm trong thư mục **`company/`**, phục vụ vận hành nội bộ của doanh nghiệp:
- **`company/identity/`**: Xác thực nội bộ (JWT, AuthHandler), Quản lý Workspace, Organization, WorkforceMember, và đồng bộ từ Control Plane.
- **`company/operations/`**: Quản lý Tasks, Initiatives, OKR Cycles, OKR Objectives & Key Results.
- **`company/commercial/`**: CRM (Accounts, Contacts, Customers) & Sales (Leads, Opportunities), Marketing.
- **`company/finance-legal/`**: Quản lý hồ sơ tài chính (AccountingProfiles, Periods, Transactions, Snapshots) và Pháp lý (Legal Checklist, Legal Obligations).
- **`company/shared/`**: Database schemas nội bộ của công ty (`core`, `operating`, `sales`, `finance`), type definitions và Domain Events.

### 3. Voice & AI Runtime
- **`realtime_agent/`**: Realtime Voice & AI Agent (Python/LiveKit + Gemini Live).

---

## Cấu trúc Database & Schemas

Hệ thống phân tách dữ liệu thành các database và schema PostgreSQL riêng biệt:

| Service / Database | Schema | Các bảng chính | Mô tả vai trò |
| :--- | :--- | :--- | :--- |
| **`control_plane`** | `cosa` | `users`, `profiles`, `companies`, `company_roles`, `plans`, `licenses`, `company_entitlements`, `company_agent_policy` | **Central Identity Plane**: Nguồn sự thật danh tính toàn cầu, xác thực đăng ký/đăng nhập ban đầu, công ty & bản quyền. |
| **`identity`** | `core` | `users`, `workspaces`, `workspace_members`, `organizations`, `workforce_members` | **Local Workspace Identity**: Dữ liệu người dùng & thành viên đồng bộ về sau khi đăng nhập/chọn công ty. |
| **`operations`** | `operating`, `strategy` | `tasks`, `initiatives`, `okr_objectives`, `key_results`, `twelve_week_cycles` | Quản lý vận hành, mục tiêu chiến lược và công việc. |
| **`commercial`** | `sales`, `commercial` | `accounts`, `contacts`, `customers`, `sales_leads`, `marketing_campaigns` | Quản lý quan hệ khách hàng và thương mại. |
| **`finance-legal`** | `finance`, `legal` | `accounting_profiles`, `financial_transactions`, `legal_checklist_items` | Quản lý sổ sách kế toán, dòng tiền và nghĩa vụ pháp lý. |

---

## Thông Tin Truy Cập & Kết Nối Database

Hệ thống có 2 chế độ chạy tương ứng với 2 môi trường Database khác nhau:

### 1. Môi trường Native Dev (`encore run`)
Khi chạy bằng lệnh `encore run`, Encore tự khởi tạo PostgreSQL độc lập quản lý riêng cho từng microservice:

#### Thông số kết nối chung (GUI / DBeaver / TablePlus):
- **Host**: `127.0.0.1` (hoặc `localhost`)
- **Port**: `9500`
- **User**: `giyds`
- **Password**: `local`
- **SSL**: `Disable`

#### Danh sách Database & Connection URI:
| Service | Tên Database | PostgreSQL Connection URI | Schema mặc định |
| :--- | :--- | :--- | :--- |
| **Control Plane** | `control_plane` | `postgresql://giyds:local@127.0.0.1:9500/control_plane?sslmode=disable` | `cosa` |
| **Identity** | `identity` | `postgresql://giyds:local@127.0.0.1:9500/identity?sslmode=disable` | `core` |
| **Operations** | `operations` | `postgresql://giyds:local@127.0.0.1:9500/operations?sslmode=disable` | `operating`, `strategy` |
| **Commercial** | `commercial` | `postgresql://giyds:local@127.0.0.1:9500/commercial?sslmode=disable` | `sales`, `commercial` |
| **Finance & Legal** | `finance_legal` | `postgresql://giyds:local@127.0.0.1:9500/finance_legal?sslmode=disable` | `finance`, `legal` |

> [!NOTE]
> **Lưu ý về Schema khi query:** Các bảng không nằm trong schema `public`. Bạn cần chỉ định rõ tên schema khi viết câu lệnh SQL (ví dụ: `SELECT * FROM cosa.users;` hoặc `SELECT * FROM core.workspaces;`).

---

### 2. Môi trường Docker Compose (`docker compose up -d`)
Khi khởi động bằng Docker Compose, toàn bộ dữ liệu dùng chung cụm PostgreSQL `cosa_services_db`:

#### Thông số kết nối:
- **Host**: `127.0.0.1` (hoặc `localhost`)
- **Port**: `5433`
- **User**: `cosa`
- **Password**: `cosa`
- **Database**: `company`
- **Connection URI**: `postgresql://cosa:cosa@127.0.0.1:5433/company?sslmode=disable`

---

## Chạy Local bằng Docker Compose

### 1. Chuẩn bị biến môi trường
```bash
cd services
cp .env.example .env
```
*(Cập nhật `GEMINI_API_KEY` nếu bạn muốn test voice agent với Gemini Live)*

### 2. Khởi động các container
```bash
docker compose up -d
```

### 3. Xem logs
```bash
docker compose logs -f
```

### 4. Truy cập các dịch vụ
- **API Gateway (Encore)**: [http://localhost:4000](http://localhost:4000)
- **Dev Dashboard & Distributed Tracing (Encore)**: [http://localhost:9400](http://localhost:9400)
- **LiveKit Server (WebRTC / Voice)**: [http://localhost:7880](http://localhost:7880)
- **Postgres Database (Docker port)**: `localhost:5433` (User: `cosa`, Pass: `cosa`, DB: `company`)

### 5. Dừng các container
```bash
docker compose down
```

---

## Chạy trực tiếp qua Encore CLI (Native Local Dev)

Hệ thống bao gồm **2 ứng dụng Encore độc lập** với 2 file `encore.app` riêng:

### 1. Chạy Company Services (Port 4000)
```bash
cd services/company

# Chạy test
encore test

# Chạy dev server (quản lý đúng 4 DB: identity, operations, commercial, finance_legal)
encore run --port=4000
```
- **API Base:** [http://localhost:4000](http://localhost:4000)
- **Database PostgreSQL:** `localhost:9500` (chỉ chứa 4 database nghiệp vụ của doanh nghiệp)

---

### 2. Chạy COSA Central Control Plane (Port 4001)
```bash
cd services/cosa

# Chạy test
encore test

# Chạy dev server (quản lý 1 DB duy nhất: control_plane)
encore run --port=4001
```
- **API Base:** [http://localhost:4001](http://localhost:4001)
- **Database PostgreSQL:** `localhost:9500` (database `control_plane` / schema `cosa`)

---

### Các lệnh CLI quản lý Database với Encore:
```bash
# Trong services/company:
cd services/company
encore db conn-uri identity
encore db conn-uri operations
encore db conn-uri commercial
encore db conn-uri finance_legal
encore db reset identity

# Trong services/cosa:
cd services/cosa
encore db conn-uri control_plane
encore db reset control_plane
```

### Ví dụ truy vấn dữ liệu mẫu qua `psql`:
```bash
# Kiểm tra tài khoản trên Central Control Plane
psql "postgresql://giyds:local@127.0.0.1:9500/control_plane?sslmode=disable" -c "SELECT id, email, status FROM cosa.users;"

# Kiểm tra workspace trên Identity Local
psql "postgresql://giyds:local@127.0.0.1:9500/identity?sslmode=disable" -c "SELECT id, name, company_stage FROM core.workspaces;"
```
