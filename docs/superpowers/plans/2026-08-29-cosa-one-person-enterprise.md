# COSA One-Person Enterprise — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cho cá nhân tạo `Venture Workspace` miễn phí từ Level 0 (trước khi có pháp nhân), có entitlement thật, vòng đời stage thật, và loại bỏ mọi UI/API finance–legal giả — làm nền cho các release sau (legal catalog, kế toán TT58, connector Cas, AI operating loop).

**Architecture:** Control Plane (`services/cosa`, Encore/TS) thêm một lớp tenant `platform_workspaces` song song với `companies` legacy, provision `free` license + entitlement trong một transaction, rồi đồng bộ một chiều xuống Company Service (`services/company`, Encore/TS) thành `core.workspaces`. Venture stage (workspace-level) trở thành state machine thật do một lifecycle service sở hữu, tách khỏi project phase (project-level). Agent Platform (`packages/agent_core` + `apps/cosa`, Python) sửa capability finance sai hợp đồng và gỡ capability payout. Flutter (`frontend`) bỏ fallback/mocks và gate feature theo entitlement backend.

**Tech Stack:** Encore.ts + Drizzle ORM + Postgres (services), Python + pytest (agent), Flutter + Dart (frontend). Outbox pattern qua `integration.event_outbox` + `appendOutboxEvent(tx, event)`. Snowflake ID (`generateSnowflake()` / `generateSnowflakeStr()`).

---

## Global Constraints

Copy nguyên văn từ spec `docs/superpowers/specs/2026-08-28-cosa-one-person-enterprise-design.md` và `CLAUDE.md`:

- **Business truth thuộc `services/*` (TypeScript/Encore), không thuộc LLM runtime.** Mọi side effect qua Capability Layer + Governance + Audit.
- **Một danh tính workforce duy nhất: `WorkforceMember`.** Không tạo bảng nhân sự riêng cho AI vs người.
- **Governance là code xác định.** Approval bind đúng `run_id + tool_call_id + checkpoint_ref`, không lookup theo tên action. Constraint lịch sử (đã REQUIRE_APPROVAL) không tự mất khi policy sau nới lỏng.
- **Trạng thái ứng dụng phải structured**, không `if "blocked" in model_text`.
- **Hành động rủi ro cao** (deploy, xóa dữ liệu, gửi tin ra ngoài, đổi quyền, hành động tài chính) cần approval qua code, không qua prompt.
- **Không tuyên bố "xong" khi chưa test.** Mỗi thay đổi hành vi cần test tương ứng; chạy test trước khi báo cáo.
- **Migration forward-only**, kèm `.down.sql`, idempotent (`IF NOT EXISTS` / check trước khi tạo). Không xóa `companies`, `core.workspaces`, `company_stage`, `accounting_profiles` hoặc dữ liệu lịch sử. Sau khi thêm migration chạy `node scripts/migrate.mjs` (hoặc `make migrate-all`).
- **`packages/agent_core/` KHÔNG import bất cứ gì từ `services/company/*`.** Chỉ `apps/cosa/` compose cả hai. Guard: `make boundary-check`.
- **Encore service layout:** `handlers/` chỉ parse input → gọi service → trả response (không query DB trực tiếp); `services/` chứa business logic + Drizzle + transaction. Lỗi trả qua `APIError` (`invalidArgument`, `unauthenticated`, `permissionDenied`, `notFound`, `alreadyExists`, `internal`, `unavailable`) — không throw `Error` trần. Endpoint nội bộ giữa service: `expose: false` hoặc `auth: false` + network. Schema Drizzle tập trung ở `services/company/shared/db/schema/<service>.ts`.
- **Comment tiếng Việt cho phần "why"**; tên định danh / log / trích dẫn văn bản tiếng Anh giữ nguyên.
- **`Venture Workspace` là sản phẩm; pháp nhân là trạng thái/liên kết sau đó.** Trạng thái pháp lý là trục riêng, không suy ra từ stage: `NOT_DECLARED → UNREGISTERED → REGISTRATION_READINESS → REGISTERED_PENDING_VERIFICATION → REGISTERED_VERIFIED`.
- **AI diễn đạt theo 3 lớp** `CURRENT_LAW` / `POLICY_WATCH` / `PROFESSIONAL_REVIEW`; mọi câu tư vấn kèm: điều đã biết + nguồn, giả định chưa kiểm chứng, hành động kế tiếp, nhãn `insight|proposal|requires_professional_review`.
- **`finance.payout.execute` và endpoint `/finance-legal/payouts` KHÔNG được tạo/đăng ký** trong phạm vi các release này.
- **Cas connector: read-only.** Scope chỉ `balance:read`, `transactions:read`. Secret ở secret manager (`secret://cosa-connectors/...`), không ở Flutter/conversation/agent memory.

---

## Bối cảnh & đối chiếu code (đọc trước khi bắt đầu)

Spec §4 phần lớn đúng, nhưng vài tiền đề sai tên/mô hình — plan này dùng tên thật:

| Spec nói | Thực tế | Nguồn |
|---|---|---|
| tenant `identity_workspaces` | Drizzle export `identityWorkspaces` → **table `core.workspaces`**; chỉ có `platformCompanyId`, **không** có `platformWorkspaceId` | `services/company/shared/db/schema/identity.ts:5-13` |
| đăng ký "bắt buộc tạo company" | `registerPlatformUser` chỉ tạo `cosa.companies` **khi có `company_name`** | `services/cosa/services/auth.service.ts:148-171` |
| Control Plane có "workspace" | Control Plane **không có** thực thể tenant; "workspace" chỉ là cột string trên bảng connector/schedule | explore |
| stage transition "chỉ ghi log" | `stage-transition.handler.ts` là **CRUD config** bảng `strategy.stage_transitions` (cặp from→to hợp lệ), **không** journal; `core.workspaces.company_stage` **không bao giờ** update sau khi tạo | `services/company/shared/db/schema/strategy.ts:17-28`, `.../strategy/handlers/stage-transition.handler.ts` |
| (không nêu) | **2 trục stage riêng hợp lệ**: `core.workspaces.company_stage` (venture, đóng băng S0) và `strategy.projects.phase` (project, đặt `"PLANNING"` lúc tạo, không update; 1 workspace → N project). `assessProjectStage()` trả recommendation nhưng **không persist** | `services/company/operations/strategy/services/stage-assessment.service.ts:46`, `.../services/project.service.ts:99` |
| sync là việc mới | **Đã có** sync một chiều pull-based: `POST /identity/sync-from-platform` → `listPlatformMemberships` / `validatePlatformMembership` (gọi `/platform/internal/list-memberships`, `/platform/internal/validate-membership` trên Control Plane), upsert `core.workspaces` keyed theo `platformCompanyId` | `services/company/identity/services/sync.service.ts`, `.../platform.client.ts` |
| agent gọi `/finance-legal/payouts` | endpoint không tồn tại; `finance.payout.execute` (HIGH) vẫn đăng ký | `apps/cosa/capabilities/finance_write.py:17-41,68-84` |
| agent ghi transaction `accountId`/`type` | backend cần `workspaceId`+`transactionDate`+`description`+`amount`+`direction('IN'\|'OUT')` | `services/company/finance-legal/services/financial-transaction.service.ts:41-51` |
| connector allow-list chỉ `sandbox-read` | đúng: `COSA_CONNECTOR_ALLOWED_KEYS \|\| "sandbox-read"`; secret_ref phải `secret://cosa-connectors/` | `services/cosa/services/workspace-connector.service.ts:27-36` |
| legal source hard-code | `frontend/lib/modules/legal/services/legal_service.dart:87` hard-code `"Thông tư 58/2024/TT-BTC"` (**sai năm**, phải 2026); không có `getLegalSources()` backend | explore |
| license/entitlement | plan `free/starter/pro/enterprise` đã seed (`plans.defaultFeatures` có `finance:false`); `cosa.licenses`/`cosa.company_entitlements` tồn tại nhưng **0 insert logic** | `services/cosa/storage/schema.ts:69-103` |
| "task event typecheck error" (Release A) | **không tìm thấy** khi explore — verify lúc implement, có thể đã fix | explore |

**Quyết định đã chốt với người dùng:** (1) plan bao phủ A–E; (2) xây stack `platform_workspaces` song song như spec; (3) venture stage và project phase là hai state machine riêng, thiết kế cả hai; (4) harness-P0 (`docs/implementation/2026-08-28-cosa-agent-harness-integration-adjustment.md`) chạy track song song, khuyến nghị xong trước khi Release C bật capability *write* finance ở production.

**Phạm vi tài liệu này:** Phase 0 (Foundations) + Phase 1 (Release A) viết chi tiết bite-sized, thực thi được ngay. Phase 2–5 (Release B–E) là **milestone spec** (file structure + bảng + endpoint + capability + nghiệm thu); **mỗi release phải chạy lại `superpowers:writing-plans` để bung task chi tiết trước khi execute**, vì thiết kế C/D/E nhiều khả năng dịch sau khi A/B lên staging (Cas webhook auth chưa chốt, COA cho TT58 mode khác chưa rõ).

---

## File Structure

### Phase 0–1 (Foundations + Release A) — tạo mới / sửa

**Control Plane `services/cosa`:**
- `storage/schema.ts` — MODIFY: thêm `platformWorkspaces`, `platformWorkspaceMemberships`, `workspaceLicenses`, `workspaceEntitlements`, `platformWorkspaceSyncLog`.
- `migrations/18_platform_workspaces.up.sql` / `.down.sql` — CREATE.
- `migrations/19_workspace_licenses_entitlements.up.sql` / `.down.sql` — CREATE.
- `migrations/20_backfill_platform_workspaces.up.sql` / `.down.sql` — CREATE (backfill từ `companies`).
- `services/venture-workspace.service.ts` — CREATE: `provisionVentureWorkspace()`, `getWorkspaceEntitlement()`, `listWorkspaceMembershipsForUser()`, `validateWorkspaceMembership()`.
- `services/auth.service.ts` — MODIFY: `registerPlatformUser` gọi provisioning; contract mới.
- `handlers/venture-workspace.handler.ts` — CREATE: `GET /platform/workspaces/:id/entitlement`, `POST /platform/internal/list-workspace-memberships`, `POST /platform/internal/validate-workspace-membership`.
- `handlers/auth.handler.ts` — MODIFY: register DTO.
- `tests/venture-workspace.test.ts` — CREATE.

**Company Service `services/company`:**
- `shared/db/schema/identity.ts` — MODIFY: `identityWorkspaces` thêm `platformWorkspaceId` (unique, nullable), `ventureStageEnteredAt`.
- `shared/db/schema/strategy.ts` — MODIFY: thêm `ventureStageTransitions`, `ventureProfiles`.
- `identity/migrations/<n>_platform_workspace_link.up.sql` / `.down.sql` — CREATE.
- `operations/migrations/<n>_venture_stage_and_profile.up.sql` / `.down.sql` — CREATE.
- `identity/services/sync.service.ts` — MODIFY: key theo `platformWorkspaceId`; tạo `venture_profiles` khi sync.
- `identity/services/platform.client.ts` — MODIFY: thêm `listPlatformWorkspaceMemberships`, `validatePlatformWorkspaceMembership`.
- `identity/services/workspace.service.ts` — MODIFY: `getWorkspaceRecord` trả `ventureStage`, `ventureStageEnteredAt`, `platformWorkspaceId`, `legalStatus`.
- `operations/strategy/services/stage-lifecycle.service.ts` — CREATE: `assessVentureStage()`, `transitionVentureStage()`.
- `operations/strategy/services/stage-assessment.service.ts` — MODIFY: persist `projects.phase` khi gate pass (qua caller).
- `operations/strategy/handlers/venture-stage.handler.ts` — CREATE: `assess`, `transition`, `list-transitions`.
- `operations/strategy/handlers/stage-transition.handler.ts` — MODIFY: đổi tên file → `stage-transition-config.handler.ts` (giữ route cũ, chỉ đổi tên để hết mơ hồ).
- `shared/events.ts` — MODIFY: thêm `VENTURE_STAGE_CHANGED = "venture.stage.changed"`, `PROJECT_PHASE_CHANGED = "project.phase.changed"`.
- `operations/strategy/events/venture-stage-events.ts` — CREATE: `buildVentureStageChangedEvent()`.
- `operations/tests/venture-stage-lifecycle.test.ts` — CREATE.

**Agent Platform:**
- `apps/cosa/capabilities/finance_write.py` — MODIFY: gỡ `FINANCE_PAYOUT_EXECUTE_SPEC` + handler; sửa `FINANCE_TRANSACTION_RECORD_SPEC`.
- `apps/cosa/capabilities/__init__.py` — MODIFY: bỏ export payout.
- `tests/apps/cosa/test_finance_write.py` — MODIFY/CREATE.

**Flutter `frontend`:**
- `lib/modules/finance/services/finance_service.dart` — MODIFY.
- `lib/modules/finance/services/finance_tt58_service.dart` — MODIFY (tắt route).
- `lib/modules/legal/services/legal_service.dart` — MODIFY (bỏ hard-code, gate flag).
- `lib/shared/providers/entitlement_provider.dart` (hoặc tương đương) — MODIFY/CREATE: đọc `/platform/workspaces/:id/entitlement`, expose `hasFeature(key)`.
- `lib/modules/auth/…` hoặc `lib/modules/workspace_picker/…` — MODIFY: onboarding S0 5 bước.
- `test/modules/finance/finance_service_test.dart`, `test/modules/legal/legal_service_test.dart` — MODIFY/CREATE.

### Phase 2–5 (Release B–E) — xem milestone spec cuối tài liệu.

---

## Phase 0 — Foundations

### Task 1: Control Plane — schema & migration `platform_workspaces` + memberships

**Files:**
- Modify: `services/cosa/storage/schema.ts`
- Create: `services/cosa/migrations/18_platform_workspaces.up.sql`, `services/cosa/migrations/18_platform_workspaces.down.sql`
- Test: `services/cosa/tests/venture-workspace.test.ts`

**Interfaces:**
- Produces: Drizzle tables `platformWorkspaces { id: bigint, workspaceName: text, ownerUserId: bigint, status: text, createdAt, updatedAt }`, `platformWorkspaceMemberships { id: bigint, platformWorkspaceId: bigint, userId: bigint, role: text, createdAt, updatedAt }`. `role ∈ {'founder','member','viewer'}`.

- [ ] **Step 1: Viết migration up**

```sql
-- services/cosa/migrations/18_platform_workspaces.up.sql
-- Lớp tenant sản phẩm ("Venture Workspace") tách khỏi pháp nhân legacy `companies`.
-- Level 0: một cá nhân tạo workspace trước khi có công ty đăng ký.
CREATE TABLE IF NOT EXISTS cosa.platform_workspaces (
  id             BIGINT PRIMARY KEY,
  workspace_name TEXT        NOT NULL,
  owner_user_id  BIGINT      NOT NULL REFERENCES cosa.users(id) ON DELETE CASCADE,
  status         TEXT        NOT NULL DEFAULT 'active'
                   CHECK (status IN ('active','archived')),
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_platform_workspaces_owner
  ON cosa.platform_workspaces(owner_user_id);

CREATE TABLE IF NOT EXISTS cosa.platform_workspace_memberships (
  id                    BIGINT PRIMARY KEY,
  platform_workspace_id BIGINT NOT NULL REFERENCES cosa.platform_workspaces(id) ON DELETE CASCADE,
  user_id               BIGINT NOT NULL REFERENCES cosa.users(id) ON DELETE CASCADE,
  role                  TEXT   NOT NULL DEFAULT 'member'
                          CHECK (role IN ('founder','member','viewer')),
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (platform_workspace_id, user_id)
);
```

```sql
-- services/cosa/migrations/18_platform_workspaces.down.sql
DROP TABLE IF EXISTS cosa.platform_workspace_memberships;
DROP TABLE IF EXISTS cosa.platform_workspaces;
```

- [ ] **Step 2: Thêm Drizzle definitions vào `services/cosa/storage/schema.ts`** (đặt sau `companyMemberships`, dùng `cosaSchema.table` như các bảng khác)

```ts
export const platformWorkspaces = cosaSchema.table("platform_workspaces", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceName: text("workspace_name").notNull(),
  ownerUserId: bigint("owner_user_id", { mode: "bigint" }).notNull().references(() => users.id, { onDelete: "cascade" }),
  status: text("status").default("active").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const platformWorkspaceMemberships = cosaSchema.table("platform_workspace_memberships", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  platformWorkspaceId: bigint("platform_workspace_id", { mode: "bigint" }).notNull().references(() => platformWorkspaces.id, { onDelete: "cascade" }),
  userId: bigint("user_id", { mode: "bigint" }).notNull().references(() => users.id, { onDelete: "cascade" }),
  role: text("role").default("member").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});
```

- [ ] **Step 3: Chạy migration & kiểm tra**

Run: `cd services/cosa && node scripts/migrate.mjs`
Expected: migration `18_platform_workspaces` applied; `psql ... -c "\d cosa.platform_workspaces"` cho thấy bảng.

- [ ] **Step 4: Test round-trip rollback**

Run: `node scripts/test-migration-rollback.mjs`
Expected: PASS (up→down→up không lỗi).

- [ ] **Step 5: Commit**

```bash
git add services/cosa/storage/schema.ts services/cosa/migrations/18_platform_workspaces.*
git commit -m "feat(cosa): platform_workspaces + memberships schema"
```

---

### Task 2: Control Plane — schema & migration `workspace_licenses` + `workspace_entitlements` + sync log

**Files:**
- Modify: `services/cosa/storage/schema.ts`
- Create: `services/cosa/migrations/19_workspace_licenses_entitlements.up.sql` / `.down.sql`

**Interfaces:**
- Produces: `workspaceLicenses { id: bigint, platformWorkspaceId: bigint, planId: text, status: text, startsAt, expiresAt, gracePeriodDays: integer }`, `workspaceEntitlements { platformWorkspaceId: bigint PK, planId: text, effectiveLimits: jsonb, effectiveFeatures: jsonb, customOverrides: jsonb, snapshotSignature: text, lastIssuedAt }`, `platformWorkspaceSyncLog { id: bigint, platformWorkspaceId: bigint, clientCreationId: text, syncStatus: text, errorMsg: text, syncedAt }`. `syncStatus ∈ {'pending','success','failed'}`.

- [ ] **Step 1: Viết migration up** (mirror `licenses`/`company_entitlements` hiện có nhưng key theo `platform_workspace_id`)

```sql
-- services/cosa/migrations/19_workspace_licenses_entitlements.up.sql
CREATE TABLE IF NOT EXISTS cosa.workspace_licenses (
  id                    BIGINT PRIMARY KEY,
  platform_workspace_id BIGINT NOT NULL REFERENCES cosa.platform_workspaces(id) ON DELETE CASCADE,
  plan_id               TEXT   NOT NULL REFERENCES cosa.plans(id),
  license_key           TEXT   NOT NULL UNIQUE,
  status                TEXT   NOT NULL DEFAULT 'active',
  starts_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at            TIMESTAMPTZ,
  grace_period_days     INTEGER NOT NULL DEFAULT 7,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at            TIMESTAMPTZ,
  UNIQUE (platform_workspace_id)
);

CREATE TABLE IF NOT EXISTS cosa.workspace_entitlements (
  platform_workspace_id BIGINT PRIMARY KEY REFERENCES cosa.platform_workspaces(id) ON DELETE CASCADE,
  plan_id               TEXT   NOT NULL REFERENCES cosa.plans(id),
  effective_limits      JSONB  NOT NULL DEFAULT '{}',
  effective_features    JSONB  NOT NULL DEFAULT '{}',
  custom_overrides      JSONB  NOT NULL DEFAULT '{}',
  snapshot_signature    TEXT,
  last_issued_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cosa.platform_workspace_sync_log (
  id                    BIGINT PRIMARY KEY,
  platform_workspace_id BIGINT NOT NULL REFERENCES cosa.platform_workspaces(id) ON DELETE CASCADE,
  client_creation_id    TEXT   NOT NULL,
  sync_status           TEXT   NOT NULL DEFAULT 'pending'
                          CHECK (sync_status IN ('pending','success','failed')),
  error_msg             TEXT,
  synced_at             TIMESTAMPTZ,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (client_creation_id)
);
```

`.down.sql`: `DROP TABLE IF EXISTS` cả 3 theo thứ tự ngược.

- [ ] **Step 2: Thêm Drizzle definitions** vào `schema.ts` (theo mẫu `licenses`/`companyEntitlements`, đổi FK sang `platformWorkspaces.id`, thêm `platformWorkspaceSyncLog`).

- [ ] **Step 3: Migrate + rollback test**

Run: `cd services/cosa && node scripts/migrate.mjs && cd ../.. && node scripts/test-migration-rollback.mjs`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add services/cosa/storage/schema.ts services/cosa/migrations/19_workspace_licenses_entitlements.*
git commit -m "feat(cosa): workspace_licenses + entitlements + sync_log schema"
```

---

### Task 3: Control Plane — `provisionVentureWorkspace()` transactional service

**Files:**
- Create: `services/cosa/services/venture-workspace.service.ts`
- Test: `services/cosa/tests/venture-workspace.test.ts`

**Interfaces:**
- Consumes: `db`, `schema` từ `../models/db`; `generateSnowflakeStr` từ `./snowflake.service`; `plans` table (đọc `defaultLimits`/`defaultFeatures` của plan `free`).
- Produces:
  ```ts
  export interface ProvisionParams { ownerUserId: bigint; workspaceName: string; clientCreationId: string; planId?: string; }
  export interface ProvisionResult { platformWorkspaceId: string; planId: string; effectiveFeatures: Record<string, unknown>; effectiveLimits: Record<string, unknown>; }
  export async function provisionVentureWorkspace(params: ProvisionParams): Promise<ProvisionResult>;
  ```
  Idempotent theo `clientCreationId` (dò `platform_workspace_sync_log`); trả kết quả cũ nếu đã tồn tại. Một `db.transaction`: insert `platform_workspaces` + `platform_workspace_memberships('founder')` + `workspace_licenses(plan)` + `workspace_entitlements(snapshot = plan.defaultLimits/defaultFeatures)` + `platform_workspace_sync_log(status='pending')`.

- [ ] **Step 1: Viết test thất bại**

```ts
// services/cosa/tests/venture-workspace.test.ts
import { describe, it, expect, beforeAll } from "vitest";
import { db, schema } from "../models/db";
import { eq } from "drizzle-orm";
import { provisionVentureWorkspace } from "../services/venture-workspace.service";
import { registerPlatformUser } from "../services/auth.service";

describe("provisionVentureWorkspace", () => {
  let userId: bigint;
  beforeAll(async () => {
    const r = await registerPlatformUser({ email: `pw-${Date.now()}@t.io`, password: "secret1" });
    // user id lookup
    const [u] = await db.select({ id: schema.users.id }).from(schema.users)
      .where(eq(schema.users.email, JSON.parse(JSON.stringify(r)).email ?? "")).limit(1);
    userId = u?.id ?? BigInt(0);
  });

  it("creates workspace + founder membership + free license + entitlement snapshot in one call", async () => {
    const cid = `cid-${Date.now()}`;
    const res = await provisionVentureWorkspace({ ownerUserId: userId, workspaceName: "AI Coffee Shop", clientCreationId: cid });
    expect(res.planId).toBe("free");
    expect(res.effectiveFeatures.finance).toBe(false); // plan free: finance disabled
    const [ws] = await db.select().from(schema.platformWorkspaces).where(eq(schema.platformWorkspaces.id, BigInt(res.platformWorkspaceId)));
    expect(ws.workspaceName).toBe("AI Coffee Shop");
    const [mem] = await db.select().from(schema.platformWorkspaceMemberships)
      .where(eq(schema.platformWorkspaceMemberships.platformWorkspaceId, BigInt(res.platformWorkspaceId)));
    expect(mem.role).toBe("founder");
  });

  it("is idempotent by clientCreationId (retry returns same workspace, no dup license)", async () => {
    const cid = `cid-idem-${Date.now()}`;
    const a = await provisionVentureWorkspace({ ownerUserId: userId, workspaceName: "W", clientCreationId: cid });
    const b = await provisionVentureWorkspace({ ownerUserId: userId, workspaceName: "W", clientCreationId: cid });
    expect(b.platformWorkspaceId).toBe(a.platformWorkspaceId);
    const licenses = await db.select().from(schema.workspaceLicenses)
      .where(eq(schema.workspaceLicenses.platformWorkspaceId, BigInt(a.platformWorkspaceId)));
    expect(licenses.length).toBe(1);
  });
});
```

- [ ] **Step 2: Chạy test — xác nhận fail**

Run: `cd services/company && :` — thực ra: `cd services/cosa && npx vitest run tests/venture-workspace.test.ts`
Expected: FAIL — `provisionVentureWorkspace` không tồn tại.

- [ ] **Step 3: Viết implementation tối thiểu**

```ts
// services/cosa/services/venture-workspace.service.ts
import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflakeStr } from "./snowflake.service";

const { plans, platformWorkspaces, platformWorkspaceMemberships, workspaceLicenses, workspaceEntitlements, platformWorkspaceSyncLog } = schema;

export interface ProvisionParams { ownerUserId: bigint; workspaceName: string; clientCreationId: string; planId?: string; }
export interface ProvisionResult {
  platformWorkspaceId: string; planId: string;
  effectiveFeatures: Record<string, unknown>; effectiveLimits: Record<string, unknown>;
}

export async function provisionVentureWorkspace(params: ProvisionParams): Promise<ProvisionResult> {
  const name = params.workspaceName.trim() || "Venture Workspace";
  const planId = params.planId ?? "free";

  // Idempotency: nếu clientCreationId đã dùng, trả lại kết quả cũ.
  const [prev] = await db.select().from(platformWorkspaceSyncLog)
    .where(eq(platformWorkspaceSyncLog.clientCreationId, params.clientCreationId)).limit(1);
  if (prev) {
    const [ent] = await db.select().from(workspaceEntitlements)
      .where(eq(workspaceEntitlements.platformWorkspaceId, prev.platformWorkspaceId)).limit(1);
    return {
      platformWorkspaceId: prev.platformWorkspaceId.toString(),
      planId: ent?.planId ?? planId,
      effectiveFeatures: (ent?.effectiveFeatures ?? {}) as Record<string, unknown>,
      effectiveLimits: (ent?.effectiveLimits ?? {}) as Record<string, unknown>,
    };
  }

  const [plan] = await db.select().from(plans).where(eq(plans.id, planId)).limit(1);
  if (!plan) throw APIError.internal(`plan ${planId} chưa được seed`);

  const wsId = BigInt(generateSnowflakeStr());
  await db.transaction(async (tx) => {
    await tx.insert(platformWorkspaces).values({ id: wsId, workspaceName: name, ownerUserId: params.ownerUserId });
    await tx.insert(platformWorkspaceMemberships).values({
      id: BigInt(generateSnowflakeStr()), platformWorkspaceId: wsId, userId: params.ownerUserId, role: "founder",
    });
    await tx.insert(workspaceLicenses).values({
      id: BigInt(generateSnowflakeStr()), platformWorkspaceId: wsId, planId,
      licenseKey: `wl_${wsId.toString()}`, status: "active",
    });
    await tx.insert(workspaceEntitlements).values({
      platformWorkspaceId: wsId, planId,
      effectiveLimits: plan.defaultLimits as object, effectiveFeatures: plan.defaultFeatures as object,
      snapshotSignature: `sig_${wsId.toString()}_${Date.now()}`,
    });
    await tx.insert(platformWorkspaceSyncLog).values({
      id: BigInt(generateSnowflakeStr()), platformWorkspaceId: wsId,
      clientCreationId: params.clientCreationId, syncStatus: "pending",
    });
  });

  return {
    platformWorkspaceId: wsId.toString(), planId,
    effectiveFeatures: plan.defaultFeatures as Record<string, unknown>,
    effectiveLimits: plan.defaultLimits as Record<string, unknown>,
  };
}
```

- [ ] **Step 4: Chạy test — xác nhận pass**

Run: `cd services/cosa && npx vitest run tests/venture-workspace.test.ts`
Expected: PASS cả 2 case.

- [ ] **Step 5: Commit**

```bash
git add services/cosa/services/venture-workspace.service.ts services/cosa/tests/venture-workspace.test.ts
git commit -m "feat(cosa): transactional venture workspace provisioning (idempotent)"
```

---

### Task 4: Control Plane — register contract mới + gọi provisioning

**Files:**
- Modify: `services/cosa/services/auth.service.ts:22-29,89-179`
- Modify: `services/cosa/handlers/auth.handler.ts` (register DTO — tìm handler `register`)
- Test: `services/cosa/tests/venture-workspace.test.ts` (thêm case)

**Interfaces:**
- Consumes: `provisionVentureWorkspace` (Task 3).
- Produces: `RegisterParams` thêm `workspace_name?: string`, `client_workspace_creation_id?: string`. `TokenResponse` thêm `platform_workspace_id?: string`, `workspace_provision_status?: "pending" | "synced"`. Giữ nguyên nhánh `company_name` / `join_company_id` (legacy).

- [ ] **Step 1: Thêm test**

```ts
it("register with workspace_name provisions a free venture workspace", async () => {
  const email = `reg-${Date.now()}@t.io`;
  const res: any = await registerPlatformUser({
    email, password: "secret1", workspace_name: "Solo Bakery",
    client_workspace_creation_id: `ccid-${Date.now()}`,
  });
  expect(res.platform_workspace_id).toBeTruthy();
  const [ent] = await db.select().from(schema.workspaceEntitlements)
    .where(eq(schema.workspaceEntitlements.platformWorkspaceId, BigInt(res.platform_workspace_id)));
  expect(ent.planId).toBe("free");
});
```

- [ ] **Step 2: Chạy — fail** (`registerPlatformUser` chưa nhận `workspace_name`).

Run: `cd services/cosa && npx vitest run tests/venture-workspace.test.ts -t "provisions a free venture"`
Expected: FAIL.

- [ ] **Step 3: Sửa `auth.service.ts`**

- Thêm vào `RegisterParams`: `workspace_name?: string;` và `client_workspace_creation_id?: string;`
- Thêm vào `TokenResponse`: `platform_workspace_id?: string;` và `workspace_provision_status?: "pending" | "synced";`
- Trong `registerPlatformUser`, sau khi transaction tạo user/profile xong (sau dòng 172), thêm:

```ts
let platformWorkspaceId: string | undefined;
let provisionStatus: "pending" | "synced" | undefined;
if (params.workspace_name && !params.join_company_id && !params.company_name) {
  const cid = params.client_workspace_creation_id || `auto-${newUserId.toString()}`;
  const prov = await provisionVentureWorkspace({
    ownerUserId: newUserId, workspaceName: params.workspace_name, clientCreationId: cid,
  });
  platformWorkspaceId = prov.platformWorkspaceId;
  provisionStatus = "pending"; // sync xuống Company Service xảy ra ở Task 8 (async/relay)
}
```

- Bổ sung `platform_workspace_id: platformWorkspaceId` và `workspace_provision_status: provisionStatus` vào object return.
- Import: `import { provisionVentureWorkspace } from "./venture-workspace.service";`

- [ ] **Step 4: Sửa handler DTO** — trong `handlers/auth.handler.ts` thêm `workspace_name?: string` và `client_workspace_creation_id?: string` vào request interface của endpoint register (tìm `register`), pass-through sang service.

- [ ] **Step 5: Chạy test — pass**

Run: `cd services/cosa && npx vitest run tests/venture-workspace.test.ts`
Expected: PASS. Chạy thêm regression: `npx vitest run tests/` (đảm bảo nhánh legacy `company_name` không vỡ).

- [ ] **Step 6: Commit**

```bash
git add services/cosa/services/auth.service.ts services/cosa/handlers/auth.handler.ts services/cosa/tests/venture-workspace.test.ts
git commit -m "feat(cosa): register provisions free venture workspace when workspace_name given"
```

---

### Task 5: Control Plane — internal endpoints workspace-membership (cho sync)

**Files:**
- Modify: `services/cosa/services/venture-workspace.service.ts` (thêm 2 hàm)
- Create: `services/cosa/handlers/venture-workspace.handler.ts`
- Modify: `services/cosa/handlers/api.ts` (barrel export) — thêm export handler mới
- Test: `services/cosa/tests/venture-workspace.test.ts`

**Interfaces:**
- Produces:
  ```ts
  export interface WorkspaceMembershipInfo {
    platformWorkspaceId: string; workspaceName: string; userId: string;
    email: string | null; displayName: string | null; role: string;
    membershipId: string; membershipUpdatedAt: string;
  }
  export async function listWorkspaceMembershipsForUser(userId: bigint): Promise<WorkspaceMembershipInfo[]>;
  export async function validateWorkspaceMembership(userId: bigint, platformWorkspaceId: bigint): Promise<WorkspaceMembershipInfo | null>;
  ```
- Endpoints (`expose: true, auth: false` — được bảo vệ bằng platform token trong body, giống `/platform/internal/*` hiện có):
  - `POST /platform/internal/list-workspace-memberships` body `{ platformToken }` → `{ memberships: WorkspaceMembershipInfo[] }`
  - `POST /platform/internal/validate-workspace-membership` body `{ platformToken, platformWorkspaceId }` → `WorkspaceMembershipInfo & { valid: boolean }`

- [ ] **Step 1: Test**

```ts
it("lists workspace memberships for the founder", async () => {
  const email = `wm-${Date.now()}@t.io`;
  const res: any = await registerPlatformUser({ email, password: "secret1", workspace_name: "WM Co", client_workspace_creation_id: `wm-${Date.now()}` });
  const [u] = await db.select({ id: schema.users.id }).from(schema.users).where(eq(schema.users.email, email)).limit(1);
  const list = await listWorkspaceMembershipsForUser(u.id);
  expect(list.some(m => m.platformWorkspaceId === res.platform_workspace_id && m.role === "founder")).toBe(true);
});
```

- [ ] **Step 2: Chạy — fail.**

Run: `cd services/cosa && npx vitest run tests/venture-workspace.test.ts -t "lists workspace memberships"`
Expected: FAIL.

- [ ] **Step 3: Implement 2 hàm service** — join `platform_workspace_memberships` × `platform_workspaces` × `users` × `profiles`, lọc theo `userId` (list) hoặc `userId + platformWorkspaceId` (validate). Trả `membershipUpdatedAt = updatedAt.toISOString()`.

- [ ] **Step 4: Implement handler** (`api({ method: "POST", path: "...", expose: true, auth: false }, ...)`) — verify platform token bằng cùng cơ chế các handler `/platform/internal/*` khác dùng (`verifyPlatformToken` / token.service), map `sub` → `userId`, gọi service. Export trong `handlers/api.ts`.

- [ ] **Step 5: Chạy test — pass.** Run: `cd services/cosa && npx vitest run tests/venture-workspace.test.ts`

- [ ] **Step 6: Commit**

```bash
git add services/cosa/services/venture-workspace.service.ts services/cosa/handlers/venture-workspace.handler.ts services/cosa/handlers/api.ts services/cosa/tests/venture-workspace.test.ts
git commit -m "feat(cosa): internal workspace-membership endpoints for identity sync"
```

---

### Task 6: Control Plane — `GET /platform/workspaces/:id/entitlement`

**Files:**
- Modify: `services/cosa/services/venture-workspace.service.ts` (`getWorkspaceEntitlement`)
- Modify: `services/cosa/handlers/venture-workspace.handler.ts`
- Test: `services/cosa/tests/venture-workspace.test.ts`

**Interfaces:**
- Produces:
  ```ts
  export interface WorkspaceEntitlementView { platformWorkspaceId: string; planId: string; effectiveLimits: Record<string, unknown>; effectiveFeatures: Record<string, unknown>; snapshotSignature: string | null; }
  export async function getWorkspaceEntitlement(platformWorkspaceId: bigint): Promise<WorkspaceEntitlementView>;
  ```
- Endpoint `GET /platform/workspaces/:id/entitlement` (`expose: true, auth: true`) — chỉ owner/member của workspace đó đọc được (permissionDenied nếu không phải).

- [ ] **Step 1: Test** — provision workspace → gọi service → `effectiveFeatures.finance === false`, `effectiveLimits.max_projects === 1`.

- [ ] **Step 2: Chạy — fail.**

- [ ] **Step 3: Implement** — `getWorkspaceEntitlement` select từ `workspace_entitlements`; handler resolve `auth` principal → check membership qua `validateWorkspaceMembership` → `notFound` nếu workspace không tồn tại, `permissionDenied` nếu không là member.

- [ ] **Step 4: Chạy test — pass.**

- [ ] **Step 5: Commit** `feat(cosa): workspace entitlement read endpoint`

---

### Task 7: Company Service — link column `platform_workspace_id` + `venture_stage_entered_at`

**Files:**
- Modify: `services/company/shared/db/schema/identity.ts:5-13`
- Create: `services/company/identity/migrations/<next>_platform_workspace_link.up.sql` / `.down.sql` (số kế tiếp trong `services/company/identity/migrations/`)

**Interfaces:**
- Produces: `identityWorkspaces` thêm `platformWorkspaceId: text("platform_workspace_id").unique()` (nullable) và `ventureStageEnteredAt: timestamp("venture_stage_entered_at", { withTimezone: true })`.

- [ ] **Step 1: Migration up**

```sql
ALTER TABLE core.workspaces
  ADD COLUMN IF NOT EXISTS platform_workspace_id TEXT,
  ADD COLUMN IF NOT EXISTS venture_stage_entered_at TIMESTAMPTZ;
CREATE UNIQUE INDEX IF NOT EXISTS uq_workspaces_platform_workspace_id
  ON core.workspaces(platform_workspace_id) WHERE platform_workspace_id IS NOT NULL;
```

`.down.sql`: `DROP INDEX IF EXISTS core.uq_workspaces_platform_workspace_id; ALTER TABLE core.workspaces DROP COLUMN IF EXISTS platform_workspace_id; ALTER TABLE core.workspaces DROP COLUMN IF EXISTS venture_stage_entered_at;`

- [ ] **Step 2: Drizzle** — thêm 2 field vào `identityWorkspaces` (giữ `companyStage`, `platformCompanyId` nguyên).

- [ ] **Step 3: Migrate + rollback test.**

Run: `cd services/company && node scripts/migrate.mjs && cd ../.. && node scripts/test-migration-rollback.mjs`

- [ ] **Step 4: Commit** `feat(company): add platform_workspace_id + venture_stage_entered_at to core.workspaces`

---

### Task 8: Company Service — sync theo `platformWorkspaceId` + tạo `venture_profiles`

**Files:**
- Modify: `services/company/shared/db/schema/strategy.ts` (thêm `ventureProfiles`)
- Create: `services/company/operations/migrations/<next>_venture_stage_and_profile.up.sql` / `.down.sql`
- Modify: `services/company/identity/services/platform.client.ts` (thêm `listPlatformWorkspaceMemberships`, `validatePlatformWorkspaceMembership`)
- Modify: `services/company/identity/services/sync.service.ts` (nhánh workspace-keyed)
- Test: `services/company/identity/tests/sync.test.ts`

**Interfaces:**
- Consumes: Control Plane endpoints từ Task 5.
- Produces: `ventureProfiles { id, workspaceId (unique), problemStatement: text, targetCustomer: text, industry: text, geography: text, currency: text, timezone: text, founderGoal: varchar, initialRunwayMonths: integer, stageEnteredAt: timestamp, createdAt, updatedAt }`. Sau sync, mỗi `core.workspaces` mới có `platformWorkspaceId` set + 1 `venture_profiles` row (fields rỗng, chờ onboarding điền).

- [ ] **Step 1: Migration** — `CREATE TABLE IF NOT EXISTS strategy.venture_profiles (...)` với `workspace_id BIGINT NOT NULL UNIQUE REFERENCES ... ` (dùng schema `strategy`; xem `strategySchema` trong `operations.ts`). (Bảng `venture_stage_transitions` tạo ở Task 9 — có thể gộp cùng file migration.)

- [ ] **Step 2: Drizzle** — `ventureProfiles = strategySchema.table("venture_profiles", { ... })`.

- [ ] **Step 3: `platform.client.ts`** — thêm 2 hàm mirror `listPlatformMemberships` / `validatePlatformMembership` nhưng gọi `/platform/internal/list-workspace-memberships` và `/platform/internal/validate-workspace-membership`, trả `platformWorkspaceId`, `workspaceName` thay cho `companyId`, `companyName`. Giữ fail-closed (`APIError.unavailable`).

- [ ] **Step 4: Test sync**

```ts
it("syncs a platform workspace into core.workspaces keyed by platform_workspace_id + creates venture_profile", async () => {
  // seed: mock listPlatformWorkspaceMemberships để trả 1 workspace membership founder
  const result = await syncFromPlatformService({ platform_access_token: TEST_PLATFORM_TOKEN });
  const [ws] = await db.select().from(schema.identityWorkspaces)
    .where(eq(schema.identityWorkspaces.platformWorkspaceId, TEST_PW_ID)).limit(1);
  expect(ws).toBeTruthy();
  const [vp] = await db.select().from(schema.ventureProfiles)
    .where(eq(schema.ventureProfiles.workspaceId, ws.id)).limit(1);
  expect(vp).toBeTruthy();
});
```

- [ ] **Step 5: Chạy — fail.**

- [ ] **Step 6: Sửa `sync.service.ts`** — thêm nhánh: nếu `listPlatformWorkspaceMemberships` trả kết quả, upsert `identityWorkspaces` `onConflictDoUpdate({ target: identityWorkspaces.platformWorkspaceId, ... })` (giữ nhánh `platformCompanyId` cũ cho legacy), upsert `identityWorkspaceMemberships`, và insert `venture_profiles` `onConflictDoNothing` theo `workspaceId`. Cập nhật `platform_workspace_sync_log` trên Control Plane qua một internal callback endpoint `POST /platform/internal/mark-workspace-synced { platformWorkspaceId }` (thêm nhỏ vào Task 5 handler) — hoặc để relay job đánh dấu; chọn callback để đơn giản.

- [ ] **Step 7: Chạy test — pass.** Run: `cd services/company && npx vitest run identity/tests/sync.test.ts`

- [ ] **Step 8: Commit** `feat(company): identity sync keyed by platform_workspace_id + venture_profile bootstrap`

---

### Task 9: Company Service — `venture_stage_transitions` journal + event constants

**Files:**
- Modify: `services/company/shared/db/schema/strategy.ts`
- Modify: `services/company/operations/migrations/<next>_venture_stage_and_profile.up.sql` (thêm bảng)
- Modify: `services/company/shared/events.ts` (thêm 2 constant)
- Create: `services/company/operations/strategy/events/venture-stage-events.ts`

**Interfaces:**
- Produces:
  ```ts
  export const ventureStageTransitions = strategySchema.table("venture_stage_transitions", {
    id: bigint("id",{mode:"bigint"}).primaryKey(),
    workspaceId: bigint("workspace_id",{mode:"bigint"}).notNull(),
    fromStage: varchar("from_stage",{length:50}).notNull(),
    toStage: varchar("to_stage",{length:50}).notNull(),
    reason: text("reason").notNull(),
    actorMemberId: bigint("actor_member_id",{mode:"bigint"}),
    overrideFlag: boolean("override_flag").default(false).notNull(),
    decidedAt: timestamp("decided_at",{withTimezone:true}).defaultNow().notNull(),
    createdAt: timestamp("created_at",{withTimezone:true}).defaultNow().notNull(),
  });
  ```
  `events.ts`: `export const VENTURE_STAGE_CHANGED = "venture.stage.changed";` `export const PROJECT_PHASE_CHANGED = "project.phase.changed";`
  `venture-stage-events.ts`: `export function buildVentureStageChangedEvent(input: { workspaceId: string; fromStage: string; toStage: string; reason: string; overrideFlag: boolean; actorMemberId: string | null; }): OutboxEventInput` — theo shape mà `appendOutboxEvent` nhận (xem `operations/services/task.service.ts` + `buildTaskCreatedEvent`).

- [ ] **Step 1: Migration** `CREATE TABLE IF NOT EXISTS strategy.venture_stage_transitions (...)` + index `(workspace_id, decided_at)`.
- [ ] **Step 2: Drizzle + events.ts + event builder.** Đọc `buildTaskCreatedEvent` để khớp envelope (`aggregate_type`, `schema_version`, `occurred_at`, `envelope`, `payload_hash`, `classification`).
- [ ] **Step 3: Migrate.** Run: `cd services/company && node scripts/migrate.mjs`
- [ ] **Step 4: Commit** `feat(company): venture_stage_transitions journal + outbox event builder`

---

### Task 10: Company Service — `stage-lifecycle.service.ts` (assess + transition)

**Files:**
- Create: `services/company/operations/strategy/services/stage-lifecycle.service.ts`
- Test: `services/company/operations/tests/venture-stage-lifecycle.test.ts`

**Interfaces:**
- Consumes: `identityWorkspaces` (đọc `companyStage`), `stagePolicies` (workspace-keyed, đã có), `evidence` / `gateEvaluations` (đã có), `ventureStageTransitions` (Task 9), `appendOutboxEvent`, `buildVentureStageChangedEvent`.
- Produces:
  ```ts
  export const VENTURE_STAGES = ["S0_GENESIS","S1_PROBLEM_VALIDATION","S2_SOLUTION_VALIDATION","S3_MVP_BUILD","S4_PRODUCT_MARKET_FIT","S5_SCALE"] as const;
  export type VentureStage = typeof VENTURE_STAGES[number];
  export interface AssessResult { currentStage: VentureStage; recommendedStage: VentureStage; gatePassed: boolean; blockers: string[]; }
  export async function assessVentureStage(workspaceId: bigint): Promise<AssessResult>;
  export interface TransitionParams { workspaceId: bigint; toStage: VentureStage; reason: string; actorMemberId?: bigint; override?: boolean; }
  export interface TransitionResult { fromStage: VentureStage; toStage: VentureStage; enteredAt: string; overrideApplied: boolean; }
  export async function transitionVentureStage(p: TransitionParams): Promise<TransitionResult>;  // throws APIError.failedPrecondition (409) khi gate fail + !override
  ```
- Quy tắc `transitionVentureStage`: đọc `currentStage` từ DB (KHÔNG nhận `fromStage` từ client); chỉ cho phép tiến 1 bậc hoặc lùi bất kỳ (lùi bắt buộc `reason`); nếu tiến >1 bậc → `APIError.invalidArgument`; check gate qua `assessVentureStage`; nếu `!gatePassed && !override` → `APIError.failedPrecondition("gate chưa đạt", {...blockers})`; ngược lại: `db.transaction` = update `identityWorkspaces.companyStage` + `ventureStageEnteredAt=now()` + insert `ventureStageTransitions` + `appendOutboxEvent(tx, buildVentureStageChangedEvent(...))`.

- [ ] **Step 1: Test**

```ts
// services/company/operations/tests/venture-stage-lifecycle.test.ts
import { describe, it, expect } from "vitest";
import { db, schema } from "../models/db";
import { eq } from "drizzle-orm";
import { assessVentureStage, transitionVentureStage } from "../strategy/services/stage-lifecycle.service";
// helper tạo workspace test — dùng _helpers.ts hiện có

describe("venture stage lifecycle", () => {
  it("assess does not mutate workspace stage", async () => {
    const wsId = await createTestWorkspace(); // S0_GENESIS
    await assessVentureStage(wsId);
    const [ws] = await db.select().from(schema.identityWorkspaces).where(eq(schema.identityWorkspaces.id, wsId));
    expect(ws.companyStage).toBe("S0_GENESIS");
  });

  it("S0 -> S1 succeeds when no gate policy configured; writes journal + outbox", async () => {
    const wsId = await createTestWorkspace();
    const r = await transitionVentureStage({ workspaceId: wsId, toStage: "S1_PROBLEM_VALIDATION", reason: "problem hypothesis + customer defined" });
    expect(r.toStage).toBe("S1_PROBLEM_VALIDATION");
    const [ws] = await db.select().from(schema.identityWorkspaces).where(eq(schema.identityWorkspaces.id, wsId));
    expect(ws.companyStage).toBe("S1_PROBLEM_VALIDATION");
    const jr = await db.select().from(schema.ventureStageTransitions).where(eq(schema.ventureStageTransitions.workspaceId, wsId));
    expect(jr.length).toBe(1);
    const ob = await db.select().from(schema.eventOutbox).where(eq(schema.eventOutbox.aggregateId, wsId.toString()));
    expect(ob.some(e => e.eventType === "venture.stage.changed")).toBe(true);
  });

  it("S1 -> S3 (skip) is rejected with invalidArgument", async () => {
    const wsId = await createTestWorkspace();
    await transitionVentureStage({ workspaceId: wsId, toStage: "S1_PROBLEM_VALIDATION", reason: "x" });
    await expect(transitionVentureStage({ workspaceId: wsId, toStage: "S3_MVP_BUILD", reason: "y" }))
      .rejects.toThrow(/1 bậc|invalid/i);
  });

  it("gate fail without override throws failedPrecondition; with override writes overrideFlag=true", async () => {
    const wsId = await createTestWorkspace();
    await seedBlockingStagePolicy(wsId, "S1_PROBLEM_VALIDATION"); // minimumEvidenceScore cao
    await expect(transitionVentureStage({ workspaceId: wsId, toStage: "S1_PROBLEM_VALIDATION", reason: "z" }))
      .rejects.toMatchObject({ code: "failed_precondition" });
    const ok = await transitionVentureStage({ workspaceId: wsId, toStage: "S1_PROBLEM_VALIDATION", reason: "founder override: thị trường khẩn", override: true });
    expect(ok.overrideApplied).toBe(true);
  });
});
```

- [ ] **Step 2: Chạy — fail.** Run: `cd services/company && npx vitest run operations/tests/venture-stage-lifecycle.test.ts`
- [ ] **Step 3: Implement** theo Interfaces ở trên. `assessVentureStage`: load `stagePolicies` cho `stageKey = nextStage`, tính `evidenceScore` từ `evidence` của workspace (tổng `strength*confidence` hoặc theo cách `gate-evaluation.service.ts` đang tính — tái dùng helper nếu có), so với `minimumEvidenceScore`, so `requirements`. `gatePassed = true` nếu không có policy cho stage đó.
- [ ] **Step 4: Chạy test — pass.**
- [ ] **Step 5: Commit** `feat(company): venture stage lifecycle service (assess + transactional transition)`

---

### Task 11: Company Service — venture-stage handlers

**Files:**
- Create: `services/company/operations/strategy/handlers/venture-stage.handler.ts`
- Modify: `services/company/operations/api.ts` (barrel)
- Rename: `services/company/operations/strategy/handlers/stage-transition.handler.ts` → `stage-transition-config.handler.ts` (giữ nguyên nội dung + route; chỉ đổi tên file + cập nhật import ở `api.ts`)
- Test: `services/company/operations/tests/venture-stage-lifecycle.test.ts` (thêm HTTP-level nếu test infra hỗ trợ; nếu không, giữ ở service-level)

**Interfaces:**
- Endpoints (`expose: true`, `auth: true`, resolve workspace qua `requireWorkspaceAccess` / `tenant-context.service.ts` hiện có):
  - `POST /operations/strategy/venture-stage/assess` body `{ workspaceId }` → `AssessResult`
  - `POST /operations/strategy/venture-stage/transition` body `{ workspaceId, toStage, reason, override? }` → `TransitionResult` | 409
  - `GET /operations/strategy/venture-stage/transitions?workspaceId=` → `{ transitions: VentureStageTransitionRow[] }`

- [ ] **Step 1:** Viết handler — parse input, gọi `requireWorkspaceAccess(auth, workspaceId)`, gọi service, map `APIError`. KHÔNG đọc/ghi DB trực tiếp trong handler.
- [ ] **Step 2:** Đổi tên file config handler + sửa import trong `operations/api.ts`. Chạy `cd services/company && npx tsc --noEmit` (hoặc lệnh typecheck của service) — expected: no errors.
- [ ] **Step 3:** Chạy `npx vitest run operations/` — regression pass.
- [ ] **Step 4: Commit** `feat(company): venture-stage assess/transition/list endpoints; rename stage-transition config handler`

---

### Task 12: Company Service — `getWorkspaceRecord` expose venture fields

**Files:**
- Modify: `services/company/identity/services/workspace.service.ts:40-55`
- Test: `services/company/identity/tests/workspace.test.ts`

**Interfaces:**
- Produces: response của `GET /identity/workspaces/:id` thêm `ventureStage: string` (alias của `companyStage`), `ventureStageEnteredAt: string | null`, `platformWorkspaceId: string | null`, `legalStatus: "NOT_DECLARED"` (hằng số cho tới Release B).

- [ ] **Step 1: Test** — sửa/ thêm assertion trong `workspace.test.ts`: sau khi tạo workspace, `getWorkspaceRecord` trả `ventureStage === "S0_GENESIS"` và `legalStatus === "NOT_DECLARED"`.
- [ ] **Step 2: Chạy — fail.**
- [ ] **Step 3: Implement** — thêm 4 field vào object trả về; `ventureStage: row.companyStage`, `legalStatus: "NOT_DECLARED"`.
- [ ] **Step 4: Chạy — pass.** `cd services/company && npx vitest run identity/tests/workspace.test.ts`
- [ ] **Step 5: Commit** `feat(company): expose ventureStage + legalStatus on workspace record`

---

### Task 13: Company Service — persist `projects.phase` từ `assessProjectStage` khi gate pass

**Files:**
- Modify: caller của `assessProjectStage` — tìm trong `services/company/operations/strategy/` (grep `assessProjectStage`; ứng viên: `next-best-action.handler.ts`, hoặc `gate-evaluation.service.ts` sau khi `result === "passed"`)
- Modify: `services/company/operations/strategy/services/gate-evaluation.service.ts` (nơi ghi `gateEvaluations` khi `passed`)
- Test: `services/company/operations/tests/` (file gate-evaluation test hiện có, thêm case)

**Interfaces:**
- Produces: khi một `gate_evaluation` chuyển `result = "passed"`, trong cùng transaction: `UPDATE strategy.projects SET phase = <recommendedStage from assessProjectStage> WHERE id = projectId` + `appendOutboxEvent(tx, buildProjectPhaseChangedEvent({ projectId, workspaceId, fromPhase, toPhase }))`. Event type `project.phase.changed` (Task 9).

- [ ] **Step 1: Test** — tạo project (phase `"PLANNING"`), seed evidence đủ, chạy gate evaluation → `projects.phase` chuyển sang stage khuyến nghị; outbox có `project.phase.changed`.
- [ ] **Step 2: Chạy — fail.**
- [ ] **Step 3: Implement** — thêm builder `buildProjectPhaseChangedEvent` vào `venture-stage-events.ts`; trong `gate-evaluation.service.ts` sau khi insert `gateEvaluations` với `result="passed"`, gọi `assessProjectStage(currentPhase, evidenceList, passedGates)` và persist + emit trong cùng `tx`.
- [ ] **Step 4: Chạy — pass.**
- [ ] **Step 5: Commit** `feat(company): persist project phase on gate pass + emit project.phase.changed`

---

### Task 14: Agent — sửa `finance_write.py` (gỡ payout, fix transaction contract)

**Files:**
- Modify: `apps/cosa/capabilities/finance_write.py`
- Modify: `apps/cosa/capabilities/__init__.py` (bỏ export `FINANCE_PAYOUT_EXECUTE_SPEC`, `create_finance_payout_execute_handler`)
- Modify: nơi đăng ký capability (grep `FINANCE_PAYOUT_EXECUTE_SPEC` — ứng viên `apps/cosa/composition/agent_plane.py` hoặc `apps/cosa/capabilities/registry`*)
- Test: `tests/apps/cosa/test_finance_write.py`

**Interfaces:**
- Produces: `FINANCE_TRANSACTION_RECORD_SPEC.input_schema.required = ["workspace_id","transaction_date","direction","amount","description"]`; handler POST `/finance-legal/transactions` với body `{ workspaceId, transactionDate, direction, amount, description, category? }`. `direction ∈ {"IN","OUT"}`. Không còn `account_id`/`type`. Không còn fallback `workspace_id or 1` — thiếu `workspace_id` → `raise ValueError("workspace_id required")`.
- Removed: `FINANCE_PAYOUT_EXECUTE_SPEC`, `create_finance_payout_execute_handler`, tham chiếu `/finance-legal/payouts`.

- [ ] **Step 1: Viết test thất bại**

```python
# tests/apps/cosa/test_finance_write.py
import pytest
from apps.cosa.capabilities import finance_write

def test_payout_spec_is_removed():
    assert not hasattr(finance_write, "FINANCE_PAYOUT_EXECUTE_SPEC")
    assert not hasattr(finance_write, "create_finance_payout_execute_handler")

def test_transaction_record_spec_matches_backend_contract():
    spec = finance_write.FINANCE_TRANSACTION_RECORD_SPEC
    assert set(spec.input_schema["required"]) == {"workspace_id", "transaction_date", "direction", "amount", "description"}
    props = spec.input_schema["properties"]
    assert props["direction"]["enum"] == ["IN", "OUT"]
    assert "account_id" not in props and "type" not in props

@pytest.mark.asyncio
async def test_transaction_handler_builds_backend_body(monkeypatch):
    captured = {}
    class FakeClient:
        async def post(self, path, json):
            captured["path"] = path; captured["body"] = json
            return {"transaction_id": "t1", "status": "recorded"}
    handler = finance_write.create_finance_transaction_record_handler(FakeClient())
    await handler(
        {"workspace_id": 42, "transaction_date": "2026-08-29", "direction": "OUT", "amount": 12.5, "description": "cà phê"},
        {},
    )
    assert captured["path"] == "/finance-legal/transactions"
    assert captured["body"] == {
        "workspaceId": 42, "transactionDate": "2026-08-29", "direction": "OUT",
        "amount": 12.5, "description": "cà phê",
    }

@pytest.mark.asyncio
async def test_transaction_handler_rejects_missing_workspace():
    handler = finance_write.create_finance_transaction_record_handler(object())
    with pytest.raises(ValueError):
        await handler({"transaction_date": "2026-08-29", "direction": "IN", "amount": 1, "description": "x"}, {})
```

- [ ] **Step 2: Chạy — fail.**

Run: `PYTHONPATH=$(pwd) .venv/bin/python -m pytest tests/apps/cosa/test_finance_write.py -q`
Expected: FAIL.

- [ ] **Step 3: Sửa `finance_write.py`** — xóa block `FINANCE_PAYOUT_EXECUTE_SPEC` (L17-41) + `create_finance_payout_execute_handler` (L68-84); cập nhật `__all__`. Đổi `FINANCE_TRANSACTION_RECORD_SPEC`:

```python
FINANCE_TRANSACTION_RECORD_SPEC = CapabilitySpec(
    id="finance.transaction.record",
    description="Ghi nhận giao dịch tài chính vào services/company/finance-legal (đúng hợp đồng backend).",
    risk=CapabilityRisk.MEDIUM,
    input_schema={
        "type": "object",
        "required": ["workspace_id", "transaction_date", "direction", "amount", "description"],
        "properties": {
            "workspace_id": {"type": "integer"},
            "transaction_date": {"type": "string", "format": "date"},
            "direction": {"type": "string", "enum": ["IN", "OUT"]},
            "amount": {"type": "number"},
            "description": {"type": "string"},
            "category": {"type": "string"},
        },
    },
    output_schema={
        "type": "object",
        "properties": {"transaction_id": {"type": "string"}, "status": {"type": "string"}},
    },
)

def create_finance_transaction_record_handler(client: CompanyServiceClient | None = None):
    svc_client = client or CompanyServiceClient()
    async def handle_transaction(payload: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
        workspace_id = payload.get("workspace_id") or ctx.get("workspace_id")
        if workspace_id is None:
            raise ValueError("workspace_id required")  # fail-closed, không fallback về 1
        body = {
            "workspaceId": workspace_id,
            "transactionDate": payload["transaction_date"],
            "direction": payload["direction"],
            "amount": payload["amount"],
            "description": payload["description"],
        }
        if payload.get("category"):
            body["category"] = payload["category"]
        return await svc_client.post("/finance-legal/transactions", json=body)
    return handle_transaction
```

- [ ] **Step 4: Gỡ đăng ký payout** — grep `finance.payout.execute` / `FINANCE_PAYOUT_EXECUTE_SPEC` toàn repo; xóa mọi nơi register nó vào registry/composition. Chạy `make boundary-check`.

- [ ] **Step 5: Chạy test — pass.**

Run: `PYTHONPATH=$(pwd) .venv/bin/python -m pytest tests/apps/cosa/test_finance_write.py -q` → PASS
Run: `make apps-cosa-test` → PASS (không regression).

- [ ] **Step 6: Commit**

```bash
git add apps/cosa/capabilities/finance_write.py apps/cosa/capabilities/__init__.py tests/apps/cosa/test_finance_write.py
git commit -m "fix(cosa): remove finance.payout.execute; align finance.transaction.record with backend contract"
```

---

### Task 15: Flutter — `finance_service.dart` cleanup

**Files:**
- Modify: `frontend/lib/modules/finance/services/finance_service.dart`
- Test: `frontend/test/modules/finance/finance_service_test.dart`

**Interfaces:**
- Produces: mọi method nhận `workspaceId` bắt buộc (throw `StateError` nếu null, không fallback `'1'`). Xóa `activateProfile()` và `previewRegimeTransition()` (mock). `createProfile` gửi key `mode` (không `regime`). Chỉ gọi các endpoint tồn tại: `/finance-legal/snapshots/latest`, `/finance-legal/transactions` (GET/POST), `/finance-legal/transactions/:id/approve`, `/finance-legal/accounting-profiles/by-workspace/:id`, `/finance-legal/accounting-profiles` (POST), `/finance-legal/accounting-periods` (+`/:id/close`), `/finance-legal/exceptions` (POST), `/finance-legal/workspaces/:id/fiscal-profiles`, `/finance-legal/fiscal-profiles` (POST). Các method gọi endpoint không tồn tại (`/finance-legal/books/templates`, `/finance-legal/reports`, `/finance-legal/documents` GET-list) → xóa hoặc đánh dấu `@Deprecated` + throw `UnimplementedError("chưa có backend — Release C")`.

- [ ] **Step 1: Test** — `finance_service_test.dart`: gọi `getTransactions(workspaceId: null)` → expect throw; `createProfile(...)` → captured request body chứa key `mode`, không `regime`; `activateProfile` không còn tồn tại (compile check).
- [ ] **Step 2: Chạy — fail.** Run: `cd frontend && flutter test test/modules/finance/finance_service_test.dart`
- [ ] **Step 3: Implement** — bỏ `?? '1'` mọi nơi; `required String workspaceId` param; xóa 2 method mock; đổi `'regime'` → `'mode'`; xử lý các endpoint thiếu như trên.
- [ ] **Step 4: Chạy — pass.** + `cd frontend && flutter analyze` (no new issues).
- [ ] **Step 5: Commit** `fix(frontend): finance_service — drop workspace '1' fallback, mocks, regime→mode`

---

### Task 16: Flutter — tắt route TT58 giả + bỏ hard-code legal

**Files:**
- Modify: `frontend/lib/modules/finance/services/finance_tt58_service.dart`
- Modify: `frontend/lib/modules/legal/services/legal_service.dart`
- Test: `frontend/test/modules/legal/legal_service_test.dart`

**Interfaces:**
- `finance_tt58_service.dart`: mọi method gọi `/workspaces/{id}/finance/tt58/...` → throw `UnimplementedError("TT58 backend chưa có — Release C")` (giữ chữ ký method để UI không vỡ compile), hoặc feature-flag ẩn toàn màn.
- `legal_service.dart`: `getLegalSources()` → gọi `GET /finance-legal/regulation-sources` nếu feature `legal` bật; nếu chưa có endpoint (pre-Release B) → trả `[]` **và** UI hiển thị trạng thái "đang cập nhật nguồn" (không hiển thị danh sách hard-code). Xóa list hard-code L83-89 (bao gồm `"Thông tư 58/2024/TT-BTC"`).

- [ ] **Step 1: Test** — `getLegalSources()` không trả string `"Thông tư 58/2024/TT-BTC"`; khi HTTP 404 → trả `[]` không throw.
- [ ] **Step 2: Chạy — fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Chạy — pass** + `flutter analyze`.
- [ ] **Step 5: Commit** `fix(frontend): disable fake TT58 routes; remove hard-coded legal sources`

---

### Task 17: Flutter — entitlement gating + onboarding S0

**Files:**
- Create/Modify: `frontend/lib/shared/providers/entitlement_provider.dart`
- Modify: các module `finance`, `legal` (và `agents`/`workflows` nếu cần) — bọc entry bằng `context.watch<EntitlementProvider>().hasFeature('finance')`
- Modify: `frontend/lib/modules/auth/…` hoặc `workspace_picker/…` — thêm onboarding S0 5 bước (spec §6.1)
- Test: `frontend/test/modules/onboarding/onboarding_flow_test.dart`, `frontend/test/shared/entitlement_provider_test.dart`

**Interfaces:**
- `EntitlementProvider`: `Future<void> load(String platformWorkspaceId)` gọi `GET /platform/workspaces/:id/entitlement`; `bool hasFeature(String key)` (default `false` khi chưa load / lỗi — fail-closed, KHÔNG "hiện tất cả"); `Map<String,dynamic> limits`.
- Onboarding S0: 5 màn tuần tự — (1) "Bạn đang muốn giải quyết điều gì?" free text; (2) "Ai đang gặp vấn đề đó?" (hiển thị AI tách problem/customer — Release B mới có AI thật, ở A chỉ lưu raw); (3) "Bạn muốn đạt điều gì trong 12 tuần?" chọn `EXPERIMENT|SIDE_INCOME|SERVICE|PRODUCT|LEARN`; (4) placeholder "AI đề xuất bản đồ khởi đầu" (Release B); (5) "Tạo Venture Workspace Free" → gọi `POST /platform/auth/register` (hoặc endpoint tạo workspace nếu user đã đăng nhập) với `workspace_name` + `client_workspace_creation_id` (UUID sinh client). Sau tạo: gọi `PATCH /strategy/venture-profile/:workspaceId` lưu `problem_statement`, `founder_goal` (endpoint này thuộc Release B — ở A, lưu tạm local hoặc thêm endpoint tối thiểu `PATCH` chỉ 2 field).

- [ ] **Step 1: Test** — `EntitlementProvider.hasFeature('finance')` == false trước khi load; == theo response sau load; onboarding flow: hoàn tất 5 bước → gọi register với `workspace_name` đúng, `client_workspace_creation_id` không đổi khi user bấm "Tạo" 2 lần (idempotent).
- [ ] **Step 2: Chạy — fail.**
- [ ] **Step 3: Implement.** (Nếu cần endpoint `PATCH /strategy/venture-profile/:id` tối thiểu cho bước 5, thêm 1 task nhỏ ở Company Service: handler + service update 2 cột `problem_statement`, `founder_goal` trên `venture_profiles`.)
- [ ] **Step 4: Chạy — pass** + `flutter analyze` + `flutter test`.
- [ ] **Step 5: Commit** `feat(frontend): entitlement-gated modules + Level 0 venture onboarding`

---

### Task 18: Backfill `companies` → `platform_workspaces` + link

**Files:**
- Create: `services/cosa/migrations/20_backfill_platform_workspaces.up.sql` / `.down.sql`
- Create: `services/cosa/scripts/backfill-platform-workspaces.mjs` (idempotent, báo cáo số record) — hoặc làm hẳn trong SQL migration nếu đủ đơn giản
- Test: `services/cosa/tests/venture-workspace.test.ts` (case backfill)

**Interfaces:**
- Produces: mỗi `cosa.companies` chưa có `platform_workspace` tương ứng → tạo `platform_workspaces(workspace_name = companies.name, owner_user_id = companies.created_by)` + `platform_workspace_memberships` (map từ `company_memberships`) + `workspace_licenses` (từ `licenses` của company đó, hoặc `free`) + `workspace_entitlements` (từ `company_entitlements`, hoặc snapshot plan). Idempotency key `client_creation_id = 'backfill:company:' || companies.id` trong `platform_workspace_sync_log`. KHÔNG suy đoán legal status. KHÔNG phát trigger AI.
- Company side: script/endpoint set `core.workspaces.platform_workspace_id` cho workspace có `platform_company_id` khớp company vừa backfill (giữ `platform_company_id` nguyên).

- [ ] **Step 1: Test** — seed 1 company + membership + license `starter`; chạy backfill; assert có `platform_workspaces` + `workspace_licenses.plan_id='starter'` + `platform_workspace_sync_log.client_creation_id='backfill:company:<id>'`; chạy backfill lần 2 → không tạo trùng.
- [ ] **Step 2: Chạy — fail.**
- [ ] **Step 3: Implement** SQL/script.
- [ ] **Step 4: Chạy — pass** + rollback test.
- [ ] **Step 5: Commit** `feat(cosa): idempotent backfill of legacy companies into platform_workspaces`

---

### Task 19: Release A — integration & acceptance pass

**Files:**
- Create: `services/company/tests/e2e/provision-sync-flow.test.ts` (hoặc vị trí e2e hiện có)
- Modify: `Makefile` nếu cần target gom

- [ ] **Step 1:** Viết e2e: register (`workspace_name`) → poll `GET /identity/workspaces/:id` tới khi `platformWorkspaceId` set → `ventureStage="S0_GENESIS"`, `legalStatus="NOT_DECLARED"` → `assess` không đổi stage → `transition` S0→S1 pass + journal + outbox → `transition` S1→S3 reject → `GET /platform/workspaces/:pwid/entitlement` `finance=false`.
- [ ] **Step 2:** Tenant isolation: user B không đọc được entitlement / workspace của user A (`permissionDenied`).
- [ ] **Step 3:** Idempotency: register lại cùng `client_workspace_creation_id` → cùng `platform_workspace_id`, `workspace_licenses` vẫn 1 dòng.
- [ ] **Step 4:** Chạy toàn bộ gate:

```
make typecheck-py
make boundary-check
make tenancy-check
cd services/cosa && npx vitest run
cd services/company && npx vitest run
make apps-cosa-test
cd frontend && flutter analyze && flutter test
```

Expected: tất cả PASS. (Nếu phát hiện "task event typecheck error" spec nhắc — fix tại đây.)

- [ ] **Step 5: Commit** `test(cosa): Release A end-to-end provision/stage/entitlement acceptance`

---

## Phase 2 — Release B: Evidence, Legal Catalog & Registration Readiness (milestone spec)

> **Chạy `superpowers:writing-plans` lại cho Phase này trước khi execute.**

**Mục tiêu:** COSA biến tư vấn AI thành đề xuất có nguồn (regulation catalog versioned + applicability), biết lúc nào chuyển chuyên gia; tách legal status khỏi stage.

**Bảng mới (`services/company`, schema `finance-legal.ts` + `strategy.ts`):**
- `legal.regulation_sources` (source_name, issuer, number, url, content_hash, status ∈ `CURRENT_LAW|POLICY_WATCH|PROFESSIONAL_REVIEW`).
- `legal.regulation_versions` (regulation_source_id, version, effective_from, effective_to, superseded_by_id).
- `legal.applicability_rules` (regulation_version_id, predicate JSONB {entity_status, fiscal_year_min/max, condition_field, condition_value}, obligation_template_id).
- `legal.legal_obligation_templates` (regulation_version_id, title, description, typical_due_offset_days).
- `legal.legal_obligation_instances` (workspace_id, legal_entity_profile_id, template_id | manual, source ∈ `REGULATION_TEMPLATE|USER_CREATED|AI_PROPOSAL`, due_date, status, evidence_artifact_id, applicability_assessed_at, owner_member_id, review_status).
- `legal.legal_entity_profiles` (workspace_id, platform_company_id nullable, entity_type, status ∈ 5 giá trị legal, registration_number, tax_id, verified_by_member_id, verified_at).
- `strategy.decision_records` mở rộng (hoặc bảng workspace-scoped mới): `regulation_refs[]`, `confidence`, `assumptions`, `alternatives`, `policy_version`, `ai_prompt_version`, `founder_decision ∈ accepted|rejected|deferred`.

**Seed (`services/cosa` hoặc `services/company` migration):** `58/2026/TT-BTC` (effective 2026-07-01, `CURRENT_LAW`), `86/NQ-CP` (2026-04-05, `POLICY_WATCH`) — URL/hash theo spec §3.

**Endpoints:** `GET /finance-legal/regulation-sources`; `POST /finance-legal/regulation-versions`; `GET /legal/obligation-templates`; `POST/GET /legal/legal-entity-profiles` + `/:id/verify` (approval, không auto-verify); `GET /legal/applicable-obligations` (read-only assess, không persist); `POST/PATCH /legal/legal-obligation-instances`; `GET/PATCH /strategy/venture-profile/:workspaceId`.

**Migrate cũ:** `legal_checklist_items` / `legal_obligations` → `legal_obligation_instances` với `source=USER_CREATED`, `regulation_version_id=NULL`.

**Capabilities (`apps/cosa/capabilities/`):** `legal.applicability.assess` (LOW/L0), `legal.obligation.create_draft` (MEDIUM/L1), `venture.profile.read` (LOW/L0), `venture.profile.propose_update` (LOW/L0), `strategy.discovery.read` (LOW/L0), `strategy.evidence.create_draft` (LOW/L1). Output kèm nhãn `insight|proposal|requires_professional_review` + nguồn + giả định.

**Flutter:** `legal_service.dart` đọc catalog; UI citation/assumption/uncertainty; màn legal entity profile; registration readiness checklist ở S3/S4.

**Nghiệm thu (spec §13):** giải thích được vì sao 1 checklist xuất hiện, nguồn nào hiệu lực, dữ kiện nào thiếu; không kết luận điều kiện pháp lý khi thiếu dữ kiện; decision record lưu `regulation_refs` + `evidence_snapshot`; source hết hiệu lực không sinh obligation mới.

---

## Phase 3 — Release C: Finance Ingestion & TT58 Foundation (milestone spec)

> **Chạy `superpowers:writing-plans` lại. Harness-P0 (context propagation + policy floor + service identity + gateway-only workflow) PHẢI xanh trước khi bật capability write finance ở production.**

**Bảng mới (`services/company`, `finance-legal.ts`):** `bank_connections` (provider ∈ `cas|manual`, consent_state, secret_ref, scopes, account_links, grant_expires_at, last_synced_at, sync_status); `ingestion_events` (provider_event_id, received_at, raw_payload_ref, checksum, status) — idempotent trước khi tạo transaction; `bank_transactions` (bank_connection_id, provider_account_id, external_transaction_id, posted_date, amount DECIMAL, currency, counterparty, description, category, mapped_status, provenance) **UNIQUE(bank_connection_id, external_transaction_id)**; `accounting_documents` (document_type, status ∈ `DRAFT|REVIEWED|CONFIRMED|VOIDED`, bank_transaction_ids, evidence_artifact_ids, confirmed_by_member_id, confirmed_at, correction_relation); `accounting_regime_policies` (regulation_version_id, effective_from/to, mode, requires_coa, requires_double_entry); `document_reconciliation_proposals` (proposed_document JSONB, confidence, explanation, status, founder_decision); `financial_snapshots` (period, regulation_version_id, review_status, is_locked). Mở rộng `financialTransactions`: `provenance`, `accounting_document_id`. Mở rộng `accountingProfiles`: `regulation_version_id`, `applicability_confirmed_at/by`.

**Endpoints:** CRUD `bank-connections` (+`/revoke`); `POST /finance-legal/ingestion-events` (internal, verify + dedupe); `POST/GET /finance-legal/bank-transactions`; `POST/GET /finance-legal/accounting-regime-policies`; `POST/PATCH /finance-legal/document-reconciliation-proposals` (+`/accept`); `POST /finance-legal/accounting-documents` + `/:id/confirm` + `/:id/void`; `POST /finance-legal/financial-snapshots` + `/:id/lock`. Outbox `finance.accounting_document.confirmed.v1`.

**Capabilities:** `finance.connection.read` (LOW/L0), `finance.transaction.read` (LOW/L0), `finance.transaction.classify.propose` (LOW/L1), `finance.accounting_document.create_draft` (MEDIUM/L1), `finance.accounting_document.confirm` (MEDIUM/L2 — founder approval qua Gateway, bind `run_id+tool_call_id+checkpoint_ref`). **KHÔNG** đăng ký lại `finance.payout.execute`.

**Mode TT58 qua `AccountingRegimePolicy`**, không rải `if(TT58)` trong Flutter. Danh mục sổ/báo cáo chỉ xuất khi Regulation Catalog xác nhận đúng văn bản.

**Nghiệm thu:** giao dịch nhập tay → candidate → founder confirm → sửa sai bằng correction; mọi số liệu màn hình truy về document/transaction nguồn; event duplicate/out-of-order/retry không tạo document/transaction kép.

---

## Phase 4 — Release D: Cas.so Read-Only Connector (milestone spec)

> **Chạy `superpowers:writing-plans` lại. Cần Cas API/webhook auth doc xác nhận trước.**

**Control Plane:** allow-list `COSA_CONNECTOR_ALLOWED_KEYS = "sandbox-read,cas"` (`services/cosa/services/workspace-connector.service.ts:27`); production không dùng mặc định `sandbox-read`. Scope Cas chỉ `balance:read`, `transactions:read`. Authorization lưu `secret://cosa-connectors/...`; token/refresh ở secret manager. Consent/link/exchange server-to-server.

**Bảng mới (`services/company`):** `cas_webhook_inbox` (webhook_id, payload_hash, retry_count, status ∈ `RECEIVED|PROCESSING|SUCCESS|DLQ`, **UNIQUE(workspace_id, webhook_id)**); `cas_account_links` (bank_connection_id, cas_account_id, workspace_account_mapping).

**Luồng:** consent → Control Plane tạo authorization (secret ref) → Cas webhook → verify chữ ký theo cơ chế Cas công bố → lưu inbox trước → xử lý async (dedupe theo `external_transaction_id` + checksum) → map account → tạo `bank_transaction` (provenance) → outbox → reconciliation proposal → founder confirm. Retry/DLQ.

**Capabilities:** không thêm mới; tái dùng `finance.transaction.read` + `finance.accounting_document.create_draft`. Trước side effect: re-check connector grant chưa revoke; grant revoke sau approval → không execute + compensate.

**Nghiệm thu:** cùng webhook gửi lại nhiều lần → 1 `bank_transaction`; mất consent / token hết hạn → chặn sync + báo rõ (không trả 0 / dữ liệu giả); agent không thấy secret; không có capability transfer/payout.

---

## Phase 5 — Release E: AI Operating Loops & Scale (milestone spec)

> **Chạy `superpowers:writing-plans` lại. Cần Harness-P1 (output contracts) song song.**

**Bảng mới (`services/company/operations`):** `strategy.next_best_actions` (source ∈ evidence/finance/legal/stage, recommendation, priority, due_by, status, capability_required, decision_reason); `operations.task_execution_records` (task_id, run_id, tool_call_id, approval_id, created_by_capability); `strategy.weekly_reviews` (week_start_date, task_completion_rate, evidence_summary, next_actions JSONB, decision_record_id, review_status).

**Endpoints:** `POST/GET /strategy/next-best-actions` + `/:id/accept`; `POST/GET /operations/weekly-reviews` + `/:id/complete`.

**Capabilities:** `operations.task.create_draft` (LOW/L1 — nhận `evidence_refs`, `regulation_refs`, `finance_justification`; task DRAFT chờ founder); `venture.stage.assess` / `venture.stage.transition.propose` (L0/L1 — chỉ propose). Next-best-action gom context deterministic (venture profile, stage, cash/runway từ `financial_snapshots`, obligation due, evidence gap) → AI sinh proposal → validate (capability tồn tại, risk ∈ LOW/MEDIUM, evidence_refs có thật) → founder review → execute qua Gateway + approval đúng scope.

**Harness-P1:** validator JSON Schema input/output; contract `ActionProposalV1`, `SupportDraftV1`, `ResearchBriefV1`; claim không có evidence hợp lệ → `insufficient_evidence`.

**Nghiệm thu:** AI tạo weekly plan có citation tới evidence/tài chính/nghĩa vụ; action write chỉ sau policy + approval đúng scope; AI không gọi được payout/transfer dù prompt yêu cầu.

---

## Dependency graph

```
Phase 0 Foundations
      │
   Phase 1 (Release A) ──► Phase 2 (B) ──► Phase 3 (C) ──► Phase 4 (D) ──► Phase 5 (E)
                                              ▲                              ▲
Harness-P0 (track song song) ─────────────────┘  (xanh trước write prod)     │
Harness-P1 (track song song) ────────────────────────────────────────────────┘
```

---

## Verification

**Migrations:** `make migrate-all` (Agent Core → COSA → Company) hoặc per-service `cd services/<svc> && node scripts/migrate.mjs`; `make migration-compat-check`; `make test-migration-rollback`.

**Test suites (theo Makefile):**
- TS: `cd services/cosa && npx vitest run`; `cd services/company && npx vitest run` (hoặc `make services-test`).
- Python: `make agent-core-test`, `make apps-cosa-test`, `make python-test-unit`, `make python-test-integration`; `make typecheck-py`; `make boundary-check`; `make tenancy-check`.
- Flutter: `cd frontend && flutter analyze && flutter test`.
- E2E: `make e2e-test`. Tổng: `make verify`.

**Walkthrough tay (Release A):**
1. `POST /platform/auth/register {email, password, workspace_name:"AI Coffee Shop", client_workspace_creation_id:"<uuid>"}` → trả `access_token` + `platform_workspace_id` + `workspace_provision_status:"pending"`.
2. Sau sync: `GET /identity/workspaces/{id}` → `ventureStage:"S0_GENESIS"`, `platformWorkspaceId` set, `legalStatus:"NOT_DECLARED"`.
3. Đăng nhập lại → cùng `workspace_id`; `GET /platform/workspaces/{pwid}/entitlement` → `effectiveFeatures.finance:false`, `effectiveLimits.max_projects:1`.
4. `POST /operations/strategy/venture-stage/assess {workspaceId}` → recommendation; `GET /identity/workspaces/{id}` xác nhận `ventureStage` **không đổi**; gọi lại `assess` → cùng kết quả.
5. `POST /operations/strategy/venture-stage/transition {workspaceId, toStage:"S1_PROBLEM_VALIDATION", reason:"3 interviews confirm problem"}` → `ventureStage="S1_PROBLEM_VALIDATION"`; có dòng `strategy.venture_stage_transitions`; `integration.event_outbox` có `venture.stage.changed`.
6. `POST .../transition {toStage:"S3_MVP_BUILD"}` → 400 (nhảy >1 bậc); `POST .../transition {toStage:"S2_SOLUTION_VALIDATION"}` khi gate fail → 409 + blockers.
7. Flutter: module finance/legal ẩn (`hasFeature('finance')==false`); `finance_service` không còn fallback `'1'`; `finance_tt58_service` route ném `UnimplementedError`; `legal_service.getLegalSources()` không trả `"Thông tư 58/2024/TT-BTC"`.
8. Agent: registry không còn `finance.payout.execute`; `finance.transaction.record` gửi `transactionDate`/`direction`; thiếu `workspace_id` → `ValueError`.
9. Register lại cùng `client_workspace_creation_id` → cùng `platform_workspace_id`; `cosa.workspace_licenses` vẫn 1 dòng cho workspace đó.

---

## Self-Review

**Spec coverage (spec §1–15):**
- §5.2 Control Plane tables → Task 1–2, 18. §5.3 local workspace + lifecycle → Task 7–13. §5.3 "một stage transition hợp lệ" 5 điều kiện → Task 10 (đọc stage từ DB, check policy, proposal 409, transaction update+journal+outbox, lùi có reason). §6.1 onboarding 5 bước → Task 17. §6.2 entitlement free → Task 2/3/6/17. §7.2 capability + `finance.payout.execute` cấm → Task 14 (Release A phần cấm); capability mới → Phase 2–5. §8 TT58/Cas → Phase 3–4. §9 legal → Phase 2. §10.2 bảng sửa Flutter/agent → Task 14–16. §11 migration/back-compat → Task 18 + mọi `.down.sql`. §12 Release A–E → Phase 1–5. §13 test bắt buộc → Task 19 + nghiệm thu mỗi Phase. §14 thứ tự ưu tiên → dependency graph. §15 quyết định giữ xuyên suốt → Global Constraints.
- **Gap có chủ đích:** decision-record UI, next-best-action, weekly review, Cas webhook chi tiết — thuộc Phase 2–5 milestone, bung task khi chạy writing-plans cho từng Phase.

**Placeholder scan:** Release A (Task 1–19) không có TBD/TODO; mọi step code có block thật. Phase 2–5 là milestone spec có chủ đích (đã ghi rõ phải chạy writing-plans lại) — không phải placeholder trong task thực thi.

**Type consistency:** `provisionVentureWorkspace` / `ProvisionResult` (Task 3) dùng lại ở Task 4. `WorkspaceMembershipInfo` (Task 5) dùng ở Task 8 (`platform.client.ts` mirror). `assessVentureStage` / `transitionVentureStage` / `VentureStage` (Task 10) dùng ở Task 11 handler. `buildVentureStageChangedEvent` (Task 9) dùng ở Task 10; `buildProjectPhaseChangedEvent` (Task 13) thêm cùng file. Event type string `"venture.stage.changed"` / `"project.phase.changed"` nhất quán Task 9/10/13 + walkthrough.
