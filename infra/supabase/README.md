# COSA Supabase Central Control Plane

Hạ tầng Supabase Self-Hosted / Hosted phục vụ **COSA Central Control Plane & Project Intelligence**.

## 1. Cấu trúc thư mục

```text
infra/supabase/
├── migrations/
│   └── 001_initial_central_control_plane.sql  # Schema Phase 1 (Identity, Commercial, Projects, Programs, Marketing)
└── README.md
```

## 2. Cách triển khai Migration lên Supabase Central

### Cách 1: Sử dụng Supabase CLI
```bash
# Đăng nhập và liên kết dự án
supabase login
supabase link --project-ref <your-project-ref>

# Chạy migration
supabase db push
```

### Cách 2: Chạy trực tiếp qua SQL Editor trên Supabase Dashboard hoặc psql
```bash
psql -h <SUPABASE_DB_HOST> -p 5432 -d postgres -U postgres -f infra/supabase/migrations/001_initial_central_control_plane.sql
```

## 3. Các Domain dữ liệu được quản lý
1. **Platform Identity**: `platform_users`, `companies`, `company_memberships`.
2. **Commercial & Licensing**: `plans`, `licenses`, `company_entitlements`.
3. **Project Intelligence**: `projects_registry`, `project_stage_history`, `project_outcomes`, `project_metrics`.
4. **Programs / Cohorts**: `programs`, `cohorts`, `program_participants`, `project_program_links` (phục vụ SIHUB).
5. **Marketing Public Edge**: `company_web_apps`, `domains`, `deployments`, `form_submissions`.
