# Plan A — Identity Foundation (COSA Control Plane ↔ Company projection)

Ngày: 2026-08-23
Phạm vi: Rework identity/tenant/auth boundary giữa COSA Control Plane (`services/cosa`) và Company (`services/company`), dựa trên phân tích `markdown/a1.md` đã verify lại từng claim bằng code thật. Đây là **Plan A** trong loạt 2 plan (Plan B — Company Business Schema Cleanup — được thiết kế sẵn ở cuối tài liệu, thực thi sau Plan A, viết plan riêng khi tới lượt).

## Context

`markdown/a1.md` là một bản review kiến trúc (không phải chính chủ dự án) đề xuất "schema reset" cho COSA, gộp 8 bước (identity → DB cleanup → cắt frontend `/workforce/*` → salvage agent legacy → gỡ dependency → xoá code legacy → squash migration + reset DB) vào một trình tự duy nhất (§19).

Tôi đã verify từng claim cụ thể trong a1.md bằng cách đọc trực tiếp code (không tin theo văn bản) trước khi dùng nó làm cơ sở plan. Toàn bộ ~14 claim gốc (schema, sync-from-platform bug, duplicate validation subsystem, ghost FK fields, legacy `/workforce/*` dependency, docker-compose mount, agent_core schema) **CONFIRMED đúng**. Một claim sai: `legacy/agent_runtime_archive` không phải "archive của archive" của `legacy/agent_runtime` — là 2 nhánh legacy độc lập (không đổi kết luận DELETE sau này, chỉ sai lý do).

**Phát hiện thêm, không có trong a1.md**: Flutter tab "Validation Studio" (`frontend/lib/modules/strategy/services/validation_service.dart`) gọi `/projects/:id/validation/*` — route này không khớp bất kỳ rule nào trong `ApiClient.normalizeEndpoint`/`resolveUri`, rơi vào nhánh mặc định, gọi thẳng Company (`localhost:4000`) với path không tồn tại ở cả `operations/strategy` lẫn `finance-legal/validation`. Route đó chỉ tồn tại ở `legacy/domains/founder_os/validation/router.py` (Python, không chạy trên port 4000). Kết luận: tab này hiện gọi vào endpoint chết (404 khi chạy thật) — không phải consumer của `finance-legal.validation`. Rewire tab này là việc frontend, nằm ở follow-up riêng.

Đã verify: frontend auth (`modules/auth/services/auth_service.dart`) chỉ gọi `/platform/auth/*`, không đụng `/identity/login`/`/identity/register` của Company → xác nhận local password auth ở Company an toàn để xoá.

## Quyết định phạm vi — đã chốt, không còn mở

Sau 2 vòng phản biện (đọc code xác nhận từng claim), phạm vi được chốt thành 2 plan độc lập, cộng các follow-up khác:

```text
Plan A — Identity Foundation          (tài liệu này, thực thi trước)
      ↓
Plan B — Company Business Schema Cleanup   (viết plan riêng sau, thiết kế đã chốt sẵn — xem cuối tài liệu)
      ↓
Follow-up riêng (không phụ thuộc thứ tự với nhau):
  - Cắt frontend khỏi /workforce/* + rewire Validation Studio
  - Salvage cosa_core/workforce → packages/agent_core
  - Xoá code legacy/* + Alembic chain (bảng quyết định domain-by-domain ở cuối)
  - Gỡ docker-compose mount legacy/backend khỏi realtime agent
      ↓
Plan riêng, cần confirm huỷ hoại rõ ràng lúc thực thi:
  - Squash migration + reset DB thật
```

Lý do tách Plan A / Plan B (đã thống nhất): **Plan A trả lời "ai đang hành động, thuộc tenant nào, quyền gì" — identity/tenant/auth thuần tuý. Plan B chuẩn hoá cách business record dùng identity/tenant đó** (dedupe `company_id`/`workspace_id`, actor naming, xoá duplicate validation, ghost FK). Plan B phụ thuộc Plan A; Plan A không phụ thuộc Plan B — thứ tự bắt buộc phải A trước.

## Plan A — Thay đổi cụ thể

### 1. Xoá local password auth khỏi Company
(`services/company/shared/db/schema/identity.ts`, `identity/services/auth.service.ts`, `identity/services/password.service.ts`, `identity/handlers/auth.handler.ts`)
- Xoá cột `password_hash` khỏi `core.users`.
- Xoá `loginUser`/`registerUserService`, xoá `POST /identity/sessions` + `POST /identity/register` (`auth.handler.ts:47-59`), xoá `password.service.ts`.
- An toàn đã verify: frontend auth chỉ gọi `/platform/auth/*`, không consumer nào gọi local login/register.

### 2. Đổi tên `core.users` → `core.user_projections`, xoá `users.role`
- File `identity.ts`: đổi tên bảng + export (`identityUsers` → `identityUserProjections`), xoá cột `role` (role chỉ còn ở membership).
- Cập nhật reference trong `identity/services/*.ts`, chỗ nào join user ở `operations/**/services/*.ts`.
- Migration: `ALTER TABLE core.users RENAME TO user_projections; ALTER TABLE core.user_projections DROP COLUMN role;`

### 3. Sửa bug role trong `syncFromPlatformService` (`identity/services/sync.service.ts:124-131`)
- Hiện tại: `role: isNewWorkspace ? "admin" : "member"` — sai, bỏ phí `member.roleId` đã có sẵn trong response.
- Sửa: dùng `member.roleId` cho `workspace_memberships.role`. Đổi check-then-insert thành upsert atomic (`ON CONFLICT (workspace_id, user_id) DO UPDATE SET role, updated_at`) — sync lần 2 trở đi phải cập nhật role thật, không đứng yên ở giá trị lần đầu.
- Thêm cột `platform_membership_id`, `source_updated_at` (từ `company_roles.updatedAt`/`company_memberships.updatedAt` phía COSA), `synced_at` vào `core.workspace_memberships`. Không thêm cột `status` giả — COSA's `company_roles` không soft-delete (revoke = xoá row), nên không có gì để đồng bộ vào đó; mở rộng khi COSA có soft-delete thật.
- Thêm `UNIQUE(workspace_id, user_id)` cho `core.workspace_memberships` — hiện chỉ có FK, 2 sync đồng thời có thể tạo duplicate membership.

### 4. Bỏ `organizations` 1:1 với workspace
- Xoá bảng `identityOrganizations`. `workforce_members.organization_id` → `workspace_id` trỏ thẳng `core.workspaces`.
- Cập nhật (đã grep, danh sách đóng): `identity/services/organization.service.ts`, `identity/services/tenant-context.service.ts`, `identity/tests/organization.test.ts`, `shared/tests/golden-path.e2e.test.ts`, `operations/tests/task.test.ts`, `scripts/seed-demo.mjs`.
- Migration: thêm `workspace_id` vào `workforce_members`, backfill từ `organizations.workspace_id`, drop `organization_id` + bảng `organizations`.

### 5. `workforce_members`: `agent_definition_id BIGINT` → `agent_spec_id TEXT` + `agent_spec_version TEXT`
- Xoá `agentDefinitionId`/`agentProfileId` (không FK, không consumer), thêm `agentSpecId text`, `agentSpecVersion text` khớp AgentSpec registry của `packages/agent_core`. Không tạo bảng `agent_definitions`.
- Thêm `manager_member_id BIGINT nullable` (self-FK) — org hierarchy tối thiểu, không tạo `workforce.org_units` (chỉ tạo khi org-chart thật cần).
- Thêm CHECK constraint: `member_type = 'HUMAN' → human_user_id NOT NULL, agent_spec_id NULL`; `member_type = 'AGENT' → human_user_id NULL, agent_spec_id NOT NULL` — chặn hybrid member vô nghĩa ở tầng DB.

### 6. Đổi tên `cosa.company_roles` → `cosa.company_memberships` (`services/cosa/storage/schema.ts:58-65`)
- Đây là bảng (company, user, role), tên cũ gây hiểu nhầm là role definition. Đổi export + bảng, cập nhật `services/cosa/handlers/company.handler.ts` và mọi chỗ dùng `companyRoles`.

### 7. Gateway auth không được chấp nhận platform token cho API thường (`identity/handlers/auth.handler.ts:26-43`)
- Đã verify `sync-from-platform` (`sync.handler.ts:11`) dùng `auth: false`, tự validate platform token riêng — không đi qua gateway này. Vậy `authHandler` không có lý do gì fallback sang `verifyPlatformToken`: bỏ hẳn nhánh đó, gateway chỉ chấp nhận local Company session token.
- Lý do: hiện cả 2 nhánh đều trả `{ userID: decoded.sub }`, nhưng `getMeProfile`/mọi service downstream giả định `userID` luôn là local snowflake ID (`BigInt(userIdStr)`). Nếu client gửi thẳng platform token vào endpoint dùng gateway này, `sub` là platform user ID (namespace khác) → ID confusion.

### 8. `TenantContext` bỏ 2 fallback ngầm về `workspaceId = "1"` (`identity/services/tenant-context.service.ts`)
- Nhánh platform-token: `ws ? ws.id.toString() : (params.workspaceId ? String(params.workspaceId) : "1")` → phải throw `notFound` nếu chưa có workspace projection và không truyền `workspaceId`, không gán `"1"`.
- Nhánh local-token, không truyền `workspaceId`, user chưa có membership nào: `targetWorkspaceId = BigInt(1)` → phải throw. (Nhánh local-token CÓ truyền `workspaceId` tường minh đã fix đúng từ trước — IDOR check đã có, giữ nguyên, không đụng.)

### 9. Local session TTL — **chốt: default 8h, configurable qua env**
```ts
const SESSION_TTL = process.env.COMPANY_LOCAL_SESSION_TTL?.trim() || "8h";
```
(`identity/services/token.service.ts:9`, hiện hard-code `"7d"` — cấm dùng lại 7d.)
- Lý do 8h: gần 1 working session — bắt buộc quyền được revalidate ít nhất mỗi phiên làm việc, không phải mỗi ngày (24h) hay quá thường xuyên gây login/sync lại liên tục (1h) trong khi chưa có refresh-token flow.
- Guardrail: production tối đa khuyến nghị 24h; 7d bị cấm.
- Company JWT chỉ chứa local identity; quyền thực tế resolve từ local membership DB mỗi request → role đổi có hiệu lực ngay khi sync mới chạy, không cần đổi token. TTL chỉ là upper bound cho session cũ chưa kịp sync lại. Không thêm refresh token trong Plan A — nếu cần Company chạy offline dài ngày, thiết kế riêng signed offline snapshot + grace policy sau, không kéo dài JWT để giả offline support.

### 10. Cập nhật `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`
- Đã verify doc hiện ghi `Status: Fully Promoted Canonical Architecture` và liệt `Hybrid Workforce Identity` tại `services/identity` (dòng 3, 41) — nhưng code thật nằm ở `services/company/identity/`, không phải service top-level riêng `services/identity`. Sau khi Plan A merge, update lại section storage ownership của doc này cho khớp `core`/`workforce` schema mới — tránh sau này AI/dev khác dựa vào doc cũ để resurrect sai boundary.

## Kiểm thử / Verify (Plan A)

1. `services/company`: chạy test suite hiện có sau mỗi cụm thay đổi — đặc biệt `identity/tests/organization.test.ts`, `shared/tests/golden-path.e2e.test.ts`, `operations/tests/task.test.ts`.
2. Golden-path e2e phải pass: COSA login → tạo company/membership → `sync-from-platform` → `user_projection` + `workspace` + `workspace_membership` đúng role → gọi API business.
3. Test sync role bug: gọi `syncFromPlatformService` 2 lần với role khác nhau ở lần 2 → xác nhận `workspace_memberships.role` được UPDATE.
4. `services/cosa`: chạy `services/cosa/tests/control-plane.test.ts` sau khi đổi tên `company_roles` → `company_memberships`.
5. Test gateway: gọi endpoint `auth: true` bằng raw platform token → phải reject.
6. Test `resolveTenantContext` không truyền `workspaceId`, user chưa có membership (cả 2 nhánh platform-token và local-token) → phải throw, không trả `"1"`.
7. Test concurrent sync: 2 lần `sync-from-platform` đồng thời cùng user/company → chỉ 1 membership row (nhờ unique constraint + upsert).
8. Chạy migration qua `node scripts/migrate.mjs` trên DB dev hiện có, xác nhận không lỗi FK do thứ tự drop/rename.
9. Grep xác nhận: `password_hash` = 0, `identityOrganizations`/`organization_id` = 0 (trừ migration file lịch sử), `agent_definition_id` = 0.

## Definition of Done — Plan A

```text
Company local password/login/register endpoint   = 0
gateway chấp nhận platform token cho API thường   = 0 (chỉ sync-from-platform, auth:false riêng)
TenantContext trả workspaceId ngầm định "1"       = 0
core.workspace_memberships duplicate(workspace,user) = impossible ở DB level
local session TTL                                  = env COMPANY_LOCAL_SESSION_TTL, default 8h, 7d bị cấm
organizations 1:1 wrapper                          = 0
workforce agent numeric definition                 = 0 (agent_spec_id + version)
COSA_CANONICAL_OWNERSHIP_MAP.md                    = khớp code thật (services/company/identity, core/workforce)
```

## Việc KHÔNG làm trong Plan A (chuyển sang Plan B hoặc follow-up khác — đã chốt, không mở lại)
- Không đụng `finance-legal.validation`, `brain_id`/`mvp_stage_id`/`offering_id`, actor/owner field naming (`assignee_id`/`owner_id`/...), dedupe `company_id`/`workspace_id` trên strategy tables — tất cả sang **Plan B**.
- Không đổi API contract phía Flutter (`/workforce/*`, `/projects/:id/validation/*`).
- Không xoá code `legacy/*`, không gỡ docker-compose mount.
- Không reset database thật — chỉ forward migration trên DB dev hiện có.

---

# Plan B — Company Business Schema Cleanup (thiết kế đã chốt, viết plan thực thi riêng sau khi Plan A xong)

Không thực thi trong lần approve Plan A. Ghi lại đây để thiết kế không bị hỏi lại lần sau.

**Nguyên tắc chốt: canonical tenant key trong Company DB = `workspace_id` duy nhất.** `core.workspaces.platform_company_id` là mapping sang COSA; business row không lưu song song `company_id` + `workspace_id`. API vẫn có thể nhận `companyId` từ client, nhưng service phải resolve sang `workspace_id` qua `core.workspaces` trước khi query/insert.

**Nguyên tắc chốt: canonical actor = `workforce.members.id`.** `owner_id`/`assignee_id`/`owner_workforce_member_id` → `owner_member_id`/`assignee_member_id`/`actor_member_id`. Không dùng `user_id` cho business actor vì actor có thể là human hoặc agent.

Nội dung Plan B:
1. Xoá `finance-legal.validation` (`validation_hypotheses`, `validation_experiments`, `evidence_items`, `customer_interviews` + `finance-legal/handlers/validation.handler.ts`) — không có consumer thật (Validation Studio Flutter gọi route legacy chết, không gọi subsystem này). `operations/strategy` là canonical chain (assumption→experiment→evidence→gate→decision).
2. Xoá ghost fields `brain_id`, `mvp_stage_id` khỏi `initiatives`/`okrCycles`/`twelveWeekCycles`/`portfolios`/`projects` (không có bảng owner nào). Xoá `offering_id` khỏi `initiatives` (không có `commercial.offerings`).
3. Dedupe `company_id`/`workspace_id` trên 11 bảng `strategy.ts` — đụng ~9 handler file `operations/strategy/handlers/*`, cần resolve helper `companyId → workspaceId` trước khi chuyển từng handler.
4. Chuẩn hoá actor naming trên `tasks`, `projects`, `experiments`, `decision_records` theo quy tắc trên.
5. Xoá domain Policies/Regulations (~20 bảng legacy, không port, không ai dùng): **bắt buộc capture 1 file ghi chú requirement** (mục đích, entity chính, business rule quan trọng) vào `docs/architecture/` trước khi xoá code+migration — không xoá âm thầm.

---

# Roadmap đầy đủ sau Plan A + Plan B (đã chốt domain-by-domain, không còn "chờ phân tích thêm")

Đã inventory ~307 bảng legacy theo domain, verify runtime dependency = 0 (không service nào hiện tại import legacy DB/ORM):

| Domain (≈ số bảng) | Quyết định |
|---|---|
| Auth/Identity, Tasks/Operations, Strategy/OKR, Skills/Tools (~14-25/nhóm) | **DELETE thẳng** — đã port đầy đủ |
| Finance/Accounting (~16) + Legal (~7) | **DELETE** — đã port một phần thật (8 bảng accounting + 2 bảng legal trong `finance-legal.ts`, xác nhận lại vì có báo cáo sai "không có gì thay thế"); phần chưa port không có consumer |
| Vault/Knowledge (~11), Memory (~11) | **DELETE** — chưa port nhưng có chủ đích (a1.md §16-17 defer), khớp premise dev-reset-safe |
| Policies/Regulations (~20) | **DELETE sau khi capture requirement note** (xem Plan B mục 5) |
| Agent hierarchy/budget/cost-ledger | **Salvage trước** (→ `packages/agent_core`), **DELETE sau** |
| 7 bảng approval trùng lặp trong chính legacy | **DELETE toàn bộ** — `packages/agent_core.approvals` đã là bản thay thế đúng |

Thứ tự thực thi follow-up (mỗi bước viết plan riêng khi tới lượt):
1. Cắt frontend khỏi `/workforce/*` (map theo bảng a1.md §7) + rewire "Validation Studio" khỏi route chết `/projects/:id/validation/*` sang `operations/strategy`.
2. Salvage `legacy/agent_runtime/cosa_core` + `workforce` (tool-loop, budget tracking, stuck-loop detection, approval-aware dispatch, extension manifest governance metadata) → `packages/agent_core`, có regression test.
3. Gỡ `./legacy/backend:/app/backend` khỏi docker-compose (`realtime-agent`, `realtime-agent-cloud`), `PYTHONPATH` fallback, `backend/.env` load trong `services/realtime_agent/main.py` — đã verify an toàn (realtime agent chỉ gọi qua `ServicesClient` HTTP).
4. Xoá code + Alembic chain theo bảng quyết định ở trên; `legacy/backend` xoá sau bước 3; `cosa_core`/`workforce` xoá sau bước 2 + regression pass.
5. **Riêng, cần confirm huỷ hoại rõ ràng lúc thực thi**: squash migration thành baseline sạch, sau đó mới DROP/tạo lại DB, seed lại chỉ COSA roles/plan/dev admin — Company users sinh qua `sync-from-platform`, không seed password/local auth.
