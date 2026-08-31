# Full MVP Settings and Release Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Settings display and manage only real membership/policy, connector, skill and runtime-node state, then produce migration, cross-plane and release evidence without overstating infrastructure readiness.

**Architecture:** Control Plane remains owner of platform identity, connector grants and runtime-node registry; Agent Platform remains owner of skills. Human Settings reads purpose-built redacted routes, while worker-only `/cosa/*` routes stay inaccessible to Flutter. The final tranche hardens token audience checks, validates all migrations on isolated databases, boots real local services for cross-plane scenarios, and records exactly what was or was not verified in release documentation.

**Tech Stack:** TypeScript/Encore/Drizzle, Python/FastAPI/Pydantic, Flutter/Dart/GetX, Postgres/MinIO/Docker Compose, Vitest, pytest and Flutter test.

**Spec:** `docs/superpowers/specs/2026-08-31-full-mvp-contract-first-truth-only-design.md`

## Global Constraints

- Complete the Foundation plan before enabling Settings capabilities.
- No Settings response contains raw secret values, connector secret references, refresh tokens, worker service tokens or device private material.
- Human Settings routes verify the user platform token audience/issuer and current workspace membership before reading/mutating a workspace. Worker endpoints retain worker-service audience/role checks and are not repurposed for browsers.
- `connected`, `enabled`, `online` and `healthy` require a confirmed owner record plus timestamp. Absent, expired, revoked, stale and unknown states retain their real names.
- All production/staging checks must fail closed. An unavailable Company/Control Plane/Agent dependency is an unavailable state, never a guessed role or connector state.
- Migration rehearsal and E2E tests use isolated real databases/services. A test skip due to unavailable Docker/Encore/Postgres/MinIO is recorded as unverified evidence, not converted into a pass.
- Edge rate limiting/WAF requires separate infrastructure authorization and an observed 429 test. Application changes may add a verifier/runbook but must not claim the edge control is deployed.

---

## File map

| File | Responsibility |
|---|---|
| `services/cosa/services/token.service.ts` | Enforces platform JWT audience/issuer for human Control Plane routes |
| `services/company/identity/services/platform.client.ts` | Enforces the same platform token audience before Company membership RPC calls |
| `services/cosa/migrations/28_workspace_settings_audit.up.sql` | Append-only workspace Settings audit events and indexes |
| `services/cosa/migrations/28_workspace_settings_audit.down.sql` | Safe removal of the new audit table only |
| `services/cosa/models/db.ts` | Control Plane Settings audit Drizzle model |
| `services/cosa/services/workspace-settings.service.ts` | Redacted connector/runtime-node/membership settings read/write orchestration |
| `services/cosa/handlers/workspace-settings.handler.ts` | Human `/platform/workspaces/:workspaceId/*` settings routes |
| `services/cosa/handlers/index.ts` | Exports Settings handlers |
| `services/cosa/services/workspace-connector.service.ts` | Returns redacted status, stable IDs and no secret references |
| `services/cosa/services/runtime-node-registry.service.ts` | Reuses observed presence for human read/revoke routes |
| `apps/cosa/api/settings_routes.py` | Agent-owned skill configuration/status read surface for Settings |
| `apps/cosa/api/app.py` | Registers Agent settings router |
| `services/cosa/tests/workspace-settings.test.ts` | Platform membership/audience/redaction/node/connector tests |
| `services/cosa/tests/control-plane.test.ts` | Platform token audience/issuer regression tests |
| `services/company/identity/tests/platform-client.test.ts` | Company platform client token-audience tests |
| `tests/apps/cosa/test_settings_routes.py` | Agent skill settings identity/source tests |
| `frontend/lib/modules/settings/models/settings_models.dart` | Typed membership/connector/node/skill DTOs |
| `frontend/lib/modules/settings/services/settings_mvp_service.dart` | Typed Control Plane and Agent Settings client |
| `frontend/lib/modules/settings/services/connectors_service.dart` | Compatibility delegate with `/connectors/*` raw paths removed |
| `frontend/lib/modules/settings/services/developer_service.dart` | Compatibility delegate with `/devices/*` raw paths removed |
| `frontend/lib/modules/settings/controllers/settings_controller.dart` | Result-aware Settings state |
| `frontend/lib/modules/settings/views/settings_view.dart` | Honest settings tabs/states |
| `frontend/lib/modules/settings/views/settings_extensions_page.dart` | Skill/plugin status and policy state |
| `frontend/test/settings_mvp_service_test.dart` | Typed source/failure/redaction client tests |
| `frontend/test/settings_mvp_views_test.dart` | Connector/node/skill widget states |
| `tests/e2e/mvp_stack.py` | Actual local Company + Control Plane + Agent + MinIO/Postgres test stack, no mock HTTP transport |
| `tests/e2e/test_mvp_settings_http.py` | Real Settings/membership/connector/node E2E |
| `tests/e2e/test_mvp_release_smoke.py` | Full cross-plane MVP smoke and no-mock evidence assertions |
| `scripts/verify_edge_rate_limit.sh` | Authorized edge endpoint 429 verifier; makes no deployment changes |
| `docs/operations/release-security-checklist.md` | Evidence-based release checklist/status |
| `docs/operations/deployment.md` | Accurate deployment/WAF prerequisites |
| `deploy/central_vps/README.md` | Removes concrete-looking historic credentials and marks examples safely |

## Task 1: Harden token audiences and add redacted Control Plane Settings routes

**Files:**

- Modify: `services/cosa/services/token.service.ts`
- Modify: `services/company/identity/services/platform.client.ts`
- Create: `services/cosa/migrations/28_workspace_settings_audit.up.sql`
- Create: `services/cosa/migrations/28_workspace_settings_audit.down.sql`
- Modify: `services/cosa/models/db.ts`
- Create: `services/cosa/services/workspace-settings.service.ts`
- Create: `services/cosa/handlers/workspace-settings.handler.ts`
- Modify: `services/cosa/handlers/index.ts`
- Modify: `services/cosa/services/workspace-connector.service.ts`
- Test: `services/cosa/tests/workspace-settings.test.ts`
- Test: `services/cosa/tests/control-plane.test.ts`
- Test: `services/company/identity/tests/platform-client.test.ts`

**Interfaces:**

- Produces `verifyPlatformToken(token)` that requires `aud: "cosa"` and `iss: "cosa_platform"` for human platform tokens.
- Produces these manifest routes:

  ```text
  GET  /platform/workspaces/:workspaceId/members
  GET  /platform/workspaces/:workspaceId/connectors
  POST /platform/workspaces/:workspaceId/connectors/:connectorKey/install
  POST /platform/workspaces/:workspaceId/connectors/:connectorKey/revoke
  GET  /platform/workspaces/:workspaceId/runtime-nodes
  POST /platform/workspaces/:workspaceId/runtime-nodes/:nodeId/revoke
  GET  /platform/workspaces/:workspaceId/audit-events
  ```

- Human responses use only `id`, `key`, `state`, scopes, owner-safe display labels, expiry/observation timestamps and policy reason. They never expose `secretRef`.

- [ ] **Step 1: Write audience, membership and redaction tests.**

  ```ts
  it("rejects a valid signature with worker audience on a human settings route", async () => {
    const workerToken = signWorkerServiceToken("worker-1", "1001");
    await expect(listWorkspaceSettings({ authorization: `Bearer ${workerToken}`, workspaceId: "1001" }))
      .rejects.toMatchObject({ code: "unauthenticated" });
  });

  it("never serializes connector secretRef", async () => {
    const result = await listConnectorStatuses(memberToken, "1001");
    expect(JSON.stringify(result)).not.toContain("secret://");
    expect(result.data[0]).toEqual(expect.objectContaining({ state: "enabled", observedAt: expect.any(String) }));
  });

  it("returns offline when the last real heartbeat is stale", async () => {
    expect((await listRuntimeNodes(memberToken, "1001")).data[0].presence).toBe("OFFLINE");
  });
  ```

- [ ] **Step 2: Run focused TypeScript tests and verify missing behavior fails.**

  Run:

  ```bash
  cd services/cosa && npx vitest run tests/workspace-settings.test.ts tests/control-plane.test.ts
  cd services/company && npx vitest run identity/tests/platform-client.test.ts
  ```

  Expected: FAIL until settings modules and audience restrictions exist.

- [ ] **Step 3: Enforce exact platform-token verification.**

  Change both `verifyPlatformToken` implementations to use `jwt.verify(token, secret, { audience: "cosa", issuer: "cosa_platform" })` and convert verify exceptions to existing typed unauthenticated errors. Retain the separate `control_plane` audience/worker-role path in `requireWorkerServiceAuth`; do not merge human/worker token logic. Update all tests that previously used a token without the expected audience/issuer.

- [ ] **Step 4: Implement redacted settings service/handlers.**

  Add `control_plane.workspace_settings_audit_events` in migration 28 with `event_id BIGINT`, `workspace_id BIGINT`, `actor_id TEXT`, `event_type TEXT`, `target_kind TEXT`, `target_id TEXT`, redacted `details JSONB`, and `created_at`, plus `(workspace_id, created_at DESC)` index. The event table is append-only: no update/delete application route. Rehearse migration 28 apply/rollback/reapply with the Control Plane migration runner before exposing the read route.

  `WorkspaceSettingsService` first verifies the human token, then calls the existing Company membership verifier for the requested workspace. It maps existing connector installation/authorization/grant records to:

  ```ts
  interface ConnectorStatusView {
    id: string; connectorKey: string; state: "not_connected" | "enabled" | "expired" | "revoked" | "unavailable";
    grantedScopes: string[]; observedAt: string | null; expiresAt: string | null; reason: string | null;
  }
  ```

  It maps `RuntimeNodeView` directly from its computed heartbeat state. Install/revoke uses existing services, verified membership and founder/co-founder policy, appends a redacted audit event with the authenticated actor and true result, and returns no raw secret/worker token. `GET audit-events` returns only those immutable stored records. Replace random connector record ID generation with the existing Control Plane ID generator before exposing new writes.

- [ ] **Step 5: Run focused tests and commit.**

  Run:

  ```bash
  cd services/cosa && npx vitest run tests/workspace-settings.test.ts tests/control-plane.test.ts tests/workspace-connector.test.ts
  cd services/company && npx vitest run identity/tests/platform-client.test.ts
  ```

  ```bash
  git add services/cosa/services/token.service.ts services/company/identity/services/platform.client.ts services/cosa/migrations/28_workspace_settings_audit.* services/cosa/models/db.ts services/cosa/services/workspace-settings.service.ts services/cosa/handlers/workspace-settings.handler.ts services/cosa/handlers/index.ts services/cosa/services/workspace-connector.service.ts services/cosa/tests services/company/identity/tests/platform-client.test.ts
  git commit -m "feat: add secure workspace settings routes"
  ```

## Task 2: Expose truthful Agent skill Settings and migrate Flutter Settings UI

**Files:**

- Create: `apps/cosa/api/settings_routes.py`
- Modify: `apps/cosa/api/app.py`
- Test: `tests/apps/cosa/test_settings_routes.py`
- Create: `frontend/lib/modules/settings/models/settings_models.dart`
- Create: `frontend/lib/modules/settings/services/settings_mvp_service.dart`
- Modify: `frontend/lib/modules/settings/services/connectors_service.dart`
- Modify: `frontend/lib/modules/settings/services/developer_service.dart`
- Modify: `frontend/lib/modules/settings/controllers/settings_controller.dart`
- Modify: `frontend/lib/modules/settings/views/settings_view.dart`
- Modify: `frontend/lib/modules/settings/views/settings_extensions_page.dart`
- Test: `frontend/test/settings_mvp_service_test.dart`
- Test: `frontend/test/settings_mvp_views_test.dart`

**Interfaces:**

- Produces `GET /agent/settings/skills` from real published skill registry/assignment/policy data.
- Produces Flutter `SettingsMvpService` methods `loadMembers`, `loadConnectors`, `installConnector`, `revokeConnector`, `loadRuntimeNodes`, `revokeRuntimeNode`, and `loadSkills`, all returning `ApiResult`.

- [ ] **Step 1: Write Agent and Flutter failure/truth tests first.**

  ```python
  async def test_skill_settings_show_registry_state_not_a_fake_extension(client, identity) -> None:
      response = await client.get("/agent/settings/skills", headers=identity.headers)
      assert response.status_code == 200
      assert response.json()["meta"]["sources"][0]["kind"] == "agent_db"
      assert all("installed" in item for item in response.json()["data"])
  ```

  ```dart
  testWidgets('unavailable connector is not shown connected', (tester) async {
    await tester.pumpWidget(SettingsView.withConnectorFailure(ApiFailureCode.unavailable));
    expect(find.text('Không lấy được trạng thái connector'), findsOneWidget);
    expect(find.text('Đã kết nối'), findsNothing);
  });
  ```

- [ ] **Step 2: Run focused tests and verify they fail before migration.**

  Run:

  ```bash
  PYTHONPATH=$(pwd) python3 -m pytest tests/apps/cosa/test_settings_routes.py -q
  cd frontend && flutter test test/settings_mvp_service_test.dart test/settings_mvp_views_test.dart
  ```

  Expected: FAIL because routes/models/services do not exist and legacy Settings clients collapse failures.

- [ ] **Step 3: Implement Agent skill Settings route.**

  The route depends on `get_authenticated_identity`, queries the published Skill registry and workspace assignment/policy state, and returns `MvpSuccess`. A system-owned published skill is labelled `available`; it is `installed` only if a real workspace assignment/configuration says so. A missing registry/service becomes unavailable, not a fabricated list. Do not expose source code, secret configuration or test fixture skills.

- [ ] **Step 4: Replace direct `/connectors/*` and `/devices/*` Flutter calls.**

  `SettingsMvpService` uses generated platform/agent endpoints and no raw path strings. Make `connectors_service.dart` and `developer_service.dart` delegate to it temporarily, then remove direct calls to `/connectors/*`, `/devices/*`, `return []`, `return null`, and status-only `bool` results from enabled Settings paths. Controller state stores the `ApiFailure`; views render not-connected, expired, revoked, offline, not-observed and unavailable distinctly with server timestamps.

- [ ] **Step 5: Ensure dangerous actions retain server policy.**

  Connector install/revoke and node revoke buttons require server-returned capability; the Flutter UI does not infer founder/admin from a display title. Skills/extensions show published/version/policy state and may link to their real approval/configuration route; they do not offer an unbacked “enable” toggle.

- [ ] **Step 6: Run Flutter/API verification, enable Settings entries, and commit.**

  Run:

  ```bash
  PYTHONPATH=$(pwd) python3 -m pytest tests/apps/cosa/test_settings_routes.py -q
  cd frontend && flutter test test/settings_mvp_service_test.dart test/settings_mvp_views_test.dart
  cd frontend && flutter analyze
  node ../scripts/gen-mvp-contracts.mjs
  ```

  ```bash
  git add apps/cosa/api/settings_routes.py apps/cosa/api/app.py tests/apps/cosa/test_settings_routes.py frontend/lib/modules/settings frontend/test/settings_mvp_service_test.dart frontend/test/settings_mvp_views_test.dart shared/contracts/mvp-surface.json frontend/lib/core/network/mvp_endpoints.g.dart docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md
  git commit -m "feat: wire truthful settings ui"
  ```

## Task 3: Build the real cross-plane MVP test harness and Settings scenario

**Files:**

- Create: `tests/e2e/mvp_stack.py`
- Modify: `tests/e2e/conftest.py`
- Create: `tests/e2e/test_mvp_settings_http.py`
- Create: `tests/e2e/test_mvp_release_smoke.py`
- Modify: `Makefile`

**Interfaces:**

- Produces `real_mvp_stack` fixture with actual ephemeral/isolated Postgres schemas, migrated Company/Control Plane/Agent services, configured MinIO/local object store and HTTP clients that never use `httpx.MockTransport`.
- Earlier domain E2E tests consume this fixture to prove their cross-plane flows.

- [ ] **Step 1: Write a harness preflight test that refuses fake transport.**

  ```python
  def test_real_mvp_stack_requires_real_processes(real_mvp_stack):
      assert real_mvp_stack.company.base_url.startswith("http://127.0.0.1:")
      assert real_mvp_stack.agent.base_url.startswith("http://127.0.0.1:")
      assert real_mvp_stack.uses_mock_transport is False
      assert real_mvp_stack.migration_versions["company"]
      assert real_mvp_stack.migration_versions["agent"]
  ```

- [ ] **Step 2: Run it before the fixture exists.**

  Run: `PYTHONPATH=$(pwd) python3 -m pytest tests/e2e/test_mvp_release_smoke.py -q`

  Expected: FAIL/explicit SKIP because `real_mvp_stack` has not been implemented. It must not auto-replace itself with a fake ASGI client.

- [ ] **Step 3: Implement startup, migration and cleanup.**

  Reuse the existing `real_company_service` principles in `tests/e2e/conftest.py`: probe dependencies, run actual migration commands, start process/container services on free loopback ports, wait for real readiness, provision two real workspace identities, and terminate processes in `finally`. Configure the Agent service with real `AGENT_DATABASE_URL`, Company/Control Plane URLs, service tokens and a real MinIO/local workspace store. The fixture has a `skip_reason` only when a prerequisite is genuinely unavailable; it never returns a partial/mocked stack.

- [ ] **Step 4: Write and run the Settings real-service scenario.**

  ```python
  def test_member_connector_node_and_skill_status_are_truthful(real_mvp_stack, workspace_a, workspace_b):
      assert real_mvp_stack.platform.list_members(workspace_a).status_code == 200
      assert real_mvp_stack.platform.list_connectors(workspace_a)["meta"]["data_state"] in {"empty", "populated"}
      assert real_mvp_stack.platform.list_runtime_nodes(workspace_a)["data"]
      assert real_mvp_stack.platform.list_members(workspace_b, token=workspace_a.token).status_code in {403, 404}
      assert all(item["installed"] in {True, False} for item in real_mvp_stack.agent.list_settings_skills(workspace_a)["data"])
  ```

  Run: `PYTHONPATH=$(pwd) python3 -m pytest tests/e2e/test_mvp_settings_http.py tests/e2e/test_mvp_release_smoke.py -q`

  Expected: PASS in a real stack; otherwise clear SKIP with no status promotion in the acceptance ledger.

- [ ] **Step 5: Add the repository target and commit the harness.**

  Add a target that fails if pytest reports skipped MVP E2E tests:

  ```make
  mvp-e2e:
	PYTHONPATH=$(CURDIR) $(PYTEST) tests/e2e/test_mvp_*.py -q -rs
	@test "$$(PYTHONPATH=$(CURDIR) $(PYTEST) tests/e2e/test_mvp_*.py -q -rs | grep -c 'SKIPPED')" -eq 0
  ```

  Replace the second shell invocation with a single checked helper script if needed to preserve test output/exit code; it must treat a skip as non-verifying failure in CI.

  ```bash
  git add tests/e2e/mvp_stack.py tests/e2e/conftest.py tests/e2e/test_mvp_settings_http.py tests/e2e/test_mvp_release_smoke.py Makefile
  git commit -m "test: add real full mvp stack harness"
  ```

## Task 4: Rehearse migrations and publish only evidence-based release status

**Files:**

- Create: `scripts/verify_edge_rate_limit.sh`
- Modify: `docs/operations/release-security-checklist.md`
- Modify: `docs/operations/deployment.md`
- Modify: `deploy/central_vps/README.md`
- Modify: `docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md`

**Interfaces:**

- Produces a no-write edge verifier accepting explicit `EDGE_VERIFY_URL` and `EDGE_VERIFY_AUTHORIZATION` inputs.
- Produces a release ledger with command, SHA, migration versions, correlation IDs, timestamps and actual outcome for every verified capability.

- [ ] **Step 1: Write an edge-verifier dry-run test.**

  ```bash
  EDGE_VERIFY_URL="" scripts/verify_edge_rate_limit.sh
  ```

  Expected: non-zero with `EDGE_VERIFY_URL is required`; the script sends no network request and does not change Caddy/Cloudflare configuration.

- [ ] **Step 2: Implement a non-destructive verifier.**

  `verify_edge_rate_limit.sh` requires an explicit target and authorization header, issues a bounded burst only against an approved safe endpoint, and exits success only when it observes at least one `429` plus the expected response header/body contract. It prints timestamp, target host, observed statuses and request count; it never prints authorization value or secrets.

- [ ] **Step 3: Rehearse all new migrations on isolated databases.**

  Run Company and Agent apply/rollback/reapply commands from the Strategy, Marketing, Workforce and Vault plans in fresh disposable databases. Capture `public.schema_migrations` service/filename/checksum rows before/after. Do not run `--down` against a shared developer/staging/production database.

- [ ] **Step 4: Run all release gates and record raw results.**

  Run:

  ```bash
  make lint
  make typecheck-py
  make agent-test
  make apps-cosa-test
  cd services/cosa && npx tsc --noEmit
  cd services/company && npx tsc --noEmit
  make frontend-test
  make frontend-analyze
  make boundary-check
  make contract-freeze-check
  make mvp-surface-check
  make mvp-e2e
  git diff --check
  ```

  Expected: all exit 0. If `mvp-e2e` cannot run in the current environment, do not claim full verified release; resolve environment access or retain the ledger as unverified.

- [ ] **Step 5: Correct operational documentation.**

  In `release-security-checklist.md`, replace unconditional approval/release wording with checkboxes/evidence fields. In `deployment.md`, retain the requirement for custom Caddy/Cloudflare rate limiting and state it is unverified until Task 4's authorized 429 evidence exists. Replace the concrete-looking `SecureCentralPass2026` example in `deploy/central_vps/README.md` with a non-secret placeholder and explicit secret-manager instruction. Correct the landing operation documentation to match its actual simulated-response behavior; do not change functionality merely to make the document sound complete.

- [ ] **Step 6: Commit release evidence, not a production claim.**

  ```bash
  git add scripts/verify_edge_rate_limit.sh docs/operations/release-security-checklist.md docs/operations/deployment.md deploy/central_vps/README.md docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md
  git commit -m "docs: record mvp release verification evidence"
  ```

## Task 5: Freeze final route inventory and acceptance status

**Files:**

- Modify: `shared/contracts/mvp-surface.json`
- Modify: `docs/architecture/generated/route-inventory.md`
- Modify: `docs/architecture/generated/route-inventory.snapshot.json`
- Modify: `docs/architecture/generated/company-usage-inventory.md`
- Modify: `docs/architecture/generated/route-inventory.allowlist.json`
- Modify: `docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md`

**Interfaces:**

- Produces an all-enabled manifest only when every capability's source/tests/E2E evidence are complete.

- [ ] **Step 1: Regenerate all generated artefacts.**

  Run:

  ```bash
  node scripts/gen-mvp-contracts.mjs
  make route-inventory
  make company-usage-inventory
  ```

- [ ] **Step 2: Run final parity/truth check.**

  Run: `python3 scripts/mvp_surface_check.py --check --ledger`

  Expected: zero enabled manifest routes without handlers, zero raw legacy MVP callers, zero runtime fixture imports, and zero incomplete ledger rows marked `VERIFIED`.

- [ ] **Step 3: Remove final allowlist entries only with proof.**

  For every removed entry, review the generated inventory call site, manifest route and backend route side by side. If an old route remains in non-MVP historical/disabled code, keep it declared as disabled; never hide an enabled ghost behind the allowlist.

- [ ] **Step 4: Run the final suite.**

  Run: `make verify && make mvp-e2e && git diff --check`

  Expected: PASS. If `make verify` reaches infrastructure-dependent tests that are intentionally skipped, record that separately and ensure `mvp-e2e` still does not pass on skips.

- [ ] **Step 5: Commit the final contract freeze.**

  ```bash
  git add shared/contracts/mvp-surface.json docs/architecture/generated docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md
  git commit -m "chore: freeze truthful full mvp surface"
  ```

## Completion gate

Run:

```bash
cd services/cosa && npx vitest run tests/workspace-settings.test.ts tests/control-plane.test.ts
cd services/company && npx vitest run identity/tests/platform-client.test.ts
PYTHONPATH=$(pwd) python3 -m pytest tests/apps/cosa/test_settings_routes.py tests/e2e/test_mvp_settings_http.py tests/e2e/test_mvp_release_smoke.py -q
cd frontend && flutter test test/settings_mvp_service_test.dart test/settings_mvp_views_test.dart
make mvp-surface-check
make contract-freeze-check
git diff --check
```

This final tranche does not authorize infrastructure writes. Public release remains blocked until the ledger contains a successful authorized staging run and the infrastructure owner supplies the rate-limit/WAF 429 evidence; without those, documentation must state `VERIFIED` only for repository/local real-service checks and `PRODUCTION` as unverified.
