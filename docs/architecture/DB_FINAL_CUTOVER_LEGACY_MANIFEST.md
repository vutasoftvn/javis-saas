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

## Bug fresh-bootstrap tiền tồn tại — phát hiện khi chạy Gate A (2026-08-24, Phase 1 Task 6)

Không liên quan tới thay đổi của Phase 1 — migration content các file dưới đây không bị sửa. Cần một đợt "canonical baseline reset" riêng theo DB_FINAL_CUTOVER.md §5.3 trước khi company/cosa có thể coi là fresh-bootstrap được (Gate A).

- **Agent Platform (`packages/agent_core`): PASS.** Fresh-bootstrap + rerun no-op đều xanh.
- **`services/company` FAIL:** `identity/4_snowflake_ids.up.sql` tham chiếu bảng `core.users` — bảng này đã được đổi tên thành `core.user_projections` ở một migration sau đó (migration 5, `identity_projection_rework`), nên trên DB rỗng chạy tuần tự 1→4 sẽ lỗi "relation core.users does not exist".
- **`services/cosa` FAIL:** `cosa/5_rename_company_roles.up.sql` giả định tồn tại bảng `cosa.company_roles` từ một schema cũ hơn, nhưng `cosa/1_create_control_plane.up.sql` hiện tại đã tạo thẳng `cosa.company_memberships` — trên DB rỗng chạy tuần tự 1→5 sẽ lỗi "relation cosa.company_roles does not exist".

Việc sửa đòi hỏi quyết định kiến trúc (viết lại chain migration làm baseline mới, hay chấp nhận `--baseline` mode chỉ dùng được trên DB đã có schema đúng từ trước) — ngoài phạm vi Phase 1 Task 1-5, cần một plan riêng.
