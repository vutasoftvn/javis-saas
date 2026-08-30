# Production Readiness Audit Remediation Program Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use \`superpowers:subagent-driven-development\` (recommended) or \`superpowers:executing-plans\` to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Close confirmed tenant-isolation, credential, remote-routing, scheduling, release-security, and quality-gate gaps before expanding production access.

**Architecture:** Preserve the four-plane boundary: Company services remain business truth; COSA Control Plane owns platform authorization and scheduling; the Agent Platform never accesses Company tables directly; Flutter sends all business traffic through a single network boundary. The legacy \`Company\` aggregate is a separately governed Workspace-canonical M2 migration, never an opportunistic rename.

**Tech Stack:** TypeScript/Encore/Drizzle, Python/FastAPI/Pytest, Flutter/Dart, PostgreSQL, Docker Compose/Caddy, GitHub Actions.

**Spec:** \`docs/architecture/plans/2026-08-29-cosa-workspace-canonical-master-plan.md\`; evidence baseline: \`docs/architecture/reports/2026-08-29-codebase-audit-recommendations.md\` and audit at commit \`5cc10904\`.

## Global Constraints

- Work directly on \`main\`; do not create a Git worktree.
- \`workspace_id\` is the tenant boundary. Tenant resources must resolve by \`(workspace_id, resource_id)\` or an equivalent composite constraint.
- A member operates only their own connector authorization unless an explicitly audited founder/admin override applies.
- Client code must not persist passwords, raw conversation content, or raw voice transcripts.
- All business JSON, form, multipart, and SSE calls use one target resolver, token resolver, workspace header, timeout policy, and REMOTE_ACCESS offline guard.
- Do not add Company aliases. Workspace-canonical removal requires its dedicated M2 design approval.
- Start each behavior change with a focused failing test; complete only after focused tests and affected checks pass.
- Do not deploy, change WAF/Coolify secrets, or execute restore drills without explicit infrastructure authorization.

---

## Program order

| Wave | Scope | Depends on | Exit gate |
|---|---|---|---|
| 0 | Repository gates and deterministic tests | None | lint, docs, generated inventory, targeted Company tests green |
| 1 | Tenant and credential security | Wave 0 | Multi-workspace negative authorization matrix green |
| 2 | Client routing and sensitive-data controls | Wave 1 | Local/remote/offline contract tests green |
| 3 | Durable scheduling and API errors | Waves 0-1 | Enqueue failure/retry test green |
| 4 | Deployment, supply chain, observability, recovery | Waves 1-3 | Staging evidence recorded |
| 5 | Workspace-canonical M2 cutover | Separate approval | No Company aggregate in product tenancy/auth/policy |

## File map

| Path | Responsibility |
|---|---|
| \`services/company/identity/services/tenant-context.service.ts\` | Resolve a workforce actor inside the requested workspace. |
| \`services/cosa/handlers/workspace-connector.handler.ts\` | Authorize connector grant/revoke caller. |
| \`services/cosa/services/workspace-schedule.service.ts\` | Durable schedule dispatch/retry. |
| \`frontend/lib/core/network/api_client.dart\` | Shared client target, auth, headers, timeout, and streaming transport. |
| \`frontend/lib/core/network/realtime_service.dart\` | SSE lifecycle through shared transport. |
| \`frontend/lib/modules/auth/controllers/auth_controller.dart\` | Remembered identifier only; no stored password. |
| \`deploy/central_vps/docker-compose.prod.yaml\` | Runtime hardening and telemetry configuration. |
| \`.github/workflows/quality.yml\` | Supply-chain and release quality gates. |

## Wave 0 — Repository truth and deterministic test harness

### Task 1: Restore failing repository contract gates

**Files:**
- Modify: \`packages/agent/contracts/spec.py:52-56\`
- Modify: \`docs/architecture/generated/company-usage-inventory.md\`
- Modify: \`docs/archive/2026-08/COSA_LEARN_CLAUDE_CODE_HARNESS_INTEGRATION_BLUEPRINT_2026-08-24.md:632\`
- Modify: \`docs/architecture/plans/2026-08-29-cosa-workspace-canonical-master-plan.md:30\`

**Interfaces:**
- Consumes: Ruff formatting, \`scripts/company_usage_inventory.py\`, and \`scripts/check_doc_links.py\`.
- Produces: a clean lint, contract-freeze, and documentation-link gate without disabling any checker.

- [ ] **Step 1: Capture the baseline failures**

\`\`\`bash
make lint
make contract-freeze-check
make check-docs
\`\`\`

Expected: one Ruff format drift, a stale generated inventory, and two exact broken links.

- [ ] **Step 2: Apply source-of-truth corrections**

Format only the AgentSpec condition. Regenerate, never hand-edit, the usage inventory. Update the archived migration link to \`packages/agent/migrations/005_idempotency_claims.sql\`; replace the missing historical Workspace-first spec link with the active M0 contract-freeze document.

\`\`\`bash
.venv/bin/python -m ruff format packages/agent/contracts/spec.py
make company-usage-inventory
\`\`\`

- [ ] **Step 3: Verify and commit**

\`\`\`bash
make lint
make contract-freeze-check
make check-docs
git diff --check
git add packages/agent/contracts/spec.py docs/architecture/generated/company-usage-inventory.md docs/archive/2026-08/COSA_LEARN_CLAUDE_CODE_HARNESS_INTEGRATION_BLUEPRINT_2026-08-24.md docs/architecture/plans/2026-08-29-cosa-workspace-canonical-master-plan.md
git commit -m "fix(quality): restore generated and documentation gates"
\`\`\`

### Task 2: Isolate Customer Engagement relay tests

**Files:**
- Modify: \`services/company/commercial/tests/customer-engagement/channel-matrix.test.ts:280\`
- Modify: \`services/company/commercial/tests/customer-engagement/delivery-relay-provider.test.ts\`
- Modify: \`services/company/commercial/services/customer-engagement/channel-adapters/registry.ts\`

**Interfaces:**
- Consumes: \`deliveryRelayTick(workerId, limit, workspaceId?)\`.
- Produces: test fixtures that dispatch only their workspace and reset mutable adapter/secret doubles after each case.

- [ ] **Step 1: Write a failing workspace-isolation test**

Create queued deliveries in A and B; dispatch only A and assert B remains queued.

\`\`\`ts
const result = await deliveryRelayTick("test-worker", 1, workspaceA);
expect(result.processed).toBe(1);
expect((await deliveryById(deliveryA)).status).toBe("sent");
expect((await deliveryById(deliveryB)).status).toBe("queued");
\`\`\`

- [ ] **Step 2: Reproduce in default parallel mode**

\`\`\`bash
cd services/company && pnpm vitest run commercial/tests/customer-engagement/channel-matrix.test.ts commercial/tests/customer-engagement/delivery-relay-provider.test.ts
\`\`\`

Expected before correction: global relay selection or a leaked adapter can cause a fixture to remain queued.

- [ ] **Step 3: Scope and reset doubles**

Pass \`wsId\` to fixture relay calls. Add \`resetChannelAdapterRegistryForTest()\` that restores default API and Zalo adapters; call it with \`setCustomConnectorGrantRunner(null)\` and \`setCustomChannelSecretResolver(null)\` in \`afterEach\`.

- [ ] **Step 4: Verify and commit**

\`\`\`bash
cd services/company && pnpm vitest run commercial/tests/customer-engagement/channel-matrix.test.ts commercial/tests/customer-engagement/delivery-relay-provider.test.ts
cd services/company && pnpm vitest run commercial/tests/customer-engagement/channel-matrix.test.ts --no-file-parallelism
git add commercial/tests/customer-engagement/channel-matrix.test.ts commercial/tests/customer-engagement/delivery-relay-provider.test.ts commercial/services/customer-engagement/channel-adapters/registry.ts
git commit -m "test(engagement): isolate outbound relay fixtures"
\`\`\`

## Wave 1 — Tenant and credential security

### Task 3: Scope workforce identity to its workspace

**Files:**
- Modify: \`services/company/identity/services/tenant-context.service.ts:107-111\`
- Test: \`services/company/identity/tests/tenant-context.test.ts\`
- Test: \`services/company/commercial/tests/customer-engagement/assignment.service.test.ts\`

**Interfaces:**
- Consumes: \`resolveTenantContext({ workspaceId, authorization })\`.
- Produces: \`TenantContext.workforceMemberId\` that belongs to that workspace.

- [ ] **Step 1: Write the failing two-workspace regression**

Create one human user, memberships in A/B, and two workforce records. Resolve B and assert that B’s workforce ID is used for thread takeover.

\`\`\`ts
const ctx = await resolveTenantContext({ authorization, workspaceId: workspaceB.toString() });
expect(ctx.workforceMemberId).toBe(workforceB.toString());
\`\`\`

- [ ] **Step 2: Run focused tests**

\`\`\`bash
cd services/company && pnpm vitest run identity/tests/tenant-context.test.ts commercial/tests/customer-engagement/assignment.service.test.ts
\`\`\`

- [ ] **Step 3: Bind both dimensions in the lookup**

\`\`\`ts
.where(and(
  eq(identityWorkforceMembers.humanUserId, localUserId),
  eq(identityWorkforceMembers.workspaceId, targetWorkspaceId),
))
\`\`\`

Preserve \`undefined\` if the selected workspace has no workforce record.

- [ ] **Step 4: Verify and commit**

\`\`\`bash
cd services/company && pnpm typecheck && pnpm vitest run identity/tests/tenant-context.test.ts commercial/tests/customer-engagement/assignment.service.test.ts
git add identity/services/tenant-context.service.ts identity/tests/tenant-context.test.ts commercial/tests/customer-engagement/assignment.service.test.ts
git commit -m "fix(identity): scope workforce actor to workspace"
\`\`\`

### Task 4: Enforce connector authorization ownership

**Files:**
- Modify: \`services/cosa/handlers/workspace-connector.handler.ts:127-165\`
- Modify: \`services/cosa/services/workspace-connector.service.ts:210-264\`
- Test: \`services/cosa/tests/workspace-connector.test.ts\`

**Interfaces:**
- Consumes: caller platform claims, workspace membership, authorization owner, and conversation ID.
- Produces: grant/revoke rejection for another member’s authorization unless an explicit privileged override is present.

- [ ] **Step 1: Write owner/non-owner/override tests**

Create principals A and B in one workspace with an authorization owned by B. Assert A cannot grant or revoke B’s authorization, B can, and only a founder/admin override can manage another owner.

\`\`\`ts
await expect(grantConnectorEndpoint({ ...aParams, authorizationId: bAuthorization.id }))
  .rejects.toThrow(/authorization owner/i);
\`\`\`

- [ ] **Step 2: Run the failing connector suite**

\`\`\`bash
cd services/cosa && pnpm vitest run tests/workspace-connector.test.ts
\`\`\`

- [ ] **Step 3: Add typed actor authorization**

Pass \`callerPrincipalId\` and \`allowManageOthers\` from handler to service. Load authorization and conversation in the same workspace; reject owner mismatch before grant/revoke writes.

\`\`\`ts
if (authRecord.principalId !== input.callerPrincipalId && !input.allowManageOthers) {
  throw APIError.permissionDenied("connector authorization belongs to another principal");
}
\`\`\`

- [ ] **Step 4: Verify and commit**

\`\`\`bash
cd services/cosa && pnpm typecheck && pnpm vitest run tests/workspace-connector.test.ts
git add handlers/workspace-connector.handler.ts services/workspace-connector.service.ts tests/workspace-connector.test.ts
git commit -m "fix(connectors): enforce authorization ownership"
\`\`\`

### Task 5: Remove plaintext remembered passwords

**Files:**
- Modify: \`frontend/lib/modules/auth/controllers/auth_controller.dart:46-55,123-131\`
- Modify: \`frontend/lib/modules/auth/views/login_view.dart\`
- Create: \`frontend/test/modules/auth/auth_controller_credentials_test.dart\`
- Modify: \`frontend/test/auth_flow_test.dart\`

**Interfaces:**
- Consumes: \`SharedPreferences\` for \`saved_identifier\` only, and secure storage for session tokens.
- Produces: legacy password deletion, remembered identifier, and no password field persistence.

- [ ] **Step 1: Write failing migration/persistence tests**

\`\`\`dart
expect(prefs.getString('saved_identifier'), 'founder@example.com');
expect(prefs.containsKey('saved_password'), isFalse);
expect(controller.passwordController.text, isEmpty);
\`\`\`

Seed both legacy keys, then test initialization and login with Remember selected.

- [ ] **Step 2: Run focused tests**

\`\`\`bash
cd frontend && flutter test test/auth_flow_test.dart test/modules/auth/auth_controller_credentials_test.dart
\`\`\`

- [ ] **Step 3: Implement account-only remember behavior**

Read and immediately delete \`saved_password\`; never assign it to the password field. Persist/remove only \`saved_identifier\`. Update UI copy to “remember this account”, not password.

- [ ] **Step 4: Verify and commit**

\`\`\`bash
cd frontend && flutter test test/auth_flow_test.dart test/modules/auth/auth_controller_credentials_test.dart && flutter analyze
git add lib/modules/auth/controllers/auth_controller.dart lib/modules/auth/views/login_view.dart test/auth_flow_test.dart test/modules/auth/auth_controller_credentials_test.dart
git commit -m "fix(frontend): never persist remembered passwords"
\`\`\`

## Wave 2 — Client routing and sensitive data

### Task 6: Centralize JSON, form, multipart, and SSE transport

**Files:**
- Modify: \`frontend/lib/core/network/api_client.dart\`
- Modify: \`frontend/lib/core/network/realtime_service.dart\`
- Modify: \`frontend/lib/core/services/voice_service.dart\`
- Modify: \`frontend/lib/modules/vault/services/vault_service.dart\`
- Modify: \`frontend/lib/modules/hologram_hub/services/chat_service.dart\`
- Modify: \`frontend/lib/modules/chat/services/agent_chat_service.dart\`
- Create: \`frontend/test/core/network/api_client_streaming_transport_test.dart\`

**Interfaces:**
- Produces: \`ApiClient.openSse(endpoint)\`, \`ApiClient.sendMultipart(endpoint, ...)\`, and \`ApiClient.sendForm(endpoint, fields)\`.
- Guarantees: each method uses \`resolveUri\`, offline guard, target-specific token selection, and \`X-Workspace-Id\`.

- [ ] **Step 1: Write routing/header contract tests**

Test business SSE, voice upload, Vault write, and hub chat in REMOTE_ACCESS. They must target \`/relay/...\`, use local-session token, and never call HTTP when the node is OFFLINE.

\`\`\`dart
expect(request.url.path, '/relay/events/stream');
expect(request.headers['X-Workspace-Id'], workspaceId);
expect(request.headers['Authorization'], 'Bearer $localSessionToken');
\`\`\`

- [ ] **Step 2: Run the focused failing tests**

\`\`\`bash
cd frontend && flutter test test/core/network/api_client_runtime_route_test.dart test/core/network/api_client_streaming_transport_test.dart
\`\`\`

- [ ] **Step 3: Add narrow shared transport primitives**

\`\`\`dart
static Future<http.StreamedResponse> openSse(String endpoint) async {
  final offline = _offlineGuard(endpoint);
  if (offline != null) throw ApiOfflineException(offline);
  final request = http.Request('GET', resolveUri(endpoint));
  request.headers.addAll(await _getHeaders(endpoint));
  request.headers['Accept'] = 'text/event-stream';
  return client.send(request);
}
\`\`\`

Keep existing JSON methods stable. Form/multipart helpers must receive URI and headers from the same resolver rather than parse \`ApiClient.baseUrl\`.

- [ ] **Step 4: Migrate raw business callers**

Replace every production \`Uri.parse(ApiClient.baseUrl)\` in the listed services. Preserve endpoint paths and field names; do not rewrite platform endpoints.

- [ ] **Step 5: Verify and commit**

\`\`\`bash
rg -n --glob '*.dart' 'Uri\\.parse\\(ApiClient\\.baseUrl\\)' frontend/lib
cd frontend && flutter test test/core/network/api_client_runtime_route_test.dart test/core/network/api_client_streaming_transport_test.dart && flutter analyze
git add lib/core/network/api_client.dart lib/core/network/realtime_service.dart lib/core/services/voice_service.dart lib/modules/vault/services/vault_service.dart lib/modules/hologram_hub/services/chat_service.dart lib/modules/chat/services/agent_chat_service.dart test/core/network
git commit -m "fix(frontend): route streaming and uploads through gateway"
\`\`\`

Expected: the search returns no production business caller.

### Task 7: Close realtime lifecycle, logs, unsafe links, and hanging calls

**Files:**
- Modify: \`frontend/lib/modules/profile/controllers/profile_controller.dart\`
- Modify: \`frontend/lib/modules/hologram_hub/controllers/hologram_hub_controller.dart\`
- Modify: \`frontend/lib/core/network/realtime_service.dart\`
- Modify: \`frontend/lib/core/services/voice_service.dart\`
- Modify: \`frontend/lib/modules/chat/services/agent_chat_service.dart\`
- Modify: \`frontend/lib/modules/hologram_hub/presentation/widgets/chat/hub_chat_message_bubble.dart\`
- Create: \`frontend/test/core/network/realtime_service_lifecycle_test.dart\`
- Create: \`frontend/test/core/services/voice_service_logging_test.dart\`

**Interfaces:**
- Produces: disconnect before logout/workspace switch; no raw transcript/response logs; HTTPS-only external links; finite 15-second read and 30-second upload timeouts.

- [ ] **Step 1: Write lifecycle/security tests**

\`\`\`dart
expect(launcher.openedUris, equals(<Uri>[Uri.parse('https://docs.cosa.vn/help')]));
expect(logs.join('\\n'), isNot(contains('confidential transcript')));
\`\`\`

Also assert logout calls \`RealtimeService.disconnect()\` and cancels reconnect.

- [ ] **Step 2: Run focused tests**

\`\`\`bash
cd frontend && flutter test test/core/network/realtime_service_lifecycle_test.dart test/core/services/voice_service_logging_test.dart test/modules/hologram_hub/hologram_projection_test.dart
\`\`\`

- [ ] **Step 3: Implement the policy**

Disconnect before credential/workspace reset. Read session through ApiClient’s token policy. Log only code plus correlation/request identifier; never body or transcript. Permit HTTPS links; permit HTTP only in debug builds. Apply timeout without mutation retry unless an idempotency key exists.

- [ ] **Step 4: Verify and commit**

\`\`\`bash
cd frontend && flutter test && flutter analyze
git add lib/modules/profile/controllers/profile_controller.dart lib/modules/hologram_hub/controllers/hologram_hub_controller.dart lib/core/network/realtime_service.dart lib/core/services/voice_service.dart lib/modules/chat/services/agent_chat_service.dart lib/modules/hologram_hub/presentation/widgets/chat/hub_chat_message_bubble.dart test
git commit -m "fix(frontend): harden realtime lifecycle and output"
\`\`\`

## Wave 3 — Scheduling and error contracts

### Task 8: Make schedule enqueue failures retryable

**Files:**
- Modify: \`services/cosa/services/workspace-schedule.service.ts:283-350\`
- Modify: \`services/cosa/control-plane.cron.ts\`
- Test: \`services/cosa/tests/workspace-schedule.test.ts\`
- Test: \`services/cosa/tests/control-plane-scheduler-crash-recovery.test.ts\`

**Interfaces:**
- Consumes: occurrence uniqueness on \`(definitionId, scheduledFor)\`.
- Produces: a queued occurrence with no task ID that is retried safely, then either gets one task ID or becomes terminal with a reason.

- [ ] **Step 1: Add fault-injection tests**

Make \`scheduleTask\` throw once then succeed. First tick must leave a retryable occurrence and not advance the definition; second tick must create exactly one task and advance once.

\`\`\`ts
expect(execution.taskId).toBeNull();
expect(execution.state).toBe('enqueue_retry');
await expect(dispatchDueSchedules(now)).resolves.toBe(1);
\`\`\`

- [ ] **Step 2: Run focused tests**

\`\`\`bash
cd services/cosa && pnpm vitest run tests/workspace-schedule.test.ts tests/control-plane-scheduler-crash-recovery.test.ts
\`\`\`

- [ ] **Step 3: Add durable retry state**

Add \`enqueue_retry\`, next-attempt time, attempt count, and terminal \`enqueue_failed\` after a documented maximum. Claim retryable rows before creating new occurrences. Advance \`nextRunAt\` only after durable storage of \`taskId\`. Emit queue-age/retry metrics.

- [ ] **Step 4: Verify and commit**

\`\`\`bash
cd services/cosa && pnpm typecheck && pnpm vitest run tests/workspace-schedule.test.ts tests/control-plane-scheduler-crash-recovery.test.ts
git add services/workspace-schedule.service.ts control-plane.cron.ts tests/workspace-schedule.test.ts tests/control-plane-scheduler-crash-recovery.test.ts
git commit -m "fix(scheduler): retry failed schedule enqueue"
\`\`\`

### Task 9: Normalize schedule public errors

**Files:**
- Modify: \`services/cosa/services/workspace-schedule.service.ts:33-39,180-205,371-373\`
- Modify: \`services/cosa/handlers/workspace-schedule.handler.ts:112-126\`
- Test: \`services/cosa/tests/workspace-schedule-handler.test.ts\`

**Interfaces:**
- Produces: invalid input as \`APIError.invalidArgument\`, missing resource as \`APIError.notFound\`, quota/precondition errors as typed API errors, and internal causes only in logs.

- [ ] **Step 1: Add handler contract tests**

\`\`\`ts
await expect(createScheduleEndpoint(invalidTimezone)).rejects.toMatchObject({ code: 'invalid_argument' });
await expect(getScheduleExecutionEndpoint(missingExecution)).rejects.toMatchObject({ code: 'not_found' });
\`\`\`

- [ ] **Step 2: Run focused tests, implement mapping, verify, commit**

\`\`\`bash
cd services/cosa && pnpm vitest run tests/workspace-schedule-handler.test.ts tests/workspace-schedule.test.ts
cd services/cosa && pnpm typecheck && pnpm vitest run tests/workspace-schedule-handler.test.ts tests/workspace-schedule.test.ts
git add services/workspace-schedule.service.ts handlers/workspace-schedule.handler.ts tests/workspace-schedule-handler.test.ts
git commit -m "fix(api): normalize schedule error responses"
\`\`\`

## Wave 4 — Operational release readiness

### Task 10: Approve edge security and recovery before configuring infrastructure

**Files:**
- Modify: \`docs/operations/deployment.md\`
- Modify: \`docs/operations/disaster-recovery.md\`
- Create: \`docs/operations/release-security-checklist.md\`
- Modify: \`tests/deploy/test_production_compose_contract.py\`

**Interfaces:**
- Consumes: an explicit infrastructure-owner decision.
- Produces: documented, verifiable preconditions; no external cloud configuration is created by this task.

- [ ] **Step 1: Record mandatory decisions**

The checklist must contain selected values for: WAF/rate-limit provider; login limits per IP and identifier; registration limit; bot-verification policy; backup cadence; PITR mode; target RPO/RTO; restore drill cadence; alert owner/destination.

- [ ] **Step 2: Request explicit authorization**

Do not create Cloudflare/Caddy/Coolify resources or modify production until the user authorizes the selected design.

- [ ] **Step 3: Encode repository-side attestations**

Require rate-limit and restore-test attestations in production Compose/preflight; add a static test that rejects absent values.

\`\`\`py
assert "EDGE_RATE_LIMIT_ATTESTED" in production_environment
assert "RESTORE_TEST_MAX_AGE_HOURS" in deploy_preflight
\`\`\`

- [ ] **Step 4: Verify and commit documents/contracts**

\`\`\`bash
PYTHONPATH=$(pwd) .venv/bin/python -m pytest tests/deploy/test_production_compose_contract.py -q
make check-docs
git add docs/operations/deployment.md docs/operations/disaster-recovery.md docs/operations/release-security-checklist.md tests/deploy/test_production_compose_contract.py
git commit -m "docs(ops): define release security and recovery gates"
\`\`\`

### Task 11: Make images reproducible and least-privilege

**Files:**
- Modify: \`packages/agent/requirements.txt\`, \`apps/cosa/requirements.txt\`
- Create: hash-verified Python lockfiles
- Modify: \`apps/cosa/Dockerfile.api\`, \`apps/cosa/Dockerfile.worker\`, \`services/Dockerfile\`
- Modify: \`deploy/central_vps/docker-compose.prod.yaml\`
- Modify: \`.github/workflows/quality.yml\`

**Interfaces:**
- Produces: exact/hash-verified Python dependencies, lockfile-respecting Node installs, non-root read-only application containers, immutable CI action pins, SBOM, and vulnerability gate.

- [ ] **Step 1: Add static container contracts**

\`\`\`py
assert "USER app" in Path("apps/cosa/Dockerfile.api").read_text()
assert "npm ci" in Path("services/Dockerfile").read_text()
\`\`\`

Also assert Compose applies \`read_only\`, \`no-new-privileges\`, \`cap_drop: [ALL]\`, and a bounded tmpfs to every long-running app container.

- [ ] **Step 2: Generate locks and prove clean installation**

Resolve exact versions and hashes with the selected tool; do not upgrade merely because a newer package exists. Build each image from clean cache twice and compare installed manifests.

- [ ] **Step 3: Implement least privilege**

Create application users, chown only runtime/temp paths, set \`USER\`, use \`npm ci\`, and remove Docker daemon/CLI from the production Encore image unless a tested production need remains. Pin base image and Encore artifact to immutable digest/checksum.

- [ ] **Step 4: Add CI gates and verify**

Pin GitHub Actions by reviewed SHA, set \`permissions: contents: read\`, generate SBOM, and fail on high-severity vulnerabilities except documented versioned exceptions.

\`\`\`bash
docker compose -f deploy/central_vps/docker-compose.prod.yaml --env-file deploy/central_vps/.env.prod.example config --quiet
make lint
\`\`\`

### Task 12: Operate observability, not just instrument it

**Files:**
- Modify: \`deploy/central_vps/docker-compose.prod.yaml\`
- Create: \`deploy/central_vps/otel-collector.yaml\`
- Create: \`deploy/central_vps/prometheus/alerts.yaml\`
- Modify: \`docs/operations/observability.md\`
- Modify: \`deploy/central_vps/smoke/test_compose_env_contract.py\`

**Interfaces:**
- Consumes: \`OTEL_EXPORTER_OTLP_ENDPOINT\` and structured correlation/run/workspace fields.
- Produces: traces plus alerts for auth abuse, queue age, dead letters, schedule retry age, backup freshness, model failures/latency, and cost signals.

- [ ] **Step 1: Add a failing Compose contract**

\`\`\`py
assert compose["services"]["cosa-api"]["environment"]["OTEL_EXPORTER_OTLP_ENDPOINT"] == "http://otel-collector:4318"
assert "otel-collector" in compose["services"]
\`\`\`

- [ ] **Step 2: Add collector and alert rules**

Use resource-limited collector configuration. Define thresholds: queue/schedule retry age over 10 minutes; dead letters over zero for 5 minutes; backup freshness over 24 hours; failed-login rate over the approved edge threshold.

- [ ] **Step 3: Verify in staging under approved authority**

Trace Company → event intake → scheduler → worker → Company callback. Record trace ID, alert test result, dashboard URL, timestamp, and RTO/RPO drill evidence in the release checklist. Never commit credentials.

## Wave 5 — Workspace-canonical M2 program

### Task 13: Freeze Company product paths and create a dedicated M2 plan

**Files:**
- Modify: \`docs/architecture/plans/2026-08-29-cosa-workspace-canonical/REMAINING-M0-M7.md\`
- Modify: \`docs/architecture/generated/company-usage-inventory.md\`
- Create: \`docs/superpowers/specs/2026-08-30-workspace-canonical-m2-cutover-design.md\`
- Create: \`docs/superpowers/plans/2026-08-30-workspace-canonical-m2-cutover.md\`

**Interfaces:**
- Consumes: Company APIs, onboarding request/response shapes, membership projections, and frontend Company calls.
- Produces: an approved removal/replacement mapping for each legacy API/table/field/client path.

- [ ] **Step 1: Classify every legacy-tenancy occurrence**

For every inventory item, record: remove, adapter-with-expiry, or valid customer/counterparty language; owner; Workspace replacement; test; and deletion criterion.

- [ ] **Step 2: Obtain contract-removal approval**

The M2 design must name the deprecation date for Company auth endpoints, \`company_id\` response fields, and Company onboarding UI. Do not remove an interface before its Workspace replacement and migration test exist.

- [ ] **Step 3: Write a separate M2 spec and execution plan**

Include schema migration order, compatibility adapter expiry, client onboarding replacement, data reset/migration policy, tenant-negative tests, rollback boundaries, and final deletion commits. Do not implement it as text replacement.

## Final release verification

- [ ] Run repository gates:

\`\`\`bash
make lint
make typecheck-py
make boundary-check
make contract-freeze-check
make check-docs
cd services/cosa && pnpm typecheck && pnpm test
cd services/company && pnpm typecheck && pnpm test
cd frontend && flutter test && flutter analyze
cd landing && npm run lint && npm run build
\`\`\`

- [ ] Run staging smoke for Company → event intake → scheduler → worker → Company callback: success, invalid HMAC, missing service token, duplicate event, worker restart, and enqueue retry.
- [ ] Run the approved isolated restore drill and record measured RTO/RPO plus cross-database consistency result.
- [ ] Review generated artifacts, migration fingerprints, release checklist, and \`git diff --check\` before release approval.

## Plan self-review

- Coverage: audit P1/P2 findings map to Waves 0-4; M2 is intentionally isolated as an architectural migration.
- No implementation is authorized by this plan alone; Wave 4 requires infrastructure authorization and Wave 5 requires separate design approval.
- Dependency consistency: shared transport precedes client migrations; tenant fixes precede release routing; scheduler recovery precedes staging release proof.

