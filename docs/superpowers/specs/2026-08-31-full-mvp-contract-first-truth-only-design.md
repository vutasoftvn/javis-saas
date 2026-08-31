# Full MVP Contract-First, Truth-Only Design

**Status:** Approved design direction; implementation requires reviewed execution plans.

**Date:** 2026-08-31

**Scope:** Deliver the complete user-visible Dashboard and Hub MVP across Strategy, Marketing, Workforce, Workspace Runtime, Vault, and Settings. The MVP includes the frontend, its canonical API contracts, durable backend data and authorization, and verification. It does not mean retaining every legacy route currently referenced by the Flutter client.

## Goal

Deliver a working MVP in which every enabled screen operates on tenant-authorized, durable data from a declared owner; every error state is visible and actionable; and no runtime layer manufactures data or hides an unavailable backend contract behind a successful-looking UI.

## Confirmed baseline

- The repository has four planes: Flutter experience, TypeScript Control Plane (`services/cosa`), TypeScript Company Plane (`services/company`), and the Python Agent Platform (`apps/cosa` plus `packages/agent`).
- The backend already has strong primitives to preserve: Company workspace authorization, Control Plane membership validation, Agent Platform JWT/workspace resolution, secret fail-closed production configuration, and migration-managed persistence.
- Frontend-to-backend parity is currently incomplete. The generated route inventory records 132 frontend requests with no matching server route, including user-visible Strategy, Marketing, Workforce, Vault, Settings and workspace-runtime flows.
- The current Flutter transport normalizes several legacy paths and some service layers turn failed HTTP responses into `null`, `false`, or empty collections. That makes a missing contract indistinguishable from genuine empty data.
- Existing lint, typecheck and most unit suites are green, but `make contract-freeze-check` currently detects generated Company usage inventory drift. Database-dependent migration/rehearsal and full cross-plane scenarios have not been represented as proof of production readiness.

## Decisions

1. **The MVP surface is the visible product surface, not the legacy route set.** Every feature currently offered in Dashboard/Hub is implemented end-to-end. Legacy endpoints with no owner are removed from the client only when the client has been moved to a canonical replacement and a route-parity check proves no enabled UI refers to the legacy form.
2. **Each record has one writable owner.** Company owns business operations and commercial records; Agent Platform owns agent, run, approval, skill, schedule and knowledge records; Control Plane owns identity, membership, connector grants and platform policy. Workspace Runtime is a read model over owner records and never becomes a second writable task/agent store.
3. **Contracts are explicit, versioned repository truth.** A shared MVP-surface manifest declares each enabled UI capability, its canonical route, method, owner, authorization requirement, request/response schema identifier, and runtime data source. Domain schema files define the payload shape and error envelope. Their examples are test fixtures only, never response defaults.
4. **Every query carries an honest data state.** Success is only `populated` when persisted/provider data was found and `empty` when an authorized query completed with zero records. `unavailable`, `forbidden`, `unauthenticated`, `not_connected`, `invalid_request`, and `conflict` are typed non-success outcomes. A handler may not convert a failure to a success with an empty payload.
5. **Runtime data is truth-only.** Production and normal development runtime may read only a repository database, configured object store, configured connector, or authenticated platform service. It may not generate demo tasks, agents, outcomes, metrics, documents, health readings, placeholders, default workspace entities, or artificial zero values to complete an API response.
6. **Test data is isolated.** Fixtures, factories, fake providers and mock transports are permitted only below test-only paths or dependency injection used exclusively by a test process. Cross-plane integration and end-to-end tests must create their own isolated database/workspace and use real local services and contracts. A fixture may validate serialization but can never be imported by a runtime handler, repository, Flutter feature, seed command, or deployment configuration.
7. **System reference data is not customer data.** A migration may install a reviewed, versioned and labelled system taxonomy or policy only when the product needs it. It must be `system-owned`, documented, and cannot claim to be a workspace's strategy, workforce, campaign, evidence, metric, document, or outcome. No synthetic backfill is permitted.
8. **Authorization is always server-derived.** New Company routes use the existing workspace access guard. New Agent routes resolve workspace and actor from verified credentials. Browser-supplied workspace, role, account, owner, or approval identity fields may identify a target only after server authorization; they never grant access.
9. **The Flutter client becomes typed and failure-preserving.** Domain clients replace broad route rewriting and nullable success conventions with typed request/response models plus a structured result/failure type. Transport may select the correct plane, but it cannot silently rewrite an undocumented legacy capability or synthesize a successful response.
10. **Visible UI communicates truth.** Every screen has loading, populated, genuinely empty, forbidden, unavailable, and retry states. An enabled action is available only if the server contract and capability permit it. The UI does not render dummy cards, numbers, charts, documents or records while loading or when a provider is absent.
11. **Operational aggregation retains provenance.** Workspace Runtime cards expose source references and freshness metadata sufficient to open the originating task, approval, run, dependency or evidence. It uses bounded, indexed read queries from source owners; it does not write parallel copies.
12. **Migrations are additive, reversible and evidence-based.** New durable entities have an ordered migration, indexes/constraints for tenant access and idempotency, a verified down path where safe, and empty-database plus upgrade/rollback proof. Existing records are mapped only when their identity and semantics are provable; unmatched records are left untouched and reported for manual handling.
13. **External metrics and connector state stay honest.** A connector that is absent, unauthorized, stale, rate-limited, or erroring returns its actual state. Marketing and Settings never display fabricated metrics, healthy device status, connected provider status, or timestamp merely to make the UI complete.
14. **Generated artifacts are release inputs.** A change to canonical routes, schemas or frontend consumers updates the generated route inventory and Company usage inventory in the same change. CI fails on drift and on any enabled MVP capability that lacks its owner route, contract declaration, tenant authorization test, and integration proof.
15. **Security and operational claims require evidence.** The observed edge rate-limiting/WAF configuration gap is a public-release blocker. The programme may add configuration checks and runbooks, but must not claim an edge control is live until an authorized infrastructure deployment and real 429 verification have occurred.
16. **Delivery is vertical and reviewable.** Foundation work lands before client migration. Each domain slice follows durable storage, authorization, canonical contract, Flutter wiring, and real integration proof. A feature flag may control rollout during implementation, but no final MVP screen may depend on a fake response or a permanently disabled substitute.

## Runtime truth policy

### Permitted runtime sources

| Source | Permitted use | Required proof |
|---|---|---|
| Company database | Strategy, execution, commercial and runtime read-model records | Migration, workspace-scoped repository test, API integration test |
| Agent Platform database/object store | Agent registry, runs, approvals, skills, schedules, vault documents and knowledge state | Migration or durable-store proof, workspace authorization test, API integration test |
| Control Plane database | Membership, connector grants, policy and platform configuration | Authenticated tenant test and audited mutation test |
| Configured external connector | Provider data and status | Grant/credential check, source timestamp and disconnected/error path test |

### Prohibited runtime behavior

- Returning a hard-coded collection or “starter” record from any API or Flutter service when a query fails or returns no rows.
- Catching 401, 403, 404, 409, 429, network, timeout or 5xx errors and changing them to `[]`, `{}`, `null`, `false`, zero KPI values, `healthy`, `connected`, or success.
- Using test fixtures, `Mock*`, `Fake*`, demo JSON, sample assets, test seeds, or conditional test defaults from a runtime import path.
- Creating customer-like data as a migration backfill, first-login initializer, empty-state initializer, or frontend default.
- Creating a request-only response schema without a persistent owner or real provider behind it.

### Enforcement

1. The shared manifest records a `source_kind` for each read capability: `company_db`, `agent_db`, `object_store`, `control_plane`, or `external_connector`.
2. Handler/service tests assert all expected error codes remain errors and that an authorized empty query returns only the explicit `empty` state.
3. Dependency checks prevent runtime imports from test fixture/fake/mock paths.
4. Route-parity checks fail if an enabled Flutter capability has no declared manifest entry or no server implementation.
5. Cross-plane tests run against isolated real services. Mock-based unit tests cannot satisfy a route's integration-proof requirement.
6. Review checklists require the data source and absence/error behavior for every changed visible field.

## Canonical MVP topology

```text
Flutter screen/controller
  -> typed domain client + structured result
  -> canonical Company / Control Plane / Agent API
  -> server-derived actor and workspace authorization
  -> writable owner database or configured provider
  -> response with data state, freshness and source references
```

The path is intentionally one-directional. Flutter cannot decide tenant scope; Workspace Runtime cannot mutate its inputs; Agent Platform cannot impersonate a Company commercial/operations owner; and fixture data cannot cross from tests into runtime.

## MVP vertical slices

### 1. Foundation: contracts, transport and capability parity

**Owners:** shared contract artefacts, Flutter networking/application shell, and the service owning each route.

**Scope:**

- Define the shared MVP-surface manifest and domain schemas for every enabled Dashboard/Hub capability.
- Introduce a typed frontend result/error model and migrate visible services away from nullable/empty-on-error conventions.
- Reduce `ApiClient` to authenticated transport and documented plane selection; remove legacy normalization only as each consumer reaches its canonical contract.
- Add route-parity and fixture-isolation checks to the existing generated-contract gate.
- Make the application shell route/capability aware so it does not offer an action without its approved server contract.

**Completion evidence:** a route in the manifest can be traced from Flutter client through its backend handler, and tests distinguish empty data from every error class.

### 2. Strategy and execution

**Owner:** Company Operations.

**Scope:**

- Strategy canvases, immutable revision history and lenses/evidence references.
- Initiatives, projects and project lifecycle data.
- OKR cycles, objectives, key results, ownership, progress and outcome evidence.
- Twelve-week cycles, plans, commitments, dependencies and status transitions.
- Read/write routes are workspace-scoped, idempotent where retries can repeat a command, and audit meaningful mutations.

**Truth policy:** calculated progress must name its inputs and timestamp; an uncalculated/missing input is unavailable or incomplete, never made into a plausible percentage. An empty workspace stays empty until an authorized user creates real records.

### 3. Workspace Runtime

**Owner:** Company Operations as a derived, read-only model over Strategy/Execution and authorized Agent Platform signals.

**Scope:**

- Needs You: decisions/approvals assigned to the authenticated actor.
- Blocked Work: unresolved project/task dependencies, blocked approvals and failed/paused agent work with their source reason.
- Work Inspector: one source-linked view across task/project, run, approval, evidence, ownership and recent transitions.
- Bounded aggregation queries, freshness timestamps, source references and deep links to owner views.

**Truth policy:** no runtime table is a writable mirror of a task, agent or document. If an upstream source cannot be queried, the result reports that source as unavailable instead of omitting it and presenting a complete-looking dashboard.

### 4. Workforce

**Owner:** Agent Platform.

**Scope:**

- Agent registry/specification, assigned workspace, configured skills and permitted capabilities.
- Schedule, run ledger, run detail, execution status, approval queue and runtime-health observations.
- Mutations use the Agent Platform approval/policy path and create auditable records; Company does not keep a competing agent registry.
- Flutter workforce views use Agent Platform canonical routes and explicit provider/routing failures.

**Truth policy:** agent health is based on an observed heartbeat/run/worker state with timestamp. It never defaults to healthy. A configured but never-run agent is visibly `not_observed`, not active.

### 5. Vault and knowledge

**Owner:** Agent Platform durable knowledge/object-store services.

**Scope:**

- Authenticated upload, document metadata, object ownership, ingestion lifecycle, chunk/index state, retrieval and source/evidence links.
- Vault list/detail/search UI with current state (`uploaded`, `processing`, `indexed`, `failed`, `unavailable`) from the actual pipeline.
- Workspace isolation for documents, retrieval results and object access.

**Truth policy:** a document is not searchable until indexed by the real ingestion path. A failed ingestion remains failed with a recoverable action; it is not shown as a placeholder document or mocked search hit.

### 6. Marketing

**Owner:** Company Commercial, with external connectors retaining authority for imported provider metrics.

**Scope:**

- Marketing context, objectives, campaigns, experiments, assets and their lifecycle.
- Metric definitions, provenance, observed values, freshness, connection state and attribution references.
- Explicit connector-grant and provider-error behavior for imported data.

**Truth policy:** absence of an integration, a provider error, or no measurement is distinct from a measured zero. Records are created only by a user/API command or an authorized connector ingestion, never for visual completeness.

### 7. Settings and platform operations

**Owners:** Control Plane for membership/connector grants/policy; Agent Platform for skills/plugins where it owns them; desktop worker for device presence.

**Scope:**

- Real membership, role/capability and workspace policy views.
- Connector grant/configuration status without exposing secrets.
- Plugin/skill configuration subject to Agent Platform policy and approval.
- Device/desktop-worker presence, last observed time and unavailable state from the actual worker/control-plane signal.

**Truth policy:** a missing device/connector/permission is presented as missing. Settings cannot show `connected`, `synced`, or `enabled` without a verified owner state and timestamp.

## Delivery sequence

### Tranche A — Establish the contract spine

1. Reconcile Company usage inventory and commit generated artefacts without weakening the check.
2. Build the manifest, schema/error envelope and contract test harness.
3. Add frontend structured results and replace failure-swallowing behavior in the visible feature clients.
4. Add parity, fixture-isolation and capability gating checks.
5. Verify tenant/role enforcement and token audience behavior on every new/changed owner route.

### Tranche B — Establish business truth and operational aggregation

1. Complete Strategy/Execution storage, migrations, canonical contracts and Flutter views.
2. Build Workspace Runtime only after its underlying source contracts are available.
3. Prove that every runtime card resolves to a real owner record and that source outages remain visible.

### Tranche C — Establish agent and knowledge truth

1. Complete Workforce canonical API/UI and run/approval/health integration proof.
2. Complete Vault upload/ingestion/retrieval API/UI and object-store/knowledge proof.
3. Integrate source references from these domains into Workspace Runtime without duplicating their records.

### Tranche D — Establish commercial and operational settings truth

1. Complete Marketing canonical API/UI, including metric provenance and disconnected-provider states.
2. Complete Settings canonical API/UI for memberships, connectors, skills/plugins and devices.
3. Remove the last enabled legacy client endpoints and require zero unresolved MVP route-parity entries.

### Tranche E — Release evidence

1. Run clean-database migrations, upgrade and safe rollback rehearsal for each changed owner.
2. Run cross-plane integration scenarios using isolated real services and data created by the scenario.
3. Run Flutter widget/integration scenarios for populated, empty, forbidden, unavailable and not-connected outcomes.
4. Run the repository quality, contract and route-parity gates.
5. Conduct an authorized staging verification. Record build SHA, migration versions, correlation IDs, source timestamps and results. Do not represent staging proof as production proof.
6. Treat verified edge rate-limiting/WAF as a separate public-release prerequisite; update release documentation only with evidence from the owner infrastructure environment.

## Mandatory verification per capability

Every manifest capability requires all of the following before it is enabled:

1. A source-owned data model or configured external provider, including tenant access indexes/constraints where durable storage is involved.
2. A canonical request/response/error schema and backend route with server-derived authorization.
3. A durable integration test that writes/reads real isolated data and proves a different workspace cannot access it.
4. Negative tests for invalid request, unauthenticated, forbidden, unavailable and provider-not-connected behavior as applicable.
5. A typed Flutter client and UI tests for loading, populated, genuine empty, error and retry states.
6. A generated route-parity entry and no runtime fixture/mock import.
7. For derived values, provenance/source references and freshness semantics.

## Migration and rollback rules

- Add tables/columns/indexes before exposing a reader or writer. Backfill only values with an exact, reviewed source mapping.
- Use forward-compatible, additive migrations first. Do not drop or reinterpret existing data in the same rollout that introduces a replacement endpoint.
- Define ownership, uniqueness and idempotency at the database layer rather than relying solely on a frontend check.
- Test empty-database migration, upgrade from the immediately preceding supported schema, and rollback of unapplied/failed changes in an isolated environment.
- For a defect, disable the affected capability and preserve the owner records. Never delete workspace data as a rollback shortcut.

## Required quality gates

The detailed plans must integrate the existing gates and add only evidence-based checks:

```bash
make lint
make typecheck-py
make agent-test
make apps-cosa-test
make frontend-test
make frontend-analyze
make contract-freeze-check
make boundary-check
git diff --check
```

The implementation plan will also identify the repository-native commands for TypeScript compilation, migration rehearsal and cross-plane integration. A newly added critical path may not reduce applicable coverage or substitute a mocked test for its required real integration proof.

## Non-goals

- Retaining undocumented legacy API compatibility after its visible client has migrated.
- Manufacturing a demo workspace, dummy agent fleet, fabricated campaign metrics, sample Vault content or artificial runtime health to make the product appear populated.
- Replacing the established four-plane architecture, workspace authorization boundary, production secret model or external infrastructure without a separate approved design.
- Claiming external WAF, staging, production deployment, connector connectivity or data migration success without recorded evidence.
- Broad unrelated refactors not required to make an enabled MVP capability truthful and contract-complete.

## Delivery artefacts

The next phase produces one master execution plan and six independently executable sub-plans:

1. Foundation, truth-only contract governance and Flutter transport.
2. Strategy, execution and Workspace Runtime.
3. Workforce.
4. Vault and knowledge.
5. Marketing.
6. Settings, migration rehearsal and release evidence.

Each task will name exact file paths, symbols, route/migration changes, tests, acceptance evidence and the applicable truth-only restriction. The plan will not use placeholder implementation instructions such as “implement API”, “add tests”, or “wire frontend”.

## Definition of done

- Every Dashboard/Hub MVP capability has an owned canonical contract, durable real source or honest provider state, workspace authorization, typed frontend behavior and integration proof.
- The enabled client has zero unresolved MVP route-parity entries and no hidden failure-to-empty conversion.
- No runtime source imports/serves fixtures, mocks, demo records or synthetic customer-like data.
- Strategy, Runtime, Workforce, Vault, Marketing and Settings each meet their owner-specific truth policy.
- Migration/recovery, quality gates and cross-plane scenarios have recorded evidence.
- Public release claims remain blocked until separately authorized and verified edge controls and staging/production checks are complete.

## Existing material reused

- `docs/architecture/generated/route-inventory.md` is the generated source for current frontend/backend parity analysis.
- `docs/implementation/frontend-endpoint-inventory-2026-08-28.md` records known frontend endpoint gaps and informs the canonical cutover map.
- `docs/architecture/plans/2026-08-29-cosa-workspace-canonical/` contains the existing M3 Workspace/Vault, M4 lifecycle, and M7 workforce implementation material; the execution plans will reconcile rather than duplicate applicable work.
- `docs/superpowers/specs/2026-08-31-codebase-quality-academy-production-design.md` supplies compatible principles for generated repository truth, durable data, tenant authorization and evidence-based release claims.
