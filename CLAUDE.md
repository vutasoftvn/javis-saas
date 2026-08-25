# CLAUDE.md

COSA là **Founder / Company Operating System với Agent Platform composable**. Không coi COSA là tập hợp các AI agent độc lập.

## Nguồn sự thật kiến trúc

Đọc theo thứ tự khi cần chi tiết — không chép lại nội dung các file này vào đây:

0. `COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md` — nguồn sự thật **cao nhất** cho phạm vi: DB baseline, identity/tenant auth, durable run/dispatch/lease, durable event log/SSE, policy wiring, legacy exit, deployment convergence, CI/E2E gate. Mục 29 "Reconciliation Addendum" (thêm 2026-08-25) đã đối chiếu tài liệu này với code thật và khoá các quyết định còn bỏ ngỏ (5 quyết định DB baseline P0.1, Decision RUNTIME-001) — đọc mục 29 trước khi đọc phần thân tài liệu để biết chỗ nào đã điều chỉnh. Tài liệu này supersede `DB_FINAL_CUTOVER.md` (nay `SUPERSEDED`, giữ lại làm evidence lịch sử).
1. `COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md` — kế hoạch triển khai đã đối chiếu (đã duyệt 2026-08-24), điều chỉnh Blueprint V2 theo code thật. Vẫn là nguồn sự thật cho phần chưa bị Mục 0 đè lên (Wave 3/5-6/8-9/11: prompt/spec registry, skills/evals, memory/knowledge v2, protocols, recipes). Đọc Wave tương ứng trước khi thêm code lớn vào `packages/agent_core/`, `apps/cosa/`, hoặc `services/cosa/`.
2. `COSA_CANONICAL_MASTER_ARCHITECTURE_AND_IMPLEMENTATION_GUIDE_2026-08-23.md` — kiến trúc target đã audit (Master M1).
3. `COSA_AGENT_PLATFORM_PROMOTION_IMPLEMENTATION_PLAN_2026-08-23.md` — plan triển khai theo phase, có Definition of Done cụ thể.

Khi các file trên xung đột với comment cũ trong code hoặc trí nhớ của bạn: **file có số thứ tự nhỏ hơn thắng** (Mục 0 thắng tất cả trong phạm vi của nó). File #0/#1 có thể sửa đổi quyết định trong #2/#3 (vd. runtime strategy, vị trí control-plane) — khi có mâu thuẫn, ưu tiên số nhỏ hơn nhưng kiểm tra ADR liên quan trong `docs/architecture/adr/` trước khi hành động.

**Runtime:** OpenAI Agents SDK là primary execution runtime, DeepSeek là primary model provider (qua LiteLLM), LangChain là optional adapter — theo `ADR-RUNTIME-002` (2026-08-25, supersede `ADR-RUNTIME-001` LangChain-primary — quyết định đó chưa từng implement và bị đảo ngược sau khi phát hiện mâu thuẫn giữa header ACCEPTED và code default thật).

**Control Plane:** vị trí tại `services/cosa` (Encore/TS) đã được chấp nhận qua `ADR-CONTROLPLANE-001` (2026-08-24) — vẫn đúng, không đổi. Header ADR này tự ghi "triển khai chưa bắt đầu"; schema + service code TypeScript đã tồn tại nhưng **zero production consumer** tính đến 2026-08-25 (xem Mục 0, §29.2).

Trạng thái ACCEPTED chỉ xác nhận quyết định kiến trúc; không mặc định có
nghĩa implementation, migration cutover, runtime wiring hoặc production
verification đã hoàn tất. Luôn kiểm tra trạng thái triển khai thực tế
(ACCEPTED / IMPLEMENTED / WIRED / VERIFIED / PRODUCTION là 5 trục khác nhau)
trước khi sửa code hoặc báo cáo tiến độ — repo này đã có ít nhất 2 trường hợp
một phiên tự báo "Wave/Phase hoàn thành" bị phiên audit sau đó phát hiện
chưa thật sự wire/verify (xem Mục 0, §29.1-29.2).

## Bốn vùng kiến trúc

```text
Experience Plane      Flutter (text chat, voice, API)
COSA Control Plane    services/cosa      (Encore/TS — global identity, license, plan)
Company Business      services/company   (Encore/TS — identity, operations/strategy, commercial, finance-legal)
Agent Platform        packages/agent_core (Python, reusable) + apps/cosa (Python, composition)
```

- `packages/agent_core/` **không được import** bất cứ gì từ `services/company/*`. Chỉ `apps/cosa/` được compose cả hai phía.
- `legacy/` đã xoá hẳn 2026-08-25 (bao gồm `agentos/` archive cũ, `legacy/backend`, `legacy/agent_runtime`, và các thư mục split-out khác) — xem `docs/architecture/LEGACY_BACKEND_CAPABILITY_AUDIT_2026-08-25.md`. Mọi tính năng runtime hiện hoạt đều nằm tại `packages/agent_core/` và `apps/cosa/`.


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
