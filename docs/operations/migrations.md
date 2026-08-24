# Vận hành: Database Migrations

## Hai hệ migration độc lập, không dùng chung tool

1. **`packages/agent_core/migrations/*.sql`** — Python side, schema `agent_core`/`agent_registry`/`agent_memory`/`knowledge`/`agent_evals`. Migration mới nhất trong phiên này: `004_harden_exact_invocation_and_approval.sql` → `010_knowledge_versioning_and_embeddings.sql` (7 file mới).
2. **`services/cosa/migrations/*.up.sql`** — Encore/TypeScript side, schema `control_plane` (Wave 7) + service cũ. Migration mới nhất: `6_control_plane_missions_tasks.up.sql` → `9_control_plane_delivery.up.sql` (4 file mới, tiếp nối `5_rename_company_roles.up.sql`).

## Quy tắc đánh số

- `agent_core`: số 3-chữ-số tăng dần (`001`, `002`...), tên mô tả nội dung.
- `services/cosa`: số nguyên tăng dần + `.up.sql` (Encore convention), chạy qua `node scripts/migrate.mjs` hoặc `make services-migrate-cosa` (theo CLAUDE.md).

**Trước khi thêm migration mới: xác nhận lại số thứ tự cuối cùng bằng `ls`/`git log`, không hard-code — backlog khác có thể đã thêm migration trước khi bạn bắt đầu.**

## CHƯA chạy thật trong phiên Wave 0-11

Không có Postgres/pg_ctl/initdb trong môi trường phát triển — toàn bộ 11 file migration mới (7 Python + 4 TypeScript) chỉ được REVIEW bằng mắt (cú pháp SQL, foreign key, unique constraint), CHƯA từng `psql`/`encore db migrate` thật. Đây là rủi ro thật cần xử lý trước khi coi Wave 1-7 "production ready":

- Migration 004 đổi PK bảng `agent_core.run_tool_calls` từ single-column sang composite `(run_id, tool_call_id)` — nếu bảng đã có data thật trong production, cần kiểm tra không có duplicate trước khi apply (chưa viết migration guard cho trường hợp này).
- Migration 008/009 (memory v2, knowledge versioning) là additive + backfill từ bảng cũ — thứ tự chạy quan trọng, chưa test rollback path.

## Trước khi chạy trên Postgres thật

1. Backup trước mọi migration đổi PK/constraint hiện có (004).
2. Chạy trên staging trước, không chạy thẳng production.
3. Xác nhận rollback script (`.down.sql` cho services/cosa) tồn tại và test được — chưa verify trong phiên này.
