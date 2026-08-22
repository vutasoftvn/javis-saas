# 10 — Deployment & Infrastructure Spec

**Blueprint gốc:** §65, §72–§74, §83–§84, §87 của `markdown/AI_Agent_OS_Master_Architecture.md`.
**Áp dụng cho:** toàn repo — đây là spec duy nhất không tách riêng theo `agentos/` vs `legacy/`, vì nó mô tả hạ tầng chạy chung.

## Trạng thái hiện tại

- `legacy/backend` (`brain-api`/`agent-worker`) **frozen-in-place** theo ADR-012 — không nhận thêm phát triển, chỉ giữ chạy để `agentos/` gọi qua adapter (LLM Gateway đã tự chủ theo ADR-012 "Follow-up", OAuth/n8n/Sandbox vẫn phụ thuộc `legacy/backend`).
- `docker-compose.yml`: `migrate`/`migrate-control-plane`/`brain-api`/`agent-worker` gated sau `--profile legacy`, không tự chạy mặc định.
- `services/` (Encore) chạy qua `encore run` (dev) — xem `services/docker-compose.yml` cho production.
- Trace bền vững: SQLite (`var/agentos/traces.sqlite3`, `var/agentos/audit_log.sqlite3`) — đúng CLAUDE.md §10 "SQLite → sessions, traces, cache".

## Còn thiếu

- Chưa có 1 integration test end-to-end nào chứng minh `frontend/` → `services/` → response hoạt động (chỉ có agent-side pilot, xem spec 05).
- Extensions/Plugin API — chưa có owner trong `services/` hay `agentos/`, `frontend/lib/modules/settings/views/settings_extensions_page.dart` vẫn trỏ `legacy/backend:8000` (ADR-012 Decision §4, cố tình chưa đổi).
- Sandbox execution (`opensandbox`) — image không tồn tại trên Docker Hub, chưa từng chạy được thật (ADR-012 "Follow-up" note).

Chi tiết đầy đủ: `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`, `docs/architecture/adr/ADR-012-legacy-backend-agentos-services-integration-plan.md`.
