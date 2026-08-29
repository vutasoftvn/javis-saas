# COSA Codebase Audit — Recommendations

**Audit date:** 2026-08-29  
**Repository baseline:** `0cbab94c`  
**Scope:** Python Agent Platform, TypeScript Control/Company planes, Flutter client, landing page, delivery configuration, quality gates, and representative end-to-end paths.  
**Method:** Read-only code/configuration review plus the existing automated checks. No production data or application code was changed during this audit.

## Executive summary

COSA has a substantial and well-separated four-plane architecture:

```text
Experience Plane      Flutter
Control Plane         services/cosa (Encore / TypeScript)
Company Plane         services/company (Encore / TypeScript)
Agent Platform        packages/agent_core + apps/cosa (Python)
```

The main risks are not architectural intent but execution-path integrity:

1. The customer-support Copilot calls methods that do not exist on the capability registry.
2. The event relay cannot reliably traverse the TypeScript-to-Python boundary in production because its HMAC payloads are serialized differently and the deployed container wiring is incomplete.
3. Production services silently fall back to localhost URLs and known development tokens instead of failing closed.
4. Current Python linting, type checking, and one protocol-conformance test are failing, so the CI quality gate is red.

The first implementation milestone should therefore be a small **production-path restoration** slice, not additional features.

## P0 — Fix before production use

### 1. Restore the Customer Support Copilot execution path

**Evidence**

- `apps/cosa/worker/copilot_run.py` calls `plane.capability_registry.get_handler(...)`.
- `packages/agent_core/capabilities/registry.py` exposes `get(...)`, not `get_handler(...)`.
- The same worker also attempts `spec_registry.get_agent_spec(...)`, while the registry protocol exposes generic `get(spec_kind, spec_id, version)`.
- Static typing reports these calls, and the worker's broad exception handler turns the error into a failed Copilot run.

**Impact**

Copilot runs can fail before context assembly, and draft validation will fail again later in the same workflow. This is a functional failure, not merely a typing concern.

**Recommendation**

1. Define one canonical registry interface. Either add a deliberate `get_handler(capability_id)` convenience method, or use `registration = registry.get(capability_id)` and then `registration.handler` at every call site.
2. Resolve agent specs through the existing generic repository contract, or add a typed agent-spec resolver that returns the expected domain model.
3. Add a non-mocked vertical test: schedule a Copilot run, resolve its three read capabilities, create the draft artifact, and verify the Company callback payload.
4. Treat capability lookup failures as explicit operational errors with structured reason codes; do not rely on a broad final `except` as the primary diagnostic path.

**Relevant files**

- `apps/cosa/worker/copilot_run.py`
- `apps/cosa/worker/autopilot_run.py`
- `packages/agent_core/capabilities/registry.py`
- `packages/agent_core/registry/repository.py`

### 2. Make the event relay a wire-compatible, authenticated production path

**Evidence**

- The Company relay signs `JSON.stringify(envelope)`.
- The Python intake verifies `json.dumps(parsed_body)` after parsing the request body.
- Those byte streams differ in whitespace and non-ASCII escaping. A representative Vietnamese payload produced distinct HMAC digests in Node and Python.
- The current tests only prove Python-to-Python signing and mock the relay HTTP request; they do not test the actual cross-language wire contract.

**Impact**

Valid outbox events can be rejected as unauthenticated. Retries will accumulate, triggers will not schedule runs, and operational lag will grow without resolving the root cause.

**Recommendation**

1. Sign and verify the exact raw request bytes. In the FastAPI handler, read `await request.body()`, validate the HMAC against those bytes, then parse JSON.
2. Send the already-signed JSON string as the request body; do not serialize it a second time in a different library layer.
3. Require `COSA_LOCAL_SERVICE_SECRET` in every non-development environment. Remove the `dev-secret` fallback.
4. Add a cross-language contract test covering Unicode, nested objects, key ordering, tampering, duplicate delivery, and a missing secret.

**Relevant files**

- `services/company/events/outbox-relay.service.ts`
- `apps/cosa/api/event_intake_routes.py`
- `apps/cosa/events/local_auth.py`
- `tests/apps/cosa/test_local_event_intake.py`
- `services/company/events/tests/outbox-relay.test.ts`

### 3. Complete production container wiring and remove unsafe defaults

**Evidence**

- `services/company` defaults Copilot calls to `http://127.0.0.1:8000`, which points back to its own container, not `cosa-api`.
- The outbox relay defaults to `http://127.0.0.1:8081`, where the target service is not deployed in the production compose topology.
- The relay's local-target guard currently rejects ordinary Docker service DNS names such as `cosa-api`.
- The production compose file does not inject the complete set of URLs and shared service credentials into Company, API, and Worker containers.
- Copilot routes use the known fallback `local-dev-service-token`, including behind the public API proxy path.
- The worker's Copilot callback defaults to `http://127.0.0.1:4000`, which is also not the Company service from inside the worker container.

**Impact**

Even after code-level fixes, the event pipeline, Copilot dispatch, durable scheduling, or Company callback will fail in the deployed topology. Known token fallbacks also weaken the intended service boundary.

**Recommendation**

1. In `deploy/central_vps/docker-compose.prod.yaml`, require and inject the appropriate variables:
   - Company: `COSA_INTERNAL_URL`, `COSA_AGENTOS_INTAKE_URL`, `COSA_LOCAL_SERVICE_SECRET`, `COSA_SERVICE_TOKEN`, and required worker credentials.
   - COSA API: `COSA_LOCAL_SERVICE_SECRET`, `COSA_SERVICE_TOKEN`, and `COSA_WORKER_SERVICE_TOKEN` for scheduler calls.
   - COSA Worker: `COMPANY_SERVICE_URL` and `COSA_SERVICE_TOKEN` for callbacks.
2. Use Docker internal names such as `http://cosa-api:8000` and `http://services-company:4000` only after replacing the hard-coded local-host check with a strict, configurable internal-host allowlist.
3. In staging and production, fail at process startup when any service token, shared secret, or internal URL is missing, short, or equal to a development value.
4. Add a compose-level smoke test that proves all four legs: Company → event intake → scheduler → worker → Company callback.

**Relevant files**

- `deploy/central_vps/docker-compose.prod.yaml`
- `services/company/commercial/services/customer-engagement/copilot-cosa-client.ts`
- `services/company/events/outbox-relay.service.ts`
- `apps/cosa/api/copilot_routes.py`
- `apps/cosa/worker/copilot_run.py`
- `apps/cosa/events/deps.py`

## P1 — Restore engineering reliability

### 4. Make the quality gate green again

Current results:

| Check | Result |
|---|---|
| Ruff | Fails: 46 findings |
| mypy | Fails: 21 errors in 7 files |
| Agent-core unit suite | Fails: 1 failed, 461 passed, 28 skipped |
| Flutter analyze | Fails: 7 informational/deprecation findings |

The failed MCP conformance test is a useful signal: MCP tools default to `MEDIUM` risk, while the test invokes them without a workspace or principal. The correct repair is to supply an authenticated `InvocationContext` in the caller/test and preserve fail-closed tenancy; do not downgrade the risk merely to make the test pass.

Recommended order:

1. Apply safe Ruff fixes, then resolve the remaining manual lint issues.
2. Correct the type/model mismatches in capability gateway, observability exporter construction, eval cases, and worker registry calls.
3. Repair the MCP test contract with tenant context and assert that missing context never produces a side effect.
4. Convert Flutter deprecations (`withOpacity`, null-aware collection style) before the next SDK upgrade.

### 5. Make local tests reproducible

**Evidence**

- `make services-test` fails against the current local Company database because `core.workspaces.company_stage` is absent; CI applies migrations first, but the local target does not.
- `make realtime-agent-test` uses the repository root Python environment, which lacks `livekit.agents`; the component's own virtual environment runs all 27 tests successfully.

**Recommendation**

1. Make each test target provision or verify its required schema in an isolated test database. Do not rely on a developer's mutable local database state.
2. Update `services-test` to perform an explicit migration precondition or provide a separate `services-test-fresh` target that creates a disposable database.
3. Change `realtime-agent-test` to run `services/realtime_agent/.venv/bin/python` when present, or create/install a component-specific environment consistently.
4. Have the local `verify` target mirror CI's dependency and migration order as closely as practical.

### 6. Replace temporal test workarounds with an explicit clock

`services/company/commercial/services/customer-engagement/automation/evaluator.ts` currently evaluates rule timing with `new Date(Date.now() + 1000)`.

This changes production semantics by activating a rule one second early, and it leaves boundary behavior nondeterministic. Inject a `Clock` or optional `now` parameter into the evaluator, use the real clock in production, and fixed instants in tests.

## P2 — Maintainability and product readiness

### 7. Re-establish a single documentation source of truth

`CLAUDE.md` references several architecture documents that are no longer present after the baseline commit. The README acknowledges the drift, but an engineer cannot reliably identify the governing design from the repository alone.

Choose the current workspace-canonical architecture plan as the index, update `CLAUDE.md`, README, and operational documents to reference it, and distinguish clearly between:

- accepted decision;
- implementation complete;
- wired to consumers;
- verified in CI/staging; and
- production verified.

Do not restore deleted documents automatically; first decide whether they are historical evidence or still normative.

### 8. Reduce high-churn module size after P0 work

Several modules combine routing, orchestration, business rules, and serialization in files larger than 1,000 lines. The most valuable first extractions are:

- FastAPI route groups from `apps/cosa/api/routes.py`;
- discrete Flutter views/forms from large strategy and marketing widgets;
- explicit service adapters around the worker execution paths.

Keep public contracts stable and make these refactors only after the vertical production paths are covered by tests.

### 9. Plan dependency hygiene

The Flutter dependency resolver reports one discontinued package (`flutter_markdown`) and multiple constrained upgrades. Replace the discontinued package through a compatibility-tested migration, then schedule dependency updates in small, separately reviewable batches.

## Verification snapshot

| Check | Observed result |
|---|---|
| `make apps-cosa-test` | 418 passed, 3 skipped; warnings remain |
| `make frontend-test` | Passed |
| TypeScript typecheck (`services/company`, `services/cosa`) | Passed |
| Landing lint | Passed |
| Knowledge ingestion tests | 129 passed, 2 skipped; two un-awaited mock warnings |
| Realtime agent with its own virtual environment | 27 passed |
| Boundary, skillpack, and Markdown link checks | Passed |

## Recommended delivery sequence

1. **P0 vertical path:** registry API consistency, raw-byte HMAC, production compose wiring, no development credential fallbacks.
2. **P0 verification:** real multi-container event-to-run-to-callback smoke test plus negative authentication tests.
3. **P1 quality:** Ruff, mypy, MCP tenant-context contract, and reproducible local service tests.
4. **P2 hardening:** canonical documentation index, component boundaries, and dependency modernization.

Each phase should be merged only when its targeted test suite and the affected production-path smoke tests pass.
