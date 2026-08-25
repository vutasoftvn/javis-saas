# Legacy Archive (Thế hệ Kiến trúc 1 & 2)

Thư mục này lưu trữ các module và logic cũ của COSA/Javis SaaS trước khi chuyển đổi sang kiến trúc canonical hiện tại (`packages/agent_core/` + `apps/cosa/` + `services/cosa`/`services/company`).

## Đã xoá ngày 2026-08-25 (zero-import, xác nhận qua grep `apps/`, `packages/`, `services/`)

- **`business/`** (`business/`, `business_core/`) — đã chuyển đổi sang `services/*` (4 cluster Encore TS).
- **`domains/`** (`founder_os/`, `regulations/`) — đã sáp nhập vào `services/operations` và `services/finance-legal`.
- **`platform/`** (`platform_core/`, `core/`) — đã chuyển đổi sang `services/cosa` (identity) và `packages/agent_core`.
- **`entrypoints/`** (`worker_main.py`, `central_main.py`, `full_main.py`) — không còn container/script nào gọi tới.
- **`agent_runtime_archive/`** (`agentos/`, `tests_agentos/`) — bản lưu trữ pre-canonical của `agentos/`, đã được thay thế hoàn toàn bởi `packages/agent_core/` + `apps/cosa/`.

Lịch sử code của các thư mục trên vẫn còn trong `git log`/tag `pre-cutover` nếu cần tra cứu lại.

## Vẫn còn giữ (chưa đủ điều kiện xoá)

- **`backend/`**: Nguồn build ra service `brain-api` (`docker-compose.yml`, `profiles: [legacy]`). **Đang HỎNG ở runtime** (`ModuleNotFoundError: No module named 'full_main'`, từ đợt tái cấu trúc 2026-08-22) — xem `docs/architecture/legacy_backend_capability_audit_2026-08-25.md` để biết năng lực nào brain-api còn giữ độc quyền (LLM gateway/OAuth/n8n/sandbox) trước khi quyết định sửa hay xoá hẳn.
- **`agent_runtime/`**: `cosa_core/`, `workforce/`, `agent_runtime/` — vẫn được `docker-compose.yml` mount vào `brain-api`/`agent-worker` (profile `legacy`), giữ song song cho tới khi audit ở trên xác nhận an toàn xoá.
