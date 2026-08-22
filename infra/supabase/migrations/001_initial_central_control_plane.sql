-- ============================================================================
-- [SUPERSEDED] File này đã được thay thế bởi Alembic migration:
-- backend/alembic_control_plane/versions/c9a1f0b2e3d4_unify_central_control_plane_schema.py
--
-- Lý do: Hợp nhất schema Central Control Plane theo kế hoạch
-- docs/superpowers/plans/2026-08-21-central-control-plane-db.md (Quyết định 6.2).
-- Tất cả các bảng đã được chuyển vào schema PostgreSQL `control_plane` riêng
-- biệt để tránh va chạm tên bảng (`deployments`) và dùng chung 1 PostgreSQL
-- instance gọn nhẹ.
--
-- GIỮ LẠI FILE NÀY ĐỂ THAM CHIẾU LỊCH SỬ — KHÔNG SỬ DỤNG CHO DEPLOY MỚI.
-- Chạy migration mới: alembic -c backend/alembic_control_plane.ini upgrade head
-- ============================================================================
-- ============================================================================
-- COSA PLATFORM CENTRAL CONTROL PLANE - INITIAL SCHEMA (PHASE 1)
-- PostgreSQL Migration - Pure Self-Hosted (Snowflake 64-bit ID, Custom JWT Auth)
-- Auth: Custom JWT (HS256) — KHÔNG dùng Supabase Auth / auth.users
-- Specification: COSA_Hybrid_Local_PostgreSQL_Supabase_Project_Intelligence_Integration_v2.md
-- ============================================================================

-- 0. EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- 0.1 NATIVE POSTGRESQL SNOWFLAKE ID GENERATOR
-- Custom Epoch: 2026-01-01 00:00:00 UTC = 1767225600000 ms
-- Bit layout: [0][41-bit timestamp][10-bit node][12-bit sequence]
-- ============================================================================
CREATE SEQUENCE IF NOT EXISTS public.snowflake_id_seq;

CREATE OR REPLACE FUNCTION public.generate_snowflake_id()
RETURNS BIGINT AS $$
DECLARE
    our_epoch BIGINT := 1767225600000; -- Epoch 2026-01-01 00:00:00 UTC
    seq_id BIGINT;
    now_millis BIGINT;
    node_id BIGINT := 1;
    result BIGINT := 0;
BEGIN
    SELECT nextval('public.snowflake_id_seq') % 4096 INTO seq_id;
    SELECT FLOOR(EXTRACT(EPOCH FROM clock_timestamp()) * 1000) INTO now_millis;
    result := (now_millis - our_epoch) << 22;
    result := result | (node_id << 12);
    result := result | seq_id;
    RETURN result;
END;
$$ LANGUAGE PLPGSQL;

-- ============================================================================
-- 1. PLATFORM IDENTITY & COMPANY REGISTRY
-- ============================================================================

-- 1.1 Platform User Profile (Snowflake ID, tự quản lý auth — không phụ thuộc Supabase Auth)
-- Đăng ký bằng email HOẶC phone (ít nhất một cái bắt buộc)
CREATE TABLE IF NOT EXISTS public.platform_users (
    id BIGINT PRIMARY KEY DEFAULT public.generate_snowflake_id(),
    email VARCHAR(255) UNIQUE,                         -- nullable: có thể đăng ký bằng phone
    phone VARCHAR(50) UNIQUE,                          -- nullable: có thể đăng ký bằng email
    hashed_password TEXT NOT NULL,                     -- bcrypt hash
    full_name VARCHAR(255),
    avatar_url TEXT,
    is_platform_admin BOOLEAN NOT NULL DEFAULT false,
    status VARCHAR(50) NOT NULL DEFAULT 'active',      -- active, suspended, deleted
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT chk_email_or_phone CHECK (
        email IS NOT NULL OR phone IS NOT NULL
    )
);

CREATE INDEX IF NOT EXISTS ix_platform_users_email ON public.platform_users(email) WHERE email IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_platform_users_phone ON public.platform_users(phone) WHERE phone IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_platform_users_status ON public.platform_users(status);

-- 1.2 Company Registry
CREATE TABLE IF NOT EXISTS public.companies (
    id BIGINT PRIMARY KEY DEFAULT public.generate_snowflake_id(),
    slug VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    logo_url TEXT,
    industry VARCHAR(100),
    country_code VARCHAR(10) DEFAULT 'VN',
    created_by BIGINT REFERENCES public.platform_users(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'active',      -- active, suspended, deleted
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_companies_slug ON public.companies(slug);
CREATE INDEX IF NOT EXISTS ix_companies_status ON public.companies(status);

-- 1.3 Company Membership (Platform RBAC)
CREATE TABLE IF NOT EXISTS public.company_memberships (
    id BIGINT PRIMARY KEY DEFAULT public.generate_snowflake_id(),
    company_id BIGINT NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES public.platform_users(id) ON DELETE CASCADE,
    platform_role VARCHAR(50) NOT NULL DEFAULT 'member', -- owner, admin, member, viewer
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_company_user UNIQUE (company_id, user_id)
);

CREATE INDEX IF NOT EXISTS ix_company_memberships_user ON public.company_memberships(user_id);
CREATE INDEX IF NOT EXISTS ix_company_memberships_company ON public.company_memberships(company_id);

-- ============================================================================
-- 2. COMMERCIAL, PLANS, LICENSES & ENTITLEMENTS
-- ============================================================================

-- 2.1 Subscription Plans
CREATE TABLE IF NOT EXISTS public.plans (
    id VARCHAR(50) PRIMARY KEY,                        -- 'free', 'starter', 'pro', 'enterprise'
    name VARCHAR(100) NOT NULL,
    description TEXT,
    default_limits JSONB NOT NULL DEFAULT '{"max_projects": 1, "max_seats": 2, "max_scheduled_agents": 1}'::jsonb,
    default_features JSONB NOT NULL DEFAULT '{"marketing": true, "crm": true, "finance": false, "custom_domain": false}'::jsonb,
    is_public BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2.2 Licenses & Commercial Subscriptions
CREATE TABLE IF NOT EXISTS public.licenses (
    id BIGINT PRIMARY KEY DEFAULT public.generate_snowflake_id(),
    company_id BIGINT NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    plan_id VARCHAR(50) NOT NULL REFERENCES public.plans(id),
    license_key VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',      -- active, grace_period, expired, cancelled
    starts_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    grace_period_days INT NOT NULL DEFAULT 7,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_licenses_company ON public.licenses(company_id);
CREATE INDEX IF NOT EXISTS ix_licenses_key ON public.licenses(license_key);

-- 2.3 Company Entitlements & Overrides
CREATE TABLE IF NOT EXISTS public.company_entitlements (
    company_id BIGINT PRIMARY KEY REFERENCES public.companies(id) ON DELETE CASCADE,
    plan_id VARCHAR(50) NOT NULL REFERENCES public.plans(id),
    effective_limits JSONB NOT NULL,
    effective_features JSONB NOT NULL,
    custom_overrides JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    snapshot_signature TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- 3. PROJECT REGISTRY, STAGE HISTORY & OUTCOMES
-- ============================================================================

-- 3.1 Central Project Registry
CREATE TABLE IF NOT EXISTS public.projects_registry (
    id BIGINT PRIMARY KEY DEFAULT public.generate_snowflake_id(),
    company_id BIGINT NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    local_project_snowflake BIGINT,                    -- Snowflake ID tại Local PostgreSQL
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100),
    industry VARCHAR(100),
    category VARCHAR(100),
    status VARCHAR(50) NOT NULL DEFAULT 'active',      -- active, paused, closed, archived, deleted
    current_stage VARCHAR(50) NOT NULL DEFAULT 'S0_EXPLORE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_stage_change_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_company_project_local UNIQUE (company_id, local_project_snowflake)
);

CREATE INDEX IF NOT EXISTS ix_projects_registry_company ON public.projects_registry(company_id);
CREATE INDEX IF NOT EXISTS ix_projects_registry_stage ON public.projects_registry(current_stage);

-- 3.2 Project Stage History
CREATE TABLE IF NOT EXISTS public.project_stage_history (
    id BIGINT PRIMARY KEY DEFAULT public.generate_snowflake_id(),
    project_id BIGINT NOT NULL REFERENCES public.projects_registry(id) ON DELETE CASCADE,
    company_id BIGINT NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    from_stage VARCHAR(50),
    to_stage VARCHAR(50) NOT NULL,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    duration_seconds BIGINT,
    change_source VARCHAR(50) DEFAULT 'local_sync',    -- local_sync, manual_override, system_rule
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS ix_project_stage_history_project ON public.project_stage_history(project_id);
CREATE INDEX IF NOT EXISTS ix_project_stage_history_company ON public.project_stage_history(company_id);

-- 3.3 Project Outcomes & Milestones (De-identified Facts)
CREATE TABLE IF NOT EXISTS public.project_outcomes (
    project_id BIGINT PRIMARY KEY REFERENCES public.projects_registry(id) ON DELETE CASCADE,
    company_id BIGINT NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    first_interview_at TIMESTAMPTZ,
    first_experiment_at TIMESTAMPTZ,
    mvp_launched_at TIMESTAMPTZ,
    first_customer_at TIMESTAMPTZ,
    first_revenue_at TIMESTAMPTZ,
    has_revenue BOOLEAN NOT NULL DEFAULT false,
    revenue_band VARCHAR(50) DEFAULT '0',              -- '0', '<1M', '1M-10M', '10M-50M', '50M+'
    team_size_band VARCHAR(50) DEFAULT '1-2',
    outcome_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3.4 Aggregate Project Metrics
CREATE TABLE IF NOT EXISTS public.project_metrics (
    project_id BIGINT PRIMARY KEY REFERENCES public.projects_registry(id) ON DELETE CASCADE,
    company_id BIGINT NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    customer_interview_count INT NOT NULL DEFAULT 0,
    experiment_count INT NOT NULL DEFAULT 0,
    validated_assumption_count INT NOT NULL DEFAULT 0,
    invalidated_assumption_count INT NOT NULL DEFAULT 0,
    lead_count INT NOT NULL DEFAULT 0,
    customer_count INT NOT NULL DEFAULT 0,
    active_campaign_count INT NOT NULL DEFAULT 0,
    mvp_release_count INT NOT NULL DEFAULT 0,
    last_metric_sync_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- 4. PROGRAMS, COHORTS & ECOSYSTEM INTELLIGENCE
-- ============================================================================

-- 4.1 Programs (e.g., SIHUB Incubation, COSA Fellowship)
CREATE TABLE IF NOT EXISTS public.programs (
    id VARCHAR(50) PRIMARY KEY,                        -- 'sihub_incubation', 'cosa_founder_fellowship'
    name VARCHAR(255) NOT NULL,
    partner_name VARCHAR(255) DEFAULT 'SIHUB',
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4.2 Cohorts
CREATE TABLE IF NOT EXISTS public.cohorts (
    id VARCHAR(100) PRIMARY KEY,                       -- 'sihub-2026-aug'
    program_id VARCHAR(50) NOT NULL REFERENCES public.programs(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    status VARCHAR(50) NOT NULL DEFAULT 'active',      -- upcoming, active, completed, archived
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4.3 Program Participants
CREATE TABLE IF NOT EXISTS public.program_participants (
    id BIGINT PRIMARY KEY DEFAULT public.generate_snowflake_id(),
    program_id VARCHAR(50) NOT NULL REFERENCES public.programs(id) ON DELETE CASCADE,
    cohort_id VARCHAR(100) NOT NULL REFERENCES public.cohorts(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES public.platform_users(id) ON DELETE CASCADE,
    company_id BIGINT NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    enrolled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    CONSTRAINT uq_cohort_participant UNIQUE (cohort_id, company_id)
);

CREATE INDEX IF NOT EXISTS ix_program_participants_cohort ON public.program_participants(cohort_id);
CREATE INDEX IF NOT EXISTS ix_program_participants_company ON public.program_participants(company_id);

-- 4.4 Project-Program Links
CREATE TABLE IF NOT EXISTS public.project_program_links (
    project_id BIGINT NOT NULL REFERENCES public.projects_registry(id) ON DELETE CASCADE,
    cohort_id VARCHAR(100) NOT NULL REFERENCES public.cohorts(id) ON DELETE CASCADE,
    linked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (project_id, cohort_id)
);

-- ============================================================================
-- 5. MARKETING & PUBLIC EDGE REGISTRY
-- ============================================================================

-- 5.1 Company Web Apps
CREATE TABLE IF NOT EXISTS public.company_web_apps (
    id BIGINT PRIMARY KEY DEFAULT public.generate_snowflake_id(),
    company_id BIGINT NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    app_type VARCHAR(50) NOT NULL DEFAULT 'marketing',
    repository_ref TEXT,
    deployment_mode VARCHAR(50) NOT NULL DEFAULT 'cosa_managed', -- cosa_managed, company_vps, fully_private
    current_version VARCHAR(50) DEFAULT 'v1.0.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5.2 Domains
CREATE TABLE IF NOT EXISTS public.domains (
    id BIGINT PRIMARY KEY DEFAULT public.generate_snowflake_id(),
    company_id BIGINT NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    app_id BIGINT NOT NULL REFERENCES public.company_web_apps(id) ON DELETE CASCADE,
    hostname VARCHAR(255) UNIQUE NOT NULL,
    domain_type VARCHAR(50) NOT NULL DEFAULT 'cosa_subdomain', -- cosa_subdomain, custom_domain
    verification_status VARCHAR(50) NOT NULL DEFAULT 'verified',
    ssl_status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_domains_hostname ON public.domains(hostname);

-- 5.3 Public Form Submissions (Intake Gateway)
CREATE TABLE IF NOT EXISTS public.form_submissions (
    id BIGINT PRIMARY KEY DEFAULT public.generate_snowflake_id(),
    company_id BIGINT NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    project_id BIGINT REFERENCES public.projects_registry(id),
    form_slug VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    source_domain VARCHAR(255),
    ip_hash VARCHAR(64),
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sync_status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, synced_to_local, archived
    synced_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_form_submissions_company_sync ON public.form_submissions(company_id, sync_status);

-- 5.4 Deployments Registry
CREATE TABLE IF NOT EXISTS public.deployments (
    id BIGINT PRIMARY KEY DEFAULT public.generate_snowflake_id(),
    company_id BIGINT NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    app_id BIGINT NOT NULL REFERENCES public.company_web_apps(id) ON DELETE CASCADE,
    version VARCHAR(50) NOT NULL,
    target_type VARCHAR(50) NOT NULL DEFAULT 'cosa_shared_vps', -- cosa_shared_vps, company_vps, custom_server
    target_ref TEXT,
    hostname VARCHAR(255),
    build_status VARCHAR(50) NOT NULL DEFAULT 'pending',        -- pending, building, success, failed
    deployment_status VARCHAR(50) NOT NULL DEFAULT 'pending',   -- pending, live, superseded, rollback
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deployed_at TIMESTAMPTZ
);

-- ============================================================================
-- 6. SESSION & REFRESH TOKEN MANAGEMENT (Custom JWT Auth)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.user_sessions (
    id BIGINT PRIMARY KEY DEFAULT public.generate_snowflake_id(),
    user_id BIGINT NOT NULL REFERENCES public.platform_users(id) ON DELETE CASCADE,
    refresh_token_hash TEXT NOT NULL,                  -- bcrypt/sha256 hash của refresh token
    device_info JSONB DEFAULT '{}'::jsonb,             -- user-agent, ip_hash, platform
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_user_sessions_user ON public.user_sessions(user_id);
CREATE INDEX IF NOT EXISTS ix_user_sessions_token ON public.user_sessions(refresh_token_hash);

-- ============================================================================
-- 7. INDEXES & PERFORMANCE
-- ============================================================================

-- Tất cả indexes đã khai báo inline trong từng bảng

-- ============================================================================
-- 8. SEED DATA (DEFAULT PLANS & PROGRAMS)
-- ============================================================================

INSERT INTO public.plans (id, name, description, default_limits, default_features, is_public)
VALUES
    ('free', 'Free / Learning', 'Dành cho học viên, người mới bắt đầu và chương trình vườn ươm khởi nghiệp',
     '{"max_projects": 1, "max_seats": 2, "max_scheduled_agents": 1}'::jsonb,
     '{"marketing": true, "crm": true, "finance": false, "custom_domain": false}'::jsonb, true),
    ('starter', 'Starter', 'Dành cho các dự án khởi nghiệp đơn lẻ đang giai đoạn kiểm chứng thị trường',
     '{"max_projects": 3, "max_seats": 5, "max_scheduled_agents": 3}'::jsonb,
     '{"marketing": true, "crm": true, "finance": true, "custom_domain": true}'::jsonb, true),
    ('pro', 'Pro / Scale', 'Dành cho doanh nghiệp tăng trưởng cần tự động hóa toàn diện',
     '{"max_projects": 20, "max_seats": 20, "max_scheduled_agents": 10}'::jsonb,
     '{"marketing": true, "crm": true, "finance": true, "custom_domain": true, "priority_sync": true}'::jsonb, true),
    ('enterprise', 'Enterprise Private', 'Dành cho doanh nghiệp lớn với hạ tầng server riêng biệt',
     '{"max_projects": 999, "max_seats": 999, "max_scheduled_agents": 999}'::jsonb,
     '{"marketing": true, "crm": true, "finance": true, "custom_domain": true, "private_intake": true}'::jsonb, false)
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.programs (id, name, partner_name, description)
VALUES
    ('sihub_incubation', 'Chương trình Ươm tạo SIHUB Startup', 'SIHUB', 'Chương trình tăng tốc khởi nghiệp đổi mới sáng tạo hỗ trợ bởi SIHUB'),
    ('cosa_founder_fellowship', 'COSA Founder Fellowship 2026', 'COSA', 'Chương trình đồng hành xây dựng doanh nghiệp cùng trợ lý ảo AI')
ON CONFLICT (id) DO NOTHING;
