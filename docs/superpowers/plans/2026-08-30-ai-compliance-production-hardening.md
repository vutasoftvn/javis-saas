# AI Compliance Production Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Đưa luồng quản trị AI của COSA sang đường chạy production an toàn: cô lập workspace ở từng resource, delegation có ràng buộc, snapshot chỉ từ deployment đã phê duyệt, evidence pháp lý có phiên bản và UI/API cùng một contract.

**Architecture:** services/company/finance-legal là nguồn sự thật cho deployment, assessment, evidence, provider/data profile và snapshot. apps/cosa chỉ nhận delegation ngắn hạn để lấy snapshot và gọi capability. packages/agent mang định danh delegation trong InvocationContext, nhưng không sở hữu dữ liệu pháp lý. Thiếu dữ liệu, sai scope, token hết hạn, snapshot cũ hoặc contract sai đều phải từ chối trước model call hay external capability.

**Tech Stack:** Encore/TypeScript, Drizzle/PostgreSQL, FastAPI/Python/Pydantic, OpenAI Agents SDK integration, Flutter/Dart, Vitest, pytest, Flutter test, GitHub Actions.

**Spec:** docs/superpowers/specs/2026-08-29-ai-compliance-design.md. Kế hoạch này sửa các khoảng cách production đã audit ngày 2026-08-30 mà đặc tả chưa phản ánh đầy đủ.

## Global Constraints

- Làm trực tiếp trên nhánh main; không tạo git worktree.
- services/company là business truth. Agent, frontend và model không được ghi trực tiếp vào database pháp lý.
- Không sửa các migration đã áp dụng 27_ai_compliance_governance và 28_ai_compliance_legal_sources; mọi sửa schema/seed là migration mới có cả up và down.
- workspaceId lấy từ context đã xác thực hoặc delegation đã verify, không lấy từ body để cấp quyền. Resource lookup luôn scope theo id và workspaceId.
- Deployment chỉ chạy với mode ADVISORY_ONLY, status APPROVED_FOR_USE, assessment/evidence/provider/data profile còn hiệu lực và capability binding chính xác.
- Không ghi prompt, completion, tài liệu gốc, subject reference hay bearer token vào audit/log/snapshot. Chỉ lưu URI phân quyền, hash, ID và metadata tối thiểu.
- Không thêm matter_id, connector filesystem hay regulatory monitor trong đợt này.
- Không coi keyword/static rule là kết luận pháp lý. Rule bắt buộc phải trỏ tới source version đã xác thực và được reviewer pháp lý phê duyệt.

## Decisions Locked by This Plan

1. Thêm private Company contract POST /finance-legal/ai-compliance/runtime/resolve-snapshot. Route này không tạo deployment, assessment hay profile.
2. Delegation Company có audience company, issuer cosa, TTL tối đa 10 phút, jti, workspace_id, principal_id, run_id và capability_ids.
3. Snapshot chứa ID/version/hash của assessment, evidence, provider profile, data profile, capability binding và legal source version. Hash bao phủ toàn bộ field; expiry là giá trị sớm nhất của các đầu vào.
4. Data model gate dùng DataAccessClaim có nguồn gốc; không suy đoán PERSONAL/BUSINESS_CONFIDENTIAL cho mọi prompt và không dùng redactor như cơ chế phân loại pháp lý.
5. Flutter gọi đúng route ai-compliance, gửi X-Workspace-Id, và chỉ render/mutation theo DTO server đã kiểm thử.

## File Structure

| File | Vai trò |
| --- | --- |
| services/company/finance-legal/services/ai-compliance-access.service.ts | Resolver fail-closed cho deployment, assessment, authorization và incident theo workspace. |
| services/company/finance-legal/services/ai-compliance-snapshot.service.ts | Resolve snapshot approved, capability/rule/evidence và canonical hash; bỏ auto-create. |
| services/company/finance-legal/handlers/ai-compliance-runtime.handler.ts | Private runtime endpoint nhận Company delegation, trả snapshot versioned. |
| services/company/shared/auth/cosa-delegation.service.ts | Verify token do COSA phát hành, audience/scope/TTL/jti, tạo TenantContext giới hạn. |
| services/company/finance-legal/migrations/29_ai_compliance_runtime_hardening.* | Ràng buộc workspace và provenance cần cho replay. |
| services/company/finance-legal/migrations/30_ai_legal_source_corrections.* | Bất hoạt seed sai và thêm source/version/rule đã xác thực. |
| apps/cosa/auth/jwt.py và dependency.py | Mint delegation Company theo identity đã xác thực. |
| apps/cosa/compliance/company_client.py và resolver.py | Gọi contract runtime với delegation, parse chặt và fail closed. |
| apps/cosa/worker/handlers.py | Propagate delegation và snapshot/policy metadata đến RunRequest. |
| packages/agent/contracts/invocation.py và packages/agent_integrations/openai_agents_sdk/kernel.py | Giữ delegation reference/claim trong invocation, không log token. |
| apps/cosa/compliance/data_access_claim.py | Pydantic model cho dữ liệu sẽ đi tới model/capability. |
| apps/cosa/compliance/data_model_gate.py | Enforce provider+model+category+purpose+authorization từ DataAccessClaim. |
| frontend/lib/modules/legal/services/ai_compliance_service.dart | Client route/body/header khớp public Company API. |
| frontend/lib/data/models/ai_compliance_models.dart | Mapping đúng Compliance Center response, assessment và incidents. |

---

### Task 1: Freeze contract, scope ownership and rejection semantics

**Files:**
- Create: docs/architecture/adr/ADR-AI-COMPLIANCE-RUNTIME-001.md
- Create: services/company/finance-legal/services/ai-compliance-access.service.ts
- Create: services/company/finance-legal/tests/ai-compliance-workspace-access.test.ts
- Modify: services/company/finance-legal/services/ai-compliance-governance.service.ts
- Modify: services/company/finance-legal/services/ai-data-governance.service.ts
- Modify: services/company/finance-legal/services/ai-compliance-snapshot.service.ts
- Modify: three existing finance-legal AI compliance handlers

**Interfaces:**
- Consumes: authenticated TenantContext.workspaceId from requireWorkspaceAccess.
- Produces: every mutation input has workspaceId; an out-of-scope ID returns the same public not-found response as an absent ID.

- [ ] **Step 1: Write the ADR**

Record the five decisions above and the invariant below.

~~~
type WorkspaceScopedId = {
  workspaceId: string | bigint;
  id: string | bigint;
};
// Every read and mutation uses WHERE id = :id AND workspace_id = :workspaceId.
~~~

- [ ] **Step 2: Add hostile workspace tests, then run them red**

~~~
it("does not mutate a deployment owned by another workspace", async () => {
  const deployment = await createApprovedDeployment(workspaceA);
  await expect(suspendAiDeployment({
    workspaceId: workspaceB,
    deploymentId: deployment.id,
    rationale: "attempt",
    suspendedByMemberId: founderB,
  })).rejects.toMatchObject({ status: 404 });
  expect((await getDeploymentInWorkspace(workspaceA, deployment.id)).status)
    .toBe("APPROVED_FOR_USE");
});
~~~

Run: cd services/company && pnpm vitest run finance-legal/tests/ai-compliance-workspace-access.test.ts
Expected: FAIL because the current lookup scopes only by id.

- [ ] **Step 3: Make every service input workspace-scoped**

Add workspaceId to ApproveAiAssessmentInput, SuspendAiDeploymentInput, ResumeAiDeploymentInput, withdrawal input, incident resolution input and snapshot verification input. The initial lookup and every update use and(eq(id), eq(workspaceId)). Do not accept an actor/member ID from the request body when TenantContext already supplies it.

Put the shared scoped lookup functions in ai-compliance-access.service.ts so governance, data-governance and snapshot services cannot drift into separate id-only implementations.

- [ ] **Step 4: Pass only verified context from public handlers**

~~~
return suspendAiDeployment({
  workspaceId: ctx.workspaceId,
  deploymentId: req.deploymentId,
  rationale: req.rationale,
  suspendedByMemberId: ctx.workforceMemberId || ctx.userId,
});
~~~

Apply the same pattern to approval, resume, withdrawal, incident resolution and snapshot verification.

- [ ] **Step 5: Run the focused suite**

Run: cd services/company && pnpm vitest run finance-legal/tests/ai-compliance-governance.test.ts finance-legal/tests/ai-compliance-workspace-access.test.ts finance-legal/tests/ai-data-governance.test.ts
Expected: PASS; deployment, authorization and incident of workspace A are indistinguishable from missing in workspace B.

- [ ] **Step 6: Commit**

~~~
git add docs/architecture/adr/ADR-AI-COMPLIANCE-RUNTIME-001.md services/company/finance-legal
git commit -m "fix: scope AI compliance resources to workspace"
~~~

### Task 2: Add database defense in depth for workspace ownership

**Files:**
- Create: services/company/finance-legal/migrations/29_ai_compliance_runtime_hardening.up.sql
- Create: services/company/finance-legal/migrations/29_ai_compliance_runtime_hardening.down.sql
- Modify: services/company/shared/db/schema/legal.ts
- Create: services/company/finance-legal/tests/ai-compliance-runtime-schema.test.ts

**Interfaces:**
- Consumes: tables introduced by migrations 27–28.
- Produces: snapshot stores capabilityBindingIds, evidenceIds, evidenceHashes, legalVersionIds, providerProfileId, dataProfileId and input expiry values. Child rows cannot reference a parent in another workspace.

- [ ] **Step 1: Write database regression test**

~~~
it("rejects a data profile that combines workspace B with deployment A", async () => {
  await expect(insertProfile({ workspaceId: workspaceB, deploymentId: deploymentA.id }))
    .rejects.toThrow();
});
~~~

Run: cd services/company && pnpm vitest run finance-legal/tests/ai-compliance-runtime-schema.test.ts
Expected: FAIL before the migration because foreign keys do not bind workspace equality.

- [ ] **Step 2: Write append-only migration 29**

Use composite unique keys on (workspace_id, id) for workspace-owned parents and composite foreign keys for children.

~~~
ALTER TABLE legal.workspace_ai_deployments
  ADD CONSTRAINT workspace_ai_deployments_workspace_id_id_key UNIQUE (workspace_id, id);

ALTER TABLE legal.ai_data_processing_profiles
  ADD CONSTRAINT ai_data_profiles_workspace_deployment_fk
  FOREIGN KEY (workspace_id, deployment_id)
  REFERENCES legal.workspace_ai_deployments (workspace_id, id);
~~~

Backfill existing snapshot provenance only from existing verified relationships. Mark legacy snapshots without full provenance unusable; do not fabricate any value.

- [ ] **Step 3: Reflect exact schema in Drizzle**

Expose the arrays/reference IDs and expiry fields with matching nullable/backfill rules. Do not create an ORM-only constraint.

- [ ] **Step 4: Apply migration in test DB and run tests**

Run: cd services/company && pnpm vitest run finance-legal/tests/ai-compliance-runtime-schema.test.ts finance-legal/tests/ai-compliance-snapshot.test.ts
Expected: PASS; cross-workspace inserts are rejected by PostgreSQL and models serialize every new snapshot field.

- [ ] **Step 5: Commit**

~~~
git add services/company/finance-legal/migrations/29_ai_compliance_runtime_hardening.* services/company/shared/db/schema/legal.ts services/company/finance-legal/tests/ai-compliance-runtime-schema.test.ts
git commit -m "feat: enforce AI compliance workspace ownership in database"
~~~

### Task 3: Implement constrained COSA-to-Company delegation

**Files:**
- Create: services/company/shared/auth/cosa-delegation.service.ts
- Create: services/company/shared/auth/cosa-delegation.test.ts
- Modify: apps/cosa/auth/jwt.py
- Modify: apps/cosa/auth/dependency.py
- Modify: tests/apps/cosa/auth/test_jwt_delegation.py

**Interfaces:**

~~~
interface CompanyDelegationClaims {
  iss: "cosa";
  aud: "company";
  sub: string;              // Company identity user/member ID
  workspace_id: string;
  principal_id: string;     // user:<id>
  run_id: string;
  capability_ids: string[];
  jti: string;
  exp: number;
}
~~~

- [ ] **Step 1: Write verification tests first**

~~~
it("rejects a valid signature when audience, workspace, run, or capability differs", () => {
  const token = mintCompanyDelegation({
    workspace_id: "w1", run_id: "r1", capability_ids: ["finance.read"],
  });
  expect(() => verifyCompanyDelegation(token, {
    workspaceId: "w2", runId: "r1", capabilityId: "finance.read",
  })).toThrow();
});
~~~

Run TypeScript and Python token tests.
Expected: FAIL because current delegation contains only sub, an optional cosa audience, and expiry.

- [ ] **Step 2: Mint Company-only delegation at COSA boundary**

Add mint_company_delegation to apps/cosa/auth/jwt.py. It accepts authenticated local Company user ID, verified workspace, generated run ID and exact declared capability IDs; it emits iss=cosa, aud=company, random jti and maximum 600-second expiry. Durable task payload never contains the original bearer token.

- [ ] **Step 3: Verify the claim in Company**

verifyCosaDelegation validates signature, issuer, audience, expiry, nonempty jti, requested workspace, requested run and requested capability. It returns a narrow context and does not call public membership resolution with an unverified header.

- [ ] **Step 4: Protect against replay for side effects**

Persist consumed jti + run_id + capability_id in existing Company idempotency/governance storage or a small Company-owned table for EXTERNAL and mutation calls. READ-only snapshot resolution is idempotent but never accepted after expiry.

- [ ] **Step 5: Run token tests**

Run: pytest tests/apps/cosa/auth/test_jwt_delegation.py -q && cd services/company && pnpm vitest run shared/auth/cosa-delegation.test.ts
Expected: PASS for valid token and for rejection of expired, altered, wrong-audience, wrong-workspace, wrong-run and out-of-scope capability tokens.

- [ ] **Step 6: Commit**

~~~
git add apps/cosa/auth services/company/shared/auth tests/apps/cosa/auth
git commit -m "feat: bind Company delegation to workspace run and capability"
~~~

### Task 4: Replace snapshot capture with approved runtime resolution

**Files:**
- Create: services/company/finance-legal/handlers/ai-compliance-runtime.handler.ts
- Create: services/company/finance-legal/tests/ai-compliance-runtime-snapshot.test.ts
- Modify: services/company/finance-legal/services/ai-compliance-snapshot.service.ts
- Modify: services/company/finance-legal/handlers/ai-compliance-snapshot.handler.ts
- Modify: apps/cosa/compliance/contracts.py
- Modify: apps/cosa/compliance/company_client.py
- Modify: apps/cosa/compliance/resolver.py
- Modify: tests/apps/cosa/compliance/test_resolver.py

**Interfaces:**

~~~
interface ResolveRuntimeSnapshotRequest {
  workspaceId: Header<"X-Workspace-Id">;
  authorization: Header<"Authorization">;
  runId: string;
  systemKey: string;
  capabilityIds: string[];
  policySnapshotHash: string;
}
~~~

Response contains approved-only data. Return 404 for nonexistent/out-of-scope system, 409 for incomplete or expired approval, and 403 for delegation scope failure.

- [ ] **Step 1: Replace auto-create test with failing fail-closed test**

~~~
it("does not create deployment or assessment when no approved deployment exists", async () => {
  await expect(resolveRuntimeComplianceSnapshot(requestWithoutDeployment))
    .rejects.toMatchObject({ status: 404 });
  expect(await countDeployments(workspaceId)).toBe(0);
});
~~~

Run: cd services/company && pnpm vitest run finance-legal/tests/ai-compliance-runtime-snapshot.test.ts
Expected: FAIL because captureComplianceSnapshot creates default system and assessment.

- [ ] **Step 2: Implement one approved-only resolver**

Select exactly one deployment by verified workspace and systemKey. Require advisory mode, approved status, current approved unexpired assessment, required evidence, approved matching provider profile, active matching data profile and declared capability bindings. Reject any empty query and any requested unbound capability.

~~~
export async function resolveRuntimeComplianceSnapshot(
  input: ResolveRuntimeSnapshotInput,
): Promise<RuntimeComplianceSnapshot>;
~~~

captureComplianceSnapshot becomes an admin/audit operation only if it calls the same resolver; runtime resolution never creates records. Existing list and verify routes scope snapshot ID by workspace.

- [ ] **Step 3: Calculate an evidence-complete hash**

Canonical payload includes deployment/assessment IDs and expiry, sorted binding IDs, sorted evidence {id, contentHash}, sorted legal version {id, contentHash}, provider/data profile IDs and versions, model key/version, policy hash, issued time and derived expiry. expiresAt is min(assessment, provider review, data profile, source review), never an arbitrary 90-day fallback.

- [ ] **Step 4: Add private handler and strict Python client**

Handler uses verifyCosaDelegation, not user requireWorkspaceAccess. AiComplianceClient.resolve_snapshot takes delegation_token and capability_ids, sets Authorization, and rejects missing or unknown fields rather than defaulting status/version.

- [ ] **Step 5: Run contract suites**

Run: cd services/company && pnpm vitest run finance-legal/tests/ai-compliance-runtime-snapshot.test.ts finance-legal/tests/ai-compliance-snapshot.test.ts && cd ../.. && pytest tests/apps/cosa/compliance/test_resolver.py -q
Expected: PASS; only approved, complete, unexpired deployment returns hash-valid snapshot with exact nonempty capabilities.

- [ ] **Step 6: Commit**

~~~
git add services/company/finance-legal apps/cosa/compliance tests/apps/cosa/compliance
git commit -m "fix: resolve AI compliance snapshots from approved state only"
~~~

### Task 5: Carry delegation and compliance state through real agent runs

**Files:**
- Modify: apps/cosa/api/routes.py
- Modify: apps/cosa/worker/handlers.py
- Modify: apps/cosa/composition/agent_plane.py
- Modify: packages/agent/contracts/invocation.py
- Modify: packages/agent_integrations/openai_agents_sdk/kernel.py
- Modify: apps/cosa/capabilities/client.py
- Create: tests/apps/cosa/compliance/test_run_delegation.py
- Create: tests/apps/cosa/compliance/test_company_client.py

**Interfaces:**
- RunRequest.metadata carries company_delegation_ref, never raw token in event/audit payload.
- InvocationContext.delegation_identity stores jti or nonsecret fingerprint. Sensitive metadata is excluded from event serialization.

- [x] **Step 1: Write end-to-end propagation test**

~~~
async def test_worker_passes_bound_delegation_to_snapshot_and_capability_clients():
    run = await execute_scheduled_run(payload_with_company_delegation())
    assert fake_snapshot_client.calls[0].authorization_claims["run_id"] == run.run_id
    assert fake_company_client.calls[0].headers["X-Workspace-Id"] == run.workspace_id
    assert "Bearer " not in serialized_run_event(run)
~~~

Run: pytest tests/apps/cosa/compliance/test_run_delegation.py -q
Expected: FAIL because worker uses delegation for policy snapshot only and omits it from RunRequest/context.

- [x] **Step 2: Mint after run ID and resolved spec are known**

At scheduling, resolve AgentSpec capability IDs and mint delegation bound to generated run_id. Worker rejects a task that lacks or cannot verify delegation; it cannot fall back to scheduled_worker_service_token for Company calls.

- [x] **Step 3: Resolve compliance before kernel execution**

After policy snapshot and before plane.kernel.run, call ComplianceResolver.resolve_for_run with delegation. Merge immutable snapshot metadata into RunRequest and emit only a reason code if it fails.

- [x] **Step 4: Forward headers only from InvocationContext**

~~~
headers = {
  "Authorization": f"Bearer {delegation_token}",
  "X-Workspace-Id": invocation.workspace_id,
  "X-COSA-Run-Id": invocation.run_id,
  "X-COSA-Capability-Id": capability_id,
}
~~~

Company capability handlers build these values from InvocationContext, never tool arguments. OpenAI kernel propagates delegation_identity, compliance_snapshot_ref and policy snapshot reference into every InvocationContext.

- [x] **Step 5: Run dedicated suites**

Run: pytest tests/apps/cosa/compliance/test_run_delegation.py tests/apps/cosa/compliance/test_company_client.py tests/e2e/test_ai_compliance_flow.py -q
Expected: PASS; expired/missing delegation makes zero Company requests and zero model calls.

- [x] **Step 6: Commit**

~~~
git add apps/cosa packages/agent packages/agent_integrations tests/apps/cosa tests/e2e
git commit -m "feat: propagate compliance delegation through agent runs"
~~~

### Task 6: Correct legal source data and make evidence decision-grade

**Files:**
- Create: services/company/finance-legal/migrations/30_ai_legal_source_corrections.up.sql
- Create: services/company/finance-legal/migrations/30_ai_legal_source_corrections.down.sql
- Modify: services/company/finance-legal/services/ai-legal-applicability.service.ts
- Modify: services/company/shared/db/schema/legal.ts
- Create: services/company/finance-legal/tests/ai-legal-provenance.test.ts
- Create: docs/legal/ai-regulatory-source-register.md

**Interfaces:**
- Executable rule exposes ruleId, ruleVersion, sourceVersionId, sourceContentHash, effectiveFrom, effectiveTo, reviewStatus and predicate.
- Evidence exposes evidenceId, contentHash, evidenceType, reviewerMemberId, reviewedAt, conclusion and sourceVersionIds; it never stores evidence body.

- [x] **Step 1: Create authoritative source register and failing provenance test**

Record official URL, publication/effective dates, downloaded artifact location, SHA-256, reviewer, verification date and legal layer. Mark current unverified/incorrect seed records non-executable. Include corrections for Law 134/2025/QH15, Decree 142/2026/NĐ-CP, Decision 33/2026/QĐ-TTg, Circular 05/2026/TT-BKHCN and wrongly described Decision 804/QĐ-TTg.

~~~
it("does not emit a CURRENT_LAW control from an unverified source version", async () => {
  await expect(assessAiApplicability(unverifiedDeployment)).resolves.toEqual(
    expect.not.objectContaining({ blockingRule: expect.anything() }),
  );
});
~~~

- [x] **Step 2: Add migration 30 without editing seed 28**

Insert corrected metadata only after named legal reviewer provides exact source artifact and hash. Set superseded/incorrect version records inactive with a correction reason; retain audit history. Add normalized source-version relations to evidence/rules and fields needed for conclusion/pinpoint.

- [x] **Step 3: Replace static legal conclusion path**

assessAiApplicability may use static code only to evaluate typed predicates from published database rules. It returns PROFESSIONAL_REVIEW_REQUIRED when no reviewed active rule applies; it never labels an unverified keyword hit CURRENT_LAW or PROHIBITED.

- [x] **Step 4: Tie runtime snapshot to legal provenance**

Resolver selects active applicable rule/source version IDs and hashes, includes them in canonical snapshot, and rejects a deployment whose mandatory active rule lacks reviewed evidence.

- [x] **Step 5: Verify date boundaries and tamper detection**

Run: cd services/company && pnpm vitest run finance-legal/tests/ai-legal-provenance.test.ts finance-legal/tests/ai-compliance-runtime-snapshot.test.ts
Expected: PASS; a rule is inactive before effective date, inactive after supersession, and changing a source/evidence hash changes snapshot hash.

- [x] **Step 6: Commit**

~~~
git add services/company/finance-legal/migrations/30_ai_legal_source_corrections.* services/company/finance-legal/services/ai-legal-applicability.service.ts services/company/shared/db/schema/legal.ts services/company/finance-legal/tests/ai-legal-provenance.test.ts docs/legal/ai-regulatory-source-register.md
git commit -m "feat: ground AI compliance rules in verified legal sources"
~~~

### Task 7: Enforce DataAccessClaim before model egress

**Files:**
- Create: apps/cosa/compliance/data_access_claim.py
- Create: tests/apps/cosa/compliance/test_data_model_gate.py
- Modify: apps/cosa/compliance/data_model_gate.py
- Modify: apps/cosa/compliance/company_client.py
- Modify: services/company/finance-legal/services/ai-data-governance.service.ts
- Modify: services/company/finance-legal/handlers/ai-data-governance.handler.ts
- Modify: services/company/finance-legal/tests/ai-data-governance.test.ts

**Interfaces:**

~~~
class DataAccessClaim(BaseModel):
    workspace_id: str
    deployment_id: str
    capability_id: str
    source_ref: str
    source_hash: str
    categories: frozenset[str]
    purpose_id: str
    subject_reference: str | None
    provider_key: str
    model_key: str
    retention_policy_id: str | None
~~~

- [x] **Step 1: Write failure tests for implicit classification and model mismatch**

~~~
async def test_gate_denies_personal_data_without_subject_reference():
    with pytest.raises(ComplianceDenied, match="PROCESSING_AUTHORIZATION_MISSING"):
        await gate.prepare_initial_input(context_with(personal_claim(None)), "input")

async def test_gate_denies_provider_profile_that_excludes_requested_model():
    with pytest.raises(ComplianceDenied, match="MODEL_NOT_APPROVED"):
        await gate.prepare_initial_input(context_with(confidential_claim("other-model")), "input")
~~~

- [x] **Step 2: Build claim at retrieval/capability boundary**

A document retrieval capability attaches classified source reference/hash/categories. Unclassified source is denied from model egress. Raw subject reference is transient only for authorization lookup; it is absent from run metadata/events.

- [x] **Step 3: Enforce relational checks in resolveDataUse**

Require deployment workspace match, exact provider and model, provider profile ID equal to data profile recipient, requested categories subset of both provider and data profile categories, active authorization for personal/sensitive categories, and a bound capability ID.

- [x] **Step 4: Remove hard-coded categories from DataModelGate**

Gate sends only claim fields needed by Company API, receives typed allow/deny, applies deterministic minimization and records only decision IDs/hashes. Redactor remains a final defensive transform, not an allow condition.

- [x] **Step 5: Run both language suites**

Run: pytest tests/apps/cosa/compliance/test_data_model_gate.py -q && cd services/company && pnpm vitest run finance-legal/tests/ai-data-governance.test.ts
Expected: PASS; missing claim, withdrawn authorization, category mismatch, provider/model mismatch and unbound capability make zero provider network calls.

- [x] **Step 6: Commit**

~~~
git add apps/cosa/compliance services/company/finance-legal tests/apps/cosa/compliance
git commit -m "feat: enforce source-grounded data access for model calls"
~~~

### Task 8: Align Compliance Center with public Company API

**Files:**
- Modify: frontend/lib/modules/legal/services/ai_compliance_service.dart
- Modify: frontend/lib/data/models/ai_compliance_models.dart
- Modify: frontend/lib/modules/legal/controllers/ai_compliance_controller.dart
- Modify: frontend/lib/modules/legal/views/widgets/compliance_center_panel.dart
- Create: frontend/test/modules/legal/ai_compliance_service_test.dart
- Create: frontend/test/data/models/ai_compliance_models_test.dart
- Modify: services/company/finance-legal/handlers/ai-compliance-governance.handler.ts
- Modify: services/company/finance-legal/handlers/ai-incident-response.handler.ts

**Interfaces:**
- Flutter routes: /finance-legal/ai-compliance/deployments/:id/{approve,suspend,resume} and /finance-legal/ai-compliance/incidents.
- Approve body has assessmentId, rationale, expiresAt. Incident body has incidentType as well as deployment/severity/summary.
- Center model maps server incidents directly; activeCount and incidentCount are derived from canonical arrays.

- [x] **Step 1: Write mock HTTP contract tests**

~~~
test("approve uses the ai-compliance route and required body", () async {
  await service.approveDeployment("dep-1",
    assessmentId: "ass-1", rationale: "reviewed", expiresAt: expiry);
  expect(client.lastPath, "/finance-legal/ai-compliance/deployments/dep-1/approve");
  expect(client.lastBody["assessmentId"], "ass-1");
});
~~~

Run: cd frontend && flutter test test/modules/legal/ai_compliance_service_test.dart
Expected: FAIL because current routes omit ai-compliance and approval inputs.

- [x] **Step 2: Match client/model/UI to the contract**

Use existing WorkspaceService header behavior and assert X-Workspace-Id in test. Do not append workspace_id query text as a replacement header. Approve only when a current pending assessment and expiry are available. Render server rejection reason instead of optimistic success.

- [x] **Step 3: Return canonical Center DTO**

Expose ComplianceCenterView matching UI needs or create versioned DTO adapter in Company handler. Flutter must not invent owner/profile/assessment data absent from response.

- [x] **Step 4: Run Flutter and Company tests**

Run: cd frontend && flutter test test/modules/legal/ai_compliance_service_test.dart test/data/models/ai_compliance_models_test.dart && cd ../services/company && pnpm vitest run finance-legal/tests/ai-compliance-governance.test.ts
Expected: PASS; incidents render, controls call valid routes and required data is sent.

- [x] **Step 5: Commit**

~~~
git add frontend/lib frontend/test services/company/finance-legal/handlers
git commit -m "fix: align AI compliance center with Company API contract"
~~~

### Task 9: Make audit/replay evidence complete without leaking content

**Files:**
- Modify: services/company/finance-legal/services/ai-compliance-snapshot.service.ts
- Modify: packages/agent/runs/models.py
- Modify: packages/agent/capabilities/gateway.py
- Modify: apps/cosa/observability/logging.py
- Create: tests/agent/capabilities/test_gateway_compliance_audit.py
- Create: tests/apps/cosa/compliance/test_log_redaction_contract.py

**Interfaces:**
- Decision event contains run_id, workspace_id, deployment_id, snapshot_hash, policy_snapshot_hash, capability_id, tool_call_id, checkpoint_ref, decision, reason_code, rule_version_ids, evidence_hashes, provider_model_ref, delegation_jti and timestamp.
- It never contains Authorization, company_delegation, prompt, completion, raw subject reference, document content or unredacted model payload.

- [x] **Step 1: Write audit completeness and secrecy tests**

~~~
assert event.payload["snapshot_hash"] == approved_snapshot.snapshot_hash
assert event.payload["evidence_hashes"] == ["sha256:evidence-a"]
assert "Bearer " not in json.dumps(event.model_dump())
assert "customer@example.com" not in json.dumps(event.model_dump())
~~~

- [x] **Step 2: Add dedicated compliance decision payload**

Extend existing run/tool event payloads and CapabilityGateway structured event creation; do not create a second event store. Logging uses allowlist serialization so unknown metadata keys, including delegation tokens, are excluded by default.

- [x] **Step 3: Preserve correct resume behavior**

On resume, load persisted snapshot reference and re-resolve current suspension/emergency state. Historical snapshot supports explanation/replay only; it never overrides a present suspension, expired input or changed mandatory rule.

- [x] **Step 4: Run audit and gateway tests**

Run: pytest tests/agent/capabilities/test_gateway_compliance_audit.py tests/agent/capabilities/test_gateway.py tests/apps/cosa/compliance/test_log_redaction_contract.py -q
Expected: PASS; audit reconstruction works from IDs/hashes and logs/events retain no sensitive payload or secret.

- [x] **Step 5: Commit**

~~~
git add packages/agent apps/cosa/observability services/company/finance-legal tests/agent tests/apps/cosa
git commit -m "feat: record replayable AI compliance decisions safely"
~~~

### Task 10: Verify real HTTP path and gate release

**Files:**
- Create: tests/e2e/test_ai_compliance_company_http.py
- Create: services/company/finance-legal/tests/ai-compliance-private-contract.test.ts
- Modify: .github/workflows/quality.yml
- Modify: Makefile
- Modify: docs/architecture/specs/README.md

**Interfaces:**
- E2E starts or targets a real Company HTTP service/test container and private runtime endpoint; it does not substitute fake snapshot client.
- make ai-compliance-production-gate is the one local CI command for this path.

- [ ] **Step 1: Write production-path acceptance test**

~~~
async def test_approved_run_reaches_company_then_model_once():
    result = await submit_real_run(approved_workspace,
      capability_ids=["operations.task.list"])
    assert result.status == RunStatus.COMPLETED
    assert company_observer.snapshot_requests == 1
    assert fake_model.call_count == 1

async def test_suspended_or_cross_workspace_run_never_reaches_model():
    result = await submit_real_run(suspended_or_foreign_workspace)
    assert result.status == RunStatus.FAILED
    assert fake_model.call_count == 0
~~~

- [ ] **Step 2: Cover negative matrix using real HTTP**

Add missing/expired/wrong-audience delegation; missing approved deployment; empty/unbound capability set; stale assessment/evidence/provider/data profile; withdrawn authorization; model mismatch; cross-workspace resource ID; UI request contract mismatch.

- [ ] **Step 3: Add deterministic local gate**

~~~
ai-compliance-production-gate:
	cd services/company && pnpm vitest run finance-legal/tests/ai-compliance-*.test.ts
	pytest tests/apps/cosa/compliance tests/e2e/test_ai_compliance_company_http.py -q
	cd frontend && flutter test test/modules/legal/ai_compliance_service_test.dart test/data/models/ai_compliance_models_test.dart
~~~

Use repository bootstrap conventions; never embed credentials in Makefile/workflow.

- [ ] **Step 4: Wire gate to CI after local reproducibility**

Add the Make target as a quality.yml job. Preserve existing tenancy, TypeScript, Python and Flutter jobs; this is an added cross-plane gate, not a replacement.

- [ ] **Step 5: Run release verification**

Run: make ai-compliance-production-gate
Expected: PASS. Then run the repository’s existing broader quality command. Record actual command output and migration versions in the release description; do not claim production readiness without these results.

- [ ] **Step 6: Commit**

~~~
git add tests/e2e services/company/finance-legal/tests .github/workflows/quality.yml Makefile docs/architecture/specs/README.md
git commit -m "test: gate AI compliance production path in CI"
~~~

## Release Criteria

- Every ID-based Company read/mutation is scoped by verified workspace, with hostile cross-workspace tests passing.
- Runtime accepts only bounded Company delegation and never sends raw user bearer token through durable task/event/audit path.
- No runtime operation auto-creates deployment, assessment, provider profile or evidence.
- Valid snapshot has declared bindings, evidence/source provenance, hash validity and expiry derived from inputs.
- No model or Company capability call occurs when approval, delegation, data authorization or legal source evidence is absent, invalid or expired.
- Compliance Center reads, approves, suspends, resumes and reports incidents through real public routes with required fields.
- Real HTTP integration test and make ai-compliance-production-gate pass in CI.

## Explicitly Deferred

- Matter-level isolation and legal-office multi-client workflows.
- Connector-specific document access UI and external SaaS connectors.
- Automated legal notification or autonomous legal decisions.
- Regulatory monitoring until verified source/rule lifecycle has one production release.
- Tenant-configurable relaxation of statutory floors.

## Plan Self-Review

- **Coverage:** Tasks 1–2 close resource tenancy; Tasks 3–5 close delegation and runtime integration; Task 6 grounds legal evidence; Task 7 controls data egress; Task 8 repairs user controls; Task 9 makes audit replayable; Task 10 verifies the production path and CI.
- **Consistency:** The same workspace/run/capability scope appears in delegation, snapshot resolution, invocation, Company capability calls and tests. Runtime snapshot creation is explicitly non-mutating.
- **Scope:** No task introduces a second compliance database, an autonomous legal subsystem, matter architecture or connector product.
- **Ambiguity resolved:** Missing relationship or unreviewed legal source means denial/review, never default allow. Past snapshot is evidence, never authority to bypass current suspension.
