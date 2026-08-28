# Customer Engagement — P0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây Human Desk tối thiểu cho Customer Engagement — inbox / thread / message / assignment /
takeover / Decision Request — do **người thật** vận hành đầu-cuối, phát business fact qua outbox hiện có,
với tenant isolation + idempotency + audit/RBAC. **Chưa có agent.**

**Architecture:** Aggregate mới `engagement_*` trong `services/company/commercial` (Drizzle schema tập
trung ở `shared/db/schema/`, migration ở `commercial/migrations/`). Handler (`expose: true`) parse input
→ `requireWorkspaceAccess()` → service; service chạy business logic + Drizzle transaction, gọi
`appendOutboxEvent(tx, …)` cùng transaction. State machine thread + Decision Request là module thuần
(validation bảng chuyển) — không suy state từ text. Outbound message qua command log
`engagement_outbound_deliveries` + local relay riêng (pattern `outbox-relay`). Không LLM, không event
consumer trong P0.

**Tech Stack:** TypeScript strict, Encore, Drizzle ORM `^0.45`, PostgreSQL 16, Vitest `^3` (real DB,
`npm test` = `vitest run` trong `services/company`). Snowflake ID qua `generateSnowflake()`.

**Spec:** [`docs/superpowers/specs/2026-08-28-customer-engagement-human-agent-design.md`](../specs/2026-08-28-customer-engagement-human-agent-design.md) —
P0 phủ spec §5 (domain model), §6 (state machine), §7 (Decision Request — authority binding fail-closed,
N-of-M distinct approvers, execution guard), §8.1 (business events, chỉ phát), §9 (Channel Adapter
contract + `api` adapter), §10.1–10.2 (Desk surfaces, backend), §11 (privacy/audit — retention NOT NULL,
legal hold, DSR export/delete), §12 (SLA snapshot + escalation routes), §15 (test matrix). P1–P4 có plan
riêng. **Quyết định §17.2/§17.4/§17.5/§17.7 đã chốt 2026-08-28** — xem §"P0 policy defaults" bên dưới.

**Overview:** [`2026-08-28-customer-engagement-overview.md`](./2026-08-28-customer-engagement-overview.md) — đọc phần "Phân kỳ & rollout gate" + "Global Constraints" trước.

## Global Constraints

- **TDD bắt buộc**: test đỏ → xác nhận đỏ → implement tối thiểu → xác nhận xanh → commit. Không tuyên bố
  xong khi chưa chạy test (CLAUDE.md #11).
- **An toàn working tree** (CLAUDE.md #10): `git status` trước thao tác có thể mất dữ liệu; không
  `--force`/`--no-verify`; không tự xoá/archive file không liên quan.
- **Tenant**: mọi bảng `engagement_*` có `workspace_id BIGINT NOT NULL`; mọi query/update/link/delete
  ràng `id AND workspace_id` bằng `and(eq(t.id, BigInt(id)), eq(t.workspaceId, BigInt(ctx.workspaceId)))`.
  Handler có auth header lấy workspace từ `requireWorkspaceAccess(authorization, workspaceId)` →
  `TenantContext`; **không** tin `workspaceId` body cho quyết định quyền.
- **Encore**: lỗi qua `APIError` (`invalidArgument`/`unauthenticated`/`permissionDenied`/`notFound`/
  `alreadyExists`/`internal`) — không throw `Error` trần. Handler chỉ parse input + gọi service.
- **Schema Drizzle** tập trung ở `services/company/shared/db/schema/` — thêm file `customer-engagement.ts`,
  re-export trong `shared/db/schema/index.ts`. **Không** rải trong `models/`.
- **Migration**: chỉ `.up.sql`. `services/company/commercial/migrations/` hiện cao nhất = **10** ⇒ file
  mới `11_customer_engagement.up.sql` (xác nhận `ls` ngay trước khi tạo). Sau khi thêm:
  `make services-migrate-company`; `node scripts/migrate.mjs --check` để preflight.
- **Event**: `eventType` khớp `^[a-z]+\.[a-z_]+\.[a-z_]+\.v[0-9]+$`, past tense. Phát qua
  `appendOutboxEvent(tx, envelope)` **cùng transaction** với state write. `producer.service` =
  `"company.commercial"` (cần Task 1). Classification mặc định `confidential`; dùng `restricted` (payload
  chỉ key khớp `^[a-z0-9_]*(id|ref|hash|count)$`) cho event mà về sau consumer agent phải gọi capability
  để đọc nội dung.
- **State structured**: transition là command validate theo bảng chuyển hợp lệ; ghi
  `engagement_thread_transitions` (append-only). Không `if "resolved" in body`.
- **No chain-of-thought** ở đâu cả (P0 không có model, nhưng giữ ràng buộc cho message body: internal
  note chứa handoff context/rationale rút gọn, không reasoning).
- **Fail-closed** (chốt 2026-08-28): không có authority `enabled` + đủ grant hợp lệ ⇒ **không cho
  approve/execute** Decision Request. Không có escalation route bind tới `WorkforceMember` thật ⇒ **không
  bật inbox tier** cần route đó (vd. `vip`). Thiếu binding = từ chối, không phải cảnh báo.
- **Retention bắt buộc** (chốt 2026-08-28): `retention_until` **NOT NULL** trên `engagement_messages`,
  `engagement_message_attachments`, `engagement_customer_interactions`. Không có "giữ vô thời hạn".
  Legal hold là record riêng (`engagement_legal_holds`) có lý do + người tạo + hạn; **không** âm thầm kéo
  dài retention. Mặc định: public transcript + internal note `+365d`; file gốc/attachment + text trích
  xuất `+90d`; metadata attachment / audit event / hash evidence `+730d`. Commercial contract/invoice
  **không** dùng retention của Engagement.
- **Residency** (chốt 2026-08-28): raw transcript + attachment chỉ lưu tại `workspace_home_region` thực
  tế đã provision (không region "trên giấy"); backup cùng vùng hoặc vùng workspace đã duyệt. Không gửi
  raw transcript sang model provider khi chưa có policy/DPA; mặc định chỉ context tối thiểu hoá / redaction.
- **Comment** tiếng Việt cho "why"; identifier/log/error English.

---

## P0 policy defaults (chốt 2026-08-28 — nguyên tắc fail-closed)

Seed các giá trị này per-workspace. **Không** authority/route binding hợp lệ ⇒ không cho approve /
không bật inbox tier tương ứng.

### Authority keys → `engagement_decision_authorities` (seed `status='pending_binding'`)

| `authority_key` | `decision_kind` | `match_criteria` (rút gọn) | `approval_policy.required_capabilities` | `distinct_approvers` |
| --- | --- | --- | --- | --- |
| `commercial.discount.up_to_10_pct` | discount | discount ≤10%, ≥ price floor, không đổi payment/contract term | `[sales_manager]` | 1 (requester ≠ approver) |
| `commercial.pricing.exception` | pricing_exception | discount >10%, < price floor, bespoke price, payment term phi chuẩn | `[sales_director, finance_controller]` | 2 |
| `commercial.pricing.high_risk` | pricing_high_risk | discount >25% hoặc margin < ngưỡng policy | `[commercial_policy_owner, finance_controller, workspace_business_owner]` | 3 |
| `billing.refund_or_credit` | refund_or_credit | refund / credit / invoice adjustment, mọi giá trị | `[finance_controller, finance_reviewer]` | 2 (requester không approve/execute) |
| `billing.cancellation.exception` | cancellation_exception | hủy sớm, waive notice/termination fee, pro-rata exception | `[customer_success_owner, finance_controller]` | 2 |
| `contract.commercial_exception` | contract_commercial | điều khoản thương mại / giá / thanh toán | `[sales_director, finance_controller]` | 2 |
| `contract.legal_privacy_exception` | contract_legal_privacy | điều khoản pháp lý / bảo mật / privacy / DPA | `[legal_reviewer, workspace_business_owner]` (+`finance_controller` nếu có tác động tiền) | 2 (3 nếu tài chính) |

`approval_policy` chuẩn: `{ required_capabilities: [...], distinct_approvers: N, requester_must_differ: true, requester_cannot_execute: true }`.
Cancellation **đúng điều khoản đã công bố** không cần Decision Request — `billing_ops` thực hiện sau khi
xác minh khách hàng. P0: không agent/job tự thực thi refund/cancel.

### Retention defaults (`retention_until` NOT NULL)

| Dữ liệu | Mặc định |
| --- | --- |
| Public transcript + internal note (`engagement_messages`) | `created_at + 365d` |
| File gốc / attachment + text trích xuất (raw) | `created_at + 90d` |
| Metadata attachment / audit event / hash evidence | `created_at + 730d` |
| Commercial contract / invoice | **không** dùng retention Engagement (theo Commercial/Finance) |

Legal hold = `engagement_legal_holds` (lý do + người tạo + `effective_until`). DSR: export (JSON/ZIP, tải
trong 24h, loại internal note + chủ thể khác) và delete (suppress ngay; purge primary ≤30 ngày sau verify;
backup ≤35 ngày). Audit DSR chỉ giữ `request_id / actor / at / basis`. Căn cứ: GDPR Art.5, NĐ 13/2023/NĐ-CP.

### SLA policy seed (`engagement_inboxes.sla_policy`, hằng `SLA_POLICY_SEED`)

`version 1`, `timezone Asia/Ho_Chi_Minh`, `business_calendar { weekdays [1..5], hours [08:30–17:30], holiday_calendar "VN" }`.

| tier | first_response | resolution | warning_at% | out_of_hours |
| --- | --- | --- | --- | --- |
| `standard` | 240' business | 1440' business | 75 | `pause` |
| `priority` | 60' business | 480' business | 75 | `pause` |
| `vip` | 30' calendar | 480' calendar | 50 | `on_call` route `support-oncall`: ack 15' → backup 15' → duty_manager 30' |

Route (`support-oncall` primary / backup / `customer-success-duty-manager`) bind tới `WorkforceMember`
thật qua `engagement_escalation_routes` — **không** hard-code email/cá nhân trong JSON. Thread lưu snapshot
(`sla_policy_version`, `sla_snapshot`, `first_response_due_at`, `resolution_due_at`, `escalation_level`,
`escalation_route_key`); đổi policy không rebaseline ticket đang mở trừ lệnh có audit.

---

## File Structure

| File | Trách nhiệm |
| --- | --- |
| `services/company/shared/events/envelope.ts` | (Modify) thêm `producer?` vào `BusinessEventInput`; `makeBusinessEvent` dùng override. |
| `services/company/shared/db/schema/customer-engagement.ts` | (Create) Drizzle schema cho toàn bộ bảng `engagement_*`. |
| `services/company/shared/db/schema/index.ts` | (Modify) `export * from "./customer-engagement"`. |
| `services/company/commercial/migrations/11_customer_engagement.up.sql` | (Create) `CREATE SCHEMA engagement` + tất cả bảng + index + composite constraint. |
| `services/company/commercial/db.ts` | (Modify) import thêm schema `customer-engagement` vào drizzle client của commercial. |
| `services/company/shared/events/customer-engagement-events.ts` | (Create) builder envelope cho `engagement.*.v1`. |
| `services/company/commercial/services/customer-engagement/thread-state.ts` | (Create) state machine thuần: bảng chuyển + `assertTransition`. |
| `services/company/commercial/services/customer-engagement/thread.service.ts` | (Create) `openThread` / `getThread` / `listThreads` / `changeThreadStatus`. |
| `services/company/commercial/services/customer-engagement/assignment.service.ts` | (Create) `assignThread` / `takeOverThread` / `handBackToAgent`. |
| `services/company/commercial/services/customer-engagement/message.service.ts` | (Create) `postInternalNote` / `sendPublicMessage` / `recordInboundMessage`. |
| `services/company/commercial/services/customer-engagement/channel-adapters/contract.ts` | (Create) interface `ChannelAdapter`. |
| `services/company/commercial/services/customer-engagement/channel-adapters/api-channel.adapter.ts` | (Create) `ApiChannelAdapter` (trivial). |
| `services/company/commercial/services/customer-engagement/channel-adapters/registry.ts` | (Create) `getChannelAdapter(channelType)`. |
| `services/company/commercial/services/customer-engagement/delivery-relay.service.ts` | (Create) `deliveryRelayTick()` — claim `engagement_outbound_deliveries`, ownership re-check, send, complete/fail. |
| `services/company/commercial/services/customer-engagement/delivery-relay.cron.ts` | (Create) Encore `CronJob` 1 phút. |
| `services/company/commercial/services/customer-engagement/customer360.service.ts` | (Create) `getCustomer360(contactId, ctx)` aggregation. |
| `services/company/commercial/services/customer-engagement/identity-resolution.service.ts` | (Create) `resolveContact({email?, phone?}, ctx)` + tạo `engagement_identity_review_items`. |
| `services/company/commercial/services/customer-engagement/decision-request-state.ts` | (Create) state machine DR: bảng chuyển + `assertDRTransition`. |
| `services/company/commercial/services/customer-engagement/decision-authority.service.ts` | (Create) seed/enable authority (`pending_binding`→`enabled` khi đủ grant), `resolveAuthority`, `assertApprovalPolicySatisfied`. |
| `services/company/commercial/services/customer-engagement/decision-request.service.ts` | (Create) state machine + N-of-M distinct approvers + requester≠approver≠executor + execution guard (fail-closed). |
| `services/company/commercial/services/customer-engagement/sla.service.ts` | (Create) `resolveTier`, `computeSlaSnapshot` (business calendar), `snapshotThreadSla`. |
| `services/company/commercial/services/customer-engagement/escalation.service.ts` | (Create) `resolveEscalationRoute(routeKey, level, ctx)` → `WorkforceMember` bind theo hiệu lực. |
| `services/company/commercial/services/customer-engagement/data-subject-request.service.ts` | (Create) DSR export/delete flow + legal-hold check. |
| `services/company/commercial/services/customer-engagement/legal-hold.service.ts` | (Create) `createLegalHold` / `releaseLegalHold` / `isUnderLegalHold`. |
| `services/company/commercial/services/customer-engagement/rbac.ts` | (Create) hằng permission + `requireEngagementPermission(ctx, perm)`. |
| `services/company/commercial/handlers/customer-engagement/*.handler.ts` | (Create) `inbox` / `thread` / `message` / `assignment` / `customer360` / `decision-request` / `decision-authority` / `data-subject-request` / `legal-hold` handlers (`expose: true`). |
| `services/company/commercial/handlers/customer-engagement/index.ts` | (Create) barrel. |
| `services/company/commercial/handlers/index.ts` | (Modify) `export * from "./customer-engagement"`. |
| `docs/architecture/customer-engagement-vocabulary.md` | (Create) chốt thuật ngữ §3 + tên state (Task 16). |
| `services/company/commercial/tests/customer-engagement/*.test.ts` | (Create) unit + test matrix §15. |

**Assumptions về helper hiện có** (đã verify trong repo):
- `requireWorkspaceAccess(authorization, workspaceId): Promise<TenantContext>` — `shared/auth/workspace-access.ts`.
- `TenantContext` có `{ workspaceId, userId, workforceMemberId?, membershipRole, permissions: readonly string[], correlationId }` — `shared/types/tenant_context.ts`.
- `generateSnowflake(): string` — `shared/services/snowflake.service.ts`.
- `appendOutboxEvent(tx, envelope)` — `shared/events/outbox.repository.ts`.
- `db.transaction(async (tx) => {...})` — Drizzle; `Tx` type = `Parameters<Parameters<typeof db.transaction>[0]>[0]`.
- Test session helper: `createTestSession({ email, displayName })` → `{ accessToken, workspaceId, ... }` — `identity/tests/helpers/test-session.ts`.

---

### Task 1: Producer override cho business event builder

**Files:**
- Modify: `services/company/shared/events/envelope.ts`
- Test: `services/company/shared/events/tests/envelope-producer.test.ts` (Create)

**Interfaces:**
- Consumes: nothing.
- Produces: `BusinessEventInput<T>` có thêm field optional `producer?: { service: string; version: string }`.
  `makeBusinessEvent(input)` dùng `input.producer ?? { service: PRODUCER_SERVICE, version: PRODUCER_VERSION }`.
  Call site cũ (operations) không đổi hành vi.

- [ ] **Step 1: Viết test đỏ**

Create `services/company/shared/events/tests/envelope-producer.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { makeBusinessEvent } from "../envelope";

describe("makeBusinessEvent producer override", () => {
  const base = {
    eventType: "engagement.thread.opened.v1",
    workspaceId: "1",
    aggregateType: "engagement_thread",
    aggregateId: "42",
    correlationId: "corr-1",
    actor: { kind: "user" as const, id: "u1" },
    classification: "confidential" as const,
    payload: { thread_id: "42" },
  };

  it("defaults producer.service to company.operations when not provided", () => {
    const e = makeBusinessEvent(base);
    expect(e.producer.service).toBe("company.operations");
  });

  it("uses the provided producer when given", () => {
    const e = makeBusinessEvent({
      ...base,
      producer: { service: "company.commercial", version: "1.2.3" },
    });
    expect(e.producer).toEqual({ service: "company.commercial", version: "1.2.3" });
  });
});
```

- [ ] **Step 2: Chạy test — xác nhận đỏ**

Run: `cd services/company && npx vitest run shared/events/tests/envelope-producer.test.ts`
Expected: FAIL — test thứ hai lỗi vì `producer` luôn = `company.operations`.

- [ ] **Step 3: Implement**

Trong `services/company/shared/events/envelope.ts`:

```typescript
export interface BusinessEventInput<T extends Record<string, unknown>> {
  eventType: string;
  workspaceId: string;
  aggregateType: string;
  aggregateId: string;
  correlationId: string;
  causationId?: string;
  actor: BusinessEventEnvelope<T>["actor"];
  classification: BusinessEventEnvelope<T>["classification"];
  payload: T;
  // Cho phép producer khác domain (vd. company.commercial cho Customer Engagement).
  // Mặc định giữ nguyên company.operations để call site cũ không đổi hành vi.
  producer?: { service: string; version: string };
}
```

và trong `makeBusinessEvent`, thay dòng `producer: { service: PRODUCER_SERVICE, version: PRODUCER_VERSION },` bằng:

```typescript
    producer: input.producer ?? { service: PRODUCER_SERVICE, version: PRODUCER_VERSION },
```

- [ ] **Step 4: Chạy test — xác nhận xanh**

Run: `cd services/company && npx vitest run shared/events/tests/envelope-producer.test.ts`
Expected: PASS (2/2).

- [ ] **Step 5: Regression — envelope test sẵn có**

Run: `cd services/company && npx vitest run shared/events`
Expected: PASS toàn bộ (không vỡ contract cross-language / operations).

- [ ] **Step 6: Commit**

```bash
git add services/company/shared/events/envelope.ts services/company/shared/events/tests/envelope-producer.test.ts
git commit -m "feat(events): optional producer override in makeBusinessEvent"
```

---

### Task 2: Engagement schema + migration

**Files:**
- Create: `services/company/shared/db/schema/customer-engagement.ts`
- Modify: `services/company/shared/db/schema/index.ts`
- Modify: `services/company/commercial/db.ts`
- Create: `services/company/commercial/migrations/11_customer_engagement.up.sql`
- Test: `services/company/commercial/tests/customer-engagement/schema-migration.test.ts` (Create)

**Interfaces:**
- Produces: Drizzle table objects exported từ `customer-engagement.ts`:
  `engagementInboxes, engagementChannelEndpoints, engagementThreads, engagementMessages,
  engagementMessageAttachments, engagementAssignments, engagementThreadLabels, engagementThreadOutcomes,
  engagementCustomerInteractions, engagementThreadTransitions, engagementDecisionAuthorities,
  engagementDecisionAuthorityGrants, engagementDecisionRequests, engagementDecisionRequestApprovals,
  engagementDecisionRequestEvents, engagementEscalationRoutes, engagementLegalHolds,
  engagementDataSubjectRequests, engagementOutboundDeliveries, engagementIdentityReviewItems`.
  Postgres schema name = `engagement`.
- Cột dùng `bigint({ mode: "bigint" })` cho id/FK, `text`/`jsonb`/`timestamp({withTimezone:true})` như
  `commercial.ts`. `id` = `bigint(...).primaryKey()` (migration dùng `BIGSERIAL` — theo migration 3;
  các bảng khác `commercial.ts` dùng `.primaryKey()` không `generatedAlwaysAsIdentity`, insert set id
  bằng `generateSnowflake()`; **theo pattern hiện có: set id thủ công**).

- [ ] **Step 1: Xác nhận migration number**

Run: `ls services/company/commercial/migrations/ | sort -V | tail -3`
Expected: `10_...` cao nhất ⇒ file mới `11_customer_engagement.up.sql`. Nếu khác, dùng số kế tiếp.

- [ ] **Step 2: Viết test đỏ (schema round-trip)**

Create `services/company/commercial/tests/customer-engagement/schema-migration.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { sql } from "drizzle-orm";
import { db } from "../../db";

describe("engagement schema migration", () => {
  it("creates the engagement schema and core tables", async () => {
    const rows = await db.execute(sql`
      SELECT table_name FROM information_schema.tables
      WHERE table_schema = 'engagement' ORDER BY table_name;
    `);
    const names = (rows as any).rows.map((r: any) => r.table_name);
    for (const t of [
      "engagement_inboxes", "engagement_channel_endpoints", "engagement_threads",
      "engagement_messages", "engagement_message_attachments", "engagement_assignments",
      "engagement_thread_labels", "engagement_thread_outcomes", "engagement_customer_interactions",
      "engagement_thread_transitions", "engagement_decision_authorities",
      "engagement_decision_authority_grants", "engagement_decision_requests",
      "engagement_decision_request_approvals", "engagement_decision_request_events",
      "engagement_escalation_routes", "engagement_legal_holds", "engagement_data_subject_requests",
      "engagement_outbound_deliveries", "engagement_identity_review_items",
    ]) {
      expect(names).toContain(t);
    }
  });

  it("retention_until is NOT NULL on messages / attachments / interactions (fail-closed)", async () => {
    const rows = await db.execute(sql`
      SELECT table_name, is_nullable FROM information_schema.columns
      WHERE table_schema = 'engagement' AND column_name = 'retention_until';
    `);
    for (const r of (rows as any).rows) expect(r.is_nullable).toBe("NO");
  });

  it("enforces unique (thread_id, idempotency_key) on engagement_messages", async () => {
    const rows = await db.execute(sql`
      SELECT indexdef FROM pg_indexes
      WHERE schemaname = 'engagement' AND tablename = 'engagement_messages';
    `);
    const defs = (rows as any).rows.map((r: any) => r.indexdef).join("\n");
    expect(defs).toMatch(/UNIQUE.*\(thread_id, idempotency_key\)/i);
  });
});
```

- [ ] **Step 3: Chạy — xác nhận đỏ**

Run: `cd services/company && npx vitest run commercial/tests/customer-engagement/schema-migration.test.ts`
Expected: FAIL — schema `engagement` chưa tồn tại.

- [ ] **Step 4: Viết migration**

Create `services/company/commercial/migrations/11_customer_engagement.up.sql`:

```sql
-- Customer Engagement (P0) — Human Desk: inbox / thread / message / assignment / decision request.
-- Tham chiếu CRM sales.* / commercial.* bằng workspace-scoped ref; KHÔNG nhân bản CRM.
CREATE SCHEMA IF NOT EXISTS engagement;

CREATE TABLE engagement.engagement_inboxes (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  channel_type TEXT NOT NULL,                 -- 'api' | 'web_chat' | 'email' | 'zalo' | 'whatsapp' | 'facebook'
  name TEXT NOT NULL,
  locale TEXT,
  business_hours JSONB,
  sla_policy JSONB NOT NULL,                  -- seed P0: {version, timezone, business_calendar, tiers:{standard,priority,vip}} — xem "P0 policy defaults"
  default_tier TEXT NOT NULL DEFAULT 'standard',  -- standard | priority | vip
  default_team_id BIGINT,
  allowed_agent_spec_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  connector_installation_ref TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_engagement_inboxes_workspace ON engagement.engagement_inboxes(workspace_id);

CREATE TABLE engagement.engagement_channel_endpoints (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  inbox_id BIGINT NOT NULL,
  provider_ref TEXT NOT NULL,
  delivery_capability TEXT NOT NULL DEFAULT 'send',
  verification_config_ref TEXT,
  secret_ref TEXT,                            -- opaque reference; KHÔNG lưu secret thật
  status TEXT NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (inbox_id, workspace_id)
    REFERENCES engagement.engagement_inboxes(id, workspace_id) ON DELETE CASCADE
);
-- composite target cần unique key:
ALTER TABLE engagement.engagement_inboxes ADD CONSTRAINT uq_engagement_inboxes_id_ws UNIQUE (id, workspace_id);
CREATE INDEX idx_engagement_channel_endpoints_inbox ON engagement.engagement_channel_endpoints(inbox_id);

CREATE TABLE engagement.engagement_threads (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  inbox_id BIGINT NOT NULL,
  contact_id BIGINT,
  account_id BIGINT,
  lead_id BIGINT,
  opportunity_id BIGINT,
  customer_id BIGINT,
  status TEXT NOT NULL DEFAULT 'open',        -- open | pending_customer | pending_internal | snoozed | resolved
  priority TEXT NOT NULL DEFAULT 'normal',
  active_mode TEXT NOT NULL DEFAULT 'team_queue', -- human_assigned | team_queue | agent_autopilot | agent_copilot | awaiting_decision
  owner_member_id BIGINT,
  snoozed_until TIMESTAMPTZ,
  correlation_id TEXT NOT NULL,
  tier TEXT NOT NULL DEFAULT 'standard',      -- standard | priority | vip (resolve tại openThread)
  sla_policy_version INTEGER,
  sla_snapshot JSONB,                         -- snapshot policy tier tại thời điểm mở; ticket đang mở giữ snapshot cũ trừ khi rebaseline có audit
  first_response_due_at TIMESTAMPTZ,
  resolution_due_at TIMESTAMPTZ,
  escalation_level INTEGER NOT NULL DEFAULT 0,
  escalation_route_key TEXT,
  last_customer_msg_at TIMESTAMPTZ,
  first_response_at TIMESTAMPTZ,
  resolved_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (inbox_id, workspace_id)
    REFERENCES engagement.engagement_inboxes(id, workspace_id) ON DELETE CASCADE
);
ALTER TABLE engagement.engagement_threads ADD CONSTRAINT uq_engagement_threads_id_ws UNIQUE (id, workspace_id);
CREATE INDEX idx_engagement_threads_workspace ON engagement.engagement_threads(workspace_id);
CREATE INDEX idx_engagement_threads_queue ON engagement.engagement_threads(workspace_id, status, priority);
CREATE INDEX idx_engagement_threads_owner ON engagement.engagement_threads(workspace_id, owner_member_id);

CREATE TABLE engagement.engagement_messages (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  thread_id BIGINT NOT NULL,
  direction TEXT NOT NULL,                    -- inbound | outbound | system
  visibility TEXT NOT NULL,                   -- customer | internal
  sender_kind TEXT NOT NULL,                  -- customer | workforce_member | automation | system
  sender_ref TEXT,
  body TEXT NOT NULL,
  body_content_hash TEXT NOT NULL,
  classification TEXT NOT NULL DEFAULT 'confidential',
  retention_until TIMESTAMPTZ NOT NULL,       -- fail-closed: KHÔNG nullable, KHÔNG "giữ vô thời hạn" (mặc định created_at + 365d)
  delivery_state TEXT,                        -- null cho inbound/internal; queued|sent|delivered|failed|cancelled cho outbound+customer
  idempotency_key TEXT NOT NULL,
  external_message_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (thread_id, workspace_id)
    REFERENCES engagement.engagement_threads(id, workspace_id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX uq_engagement_messages_thread_idem
  ON engagement.engagement_messages(thread_id, idempotency_key);
CREATE INDEX idx_engagement_messages_thread ON engagement.engagement_messages(thread_id, created_at);
-- dedupe inbound theo provider message id (P2), nullable nên partial unique:
CREATE UNIQUE INDEX uq_engagement_messages_external
  ON engagement.engagement_messages(workspace_id, external_message_id)
  WHERE external_message_id IS NOT NULL;

CREATE TABLE engagement.engagement_assignments (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  thread_id BIGINT NOT NULL,
  assigned_team_id BIGINT,
  assigned_member_id BIGINT,
  assigned_agent_spec_id TEXT,
  reason TEXT NOT NULL,
  assigned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  ended_at TIMESTAMPTZ,
  FOREIGN KEY (thread_id, workspace_id)
    REFERENCES engagement.engagement_threads(id, workspace_id) ON DELETE CASCADE
);
-- tối đa 1 assignment active / thread:
CREATE UNIQUE INDEX uq_engagement_assignments_active
  ON engagement.engagement_assignments(thread_id) WHERE ended_at IS NULL;

CREATE TABLE engagement.engagement_thread_labels (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  thread_id BIGINT NOT NULL,
  label_key TEXT NOT NULL,
  taxonomy_version TEXT NOT NULL,
  source TEXT NOT NULL,                       -- human | automation | agent_proposal
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (thread_id, workspace_id)
    REFERENCES engagement.engagement_threads(id, workspace_id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX uq_engagement_thread_labels
  ON engagement.engagement_thread_labels(thread_id, label_key);

CREATE TABLE engagement.engagement_thread_outcomes (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  thread_id BIGINT NOT NULL,
  intent TEXT,
  resolution_code TEXT,
  escalation_reason TEXT,
  csat_ref TEXT,
  sales_signal_evidence JSONB,
  decision_request_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (thread_id, workspace_id)
    REFERENCES engagement.engagement_threads(id, workspace_id) ON DELETE CASCADE
);
CREATE INDEX idx_engagement_thread_outcomes_thread ON engagement.engagement_thread_outcomes(thread_id);

CREATE TABLE engagement.engagement_customer_interactions (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  contact_id BIGINT,
  account_id BIGINT,
  lead_id BIGINT,
  opportunity_id BIGINT,
  customer_id BIGINT,
  thread_id BIGINT,
  summary TEXT NOT NULL,
  source_evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
  confidence TEXT NOT NULL DEFAULT 'medium',
  retention_until TIMESTAMPTZ NOT NULL,       -- fail-closed (mặc định created_at + 365d)
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_engagement_cust_interactions_contact
  ON engagement.engagement_customer_interactions(workspace_id, contact_id);

CREATE TABLE engagement.engagement_thread_transitions (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  thread_id BIGINT NOT NULL,
  actor JSONB NOT NULL,                       -- { kind, id }
  reason_code TEXT NOT NULL,
  previous_state TEXT,
  current_state TEXT NOT NULL,
  previous_mode TEXT,
  current_mode TEXT,
  correlation_id TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (thread_id, workspace_id)
    REFERENCES engagement.engagement_threads(id, workspace_id) ON DELETE CASCADE
);
CREATE INDEX idx_engagement_thread_transitions_thread
  ON engagement.engagement_thread_transitions(thread_id, created_at);

-- Authority = capability được bind rõ tới WorkforceMember trong TỪNG workspace.
-- KHÔNG suy quyền từ role_title / "admin" / "founder". Seed ở trạng thái pending_binding;
-- chỉ 'enabled' sau khi mọi capability trong approval_policy.required_capabilities có >=1 grant active.
CREATE TABLE engagement.engagement_decision_authorities (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  authority_key TEXT NOT NULL,                -- vd. commercial.discount.up_to_10_pct, billing.refund_or_credit
  decision_kind TEXT NOT NULL,               -- discount | pricing_exception | pricing_high_risk | refund_or_credit | cancellation_exception | contract_commercial | contract_legal_privacy
  match_criteria JSONB NOT NULL DEFAULT '{}'::jsonb,   -- điều kiện định lượng: {max_discount_pct, below_price_floor, payment_term_nonstandard, ...}
  approval_policy JSONB NOT NULL,             -- {required_capabilities:[...], distinct_approvers:N, requester_must_differ:true, requester_cannot_execute:true}
  version INTEGER NOT NULL DEFAULT 1,
  status TEXT NOT NULL DEFAULT 'pending_binding',   -- pending_binding | enabled | disabled
  effective_from TIMESTAMPTZ NOT NULL DEFAULT now(),
  effective_until TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_engagement_decision_authorities
  ON engagement.engagement_decision_authorities(workspace_id, authority_key, version);

-- Grant: capability cụ thể của authority được gán cho một WorkforceMember thật, có hiệu lực thời gian.
CREATE TABLE engagement.engagement_decision_authority_grants (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  authority_key TEXT NOT NULL,
  workforce_member_id BIGINT NOT NULL,
  capability TEXT NOT NULL,                   -- vd. sales_manager, finance_controller, legal_reviewer, workspace_business_owner
  active_from TIMESTAMPTZ NOT NULL DEFAULT now(),
  active_until TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_engagement_authority_grants_lookup
  ON engagement.engagement_decision_authority_grants(workspace_id, authority_key, capability);

CREATE TABLE engagement.engagement_decision_requests (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  thread_id BIGINT,
  request_type TEXT NOT NULL,                 -- = decision_kind
  status TEXT NOT NULL DEFAULT 'draft',       -- draft|submitted|under_review|needs_information|approved|execution_pending|executed|rejected|expired
  contact_id BIGINT, account_id BIGINT, lead_id BIGINT, opportunity_id BIGINT, customer_id BIGINT,
  policy_id TEXT, policy_version TEXT, policy_snapshot_ref TEXT,
  facts_ref TEXT,
  evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
  options JSONB NOT NULL DEFAULT '[]'::jsonb,
  recommendation_ref TEXT,
  requested_by_actor JSONB NOT NULL,
  requested_by_workforce_member_id BIGINT NOT NULL,   -- để enforce requester != approver != executor
  authority_key TEXT NOT NULL,
  authority_version INTEGER NOT NULL,
  approval_policy_snapshot JSONB NOT NULL,    -- copy approval_policy tại lúc submit
  approval_deadline TIMESTAMPTZ,
  decision TEXT,                              -- approved | rejected | needs_information (kết luận cuối)
  decision_reason TEXT,
  approved_at TIMESTAMPTZ,                    -- thời điểm approval_policy được thoả
  executed_by_workforce_member_id BIGINT,
  execution_ref TEXT,
  correlation_id TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_engagement_decision_requests_ws_status
  ON engagement.engagement_decision_requests(workspace_id, status);
CREATE INDEX idx_engagement_decision_requests_thread
  ON engagement.engagement_decision_requests(thread_id);

-- Mỗi phê duyệt của một người = 1 dòng. N-of-M distinct approvers suy ra từ đây, không phải 2 cột cứng.
CREATE TABLE engagement.engagement_decision_request_approvals (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  decision_request_id BIGINT NOT NULL,
  workforce_member_id BIGINT NOT NULL,
  capability TEXT NOT NULL,                   -- capability mà người này cover (từ grant)
  decision TEXT NOT NULL,                     -- approve | reject | needs_information
  reason TEXT,
  decided_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_engagement_dr_approvals_distinct
  ON engagement.engagement_decision_request_approvals(decision_request_id, workforce_member_id);

CREATE TABLE engagement.engagement_decision_request_events (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  decision_request_id BIGINT NOT NULL,
  event_type TEXT NOT NULL,                   -- submitted|review_started|approval_recorded|needs_information|approved|rejected|expired|execution_started|executed|execution_failed
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  actor JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_engagement_dr_events_dr
  ON engagement.engagement_decision_request_events(decision_request_id, created_at);

-- Escalation route: primary / backup / duty_manager bind tới WorkforceMember thật, theo hiệu lực.
-- KHÔNG hard-code email / cá nhân trong sla_policy JSON.
CREATE TABLE engagement.engagement_escalation_routes (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  route_key TEXT NOT NULL,                    -- vd. support-oncall
  role TEXT NOT NULL,                         -- primary | backup | duty_manager
  workforce_member_id BIGINT NOT NULL,
  active_from TIMESTAMPTZ NOT NULL DEFAULT now(),
  active_until TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_engagement_escalation_routes_lookup
  ON engagement.engagement_escalation_routes(workspace_id, route_key, role);

-- Legal hold: record riêng, có lý do + người tạo + hạn. Chặn xoá; KHÔNG âm thầm kéo dài retention.
CREATE TABLE engagement.engagement_legal_holds (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  scope TEXT NOT NULL,                        -- thread | contact | workspace
  scope_ref BIGINT,                           -- thread_id / contact_id; null khi scope=workspace
  reason TEXT NOT NULL,
  created_by_workforce_member_id BIGINT NOT NULL,
  effective_until TIMESTAMPTZ NOT NULL,
  released_at TIMESTAMPTZ,
  released_by_workforce_member_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_engagement_legal_holds_scope
  ON engagement.engagement_legal_holds(workspace_id, scope, scope_ref);

-- Data Subject Request (GDPR Art.5 / NĐ 13/2023/NĐ-CP): export | delete.
CREATE TABLE engagement.engagement_data_subject_requests (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  kind TEXT NOT NULL,                         -- export | delete
  subject_contact_id BIGINT NOT NULL,
  status TEXT NOT NULL DEFAULT 'received',    -- received | verified | suppressed | exported | purging | completed | blocked_legal_hold | rejected
  requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  verified_at TIMESTAMPTZ,
  verified_by_workforce_member_id BIGINT,     -- Privacy Officer
  export_ref TEXT,
  export_expires_at TIMESTAMPTZ,              -- tải trong 24h
  suppressed_at TIMESTAMPTZ,                  -- khoá truy cập ngay sau tiếp nhận (delete)
  primary_purge_due_at TIMESTAMPTZ,          -- <= verified_at + 30 ngày
  backup_purge_due_at TIMESTAMPTZ,           -- <= 35 ngày
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_engagement_dsr_ws_status
  ON engagement.engagement_data_subject_requests(workspace_id, status);

-- Attachment (metadata P0; raw byte store = P2). retention_until NOT NULL (mặc định +90d cho raw, +730d cho metadata-only row).
CREATE TABLE engagement.engagement_message_attachments (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  message_id BIGINT NOT NULL,
  thread_id BIGINT NOT NULL,
  filename TEXT NOT NULL,
  content_type TEXT,
  byte_size BIGINT,
  content_ref TEXT,                           -- reference tới object store tại workspace_home_region; null nếu chưa upload
  content_hash TEXT,
  retention_until TIMESTAMPTZ NOT NULL,       -- fail-closed
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_engagement_message_attachments_msg
  ON engagement.engagement_message_attachments(message_id);

CREATE TABLE engagement.engagement_outbound_deliveries (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  message_id BIGINT NOT NULL,
  thread_id BIGINT NOT NULL,
  channel_type TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',      -- queued | sent | delivered | failed
  attempt_count INTEGER NOT NULL DEFAULT 0,
  max_attempts INTEGER NOT NULL DEFAULT 8,
  claim_token TEXT,
  visibility_timeout_at TIMESTAMPTZ,
  last_error TEXT,
  dead_letter_reason TEXT,
  external_message_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  delivered_at TIMESTAMPTZ
);
CREATE UNIQUE INDEX uq_engagement_outbound_deliveries_idem
  ON engagement.engagement_outbound_deliveries(workspace_id, idempotency_key);
CREATE INDEX idx_engagement_outbound_deliveries_due
  ON engagement.engagement_outbound_deliveries(status, visibility_timeout_at);

CREATE TABLE engagement.engagement_identity_review_items (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  thread_id BIGINT NOT NULL,
  candidate_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
  reason TEXT NOT NULL,                       -- multiple_candidates | unverified | do_not_contact | account_conflict
  status TEXT NOT NULL DEFAULT 'open',        -- open | resolved | dismissed
  resolved_by_workforce_member_id BIGINT,
  resolved_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_engagement_identity_review_items_thread
  ON engagement.engagement_identity_review_items(thread_id);
```

> **Lưu ý thứ tự**: `ALTER TABLE ... ADD CONSTRAINT uq_engagement_inboxes_id_ws` phải chạy **trước**
> `CREATE TABLE engagement_channel_endpoints` và `engagement_threads` (composite FK target). Di chuyển
> 2 dòng `ALTER TABLE ... UNIQUE (id, workspace_id)` lên ngay sau `CREATE TABLE` tương ứng khi hoàn thiện.

- [ ] **Step 5: Drizzle schema file**

Create `services/company/shared/db/schema/customer-engagement.ts` — mirror bảng trên. Ví dụ 2 bảng
(còn lại theo cùng khuôn, tham chiếu `commercial.ts`):

```typescript
import { pgSchema, text, bigint, timestamp, boolean, integer, jsonb } from "drizzle-orm/pg-core";

export const engagementSchema = pgSchema("engagement");

export const engagementThreads = engagementSchema.table("engagement_threads", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  inboxId: bigint("inbox_id", { mode: "bigint" }).notNull(),
  contactId: bigint("contact_id", { mode: "bigint" }),
  accountId: bigint("account_id", { mode: "bigint" }),
  leadId: bigint("lead_id", { mode: "bigint" }),
  opportunityId: bigint("opportunity_id", { mode: "bigint" }),
  customerId: bigint("customer_id", { mode: "bigint" }),
  status: text("status").notNull().default("open"),
  priority: text("priority").notNull().default("normal"),
  activeMode: text("active_mode").notNull().default("team_queue"),
  ownerMemberId: bigint("owner_member_id", { mode: "bigint" }),
  snoozedUntil: timestamp("snoozed_until", { withTimezone: true }),
  correlationId: text("correlation_id").notNull(),
  tier: text("tier").notNull().default("standard"),
  slaPolicyVersion: integer("sla_policy_version"),
  slaSnapshot: jsonb("sla_snapshot"),
  firstResponseDueAt: timestamp("first_response_due_at", { withTimezone: true }),
  resolutionDueAt: timestamp("resolution_due_at", { withTimezone: true }),
  escalationLevel: integer("escalation_level").notNull().default(0),
  escalationRouteKey: text("escalation_route_key"),
  lastCustomerMsgAt: timestamp("last_customer_msg_at", { withTimezone: true }),
  firstResponseAt: timestamp("first_response_at", { withTimezone: true }),
  resolvedAt: timestamp("resolved_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const engagementMessages = engagementSchema.table("engagement_messages", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  threadId: bigint("thread_id", { mode: "bigint" }).notNull(),
  direction: text("direction").notNull(),
  visibility: text("visibility").notNull(),
  senderKind: text("sender_kind").notNull(),
  senderRef: text("sender_ref"),
  body: text("body").notNull(),
  bodyContentHash: text("body_content_hash").notNull(),
  classification: text("classification").notNull().default("confidential"),
  retentionUntil: timestamp("retention_until", { withTimezone: true }).notNull(),
  deliveryState: text("delivery_state"),
  idempotencyKey: text("idempotency_key").notNull(),
  externalMessageId: text("external_message_id"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});
```

Thêm 18 bảng còn lại theo migration Step 4 (gồm `engagement_decision_authorities`,
`engagement_decision_authority_grants`, `engagement_decision_request_approvals`,
`engagement_escalation_routes`, `engagement_legal_holds`, `engagement_data_subject_requests`,
`engagement_message_attachments`). Export tất cả.

- [ ] **Step 6: Wire schema vào commercial db + index**

`services/company/shared/db/schema/index.ts` — thêm dòng:

```typescript
export * from "./customer-engagement";
```

`services/company/commercial/db.ts` — mở rộng schema truyền vào drizzle client:

```typescript
import { createDrizzleClient, DEFAULT_COMPANY_DB_URL } from "../shared/db/client";
import * as commercialSchema from "../shared/db/schema/commercial";
import * as engagementSchema from "../shared/db/schema/customer-engagement";

const schema = { ...commercialSchema, ...engagementSchema };
const conn = process.env.COMPANY_DATABASE_URL || DEFAULT_COMPANY_DB_URL;
export const db = createDrizzleClient(conn, schema);
export { schema };
```

- [ ] **Step 7: Áp migration**

Run: `make services-migrate-company`
Expected: `11_customer_engagement.up.sql` applied; không lỗi. `node services/company/scripts/migrate.mjs --check` → clean.

- [ ] **Step 8: Chạy test — xác nhận xanh**

Run: `cd services/company && npx vitest run commercial/tests/customer-engagement/schema-migration.test.ts`
Expected: PASS.

- [ ] **Step 9: Typecheck**

Run: `cd services/company && npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add services/company/shared/db/schema/customer-engagement.ts services/company/shared/db/schema/index.ts services/company/commercial/db.ts services/company/commercial/migrations/11_customer_engagement.up.sql services/company/commercial/tests/customer-engagement/schema-migration.test.ts
git commit -m "feat(engagement): P0 schema + migration for customer engagement aggregates"
```

---

### Task 3: Customer Engagement event builders

**Files:**
- Create: `services/company/shared/events/customer-engagement-events.ts`
- Test: `services/company/shared/events/tests/customer-engagement-events.test.ts` (Create)

**Interfaces:**
- Produces: các builder trả `BusinessEventEnvelope<...>` với `producer.service = "company.commercial"`,
  `aggregateType = "engagement_thread"` (hoặc `"engagement_decision_request"`), `correlationId` truyền vào:
  - `buildThreadOpenedEvent(t: { id; workspaceId; inboxId; correlationId }, actor)`
  - `buildThreadAssignedEvent({ threadId; workspaceId; assignmentId; correlationId }, actor)`
  - `buildThreadTakenOverEvent({ threadId; workspaceId; newOwnerMemberId; correlationId }, actor)`
  - `buildMessageReceivedEvent({ threadId; workspaceId; messageId; correlationId }, actor)` — **restricted**
  - `buildMessageSentEvent({ threadId; workspaceId; messageId; correlationId }, actor)` — **restricted**
  - `buildThreadStatusChangedEvent({ threadId; workspaceId; previousState; currentState; correlationId }, actor)`
  - `buildThreadResolvedEvent({ threadId; workspaceId; resolutionCode; correlationId }, actor)`
  - `buildDecisionRequestSubmittedEvent({ decisionRequestId; workspaceId; requestType; correlationId }, actor)`
  - `buildDecisionRequestDecidedEvent({ decisionRequestId; workspaceId; decision; correlationId }, actor)`
  - `Actor = { kind: "user" | "agent" | "system"; id: string }`
- Consumes: `makeBusinessEvent` (Task 1), `COMPANY_SERVICE_VERSION` env (fallback `"0.0.0-dev"`).

- [ ] **Step 1: Viết test đỏ**

```typescript
import { describe, expect, it } from "vitest";
import {
  buildThreadOpenedEvent, buildMessageReceivedEvent, buildThreadStatusChangedEvent,
} from "../customer-engagement-events";

const actor = { kind: "user" as const, id: "wm-1" };

describe("customer-engagement-events", () => {
  it("thread.opened.v1 uses company.commercial producer + confidential", () => {
    const e = buildThreadOpenedEvent(
      { id: "10", workspaceId: "1", inboxId: "5", correlationId: "c1" }, actor);
    expect(e.eventType).toBe("engagement.thread.opened.v1");
    expect(e.producer.service).toBe("company.commercial");
    expect(e.classification).toBe("confidential");
    expect(e.aggregateId).toBe("10");
  });

  it("message.received.v1 is restricted with reference-only payload", () => {
    const e = buildMessageReceivedEvent(
      { threadId: "10", workspaceId: "1", messageId: "77", correlationId: "c1" }, actor);
    expect(e.classification).toBe("restricted");
    // validateEnvelope trong makeBusinessEvent sẽ throw nếu payload có key không phải *_id/ref/hash/count
    expect(Object.keys(e.payload).every((k) => /^[a-z0-9_]*(id|ref|hash|count)$/i.test(k))).toBe(true);
  });

  it("thread.status_changed.v1 carries previous + current", () => {
    const e = buildThreadStatusChangedEvent(
      { threadId: "10", workspaceId: "1", previousState: "open", currentState: "resolved", correlationId: "c1" }, actor);
    expect(e.payload).toMatchObject({ previous_state: "open", current_state: "resolved" });
  });
});
```

- [ ] **Step 2: Chạy — xác nhận đỏ** (`Cannot find module`).

Run: `cd services/company && npx vitest run shared/events/tests/customer-engagement-events.test.ts`

- [ ] **Step 3: Implement**

```typescript
import { makeBusinessEvent, type BusinessEventEnvelope } from "./envelope";

export type Actor = { kind: "user" | "agent" | "system"; id: string };
const PRODUCER = { service: "company.commercial", version: process.env.COMPANY_SERVICE_VERSION || "0.0.0-dev" };

function thread<T extends Record<string, unknown>>(
  eventType: string, workspaceId: string, threadId: string, correlationId: string,
  classification: "confidential" | "restricted", actor: Actor, payload: T,
): BusinessEventEnvelope<T> {
  return makeBusinessEvent({
    eventType, workspaceId, aggregateType: "engagement_thread", aggregateId: threadId,
    correlationId, actor, classification, producer: PRODUCER, payload,
  });
}

export function buildThreadOpenedEvent(
  t: { id: string; workspaceId: string; inboxId: string; correlationId: string }, actor: Actor,
) {
  return thread("engagement.thread.opened.v1", t.workspaceId, t.id, t.correlationId, "confidential", actor, {
    thread_id: t.id, inbox_id: t.inboxId,
  });
}

export function buildThreadAssignedEvent(
  a: { threadId: string; workspaceId: string; assignmentId: string; correlationId: string }, actor: Actor,
) {
  return thread("engagement.thread.assigned.v1", a.workspaceId, a.threadId, a.correlationId, "confidential", actor, {
    thread_id: a.threadId, assignment_id: a.assignmentId,
  });
}

export function buildThreadTakenOverEvent(
  a: { threadId: string; workspaceId: string; newOwnerMemberId: string; correlationId: string }, actor: Actor,
) {
  return thread("engagement.thread.taken_over.v1", a.workspaceId, a.threadId, a.correlationId, "confidential", actor, {
    thread_id: a.threadId, new_owner_member_id: a.newOwnerMemberId,
  });
}

export function buildMessageReceivedEvent(
  m: { threadId: string; workspaceId: string; messageId: string; correlationId: string }, actor: Actor,
) {
  return thread("engagement.message.received.v1", m.workspaceId, m.threadId, m.correlationId, "restricted", actor, {
    thread_id: m.threadId, message_id: m.messageId,
  });
}

export function buildMessageSentEvent(
  m: { threadId: string; workspaceId: string; messageId: string; correlationId: string }, actor: Actor,
) {
  return thread("engagement.message.sent.v1", m.workspaceId, m.threadId, m.correlationId, "restricted", actor, {
    thread_id: m.threadId, message_id: m.messageId,
  });
}

export function buildThreadStatusChangedEvent(
  s: { threadId: string; workspaceId: string; previousState: string; currentState: string; correlationId: string },
  actor: Actor,
) {
  return thread("engagement.thread.status_changed.v1", s.workspaceId, s.threadId, s.correlationId, "confidential", actor, {
    thread_id: s.threadId, previous_state: s.previousState, current_state: s.currentState,
  });
}

export function buildThreadResolvedEvent(
  s: { threadId: string; workspaceId: string; resolutionCode: string; correlationId: string }, actor: Actor,
) {
  return thread("engagement.thread.resolved.v1", s.workspaceId, s.threadId, s.correlationId, "confidential", actor, {
    thread_id: s.threadId, resolution_code: s.resolutionCode,
  });
}

export function buildDecisionRequestSubmittedEvent(
  d: { decisionRequestId: string; workspaceId: string; requestType: string; correlationId: string }, actor: Actor,
) {
  return makeBusinessEvent({
    eventType: "engagement.decision_request.submitted.v1", workspaceId: d.workspaceId,
    aggregateType: "engagement_decision_request", aggregateId: d.decisionRequestId,
    correlationId: d.correlationId, actor, classification: "confidential", producer: PRODUCER,
    payload: { decision_request_id: d.decisionRequestId, request_type: d.requestType },
  });
}

export function buildDecisionRequestDecidedEvent(
  d: { decisionRequestId: string; workspaceId: string; decision: string; correlationId: string }, actor: Actor,
) {
  return makeBusinessEvent({
    eventType: "engagement.decision_request.decided.v1", workspaceId: d.workspaceId,
    aggregateType: "engagement_decision_request", aggregateId: d.decisionRequestId,
    correlationId: d.correlationId, actor, classification: "confidential", producer: PRODUCER,
    payload: { decision_request_id: d.decisionRequestId, decision: d.decision },
  });
}
```

- [ ] **Step 4: Chạy — xác nhận xanh.** Run: `npx vitest run shared/events/tests/customer-engagement-events.test.ts`

- [ ] **Step 5: Commit**

```bash
git add services/company/shared/events/customer-engagement-events.ts services/company/shared/events/tests/customer-engagement-events.test.ts
git commit -m "feat(engagement): canonical business-event builders (company.commercial producer)"
```

---

### Task 4: Thread state machine + open/get/list

**Files:**
- Create: `services/company/commercial/services/customer-engagement/thread-state.ts`
- Create: `services/company/commercial/services/customer-engagement/thread.service.ts`
- Create: `services/company/commercial/services/customer-engagement/rbac.ts`
- Test: `services/company/commercial/tests/customer-engagement/thread-state.test.ts`
- Test: `services/company/commercial/tests/customer-engagement/thread.service.test.ts`

**Interfaces:**
- Produces:
  - `thread-state.ts`: `type ThreadStatus = "open" | "pending_customer" | "pending_internal" | "snoozed" | "resolved"`;
    `type ThreadMode = "human_assigned" | "team_queue" | "agent_autopilot" | "agent_copilot" | "awaiting_decision"`;
    `assertStatusTransition(from: ThreadStatus, to: ThreadStatus): void` (throw `APIError.invalidArgument` nếu không hợp lệ);
    `STATUS_TRANSITIONS: Record<ThreadStatus, ThreadStatus[]>`.
  - `rbac.ts`: hằng `ENGAGEMENT_PERMISSIONS` (mỗi cái prefix `engagement.`): `thread.read`,
    `thread.write`, `message.send`, `thread.takeover`, `decision_request.review`,
    `decision_request.decide`, `decision_authority.manage`, `escalation_route.manage`,
    `data_subject_request.manage`, `legal_hold.manage`; `requireEngagementPermission(ctx: TenantContext,
    perm: string): void` (throw `APIError.permissionDenied`).
  - `thread.service.ts`:
    - `openThread(params: { workspaceId; inboxId; contactId?; priority?; tier?; correlationId? }, ctx): Promise<ThreadDTO>` —
      resolve tier (`params.tier ?? inbox.default_tier`); gọi `snapshotThreadSla(threadRow, inbox.sla_policy, tier)` (Task 14)
      để set `sla_policy_version`, `sla_snapshot`, `first_response_due_at`, `resolution_due_at`,
      `escalation_route_key` **cùng transaction** insert thread. Nếu tier cần escalation route mà workspace
      chưa có route bind (`engagement_escalation_routes`) → `APIError.failedPrecondition("escalation route not bound for tier <tier>")` (**fail-closed**).
    - `getThread(id: string, ctx): Promise<ThreadDTO>` — 404 nếu khác workspace.
    - `listThreads(filter: { status?; priority?; ownerMemberId?; activeMode?; limit?; cursor? }, ctx): Promise<ThreadDTO[]>`
    - `changeThreadStatus(id: string, params: { to: ThreadStatus; reasonCode: string; snoozedUntil?; resolutionCode? }, ctx): Promise<ThreadDTO>`
    - `ThreadDTO = { id; workspaceId; inboxId; contactId: string|null; status; priority; tier; activeMode; ownerMemberId: string|null; correlationId; firstResponseDueAt: string|null; resolutionDueAt: string|null; escalationLevel; createdAt; updatedAt }`
- Consumes: `db`, `schema` từ `commercial/models/db`; `appendOutboxEvent`; builders Task 3;
  `snapshotThreadSla` (Task 14); `generateSnowflake`; `requireWorkspaceAccess` (ở handler); `TenantContext`.

> **Thứ tự thực thi:** Task 14 (`sla.service.ts` + `escalation.service.ts`) nên làm **trước** phần
> `openThread` của Task 4, hoặc stub `snapshotThreadSla` trả `{}` ở Task 4 rồi hoàn thiện ở Task 14.
> Test `thread.service.test.ts` seed inbox với `sla_policy` hợp lệ + route `support-oncall` nếu test tier `vip`.

- [ ] **Step 1: Test đỏ — state machine**

`thread-state.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { assertStatusTransition } from "../../services/customer-engagement/thread-state";

describe("thread status transitions", () => {
  it("allows open -> pending_customer", () => {
    expect(() => assertStatusTransition("open", "pending_customer")).not.toThrow();
  });
  it("allows resolved -> open (reopen collapses to open)", () => {
    expect(() => assertStatusTransition("resolved", "open")).not.toThrow();
  });
  it("rejects snoozed -> resolved directly", () => {
    expect(() => assertStatusTransition("snoozed", "resolved")).toThrow(/invalid/i);
  });
  it("rejects unknown target", () => {
    // @ts-expect-error deliberate
    expect(() => assertStatusTransition("open", "archived")).toThrow();
  });
});
```

- [ ] **Step 2: Chạy — đỏ.** `npx vitest run commercial/tests/customer-engagement/thread-state.test.ts`

- [ ] **Step 3: Implement `thread-state.ts`**

```typescript
import { APIError } from "encore.dev/api";

export type ThreadStatus =
  | "open" | "pending_customer" | "pending_internal" | "snoozed" | "resolved";

export type ThreadMode =
  | "human_assigned" | "team_queue" | "agent_autopilot" | "agent_copilot" | "awaiting_decision";

// Bảng chuyển hợp lệ. `reopened` KHÔNG phải persisted status — inbound message / lệnh reopen
// đưa `resolved` về `open`, và ghi outcome event riêng.
export const STATUS_TRANSITIONS: Record<ThreadStatus, ThreadStatus[]> = {
  open: ["pending_customer", "pending_internal", "snoozed", "resolved"],
  pending_customer: ["open", "pending_internal", "snoozed", "resolved"],
  pending_internal: ["open", "pending_customer", "snoozed", "resolved"],
  snoozed: ["open", "pending_customer", "pending_internal"],
  resolved: ["open"],
};

export function assertStatusTransition(from: ThreadStatus, to: ThreadStatus): void {
  const allowed = STATUS_TRANSITIONS[from];
  if (!allowed || !allowed.includes(to)) {
    throw APIError.invalidArgument(`invalid thread status transition: ${from} -> ${to}`);
  }
}
```

- [ ] **Step 4: Chạy — xanh.**

- [ ] **Step 5: Test đỏ — thread.service (real DB)**

`thread.service.test.ts` (dùng helper `makeAuthedWorkspace` như `commercial/tests/tenant-isolation.test.ts`; tạo inbox trực tiếp qua `db.insert`):

```typescript
import { describe, expect, it } from "vitest";
import { createTestSession } from "../../../identity/tests/helpers/test-session";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import { db, schema } from "../../db";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { openThread, getThread, changeThreadStatus, listThreads } from "../../services/customer-engagement/thread.service";

async function ws(name: string) {
  const u = await createTestSession({ email: `${name}-${Date.now()}-${Math.random().toString(36).slice(2)}@ex.com`, displayName: name });
  const ctx = await requireWorkspaceAccess(`Bearer ${u.accessToken}`, u.workspaceId);
  return { ctx, workspaceId: u.workspaceId };
}
// SLA_POLICY_SEED = JSON ở "P0 policy defaults" (overview). retention/sla_policy là NOT NULL.
import { SLA_POLICY_SEED } from "../../services/customer-engagement/sla.service"; // exported hằng seed
async function seedInbox(workspaceId: string, tier = "standard") {
  const id = BigInt(generateSnowflake());
  await db.insert(schema.engagementInboxes).values({
    id, workspaceId: BigInt(workspaceId), channelType: "api", name: "Primary",
    slaPolicy: SLA_POLICY_SEED, defaultTier: tier,
  });
  return String(id);
}

describe("thread.service", () => {
  it("openThread creates an open/team_queue thread scoped to workspace", async () => {
    const a = await ws("thr-a");
    const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    expect(t.status).toBe("open");
    expect(t.activeMode).toBe("team_queue");
    expect(t.correlationId).toBeTruthy();
  });

  it("getThread from another workspace throws not found", async () => {
    const a = await ws("thr-a2"); const b = await ws("thr-b2");
    const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    await expect(getThread(t.id, b.ctx)).rejects.toThrow(/not found/i);
  });

  it("changeThreadStatus enforces the transition table and records a transition row", async () => {
    const a = await ws("thr-a3");
    const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    await changeThreadStatus(t.id, { to: "pending_customer", reasonCode: "awaiting_reply" }, a.ctx);
    await expect(
      changeThreadStatus(t.id, { to: "resolved", reasonCode: "x" }, a.ctx)
    ).resolves.toMatchObject({ status: "resolved" });
    const rows = await db.execute(
      // @ts-ignore raw
      require("drizzle-orm").sql`SELECT current_state FROM engagement.engagement_thread_transitions WHERE thread_id = ${BigInt(t.id)} ORDER BY created_at`
    );
    expect((rows as any).rows.map((r: any) => r.current_state)).toEqual(["pending_customer", "resolved"]);
  });
});
```

- [ ] **Step 6: Chạy — đỏ.**

- [ ] **Step 7: Implement `thread.service.ts`**

Điểm chính:
- `openThread`: set `id = BigInt(generateSnowflake())`, `status="open"`, `activeMode="team_queue"`,
  `correlationId = params.correlationId ?? ctx.correlationId ?? \`thr_${id}\``. Trong `db.transaction`:
  insert thread → `appendOutboxEvent(tx, buildThreadOpenedEvent(...))` → insert transition row
  (`previous_state=null, current_state="open", reason_code="opened"`).
- `getThread` / `listThreads`: query với `and(eq(t.id, BigInt(id)), eq(t.workspaceId, BigInt(ctx.workspaceId)))`;
  `getThread` throw `APIError.notFound("thread not found")` khi rỗng. `listThreads` thêm filter optional,
  `limit` mặc định 50, order `created_at desc`.
- `changeThreadStatus`: load thread (scoped) → `assertStatusTransition(current, to)` → trong transaction:
  update `status` (+ `snoozed_until` nếu `to==="snoozed"`, + `resolved_at=now()` nếu `to==="resolved"`) →
  insert transition (`actor` từ `ctx` → `{ kind: "user", id: ctx.workforceMemberId ?? ctx.userId }`) →
  `appendOutboxEvent(tx, buildThreadStatusChangedEvent(...))`; nếu `to==="resolved"` thêm
  `appendOutboxEvent(tx, buildThreadResolvedEvent({ resolutionCode: params.resolutionCode ?? "resolved", ... }))`.
- Tất cả trả `ThreadDTO` qua `toThreadDTO(row)` (String hoá bigint như `toContact` trong `contact.service.ts`).

```typescript
import { APIError } from "encore.dev/api";
import { and, eq, desc, sql } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { appendOutboxEvent } from "../../../shared/events/outbox.repository";
import { TenantContext } from "../../../shared/types/tenant_context";
import {
  buildThreadOpenedEvent, buildThreadStatusChangedEvent, buildThreadResolvedEvent,
} from "../../../shared/events/customer-engagement-events";
import { assertStatusTransition, type ThreadStatus } from "./thread-state";

const { engagementThreads, engagementThreadTransitions } = schema;

export interface ThreadDTO {
  id: string; workspaceId: string; inboxId: string; contactId: string | null;
  status: string; priority: string; activeMode: string; ownerMemberId: string | null;
  correlationId: string; createdAt: string; updatedAt: string;
}

function toThreadDTO(r: typeof engagementThreads.$inferSelect): ThreadDTO {
  return {
    id: String(r.id), workspaceId: String(r.workspaceId), inboxId: String(r.inboxId),
    contactId: r.contactId ? String(r.contactId) : null, status: r.status, priority: r.priority,
    activeMode: r.activeMode, ownerMemberId: r.ownerMemberId ? String(r.ownerMemberId) : null,
    correlationId: r.correlationId, createdAt: r.createdAt.toISOString(), updatedAt: r.updatedAt.toISOString(),
  };
}
function actorOf(ctx: TenantContext) {
  return { kind: "user" as const, id: ctx.workforceMemberId ?? ctx.userId };
}

export async function openThread(
  params: { workspaceId: string; inboxId: string; contactId?: string; priority?: string; correlationId?: string },
  ctx: TenantContext,
): Promise<ThreadDTO> {
  if (String(params.workspaceId) !== String(ctx.workspaceId)) {
    throw APIError.permissionDenied("workspace mismatch");
  }
  const id = BigInt(generateSnowflake());
  const correlationId = params.correlationId ?? ctx.correlationId ?? `thr_${id}`;
  const row = await db.transaction(async (tx) => {
    const [t] = await tx.insert(engagementThreads).values({
      id, workspaceId: BigInt(params.workspaceId), inboxId: BigInt(params.inboxId),
      contactId: params.contactId ? BigInt(params.contactId) : null,
      status: "open", priority: params.priority ?? "normal", activeMode: "team_queue",
      correlationId,
    }).returning();
    if (!t) throw APIError.internal("failed to open thread");
    await appendOutboxEvent(tx, buildThreadOpenedEvent(
      { id: String(id), workspaceId: String(params.workspaceId), inboxId: String(params.inboxId), correlationId },
      actorOf(ctx),
    ));
    await tx.insert(engagementThreadTransitions).values({
      id: BigInt(generateSnowflake()), workspaceId: BigInt(params.workspaceId), threadId: id,
      actor: actorOf(ctx), reasonCode: "opened", previousState: null, currentState: "open",
      correlationId,
    });
    return t;
  });
  return toThreadDTO(row);
}

async function loadThread(id: string, ctx: TenantContext) {
  const [row] = await db.select().from(engagementThreads).where(and(
    eq(engagementThreads.id, BigInt(id)),
    eq(engagementThreads.workspaceId, BigInt(ctx.workspaceId)),
  )).limit(1);
  if (!row) throw APIError.notFound("thread not found");
  return row;
}

export async function getThread(id: string, ctx: TenantContext): Promise<ThreadDTO> {
  return toThreadDTO(await loadThread(id, ctx));
}

export async function listThreads(
  filter: { status?: string; priority?: string; ownerMemberId?: string; activeMode?: string; limit?: number },
  ctx: TenantContext,
): Promise<ThreadDTO[]> {
  const conds = [eq(engagementThreads.workspaceId, BigInt(ctx.workspaceId))];
  if (filter.status) conds.push(eq(engagementThreads.status, filter.status));
  if (filter.priority) conds.push(eq(engagementThreads.priority, filter.priority));
  if (filter.activeMode) conds.push(eq(engagementThreads.activeMode, filter.activeMode));
  if (filter.ownerMemberId) conds.push(eq(engagementThreads.ownerMemberId, BigInt(filter.ownerMemberId)));
  const rows = await db.select().from(engagementThreads).where(and(...conds))
    .orderBy(desc(engagementThreads.createdAt)).limit(filter.limit ?? 50);
  return rows.map(toThreadDTO);
}

export async function changeThreadStatus(
  id: string,
  params: { to: ThreadStatus; reasonCode: string; snoozedUntil?: string; resolutionCode?: string },
  ctx: TenantContext,
): Promise<ThreadDTO> {
  const current = await loadThread(id, ctx);
  assertStatusTransition(current.status as ThreadStatus, params.to);
  const updated = await db.transaction(async (tx) => {
    const patch: Record<string, unknown> = { status: params.to, updatedAt: new Date() };
    if (params.to === "snoozed") patch.snoozedUntil = params.snoozedUntil ? new Date(params.snoozedUntil) : null;
    if (params.to === "resolved") patch.resolvedAt = new Date();
    const [row] = await tx.update(engagementThreads).set(patch).where(and(
      eq(engagementThreads.id, BigInt(id)),
      eq(engagementThreads.workspaceId, BigInt(ctx.workspaceId)),
    )).returning();
    await tx.insert(engagementThreadTransitions).values({
      id: BigInt(generateSnowflake()), workspaceId: BigInt(ctx.workspaceId), threadId: BigInt(id),
      actor: actorOf(ctx), reasonCode: params.reasonCode,
      previousState: current.status, currentState: params.to, correlationId: current.correlationId,
    });
    await appendOutboxEvent(tx, buildThreadStatusChangedEvent({
      threadId: id, workspaceId: String(ctx.workspaceId),
      previousState: current.status, currentState: params.to, correlationId: current.correlationId,
    }, actorOf(ctx)));
    if (params.to === "resolved") {
      await appendOutboxEvent(tx, buildThreadResolvedEvent({
        threadId: id, workspaceId: String(ctx.workspaceId),
        resolutionCode: params.resolutionCode ?? "resolved", correlationId: current.correlationId,
      }, actorOf(ctx)));
    }
    return row;
  });
  return toThreadDTO(updated);
}
```

- [ ] **Step 8: Implement `rbac.ts`**

```typescript
import { APIError } from "encore.dev/api";
import { TenantContext } from "../../../shared/types/tenant_context";

export const ENGAGEMENT_PERMISSIONS = {
  threadRead: "engagement.thread.read",
  threadWrite: "engagement.thread.write",
  messageSend: "engagement.message.send",
  threadTakeover: "engagement.thread.takeover",
  decisionReview: "engagement.decision_request.review",
  decisionDecide: "engagement.decision_request.decide",
} as const;

export function requireEngagementPermission(ctx: TenantContext, perm: string): void {
  if (!ctx.permissions.includes(perm)) {
    throw APIError.permissionDenied(`missing permission: ${perm}`);
  }
}
```

> **Note về test:** `createTestSession` cấp `permissions` gì cho `TenantContext` phải kiểm khi viết
> test — nếu helper không cấp `engagement.*`, thêm 1 helper test `grantEngagementPermissions(ctx)` hoặc
> mở rộng `createTestSession` để nhận `permissions`. Kiểm `identity/tests/helpers/test-session.ts` +
> `resolveTenantContext` trước khi viết Task 13.

- [ ] **Step 9: Chạy — xanh.** `npx vitest run commercial/tests/customer-engagement/thread-state.test.ts commercial/tests/customer-engagement/thread.service.test.ts`

- [ ] **Step 10: Commit**

```bash
git add services/company/commercial/services/customer-engagement/thread-state.ts services/company/commercial/services/customer-engagement/thread.service.ts services/company/commercial/services/customer-engagement/rbac.ts services/company/commercial/tests/customer-engagement/thread-state.test.ts services/company/commercial/tests/customer-engagement/thread.service.test.ts
git commit -m "feat(engagement): thread state machine + open/get/list/status service"
```

---

### Task 5: Message service — internal note / public message / inbound + idempotency

**Files:**
- Create: `services/company/commercial/services/customer-engagement/message.service.ts`
- Test: `services/company/commercial/tests/customer-engagement/message.service.test.ts`

**Interfaces:**
- Produces:
  - `postInternalNote({ threadId; body; idempotencyKey }, ctx): Promise<MessageDTO>` — `direction="system"`
    hoặc `"outbound"`? → **`direction` phải là `system` hoặc `internal`?** Chốt: internal note dùng
    `direction: "outbound"` **cấm**; dùng `direction: "system"`, `visibility: "internal"`. Không tạo
    delivery row.
  - `sendPublicMessage({ threadId; body; idempotencyKey }, ctx): Promise<MessageDTO>` —
    `direction="outbound", visibility="customer", delivery_state="queued"`; tạo
    `engagement_outbound_deliveries` row cùng transaction; `appendOutboxEvent(buildMessageSentEvent)`.
  - `recordInboundMessage({ threadId; body; idempotencyKey; senderRef?; externalMessageId? }, ctx):
    Promise<MessageDTO>` — `direction="inbound", visibility="customer"`;
    `appendOutboxEvent(buildMessageReceivedEvent)`; cập nhật `thread.last_customer_msg_at`; nếu thread
    `resolved` → chuyển về `open` (reopen) qua `changeThreadStatus`-tương-đương trong cùng tx + outcome
    row `reopened`.
  - `MessageDTO = { id; threadId; direction; visibility; senderKind; body; deliveryState: string|null; idempotencyKey; createdAt }`
- Idempotency: retry cùng `(threadId, idempotencyKey)` → trả message đã tồn tại (SELECT trước; hoặc
  `onConflictDoNothing` rồi SELECT), **không** tạo trùng, **không** phát event lần 2.
- Consumes: `db`, builders Task 3, `generateSnowflake`, `sha256` (`node:crypto`), `loadThread` logic
  (copy nội bộ hoặc export từ `thread.service`).

- [ ] **Step 1: Test đỏ**

```typescript
import { describe, expect, it } from "vitest";
// ... ws(), seedInbox() như Task 4 ...
import { openThread, getThread } from "../../services/customer-engagement/thread.service";
import { postInternalNote, sendPublicMessage, recordInboundMessage } from "../../services/customer-engagement/message.service";
import { db } from "../../db";
import { sql } from "drizzle-orm";

describe("message.service", () => {
  it("internal note has no delivery row and visibility=internal", async () => {
    const a = await ws("msg-a"); const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    const m = await postInternalNote({ threadId: t.id, body: "handoff: khách bực", idempotencyKey: "n1" }, a.ctx);
    expect(m.visibility).toBe("internal");
    expect(m.deliveryState).toBeNull();
    const d = await db.execute(sql`SELECT count(*)::int c FROM engagement.engagement_outbound_deliveries WHERE message_id = ${BigInt(m.id)}`);
    expect((d as any).rows[0].c).toBe(0);
  });

  it("public message enqueues exactly one delivery; retry with same key is idempotent", async () => {
    const a = await ws("msg-b"); const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    const m1 = await sendPublicMessage({ threadId: t.id, body: "Chào anh", idempotencyKey: "p1" }, a.ctx);
    const m2 = await sendPublicMessage({ threadId: t.id, body: "Chào anh", idempotencyKey: "p1" }, a.ctx);
    expect(m2.id).toBe(m1.id);
    const d = await db.execute(sql`SELECT count(*)::int c FROM engagement.engagement_outbound_deliveries WHERE thread_id = ${BigInt(t.id)}`);
    expect((d as any).rows[0].c).toBe(1);
  });

  it("inbound on a resolved thread reopens it to open", async () => {
    const a = await ws("msg-c"); const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    // resolve
    const { changeThreadStatus } = await import("../../services/customer-engagement/thread.service");
    await changeThreadStatus(t.id, { to: "resolved", reasonCode: "done" }, a.ctx);
    await recordInboundMessage({ threadId: t.id, body: "còn lỗi nữa", idempotencyKey: "i1" }, a.ctx);
    expect((await getThread(t.id, a.ctx)).status).toBe("open");
  });
});
```

- [ ] **Step 2: Chạy — đỏ.**

- [ ] **Step 3: Implement `message.service.ts`**

Điểm chính:
- Helper `findExisting(threadId, key, ctx)` → SELECT theo `(thread_id, idempotency_key, workspace_id)`;
  nếu có, trả `toMessageDTO`.
- `bodyContentHash = createHash("sha256").update(body).digest("hex")`.
- **`retentionUntil` bắt buộc (NOT NULL, fail-closed)** trên mọi insert message: `= created_at + 365 ngày`
  (hằng `RETENTION_TRANSCRIPT_DAYS = 365` trong module retention dùng chung; xem "P0 policy defaults").
  Không insert message thiếu `retention_until`.
- `postInternalNote`: insert message (`direction:"system", visibility:"internal", senderKind:"workforce_member",
  senderRef: ctx.workforceMemberId ?? ctx.userId, deliveryState: null`). Không event outbox (note nội bộ
  không phải business fact ra ngoài) — hoặc phát `engagement.message.received.v1`? **Chốt: không phát**;
  internal note không phải public fact.
- `sendPublicMessage`: load thread (scoped). Trong transaction: insert message
  (`direction:"outbound", visibility:"customer", deliveryState:"queued"`) → insert
  `engagement_outbound_deliveries` (`status:"queued", idempotencyKey: \`snd_${message.id}\``,
  `channelType` = inbox.channel_type — cần join inbox) → `appendOutboxEvent(tx, buildMessageSentEvent(...))`.
  Nếu `findExisting` có → trả luôn, bỏ qua.
- `recordInboundMessage`: load thread. Trong transaction: insert message
  (`direction:"inbound", visibility:"customer", senderKind:"customer"`) → update thread
  `last_customer_msg_at=now()` → nếu `thread.status === "resolved"`: update `status="open"` + insert
  transition (`reason_code:"reopened_by_inbound"`, `previous_state:"resolved"`, `current_state:"open"`) +
  insert `engagement_thread_outcomes` (`intent:null, resolution_code:null, escalation_reason:"reopened"`)
  → `appendOutboxEvent(tx, buildMessageReceivedEvent(...))` (+ `buildThreadStatusChangedEvent` nếu reopen).
- `toMessageDTO` String-hoá.

(Code đầy đủ ~120 dòng — engineer viết theo mô tả + pattern `thread.service.ts` Task 4. Mọi insert set
`id = BigInt(generateSnowflake())`, mọi query ràng `workspace_id`.)

- [ ] **Step 4: Chạy — xanh.**

- [ ] **Step 5: Commit**

```bash
git add services/company/commercial/services/customer-engagement/message.service.ts services/company/commercial/tests/customer-engagement/message.service.test.ts
git commit -m "feat(engagement): message service (internal note / public / inbound) with idempotency + reopen"
```

---

### Task 6: Assignment + atomic Takeover

**Files:**
- Create: `services/company/commercial/services/customer-engagement/assignment.service.ts`
- Test: `services/company/commercial/tests/customer-engagement/assignment.service.test.ts`

**Interfaces:**
- Produces:
  - `assignThread({ threadId; teamId?; memberId?; agentSpecId?; reason }, ctx): Promise<AssignmentDTO>` —
    end assignment active hiện tại (`ended_at=now()`), insert assignment mới, set
    `thread.owner_member_id` + `thread.active_mode` (`human_assigned` nếu có `memberId`, else
    `team_queue`); `appendOutboxEvent(buildThreadAssignedEvent)`.
  - `takeOverThread({ threadId; reason }, ctx): Promise<AssignmentDTO>` — **atomic**: end assignment
    agent/khác → insert assignment cho `ctx.workforceMemberId` → `thread.active_mode="human_assigned"`,
    `owner_member_id=ctx.workforceMemberId` → **UPDATE mọi `engagement_messages` của thread có
    `direction="outbound" AND visibility="customer" AND delivery_state="queued"` set
    `delivery_state="cancelled"`** và **UPDATE `engagement_outbound_deliveries` `status="queued"` set
    `status="failed", dead_letter_reason="superseded_by_takeover"`** → insert transition
    (`reason_code:"taken_over"`, `current_mode:"human_assigned"`) → `appendOutboxEvent(buildThreadTakenOverEvent)`.
    Yêu cầu `requireEngagementPermission(ctx, "engagement.thread.takeover")`.
  - `handBackToAgent({ threadId; agentSpecId; scope; expiresAt }, ctx): Promise<AssignmentDTO>` — end
    human assignment, insert assignment agent với `reason` ghi `scope`+`expiresAt` (JSON trong `reason`
    hoặc cột riêng — P0 nhét vào `reason` string), `active_mode="agent_copilot"`; transition
    `reason_code:"handed_back"`. **Không** vô thời hạn: `expiresAt` bắt buộc.
  - `AssignmentDTO = { id; threadId; assignedTeamId: string|null; assignedMemberId: string|null; assignedAgentSpecId: string|null; reason; assignedAt; endedAt: string|null }`
- Concurrency: partial unique index `uq_engagement_assignments_active` đảm bảo 2 takeover đồng thời →
  1 thắng, cái kia lỗi unique → bắt lại, retry đọc, trả assignment hiện hành hoặc throw
  `APIError.alreadyExists("thread already taken over")`.

- [ ] **Step 1: Test đỏ**

```typescript
describe("assignment.service", () => {
  it("takeOver cancels queued outbound messages and wins over a prior agent assignment", async () => {
    const a = await ws("asg-a"); const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    // giả lập agent đã enqueue 1 outbound
    await sendPublicMessage({ threadId: t.id, body: "auto reply", idempotencyKey: "auto1" }, a.ctx);
    await takeOverThread({ threadId: t.id, reason: "manual handling" }, a.ctx);
    const th = await getThread(t.id, a.ctx);
    expect(th.activeMode).toBe("human_assigned");
    const m = await db.execute(sql`SELECT delivery_state FROM engagement.engagement_messages WHERE thread_id = ${BigInt(t.id)} AND direction='outbound'`);
    expect((m as any).rows.every((r: any) => r.delivery_state === "cancelled")).toBe(true);
    const d = await db.execute(sql`SELECT status, dead_letter_reason FROM engagement.engagement_outbound_deliveries WHERE thread_id = ${BigInt(t.id)}`);
    expect((d as any).rows[0]).toMatchObject({ status: "failed", dead_letter_reason: "superseded_by_takeover" });
  });

  it("two concurrent takeovers: exactly one active assignment remains", async () => {
    const a = await ws("asg-b"); const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    const results = await Promise.allSettled([
      takeOverThread({ threadId: t.id, reason: "r1" }, a.ctx),
      takeOverThread({ threadId: t.id, reason: "r2" }, a.ctx),
    ]);
    const ok = results.filter((r) => r.status === "fulfilled").length;
    expect(ok).toBeGreaterThanOrEqual(1);
    const act = await db.execute(sql`SELECT count(*)::int c FROM engagement.engagement_assignments WHERE thread_id = ${BigInt(t.id)} AND ended_at IS NULL`);
    expect((act as any).rows[0].c).toBe(1);
  });
});
```

- [ ] **Step 2: Chạy — đỏ.**
- [ ] **Step 3: Implement `assignment.service.ts`** theo Interfaces trên. Toàn bộ end+insert+update+event
  trong **một** `db.transaction`. Bắt lỗi Postgres unique violation (`e.code === "23505"`) trên
  `uq_engagement_assignments_active` → throw `APIError.alreadyExists(...)`.
- [ ] **Step 4: Chạy — xanh.**
- [ ] **Step 5: Commit**

```bash
git add services/company/commercial/services/customer-engagement/assignment.service.ts services/company/commercial/tests/customer-engagement/assignment.service.test.ts
git commit -m "feat(engagement): assignment + atomic takeover (cancels queued sends, single active assignment)"
```

---

### Task 7: Channel Adapter contract + `api` adapter + registry

**Files:**
- Create: `services/company/commercial/services/customer-engagement/channel-adapters/contract.ts`
- Create: `services/company/commercial/services/customer-engagement/channel-adapters/api-channel.adapter.ts`
- Create: `services/company/commercial/services/customer-engagement/channel-adapters/registry.ts`
- Test: `services/company/commercial/tests/customer-engagement/channel-adapter.test.ts`

**Interfaces:**
- Produces `contract.ts`:

```typescript
export interface VerifiedInbound {
  externalMessageId: string;
  senderRef: string;
  body: string;
  receivedAt: string;
}
export interface OutboundCommand {
  deliveryId: string;
  threadId: string;
  body: string;
  endpointProviderRef: string | null;
  secretRef: string | null;
}
export interface DeliveryResult {
  status: "sent" | "failed";
  externalMessageId?: string;
  error?: string;
}
export interface ChannelAdapter {
  readonly channelType: string;
  verifyInbound(raw: unknown): Promise<VerifiedInbound>;
  normalizeInbound(v: VerifiedInbound): { body: string; senderRef: string; externalMessageId: string };
  sendOutbound(cmd: OutboundCommand): Promise<DeliveryResult>;
  getDeliveryStatus(externalMessageId: string): Promise<"sent" | "delivered" | "failed" | "unknown">;
  resolveExternalIdentity(senderRef: string): Promise<{ email?: string; phone?: string }>;
}
```

- `api-channel.adapter.ts`: `ApiChannelAdapter implements ChannelAdapter`, `channelType = "api"`.
  `verifyInbound` tin request nội bộ đã auth — chỉ validate shape (`{ externalMessageId, senderRef, body }`),
  throw `APIError.invalidArgument` nếu thiếu. `sendOutbound` → `{ status: "sent", externalMessageId: \`api_${cmd.deliveryId}\` }`.
  `getDeliveryStatus` → `"sent"`. `resolveExternalIdentity(senderRef)` → nếu `senderRef` là email hợp lệ
  trả `{ email: senderRef }`, else `{}`.
- `registry.ts`: `getChannelAdapter(channelType: string): ChannelAdapter` — map `{ api: new ApiChannelAdapter() }`;
  throw `APIError.invalidArgument(\`no channel adapter for ${channelType}\`)` nếu chưa hỗ trợ. (P2 thêm entries.)

- [ ] **Step 1: Test đỏ**

```typescript
import { describe, expect, it } from "vitest";
import { getChannelAdapter } from "../../services/customer-engagement/channel-adapters/registry";

describe("channel adapter (api)", () => {
  it("verifyInbound rejects malformed payloads", async () => {
    const a = getChannelAdapter("api");
    await expect(a.verifyInbound({ body: "hi" })).rejects.toThrow(/invalid/i);
  });
  it("sendOutbound returns sent with a synthetic external id", async () => {
    const a = getChannelAdapter("api");
    const r = await a.sendOutbound({ deliveryId: "9", threadId: "1", body: "x", endpointProviderRef: null, secretRef: null });
    expect(r.status).toBe("sent");
    expect(r.externalMessageId).toBe("api_9");
  });
  it("registry throws for unknown channel", () => {
    expect(() => getChannelAdapter("telegram")).toThrow(/no channel adapter/i);
  });
});
```

- [ ] **Step 2: Chạy — đỏ.**
- [ ] **Step 3: Implement 3 file** theo Interfaces.
- [ ] **Step 4: Chạy — xanh.**
- [ ] **Step 5: Commit**

```bash
git add services/company/commercial/services/customer-engagement/channel-adapters/
git add services/company/commercial/tests/customer-engagement/channel-adapter.test.ts
git commit -m "feat(engagement): provider-agnostic ChannelAdapter contract + api reference adapter"
```

---

### Task 8: Outbound delivery relay + cron + pre-delivery ownership re-check

**Files:**
- Create: `services/company/commercial/services/customer-engagement/delivery-relay.service.ts`
- Create: `services/company/commercial/services/customer-engagement/delivery-relay.cron.ts`
- Test: `services/company/commercial/tests/customer-engagement/delivery-relay.test.ts`

**Interfaces:**
- Produces:
  - `deliveryRelayTick(limit?: number): Promise<{ claimed: number; sent: number; failed: number }>` — claim
    `engagement_outbound_deliveries` `status='queued' OR (status='sent'?? no)`; đúng hơn: claim
    `status='queued' OR (status='queued' AND visibility_timeout_at < now())` bằng `FOR UPDATE SKIP LOCKED`
    (pattern `claimDueOutboxEvents` trong `shared/events/outbox.repository.ts`), set `claim_token`,
    `attempt_count++`, `visibility_timeout_at = now() + interval '120s'`.
  - Cho từng row: load message + thread (scoped by `workspace_id`). **Pre-delivery ownership re-check**:
    nếu `message.delivery_state !== 'queued'` (đã cancelled) HOẶC `thread.active_mode === 'human_assigned'`
    và message do automation/agent tạo → **drop**: set delivery `status='failed'`,
    `dead_letter_reason='ownership_changed'`, message giữ `cancelled`; ghi transition
    (`reason_code='delivery_dropped_ownership'`). Không gọi adapter.
  - Ngược lại: `getChannelAdapter(delivery.channel_type).sendOutbound({...})`. `sent` → delivery
    `status='sent'`, `external_message_id`, message `delivery_state='sent'`. `failed` → nếu
    `attempt_count >= max_attempts` → `status='failed'`, `dead_letter_reason`; else về `status='queued'`,
    `visibility_timeout_at = now() + backoff` (exponential, cap 300s — pattern `failOutboxEvent`).
  - `delivery-relay.cron.ts`: `CronJob("engagement-delivery-relay", { every: "1m", endpoint })` giống
    `events/outbox-relay.cron.ts`.
- Consumes: `db` (raw `sql` cho claim), `getChannelAdapter` (Task 7), `generateSnowflake`.

- [ ] **Step 1: Test đỏ**

```typescript
describe("delivery-relay", () => {
  it("delivers a queued api message and marks it sent", async () => {
    const a = await ws("rel-a"); const inbox = await seedInbox(a.workspaceId); // channelType api
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    const m = await sendPublicMessage({ threadId: t.id, body: "hi", idempotencyKey: "r1" }, a.ctx);
    const res = await deliveryRelayTick(10);
    expect(res.sent).toBeGreaterThanOrEqual(1);
    const d = await db.execute(sql`SELECT status FROM engagement.engagement_outbound_deliveries WHERE message_id = ${BigInt(m.id)}`);
    expect((d as any).rows[0].status).toBe("sent");
  });

  it("drops delivery when human has taken over before the tick", async () => {
    const a = await ws("rel-b"); const inbox = await seedInbox(a.workspaceId);
    const t = await openThread({ workspaceId: a.workspaceId, inboxId: inbox }, a.ctx);
    await sendPublicMessage({ threadId: t.id, body: "auto", idempotencyKey: "r2" }, a.ctx);
    await takeOverThread({ threadId: t.id, reason: "manual" }, a.ctx); // cancels queued
    const res = await deliveryRelayTick(10);
    expect(res.sent).toBe(0);
    const d = await db.execute(sql`SELECT status, dead_letter_reason FROM engagement.engagement_outbound_deliveries WHERE thread_id = ${BigInt(t.id)}`);
    expect((d as any).rows[0]).toMatchObject({ status: "failed" });
  });
});
```

> Takeover (Task 6) đã set delivery `status='failed'` nên tick sẽ không claim — test thứ 2 vẫn hợp lệ
> (`sent===0`). Nếu muốn test đúng nhánh "relay tự drop", tạo delivery `status='queued'` thủ công + set
> `thread.active_mode='human_assigned'` rồi tick.

- [ ] **Step 2: Chạy — đỏ.**
- [ ] **Step 3: Implement** theo Interfaces (tham chiếu `shared/events/outbox.repository.ts` cho SQL
  claim/backoff và `events/outbox-relay.service.ts` cho vòng lặp).
- [ ] **Step 4: Chạy — xanh.**
- [ ] **Step 5: Commit**

```bash
git add services/company/commercial/services/customer-engagement/delivery-relay.service.ts services/company/commercial/services/customer-engagement/delivery-relay.cron.ts services/company/commercial/tests/customer-engagement/delivery-relay.test.ts
git commit -m "feat(engagement): outbound delivery relay with pre-delivery ownership re-check + DLQ"
```

---

### Task 9: Customer 360 read model + identity resolution

**Files:**
- Create: `services/company/commercial/services/customer-engagement/customer360.service.ts`
- Create: `services/company/commercial/services/customer-engagement/identity-resolution.service.ts`
- Test: `services/company/commercial/tests/customer-engagement/customer360.service.test.ts`
- Test: `services/company/commercial/tests/customer-engagement/identity-resolution.test.ts`

**Interfaces:**
- `getCustomer360(contactId: string, ctx): Promise<Customer360DTO>` — 1 truy vấn/nhiều truy vấn, **mọi**
  bảng ràng `workspace_id = ctx.workspaceId`. `Customer360DTO = { contact; account: {...}|null;
  leads: [...]; opportunities: [...]; customer: {...}|null; invoices: [...]; subscriptions: [...];
  recentInteractions: [...] }`. Throw `notFound` nếu contact khác workspace / không tồn tại.
  **Không** trả field billing/subscription nếu `opts.identityVerified === false` → chỉ trả
  `{ contact, account, leads, opportunities }` (spec §11.4). Chữ ký:
  `getCustomer360(contactId, ctx, opts?: { identityVerified?: boolean })`.
- `resolveContact(input: { email?: string; phone?: string; emailVerified?: boolean }, threadId: string, ctx):
  Promise<{ contactId: string | null; reviewItemId: string | null }>`:
  1. Nếu `email && emailVerified` → tìm `sales.contacts` `lower(email)=lower(input.email)` scoped; đúng 1
     → trả `contactId`. >1 → tạo `engagement_identity_review_items` (`reason:"multiple_candidates"`),
     trả `{ contactId: null, reviewItemId }`.
  2. Nếu match contact có `do_not_contact=true` → review item `reason:"do_not_contact"`, `contactId: null`.
  3. `phone` chỉ dùng khi không có email match; E.164 exact; nếu phone match nhiều account khác nhau →
     review `reason:"account_conflict"`.
  4. Email chưa verified → review `reason:"unverified"`, `contactId: null`.
  5. Không match gì → `{ contactId: null, reviewItemId: null }` (thread giữ contact null).
  **Không bao giờ** tự merge/insert contact.

- [ ] **Step 1: Test đỏ (customer360)** — seed `sales.accounts` + `sales.contacts` + `commercial.invoices`
  ở workspace A, verify aggregation trả đủ; verify workspace B nhận `notFound`; verify
  `identityVerified:false` ẩn invoices/subscriptions.
- [ ] **Step 2: Chạy — đỏ.**
- [ ] **Step 3: Implement `customer360.service.ts`** — dùng `db.select().from(schema.contacts).where(and(eq(id), eq(workspaceId)))`
  rồi các truy vấn con theo `contactId`/`accountId`, tất cả kèm `eq(*.workspaceId, BigInt(ctx.workspaceId))`.
- [ ] **Step 4: Test đỏ (identity-resolution)** — 5 nhánh trên, mỗi nhánh 1 `it`.
- [ ] **Step 5: Chạy — đỏ → implement `identity-resolution.service.ts` → xanh.**
- [ ] **Step 6: Commit**

```bash
git add services/company/commercial/services/customer-engagement/customer360.service.ts services/company/commercial/services/customer-engagement/identity-resolution.service.ts services/company/commercial/tests/customer-engagement/customer360.service.test.ts services/company/commercial/tests/customer-engagement/identity-resolution.test.ts
git commit -m "feat(engagement): customer 360 read model + non-merging identity resolution"
```

---

### Task 10: Decision Request — state machine + authority binding (fail-closed) + N-of-M approvers + execution guard

**Files:**
- Create: `services/company/commercial/services/customer-engagement/decision-request-state.ts`
- Create: `services/company/commercial/services/customer-engagement/decision-authority.service.ts`
- Create: `services/company/commercial/services/customer-engagement/decision-request.service.ts`
- Test: `services/company/commercial/tests/customer-engagement/decision-request-state.test.ts`
- Test: `services/company/commercial/tests/customer-engagement/decision-authority.service.test.ts`
- Test: `services/company/commercial/tests/customer-engagement/decision-request.service.test.ts`

> **Chốt 2026-08-28 — authority model (xem "P0 policy defaults"):** authority **không** suy từ role
> title / "admin" / "founder". Mỗi `authority_key` có `approval_policy` jsonb
> `{ required_capabilities: string[], distinct_approvers: N, requester_must_differ: true,
> requester_cannot_execute: true }`. Authority seed ở `status='pending_binding'`; chỉ `enabled` khi
> **mọi** capability trong `required_capabilities` có ≥1 grant active
> (`engagement_decision_authority_grants`). **Fail-closed**: authority không `enabled` ⇒ không cho
> submit/decide/execute.

**Interfaces:**
- `decision-request-state.ts`: `type DRStatus = "draft"|"submitted"|"under_review"|"needs_information"|"approved"|"execution_pending"|"executed"|"rejected"|"expired"`;
  `DR_TRANSITIONS: Record<DRStatus, DRStatus[]>`:
  ```
  draft: [submitted]
  submitted: [under_review, rejected, expired]
  under_review: [approved, rejected, needs_information, expired]
  needs_information: [submitted, expired]
  approved: [execution_pending, expired]
  execution_pending: [executed, rejected, expired]
  executed: []
  rejected: []
  expired: []
  ```
  `assertDRTransition(from, to): void`.
- `decision-authority.service.ts`:
  - `seedDecisionAuthority({ workspaceId; authorityKey; decisionKind; matchCriteria; approvalPolicy }, ctx): Promise<AuthorityDTO>` —
    insert `status='pending_binding'`, `version=1`.
  - `grantAuthorityCapability({ workspaceId; authorityKey; workforceMemberId; capability; activeUntil? }, ctx): Promise<void>` —
    insert grant; sau đó gọi `recomputeAuthorityStatus(authorityKey, ctx)`.
  - `recomputeAuthorityStatus(authorityKey, ctx): Promise<"pending_binding" | "enabled">` — set `enabled`
    nếu mọi capability trong `approval_policy.required_capabilities` có ≥1 grant active (`active_from <=
    now() < coalesce(active_until, 'infinity')`); ngược lại `pending_binding`. Audit thay đổi status.
  - `resolveEnabledAuthority(authorityKey, ctx): Promise<{ authority; approvalPolicy }>` — trả authority
    `status='enabled'` trong `[effective_from, effective_until)`; nếu không → `APIError.failedPrecondition("authority not enabled: <key>")` (**fail-closed**).
  - `memberCoversCapability(workforceMemberId, authorityKey, ctx): Promise<string | null>` — trả
    `capability` nếu member có grant active cho một capability của authority; else null.
  - `assertApprovalPolicySatisfied(approvalPolicy, approvalRows): void` — throw nếu chưa đủ:
    số approver `distinct` < `distinct_approvers`, hoặc union capability chưa phủ hết `required_capabilities`,
    hoặc có approver = requester khi `requester_must_differ`.
- `decision-request.service.ts`:
  - `createDecisionRequest({ threadId?; requestType; contactId?; ...; options; factsRef?; recommendationRef?; authorityKey }, ctx): Promise<DR_DTO>` —
    status `draft`. `resolveEnabledAuthority(authorityKey, ctx)` (fail-closed) → snapshot `authority_version`
    + `approval_policy_snapshot`. `requested_by_workforce_member_id = ctx.workforceMemberId` (bắt buộc; nếu
    null → `APIError.permissionDenied("requester must be a workforce member")`). `correlation_id` từ thread
    nếu có, else `dr_<id>`.
  - `submitDecisionRequest(id, { policyId; policyVersion; policySnapshotRef }, ctx): Promise<DR_DTO>` —
    **bắt buộc** `policySnapshotRef`; re-`resolveEnabledAuthority` (fail-closed); `draft→submitted`;
    event `submitted`; `appendOutboxEvent(buildDecisionRequestSubmittedEvent)`;
    `thread.active_mode="awaiting_decision"` nếu có thread.
  - `startReview(id, ctx)` — `requireEngagementPermission(ctx, "engagement.decision_request.review")`;
    `submitted→under_review`; event `review_started`.
  - `recordApproval(id, { decision: "approve"|"reject"|"needs_information"; reason }, ctx): Promise<DR_DTO>`:
    - `requireEngagementPermission(ctx, "engagement.decision_request.decide")`.
    - `cap = memberCoversCapability(ctx.workforceMemberId, dr.authority_key, ctx)`; null → `APIError.permissionDenied("no active grant for this authority")` (**fail-closed**).
    - `ctx.workforceMemberId === dr.requested_by_workforce_member_id` → `APIError.permissionDenied("requester cannot approve")`.
    - Insert `engagement_decision_request_approvals` (unique `(dr_id, workforce_member_id)` → cùng người
      lần 2 = `APIError.alreadyExists("already recorded an approval")`). Event `approval_recorded`.
    - `reject` bất kỳ → `status="rejected"`, `decision="rejected"`, event `rejected` +
      `appendOutboxEvent(buildDecisionRequestDecidedEvent)`.
    - `needs_information` → `status="needs_information"`, event.
    - Sau mỗi `approve`: `assertApprovalPolicySatisfied(dr.approval_policy_snapshot, allApprovalRows)`;
      nếu thoả → `status="approved"`, `decision="approved"`, `approved_at=now()`, event `approved` +
      `appendOutboxEvent(buildDecisionRequestDecidedEvent)`. Nếu chưa đủ → giữ `under_review`.
  - `executeDecisionRequest(id, ctx): Promise<DR_DTO>` — **execution guard (fail-closed, kiểm tất cả)**:
    1. `dr.status === "approved"` (else `APIError.failedPrecondition`).
    2. `dr.approval_deadline && dr.approval_deadline < now()` → `status="expired"`, event `expired`,
       throw `APIError.invalidArgument("decision request expired")`.
    3. `resolveEnabledAuthority(dr.authority_key, ctx)` — authority vẫn `enabled` (bị disable sau approve
       ⇒ chặn).
    4. `requireEngagementPermission(ctx, "engagement.decision_request.decide")` +
       `memberCoversCapability(ctx.workforceMemberId, dr.authority_key, ctx)` ≠ null.
    5. `dr.approval_policy_snapshot.requester_cannot_execute` (mặc định true) &&
       `ctx.workforceMemberId === dr.requested_by_workforce_member_id` → `APIError.permissionDenied`.
    6. Re-`assertApprovalPolicySatisfied` trên approval rows hiện tại (grant có thể đã hết hạn giữa chừng).
    7. `approved→execution_pending→executed`; P0 **không** gọi `billing.*` — `execution_ref = \`noop_${id}\``,
       `executed_by_workforce_member_id = ctx.workforceMemberId`, event `execution_started` + `executed`.
  - `expireDueDecisionRequests(): Promise<number>` — batch: DR `status IN (submitted, under_review,
    needs_information, approved, execution_pending)` có `approval_deadline < now()` → `status="expired"` +
    event. Dùng bởi cron `engagement-housekeeping` (Task 12).
- `DR_DTO` String-hoá đủ field cho Desk decision queue (gồm `authorityKey`, `status`, `decision`,
  `approvals: [{ workforceMemberId, capability, decision, decidedAt }]`, `approvalDeadline`).

- [ ] **Step 1: Test đỏ — state table** (`assertDRTransition`: cho phép `under_review→approved`, chặn
  `approved→executed` trực tiếp, chặn `rejected→*`). → implement `decision-request-state.ts` → xanh.
- [ ] **Step 2: Test đỏ — `decision-authority.service` (real DB)**:
  - `seedDecisionAuthority` → `status='pending_binding'`.
  - `grantAuthorityCapability` cho **một phần** `required_capabilities` → vẫn `pending_binding`.
  - grant đủ mọi capability → `recomputeAuthorityStatus` = `enabled`.
  - `resolveEnabledAuthority` khi `pending_binding` → throw `failedPrecondition` (**fail-closed**).
  - `assertApprovalPolicySatisfied`: 1 approver khi cần 2 distinct → throw; 2 distinct đủ capability → OK;
    2 approver nhưng cùng người (không thể do unique) / thiếu capability → throw.
  → implement → xanh.
- [ ] **Step 3: Test đỏ — `decision-request.service` (real DB)**, tối thiểu:
  - `create`/`submit` fail khi authority `pending_binding` (**fail-closed**); pass sau khi authority `enabled`.
  - `submit` fail khi thiếu `policySnapshotRef`.
  - `recordApproval` bởi requester → `permissionDenied` (`requester_must_differ`).
  - `recordApproval` bởi member không có grant → `permissionDenied` (no active grant).
  - `distinct_approvers: 2` (vd. `commercial.pricing.exception`): 1 approve → vẫn `under_review`, execute
    bị chặn; approver thứ 2 khác người, capability còn thiếu → `assertApprovalPolicySatisfied` throw;
    approver thứ 2 phủ nốt capability → `approved`; execute → `executed`.
  - `distinct_approvers: 3` (`commercial.pricing.high_risk`): chỉ `approved` sau 3 approver phân biệt
    phủ đủ `sales`/`finance`/`business_owner` capability.
  - `approval_deadline` quá khứ khi `execute` → `expired` + throw, **không** `executed`, `execution_ref` null.
  - authority bị `disabled` sau khi `approved` → `execute` bị chặn (`failedPrecondition`).
  - `requester_cannot_execute`: requester gọi `execute` → `permissionDenied`.
  - `billing.refund_or_credit`: requester không được ghi vào approvals lẫn execute (cả 2 chặn).
- [ ] **Step 4: đỏ → implement `decision-authority.service.ts` + `decision-request.service.ts` → xanh.**
- [ ] **Step 5: Commit**

```bash
git add services/company/commercial/services/customer-engagement/decision-request-state.ts services/company/commercial/services/customer-engagement/decision-authority.service.ts services/company/commercial/services/customer-engagement/decision-request.service.ts services/company/commercial/tests/customer-engagement/decision-request-state.test.ts services/company/commercial/tests/customer-engagement/decision-authority.service.test.ts services/company/commercial/tests/customer-engagement/decision-request.service.test.ts
git commit -m "feat(engagement): decision authority binding (fail-closed) + N-of-M distinct approvers + execution guard"
```

---

### Task 11: Handlers + RBAC wiring + Encore surface

**Files:**
- Create: `services/company/commercial/handlers/customer-engagement/inbox.handler.ts`
- Create: `services/company/commercial/handlers/customer-engagement/thread.handler.ts`
- Create: `services/company/commercial/handlers/customer-engagement/message.handler.ts`
- Create: `services/company/commercial/handlers/customer-engagement/assignment.handler.ts`
- Create: `services/company/commercial/handlers/customer-engagement/customer360.handler.ts`
- Create: `services/company/commercial/handlers/customer-engagement/decision-request.handler.ts`
- Create: `services/company/commercial/handlers/customer-engagement/decision-authority.handler.ts`
- Create: `services/company/commercial/handlers/customer-engagement/escalation-route.handler.ts`
- Create: `services/company/commercial/handlers/customer-engagement/data-subject-request.handler.ts`
- Create: `services/company/commercial/handlers/customer-engagement/legal-hold.handler.ts`
- Create: `services/company/commercial/handlers/customer-engagement/index.ts`
- Modify: `services/company/commercial/handlers/index.ts`
- Test: `services/company/commercial/tests/customer-engagement/handlers.test.ts`

**Interfaces:**
- Mỗi handler theo pattern `contact.handler.ts`: `api({ method, path, expose: true }, async ({ ..., workspaceId: Header<"X-Workspace-Id">, authorization?: Header<"Authorization"> }) => { const ctx = await requireWorkspaceAccess(authorization, workspaceId); requireEngagementPermission(ctx, <perm>); return <service>(...); })`.
- Endpoints (prefix `/commercial/engagement`):
  - `POST /commercial/engagement/inboxes` → tạo inbox (perm `engagement.thread.write`).
  - `POST /commercial/engagement/threads` → `openThread` (perm `thread.write`).
  - `GET /commercial/engagement/threads/:id` → `getThread` (perm `thread.read`).
  - `GET /commercial/engagement/threads` → `listThreads` (perm `thread.read`).
  - `POST /commercial/engagement/threads/:id/status` → `changeThreadStatus` (perm `thread.write`).
  - `POST /commercial/engagement/threads/:id/notes` → `postInternalNote` (perm `thread.write`).
  - `POST /commercial/engagement/threads/:id/messages` → `sendPublicMessage` (perm `message.send`).
  - `POST /commercial/engagement/threads/:id/inbound` → `recordInboundMessage` (perm `thread.write`; P2
    thay bằng webhook per adapter — P0 để nội bộ/test).
  - `POST /commercial/engagement/threads/:id/assign` → `assignThread` (perm `thread.write`).
  - `POST /commercial/engagement/threads/:id/takeover` → `takeOverThread` (perm `thread.takeover`).
  - `GET /commercial/engagement/customer360/:contactId` → `getCustomer360` (perm `thread.read`).
  - `POST /commercial/engagement/decision-authorities` → `seedDecisionAuthority` (perm `decision_authority.manage`).
  - `POST /commercial/engagement/decision-authorities/:key/grants` → `grantAuthorityCapability` (perm `decision_authority.manage`).
  - `GET /commercial/engagement/decision-authorities` → list + status (`pending_binding`/`enabled`) (perm `decision_authority.manage`).
  - `POST /commercial/engagement/escalation-routes` → tạo/đổi route bind `WorkforceMember` (perm `escalation_route.manage`).
  - `POST /commercial/engagement/decision-requests` → `createDecisionRequest` (perm `decision_request.review`).
  - `POST /commercial/engagement/decision-requests/:id/submit` → `submitDecisionRequest` (perm `decision_request.review`).
  - `POST /commercial/engagement/decision-requests/:id/review` → `startReview` (perm `decision_request.review`).
  - `POST /commercial/engagement/decision-requests/:id/approvals` → `recordApproval` (perm `decision_request.decide`).
  - `POST /commercial/engagement/decision-requests/:id/execute` → `executeDecisionRequest` (perm `decision_request.decide`).
  - `POST /commercial/engagement/legal-holds` / `POST .../legal-holds/:id/release` → `createLegalHold` / `releaseLegalHold` (perm `legal_hold.manage`).
  - `POST /commercial/engagement/data-subject-requests` → `createDataSubjectRequest`; `POST .../:id/verify`, `POST .../:id/export`, `POST .../:id/execute-delete` (perm `data_subject_request.manage`).
- `handlers/customer-engagement/index.ts` re-export tất cả; `handlers/index.ts` thêm
  `export * from "./customer-engagement";`.

- [ ] **Step 1: Test đỏ** — 1 file `handlers.test.ts`: gọi qua handler (không service trực tiếp) cho:
  open→get happy path; `getThread` cross-workspace → `notFound`; caller thiếu permission → `permissionDenied`.
- [ ] **Step 2: Chạy — đỏ.**
- [ ] **Step 3: Implement handlers + index.** Giữ handler mỏng.
- [ ] **Step 4: Chạy — xanh + `npx tsc --noEmit`.**
- [ ] **Step 5: Commit**

```bash
git add services/company/commercial/handlers/customer-engagement/ services/company/commercial/handlers/index.ts services/company/commercial/tests/customer-engagement/handlers.test.ts
git commit -m "feat(engagement): Encore handlers for customer engagement (expose:true, RBAC-guarded)"
```

---

### Task 12: Housekeeping cron (snooze re-open + DR expiry)

**Files:**
- Create: `services/company/commercial/services/customer-engagement/housekeeping.service.ts`
- Create: `services/company/commercial/services/customer-engagement/housekeeping.cron.ts`
- Test: `services/company/commercial/tests/customer-engagement/housekeeping.test.ts`

**Interfaces:**
- `runHousekeepingTick(): Promise<{ snoozeReopened: number; drExpired: number; slaEscalated: number }>`:
  - Mọi thread `status='snoozed' AND snoozed_until < now()` → `changeThreadStatus`-tương-đương về `open`
    (transition `reason_code='snooze_expired'`, actor `{ kind:"system", id:"housekeeping" }`), event
    `engagement.thread.status_changed.v1`. **Re-check state hiện tại**, không hành động trên snapshot cũ.
  - Gọi `expireDueDecisionRequests()` (Task 10).
  - **SLA escalation** (dùng `sla_snapshot` đã pin trên thread, **không** đọc lại `sla_policy` inbox):
    thread chưa `resolved`, chưa `first_response_at`, `now() >= first_response_due_at` (hoặc
    `resolution_due_at`) → tăng `escalation_level`, resolve `WorkforceMember` qua
    `resolveEscalationRoute(thread.escalation_route_key, level, ctx)` (Task 14) theo bậc
    primary → backup (sau `acknowledge_minutes`) → duty_manager. Ghi transition
    `reason_code='sla_escalated'` + outcome `escalation_reason`. Nếu route không bind được người thật →
    **không** nuốt lỗi: ghi transition `reason_code='sla_escalation_unrouted'` để operator thấy (fail-closed
    đã chặn ở `openThread` nên trường hợp này hiếm).
- `housekeeping.cron.ts`: `CronJob("engagement-housekeeping", { every: "1m", endpoint })`.

- [ ] **Step 1: Test đỏ** — (a) snooze thread `snoozed_until` quá khứ → tick → `open`; (b) DR
  `approval_deadline` quá khứ ở `submitted` → tick → `expired` + event; (c) thread tier `priority` với
  `first_response_due_at` quá khứ, chưa `first_response_at` → tick → `escalation_level=1` + transition
  `sla_escalated`.
- [ ] **Step 2: đỏ → implement → xanh.**
- [ ] **Step 3: Commit**

```bash
git add services/company/commercial/services/customer-engagement/housekeeping.service.ts services/company/commercial/services/customer-engagement/housekeeping.cron.ts services/company/commercial/tests/customer-engagement/housekeeping.test.ts
git commit -m "feat(engagement): housekeeping cron for snooze re-open + decision request expiry"
```

---

### Task 13: Test matrix (spec §15) — bắt buộc trước khi coi P0 xong

**Files:**
- Create: `services/company/commercial/tests/customer-engagement/matrix.test.ts`
- (Có thể) Modify: `services/company/identity/tests/helpers/test-session.ts` — nếu cần tham số
  `permissions` để cấp `engagement.*` cho `TenantContext` trong test (kiểm trước; nếu `resolveTenantContext`
  lấy permission từ membership role, thêm helper `withEngagementPermissions(ctx)` thay vì sửa identity helper).

**Interfaces:**
- Consumes toàn bộ service + handler các task trước. Không code sản phẩm mới — chỉ test.

**Mỗi hàng spec §15 = 1 `it`:**

- [ ] **Step 1: Viết `matrix.test.ts`** với các case:

```typescript
import { describe, expect, it } from "vitest";
// helpers ws(), seedInbox(), grant permissions ...

describe("Customer Engagement — required test matrix (spec §15)", () => {
  it("cross-workspace thread access → not found, no record disclosure", async () => { /* getThread(b.ctx) rejects /not found/ */ });

  it("concurrent assignment/takeover → exactly one active assignment; stale agent command invalidated", async () => {
    /* Promise.allSettled 2 takeOver; assert 1 active row; queued deliveries → failed */
  });

  it("retry inbound with same idempotency key → no duplicate message", async () => {
    /* recordInboundMessage x2 same key → same id; count=1 */
  });
  it("retry outbound with same idempotency key → no duplicate message/delivery/CRM effect", async () => {
    /* sendPublicMessage x2 same key → same id; deliveries count=1 */
  });

  it("internal note has no customer delivery path and is absent from customer-facing export", async () => {
    /* postInternalNote → no delivery row; a hypothetical export filter visibility='customer' excludes it */
  });

  it("agent send after human takeover → denied/cancelled before delivery", async () => {
    /* enqueue outbound; takeOver; deliveryRelayTick → sent=0; delivery failed */
  });

  it("thread with unverified customer → restricted billing/account data not disclosed", async () => {
    /* getCustomer360(contactId, ctx, { identityVerified:false }) → no invoices/subscriptions keys */
  });

  it("proposal to create Opportunity → no write without proper approval (P0: DR gate)", async () => {
    /* createDecisionRequest(type 'contract_exception') → execute before approve → invalidArgument; no opportunity row */
  });

  it("expired Decision Request → not executed even though previously approved", async () => {
    /* approve; set approval_deadline past; execute → throws 'expired'; status='expired'; execution_ref null */
  });

  it("delayed automation re-checks state/owner/policy before executing", async () => {
    /* snooze thread; move snoozed_until to past; change owner; runHousekeepingTick; assert reopen used current state */
  });

  it("provider delivery failure → outbox ret/DLQ audited; WorkforceMember sees error + safe retry", async () => {
    /* monkeypatch api adapter sendOutbound → { status:'failed' }; tick until attempt>=max; status='failed' + dead_letter_reason; last_error visible */
  });

  it("invalid state transition is rejected and no transition row is written", async () => {
    /* changeThreadStatus snoozed->resolved → throws; assert transitions count unchanged */
  });

  it("fail-closed: authority pending_binding blocks submit/decide/execute", async () => {
    /* seedDecisionAuthority (no grants) → createDecisionRequest/submit → failedPrecondition;
       grant all required capabilities → recompute enabled → submit OK */
  });

  it("N-of-M distinct approvers: pricing.exception needs 2 distinct, high_risk needs 3", async () => {
    /* distinct_approvers:2 → 1 approve stays under_review + execute blocked; 2nd distinct covering
       remaining capability → approved + execute OK.
       distinct_approvers:3 → only approved after 3 distinct approvers cover sales/finance/business_owner */
  });

  it("requester cannot approve or execute their own decision request", async () => {
    /* recordApproval by requester → permissionDenied; executeDecisionRequest by requester → permissionDenied */
  });

  it("retention_until is NOT NULL and set on every message/interaction insert (fail-closed)", async () => {
    /* recordInboundMessage / sendPublicMessage / postInternalNote → retention_until = created_at + 365d;
       raw INSERT without retention_until → DB rejects */
  });

  it("legal hold blocks a delete Data Subject Request", async () => {
    /* createLegalHold(scope:'contact', scope_ref:contactId); createDataSubjectRequest(kind:'delete') + verify
       + execute-delete → status='blocked_legal_hold'; no primary purge scheduled */
  });

  it("DSR export excludes internal notes and other subjects' data", async () => {
    /* thread with 1 customer message + 1 internal note; export → payload has the customer message,
       not the internal note; export_expires_at = now + 24h */
  });
});
```

- [ ] **Step 2: Chạy full suite**

Run: `cd services/company && npx vitest run commercial/tests/customer-engagement/`
Expected: PASS toàn bộ. Ghi lại số test.

- [ ] **Step 3: Chạy regression toàn service**

Run: `cd services/company && npm test`
Expected: không hồi quy ở commercial/identity/events khác.

- [ ] **Step 4: Typecheck**

Run: `cd services/company && npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/company/commercial/tests/customer-engagement/matrix.test.ts
git commit -m "test(engagement): P0 required test matrix (spec §15)"
```

---

### Task 14: SLA snapshot + escalation routes

> **Thứ tự thực thi:** làm sau Task 2, có thể trước hoặc song song Task 4 (phần `openThread` gọi
> `snapshotThreadSla`). Nếu làm Task 4 trước, stub `snapshotThreadSla` trả `{}` rồi hoàn thiện ở đây.

**Files:**
- Create: `services/company/commercial/services/customer-engagement/sla.service.ts`
- Create: `services/company/commercial/services/customer-engagement/escalation.service.ts`
- Test: `services/company/commercial/tests/customer-engagement/sla.service.test.ts`
- Test: `services/company/commercial/tests/customer-engagement/escalation.service.test.ts`

**Interfaces:**
- `sla.service.ts`:
  - `export const SLA_POLICY_SEED` — object JSON đúng "P0 policy defaults" (version 1, timezone
    `Asia/Ho_Chi_Minh`, `business_calendar` weekdays 1–5 / 08:30–17:30 / `holiday_calendar: "VN"`,
    tiers `standard` / `priority` / `vip`).
  - `export const RETENTION_TRANSCRIPT_DAYS = 365`, `RETENTION_RAW_ATTACHMENT_DAYS = 90`,
    `RETENTION_METADATA_DAYS = 730` (hằng dùng chung cho message / attachment / interaction / DSR).
  - `resolveTier(inbox, params): "standard" | "priority" | "vip"` — `params.tier ?? inbox.default_tier`.
  - `computeSlaSnapshot(slaPolicy, tier, openedAt): { version; tier; firstResponseDueAt: Date; resolutionDueAt: Date; warningAtPercent; outOfHoursMode; routeKey: string | null }` —
    tính deadline theo `clock` (`business` cộng theo business calendar + timezone; `calendar` cộng thẳng),
    `out_of_hours.mode` (`pause` ⇒ deadline "đóng băng" ngoài giờ; `on_call` ⇒ `routeKey = "support-oncall"`).
  - `snapshotThreadSla(threadValues, slaPolicy, tier, openedAt): Partial<thread insert>` — trả
    `{ tier, slaPolicyVersion, slaSnapshot, firstResponseDueAt, resolutionDueAt, escalationRouteKey }`
    để merge vào `insert(engagementThreads)`. Ticket đã mở giữ snapshot cũ; đổi policy **không** rebaseline
    trừ khi có lệnh audit (P0 chưa cần lệnh rebaseline).
- `escalation.service.ts`:
  - `setEscalationRoute({ workspaceId; routeKey; role; workforceMemberId; activeUntil? }, ctx): Promise<void>` —
    upsert `engagement_escalation_routes` (`role` ∈ `primary|backup|duty_manager`).
  - `resolveEscalationRoute(routeKey, level, ctx): Promise<{ workforceMemberId: string; role: string }>` —
    `level` 1 → primary, 2 → backup, 3+ → duty_manager; chỉ grant active (`active_from <= now() <
    coalesce(active_until,'infinity')`). Không có → `APIError.failedPrecondition("no active <role> for route <routeKey>")`.
  - `assertRouteBound(routeKey, ctx): Promise<void>` — dùng bởi `openThread` khi tier yêu cầu `on_call`:
    throw nếu chưa có primary bind (**fail-closed**).

- [ ] **Step 1: Test đỏ — `sla.service`**: `computeSlaSnapshot` cho `standard` (business clock, 240'
  first response tính qua business hours + cuối tuần bỏ qua), `vip` (calendar clock, 30'/`route_key
  support-oncall`), `warning_at_percent` đúng. → implement → xanh.
- [ ] **Step 2: Test đỏ — `escalation.service`**: `resolveEscalationRoute` level 1/2/3 → primary/backup/
  duty_manager; route chưa bind → `failedPrecondition`; grant hết hạn → bỏ qua. → implement → xanh.
- [ ] **Step 3: Nối `openThread` (Task 4)** với `snapshotThreadSla` + `assertRouteBound` (nếu tier
  `on_call`). Cập nhật test `thread.service.test.ts`: mở thread `vip` khi chưa bind route → `failedPrecondition`;
  sau `setEscalationRoute(primary)` → mở OK, `first_response_due_at` set.
- [ ] **Step 4: Commit**

```bash
git add services/company/commercial/services/customer-engagement/sla.service.ts services/company/commercial/services/customer-engagement/escalation.service.ts services/company/commercial/tests/customer-engagement/sla.service.test.ts services/company/commercial/tests/customer-engagement/escalation.service.test.ts
git commit -m "feat(engagement): SLA snapshot on thread open + escalation routes bound to WorkforceMember"
```

---

### Task 15: Data Subject Request (export/delete) + Legal Hold

**Files:**
- Create: `services/company/commercial/services/customer-engagement/legal-hold.service.ts`
- Create: `services/company/commercial/services/customer-engagement/data-subject-request.service.ts`
- Test: `services/company/commercial/tests/customer-engagement/legal-hold.service.test.ts`
- Test: `services/company/commercial/tests/customer-engagement/data-subject-request.service.test.ts`

**Interfaces:**
- `legal-hold.service.ts`:
  - `createLegalHold({ scope: "thread"|"contact"|"workspace"; scopeRef?; reason; effectiveUntil }, ctx): Promise<LegalHoldDTO>` —
    `effectiveUntil` **bắt buộc**; `reason` bắt buộc; `created_by_workforce_member_id = ctx.workforceMemberId`.
  - `releaseLegalHold(id, ctx): Promise<void>` — set `released_at`, `released_by_workforce_member_id`.
  - `isUnderLegalHold({ contactId?; threadId? }, ctx): Promise<boolean>` — true nếu có hold chưa release,
    chưa hết `effective_until`, khớp scope (contact/thread/workspace-wide).
- `data-subject-request.service.ts`:
  - `createDataSubjectRequest({ kind: "export"|"delete"; subjectContactId }, ctx): Promise<DSR_DTO>` —
    status `received`. Với `delete`: set `suppressed_at = now()` ngay (khoá truy cập/suppress khi tiếp nhận).
  - `verifyDataSubjectRequest(id, ctx): Promise<DSR_DTO>` — `requireEngagementPermission(ctx,
    "engagement.data_subject_request.manage")` (Privacy Officer). `received→verified`, `verified_at`,
    `verified_by_workforce_member_id`. Với `delete`: set `primary_purge_due_at = verified_at + 30d`,
    `backup_purge_due_at = verified_at + 35d`.
  - `exportDataSubject(id, ctx): Promise<{ exportRef; expiresAt }>` — chỉ `kind="export"`, `status>=verified`.
    Gom `engagement_messages` `visibility='customer'` + interactions của `subject_contact_id` (**loại**
    internal note + dữ liệu chủ thể khác) → artifact ref; `export_ref`, `export_expires_at = now()+24h`,
    `status='exported'`.
  - `executeDelete(id, ctx): Promise<DSR_DTO>` — chỉ `kind="delete"`, `status='verified'`. **Fail-closed**:
    `isUnderLegalHold({ contactId: subject })` true → `status='blocked_legal_hold'`, **không** xoá,
    **không** lịch purge. Else: `status='purging'` → xoá/anonymize primary data của subject trong
    engagement (message body → tombstone, giữ `id`/`created_at`/hash cho audit; interactions xoá) →
    `status='completed'`, `completed_at`. Audit chỉ giữ `{ request_id, actor, at, basis }` — **không**
    raw transcript.
  - `DSR_DTO` String-hoá.

- [ ] **Step 1: Test đỏ — `legal-hold`**: create (thiếu `effectiveUntil` → `invalidArgument`);
  `isUnderLegalHold` true khi có hold contact-scope; false sau `releaseLegalHold` hoặc quá `effective_until`.
  → implement → xanh.
- [ ] **Step 2: Test đỏ — `data-subject-request`**:
  - `delete` request → `suppressed_at` set ngay ở `received`.
  - `verify` → `primary_purge_due_at = verified_at + 30d`, `backup_purge_due_at = +35d`.
  - `export` gom đúng: customer message có, internal note **không**, message của contact khác **không**;
    `export_expires_at ≈ now+24h`.
  - `executeDelete` khi có legal hold → `blocked_legal_hold`, message body còn nguyên.
  - `executeDelete` khi không hold → message body thành tombstone, `id`/hash giữ; `status='completed'`.
  → implement → xanh.
- [ ] **Step 3: Commit**

```bash
git add services/company/commercial/services/customer-engagement/legal-hold.service.ts services/company/commercial/services/customer-engagement/data-subject-request.service.ts services/company/commercial/tests/customer-engagement/legal-hold.service.test.ts services/company/commercial/tests/customer-engagement/data-subject-request.service.test.ts
git commit -m "feat(engagement): data subject request (export/delete) + legal hold (fail-closed)"
```

---

### Task 16: Vocabulary lock doc

**Files:**
- Create: `docs/architecture/customer-engagement-vocabulary.md`

**Interfaces:** không code. Tài liệu chốt thuật ngữ spec §3 + tên state/mode/event/permission P0 để P1–P4
tham chiếu, không tự đặt lại.

- [ ] **Step 1: Viết doc** — bảng: Khách / Người dùng nội bộ / Inbox / Conversation Thread / Public
  Message / Internal Note / Copilot / Autopilot / Decision Request / Takeover (spec §3, nguyên văn) +
  bảng: `ThreadStatus` (5) / `ThreadMode` (5) / `DRStatus` (9) / event type list (10) / permission list
  (10) / authority key list (7, "P0 policy defaults") / retention defaults / SLA tiers — copy từ code +
  overview đã landed, ghi rõ file nguồn.

- [ ] **Step 2: Commit**

```bash
git add docs/architecture/customer-engagement-vocabulary.md
git commit -m "docs(engagement): lock P0 vocabulary + state/mode/event/permission/authority names"
```

---

## Self-Review (đã chạy khi soạn plan)

**Spec coverage:**
- §5 domain model → Task 2 (schema), Task 4/5/6 (thread/message/assignment), Task 9 (customer_interactions gián tiếp qua customer360).
- §5.2 identity resolution → Task 9.
- §6 state machine + mode + takeover + public/internal → Task 4, Task 5, Task 6.
- §7 Decision Request (record, state machine, authority binding fail-closed, N-of-M distinct approvers, execution guard, business-vs-tool approval) → Task 10.
- §8.1 business events (chỉ phát) → Task 3 + append tại Task 4/5/6/10.
- §8.4 kiểm takeover ngay trước delivery → Task 8.
- §9 Channel Adapter contract + verify/dedupe/atomic + outbox riêng + DLQ → Task 7, Task 8 (P0: `api` adapter; verify/dedupe provider thật = P2).
- §10.1 Desk surfaces (backend) → Task 11 endpoints. UI Flutter ngoài phạm vi service plan.
- §10.2 takeover behavior → Task 6 + Task 8.
- §11 privacy/audit → Task 6 (rbac.ts), Task 4/10 (transition + DR event ledgers), Task 9 (`identityVerified` guard), Task 2 (`classification` + `retention_until NOT NULL`), Task 15 (legal hold + DSR export/delete).
- §12 SLA / escalation nhận diện → Task 14 (snapshot + routes), Task 12 (breach escalation).
- §15 test matrix → Task 13 (+ unit tests rải ở Task 4–15).
- **§17.2 / §17.7** (authority + dual/triple-control) → `engagement_decision_authorities` +
  `engagement_decision_authority_grants` + `approval_policy` jsonb; seed 7 authority key theo
  "P0 policy defaults" ở `status='pending_binding'`, `enabled` sau binding — Task 10.
- **§17.4** (retention / residency / DSR) → `retention_until NOT NULL` + hằng
  `RETENTION_TRANSCRIPT_DAYS=365` / `RAW_ATTACHMENT=90` / `METADATA=730` (Task 14); DSR export/delete +
  legal hold (Task 15); residency ghi ở Global Constraints (raw chỉ ở `workspace_home_region`).
- **§17.5** (SLA per tier + escalation ngoài giờ) → `SLA_POLICY_SEED` (standard/priority/vip) +
  `engagement_escalation_routes` bind `WorkforceMember` (Task 14).

**Gaps có chủ đích (không làm ở P0, đã ghi):**
- Provider verification/signature + dedupe theo provider message ID cho kênh thật → P2.
- Deterministic routing/label rule engine → P3 (P0 chỉ housekeeping cron: snooze / DR expiry / SLA escalation).
- Copilot / agent / event consumer → P1/P4.
- DR execution nối `billing.*` thật (refund/cancel) → P4; P0 chỉ ghi `execution_ref` noop + audit.
- Raw attachment byte store + backup region automation → P2; P0 chỉ metadata + `content_ref` + retention.
- Rebaseline lệnh SLA cho ticket đang mở → sau P0 (P0: ticket giữ `sla_snapshot` đã pin).

**Placeholder scan:** không có "TBD"/"TODO"; các Task 5/8/9/10/14/15 mô tả implement bằng bullet +
interface đầy đủ + tham chiếu file mẫu (`contact.service.ts`, `outbox.repository.ts`) thay vì dán lại
toàn bộ code — chấp nhận cho engineer có pattern.

**Type consistency:** `ThreadDTO` (có `tier` / `firstResponseDueAt` / `escalationLevel`) / `MessageDTO` /
`AssignmentDTO` / `DR_DTO` (có `authorityKey` / `approvals[]`) / `AuthorityDTO` / `DSR_DTO` / `LegalHoldDTO`
khớp giữa các task. `assertStatusTransition` / `assertDRTransition` / `assertApprovalPolicySatisfied` /
`resolveEnabledAuthority` / `resolveEscalationRoute` / `snapshotThreadSla` tên nhất quán. Permission +
`SLA_POLICY_SEED` + hằng retention export từ 1 module dùng chung (`rbac.ts`, `sla.service.ts`).

---

## Execution Handoff

Sau khi P0 landed + test matrix xanh: viết `2026-08-28-customer-engagement-p1.md` (Copilot artifact-only,
human-invoked) theo cùng cấu trúc, dùng interface names đã cố định ở P0 (`getThread`, `getCustomer360`,
`ThreadDTO`, event types...).
