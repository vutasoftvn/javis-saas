# Maintainable MVP Agent, Control, and Real-E2E Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the Agent HTTP/composition and persistence layers into maintainable adapters, make Vault and Settings perform only real persisted/object-store work, fail closed for missing production signal configuration, and replace simulated MVP E2E with a real cross-plane stack.

**Architecture:** `packages/agent` remains reusable domain/port code; `apps/cosa` remains FastAPI composition and adapters. Split the mega router by capability, keep owner routes stable, expose typed repository protocols, and defer legacy repository-file deletion until callers are migrated. Vault upload/index status comes from real object storage and real ingestion. Settings values come from a configured registry plus durable workspace policy. E2E reaches live local instances of Company, Control, Agent, Postgres, and MinIO—never an in-process fake.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, SQLAlchemy/PostgreSQL, MinIO/S3-compatible storage, HTTPX, pytest, Docker Compose, Make, TypeScript Company/Control services.

**Spec:** `docs/superpowers/specs/2026-08-31-maintainable-modular-truthful-mvp-design.md`

**Depends on:** Foundation Tasks 1–4; Company Task 3 before true Runtime E2E; Company Task 4 before true Marketing E2E.

## Global Constraints

- Read and obey the master plan and Foundation plan. `tests/e2e/test_mvp_*.py` must pass `make mvp-e2e-purity-check` at every commit.
- Do not return an empty Settings list on registry outage, fabricate a skill version/provider/mode/timestamp, issue a made-up upload URL, create a fake object reference, or set a Vault document to `INDEXED` before real ingestion persisted a terminal success.
- A configured local-development default may exist only in an explicitly local compose/env file and must never be selected in staging/production. Missing service URL/credential is an explicit startup or request failure, not an implicit loopback token.
- Repository interfaces belong in `packages/agent/<capability>/ports.py`; concrete SQLAlchemy adapters belong in `postgres.py`; test-only in-memory adapters belong in `in_memory.py` and must not be reachable from production composition.
- Keep existing migrations immutable. New Agent migrations require exact up/down scripts and isolated apply/rollback/reapply evidence.
- Do not use `pytest.skip`, mock transports, mocks, monkeypatches, `ASGITransport`, or fake models in required real E2E. If authorized infrastructure cannot run, keep the ledger `BLOCKED` and report the blocker.

## Target module map

```text
apps/cosa/
  api/
    dependencies.py
    routers/{runs.py,conversations.py,approvals.py,sessions.py,artifacts.py,connectors.py,schedules.py,knowledge.py}
    settings_routes.py                  # thin HTTP adapter over settings service
    vault_routes.py                     # thin HTTP adapter over vault application service
    workforce_routes.py                 # thin HTTP adapter over workforce application service
  composition/{agent_plane.py,settings.py,vault.py,workforce.py}
  events/runtime_signal.py
packages/agent/
  workforce/{ports.py,postgres.py,in_memory.py,service.py,repository.py}
  vault/{ports.py,postgres.py,in_memory.py,object_store.py,ingestion.py,service.py,repository.py}
  settings/{ports.py,postgres.py,service.py}
tests/e2e/
  mvp_stack.py
  conftest.py
  test_mvp_*.py
docker-compose.mvp-e2e.yml
```

`repository.py` may remain only as a compatibility re-export during migration. It must contain no active SQL query once caller scans are empty.

## Task 1: Split the FastAPI mega-router without changing public behavior

**Files:**

- Create: `apps/cosa/api/dependencies.py`
- Create: `apps/cosa/api/routers/__init__.py`
- Create: `apps/cosa/api/routers/runs.py`
- Create: `apps/cosa/api/routers/conversations.py`
- Create: `apps/cosa/api/routers/approvals.py`
- Create: `apps/cosa/api/routers/sessions.py`
- Create: `apps/cosa/api/routers/artifacts.py`
- Create: `apps/cosa/api/routers/connectors.py`
- Create: `apps/cosa/api/routers/schedules.py`
- Create: `apps/cosa/api/routers/knowledge.py`
- Modify: `apps/cosa/api/routes.py`
- Modify: `apps/cosa/api/app.py`
- Create: `tests/apps/cosa/test_router_registration.py`
- Create: `tests/apps/cosa/test_routes_contract.py`

**Interfaces:**

```python
def get_agent_plane(request: Request) -> AgentPlane: ...
def get_current_actor(request: Request) -> AuthenticatedActor: ...
def require_workspace_access(actor: AuthenticatedActor, workspace_id: str) -> None: ...
```

Each router exports exactly one `APIRouter`; dependency helpers perform no business persistence and expose no raw headers outside the authentication boundary.

- [ ] **Step 1: Freeze route inventory and write registration failure tests.**

  Generate/check `docs/architecture/generated/route-inventory.md`. Add a test asserting every pre-existing public method/path from `routes.py` remains registered once, has unchanged request/response schema name, and has the same authorization dependency. Add an integration test for one success and one 403/404 path per extracted router.

  Run:

  ```bash
  PYTHONPATH=$(pwd) .venv/bin/python -m pytest tests/apps/cosa/test_router_registration.py tests/apps/cosa/test_routes_contract.py -q
  ```

  Expected: FAIL before extraction.

- [ ] **Step 2: Extract pure shared dependencies.**

  Move plane lookup, actor construction, workspace authorization, pagination parsing, and error-envelope helpers into `dependencies.py`. Do not swallow plane startup errors, use an `InMemory` default, or accept workspace IDs without membership verification.

- [ ] **Step 3: Move routes by bounded capability group.**

  Move one router group at a time in this order: conversations, runs, approvals, sessions, artifacts, connectors, schedules, knowledge ingestion. After each group, import its `APIRouter` in `routes.py` or main registration, preserve paths/tags/dependencies, run the two focused tests, and commit only after all eight groups pass. `routes.py` ends as compatibility registration plus route imports; it must not retain duplicate endpoint definitions.

- [ ] **Step 4: Verify inventory, app behavior, and size boundary.**

  Run:

  ```bash
  PYTHONPATH=$(pwd) .venv/bin/python -m pytest tests/apps/cosa/test_router_registration.py tests/apps/cosa/test_routes_contract.py -q
  make route-inventory-check
  test $(wc -l < apps/cosa/api/routes.py) -lt 250
  ```

  Expected: all pass. If a truly legacy endpoint cannot move, document the exact endpoint and blocking dependency in the ledger; do not satisfy the line check by deleting behavior.

- [ ] **Step 5: Commit router extraction.**

  ```bash
  git add apps/cosa/api/dependencies.py apps/cosa/api/routers apps/cosa/api/routes.py apps/cosa/api/app.py tests/apps/cosa/test_router_registration.py tests/apps/cosa/test_routes_contract.py docs/architecture/generated/route-inventory.md docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md
  git commit -m "refactor(agent): split agent api routers by capability"
  ```

## Task 2: Extract Workforce ports, adapters, and application service

**Files:**

- Create: `packages/agent/workforce/ports.py`
- Create: `packages/agent/workforce/postgres.py`
- Create: `packages/agent/workforce/in_memory.py`
- Create: `packages/agent/workforce/service.py`
- Modify: `packages/agent/workforce/repository.py`
- Modify: `apps/cosa/composition/agent_plane.py`
- Modify: `apps/cosa/api/workforce_routes.py`
- Create: `tests/agent/workforce/test_service.py`
- Modify: `tests/agent/workforce/test_repository.py`
- Modify: `tests/apps/cosa/test_workforce_routes.py`

**Interfaces:**

```python
@runtime_checkable
class WorkforceRepository(Protocol):
    async def list_assignments(self, workspace_id: str, *, status: str | None = None) -> list[WorkforceAssignmentRecord]: ...
    async def assign(self, command: AssignWorkforceCommand) -> WorkforceAssignmentRecord: ...

class WorkforceService:
    def __init__(self, repository: WorkforceRepository, membership: MembershipPort) -> None: ...
```

- [ ] **Step 1: Write service and adapter contract tests before moving code.**

  Cover: workspace isolation, string Snowflake/UUID preservation, empty-assignment result as a real empty result, membership rejection, durable round-trip through Postgres, and database outage propagated as an explicit failure. The in-memory adapter is allowed in `tests/agent/workforce` only to test service control flow.

  Run:

  ```bash
  PYTHONPATH=$(pwd) .venv/bin/python -m pytest tests/agent/workforce/test_service.py tests/agent/workforce/test_repository.py tests/apps/cosa/test_workforce_routes.py -q
  ```

  Expected: FAIL before ports/service are present.

- [ ] **Step 2: Split repository responsibilities without changing data ownership.**

  Define all record/command Protocol types in `ports.py`. Move SQLAlchemy queries and mapping to `postgres.py`; use a production constructor that requires configured session factory/database URL. Put existing in-memory implementation in `in_memory.py`, guarded as test-only. `repository.py` re-exports the public names temporarily and contains a removal TODO pointing to this plan task.

- [ ] **Step 3: Make composition fail closed and route through service.**

  `AgentPlane` construction injects `PostgresWorkforceRepository` in all non-test environments. There must be no `or InMemoryWorkforceRepository()` fallback. `workforce_routes.py` parses HTTP and delegates to `WorkforceService`; it cannot instantiate a repository.

- [ ] **Step 4: Verify direct and real-dependency tests.**

  Run focused tests plus the existing required Postgres test with `AGENT_DATABASE_URL` set to the isolated test database. A skipped required repository test is failure for this task, not a pass.

  Expected: PASS with a real database adapter.

- [ ] **Step 5: Commit.**

  ```bash
  git add packages/agent/workforce apps/cosa/composition/agent_plane.py apps/cosa/api/workforce_routes.py tests/agent/workforce tests/apps/cosa/test_workforce_routes.py docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md
  git commit -m "refactor(agent): separate workforce ports and adapters"
  ```

## Task 3: Implement durable Settings policy; remove fabricated registry fallbacks

**Files:**

- Create: `packages/agent/settings/__init__.py`
- Create: `packages/agent/settings/ports.py`
- Create: `packages/agent/settings/postgres.py`
- Create: `packages/agent/settings/service.py`
- Create: additive `packages/agent/migrations/024_workspace_skill_settings.sql`
- Create: additive `packages/agent/migrations/024_workspace_skill_settings.down.sql`
- Modify: `apps/cosa/api/settings_routes.py`
- Modify: `apps/cosa/composition/agent_plane.py`
- Modify: `apps/cosa/api/mvp_contracts_generated.py` only via `make mvp-contracts-gen` if the contract needs an explicit unavailable error
- Create: `tests/agent/settings/__init__.py`
- Create: `tests/agent/settings/test_service.py`
- Create: `tests/agent/settings/test_postgres.py`
- Modify: `tests/apps/cosa/test_settings_routes.py`

**Interfaces:**

```python
class SkillRegistryPort(Protocol):
    async def get(self, skill_id: str) -> RegisteredSkill | None: ...

class WorkspaceSkillSettingsRepository(Protocol):
    async def get(self, workspace_id: str, skill_id: str) -> WorkspaceSkillSetting | None: ...
    async def upsert(self, setting: WorkspaceSkillSetting) -> WorkspaceSkillSetting: ...
```

The persistent record holds only user/admin-selected mutable policy (for example enabled/mode) plus audit fields. Canonical skill title/version/provider come only from the configured registry record, never from a route default.

- [ ] **Step 1: Write failing truth and availability tests.**

  Cover: registry unavailable becomes typed 503/explicit unavailable, not `[]`; unknown skill is 404; known registry skill without workspace override returns the registry data plus explicit `not_configured` state; update creates/updates a durable policy record; returned title/version/provider are registry-sourced; no success response includes `Workspace configured skill`, `1.0.0`, `cosa_platform`, `supervised`, or a generated “now” value unless stored/registered data actually equals it.

  Run:

  ```bash
  PYTHONPATH=$(pwd) .venv/bin/python -m pytest tests/agent/settings/test_service.py tests/agent/settings/test_postgres.py tests/apps/cosa/test_settings_routes.py -q
  ```

  Expected: FAIL because current route catches registry errors and builds fake settings.

- [ ] **Step 2: Add only the additive workspace-policy migration.**

  Table must have workspace/skill unique key, selected policy fields, `created_at`, `updated_at`, `created_by`, `updated_by`, and no duplicated canonical registry content. Write up/down scripts. Execute against an isolated database: apply, verify schema, rollback, verify absent, reapply.

- [ ] **Step 3: Implement service and make routes thin.**

  Service composes the real registry and policy repository. Route translates authenticated request to service input and publishes existing generated envelope. It must preserve exception causality and must never `except Exception: pass`. Register the service in composition with fail-fast configuration.

- [ ] **Step 4: Verify and commit.**

  Run focused tests, migration proof, `make lint`, and `make typecheck-py`.

  Expected: PASS; `rg -n "Workspace configured skill|cosa_platform|except Exception.*pass" apps/cosa/api/settings_routes.py` returns no fabricated fallback.

  ```bash
  git add packages/agent/settings packages/agent/migrations/024_workspace_skill_settings.sql packages/agent/migrations/024_workspace_skill_settings.down.sql apps/cosa/api/settings_routes.py apps/cosa/composition/agent_plane.py apps/cosa/api/mvp_contracts_generated.py tests/agent/settings tests/apps/cosa/test_settings_routes.py docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md
  git commit -m "fix(agent): persist settings and expose registry truth"
  ```

## Task 4: Implement real Vault object lifecycle and split Vault repository

**Files:**

- Create: `packages/agent/vault/ports.py`
- Create: `packages/agent/vault/postgres.py`
- Create: `packages/agent/vault/in_memory.py`
- Modify: `packages/agent/vault/object_store.py`
- Create: `packages/agent/vault/ingestion.py`
- Create: `packages/agent/vault/service.py`
- Create: additive `packages/agent/migrations/025_vault_ingestion_links.sql`
- Create: additive `packages/agent/migrations/025_vault_ingestion_links.down.sql`
- Modify: `packages/agent/requirements.txt`
- Modify: `packages/agent/vault/repository.py`
- Modify: `apps/cosa/api/vault_routes.py`
- Modify: `apps/cosa/composition/agent_plane.py`
- Modify: `apps/cosa/api/routes.py`
- Modify: `apps/cosa/knowledge_ingestion/handler.py`
- Modify: `apps/cosa/worker/main.py`
- Create: `tests/agent/vault/test_service.py`
- Modify: `tests/agent/vault/test_repository.py`
- Modify: `tests/agent/vault/test_workspace_object_store.py`
- Modify: `tests/apps/cosa/test_vault_routes.py`

**Interfaces:**

```python
class WorkspaceObjectStore(Protocol):
    async def create_upload(self, *, workspace_id: str, document_id: str, content_type: str, size_bytes: int) -> UploadTicket: ...
    async def head(self, object_key: str) -> ObjectMetadata: ...

class VaultIngestionPort(Protocol):
    async def enqueue(self, document_id: str, version_id: str, object_key: str) -> IngestionJob: ...
```

State transition:

```text
DRAFT --real presigned ticket--> UPLOADING --object HEAD/checksum--> STORED
STORED --actual enqueue--> PROCESSING --persisted worker success--> INDEXED
PROCESSING --persisted worker failure--> FAILED
```

No HTTP create/upload/confirm endpoint may jump directly to `INDEXED`.

- [ ] **Step 1: Write failing lifecycle tests.**

  Cover ticket URL/object key comes from a `WorkspaceObjectStore` result; a failed/missing object HEAD cannot create a version; confirmed object metadata is persisted; ingestion enqueue failure leaves a retriable explicit failure; `INDEXED` only follows a persisted worker completion; tenant isolation includes object prefix/key ownership. Test the new `S3WorkspaceObjectStore` adapter against the isolated MinIO service, not a fake URL string. Add boto3 to `packages/agent/requirements.txt`; do not rely on the unrelated `apps/cosa/requirements.txt` to make reusable package code import.

  Run:

  ```bash
  PYTHONPATH=$(pwd) .venv/bin/python -m pytest tests/agent/vault/test_service.py tests/agent/vault/test_workspace_object_store.py tests/agent/vault/test_repository.py tests/apps/cosa/test_vault_routes.py -q
  ```

  Expected: FAIL because current route manufactures a ticket, object ref, and `INDEXED` state.

- [ ] **Step 2: Inspect existing storage/knowledge contracts before adding one.**

  `packages/agent/vault/object_store.py` currently has the local-filesystem `WorkspaceObjectStore`; `apps/cosa/api/routes.py`, `apps/cosa/knowledge_ingestion/handler.py`, and `apps/cosa/worker/main.py` are the existing knowledge-ingestion route/worker path. Preserve the store’s safe workspace key layout; extend its abstract contract with `create_upload_ticket` and `head`, implement both in `LocalFilesystemWorkspaceStore` for local development, and add `S3WorkspaceObjectStore` for MinIO/S3 with presigned PUT and HEAD verification. Do not create another knowledge worker.

  Migration `025_vault_ingestion_links.sql` adds `ingestion_id TEXT NULL`, `ingestion_state TEXT NULL`, and `ingestion_completed_at TIMESTAMPTZ NULL` to `vault.documents`, plus a workspace/ingestion index. Its down migration removes exactly those columns/index. Apply/rollback/reapply it on an isolated database before writing application code.

- [ ] **Step 3: Extract ports/adapters and implement only real lifecycle transitions.**

  Move SQL into `postgres.py`; define service orchestration in `service.py`; implement MinIO/S3 adapter in `object_store.py` using configured endpoint/credentials; add an ingestion adapter that calls the existing knowledge-ingestion route/worker contract and persists its returned ingestion ID/state. `handler.py` updates the linked Vault document only after its durable ingestion outcome is known; `worker/main.py` preserves this handoff. In production composition all adapters must be configured or startup must fail. In-memory classes remain test-only. Route delegates and returns durable document/version IDs plus current truthful state.

- [ ] **Step 4: Run real storage proof and scanner.**

  Start the isolated MinIO/Postgres dependencies described in Task 6. Run focused tests and:

  ```bash
  rg -n "upload\.example|fake.*ticket|INDEXED|presigned" apps/cosa/api/vault_routes.py packages/agent/vault -g '*.py'
  make lint typecheck-py
  ```

  Expected: the scan shows real lifecycle code only; no hardcoded upload host, fabricated URL, or immediate `INDEXED` assignment in the route.

- [ ] **Step 5: Commit.**

  ```bash
  git add packages/agent/requirements.txt packages/agent/vault packages/agent/migrations/025_vault_ingestion_links.sql packages/agent/migrations/025_vault_ingestion_links.down.sql apps/cosa/api/vault_routes.py apps/cosa/api/routes.py apps/cosa/knowledge_ingestion/handler.py apps/cosa/worker/main.py apps/cosa/composition/agent_plane.py tests/agent/vault tests/apps/cosa/test_vault_routes.py docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md
  git commit -m "fix(agent): make vault lifecycle storage-backed"
  ```

## Task 5: Fail closed for runtime signal configuration and preserve evidence

**Files:**

- Create: `apps/cosa/events/runtime_signal_config.py`
- Modify: `apps/cosa/events/runtime_signal.py`
- Modify: `apps/cosa/config/planes.py`
- Modify: `.env.prod.example`
- Modify: `docker-compose.yml`
- Create: `tests/apps/cosa/events/test_runtime_signal_config.py`
- Modify: `tests/apps/cosa/test_runtime_signal_delivery.py`

**Interfaces:**

```python
@dataclass(frozen=True)
class RuntimeSignalConfig:
    company_base_url: str
    service_token: SecretStr
    environment: Literal["local", "test", "staging", "production"]
```

- [ ] **Step 1: Write failing environment tests.**

  Test that staging/production with missing Company URL/token fails configuration; loopback URL and `dev-worker-service-token` are rejected outside `local`/`test`; local test config may use an explicit injected local value; outbound payload preserves source-provided evidence fields unchanged and omits unavailable values.

  Run: `PYTHONPATH=$(pwd) .venv/bin/python -m pytest tests/apps/cosa/events/test_runtime_signal_config.py tests/apps/cosa/test_runtime_signal_delivery.py -q`

  Expected: FAIL because runtime signal currently supplies implicit loopback/token defaults.

- [ ] **Step 2: Implement validated config and injection.**

  Parse once at startup/composition. Reject invalid values with an actionable configuration error before workers run. `runtime_signal.py` takes `RuntimeSignalConfig`; it does not read environment variables directly or invent defaults. Update examples to show variable names with no live values.

- [ ] **Step 3: Verify and commit.**

  Run focused tests, `make lint`, `make typecheck-py`.

  Expected: PASS; `rg -n "127\.0\.0\.1:4000|dev-worker-service-token" apps/cosa/events` returns no production default.

  ```bash
  git add apps/cosa/events/runtime_signal_config.py apps/cosa/events/runtime_signal.py apps/cosa/config/planes.py .env.prod.example docker-compose.yml tests/apps/cosa/events/test_runtime_signal_config.py tests/apps/cosa/test_runtime_signal_delivery.py
  git commit -m "fix(agent): require runtime signal configuration"
  ```

## Task 6: Build a required, real cross-plane MVP E2E harness

**Files:**

- Create: `docker-compose.mvp-e2e.yml`
- Create: `scripts/run_mvp_real_e2e.sh`
- Modify: `tests/e2e/mvp_stack.py`
- Modify: `tests/e2e/conftest.py`
- Modify: `tests/e2e/test_mvp_strategy_runtime_http.py`
- Modify: `tests/e2e/test_mvp_marketing_http.py`
- Modify: `tests/e2e/test_mvp_workforce_http.py`
- Modify: `tests/e2e/test_mvp_vault_http.py`
- Modify: `tests/e2e/test_mvp_settings_http.py`
- Modify: every other matching `tests/e2e/test_mvp_*.py`
- Modify: `Makefile`
- Modify: `.github/workflows/quality.yml`
- Modify: `docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md`
- Test: `tests/quality/test_mvp_e2e_purity.py`

**Interfaces:**

```bash
make mvp-real-e2e
```

This command must boot/use: isolated PostgreSQL, isolated MinIO, Company service, Control service, and Agent FastAPI service; wait for authenticated health/readiness; migrate each owned schema; seed only deterministic authorized tenant/membership prerequisites through owner APIs or migrations; execute HTTP calls over actual network sockets; and tear down on completion while retaining logs on failure.

- [ ] **Step 1: Classify and replace every simulated MVP E2E.**

  Run:

  ```bash
  rg -n "ASGITransport|MockTransport|AsyncMock|FakeSDKModel|InMemory|pytest\.skip|monkeypatch" tests/e2e/test_mvp_*.py tests/e2e/mvp_stack.py tests/e2e/conftest.py
  rg -n "real_company_service" tests/e2e
  ```

  Move tests requiring in-process/mocked dependencies to `tests/integration/` with an appropriate filename. Do not rename them to E2E. Rewrite required `test_mvp_*.py` so they use `MvpStack` endpoints/credentials from real composed services and never skip.

- [ ] **Step 2: Write a red harness readiness test and compose contract.**

  Test `run_mvp_real_e2e.sh` exits non-zero if a required service cannot become ready, a migration fails, expected environment variables are absent, or requested endpoints point to loopback processes outside the declared compose network. Test it prints collected logs/endpoint evidence on failure without credentials.

  Run: `PYTHONPATH=$(pwd) .venv/bin/python -m pytest tests/quality/test_mvp_e2e_purity.py -q`

  Expected: purity test may fail while prohibited code remains; preserve the failure until simulated code is removed.

- [ ] **Step 3: Build the compose/harness with explicit real dependencies.**

  Compose services must expose only test ports, have independent Postgres databases/schemas per owner, use a disposable MinIO bucket/prefix, and receive explicit runtime signal credentials. The script creates a unique run ID, uses it in database/bucket names, waits by health endpoint, applies migrations, runs `pytest tests/e2e/test_mvp_*.py -q`, then tears down. Do not run `docker compose down -v` against an unspecified project; use the unique project name and explicit compose file.

- [ ] **Step 4: Implement capability evidence in real HTTP tests.**

  Each enabled capability has at least one real request proving authorization and its truthful result:

  - Canvas/Runtime: seed real Company state and verify observed versus not-observed source presentation.
  - Marketing: create/read a Company-owned context/evidence record and verify tenant isolation.
  - Workforce: create/list Agent-owned assignment through actual Agent API/database.
  - Vault: upload bytes to the issued real MinIO ticket, confirm object, run/observe actual ingestion completion, then read `INDEXED`; separately verify pre-ingestion state.
  - Settings: use a configured actual registry and persisted workspace policy, including registry-unavailable error.

  Seed data is allowed only as controlled precondition in the isolated harness. It must have an owner, source, and cleanup; it cannot be a response fallback.

- [ ] **Step 5: Prove purity, running stack, and update only observed ledger rows.**

  Run:

  ```bash
  make mvp-e2e-purity-check
  make mvp-real-e2e
  ```

  Expected: both pass with no skip. Update every actually exercised capability row to `VERIFIED`, putting this commit hash and exact test name in `real_e2e_test`. Keep unexercised rows `BLOCKED`.

- [ ] **Step 6: Wire CI and commit.**

  CI must run `make mvp-e2e-purity-check` on every relevant change and run the composed real E2E in a runner with Docker. Do not mark a test optional because the runner lacks Docker; provision a compatible runner or retain a blocking status.

  ```bash
  git add docker-compose.mvp-e2e.yml scripts/run_mvp_real_e2e.sh tests/e2e tests/integration Makefile .github/workflows/quality.yml docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md tests/quality/test_mvp_e2e_purity.py
  git commit -m "test: run mvp e2e against real service stack"
  ```

## Task 7: Retire Agent repository compatibility shims only after caller proof

**Files:**

- Modify/Delete only after scans are empty: `packages/agent/workforce/repository.py`
- Modify/Delete only after scans are empty: `packages/agent/vault/repository.py`
- Modify: remaining imports/callers found by Step 1
- Modify: `docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md`
- Test: all Workforce/Vault service, Postgres, API, and real E2E tests above

- [ ] **Step 1: Inventory production imports and SQL content.**

  Run:

  ```bash
  rg -n "agent\.(workforce|vault)\.repository|from .*workforce\.repository|from .*vault\.repository" apps packages -g '*.py'
  rg -n "select\(|insert\(|update\(|delete\(" packages/agent/workforce/repository.py packages/agent/vault/repository.py
  ```

  Expected: all active production imports are known. Tests may keep compatibility imports only until migrated in the same task.

- [ ] **Step 2: Migrate each caller to a named port, service, or Postgres adapter.**

  Write/update caller test first. Composition chooses concrete adapters; domain/application callers depend on Protocols. No caller should need the old omnibus repository class.

- [ ] **Step 3: Prove no compatibility reliance remains.**

  Run caller scans, focused test suites, `make typecheck-py`, and `make mvp-real-e2e`.

  Expected: no production import; repository shims either delete cleanly or contain only intentional public re-export aliases with an expiry recorded in ledger.

- [ ] **Step 4: Commit.**

  ```bash
  git add packages/agent/workforce packages/agent/vault apps/cosa docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md
  git commit -m "refactor(agent): retire repository compatibility shims"
  ```
