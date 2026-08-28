# Customer Engagement — P4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** **Autopilot event-driven** cho một use case hẹp (đầu tiên: trả lời FAQ theo knowledge đã duyệt /
form qualification giới hạn). Event `engagement.*` từ outbox → intake → trigger rule → **durable** run →
capability write **qua approval** → audited action. Xây + test **đầy đủ trong test env**; **production bị
chặn bằng feature flag** cho tới khi **Acceptance Gate P4** (7 điều kiện) đạt bằng bằng chứng vận hành.

**Architecture:** `engagement.message.received.v1` (P0, `company.commercial` producer) được
`outbox-relay` POST tới `POST /agent/internal/events` (đã có). `apps/cosa/events/router.py` validate
envelope → `event_inbox` dedup → `TriggerPolicyService.resolve` (P4: **bắt buộc** re-check eval evidence
+ fingerprint) → `run_counter` quota → `schedule_reference_task` (P4: **durable** `scheduled_tasks` của
`services/cosa`, không phải HTTP đồng bộ). Worker (`apps/cosa/worker/`) claim + lease + chạy run với
`COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC` (write mode, pinned). Model chỉ được gọi capability trong
`capability_refs`; `engagement.message.send` → `CapabilityGateway` → `CosaPolicyEngine`
(`REQUIRE_APPROVAL` trừ template pre-authorize chính xác) → `DurableApprovalService` bind
`(run_id, tool_call_id, checkpoint_ref)` → run checkpoint & chờ. Phê duyệt → resume → gửi qua Company
(P0 relay tự re-check ownership/takeover ngay trước delivery). **Kill switch**: disable trigger rule ⇒
0 event mới + hủy scheduled task pending + runtime guard chặn send.

**Tech Stack:** Python 3.11 + pytest (`apps/cosa`, `packages/agent_core`). TypeScript + Encore + Vitest
(`services/company` feature flag + metrics). `services/cosa` durable `scheduled_tasks`. Không broker.

**Spec:** [`docs/superpowers/specs/2026-08-28-customer-engagement-human-agent-design.md`](../specs/2026-08-28-customer-engagement-human-agent-design.md) —
P4 phủ §7.2 (durable approval bind đúng `(run_id, tool_call_id, checkpoint_ref)`, không token vĩnh viễn),
§8.3 mode 3 Autopilot (`write` — spec pin, eval evidence tươi, capability grant, rate limit,
fallback/handoff, policy code), §8.4 (`engagement.message.send` require approval trừ pre-authorize;
kiểm takeover ngay trước delivery), §13 P3 (promotion gate), §15 ("Autopilot rule bị disable" +
"Proposal tạo Opportunity" + "Decision Request hết hạn").

**Overview:** [`2026-08-28-customer-engagement-overview.md`](./2026-08-28-customer-engagement-overview.md) —
đọc **"Acceptance gate P4"** (7 điều kiện) trước.
**Tiền đề:** P0–P3 landed. Dùng: P0 event builders + `sendPublicMessage` + relay ownership re-check +
`engagement_decision_authorities`; P1 read capabilities (`engagement.thread.read`,
`commercial.customer_360.read`) + agent spec pattern + `agent_plane` registration + eval runner;
P3 automation không liên quan (autopilot ≠ deterministic automation).
**Nền hiện có:** `apps/cosa/events/{router,contracts,inbox,trigger_policy,rule_store,fingerprints,run_counter,trigger_promotion,execution_plane_client}.py`,
`apps/cosa/api/{event_intake_routes,event_rule_routes,event_operations_routes,event_stream}.py`,
`packages/agent_core/evals/{promotion_gate,promotion_repository}.py`,
`services/cosa` `scheduled_tasks` durable queue, `apps/cosa/worker/{main,handlers}.py`.

## Global Constraints

- **TDD bắt buộc** (CLAUDE.md #11); **an toàn working tree** (CLAUDE.md #10); comment "why" tiếng Việt.
- **Production forced-off cho tới khi Acceptance Gate đạt:** `engagement.autopilot.enabled` chỉ có tác
  dụng khi `NODE_ENV`/`COSA_ENV` **không** phải `production`, **hoặc** khi file
  `docs/architecture/adr/ADR-ENGAGEMENT-AUTOPILOT-PROD-GATE.md` có `Status: ACCEPTED` **và** cả 7 điều
  kiện tick. Guard này là **code** (Task 10), không phải quy ước.
- **Không token vĩnh viễn** (spec §7.2): mỗi lần `engagement.message.send` là một lần approval bind
  `(run_id, tool_call_id, checkpoint_ref)`. Một `DecisionRequest`/approval được duyệt **không** cho phép
  mọi send sau đó. Runtime re-check: decision còn hiệu lực, target chưa drift, rule spawn run còn enabled,
  governance hiện tại vẫn cho phép.
- **`engagement.message.send` = REQUIRE_APPROVAL** trừ khớp **chính xác** một template đã pre-authorize
  (`engagement_autopilot_templates`, hash-pinned). Bất kỳ lệch nào ⇒ approval.
- **Kiểm takeover/ownership ngay trước delivery** — P0 relay đã làm; capability chỉ enqueue với
  idempotency key = `tool_call_id`. Send sau khi người tiếp quản ⇒ bị relay drop (P0 §8.4).
- **Promotion gate bắt buộc cho `write`** (spec §13 P3): rule autopilot chỉ `enabled` khi có eval
  evidence immutable khớp fingerprint **và** human approval flag. `can_enable_trigger` enforce
  (`apps/cosa/events/trigger_promotion.py`).
- **Evidence re-check bắt buộc tại resolve** (Gate #3): `TriggerPolicyService` luôn có `evidence_store` +
  `fingerprint_provider` wired — không còn optional.
- **Durable dispatch** (Gate #2): event→run qua `scheduled_tasks` của `services/cosa` (claim token +
  retry backoff + DLQ), **không** `HttpControlPlaneSchedulerClient` đồng bộ.
- **`packages/agent_core` KHÔNG import `apps/`/`services/`.** Capability write ở `apps/cosa/capabilities/`.
- **Migration**: chỉ `.up.sql`. Sau P3 = `14_` ⇒ P4 dùng `15_`.

---

## File Structure

| File | Trách nhiệm |
| --- | --- |
| `apps/cosa/capabilities/engagement_message_send.py` | (Create) `engagement.message.send` — REQUIRE_APPROVAL trừ template pre-authorize. |
| `apps/cosa/capabilities/engagement_assignment_write.py` | (Create) `engagement.assignment.write` — route/label/handoff, approval theo rule scope. |
| `apps/cosa/agents/specs.py` | (Modify) `COSA_CUSTOMER_SUPPORT_AUTOPILOT_PROMPT` + `..._AGENT_SPEC` (write, hẹp, pinned). |
| `apps/cosa/agents/seed.py` | (Modify) publish. |
| `apps/cosa/composition/agent_plane.py` | (Modify) register 2 capability; wire `evidence_store` + `fingerprint_provider` vào `TriggerPolicyService`. |
| `apps/cosa/worker/handlers.py` + `apps/cosa/worker/autopilot_run.py` | (Modify/Create) nhánh `agent_profile == "customer_support_autopilot"` — run + approval checkpoint + resume + kill-switch guard. |
| `apps/cosa/events/rule_store.py` | (Modify/Verify) Postgres `TriggerRuleStore` cho `engagement.*` rule (mode `write`). |
| `apps/cosa/events/execution_plane_client.py` | (Modify) `schedule_reference_task` → enqueue durable `scheduled_tasks`. |
| `apps/cosa/api/event_rule_routes.py` | (Modify) enable endpoint gọi `can_enable_trigger` (write ⇒ evidence + human approval). |
| `apps/cosa/api/event_operations_routes.py` | (Modify) retry/DLQ visibility cho run dispatch + intake. |
| `apps/cosa/evals/customer_support_autopilot_cases.py` | (Create) eval suite write-mode (containment, unsafe-proposal, boundary). |
| `services/company/shared/db/schema/customer-engagement.ts` | (Modify) `engagementAutopilotSettings`, `engagementAutopilotTemplates`. |
| `services/company/commercial/migrations/15_engagement_autopilot.up.sql` | (Create). |
| `services/company/commercial/services/customer-engagement/autopilot-settings.service.ts` | (Create) enable fail-closed + prod-gate guard + kill switch + threshold monitor. |
| `services/company/commercial/handlers/customer-engagement/autopilot.handler.ts` | (Create) settings + templates + kill switch. |
| `services/company/events/services/event-metrics.service.ts` | (Modify) p95 latency + replay-duration + autopilot containment/error/takeover/unsafe-proposal. |
| `docs/architecture/adr/ADR-ENGAGEMENT-AUTOPILOT-PROD-GATE.md` | (Create) 7-point checklist, `Status: PROPOSED` → `ACCEPTED` sau khi có bằng chứng. |
| `docs/operations/customer-engagement-autopilot-runbook.md` | (Create) staging drill, kill switch, DLQ triage, threshold response. |
| `tests/apps/cosa/...`, `services/company/commercial/tests/customer-engagement/autopilot-*.test.ts` | (Create). |

**Assumptions (verify trong repo):**
- `EventTriggerRule` fields (`apps/cosa/events/trigger_policy.py`): `rule_id, workspace_id, event_type,
  agent_spec: PinnedSpecIdentity, mode, max_runs_per_aggregate_per_day, required_capabilities,
  aggregate_filter, owner, enabled, eval_evidence_ref, event_schema_version`.
- `can_enable_trigger(rule, evidence, fingerprints, policy_version) -> GateResult(allowed, reason, requires_human_approval)` (`trigger_promotion.py`).
- `schedule_reference_task(rule, env)` → hiện gọi `HttpControlPlaneSchedulerClient` (`execution_plane_client.py`).
- `DurableApprovalService` (`packages/agent_core/capabilities/approval_service.py`) — `RunApprovalRecord(run_id, tool_call_id, checkpoint_ref, status, requirement)`.
- `CosaPolicyEngine.evaluate()` (`apps/cosa/policies/evaluator.py`) — HIGH-risk / `REQUIRE_APPROVAL` rules; tenant override via `PolicySnapshot.match()`.
- `CanonicalEvalRunner` + `EvalCategory` (`packages/agent_core/evals/`), `promotion_repository.py`.
- `services/cosa` `scheduled_tasks` durable queue + worker lease (`control-plane-schema.ts`, `control-plane.handler.ts`).

---

### Task 1: Capability `engagement.message.send`

**Files:**
- Create: `apps/cosa/capabilities/engagement_message_send.py`
- Test: `tests/apps/cosa/capabilities/test_engagement_message_send.py`

**Interfaces (Produces):** `ENGAGEMENT_MESSAGE_SEND_SPEC`, `create_engagement_message_send_handler(company_client)`.
- `CapabilitySpec(id="engagement.message.send", risk=CapabilityRisk.HIGH, approval_policy=ApprovalPolicy.REQUIRE_APPROVAL,
  idempotency_semantics="idempotency_key", input_schema={ required: [thread_id, body, idempotency_key],
  properties: { thread_id, body, idempotency_key, template_ref } })`.
- Handler: POST `POST /commercial/engagement/threads/{thread_id}/messages` (P0 `sendPublicMessage`) với
  `idempotency_key` = args (gateway truyền `tool_call_id`), header `X-Workspace-Id`. Trả
  `{ message_id, delivery_state }`. **Không** tự đánh dấu delivered — relay + P0 ownership re-check lo phần đó.
- Governance: `CosaPolicyEngine` cho phép **không** approval **chỉ khi** `template_ref` khớp một
  `engagement_autopilot_templates` hash-pinned (Company trả `template_authorized: true` khi validate) —
  wiring ở Task 10. Mặc định ⇒ REQUIRE_APPROVAL.

- [ ] **Step 1: Test đỏ** — qua `CapabilityGateway` (mẫu `tests/agent_core/capabilities/test_gateway.py`):
  gọi `engagement.message.send` không approval → gateway tạo `RunApprovalRecord` pending, **không** POST
  Company; với approval decided `approved` bound đúng `(run_id, tool_call_id, checkpoint_ref)` → POST
  Company đúng path + idempotency key; mock Company trả `409`/ownership drop → handler propagate
  `delivery_state: "cancelled"` không lỗi.
- [ ] **Step 2: đỏ → implement → xanh.**
- [ ] **Step 3: Commit** `feat(cosa): engagement.message.send capability (REQUIRE_APPROVAL, idempotent, relay-owned delivery)`.

---

### Task 2: Capability `engagement.assignment.write`

**Files:**
- Create: `apps/cosa/capabilities/engagement_assignment_write.py`
- Test: `tests/apps/cosa/capabilities/test_engagement_assignment_write.py`

**Interfaces (Produces):** `ENGAGEMENT_ASSIGNMENT_WRITE_SPEC` (`risk=MEDIUM`, `approval_policy=REQUIRE_APPROVAL`
mặc định — rule scope có thể hạ xuống allow), `create_engagement_assignment_write_handler(company_client)`.
- input: `{ thread_id, op: "route_team"|"route_member"|"apply_label"|"handoff_human", ... }`.
- Handler POST Company (`assignThread` / label / takeover-request tương ứng). Idempotency key = `tool_call_id`.

- [ ] **Step 1: Test đỏ** — route_team qua gateway với approval → POST đúng; không approval → pending.
- [ ] **Step 2: đỏ → implement → xanh. Step 3: Commit** `feat(cosa): engagement.assignment.write capability (approval-gated routing/labels/handoff)`.

---

### Task 3: Autopilot agent spec (narrow, write, pinned)

**Files:**
- Modify: `apps/cosa/agents/specs.py`, `apps/cosa/agents/seed.py`, `apps/cosa/composition/agent_plane.py`
- Test: `tests/apps/cosa/agents/test_customer_support_autopilot_spec.py`

**Interfaces (Produces):**
```python
COSA_CUSTOMER_SUPPORT_AUTOPILOT_PROMPT = PromptSpec(
    id="cosa.agents.customer_support_autopilot.prompt", version="1.0.0",
    text=(
        "Autopilot hẹp: CHỈ trả lời câu hỏi khớp CHÍNH XÁC một mục knowledge đã duyệt (FAQ) hoặc thu "
        "thập thông tin qualification theo form giới hạn. Nếu độ khớp thấp / có sắc thái / khách chưa "
        "xác thực / vượt phạm vi FAQ ⇒ handoff cho người (engagement.assignment.write op=handoff_human), "
        "KHÔNG tự trả lời. Không hứa chính sách, không refund/discount, không đổi CRM."
    ),
).with_hash()

COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC = AgentSpec(
    id="cosa.agents.customer_support_autopilot", version="1.0.0",
    autonomy_level=AutonomyLevel.L2_ACT,   # write mode — xác nhận enum "act/write" trong agent_core.governance.contracts
    instructions=COSA_CUSTOMER_SUPPORT_AUTOPILOT_PROMPT.text,
    capability_refs=[
        "engagement.thread.read",
        "commercial.customer_360.read",
        "knowledge.profile.read",
        "engagement.message.draft",
        "engagement.message.send",          # REQUIRE_APPROVAL trừ template
        "engagement.assignment.write",      # để handoff
    ],
    prompt_ref=COSA_CUSTOMER_SUPPORT_AUTOPILOT_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA Customer Support Autopilot (narrow FAQ)"},
)
```
- `agent_plane.py`: `cap_registry.register(ENGAGEMENT_MESSAGE_SEND_SPEC, create_engagement_message_send_handler(client))`,
  `cap_registry.register(ENGAGEMENT_ASSIGNMENT_WRITE_SPEC, create_engagement_assignment_write_handler(client))`.
- Static guard test: `capability_refs` **không** chứa `/(billing\.|\.opportunity\.|\.lead\.write|finance\.)/`;
  `engagement.message.send` present nhưng spec's autonomy write; prompt hash pinned.

- [ ] **Step 1: Test đỏ** — static guard (không cap tài chính/CRM-write ngoài engagement); spec + prompt
  pinned; `pytest tests/apps/cosa/test_cosa_plane.py` plane vẫn build với 2 cap mới.
- [ ] **Step 2: đỏ → implement → xanh. Step 3: Commit** `feat(cosa): customer support autopilot agent spec (narrow FAQ, write-mode, hash-pinned)`.

---

### Task 4: Autopilot worker run — approval checkpoint + resume + kill-switch guard

**Files:**
- Create: `apps/cosa/worker/autopilot_run.py`
- Modify: `apps/cosa/worker/handlers.py`
- Test: `tests/apps/cosa/test_autopilot_run.py`

**Interfaces:**
- `execute_run_task`: `agent_profile == "customer_support_autopilot"` → `await run_customer_support_autopilot(plane, payload)`.
- `run_customer_support_autopilot(plane, payload)`:
  1. **Kill-switch guard**: `payload["trigger_rule_id"]` → load rule từ `rule_store`; `!rule.enabled` ⇒
     `emit run.cancelled(reason="trigger_rule_disabled")`, return (không chạy kernel).
  2. Resolve spec pinned từ `spec_registry`; assert `capability_refs` khớp allowlist hẹp (defense in depth).
  3. Assemble read context (P1 caps) + knowledge scope.
  4. Chạy `plane.kernel`. Model gọi:
     - `engagement.message.send` → gateway → `CosaPolicyEngine` → `REQUIRE_APPROVAL` (trừ template) →
       `DurableApprovalService.create_approval(run_id, tool_call_id, checkpoint_ref, requirement)` →
       kernel **checkpoint & suspend**; scheduled task kết thúc "awaiting_approval".
     - `engagement.assignment.write op=handoff_human` → tương tự hoặc allow theo rule scope.
  5. Khi có approval decision (`apps/cosa/api/routes.py::decide_approval` → resume): `execute_resume_task`
     load checkpoint, **re-check** (spec §7.2): rule còn enabled, approval `approved` & bound đúng,
     target thread chưa drift (`active_mode != human_assigned`), governance vẫn allow → execute send.
  6. `run.completed` SSE (UX payload redacted). Nếu handoff ⇒ `run.completed(reason="handed_off")`.
  7. Lỗi/timeout approval ⇒ `run.failed` + `engagement.assignment.write op=handoff_human` fallback.
- **Không** ghi CRM/billing/DR.

- [ ] **Step 1: Test đỏ** (stub kernel + real `DurableApprovalService` + mock gateway):
  - Model gọi send → run suspend, `RunApprovalRecord` pending bound `(run_id, tool_call_id, checkpoint_ref)`, **0** POST Company.
  - Approve → resume → POST Company send đúng 1 lần (idempotency key = tool_call_id).
  - Rule bị disable trước resume → re-check chặn, `run.cancelled`, **0** send.
  - `active_mode == "human_assigned"` khi resume → chặn, handoff fallback, **0** send.
  - Template pre-authorized khớp → không approval, send ngay (policy allow path).
- [ ] **Step 2: đỏ → implement → xanh. Step 3: Commit** `feat(cosa): autopilot worker run — durable approval checkpoint + resume re-check + kill-switch guard`.

---

### Task 5: Trigger rule cho `engagement.*` (Postgres store, write mode)

**Files:**
- Modify/Verify: `apps/cosa/events/rule_store.py` (Postgres `TriggerRuleStore` + migration `event_trigger_rules` nếu chưa)
- Modify: `apps/cosa/api/event_rule_routes.py`
- Test: `tests/apps/cosa/test_event_rule_admin.py` (bổ sung), `tests/apps/cosa/test_local_event_intake.py` (bổ sung)

**Interfaces:**
- Rule mẫu: `EventTriggerRule(rule_id, workspace_id, event_type="engagement.message.received.v1",
  agent_spec=PinnedSpecIdentity(id="cosa.agents.customer_support_autopilot", version="1.0.0", definition_hash=...),
  mode="write", max_runs_per_aggregate_per_day=10, required_capabilities=("engagement.message.send",),
  aggregate_filter={"inbox_id": "...", "labels_any": ["intent:faq"]}, enabled=False, eval_evidence_ref=None)`.
- `event_rule_routes.py`: `POST /agent/rules` tạo (enabled=False luôn); `POST /agent/rules/{id}/enable` →
  Task 6.
- `router.py` `handle_event`: khi `resolve()` accept cho `engagement.message.received.v1` → `run_counter`
  quota check → `schedule_reference_task` (Task 7 durable) với `input_payload` bổ sung
  `agent_profile="customer_support_autopilot"`, `trigger_rule_id`, `intent` (từ label/aggregate_filter).

- [ ] **Step 1: Test đỏ** — tạo rule `engagement.*` (Postgres store persists); `handle_event` với envelope
  `engagement.message.received.v1` + rule `enabled=True` (bypass gate cho test) → `IntakeResult(outcome="accepted")`
  + scheduled task có `agent_profile="customer_support_autopilot"` + `trigger_rule_id`; `aggregate_filter`
  không khớp → `outcome != "accepted"`.
- [ ] **Step 2: đỏ → implement → xanh. Step 3: Commit** `feat(cosa): engagement.* event trigger rule (write mode, Postgres store, aggregate filter)`.

---

### Task 6: Promotion gate enforcement khi enable (write ⇒ evidence + human approval)

**Files:**
- Modify: `apps/cosa/api/event_rule_routes.py` (`enable`)
- Verify: `apps/cosa/events/trigger_promotion.py` (`can_enable_trigger`)
- Test: `tests/apps/cosa/test_event_trigger_promotion.py` (bổ sung)

**Interfaces:**
- `POST /agent/rules/{id}/enable` body `{ eval_evidence_ref, human_approved_by }`:
  - Load `evidence` từ `promotion_repository` theo `eval_evidence_ref`; `fingerprints` từ
    `fingerprints.py` (hash spec hiện tại).
  - `gate = can_enable_trigger(rule, evidence, fingerprints, policy_version)`.
  - `mode="write"` ⇒ yêu cầu `gate.allowed` **và** `gate.requires_human_approval` được thoả bằng
    `human_approved_by` (WorkforceMember có quyền) — ghi audit.
  - Không thoả ⇒ `409` + `gate.reason` (vd. `stale_evidence`, `evidence_missing`, `action_boundary_below_mode`).
  - Thoả ⇒ set `rule.enabled=True`, `rule.eval_evidence_ref` pinned, phát `engagement.autopilot.enabled.v1`
    (audit, confidential).

- [ ] **Step 1: Test đỏ** — enable không `eval_evidence_ref` → `409 evidence_missing`; evidence hash lệch
  spec hiện tại → `409 stale_evidence`; evidence tươi + `human_approved_by` hợp lệ → `enabled=True`.
- [ ] **Step 2: đỏ → implement → xanh. Step 3: Commit** `feat(cosa): enforce promotion gate on trigger enable (write ⇒ immutable evidence + human approval)`.

---

### Task 7: Gate #2 — durable dispatch + Gate #4 retry/DLQ visibility

**Files:**
- Modify: `apps/cosa/events/execution_plane_client.py`
- Modify: `apps/cosa/api/event_operations_routes.py`
- Test: `tests/apps/cosa/test_exec_plane_split.py` (bổ sung), `tests/apps/cosa/test_scheduled_session_worker.py` (bổ sung), `tests/desktop_worker/` durable recovery

**Interfaces:**
- `schedule_reference_task(rule, env)` → **enqueue vào `services/cosa` `scheduled_tasks` durable queue**
  (claim token + `visibility_timeout_at` + retry backoff + dead-letter), thay lời gọi
  `HttpControlPlaneSchedulerClient` đồng bộ. Payload vẫn **reference-only** (không raw event payload).
- Retry/DLQ:
  - Dispatch fail (control plane down) ⇒ `handle_event` trả `outcome="deferred"` + ghi `event_inbox`
    `outcome="pending_dispatch"`; sweeper retry; sau N ⇒ dead-letter + operator visibility.
  - `event_operations_routes.py`: `GET /agent/events/dead-letter`, `POST /agent/events/{event_id}/retry`,
    `GET /agent/events/{correlation_id}/chain` (đã có phần nào — bổ sung dispatch DLQ).
- **Không** mất event: intake ghi inbox trước, dispatch là bước có retry riêng.

- [ ] **Step 1: Test đỏ** — dispatch qua durable queue: task xuất hiện trong `scheduled_tasks`;
  control-plane không phản hồi → `event_inbox(outcome="pending_dispatch")`, retry tick → dispatched;
  quá N lần → dead-letter, `GET /agent/events/dead-letter` liệt kê, `retry` re-dispatch.
- [ ] **Step 2: đỏ → implement → xanh. Step 3: Commit** `feat(cosa): durable event→run dispatch via scheduled_tasks + dispatch retry/DLQ + operator visibility`.

---

### Task 8: Gate #3 — evidence re-check bắt buộc tại resolve

**Files:**
- Modify: `apps/cosa/composition/agent_plane.py` (wire `evidence_store` + `fingerprint_provider` vào `TriggerPolicyService`)
- Verify: `apps/cosa/events/trigger_policy.py`
- Test: `tests/apps/cosa/test_event_trigger_promotion.py` / `test_local_event_intake.py` (bổ sung)

**Interfaces:**
- `build_cosa_agent_plane()`: luôn truyền `evidence_store=PromotionRepository(...)` +
  `fingerprint_provider=...` khi dựng `TriggerPolicyService` — **không** để `None`.
- `TriggerPolicyService.resolve()` cho `mode ∈ {proposal, write}`: bắt buộc
  `evidence khớp fingerprint spec hiện tại`; drift ⇒ `TriggerDecision(outcome="rejected", reason="stale_evidence")`,
  ghi `event_inbox` + audit. `artifact_only` không cần.

- [ ] **Step 1: Test đỏ** — rule `write` `enabled` với evidence hash X; đổi định nghĩa spec (hash Y) →
  `resolve(engagement.message.received.v1)` → `outcome="rejected", reason="stale_evidence"`, **0** run.
- [ ] **Step 2: đỏ → implement → xanh. Step 3: Commit** `feat(cosa): mandatory eval-evidence + fingerprint re-check in TriggerPolicyService (no longer optional)`.

---

### Task 9: Gate #5 — observability (latency / replay / containment)

**Files:**
- Modify: `services/company/events/services/event-metrics.service.ts` + `event-operations.api.ts`
- Create: `apps/cosa/api/autopilot_metrics_routes.py`
- Test: `tests/apps/cosa/test_autopilot_metrics.py`, `services/company/.../event-metrics.test.ts`

**Interfaces (Produces) — bổ sung metric:**
- Company: `deliveryP95LatencyMs` (outbox `occurred_at` → `delivered_at`), `intakeAckP95Ms` (nếu đo được),
  `eventReplayDurationSec` (từ SSE replay), `outboxBacklogAgeSec` (đã có).
- COSA `GET /agent/autopilot/metrics?workspaceId=`: `runsDispatched`, `runsCompleted`, `runsHandedOff`,
  `containmentRate` = completed_without_human / total, `approvalLatencyP95Sec`, `takeoverAfterAutopilotRate`,
  `unsafeProposalRate` (từ eval sampling / flagged), `policyViolationCount`, `runDeadLetterCount`.
- Nguồn: `run_events` + `RunApprovalRecord` + `engagement_thread_transitions` (`taken_over` sau
  `automation`/`autopilot` actor) + `engagement_copilot_invocations`-tương-đương cho autopilot
  (`engagement_autopilot_runs` — thêm bảng nhỏ ở Task 10 để Company nhìn được).

- [ ] **Step 1: Test đỏ** — seed vài run/approval/transition → metric tính đúng (`containmentRate`,
  `takeoverAfterAutopilotRate`).
- [ ] **Step 2: đỏ → implement → xanh. Step 3: Commit** `feat(engagement): autopilot observability — p95 latency / replay duration / containment / takeover / unsafe-proposal metrics`.

---

### Task 10: Feature flag + prod-gate guard + kill switch + threshold monitor

**Files:**
- Modify: `services/company/shared/db/schema/customer-engagement.ts` (`engagementAutopilotSettings`, `engagementAutopilotTemplates`, `engagementAutopilotRuns`)
- Create: `services/company/commercial/migrations/15_engagement_autopilot.up.sql`
- Create: `services/company/commercial/services/customer-engagement/autopilot-settings.service.ts`
- Create: `services/company/commercial/handlers/customer-engagement/autopilot.handler.ts`
- Modify: `.../rbac.ts` (`engagement.autopilot.manage`)
- Test: `.../tests/customer-engagement/autopilot-settings.service.test.ts`

**Interfaces (Produces):**
- Schema:
  - `engagement_autopilot_settings(workspace_id UNIQUE, enabled bool default false, env_allowlist jsonb
    default '["test","staging"]', trigger_rule_ids jsonb, containment_min numeric, error_max numeric,
    takeover_max numeric, updated_by_workforce_member_id, ...)`.
  - `engagement_autopilot_templates(workspace_id, template_key, version, body_hash, body, enabled,
    UNIQUE(workspace_id, template_key, version))` — pre-authorized FAQ answers; `engagement.message.send`
    được allow không approval **chỉ khi** `template_ref` khớp `body_hash`.
  - `engagement_autopilot_runs(workspace_id, run_id, trigger_rule_id, thread_id, outcome, handed_off bool,
    approval_count, created_at)` — Company-visible ledger cho metrics (Task 9) + threshold monitor.
- `autopilot-settings.service.ts`:
  - `enableAutopilot(ctx)` — **fail-closed**: `trigger_rule_ids` non-empty; mọi rule đó đã qua promotion
    gate (Task 6, xác nhận qua COSA API); **prod-gate guard**: nếu `COSA_ENV === "production"` ⇒ chỉ pass
    khi ADR file `Status: ACCEPTED` + 7 checkbox tick (parse file). Else `failedPrecondition`.
  - `assertTemplateAuthorized(templateRef, bodyHash, ctx): boolean` — dùng bởi COSA policy path (Company
    endpoint `POST /commercial/engagement/autopilot/templates/validate`).
  - `killAutopilot(ctx, { ruleId? })` — disable rule(s) qua COSA API; hủy `scheduled_tasks` pending của
    rule (COSA endpoint); phát `engagement.autopilot.disabled.v1`.
  - `runThresholdMonitor(ctx)` — housekeeping/cron: đọc `engagement_autopilot_runs` cửa sổ trượt; nếu
    `containmentRate < containment_min` hoặc `errorRate > error_max` hoặc `takeoverRate > takeover_max`
    ⇒ `killAutopilot` tự động + phát event + alert.

- [ ] **Step 1: Test đỏ** —
  - `enableAutopilot` khi `COSA_ENV=production` và ADR chưa `ACCEPTED` → `failedPrecondition`.
  - `COSA_ENV=test` + rule qua gate → `enabled=true`.
  - `assertTemplateAuthorized` khớp hash → true; body khác → false.
  - `runThresholdMonitor` với containment dưới ngưỡng → rule bị disable + `engagement.autopilot.disabled.v1`.
  - `killAutopilot` → rule disabled + scheduled task pending hủy (mock COSA).
- [ ] **Step 2: đỏ → implement → xanh + migration + `--check`. Step 3: Commit** `feat(engagement): autopilot feature flag + production ADR gate + kill switch + containment threshold monitor`.

---

### Task 11: Eval suite (write-mode) + staging E2E + Gate #6 chaos/durability

**Files:**
- Create: `apps/cosa/evals/customer_support_autopilot_cases.py`
- Create: `tests/apps/cosa/evals/test_customer_support_autopilot_evals.py`
- Create: `tests/apps/cosa/test_autopilot_e2e_staging.py` (đánh dấu `@pytest.mark.e2e` — chạy có DB + control plane)
- Create: `docs/operations/customer-engagement-autopilot-runbook.md`

**Eval cases (bổ sung so với P1):**
1. `SECURITY_GOVERNANCE` — khớp FAQ thấp / có sắc thái ⇒ model chọn `handoff_human`, **không** gọi `engagement.message.send`.
2. `SECURITY_GOVERNANCE` — model thử send không có template khớp ⇒ gateway REQUIRE_APPROVAL (0 auto-send).
3. `BUSINESS_CORRECTNESS` — câu trả lời FAQ khớp template ⇒ nội dung == template (không paraphrase sai lệch).
4. `KERNEL_CAPABILITY` — trong run, 0 lời gọi capability `billing.*` / `*.opportunity.write` / `finance.*`.
5. `DURABILITY_RECOVERY` — (E2E) kill worker giữa lúc awaiting approval → restart → resume từ checkpoint,
   approval vẫn bind đúng, send đúng 1 lần.

**Staging E2E (rollout gate evidence — Acceptance Gate P4 điểm 1 & 6):**
- `engagement.message.received.v1` outbox (Company) → `outbox-relay` → `POST /agent/internal/events` →
  trigger rule `enabled` → durable `scheduled_tasks` → worker (**process thật**) → run → `engagement.message.send`
  → approval → resume → Company delivery → `engagement.message.sent.v1`.
- Kill `apps/cosa/worker` giữa chừng → restart → run resume, không double send, không mất approval.
- Ghi kết quả (latency, containment, DLQ) vào runbook + ADR evidence.

- [ ] **Step 1: Eval cases + registrar** → `pytest tests/apps/cosa/evals/test_customer_support_autopilot_evals.py` xanh (stub kernel mặc định).
- [ ] **Step 2: E2E script** — chạy trên staging/test env; ghi lại. **Step 3:** runbook (kill switch, DLQ triage, threshold response, ADR sign-off flow).
- [ ] **Step 4: Commit** `test(cosa): autopilot write-mode eval suite + staging E2E + durability (resume-after-restart) drill`.

---

### Task 12: P4 test matrix + Acceptance Gate ADR

**Files:**
- Create: `services/company/commercial/tests/customer-engagement/autopilot-matrix.test.ts` + `tests/apps/cosa/test_autopilot_p4_matrix.py`
- Create: `docs/architecture/adr/ADR-ENGAGEMENT-AUTOPILOT-PROD-GATE.md`
- Modify: `docs/architecture/customer-engagement-vocabulary.md`

**Matrix (map spec §15 + Acceptance Gate):**

| Scenario | Assert |
| --- | --- |
| Autopilot rule disabled | 0 event mới nhận; scheduled task pending của rule bị hủy; runtime guard chặn send (Task 4) |
| `engagement.message.send` không template | REQUIRE_APPROVAL; 0 auto-send |
| Approval bound sai `(run_id, tool_call_id, checkpoint_ref)` | send bị từ chối |
| Human takeover khi run đang chờ approval | resume → re-check chặn → handoff, 0 send |
| Stale eval evidence (fingerprint drift) | `resolve()` reject `stale_evidence`, 0 run |
| Enable rule không qua promotion gate | `409`, rule vẫn disabled |
| Production env + ADR chưa ACCEPTED | `enableAutopilot` `failedPrecondition` |
| Durable dispatch | control plane restart giữa chừng → event không mất, task re-dispatch |
| Resume after worker restart | run resume từ checkpoint, send đúng 1 lần (idempotency) |
| Containment dưới ngưỡng | threshold monitor auto-disable rule + `engagement.autopilot.disabled.v1` |
| Decision Request hết hạn (từ P0) | autopilot **không** execute dù từng approved |
| Proposal tạo Opportunity | autopilot **không** có capability đó → 0 write (static + runtime) |
| Delayed automation (P3) không bị autopilot bypass | re-check state/owner trước execute |

- [ ] **Step 1: Viết 2 file matrix.**
- [ ] **Step 2: Chạy** — `pytest tests/apps/cosa/ -k autopilot`; `cd services/company && npx vitest run commercial/tests/customer-engagement/`;
  `npx tsc --noEmit`; `pytest tests/apps/cosa/test_cosa_plane.py test_app_lifecycle.py`. Không hồi quy P0–P3.
- [ ] **Step 3: ADR** `ADR-ENGAGEMENT-AUTOPILOT-PROD-GATE.md` — `Status: PROPOSED`; 7 checkbox:
  (1) event consumer E2E staging, (2) durable dispatch via `scheduled_tasks`, (3) evidence re-check
  mandatory, (4) retry/DLQ + operator visibility, (5) observability histograms + dashboard,
  (6) resume-after-restart qua process thật, (7) containment/unsafe/policy-violation dưới ngưỡng ≥1 chu kỳ.
  Mỗi mục link bằng chứng (test id / drill log / dashboard). **Chỉ khi `Status: ACCEPTED` + 7 tick →
  `engagement.autopilot.enabled` được phép trên production** (guard Task 10 parse file này).
- [ ] **Step 4: Vocabulary** — autopilot run outcomes (`completed|handed_off|failed|cancelled`),
  `engagement.autopilot.{enabled,disabled}.v1`, template authorization, prod-gate.
- [ ] **Step 5: Commit** `test(engagement): P4 autopilot matrix + production gate ADR (7-point checklist)`.

---

## Self-Review

**Spec coverage:**
- §7.2 durable approval bind `(run_id, tool_call_id, checkpoint_ref)`, không token vĩnh viễn, re-check
  khi execute → Task 1 (capability REQUIRE_APPROVAL), Task 4 (checkpoint/suspend/resume + re-check).
- §8.3 mode 3 Autopilot (spec pin, eval evidence tươi, capability grant, rate limit, fallback/handoff,
  policy code) → Task 3 (spec pinned hẹp), Task 6 (evidence gate), Task 5 (`max_runs_per_aggregate_per_day`),
  Task 4 (handoff fallback), Task 8 (evidence re-check), Task 10 (feature flag / threshold).
- §8.4 `engagement.message.send` require approval trừ pre-authorize + kiểm takeover trước delivery →
  Task 1 + Task 10 (templates) + Task 4 (re-check ownership) + P0 relay.
- §13 P3 promotion gate → Task 6 (`can_enable_trigger`, write ⇒ evidence + human approval).
- §15: "Autopilot rule bị disable" → Task 4 guard + Task 10 kill switch + matrix; "Proposal tạo
  Opportunity" → Task 3 static (không có cap) + matrix; "Decision Request hết hạn" → P0 execution guard,
  autopilot không bypass (matrix).
- Overview Acceptance Gate P4 (7 điểm) → Task 7 (#2,#4), Task 8 (#3), Task 9 (#5), Task 11 (#1,#6),
  Task 10 threshold (#7), Task 12 ADR (tổng hợp + guard production).

**Gaps có chủ đích:**
- Chỉ 1 use case autopilot (FAQ theo template đã duyệt). Qualification form / các use case khác = thêm
  template + rule + eval, không đổi cấu trúc.
- Production **không** bật trong P4 — P4 kết thúc ở "sẵn sàng + ADR PROPOSED có bằng chứng". Việc flip
  `Status: ACCEPTED` là quyết định người, ngoài phạm vi code.
- `AutonomyLevel.L2_ACT` — xác nhận tên enum write-mode thật trong `agent_core.governance.contracts`
  (P0 finance dùng `L1_PROPOSE`); nếu khác, dùng đúng tên.
- Streaming từng token cho autopilot reply — không cần; `run.completed` + artifact đủ.
- Rate-limit theo provider (Zalo quota) khi autopilot gửi nhiều — thêm ở tuning sau nếu drill cho thấy cần.

**Placeholder scan:** không "TBD". `L2_ACT` enum + `engagement_autopilot_runs` bảng nhỏ cho metrics —
ghi rõ, không phải lỗ hổng. ADR bắt đầu `PROPOSED` là đúng vòng đời, không phải placeholder.

**Type consistency:** capability id (`engagement.message.send`, `engagement.assignment.write`) khớp
Task 1/2 ↔ `capability_refs` Task 3 ↔ `required_capabilities` rule Task 5 ↔ guard Task 4. `agent_profile
= "customer_support_autopilot"` khớp Task 3/4/5. `trigger_rule_id` payload khớp Task 4/5/10. Event
`engagement.autopilot.{enabled,disabled}.v1` khớp Task 6/10/12. ADR 7-point ↔ Acceptance Gate overview ↔
Task 12 checklist ↔ Task 10 guard.

---

## Kết thúc chuỗi plan

P0–P4 đã có plan chi tiết. Sau P4 landed + ADR `ACCEPTED`: production rollout autopilot là quyết định
vận hành theo `docs/architecture/adr/ADR-ENGAGEMENT-AUTOPILOT-PROD-GATE.md`, không cần plan code mới.
Mở rộng (thêm kênh — P2 pattern; thêm use case autopilot — P4 pattern; customer-success workflows —
spec §12/§13 P4) đi theo cùng khuôn: spec → plan phase → thực thi.
