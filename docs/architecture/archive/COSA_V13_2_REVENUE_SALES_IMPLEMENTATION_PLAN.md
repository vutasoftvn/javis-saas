# COSA V13.2 — Revenue & Sales Operating System: P0 Implementation Plan

## Context

`COSA_V13_2_Revenue_Sales_Operating_System_Integration.md` (repo root) is a 3037-line
spec, not yet implemented — it describes upgrading the existing Sales Function into a
full Revenue Operating System (Account/Contact/Lead/Opportunity/Customer, funnel,
forecasting, Customer Success, outreach automation), reusing the V13.1 Company Runtime
instead of building a second engine.

Current backend Sales (`backend/app/modules/sales/`) is a stub: one `SalesLead` model
(name, company, stage, value, owner_id) and two endpoints (`GET/POST /leads`), gated by
`FLAG_SALES_FUNCTION_V13`. Everything the spec asks for — Account, Contact, Opportunity,
Customer, Activity, qualification, funnel metrics, cross-function handoffs — is missing.

V13.1 (Company Runtime: WorkItem-equivalent, Handoff, Blocker, Needs You, Review,
Checkpoint) is fully implemented and battle-tested (`backend/app/modules/company_runtime/`,
shipped commit `0bfb0ac`). The spec's own rule is "reuse WorkItem/Handoff/Blocker/Needs
You/Learning, never create a second runtime" (§106.3-4) — so this plan wires Sales into
that existing runtime rather than inventing new orchestration.

The spec's literal proposals (`app/functions/sales/{domain,application,api}`,
`WorkItem`, `Cycle Grant`, a `PolicyEngine`, `linked_kr_id` columns) don't match what
actually exists in this repo and must be translated:

| Spec term | What this repo actually has |
|---|---|
| `WorkItem` | `Task` (execution state) + `Outcome` (result contract), joined by `outcomes.task_id` — no `WorkItem` table (ADR-V13-1-001) |
| `app/functions/sales/` | Flat sibling module `backend/app/modules/sales/`, same shape as `finance/`/`marketing/` (ADR-V13-003) |
| `Cycle Grant` | **Not implemented.** `FLAG_CYCLE_GRANTS_V13_1` is a reserved P1 flag with zero code behind it — cannot be relied on |
| `Policy Engine` | **Doesn't exist as one module.** Approvals are composed per-module today: `WorkReview` (company_runtime), `PendingApproval` (marketing) — Sales should follow the same composition, not invent a "Sales Policy Engine" |
| `linked_kr_id` field | Generic `OkrLink` polymorphic table (`strategy/models.py`) already used by `WorkContractService` for Outcome↔KeyResult — reuse it instead of a dedicated FK |
| Sales Lead Agent (persistent agent) | No persistent-agent/orchestration framework exists anywhere in the repo (only `finance/agent/finance_agent_service.py`, a single deterministic-service-plus-LLM-summary pattern). P0 follows that same pattern; the fuller "persistent Lead + ephemeral specialists" architecture depends on `ExecutorResolver`/`ephemeral_specialist_v13_1`, unimplemented V13.1 P1 flags — out of scope here |
| Finance invoice/receivable/pricing | **Doesn't exist.** Finance (`finance/models.py`) is TT58 Vietnamese-accounting-record focused (`AccountingDocument`, `FinancialTransaction`, `AccountingRecord`, `AccountingPeriod`) — no invoice/receivable/pricing entity. Sales→Finance handoff fires; actual receivable bookkeeping is a Finance-side gap, not built here |

This plan scopes the **full P0 vertical slice** (backend + Flutter + tests, one
flag-gated deliverable), matching how V13.1's own P0 shipped in a single reviewed
slice. P1–P3 (Prospecting Specialist, Lead scoring automation, Sequences/outreach,
Proposal workflow, LiveKit Sales voice, Customer Success automation, Forecast, Revenue
Health, SalesTargetCompiler) are explicitly deferred — the source doc itself mandates
"implement P0 before P1/P2/P3" (§106.28).

**Important nuance on "no second WorkItem engine":** Opportunity and Lead get their own
business-state machines (stage/qualification_status) in this plan. This is *not* a
second WorkItem engine — Task+Outcome remain the only execution/work-tracking primitive.
Opportunity stage is a commercial-entity state (like `Task.status` is an execution
state, or `Outcome.status` is a result state) — a new, narrow, domain-specific state
machine, exactly as `TaskStateService` is narrow to Task. No Sales work gets tracked
outside Task+Outcome; only the Account/Contact/Lead/Opportunity/Customer *data* gets
its own lifecycle fields.

## P0 scope (what ships)

Account, Contact, Lead (extended), Opportunity, Customer, Activity entities · lead
qualification · opportunity stage transitions incl. Won/Lost with structured reason ·
Sales Activity history · Marketing→Sales handoff (creates deduped Leads) · Sales→Finance
handoff on Won · Sales→Legal / Sales→Tech blockers · Needs You wiring for pricing/
proposal/contract decisions · deterministic Funnel metrics · Sales Today + Funnel +
Customer Flutter views, all behind new disabled-by-default flags.

---

## 1. Data model (additive only)

Extend `backend/app/modules/sales/models.py`. Snowflake PK via `generate_snowflake_id()`
(inline pattern, matching the file today), `workspace_id` FK indexed for tenancy, string
columns for state (no DB enum types — matches `Blocker.blocker_type`/`Task.status`).

### `accounts` (new)
| column | type | notes |
|---|---|---|
| id | BigInteger PK | snowflake |
| workspace_id | FK workspaces.id | indexed |
| name | String(255) | required |
| domain | String(255) nullable | **dedupe key**: unique per `(workspace_id, domain)` where domain is not null |
| industry, size_segment, country | String nullable | |
| source | String(100) nullable | e.g. `marketing_campaign`, `manual`, `referral` |
| lifecycle_status | String(30), default `TARGET` | TARGET / PROSPECT / CUSTOMER / FORMER_CUSTOMER / PARTNER / DISQUALIFIED |
| owner_id | FK users.id nullable | |
| tags | JSONB nullable | |
| created_at, updated_at | DateTime | |

### `contacts` (new)
| column | type | notes |
|---|---|---|
| id, workspace_id | as above | |
| account_id | FK accounts.id nullable | |
| name | String(255) required | |
| title, phone | String nullable | |
| email | String(255) nullable | **dedupe key**: unique per `(workspace_id, email)` where email is not null |
| source | String(100) nullable | |
| consent_status | String(30) nullable | e.g. `UNKNOWN`/`OPTED_IN`/`OPTED_OUT` |
| do_not_contact | Boolean default false | |
| owner_id | FK users.id nullable | |
| created_at, updated_at | DateTime | |

### `sales_leads` (extend existing table — additive columns only, no rename/drop)
Existing columns kept as-is: `id, workspace_id, key_result_id, name, company, stage,
value, owner_id, created_at`.

New nullable columns:
| column | type | notes |
|---|---|---|
| account_id | FK accounts.id nullable | |
| contact_id | FK contacts.id nullable | **dedupe key** for handoff intake: skip insert if `(workspace_id, contact_id)` already has a non-`DISQUALIFIED`/`CONVERTED` lead |
| source | String(100) nullable | |
| source_campaign_id | FK marketing_campaigns.id nullable | |
| fit_score, intent_score, engagement_score | Float nullable | 0-100, three separate scores per §10 — never collapse into one number |
| qualification_status | String(30) nullable | QUALIFIED / DISQUALIFIED / NEEDS_DISCOVERY — output of `QualificationService`, distinct from `stage` |
| disqualification_reason | Text nullable | |
| next_action_at | DateTime nullable | |
| next_action_type | String(50) nullable | |
| updated_at | DateTime | (existing table has no updated_at — add it) |

`stage` keeps its existing free-string column but the service layer now validates it
against: `NEW, RESEARCHING, QUALIFYING, QUALIFIED, NURTURING, DISQUALIFIED, CONVERTED`
(§14) — a superset of today's implicit default `NEW`. This is the Lead's *lifecycle*
state; `qualification_status` is the *qualification result* (§9) — two different axes,
kept as two columns to match the spec's own distinction.

### `sales_opportunities` (new)
| column | type | notes |
|---|---|---|
| id, workspace_id | as above | |
| account_id | FK accounts.id required | |
| primary_contact_id | FK contacts.id nullable | |
| owner_id | FK users.id nullable | |
| source_lead_id | FK sales_leads.id nullable | set by the `/leads/{id}/convert` endpoint |
| product | String(255) nullable | |
| stage | String(30) default `DISCOVERY` | see state machine below |
| estimated_value | Float nullable | |
| currency | String(10) default `VND` | |
| probability | Float nullable | stage-default unless overridden; see Funnel section |
| expected_close_date | Date nullable | |
| pain_points, needs, objections, competitors | JSONB nullable | lists |
| next_action, next_action_due_at | String/DateTime nullable | |
| won_reason | String(30) nullable | required when stage→WON |
| lost_reason | String(30) nullable | required when stage→LOST; one of PRICE/NO_NEED/NO_BUDGET/TIMING/COMPETITOR/TRUST/FEATURE_GAP/NO_RESPONSE/LEGAL/TECHNICAL/OTHER (§46) |
| lost_reason_detail | Text nullable | free-text evidence alongside the structured reason (§46 "store both") |
| created_at, updated_at | DateTime | |

**Opportunity stage state machine** (service-layer guard in `domain/opportunities.py`,
same allow-list style as `TaskStateService.LEGAL_TRANSITIONS` but a separate class —
do not reuse `TaskStateService` itself, Opportunity is not a Task):

```
DISCOVERY   → QUALIFIED, LOST
QUALIFIED   → SOLUTION, LOST
SOLUTION    → PROPOSAL, LOST
PROPOSAL    → NEGOTIATION, LOST
NEGOTIATION → WON, LOST
WON         → (terminal)
LOST        → (terminal)
```
Forward-only plus LOST-from-anywhere-before-WON. No backward transition in P0 (spec
doesn't require it; keep it simple — §16 "do not overload funnel with too many custom
stages"). `WON` requires `won_reason` non-null; `LOST` requires `lost_reason` non-null —
enforced in the endpoint, not the DB.

### `sales_activities` (new)
| column | type | notes |
|---|---|---|
| id, workspace_id | as above | |
| entity_type | String(20) | `account`/`contact`/`lead`/`opportunity`/`customer` |
| entity_id | BigInteger | polymorphic target, no FK constraint (matches `Blocker`'s style of optional pointers) |
| activity_type | String(30) | RESEARCH/EMAIL/MESSAGE/CALL/MEETING/DEMO/PROPOSAL/FOLLOW_UP/NOTE/STATUS_CHANGE |
| channel, direction | String nullable | |
| summary | Text | |
| outcome, next_action | Text nullable | |
| actor_id | FK users.id nullable | |
| occurred_at | DateTime default now | |
| artifact_refs | JSONB nullable | |

A `STATUS_CHANGE` activity row is written automatically by the stage-transition and
qualification services (not just user-authored notes) — this is what makes §68's
"Activity Timeline" show stage changes without relying on chat history (§68 explicit
rule).

### `customers` (new)
| column | type | notes |
|---|---|---|
| id, workspace_id | as above | |
| account_id | FK accounts.id required, unique per workspace | one Customer row per Account |
| acquired_from_opportunity_id | FK sales_opportunities.id nullable | |
| lifecycle_status | String(30) default `ONBOARDING` | ONBOARDING/ACTIVE/WATCH/AT_RISK/CHURNED/EXPANSION |
| activation_status | String(30) nullable | |
| owner_id | FK users.id nullable | |
| first_purchase_at | DateTime nullable | |
| renewal_date | Date nullable | |
| health_status | String(20) default `HEALTHY` | HEALTHY/WATCH/AT_RISK — manually set in P0 (no `CustomerHealthService` yet, that's P2) |
| last_success_interaction_at, next_success_action_at | DateTime nullable | |
| created_at, updated_at | DateTime | |

---

## 2. Backend structure

Extend the existing flat module (mirrors `finance/`'s domain+routers shape, not the
spec's literal `app/functions/sales/`):

```
backend/app/modules/sales/
  models.py                        (extend, see §1)
  domain/
    accounts.py       # create/get/list, domain dedupe by (workspace_id, domain)
    contacts.py        # create/get/list, dedupe by (workspace_id, email)
    leads.py            # create, qualify, convert, from-handoff intake, dedupe
    opportunities.py    # create, stage transition guard, win, lose
    customers.py        # get/list, health update
    activities.py       # create/list, auto-write STATUS_CHANGE entries
    qualification.py    # QualificationService: FIT/NEED/URGENCY/AUTHORITY/ABILITY_TO_PAY -> QUALIFIED/DISQUALIFIED/NEEDS_DISCOVERY
    funnel.py            # FunnelMetricsService: deterministic aggregation only
  routers/
    accounts_router.py
    contacts_router.py
    leads_router.py
    opportunities_router.py
    customers_router.py
    activities_router.py
    funnel_router.py
  router.py                        (aggregates sub-routers; already mounted at
                                     /api/v1/sales in app/main.py — extend, don't remount)
```

### API sketch (P0 only — forecast/next-actions/stalled/targets/prospect/sequence/
proposal/success-action endpoints from spec §79-80 are explicitly deferred to P1+)

```
POST   /sales/accounts
GET    /sales/accounts
GET    /sales/accounts/{id}

POST   /sales/contacts
GET    /sales/contacts
GET    /sales/contacts/{id}

GET    /sales/leads                          (existing, response gains new fields)
POST   /sales/leads                          (existing, unchanged)
POST   /sales/leads/from-handoff/{handoff_id} (new — Marketing intake, see §3)
POST   /sales/leads/{id}/qualify              (new — runs QualificationService)
POST   /sales/leads/{id}/convert              (new — creates Opportunity, stage->CONVERTED)

POST   /sales/opportunities
GET    /sales/opportunities
GET    /sales/opportunities/{id}
POST   /sales/opportunities/{id}/stage        (body: {target_stage})
POST   /sales/opportunities/{id}/win           (body: {won_reason, evidence})
POST   /sales/opportunities/{id}/lose          (body: {lost_reason, detail})

GET    /sales/customers
GET    /sales/customers/{id}

POST   /sales/activities
GET    /sales/activities?entity_type=&entity_id=

GET    /sales/funnel                          (FunnelMetricsService output)
```

Every mutating endpoint takes the existing `_guard(workspace_id, member, db)` pattern
from today's `sales/router.py`, gated by the new `_V13_2` flags (§5). The two
pre-existing `/leads` endpoints stop being gated by `FLAG_SALES_FUNCTION_V13` alone —
`_guard` now requires **both** `FLAG_SALES_FUNCTION_V13` (nav/tab visibility, matches
the same master-flag pattern Legal/Marketing/Tech/Finance already use) **and**
`FLAG_LEAD_MANAGEMENT_V13_2` (the capability itself), nested exactly like V13.1's
`company_runtime_v13_1` master flag nests its twelve P0 sub-flags. This closes the gap
where the base list/create endpoints and the new qualify/convert/from-handoff endpoints
could otherwise be toggled independently and land in an inconsistent combination.

### Deterministic services — no LLM arithmetic (spec rule §106.17-18)

- **`QualificationService.qualify(fit, need, urgency, authority, ability_to_pay)`** —
  pure rule evaluation (all five present and above threshold → QUALIFIED; any hard-fail
  like `ability_to_pay=NO` → DISQUALIFIED; missing dimensions → NEEDS_DISCOVERY),
  returns `qualification_status` + writes a `STATUS_CHANGE` Activity.
- **`FunnelMetricsService`** — mirrors `finance/domain/management_metrics_service.py`'s
  style (pure SQL aggregation, no model call):
  - `lead_to_qualified_rate`, `qualified_to_opportunity_rate`,
    `opportunity_to_won_rate` — count ratios over a date window
  - `pipeline_value` = `SUM(estimated_value)` over open (non-WON/LOST) Opportunities
  - `weighted_pipeline` = `SUM(estimated_value * probability)`, where `probability`
    falls back to a stage-default table when not manually set:
    `{DISCOVERY: 0.1, QUALIFIED: 0.25, SOLUTION: 0.4, PROPOSAL: 0.6, NEGOTIATION: 0.8}`
    — and the response includes a `probability_source` field per opportunity
    (`manual`/`stage-default`), per §53's explicit requirement never to silently blend
    the two.
- **Stage-transition guard** (`domain/opportunities.py`) — allow-list table from §1,
  raises on illegal transition, exactly like `TaskStateService.can_transition` but a
  separate, Opportunity-scoped class.

No persistent-agent framework is built. An optional `sales/agent/sales_agent_service.py`
(LLM summary over `FunnelMetricsService` output, modeled on
`finance/agent/finance_agent_service.py`) may be added if time allows — **not required**
for P0 acceptance (§106.9 in the checklist below is marked deferred, not blocking).

---

## 3. Company Runtime integration (reuse, don't reimplement)

### Marketing → Sales handoff (spec §21, §96)
1. Marketing creates a `Handoff` via the existing
   `HandoffService.create_handoff(from_function="MARKETING", to_function="SALES",
   handoff_type="HANDOFF_TO_NEXT_FUNCTION", artifact_refs=[{name, email, company,
   source_campaign_id, fit_reason}, ...])` — no new code needed in
   `company_runtime/handoff_service.py`, this call already works today.
2. New `POST /sales/leads/from-handoff/{handoff_id}`:
   - loads the `Handoff`, reads `artifact_refs`
   - for each item: find-or-create `Contact` by `(workspace_id, email)`, find-or-create
     `Account` by `(workspace_id, domain-derived-from-email-or-company)`, then
     find-or-create `Lead` by `(workspace_id, contact_id)` — **skip creating a
     duplicate Lead** if an open (non-DISQUALIFIED/CONVERTED) Lead already exists for
     that contact
   - calls `HandoffService.accept_handoff(handoff_id)` (existing method, unchanged)
   - writes one `STATUS_CHANGE` Activity per created Lead
   - returns `{leads_created: [...], leads_deduped: [...]}`

### Sales → Finance (on WON, spec §35, §39)
`POST /sales/opportunities/{id}/win`:
1. Validates stage-transition guard, requires `won_reason`
2. Sets `stage=WON`
3. Creates/updates the `Customer` row (`lifecycle_status=ONBOARDING`,
   `acquired_from_opportunity_id=opportunity.id`, `first_purchase_at=now`)
4. Calls `HandoffService.create_handoff(from_function="SALES", to_function="FINANCE",
   handoff_type="HANDOFF_TO_NEXT_FUNCTION", requested_action="Record receivable for
   won deal", artifact_refs=[{opportunity_id, estimated_value, currency, account_id}])`
   — satisfies acceptance criterion §102.15. **Does not** attempt to write a
   receivable/invoice record — Finance has no such entity (see Context table); this is
   a documented Finance-side gap, not built in this plan.
5. Writes a generic `Lesson` (`function="SALES"`, `observation` templated from
   `won_reason`) — reuses `learning/models.py::Lesson`, per spec §49's explicit "reuse
   generic Lesson" instruction; do not clone `MarketingLearning`.

### Sales → Legal / Sales → Tech (spec §37-38, §72)
New `Blocker.blocker_type` string values (additive — `blocker_type` is a free string
column, no migration needed): `LEGAL_REVIEW`, `TECHNICAL_QUESTION`, `PRODUCT_GAP`,
`PRICING_NEEDED`, `DISCOUNT_APPROVAL`, `PAYMENT_ISSUE`.

Extend `BlockerRouter.route_blocker_function`'s direct-mapping dict in
`company_runtime/blocker_router.py::route_blocker_function` (currently maps
`FINANCE_EXCEPTION`/`MISSING_DOCUMENT`→FINANCE, `LEGAL_UNCERTAINTY`→LEGAL,
`TECHNICAL_BLOCK`→TECH) by adding:
```
LEGAL_REVIEW      -> LEGAL
TECHNICAL_QUESTION -> TECH
PRODUCT_GAP        -> TECH
PRICING_NEEDED     -> FINANCE
DISCOUNT_APPROVAL  -> FINANCE
PAYMENT_ISSUE      -> FINANCE
```
`BUDGET_UNKNOWN`, `DECISION_MAKER_UNKNOWN`, `CUSTOMER_TIMING` (spec §72) stay
self-serve within Sales in P0 — they don't need cross-function routing, so they are not
added to the router map; Sales domain code can create them as plain informational
Activities instead of Blockers if no routing is needed.

Sales domain code calls `BlockerRouter.create_blocker(db, workspace_id, blocker_type=...,
description=..., task_id=None, outcome_id=None, ...)` — `task_id`/`outcome_id` stay
`None` since Opportunities aren't Tasks; the Blocker just carries `assigned_function`.

### Needs You (spec §31, §73)
No new code in `company_runtime/` — `BlockerRouter.create_blocker` already escalates to
`NeedsYouItem` automatically when `assigned_function is None` or `blocker_type` is
founder-level. Sales domain code creates founder-level blockers directly for:
`PRICING_DECISION`, `DISCOUNT_EXCEPTION`, `STRATEGIC_CUSTOMER`, `PROPOSAL_APPROVAL`,
`CONTRACT_DECISION`, `PRODUCT_COMMITMENT`, `NEGOTIATION_DECISION`,
`CUSTOMER_ESCALATION` — pass `blocker_type="FOUNDER_DECISION"` (existing enum value)
and put the specific reason in `description`, exactly as `Blocker.blocker_type` already
supports.

### KR linkage (spec §15 `linked_kr_id`)
Reuse `OkrLink` (`strategy/models.py`) exactly as `WorkContractService.set_work_contract`
does for Outcomes: `OkrLink(from_entity_type="opportunity", from_entity_id=opp.id,
to_entity_type="key_result", to_entity_id=kr_id, relation_type="supports")`. No new FK
column on `sales_opportunities`.

Note: `sales_leads.key_result_id` (a direct FK, the older V13 pattern) already exists in
production schema from `v13_004_legal_sales_tables` and is kept as-is — dropping it
would violate the additive/no-drop rule and spec §106.24 ("preserve existing Sales data
where possible"). This is a deliberate, documented exception: Lead keeps its existing
direct FK, Opportunity (a new entity with no legacy baggage) uses the newer `OkrLink`
pattern going forward. Do not retrofit `sales_leads.key_result_id` into `OkrLink` rows
in this plan — that's a separate, optional cleanup with no functional benefit here.

---

## 4. Feature flags

Add to `backend/app/core/feature_flags.py`, following the existing `_V13_1` grouping
pattern:

```python
FLAG_SALES_CRM_CORE_V13_2 = "sales_crm_core_v13_2"                 # accounts/contacts CRUD
FLAG_ACCOUNT_CONTACT_V13_2 = "account_contact_v13_2"                 # (kept distinct per spec §81 naming)
FLAG_LEAD_MANAGEMENT_V13_2 = "lead_management_v13_2"                 # qualify/convert/from-handoff
FLAG_OPPORTUNITY_MANAGEMENT_V13_2 = "opportunity_management_v13_2"   # stage/win/lose
FLAG_CUSTOMER_CORE_V13_2 = "customer_core_v13_2"                     # customers read endpoints
FLAG_MARKETING_SALES_HANDOFF_V13_2 = "marketing_sales_handoff_v13_2" # from-handoff intake
FLAG_SALES_FINANCE_HANDOFF_V13_2 = "sales_finance_handoff_v13_2"     # win -> Finance handoff
FLAG_SALES_LEGAL_HANDOFF_V13_2 = "sales_legal_handoff_v13_2"         # LEGAL_REVIEW blocker
FLAG_SALES_TECH_HANDOFF_V13_2 = "sales_tech_handoff_v13_2"           # TECHNICAL_QUESTION/PRODUCT_GAP blocker

V13_2_P0_FLAGS = frozenset({
    FLAG_SALES_CRM_CORE_V13_2, FLAG_ACCOUNT_CONTACT_V13_2, FLAG_LEAD_MANAGEMENT_V13_2,
    FLAG_OPPORTUNITY_MANAGEMENT_V13_2, FLAG_CUSTOMER_CORE_V13_2,
    FLAG_MARKETING_SALES_HANDOFF_V13_2, FLAG_SALES_FINANCE_HANDOFF_V13_2,
    FLAG_SALES_LEGAL_HANDOFF_V13_2, FLAG_SALES_TECH_HANDOFF_V13_2,
})
```

Do **not** add flags for P1-P3 items (`prospecting_agent_v13_2`,
`outreach_sequence_v13_2`, `customer_success_v13_2`, `sales_forecast_v13_2`,
`revenue_health_v13_2`, `sales_voice_copilot_v13_2`, `customer_facing_ai_calls`,
`autonomous_cold_outreach`) — ADR-V13-1-008 is "no flags without code," and none of
that code ships in this slice.

`FLAG_SALES_FUNCTION_V13` is **not** retired — it's the same master nav-visibility flag
Legal/Marketing/Tech/Finance already use (`V13_FEATURE_FLAGS` in
`feature_flags.py:67`), and the Flutter nav item
(`dashboard_view.dart:114`, `flagKey: 'sales_function_v13'`) still needs it to decide
whether the Sales tab shows at all. What changes is that the two pre-existing `/leads`
endpoints move from being gated by that flag *alone* to requiring it *plus*
`FLAG_LEAD_MANAGEMENT_V13_2` (§2) — no endpoint is left half-migrated onto only the old
flag while its sibling endpoints run on the new scheme.

---

## 5. Migrations

Continue the chain from `v13_013_runtime_flag_defaults`:

- **`v13_014_sales_crm_core.py`** — `op.create_table` for `accounts`, `contacts`,
  `sales_opportunities`, `sales_activities`, `customers` (per §1's column tables);
  `op.add_column` for the nine new nullable columns + `updated_at` on `sales_leads`;
  unique indexes: `uq_accounts_workspace_domain` (partial, `WHERE domain IS NOT NULL`),
  `uq_contacts_workspace_email` (partial, `WHERE email IS NOT NULL`),
  `uq_customers_workspace_account`.
- **`v13_015_sales_crm_flags.py`** — insert-only, seeds the nine `V13_2_P0_FLAGS` at
  `enabled=false, workspace_id=NULL, description='COSA V13.2 Revenue OS default'`
  (mirrors `v13_012`).
- **`v13_016_sales_crm_flag_defaults.py`** — scoped `UPDATE ... WHERE workspace_id IS
  NULL AND description = 'COSA V13.2 Revenue OS default'` flipping only those
  self-seeded rows to `true` (mirrors `v13_013`'s gate discipline exactly, including an
  intentionally empty `downgrade()`). **Run only after** golden scenarios pass by hand
  against one Developer Workspace — same rollout rule V13.1 used; to stop before the
  gate, run `alembic upgrade v13_015_sales_crm_flags` instead of `head`.

---

## 6. Frontend (Flutter)

Extend `frontend/lib/modules/sales/` (current: `sales_view.dart` (view) +
`sales_controller.dart` (11 lines, GetX) + `sales_binding.dart`, backed by
`data/services/sales_service.dart`) — not `lib/features/ai_team/sales/` as the spec
literally names it. Use `modules/marketing/` (tabs, KPI header, campaign dialogs) as the
UI reference since it's the most developed Function UI in the app today.

| File | Content |
|---|---|
| `controllers/sales_today_controller.dart` | loads Needs You count (existing `/needs-you` endpoint filtered client-side or by function), static Next-Best-Action list (no `SalesNextBestActionService` in P0 — hand-rolled from open Opportunities' `next_action`/`next_action_due_at`), pipeline snapshot from `/sales/funnel`, at-risk Opportunity count |
| `views/sales_today_view.dart` | mirrors spec §64's mock: Needs You badge, Next Actions list, Pipeline number, At Risk count |
| `controllers/funnel_controller.dart` | loads `/sales/opportunities` grouped by stage |
| `views/funnel_view.dart` | Kanban columns LEADS/QUALIFIED/OPPORTUNITY/PROPOSAL/WON; drag-to-change-stage calls `POST /sales/opportunities/{id}/stage` through the controller — **not** local-state-only, per §65's explicit rule that stage transitions must call the domain service |
| `views/opportunity_detail_view.dart` | Account/Contact, stage, pain points/objections, Activity timeline (from `/sales/activities`), Win/Lose action buttons (Lose requires picking a `lost_reason` from the fixed list) |
| `views/customer_view.dart` | Customer list + detail: lifecycle_status, health_status, renewal_date, last interaction |
| `data/services/sales_service.dart` | extend with the new endpoint calls from §2's API sketch |

---

## 7. ADRs to add (`docs/adr/`, following existing numbering)

- `ADR-V13-2-001` — WorkItem reuse = Task+Outcome (same decision as V13.1, restated for Sales; clarifies Opportunity/Lead state machines are domain state, not a second WorkItem engine)
- `ADR-V13-2-002` — Sales module stays a flat sibling under `app/modules/`, not `app/functions/`
- `ADR-V13-2-003` — Account/Contact/Lead/Opportunity/Customer model, with dedupe keys
- `ADR-V13-2-004` — Cycle Grant unavailable in this repo; Sales automation stays founder-approval-gated in P0
- `ADR-V13-2-005` — KR linkage via existing `OkrLink`, no new FK column
- `ADR-V13-2-006` — Sales→Finance handoff fires; receivable/invoice bookkeeping is a Finance-side gap, not built here

---

## 8. Implementation order

1. **Data model** — `models.py` additions, `v13_014_sales_crm_core.py`, run migration
   locally, confirm no `DuplicateTable`/FK errors against a throwaway DB.
2. **CRUD domain + routers** — accounts, contacts, activities (simplest, no state
   machine) end to end, including flag gating.
3. **Qualification + Opportunity state machine** — `qualification.py`, `opportunities.py`
   stage guard, `leads_router.py` qualify/convert, `opportunities_router.py`
   stage/win/lose. Unit-test the transition table exhaustively (legal and illegal
   transitions) before wiring HTTP.
4. **Funnel** — `FunnelMetricsService`, `funnel_router.py`; unit-test the arithmetic
   against hand-computed fixtures.
5. **Company Runtime integration** — handoff intake endpoint, blocker_type additions +
   `BlockerRouter` map extension, Finance handoff on win, `OkrLink` write, `Lesson`
   write. This is where most cross-module risk lives — write the golden-scenario tests
   (§10) alongside this step, not after.
6. **Flags + gate migrations** — add the nine flags, `v13_015`/`v13_016`, keep the gate
   migration un-run until step 8 passes.
7. **Flutter** — Sales Today, Funnel, Opportunity detail, Customer views; wire to the
   now-working API.
8. **Golden-scenario manual pass** in one Developer Workspace, then run
   `v13_016_sales_crm_flag_defaults` to flip flags on.
9. **DEPLOYMENT.md** update (new "COSA V13.2 — Revenue & Sales" section, same style as
   the existing V13/V13.1 sections) — required by CLAUDE.md whenever the runtime
   boundary or startup sequence changes.

---

## 9. P0 acceptance criteria (translated from spec §102, all 20 items)

| # | Criterion | How this plan satisfies it |
|---|---|---|
| 1 | Account/Contact/Lead/Opportunity/Customer are distinct entities | §1 — five distinct tables |
| 2 | Lead can be qualified/disqualified | `qualification_status` + `POST /leads/{id}/qualify` |
| 3 | Qualified Lead can convert to Opportunity | `POST /leads/{id}/convert` |
| 4 | Opportunity has validated stage transitions | allow-list guard in `domain/opportunities.py` |
| 5 | Opportunity can be WON or LOST | `/win`, `/lose` endpoints |
| 6 | Won/Lost reason is captured | `won_reason`/`lost_reason` required fields |
| 7 | Sales Activity history is visible | `sales_activities` table + `/activities` endpoint + auto `STATUS_CHANGE` writes |
| 8 | Next Action is stored | `next_action`/`next_action_due_at` on Lead and Opportunity |
| 9 | Sales Lead Agent can summarize funnel | **deferred, non-blocking** — optional `sales_agent_service.py` |
| 10 | Marketing can hand off leads to Sales | `/leads/from-handoff/{handoff_id}` + existing `HandoffService` |
| 11 | Sales can hand off pricing to Finance | `PRICING_NEEDED`/`DISCOUNT_APPROVAL` blockers → FINANCE |
| 12 | Sales can hand off legal issues to Legal | `LEGAL_REVIEW` blocker → LEGAL |
| 13 | Sales can hand off technical issues to Tech | `TECHNICAL_QUESTION`/`PRODUCT_GAP` blockers → TECH |
| 14 | WON creates Customer | step in `/opportunities/{id}/win` |
| 15 | WON can trigger Finance handoff | same endpoint, `HandoffService.create_handoff` |
| 16 | Sales state remains PostgreSQL source of truth | no agent-memory read path used anywhere in Sales |
| 17 | Finance remains source of actual economic truth | no revenue-recognition logic added to Sales; handoff only |
| 18 | Existing V13.1 Company Runtime is reused | Handoff/Blocker/NeedsYou/OkrLink/Lesson, zero new runtime primitives |
| 19 | No second WorkItem engine is created | Opportunity/Lead state machines are domain state, not execution state — see callout in §"P0 scope" |
| 20 | No autonomous spam workflow is enabled | no Sequence/outreach code ships; those flags stay unadded |

---

## 10. Golden scenario tests

New `backend/app/tests/sales/` module, mirroring `backend/app/tests/company_runtime/
test_golden_scenarios.py`'s MagicMock-DB style plus real fixtures where dedupe logic
needs a real query.

**Golden Scenario A — Marketing → Sales (spec §96)**
- *Given*: an active `MarketingCampaign`; Marketing calls
  `HandoffService.create_handoff(from_function="MARKETING", to_function="SALES",
  handoff_type="HANDOFF_TO_NEXT_FUNCTION")` with `artifact_refs` containing 10 contact
  payloads, one of which shares an email with an already-existing open Lead.
- *When*: `POST /sales/leads/from-handoff/{handoff_id}`.
- *Then*: exactly 9 new `Lead` rows are created (the 10th is deduped against the
  existing open Lead, not duplicated); each new Lead has `source_campaign_id` set and
  `stage=NEW`; the `Handoff.status` becomes `ACCEPTED`. Qualifying 4 of them with
  passing FIT/NEED/URGENCY/AUTHORITY/ABILITY_TO_PAY inputs sets
  `qualification_status=QUALIFIED`; converting 2 of the qualified Leads creates 2
  `Opportunity` rows in `stage=DISCOVERY` with `source_lead_id` set.

**Golden Scenario B — Won → Finance (spec §99)**
- *Given*: an `Opportunity` in `stage=NEGOTIATION` with `estimated_value=50_000_000`.
- *When*: `POST /sales/opportunities/{id}/win` with `won_reason="COMPETITOR_LOST"`.
- *Then*: `Opportunity.stage=WON`; a `Customer` row exists with
  `acquired_from_opportunity_id=opportunity.id` and `lifecycle_status=ONBOARDING`; a
  `Handoff(from_function=SALES, to_function=FINANCE)` exists with the opportunity's
  value in `artifact_refs`; no `Task`/`Outcome` row was created by this flow (confirms
  criterion #19 — this is a business-state transition, not Company Runtime work).

**Illegal transition test** — `POST /sales/opportunities/{id}/stage` with
`target_stage=WON` on an Opportunity currently in `DISCOVERY` returns an error and
leaves `stage` unchanged (transition table only allows `NEGOTIATION→WON`).

**Blocker routing test** — creating a Blocker with `blocker_type="LEGAL_REVIEW"` (no
explicit `assigned_function`) resolves to `assigned_function="LEGAL"` via
`BlockerRouter.route_blocker_function`; same for `TECHNICAL_QUESTION`→`TECH` and
`PRICING_NEEDED`→`FINANCE`.

**Funnel arithmetic test** — fixed fixture (10 leads, 4 qualified, 2 opportunities, 1
won at 50_000_000 with 0.8 probability) produces exact expected
`lead_to_qualified_rate=0.4`, `weighted_pipeline` computed by hand and asserted equal —
no LLM call anywhere in this test.

---

## 11. Verification

- `backend/app/tests/sales/` — unit tests per §10 plus qualification-service edge cases
  (missing dimension → NEEDS_DISCOVERY, hard-fail ability_to_pay → DISQUALIFIED).
- `RUN_DB_INTEGRATION=1 DATABASE_URL=... PYTHONPATH=backend .venv/bin/pytest` pass
  against a real Postgres after migrations, same invocation documented in
  `DEPLOYMENT.md`, extended to touch the new sales tables (confirms the unique partial
  indexes on `accounts.domain`/`contacts.email` actually dedupe at the DB level, not
  just in application code).
- `flutter analyze` clean; widget test for the Funnel view's stage-drag → API call
  (verify it calls the controller method, not just mutates local list state).
- Manual golden-scenario pass (§10, by hand, one Developer Workspace) **before**
  running `v13_016_sales_crm_flag_defaults`.
- Update `DEPLOYMENT.md` per §8 step 9.
