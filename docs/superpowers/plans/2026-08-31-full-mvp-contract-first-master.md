# Full MVP Contract-First Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver every enabled Dashboard/Hub capability through an owned, tenant-authorized backend contract and truthful Flutter experience, without runtime mock or fabricated data.

**Architecture:** The programme replaces visible legacy client calls with six canonical vertical slices. A shared contract spine makes route ownership, schemas, data provenance and failure semantics machine-checkable; Company owns business/commercial data, Agent Platform owns workforce/knowledge data, and Control Plane owns membership, connectors and runtime-node state. Each vertical slice is complete only after durable storage/provider access, authorization, typed Flutter behavior and real-service integration proof.

**Tech Stack:** Flutter/Dart with GetX and `http`; TypeScript/Encore with Drizzle/PostgreSQL; Python/FastAPI/Pydantic with PostgreSQL/object store; Vitest, pytest and Flutter test; repository scripts and Make targets.

**Spec:** `docs/superpowers/specs/2026-08-31-full-mvp-contract-first-truth-only-design.md`

## Global Constraints

- Production and ordinary development runtime may read only declared Company/Agent/Control Plane storage or a configured external connector. It must not create demo, placeholder, default customer, synthetic-metric, fake-health or fake-provider records.
- A successful read has only `populated` or `empty` data state. Authentication, authorization, connection, provider, validation, conflict and server failures remain typed failures; they may not become `[]`, `{}`, `null`, `false`, zero metrics, `healthy`, `connected`, or success.
- Fixtures, fake providers and mock transports live only in test execution. A mocked unit test cannot satisfy an API capability's integration requirement.
- Every tenant-owned route derives actor/workspace authorization on the server. Browser-supplied IDs cannot grant access. Snowflake IDs remain strings at JSON/Dart boundaries; do not cast them through JavaScript/Dart `number`/`double`.
- Migrations are additive, immutable once applied, indexed by `workspace_id`, and include a reviewed down migration. Backfill only exact, source-proven values; otherwise preserve records and report them for manual action.
- Do not add a writable Company mirror of Agent Platform agents, runs, approvals, documents or skills. Workspace Runtime may hold only an immutable source projection and a user-specific snooze overlay.
- All enabled routes must appear in `shared/contracts/mvp-surface.json`, be validated by `scripts/mvp_surface_check.py`, and update generated inventory artefacts in the same commit.
- Existing system-owned catalog/policy records are permitted only when versioned and explicitly labelled. They are not workspace activity or customer data.
- Do not claim WAF/rate limiting, staging success, production deployment or a working third-party connector without recorded verification in the authorized environment.

---

## Programme map and dependency order

| Order | Plan | Delivers | Depends on | Can enable visible routes when |
|---|---|---|---|---|
| 1 | `2026-08-31-full-mvp-foundation.md` | Contract manifest, result/error envelope, route parity, fixture isolation and Flutter typed transport | Approved spec | Each migrated client preserves failures and manifest check passes |
| 2 | `2026-08-31-full-mvp-strategy-runtime.md` | Strategy canvas/revisions, complete list/read contracts, Workspace Runtime projection and UI | Foundation | Strategy/Runtime reads and actions resolve to Company source records |
| 3 | `2026-08-31-full-mvp-workforce.md` | Durable workforce assignments, Agent Platform roster/runs/approvals/health and runtime signals | Foundation | Workforce UI observes real registry/assignment/run data |
| 4 | `2026-08-31-full-mvp-vault-knowledge.md` | Agent-owned Vault document/index/retrieval contracts and Flutter states | Foundation; existing M3 primitives | Vault records derive from object/knowledge stores and preserve workspace isolation |
| 5 | `2026-08-31-full-mvp-marketing.md` | Commercial objectives/campaigns/assets/experiments/metrics and provenance UI | Foundation; Strategy project references | Marketing values are persisted or connector-observed, never inferred placeholders |
| 6 | `2026-08-31-full-mvp-settings-release.md` | Platform settings/connector/runtime-node UI, migration rehearsal, E2E and release evidence | Foundation for Task 3 harness; Plans 1–5 for remaining tasks | Zero enabled MVP ghosts, full integration evidence, and truthful release status |

The six plans are intentionally separate review units. Execute **Settings/Release Task 3 (the real cross-plane test harness)** immediately after Foundation Tasks 1–5 and before the integration task in any domain plan; it is a test-support prerequisite, not a reason to expose the Settings UI early. Execute the remaining Settings/Release tasks after the domain slices. Do not begin a later plan's UI migration until its source owner and manifest route are available. Work that changes a shared file is serialized through the Foundation plan; independent service work may proceed in parallel only after its foundation interfaces land.

## Canonical route families

The exact capability IDs and schemas live in the Foundation manifest. These route families are fixed for the MVP and replace the legacy forms named below.

| Surface | Canonical family | Owner | Replaces |
|---|---|---|---|
| Strategy canvases/revisions | `/operations/strategy/canvases/*`, `/operations/strategy/canvas-revisions/*` | Company Operations | `/strategy/canvases/*`, `/strategy/revisions/*` |
| Strategy execution/OKR/12-week | `/operations/projects*`, `/operations/okr-cycles*`, `/operations/objectives*`, `/operations/twelve-week-*` | Company Operations | partial `/strategy/*` and default workspace/id fallbacks |
| Workspace Runtime | `/operations/workspace-runtime/*` | Company Operations projection | `/company-runtime/*`, `/agents/execution/*` |
| Workforce | `/agent/workforce/*`, existing `/agent/runs/*`, `/agent/approvals/*` | Agent Platform | `/workforce/*`, `/agents/*` |
| Vault/knowledge | `/agent/vault/*`, existing `/agent/knowledge/*` | Agent Platform | `/vault/*` |
| Marketing | `/commercial/marketing/*`, `/commercial/marketing-context/*` | Company Commercial | `/marketing/*` |
| Settings: connector/member/node | `/platform/workspaces/:workspaceId/*` and existing worker-only `/cosa/*` internals | Control Plane | `/connectors/*`, `/devices/*`, `/admin/*` |

Internal worker routes remain under `/cosa/*` and are never used by the human Flutter session. The human settings routes must return redacted status only; secret references and worker credentials never reach Flutter.

## Complete visible capability coverage

The following matrix is the scope lock for “full MVP”. A row is not satisfied by a disabled button, a static card, a legacy alias, a placeholder response, or a test fixture. Where a record does not exist, the result is an explicit genuine empty/not-connected/unavailable state.

| Hub area | Visible capability bundle | Canonical owner/source | Implementation plan task |
|---|---|---|---|
| Strategy — Foundation | Canvas list/detail/create/edit/delete; revisions; source-linked model drafts; review/approval/rejection; venture profile and strategy lenses | Company Operations / Strategy tables + approved evidence refs | Strategy/Runtime Tasks 1, 2 and 4 |
| Strategy — Validation | Assumptions, interviews, discovery signals, experiments, evidence ingestion/review and learning result | Company Operations / existing Strategy tables and Vault evidence references | Strategy/Runtime Tasks 2 and 4 |
| Strategy — Execution | Initiatives, portfolios, projects, lifecycle stage context/transition, stage gates, pilots, PMF scoreboards, next actions and decision journal | Company Operations / operations + strategy tables | Strategy/Runtime Tasks 2 and 4 |
| Strategy — OKR/12-week | Cycle/objective/key-result lists, check-ins, project links, weekly plan, commitment, review and progress with measured/not-measured state | Company Operations / Strategy + Operating tables | Strategy/Runtime Tasks 2 and 4 |
| Strategy — Funding | Catalog/match/watchlist views show only connector/provider observations; missing provider is `not_connected` | Declared external connector / source provenance | Strategy/Runtime Task 2 and Settings/Release Task 1 |
| Workspace Runtime | Needs You, blocker list, source status, snooze, source-owner resolution and work inspector | Company Operations projection + immutable Agent signals | Strategy/Runtime Tasks 1–5 and Workforce Task 3 |
| Workforce — Roster | Assignment list, composition/eligibility, org chart and functional/spec version details | Agent Platform assignments + published registry | Workforce Tasks 1, 2 and 4 |
| Workforce — Execution | Run history/detail/events, schedules/routines, work products/artifacts, approval queue/decision, capability policy, cost/budget observations and health/heartbeats | Agent Platform durable run/approval/schedule/artifact/telemetry records | Workforce Tasks 2–5 |
| Vault — Documents | File/document list/detail/version/content/write lifecycle, upload ticket, processing/review/failure and retention state | Agent Platform Vault metadata + object store | Vault/Knowledge Tasks 1–4 |
| Vault — Knowledge | Indexed sources, retrieval/search, backlinks, graph, evidence links and active SOP policy state | Agent Platform knowledge/Vault stores | Vault/Knowledge Tasks 1–4 |
| Marketing — Context/Content | Context/revision/review, research/evidence, objectives, campaigns, assets, forms and publish approval state | Company Commercial / Commercial tables | Marketing Tasks 1–4 |
| Marketing — Learning | Experiments, interview/attribution intake, learnings, loops, decisions, recommendations and model drafts requiring review | Company Commercial / persisted records with Strategy/Vault refs | Marketing Tasks 1–4 |
| Marketing — Measurement | Funnel/KPI/metric history/attribution show measurement/provenance/freshness; missing provider has setup state | Company Commercial observed metrics + Control Plane connector status | Marketing Tasks 1–4 and Settings/Release Task 1 |
| Settings — Access | Membership, server-authorized role/capability and audit events | Control Plane membership/audit records | Settings/Release Tasks 1, 2 and 3 |
| Settings — Integrations | Connector install/grant/revoke/status/expiry and redacted scope view | Control Plane connector records | Settings/Release Tasks 1–4 |
| Settings — Runtime/Extensions | Device/runtime node presence/revoke, skill/plugin version/assignment/policy status | Control Plane nodes + Agent Platform skills | Settings/Release Tasks 1–4 |

## Shared interfaces introduced first

All later plans consume these interfaces without renaming them:

```dart
enum ApiPlane { company, platform, agent, localWorker }

sealed class ApiResult<T> {
  const ApiResult();
}
final class ApiSuccess<T> extends ApiResult<T> {
  const ApiSuccess({required this.data, required this.meta});
  final T data;
  final ApiResponseMeta meta;
}
final class ApiFailure<T> extends ApiResult<T> {
  const ApiFailure(this.failure);
  final ApiFailureDetail failure;
}
```

```ts
export type MvpDataState = "populated" | "empty";
export interface MvpResponseMeta {
  dataState: MvpDataState;
  observedAt: string;
  sources: readonly MvpSourceRef[];
}
export interface MvpSuccess<T> { data: T; meta: MvpResponseMeta; }
```

```python
class MvpResponseMeta(BaseModel):
    data_state: Literal["populated", "empty"]
    observed_at: datetime
    sources: list[MvpSourceRef] = Field(default_factory=list)
```

`ApiFailureDetail.code` is exactly one of `unauthenticated`, `forbidden`, `not_found`, `invalid_request`, `conflict`, `unavailable`, `not_connected`, `rate_limited`, `malformed_response`, or `unknown`. A network/client failure is never represented by `MvpSuccess`.

## Cross-plan source and event rules

1. Company Operations reads Company-owned tasks, dependencies, projects, commitments, decisions and Strategy records directly with workspace predicates.
2. Agent Platform emits an immutable `agent.runtime-signal.v1` only after a persisted run/approval transition. The signal includes `workspace_id`, `source_kind`, `source_id`, `state`, `observed_at`, `correlation_id` and a version/sequence. It contains no invented title, metric or customer content.
3. Company stores the signal as a deduplicated projection keyed by `(workspace_id, source_kind, source_id, sequence)`. Flutter cannot write it. If the signal feed is unavailable, Workspace Runtime exposes the Agent source as unavailable with its last confirmed timestamp.
4. A `runtime_snooze` record is actor-specific notification state only. Resolving a blocker/approval invokes the original owner operation; it does not mark a projection row as solved.
5. Marketing connector values include `provider_key`, `observed_at`, `metric_definition`, and status. A missing grant is `not_connected`, not numeric zero.

## Global verification matrix

| Proof | Required on every new read/write route |
|---|---|
| Contract | Manifest entry, request/response schema identifier, client capability identifier and route-parity test |
| Authorization | Missing token, same-workspace allowed and different-workspace denied test |
| Truth | Persisted/provider source test; exact empty-data assertion; every expected failure retains its failure code |
| Durability | Migration test for new tables plus fresh read after service/repository recreation |
| UI | Loading, populated, genuine empty, forbidden/unavailable, not-connected where relevant, and retry widget tests |
| Integration | Real local database/service scenario; no `MockTransport`, monkeypatch transport or fake server in the route proof |

## Task 1: Establish the shared acceptance ledger

**Files:**

- Create: `docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md`
- Modify: `shared/contracts/mvp-surface.json` (created in Foundation plan)
- Modify: this master plan only if scope is explicitly changed by the user

**Interfaces:**

- Consumes: the manifest `capabilities[]` from the Foundation plan.
- Produces: a review table mapping every capability ID to source owner, migration, backend test, Flutter test, integration scenario and release evidence.

- [ ] **Step 1: Create the capability rows before implementing a route.**

  Use one row per manifest ID, not one row per screen. Start each row in `PLANNED` state and include the exact fields below:

  ```markdown
  | capability_id | owner | source_kind | contract_schema | backend_test | flutter_test | integration_test | status |
  |---|---|---|---|---|---|---|---|
  | strategy.canvas.list | company-operations | company_db | strategy.canvas.list.v1 | operations/tests/mvp-canvas-runtime.test.ts | frontend/test/strategy_mvp_service_test.dart | tests/e2e/test_mvp_strategy_runtime_http.py | PLANNED |
  ```

- [ ] **Step 2: Verify the ledger fails review when a required proof is blank.**

  Add this negative record to the ledger's verification examples and ensure `scripts/mvp_surface_check.py --ledger` reports the missing `integration_test` field:

  ```markdown
  | workforce.agent.list | agent-platform | agent_db | workforce.agent.list.v1 | tests/apps/cosa/test_workforce_routes.py | frontend/test/workforce_service_test.dart |  | PLANNED |
  ```

- [ ] **Step 3: Keep implementation status evidence-based.**

  Set `IMPLEMENTED` only after code and focused tests pass; set `WIRED` only after the manifest's Flutter client call is live; set `VERIFIED` only after the listed real-service integration test passes. Never use `PRODUCTION` without authorized environment evidence.

- [ ] **Step 4: Run the ledger consistency check.**

  Run: `python3 scripts/mvp_surface_check.py --ledger`

  Expected: every enabled manifest capability has exactly one complete ledger row; no `VERIFIED` row points to a mock-only test.

- [ ] **Step 5: Commit the ledger with its matching contract change.**

  ```bash
  git add docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md shared/contracts/mvp-surface.json
  git commit -m "docs: track mvp capability acceptance"
  ```

## Task 2: Enforce final programme completion

**Files:**

- Modify: `docs/architecture/generated/route-inventory.md`
- Modify: `docs/architecture/generated/route-inventory.snapshot.json`
- Modify: `docs/architecture/generated/company-usage-inventory.md`
- Modify: `docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md`

**Interfaces:**

- Consumes: all six sub-plan routes, tests and acceptance ledger rows.
- Produces: a reviewed repository snapshot with zero enabled MVP ghost entries and complete evidence.

- [ ] **Step 1: Regenerate rather than hand-edit the inventories.**

  Run:

  ```bash
  make route-inventory
  make company-usage-inventory
  ```

- [ ] **Step 2: Run the final MVP check before broad suites.**

  Run: `python3 scripts/mvp_surface_check.py --check --ledger`

  Expected: `0 enabled MVP capabilities without a canonical handler`, `0 direct legacy calls in enabled MVP clients`, and `0 runtime fixture imports`.

- [ ] **Step 3: Run the full repository verification set.**

  Run:

  ```bash
  make lint
  make typecheck-py
  make agent-test
  make apps-cosa-test
  make frontend-test
  make frontend-analyze
  make boundary-check
  make contract-freeze-check
  git diff --check
  ```

  Expected: every command exits 0. The current Company usage inventory drift is resolved by the generated artefact, never by weakening `contract-freeze-check`.

- [ ] **Step 4: Record only real integration evidence.**

  Add the command, commit SHA, database migration versions, timestamp, correlation IDs and pass/fail result from every `tests/e2e/test_mvp_*.py` scenario to the ledger. If a prerequisite is unavailable, keep the status below `VERIFIED`; do not substitute a mock run.

- [ ] **Step 5: Commit the reviewed final snapshot.**

  ```bash
  git add docs/architecture/generated docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md
  git commit -m "chore: freeze full mvp contract inventory"
  ```

## Completion decision

The programme is complete only when all ledger rows are `VERIFIED`, all global gates pass, the enabled-client legacy scan is empty, and the release documentation says exactly what has been verified. Edge WAF/rate limiting remains a public-release no-go until its owner performs and records an authorized 429 verification; application code must not attest it on the infrastructure owner's behalf.
