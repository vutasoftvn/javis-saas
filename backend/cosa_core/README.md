# cosa_core

Nền tảng Agent Harness tái sử dụng của COSA — runtime, governance, identity,
tools, reliability, profiles, capabilities. Tách khỏi javis-saas app để dùng
lại cho các hệ thống AI Agent khác.

## Dependency chính thức (không phải optional)
- `deepseek-harness-sdk` — runtime mặc định (xem `cosa_core/runtime/adapters/deepseek_harness.py`)
- `google-adk` — orchestrator mặc định (thêm ở Đợt 2, xem `docs/architecture/COSA_ADK_ORCHESTRATOR_UUID7_PROPOSAL.md`)

## Quy tắc dependency
`cosa_core` không import từ `app/workforce/platform_core/business_core/founder_os/integrations`.
Ngoại lệ duy nhất: `db.base_class.Base`, `db.snowflake_model.SnowflakeIDMixin` (ORM
plumbing dùng chung Alembic metadata với app).

Kiểm tra: `bash backend/cosa_core/check_boundary.sh`

## Trạng thái di chuyển
Xem `docs/architecture/2026-08-22-cosa-core-extraction-plan.md`.
