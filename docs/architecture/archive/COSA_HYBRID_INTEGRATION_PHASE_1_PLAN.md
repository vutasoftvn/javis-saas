# COSA Hybrid Architecture — Phase 1 Detailed Implementation Plan
## Schema Standardization, Supabase Central Control Plane & Local Baseline

> **Superseded by `docs/architecture/COSA_ADK_ORCHESTRATOR_UUID7_PROPOSAL.md` Quyết định 2 (2026-08-21)** — production does not use Supabase; control-plane is pure Postgres via Alembic. Kept for historical context.

> **Tài liệu cha:** [`COSA_HYBRID_LOCAL_POSTGRESQL_SUPABASE_INTEGRATION_PLAN.md`](./COSA_HYBRID_LOCAL_POSTGRESQL_SUPABASE_INTEGRATION_PLAN.md)  
> **Tài liệu đặc tả kiến trúc v2:** [`markdown/COSA_Hybrid_Local_PostgreSQL_Supabase_Project_Intelligence_Integration_v2.md`](../../markdown/COSA_Hybrid_Local_PostgreSQL_Supabase_Project_Intelligence_Integration_v2.md)  
> **Mục tiêu Phase 1:** Khởi tạo DDL chuẩn cho Supabase Central (Control Plane), thiết lập Row Level Security (RLS), định nghĩa lớp ánh xạ định danh (Snowflake 64-bit ID $\leftrightarrow$ Platform UUID), và cập nhật schema nền tảng tại PostgreSQL Local mà không làm gián đoạn hệ thống hiện tại.  
> **Trạng thái:** Kế hoạch chi tiết (Chờ duyệt, chưa thực thi code).

---

## 1. PHÂN TÍCH HIỆN TRẠNG & KHOẢNG TRỐNG (CODEBASE AUDIT)

### 1.1 Khảo sát mô hình dữ liệu Local hiện tại
Qua rà soát hệ thống PostgreSQL Local (`backend/app`):

| Local Model / File | Định danh hiện tại | Đặc điểm nghiệp vụ | Ánh xạ mục tiêu lên Central Supabase |
| :--- | :--- | :--- | :--- |
| [`User`](file:///Volumes/SSD/javis-saas/backend/app/platform/auth/models.py) | `BigInteger` (Snowflake) | Chứa email, phone, password_hash, status. | `platform_users` (UUID từ Supabase Auth `auth.users.id`) |
| [`Workspace`](file:///Volumes/SSD/javis-saas/backend/app/platform/auth/models.py) | `BigInteger` (Snowflake) | Đại diện cho một Company/Tenant trên Local (`company_stage`). | `companies` (UUID `platform_company_id`) |
| [`WorkspaceMember`](file:///Volumes/SSD/javis-saas/backend/app/platform/auth/models.py) | `BigInteger` (Snowflake) | Map quan hệ User - Workspace (`role: admin, member`). | `company_memberships` |
| [`Project`](file:///Volumes/SSD/javis-saas/backend/app/founder_os/strategy/models.py) | `BigInteger` (Snowflake) | Quản lý dự án, taxonomy stage: `S0_EXPLORE` $\rightarrow$ `S6_SCALE_GOVERN`. | `projects_registry` (`platform_project_id` UUID) |
| [`ProjectStageHistory`](file:///Volumes/SSD/javis-saas/backend/app/founder_os/validation/models.py) | `BigInteger` (Snowflake) | Lưu vết chuyển đổi stage trong Validation. | `project_stage_history` (Central Stage Tracking) |
| [`FormDefinition` / `FormSubmission`](file:///Volumes/SSD/javis-saas/backend/app/business/marketing/form_models.py) | `BigInteger` (Snowflake) | Định nghĩa form và lưu submission từ web. | `form_submissions` (Public Edge Intake) |
| [`Deployment`](file:///Volumes/SSD/javis-saas/backend/app/platform/core/deployment_models.py) | `BigInteger` (Snowflake) | Lưu metadata deployment frontend. | `deployments` (Target: `cosa_shared_vps`, `company_vps`...) |

### 1.2 Khoảng trống kỹ thuật cần giải quyết trong Phase 1
1. **Lệch kiểu dữ liệu ID (ID Mismatch)**: Local sử dụng `SnowflakeID` (`BigInteger` int64), trong khi Supabase Auth và Central Control Plane sử dụng `UUIDv4/UUIDv7`. Cần bổ sung trường `platform_xxx_id` (UUID) có đánh index trên Local để làm foreign key logic với Central.
2. **Chưa có DDL cho Central Control Plane**: Cần bộ DDL PostgreSQL độc lập cho Supabase Central gồm các domain: Identity, Commercial (Plans/Licenses/Entitlements), Project Registry, Programs/Cohorts và Public Marketing Registry.
3. **Đồng bộ Taxonomy Stage**: Cần chuẩn hóa enum taxonomy các giai đoạn khởi nghiệp thống nhất giữa Local và Central (`S0_EXPLORE`, `S1_PROBLEM_VALIDATION`, `S2_SOLUTION_VALIDATION`, `S3_BUSINESS_VALIDATION`, `S4_GO_TO_MARKET`, `S5_OPERATE_GROWTH`, `S6_SCALE_GOVERN`).

---

## 2. THIẾT KẾ CENTRAL SUPABASE CONTROL PLANE DDL (PHASE 1)

Bộ script DDL dưới đây được phân bổ theo 5 domain nghiệp vụ trên Supabase Central:

```
Supabase Central Database
├── 1. Platform Identity & RBAC (platform_users, companies, company_memberships)
├── 2. Commercial & Entitlements (plans, licenses, company_entitlements)
├── 3. Project Registry & Intelligence (projects_registry, project_stage_history, project_outcomes)
├── 4. Programs & Cohorts Ecosystem (programs, cohorts, program_participants, project_program_links)
└── 5. Marketing & Public Edge Registry (company_web_apps, domains, deployments, form_submissions)
```

### 2.1 Domain 1: Platform Identity & Company Registry

```sql
-- Kích hoạt extension UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. Platform User Profile (Liên kết với Supabase auth.users)
CREATE TABLE public.platform_users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    avatar_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Company Registry
CREATE TABLE public.companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    logo_url TEXT,
    industry VARCHAR(100),
    country_code VARCHAR(10) DEFAULT 'VN',
    created_by UUID REFERENCES public.platform_users(id),
    status VARCHAR(50) NOT NULL DEFAULT 'active', -- active, suspended, deleted
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- 3. Company Membership (RBAC trên Platform)
CREATE TABLE public.company_memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.platform_users(id) ON DELETE CASCADE,
    platform_role VARCHAR(50) NOT NULL DEFAULT 'member', -- owner, admin, member, viewer
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_company_user UNIQUE (company_id, user_id)
);
```

### 2.2 Domain 2: Plans, Licenses & Data-Driven Entitlements

```sql
-- 4. Subscription Plans
CREATE TABLE public.plans (
    id VARCHAR(50) PRIMARY KEY, -- 'free', 'starter', 'pro', 'enterprise'
    name VARCHAR(100) NOT NULL,
    description TEXT,
    default_limits JSONB NOT NULL DEFAULT '{"max_projects": 1, "max_seats": 2, "max_scheduled_agents": 1}'::jsonb,
    default_features JSONB NOT NULL DEFAULT '{"marketing": true, "crm": true, "finance": false, "custom_domain": false}'::jsonb,
    is_public BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. Licenses & Commercial Subscriptions
CREATE TABLE public.licenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    plan_id VARCHAR(50) NOT NULL REFERENCES public.plans(id),
    license_key VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active', -- active, grace_period, expired, cancelled
    starts_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    grace_period_days INT NOT NULL DEFAULT 7,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. Dynamic Company Entitlements & Overrides
CREATE TABLE public.company_entitlements (
    company_id UUID PRIMARY KEY REFERENCES public.companies(id) ON DELETE CASCADE,
    plan_id VARCHAR(50) NOT NULL REFERENCES public.plans(id),
    effective_limits JSONB NOT NULL,
    effective_features JSONB NOT NULL,
    custom_overrides JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    snapshot_signature TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 2.3 Domain 3: Project Registry & Stage History

```sql
-- 7. Central Project Registry
CREATE TABLE public.projects_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    local_project_snowflake BIGINT, -- Snowflake ID tại Local PostgreSQL
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100),
    industry VARCHAR(100),
    category VARCHAR(100),
    status VARCHAR(50) NOT NULL DEFAULT 'active', -- active, paused, closed, archived, deleted
    current_stage VARCHAR(50) NOT NULL DEFAULT 'S0_EXPLORE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_stage_change_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_company_project_local UNIQUE (company_id, local_project_snowflake)
);

-- 8. Project Stage History
CREATE TABLE public.project_stage_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES public.projects_registry(id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    from_stage VARCHAR(50),
    to_stage VARCHAR(50) NOT NULL,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    duration_seconds BIGINT, -- Thời gian lưu trú ở stage trước
    change_source VARCHAR(50) DEFAULT 'local_sync', -- local_sync, manual_override, system_rule
    metadata JSONB DEFAULT '{}'::jsonb
);

-- 9. Project Outcomes & Milestones (De-identified facts)
CREATE TABLE public.project_outcomes (
    project_id UUID PRIMARY KEY REFERENCES public.projects_registry(id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    first_interview_at TIMESTAMPTZ,
    first_experiment_at TIMESTAMPTZ,
    mvp_launched_at TIMESTAMPTZ,
    first_customer_at TIMESTAMPTZ,
    first_revenue_at TIMESTAMPTZ,
    has_revenue BOOLEAN NOT NULL DEFAULT false,
    revenue_band VARCHAR(50) DEFAULT '0', -- '0', '<1M', '1M-10M', '10M-50M', '50M-100M', '100M+'
    team_size_band VARCHAR(50) DEFAULT '1-2',
    outcome_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 2.4 Domain 4: Programs & Cohort Intelligence (SIHUB / Incubators)

```sql
-- 10. Programs
CREATE TABLE public.programs (
    id VARCHAR(50) PRIMARY KEY, -- 'sihub_incubation', 'cosa_founder_fellowship'
    name VARCHAR(255) NOT NULL,
    partner_name VARCHAR(255) DEFAULT 'SIHUB',
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 11. Cohorts
CREATE TABLE public.cohorts (
    id VARCHAR(100) PRIMARY KEY, -- 'sihub-2026-aug'
    program_id VARCHAR(50) NOT NULL REFERENCES public.programs(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    status VARCHAR(50) NOT NULL DEFAULT 'active', -- upcoming, active, completed, archived
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 12. Program Participants & Project Links
CREATE TABLE public.program_participants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    program_id VARCHAR(50) NOT NULL REFERENCES public.programs(id) ON DELETE CASCADE,
    cohort_id VARCHAR(100) NOT NULL REFERENCES public.cohorts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.platform_users(id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    enrolled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    CONSTRAINT uq_cohort_participant UNIQUE (cohort_id, company_id)
);

CREATE TABLE public.project_program_links (
    project_id UUID NOT NULL REFERENCES public.projects_registry(id) ON DELETE CASCADE,
    cohort_id VARCHAR(100) NOT NULL REFERENCES public.cohorts(id) ON DELETE CASCADE,
    linked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (project_id, cohort_id)
);
```

### 2.5 Domain 5: Marketing App & Public Edge Intake

```sql
-- 13. Company Web Apps
CREATE TABLE public.company_web_apps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    app_type VARCHAR(50) NOT NULL DEFAULT 'marketing',
    repository_ref TEXT,
    deployment_mode VARCHAR(50) NOT NULL DEFAULT 'cosa_managed', -- cosa_managed, company_vps, fully_private
    current_version VARCHAR(50) DEFAULT 'v1.0.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 14. Domains
CREATE TABLE public.domains (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    app_id UUID NOT NULL REFERENCES public.company_web_apps(id) ON DELETE CASCADE,
    hostname VARCHAR(255) UNIQUE NOT NULL,
    domain_type VARCHAR(50) NOT NULL DEFAULT 'cosa_subdomain', -- cosa_subdomain, custom_domain
    verification_status VARCHAR(50) NOT NULL DEFAULT 'verified',
    ssl_status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 15. Public Form Submissions (Intake Gateway Edge)
CREATE TABLE public.form_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    project_id UUID REFERENCES public.projects_registry(id),
    form_slug VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    source_domain VARCHAR(255),
    ip_hash VARCHAR(64),
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sync_status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, synced_to_local, archived
    synced_at TIMESTAMPTZ
);
```

---

## 3. ROW LEVEL SECURITY (RLS) POLICIES TRÊN SUPABASE CENTRAL

Để ngăn chặn tuyệt đối rò rỉ dữ liệu giữa các công ty (Multi-tenant isolation):

```sql
-- Bật RLS cho tất cả các bảng
ALTER TABLE public.platform_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.company_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.licenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.company_entitlements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.projects_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.project_stage_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.project_outcomes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.form_submissions ENABLE ROW LEVEL SECURITY;

-- Helper function: Lấy danh sách company_id của user hiện tại từ JWT
CREATE OR REPLACE FUNCTION public.current_user_company_ids()
RETURNS SETOF UUID AS $$
    SELECT company_id 
    FROM public.company_memberships 
    WHERE user_id = auth.uid();
$$ LANGUAGE sql STABLE SECURITY DEFINER;

-- Policy mẫu cho Projects Registry: User chỉ thấy project thuộc company của mình
CREATE POLICY "Users can view their company projects"
ON public.projects_registry
FOR SELECT
USING (company_id IN (SELECT public.current_user_company_ids()));

-- Policy cho Form Submissions: Public có thể INSERT, nhưng chỉ Company Members mới có thể SELECT
CREATE POLICY "Public edge can insert form submissions"
ON public.form_submissions
FOR INSERT
WITH CHECK (true);

CREATE POLICY "Company members can read own form submissions"
ON public.form_submissions
FOR SELECT
USING (company_id IN (SELECT public.current_user_company_ids()));
```

---

## 4. BỔ SUNG NỀN TẢNG LOCAL POSTGRESQL (BACKWARD-COMPATIBLE)

Tại PostgreSQL Local, các model được cập nhật thêm các trường liên kết mà không làm thay đổi hay xóa dữ liệu cũ:

### 4.1 Nâng cấp Model `Workspace` và `User` ([`app.platform.auth.models`](file:///Volumes/SSD/javis-saas/backend/app/platform/auth/models.py))
```python
# Bổ sung vào User:
platform_user_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True) # UUIDv4

# Bổ sung vào Workspace:
platform_company_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True) # UUIDv4
```

### 4.2 Nâng cấp Model `Project` ([`app.founder_os.strategy.models`](file:///Volumes/SSD/javis-saas/backend/app/founder_os/strategy/models.py))
```python
# Bổ sung vào Project:
platform_project_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True) # UUIDv4
sync_status: Mapped[str] = mapped_column(String(50), default="synced", index=True) # synced, pending_sync, sync_error
last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
```

---

## 5. KẾ HOẠCH BƯỚC THỰC HIỆN PHASE 1 (STEP-BY-STEP TASKS)

```text
Phase 1 Execution Steps
├── Bước 1.1: Tạo thư mục DDL migrations cho Supabase Central (`backend/migrations/central_supabase/`)
├── Bước 1.2: Viết script DDL 001_initial_central_control_plane.sql (Bao gồm RLS & Functions)
├── Bước 1.3: Viết Alembic migration tại Local để thêm các cột `platform_xxx_id` (Safe, Nullable, Non-breaking)
├── Bước 1.4: Định nghĩa bộ Pydantic Base Schemas cho Data Contracts (`app/platform/sync/schemas.py`)
└── Bước 1.5: Viết Unit test kiểm tra ID Translation (Snowflake <-> UUID) và Schema validation
```

---

## 6. TIÊU CHÍ NGHIỆM THU PHASE 1 (ACCEPTANCE CRITERIA)

- [ ] DDL Supabase Central chạy thành công không có lỗi cú pháp, đã kích hoạt đầy đủ RLS và Index.
- [ ] Schema Local PostgreSQL được cập nhật an toàn bằng migration (Alembic), bảo toàn 100% dữ liệu hiện có.
- [ ] Các Enum taxonomy của Stage (`S0_EXPLORE` $\rightarrow$ `S6_SCALE_GOVERN`) được chuẩn hóa nhất quán giữa 2 bên.
- [ ] RLS Policy được xác thực: Không một user nào có thể đọc dữ liệu project của company khác qua Supabase API.
- [ ] Không có code sửa đổi logic nghiệp vụ đang chạy ở Local hay Frontend.
