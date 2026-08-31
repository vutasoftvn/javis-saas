# CLAUDE.md

COSA là **Founder / Company Operating System với Agent Platform composable**. Không coi COSA là tập hợp các AI agent độc lập.

## Quy tắc Git & Workspace (BẮT BUỘC)

- **Tuyệt đối KHÔNG tạo git worktree:** Không bao giờ chạy `git worktree add` hoặc tạo / chuyển ngữ cảnh làm việc sang worktree tách biệt.
- **Code trực tiếp trong `main`:** Mọi thao tác đọc, sửa code, chạy lệnh, refactor và commit phải được thực hiện trực tiếp trên nhánh `main` tại thư mục gốc của repository này.

## Nguồn sự thật kiến trúc

**Quyết định 2026-08-31 — Option 1 "keep deleted":** 5 tài liệu source-of-truth cũ
(`COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md`,
`COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md`,
`COSA_CANONICAL_MASTER_ARCHITECTURE_AND_IMPLEMENTATION_GUIDE_2026-08-23.md`,
`COSA_AGENT_PLATFORM_PROMOTION_IMPLEMENTATION_PLAN_2026-08-23.md`,
`DB_FINAL_CUTOVER.md`) cùng nhiều ADR cũ đã bị xóa trong commit `34507dd9`
(2026-08-27). Giữ nguyên trạng thái đã xóa, không khôi phục. Các file tên tương
tự trong `docs/archive/` chỉ là lưu trữ lịch sử, KHÔNG phải nguồn sự thật.

**Document index hiện tại** (chỉ đọc các file TỒN TẠI trong cây):

- `docs/architecture/adr/` — ADR đang hoạt động: `ADR-AGENT-REG-001`,
  `ADR-AI-COMPLIANCE-RUNTIME-001`, `ADR-CONV-001`, `ADR-CUTOVER-001`,
  `ADR-DEPLOY-001`, `ADR-ID-MODEL-001`, `ADR-LOCAL-EVENT-BACKBONE-001`,
  `ADR-LOCAL-FIRST-001`, `ADR-SLUG-001`. Trước khi hành động, kiểm tra ADR
  liên quan tại đây.
- `docs/superpowers/specs/` — design đã duyệt (vd.
  `2026-08-31-maintainable-modular-truthful-mvp-design.md`).
- `docs/superpowers/plans/` — plan triển khai đã duyệt.
- `docs/architecture/generated/` — snapshot sinh tự động (contracts, route
  inventory, company usage inventory) — generator-owned, không hand-edit.

**Runtime:** OpenAI Agents SDK là primary execution runtime, DeepSeek là primary
model provider (qua LiteLLM), LangChain là optional adapter.

**Control Plane:** vị trí tại `services/cosa` (Encore/TS). Schema + service code
TypeScript đã tồn tại nhưng **zero production consumer** tính đến 2026-08-25.

Trạng thái ACCEPTED chỉ xác nhận quyết định kiến trúc; không mặc định có
nghĩa implementation, migration cutover, runtime wiring hoặc production
verification đã hoàn tất. Luôn kiểm tra trạng thái triển khai thực tế
(ACCEPTED / IMPLEMENTED / WIRED / VERIFIED / PRODUCTION là 5 trục khác nhau)
trước khi sửa code hoặc báo cáo tiến độ.

## Bốn vùng kiến trúc

```text
Experience Plane      Flutter (text chat, voice, API)
COSA Control Plane    services/cosa      (Encore/TS — global identity, license, plan)
Company Business      services/company   (Encore/TS — identity, operations/strategy, commercial, finance-legal)
Agent Platform        packages/agent (Python, reusable) + apps/cosa (Python, composition)
```

- `packages/agent/` **không được import** bất cứ gì từ `services/company/*`. Chỉ `apps/cosa/` được compose cả hai phía.
- `legacy/` đã xoá hẳn 2026-08-25 (bao gồm `agentos/` archive cũ, `legacy/backend`, `legacy/agent_runtime`, và các thư mục split-out khác). Mọi tính năng runtime hiện hoạt đều nằm tại `packages/agent/` và `apps/cosa/`.


## Quy tắc bắt buộc

1. **Business truth thuộc `services/*` (TypeScript/Encore), không thuộc LLM runtime.** Agent Platform không tự quyết định authorization hay ghi business DB trực tiếp — mọi side effect qua Capability Layer + Governance + Audit.
2. **Một danh tính workforce duy nhất: `WorkforceMember`.** Không tạo bảng nhân sự riêng cho AI vs người.
3. **Không tạo Agent mới khi chưa cần.** Trước tiên hỏi: đây là Skill / Tool / Workflow / Knowledge / Executor / Integration? Chỉ tạo Agent Profile khi có vai trò nghiệp vụ thật mới.
4. **Không nhân bản kiến trúc.** Trước khi thêm prompt/skill/tool/workflow/agent/service mới, tìm trong repo xem đã có chưa — ưu tiên compose/reuse.
5. **Governance là code xác định, không phải LLM tự quyết.** Approval phải bind đúng `run_id + tool_call_id + checkpoint_ref`, không lookup theo tên action. Constraint lịch sử (đã REQUIRE_APPROVAL) không tự mất khi policy sau nới lỏng.
6. **Test durability phải qua process thật.** Một test "resume sau restart" chỉ tạo instance thứ hai trong cùng process không được coi là chứng minh — đây là gap đã phát hiện trong audit, đừng lặp lại.
7. **Trạng thái ứng dụng phải structured, không suy diễn từ văn bản tự nhiên.** Không dùng kiểu `if "blocked" in model_text`.
8. **Hành động rủi ro cao (deploy, xóa dữ liệu, gửi tin nhắn ra ngoài, đổi quyền, hành động tài chính) cần approval qua code, không qua prompt.**
9. **Trước khi coi một API/service là "không ai dùng":** kiểm tra cả phía client (frontend có gọi không) lẫn phía deploy (có server nào start không) — đừng chỉ nhìn một phía. Absence of reported traffic không đồng nghĩa absence of attempted traffic.
10. **An toàn khi sửa code:** chạy `git status` trước thao tác có thể mất dữ liệu; không dùng `--force`/`--no-verify` trừ khi được yêu cầu rõ; không tự ý xóa/archive file — xác nhận với người dùng trước hành động phá hủy.
11. **Không tuyên bố "xong" khi chưa test.** Mỗi thay đổi hành vi cần test tương ứng; chạy test trước khi báo cáo hoàn thành.
12. **Không bao giờ tạo git worktree — Code trực tiếp trong `main`:** Tuyệt đối KHÔNG tạo worktrees (`git worktree add`, v.v.). Luôn luôn chỉnh sửa code, chạy lệnh và commit trực tiếp trên nhánh `main` tại root workspace.

## Encore.ts (services/company, services/cosa)

Mỗi service theo layout: `encore.service.ts`, `api.ts` (barrel export), `db.ts`, `handlers/` (parse input → gọi service → trả response, không query DB trực tiếp), `services/` (business logic, Drizzle ORM, transaction), `models/` (re-export DB), `migrations/`, `tests/`.

- Lỗi trả về qua `APIError` (`invalidArgument`, `unauthenticated`, `permissionDenied`, `notFound`, `alreadyExists`, `internal`) — không throw `Error` trần.
- Endpoint nội bộ giữa service: `expose: false`. Chỉ endpoint cho client ngoài mới `expose: true`.
- Schema Drizzle tập trung ở `<app>/shared/db/schema/<service>.ts` (không rải trong `models/` của từng service) — tránh circular import khi service cần join bảng chéo.
- Đổi schema DB phải có migration; sau khi thêm migration mới chạy `node scripts/migrate.mjs` (hoặc `make services-migrate-company` / `make services-migrate-cosa`).

## Comment code

Viết bằng tiếng Việt cho phần giải thích ý nghĩa/lý do (why). Tên định danh, thông báo lỗi hệ thống/log, và trích dẫn nguyên văn tài liệu tiếng Anh vẫn giữ tiếng Anh. Không bắt buộc viết lại comment cũ ngay — áp dụng cho comment mới, chuyển dần khi sửa file.

## Trước khi làm việc lớn

1. Đọc code hiện có, tìm component/pattern có thể tái dùng trước khi viết mới.
2. Xác định đúng layer kiến trúc (4 vùng ở trên).
3. Làm thay đổi nhỏ nhất an toàn, giữ hành vi đang chạy đúng.
4. Với việc nhiều bước: viết plan trước khi sửa code (không có plan → không thực thi).
5. Chạy test/verify sau mỗi thay đổi có ý nghĩa.
