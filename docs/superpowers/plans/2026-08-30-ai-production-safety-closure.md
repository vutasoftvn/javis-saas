# AI Production Safety Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Allow governed direct user chat input to reach the production model only with verifiable data-egress context, while restoring the failing quality gates.

**Architecture:** Company remains the authority for approved provider/model, purpose, retention, and data-use authorization. COSA gets a provenance-complete private snapshot, creates a claim from server-derived message provenance plus explicit user classification, and calls the existing fail-closed gate. Flutter collects classification only; it never selects governance values.

**Tech Stack:** Python/FastAPI/Pydantic, OpenAI Agents SDK integration, TypeScript/Encore/Drizzle, Flutter/Dart, Docker Compose, pytest, Vitest, Flutter test, npm.

**Spec:** docs/superpowers/specs/2026-08-30-ai-production-safety-closure-design.md

## Global Constraints

- Work directly on main; do not create a git worktree.
- services/company remains business truth; packages/agent must not import Company code.
- Missing classification, provenance, approval, provider/model, or authorization denies before the model call; no defaults.
- Never write raw prompts, delegation JWTs, or secret values into durable events or audit logs.
- Only direct user text is enabled. Attachments, retrieval, connector output, autopilot, and copilot remain blocked.
- Every behavior change begins with a focused failing test and ends with that test passing before commit.

---

## File structure

| Path | Responsibility |
|---|---|
| deploy/central_vps/docker-compose.prod.yaml | Required delegation secret for production consumers. |
| .env.example, deploy/central_vps/.env.prod.example, docs/operations/secrets.md, docs/runbooks/prod-cutover.md | Secret declaration, rotation, and cutover evidence. |
| tests/deploy/test_production_compose_contract.py | Static Compose secret consumer contract. |
| services/company/finance-legal/services/ai-compliance-snapshot.service.ts | Source of private snapshot provenance. |
| packages/agent/contracts/spec.py and apps/cosa/agents/specs.py | Non-tool direct-model-input capability declaration. |
| apps/cosa/compliance/data_egress_context.py | Immutable provenance and claim construction. |
| apps/cosa/compliance/contracts.py, company_client.py, resolver.py | Snapshot contract and claim resolution. |
| apps/cosa/api/schemas.py, routes.py, apps/cosa/worker/handlers.py | API validation and durable propagation. |
| frontend/lib/modules/chat | Classification input and serialization. |
| tests/e2e/test_ai_compliance_company_http.py | Real Company HTTP allow/deny proof. |

## Task 1: Require and document the delegation secret

**Files:**
- Create: tests/deploy/test_production_compose_contract.py
- Modify: deploy/central_vps/docker-compose.prod.yaml:109-224
- Modify: .env.example, deploy/central_vps/.env.prod.example, docs/operations/secrets.md, docs/runbooks/prod-cutover.md

**Interfaces:**
- Consumes: apps/cosa/auth/jwt.py::_get_company_delegation_secret and services/company/shared/auth/cosa-delegation.service.ts::getDelegationSecret.
- Produces: a required COSA_COMPANY_DELEGATION_SECRET on services-company, cosa-api, and cosa-worker.

- [ ] **Step 1: Write the failing deployment contract**

    def test_all_delegation_consumers_require_the_secret() -> None:
        compose = Path("deploy/central_vps/docker-compose.prod.yaml").read_text()
        for service in ("services-company:", "cosa-api:", "cosa-worker:"):
            body = compose.split(service, 1)[1].split("\n  # --------------------------------------------------------------------------", 1)[0]
            assert "COSA_COMPANY_DELEGATION_SECRET" in body

- [ ] **Step 2: Run the test to verify failure**

Run: PYTHONPATH=packages:. .venv/bin/pytest tests/deploy/test_production_compose_contract.py -q

Expected: FAIL because none of the three service blocks provides the secret.

- [ ] **Step 3: Implement the deployment closure**

Add the required Compose secret expression to all three consumers. Add a development-only placeholder and a blank production example. Document shared-secret rotation as deploy-all-three, staging verification, and old-value revocation. Add it to the pre-go-live checklist; do not alter platform/session/service tokens.

- [ ] **Step 4: Verify and commit**

Run: PYTHONPATH=packages:. .venv/bin/pytest tests/deploy/test_production_compose_contract.py -q

Run: git diff --check

    git add tests/deploy/test_production_compose_contract.py deploy/central_vps/docker-compose.prod.yaml .env.example deploy/central_vps/.env.prod.example docs/operations/secrets.md docs/runbooks/prod-cutover.md
    git commit -m "fix(deploy): require company delegation secret"

## Task 2: Expose provenance in Company runtime snapshots

**Files:**
- Modify: services/company/finance-legal/services/ai-compliance-snapshot.service.ts:64-82,401-421
- Modify: services/company/finance-legal/tests/ai-compliance-runtime-snapshot.test.ts
- Modify: services/company/finance-legal/tests/ai-compliance-private-contract.test.ts

**Interfaces:**
- Consumes: selected approved aiProviderProfiles and aiDataProcessingProfiles.
- Produces: non-null providerKey, modelKey, purposeId, and retentionPolicyId on RuntimeComplianceSnapshot.

- [ ] **Step 1: Add failing contract assertions**

    expect(snapshot).toMatchObject({
      providerKey: "deepseek",
      modelKey: "deepseek-chat",
      purposeId: "runtime-resolve-test",
      retentionPolicyId: "retention-30d",
    });

- [ ] **Step 2: Run the focused test to verify failure**

Run: pnpm --dir services/company test -- ai-compliance-runtime-snapshot.test.ts

Expected: FAIL because the private response omits provenance.

- [ ] **Step 3: Implement at the Company source**

Extend RuntimeComplianceSnapshot and resolveApprovedComplianceSnapshot with providerProfile.providerKey, providerProfile.modelKey, dataProfile.purposeId, and dataProfile.retentionPolicyId. Do not add a migration and do not default absent profile data.

- [ ] **Step 4: Verify and commit**

Run: pnpm --dir services/company typecheck && pnpm --dir services/company test -- ai-compliance-runtime-snapshot.test.ts ai-compliance-private-contract.test.ts

    git add services/company/finance-legal/services/ai-compliance-snapshot.service.ts services/company/finance-legal/tests/ai-compliance-runtime-snapshot.test.ts services/company/finance-legal/tests/ai-compliance-private-contract.test.ts
    git commit -m "feat(compliance): expose runtime snapshot provenance"

## Task 3: Declare direct model input as a non-tool scope

**Files:**
- Modify: packages/agent/contracts/spec.py
- Modify: apps/cosa/agents/specs.py
- Modify: tests/agent/contracts/test_agent_spec.py
- Modify: tests/apps/cosa/compliance/test_resolver.py
- Modify: services/company/finance-legal/services/ai-compliance-e2e-seed.service.ts

**Interfaces:**
- Consumes: AgentSpec.capability_refs, which remain executable tool capabilities.
- Produces: AgentSpec.model_input_capability_ref, set to model.input.direct-user-message for chat-capable profiles. Resolver validates it through Company but kernel does not expose it as a tool.

- [ ] **Step 1: Write the failing AgentSpec and resolver tests**

    async def test_resolver_requests_non_tool_input_scope() -> None:
        await resolver.resolve_for_run(request, spec)
        assert client.snapshot_request["capability_ids"] == [
            "operations.task.list",
            "model.input.direct-user-message",
        ]

- [ ] **Step 2: Run the tests to verify failure**

Run: PYTHONPATH=packages:. .venv/bin/pytest tests/agent/contracts/test_agent_spec.py tests/apps/cosa/compliance/test_resolver.py -q

Expected: FAIL because the field and requested scope do not exist.

- [ ] **Step 3: Implement the separate scope**

Add required model_input_capability_ref to AgentSpec, populate chat-capable COSA profiles, and append it exactly once in ComplianceResolver snapshot/delegation scope. Leave kernel tool construction driven exclusively by capability_refs. Add matching approved binding to the Company E2E seed.

- [ ] **Step 4: Verify and commit**

Run: PYTHONPATH=packages:. .venv/bin/pytest tests/agent/contracts/test_agent_spec.py tests/apps/cosa/compliance/test_resolver.py tests/agent -q

    git add packages/agent/contracts/spec.py apps/cosa/agents/specs.py tests/agent/contracts/test_agent_spec.py tests/apps/cosa/compliance/test_resolver.py services/company/finance-legal/services/ai-compliance-e2e-seed.service.ts
    git commit -m "feat(agent): declare direct model input scope"

## Task 4: Build the immutable egress-context boundary

**Files:**
- Create: apps/cosa/compliance/data_egress_context.py
- Modify: apps/cosa/compliance/contracts.py, company_client.py, resolver.py
- Create: tests/apps/cosa/compliance/test_data_egress_context.py
- Modify: tests/apps/cosa/compliance/test_data_model_gate.py and test_resolver.py

**Interfaces:**
- Consumes: DirectMessageDataAccess(categories, subject_reference, source_ref, source_hash) and a provenance-complete ComplianceSnapshot.
- Produces: a frozen DataAccessClaim with provider/model/purpose/retention derived only from the snapshot.

- [ ] **Step 1: Write failing context and client-contract tests**

    def test_direct_message_context_hashes_server_content() -> None:
        context = DirectMessageDataAccess.from_message(
            message_id="msg_1",
            content="confidential plan",
            categories=frozenset({"BUSINESS_CONFIDENTIAL"}),
            subject_reference=None,
        )
        assert context.source_ref == "conversation_message:msg_1"
        assert context.source_hash == hashlib.sha256(b"confidential plan").hexdigest()

    async def test_missing_provider_key_is_a_contract_violation() -> None:
        with pytest.raises(AiComplianceUnavailable, match="CONTRACT_VIOLATION"):
            await client.resolve_snapshot(request)

- [ ] **Step 2: Run the tests to verify failure**

Run: PYTHONPATH=packages:. .venv/bin/pytest tests/apps/cosa/compliance/test_data_egress_context.py tests/apps/cosa/compliance/test_resolver.py tests/apps/cosa/compliance/test_data_model_gate.py -q

Expected: FAIL because context and required provenance fields do not exist.

- [ ] **Step 3: Implement the boundary**

Create frozen Pydantic context models that reject empty categories and personal categories without subject_reference. Make all four snapshot fields required in the client. After snapshot resolution, resolver builds data_access_claim only from valid direct-message context and model_input_capability_ref; otherwise it raises ComplianceDenied with DATA_ACCESS_CLAIM_MISSING.

- [ ] **Step 4: Verify and commit**

Run: PYTHONPATH=packages:. .venv/bin/pytest tests/apps/cosa/compliance/test_data_egress_context.py tests/apps/cosa/compliance/test_resolver.py tests/apps/cosa/compliance/test_data_model_gate.py -q

    git add apps/cosa/compliance/data_egress_context.py apps/cosa/compliance/contracts.py apps/cosa/compliance/company_client.py apps/cosa/compliance/resolver.py tests/apps/cosa/compliance/test_data_egress_context.py tests/apps/cosa/compliance/test_resolver.py tests/apps/cosa/compliance/test_data_model_gate.py
    git commit -m "feat(compliance): derive direct-message egress claims"

## Task 5: Validate and durably propagate message classification

**Files:**
- Modify: apps/cosa/api/schemas.py:38-67
- Modify: apps/cosa/api/routes.py:260-321
- Modify: apps/cosa/worker/handlers.py:96-240
- Modify: tests/apps/cosa/test_routes.py and tests/apps/cosa/worker/test_handlers.py

**Interfaces:**
- Consumes: HTTP MessageCreate.data_access with categories and optional subject_reference.
- Produces: durable data_access_context with server-generated source reference/hash, copied to RunRequest.metadata["direct_message_data_access"].

- [ ] **Step 1: Write failing endpoint and worker tests**

    async def test_message_without_data_access_is_rejected_before_dispatch(client) -> None:
        response = await client.post(url, json={"content": "plan next quarter"})
        assert response.status_code == 422

    async def test_worker_forwards_server_provenance() -> None:
        await execute_run_task(payload)
        context = resolver.request.metadata["direct_message_data_access"]
        assert context["source_ref"] == "conversation_message:msg_123"
        assert context["source_hash"] != "plan next quarter"

- [ ] **Step 2: Run the tests to verify failure**

Run: PYTHONPATH=packages:. .venv/bin/pytest tests/apps/cosa/test_routes.py tests/apps/cosa/worker/test_handlers.py -q

Expected: FAIL because the request and durable payload have no classification.

- [ ] **Step 3: Implement validation and propagation**

Add MessageDataAccess Pydantic schema. Reject missing/empty classification and personal data without a subject reference before storing/scheduling an AI run. After add_message returns its ID, derive source reference/hash from stored message content; persist only context in scheduled payload and forward it to RunRequest metadata. Do not put raw content in metadata or events.

- [ ] **Step 4: Verify and commit**

Run: PYTHONPATH=packages:. .venv/bin/pytest tests/apps/cosa/test_routes.py tests/apps/cosa/worker/test_handlers.py -q

    git add apps/cosa/api/schemas.py apps/cosa/api/routes.py apps/cosa/worker/handlers.py tests/apps/cosa/test_routes.py tests/apps/cosa/worker/test_handlers.py
    git commit -m "feat(api): require chat data classification"

## Task 6: Collect explicit classification in Flutter chat

**Files:**
- Create: frontend/lib/modules/chat/models/data_access_declaration.dart
- Modify: frontend/lib/modules/chat/services/agent_chat_service.dart:151-177
- Modify: frontend/lib/modules/chat/controllers/chat_controller.dart:114-177
- Modify: frontend/lib/modules/chat/views/chat_view.dart:673-710
- Modify: frontend/test/modules/chat/chat_module_test.dart

**Interfaces:**
- Consumes: selected categories and optional subject reference.
- Produces: JSON data_access object only after local validation.

- [ ] **Step 1: Write failing service and widget tests**

    test('sendMessage serializes explicit data access', () async {
      await service.sendMessage('conv_1', content: 'Kế hoạch quý', dataAccess: declaration);
      expect(sentJson['data_access']['categories'], ['BUSINESS_CONFIDENTIAL']);
    });

    testWidgets('personal classification requires a subject reference', (tester) async {
      // Select PERSONAL, leave subject blank, then tap Send.
      expect(find.textContaining('subject'), findsOneWidget);
    });

- [ ] **Step 2: Run the chat tests to verify failure**

Run: cd frontend && flutter test test/modules/chat/chat_module_test.dart

Expected: FAIL because no declaration, serialization, or required classification UI exists.

- [ ] **Step 3: Implement minimal safe UX**

Create immutable declaration data. Add category chips and a conditional subject-reference input above the composer. Disable Send until valid classification exists; pass it through controller and service. Reject attachment-only model submissions with explicit UI feedback because attachment egress is out of scope.

- [ ] **Step 4: Verify and commit**

Run: cd frontend && flutter test test/modules/chat/chat_module_test.dart && flutter analyze

    git add frontend/lib/modules/chat/models/data_access_declaration.dart frontend/lib/modules/chat/services/agent_chat_service.dart frontend/lib/modules/chat/controllers/chat_controller.dart frontend/lib/modules/chat/views/chat_view.dart frontend/test/modules/chat/chat_module_test.dart
    git commit -m "feat(chat): classify direct model input"

## Task 7: Prove real Company HTTP allow/deny behavior

**Files:**
- Modify: tests/e2e/test_ai_compliance_company_http.py
- Modify: tests/apps/cosa/test_api_contracts.py
- Modify: tests/apps/cosa/compliance/test_process_smoke.py

**Interfaces:**
- Consumes: the snapshot provenance, non-tool scope, and direct-message claim from Tasks 2–5.
- Produces: one real HTTP allowed model invocation and zero model calls for denied cases.

- [ ] **Step 1: Write failing E2E cases**

    async def test_approved_direct_business_input_reaches_model_once(real_company_service) -> None:
        result = await run_direct_message(categories={"BUSINESS_CONFIDENTIAL"})
        assert result.status is RunStatus.COMPLETED
        assert fake_model.call_count == 1

    async def test_withdrawn_personal_authorization_never_reaches_model(real_company_service) -> None:
        result = await run_direct_message(categories={"PERSONAL"}, subject_reference=withdrawn_subject)
        assert result.status is RunStatus.FAILED
        assert fake_model.call_count == 0

- [ ] **Step 2: Verify the current gap**

Run: PYTHONPATH=packages:. .venv/bin/pytest tests/e2e/test_ai_compliance_company_http.py -q

Expected: FAIL until Tasks 2–5 are fully wired. This starts/migrates the Company E2E database; use isolated CI database configuration only.

- [ ] **Step 3: Turn async mock warnings into assertions**

Replace every unawaited async mock in the listed API/process tests with an awaited call or AsyncMock.assert_awaited_* assertion. Do not suppress RuntimeWarning.

- [ ] **Step 4: Verify and commit**

Run: PYTHONPATH=packages:. .venv/bin/pytest tests/e2e/test_ai_compliance_company_http.py tests/apps/cosa/test_api_contracts.py tests/apps/cosa/compliance/test_process_smoke.py -q -W error::RuntimeWarning

    git add tests/e2e/test_ai_compliance_company_http.py tests/apps/cosa/test_api_contracts.py tests/apps/cosa/compliance/test_process_smoke.py
    git commit -m "test(compliance): prove direct-message egress controls"

## Task 8: Restore lint, typing, and stale fixture gates

**Files:**
- Modify: apps/cosa/compliance/company_client.py, apps/cosa/composition/agent_plane.py, apps/cosa/worker/handlers.py, packages/agent/capabilities/gateway.py
- Modify: services/company/operations/tests/executive-context.test.ts
- Modify: landing/src/components/layout/Navbar.tsx, landing/src/components/sections/BentoFeatures.tsx, landing/src/components/sections/LeadFormSection.tsx

**Interfaces:**
- Consumes: current Ruff, mypy, Company test, and ESLint diagnostics.
- Produces: unchanged product behavior with green static gates.

- [ ] **Step 1: Reproduce failures**

Run: make lint typecheck-py

Run: pnpm --dir services/company test -- executive-context.test.ts

Run: cd landing && npm run lint

Expected: current missing types, gateway list normalization errors, lower-case status failures, and five unused imports.

- [ ] **Step 2: Write the gateway regression test**

    async def test_gateway_handles_missing_snapshot_evidence_lists(test_setup) -> None:
        gateway, request = test_setup
        request.context = {"metadata": {"compliance_snapshot": {"status": "APPROVED_FOR_USE"}}}
        result = await gateway.execute(request)
        assert result.status == "completed"

Use the existing public gateway method and test file; do not export a helper only for static typing.

- [ ] **Step 3: Apply minimal fixes**

Import or resolve missing Python types, sort imports, and narrow Any/list/None values before list conversion. Change only stale status fixture values from active to ACTIVE. Remove only the five ESLint-reported imports.

- [ ] **Step 4: Verify and commit**

Run: make lint typecheck-py

Run: pnpm --dir services/company typecheck && pnpm --dir services/company test -- executive-context.test.ts

Run: cd landing && npm run lint && npm run build

git add apps/cosa/compliance/company_client.py apps/cosa/composition/agent_plane.py apps/cosa/worker/handlers.py packages/agent/capabilities/gateway.py services/company/operations/tests/executive-context.test.ts landing/src/components/layout/Navbar.tsx landing/src/components/sections/BentoFeatures.tsx landing/src/components/sections/LeadFormSection.tsx
    git commit -m "fix(quality): restore lint typecheck and fixtures"

## Task 9: Release-level verification

**Files:**
- Modify: docs/superpowers/specs/2026-08-30-ai-production-safety-closure-design.md only if tests reveal a factual correction.

**Interfaces:**
- Consumes: Tasks 1–8.
- Produces: evidence that direct text runs only when governed and all affected CI gates are green.

- [ ] **Step 1: Run Python and contract verification**

Run: make contracts-check route-inventory-check lint typecheck-py

Run: PYTHONPATH=packages:. .venv/bin/pytest tests/agent packages/agent_testkit tests/apps/cosa -m 'not integration' -q

- [ ] **Step 2: Run Company, Flutter, landing, and E2E verification**

Run: pnpm --dir services/company typecheck && pnpm --dir services/company test

Run: cd frontend && flutter test && flutter analyze

Run: cd landing && npm run lint && npm run build && npm audit --omit=dev --audit-level=high

Run: PYTHONPATH=packages:. .venv/bin/pytest tests/e2e/test_ai_compliance_company_http.py -q

- [ ] **Step 3: Inspect delivery integrity**

Run: git diff --check && git status --short

Expected: all commands pass; no whitespace errors or unrelated files are present.

- [ ] **Step 4: Commit factual evidence update only when the spec changed**

    git add docs/superpowers/specs/2026-08-30-ai-production-safety-closure-design.md
    git commit -m "docs: record AI safety verification"
