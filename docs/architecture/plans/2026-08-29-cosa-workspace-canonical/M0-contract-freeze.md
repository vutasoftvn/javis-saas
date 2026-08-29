# M0 — Contract freeze trước khi sửa schema

**Audit:** §9.0 · **Phụ thuộc:** không · **Là gate cứng chặn M1–M7 (C-4)**
**Master:** [../2026-08-29-cosa-workspace-canonical-master-plan.md](../2026-08-29-cosa-workspace-canonical-master-plan.md)

## Context

Repo hiện có nhiều "nguồn sự thật" cạnh tranh cho cùng khái niệm: workspace lifecycle sống ở
cột `company_stage` + alias `ventureStage`; project stage có bộ enum khác nhau giữa backend
(S0–S5) và frontend (`ProjectStage` S0_EXPLORE…S6_SCALE_GOVERN); frontend gọi các route
không tồn tại (`/operations/strategy/stage-context`, `/workforce/agents|packs|org-chart`);
Snowflake serialize không nhất quán. Nếu bắt đầu sửa schema trước khi khóa vocabulary/enum/ID/
route, mỗi milestone sau sẽ tiếp tục đẻ alias mới.

M0 **không sửa code sản phẩm hay schema**. Nó tạo: (1) tài liệu vocabulary canonical, (2) một
nguồn enum dùng chung 3 runtime + contract test round-trip, (3) route inventory + CI lint
chặn route alias mới, (4) Company read/write inventory, (5) ADR-ID-MODEL-001 (SpineId Snowflake
/ LeafId UUIDv7 + generator registry) cho M2, (6) ADR-SLUG-001 cho M2.

## Deliverables

### 1. Canonical vocabulary doc
`docs/architecture/specs/2026-08-29-workspace-canonical-vocabulary.md` — định nghĩa và cấm alias cho:
Workspace, Workspace Member, Workspace Runtime Node, Workspace Vault, Workspace Lifecycle,
Project Lifecycle, Legal Entity Profile, Functional AgentSpec, Workforce Role/Persona,
Runtime Mode, Sync Policy, Sync Status. Mỗi mục ghi rõ: định nghĩa 1 câu, alias bị cấm
(vd. "venture", "company stage", "brain"), lớp kiến trúc sở hữu (4 vùng CLAUDE.md).

### 2. Canonical enum — một nguồn, ba runtime
Tạo `shared/contracts/enums/` (vị trí chính xác chốt khi execute — ưu tiên chỗ đã có codegen).
File nguồn JSON:

```
workspace_lifecycle_stage: [W0_IDEA, W1_PROBLEM_VALIDATION, W2_SOLUTION_VALIDATION,
                            W3_MVP_BUILD, W4_PRODUCT_MARKET_FIT, W5_SCALE]
project_lifecycle_stage:   [P0_DISCOVERY, P1_PROBLEM_VALIDATION, P2_SOLUTION_VALIDATION,
                            P3_BUILD_VALIDATE, P4_GO_TO_MARKET, P5_OPERATE_GROWTH, P6_SCALE_GOVERN]
workspace_status:          [ACTIVE, ARCHIVED, SUSPENDED]
project_status:            [ACTIVE, PAUSED, COMPLETED, ARCHIVED]
runtime_mode:              [LOCAL_ONLY, REMOTE_ACCESS, CLOUD_CONTINUITY]
sync_policy:                [CONTROL_METADATA_ONLY, SELECTIVE_ENCRYPTED, FULL_ENCRYPTED]
sync_status:                [LOCAL_ONLY, PENDING, IN_SYNC, CONFLICT, ERROR]
legal_entity_status:       [DRAFT, REGISTRATION_PREPARATION, REGISTERED_UNVERIFIED,
                            VERIFIED, SUSPENDED, DISSOLVED]
```

- Sinh: `.ts` const union (cho `services/*`), `.dart` enum + `fromString`/`toApi` (cho `frontend/`),
  `.py` `StrEnum` (cho `packages/agent_core` + `apps/cosa`).
- Frontend `ProjectStage` hiện tại ([frontend/lib/data/models/stage_model.dart:142-154](../../../../frontend/lib/data/models/stage_model.dart#L142-L154))
  giữ tên class nhưng đổi giá trị wire sang `P0_DISCOVERY..P6_SCALE_GOVERN`; giữ một bảng map
  tạm S0_EXPLORE→P0_DISCOVERY… để migration M4 dùng.
- **Chưa** đụng cột DB — chỉ là contract. M2/M4 mới migrate cột.

### 3. Route inventory + CI lint
- `docs/architecture/generated/route-inventory.md` (sinh bằng script): mọi route Dart gọi
  (grep `ApiClient.(get|post|put|delete|patch)\(` + `postJson`/`getJson` trong `frontend/lib/`)
  đối chiếu handler Encore thật (`api({ ... path: ... })` trong `services/*/**/handlers/`).
- Đánh dấu route "ma" đã biết: `/operations/strategy/stage-context`,
  `/operations/strategy/projects/:id/stage` ([frontend/lib/modules/strategy/services/stage_service.dart:85](../../../../frontend/lib/modules/strategy/services/stage_service.dart#L85), [:130](../../../../frontend/lib/modules/strategy/services/stage_service.dart#L130));
  `/workforce/agents`, `/workforce/packs`, `/workforce/org-chart` ([frontend/lib/modules/agents/services/agent_platform_service.dart](../../../../frontend/lib/modules/agents/services/agent_platform_service.dart));
  drift `/strategy/projects` vs `/operations/strategy/projects` ([frontend/lib/modules/strategy/services/strategy_service.dart](../../../../frontend/lib/modules/strategy/services/strategy_service.dart)).
- CI check mới: fail nếu route Dart không khớp handler nào **và** không nằm trong allowlist
  "known-broken, owned by M4/M7". Chặn thêm route mới không có handler.
- `ApiClient.normalizeEndpoint` ([frontend/lib/core/network/api_client.dart:92-102](../../../../frontend/lib/core/network/api_client.dart#L92-L102))
  rewrite `/finance/`→`/finance-legal/`, `/legal/`→`/finance-legal/` — ghi vào inventory là
  "rewrite gây route drift, M7 gỡ".

### 4. Company read/write inventory
`docs/architecture/generated/company-usage-inventory.md`: phân loại mọi occurrence của
`company`/`companyId`/`company_id` thành:
- **Legacy tenancy (M2 xóa):** `services/cosa/storage/schema.ts` bảng `companies`,
  `company_memberships`, `company_agent_policy`, `licenses.companyId`, `company_entitlements`
  ([schema.ts:36-146](../../../../services/cosa/storage/schema.ts#L36-L146)); `auth.service.ts`
  params `company_name`/`join_company_id` ([services/cosa/services/auth.service.ts:25-34](../../../../services/cosa/services/auth.service.ts#L25-L34));
  handler `/platform/auth/companies/create|join` ([services/cosa/handlers/company.handler.ts:51](../../../../services/cosa/handlers/company.handler.ts#L51), [:58](../../../../services/cosa/handlers/company.handler.ts#L58));
  `company_stage`/`venture_stage_entered_at` ([services/company/shared/db/schema/identity.ts:8-11](../../../../services/company/shared/db/schema/identity.ts#L8-L11));
  `platformCompanyId` trên legal entity; `sync.service.ts` fallback company membership
  ([services/company/identity/services/sync.service.ts:45-51](../../../../services/company/identity/services/sync.service.ts#L45-L51)).
- **Hợp lệ (giữ nguyên):** tên công ty của customer/counterparty trong CRM/commercial,
  `commercial.*` company fields, tài liệu tiếng Anh trích dẫn.

### 5. ID model contract (spec cho M2 — C-3, C-5, C-6)
`docs/architecture/adr/ADR-ID-MODEL-001-spine-snowflake-leaf-uuidv7.md` (thay cho tên
"managed-generator-registry" cũ):

**Hai loại ID.**
- `SpineId` = **Snowflake `BIGINT`** — entity ít cardinality, ít tần suất, tạo là hành động
  provisioning có chủ đích: `workspace`, `project`, `legal_entity_profile`, `workforce_member`,
  `sop_definition`, lifecycle transition record, approval record.
- `LeafId` = **UUIDv7** (lưu cột `uuid`, chuỗi canonical trên wire) — entity cardinality cao do
  runtime sinh liên tục, có thể **offline**: `knowledge_document`, `knowledge_chunk`, `run`,
  `conversation`, `artifact`, `memory_item`, `bank_transaction`, ingestion object.
- Cả hai time-ordered. Không dùng cho ID: capability/spec ID (namespace + semver + content hash),
  idempotency key, external provider ID, object URI, encryption key ref.

**Snowflake generator (chỉ authoritative, luôn online).**
- Chỉ `services/cosa` (control-plane) chạy generator; cloud workspace runtime chạy generator khi
  Cloud Continuity, dưới lease của cùng registry. Local `services/company` / AgentOS **không**
  chạy generator — xin SpineId qua RPC control-plane.
- Bỏ `NODE_ID = Math.random()*1024`
  (hiện [services/company/shared/services/snowflake.service.ts:6](../../../../services/company/shared/services/snowflake.service.ts#L6),
  [services/cosa/services/snowflake.service.ts](../../../../services/cosa/services/snowflake.service.ts)).
  Slot do registry cấp + lease + heartbeat + fencing token; process authoritative **không start**
  nếu thiếu/trùng slot.
- Bit layout versioned (không đổi âm thầm): `41` bit ms từ COSA epoch (~69 năm) · `1` bit
  reserved(=0) · `10` bit slot (1024) · `12` bit sequence (4096/ms). Fleet authoritative nhỏ +
  luôn online ⇒ 1024 slot dư; vấn đề cũ là `random()`, không phải số lượng.
- Clock-regression handling (persist `last_ts` checkpoint xuống đĩa; không phát lùi; virtual-clock
  advance trong drift budget, alert khi vượt), sequence-exhaustion handling (nhảy ms kế),
  restart fencing.
- Mọi Snowflake qua JSON = **decimal string** (không JS/Dart `Number` — mantissa 53-bit < 63-bit).

**C-6: SpineId chỉ tạo được khi online.** Tạo workspace/project/legal entity/workforce
member/SOP = provisioning qua control-plane. Local offline ⇒ `APIError.unavailable`, KHÔNG queue
bằng ID tạm. Không có đường sinh SpineId offline ⇒ không cần zone bit / per-workspace local slot.
Vận hành offline (agent run, sửa nội dung, sinh LeafId) không đổi.

**Làm rõ D-06 (không đảo ngược):** "persistent domain **resource** (spine) dùng Snowflake
`BIGINT`; **record** cardinality cao do runtime sinh dùng UUIDv7; cùng `workspace_id` giữ nguyên
xuyên local/cloud". Supersede audit §4.5: bullet "node đã kích hoạt sinh ID offline" chỉ còn
đúng cho LeafId; bỏ bullet "local-only tự mint workspace ID rồi platform adopt".

### 6. Slug + subdomain contract (spec cho M2)
`docs/architecture/adr/ADR-SLUG-001-workspace-slug-subdomain.md`:
- `name` = display, Unicode, mutable, không phải DNS identity.
- `slug` = lowercase ASCII DNS label, unique toàn cầu khi link platform, platform giữ chỗ atomically.
- `WorkspaceSlug` table: `workspace_id`, `slug`, `status` (ACTIVE|REDIRECT|RELEASED),
  `redirect_to_slug`, `reserved_at`, `released_at`.
- Reserved list: `admin, api, app, www, support, assets, static, cdn, mail, ...` (chốt danh sách đầy đủ).
- Normalization: NFKC → lowercase → strip → thay khoảng trắng bằng `-` → bỏ ký tự ngoài `[a-z0-9-]`
  → collapse `-` → trim `-` → reject nếu rỗng/reserved/đã tồn tại.
- Rename tạo redirect history trong retention window, không đổi `workspace_id`.
- `custom_domain` + LadiPage connector chỉ tham chiếu `workspace_id` + active slug (integration
  record, không phải tenant identity).

## Test plan

- **Enum round-trip:** cho mỗi enum, test trên TS + Dart + Python: `fromWire(toWire(v)) == v`
  với mọi giá trị; unknown value ⇒ lỗi rõ ràng (không im lặng map về default).
- **Snowflake serialization contract test:** ID mẫu (max 63-bit) round-trip JSON không mất
  precision trên Dart, TS, Python (test này chạy được ngay, dùng generator hiện tại).
- **UUIDv7 contract test:** parse/format canonical string + tính đơn điệu theo thời gian trên
  Dart, TS, Python; phân biệt v7 với v4 hiện tại (`uuid.uuid4()` trong Agent Core).
- **Slug normalization test:** bảng case gồm Unicode, khoảng trắng, reserved word, case-fold
  collision, chuỗi rỗng sau normalize.
- **Route inventory test:** snapshot test — route Dart mới không match handler + không trong
  allowlist ⇒ CI fail.

## Exit gate (chặn M1)

- [ ] Vocabulary doc + 2 ADR (ID model, slug) merged.
- [ ] Enum contract sinh cho 3 runtime; round-trip test xanh trên cả 3.
- [ ] Route inventory + company-usage inventory sinh và commit; CI route-alias lint bật.
- [ ] Snowflake JSON precision test + UUIDv7 contract test xanh trên Dart/TS/Python.
- [ ] Danh sách SpineId vs LeafId chốt trong ADR-ID-MODEL-001.
- [ ] Không có thay đổi schema DB hay behavior sản phẩm trong M0 (diff review xác nhận).

## Ngoài phạm vi M0

Sửa cột DB, migrate enum thật, implement generator registry (M2), implement slug reservation
(M2), sửa route ma (M4/M7). M0 chỉ khóa hợp đồng.
