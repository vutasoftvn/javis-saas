# Maintainable Modular Truthful MVP Design

**Status:** Approved design, pending implementation plan

**Date:** 2026-08-31

## Goal

Make the implemented full MVP maintainable without changing its product scope: keep the existing four runtime planes, remove legacy client paths gradually, split oversized modules by business responsibility, and require all visible data and release evidence to be truthful.

## Scope

This design covers the implemented MVP surface in Strategy, Workspace Runtime, Workforce, Vault/Knowledge, Marketing, and Settings. It also covers the shared transport/contract spine, real-stack integration proof, and CI guardrails required to keep the resulting boundaries intact.

It does not create a new deployable microservice, change a business owner, rewrite the application in a new state-management framework, or alter a migration that has already been applied.

## Non-negotiable truth and safety rules

1. Production and ordinary development runtime may read only owned storage or a configured external connector. It must not create demo, placeholder, default customer, synthetic metric, fake health, fake provider, or fake role data.
2. A successful read has only `populated` or `empty` data state. Authentication, authorization, validation, conflict, provider, connection, malformed-response, and server errors are typed failures; they are never converted to `null`, `[]`, `{}`, `false`, zero, `HEALTHY`, or `connected`.
3. A label derived by the system is allowed only when its origin is explicitly `system_derived`. It must not be represented as source content authored by a customer, employee, agent, or provider.
4. An `online`, `healthy`, `connected`, `enabled`, or `verified` state requires an owner record and an actual observation timestamp. No observation yields the relevant unknown, unavailable, not-connected, or not-observed state.
5. Fixtures, fake providers, in-memory repositories, ASGI transports, monkeypatched transports, mock transports, and mocked clients are permitted only in unit or in-process integration tests. They are forbidden from `tests/e2e/test_mvp_*.py` and cannot satisfy a release proof.
6. Every tenant-owned operation derives actor and workspace authorization on the server. A workspace ID supplied by the browser is context only and never grants access.
7. Snowflake IDs remain strings across JSON, Dart, and browser-facing TypeScript. No feature converts an ID through JavaScript `number`, Dart `double`, or a lossy display value.
8. Existing migrations are immutable. Every new migration is additive, workspace-indexed where applicable, has a reviewed down migration, and is exercised by apply, rollback, and reapply tests.
9. Agent Platform never writes Company business tables. Company stores only an immutable, deduplicated projection of Agent signals and never becomes a mutable mirror of Agent assignments, runs, approvals, documents, or skills.
10. Infrastructure readiness cannot be asserted from an environment variable or a document. Rate limiting, WAF, staging, production, and connector readiness require an observed check in the authorized environment.

## Target architecture

The existing four planes remain the deployment topology.

```text
Flutter Experience
  -> services/cosa                 Control Plane: identity, membership, policy, connectors, runtime nodes
  -> services/company              Business: operations, strategy, commercial, finance/legal
  -> apps/cosa + packages/agent    Agent composition and reusable Agent Platform
```

The change is an internal modularization. It is not a microservice split. Business transactions, tenancy boundaries, and deployment topology therefore remain stable while files and interfaces become smaller and clearer.

### Shared contract spine

`shared/contracts/mvp-surface.json` remains the only handwritten endpoint/capability manifest. It generates the TypeScript, Python, and Dart endpoint definitions. Generated files are never edited manually.

All migrated Flutter calls use `MvpEndpoint` and `MvpRequestClient` and return `ApiResult<T>`. The request client resolves the authentication token by `ApiPlane` through a single shared resolver: Company and Agent use the local session token; Control Plane uses the platform token; fallback to an old token is temporary compatibility behavior with an explicit removal gate.

`WorkspaceScopedService` is a compatibility layer only. No migrated caller can use it. It must preserve a typed failure while legacy callers remain, and it is deleted when the final caller is migrated.

### Flutter module boundaries

Flutter adopts an incremental feature structure.

```text
frontend/lib/
  app/                                bootstrap, dependency injection, routing, app shell
  core/                               auth, workspace context, network, result, shared primitives
  features/
    <feature>/
      domain/                         typed entities, repository ports, public feature contracts
      data/                           DTOs, generated-endpoint clients, remote repositories
      presentation/                   controllers, views, widgets
  surfaces/
    hologram_hub/                     UI composition through typed facades only
```

The migration keeps existing `modules/<feature>` paths until a feature slice has moved safely. Each migrated feature publishes a minimal public facade from `domain/`. Presentation code cannot import another feature's `data/`, service, repository implementation, controller, or widget.

Cross-feature flows use a typed facade owned by the consumer or an application-level query. For example, `HubOverviewQuery` collects typed overview records, and `HubCommandFacade` dispatches explicit user commands. Hologram Hub cannot import Strategy, Vault, Workforce, Auth, Dashboard, Control Plane, or Workspace Runtime service classes directly.

The first frontend decompositions are:

| Existing hotspot | Replacement responsibility boundaries |
|---|---|
| `StrategyService` | Canvas, OKR, Planning, Portfolio, Lifecycle repositories |
| `MarketingController` and `MarketingService` | Context, Campaign/Asset, Experiment/Learning, Measurement controllers and repositories |
| `AgentPlatformService` | Workforce, Runs, Approvals, Schedules, Telemetry repositories |
| Hologram Hub controller/mixins | Hub overview query and hub command facade, with presentation-only widgets |
| Vault service | Document lifecycle and Knowledge retrieval repositories |

No new public domain boundary uses `Map<String, dynamic>`, `List<dynamic>`, `dynamic`, `any`, or unvalidated raw JSON. DTO parsing happens once in the data layer and returns typed domain models or `ApiFailure`.

### Company service boundaries

`services/company` remains organized by Operations, Commercial, and Finance-Legal. Within each domain, code is separated by responsibility:

```text
<domain>/
  handlers/                           Encore HTTP: parse request, establish context, return response
  application/                        one use case per capability or closely related aggregate
  domain/                             typed value objects, policy, ports, state transitions
  infrastructure/                     Drizzle queries, provider adapters, event outbox/projection
```

Handlers stay thin. They may not assemble untyped persistence data or duplicate authorization. Application services consume a typed tenant context. Infrastructure implements a port and owns SQL/Drizzle details.

Operations is divided into Canvas, OKR, Planning, Portfolio/Lifecycle, and Workspace Runtime read projection. Workspace Runtime can read Company tasks/dependencies and its immutable Agent signal projection. Its health source is an observed record or explicit unavailable state; it may not create current-time healthy records.

Commercial is divided into Marketing Context, Campaign/Asset, Experiment/Learning, and Measurement. Provider observations retain provider key, source record, observation time, freshness, and source status.

### Control Plane and Agent Platform boundaries

`services/cosa` remains owner of human platform identity, membership, policy, connector grants, runtime-node registry, and redacted Settings audit records. Browser Settings routes use human platform token audience/issuer checks. Worker-only routes remain separate.

`apps/cosa` is a composition and HTTP adapter layer. Its old router is separated into Conversations, Runs, Approvals, Sessions, Artifacts, Connectors, and Schedules routers. A route may depend on a typed `CosaAgentPlane` port but must not contain persistence policy.

`packages/agent` owns reusable domain behavior. Each repository is divided into a typed port and adapter implementations:

```text
packages/agent/<capability>/
  models.py or domain.py
  ports.py
  adapters/postgres.py
  adapters/in_memory.py
```

The production composition root selects Postgres adapters only. Test and explicit local test wiring may select in-memory adapters. The root remains fail-fast when a production database/configuration requirement is missing.

Agent-to-Company signals use a persisted Agent outbox and an idempotent Company projection keyed by workspace, source kind, source ID, and sequence. The Agent event contains only confirmed source fields. Company may attach a clearly marked system presentation label but cannot manufacture agent/customer/provider facts.

## Testing and release evidence

Tests are classified by the dependency they prove:

| Test class | Allowed doubles | Required proof |
|---|---|---|
| Unit | fake, in-memory, mock | domain transition, mapper, policy, failure mapping |
| In-process integration | ASGI transport, injected fake adapter | route wiring and adapter contract only |
| Adapter/database | isolated real Postgres/MinIO | migration, persistence, workspace isolation, restart-safe read |
| MVP E2E | real process HTTP, real isolated Company/Control Plane/Agent/Postgres/MinIO | cross-plane request, auth, durable data, provenance, failure behavior |

`tests/e2e/test_mvp_*.py` are the fourth class. They must not import `ASGITransport`, `MockTransport`, `AsyncMock`, `FakeSDKModel`, `InMemory`, fake policy clients, or monkeypatch the transport. An unavailable prerequisite is recorded as unverified release evidence and fails the required MVP gate; it cannot be silently skipped.

Every migrated endpoint requires contract, same-workspace allow, other-workspace deny, persisted/provider source proof, genuine empty proof, typed failure proof, Flutter loading/populated/empty/error proof, and a real E2E scenario.

## Enforced maintainability gates

The repository adds checks that prevent regressions rather than relying on review memory:

1. Generated contract and route inventory are synchronized.
2. A migrated feature contains no raw route literal or `WorkspaceScopedService` caller.
3. A migrated feature presentation import cannot target another feature's implementation layer.
4. `tests/e2e/test_mvp_*.py` contains no mock/in-memory/ASGI transport imports and no skip for required infrastructure.
5. Every enabled capability has its owner, schema, backend test, Flutter test, real integration test, and release evidence in the acceptance ledger.
6. Ruff, mypy, both TypeScript type checks, Flutter analyze, focused tests, and feature E2E all pass before a task is committed.
7. Generated and test files are exempt from file-size review. New handwritten controller, route, service, or repository code exceeding 500 lines must be split within the same task or have an explicit, reviewed exception in the acceptance ledger.

## Delivery strategy

The work uses a contract-first strangler sequence. Each slice is independently deployable and reversible:

1. Repair current quality gates and harden common transport, no product behavior expansion.
2. Establish enforceable module/E2E guards and real-stack harness.
3. Migrate Strategy and Workspace Runtime, including truthful signal/health semantics.
4. Migrate Workforce and Vault/Knowledge Agent slices.
5. Migrate Marketing and Settings.
6. Convert Hologram Hub to typed composition after its dependencies are exposed.
7. Remove remaining legacy clients/routes only after inventory and acceptance ledger evidence are complete.

Each delivery task begins with a failing test, implements the smallest behavior required, proves it with its exact command, updates the ledger, and commits only with all task gates green. Any task that needs a new product capability, a new deployable service, a migration rewrite, or fabricated data stops and asks for scope approval.

## Success criteria

The refactor is complete when all visible enabled MVP flows use typed generated endpoint contracts; no enabled flow calls a ghost route or swallows a failure; source/health/provenance claims are observed and durable; real E2E covers all four planes; frontend feature presentation boundaries are enforced; the old mega-services and mega-router are decomposed; and every required quality gate is green.
