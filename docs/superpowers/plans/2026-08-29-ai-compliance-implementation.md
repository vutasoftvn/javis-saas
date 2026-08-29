# AI Compliance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Build an AI-governance, personal-data and runtime-control layer so COSA operates only approved private-business advisory deployments.

**Architecture:** Company service owns legal sources, deployments, assessments, data profiles, incidents and signed compliance snapshots in the legal schema. COSA resolves that snapshot at run and resume boundaries, applies statutory controls before workspace policy, then gates model and capability use. Generic Agent packages receive neutral protocols only and never import apps or services.

**Tech Stack:** PostgreSQL, Drizzle, Encore, TypeScript, Vitest, Python 3.11, Pydantic, httpx, pytest, OpenAI Agents SDK adapter, Flutter, GetX.

**Spec:** docs/superpowers/specs/2026-08-29-ai-compliance-design.md

## Global Constraints

- COSA serves private businesses only and every deployment has mode ADVISORY_ONLY.
- Finance, legal, HR and operations output is advisory or draft content; an authorized human confirms external consequences.
- No automated credit, hiring, health, education, biometric, benefit-eligibility or other high-impact personal decision is allowed.
- Company service is business source of truth. Apps COSA never writes the workspace database directly.
- CURRENT_LAW may block, POLICY_WATCH only alerts, and PROFESSIONAL_REVIEW requires human review.
- Missing, expired, suspended or unverifiable compliance state fails closed.
- A workspace policy can be stricter than statutory controls but can never relax them.
- No audit/log/event payload contains raw prompts, model completions, source documents, evidence content or sensitive values.
- Provider secrets remain in environment or a secret manager, never in the legal schema.
- Begin every production behavior change with a focused failing test; commit only after that task test passes.
- Keep packages/agent independent of apps and services.

## File Structure

| Unit | Files | Responsibility |
| --- | --- | --- |
| Persistence | services/company/shared/db/schema/legal.ts; finance-legal migrations 27 and 28 | Governance records, states, indexes and legal-source seed. |
| Company domain | finance-legal/services/ai-*.service.ts and handlers/ai-*.handler.ts | Lifecycle, data-use decision, snapshot, incidents and workspace summary. |
| COSA compliance | apps/cosa/compliance/ | Typed snapshot client, resolver, floor, redaction, model gate, audit and retention coordination. |
| Agent boundary | packages/agent_integrations/openai_agents_sdk/model_guard.py and kernel.py | Generic callbacks before model input, model call and tool-result return. |
| User experience | frontend/lib/modules/legal and frontend/lib/modules/chat | Compliance Center, advisory disclosure, data warning and reporting. |
| Operations | docs/operations/ai-compliance.md; docs/runbooks/ai-compliance-incident.md | Release, suspension, incident and data-rights procedure. |

---

### Task 1: Add the governance schema and source seed

**Files:**
- Create: services/company/finance-legal/migrations/27_ai_compliance_governance.up.sql
- Create: services/company/finance-legal/migrations/27_ai_compliance_governance.down.sql
- Create: services/company/finance-legal/migrations/28_ai_compliance_legal_sources.up.sql
- Create: services/company/finance-legal/migrations/28_ai_compliance_legal_sources.down.sql
- Modify: services/company/shared/db/schema/legal.ts
- Modify: services/company/shared/db/schema/index.ts
- Create: services/company/finance-legal/tests/ai-compliance-schema.test.ts

**Interfaces:**
- Creates ai_system_catalog, ai_system_versions, workspace_ai_deployments, ai_system_capability_bindings, ai_risk_assessments, ai_compliance_evidence, ai_provider_profiles, ai_data_processing_profiles, data_processing_authorizations, data_subject_requests, ai_incidents, ai_incident_actions and ai_compliance_snapshots.
- Deployment states are DRAFT, ASSESSED, APPROVED_FOR_USE, SUSPENDED, REJECTED and RETIRED.
- Every workspace-owned table has workspace_id and a workspace-leading index.

- [x] **Step 1: Write failing database-invariant tests.**

    it("does not accept a non-advisory deployment", async () => {
      await expect(
        db.execute("INSERT INTO legal.workspace_ai_deployments (id, workspace_id, system_version_id, mode, status, founder_member_id) VALUES (1, 1, 1, 'AUTONOMOUS', 'DRAFT', 1)")
      ).rejects.toThrow();
    });

    it("creates official AI and data-protection sources at the intended layers", async () => {
      const sources = await listRegulationSources();
      expect(sources.find((x) => x.number === "134/2025/QH15")?.layer).toBe("CURRENT_LAW");
      expect(sources.find((x) => x.number === "804/QĐ-TTg")?.layer).toBe("POLICY_WATCH");
    });

- [x] **Step 2: Run the test and confirm it fails because the tables and seed rows do not exist.**

Run: cd services/company && npx vitest run finance-legal/tests/ai-compliance-schema.test.ts

Expected: relation/table error or missing source assertion.

- [x] **Step 3: Implement migration 27 with explicit constraints, keys and indexes.**

    CREATE TABLE legal.workspace_ai_deployments (
      id BIGINT PRIMARY KEY,
      workspace_id BIGINT NOT NULL,
      system_version_id BIGINT NOT NULL REFERENCES legal.ai_system_versions(id),
      mode TEXT NOT NULL CHECK (mode = 'ADVISORY_ONLY'),
      status TEXT NOT NULL CHECK (status IN ('DRAFT','ASSESSED','APPROVED_FOR_USE','SUSPENDED','REJECTED','RETIRED')),
      founder_member_id BIGINT NOT NULL,
      technical_owner_member_id BIGINT,
      current_assessment_id BIGINT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE INDEX workspace_ai_deployments_workspace_status_idx
      ON legal.workspace_ai_deployments (workspace_id, status);

Add equivalent foreign-key, check and tenant-leading-index protections to every listed table. Down migration drops dependent tables in reverse order.

- [x] **Step 4: Implement migration 28 and Drizzle table mappings.**

Seed the five mandatory sources and their official URLs from the spec at CURRENT_LAW. Seed Decisions 804, 367, 1528 and Resolution 86 only at POLICY_WATCH. Add tables to legal.ts using the existing bigint mode, timestamp convention and explicit field names.

    export const workspaceAiDeployments = legalSchema.table("workspace_ai_deployments", {
      id: bigint("id", { mode: "bigint" }).primaryKey(),
      workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
      systemVersionId: bigint("system_version_id", { mode: "bigint" }).notNull(),
      mode: text("mode").notNull(),
      status: text("status").notNull(),
      founderMemberId: bigint("founder_member_id", { mode: "bigint" }).notNull(),
      technicalOwnerMemberId: bigint("technical_owner_member_id", { mode: "bigint" }),
      currentAssessmentId: bigint("current_assessment_id", { mode: "bigint" }),
      createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
      updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
    });

- [x] **Step 5: Apply migrations, rerun the test and commit.**

Run: cd services/company && WORKSPACE_DATABASE_URL="$WORKSPACE_DATABASE_URL" node scripts/migrate.mjs

Run: cd services/company && npx vitest run finance-legal/tests/ai-compliance-schema.test.ts

Expected: PASS.

    git add services/company/finance-legal/migrations/27_ai_compliance_governance.* services/company/finance-legal/migrations/28_ai_compliance_legal_sources.* services/company/shared/db/schema/legal.ts services/company/shared/db/schema/index.ts services/company/finance-legal/tests/ai-compliance-schema.test.ts
    git commit -m "feat: add AI compliance governance schema"

### Task 2: Implement typed legal applicability for AI deployments

**Files:**
- Create: services/company/finance-legal/services/ai-legal-applicability.service.ts
- Modify: services/company/finance-legal/services/legal-applicability.service.ts
- Modify: services/company/finance-legal/services/index.ts
- Create: services/company/finance-legal/tests/ai-legal-applicability.test.ts

**Interfaces:**
- Produces AiApplicabilityInput, AiApplicabilityResult and assessAiApplicability(input).
- Input includes workspaceId, deploymentMode, intendedPurpose, decisionDomain, capabilityEffectClass, dataCategories, providerProfileStatus and lastAssessmentAt.
- Result includes currentLawBlocks, professionalReviewRequired, policyWatchItems, matchedRuleIds and recheckRequired.

- [x] **Step 1: Write failing rule examples.**

    it("blocks a prohibited automated hiring purpose even when a tenant wants ALLOW", async () => {
      const result = await assessAiApplicability({
        workspaceId,
        deploymentMode: "ADVISORY_ONLY",
        intendedPurpose: "candidate ranking",
        decisionDomain: "HR",
        capabilityEffectClass: "EXTERNAL",
        dataCategories: ["PERSONAL"],
        providerProfileStatus: "APPROVED",
        lastAssessmentAt: "2026-08-29T00:00:00Z",
      });
      expect(result.currentLawBlocks).toContain("PROHIBITED_DECISION_DOMAIN");
    });

    it("returns policy-watch information without a blocking result", async () => {
      const result = await assessAiApplicability(privateBusinessAdvisoryInput);
      expect(result.currentLawBlocks).toEqual([]);
      expect(result.policyWatchItems.length).toBeGreaterThan(0);
    });

- [x] **Step 2: Run the test and confirm the evaluator export is absent.**

Run: cd services/company && npx vitest run finance-legal/tests/ai-legal-applicability.test.ts

Expected: FAIL with missing module or export.

- [x] **Step 3: Add the pure predicate evaluator.**

    export function evaluateAiRule(
      rule: AiApplicabilityRule,
      input: AiApplicabilityInput,
    ): "BLOCK" | "REVIEW" | "NOTICE" | "NO_MATCH" {
      if (!matchesPredicate(rule.predicate, input)) return "NO_MATCH";
      if (rule.layer === "CURRENT_LAW" && rule.effect === "BLOCK") return "BLOCK";
      if (rule.layer === "PROFESSIONAL_REVIEW") return "REVIEW";
      return "NOTICE";
    }

Rules match typed fields only. Do not derive legal obligation from a natural-language prompt or model response.

- [x] **Step 4: Extend the existing legal applicability service without changing entity-status results.**

Add assessWorkspaceAiApplicability(workspaceId, input). It resolves active regulation versions, evaluates AI-specific rules and maps result into the read model. Existing assessApplicableObligations remains unchanged for the finance/legal obligation screens.

- [x] **Step 5: Verify and commit.**

Run: cd services/company && npx vitest run finance-legal/tests/ai-legal-applicability.test.ts finance-legal/tests/legal-applicability.test.ts

Expected: PASS.

    git add services/company/finance-legal/services/ai-legal-applicability.service.ts services/company/finance-legal/services/legal-applicability.service.ts services/company/finance-legal/services/index.ts services/company/finance-legal/tests/ai-legal-applicability.test.ts
    git commit -m "feat: add AI legal applicability controls"

### Task 3: Build deployment, assessment and evidence lifecycle services

**Files:**
- Create: services/company/finance-legal/services/ai-compliance-governance.service.ts
- Create: services/company/finance-legal/handlers/ai-compliance-governance.handler.ts
- Modify: services/company/finance-legal/handlers/index.ts
- Modify: services/company/finance-legal/api.ts
- Create: services/company/finance-legal/tests/ai-compliance-governance.test.ts
- Modify: services/company/finance-legal/tests/tenant-isolation.test.ts

**Interfaces:**
- Produces createAiDeployment, submitAiAssessment, approveAiAssessment, suspendAiDeployment, resumeAiDeployment and getComplianceCenterView.
- Approval input is deploymentId, assessmentId, approvedByMemberId, rationale and expiresAt.
- Center view is workspace-scoped metadata and has no raw evidence or subject data.

- [x] **Step 1: Write failing lifecycle and isolation tests.**

    it("requires Founder approval of the exact assessment before activation", async () => {
      const deployment = await createAiDeployment(draftInput);
      const assessment = await submitAiAssessment({
        deploymentId: deployment.id,
        classification: "OUT_OF_CATALOG",
        intendedPurpose: "private-business advisory",
        controls: ["HUMAN_CONFIRMATION", "DATA_GATE"],
      });
      await expect(approveAiAssessment({
        deploymentId: deployment.id,
        assessmentId: assessment.id,
        approvedByMemberId: technicalOwnerId,
        rationale: "ship",
        expiresAt: "2027-01-01T00:00:00Z",
      })).rejects.toMatchObject({ code: "FOUNDER_APPROVAL_REQUIRED" });
    });

    it("returns no deployment from another workspace", async () => {
      await expect(getComplianceCenterView(otherWorkspaceId)).resolves.toMatchObject({ deployments: [] });
    });

- [x] **Step 2: Run the test and confirm lifecycle services are absent.**

Run: cd services/company && npx vitest run finance-legal/tests/ai-compliance-governance.test.ts

Expected: FAIL with missing module or export.

- [x] **Step 3: Implement one transition map and all activation preconditions.**

    const transitions: Record<DeploymentStatus, readonly DeploymentStatus[]> = {
      DRAFT: ["ASSESSED", "REJECTED"],
      ASSESSED: ["APPROVED_FOR_USE", "REJECTED", "SUSPENDED"],
      APPROVED_FOR_USE: ["SUSPENDED", "RETIRED"],
      SUSPENDED: ["APPROVED_FOR_USE", "RETIRED"],
      REJECTED: [],
      RETIRED: [],
    };

    function assertTransition(from: DeploymentStatus, to: DeploymentStatus): void {
      if (!transitions[from].includes(to)) {
        throw APIError.invalidArgument("Invalid AI deployment transition");
      }
    }

Activation verifies assessment ownership, no current-law block, required evidence, active provider/data profile, Founder identity and non-expired approval.

- [x] **Step 4: Add authorized handlers.**

Expose workspace-scoped reads for Compliance Center. Mutation handlers reject a caller who is neither the Founder nor a permitted reviewer. Add one non-exposed snapshot route only in Task 5.

- [x] **Step 5: Verify and commit.**

Run: cd services/company && npx vitest run finance-legal/tests/ai-compliance-governance.test.ts finance-legal/tests/tenant-isolation.test.ts

Run: cd services/company && npm run typecheck

Expected: PASS.

    git add services/company/finance-legal/services/ai-compliance-governance.service.ts services/company/finance-legal/handlers/ai-compliance-governance.handler.ts services/company/finance-legal/handlers/index.ts services/company/finance-legal/api.ts services/company/finance-legal/tests/ai-compliance-governance.test.ts services/company/finance-legal/tests/tenant-isolation.test.ts
    git commit -m "feat: add AI deployment compliance lifecycle"

### Task 4: Add provider, purpose, authorization and data-subject workflows

**Files:**
- Create: services/company/finance-legal/services/ai-data-governance.service.ts
- Create: services/company/finance-legal/handlers/ai-data-governance.handler.ts
- Modify: services/company/finance-legal/handlers/index.ts
- Modify: services/company/finance-legal/api.ts
- Create: services/company/finance-legal/tests/ai-data-governance.test.ts

**Interfaces:**
- Produces upsertProviderProfile, upsertDataProcessingProfile, grantProcessingAuthorization, withdrawProcessingAuthorization, createDataSubjectRequest and resolveDataUse.
- resolveDataUse input has workspaceId, deploymentId, capabilityId, purposeId, dataCategories, providerKey and subjectReference.
- resolveDataUse output has allowed, denialCode, providerProfileVersion, dataProfileVersion, retentionPolicyId and minimizationRequired.

- [x] **Step 1: Write failing withdrawal and minimization tests.**

    it("denies a provider call after authorization is withdrawn", async () => {
      await grantProcessingAuthorization(activeAuthorization);
      await withdrawProcessingAuthorization(activeAuthorization.id, founderId);
      await expect(resolveDataUse(activeDataUse)).resolves.toMatchObject({
        allowed: false,
        denialCode: "PROCESSING_AUTHORIZATION_WITHDRAWN",
      });
    });

    it("stores only a hash for subject reference", async () => {
      const row = await grantProcessingAuthorization({
        ...activeAuthorization,
        subjectReference: "contact_123",
        proofReference: "vault://proof/abc",
      });
      expect(row.subjectReferenceHash).not.toEqual("contact_123");
      expect(JSON.stringify(row)).not.toContain("Nguyen Van A");
    });

- [x] **Step 2: Run the test and confirm the service is missing.**

Run: cd services/company && npx vitest run finance-legal/tests/ai-data-governance.test.ts

Expected: FAIL with missing module or export.

- [x] **Step 3: Implement one data-use decision function.**

    export async function resolveDataUse(input: ResolveDataUseInput): Promise<DataUseDecision> {
      const provider = await requireApprovedProvider(input.providerKey, input.dataCategories);
      const profile = await requireActiveProcessingProfile(input);
      const authorization = await requireActiveAuthorization(input);
      return {
        allowed: true,
        denialCode: null,
        providerProfileVersion: provider.version,
        dataProfileVersion: profile.version,
        retentionPolicyId: profile.retentionPolicyId,
        minimizationRequired: profile.minimizationRequired,
      };
    }

Missing, expired, restricted or withdrawn state returns allowed false with a stable denialCode. It does not leak raw database errors or input values.

- [x] **Step 4: Add Founder-managed profile endpoints and request intake.**

Create typed POST/PATCH handlers for provider, processing profile and authorization. Create GET/POST handlers for data-subject requests. A deletion request records a request; it never deletes data immediately or bypasses legal hold.

- [x] **Step 5: Verify and commit.**

Run: cd services/company && npx vitest run finance-legal/tests/ai-data-governance.test.ts finance-legal/tests

Expected: PASS.

    git add services/company/finance-legal/services/ai-data-governance.service.ts services/company/finance-legal/handlers/ai-data-governance.handler.ts services/company/finance-legal/handlers/index.ts services/company/finance-legal/api.ts services/company/finance-legal/tests/ai-data-governance.test.ts
    git commit -m "feat: add AI data governance workflows"

### Task 5: Create snapshots and incident controls

**Files:**
- Create: services/company/finance-legal/services/ai-compliance-snapshot.service.ts
- Create: services/company/finance-legal/services/ai-incident.service.ts
- Create: services/company/finance-legal/handlers/ai-compliance-snapshot.handler.ts
- Create: services/company/finance-legal/handlers/ai-incident.handler.ts
- Modify: services/company/finance-legal/handlers/index.ts
- Modify: services/company/finance-legal/api.ts
- Create: services/company/finance-legal/tests/ai-compliance-snapshot.test.ts
- Create: services/company/finance-legal/tests/ai-incident.test.ts

**Interfaces:**
- ComplianceSnapshotView contains workspaceId, deploymentId, assessmentId, mode, status, allowedCapabilities, providerProfileVersion, dataProfileVersion, legalVersionIds, policySnapshotHash, issuedAt, expiresAt and snapshotHash.
- Snapshot failure uses NOT_READY, SUSPENDED, EXPIRED or ASSESSMENT_REQUIRED; no empty permissive response exists.
- Incident states are OPEN, CONTAINED, ASSESSING, NOTIFICATION_DECISION_PENDING, REMEDIATING and CLOSED.

- [x] **Step 1: Write failing snapshot and critical-incident tests.**

    it("creates a stable snapshot without raw evidence or subject data", async () => {
      const snapshot = await resolveComplianceSnapshot(validSnapshotRequest);
      expect(snapshot.snapshotHash).toMatch(/^[a-f0-9]{64}$/);
      expect(JSON.stringify(snapshot)).not.toContain("contract_text");
    });

    it("suspends a deployment when a critical incident opens", async () => {
      await openAiIncident({
        deploymentId,
        severity: "CRITICAL",
        detectedAt: "2026-08-29T08:00:00Z",
        dataCategories: ["SENSITIVE_PERSONAL"],
      });
      await expect(getDeployment(deploymentId)).resolves.toMatchObject({ status: "SUSPENDED" });
    });

- [x] **Step 2: Run tests and confirm services are absent.**

Run: cd services/company && npx vitest run finance-legal/tests/ai-compliance-snapshot.test.ts finance-legal/tests/ai-incident.test.ts

Expected: FAIL with missing module or export.

- [x] **Step 3: Implement canonical snapshot assembly.**

    const body = {
      workspaceId: String(deployment.workspaceId),
      deploymentId: String(deployment.id),
      assessmentId: String(assessment.id),
      mode: deployment.mode,
      status: deployment.status,
      allowedCapabilities: bindings.map((x) => x.capabilityId).sort(),
      providerProfileVersion: provider.version,
      dataProfileVersion: dataProfile.version,
      legalVersionIds: legalVersions.map(String).sort(),
      policySnapshotHash: input.policySnapshotHash,
      issuedAt: now.toISOString(),
      expiresAt: expiresAt.toISOString(),
    };
    const snapshotHash = createHash("sha256").update(canonicalJson(body)).digest("hex");

Persist body/hash and immutable version references only. Do not persist evidence URI, authorization proof, prompt or incident narrative in a snapshot.

- [x] **Step 4: Implement incident transitions and endpoints.**

Open a CRITICAL incident and set the linked deployment SUSPENDED in one transaction. Public incident handlers can create, contain and record Founder notification decisions; they never send an external notice. The snapshot endpoint is non-exposed and service-authenticated.

- [x] **Step 5: Verify and commit.**

Run: cd services/company && npx vitest run finance-legal/tests/ai-compliance-snapshot.test.ts finance-legal/tests/ai-incident.test.ts

Expected: PASS.

    git add services/company/finance-legal/services/ai-compliance-snapshot.service.ts services/company/finance-legal/services/ai-incident.service.ts services/company/finance-legal/handlers/ai-compliance-snapshot.handler.ts services/company/finance-legal/handlers/ai-incident.handler.ts services/company/finance-legal/handlers/index.ts services/company/finance-legal/api.ts services/company/finance-legal/tests/ai-compliance-snapshot.test.ts services/company/finance-legal/tests/ai-incident.test.ts
    git commit -m "feat: add AI compliance snapshots and incidents"

### Task 6: Resolve compliance into every COSA run and resume

**Files:**
- Create: apps/cosa/compliance/__init__.py
- Create: apps/cosa/compliance/contracts.py
- Create: apps/cosa/compliance/company_client.py
- Create: apps/cosa/compliance/resolver.py
- Modify: apps/cosa/composition/agent_plane.py
- Modify: packages/agent_integrations/openai_agents_sdk/kernel.py
- Create: tests/apps/cosa/compliance/test_company_client.py
- Create: tests/apps/cosa/compliance/test_resolver.py

**Interfaces:**
- ComplianceSnapshot is a validated Pydantic representation of ComplianceSnapshotView.
- AiComplianceClient.resolve_snapshot(workspaceId, runId, systemKey, policySnapshotHash) returns ComplianceSnapshot or raises AiComplianceUnavailable.
- ComplianceResolver.resolve_for_run(request, spec) returns metadata with compliance_snapshot, compliance_snapshot_ref and compliance_snapshot_version.
- The SDK kernel resolves compliance before persisting a run and before a resume rebuilds context.

- [x] **Step 1: Write failing client and resolver tests.**

    @pytest.mark.asyncio
    async def test_resolver_fails_closed_when_snapshot_is_not_ready() -> None:
        resolver = ComplianceResolver(FakeAiComplianceClient(error=AiComplianceUnavailable("NOT_READY")))
        with pytest.raises(ComplianceDenied, match="NOT_READY"):
            await resolver.resolve_for_run(request, spec)

    @pytest.mark.asyncio
    async def test_resolver_attaches_snapshot_hash() -> None:
        metadata = await resolver.resolve_for_run(request, spec)
        assert metadata["compliance_snapshot_ref"] == "sha256:abc123"
        assert metadata["compliance_snapshot"]["mode"] == "ADVISORY_ONLY"

- [x] **Step 2: Run tests and confirm imports are absent.**

Run: PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/compliance/test_company_client.py tests/apps/cosa/compliance/test_resolver.py -q

Expected: FAIL with module not found.

- [x] **Step 3: Implement typed client, contract and resolver.**

    class ComplianceSnapshot(BaseModel):
        workspace_id: str
        deployment_id: str
        assessment_id: str
        mode: Literal["ADVISORY_ONLY"]
        status: Literal["APPROVED_FOR_USE"]
        allowed_capabilities: frozenset[str]
        provider_profile_version: str
        data_profile_version: str
        snapshot_hash: str
        expires_at: datetime

Use CompanyServiceClient-style httpx errors and internal service authentication. Invalid JSON, non-200, hash mismatch and expiry all become AiComplianceUnavailable.

- [x] **Step 4: Wire the resolver in the composition and kernel boundaries.**

Build one ComplianceResolver in build_cosa_agent_plane and pass it to RealOpenAIAgentsSDKKernel. In run and resume, merge its result only after success. Persist snapshot identifiers/hashes and sanitized input metadata, not an unbounded raw input structure.

- [x] **Step 5: Verify and commit.**

Run: PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/compliance/test_company_client.py tests/apps/cosa/compliance/test_resolver.py tests/apps/cosa/composition/test_agent_plane.py -q

Expected: PASS.

    git add apps/cosa/compliance apps/cosa/composition/agent_plane.py packages/agent_integrations/openai_agents_sdk/kernel.py tests/apps/cosa/compliance tests/apps/cosa/composition/test_agent_plane.py
    git commit -m "feat: resolve compliance snapshots for COSA runs"

### Task 7: Enforce statutory floor before workspace policy

**Files:**
- Create: apps/cosa/compliance/statutory_floor.py
- Modify: apps/cosa/policies/evaluator.py
- Modify: packages/agent_integrations/openai_agents_sdk/kernel.py
- Create: tests/apps/cosa/compliance/test_statutory_floor.py
- Modify: tests/apps/cosa/policy_test_helpers.py
- Modify: tests/apps/cosa/test_legal_capabilities.py

**Interfaces:**
- StatutoryFloor.evaluate(capabilityId, payload, snapshot) returns DENY or CONTINUE with a reason code.
- It denies missing binding, non-advisory mode, forbidden decision domain, suspended snapshot, unbound capability and EXTERNAL action without human confirmation.
- CosaPolicyEngine evaluates the floor before PolicySnapshot matching.
- The SDK kernel filters a capability before it is offered to a model and the gateway checks again before execution.

- [x] **Step 1: Write failing bypass tests.**

    def test_tenant_allow_cannot_bypass_forbidden_hr_decision() -> None:
        decision = CosaPolicyEngine().evaluate(
            "hr.candidate.rank",
            {},
            context={
                "policy_snapshot": allow_all_policy_snapshot(),
                "compliance_snapshot": compliance_snapshot(
                    allowed_capabilities={"hr.candidate.rank"},
                    prohibited_purpose=True,
                ),
            },
        )
        assert decision.outcome == PolicyOutcome.DENY
        assert decision.reasons == ("PROHIBITED_DECISION_DOMAIN",)

    @pytest.mark.asyncio
    async def test_unbound_capability_is_not_offered_to_sdk_model() -> None:
        model = FakeSDKModel(responses=[tool_call_response("call_1", "finance.transaction.record")])
        result = await kernel.run(request, spec_with_unbound_capability)
        assert result.status == RunStatus.FAILED
        assert model.call_count == 0

- [x] **Step 2: Run tests and confirm current tenant-first policy order fails.**

Run: PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/compliance/test_statutory_floor.py tests/apps/cosa/test_legal_capabilities.py -q

Expected: FAIL because tenant ALLOW is evaluated before the floor.

- [x] **Step 3: Implement the app-owned floor.**

    class StatutoryFloor:
        def evaluate(self, capability_id: str, payload: dict[str, Any], snapshot: ComplianceSnapshot | None) -> FloorDecision:
            if snapshot is None:
                return FloorDecision.deny("COMPLIANCE_SNAPSHOT_MISSING")
            if capability_id not in snapshot.allowed_capabilities:
                return FloorDecision.deny("CAPABILITY_NOT_BOUND")
            if snapshot.mode != "ADVISORY_ONLY":
                return FloorDecision.deny("NON_ADVISORY_MODE")
            if snapshot.binding(capability_id).prohibited_purpose:
                return FloorDecision.deny("PROHIBITED_DECISION_DOMAIN")
            if snapshot.binding(capability_id).effect_class == "EXTERNAL" and not snapshot.binding(capability_id).requires_human_confirmation:
                return FloorDecision.deny("EXTERNAL_ACTION_REQUIRES_HUMAN_CONFIRMATION")
            return FloorDecision.continue_()

- [x] **Step 4: Call the floor first and filter SDK tools.**

CosaPolicyEngine returns the deny immediately. RealOpenAIAgentsSDKKernel receives an optional capability_filter and excludes a disallowed capability in _build_tools. Gateway policy evaluation remains the second enforcement point.

- [x] **Step 5: Verify and commit.**

Run: PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/compliance/test_statutory_floor.py tests/apps/cosa/policies tests/apps/cosa/test_legal_capabilities.py -q

Expected: PASS.

    git add apps/cosa/compliance/statutory_floor.py apps/cosa/policies/evaluator.py packages/agent_integrations/openai_agents_sdk/kernel.py tests/apps/cosa/compliance/test_statutory_floor.py tests/apps/cosa/policy_test_helpers.py tests/apps/cosa/test_legal_capabilities.py
    git commit -m "feat: enforce AI statutory floor"

### Task 8: Gate model input and tool result data

**Files:**
- Create: packages/agent_integrations/openai_agents_sdk/model_guard.py
- Modify: packages/agent_integrations/openai_agents_sdk/kernel.py
- Create: apps/cosa/compliance/data_model_gate.py
- Create: apps/cosa/compliance/redaction.py
- Modify: apps/cosa/composition/model_provider.py
- Modify: apps/cosa/composition/agent_plane.py
- Create: tests/apps/cosa/compliance/test_data_model_gate.py
- Modify: packages/agent_testkit/kernel_conformance/test_openai_agents_sdk_kernel.py
- Modify: tests/apps/cosa/composition/test_model_provider.py

**Interfaces:**
- Generic ModelInputGuard defines async prepare_initial_input, prepare_tool_output and assert_before_model_call methods.
- CosaDataModelGate implements that protocol with the compliance snapshot plus the Company data-use endpoint.
- Denial prevents an underlying SDK model call. Redaction returns a sanitized value before any model call.

- [x] **Step 1: Write failing gate tests.**

    @pytest.mark.asyncio
    async def test_withdrawn_authorization_prevents_model_call() -> None:
        model = FakeSDKModel(responses=[text_response("unreachable")])
        kernel = RealOpenAIAgentsSDKKernel(
            model=model,
            model_input_guard=denying_guard("PROCESSING_AUTHORIZATION_WITHDRAWN"),
        )
        result = await kernel.run(request_with_personal_prompt, advisory_spec)
        assert result.status == RunStatus.FAILED
        assert model.call_count == 0

    @pytest.mark.asyncio
    async def test_email_is_redacted_before_provider_input() -> None:
        sanitized = await gate.prepare_initial_input(run_context, "Email: a@example.com")
        assert "a@example.com" not in sanitized
        assert "[EMAIL_REDACTED]" in sanitized

- [x] **Step 2: Run tests and confirm direct model invocation fails their assertions.**

Run: PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/compliance/test_data_model_gate.py packages/agent_testkit/kernel_conformance/test_openai_agents_sdk_kernel.py tests/apps/cosa/composition/test_model_provider.py -q

Expected: FAIL because ModelInputGuard and CosaDataModelGate are missing.

- [x] **Step 3: Add the neutral protocol and invoke it at every SDK boundary.**

    class ModelInputGuard(Protocol):
        async def prepare_initial_input(self, run_context: Mapping[str, Any], raw_input: str) -> str: ...
        async def prepare_tool_output(self, run_context: Mapping[str, Any], capability_id: str, output: Any) -> Any: ...
        async def assert_before_model_call(self, run_context: Mapping[str, Any]) -> None: ...

RealOpenAIAgentsSDKKernel calls prepare_initial_input before RunRecord creation and Runner.run. It calls prepare_tool_output immediately before returning tool output to the SDK. Extend the existing RunHooks implementation so on_llm_start first calls assert_before_model_call, then checks cancellation.

- [x] **Step 4: Implement CosaDataModelGate and approved provider selection.**

    async def prepare_initial_input(self, run_context: Mapping[str, Any], raw_input: str) -> str:
        decision = await self._client.resolve_data_use(
            workspace_id=run_context["workspace_id"],
            deployment_id=run_context["compliance_snapshot"]["deployment_id"],
            capability_id="model.input",
            purpose_id=run_context["purpose_id"],
            data_categories=self._classifier.categories_for_initial_input(run_context, raw_input),
            provider_key=run_context["provider_key"],
        )
        if not decision.allowed:
            raise ComplianceDenied(decision.denial_code)
        return self._redactor.minimize(raw_input, decision)

The DeepSeek API key remains in environment configuration. Its provider profile defaults to non-personal, non-sensitive and non-confidential content until a Founder-approved data profile permits a narrower, explicit exception.

- [x] **Step 5: Verify and commit.**

Run: PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/compliance/test_data_model_gate.py packages/agent_testkit/kernel_conformance/test_openai_agents_sdk_kernel.py tests/apps/cosa/composition/test_model_provider.py -q

Expected: PASS.

    git add packages/agent_integrations/openai_agents_sdk/model_guard.py packages/agent_integrations/openai_agents_sdk/kernel.py apps/cosa/compliance/data_model_gate.py apps/cosa/compliance/redaction.py apps/cosa/composition/model_provider.py apps/cosa/composition/agent_plane.py tests/apps/cosa/compliance/test_data_model_gate.py packages/agent_testkit/kernel_conformance/test_openai_agents_sdk_kernel.py tests/apps/cosa/composition/test_model_provider.py
    git commit -m "feat: guard AI model data processing"

### Task 9: Make logs, audit and retention governed-data safe

**Files:**
- Create: apps/cosa/compliance/audit_metadata.py
- Create: apps/cosa/compliance/retention_coordinator.py
- Modify: apps/cosa/observability/logging.py
- Modify: packages/agent_integrations/openai_agents_sdk/kernel.py
- Modify: packages/agent/kernel/openai_agents_kernel.py
- Modify: apps/cosa/knowledge_ingestion/publish.py
- Modify: apps/cosa/knowledge_ingestion/object_store.py
- Modify: packages/agent/memory/retention.py
- Create: tests/apps/cosa/compliance/test_audit_metadata.py
- Create: tests/apps/cosa/compliance/test_retention_coordinator.py
- Modify: tests/apps/cosa/observability/test_logging.py

**Interfaces:**
- safe_audit_metadata(eventType, runContext, decision) returns IDs, hashes, status, reasonCode and model/capability keys only.
- RetentionCoordinator.execute(subjectRequestId) returns PURGED, HELD or FAILED with a tombstone ref.
- Generic RetentionPolicy receives explicit refs and policy values; it imports no Company service.

- [x] **Step 1: Write failing leakage and lifecycle tests.**

    def test_safe_audit_metadata_excludes_prompt_and_result() -> None:
        event = safe_audit_metadata(
            "model.denied",
            {"run_id": "run_1", "prompt": "secret contract clause"},
            {"reason_code": "PROVIDER_NOT_APPROVED"},
        )
        assert "secret contract clause" not in json.dumps(event)
        assert event["reason_code"] == "PROVIDER_NOT_APPROVED"

    @pytest.mark.asyncio
    async def test_retention_purges_object_memory_and_index_without_hold() -> None:
        result = await coordinator.execute(delete_request_id)
        assert result.status == "PURGED"
        assert fake_object_store.deleted_refs == ["workspaces/1/source.pdf"]
        assert fake_memory_store.deleted_scope_ids == ["subject_hash_1"]
        assert fake_index.deleted_document_ids == ["doc_1"]

- [x] **Step 2: Run tests and confirm current raw event payload/no coordinator fails.**

Run: PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/compliance/test_audit_metadata.py tests/apps/cosa/compliance/test_retention_coordinator.py tests/apps/cosa/observability/test_logging.py -q

Expected: FAIL because kernel event payloads include tool/final values and no coordinator exists.

- [x] **Step 3: Add metadata allowlists and remove raw kernel event payload.**

    def safe_audit_metadata(event_type: str, run_context: Mapping[str, Any], decision: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "event_type": event_type,
            "run_id": run_context.get("run_id"),
            "workspace_id": run_context.get("workspace_id"),
            "deployment_id": run_context.get("deployment_id"),
            "snapshot_hash": run_context.get("compliance_snapshot_ref"),
            "reason_code": decision.get("reason_code"),
            "capability_id": decision.get("capability_id"),
            "provider_key": decision.get("provider_key"),
        }

Use this mapping for tool.completed, run.completed and run.failed events. Keep user-visible work product in governed artifact storage, never event payload.

- [x] **Step 4: Implement deletion with legal-hold precedence.**

    async def execute(self, request_id: str) -> RetentionExecutionResult:
        request = await self._rights_client.get_request(request_id)
        targets = await self._locator.find_targets(request.subject_reference_hash)
        if request.legal_hold:
            return await self._record_hold(request, targets)
        await self._object_store.delete_many(targets.object_refs)
        await self._memory_service.delete_subject_scope(request.subject_reference_hash)
        await self._knowledge_index.delete_documents(targets.document_ids)
        return await self._record_tombstone(request, targets)

Run only through a durable job. A failed deletion stays retryable and retains a structured pending request state.

- [x] **Step 5: Verify and commit.**

Run: PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/compliance/test_audit_metadata.py tests/apps/cosa/compliance/test_retention_coordinator.py tests/apps/cosa/observability/test_logging.py -q

Run: make knowledge-ingestion-test

Run: make lint

Expected: PASS.

    git add apps/cosa/compliance/audit_metadata.py apps/cosa/compliance/retention_coordinator.py apps/cosa/observability/logging.py packages/agent_integrations/openai_agents_sdk/kernel.py packages/agent/kernel/openai_agents_kernel.py apps/cosa/knowledge_ingestion/publish.py apps/cosa/knowledge_ingestion/object_store.py packages/agent/memory/retention.py tests/apps/cosa/compliance tests/apps/cosa/observability/test_logging.py
    git commit -m "feat: govern AI audit data and retention"

### Task 10: Deliver Compliance Center, disclosure, smoke tests and runbooks

**Files:**
- Create: frontend/lib/data/models/ai_compliance_models.dart
- Create: frontend/lib/modules/legal/services/ai_compliance_service.dart
- Create: frontend/lib/modules/legal/controllers/ai_compliance_controller.dart
- Create: frontend/lib/modules/legal/views/widgets/compliance_center_panel.dart
- Create: frontend/lib/modules/legal/views/widgets/compliance_incident_dialog.dart
- Create: frontend/lib/shared/widgets/ai_advisory_disclosure.dart
- Modify: frontend/lib/modules/legal/views/legal_view.dart
- Modify: frontend/lib/modules/legal/views/widgets/contract_risk_analyzer_dialog.dart
- Modify: frontend/lib/modules/legal/controllers/legal_controller.dart
- Modify: frontend/lib/modules/chat/views/chat_view.dart
- Modify: frontend/lib/modules/chat/views/session_view_widget.dart
- Create: frontend/test/modules/legal/compliance_center_test.dart
- Create: frontend/test/modules/legal/contract_risk_analyzer_dialog_test.dart
- Create: frontend/test/modules/chat/ai_advisory_disclosure_test.dart
- Create: tests/apps/cosa/compliance/test_process_smoke.py
- Create: tests/e2e/test_ai_compliance_flow.py
- Create: docs/operations/ai-compliance.md
- Create: docs/runbooks/ai-compliance-incident.md
- Modify: Makefile

**Interfaces:**
- Compliance Center displays workspace-scoped deployment, owner, expiry, provider, incident and approval metadata; it requires a rationale for Founder actions.
- AiAdvisoryDisclosure displays advisory-only notice, data warning and report/review action.
- Contract review presents sources, assumptions, limits, findings and required review status; it never presents a safety score.
- ai-compliance-test and ai-compliance-smoke are reproducible Make targets.

- [x] **Step 1: Write failing Flutter and process tests.**

    testWidgets("shows advisory disclosure before contract text entry", (tester) async {
      await tester.pumpWidget(testable(const ContractRiskAnalyzerDialog(onAnalyze: fakeAnalyze)));
      expect(find.textContaining("chỉ mang tính tham khảo"), findsOneWidget);
      expect(find.textContaining("dữ liệu cá nhân"), findsOneWidget);
    });

    testWidgets("does not show a legacy safety score", (tester) async {
      await tester.pumpWidget(testableDialog(result: {"safety_score": 98, "risk_level": "SAFE"}));
      expect(find.textContaining("ĐIỂM AN TOÀN"), findsNothing);
    });

    @pytest.mark.asyncio
    async def test_suspended_deployment_never_reaches_fake_provider(stack) -> None:
        stack.company.seed_deployment(status="SUSPENDED")
        result = await stack.cosa.submit_run(prompt="private input")
        assert result.status == "FAILED"
        assert stack.fake_provider.call_count == 0
        assert stack.audit.contains_reason("DEPLOYMENT_SUSPENDED")

- [x] **Step 2: Run tests and confirm all new UI/process components are absent.**

Run: cd frontend && flutter test test/modules/legal/compliance_center_test.dart test/modules/legal/contract_risk_analyzer_dialog_test.dart test/modules/chat/ai_advisory_disclosure_test.dart

Run: PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/compliance/test_process_smoke.py tests/e2e/test_ai_compliance_flow.py -q

Expected: FAIL with target files or components not found.

- [x] **Step 3: Implement typed Compliance Center and advisory disclosure.**

    class AiComplianceDeployment {
      final String id;
      final String status;
      final String ownerName;
      final String assessmentExpiresAt;
      final String providerStatus;
      const AiComplianceDeployment({
        required this.id,
        required this.status,
        required this.ownerName,
        required this.assessmentExpiresAt,
        required this.providerStatus,
      });
    }

    class AiAdvisoryDisclosure extends StatelessWidget {
      final String domain;
      final bool hasDataWarning;
      final VoidCallback? onReportProblem;
      const AiAdvisoryDisclosure({
        super.key,
        required this.domain,
        this.hasDataWarning = true,
        this.onReportProblem,
      });
    }

Map API JSON once in AiComplianceService. Widgets never receive raw evidence, subject reference or prompt data. Suspension, approval, resume and incident close each use a confirmation dialog with non-empty rationale.

- [x] **Step 4: Replace unsafe legal/chat presentation and add targets/runbooks.**

LegalController reports an advisory review, not a safety score. ContractRiskAnalyzerDialog renders sources, assumptions, limitations, findings, recommendations and review status. ChatView and SessionViewWidget show disclosure and report action. Add:

    ai-compliance-test:
        cd services/company && npx vitest run finance-legal/tests/ai-*.test.ts
        PYTHONPATH=$(CURDIR) $(PYTEST) tests/apps/cosa/compliance -q
        cd frontend && flutter test test/modules/legal/compliance_center_test.dart test/modules/legal/contract_risk_analyzer_dialog_test.dart test/modules/chat/ai_advisory_disclosure_test.dart

    ai-compliance-smoke:
        PYTHONPATH=$(CURDIR) $(PYTEST) tests/apps/cosa/compliance/test_process_smoke.py tests/e2e/test_ai_compliance_flow.py -q

Each command line in the actual Makefile starts with one literal tab. The indented sample above uses spaces only so the plan stays whitespace-clean.

The runbooks state that COSA never sends an external legal or incident notification itself. Founder records every notification decision and evidence.

- [x] **Step 5: Run final verification and commit.**

Run: make ai-compliance-test

Run: make ai-compliance-smoke

Run: make boundary-check

Run: make contracts-check

Run: make route-inventory-check

Run: git diff --check

Expected: PASS.

    git add frontend/lib frontend/test docs/operations/ai-compliance.md docs/runbooks/ai-compliance-incident.md tests/apps/cosa/compliance/test_process_smoke.py tests/e2e/test_ai_compliance_flow.py Makefile
    git commit -m "feat: surface AI compliance controls"

## Final Verification Sequence

- [ ] Run fresh migrations and rollback compatibility.

    make migrate-all
    make migration-check
    make test-migration-rollback

- [ ] Run Company services and types.

    cd services/company && npx vitest run finance-legal/tests/ai-*.test.ts finance-legal/tests/legal-applicability.test.ts finance-legal/tests/tenant-isolation.test.ts
    npm run typecheck

- [ ] Run COSA and generic boundary checks.

    make apps-cosa-test
    make boundary-check
    make lint
    make typecheck-py

- [ ] Run Flutter and process verification.

    make frontend-test
    make frontend-analyze
    make ai-compliance-smoke
    git diff --check

## Rollout and Rollback

1. Deploy schema and legal-source migrations first. Current systems remain DRAFT and cannot be labeled compliant by migration alone.
2. Register current COSA system versions and capability bindings. Founder approves an advisory private-business deployment only after evidence is present.
3. Turn on snapshot, statutory floor and data gates with FakeSDKModel in test/staging. Verify provider revocation, withdrawal and suspension produce zero provider calls.
4. Turn on the same gates in production. DeepSeek remains limited to non-personal, non-sensitive and non-confidential content until an approved provider/data profile exists.
5. During an incident, Founder opens the incident and suspends deployment. Runtime re-observes status and blocks new run, resume, model and external capability actions.
6. Never roll back legal audit history. Roll back only application code after preserving deployment, snapshot and incident records; keep the deployment SUSPENDED until a new assessment is approved.
