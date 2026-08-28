# Customer Engagement — P3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** **Deterministic automation** cho Customer Engagement — rule evaluator typed + versioned, chạy
hoàn toàn trên **structured facts**, **không LLM**, nằm trong `services/company/commercial` (sở hữu rule +
state transition + outbox trong cùng business boundary). Chức năng: route inbox theo locale / business
hours / customer tier / priority; áp SLA action + nhãn taxonomy; tạo follow-up task; snooze / reopen;
escalate khi deadline / CSAT âm / customer health xuống ngưỡng; **tạo Decision Request** khi thread thuộc
nhóm policy exception. Rule delayed **re-check state / owner / policy** trước khi execute.

**Architecture:** `evaluateRules({ trigger, threadId }, ctx)` gọi **sau** mỗi state change (thread opened,
message received, status changed, CSAT recorded) — trong `services/company/commercial`, **không** qua
agent event backbone. Condition là **cây predicate typed** (`all`/`any`/`not` + op đóng), fact path
validate theo `FACT_KEYS` registry lúc lưu rule. Action là **union đóng** (route / label / task / snooze
/ reopen / escalate / create_decision_request / schedule_delayed), mỗi action idempotent qua
`engagement_automation_applications`. Delayed action ghi vào `engagement_automation_schedules`; housekeeping
tick khi đến hạn **dựng lại facts hiện tại + re-eval condition + re-check owner/mode**, chỉ apply nếu vẫn
đúng. Không có code path nào gọi model / `eval` / `new Function` (test tĩnh).

**Tech Stack:** TypeScript strict + Encore + Drizzle + Vitest, `services/company/commercial`. Không LLM,
không broker.

**Spec:** [`docs/superpowers/specs/2026-08-28-customer-engagement-human-agent-design.md`](../specs/2026-08-28-customer-engagement-human-agent-design.md) —
P3 phủ §5.5 (automation xác định tách khỏi reasoning), §6 (state transition là command có validation),
§7.1 (Decision Request khi command thuộc policy exception), §8.2 (deterministic automation trước, agent
sau — condition trên structured facts, delayed rule re-check state), §12 (metric là projection của
immutable events), §13 P3, §15 ("Delayed automation" re-check).

**Overview:** [`2026-08-28-customer-engagement-overview.md`](./2026-08-28-customer-engagement-overview.md).
**Tiền đề:** [P0](./2026-08-28-customer-engagement-p0.md) landed — dùng `changeThreadStatus` /
`assignThread` / `engagement_thread_labels` / `engagement_thread_transitions` / `engagement_thread_outcomes`
/ `sla.service.ts` + thread SLA snapshot / `escalation.service.ts` / `decision-request.service.ts` +
`engagement_decision_authorities` / `runHousekeepingTick`. [P1](./2026-08-28-customer-engagement-p1.md) &
[P2](./2026-08-28-customer-engagement-p2.md) landed nhưng **không** phải phụ thuộc.

## Global Constraints

- **TDD bắt buộc** (CLAUDE.md #11); **an toàn working tree** (CLAUDE.md #10); comment "why" tiếng Việt.
- **KHÔNG LLM trong automation** (spec §8.2): `automation/` không import model client, không gọi
  `eval` / `new Function` / template string execution. Condition chỉ so khớp trên `AutomationFacts`
  typed. Test tĩnh (Task 9) enforce.
- **State transition qua command có validation** (spec §6): action **không** UPDATE `engagement_threads`
  trực tiếp — gọi `changeThreadStatus` / `assignThread` (P0) để giữ bảng chuyển + transition ledger +
  outbox. Action ghi thêm `engagement_thread_transitions` với `actor = { kind: "system", id: "automation:<rule_key>" }`.
- **Rule versioned + immutable**: sửa rule ⇒ tạo `version` mới; application/schedule tham chiếu
  `(rule_key, version)` chính xác. Rule `disabled` ⇒ không nhận trigger mới; schedule pending của nó ⇒
  `skipped_rule_disabled`.
- **Delayed action không chạy trên snapshot cũ** (spec §15): housekeeping dựng lại facts hiện tại,
  re-eval condition, re-check `thread.owner_member_id` / `active_mode` / policy còn hiệu lực; sai ⇒
  `skipped_condition_changed` / `skipped_ownership_changed`.
- **Idempotency**: mỗi (rule_key, version, thread_id, action_index, dedupe_key) chỉ apply **một lần**
  (ledger `engagement_automation_applications`). Re-trigger cùng fact ⇒ 0 effect trùng.
- **Fail-closed cho `create_decision_request`**: không có authority `enabled` cho `decision_kind` ⇒
  action `skipped_no_authority` (không tạo DR "mồ côi", không bypass P0 fail-closed).
- **Rule failure cô lập**: `evaluateRules` chạy **sau** transaction state change; lỗi rule ⇒ log +
  `engagement_automation_applications(outcome:"error")`, **không** rollback message/thread.
- **Migration**: chỉ `.up.sql`. Sau P2 = `13_` ⇒ P3 dùng `14_`.

---

## File Structure

| File | Trách nhiệm |
| --- | --- |
| `services/company/shared/db/schema/customer-engagement.ts` | (Modify) `engagementAutomationRules`, `engagementAutomationApplications`, `engagementAutomationSchedules`; `engagement_thread_outcomes` thêm `csat_score` (nếu chưa). |
| `services/company/commercial/migrations/14_engagement_automation.up.sql` | (Create). |
| `services/company/commercial/services/customer-engagement/automation/facts.ts` | (Create) `AutomationFacts` type + `buildAutomationFacts` + `FACT_KEYS`. |
| `services/company/commercial/services/customer-engagement/automation/predicate.ts` | (Create) predicate tree + `evaluatePredicate` + `validatePredicate`. |
| `services/company/commercial/services/customer-engagement/automation/actions.ts` | (Create) action union + `applyAction` (idempotent). |
| `services/company/commercial/services/customer-engagement/automation/rule-model.ts` | (Create) `AutomationRule` type + `validateRule` + versioning helper. |
| `services/company/commercial/services/customer-engagement/automation/evaluator.ts` | (Create) `evaluateRules({ trigger, threadId, dryRun? }, ctx)`. |
| `services/company/commercial/services/customer-engagement/automation/rule-store.service.ts` | (Create) CRUD + version + disable + seed default rules. |
| `services/company/commercial/services/customer-engagement/thread.service.ts` | (Modify) gọi `evaluateRules` sau `openThread` / `changeThreadStatus`. |
| `services/company/commercial/services/customer-engagement/message.service.ts` | (Modify) gọi `evaluateRules` sau `recordInboundMessage`. |
| `services/company/commercial/services/customer-engagement/csat.service.ts` | (Create) `recordCsat` → `engagement_thread_outcomes` + trigger `csat_recorded`. |
| `services/company/commercial/services/customer-engagement/housekeeping.service.ts` | (Modify) xử lý `engagement_automation_schedules`; thay pass SLA-escalation hardcode P0 bằng seeded rule. |
| `services/company/commercial/handlers/customer-engagement/automation.handler.ts` | (Create) CRUD rule + dry-run (`expose:true`, `engagement.automation.manage`). |
| `services/company/commercial/handlers/customer-engagement/index.ts` | (Modify) re-export. |
| `services/company/commercial/services/customer-engagement/rbac.ts` | (Modify) `engagement.automation.manage`. |
| `services/company/commercial/tests/customer-engagement/automation-*.test.ts` | (Create). |
| `services/company/commercial/tests/customer-engagement/automation-no-llm.test.ts` | (Create) determinism guard. |
| `docs/operations/customer-engagement-automation-runbook.md` | (Create). |
| `docs/architecture/customer-engagement-vocabulary.md` | (Modify) fact keys, action catalog, rule/schedule states. |

**Assumptions (verify trong repo):**
- P0: `changeThreadStatus(id, { to, reasonCode, snoozedUntil?, resolutionCode? }, ctx)`,
  `assignThread({ threadId, teamId?, memberId?, reason }, ctx)`, insert `engagement_thread_labels`,
  `resolveEscalationRoute(routeKey, level, ctx)`, `createDecisionRequest({ threadId, requestType, ..., authorityKey }, ctx)`,
  `runHousekeepingTick()`, thread cột `sla_snapshot`/`first_response_due_at`/`resolution_due_at`/`escalation_level`/`tier`.
- Operations: `createTaskService(params, authorization)` với outbox (`services/company/operations/services/task.service.ts:82`).
- `sla.service.ts` `SLA_POLICY_SEED` + `computeSlaSnapshot`; business-calendar helper (dùng lại cho fact `inbox.businessHoursOpen`).
- `sales.customers.health_status`, `sales.contacts.do_not_contact` — qua P0 `getCustomer360` hoặc query trực tiếp scoped.

---

### Task 1: Automation schema

**Files:**
- Modify: `services/company/shared/db/schema/customer-engagement.ts`
- Create: `services/company/commercial/migrations/14_engagement_automation.up.sql`
- Test: `services/company/commercial/tests/customer-engagement/automation-schema.test.ts`

- [ ] **Step 1: Xác nhận migration number** — `ls .../migrations | sort -V | tail -2` ⇒ `14_`.
- [ ] **Step 2: Test đỏ** — 3 bảng tồn tại; unique `(workspace_id, rule_key, version)`;
  `engagement_automation_applications` unique `(rule_key, rule_version, thread_id, action_index, dedupe_key)`.
- [ ] **Step 3: Migration**

```sql
-- P3: deterministic automation — rule typed/versioned + ledger idempotency + delayed schedule.
CREATE TABLE engagement.engagement_automation_rules (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  rule_key TEXT NOT NULL,                      -- ổn định qua các version
  version INTEGER NOT NULL DEFAULT 1,
  name TEXT NOT NULL,
  trigger TEXT NOT NULL,                       -- thread_opened | message_received | thread_status_changed | csat_recorded | time_sweep
  priority INTEGER NOT NULL DEFAULT 100,       -- nhỏ chạy trước
  condition JSONB NOT NULL,                    -- predicate tree typed
  actions JSONB NOT NULL,                      -- array typed action
  enabled BOOLEAN NOT NULL DEFAULT false,      -- fail-closed: rule mới off cho tới khi bật
  stop_on_match BOOLEAN NOT NULL DEFAULT false,
  effective_from TIMESTAMPTZ NOT NULL DEFAULT now(),
  effective_until TIMESTAMPTZ,
  created_by_workforce_member_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_engagement_automation_rules_ver
  ON engagement.engagement_automation_rules(workspace_id, rule_key, version);
CREATE INDEX idx_engagement_automation_rules_trigger
  ON engagement.engagement_automation_rules(workspace_id, trigger, enabled, priority);

CREATE TABLE engagement.engagement_automation_applications (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  rule_key TEXT NOT NULL,
  rule_version INTEGER NOT NULL,
  thread_id BIGINT NOT NULL,
  trigger TEXT NOT NULL,
  action_index INTEGER NOT NULL,
  action_type TEXT NOT NULL,
  dedupe_key TEXT NOT NULL DEFAULT '',
  outcome TEXT NOT NULL,                       -- applied | skipped_condition_changed | skipped_ownership_changed | skipped_rule_disabled | skipped_no_authority | error
  detail JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_engagement_automation_applications
  ON engagement.engagement_automation_applications(rule_key, rule_version, thread_id, action_index, dedupe_key);
CREATE INDEX idx_engagement_automation_applications_thread
  ON engagement.engagement_automation_applications(thread_id, created_at);

CREATE TABLE engagement.engagement_automation_schedules (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  rule_key TEXT NOT NULL,
  rule_version INTEGER NOT NULL,
  thread_id BIGINT NOT NULL,
  action_index INTEGER NOT NULL,
  action JSONB NOT NULL,                       -- snapshot action delayed
  condition JSONB NOT NULL,                    -- snapshot condition phải still-true khi đến hạn
  due_at TIMESTAMPTZ NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',      -- pending | done | skipped | error
  skip_reason TEXT,
  claimed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_engagement_automation_schedules_due
  ON engagement.engagement_automation_schedules(status, due_at);

-- CSAT trên outcome (nếu P0 chỉ có csat_ref):
ALTER TABLE engagement.engagement_thread_outcomes
  ADD COLUMN csat_score INTEGER,
  ADD COLUMN csat_recorded_at TIMESTAMPTZ;
```

- [ ] **Step 4: Drizzle schema** — thêm 3 table object + cột, export.
- [ ] **Step 5: Áp migration** — `make services-migrate-company`; `--check` clean.
- [ ] **Step 6: Chạy — xanh** + `npx tsc --noEmit`.
- [ ] **Step 7: Commit** `feat(engagement): P3 automation schema — versioned rules + application ledger + delayed schedules`.

---

### Task 2: Fact model

**Files:**
- Create: `services/company/commercial/services/customer-engagement/automation/facts.ts`
- Test: `.../tests/customer-engagement/automation-facts.test.ts`

**Interfaces (Produces):**
- `type AutomationFacts` — cây phẳng, **chỉ** primitive/enum/bool/number/string:
  ```
  thread: { status, priority, tier, activeMode, ownerMemberId: string|null, escalationLevel,
            ageMinutes, minutesSinceLastCustomerMsg: number|null, firstResponded: boolean,
            hasOpenDecisionRequest: boolean }
  inbox:  { channelType, locale: string|null, businessHoursOpen: boolean }
  sla:    { firstResponseDueInMinutes: number|null, resolutionDueInMinutes: number|null,
            firstResponseBreached: boolean, resolutionBreached: boolean, pctToFirstResponseBreach: number|null }
  contact:{ present: boolean, doNotContact: boolean }
  account:{ present: boolean }
  customer:{ present: boolean, healthStatus: string|null, tier: string|null }
  lastMessage: { direction: string|null, visibility: string|null }
  csat:   { latestScore: number|null, latestRecordedMinutesAgo: number|null }
  labels: string[]
  ```
- `buildAutomationFacts(threadId: string, ctx): Promise<AutomationFacts>` — load thread scoped + inbox +
  (nếu có) contact/customer + last message + latest outcome CSAT + labels; tính derived (age, breach,
  businessHoursOpen từ `sla_snapshot.business_calendar` + timezone). **Mọi query ràng `workspace_id`.**
- `FACT_KEYS: ReadonlySet<string>` — mọi path hợp lệ (`"thread.status"`, `"sla.firstResponseBreached"`,
  …). Dùng bởi `validatePredicate` (Task 3).

- [ ] **Step 1: Test đỏ** — seed thread P0 (tier `priority`, SLA snapshot với `first_response_due_at` quá
  khứ, chưa `first_response_at`) + 1 inbound message + 1 customer (health `AT_RISK`) → `buildAutomationFacts`
  trả `sla.firstResponseBreached === true`, `thread.firstResponded === false`, `customer.healthStatus === "AT_RISK"`,
  `inbox.businessHoursOpen` đúng theo giờ test (mock clock nếu cần). Cross-workspace → `notFound`.
  `FACT_KEYS` chứa mọi path xuất hiện trong type.
- [ ] **Step 2: đỏ → implement → xanh.**
- [ ] **Step 3: Commit** `feat(engagement): automation fact model (structured, workspace-scoped)`.

---

### Task 3: Predicate tree + evaluator + validator

**Files:**
- Create: `services/company/commercial/services/customer-engagement/automation/predicate.ts`
- Test: `.../tests/customer-engagement/automation-predicate.test.ts`

**Interfaces (Produces):**
- `type Predicate =
    | { all: Predicate[] } | { any: Predicate[] } | { not: Predicate }
    | { fact: string; op: Op; value: string | number | boolean | Array<string|number> }`
- `type Op = "eq" | "ne" | "gt" | "gte" | "lt" | "lte" | "in" | "not_in" | "contains"` (đóng — thêm op
  mới phải sửa code + test).
- `evaluatePredicate(node: Predicate, facts: AutomationFacts): boolean` — **thuần**, không async, không
  I/O, không throw cho fact null (null so sánh: `eq null` OK; `gt`/`lt` với null ⇒ `false`).
- `validatePredicate(node: Predicate): void` — throw `APIError.invalidArgument` nếu: `fact ∉ FACT_KEYS`,
  `op ∉ Op`, `contains` dùng trên fact không phải array (`labels`), cấu trúc sai. Gọi lúc lưu rule.

- [ ] **Step 1: Test đỏ** — mỗi op (số, string, bool, array `in`/`contains`); `all`/`any`/`not` lồng;
  fact null với `gt` → false; `validatePredicate` với `fact:"thread.unknown"` → `invalidArgument`;
  `op:"regex"` → `invalidArgument`.
- [ ] **Step 2: đỏ → implement → xanh.**
- [ ] **Step 3: Commit** `feat(engagement): typed predicate tree + deterministic evaluator + save-time validator`.

---

### Task 4: Action union + idempotent apply

**Files:**
- Create: `services/company/commercial/services/customer-engagement/automation/actions.ts`
- Test: `.../tests/customer-engagement/automation-actions.test.ts`

**Interfaces (Produces):**
- `type AutomationAction =
    | { type: "route_to_team"; teamId: string }
    | { type: "route_to_member"; memberId: string }
    | { type: "set_priority"; priority: string }
    | { type: "apply_label"; labelKey: string; taxonomyVersion: string }
    | { type: "create_follow_up_task"; title: string; dueInHours: number }
    | { type: "snooze"; minutes: number }
    | { type: "reopen" }
    | { type: "escalate" }                                  // bump escalation_level + resolve route
    | { type: "create_decision_request"; decisionKind: string }
    | { type: "schedule_delayed"; delayMinutes: number; action: AutomationAction; requireStillTrue: true }`
- `validateAction(a): void` — enum đóng; `create_decision_request.decisionKind ∈` set P0; `schedule_delayed.action`
  không được lồng `schedule_delayed`.
- `applyAction(a, { threadId, ruleKey, ruleVersion, trigger, actionIndex }, ctx): Promise<ApplicationOutcome>`:
  - **Idempotency**: `dedupeKey` = deterministic theo action (vd. `apply_label` → `labelKey`;
    `create_decision_request` → `decisionKind`; `escalate` → `\`lvl:${facts.thread.escalationLevel}\``).
    `insert engagement_automation_applications onConflictDoNothing`; nếu đã có `outcome:"applied"` ⇒ trả
    `"already_applied"`, **không** làm lại.
  - `route_to_team`/`route_to_member` → `assignThread` (P0); `set_priority` → `changeThread…`/update qua
    command (thêm helper P0 `setThreadPriority` nếu chưa có — 1 dòng + transition).
  - `apply_label` → insert `engagement_thread_labels` (unique `(thread_id, label_key)` — trùng ⇒ no-op).
  - `create_follow_up_task` → `createTaskService({ workspaceId, title, dueAt, source: "engagement:automation", threadRef: threadId }, ...)` (operations, có outbox).
  - `snooze` → `changeThreadStatus(threadId, { to:"snoozed", reasonCode:"automation_snooze", snoozedUntil })`.
  - `reopen` → nếu `resolved` → `changeThreadStatus(... to:"open", reasonCode:"automation_reopen")`.
  - `escalate` → `thread.escalation_level += 1`; `resolveEscalationRoute(thread.escalation_route_key, level, ctx)`
    → assign duty member; transition `automation_escalate`; nếu route không bind → `outcome:"error"` (không nuốt).
  - `create_decision_request` → lookup authority `enabled` cho `decisionKind` (P0 `resolveEnabledAuthority`);
    không có ⇒ `outcome:"skipped_no_authority"`. Có ⇒ `createDecisionRequest({ threadId, requestType: decisionKind, authorityKey, requested_by_actor: { kind:"system", id:"automation:<rule_key>" } })`.
    (Requester là system ⇒ P0 `requester_must_differ` tự thoả vì người approve là người thật.)
  - `schedule_delayed` → insert `engagement_automation_schedules` (snapshot inner `action` + rule
    `condition` + `due_at = now()+delay`); **không** apply ngay.
  - Actor mọi thao tác: `{ kind: "system", id: \`automation:${ruleKey}\` }`.
- `ApplicationOutcome = "applied" | "already_applied" | "skipped_no_authority" | "error"` + `detail`.

- [ ] **Step 1: Test đỏ** (real DB): mỗi action type → hiệu ứng đúng qua command P0 (transition ledger có
  dòng `actor.kind === "system"`); apply cùng action lần 2 → `"already_applied"`, 0 hiệu ứng trùng;
  `create_decision_request` khi không có authority `enabled` → `"skipped_no_authority"`, 0 DR;
  `schedule_delayed` → 1 row `engagement_automation_schedules(status:"pending")`, thread chưa đổi.
- [ ] **Step 2: đỏ → implement → xanh.**
- [ ] **Step 3: Commit** `feat(engagement): typed automation action union + idempotent apply via command layer`.

---

### Task 5: Rule model + evaluator

**Files:**
- Create: `services/company/commercial/services/customer-engagement/automation/rule-model.ts`
- Create: `services/company/commercial/services/customer-engagement/automation/evaluator.ts`
- Test: `.../tests/customer-engagement/automation-evaluator.test.ts`

**Interfaces (Produces):**
- `rule-model.ts`: `type AutomationRule = { ruleKey; version; name; trigger; priority; condition: Predicate;
  actions: AutomationAction[]; enabled; stopOnMatch; effectiveFrom; effectiveUntil }`; `validateRule(rule): void`
  (gọi `validatePredicate` + `validateAction[]` + trigger ∈ set).
- `evaluator.ts`: `evaluateRules(input: { trigger: string; threadId: string; dryRun?: boolean }, ctx):
  Promise<{ facts: AutomationFacts; matched: Array<{ ruleKey; version; actions: AutomationAction[] }>;
  applied: Array<{ ruleKey; version; actionIndex; outcome: ApplicationOutcome }> }>`:
  1. Load rule `enabled`, `trigger` khớp, `now() ∈ [effective_from, effective_until)`, order `priority ASC`.
  2. `facts = await buildAutomationFacts(threadId, ctx)` — **một lần**.
  3. Mỗi rule: `evaluatePredicate(condition, facts)`; match ⇒ push `matched`; nếu `!dryRun` ⇒
     `for (i, action) applyAction(...)` (tuần tự, action delayed → schedule). `stopOnMatch` ⇒ dừng vòng lặp.
  4. Trả `{ facts, matched, applied }`. `dryRun` ⇒ `applied` rỗng, 0 write.
  - **Không** async race: rules cùng trigger chạy tuần tự trong 1 lời gọi `evaluateRules`.

- [ ] **Step 1: Test đỏ** (real DB): seed rule `trigger:"message_received"`, condition
  `{ all: [{fact:"lastMessage.direction",op:"eq",value:"inbound"}, {fact:"inbox.locale",op:"eq",value:"vi"}] }`,
  action `route_to_team` → `evaluateRules` route thread; thread locale khác → `matched: []`;
  `dryRun:true` → `matched` có nhưng `applied: []`, thread không đổi; `stopOnMatch` → rule priority thấp hơn không chạy.
- [ ] **Step 2: đỏ → implement → xanh.**
- [ ] **Step 3: Commit** `feat(engagement): automation rule model + deterministic evaluator (priority order, dry-run, stop-on-match)`.

---

### Task 6: Trigger wiring + CSAT

**Files:**
- Modify: `services/company/commercial/services/customer-engagement/thread.service.ts` (sau `openThread`, `changeThreadStatus`)
- Modify: `services/company/commercial/services/customer-engagement/message.service.ts` (sau `recordInboundMessage`)
- Create: `services/company/commercial/services/customer-engagement/csat.service.ts`
- Test: `.../tests/customer-engagement/automation-triggers.test.ts`

**Interfaces:**
- Sau khi transaction state change **commit**, gọi `await evaluateRulesSafe({ trigger, threadId }, ctx)` —
  wrapper bắt mọi lỗi → log + `engagement_automation_applications(outcome:"error", detail)`, **không** ném
  ra ngoài (message/thread đã persist).
  - `openThread` → trigger `thread_opened`.
  - `changeThreadStatus` → trigger `thread_status_changed`.
  - `recordInboundMessage` → trigger `message_received` (sau reopen logic P0).
- `csat.service.ts`: `recordCsat(threadId, { score: 1..5, comment? }, ctx)` — `requireEngagementPermission(ctx, "engagement.thread.write")`;
  insert/update `engagement_thread_outcomes` (`csat_score`, `csat_recorded_at`); `appendOutboxEvent` (event
  `engagement.thread.csat_recorded.v1`, confidential — thêm builder); rồi `evaluateRulesSafe({ trigger:"csat_recorded", threadId }, ctx)`.

- [ ] **Step 1: Test đỏ** — inbound message trên workspace có rule routing → thread routed sau khi
  `recordInboundMessage` trả về; rule ném lỗi (mock `applyAction` throw) → message vẫn persist, 1 row
  `applications(outcome:"error")`; `recordCsat(score:1)` với rule `csat_recorded` + condition
  `{fact:"csat.latestScore",op:"lte",value:2}` action `escalate` → thread escalated.
- [ ] **Step 2: đỏ → implement → xanh.**
- [ ] **Step 3: Commit** `feat(engagement): wire automation triggers (thread/message/status/csat) with isolated failure`.

---

### Task 7: Delayed schedules in housekeeping (re-check before execute)

**Files:**
- Modify: `services/company/commercial/services/customer-engagement/housekeeping.service.ts`
- Test: `.../tests/customer-engagement/automation-delayed.test.ts`

**Interfaces:** `runHousekeepingTick` thêm `automationDelayed` vào kết quả. Pass:
- Claim `engagement_automation_schedules` `status='pending' AND due_at < now()` (bounded, `FOR UPDATE SKIP LOCKED`), set `claimed_at`.
- Mỗi row:
  1. Rule `(rule_key, rule_version)` vẫn `enabled` & trong hiệu lực? Không ⇒ `status:"skipped", skip_reason:"rule_disabled"`.
  2. `facts = buildAutomationFacts(thread_id, ctx)`; `evaluatePredicate(row.condition, facts)` **vẫn true**?
     Không ⇒ `status:"skipped", skip_reason:"condition_changed"`.
  3. Re-check ownership: nếu inner action là loại tác động conversation và `facts.thread.activeMode === "human_assigned"`
     (người đã tiếp quản) ⇒ `status:"skipped", skip_reason:"ownership_changed"`.
  4. `applyAction(row.action, { ..., actionIndex: row.action_index, dedupeKey: \`sched:${row.id}\` }, ctx)`
     → `status:"done"` / `"error"`.
- Actor `{ kind: "system", id: "automation:delayed" }`.

- [ ] **Step 1: Test đỏ** — schedule "escalate sau 30' nếu chưa first response":
  - respond trước due (`first_response_at` set) → tick → `skipped:condition_changed`, escalation_level không đổi.
  - không respond → tick sau due → `done`, escalation_level +1.
  - human takeover trước due → tick → `skipped:ownership_changed`.
  - rule bị disable trước due → tick → `skipped:rule_disabled`.
- [ ] **Step 2: đỏ → implement → xanh.**
- [ ] **Step 3: Commit** `feat(engagement): delayed automation execution with facts/ownership/rule re-check`.

---

### Task 8: Admin API + dry-run

**Files:**
- Create: `services/company/commercial/handlers/customer-engagement/automation.handler.ts`
- Modify: `services/company/commercial/handlers/customer-engagement/index.ts`, `.../rbac.ts`
- Create: `services/company/commercial/services/customer-engagement/automation/rule-store.service.ts`
- Test: `.../tests/customer-engagement/automation-admin.test.ts`

**Interfaces — endpoints (`expose:true`, `requireEngagementPermission(ctx, "engagement.automation.manage")`):**
- `POST /commercial/engagement/automation/rules` — `createOrVersionRule(ruleInput, ctx)`: `validateRule`;
  nếu `rule_key` đã có ⇒ tạo `version = max+1` (immutable), `enabled:false`.
- `POST /commercial/engagement/automation/rules/:key/enable` / `:key/disable` — toggle version mới nhất;
  disable ⇒ schedule pending của rule sẽ `skipped:rule_disabled` (Task 7).
- `GET  /commercial/engagement/automation/rules` — list + version + enabled.
- `POST /commercial/engagement/threads/:id/automation/dry-run` — body `{ trigger }` →
  `evaluateRules({ trigger, threadId, dryRun:true }, ctx)` → trả `{ facts, matched }` (0 write).
- `GET  /commercial/engagement/threads/:id/automation/applications` — ledger cho audit/QA.

- [ ] **Step 1: Test đỏ** — create rule → version 1 disabled; update cùng key → version 2; enable v2;
  dry-run trả `matched` không write; rule condition sai fact key → `invalidArgument`; thiếu perm → `permissionDenied`.
- [ ] **Step 2: đỏ → implement (handler mỏng, logic ở `rule-store.service`) → xanh + `npx tsc --noEmit`.**
- [ ] **Step 3: Commit** `feat(engagement): automation rule admin API + thread dry-run`.

---

### Task 9: Determinism guard + migrate P0 SLA-escalation into a seeded rule

**Files:**
- Create: `services/company/commercial/tests/customer-engagement/automation-no-llm.test.ts`
- Modify: `services/company/commercial/services/customer-engagement/housekeeping.service.ts` (bỏ pass
  SLA-escalation hardcode P0)
- Create: `services/company/commercial/services/customer-engagement/automation/default-rules.ts` (seed)
- Test: `.../tests/customer-engagement/automation-sla-parity.test.ts`

**Interfaces:**
- `automation-no-llm.test.ts` — quét thư mục `services/company/commercial/services/customer-engagement/automation/`:
  không có match `/(\beval\s*\(|new\s+Function|\bFunction\s*\(|require\(['"].*llm|openai|deepseek|litellm|anthropic)/i`;
  không import model client. Fail nếu vi phạm.
- `default-rules.ts`: `DEFAULT_ENGAGEMENT_RULES: AutomationRule[]` gồm:
  - `sla_first_response_escalation` (`trigger:"time_sweep"`, condition
    `{ all:[{fact:"sla.firstResponseBreached",op:"eq",value:true},{fact:"thread.firstResponded",op:"eq",value:false},{fact:"thread.status",op:"ne",value:"resolved"}] }`,
    action `escalate`) — **thay** pass hardcode P0.
  - `route_by_locale` (ví dụ, disabled mặc định).
  - `seedDefaultRules(ctx)` — idempotent (upsert theo `rule_key` version 1); `sla_first_response_escalation`
    `enabled:true`, còn lại `enabled:false`.
- `housekeeping.service.ts` — xoá nhánh SLA-escalation hardcode; thay bằng: mỗi tick, với thread mở, gọi
  `evaluateRules({ trigger:"time_sweep", threadId }, ctx)` (bounded batch). `runHousekeepingTick` trả
  `slaEscalated` = số application `escalate` outcome `applied` (giữ tương thích key kết quả P0).

- [ ] **Step 1: Test đỏ — parity** (`automation-sla-parity.test.ts`): tái tạo kịch bản P0 test
  "thread tier priority, first_response_due_at quá khứ, chưa first_response_at" → sau `runHousekeepingTick`
  → `escalation_level` tăng đúng như hành vi P0; thread đã `first_response_at` → không tăng.
- [ ] **Step 2: Viết `automation-no-llm.test.ts`** (chạy được ngay, xanh).
- [ ] **Step 3: Implement `default-rules.ts` + sửa housekeeping; wire `seedDefaultRules` vào chỗ seed
  workspace (hoặc migration/CI seed).**
- [ ] **Step 4: Chạy — parity + no-llm + housekeeping tests xanh.**
- [ ] **Step 5: Commit** `refactor(engagement): move P0 SLA-escalation into seeded automation rule + no-LLM guard`.

---

### Task 10: P3 test matrix + regression

**Files:**
- Create: `services/company/commercial/tests/customer-engagement/automation-matrix.test.ts`

**Cases (map spec §8.2 / §15):**

| Scenario | Assert |
| --- | --- |
| Deterministic replay | Cùng `AutomationFacts` + cùng `(rule_key, version)` → cùng `matched`/`actions` qua nhiều lần chạy |
| Rule versioned | Sửa rule → version mới; application/schedule cũ tham chiếu version cũ; enable version mới không đổi hồi tố |
| No LLM | `automation-no-llm.test.ts` xanh; evaluator thuần, không async I/O trong `evaluatePredicate` |
| Delayed re-check state | respond trước due → `skipped:condition_changed`; not respond → applied |
| Delayed re-check owner | human takeover trước due → `skipped:ownership_changed` |
| Disabled rule kill | disable → trigger mới không match; schedule pending → `skipped:rule_disabled` |
| Idempotency | Re-trigger cùng fact → `already_applied`, 0 effect trùng (label/route/DR) |
| Priority + stopOnMatch | Rule priority thấp chạy trước; `stopOnMatch` chặn phần còn lại |
| `create_decision_request` fail-closed | Không authority `enabled` cho `decisionKind` → `skipped_no_authority`, 0 DR |
| `create_decision_request` happy | Authority `enabled` → DR tạo với đúng `authority_key`, requester=system |
| State qua command | Mọi thay đổi thread do action → có `engagement_thread_transitions` với `actor.kind="system"` + outbox event |
| Rule failure cô lập | `applyAction` throw → message/thread vẫn persist, `applications(outcome:"error")` |
| SLA parity | Hành vi escalation giống P0 (Task 9) |

- [ ] **Step 1: Viết `automation-matrix.test.ts`.**
- [ ] **Step 2: Chạy**
  - `cd services/company && npx vitest run commercial/tests/customer-engagement/` — P0..P3 xanh.
  - `cd services/company && npx tsc --noEmit`; `npm test` — không hồi quy.
- [ ] **Step 3: Commit** `test(engagement): P3 automation matrix (determinism / delayed re-check / idempotency / fail-closed DR)`.

---

### Task 11: Runbook + vocabulary addendum

**Files:**
- Create: `docs/operations/customer-engagement-automation-runbook.md`
- Modify: `docs/architecture/customer-engagement-vocabulary.md`

- [ ] **Step 1: Runbook** — cách author rule (predicate JSON + action JSON), catalog `FACT_KEYS`, catalog
  action + `dedupe_key` mỗi loại, quy trình version/enable/disable, ngữ nghĩa delayed schedule + các
  `skip_reason`, cách dùng dry-run trước khi enable, "automation không gọi LLM — đó là ranh giới cứng".
- [ ] **Step 2: Vocabulary** — thêm: trigger set, rule `enabled`/version, `engagement_automation_applications.outcome`
  values, `engagement_automation_schedules.status`/`skip_reason` values, "state change do automation vẫn
  qua command layer + transition ledger".
- [ ] **Step 3: Commit** `docs(engagement): P3 automation runbook + vocabulary (facts/actions/triggers/skip reasons)`.

---

## Self-Review

**Spec coverage:**
- §8.2 "deterministic automation trước, agent sau; condition trên structured facts; không LLM;
  delayed rule re-check state" → Task 2 (facts), Task 3 (predicate thuần), Task 7 (re-check),
  Task 9 (no-LLM guard).
- §8.2 ví dụ: route theo locale/business-hours/tier/priority (Task 4 `route_*` + Task 2 fact
  `inbox.businessHoursOpen`/`customer.tier`), SLA + nhãn taxonomy (Task 4 `apply_label` + `escalate`),
  follow-up task (Task 4 `create_follow_up_task` qua operations), snooze/reopen (Task 4), escalate khi
  deadline/CSAT âm/health (Task 2 facts `csat`/`customer.healthStatus` + Task 6 trigger `csat_recorded` +
  Task 7 `time_sweep`), tạo Decision Request khi policy exception (Task 4 `create_decision_request`
  fail-closed).
- §6 state transition là command có validation → Global Constraints + Task 4 (không UPDATE trực tiếp).
- §7.1 DR khi command thuộc policy exception → Task 4 `create_decision_request` → P0
  `resolveEnabledAuthority` + `createDecisionRequest`.
- §12 metric là projection của immutable events → automation phát qua command/outbox (không field tự do
  làm KPI); `engagement_automation_applications` là ledger audit.
- §15 "Delayed automation: re-check state, owner và policy trước lúc execute" → Task 7.

**Gaps có chủ đích:**
- Không có config UI — chỉ API + JSON (Flutter/console admin ngoài phạm vi backend plan).
- Rule chỉ theo trigger + facts hiện tại; không có "aggregate across threads" (vd. "nếu backlog team > N")
  — lùi sau, cần fact nguồn khác.
- `time_sweep` quét mọi thread mở mỗi tick — bounded batch; nếu volume lớn cần cursor/partition ⇒ P4 tuning.
- Sales stage transition deterministic sau approval (§17.6) — cần chốt danh sách transition; P3 để
  `create_decision_request` cho commercial exception, transition sales-stage tự động lùi tới khi §17.6 trả lời.
- `customer.tier` nguồn: P3 đọc từ `sales.customers`/account segment nếu có; nếu chưa chuẩn hoá ⇒ fact
  trả `null`, rule tier-based tự không match (an toàn).

**Placeholder scan:** không "TBD". `setThreadPriority` helper P0 "nếu chưa có" — ghi rõ là 1 dòng +
transition, không phải lỗ hổng. Predicate/action đều enum đóng, mở rộng phải sửa code + test (có chủ đích).

**Type consistency:** `AutomationFacts` paths ↔ `FACT_KEYS` ↔ `validatePredicate`. `Op` set ↔
`evaluatePredicate` ↔ `validatePredicate`. `AutomationAction` union ↔ `validateAction` ↔ `applyAction` ↔
`schedule.action` snapshot. `outcome` values (`applied|already_applied|skipped_condition_changed|
skipped_ownership_changed|skipped_rule_disabled|skipped_no_authority|error`) khớp Task 4 ↔ 7 ↔ 8 ↔ 10 ↔ 11.
`trigger` set (`thread_opened|message_received|thread_status_changed|csat_recorded|time_sweep`) khớp
Task 1 ↔ 5 ↔ 6 ↔ 9.

---

## Execution Handoff

Sau khi P3 landed + matrix xanh: viết `2026-08-28-customer-engagement-p4.md` (autopilot event-driven,
feature-flagged, test-env-only cho tới Acceptance Gate P4) — dùng `apps/cosa/events/` trigger rule +
`trigger_promotion.py` + capability write (`engagement.message.send`/`assignment.write`) require approval,
và các điều kiện Acceptance Gate P4 trong overview.
