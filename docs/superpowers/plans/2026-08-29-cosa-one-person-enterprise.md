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

**Phạm vi tài liệu này:** Phase 0 (Foundations) + Phase 1 (Release A) viết chi tiết bite-sized, thực thi được ngay (Task 1–19). Phase 2–5 (Release B–E) viết ở **mức task-level** (Task 20–69): mỗi task có Files + Interfaces (`Consumes`/`Produces` với chữ ký/kiểu cụ thể) + các step TDD gọn + Acceptance + commit boundary — implementer viết test thất bại và code theo Interfaces đã khai. Phase 3/4/5 có **DECISION GATE** ghi đầu mỗi Phase: khi kết quả gate lệch giả định (Harness-P0/P1, Cas webhook auth, COA cho TT58 mode), chạy lại `superpowers:writing-plans` cho đúng các task được nêu trước khi execute.

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

### Phase 2–5 (Release B–E) — mỗi Phase có mục "Phase N — File Structure" riêng ngay đầu Phase (Task 20–69 ở cuối tài liệu).

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

## Phase 2 — Release B: Evidence, Legal Catalog & Registration Readiness

**Mục tiêu:** COSA biến tư vấn AI thành đề xuất **có nguồn** (regulation catalog versioned + applicability rules), tách trục *legal status* khỏi *venture stage*, và biết lúc nào phải chuyển sang chuyên gia — không kết luận pháp lý khi thiếu dữ kiện.

**Điều kiện vào:** Release A đã lên staging (provision + sync + `venture_stage_transitions` + entitlement `free`); mỗi workspace đã có `venture_profiles` row.

> **Mức chi tiết:** task-level (files + interfaces + acceptance + commit boundary). Mỗi task theo TDD — viết test thất bại trước khi code; mọi migration kèm `.down.sql` + rollback round-trip (`node scripts/test-migration-rollback.mjs`). Hằng số 3 lớp `CURRENT_LAW | POLICY_WATCH | PROFESSIONAL_REVIEW` và nhãn output `insight | proposal | requires_professional_review` copy verbatim spec §3/§6.1. Trục legal status: `NOT_DECLARED → UNREGISTERED → REGISTRATION_READINESS → REGISTERED_PENDING_VERIFICATION → REGISTERED_VERIFIED` — **không suy ra từ stage**.

### Phase 2 — File Structure

**Company Service `services/company`** (service `finance-legal` sở hữu Postgres schema `legal`; nếu team muốn tách service `legal` riêng — quyết định lúc execute, giữ nguyên tên bảng):
- `shared/db/schema/legal.ts` — CREATE: `legalSchema = pgSchema("legal")` + `regulationSources`, `regulationVersions`, `applicabilityRules`, `legalObligationTemplates`, `legalObligationInstances`, `legalEntityProfiles`.
- `shared/db/schema/strategy.ts` — MODIFY: thêm `decisionRecords` (nếu chưa có).
- `finance-legal/migrations/<n>_legal_catalog.{up,down}.sql` — CREATE (schema `legal` + sources + versions).
- `finance-legal/migrations/<n>_legal_applicability_obligations.{up,down}.sql` — CREATE (rules + templates + instances + entity_profiles).
- `finance-legal/migrations/<n>_legal_seed_tt58_nq86.{up,down}.sql` — CREATE (seed).
- `finance-legal/migrations/<n>_migrate_legacy_legal_checklist.{up,down}.sql` — CREATE (backfill `source=USER_CREATED`).
- `operations/migrations/<n>_decision_records.{up,down}.sql` — CREATE / extend.
- `finance-legal/services/regulation-catalog.service.ts`, `legal-entity-profile.service.ts`, `legal-applicability.service.ts`, `legal-obligation.service.ts` — CREATE.
- `finance-legal/handlers/regulation-catalog.handler.ts`, `legal-entity-profile.handler.ts`, `legal-applicability.handler.ts`, `legal-obligation.handler.ts` — CREATE; `finance-legal/api.ts` — MODIFY (barrel).
- `operations/strategy/services/venture-profile.service.ts`, `operations/strategy/handlers/venture-profile.handler.ts` — CREATE.
- `identity/services/workspace.service.ts` — MODIFY: `legalStatus` đọc từ `legal_entity_profiles` (status "cao nhất" theo thứ tự trục), fallback `NOT_DECLARED` khi chưa có profile (thay hằng số ở Task 12).
- `shared/events.ts` — MODIFY: `LEGAL_STATUS_CHANGED = "legal.status.changed"`, `LEGAL_OBLIGATION_CREATED = "legal.obligation.created"`.
- Tests: `finance-legal/tests/{regulation-catalog,legal-entity-profile,legal-applicability,legal-obligation}.test.ts`, `operations/tests/venture-profile.test.ts`.

**Agent Platform:**
- `apps/cosa/capabilities/legal_read.py` — CREATE: `LEGAL_APPLICABILITY_ASSESS_SPEC` (LOW/L0) + handler.
- `apps/cosa/capabilities/legal_write.py` — CREATE: `LEGAL_OBLIGATION_CREATE_DRAFT_SPEC` (MEDIUM/L1) + handler.
- `apps/cosa/capabilities/venture_profile.py` — CREATE: `VENTURE_PROFILE_READ_SPEC` (LOW/L0), `VENTURE_PROFILE_PROPOSE_UPDATE_SPEC` (LOW/L0).
- `apps/cosa/capabilities/strategy_read.py` — CREATE: `STRATEGY_DISCOVERY_READ_SPEC` (LOW/L0).
- `apps/cosa/capabilities/strategy_write.py` — CREATE/MODIFY: `STRATEGY_EVIDENCE_CREATE_DRAFT_SPEC` (LOW/L1).
- `apps/cosa/capabilities/_advisory_envelope.py` — CREATE: `wrap_advisory(payload, *, label, sources, assumptions, next_actions)` enforce shape spec §6.1 (raise nếu thiếu `sources` khi `label != "insight"` hoặc thiếu `next_actions`).
- `apps/cosa/capabilities/__init__.py`, `apps/cosa/composition/agent_plane.py` — MODIFY: register.
- Tests: `tests/apps/cosa/test_legal_capabilities.py`, `test_venture_profile_capabilities.py`, `test_advisory_envelope.py`.

**Flutter `frontend`:**
- `lib/modules/legal/services/legal_service.dart` — MODIFY: `getLegalSources()` → catalog; thêm `getApplicableObligations(workspaceId)`, `getLegalEntityProfiles(workspaceId)`, `createLegalEntityProfile(...)`, `requestVerification(profileId)`.
- `lib/modules/legal/models/` — CREATE typed DTO (regulation source/version, obligation instance, entity profile).
- `lib/modules/legal/widgets/citation_card.dart` — CREATE: render `source + effective date + assumptions + uncertainty + label`.
- `lib/modules/legal/screens/legal_entity_profile_screen.dart` — CREATE.
- `lib/modules/strategy/` — MODIFY: registration readiness checklist ở stage S3/S4 (đọc `getApplicableObligations`).
- Tests: `test/modules/legal/legal_service_test.dart`, `test/modules/legal/citation_card_test.dart`.

---

### Task 20: Company — `legal` schema: `regulation_sources` + `regulation_versions`

**Files:**
- Create: `services/company/shared/db/schema/legal.ts`
- Create: `services/company/finance-legal/migrations/<n>_legal_catalog.up.sql` / `.down.sql`
- Test: `services/company/finance-legal/tests/regulation-catalog.test.ts`

**Interfaces:**
- Produces:
  - `regulationSources { id: bigint PK, sourceName: text, issuer: text, number: text UNIQUE, url: text, contentHash: text, layer: text CHECK IN ('CURRENT_LAW','POLICY_WATCH','PROFESSIONAL_REVIEW'), createdAt, updatedAt }`
  - `regulationVersions { id: bigint PK, regulationSourceId: bigint FK→regulationSources, version: text, effectiveFrom: date, effectiveTo: date NULL, supersededById: bigint NULL FK self, createdAt }` — UNIQUE(regulation_source_id, version), index `(regulation_source_id, effective_from)`.
  - Migration mở đầu `CREATE SCHEMA IF NOT EXISTS legal;`

- [ ] **Step 1:** Viết `.up.sql` (2 bảng + schema + index) và `.down.sql` (drop 2 bảng thứ tự ngược; **không** drop schema `legal`).
- [ ] **Step 2:** Drizzle `legalSchema = pgSchema("legal")` + export 2 table; `cd services/company && npx tsc --noEmit`.
- [ ] **Step 3:** Test thất bại: insert 1 source + 2 version (v1 `effectiveTo` = ngày X, v2 `effectiveFrom` = X); helper `activeVersionAt(sourceId, date)` trả đúng 1 version cho ngày trước/sau X.
- [ ] **Step 4:** `node scripts/migrate.mjs` → applied; `node scripts/test-migration-rollback.mjs` → PASS; test Step 3 PASS.
- [ ] **Step 5:** Commit `feat(company): legal regulation catalog schema (sources + versions)`

**Acceptance:** `\d legal.regulation_sources` có bảng; rollback round-trip PASS; `activeVersionAt` chọn đúng version theo hiệu lực.

---

### Task 21: Company — `applicability_rules` + `legal_obligation_templates` + `legal_obligation_instances` + `legal_entity_profiles`

**Files:**
- Modify: `services/company/shared/db/schema/legal.ts`
- Create: `services/company/finance-legal/migrations/<n>_legal_applicability_obligations.up.sql` / `.down.sql`
- Test: `services/company/finance-legal/tests/legal-obligation.test.ts` (schema-level)

**Interfaces:**
- Produces:
  - `legalEntityProfiles { id: bigint PK, workspaceId: bigint, platformCompanyId: text NULL, entityType: text, status: text CHECK IN ('NOT_DECLARED','UNREGISTERED','REGISTRATION_READINESS','REGISTERED_PENDING_VERIFICATION','REGISTERED_VERIFIED') DEFAULT 'NOT_DECLARED', registrationNumber: text NULL, taxId: text NULL, verifiedByMemberId: bigint NULL, verifiedAt: timestamptz NULL, createdAt, updatedAt }` — index `(workspace_id)`.
  - `legalObligationTemplates { id: bigint PK, regulationVersionId: bigint FK, title: text, description: text, typicalDueOffsetDays: integer NULL, createdAt }`
  - `applicabilityRules { id: bigint PK, regulationVersionId: bigint FK, predicate: jsonb NOT NULL (`{entity_status?, fiscal_year_min?, fiscal_year_max?, condition_field?, condition_value?}`), obligationTemplateId: bigint FK→legalObligationTemplates, createdAt }`
  - `legalObligationInstances { id: bigint PK, workspaceId: bigint, legalEntityProfileId: bigint NULL FK, templateId: bigint NULL FK, regulationVersionId: bigint NULL FK, source: text CHECK IN ('REGULATION_TEMPLATE','USER_CREATED','AI_PROPOSAL'), title: text, dueDate: date NULL, status: text DEFAULT 'OPEN', evidenceArtifactId: bigint NULL, applicabilityAssessedAt: timestamptz NULL, ownerMemberId: bigint NULL, reviewStatus: text DEFAULT 'PENDING', createdAt, updatedAt }` — index `(workspace_id, status)`, `(workspace_id, due_date)`.

- [ ] **Step 1:** `.up.sql` 4 bảng (thứ tự FK: entity_profiles → templates → rules → instances) + index; `.down.sql` ngược.
- [ ] **Step 2:** Drizzle 4 table export; `npx tsc --noEmit`.
- [ ] **Step 3:** Test thất bại: insert version → template → rule (predicate `{entity_status:'UNREGISTERED'}`) → instance `source='REGULATION_TEMPLATE'`; query instances theo `workspace_id + status='OPEN'` trả 1 dòng.
- [ ] **Step 4:** migrate + rollback round-trip PASS; test PASS.
- [ ] **Step 5:** Commit `feat(company): legal applicability rules + obligation templates/instances + entity profiles`

**Acceptance:** 4 bảng tồn tại với CHECK constraint đúng enum; rollback PASS.

---

### Task 22: Company — `strategy.decision_records`

**Files:**
- Modify: `services/company/shared/db/schema/strategy.ts`
- Create: `services/company/operations/migrations/<n>_decision_records.up.sql` / `.down.sql`
- Test: `services/company/operations/tests/decision-records.test.ts`

**Interfaces:**
- Consumes: grep `decision_records` / `decisionRecords` — nếu đã tồn tại thì `ALTER TABLE ADD COLUMN IF NOT EXISTS`; nếu chưa, `CREATE TABLE`.
- Produces: `decisionRecords { id: bigint PK, workspaceId: bigint, decisionType: text, createdByKind: text CHECK IN ('FOUNDER','AI','SYSTEM'), createdByRef: text NULL, evidenceRefs: jsonb DEFAULT '[]', regulationRefs: jsonb DEFAULT '[]', confidence: numeric NULL, assumptions: jsonb DEFAULT '[]', alternatives: jsonb DEFAULT '[]', policyVersion: text NULL, aiPromptVersion: text NULL, founderDecision: text CHECK IN ('accepted','rejected','deferred') NULL, evidenceSnapshot: jsonb NULL, decidedAt: timestamptz NULL, createdAt: timestamptz DEFAULT now() }` — index `(workspace_id, decision_type, created_at)`. **Không** cập nhật row sau khi `founderDecision` set + `decidedAt` (immutable audit — enforce ở service, không ở DB trigger).

- [ ] **Step 1:** Migration (create hoặc alter) + `.down.sql`.
- [ ] **Step 2:** Drizzle; `npx tsc --noEmit`.
- [ ] **Step 3:** Test thất bại: `createDecisionRecord(...)` với `regulationRefs` + `evidenceSnapshot`; cố `updateDecisionRecord` sau khi `founderDecision` set → service ném `APIError.failedPrecondition`.
- [ ] **Step 4:** migrate + rollback PASS; test PASS.
- [ ] **Step 5:** Commit `feat(company): workspace-scoped decision_records (immutable after founder decision)`

**Acceptance:** decision record lưu được `regulation_refs` + `evidence_snapshot`; update sau khi chốt bị chặn.

---

### Task 23: Company — seed `58/2026/TT-BTC` + `86/NQ-CP`

**Files:**
- Create: `services/company/finance-legal/migrations/<n>_legal_seed_tt58_nq86.up.sql` / `.down.sql`
- Test: `services/company/finance-legal/tests/regulation-catalog.test.ts` (thêm case)

**Interfaces:**
- Produces (idempotent — `INSERT ... ON CONFLICT (number) DO NOTHING`):
  - Source `58/2026/TT-BTC`, issuer "Bộ Tài chính", `layer='CURRENT_LAW'`, url `https://congbao.chinhphu.vn/...` (spec §3), `contentHash` = sha256 placeholder ghi rõ TODO-verify khi có bản chính thức → version `2026`, `effectiveFrom='2026-07-01'`, `effectiveTo=NULL`. Thêm 1 `legal_obligation_templates` mẫu ("Nộp báo cáo tài chính năm theo TT58") + 1 `applicability_rules` predicate `{entity_status:'REGISTERED_VERIFIED', condition_field:'accounting_regime', condition_value:'TT58_2026'}`.
  - Source `86/NQ-CP`, issuer "Chính phủ", `layer='POLICY_WATCH'`, url `https://vanban.chinhphu.vn/?...217558...` → version `2026`, `effectiveFrom='2026-04-05'`. **Không** kèm obligation template (POLICY_WATCH không sinh nghĩa vụ).
- IDs dùng `generateSnowflakeStr()` không khả dụng trong SQL → dùng số cố định reserved range (ghi comment) hoặc chạy qua `scripts/` node seed. Chọn: node seed script `finance-legal/scripts/seed-legal-catalog.mjs` gọi trong migration runner hook, hoặc hard-code BIGINT literals reserved `1..99`.

- [ ] **Step 1:** Viết seed (SQL literal ids reserved, `ON CONFLICT DO NOTHING`), `.down.sql` xóa theo `number`.
- [ ] **Step 2:** Test thất bại: `getRegulationSources()` trả cả 2, `86/NQ-CP` có `layer='POLICY_WATCH'` và 0 obligation template.
- [ ] **Step 3:** migrate + chạy 2 lần (idempotent — không nhân đôi) + rollback PASS.
- [ ] **Step 4:** Commit `feat(company): seed TT58/2026 (CURRENT_LAW) + NQ86 (POLICY_WATCH) regulation catalog`

**Acceptance:** catalog có 2 source đúng layer; seed chạy lại không tạo trùng; `POLICY_WATCH` không có obligation.

---

### Task 24: Company — migrate legacy `legal_checklist_items` / `legal_obligations` → instances

**Files:**
- Create: `services/company/finance-legal/migrations/<n>_migrate_legacy_legal_checklist.up.sql` / `.down.sql`
- Test: `services/company/finance-legal/tests/legal-obligation.test.ts` (thêm case)

**Interfaces:**
- Consumes: grep bảng legacy thật (`legal_checklist_items`, `legal_obligations`, hoặc tên khác trong `finance-legal` schema) — verify lúc implement.
- Produces: mỗi row legacy → `legal_obligation_instances` với `source='USER_CREATED'`, `regulation_version_id=NULL`, `template_id=NULL`, `title` = title cũ, `status` map (`done→CLOSED`, còn lại `OPEN`), `review_status='USER_MANAGED'`. Idempotency: cột `legacy_ref` (text) UNIQUE trên instances = `'legacy:checklist:'||old.id`; `ON CONFLICT (legacy_ref) DO NOTHING`. **Không** xóa bảng legacy.

- [ ] **Step 1:** `ALTER TABLE legal.legal_obligation_instances ADD COLUMN IF NOT EXISTS legacy_ref TEXT`; unique index partial. Migration copy dữ liệu. `.down.sql`: xóa các instance có `legacy_ref LIKE 'legacy:%'` + drop cột.
- [ ] **Step 2:** Test thất bại: seed 2 row legacy → chạy migrate → 2 instance `source='USER_CREATED'`, `regulation_version_id IS NULL`; chạy lại không nhân đôi.
- [ ] **Step 3:** migrate + rollback PASS; test PASS.
- [ ] **Step 4:** Commit `feat(company): migrate legacy legal checklist into obligation instances (source=USER_CREATED)`

**Acceptance:** không có instance nào gán regulation source giả; re-run idempotent; bảng legacy còn nguyên.

---

### Task 25: Company — `regulation-catalog.service.ts` + endpoints

**Files:**
- Create: `services/company/finance-legal/services/regulation-catalog.service.ts`
- Create: `services/company/finance-legal/handlers/regulation-catalog.handler.ts`
- Modify: `services/company/finance-legal/api.ts`
- Test: `services/company/finance-legal/tests/regulation-catalog.test.ts`

**Interfaces:**
- Produces:
  ```ts
  export interface RegulationSourceView { id: string; sourceName: string; issuer: string; number: string; url: string; layer: "CURRENT_LAW"|"POLICY_WATCH"|"PROFESSIONAL_REVIEW"; versions: { id: string; version: string; effectiveFrom: string; effectiveTo: string | null; isActive: boolean }[]; }
  export async function listRegulationSources(filter?: { layer?: string; activeOnly?: boolean }): Promise<RegulationSourceView[]>;
  export async function createRegulationVersion(p: { regulationSourceId: bigint; version: string; effectiveFrom: string; effectiveTo?: string; supersededById?: bigint }): Promise<{ id: string }>;
  ```
- Endpoints (`expose: true`, `auth: true`):
  - `GET /finance-legal/regulation-sources?layer=&activeOnly=` → `{ sources: RegulationSourceView[] }`
  - `GET /finance-legal/obligation-templates?regulationVersionId=` → `{ templates: [...] }`
  - `POST /finance-legal/regulation-versions` (chỉ role admin/platform — kiểm ở handler) → `{ id }`. Khi thêm version mới có `effectiveTo` cho version cũ: set `supersededById`. **Source đã hết hiệu lực (`effectiveTo < today` cho mọi version) → không dùng để sinh obligation** (enforce ở Task 27).

- [ ] **Step 1:** Test thất bại — `listRegulationSources({activeOnly:true})` chỉ trả source có ≥1 version còn hiệu lực; `isActive` đúng.
- [ ] **Step 2:** Implement service (join sources×versions, tính `isActive = effectiveFrom<=now && (effectiveTo==null || effectiveTo>now)`).
- [ ] **Step 3:** Implement handler + barrel; `npx tsc --noEmit`.
- [ ] **Step 4:** Test PASS + `npx vitest run finance-legal/`.
- [ ] **Step 5:** Commit `feat(company): regulation catalog read + version admin endpoints`

**Acceptance:** Flutter đọc được catalog versioned; không endpoint nào trả hằng số hard-code.

---

### Task 26: Company — `legal-entity-profile.service.ts` + endpoints (+ verify approval)

**Files:**
- Create: `services/company/finance-legal/services/legal-entity-profile.service.ts`
- Create: `services/company/finance-legal/handlers/legal-entity-profile.handler.ts`
- Modify: `services/company/finance-legal/api.ts`, `services/company/shared/events.ts`
- Test: `services/company/finance-legal/tests/legal-entity-profile.test.ts`

**Interfaces:**
- Consumes: approval infra hiện có cho hành động rủi ro cao (grep `requireApproval` / approval service trong `finance-legal`); `appendOutboxEvent`.
- Produces:
  ```ts
  export type LegalStatus = "NOT_DECLARED"|"UNREGISTERED"|"REGISTRATION_READINESS"|"REGISTERED_PENDING_VERIFICATION"|"REGISTERED_VERIFIED";
  export interface LegalEntityProfileView { id: string; workspaceId: string; entityType: string; status: LegalStatus; registrationNumber: string|null; taxId: string|null; verifiedAt: string|null; platformCompanyId: string|null; }
  export async function listLegalEntityProfiles(workspaceId: bigint): Promise<LegalEntityProfileView[]>;
  export async function createLegalEntityProfile(p: { workspaceId: bigint; entityType: string; registrationNumber?: string; taxId?: string }): Promise<LegalEntityProfileView>;  // status luôn khởi tạo 'UNREGISTERED' (hoặc 'REGISTRATION_READINESS' nếu có registrationNumber) — KHÔNG 'REGISTERED_VERIFIED'
  export async function requestVerification(p: { profileId: bigint; actorMemberId: bigint }): Promise<{ approvalId: string; status: "PENDING_APPROVAL" }>;
  export async function applyVerification(p: { profileId: bigint; approvalId: string; approverMemberId: bigint }): Promise<LegalEntityProfileView>;  // set status='REGISTERED_VERIFIED' + verifiedBy/At; emit legal.status.changed; chỉ khi approval bound đúng
  ```
- Endpoints: `GET /legal/legal-entity-profiles?workspaceId=`, `POST /legal/legal-entity-profiles`, `POST /legal/legal-entity-profiles/:id/verify` (tạo approval request), `POST /legal/legal-entity-profiles/:id/verify/confirm` (áp dụng sau approval). **Auto-verify bị cấm** — `verify` không bao giờ set `REGISTERED_VERIFIED` trực tiếp.

- [ ] **Step 1:** Test thất bại: create → status ∈ {`UNREGISTERED`,`REGISTRATION_READINESS`}; `requestVerification` → PENDING; `applyVerification` với `approvalId` sai → `permissionDenied`; đúng → `REGISTERED_VERIFIED` + outbox `legal.status.changed`.
- [ ] **Step 2:** Implement service + event builder `buildLegalStatusChangedEvent`.
- [ ] **Step 3:** Implement handlers + barrel; `npx tsc --noEmit`.
- [ ] **Step 4:** Test PASS + regression `npx vitest run finance-legal/`.
- [ ] **Step 5:** Commit `feat(company): legal entity profiles + human-approved verification (no auto-verify)`

**Acceptance:** không thể lên `REGISTERED_VERIFIED` nếu không có approval bound; mỗi lần đổi status có outbox event + audit.

---

### Task 27: Company — `legal-applicability.service.ts` + `GET /legal/applicable-obligations` (read-only)

**Files:**
- Create: `services/company/finance-legal/services/legal-applicability.service.ts`
- Create: `services/company/finance-legal/handlers/legal-applicability.handler.ts`
- Modify: `services/company/finance-legal/api.ts`
- Test: `services/company/finance-legal/tests/legal-applicability.test.ts`

**Interfaces:**
- Consumes: `applicabilityRules`, `regulationVersions` (chỉ version còn hiệu lực), `legalEntityProfiles`, `ventureProfiles` (fiscal year, currency).
- Produces:
  ```ts
  export interface ApplicableObligation {
    templateId: string; title: string; regulationSourceNumber: string; regulationVersion: string; effectiveFrom: string;
    layer: "CURRENT_LAW"|"POLICY_WATCH"|"PROFESSIONAL_REVIEW";
    predicateSatisfied: boolean; unresolvedFacts: string[];   // field nào trong predicate chưa có dữ liệu
    recommendedLabel: "insight"|"proposal"|"requires_professional_review";
    dueDateEstimate: string | null;
  }
  export async function assessApplicableObligations(workspaceId: bigint): Promise<ApplicableObligation[]>;  // KHÔNG persist gì
  ```
- Quy tắc: chỉ đánh giá rule của version **còn hiệu lực** (`effectiveTo == null || > today`). `predicateSatisfied=false` khi có `unresolvedFacts` → `recommendedLabel='requires_professional_review'` nếu predicate chạm điều kiện đăng ký/cơ quan; `POLICY_WATCH` luôn `label='insight'` + không đề xuất due date. Source hết hiệu lực → **loại khỏi kết quả**.
- Endpoint `GET /legal/applicable-obligations?workspaceId=` (`expose: true`, `auth: true`) → `{ obligations: ApplicableObligation[] }`. Read-only, không tạo instance.

- [ ] **Step 1:** Test thất bại: workspace `UNREGISTERED` + thiếu `fiscal_year` → obligation trả `predicateSatisfied=false`, `unresolvedFacts` chứa `"fiscal_year"`, `recommendedLabel='requires_professional_review'`. Version hết hiệu lực (set `effectiveTo` quá khứ) → không xuất hiện.
- [ ] **Step 2:** Implement (evaluate predicate JSONB vs workspace facts; tái dùng helper evidence/gate nếu phù hợp).
- [ ] **Step 3:** Handler + barrel; `npx tsc --noEmit`.
- [ ] **Step 4:** Test PASS.
- [ ] **Step 5:** Commit `feat(company): read-only applicable-obligations assessment (versioned, no persist)`

**Acceptance:** giải thích được vì sao 1 checklist xuất hiện (rule + version + effective date) và dữ kiện nào thiếu; source hết hiệu lực không sinh obligation.

---

### Task 28: Company — `legal-obligation.service.ts` + `POST/PATCH /legal/legal-obligation-instances`

**Files:**
- Create: `services/company/finance-legal/services/legal-obligation.service.ts`
- Create: `services/company/finance-legal/handlers/legal-obligation.handler.ts`
- Modify: `services/company/finance-legal/api.ts`, `services/company/shared/events.ts`
- Test: `services/company/finance-legal/tests/legal-obligation.test.ts`

**Interfaces:**
- Produces:
  ```ts
  export interface ObligationInstanceView { id: string; workspaceId: string; source: "REGULATION_TEMPLATE"|"USER_CREATED"|"AI_PROPOSAL"; title: string; dueDate: string|null; status: string; reviewStatus: string; regulationVersionId: string|null; templateId: string|null; ownerMemberId: string|null; }
  export async function createObligationInstance(p: { workspaceId: bigint; source: "REGULATION_TEMPLATE"|"USER_CREATED"|"AI_PROPOSAL"; templateId?: bigint; title: string; dueDate?: string; ownerMemberId?: bigint; legalEntityProfileId?: bigint }): Promise<ObligationInstanceView>;  // source='REGULATION_TEMPLATE' bắt buộc templateId + version còn hiệu lực; source='AI_PROPOSAL' → reviewStatus='PENDING'
  export async function patchObligationInstance(p: { id: bigint; status?: string; reviewStatus?: string; dueDate?: string; ownerMemberId?: bigint; evidenceArtifactId?: bigint }): Promise<ObligationInstanceView>;  // emit legal.obligation.created chỉ ở create; patch không đổi source/template
  export async function listObligationInstances(workspaceId: bigint, filter?: { status?: string }): Promise<ObligationInstanceView[]>;
  ```
- Endpoints: `GET /legal/legal-obligation-instances?workspaceId=&status=`, `POST /legal/legal-obligation-instances`, `PATCH /legal/legal-obligation-instances/:id`.

- [ ] **Step 1:** Test thất bại: create `source='REGULATION_TEMPLATE'` không `templateId` → `invalidArgument`; create hợp lệ → outbox `legal.obligation.created`; `source='AI_PROPOSAL'` → `reviewStatus='PENDING'` (founder phải PATCH duyệt).
- [ ] **Step 2:** Implement service + event builder.
- [ ] **Step 3:** Handlers + barrel; `npx tsc --noEmit`.
- [ ] **Step 4:** Test PASS + regression.
- [ ] **Step 5:** Commit `feat(company): legal obligation instances create/patch/list with provenance + outbox`

**Acceptance:** obligation từ AI luôn ở trạng thái chờ founder; mọi instance truy được nguồn (template→version→source) hoặc `USER_CREATED`.

---

### Task 29: Company — `venture-profile.service.ts` + `GET/PATCH /strategy/venture-profile/:workspaceId`

**Files:**
- Create: `services/company/operations/strategy/services/venture-profile.service.ts`
- Create: `services/company/operations/strategy/handlers/venture-profile.handler.ts`
- Modify: `services/company/operations/api.ts`
- Test: `services/company/operations/tests/venture-profile.test.ts`

**Interfaces:**
- Consumes: `ventureProfiles` (Task 8).
- Produces:
  ```ts
  export interface VentureProfileView { workspaceId: string; problemStatement: string|null; targetCustomer: string|null; industry: string|null; geography: string|null; currency: string|null; timezone: string|null; founderGoal: string|null; initialRunwayMonths: number|null; stageEnteredAt: string|null; }
  export async function getVentureProfile(workspaceId: bigint): Promise<VentureProfileView>;
  export async function patchVentureProfile(workspaceId: bigint, patch: Partial<Omit<VentureProfileView,"workspaceId"|"stageEnteredAt">>): Promise<VentureProfileView>;  // whitelist field; không cho set stageEnteredAt qua đây
  ```
- Endpoints: `GET /strategy/venture-profile/:workspaceId`, `PATCH /strategy/venture-profile/:workspaceId` (`auth: true`, `requireWorkspaceAccess`). Thay endpoint tạm ở Task 17 Step 3.

- [ ] **Step 1:** Test thất bại: PATCH `{problemStatement, founderGoal}` → GET trả đúng; PATCH `{stageEnteredAt}` → bị bỏ qua (không đổi).
- [ ] **Step 2:** Implement service (whitelist) + handler.
- [ ] **Step 3:** `npx tsc --noEmit`; barrel.
- [ ] **Step 4:** Test PASS + regression `npx vitest run operations/`.
- [ ] **Step 5:** Commit `feat(company): venture-profile read/patch endpoints`

**Acceptance:** onboarding S0 bước 1–3 (spec §6.1) lưu được vào backend; field ngoài whitelist bị từ chối.

---

### Task 30: Company — `getWorkspaceRecord.legalStatus` đọc từ entity profiles

**Files:**
- Modify: `services/company/identity/services/workspace.service.ts`
- Test: `services/company/identity/tests/workspace.test.ts`

**Interfaces:**
- Consumes: `listLegalEntityProfiles` (Task 26).
- Produces: `legalStatus` trong response `GET /identity/workspaces/:id` = status "tiến xa nhất" trong `legal_entity_profiles` của workspace theo thứ tự trục; `NOT_DECLARED` nếu 0 profile. Thay hằng số cố định ở Task 12.

- [ ] **Step 1:** Test thất bại: workspace không profile → `legalStatus='NOT_DECLARED'`; tạo profile `REGISTRATION_READINESS` → record trả `REGISTRATION_READINESS`.
- [ ] **Step 2:** Implement (helper `maxLegalStatus(profiles)` theo ordinal của trục).
- [ ] **Step 3:** Test PASS + regression.
- [ ] **Step 4:** Commit `feat(company): derive workspace legalStatus from legal entity profiles`

**Acceptance:** trục legal status độc lập với `ventureStage`; không suy diễn ngược.

---

### Task 31: Agent — advisory envelope helper + contract test

**Files:**
- Create: `apps/cosa/capabilities/_advisory_envelope.py`
- Test: `tests/apps/cosa/test_advisory_envelope.py`

**Interfaces:**
- Produces:
  ```python
  Label = Literal["insight", "proposal", "requires_professional_review"]
  def wrap_advisory(payload: dict, *, label: Label, sources: list[dict], assumptions: list[str], next_actions: list[str]) -> dict:
      # trả {"label", "known": {...payload, "sources": sources}, "assumptions", "next_actions", "generated_at"}
      # raise ValueError nếu: label != "insight" và sources rỗng; next_actions rỗng; source thiếu key {"number","url","layer"}
  ```
- Mọi capability legal/venture/strategy ở Release B **phải** trả qua `wrap_advisory` (spec §6.1).

- [ ] **Step 1:** Test thất bại: `wrap_advisory({}, label="proposal", sources=[], assumptions=[], next_actions=["x"])` → `ValueError`; hợp lệ → dict có đủ 5 key.
- [ ] **Step 2:** Implement.
- [ ] **Step 3:** `PYTHONPATH=$(pwd) .venv/bin/python -m pytest tests/apps/cosa/test_advisory_envelope.py -q` PASS; `make boundary-check`.
- [ ] **Step 4:** Commit `feat(cosa): advisory envelope helper enforcing source+assumption+label contract`

**Acceptance:** không capability nào ở Phase 2 trả payload trần không nhãn/nguồn.

---

### Task 32: Agent — `legal.applicability.assess` (L0) + `legal.obligation.create_draft` (L1)

**Files:**
- Create: `apps/cosa/capabilities/legal_read.py`, `apps/cosa/capabilities/legal_write.py`
- Modify: `apps/cosa/capabilities/__init__.py`, `apps/cosa/composition/agent_plane.py`
- Test: `tests/apps/cosa/test_legal_capabilities.py`

**Interfaces:**
- Consumes: `CompanyServiceClient` (với **service identity** — không anonymous, spec §7.2); `wrap_advisory` (Task 31).
- Produces:
  - `LEGAL_APPLICABILITY_ASSESS_SPEC` `id="legal.applicability.assess"`, `risk=LOW`, input `{workspace_id}` required → handler `GET /legal/applicable-obligations` → `wrap_advisory(..., label` map từ `recommendedLabel` của từng obligation; nếu bất kỳ obligation `requires_professional_review` → label tổng = `requires_professional_review`).
  - `LEGAL_OBLIGATION_CREATE_DRAFT_SPEC` `id="legal.obligation.create_draft"`, `risk=MEDIUM`, input `{workspace_id, title, template_id?, due_date?}` → handler `POST /legal/legal-obligation-instances` với `source='AI_PROPOSAL'` (backend ép `reviewStatus='PENDING'`). **Không** tự set status OPEN/CLOSED.

- [ ] **Step 1:** Test thất bại: registry chứa 2 spec đúng risk; `create_draft` handler gửi body `source='AI_PROPOSAL'`; `assess` handler trả dict có `label` + `sources`.
- [ ] **Step 2:** Implement 2 file + register.
- [ ] **Step 3:** `make apps-cosa-test` + `make boundary-check` + `make typecheck-py` PASS.
- [ ] **Step 4:** Commit `feat(cosa): legal applicability assess (L0) + obligation create-draft (L1) capabilities`

**Acceptance:** AI chỉ propose obligation (chờ founder); assess không persist; output có nguồn + nhãn.

---

### Task 33: Agent — `venture.profile.read/propose_update` + `strategy.discovery.read` + `strategy.evidence.create_draft`

**Files:**
- Create: `apps/cosa/capabilities/venture_profile.py`, `apps/cosa/capabilities/strategy_read.py`, `apps/cosa/capabilities/strategy_write.py`
- Modify: `apps/cosa/capabilities/__init__.py`, `apps/cosa/composition/agent_plane.py`
- Test: `tests/apps/cosa/test_venture_profile_capabilities.py`

**Interfaces:**
- Produces:
  - `VENTURE_PROFILE_READ_SPEC` `id="venture.profile.read"` risk LOW → `GET /strategy/venture-profile/:workspace_id`.
  - `VENTURE_PROFILE_PROPOSE_UPDATE_SPEC` `id="venture.profile.propose_update"` risk LOW → **không** gọi PATCH; trả `wrap_advisory(label="proposal", ...)` với diff đề xuất để founder tự apply qua UI. (Ghi rõ: propose ≠ execute.)
  - `STRATEGY_DISCOVERY_READ_SPEC` `id="strategy.discovery.read"` risk LOW → đọc evidence/assumption/decision list (endpoint strategy hiện có).
  - `STRATEGY_EVIDENCE_CREATE_DRAFT_SPEC` `id="strategy.evidence.create_draft"` risk LOW → tạo evidence draft (endpoint evidence hiện có) ở trạng thái draft/pending, không confirmed.

- [ ] **Step 1:** Test thất bại: `propose_update` handler **không** phát HTTP PATCH (mock client assert 0 mutating call); registry có 4 spec.
- [ ] **Step 2:** Implement + register.
- [ ] **Step 3:** `make apps-cosa-test` + `make boundary-check` PASS.
- [ ] **Step 4:** Commit `feat(cosa): venture profile + strategy discovery/evidence draft capabilities (L0/L1)`

**Acceptance:** `propose_update` không mutate; evidence tạo ra là draft chờ founder.

---

### Task 34: Flutter — legal catalog UI + citation card + entity profile + readiness checklist

**Files:**
- Modify: `frontend/lib/modules/legal/services/legal_service.dart`
- Create: `frontend/lib/modules/legal/models/legal_dtos.dart`, `frontend/lib/modules/legal/widgets/citation_card.dart`, `frontend/lib/modules/legal/screens/legal_entity_profile_screen.dart`
- Modify: `frontend/lib/modules/strategy/…` (readiness checklist S3/S4)
- Test: `frontend/test/modules/legal/legal_service_test.dart`, `frontend/test/modules/legal/citation_card_test.dart`

**Interfaces:**
- `legal_service.dart`: `getLegalSources()` → `GET /finance-legal/regulation-sources` (typed DTO, không còn list hard-code / không còn `"Thông tư 58/2024/TT-BTC"`); `getApplicableObligations(workspaceId)` → `GET /legal/applicable-obligations`; `getLegalEntityProfiles(workspaceId)`, `createLegalEntityProfile(...)`, `requestVerification(profileId)`. HTTP 404/lỗi → ném typed exception (không nuốt thành `[]`), trừ pre-Release-B fallback đã gỡ.
- `citation_card.dart`: nhận `{sourceNumber, url, effectiveFrom, layer, assumptions, unresolvedFacts, label}` → render badge theo `layer` (CURRENT_LAW/POLICY_WATCH/PROFESSIONAL_REVIEW) + danh sách "dữ kiện còn thiếu" + link nguồn.
- Readiness checklist: chỉ hiển thị khi `ventureStage ∈ {S3_MVP_BUILD, S4_PRODUCT_MARKET_FIT}` (đọc từ workspace record), list từ `getApplicableObligations`, mỗi item bọc `CitationCard`.

- [ ] **Step 1:** Test thất bại: `getLegalSources()` không trả string chứa `"2024/TT-BTC"`; `CitationCard` render `label='requires_professional_review'` → hiện CTA "Gặp chuyên gia".
- [ ] **Step 2:** Implement service + DTO + widget + screen + checklist gating.
- [ ] **Step 3:** `cd frontend && flutter analyze && flutter test test/modules/legal/`.
- [ ] **Step 4:** Commit `feat(frontend): legal catalog UI, citation card, entity profile screen, S3/S4 readiness checklist`

**Acceptance:** UI hiển thị nguồn + ngày hiệu lực + dữ kiện thiếu cho mỗi checklist; không còn nguồn hard-code sai năm.

---

### Task 35: Release B — integration & acceptance pass

**Files:**
- Create: `services/company/tests/e2e/legal-catalog-flow.test.ts`

- [ ] **Step 1:** E2E: seed catalog → `GET /finance-legal/regulation-sources?activeOnly=true` trả TT58/2026 + NQ86; tạo `legal_entity_profile` → `GET /identity/workspaces/:id` `legalStatus` đổi theo profile (không theo stage).
- [ ] **Step 2:** `GET /legal/applicable-obligations` giải thích `predicateSatisfied=false` + `unresolvedFacts` khi thiếu fiscal year; set `regulation_versions.effective_to` quá khứ → obligation biến mất (source hết hiệu lực không sinh mới).
- [ ] **Step 3:** `legal.obligation.create_draft` (agent) → instance `source='AI_PROPOSAL'`, `reviewStatus='PENDING'`; founder PATCH duyệt → OPEN.
- [ ] **Step 4:** Verify approval: `applyVerification` với `approvalId` sai → `permissionDenied`; đúng → `REGISTERED_VERIFIED` + outbox `legal.status.changed`.
- [ ] **Step 5:** Tenant isolation: user B không đọc được obligation/entity-profile của workspace user A.
- [ ] **Step 6:** Chạy gate: `make typecheck-py && make boundary-check && make tenancy-check && cd services/company && npx vitest run && cd ../.. && make apps-cosa-test && cd frontend && flutter analyze && flutter test`.
- [ ] **Step 7:** Commit `test(company): Release B legal-catalog + applicability + verification acceptance`

**Acceptance (spec §13):** giải thích được vì sao 1 checklist xuất hiện, nguồn nào hiệu lực, dữ kiện nào thiếu; không kết luận điều kiện pháp lý khi thiếu dữ kiện; decision record lưu `regulation_refs` + `evidence_snapshot`; source hết hiệu lực không sinh obligation mới.

---

## Phase 3 — Release C: Finance Ingestion & TT58 Foundation

**Mục tiêu:** Có dữ liệu tài chính đáng tin và chứng từ nháp/đã xác nhận với provenance đầy đủ — chưa tự động khai/nộp. Mode kế toán TT58 do `AccountingRegimePolicy` quyết định, không rải `if(TT58)` trong Flutter.

> **DECISION GATE trước khi execute Phase 3:**
> 1. **Harness-P0 xanh** (context propagation + policy floor + service identity + gateway-only workflow — `docs/implementation/2026-08-28-cosa-agent-harness-integration-adjustment.md`) là điều kiện bắt buộc để bật capability *write* finance (`finance.accounting_document.confirm`) ở **production**. Task 49 chỉ register ở `dev`/`staging` tới khi gate xanh; Task 51 (Flutter) không expose nút confirm ở prod build tới khi đó.
> 2. **COA / double-entry cho TT58 mode:** `AccountingRegimePolicy.requires_coa` / `requires_double_entry` phải chốt từ văn bản `58/2026/TT-BTC` thực tế (Task 45). Plan này giả định **register-based, không sổ cái kép** cho DN siêu nhỏ. Nếu kết luận khác → chạy lại `superpowers:writing-plans` cho Task 45–48 trước khi execute.
> 3. Không phát hành finance nếu TypeScript typecheck còn lỗi hoặc contract test chưa chạy trong CI (spec §13).
>
> **Mức chi tiết:** task-level. Mỗi task TDD; mọi migration kèm `.down.sql` + rollback round-trip. `amount` luôn `DECIMAL`/`numeric`, không float.

### Phase 3 — File Structure

**Company Service `services/company` (`finance-legal`):**
- `shared/db/schema/finance-legal.ts` — MODIFY: thêm `bankConnections`, `ingestionEvents`, `bankTransactions`, `accountingDocuments`, `accountingRegimePolicies`, `documentReconciliationProposals`, `financialSnapshots`; mở rộng `financialTransactions` (+`provenance` jsonb, +`accountingDocumentId` bigint NULL), `accountingProfiles` (+`regulationVersionId`, +`applicabilityConfirmedAt/By`).
- `finance-legal/migrations/<n>_accounting_regime_policies.{up,down}.sql`
- `finance-legal/migrations/<n>_bank_connections.{up,down}.sql`
- `finance-legal/migrations/<n>_ingestion_events.{up,down}.sql`
- `finance-legal/migrations/<n>_bank_transactions.{up,down}.sql`
- `finance-legal/migrations/<n>_accounting_documents_and_proposals.{up,down}.sql`
- `finance-legal/migrations/<n>_financial_snapshots_and_txn_provenance.{up,down}.sql`
- `finance-legal/services/`: `bank-connection.service.ts`, `ingestion.service.ts`, `bank-transaction.service.ts`, `accounting-regime-policy.service.ts`, `reconciliation-proposal.service.ts`, `accounting-document.service.ts`, `financial-snapshot.service.ts` — CREATE.
- `finance-legal/handlers/`: matching handlers — CREATE; `finance-legal/api.ts` — MODIFY.
- `shared/events.ts` — MODIFY: `FINANCE_ACCOUNTING_DOCUMENT_CONFIRMED = "finance.accounting_document.confirmed.v1"`, `FINANCE_BANK_TRANSACTION_INGESTED = "finance.bank_transaction.ingested"`.
- Tests: `finance-legal/tests/{ingestion,bank-transaction,accounting-document,reconciliation,regime-policy,financial-snapshot}.test.ts`.

**Agent Platform:**
- `apps/cosa/capabilities/finance_read.py` — CREATE: `FINANCE_CONNECTION_READ_SPEC` (L0), `FINANCE_TRANSACTION_READ_SPEC` (L0).
- `apps/cosa/capabilities/finance_write.py` — MODIFY: thêm `FINANCE_TRANSACTION_CLASSIFY_PROPOSE_SPEC` (L1), `FINANCE_ACCOUNTING_DOCUMENT_CREATE_DRAFT_SPEC` (L1), `FINANCE_ACCOUNTING_DOCUMENT_CONFIRM_SPEC` (L2). **Không** re-add `FINANCE_PAYOUT_EXECUTE_SPEC`.
- `apps/cosa/composition/agent_plane.py` — MODIFY: register theo env; `finance.accounting_document.confirm` chỉ register khi `COSA_HARNESS_P0_VERIFIED=true`.
- Tests: `tests/apps/cosa/test_finance_read.py`, `tests/apps/cosa/test_finance_write.py` (mở rộng).

**Flutter `frontend`:**
- `lib/modules/finance/services/finance_service.dart` — MODIFY: thêm `getBankConnections`, `getBankTransactions`, `getAccountingRegimePolicy(workspaceId)`, `getReconciliationProposals`, `acceptReconciliationProposal`, `createAccountingDocument`, `confirmAccountingDocument`, `voidAccountingDocument`, `getFinancialSnapshots`.
- `lib/modules/finance/services/finance_tt58_service.dart` — MODIFY: thay `UnimplementedError` bằng typed API; **mọi nhánh TT58** đọc `AccountingRegimePolicy.mode` từ backend, không hard-code.
- `lib/modules/finance/screens/`: `transaction_review_screen.dart` (candidate → confirm), `document_correction_screen.dart` — CREATE.
- `lib/modules/finance/widgets/provenance_trail.dart` — CREATE: mỗi con số → link về document/transaction nguồn.
- Tests: `test/modules/finance/finance_service_test.dart`, `test/modules/finance/provenance_trail_test.dart`.

---

### Task 36: Company — `accounting_regime_policies` + extend `accounting_profiles`

**Files:**
- Modify: `services/company/shared/db/schema/finance-legal.ts`
- Create: `services/company/finance-legal/migrations/<n>_accounting_regime_policies.up.sql` / `.down.sql`
- Test: `services/company/finance-legal/tests/regime-policy.test.ts`

**Interfaces:**
- Consumes: `regulationVersions` (Task 20).
- Produces:
  - `accountingRegimePolicies { id: bigint PK, workspaceId: bigint, regulationVersionId: bigint FK, mode: text (vd 'TT58_2026_MICRO'), effectiveFrom: date, effectiveTo: date NULL, requiresCoa: boolean DEFAULT false, requiresDoubleEntry: boolean DEFAULT false, createdAt, updatedAt }` — index `(workspace_id, effective_from)`.
  - `accountingProfiles` +`regulationVersionId: bigint NULL FK`, +`applicabilityConfirmedAt: timestamptz NULL`, +`applicabilityConfirmedBy: bigint NULL`.

- [ ] **Step 1:** Migration up/down (`ALTER TABLE accounting_profiles ADD COLUMN IF NOT EXISTS ...` + `CREATE TABLE accounting_regime_policies`).
- [ ] **Step 2:** Drizzle; `npx tsc --noEmit`.
- [ ] **Step 3:** Test thất bại: `resolveRegimePolicy(workspaceId, date)` trả policy có `effectiveFrom<=date<effectiveTo|∞`; mặc định `requiresDoubleEntry=false`.
- [ ] **Step 4:** migrate + rollback PASS; test PASS.
- [ ] **Step 5:** Commit `feat(company): accounting_regime_policies + accounting_profiles applicability columns`

**Acceptance:** mode kế toán là dữ liệu (policy row) gắn regulation version, không phải hằng số UI.

---

### Task 37: Company — `bank_connections`

**Files:**
- Modify: `services/company/shared/db/schema/finance-legal.ts`
- Create: `services/company/finance-legal/migrations/<n>_bank_connections.up.sql` / `.down.sql`
- Test: `services/company/finance-legal/tests/bank-connection.test.ts`

**Interfaces:**
- Produces: `bankConnections { id: bigint PK, workspaceId: bigint, provider: text CHECK IN ('cas','manual'), consentState: text CHECK IN ('PENDING','GRANTED','REVOKED','EXPIRED') DEFAULT 'PENDING', secretRef: text NULL (chỉ `secret://cosa-connectors/...`), scopes: jsonb DEFAULT '[]', accountLinks: jsonb DEFAULT '[]', grantExpiresAt: timestamptz NULL, lastSyncedAt: timestamptz NULL, syncStatus: text DEFAULT 'IDLE', createdAt, updatedAt }` — index `(workspace_id, provider)`. **CHECK**: `secretRef IS NULL OR secretRef LIKE 'secret://cosa-connectors/%'` (không lưu token thô).

- [ ] **Step 1:** Migration up/down + CHECK constraint.
- [ ] **Step 2:** Drizzle; `npx tsc --noEmit`.
- [ ] **Step 3:** Test thất bại: insert row với `secretRef='raw-token'` → DB reject; `secret://cosa-connectors/x` → OK.
- [ ] **Step 4:** migrate + rollback PASS; test PASS.
- [ ] **Step 5:** Commit `feat(company): bank_connections schema (secret-ref only, consent state machine)`

**Acceptance:** không thể lưu access token thô trong DB nghiệp vụ.

---

### Task 38: Company — `ingestion_events` (idempotency layer)

**Files:**
- Modify: `services/company/shared/db/schema/finance-legal.ts`
- Create: `services/company/finance-legal/migrations/<n>_ingestion_events.up.sql` / `.down.sql`
- Test: `services/company/finance-legal/tests/ingestion.test.ts`

**Interfaces:**
- Produces: `ingestionEvents { id: bigint PK, bankConnectionId: bigint FK, providerEventId: text, receivedAt: timestamptz DEFAULT now(), rawPayloadRef: text (blob store ref, không lưu payload thô lớn inline), checksum: text, status: text CHECK IN ('RECEIVED','PROCESSING','PROCESSED','FAILED','DLQ') DEFAULT 'RECEIVED', errorMsg: text NULL, processedAt: timestamptz NULL }` — **UNIQUE(bank_connection_id, provider_event_id)**, index `(status, received_at)`.

- [ ] **Step 1:** Migration up/down + unique.
- [ ] **Step 2:** Drizzle; `npx tsc --noEmit`.
- [ ] **Step 3:** Test thất bại: insert cùng `(bankConnectionId, providerEventId)` 2 lần → lần 2 conflict; helper `recordIngestionEvent` trả `{isNew: false}` khi trùng.
- [ ] **Step 4:** migrate + rollback PASS; test PASS.
- [ ] **Step 5:** Commit `feat(company): ingestion_events idempotency table`

**Acceptance:** cùng provider event id không tạo 2 bản ghi ingestion.

---

### Task 39: Company — `bank_transactions`

**Files:**
- Modify: `services/company/shared/db/schema/finance-legal.ts`
- Create: `services/company/finance-legal/migrations/<n>_bank_transactions.up.sql` / `.down.sql`
- Test: `services/company/finance-legal/tests/bank-transaction.test.ts`

**Interfaces:**
- Produces: `bankTransactions { id: bigint PK, bankConnectionId: bigint FK, providerAccountId: text, externalTransactionId: text, postedDate: date, amount: numeric(18,2), currency: text, counterparty: text NULL, description: text NULL, category: text NULL, mappedStatus: text CHECK IN ('UNMAPPED','PROPOSED','CONFIRMED') DEFAULT 'UNMAPPED', provenance: jsonb NOT NULL (`{source, ingestion_event_id, checksum}`), createdAt, updatedAt }` — **UNIQUE(bank_connection_id, external_transaction_id)**, index `(bank_connection_id, posted_date)`.

- [ ] **Step 1:** Migration up/down + unique.
- [ ] **Step 2:** Drizzle; `npx tsc --noEmit`.
- [ ] **Step 3:** Test thất bại: `upsertBankTransaction` cùng `(bankConnectionId, externalTransactionId)` với `postedDate` đảo thứ tự đến → chỉ 1 row, giữ dữ liệu ổn định (không double).
- [ ] **Step 4:** migrate + rollback PASS; test PASS.
- [ ] **Step 5:** Commit `feat(company): bank_transactions with unique(external_transaction_id) + provenance`

**Acceptance:** replay/out-of-order không tạo transaction kép.

---

### Task 40: Company — `accounting_documents` + `document_reconciliation_proposals`

**Files:**
- Modify: `services/company/shared/db/schema/finance-legal.ts`
- Create: `services/company/finance-legal/migrations/<n>_accounting_documents_and_proposals.up.sql` / `.down.sql`
- Test: `services/company/finance-legal/tests/accounting-document.test.ts` (schema-level)

**Interfaces:**
- Produces:
  - `accountingDocuments { id: bigint PK, workspaceId: bigint, documentType: text, status: text CHECK IN ('DRAFT','REVIEWED','CONFIRMED','VOIDED') DEFAULT 'DRAFT', bankTransactionIds: jsonb DEFAULT '[]', evidenceArtifactIds: jsonb DEFAULT '[]', financialTransactionId: bigint NULL, confirmedByMemberId: bigint NULL, confirmedAt: timestamptz NULL, voidedByMemberId: bigint NULL, voidedAt: timestamptz NULL, correctionOfId: bigint NULL FK self, createdAt, updatedAt }` — index `(workspace_id, status)`.
  - `documentReconciliationProposals { id: bigint PK, workspaceId: bigint, bankTransactionId: bigint FK, proposedDocument: jsonb NOT NULL, confidence: numeric, explanation: text, status: text CHECK IN ('OPEN','ACCEPTED','REJECTED','SUPERSEDED') DEFAULT 'OPEN', founderDecision: text NULL, decidedByMemberId: bigint NULL, createdAt, updatedAt }`.

- [ ] **Step 1:** Migration up/down.
- [ ] **Step 2:** Drizzle; `npx tsc --noEmit`.
- [ ] **Step 3:** Test thất bại: insert document `correctionOfId` trỏ document khác; query "chuỗi correction" trả đúng thứ tự.
- [ ] **Step 4:** migrate + rollback PASS; test PASS.
- [ ] **Step 5:** Commit `feat(company): accounting_documents lifecycle + reconciliation proposals schema`

**Acceptance:** correction là quan hệ dữ liệu (không sửa lịch sử im lặng).

---

### Task 41: Company — `financial_snapshots` + `financial_transactions` provenance

**Files:**
- Modify: `services/company/shared/db/schema/finance-legal.ts`
- Create: `services/company/finance-legal/migrations/<n>_financial_snapshots_and_txn_provenance.up.sql` / `.down.sql`
- Test: `services/company/finance-legal/tests/financial-snapshot.test.ts`

**Interfaces:**
- Produces:
  - `financialSnapshots { id: bigint PK, workspaceId: bigint, period: text (vd '2026-Q3'), regulationVersionId: bigint NULL FK, reviewStatus: text CHECK IN ('DRAFT','REVIEWED') DEFAULT 'DRAFT', isLocked: boolean DEFAULT false, generatedAt: timestamptz DEFAULT now(), lockedByMemberId: bigint NULL, lockedAt: timestamptz NULL }` — UNIQUE(workspace_id, period).
  - `financialTransactions` +`provenance: jsonb DEFAULT '{}'`, +`accountingDocumentId: bigint NULL FK`.

- [ ] **Step 1:** Migration up/down (`ALTER TABLE financial_transactions ADD COLUMN IF NOT EXISTS ...`).
- [ ] **Step 2:** Drizzle; `npx tsc --noEmit`.
- [ ] **Step 3:** Test thất bại: lock snapshot → cố ghi `financial_transaction` với `accountingDocumentId` thuộc period đã lock → service (Task 47) chặn; snapshot không tự set "ready to file".
- [ ] **Step 4:** migrate + rollback PASS; test PASS.
- [ ] **Step 5:** Commit `feat(company): financial_snapshots + transaction provenance columns`

**Acceptance:** mọi `financial_transaction` truy được về document/bank_transaction nguồn qua `provenance` + `accountingDocumentId`.

---

### Task 42: Company — `bank-connection.service.ts` + CRUD endpoints (+ `/revoke`)

**Files:**
- Create: `services/company/finance-legal/services/bank-connection.service.ts`, `services/company/finance-legal/handlers/bank-connection.handler.ts`
- Modify: `services/company/finance-legal/api.ts`
- Test: `services/company/finance-legal/tests/bank-connection.test.ts`

**Interfaces:**
- Produces:
  ```ts
  export interface BankConnectionView { id: string; workspaceId: string; provider: "cas"|"manual"; consentState: "PENDING"|"GRANTED"|"REVOKED"|"EXPIRED"; scopes: string[]; lastSyncedAt: string|null; syncStatus: string; grantExpiresAt: string|null; }
  export async function createBankConnection(p: { workspaceId: bigint; provider: "cas"|"manual"; scopes: string[] }): Promise<BankConnectionView>;   // secretRef set bởi Control Plane callback, không nhận từ client
  export async function listBankConnections(workspaceId: bigint): Promise<BankConnectionView[]>;
  export async function revokeBankConnection(id: bigint, actorMemberId: bigint): Promise<BankConnectionView>;  // consentState='REVOKED', xoá secretRef, syncStatus='DISABLED'
  export async function isGrantActive(id: bigint): Promise<boolean>;  // GRANTED && (grantExpiresAt==null || > now)
  ```
- Endpoints: `GET/POST /finance-legal/bank-connections`, `POST /finance-legal/bank-connections/:id/revoke`. `provider='cas'` chỉ cho phép scope `['balance:read','transactions:read']` — reject scope khác.

- [ ] **Step 1:** Test thất bại: create `provider='cas'` với scope `['transfer']` → `invalidArgument`; `revoke` → `consentState='REVOKED'` + `secretRef` null; `isGrantActive` false sau revoke.
- [ ] **Step 2:** Implement service + handler.
- [ ] **Step 3:** `npx tsc --noEmit`; barrel.
- [ ] **Step 4:** Test PASS + regression.
- [ ] **Step 5:** Commit `feat(company): bank-connection CRUD + revoke (cas read-only scopes enforced)`

**Acceptance:** không xin được transfer/payout scope; revoke chặn sync ngay.

---

### Task 43: Company — `ingestion.service.ts` + `POST /finance-legal/ingestion-events` (internal, verify + dedupe)

**Files:**
- Create: `services/company/finance-legal/services/ingestion.service.ts`, `services/company/finance-legal/handlers/ingestion.handler.ts`
- Modify: `services/company/finance-legal/api.ts`
- Test: `services/company/finance-legal/tests/ingestion.test.ts`

**Interfaces:**
- Produces:
  ```ts
  export interface IngestResult { ingestionEventId: string; isNew: boolean; status: "RECEIVED"|"PROCESSED"|"FAILED"; }
  export async function ingestEvent(p: { bankConnectionId: bigint; providerEventId: string; checksum: string; rawPayloadRef: string }): Promise<IngestResult>;   // upsert theo unique; nếu trùng → {isNew:false}, không xử lý lại
  export async function markProcessed(ingestionEventId: bigint): Promise<void>;
  export async function markFailed(ingestionEventId: bigint, err: string, toDlq: boolean): Promise<void>;
  ```
- Endpoint `POST /finance-legal/ingestion-events` — **internal** (`expose: false` hoặc network-guard + service identity, spec §7.2). Body `{ bankConnectionId, providerEventId, checksum, rawPayloadRef }`. Response 200 kể cả khi trùng (idempotent ack).

- [ ] **Step 1:** Test thất bại: gọi 2 lần cùng `(bankConnectionId, providerEventId)` → lần 2 `isNew=false`, không side effect thêm.
- [ ] **Step 2:** Implement (transaction: insert ingestion_event `onConflictDoNothing`, đọc lại).
- [ ] **Step 3:** Handler (chỉ service identity gọi được); `npx tsc --noEmit`.
- [ ] **Step 4:** Test PASS.
- [ ] **Step 5:** Commit `feat(company): idempotent ingestion-events endpoint (internal, dedupe by provider_event_id)`

**Acceptance:** duplicate ingestion không tạo transaction/document kép ở downstream.

---

### Task 44: Company — `bank-transaction.service.ts` + endpoints; map từ ingestion event

**Files:**
- Create: `services/company/finance-legal/services/bank-transaction.service.ts`, `services/company/finance-legal/handlers/bank-transaction.handler.ts`
- Modify: `services/company/finance-legal/api.ts`, `services/company/shared/events.ts`
- Test: `services/company/finance-legal/tests/bank-transaction.test.ts`

**Interfaces:**
- Consumes: `ingestEvent` (Task 43), `isGrantActive` (Task 42), `appendOutboxEvent`.
- Produces:
  ```ts
  export interface BankTransactionView { id: string; bankConnectionId: string; externalTransactionId: string; postedDate: string; amount: string; currency: string; counterparty: string|null; description: string|null; mappedStatus: "UNMAPPED"|"PROPOSED"|"CONFIRMED"; }
  export async function upsertBankTransactionFromIngestion(p: { bankConnectionId: bigint; ingestionEventId: bigint; rows: Array<{ providerAccountId: string; externalTransactionId: string; postedDate: string; amount: string; currency: string; counterparty?: string; description?: string }> }): Promise<{ inserted: number; skipped: number }>;   // onConflict(bank_connection_id, external_transaction_id) DO NOTHING; emit finance.bank_transaction.ingested cho row mới; skip nếu !isGrantActive
  export async function listBankTransactions(workspaceId: bigint, filter?: { connectionId?: bigint; mappedStatus?: string }): Promise<BankTransactionView[]>;
  export async function recordManualTransaction(p: { workspaceId: bigint; postedDate: string; amount: string; currency: string; direction: "IN"|"OUT"; description: string }): Promise<BankTransactionView>;   // provider='manual' connection tự tạo nếu chưa có
  ```
- Endpoints: `GET /finance-legal/bank-transactions?workspaceId=&connectionId=&mappedStatus=`, `POST /finance-legal/bank-transactions` (manual entry).

- [ ] **Step 1:** Test thất bại: `upsertBankTransactionFromIngestion` 2 lần cùng rows → `inserted` chỉ lần đầu, lần 2 `skipped`; grant revoked → 0 inserted; manual entry → row `provider='manual'`, `mappedStatus='UNMAPPED'`.
- [ ] **Step 2:** Implement service + event builder.
- [ ] **Step 3:** Handlers + barrel; `npx tsc --noEmit`.
- [ ] **Step 4:** Test PASS + regression.
- [ ] **Step 5:** Commit `feat(company): bank-transaction upsert (idempotent) + manual entry + list`

**Acceptance:** giao dịch nhập tay tạo candidate `UNMAPPED`; grant revoke chặn sync.

---

### Task 45: Company — `accounting-regime-policy.service.ts` + endpoints; applicability confirm

**Files:**
- Create: `services/company/finance-legal/services/accounting-regime-policy.service.ts`, `services/company/finance-legal/handlers/accounting-regime-policy.handler.ts`
- Modify: `services/company/finance-legal/api.ts`
- Test: `services/company/finance-legal/tests/regime-policy.test.ts`

**Interfaces:**
- Consumes: `regulationVersions` (Task 20), approval infra (applicability confirm là hành động cần founder).
- Produces:
  ```ts
  export interface RegimePolicyView { id: string; workspaceId: string; mode: string; regulationVersionId: string; effectiveFrom: string; effectiveTo: string|null; requiresCoa: boolean; requiresDoubleEntry: boolean; applicabilityConfirmedAt: string|null; }
  export async function getEffectiveRegimePolicy(workspaceId: bigint, atDate?: string): Promise<RegimePolicyView | null>;
  export async function createRegimePolicy(p: { workspaceId: bigint; mode: string; regulationVersionId: bigint; effectiveFrom: string; requiresCoa?: boolean; requiresDoubleEntry?: boolean }): Promise<RegimePolicyView>;   // chỉ chấp nhận regulationVersionId của source đã CURRENT_LAW còn hiệu lực
  export async function confirmApplicability(p: { workspaceId: bigint; policyId: bigint; approverMemberId: bigint }): Promise<RegimePolicyView>;
  ```
- Endpoints: `GET /finance-legal/accounting-regime-policies?workspaceId=&atDate=`, `POST /finance-legal/accounting-regime-policies`, `POST /finance-legal/accounting-regime-policies/:id/confirm-applicability`.
- **Quy tắc TT58:** `mode` chỉ là nhãn; hành vi (sổ/báo cáo xuất được) do `requiresCoa`/`requiresDoubleEntry` + regulation version quyết định. Nếu `requiresDoubleEntry=false` → downstream dùng transaction/document register, **không** build chart-of-accounts.

- [ ] **Step 1:** Test thất bại: `createRegimePolicy` với version của source `POLICY_WATCH` → `invalidArgument`; `getEffectiveRegimePolicy` chọn đúng theo `atDate`; default `requiresDoubleEntry=false`.
- [ ] **Step 2:** Implement service + handler.
- [ ] **Step 3:** `npx tsc --noEmit`; barrel.
- [ ] **Step 4:** Test PASS.
- [ ] **Step 5:** Commit `feat(company): accounting-regime-policy resolution + human applicability confirmation`

**Acceptance:** không gắn nhãn TT58 chỉ bằng lựa chọn UI; danh mục sổ/báo cáo chỉ xuất khi regulation version xác nhận.

---

### Task 46: Company — `reconciliation-proposal.service.ts` + endpoints (+ `/accept`)

**Files:**
- Create: `services/company/finance-legal/services/reconciliation-proposal.service.ts`, `services/company/finance-legal/handlers/reconciliation-proposal.handler.ts`
- Modify: `services/company/finance-legal/api.ts`
- Test: `services/company/finance-legal/tests/reconciliation.test.ts`

**Interfaces:**
- Consumes: `bankTransactions`, `getEffectiveRegimePolicy` (Task 45).
- Produces:
  ```ts
  export interface ReconciliationProposalView { id: string; bankTransactionId: string; proposedDocument: Record<string,unknown>; confidence: number; explanation: string; status: "OPEN"|"ACCEPTED"|"REJECTED"|"SUPERSEDED"; }
  export async function createProposal(p: { workspaceId: bigint; bankTransactionId: bigint; proposedDocument: Record<string,unknown>; confidence: number; explanation: string }): Promise<ReconciliationProposalView>;
  export async function listProposals(workspaceId: bigint, status?: string): Promise<ReconciliationProposalView[]>;
  export async function acceptProposal(p: { id: bigint; founderMemberId: bigint }): Promise<{ documentId: string }>;   // tạo accounting_document DRAFT từ proposedDocument, mark proposal ACCEPTED, bank_transaction mappedStatus='PROPOSED'
  export async function rejectProposal(p: { id: bigint; founderMemberId: bigint; reason: string }): Promise<ReconciliationProposalView>;
  ```
- Endpoints: `GET/POST /finance-legal/document-reconciliation-proposals`, `PATCH /finance-legal/document-reconciliation-proposals/:id` (reject), `POST /finance-legal/document-reconciliation-proposals/:id/accept`.

- [ ] **Step 1:** Test thất bại: `acceptProposal` → tạo `accounting_documents` `status='DRAFT'`, proposal `ACCEPTED`, bank_transaction `mappedStatus='PROPOSED'`; accept lần 2 → `failedPrecondition` (đã ACCEPTED).
- [ ] **Step 2:** Implement service (transaction) + handler.
- [ ] **Step 3:** `npx tsc --noEmit`; barrel.
- [ ] **Step 4:** Test PASS + regression.
- [ ] **Step 5:** Commit `feat(company): reconciliation proposals + founder accept → draft document`

**Acceptance:** transaction Cas/manual không tự thành chứng từ chính thức — chỉ candidate tới khi founder accept.

---

### Task 47: Company — `accounting-document.service.ts` lifecycle + outbox

**Files:**
- Create: `services/company/finance-legal/services/accounting-document.service.ts`, `services/company/finance-legal/handlers/accounting-document.handler.ts`
- Modify: `services/company/finance-legal/api.ts`, `services/company/shared/events.ts`
- Test: `services/company/finance-legal/tests/accounting-document.test.ts`

**Interfaces:**
- Consumes: `financialSnapshots` (Task 41 — chặn ghi vào period đã lock), `appendOutboxEvent`, `buildAccountingDocumentConfirmedEvent`.
- Produces:
  ```ts
  export interface AccountingDocumentView { id: string; workspaceId: string; documentType: string; status: "DRAFT"|"REVIEWED"|"CONFIRMED"|"VOIDED"; bankTransactionIds: string[]; correctionOfId: string|null; confirmedAt: string|null; }
  export async function createAccountingDocument(p: { workspaceId: bigint; documentType: string; bankTransactionIds: bigint[]; evidenceArtifactIds?: bigint[] }): Promise<AccountingDocumentView>;
  export async function confirmAccountingDocument(p: { id: bigint; founderMemberId: bigint }): Promise<AccountingDocumentView>;   // DRAFT|REVIEWED → CONFIRMED; tạo financial_transaction với provenance; bank_transaction mappedStatus='CONFIRMED'; emit finance.accounting_document.confirmed.v1; reject nếu period đã lock
  export async function voidAccountingDocument(p: { id: bigint; founderMemberId: bigint; reason: string }): Promise<AccountingDocumentView>;   // CONFIRMED → VOIDED (giữ row); không xoá financial_transaction, đánh dấu reversed
  export async function createCorrection(p: { correctionOfId: bigint; founderMemberId: bigint; documentType: string; payload: Record<string,unknown> }): Promise<AccountingDocumentView>;   // document mới correctionOfId trỏ bản cũ
  ```
- Endpoints: `POST /finance-legal/accounting-documents`, `POST /finance-legal/accounting-documents/:id/confirm`, `POST /finance-legal/accounting-documents/:id/void`, `POST /finance-legal/accounting-documents/:id/correct`.

- [ ] **Step 1:** Test thất bại: confirm → `financial_transactions` có 1 row `provenance.accountingDocumentId` set + outbox `finance.accounting_document.confirmed.v1`; confirm document thuộc period đã lock → `failedPrecondition`; void → status `VOIDED`, row vẫn tồn tại; correction tạo document mới link bản cũ.
- [ ] **Step 2:** Implement service (transaction) + event builder.
- [ ] **Step 3:** Handlers + barrel; `npx tsc --noEmit`.
- [ ] **Step 4:** Test PASS + regression `npx vitest run finance-legal/`.
- [ ] **Step 5:** Commit `feat(company): accounting document confirm/void/correct lifecycle + confirmed outbox event`

**Acceptance:** confirm/void có audit; sửa sai bằng correction, không sửa lịch sử; số liệu truy về nguồn.

---

### Task 48: Company — `financial-snapshot.service.ts` + endpoints (+ `/lock`)

**Files:**
- Create: `services/company/finance-legal/services/financial-snapshot.service.ts`, `services/company/finance-legal/handlers/financial-snapshot.handler.ts`
- Modify: `services/company/finance-legal/api.ts`
- Test: `services/company/finance-legal/tests/financial-snapshot.test.ts`

**Interfaces:**
- Consumes: `financialTransactions`, `getEffectiveRegimePolicy`.
- Produces:
  ```ts
  export interface FinancialSnapshotView { id: string; workspaceId: string; period: string; regulationVersionId: string|null; reviewStatus: "DRAFT"|"REVIEWED"; isLocked: boolean; totals: Record<string,string>; }
  export async function generateSnapshot(p: { workspaceId: bigint; period: string }): Promise<FinancialSnapshotView>;   // aggregate confirmed financial_transactions trong period; KHÔNG set "ready to file"
  export async function lockSnapshot(p: { id: bigint; reviewerMemberId: bigint }): Promise<FinancialSnapshotView>;
  export async function listSnapshots(workspaceId: bigint): Promise<FinancialSnapshotView[]>;
  ```
- Endpoints: `GET/POST /finance-legal/financial-snapshots`, `POST /finance-legal/financial-snapshots/:id/lock`.

- [ ] **Step 1:** Test thất bại: `generateSnapshot` tổng đúng từ confirmed transactions; `lockSnapshot` → `isLocked=true`; sau lock, `confirmAccountingDocument` cho period đó (Task 47) bị chặn.
- [ ] **Step 2:** Implement service + handler.
- [ ] **Step 3:** `npx tsc --noEmit`; barrel.
- [ ] **Step 4:** Test PASS.
- [ ] **Step 5:** Commit `feat(company): financial snapshot generate + lock (no auto ready-to-file)`

**Acceptance:** snapshot gắn regulation version + reviewer; không tự đánh dấu sẵn sàng nộp.

---

### Task 49: Agent — finance read/propose/draft/confirm capabilities

**Files:**
- Create: `apps/cosa/capabilities/finance_read.py`
- Modify: `apps/cosa/capabilities/finance_write.py`, `apps/cosa/capabilities/__init__.py`, `apps/cosa/composition/agent_plane.py`
- Test: `tests/apps/cosa/test_finance_read.py`, `tests/apps/cosa/test_finance_write.py`

**Interfaces:**
- Consumes: `CompanyServiceClient` với service identity; Gateway approval infra (bind `run_id + tool_call_id + checkpoint_ref`, spec §7.2).
- Produces:
  - `FINANCE_CONNECTION_READ_SPEC` `id="finance.connection.read"` risk LOW → `GET /finance-legal/bank-connections`.
  - `FINANCE_TRANSACTION_READ_SPEC` `id="finance.transaction.read"` risk LOW → `GET /finance-legal/bank-transactions`.
  - `FINANCE_TRANSACTION_CLASSIFY_PROPOSE_SPEC` `id="finance.transaction.classify.propose"` risk LOW → `POST /finance-legal/document-reconciliation-proposals` (proposal, không tạo document).
  - `FINANCE_ACCOUNTING_DOCUMENT_CREATE_DRAFT_SPEC` `id="finance.accounting_document.create_draft"` risk MEDIUM → `POST /finance-legal/accounting-documents` (status DRAFT).
  - `FINANCE_ACCOUNTING_DOCUMENT_CONFIRM_SPEC` `id="finance.accounting_document.confirm"` risk MEDIUM, **L2** → `POST /finance-legal/accounting-documents/:id/confirm`; handler **phải** có `approval_context` bound; registered ở `agent_plane.py` chỉ khi `os.environ.get("COSA_HARNESS_P0_VERIFIED") == "true"`.
- Guard: assert `FINANCE_PAYOUT_EXECUTE_SPEC` vẫn không tồn tại (test từ Task 14 giữ nguyên).

- [ ] **Step 1:** Test thất bại: 5 spec đúng id/risk; `confirm` handler không có `approval_context` → raise; `agent_plane` không register `confirm` khi env chưa set; payout vẫn absent.
- [ ] **Step 2:** Implement 2 file + register có điều kiện.
- [ ] **Step 3:** `make apps-cosa-test && make boundary-check && make typecheck-py` PASS.
- [ ] **Step 4:** Commit `feat(cosa): finance read/classify/draft/confirm capabilities (confirm gated on Harness-P0)`

**Acceptance:** AI không confirm được nếu thiếu approval bound; payout không đăng ký lại; write prod tắt tới khi Harness-P0 xanh.

---

### Task 50: Flutter — regime-driven TT58 + transaction review + provenance trail

**Files:**
- Modify: `frontend/lib/modules/finance/services/finance_service.dart`, `frontend/lib/modules/finance/services/finance_tt58_service.dart`
- Create: `frontend/lib/modules/finance/screens/transaction_review_screen.dart`, `frontend/lib/modules/finance/screens/document_correction_screen.dart`, `frontend/lib/modules/finance/widgets/provenance_trail.dart`
- Test: `frontend/test/modules/finance/finance_service_test.dart`, `frontend/test/modules/finance/provenance_trail_test.dart`

**Interfaces:**
- `finance_service.dart`: thêm method map 1-1 với endpoint Task 42–48 (typed DTO). Không method nào gọi endpoint không tồn tại.
- `finance_tt58_service.dart`: bỏ mọi `UnimplementedError`; mọi nhánh hiển thị sổ/báo cáo đọc `getAccountingRegimePolicy(workspaceId)` → dùng `requiresCoa`/`requiresDoubleEntry`/`mode`; **không** `if (mode == 'TT58')` hard-code — bảng hiển thị suy từ policy field.
- `transaction_review_screen.dart`: list `bank_transactions` `UNMAPPED`/`PROPOSED` → founder chọn accept proposal → tạo DRAFT document → confirm. Nút confirm ẩn nếu build flag prod và Harness-P0 chưa verified (đọc capability availability từ backend).
- `provenance_trail.dart`: nhận id document/transaction → render chuỗi `financial_transaction ← accounting_document ← bank_transaction ← ingestion_event`.

- [ ] **Step 1:** Test thất bại: `finance_tt58_service` không chứa literal `'TT58'` trong `if`; `provenance_trail` render đủ 4 mắt xích; `finance_service` gọi đúng path.
- [ ] **Step 2:** Implement.
- [ ] **Step 3:** `cd frontend && flutter analyze && flutter test test/modules/finance/`.
- [ ] **Step 4:** Commit `feat(frontend): regime-policy-driven TT58 UI, transaction review flow, provenance trail`

**Acceptance:** mọi số liệu màn hình truy về document/transaction nguồn; không rải `if(TT58)`.

---

### Task 51: Release C — integration & acceptance pass

**Files:**
- Create: `services/company/tests/e2e/finance-ingestion-flow.test.ts`

- [ ] **Step 1:** E2E: tạo `bank_connection` `manual` → `recordManualTransaction` → `bank_transactions` `UNMAPPED` → `createProposal` → `acceptProposal` → DRAFT document → `confirmAccountingDocument` → `financial_transactions` có provenance + outbox `finance.accounting_document.confirmed.v1`.
- [ ] **Step 2:** Correction: `createCorrection` cho document đã confirm → document mới link bản cũ; số liệu snapshot phản ánh correction, không mất lịch sử.
- [ ] **Step 3:** Idempotency: `ingestEvent` cùng `providerEventId` 3 lần + `upsertBankTransactionFromIngestion` với rows out-of-order → đúng 1 `bank_transaction`, 0 document kép.
- [ ] **Step 4:** Grant revoke: `revokeBankConnection` → `upsertBankTransactionFromIngestion` skip toàn bộ; approval hết hạn → `confirmAccountingDocument` không resume được.
- [ ] **Step 5:** Regime: workspace không có `accounting_regime_policy` → Flutter không xuất danh mục sổ; tạo policy với version TT58/2026 + confirm applicability → danh mục xuất theo `requires*` field.
- [ ] **Step 6:** Tenant isolation: user B không đọc `bank_transactions`/`accounting_documents` của user A.
- [ ] **Step 7:** Gate: `make typecheck-py && make boundary-check && make tenancy-check && cd services/company && npx vitest run && cd ../.. && make apps-cosa-test && cd frontend && flutter analyze && flutter test`. **Không** merge nếu typecheck lỗi hoặc contract test chưa xanh trong CI.
- [ ] **Step 8:** Commit `test(company): Release C finance ingestion + document lifecycle + idempotency acceptance`

**Acceptance (spec §13):** giao dịch nhập tay → candidate → founder confirm → sửa sai bằng correction; mọi số liệu màn hình truy về document/transaction nguồn; event duplicate/out-of-order/retry không tạo document/transaction kép; Harness-P0 xanh trước khi bật `confirm` ở prod.

---

## Phase 4 — Release D: Cas.so Read-Only Connector

**Mục tiêu:** Founder kết nối Cas và nhận giao dịch/số dư đã đồng ý chia sẻ, **không có lệnh chi**. Webhook idempotent, sync health hiển thị rõ, agent không thấy secret.

> **DECISION GATE trước khi execute Phase 4:**
> 1. **Task 52 (Cas API/webhook auth spike)** phải xong + ADR duyệt trước khi execute Task 53+. Cần xác nhận từ tài liệu Cas thực tế (https://cas.so/en/general/api/ , .../webhook/): cơ chế verify chữ ký webhook, luồng consent/link/exchange, scope Cas thực cấp, format `external_transaction_id`, retry semantics của Cas.
> 2. Nếu cơ chế verify / scope khác giả định (HMAC-style signature header; scope `balance:read` + `transactions:read`; Cas tự retry) → chạy lại `superpowers:writing-plans` cho Task 54–57.
> 3. Không xin transfer/payout scope trong bất kỳ trường hợp nào.
>
> **Mức chi tiết:** task-level. Tái dùng hạ tầng Release C (`bank_connections`, `ingestion_events`, `bank_transactions`, reconciliation, `accounting_documents`). Không thêm capability mới.

### Phase 4 — File Structure

**Control Plane `services/cosa`:**
- `services/workspace-connector.service.ts` — MODIFY (`:27`): `COSA_CONNECTOR_ALLOWED_KEYS` default vẫn `"sandbox-read"`, nhưng `cas` hợp lệ khi có trong env; production env đặt `"sandbox-read,cas"`. Thêm scope allow-list per key: `cas → ['balance:read','transactions:read']` (reject key khác).
- `services/cas-connector.service.ts` — CREATE: `startCasConsent()`, `handleCasCallback()` (server-to-server exchange), `getCasAuthorizationRef()` (trả `secret://cosa-connectors/cas/<id>`, **không** trả token), `revokeCasAuthorization()`.
- `handlers/cas-connector.handler.ts` — CREATE: `POST /platform/connectors/cas/consent`, `GET/POST /platform/connectors/cas/callback`, `POST /platform/connectors/cas/:id/revoke`.
- `migrations/<n>_cas_connector_authorizations.{up,down}.sql` — CREATE (authorization row: workspace_id, secret_ref, scopes, status, grant_expires_at).
- Tests: `tests/cas-connector.test.ts`.

**Company Service `services/company` (`finance-legal`):**
- `shared/db/schema/finance-legal.ts` — MODIFY: `casWebhookInbox`, `casAccountLinks`.
- `finance-legal/migrations/<n>_cas_webhook_inbox_and_account_links.{up,down}.sql` — CREATE.
- `finance-legal/services/cas-webhook.service.ts` — CREATE: `verifyAndStore()`, `processInboxEntry()`, `retryDlq()`.
- `finance-legal/services/cas-mapper.service.ts` — CREATE: `mapCasAccount()`, `casPayloadToBankTransactionRows()`.
- `finance-legal/handlers/cas-webhook.handler.ts` — CREATE: `POST /finance-legal/cas/webhook` (verify → store inbox → 200 nhanh), `POST /finance-legal/cas/webhook/reprocess/:id`.
- `finance-legal/jobs/cas-inbox-processor.ts` — CREATE: async drain inbox (cron/queue theo pattern hiện có).
- `finance-legal/api.ts` — MODIFY (barrel).
- Tests: `finance-legal/tests/cas-webhook.test.ts`, `finance-legal/tests/cas-mapper.test.ts`.

**Agent Platform:** không file mới. `apps/cosa/capabilities/finance_read.py` / `finance_write.py` (Release C) tái dùng. Thêm guard test: capability handler re-check `isGrantActive` trước side effect.

**Flutter `frontend`:**
- `lib/modules/finance/services/cas_connector_service.dart` — CREATE: `startConsent(workspaceId)`, `getConnectionHealth(connectionId)`, `revoke(connectionId)`.
- `lib/modules/finance/screens/cas_connect_screen.dart` — CREATE: consent flow, hiển thị scope xin cấp.
- `lib/modules/finance/widgets/sync_health_banner.dart` — CREATE: `last_synced_at`, connection state, nguồn "Cas"; lỗi sync → hiện lỗi, **không** trả số 0.
- Tests: `test/modules/finance/cas_connector_service_test.dart`, `test/modules/finance/sync_health_banner_test.dart`.

---

### Task 52: Cas API/webhook auth spike + ADR (DECISION GATE)

**Files:**
- Create: `docs/architecture/adr/ADR-CONNECTOR-CAS-001.md`
- Create: `docs/research/2026-XX-cas-api-webhook-notes.md`

**Interfaces:**
- Produces: ADR chốt — (a) webhook signature verification mechanism (header name, algo, secret nguồn); (b) consent/link/exchange sequence + endpoint Cas; (c) scope thực Cas cấp cho account (xác nhận chỉ read); (d) `external_transaction_id` format + độ ổn định; (e) Cas retry/at-least-once semantics; (f) rate limit. Không code sản phẩm ở task này.

- [ ] **Step 1:** Đọc https://cas.so/en/general/api/ + .../webhook/ ; ghi note (endpoint, auth, payload shape, signature).
- [ ] **Step 2:** Nếu có sandbox Cas — thử consent + nhận 1 webhook thật, capture header/payload.
- [ ] **Step 3:** Viết ADR-CONNECTOR-CAS-001 (ACCEPTED / NEEDS-CLARIFICATION); liệt kê giả định plan này và điểm khác biệt (nếu có).
- [ ] **Step 4:** Nếu ADR lệch giả định "HMAC header + read-only scope + at-least-once" → **dừng, chạy lại `superpowers:writing-plans` cho Task 54–57**.
- [ ] **Step 5:** Commit `docs(connector): ADR-CONNECTOR-CAS-001 Cas API/webhook auth + integration notes`

**Acceptance:** verify mechanism + scope + retry semantics của Cas được ghi rõ, đội đồng ý trước khi viết code inbox.

---

### Task 53: Control Plane — `cas` connector key + scope allow-list + authorization row

**Files:**
- Modify: `services/cosa/services/workspace-connector.service.ts`
- Create: `services/cosa/migrations/<n>_cas_connector_authorizations.up.sql` / `.down.sql`
- Modify: `services/cosa/storage/schema.ts`
- Test: `services/cosa/tests/cas-connector.test.ts`

**Interfaces:**
- Produces:
  - `casConnectorAuthorizations { id: bigint PK, platformWorkspaceId: bigint FK, secretRef: text CHECK LIKE 'secret://cosa-connectors/%', scopes: jsonb DEFAULT '["balance:read","transactions:read"]', status: text CHECK IN ('PENDING','GRANTED','REVOKED','EXPIRED') DEFAULT 'PENDING', grantExpiresAt: timestamptz NULL, createdAt, updatedAt }`.
  - Trong `workspace-connector.service.ts`: `CONNECTOR_SCOPE_ALLOWLIST = { "sandbox-read": [...], "cas": ["balance:read","transactions:read"] }`; helper `assertConnectorKeyAllowed(key, env)` — `cas` chỉ pass khi `COSA_CONNECTOR_ALLOWED_KEYS` chứa `cas`; scope ngoài allow-list → `APIError.invalidArgument`.

- [ ] **Step 1:** Test thất bại: request connector `cas` với scope `transfer` → reject; với env không có `cas` → reject; hợp lệ → tạo authorization `PENDING`.
- [ ] **Step 2:** Migration + Drizzle + scope allow-list logic.
- [ ] **Step 3:** `npx tsc --noEmit`; migrate + rollback PASS.
- [ ] **Step 4:** Test PASS + regression `npx vitest run tests/`.
- [ ] **Step 5:** Commit `feat(cosa): cas connector key + read-only scope allow-list + authorization row`

**Acceptance:** production không dùng mặc định `sandbox-read`; không xin được scope ghi.

---

### Task 54: Control Plane — `cas-connector.service.ts` consent/link/exchange (server-to-server)

**Files:**
- Create: `services/cosa/services/cas-connector.service.ts`, `services/cosa/handlers/cas-connector.handler.ts`
- Modify: `services/cosa/handlers/api.ts`
- Test: `services/cosa/tests/cas-connector.test.ts`

**Interfaces:**
- Consumes: secret manager client (grep client hiện có); Task 52 ADR mechanism.
- Produces:
  ```ts
  export async function startCasConsent(p: { platformWorkspaceId: bigint; redirectUri: string }): Promise<{ consentUrl: string; authorizationId: string }>;
  export async function handleCasCallback(p: { authorizationId: string; code: string }): Promise<{ status: "GRANTED"; secretRef: string }>;   // exchange server-to-server; lưu token vào secret manager, DB chỉ giữ secretRef
  export async function getCasAuthorizationRef(authorizationId: bigint): Promise<string>;   // 'secret://cosa-connectors/cas/<id>' — KHÔNG trả token
  export async function revokeCasAuthorization(authorizationId: bigint): Promise<void>;   // status='REVOKED', xoá secret ở manager
  ```
- Endpoints: `POST /platform/connectors/cas/consent`, `GET /platform/connectors/cas/callback`, `POST /platform/connectors/cas/:id/revoke`. Callback exchange chạy hoàn toàn server-side; token không bao giờ qua Flutter/response.

- [ ] **Step 1:** Test thất bại: `handleCasCallback` (mock Cas exchange) → DB row `GRANTED` có `secretRef`, **không** có cột token; `getCasAuthorizationRef` trả string `secret://...` không phải token.
- [ ] **Step 2:** Implement service (mock secret manager + Cas HTTP trong test) + handlers.
- [ ] **Step 3:** `npx tsc --noEmit`; barrel.
- [ ] **Step 4:** Test PASS.
- [ ] **Step 5:** Commit `feat(cosa): cas consent + server-to-server token exchange (secret-ref only)`

**Acceptance:** token/refresh chỉ ở secret manager; Flutter/agent không nhận secret.

---

### Task 55: Company — `cas_webhook_inbox` + `cas_account_links`

**Files:**
- Modify: `services/company/shared/db/schema/finance-legal.ts`
- Create: `services/company/finance-legal/migrations/<n>_cas_webhook_inbox_and_account_links.up.sql` / `.down.sql`
- Test: `services/company/finance-legal/tests/cas-webhook.test.ts` (schema-level)

**Interfaces:**
- Produces:
  - `casWebhookInbox { id: bigint PK, workspaceId: bigint, webhookId: text, payloadHash: text, rawPayloadRef: text, retryCount: integer DEFAULT 0, status: text CHECK IN ('RECEIVED','PROCESSING','SUCCESS','DLQ') DEFAULT 'RECEIVED', errorMsg: text NULL, receivedAt: timestamptz DEFAULT now(), processedAt: timestamptz NULL }` — **UNIQUE(workspace_id, webhook_id)**, index `(status, received_at)`.
  - `casAccountLinks { id: bigint PK, bankConnectionId: bigint FK, casAccountId: text, workspaceAccountMapping: jsonb, createdAt, updatedAt }` — UNIQUE(bank_connection_id, cas_account_id).

- [ ] **Step 1:** Migration up/down + unique.
- [ ] **Step 2:** Drizzle; `npx tsc --noEmit`.
- [ ] **Step 3:** Test thất bại: insert cùng `(workspaceId, webhookId)` 2 lần → conflict.
- [ ] **Step 4:** migrate + rollback PASS; test PASS.
- [ ] **Step 5:** Commit `feat(company): cas_webhook_inbox (idempotent) + cas_account_links`

**Acceptance:** cùng `webhook_id` không lưu 2 lần.

---

### Task 56: Company — `cas-webhook.service.ts` verify + store inbox; endpoint

**Files:**
- Create: `services/company/finance-legal/services/cas-webhook.service.ts`, `services/company/finance-legal/handlers/cas-webhook.handler.ts`
- Modify: `services/company/finance-legal/api.ts`
- Test: `services/company/finance-legal/tests/cas-webhook.test.ts`

**Interfaces:**
- Consumes: verify mechanism từ ADR (Task 52); `getCasAuthorizationRef` (Task 54) để lấy signing secret qua secret manager.
- Produces:
  ```ts
  export interface WebhookAck { inboxId: string; accepted: boolean; duplicate: boolean; }
  export async function verifyAndStore(p: { workspaceId: bigint; webhookId: string; signature: string; rawBody: string }): Promise<WebhookAck>;   // verify chữ ký; sai → APIError.unauthenticated (KHÔNG lưu); đúng → insert inbox onConflictDoNothing; trả duplicate=true nếu trùng
  ```
- Endpoint `POST /finance-legal/cas/webhook` — verify → store → trả 200 nhanh (không xử lý inline). Signature sai → 401. Payload chưa verify **không** được lưu.

- [ ] **Step 1:** Test thất bại: signature sai → 401 + 0 inbox row; đúng → inbox `RECEIVED`; gửi lại cùng `webhookId` → `duplicate=true`, vẫn 200.
- [ ] **Step 2:** Implement service (verify + store) + handler.
- [ ] **Step 3:** `npx tsc --noEmit`; barrel.
- [ ] **Step 4:** Test PASS.
- [ ] **Step 5:** Commit `feat(company): cas webhook verify + idempotent inbox store`

**Acceptance:** webhook chỉ xử lý sau verify; replay → 200 nhưng không tạo bản ghi mới.

---

### Task 57: Company — `cas-inbox-processor` async: dedupe → map → `bank_transaction` → outbox; retry/DLQ

**Files:**
- Create: `services/company/finance-legal/jobs/cas-inbox-processor.ts`, `services/company/finance-legal/services/cas-mapper.service.ts`
- Modify: `services/company/finance-legal/handlers/cas-webhook.handler.ts` (thêm `POST /finance-legal/cas/webhook/reprocess/:id`)
- Test: `services/company/finance-legal/tests/cas-mapper.test.ts`, `services/company/finance-legal/tests/cas-webhook.test.ts`

**Interfaces:**
- Consumes: `verifyAndStore` output; `upsertBankTransactionFromIngestion` (Task 44); `isGrantActive` (Task 42) + Cas authorization status (Task 53); `casAccountLinks`.
- Produces:
  ```ts
  export function casPayloadToBankTransactionRows(payload: unknown): Array<{ casAccountId: string; externalTransactionId: string; postedDate: string; amount: string; currency: string; counterparty?: string; description?: string }>;
  export async function mapCasAccount(p: { bankConnectionId: bigint; casAccountId: string }): Promise<{ providerAccountId: string } | null>;   // null nếu chưa link → inbox entry giữ RECEIVED, không tạo transaction
  export async function processInboxEntry(inboxId: bigint): Promise<{ status: "SUCCESS"|"DLQ"|"RETRY"; inserted: number }>;   // PROCESSING → dedupe external_transaction_id+checksum → map → upsert bank_transaction (provenance {source:'cas', webhook_id, checksum}) → outbox; lỗi tạm → retryCount++, RETRY; retryCount≥N → DLQ
  export async function retryDlq(inboxId: bigint): Promise<void>;
  ```
- Grant không active (revoked/expired) → `processInboxEntry` trả `DLQ` với `errorMsg='grant inactive'`, **không** tạo transaction.

- [ ] **Step 1:** Test thất bại: 2 inbox entry cùng `externalTransactionId` (replay/out-of-order) → 1 `bank_transaction`; entry với `casAccountId` chưa link → 0 transaction, status không SUCCESS; grant revoked → `DLQ`; lỗi tạm 3 lần → `DLQ`.
- [ ] **Step 2:** Implement mapper + processor + reprocess endpoint.
- [ ] **Step 3:** `npx tsc --noEmit`; wire job theo pattern cron/queue hiện có.
- [ ] **Step 4:** Test PASS + regression `npx vitest run finance-legal/`.
- [ ] **Step 5:** Commit `feat(company): cas inbox async processor (dedupe, account mapping, retry/DLQ)`

**Acceptance:** cùng webhook nhiều lần → 1 `bank_transaction`; mất consent → DLQ + báo lỗi, không dữ liệu giả.

---

### Task 58: Agent + Company — grant re-check trước side effect + compensate

**Files:**
- Modify: `apps/cosa/capabilities/finance_write.py` (`finance.accounting_document.create_draft` / `confirm` handler)
- Modify: `services/company/finance-legal/services/accounting-document.service.ts` (guard)
- Test: `tests/apps/cosa/test_finance_write.py`, `services/company/finance-legal/tests/accounting-document.test.ts`

**Interfaces:**
- Produces: trước mọi side effect finance dùng dữ liệu Cas, handler gọi `GET /finance-legal/bank-connections` → nếu connection nguồn `consentState != 'GRANTED'` hoặc grant hết hạn → raise `PermissionError("connector grant inactive")`, **không** thực thi. Nếu grant revoke **sau** approval nhưng **trước** execute → skip + ghi audit `compensated=true` (không tạo document; đánh dấu proposal `SUPERSEDED`).

- [ ] **Step 1:** Test thất bại: approval bound OK nhưng grant `REVOKED` giữa chừng → `confirmAccountingDocument` không tạo `financial_transaction`; audit có `compensated=true`.
- [ ] **Step 2:** Implement guard 2 phía.
- [ ] **Step 3:** `make apps-cosa-test && cd services/company && npx vitest run finance-legal/`.
- [ ] **Step 4:** Commit `feat(cosa): re-check connector grant before finance side effect + compensate on revoke`

**Acceptance:** approval hết hạn / grant revoke không resume được execution (spec §13).

---

### Task 59: Flutter — Cas connect + sync health UI

**Files:**
- Create: `frontend/lib/modules/finance/services/cas_connector_service.dart`, `frontend/lib/modules/finance/screens/cas_connect_screen.dart`, `frontend/lib/modules/finance/widgets/sync_health_banner.dart`
- Modify: `frontend/lib/modules/finance/screens/transaction_review_screen.dart` (hiện `sync_health_banner`)
- Test: `frontend/test/modules/finance/cas_connector_service_test.dart`, `frontend/test/modules/finance/sync_health_banner_test.dart`

**Interfaces:**
- `cas_connector_service.dart`: `startConsent(workspaceId)` → mở `consentUrl` từ Control Plane; `getConnectionHealth(connectionId)` → `{consentState, lastSyncedAt, syncStatus}`; `revoke(connectionId)`.
- `cas_connect_screen.dart`: hiển thị **rõ** scope xin cấp (`balance:read`, `transactions:read`), không nhắc transfer.
- `sync_health_banner.dart`: 3 trạng thái — GRANTED+recent (xanh, `last_synced_at`), STALE (vàng), REVOKED/EXPIRED/DLQ (đỏ + CTA). Khi lỗi → hiện lỗi, **không** hiển thị số dư 0 hay danh sách rỗng như thể "không có giao dịch".

- [ ] **Step 1:** Test thất bại: `getConnectionHealth` trả `REVOKED` → banner đỏ + không render "0₫"; scope list hiển thị đúng 2 scope read.
- [ ] **Step 2:** Implement.
- [ ] **Step 3:** `cd frontend && flutter analyze && flutter test test/modules/finance/`.
- [ ] **Step 4:** Commit `feat(frontend): cas connect screen + sync health banner (no fake zeros on error)`

**Acceptance:** mọi số liệu Cas hiển thị `last_synced_at` + connection state + nguồn; lỗi sync không bị che bằng dữ liệu giả.

---

### Task 60: Release D — integration & acceptance pass

**Files:**
- Create: `services/company/tests/e2e/cas-connector-flow.test.ts`

- [ ] **Step 1:** E2E (mock Cas): consent → `handleCasCallback` → `bank_connection` `GRANTED` (secretRef only) → webhook verify OK → inbox `RECEIVED` → processor → `bank_transaction` với `provenance.source='cas'` → reconciliation proposal → founder confirm → `financial_transaction`.
- [ ] **Step 2:** Idempotency: cùng webhook payload gửi 5 lần (verify OK mỗi lần) → 1 inbox row hoạt động, 1 `bank_transaction`.
- [ ] **Step 3:** Out-of-order: 2 webhook cùng `externalTransactionId`, `postedDate` đảo → 1 `bank_transaction`.
- [ ] **Step 4:** Consent loss: `revokeCasAuthorization` → webhook mới → inbox `DLQ`, Flutter banner đỏ, không số 0 giả.
- [ ] **Step 5:** Signature sai → 401, 0 inbox row.
- [ ] **Step 6:** Security: agent/Flutter không đọc được secret (grep response payload không chứa token); registry không có capability transfer/payout.
- [ ] **Step 7:** Tenant isolation: webhook workspace A không tạo dữ liệu ở workspace B.
- [ ] **Step 8:** Gate: `make typecheck-py && make boundary-check && make tenancy-check && cd services/cosa && npx vitest run && cd ../company && npx vitest run && cd ../.. && make apps-cosa-test && cd frontend && flutter analyze && flutter test`.
- [ ] **Step 9:** Commit `test(company): Release D cas connector dedupe + consent-loss + secret-isolation acceptance`

**Acceptance (spec §13):** cùng webhook gửi lại nhiều lần → 1 `bank_transaction`; mất consent / token hết hạn → chặn sync + báo rõ (không trả 0 / dữ liệu giả); agent không thấy secret; không có capability transfer/payout.

---

## Phase 5 — Release E: AI Operating Loops & Scale

**Mục tiêu:** AI thực sự điều hành bằng vòng **proposal → approval → execution** trên dữ liệu đã kiểm chứng (evidence, stage, cash/runway, obligation due). Không action write nào chạy ngoài Gateway + approval đúng scope.

> **DECISION GATE trước khi execute Phase 5:**
> 1. **Harness-P1** (output contracts + JSON Schema validator) chạy track song song. Task 65 (validator) và Task 63/64 (AI proposal) phụ thuộc contract cuối `ActionProposalV1` / `SupportDraftV1` / `ResearchBriefV1`. Không bật `operations.task.create_draft` ở **production** tới khi validator từ chối được claim thiếu evidence (`insufficient_evidence`).
> 2. Release E xây trên `financial_snapshots` (Release C) + obligation instances (Release B) đã có dữ liệu thật ở staging.
> 3. Nếu contract Harness-P1 khác giả định trong Task 65 → chạy lại `superpowers:writing-plans` cho Task 63–65.
>
> **Mức chi tiết:** task-level. Context assembler **deterministic** (code, không LLM); LLM chỉ sinh proposal; validator + founder approval đứng giữa proposal và execute.

### Phase 5 — File Structure

**Company Service `services/company` (`operations`):**
- `shared/db/schema/strategy.ts` — MODIFY: `nextBestActions`, `weeklyReviews`.
- `shared/db/schema/operations.ts` — MODIFY: `taskExecutionRecords`.
- `operations/migrations/<n>_next_best_actions.{up,down}.sql`
- `operations/migrations/<n>_weekly_reviews.{up,down}.sql`
- `operations/migrations/<n>_task_execution_records.{up,down}.sql`
- `operations/strategy/services/next-best-action.service.ts` — CREATE: `assembleContext()` (deterministic), `createProposal()`, `acceptProposal()`.
- `operations/strategy/services/weekly-review.service.ts` — CREATE.
- `operations/strategy/handlers/next-best-action.handler.ts`, `weekly-review.handler.ts` — CREATE; `operations/api.ts` — MODIFY.
- `operations/services/task-execution-record.service.ts` — CREATE: `recordExecution()` (dùng bởi mọi capability tạo task).
- `shared/events.ts` — MODIFY: `NEXT_BEST_ACTION_ACCEPTED = "strategy.next_best_action.accepted"`, `WEEKLY_REVIEW_COMPLETED = "operations.weekly_review.completed"`.
- Tests: `operations/tests/{next-best-action,weekly-review,task-execution-record}.test.ts`.

**Agent Platform:**
- `apps/cosa/capabilities/operations_write.py` — CREATE: `OPERATIONS_TASK_CREATE_DRAFT_SPEC` (LOW/L1).
- `apps/cosa/capabilities/venture_stage.py` — CREATE: `VENTURE_STAGE_ASSESS_SPEC` (LOW/L0), `VENTURE_STAGE_TRANSITION_PROPOSE_SPEC` (LOW/L1 — propose only).
- `apps/cosa/harness/output_contracts.py` — CREATE: `ActionProposalV1`, `SupportDraftV1`, `ResearchBriefV1` pydantic/JSON Schema + `validate_output(contract, payload)`.
- `apps/cosa/harness/evidence_guard.py` — CREATE: `require_evidence(refs)` → raise `InsufficientEvidence` nếu ref không resolve về evidence/finance/legal thật.
- `apps/cosa/composition/agent_plane.py`, `apps/cosa/capabilities/__init__.py` — MODIFY: register (gated `COSA_HARNESS_P1_VERIFIED`).
- Tests: `tests/apps/cosa/test_output_contracts.py`, `test_evidence_guard.py`, `test_operations_capabilities.py`, `test_venture_stage_capabilities.py`.

**Flutter `frontend`:**
- `lib/modules/strategy/services/next_best_action_service.dart` — CREATE.
- `lib/modules/strategy/screens/weekly_review_screen.dart` — CREATE: plan có citation tới evidence/finance/obligation.
- `lib/modules/strategy/widgets/action_proposal_card.dart` — CREATE: hiện `decision_reason` + refs + `capability_required` + nút accept.
- `lib/modules/workspace/screens/upgrade_and_members_screen.dart` — CREATE: feature upgrade + multi-member controls (gated theo entitlement).
- Tests: `test/modules/strategy/next_best_action_service_test.dart`, `test/modules/strategy/weekly_review_screen_test.dart`.

---

### Task 61: Company — `strategy.next_best_actions`

**Files:**
- Modify: `services/company/shared/db/schema/strategy.ts`
- Create: `services/company/operations/migrations/<n>_next_best_actions.up.sql` / `.down.sql`
- Test: `services/company/operations/tests/next-best-action.test.ts` (schema-level)

**Interfaces:**
- Produces: `nextBestActions { id: bigint PK, workspaceId: bigint, source: text CHECK IN ('evidence','finance','legal','stage'), recommendation: text, priority: integer, dueBy: date NULL, status: text CHECK IN ('PROPOSED','ACCEPTED','REJECTED','DONE') DEFAULT 'PROPOSED', capabilityRequired: text NULL, decisionReason: text NOT NULL, contextSnapshot: jsonb NOT NULL, evidenceRefs: jsonb DEFAULT '[]', regulationRefs: jsonb DEFAULT '[]', createdAt, updatedAt }` — index `(workspace_id, status, priority)`.

- [ ] **Step 1:** Migration up/down.
- [ ] **Step 2:** Drizzle; `npx tsc --noEmit`.
- [ ] **Step 3:** Test thất bại: insert action `source='finance'` không `decisionReason` → DB reject (NOT NULL); query theo `(workspace_id, status='PROPOSED')` order by priority.
- [ ] **Step 4:** migrate + rollback PASS; test PASS.
- [ ] **Step 5:** Commit `feat(company): strategy.next_best_actions schema`

**Acceptance:** mọi action lưu `decision_reason` + `context_snapshot` (giải thích được).

---

### Task 62: Company — `strategy.weekly_reviews` + `operations.task_execution_records`

**Files:**
- Modify: `services/company/shared/db/schema/strategy.ts`, `services/company/shared/db/schema/operations.ts`
- Create: `services/company/operations/migrations/<n>_weekly_reviews.{up,down}.sql`, `<n>_task_execution_records.{up,down}.sql`
- Test: `services/company/operations/tests/weekly-review.test.ts`, `operations/tests/task-execution-record.test.ts`

**Interfaces:**
- Produces:
  - `weeklyReviews { id: bigint PK, workspaceId: bigint, weekStartDate: date, taskCompletionRate: numeric NULL, evidenceSummary: text NULL, nextActions: jsonb DEFAULT '[]', decisionRecordId: bigint NULL FK, reviewStatus: text CHECK IN ('DRAFT','COMPLETED') DEFAULT 'DRAFT', createdAt, updatedAt }` — UNIQUE(workspace_id, week_start_date).
  - `taskExecutionRecords { id: bigint PK, taskId: bigint FK, runId: text, toolCallId: text, approvalId: text NULL, createdByCapability: text, createdAt }` — UNIQUE(run_id, tool_call_id).

- [ ] **Step 1:** Migrations up/down + unique.
- [ ] **Step 2:** Drizzle; `npx tsc --noEmit`.
- [ ] **Step 3:** Test thất bại: 2 `taskExecutionRecords` cùng `(runId, toolCallId)` → conflict; `weeklyReviews` cùng `(workspaceId, weekStartDate)` → conflict.
- [ ] **Step 4:** migrate + rollback PASS; test PASS.
- [ ] **Step 5:** Commit `feat(company): weekly_reviews + task_execution_records schema`

**Acceptance:** mỗi task do capability tạo truy được `run_id + tool_call_id + approval_id + created_by_capability`.

---

### Task 63: Company — `next-best-action.service.ts` deterministic context + proposal + accept

**Files:**
- Create: `services/company/operations/strategy/services/next-best-action.service.ts`, `services/company/operations/strategy/handlers/next-best-action.handler.ts`
- Modify: `services/company/operations/api.ts`, `services/company/shared/events.ts`
- Test: `services/company/operations/tests/next-best-action.test.ts`

**Interfaces:**
- Consumes: `getVentureProfile` (Task 29), `assessVentureStage` (Task 10), `generateSnapshot`/`listSnapshots` (Task 48), `listObligationInstances` (Task 28), evidence list (strategy hiện có).
- Produces:
  ```ts
  export interface NbaContext { ventureProfile: unknown; stage: string; cashRunwayMonths: number|null; obligationsDue: Array<{ id: string; title: string; dueDate: string }>; evidenceGaps: string[]; }
  export async function assembleContext(workspaceId: bigint): Promise<NbaContext>;   // deterministic — 0 LLM call
  export interface NbaProposalInput { workspaceId: bigint; source: "evidence"|"finance"|"legal"|"stage"; recommendation: string; priority: number; dueBy?: string; capabilityRequired?: string; decisionReason: string; evidenceRefs: string[]; regulationRefs: string[]; contextSnapshot: NbaContext; }
  export async function createProposal(p: NbaProposalInput): Promise<{ id: string }>;   // validate: nếu capabilityRequired set → phải là capability id tồn tại & risk ∈ {LOW,MEDIUM}; evidenceRefs phải resolve
  export async function acceptProposal(p: { id: bigint; founderMemberId: bigint }): Promise<{ id: string; taskId?: string }>;   // status='ACCEPTED'; nếu capabilityRequired → KHÔNG tự execute, chỉ mở đường cho Gateway; emit strategy.next_best_action.accepted
  export async function listActions(workspaceId: bigint, status?: string): Promise<unknown[]>;
  ```
- Endpoints: `GET/POST /strategy/next-best-actions`, `POST /strategy/next-best-actions/:id/accept`.

- [ ] **Step 1:** Test thất bại: `assembleContext` không gọi LLM (mock/spy); `createProposal` với `capabilityRequired='finance.payout.execute'` → `invalidArgument` (không tồn tại); với `evidenceRefs=['bogus']` → `invalidArgument`; `acceptProposal` không tạo side effect ngoài status + event.
- [ ] **Step 2:** Implement service + handler + event builder.
- [ ] **Step 3:** `npx tsc --noEmit`; barrel.
- [ ] **Step 4:** Test PASS + regression `npx vitest run operations/`.
- [ ] **Step 5:** Commit `feat(company): next-best-action deterministic context + validated proposal + accept`

**Acceptance:** context gom bằng code; proposal có capability không hợp lệ hoặc evidence giả bị từ chối; accept không auto-execute.

---

### Task 64: Company — `weekly-review.service.ts` + endpoints (+ `/complete`)

**Files:**
- Create: `services/company/operations/strategy/services/weekly-review.service.ts`, `services/company/operations/strategy/handlers/weekly-review.handler.ts`
- Modify: `services/company/operations/api.ts`, `services/company/shared/events.ts`
- Test: `services/company/operations/tests/weekly-review.test.ts`

**Interfaces:**
- Consumes: `assembleContext` (Task 63), task list (operations), `createDecisionRecord` (Task 22).
- Produces:
  ```ts
  export interface WeeklyReviewView { id: string; workspaceId: string; weekStartDate: string; taskCompletionRate: number|null; evidenceSummary: string|null; nextActions: unknown[]; decisionRecordId: string|null; reviewStatus: "DRAFT"|"COMPLETED"; }
  export async function generateWeeklyReview(p: { workspaceId: bigint; weekStartDate: string }): Promise<WeeklyReviewView>;   // tính taskCompletionRate từ tasks tuần đó; nextActions = listActions(status='PROPOSED'); mỗi entry kèm evidence/regulation refs
  export async function completeWeeklyReview(p: { id: bigint; founderMemberId: bigint; decision: "accepted"|"deferred"; notes: string }): Promise<WeeklyReviewView>;   // tạo decision_record link; reviewStatus='COMPLETED'; emit operations.weekly_review.completed
  export async function listWeeklyReviews(workspaceId: bigint): Promise<WeeklyReviewView[]>;
  ```
- Endpoints: `GET/POST /operations/weekly-reviews`, `POST /operations/weekly-reviews/:id/complete`.

- [ ] **Step 1:** Test thất bại: `generateWeeklyReview` → `nextActions` mỗi item có ≥1 ref (evidence/finance/legal); `completeWeeklyReview` tạo `decision_records` row link `decisionRecordId` + outbox event.
- [ ] **Step 2:** Implement service + handler + event builder.
- [ ] **Step 3:** `npx tsc --noEmit`; barrel.
- [ ] **Step 4:** Test PASS + regression.
- [ ] **Step 5:** Commit `feat(company): weekly review generate + complete with decision record link`

**Acceptance:** weekly plan có citation tới evidence/tài chính/nghĩa vụ; complete để lại decision record bất biến.

---

### Task 65: Agent — Harness-P1 output contracts + evidence guard

**Files:**
- Create: `apps/cosa/harness/output_contracts.py`, `apps/cosa/harness/evidence_guard.py`
- Test: `tests/apps/cosa/test_output_contracts.py`, `tests/apps/cosa/test_evidence_guard.py`

**Interfaces:**
- Produces:
  ```python
  class ActionProposalV1(BaseModel): ...   # workspace_id, recommendation, decision_reason, evidence_refs: list[str], regulation_refs: list[str], capability_required: str | None, priority: int
  class SupportDraftV1(BaseModel): ...
  class ResearchBriefV1(BaseModel): ...
  def validate_output(contract: type[BaseModel], payload: dict) -> BaseModel   # raise OutputContractError với path lỗi
  class InsufficientEvidence(Exception): ...
  async def require_evidence(refs: list[str], *, client) -> None   # resolve từng ref qua Company Service; rỗng hoặc không resolve → raise InsufficientEvidence("insufficient_evidence")
  ```
- `validate_output` là JSON-Schema-based (export schema để CI dùng).

- [ ] **Step 1:** Test thất bại: `validate_output(ActionProposalV1, {})` → `OutputContractError`; `require_evidence([])` → `InsufficientEvidence`; `require_evidence(['ev_real'])` (mock resolve OK) → pass.
- [ ] **Step 2:** Implement contracts + guard.
- [ ] **Step 3:** `make apps-cosa-test && make typecheck-py && make boundary-check` PASS.
- [ ] **Step 4:** Commit `feat(cosa): Harness-P1 output contracts (ActionProposalV1/SupportDraftV1/ResearchBriefV1) + evidence guard`

**Acceptance:** claim không có evidence hợp lệ → `insufficient_evidence`; output sai contract bị chặn trước khi tới founder.

---

### Task 66: Agent — `operations.task.create_draft` + `venture.stage.assess` / `transition.propose`

**Files:**
- Create: `apps/cosa/capabilities/operations_write.py`, `apps/cosa/capabilities/venture_stage.py`
- Modify: `apps/cosa/capabilities/__init__.py`, `apps/cosa/composition/agent_plane.py`
- Test: `tests/apps/cosa/test_operations_capabilities.py`, `tests/apps/cosa/test_venture_stage_capabilities.py`

**Interfaces:**
- Consumes: `validate_output` + `require_evidence` (Task 65); `wrap_advisory` (Task 31); `CompanyServiceClient` service identity.
- Produces:
  - `OPERATIONS_TASK_CREATE_DRAFT_SPEC` `id="operations.task.create_draft"` risk LOW → input `{workspace_id, title, evidence_refs, regulation_refs?, finance_justification?}`; handler gọi `require_evidence(evidence_refs)` trước; tạo task **DRAFT** (endpoint task hiện có, trạng thái chờ founder). Register ở `agent_plane` chỉ khi `COSA_HARNESS_P1_VERIFIED == "true"`.
  - `VENTURE_STAGE_ASSESS_SPEC` `id="venture.stage.assess"` risk LOW → `POST /operations/strategy/venture-stage/assess` (Task 11) → `wrap_advisory(label="insight", ...)`.
  - `VENTURE_STAGE_TRANSITION_PROPOSE_SPEC` `id="venture.stage.transition.propose"` risk LOW → **không** gọi `/transition`; trả `wrap_advisory(label="proposal", ...)` với `toStage` + blockers từ assess. Founder tự transition qua UI/Gateway.

- [ ] **Step 1:** Test thất bại: `operations.task.create_draft` với `evidence_refs=[]` → `InsufficientEvidence`; task tạo ra ở trạng thái DRAFT; `venture.stage.transition.propose` không phát HTTP tới `/transition` (spy 0 mutating call); `agent_plane` không register `create_draft` khi env chưa set.
- [ ] **Step 2:** Implement + register có điều kiện.
- [ ] **Step 3:** `make apps-cosa-test && make boundary-check && make typecheck-py` PASS.
- [ ] **Step 4:** Commit `feat(cosa): operations.task.create_draft (evidence-gated) + venture stage assess/propose capabilities`

**Acceptance:** task từ AI luôn DRAFT chờ founder; stage transition chỉ propose; write gated trên Harness-P1.

---

### Task 67: Agent + Company — `task_execution_records` wiring

**Files:**
- Create: `services/company/operations/services/task-execution-record.service.ts`, handler nội bộ `POST /operations/internal/task-execution-records`
- Modify: `apps/cosa/capabilities/operations_write.py` (ghi record sau khi tạo task), Gateway execute path
- Test: `services/company/operations/tests/task-execution-record.test.ts`, `tests/apps/cosa/test_operations_capabilities.py`

**Interfaces:**
- Produces:
  ```ts
  export async function recordExecution(p: { taskId: bigint; runId: string; toolCallId: string; approvalId?: string; createdByCapability: string }): Promise<{ id: string }>;   // onConflict(run_id, tool_call_id) DO NOTHING (idempotent)
  ```
- Mọi capability tạo task/document qua Gateway → sau side effect gọi `recordExecution` với `run_id + tool_call_id + approval_id` từ execution context (spec §5.3/§7.2).

- [ ] **Step 1:** Test thất bại: chạy `operations.task.create_draft` qua Gateway (mock) → `task_execution_records` có 1 row với đủ 4 field; chạy lại cùng `(runId, toolCallId)` → không nhân đôi.
- [ ] **Step 2:** Implement service + internal handler + wire vào capability handler.
- [ ] **Step 3:** `npx tsc --noEmit`; `make apps-cosa-test`.
- [ ] **Step 4:** Commit `feat(cosa): record task execution provenance (run_id + tool_call_id + approval_id + capability)`

**Acceptance:** truy được task nào do capability nào tạo, dưới approval nào.

---

### Task 68: Flutter — weekly review + action proposal + upgrade/members

**Files:**
- Create: `frontend/lib/modules/strategy/services/next_best_action_service.dart`, `frontend/lib/modules/strategy/screens/weekly_review_screen.dart`, `frontend/lib/modules/strategy/widgets/action_proposal_card.dart`, `frontend/lib/modules/workspace/screens/upgrade_and_members_screen.dart`
- Modify: `frontend/lib/shared/providers/entitlement_provider.dart` (gate multi-member)
- Test: `frontend/test/modules/strategy/next_best_action_service_test.dart`, `frontend/test/modules/strategy/weekly_review_screen_test.dart`

**Interfaces:**
- `next_best_action_service.dart`: `getActions(workspaceId, status)`, `acceptAction(id)` → `POST /strategy/next-best-actions/:id/accept`.
- `weekly_review_screen.dart`: render review với mỗi `nextAction` hiện citation (evidence/finance/obligation refs); nút "Hoàn tất review" → `/complete` với decision.
- `action_proposal_card.dart`: hiện `decision_reason` + `capability_required` + refs; accept → chỉ đổi status, không tự execute (execute đi qua Gateway approval riêng).
- `upgrade_and_members_screen.dart`: chỉ hiện invite member / automation nếu `entitlement.hasFeature('multi_member')` / `hasFeature('automation')`.

- [ ] **Step 1:** Test thất bại: `action_proposal_card` với `capabilityRequired` set → hiện badge "cần phê duyệt"; accept không gọi endpoint execute; `upgrade_and_members_screen` ẩn invite khi `hasFeature('multi_member')==false`.
- [ ] **Step 2:** Implement.
- [ ] **Step 3:** `cd frontend && flutter analyze && flutter test test/modules/strategy/`.
- [ ] **Step 4:** Commit `feat(frontend): weekly review + action proposal card + entitlement-gated upgrade/members`

**Acceptance:** weekly plan hiển thị citation; accept ≠ execute; feature trưởng thành gate theo entitlement.

---

### Task 69: Release E — integration & acceptance pass

**Files:**
- Create: `services/company/tests/e2e/ai-operating-loop.test.ts`

- [ ] **Step 1:** E2E: seed workspace ở S3 với evidence + `financial_snapshot` + obligation due → `assembleContext` (deterministic, 0 LLM) → `createProposal` (`source='finance'`, evidence refs thật) → founder `acceptProposal` → không side effect ngoài status/event.
- [ ] **Step 2:** `generateWeeklyReview` → `nextActions` mỗi item có ≥1 citation; `completeWeeklyReview` → `decision_records` row bất biến + outbox `operations.weekly_review.completed`.
- [ ] **Step 3:** `operations.task.create_draft` (agent) với `evidence_refs=[]` → `insufficient_evidence`; với refs thật → task DRAFT + `task_execution_records` có `run_id + tool_call_id + approval_id`.
- [ ] **Step 4:** Payout guard: prompt yêu cầu "chuyển tiền / payout" → registry không có capability nào khớp; `createProposal` với `capabilityRequired='finance.payout.execute'` → `invalidArgument`.
- [ ] **Step 5:** Approval scope: execute capability write không có approval bound đúng `run_id+tool_call_id+checkpoint_ref` → deny.
- [ ] **Step 6:** Tenant isolation: user B không đọc `next_best_actions` / `weekly_reviews` của user A.
- [ ] **Step 7:** Gate: `make typecheck-py && make boundary-check && make tenancy-check && cd services/company && npx vitest run && cd ../.. && make apps-cosa-test && cd frontend && flutter analyze && flutter test && make e2e-test`.
- [ ] **Step 8:** Commit `test(company): Release E AI operating loop — citations, evidence gate, payout deny acceptance`

**Acceptance (spec §13):** AI tạo weekly plan có citation tới evidence/tài chính/nghĩa vụ; action write chỉ sau policy + approval đúng scope; AI không gọi được payout/transfer dù prompt yêu cầu.

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

**Thứ tự trong từng Phase (song song hoá được chỗ nào):**

- **Phase 2 (B):** schema Task 20→21→22 tuần tự (FK); Task 23 (seed) sau 21; Task 24 (migrate legacy) sau 21. Service Task 25–29 song song sau schema (25 cần 20; 27 cần 21+29; 28 cần 21). Task 30 sau 26. Agent Task 31→(32,33) song song. Flutter Task 34 sau 25–28. Task 35 chốt.
- **Phase 3 (C):** DECISION GATE trước tiên. Schema Task 36–41 song song (độc lập nhau). Service: 42→43→44 tuần tự; 45 độc lập; 46 cần 44+45; 47 cần 40+41+46; 48 cần 41+47. Agent Task 49 cần 44–47. Flutter Task 50 cần 45–48. Task 51 chốt.
- **Phase 4 (D):** Task 52 (spike/ADR) **chặn tất cả**. Task 53→54 tuần tự (Control Plane). Task 55 độc lập. Task 56 cần 54+55; Task 57 cần 44+56. Task 58 cần 42+57. Flutter Task 59 cần 54+57. Task 60 chốt.
- **Phase 5 (E):** DECISION GATE (Harness-P1 contract). Schema Task 61,62 song song. Task 63 cần 10+28+48+61. Task 64 cần 22+63. Agent Task 65→66 tuần tự; 66 cần 11+65. Task 67 cần 62+66. Flutter Task 68 cần 63+64. Task 69 chốt.

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
- §5.2 Control Plane tables → Task 1–2, 18. §5.3 local workspace + lifecycle → Task 7–13. §5.3 "một stage transition hợp lệ" 5 điều kiện → Task 10 (đọc stage từ DB, check policy, proposal 409, transaction update+journal+outbox, lùi có reason). §6.1 onboarding 5 bước → Task 17 + Task 29 (venture-profile persist). §6.2 entitlement free → Task 2/3/6/17. §7.1 mô hình quyền L0/L1/L2 → nhãn risk/level ghi ở từng capability task (32, 33, 49, 66). §7.2 capability list đầy đủ → `finance.payout.execute` cấm: Task 14 + guard Task 49/63; `venture.profile.*` + `strategy.*` → Task 32–33; `finance.connection/transaction/accounting_document.*` → Task 49; `legal.applicability.assess` + `legal.obligation.create_draft` → Task 32; `venture.stage.assess` + `transition.propose` → Task 66. §7.3 decision record chuẩn → Task 22 (schema) + Task 64 (weekly review link). §8.1 kiến trúc TT58 (regulation catalog / applicability / bank connection / ingestion / bank transaction / accounting document / snapshot) → Task 20, 27, 37, 38, 39, 40, 41, 45–48. §8.2 luồng Cas read-only + 7 yêu cầu bắt buộc → Task 52–60. §9 legal workspace → Task 20–28, 34. §10.2 sửa Flutter/agent → Task 14–17 (Release A) + Task 50/59/68 (release sau). §11 migration/back-compat → Task 18, 24 + mọi `.down.sql` + rollback round-trip mỗi task DB. §12 Release A–E → Phase 1–5. §13 test bắt buộc (8 case) → Task 19, 35, 51, 60, 69 (mỗi Release có tenant isolation + idempotency + approval-expiry + payout-deny). §14 thứ tự ưu tiên → dependency graph + DECISION GATE đầu Phase 3/4/5. §15 quyết định giữ xuyên suốt → Global Constraints.
- **Gap có chủ đích (task-level, không phải placeholder):** code/test cụ thể từng dòng cho Task 20–69 để implementer viết theo TDD từ khối Interfaces; các quyết định phụ thuộc gate ngoài (Harness-P0/P1 contract cuối, ADR-CONNECTOR-CAS-001, kết luận COA cho TT58 mode) — mỗi chỗ đã đánh dấu "chạy lại `superpowers:writing-plans` cho Task X–Y" ngay tại DECISION GATE.

**Placeholder scan:** Task 1–19 (Release A) có block code/test thật ở mọi step. Task 20–69 (Release B–E) ở mức task-level theo lựa chọn "1 file gộp, task-level": mỗi task có Files + Interfaces (chữ ký + kiểu cụ thể, không "TBD") + step TDD gọn + Acceptance + commit message. Không có "implement later" / "add error handling" trần — mọi hành vi cần test đều nêu rõ assertion trong Step 1. Điểm cần chốt ngoài repo được gọi tên cụ thể (không mơ hồ) ở DECISION GATE.

**Type consistency:** `provisionVentureWorkspace` / `ProvisionResult` (Task 3) → Task 4. `WorkspaceMembershipInfo` (Task 5) → Task 8. `assessVentureStage` / `transitionVentureStage` / `VentureStage` (Task 10) → Task 11, và `VENTURE_STAGE_ASSESS_SPEC` (Task 66) gọi cùng endpoint. `buildVentureStageChangedEvent` (Task 9) → Task 10; `buildProjectPhaseChangedEvent` (Task 13). Release B–E: `regulationVersions` (Task 20) → dùng ở Task 21/25/27/36/45. `wrap_advisory` (Task 31) → Task 32/33/66. `RegulationSourceView` (Task 25) → Flutter Task 34. `isGrantActive` (Task 42) → Task 44/57/58. `getEffectiveRegimePolicy` (Task 45) → Task 46/48/50. `upsertBankTransactionFromIngestion` (Task 44) → Task 57. `assembleContext` / `NbaContext` (Task 63) → Task 64. `validate_output` / `require_evidence` / `InsufficientEvidence` (Task 65) → Task 66/67. `recordExecution` (Task 67) dùng chung `(run_id, tool_call_id)` unique với `taskExecutionRecords` (Task 62). Event strings: `"venture.stage.changed"` / `"project.phase.changed"` (Task 9/10/13), `"legal.status.changed"` / `"legal.obligation.created"` (Task 26/28), `"finance.accounting_document.confirmed.v1"` / `"finance.bank_transaction.ingested"` (Task 44/47), `"strategy.next_best_action.accepted"` / `"operations.weekly_review.completed"` (Task 63/64) — mỗi string khai ở `shared/events.ts` một lần, tham chiếu ở event builder + acceptance test.
