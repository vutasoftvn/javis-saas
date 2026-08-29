# M2 — Workspace canonical + Snowflake registry + slug cutover

**Audit:** §9.2 · **Phụ thuộc:** M0, M1 · **Master:** [../2026-08-29-cosa-workspace-canonical-master-plan.md](../2026-08-29-cosa-workspace-canonical-master-plan.md)

## Context

`Company` vẫn là aggregate tenancy song song với `Workspace`:
[services/cosa/storage/schema.ts:36-146](../../../../services/cosa/storage/schema.ts#L36-L146)
có `companies`, `company_memberships`, `company_agent_policy`, `licenses(company_id)`,
`company_entitlements` **cạnh** `platform_workspaces`, `workspace_licenses`,
`workspace_entitlements`. Auth vẫn nhận `company_name`/`join_company_id`; workspace
provisioning chỉ chạy khi vắng tham số company
([services/cosa/services/auth.service.ts:181-190](../../../../services/cosa/services/auth.service.ts#L181-L190)).
Local sinh Snowflake mới rồi lưu `platformWorkspaceId` làm mapping
([services/company/identity/services/sync.service.ts:110-117](../../../../services/company/identity/services/sync.service.ts#L110-L117)) —
trái quyết định D-06 (một workspace identity xuyên hai plane). Snowflake `NODE_ID` random lúc
process start, không registry/lease/fencing
([services/company/shared/services/snowflake.service.ts:6](../../../../services/company/shared/services/snowflake.service.ts#L6)).
`platform_workspaces.workspace_name` là text không unique; không có slug contract.

**C-2 (pre-launch, ~0 dữ liệu thật):** M2 cut thẳng model ID canonical + reset dev/test
fixture. KHÔNG làm `workspace_id_map` + batched FK-rewrite migration + shadow read comparison
+ reconciliation report cho dữ liệu thật. VẪN viết guard code + test để hệ thống không tự
sinh mapping-ID về sau.

## Deliverables

### 1. Canonical Workspace schema (audit §4.1)
Workspace (aggregate root, tenant duy nhất):

```
id                        BIGINT Snowflake — canonical, giữ nguyên xuyên local/cloud
name                      display, Unicode, mutable
slug                      DNS-safe, globally unique khi link platform (nullable khi local-only)
status                    ACTIVE | ARCHIVED | SUSPENDED
lifecycle_stage           W0_IDEA .. W5_SCALE
stage_entered_at          TIMESTAMPTZ
stage_version             INT — optimistic concurrency (dùng ở M4)
runtime_mode              LOCAL_ONLY | REMOTE_ACCESS | CLOUD_CONTINUITY  (default LOCAL_ONLY)
sync_policy               CONTROL_METADATA_ONLY | SELECTIVE_ENCRYPTED | FULL_ENCRYPTED
sync_status               LOCAL_ONLY | PENDING | IN_SYNC | CONFLICT | ERROR
primary_legal_entity_id   BIGINT Snowflake NULL
created_at / updated_at / archived_at(NULL)
```

- `services/company/shared/db/schema/identity.ts` — bảng workspace canonical; cột
  `company_stage`/`venture_stage_entered_at` giữ tạm cho M4 backfill rồi drop ở M4.
- `services/cosa/storage/schema.ts` — giữ `platform_workspaces` + `workspace_licenses` +
  `workspace_entitlements`; **drop** `companies`, `company_memberships`, `company_agent_policy`;
  chuyển `licenses`/`entitlements` sang khóa `platform_workspace_id`.
- Bỏ `company_id`, `platform_company_id`, `company_stage`, `workspace_uid`, Company alias khỏi
  public/core contract. `platform_company_id` chỉ được phép tồn tại như private integration
  metadata ở Identity DB (theo spec 2026-08-27 §3), KHÔNG trong business schema / public endpoint.
- Migration + `node scripts/migrate.mjs`. Vì C-2: migration có thể `DROP` bảng company trực
  tiếp + seed fixture mới, không cần data-copy có kiểm chứng.

### 2. Managed Snowflake generator registry — chỉ authoritative (C-3, C-5, C-6)
`SpineId` = Snowflake; `LeafId` = UUIDv7 (xem [M0 §5 / ADR-ID-MODEL-001](./M0-contract-freeze.md)).
Chỉ control-plane sinh SpineId; local `services/company`/AgentOS xin qua RPC.

Bảng `snowflake_generator_slots` (ở `services/cosa` control-plane):

```
generator_id       TEXT PK        -- "cosa:<instance>", "cloud-rt:<workspace_id>:<region>"
slot               INT            -- 0..1023, nhét vào bit layout, unique đang-active
runtime_role       TEXT           -- cosa_control_plane | cloud_workspace_runtime
lease_epoch        BIGINT
fencing_token      BIGINT
lease_expires_at   TIMESTAMPTZ
last_heartbeat_at  TIMESTAMPTZ
clock_checkpoint   BIGINT         -- last max timestamp phát ra, chống clock regression
created_at
UNIQUE (slot) WHERE lease_expires_at > now()
```

- Reuse pattern lease: [services/cosa/services/control-plane-lease.service.ts](../../../../services/cosa/services/control-plane-lease.service.ts).
- [services/cosa/services/snowflake.service.ts](../../../../services/cosa/services/snowflake.service.ts):
  - Bỏ `NODE_ID = Math.floor(Math.random()*1024)`.
  - Startup: registry `acquire(generator_id, runtime_role)` → `slot` + `fencing_token`; registry
    unreachable hoặc slot đang bị lease process khác ⇒ **process không start** (fatal), trừ
    `NODE_ENV=test`/`dev` dùng stub deterministic.
  - Heartbeat renew lease; clock regression (`now < clock_checkpoint`) ⇒ virtual-clock advance
    trong drift budget, không phát lùi; vượt budget ⇒ alert.
  - Sequence exhaustion trong 1ms ⇒ spin ms kế, không wrap.
- [services/company/shared/services/snowflake.service.ts](../../../../services/company/shared/services/snowflake.service.ts):
  - **Không còn là generator.** Đổi thành client gọi RPC control-plane `mintSpineId(kind)` (hoặc
    xóa hẳn, ép call site dùng endpoint provisioning tương ứng). Local offline ⇒ `APIError.unavailable`.
  - Rà mọi call `generateSnowflake()` trong write path của `services/company` → thay bằng
    provisioning call (workspace/project/legal/member/SOP đều tạo qua control-plane).
- Bit layout: `41` ms (COSA epoch) · `1` reserved(=0) · `10` slot · `12` sequence — chốt ở
  ADR-ID-MODEL-001. Fleet authoritative nhỏ + luôn online ⇒ 1024 slot dư.
- **JSON = decimal string everywhere:** rà `services/*` trả Snowflake dạng number; ép `.toString()`.
  Contract test precision (M0) mở rộng cho payload thật.

### 3. Agent Core leaf entity ID → UUIDv7 (audit §3.10, C-5)
- [packages/agent_core/knowledge/models.py](../../../../packages/agent_core/knowledge/models.py) —
  `KnowledgeDocument.id`, `KnowledgeChunk.id`: `uuid.uuid4()` → **UUIDv7** (`uuid6` lib hoặc
  `uuid.uuid7()` khi có; giữ kiểu `str`). KHÔNG chuyển sang Snowflake.
- `packages/agent_core/conversations/models.py`, `runs/models.py`, `artifacts/models.py`,
  `memory/models.py` — tương tự: prefix + UUIDv7 (giữ prefix `conv_`/`run_`/`art_` nếu code đang
  phụ thuộc, phần UUID đổi v4→v7).
- `bank_transaction` + ingestion object ([apps/cosa/knowledge_ingestion/](../../../../apps/cosa/knowledge_ingestion/)) — LeafId UUIDv7.
- Giữ nguyên non-ID: `PinnedSpecIdentity` (capability/spec), semver, content hash, idempotency
  key, external provider ID, object URI, encryption key ref.
- Agent Core sinh LeafId **cục bộ, offline OK** — không gọi control-plane, không cần lease.
- SpineId mà Agent Core cần tham chiếu (workspace_id, project_id, sop_id…) nhận từ context đã
  provisioned, không tự sinh.

### 4. Một workspace ID xuyên plane — luôn platform-minted (audit §3.4, C-6)
- Tạo workspace là bước provisioning online qua `services/cosa`; platform mint `workspace_id`
  (SpineId). **Không có** đường tạo workspace offline — client offline ⇒ `APIError.unavailable`,
  không ID tạm.
- [services/company/identity/services/sync.service.ts:110-117](../../../../services/company/identity/services/sync.service.ts#L110-L117) —
  local INSERT workspace dùng `id = platformWorkspaceId`, KHÔNG `generateSnowflake()`; bỏ khái
  niệm mapping-ID. Cột `platformWorkspaceId` → không còn cần (id local == id platform); giữ tạm
  nếu cần transition, drop khi call site sạch.
- [sync.service.ts:45-51](../../../../services/company/identity/services/sync.service.ts#L45-L51),
  [:196-202](../../../../services/company/identity/services/sync.service.ts#L196-L202) —
  bỏ `catch { workspaceMemberships = [] }` nuốt lỗi + fallback `listPlatformMemberships`
  (company membership). Lỗi mạng/auth ⇒ trả lỗi sync-required rõ ràng, không "no workspace".
- `runtime_mode = LOCAL_ONLY` chỉ là chế độ vận hành (business data ở local, chạy offline được).
  Nó **vẫn được tạo online** như mọi workspace khác — không có "local-only chưa từng lên platform".
  Sau khi provisioned + sync-down, workspace LOCAL_ONLY hoạt động hoàn toàn offline.
- Guard test: **không code path nào** gọi `generateSnowflake()` cho `workspace.id`; mọi INSERT
  workspace ở local dùng đúng ID nhận từ control-plane provisioning.

### 5. Auth/register/join/membership/license/entitlement/policy → Workspace (audit §3.1)
- [services/cosa/services/auth.service.ts:25-34](../../../../services/cosa/services/auth.service.ts#L25-L34),
  [:181-190](../../../../services/cosa/services/auth.service.ts#L181-L190) — bỏ `company_name`,
  `join_company_id`; `RegisterParams` chỉ workspace fields (name, slug request, email, password,
  problemStatement, targetCustomer, goal). Workspace provisioning là path chính.
- [services/cosa/handlers/company.handler.ts:51](../../../../services/cosa/handlers/company.handler.ts#L51),
  [:58](../../../../services/cosa/handlers/company.handler.ts#L58) — drop
  `/platform/auth/companies/create|join`. Nếu cần compatibility tạm cho client cũ: adapter ở
  biên trả `410 Gone` + hướng dẫn, xóa sau 1 release.
- `licenses`, `company_entitlements` → `workspace_licenses`, `workspace_entitlements` khóa
  `platform_workspace_id` (audit §3.1).
- `company_agent_policy` → `workspace_agent_policy` ([services/cosa/services/agent-policy.service.ts](../../../../services/cosa/services/agent-policy.service.ts)).
- Frontend đăng ký gửi đủ workspace fields + email/password (audit §3.9 — hiện onboarding bỏ
  `problemStatement`/`targetCustomer`/`goal` nếu không inject callback).

### 6. Slug contract (audit §4.6)
- Bảng `workspace_slugs` (`services/cosa/storage/schema.ts`): `workspace_id`, `slug`,
  `status` (ACTIVE|REDIRECT|RELEASED), `redirect_to_slug`, `reserved_at`, `released_at`.
  `UNIQUE` index trên normalized `slug`.
- Reserved list + normalization theo ADR-SLUG-001 (M0).
- Handler slug reservation: atomic INSERT (unique constraint là cơ chế giữ chỗ); conflict ⇒
  gợi ý slug khác. Slug derive từ `name` làm default, user chỉnh được.
- Rename: tạo row REDIRECT trỏ slug cũ → slug mới, retention window; `workspace_id` không đổi.
- `custom_domain` / LadiPage: chỉ tham chiếu `workspace_id` + active slug (integration record).

### 7. Đổi tên physical folder/service/env `company` (audit §9.2.9)
CHỈ sau khi domain cutover xong (mục 1–6 merged + xanh), để diff cơ học không che logic lỗi.
Có thể để sang cuối M2 hoặc milestone dọn dẹp riêng.

## Test plan (audit §10.1, §10.2)

- Generator restart giữ slot identity, không collision; hai process không lease cùng slot
  (unique-while-active); clock regression không tạo duplicate/ID ngược (virtual-clock advance);
  sequence exhaustion spin ms kế đúng.
- JSON round-trip Snowflake không mất precision + UUIDv7 parse/monotonic trên Dart/TS/Python với payload thật.
- Platform/local/AgentOS/event/backup dùng **cùng** workspace ID (E2E: tạo workspace ở platform
  → sync xuống local → run AgentOS → event envelope; assert ID bằng nhau).
- **SpineId offline**: local `services/company` offline gọi tạo workspace/project/legal/member/SOP
  ⇒ `APIError.unavailable`, KHÔNG tạo row với ID tạm.
- **LeafId offline**: AgentOS offline sinh knowledge doc/chunk/run/conversation/artifact bằng
  UUIDv7 bình thường; sync lên cloud sau đó không đụng.
- Tạo workspace W0 khi chưa có legal entity — pass (qua control-plane provisioning online).
- Slug: normalization, reserved word, case-fold, concurrent reservation (chỉ một thắng);
  rename giữ workspace ID + redirect history đúng.
- CRM counterparty/company name hợp lệ KHÔNG bị xóa (grep review + test commercial module).
- Không code path nào gọi `generateSnowflake()` cho `workspace.id`/`project.id` ở local (guard test).
- `sync.service.ts` cloud timeout ⇒ sync-required error, không company fallback.

## Exit gate

- [ ] Một user tạo/chọn nhiều workspace; cùng workspace ID xuyên platform/local/AgentOS/event.
- [ ] Zero mismatch ở membership/license/policy khi resolve theo workspace.
- [ ] Generator registry: process authoritative không start khi thiếu/trùng slot; restart +
      collision test xanh. Local `services/company` không chạy generator (chỉ RPC provisioning).
- [ ] SpineId chỉ sinh khi online; LeafId (UUIDv7) sinh offline OK; Agent Core leaf ID = v7.
- [ ] Bảng `companies`/`company_memberships`/`company_agent_policy` đã drop; không endpoint nào
      trả `company_id` trong business contract.
- [ ] `services/company` + `services/cosa` typecheck + tests xanh (fixture reset chấp nhận
      thay đổi số lượng test, không giảm coverage nhánh).

## Ngoài phạm vi M2

`workspace_id_map` + batched FK-rewrite + shadow comparison (không cần — C-2). Workspace &
Project lifecycle CAS/journal (M4). Vault physical isolation + RLS (M3). Đổi `company_stage`
column (M4).
