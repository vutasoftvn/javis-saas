# Audit P0/P1 Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Repair the confirmed cross-service runtime-signal defect and restore the failing Python and generated-contract quality gates, while preserving the existing four-plane architecture and truthful release evidence.

**Architecture:** Company owns the internal event route and its durable, idempotent projection. COSA's outbox publisher sends a signed internal HTTP request to that route. The Agent ExecutionKernel protocol describes the common behavioral surface of every selectable adapter; streaming is an async-iterator-producing method, and adapters normalize their events through the owned run repository.

**Tech Stack:** Python 3.12, FastAPI, httpx, Ruff, mypy, pytest, TypeScript/Encore, Vitest, PostgreSQL, Flutter/Dart, GitHub Actions.

**Spec:** docs/superpowers/specs/2026-08-31-audit-p0-p1-remediation-design.md

## Global constraints

- Preserve the existing Company, Control Plane, Agent Platform, and Flutter ownership boundaries. No direct cross-plane database access.
- Do not change public product endpoints, existing migrations, production infrastructure, credentials, Caddy configuration, or deployment state in this plan.
- Start every behavior change with the stated focused failing test. Do not repair a test by weakening its assertion.
- Do not use Any, cast, type-ignore comments, a broad except, or a false-success fallback to satisfy lint or mypy.
- A mock transport proves the publisher envelope only. It cannot be release evidence for the cross-language HTTP route; the real Company-process test is required.
- Treat all generated files as generator-owned. Do not hand-edit docs/architecture/generated/company-usage-inventory.md.
- Preserve pre-existing user changes. Before each task, inspect git status --short; stage only the files named by that task.
- This document does not supersede the approved maintainable-MVP design or duplicate its larger frontend, security, and architectural workstreams.

---

## Delivery order

| Wave | Deliverable | Exit gate |
| --- | --- | --- |
| 0 | Clean baseline and reproduce the three broken gates | Failures match the audit evidence and working tree is understood |
| 1 | Exact COSA-to-Company runtime-signal contract | Unit envelope test plus real Company HTTP contract pass |
| 2 | Correct Python lint and kernel/gateway/seed typing | Ruff, targeted tests, and mypy pass without suppression |
| 3 | Regenerated Company usage inventory and release evidence | Contract freeze and complete proportional verification pass |
| 4 | Approved follow-on program work | Existing plans run in dependency order; no duplicate broad rewrite |

## File map

| Path | Responsibility after this plan |
| --- | --- |
| apps/cosa/events/runtime_signal.py | Publish runtime signals only to the authoritative Company internal route. |
| tests/apps/cosa/test_runtime_signal_delivery.py | Assert publisher method, path, authorization, and payload. |
| tests/e2e/test_agent_runtime_signal_http.py | Prove Company accepts the real internal HTTP delivery contract. |
| packages/agent/contracts/kernel.py | Define the correct common kernel stream interface. |
| packages/agent_integrations/openai_agents_sdk/kernel.py | Implement normalized streaming for the selectable OpenAI Agents SDK runtime. |
| apps/cosa/composition/kernel_factory.py | Return only complete ExecutionKernel implementations. |
| packages/agent/capabilities/gateway.py | Return concrete gateway results and non-null idempotency failure detail. |
| apps/cosa/agents/seed.py | Register seeded capabilities with a type-preserving representation. |
| docs/architecture/generated/company-usage-inventory.md | Generated snapshot of current Company usage classification. |
| docs/architecture/reports/2026-08-31-audit-p0-p1-remediation-evidence.md | Immutable release-evidence record produced after all gates pass. |

## Task 0: Reproduce and record the starting state

**Files:**

- Create: docs/architecture/reports/2026-08-31-audit-p0-p1-remediation-evidence.md (only after Wave 3 passes)
- No source change in this task.

- [x] **Step 1: Protect the current working tree**

Run:

    git status --short
    git diff --check
    git rev-parse HEAD

Expected: identify any user-owned work before editing. Save the final command's SHA as AUDIT_P0P1_BASE_SHA in the task notes; it is the comparison base for the complete remediation. If an intended file is already modified by the user, stop and obtain a conflict-free scope before changing it.

- [x] **Step 2: Reproduce the three release-blocking checks**

Run:

    make lint
    make typecheck-py
    make contract-freeze-check

Expected before implementation:

- Ruff reports the unused os import in apps/cosa/composition/agent_plane.py and unused Any import in apps/cosa/composition/capability_registration.py.
- Mypy reports the gateway optional-result/detail issues, seed overload issue, and incomplete/mismatched kernel adapters.
- Contract freeze reports a stale company-usage-inventory.md.

- [x] **Step 3: Save only command output metadata**

Record command, exit result, and date in the evidence document after the final successful run. Do not copy credentials, headers, access tokens, or customer data into the report.

## Task 1: Repair the runtime-signal delivery contract

**Files:**

- Modify: apps/cosa/events/runtime_signal.py:58-89
- Modify: tests/apps/cosa/test_runtime_signal_delivery.py:13-68
- Create: tests/e2e/test_agent_runtime_signal_http.py
- Inspect only: services/company/events/handlers/agent-runtime-signal.handler.ts:62-94
- Inspect only: services/company/events/agent-runtime-signal.api.ts or the current Encore route declaration that owns the endpoint

**Interfaces:**

- Produces: POST /events/internal/agent-runtime-signal
- Required headers: Authorization: Bearer <service-token> and Content-Type: application/json
- Body: the existing runtime-signal envelope, including stable source identity/idempotency fields. No schema expansion in this task.

- [x] **Step 1: Make the publisher test prove the complete request**

Extend the current httpx.MockTransport handler so it records request.method, request.url.path, request.headers, and decoded JSON, rather than only the JSON body. Add assertions for all of the following:

    assert captured["method"] == "POST"
    assert captured["path"] == "/events/internal/agent-runtime-signal"
    assert captured["authorization"] == "Bearer service-token"
    assert captured["content_type"].startswith("application/json")
    assert captured["json"] == expected_signal_envelope

Use the test's configured non-secret test token. Retain the existing retry/non-delivery assertions and add a negative response test proving 401 and 404 are returned as delivery failure rather than recorded as successful publication.

- [x] **Step 2: Run the focused test before changing production code**

Run:

    pytest -q tests/apps/cosa/test_runtime_signal_delivery.py

Expected before implementation: FAIL because the captured path is /events/agent-runtime-signals.

- [x] **Step 3: Correct the single publisher endpoint**

In apps/cosa/events/runtime_signal.py, replace the outbound suffix with exactly:

    /events/internal/agent-runtime-signal

Do not add a compatibility call, second delivery attempt, redirect, route alias, or separate raw body format. The Company handler's canonical route is the single source for this contract.

- [x] **Step 4: Add real Company-process contract proof**

Follow the existing real-service fixture style in tests/e2e/. The new test must start or target the isolated real Company process; it must not import ASGITransport, MockTransport, AsyncMock, a fake repository, or monkeypatch the HTTP client.

Post the smallest valid runtime-signal envelope to /events/internal/agent-runtime-signal with the fixture's configured internal service token. Assert a success response and the observable idempotent effect defined by the handler (accepted projection/event identity). Then repeat the same source identity and assert it does not create a duplicate projection. Add negative assertions that an old plural route returns 404 and a missing or invalid service token is rejected.

If the existing e2e fixture lacks a real Company service or database, add the smallest reusable fixture in its established conftest module; do not replace it with an in-process ASGI test.

- [x] **Step 5: Verify the contract at unit and real-service levels**

Run:

    pytest -q tests/apps/cosa/test_runtime_signal_delivery.py
    pytest -q tests/e2e/test_agent_runtime_signal_http.py

Expected: exact URL, headers, and payload pass in the publisher test; Company accepts the real canonical request once and rejects old or unauthorized requests.

- [x] **Step 6: Commit the isolated P0 repair**

    git add apps/cosa/events/runtime_signal.py tests/apps/cosa/test_runtime_signal_delivery.py tests/e2e/test_agent_runtime_signal_http.py
    git commit -m "fix(events): deliver runtime signals to company contract"

## Task 2: Restore lint and type safety with behavioral tests

**Files:**

- Modify: apps/cosa/composition/agent_plane.py:1-12
- Modify: apps/cosa/composition/capability_registration.py:1-12
- Modify: packages/agent/contracts/kernel.py:13-45
- Modify: packages/agent_integrations/openai_agents_sdk/kernel.py:65-420
- Modify: apps/cosa/composition/kernel_factory.py:78-159
- Modify: packages/agent/capabilities/gateway.py:421-540
- Modify: apps/cosa/agents/seed.py:42-72
- Modify or create: focused gateway, kernel factory, OpenAI SDK kernel, and seed-registration tests in their existing corresponding test directories

**Interfaces:**

- ExecutionKernel.stream(request, spec) -> AsyncIterator[dict[str, Any]] is called with async-for; it is not awaited.
- Each runtime selectable through build_execution_kernel implements run, resume, cancel, and stream as required by ExecutionKernel.
- Denied gateway paths return GatewayExecutionResult and IdempotencyClaimService.fail receives a non-empty str detail.

- [x] **Step 1: Add regression tests for the actual typing and behavior boundaries**

Add or extend focused tests before modifying code:

1. A policy or compliance denied execution produces a concrete GatewayExecutionResult with the existing denied status/error contract, not None or an untyped value.
2. A connector or grant denial causes the idempotency claim to be failed with a deterministic non-empty detail; test the collaborator's received value, not only the outer HTTP result.
3. Every runtime exposed by kernel_factory can be treated as an ExecutionKernel; exercise at least the stream call shape with async-for for the manual loop and the Real OpenAI SDK adapter using existing fake model/repository test fixtures.
4. Seed registration invokes each capability registration through a type-preserving typed callable/spec pairing and preserves the existing resulting registry contents.

Name tests by the boundary they prove, for example test_denied_gateway_result_is_concrete, test_openai_agents_sdk_kernel_streams_owned_events, and test_seed_registration_preserves_capability_types.

- [x] **Step 2: Run focused tests and the failing type gate**

Run the exact selected test files, then:

    make typecheck-py

Expected before implementation: the new behavior tests expose missing stream/optional-result behavior where reachable, and mypy retains the ten audit errors.

- [x] **Step 3: Make the kernel protocol describe actual async-generator behavior**

Change only the protocol signature from async def stream(...) -> AsyncIterator[...] to:

    def stream(
        self,
        request: RunRequest,
        spec: AgentSpec,
    ) -> AsyncIterator[dict[str, Any]]:
        ...

Keep all existing adapter implementations as async def functions containing yield; Python and mypy model those as normal callables returning AsyncIterator. Add RealOpenAIAgentsSDKKernel.stream using the same normalized owned-event behavior as the other adapters: await run, read self._repo.list_events(result.run_id), and yield the standard event_id, event_type, payload, and sequence_no envelope. Preserve the adapter's existing error and cancellation behavior. Do not create a separate SSE format or claim token-by-token provider streaming when it does not exist.

Keep kernel_factory's return annotation as ExecutionKernel; do not paper over an incomplete implementation with cast.

- [x] **Step 4: Narrow gateway values at their semantic boundaries**

At the two deny-return sites in packages/agent/capabilities/gateway.py, return the concrete GatewayExecutionResult object already constructed for the denial path. Normalize optional grant denial detail exactly once before calling IdempotencyClaimService.fail, using the existing user-safe fallback message only when no specific detail exists. Retain structured error metadata; do not stringify exceptions or treat a denied action as completed.

- [x] **Step 5: Preserve seed callable overload types**

Replace the heterogeneous function/spec tuple that erases overload compatibility with either:

- explicit typed registration calls in a short, readable sequence; or
- a local typed registration object/protocol whose callable and spec type are paired.

Choose the smallest form that leaves the registry order and capability identifiers unchanged. Do not annotate the collection Any or force a call through an unchecked cast.

- [x] **Step 6: Remove only proven unused imports**

Delete os from apps/cosa/composition/agent_plane.py and Any from apps/cosa/composition/capability_registration.py after confirming neither is used. Do not run a repository-wide automatic import rewrite in this task.

- [x] **Step 7: Verify focused behavior and static contracts**

Run:

    make lint
    make typecheck-py
    pytest -q tests/agent tests/apps/cosa/composition tests/apps/cosa/agents

Expected: Ruff and mypy pass with no new ignores; every selected regression test passes. If the repository's focused test paths differ, use the existing test-file locations selected in Step 1 and record the exact paths in the evidence document.

- [x] **Step 8: Commit the type-safe repair**

    git add apps/cosa/composition/agent_plane.py apps/cosa/composition/capability_registration.py apps/cosa/composition/kernel_factory.py apps/cosa/agents/seed.py packages/agent/contracts/kernel.py packages/agent/capabilities/gateway.py packages/agent_integrations/openai_agents_sdk/kernel.py
    git add <exact focused test files>
    git commit -m "fix(agent): restore kernel and gateway type contracts"

Do not stage the whole tests directory; preserve unrelated user work.

## Task 3: Regenerate the Company usage inventory and freeze it

**Files:**

- Modify (generated): docs/architecture/generated/company-usage-inventory.md
- Inspect only: scripts/company_usage_inventory.py and the invoked Make target

- [x] **Step 1: Confirm the current discrepancy is generator-derived**

Run:

    make contract-freeze-check

Expected before regeneration: it reports only that company-usage-inventory.md is stale. If other checks fail, stop and return them to the owning workstream instead of hiding them inside a generated-doc commit.

- [x] **Step 2: Regenerate through the supported target**

Run:

    make company-usage-inventory
    git diff -- docs/architecture/generated/company-usage-inventory.md

Review that the diff changes inventory counts and locations from current source only (the audit baseline was REVIEW: 864 to 873). Do not edit the Markdown manually and do not alter classification policy in this task.

- [x] **Step 3: Freeze the generated output**

Run:

    make contract-freeze-check

Expected: the Company inventory subcheck, shared contract check, and route inventory check all pass.

- [x] **Step 4: Commit only the generated snapshot**

    git add docs/architecture/generated/company-usage-inventory.md
    git commit -m "docs(architecture): refresh company usage inventory"

## Task 4: Produce release evidence and run proportional regression gates

**Files:**

- Create: docs/architecture/reports/2026-08-31-audit-p0-p1-remediation-evidence.md
- Modify: docs/superpowers/plans/2026-08-31-audit-p0-p1-remediation.md only to mark completed checkboxes after each task succeeds

- [x] **Step 1: Run the full relevant release gate set from a clean checkout**

Run:

    make lint
    make typecheck-py
    make contract-freeze-check
    make python-test-unit
    make apps-cosa-test
    make frontend-analyze
    make frontend-test
    make boundary-check
    make frontend-boundary-check
    make company-boundary-check
    make mvp-e2e-purity-check
    make mvp-surface-check
    (cd services/company && pnpm typecheck && pnpm vitest run)
    (cd services/cosa && pnpm typecheck && pnpm vitest run)

If the new real-service test requires an explicitly provisioned local dependency, run it with its documented setup immediately before this gate and record the command/result. A missing prerequisite is unverified, not a passing skip.

- [x] **Step 2: Record evidence, not conclusions without data**

Write a concise Markdown table with each command, date, pass/fail status, test count where emitted, and commit SHA. Include the runtime-signal real-service test separately. State that frontend coverage remains a monitored 48.20% baseline with no new threshold in this remediation, and point to the approved maintainable-MVP program for its policy work.

- [x] **Step 3: Inspect the final diff and commit evidence**

Run:

    git status --short
    git diff --check
    git diff --stat AUDIT_P0P1_BASE_SHA..HEAD

Replace AUDIT_P0P1_BASE_SHA with the recorded immutable baseline SHA; do not compare only the previous evidence commit. Ensure no credentials, generated test caches, unrelated files, or user-owned edits are included. Commit the evidence document only after every stated required gate is green:

    git add docs/architecture/reports/2026-08-31-audit-p0-p1-remediation-evidence.md docs/superpowers/plans/2026-08-31-audit-p0-p1-remediation.md
    git commit -m "docs(quality): record audit remediation evidence"

## Task 5: Decision gate for removed architecture source documents

**Files:**

- Inspect: CLAUDE.md:16-28
- Inspect: commit 34507dd9
- Modify only after explicit decision: CLAUDE.md and the selected documentation target

- [x] **Step 1: Obtain an architecture-owner decision**

Present the evidence that four named source-of-truth documents were removed in 34507dd9. Request exactly one approved action:

1. keep deleted and remove or replace stale references;
2. archive historical snapshots, clearly non-canonical and tagged with the removal/source commit; or
3. author a canonical successor with current ADRs and active plans.

No restoration occurs merely to make a warning disappear.

- [x] **Step 2: Execute the selected documentation path as a separate documentation-only commit**

For option 1, update all references atomically and add a current document index. For option 2, preserve originals under an explicit archive path and add a non-canonical banner plus provenance. For option 3, create docs/architecture/ARCHITECTURE_SOURCE_OF_TRUTH.md containing active owners, ADRs, and plan links, then repoint CLAUDE.md to it. In all cases, validate links with rg and review the diff; do not edit application code.

## Follow-on program sequence (not implemented by this plan)

| Priority | Owned plan/spec | Work to execute after this remediation | Entry condition |
| --- | --- | --- | --- |
| P1 | docs/superpowers/plans/2026-08-31-maintainable-mvp-agent-control-e2e.md | Expand real-stack Agent/Company/control-plane E2E, including fail-closed runtime configuration. | Task 1 real HTTP contract is green. |
| P1 | docs/superpowers/specs/2026-08-31-maintainable-modular-truthful-mvp-design.md | Typed ApiResult migration, error-state truthfulness, frontend feature boundaries, and progressive retirement of dynamic. | Common release gates are green. |
| P1 | docs/superpowers/plans/2026-08-31-backend-frontend-security-quality-remediation.md | Tenant/auth hardening, landing validation, static-analysis enforcement, and delivery evidence. | This remediation is merged; duplicate task IDs are reconciled. |
| P2 | The approved MVP design plus a new approved security-hardening spec | Replace root container execution, remove Docker npm-install fallback, and add pinned dependency/container scanning/SBOM policy. | Infrastructure owner approves image, scanner, and rollout policy. |
| P2 | New coverage-policy task under the approved MVP design | Establish a ratcheting frontend coverage baseline, initially at or below measured current coverage, then set risk-module floors and CI enforcement. | Baseline test collection is reproducible in CI. |

## Final verification checklist

- [x] The runtime-signal publisher uses /events/internal/agent-runtime-signal and tests its complete HTTP envelope.
- [x] A real Company-process test accepts the canonical request once, rejects the old route/invalid token, and proves idempotency.
- [x] Ruff and mypy are clean without suppression, including all selectable ExecutionKernel adapters.
- [x] The Company inventory is regenerated through its Make target and contract freeze passes.
- [ ] Full proportional gates and both TypeScript services remain green.
- [x] Release evidence contains reproducible commands and final commit SHAs; it never treats a skipped dependency as a pass.
- [x] Architecture-document restoration/replacement waits for the explicit decision gate.
