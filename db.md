# COSA / JAVIS Database Architecture & Operations Guide

Tài liệu chi tiết về cấu trúc cơ sở dữ liệu, phân vùng schema, cấu hình kết nối, quy trình migration và hướng dẫn vận hành cho hệ thống **JAVIS - COSA SaaS**.

---

## 1. Tổng quan kiến trúc Database

Hệ thống sử dụng **PostgreSQL 16** tích hợp extension **`pgvector`** (v0.8.6+) phục vụ lưu trữ vector embeddings cho AI Agents, Knowledge Base và RAG.

### Mô hình Hybrid Data Architecture
**Đã tách vật lý** (không chỉ tách schema) thành 2 database riêng biệt, cùng 1 Postgres server hiện tại nhưng KHÔNG còn co-locate chung database/role:
1. **Local Business Database — database `javis`** (schema `public`):
   - Lưu trữ toàn bộ dữ liệu nghiệp vụ của workspace/doanh nghiệp: AI Workforce, Agent Runtime, Chat Sessions, Vault Documents, Workflows, Strategy, Projects, OKRs, Outbox/Inbox.
   - Quản lý migration độc lập qua `backend/alembic.ini`.
   - Truy cập bằng role `javis_app` (không superuser).
2. **Central Control Plane — database `cosa_control_plane`** (schema `control_plane`):
   - Lưu trữ metadata tập trung quản lý đa tenant: Companies, Licenses, Plans, Deployments, Programs, Cohorts, Platform Users, Install Credentials.
   - Quản lý migration độc lập qua `backend/alembic_control_plane.ini`.
   - Truy cập bằng role `cosa_control_plane_app` (không superuser) — **cách ly hoàn toàn** khỏi `javis_app` (đã `REVOKE CONNECT ... FROM PUBLIC` + chỉ `GRANT CONNECT` đích danh cho từng role trên đúng 1 database của nó, xem `deploy/postgres/init/01-create-app-roles.sql`).
3. **ADK Agent Runtime (Schema `adk_runtime`, trong database `javis`)**:
   - Schema chuyên dụng cho Google ADK (Agent Development Kit) lưu trữ session state, memory và event streams của realtime agents.

Role `javis` (superuser) gốc của image vẫn tồn tại nhưng **ứng dụng không dùng nữa** — chỉ dùng để vận hành/migration thủ công qua `docker compose exec postgres psql -U javis`. Trước đây `javis` là superuser dùng chung cho mọi service — 1 credential có toàn quyền trên cả cluster Postgres, không chỉ 2 schema; đã vá bằng cách tách role riêng cho từng bên.

> **Quy ước định danh (Snowflake ID)**: Toàn bộ bảng sử dụng pure 64-bit integer Snowflake ID làm Primary Key (kiểu `BIGINT` trong PostgreSQL), không sử dụng UUID làm PK.

---

## 2. Thông tin kết nối & Cấu hình môi trường

### 2.1. Môi trường Local / Docker

| Thông số | Giá trị mặc định |
| :--- | :--- |
| **Host (từ máy chủ host)** | `127.0.0.1` |
| **Port** | `5432` |
| **Database Name** | `javis` |
| **User** | `javis` |
| **Password** | `javis` |
| **Container Name** | `cosa_postgres` (`pgvector/pgvector:pg16`) |

### 2.2. Connection Strings

- **Local Business DB — từ Host / Local Script**:
  ```bash
  postgresql://javis_app:<password>@127.0.0.1:5432/javis
  ```
- **Local Business DB — nội bộ giữa các Docker Containers**:
  ```bash
  postgresql://javis_app:<password>@postgres:5432/javis
  ```
- **Central Control Plane — nội bộ giữa các Docker Containers**:
  ```bash
  postgresql://cosa_control_plane_app:<password>@postgres:5432/cosa_control_plane
  ```
- **Vận hành thủ công (superuser, chỉ dùng ngoài ứng dụng)**:
  ```bash
  docker compose exec postgres psql -U javis -d javis        # hoặc -d cosa_control_plane, -d postgres
  ```

### 2.3. Biến môi trường (`.env` / `backend/.env`)

```env
# Database Settings — role/database RIÊNG cho từng bên, xem mục 1
POSTGRES_USER=javis
POSTGRES_PASSWORD=javis
POSTGRES_DB=javis
DATABASE_URL=postgresql://javis_app:<password>@postgres:5432/javis
CONTROL_PLANE_DATABASE_URL=postgresql://cosa_control_plane_app:<password>@postgres:5432/cosa_control_plane
```

Mật khẩu thật của `javis_app`/`cosa_control_plane_app` lưu trong `.env` (đã gitignore) — không commit vào repo. `deploy/postgres/init/01-create-app-roles.sql` chỉ chứa placeholder, tự chạy khi khởi tạo volume Postgres mới; instance đang chạy sẵn phải tạo role này thủ công 1 lần.

---

## 3. Danh mục Schema & Bảng dữ liệu

### 3.1. Database `javis` (Local Business DB)

Đã tách thêm 2 schema con theo FK graph thật (nhóm có ít phụ thuộc ngược ra ngoài) — business core (auth/vault/strategy/sales/finance/validation/policy, ~202 bảng, đan xen quá dày để tách an toàn) vẫn ở `public`.

**Schema `public` (~202 bảng)**:
- **Platform Core & Auth**: `users`, `workspaces`, `workspace_members`, `workspace_domains`, `audit_logs`, `feature_flags`, `platform_inbox`, `platform_outbox`.
- **Vault & Knowledge (RAG)**: `vault_documents`, `vault_revisions`, `document_chunks`, `knowledge_objects`, `context_packs`, `context_pack_sources`, `analysis_imports`.
- **Strategy, OKR & Projects**: `strategy_foundations`, `strategy_canvases`, `strategy_analyses`, `swot_items`, `pestel_items`, `okr_cycles`, `okr_objectives`, `key_results`, `portfolios`, `portfolio_projects`, `projects`, `twelve_week_cycles`, `weekly_plans`, `tasks`.
- Sales, Marketing, Finance, Legal, Validation/Learning, Organization — xem `backend/business_core/*`.

**Schema `agent_runtime` (54 bảng)** — Agent Definitions/Governance/Memory/Sandbox, xem `backend/workforce/*` (trừ `workforce/chat`), `backend/agent_runtime/*`, `backend/core/protected_resources`:
- `agent_definitions`, `agent_hierarchies`, `agent_goals`, `agent_plans`, `agent_plan_steps`, `agent_runs`, `agent_events`, `agent_tool_calls`, `agent_approvals`, `runtime_sessions`, `sandbox_policies`, `protected_resources`, `protected_resource_revisions`, `capability_grants`, `job_outcomes`, `tool_definitions`, `platform_tool_versions`, `unified_permissions`, `approval_requests`, `agent_budgets`, `cost_ledger_entries`, `platform_prompt_templates`, `platform_prompt_versions`, `platform_secret_refs`, `execution_jobs`, `execution_steps`, `delegation_jobs`, `mission_resume_jobs`, `memory_candidates`, `memory_evaluations`, `agent_memory_engines`, `agent_memory_entries`, `agent_memory_scopes`, `automation_definitions`, `automation_runs`, `agent_proposals`, `global_skill_registry`... (danh sách đầy đủ 54 bảng: xem `AGENT_RUNTIME_TABLES` trong `backend/alembic/versions/ce172b817a1d_split_agent_runtime_and_integrations_.py`).

**Schema `integrations` (25 bảng)** — Connectors, Chat/Realtime, Workflows, xem `backend/integrations/*`, `backend/workforce/chat`:
- `mcp_connections`, `workspace_secrets`, `chatbots`, `chatbot_conversations`, `chat_sessions`, `chat_messages`, `ai_runs`, `plugins`, `workspace_plugins`, `outbox`, `email_approvals`, `zalo_qr_sessions`, `devices`, `device_credentials`, `developer_jobs`, `job_leases`, `realtime_sessions`, `realtime_events`, `voice_usage_records`, `task_workflow_bindings`, `workflow_runs`, `workflow_definitions`, `workflow_versions`, `workflow_steps`, `workflow_approvals` (danh sách đầy đủ: xem `INTEGRATIONS_TABLES` cùng file migration trên).

**Schema `adk_runtime` (Google ADK Realtime State)** — ADK tự tạo bảng của nó (`sessions`, `app_states`, `user_states`, `events`), COSA chỉ đảm bảo schema tồn tại sẵn (`CREATE SCHEMA IF NOT EXISTS`).

### 3.2. Database `cosa_control_plane` (Central Control Plane, tách vật lý — mục 1)

Schema `control_plane` (20 bảng nghiệp vụ + `alembic_version`) — quản trị multi-tenant và SaaS subscriptions:
- `companies`, `company_memberships`, `company_entitlements`, `company_web_apps`
- `plans`, `licenses`
- `cohorts`, `programs`, `program_participants`
- `deployments`, `domains`
- `projects_registry`, `project_metrics`, `project_outcomes`, `project_program_links`, `project_stage_history`
- `platform_users`, `user_sessions`, `form_submissions`
- `install_credentials` (bearer credential máy-với-máy cho kênh sync, xem mục 7)

---

## 4. Quản lý Migration (Alembic)

Hệ thống duy trì **2 luồng migration độc lập**:

### 4.1. Local Business DB Migrations
- **Config**: `backend/alembic.ini`
- **Thư mục scripts**: `backend/alembic/versions/`
- **Chạy nâng cấp lên phiên bản mới nhất**:
  ```bash
  # Trên máy host (có venv):
  PYTHONPATH=backend ./backend/.venv/bin/alembic -c backend/alembic.ini upgrade head

  # Hoặc thông qua Docker:
  docker compose exec brain-api alembic upgrade head
  ```
- **Tạo migration mới**:
  ```bash
  cd backend && alembic revision --autogenerate -m "ten_migration"
  ```

### 4.2. Control Plane Migrations
- **Config**: `backend/alembic_control_plane.ini`
- **Thư mục scripts**: `backend/alembic_control_plane/versions/`
- **Chạy nâng cấp**:
  ```bash
  # Trên máy host:
  CONTROL_PLANE_DATABASE_URL=postgresql://cosa_control_plane_app:<password>@127.0.0.1:5432/cosa_control_plane \
    PYTHONPATH=backend ./backend/.venv/bin/alembic -c backend/alembic_control_plane.ini upgrade head

  # Hoặc thông qua Docker:
  docker compose --profile control-plane run --rm migrate-control-plane
  ```

---

## 5. Hướng dẫn Reset Database

### 5.1. Reset nhanh qua SQL (Khuyên dùng trong Dev)
Reset database `javis` (Local Business) và `cosa_control_plane` (Control Plane) **riêng biệt** — 2 database vật lý khác nhau từ khi tách (mục 1), không còn 1 lệnh DROP SCHEMA xử lý cả 2 như trước:

```bash
# 1. Reset database Local Business (javis)
docker compose exec postgres psql -U javis -d javis -c "
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO javis_app;
CREATE EXTENSION IF NOT EXISTS vector SCHEMA public;
DROP SCHEMA IF EXISTS adk_runtime CASCADE;
DROP SCHEMA IF EXISTS agent_runtime CASCADE;
DROP SCHEMA IF EXISTS integrations CASCADE;
"

# 2. Reset database Control Plane (cosa_control_plane)
docker compose exec postgres psql -U javis -d cosa_control_plane -c "
DROP SCHEMA IF EXISTS control_plane CASCADE;
"

# 3. Chạy migration Business DB
docker compose exec brain-api alembic upgrade head

# 4. Chạy migration Control Plane DB
docker compose --profile control-plane up migrate-control-plane

# 5. Khởi tạo tài khoản dev admin (tùy chọn)
docker compose exec -e DEV_ADMIN_PASSWORD=admin123 brain-api python -m scripts.bootstrap_dev_user
```

### 5.2. Reset hoàn toàn bằng việc xóa Docker Volume
```bash
docker compose down -v
docker compose up -d
docker compose --profile control-plane up migrate-control-plane
```

---

## 6. Kiểm tra trạng thái & Health Check

### 6.1. Kiểm tra readiness qua API
```bash
curl -fsS http://127.0.0.1:8000/ready
```
**Kết quả mong đợi**:
```json
{
  "status": "ready",
  "checks": {
    "database": "ok",
    "storage": "ok",
    "migrations": "ok",
    "worker": "ok"
  }
}
```

### 6.2. Truy cập psql CLI trực tiếp
```bash
docker compose exec postgres psql -U javis -d javis              # Local Business DB
docker compose exec postgres psql -U javis -d cosa_control_plane  # Central Control Plane DB
```
- Liệt kê schemas trong 1 database: `\dn`
- Liệt kê bảng trong schema `public` (DB `javis`): `\dt public.*`
- Liệt kê bảng trong schema `control_plane` (DB `cosa_control_plane`): `\dt control_plane.*`
- Liệt kê tất cả database: `\l`
- Liệt kê role: `\du`
- Kiểm tra extensions: `\dx`

---

## 7. Auth & Role - 2 tầng tách biệt

Local Business DB và Central Control Plane co-locate cùng 1 Postgres instance (mục 1) nhưng có 2 cơ chế auth hoàn toàn độc lập, không dùng chung JWT:

### 7.1. Local (`public.users` / `WorkspaceMember.role`)
- Login: `POST /api/v1/auth/sessions` (`backend/platform_core/auth/router.py`) → JWT chỉ mang claim `sub=user_id`, KHÔNG có `aud`.
- Phân quyền: `backend/core/authz.py` đọc `WorkspaceMember.role` (`owner/admin/editor/member/viewer`) - quyền trong phạm vi 1 workspace/project, không liên quan control-plane.

### 7.2. Central Control Plane (`control_plane.platform_users` / `CompanyMembership.platform_role`)
- Login: `POST /api/v1/platform/auth/sessions` (`backend/platform_core/control_plane/router_auth.py`) → JWT dùng chung `JWT_SECRET`/`JWT_ALGORITHM` với Local nhưng **bắt buộc claim `aud="control_plane"`** (`backend/platform_core/control_plane/security.py`) - PyJWT tự chặn cả 2 chiều nên 1 token Local không thể dùng cho control-plane và ngược lại.
- Phân quyền hành động quản trị company (billing, mời thành viên...): `backend/platform_core/control_plane/authz.py` đọc `CompanyMembership.platform_role` (`owner/admin/member`).
- Hành động toàn nền tảng không thuộc 1 company (vd. ký entitlement snapshot, `/sync/entitlement/sign`): yêu cầu `PlatformUser.is_platform_admin=True`, kiểm tra qua `require_platform_admin()`.
- Kênh sync máy-với-máy giữa 1 Local install và Central (`/sync/ingest`, `/sync/outbox/trigger`, `/sync/status`): **không** dùng JWT người dùng - dùng `InstallCredential` (bearer token hash SHA-256, mirror `DeviceCredential` của Local) tạo qua `POST /api/v1/platform/sync/install-credentials` (chỉ platform admin gọi được).

### 7.3. Mapping giữa 2 tầng
- `public.users.platform_user_id`, `public.workspaces.platform_company_id`, `public.projects.platform_project_id` trỏ sang ID bên control-plane.
- Không đồng bộ (không "đẩy") `platform_role` xuống Local lưu bản sao - nếu Local UI cần biết role quản trị công ty, gọi trực tiếp API control-plane đã xác thực theo yêu cầu (on-demand), tránh 2 nguồn sự thật lệch nhau.
