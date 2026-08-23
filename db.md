# COSA / JAVIS Database Architecture & Operations Guide

Tài liệu chi tiết về cấu trúc cơ sở dữ liệu, phân vùng schema, cấu hình kết nối, quy trình quản lý Docker và hướng dẫn truy cập qua GUI (pgAdmin / DBeaver / TablePlus) cho toàn bộ hệ thống **JAVIS - COSA SaaS**.

---

## 1. Tổng quan Kiến trúc 2 Ứng Dụng Độc Lập

Hệ thống được thiết kế theo mô hình **Hybrid SaaS (Central Control Plane + Company Self-Host Nodes)**, tổ chức thành **2 ứng dụng Encore độc lập** kết nối trực tiếp vào các container cơ sở dữ liệu cố định (Drizzle ORM thuần, **không để Encore sinh container `sqldb-*` ngẫu nhiên**):

```
┌────────────────────────────────────────────────────────────────────────┐
│  ỨNG DỤNG 1: COSA CENTRAL CONTROL PLANE (services/cosa)                │
│  - File cấu hình: services/cosa/encore.app                              │
│  - API Gateway: Port 4001                                              │
│  - Quản lý danh tính toàn cầu (Platform Identity / Users / Roles)       │
│  - Quản lý Công ty (Tenants), Gói cước (Plans), Bản quyền (Licenses)   │
│  - Database Container: cosa_db (Port 5434 - DB: cosa)                  │
│  - PostgreSQL Schema: cosa (9 bảng)                                    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                    1. Đăng ký/Đăng nhập lấy Platform Token
                    2. Đồng bộ xuống Local Workspace qua REST API
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  ỨNG DỤNG 2: COMPANY BUSINESS NODE (services/company)                  │
│  - File cấu hình: services/company/encore.app                          │
│  - API Gateway: Port 4000                                              │
│  - Quản lý vận hành nội bộ: Workspace, OKRs, Tasks, CRM, Sổ sách       │
│  - AI Multi-Agent Plane (AgentOS) + Realtime Voice Agent (LiveKit)     │
│  - Database Container: company_db (Port 5433 - DB: company)            │
│  - 8 PostgreSQL Schemas: core, operating, strategy, sales,             │
│    commercial, finance, legal, validation (55 bảng)                    │
└────────────────────────────────────────────────────────────────────────┘
```

> **Quy ước định danh (Snowflake ID)**: Toàn bộ bảng sử dụng 64-bit BigInt Snowflake ID làm Primary Key (kiểu `BIGINT` trong PostgreSQL), không dùng UUID cho PK.

---

## 2. Thông tin Truy cập Database Cố Định (pgAdmin / DBeaver / TablePlus)

Toàn bộ dịch vụ kết nối trực tiếp vào cụm PostgreSQL Docker Compose cố định:

```
+---------------------------------------------------------------------------------------------------+
| 1. COSA COMPANY NODE (Doanh nghiệp)                                                               |
|    - Container Name: company_db (Nhóm: company)                                                   |
|    - Host: 127.0.0.1 (hoặc localhost)                                                             |
|    - Port: 5433                                                                                   |
|    - User: cosa                                                                                   |
|    - Password: cosa                                                                               |
|    - Database: company                                                                            |
|    - Schemas (8): core, operating, strategy, sales, commercial, finance, legal, validation        |
|    - Connection URI: postgresql://cosa:cosa@127.0.0.1:5433/company?sslmode=disable                |
+---------------------------------------------------------------------------------------------------+
| 2. COSA CENTRAL CONTROL PLANE (Nền tảng Quản trị)                                                 |
|    - Container Name: cosa_db (Nhóm: cosa)                                                         |
|    - Host: 127.0.0.1 (hoặc localhost)                                                             |
|    - Port: 5434                                                                                   |
|    - User: cosa_central_admin                                                                     |
|    - Password: SecureCentralPass2026                                                              |
|    - Database: cosa                                                                               |
|    - Schema (1): cosa                                                                             |
|    - Connection URI: postgresql://cosa_central_admin:SecureCentralPass2026@127.0.0.1:5434/cosa?sslmode=disable |
+---------------------------------------------------------------------------------------------------+
```

---

## 3. Danh mục Schema & Bảng Dữ liệu Chi Tiết

### 3.1. Cụm Company Node (`Port 5433` - Database `company` - 55 Bảng)

| Schema | Số bảng | Danh mục các bảng | Mô tả vai trò nghiệp vụ |
| :--- | :---: | :--- | :--- |
| **`core`** | 5 | `workspaces`, `users`, `workspace_members`, `organizations`, `workforce_members` | Không gian làm việc (Workspace), định danh nội bộ & phân bổ nhân sự (Workforce con người/AI) |
| **`operating`** | 6 | `tasks`, `task_dependencies`, `task_schedules`, `twelve_week_cycles`, `weekly_plans`, `weekly_commitments` | Quản lý tác vụ vận hành hàng ngày, phụ thuộc task, lịch định kỳ & chu kỳ thực thi 12 tuần |
| **`strategy`** | 18 | `portfolios`, `projects`, `portfolio_projects`, `initiatives`, `okr_cycles`, `okr_objectives`, `key_results`, `stage_policies`, `stage_transitions`, `assumptions`, `experiments`, `evidence`, `interviews`, `discovery_signals`, `gate_evaluations`, `decision_records`, `next_action_candidates`, `next_action_rankings` | Chiến lược khởi nghiệp, quản trị mục tiêu OKRs, đánh giá Stage Gate, kiểm chứng giả định và xếp hạng hành động tiếp theo |
| **`sales`** | 5 | `accounts`, `contacts`, `sales_leads`, `sales_opportunities`, `customers` | Quản trị quan hệ khách hàng (CRM), quản lý đầu mối, cơ hội bán hàng B2B & hồ sơ khách hàng |
| **`commercial`** | 7 | `marketing_contexts`, `marketing_campaigns`, `campaign_assets`, `marketing_forms`, `marketing_lead_intakes`, `invoices`, `subscriptions` | Ngữ cảnh thị trường, chiến dịch Marketing đa kênh, Form thu thập khách hàng & Hóa đơn / Gói đăng ký |
| **`finance`** | 8 | `accounting_profiles`, `accounting_periods`, `financial_transactions`, `finance_exceptions`, `finance_management_snapshots`, `accounting_fiscal_profiles`, `accounting_coa_mappings`, `accounting_regime_transition_logs` | Quản lý sổ sách kế toán (Thông tư 58 / TT133 / TT200), chuyển đổi niên độ, dòng tiền & báo cáo quản trị |
| **`legal`** | 2 | `legal_checklist_items`, `legal_obligations` | Danh mục kiểm soát tuân thủ pháp lý, nghĩa vụ hợp đồng & giấy phép doanh nghiệp |
| **`validation`** | 4 | `validation_hypotheses`, `validation_experiments`, `evidence_items`, `customer_interviews` | Kiểm chứng mô hình kinh doanh giai đoạn sớm, lưu trữ phỏng vấn & bằng chứng khách hàng |

> [!IMPORTANT]
> **Lưu ý về Schema khi viết SQL:** Các bảng **KHÔNG** nằm trong schema `public`. Khi viết câu lệnh SQL cần chỉ định rõ schema (ví dụ: `SELECT * FROM core.workspaces;`, `SELECT * FROM strategy.projects;` hoặc `SELECT * FROM operating.tasks;`).

---

### 3.2. Cụm Control Plane (`Port 5434` - Database `cosa` - 9 Bảng)

| Schema | Số bảng | Danh mục các bảng | Mô tả vai trò nghiệp vụ |
| :--- | :---: | :--- | :--- |
| **`cosa`** | 9 | `users`, `profiles`, `roles`, `companies`, `company_roles`, `plans`, `licenses`, `company_entitlements`, `company_agent_policy` | Nguồn sự thật danh tính toàn cầu (Platform Identity), phân quyền RBAC, quản lý Công ty (Tenants), Gói cước (Plans), Bản quyền (Licenses), Hạn ngạch (Entitlements) & Chính sách AI Agent |

---

## 4. Cấu Trúc Docker Desktop & Quản Lý Container

Tên nhóm container trong Docker Desktop được cấu hình đồng bộ chuẩn với cấu trúc thư mục dự án:

```
Docker Desktop
├── 📂 company
│   ├── 🟢 company_db              # PostgreSQL 16 + pgvector (Port 5433:5432 - DB: company)
│   ├── 🟢 company_livekit         # LiveKit WebRTC Server (Port 7885/7886, UDP 50030-50040)
│   └── 🟢 company_agent           # Python Realtime AI Voice Agent
│
├── 📂 cosa
│   └── 🟢 cosa_db                 # PostgreSQL 16 Alpine (Port 5434:5432 - DB: cosa)
│
└── 📂 n8n
    └── 🟢 javis_n8n               # n8n Automation Engine (Port 5678:5678)
```

### Lệnh Quản Lý Docker Containers:

```bash
# 1. Khởi động nhóm Company (Database + LiveKit + Voice Agent)
cd /Volumes/SSD/javis-saas/services
docker compose up -d

# 2. Khởi động nhóm COSA Control Plane (Central Database)
cd /Volumes/SSD/javis-saas/deploy/central_vps
docker compose up -d

# 3. Khởi động nhóm n8n Automation (Workflow Engine)
cd /Volumes/SSD/javis-saas/infra/n8n
docker compose up -d

# Kiểm tra trạng thái toàn bộ containers
docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}"
```

---

## 5. Hướng dẫn Đăng ký Server trong GUI (pgAdmin / DBeaver / TablePlus)

### Bước 1: Tạo Server cho Company Node (Doanh nghiệp)
1. Trong pgAdmin / DBeaver / TablePlus, tạo kết nối mới:
   - **Tên kết nối:** `COSA Company DB`
   - **Host:** `localhost` hoặc `127.0.0.1`
   - **Port:** `5433`
   - **Database:** `company`
   - **Username:** `cosa`
   - **Password:** `cosa`
2. Lưu kết nối. Mở Database `company` ➔ **Schemas** để truy cập 8 schemas (`core`, `operating`, `strategy`, `sales`, `commercial`, `finance`, `legal`, `validation`) với tổng cộng **55 bảng**.

---

### Bước 2: Tạo Server cho COSA Control Plane (Nền tảng Quản trị)
1. Tạo kết nối mới:
   - **Tên kết nối:** `COSA Central DB`
   - **Host:** `localhost` hoặc `127.0.0.1`
   - **Port:** `5434`
   - **Database:** `cosa`
   - **Username:** `cosa_central_admin`
   - **Password:** `SecureCentralPass2026`
2. Lưu kết nối. Mở Database `cosa` ➔ **Schemas** ➔ `cosa` để truy cập **9 bảng** quản trị nền tảng.

---

## 6. Bảng Tổng Hợp Cổng (Ports) Toàn Hệ Thống

| Cổng (Port) | Dịch vụ | Thư mục mã nguồn | Container Name | Vai trò |
| :--- | :--- | :--- | :--- | :--- |
| **`4000`** | **Company Encore Gateway** | `services/company` | *(Host process)* | API Microservices Doanh nghiệp (`identity`, `operations`, `commercial`, `finance-legal`) |
| **`4001`** | **COSA Platform Gateway** | `services/cosa` | *(Host process)* | API Central Control Plane (Đăng ký, Đăng nhập platform, Gói cước, Bản quyền) |
| **`8000`** | **AgentOS / Brain API** | `backend` | `cosa_brain_api` | AI Multi-Agent Engine & Governance Plane (FastAPI / Python) |
| **`8765`** | **Desktop Worker** | `worker` | *(Host process)* | Worker thực thi tác vụ cục bộ trên máy (Loopback Plane) |
| **`7885` / `7886`** | **LiveKit Server** | `services/realtime_agent` | `company_livekit` | WebRTC Streaming cho Realtime Voice AI |
| **`5433`** | **Company Postgres DB** | Docker Compose (`services`) | `company_db` | Database nghiệp vụ của doanh nghiệp (Database `company` - 55 bảng) |
| **`5434`** | **Central Postgres DB** | Docker Compose (`central_vps`) | `cosa_db` | Database quản trị nền tảng COSA (Database `cosa` - 9 bảng) |
| **`5678`** | **n8n Automation** | Docker Compose (`infra/n8n`) | `javis_n8n` | Workflow Automation cho Marketing & Email |

---

## 7. Quy trình Khởi Động & Chạy Kiểm Thử

### 7.1. Khởi động 2 ứng dụng Backend

```bash
# 1. Khởi động Company Services (Port 4000)
cd /Volumes/SSD/javis-saas/services/company
encore run --port=4000

# 2. Khởi động COSA Central Control Plane (Port 4001, mở terminal riêng)
cd /Volumes/SSD/javis-saas/services/cosa
encore run --port=4001
```

---

### 7.2. Chạy Kiểm Thử Tự Động (100% Tests Pass)

```bash
# Test Company Microservices (36 test suites, 145 tests)
cd /Volumes/SSD/javis-saas/services/company
encore test

# Test COSA Control Plane (2 test suites, 14 tests)
cd /Volumes/SSD/javis-saas/services/cosa
encore test

# Test Frontend Flutter (29 unit & widget tests)
cd /Volumes/SSD/javis-saas/frontend
flutter test test/auth_flow_test.dart
```

---

### 7.3. Các câu lệnh SQL mẫu tra cứu dữ liệu

#### 1. Kiểm tra tài khoản Platform, Bản quyền & Gói cước trên Control Plane (Port 5434):
```sql
-- Kết nối vào database cosa (Port 5434)
SELECT id, email, phone, status, is_platform_admin, created_at 
FROM cosa.users 
ORDER BY created_at DESC;

SELECT id, slug, name, status, created_by 
FROM cosa.companies;

SELECT id, name, default_limits, default_features 
FROM cosa.plans;

SELECT id, company_id, plan_id, license_key, status, expires_at 
FROM cosa.licenses;

SELECT company_id, plan_id, effective_limits, effective_features 
FROM cosa.company_entitlements;
```

#### 2. Kiểm tra tài khoản, Workspace & Tổ chức trên Company Node (Port 5433):
```sql
-- Kết nối vào database company (Port 5433)
SELECT id, email, display_name, role, platform_user_id, status 
FROM core.users;

SELECT id, name, company_stage, platform_company_id 
FROM core.workspaces;

SELECT id, workspace_id, user_id, role 
FROM core.workspace_members;

SELECT id, organization_id, member_type, role_title, status 
FROM core.workforce_members;
```

#### 3. Kiểm tra Tasks, OKRs & Kế hoạch 12 tuần (Port 5433):
```sql
-- Kết nối vào database company (Port 5433)
SELECT id, title, status, priority, workspace_id 
FROM operating.tasks;

SELECT id, task_id, depends_on_task_id, dependency_type, status 
FROM operating.task_dependencies;

SELECT id, title, status, cycle_id 
FROM strategy.okr_objectives;

SELECT id, objective_id, title, baseline_value, current_value, target_value 
FROM strategy.key_results;

SELECT id, theme, vision_statement, status, overall_execution_score 
FROM operating.twelve_week_cycles;

SELECT id, cycle_id, week_no, mission, execution_score 
FROM operating.weekly_plans;
```

#### 4. Kiểm tra Chiến lược Khởi nghiệp & Stage Gates (Port 5433):
```sql
-- Kết nối vào database company (Port 5433)
SELECT id, title, phase, current_gate, status 
FROM strategy.projects;

SELECT id, project_id, statement, risk_score, status 
FROM strategy.assumptions;

SELECT id, project_id, hypothesis, method, status 
FROM strategy.experiments;

SELECT id, project_id, source_type, claim, strength, supports_or_refutes 
FROM strategy.evidence;

SELECT id, project_id, result, evidence_score, requirements_met 
FROM strategy.gate_evaluations;

SELECT id, project_id, decision, actor_workforce_member_id 
FROM strategy.decision_records;
```

#### 5. Kiểm tra CRM & Chiến dịch Marketing (Port 5433):
```sql
-- Kết nối vào database company (Port 5433)
SELECT id, name, industry, size_segment, lifecycle_status 
FROM sales.accounts;

SELECT id, account_id, name, stage, value, fit_score 
FROM sales.sales_leads;

SELECT id, account_id, stage, estimated_value, probability 
FROM sales.sales_opportunities;

SELECT id, name, funnel_stage, budget, status 
FROM commercial.marketing_campaigns;

SELECT id, customer_id, invoice_number, amount, currency, status 
FROM commercial.invoices;
```

#### 6. Kiểm tra Sổ sách Kế toán & Quản trị Tài chính (Port 5433):
```sql
-- Kết nối vào database company (Port 5433)
SELECT id, workspace_id, mode, status 
FROM finance.accounting_profiles;

SELECT id, fiscal_year, regulation_code, mode, status 
FROM finance.accounting_fiscal_profiles;

SELECT id, transaction_date, description, amount, direction, approval_status 
FROM finance.financial_transactions;

SELECT id, cycle_id, as_of, cash, burn, runway_months, revenue, expenses 
FROM finance.finance_management_snapshots;
```
