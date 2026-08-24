# Recipe: Dependency Release Radar

Pattern `watch-rank-deliver` (Blueprint V2 §70) — ví dụ điển hình cho nguyên tắc deterministic-first (§72): parser/version-diff là code thường, LLM chỉ dùng ở bước đánh giá độ liên quan/rủi ro.

## Trạng thái phụ thuộc (2026-08-24)

Dùng trực tiếp control-plane primitives xây ở **Wave 7** (`services/cosa` — `control_plane.watches`, `control_plane.signal_observations` với dedupe theo `dedupe_key`, `control_plane.delivery_policies`/`delivery_attempts`). **Lưu ý quan trọng:** Wave 7 tự nó CHƯA có consumer production nào và CHƯA verify được bằng Postgres/Encore CLI thật (xem `COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md` Phần H) — recipe này do đó cũng ở trạng thái **thiết kế, chưa chạy thử end-to-end**, không phải recipe production-ready.

Parser dependency manifest (`requirements.txt`/`package.json`) và GitHub release API collector **chưa được viết** — đây là phần "deterministic acquisition" cụ thể cần code riêng khi triển khai recipe này thật, không phải hạ tầng chung của Agent Platform.
