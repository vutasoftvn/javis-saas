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

## Loại bỏ khỏi phạm vi (quyết định 2026-08-22, user xác nhận)

Hai mục sau **không còn được theo đuổi** trong roadmap `agentos/` — không phải "vẫn bị chặn, để sau", mà là quyết định dừng đầu tư:

- **Sandbox execution** (`opensandbox`) — image `opensandbox/server:0.2.2` không tồn tại trên Docker Hub, chưa từng chạy được thật kể cả ở `legacy/backend` (ADR-012 "Follow-up" note). Nếu sau này cần thực thi code trong sandbox, đây sẽ là 1 quyết định mới, không phải tiếp tục từ điểm dừng này.
- **Extensions/Plugin API** — chưa có owner trong `services/` hay `agentos/`; `frontend/lib/modules/settings/views/settings_extensions_page.dart` tiếp tục trỏ `legacy/backend:8000` vô thời hạn (không chỉ "cố tình chưa đổi" như ADR-012 Decision §4 ghi trước đây — nay là quyết định dừng hẳn).

Không xóa code liên quan đã tồn tại trong `legacy/backend` (đó là quyết định retire riêng, ngoài phạm vi này) — chỉ đánh dấu 2 mục này không còn nằm trong roadmap hoàn thiện `agentos/`.

Chi tiết đầy đủ: `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`, `docs/architecture/adr/ADR-012-legacy-backend-agentos-services-integration-plan.md`.
