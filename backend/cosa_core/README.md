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

## Đã move (Batch 1 - Tasks 2-12)

Các nhóm sau đã được di chuyển vào `cosa_core/`:
1. `config` - configuration management
2. `constants` - project constants
3. `db` - database models (base classes, migrations support)
4. `feature_flags` - feature flag models and utilities
5. `governance` - kernel, governance decisions, budget tracking
6. `runtime` - agent runtime adapters (DeepSeek Harness)
7. `types` - core data types (AgentRun, ToolSpec, etc.)
8. `tools` - tool dispatch and registry
9. `capabilities` - initial capability infrastructure
10. `snowflake` - Snowflake ID generation utilities
11. `exceptions` - core exception types
12. `logger` - logging configuration

## Chưa move (Batch 2 - Future)

Những thành phần sau vẫn còn trong `backend/` do entanglement với `business_core/founder_os/integrations`:
- `auth/` - identity, sessions, router
- `control_plane/` - workspace, teams, schema management
- `delegation/` - mission delegation, worker coordination
- `orchestration/` - workflow orchestration
- `workflows/` - workflow definitions
- `extensions/` - external integration infrastructure
- `vault/` - secret management
- `scope_resolver.py` - scope resolution logic
- `mcp_adapter.py` - MCP protocol adapter
- `credential_broker.py` - credential management
- `platform_core/organization/service.py` — `get_ceo_command_center`, `get_daily_briefing` functions
- `capabilities/{service.py, quick_action_service.py, router.py}` - capability service and routing

Lý do: Những thành phần này có phụ thuộc vòng tròn sâu (circular dependencies) với `business_core` (organization, portfolio, revenue) và `founder_os` (command center, briefing logic) cần cấu trúc lại trước khi tách riêng.

## Trạng thái di chuyển
Xem `docs/architecture/2026-08-22-cosa-core-extraction-plan.md` để chi tiết từng task.
