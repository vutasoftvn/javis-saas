# DB_FINAL_CUTOVER — Legacy Migration Manifest

Snapshot tại tag `pre-db-final-cutover` (commit `f0121a685ba220fa040c5e1774df5516bf2a18a4`).

Ghi chú: tag này được tạo sau khi Phase 0 (quick wins) + Phase 2 (workforce/workspace auth) của Epic `DB-FINAL-CUTOVER` đã merge vào `main` — xem `docs/superpowers/plans/2026-08-24-phase0-quickwins-phase2-workforce-auth.md`. Tag đánh dấu baseline ngay trước khi bắt đầu Phase 1 (canonical migration baseline).

## Migration đã di dời sang canonical

| Nội dung gốc | Vị trí gốc | Vị trí canonical mới | Ghi chú |
|---|---|---|---|
| Governance temporal model | `legacy/agent_runtime_archive/agentos/migrations/002_governance_temporal_model.sql` | `packages/agent_core/migrations/002_governance_temporal_model.sql` | Nội dung SQL giữ nguyên, chỉ sửa comment path |
| Agent memory + knowledge (pgvector) | `deploy/postgres/migrations/001_agent_memory_and_knowledge.sql` | `packages/agent_core/migrations/003_agent_memory_and_knowledge.sql` | Đánh số lại thành 003 vì 001 đã là run substrate, 002 là governance |

## Migration lịch sử KHÔNG di dời (giữ nguyên trong git history, không copy)

- `legacy/backend/alembic/versions/*.py` (85 file) — monolith cũ, tham chiếu qua git tag `pre-db-final-cutover`, không phải nguồn của bất kỳ canonical schema nào (Company/COSA/Agent Platform đều có baseline riêng).
- `legacy/backend/alembic_control_plane/versions/*.py` (4 file) — tương tự.

## Requirement notes cho behavior chưa port (điền dần khi Phase 4/5 xử lý)

(để trống, cập nhật khi có quyết định RETIRE/PROMOTE cụ thể cho từng nhóm legacy còn lại)
