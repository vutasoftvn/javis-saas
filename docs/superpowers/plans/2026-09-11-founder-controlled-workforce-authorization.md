# Founder-Controlled Workforce Authorization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Founder quản lý role của human và AI workforce; AI chỉ thực thi business capability đã được cấp, delegated và kiểm soát bởi approval/policy.

**Architecture:** Company Identity là authority source cho workforce role, agent grant, catalog capability-to-business-permission, version/epoch và audit. Agent Platform chỉ consume snapshot, xin ticket one-time cho side effect và gọi Company qua delegation; GraphQL là persisted read BFF, còn Flutter gửi command qua typed endpoints.

**Tech Stack:** Encore/TypeScript + Drizzle/PostgreSQL, Python/FastAPI + OpenAI Agents SDK CapabilityGateway, persisted-operation GraphQL BFF, Flutter/GetX, Vitest, pytest, Flutter test và disposable PostgreSQL E2E.

**Spec:** docs/superpowers/specs/2026-09-11-founder-controlled-workforce-authorization-design.md

## Global Constraints

- Làm trực tiếp trên main; không tạo git worktree.
- services/company là business truth; Agent Platform không ghi business DB trực tiếp.
- Dùng một WorkforceMember cho HUMAN và AI_AGENT; không tạo principal table song song.
- Founder authority chỉ thuộc HUMAN; role/permission human-only phải bị chặn ở service và database.
- DENY thắng, REQUIRE_APPROVAL không được nới bởi UI, agent hay Control Plane.
- Delegation cross-plane chỉ dùng secret đúng chiều; giữ TTL tối đa 600 giây và replay protection hiện có.
- GraphQL chỉ nhận persisted operationId và chỉ đọc; command authorization là typed Company API.
- Migration release chỉ additive. Không xóa role/run/audit/evidence lịch sử.
- Không thêm route vào allowlist hay UI unavailable để mô phỏng capability chưa có backend thật.

---

## File map

| Vùng | File chính | Trách nhiệm sau thay đổi |
|---|---|---|
| Company schema | services/company/shared/db/schema/identity.ts | role subject type, grant, binding, ticket, event, authorization state |
| Company migration | services/company/identity/migrations/003_founder_controlled_authorization.up.sql | expand schema, backfill safe và trigger chặn role sai loại subject |
| Company authority | services/company/identity/services/authorization.service.ts | founder guard, overview, event/version/epoch |
| Company commands | services/company/identity/handlers/agent-authorization.handler.ts | grant, revoke, simulate, ticket commands |
| Runtime policy | apps/cosa/policies/{snapshot,evaluator,business_permission_evaluator}.py | consume Company mapping/grant; overlay chỉ siết quyền |
| Runtime execution | packages/agent/capabilities/gateway.py | injected live authorizer trước side effect |
| Workforce runtime | packages/agent/workforce, apps/cosa/api/workforce_routes.py | assignment/run bind Company AI WorkforceMember |
| Read BFF | apps/cosa/graphql/{schema,resolvers,persisted_operations}.py | persisted workspaceAuthorityOverview read-only |
| Flutter | frontend/lib/modules/settings | founder authority panel truthful |
| Contracts/E2E | shared/contracts/mvp-surface.json, tests/e2e | endpoint contract và four-plane proof |

## Delivery order

1. Company data and founder-only authority.
2. Agent capability grant and mapping.
3. Snapshot bridge and workforce runtime identity.
4. Live ticket enforcement.
5. GraphQL read BFF.
6. Flutter truthful surface and generated contracts.
7. Shadow cutover and four-plane evidence.

### Task 1: Expand Company authorization schema and database invariants

**Files:**

- Modify: services/company/shared/db/schema/identity.ts
- Create: services/company/identity/migrations/003_founder_controlled_authorization.up.sql
- Create: services/company/identity/migrations/003_founder_controlled_authorization.down.sql
- Create: services/company/identity/tests/authorization-schema.test.ts
- Modify: services/company/identity/tests/permissions-api.test.ts

**Interfaces:**

- Produce RoleMemberType = "HUMAN" | "AI_AGENT" and AuthorizationEnforcementMode = "SHADOW" | "ENFORCED".
- Produce tables coreWorkspaceAuthorizationStates, coreCapabilityPermissionBindings, coreAgentCapabilityGrants, coreAuthorizationEvents and coreAgentAuthorizationTickets.
- Later tasks consume workspaceId, authorizationEpoch, policyVersion, workforceMemberId, capabilityId and resource scope columns.

- [ ] **Step 1: Write failing database and service tests**

~~~ts
it("rejects assigning a HUMAN-only founder role to an AI_AGENT in the database", async () => {
  const { workspaceId, founderCtx, aiMemberId, founderRoleId } = await seedAuthorityWorkspace();
  await expect(updatePermissionsService(founderCtx, {
    expectedVersion: 1,
    reason: "invalid AI founder assignment",
    mutations: [{ kind: "ASSIGN_ROLE", memberId: aiMemberId, roleId: founderRoleId }],
  })).rejects.toThrow(/ROLE_MEMBER_TYPE_MISMATCH/);
  await expect(db.insert(coreMemberRoleAssignments).values({
    workspaceId: BigInt(workspaceId), workforceMemberId: BigInt(aiMemberId), roleId: founderRoleId,
  })).rejects.toThrow();
});
~~~

- [ ] **Step 2: Run the focused test to verify it fails**

Run: cd services/company && npx vitest run identity/tests/authorization-schema.test.ts

Expected: FAIL because roles have no subject-type metadata and direct SQL insert is accepted.

- [ ] **Step 3: Add additive schema, migration and trigger**

Add allowedMemberTypes to workspace roles and these Drizzle records:

~~~ts
export const coreWorkspaceAuthorizationStates = coreSchema.table("workspace_authorization_states", {
  workspaceId: bigint("workspace_id", { mode: "bigint" }).primaryKey(),
  enforcementMode: text("enforcement_mode").default("SHADOW").notNull(),
  authorizationEpoch: integer("authorization_epoch").default(1).notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const coreAgentCapabilityGrants = coreSchema.table("agent_capability_grants", {
  id: uuid("id").primaryKey().defaultRandom(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  agentWorkforceMemberId: bigint("agent_workforce_member_id", { mode: "bigint" }).notNull(),
  capabilityId: text("capability_id").notNull(),
  projectId: bigint("project_id", { mode: "bigint" }),
  legalEntityId: bigint("legal_entity_id", { mode: "bigint" }),
  constraints: jsonb("constraints").default({}).notNull(),
  validFrom: timestamp("valid_from", { withTimezone: true }).defaultNow().notNull(),
  validUntil: timestamp("valid_until", { withTimezone: true }),
  status: text("status").default("ACTIVE").notNull(),
  grantedByFounderMemberId: bigint("granted_by_founder_member_id").notNull(),
  revokedAt: timestamp("revoked_at", { withTimezone: true }),
  revokeReason: text("revoke_reason"),
});
~~~

The SQL migration must backfill every existing role from its existing assignments, set system founder rows to ARRAY['HUMAN'], insert SHADOW state for every workspace, and create a BEFORE INSERT OR UPDATE trigger on member_role_assignments. The trigger joins target role and workforce member, requires same workspace, and raises ROLE_MEMBER_TYPE_MISMATCH when member_type is not allowed.

- [ ] **Step 4: Run schema tests and migration gates**

Run: cd services/company && npx vitest run identity/tests/authorization-schema.test.ts identity/tests/permissions-api.test.ts && node scripts/migrate.mjs --check-pending

Expected: PASS; AI founder assignment fails through service and direct DB insert.

- [ ] **Step 5: Commit the isolated schema deliverable**

~~~bash
git add services/company/shared/db/schema/identity.ts services/company/identity/migrations/003_founder_controlled_authorization.*.sql services/company/identity/tests/authorization-schema.test.ts services/company/identity/tests/permissions-api.test.ts
git commit -m "feat(identity): add workforce authorization schema"
~~~

### Task 2: Enforce founder-human-only role management and append authority audit events

**Files:**

- Create: services/company/identity/services/authorization.service.ts
- Modify: services/company/identity/services/{command-authority,permissions,tenant-context}.ts
- Modify: services/company/identity/handlers/permissions.handler.ts
- Create: services/company/identity/tests/founder-authorization.test.ts
- Modify: services/company/identity/tests/permissions-api.test.ts

**Interfaces:**

- Produce requireFounderAuthorization(ctx: TenantContext): Promise<FounderAuthorization>.
- Produce appendAuthorizationEvent(tx, event) and advanceAuthorizationEpoch(tx, workspaceId, actorMemberId, reason).
- updatePermissionsService consumes this guard and writes events/version/epoch atomically.

- [ ] **Step 1: Write failing founder authority tests**

~~~ts
it("rejects co-founder authority mutation after enforcement but permits human founder", async () => {
  const { founderCtx, cofounderCtx, roleId } = await seedEnforcedAuthorityWorkspace();
  await expect(updatePermissionsService(cofounderCtx, {
    expectedVersion: 1, reason: "escalate",
    mutations: [{ kind: "SET_ROLE_PERMISSION", roleId, permissionKey: "operations.task.read", effect: "ALLOW" }],
  })).rejects.toThrow(/FOUNDER_AUTHORITY_REQUIRED/);
  await expect(updatePermissionsService(founderCtx, {
    expectedVersion: 1, reason: "grant read",
    mutations: [{ kind: "SET_ROLE_PERMISSION", roleId, permissionKey: "operations.task.read", effect: "ALLOW" }],
  })).resolves.toMatchObject({ success: true, version: 2 });
});
~~~

- [ ] **Step 2: Run the focused tests to verify failure**

Run: cd services/company && npx vitest run identity/tests/founder-authorization.test.ts identity/tests/permissions-api.test.ts

Expected: FAIL because requireFounderCommand accepts co-founder and no authority event is written.

- [ ] **Step 3: Implement resolver, shadow comparison and transaction behavior**

~~~ts
export async function requireFounderAuthorization(ctx: TenantContext): Promise<FounderAuthorization> {
  const subject = await resolveAuthorizationSubject(ctx.workspaceId, ctx.workforceMemberId);
  if (subject.memberType !== "HUMAN" || !subject.hasActiveFounderRole) {
    throw APIError.permissionDenied("FOUNDER_AUTHORITY_REQUIRED");
  }
  return subject;
}
~~~

Resolve active human founder assignment in the requested workspace. In SHADOW mode compare it with legacy membershipRole and append a non-mutating discrepancy event. In ENFORCED mode reject all non-founder authority commands. Apply this helper only to authorization/agent-governance mutation, not unrelated finance/operations guards. updatePermissionsService must validate allowedMemberTypes before insert, append one event per mutation plus one epoch/version event in the same transaction, and retain last-founder protection.

- [ ] **Step 4: Run Company tests and static boundaries**

Run: cd services/company && npx vitest run identity/tests/founder-authorization.test.ts identity/tests/permissions-api.test.ts identity/tests/business-command-authority.test.ts && npm run typecheck

Run: make company-boundary-check && make encore-handler-boundary-check && make ts-suppression-check

Expected: PASS; co-founder can retain unrelated business privileges but cannot mutate authority.

- [ ] **Step 5: Commit the authority-command deliverable**

~~~bash
git add services/company/identity/services/authorization.service.ts services/company/identity/services/{command-authority,permissions,tenant-context}.ts services/company/identity/handlers/permissions.handler.ts services/company/identity/tests/{founder-authorization,permissions-api}.test.ts
git commit -m "feat(identity): enforce founder authority commands"
~~~

### Task 3: Implement typed agent grants, capability mapping, overview and simulation commands

**Files:**

- Modify: services/company/identity/services/{permission-catalog,business-authorization}.ts
- Create: services/company/identity/services/agent-authorization.service.ts
- Create: services/company/identity/handlers/agent-authorization.handler.ts
- Modify: services/company/identity/handlers/index.ts
- Create: services/company/identity/tests/agent-authorization.test.ts
- Modify: services/company/identity/tests/business-policy-rules.test.ts

**Interfaces:**

- Produce CapabilityPermissionBinding { capabilityId, permissionKey, riskClass, version }.
- Produce grantAgentCapability, revokeAgentCapability, evaluateAgentCapabilityAuthority and getAuthorizationOverview.
- Expose GET /identity/authorization/overview, POST /identity/agent-capability-grants, POST /identity/agent-capability-grants/:grantId/revoke and POST /identity/authorization/simulate.

- [ ] **Step 1: Write failing mapping/grant tests**

~~~ts
it("denies an AI agent with a role but no exact capability grant", async () => {
  const seeded = await seedAgentAuthorityWorkspace({ capabilityId: "operations.task.list" });
  const decision = await evaluateAgentCapabilityAuthority({
    workspaceId: seeded.workspaceId,
    agentWorkforceMemberId: seeded.agentMemberId,
    capabilityId: "operations.task.list",
    scope: { workspaceId: seeded.workspaceId },
    facts: {},
  });
  expect(decision.effect).toBe("DENY");
  expect(decision.reasonCodes).toContain("MISSING_AGENT_CAPABILITY_GRANT");
});
~~~

- [ ] **Step 2: Run the tests to verify failure**

Run: cd services/company && npx vitest run identity/tests/agent-authorization.test.ts identity/tests/business-policy-rules.test.ts

Expected: FAIL because no grant/mapping service exists and the old policy code compares capability text with permission key.

- [ ] **Step 3: Add typed grant logic**

Add operations.task.read to the permission catalog and migration seed. Add the reviewed first binding operations.task.list -> operations.task.read -> READ. Require founder-human-only for grant/revoke. Permit a grant only when target is active AI_AGENT, binding exists, target has matching active role permission, and scope/constraints validate. Revoke changes status to REVOKED, writes revokedAt/revokeReason, appends event and increments epoch. Overview returns only the request workspace's roles, assignments, grants, binding version, policy version/epoch, pending approval summary and audit summary.

~~~ts
export interface EvaluateAgentCapabilityInput {
  workspaceId: string;
  agentWorkforceMemberId: string;
  capabilityId: string;
  scope: ResourceScope;
  facts: Record<string, unknown>;
}

export async function evaluateAgentCapabilityAuthority(
  input: EvaluateAgentCapabilityInput,
): Promise<RuleDecision & { grantId?: string; riskClass: CapabilityRiskClass }>;
~~~

- [ ] **Step 4: Run Company API and policy tests**

Run: cd services/company && npx vitest run identity/tests/agent-authorization.test.ts identity/tests/business-policy-rules.test.ts identity/tests/permissions-api.test.ts && npm run typecheck

Expected: PASS; unknown capability, foreign agent, expired/revoked grant and amount/currency mismatch are denied; simulation is read-only.

- [ ] **Step 5: Commit the grant/catalog deliverable**

~~~bash
git add services/company/identity/services/{permission-catalog,business-authorization,agent-authorization}.ts services/company/identity/handlers/{agent-authorization,index}.ts services/company/identity/tests/{agent-authorization,business-policy-rules}.test.ts
git commit -m "feat(identity): add agent capability grants"
~~~

### Task 4: Return one Company authority snapshot and make policy evaluation deny by intersection

**Files:**

- Modify: services/company/identity/handlers/business-policy.handler.ts
- Modify: services/company/identity/services/business-authorization.service.ts
- Modify: apps/cosa/policies/{company_policy_client,snapshot,business_permission_evaluator,evaluator}.py
- Modify: tests/apps/cosa/policy_test_helpers.py
- Create: tests/apps/cosa/policies/test_agent_authorization_snapshot.py

**Interfaces:**

- Extend GET /identity/business-policy/rules with authorizationEpoch, capabilityBindings and agentCapabilityGrants for one requested AI workforce member.
- Produce AgentAuthorizationSnapshot.resolve(capabilityId, payload).
- CosaPolicyEngine evaluates mapped business permission and lets Control Plane only deny or require approval.

- [ ] **Step 1: Write failing policy-order test**

~~~python
def test_platform_allow_cannot_bypass_missing_company_agent_grant() -> None:
    snapshot = policy_snapshot_with(
        control_rule=("operations.task.*", "ALLOW"),
        agent_authority=agent_authority_snapshot(grants=[]),
    )
    decision = CosaPolicyEngine().evaluate("operations.task.list", {}, {"policy_snapshot": snapshot})
    assert decision.outcome is PolicyOutcome.DENY
    assert "MISSING_AGENT_CAPABILITY_GRANT" in decision.reasons
~~~

- [ ] **Step 2: Run the focused test to verify failure**

Run: PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/policies/test_agent_authorization_snapshot.py -q

Expected: FAIL because the current evaluator returns early for Control Plane ALLOW and compares raw capability against business permission rules.

- [ ] **Step 3: Implement snapshot DTOs and evaluation order**

~~~python
class AgentCapabilityAuthority(BaseModel):
    capability_id: str
    permission_key: str
    risk_class: str
    grant_id: str
    constraints: dict[str, Any]

class BusinessPolicyRuleSet(BaseModel):
    policy_version: int
    authorization_epoch: int
    rule_groups: list[list[BusinessPermissionRule]]
    agent_capabilities: list[AgentCapabilityAuthority]
~~~

Keep the Company route delegation-only with CAP_BUSINESS_POLICY_RULES_READ. Runtime must evaluate statutory floor and live deny state first, exact mapping/grant next, mapped permission with validated facts next, then Control Plane DENY/REQUIRE_APPROVAL. Control Plane ALLOW must fall through; a missing agent snapshot is DENY for an agent capability. Keep hard-coded safety checks only as an extra safety floor until they receive catalog bindings.

- [ ] **Step 4: Run Python and Company contract tests**

Run: PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/policies/test_agent_authorization_snapshot.py tests/apps/cosa/api/test_graphql_routes.py -q

Run: cd services/company && npx vitest run identity/tests/business-policy-rules.test.ts identity/tests/agent-authorization.test.ts

Expected: PASS; mapping drift cannot silently allow a capability and overlay never broadens authority.

- [ ] **Step 5: Commit the policy bridge deliverable**

~~~bash
git add services/company/identity/{handlers/business-policy.handler.ts,services/business-authorization.service.ts} apps/cosa/policies/{company_policy_client.py,snapshot.py,business_permission_evaluator.py,evaluator.py} tests/apps/cosa/policies/test_agent_authorization_snapshot.py
git commit -m "feat(agent): enforce company capability policy snapshot"
~~~

### Task 5: Bind agent assignments and durable runs to Company AI workforce identity

**Files:**

- Modify: packages/agent/workforce/{models,repository}.py
- Create: packages/agent/migrations/003_add_workforce_member_reference.sql
- Modify: apps/cosa/api/{workforce_schemas,workforce_routes}.py
- Modify: apps/cosa/worker/handlers.py
- Modify: apps/cosa/policies/company_policy_client.py
- Create: tests/apps/cosa/api/test_workforce_authority_routes.py
- Create: tests/agent/workforce/test_company_workforce_member_binding.py

**Interfaces:**

- Extend WorkforceAssignmentRecord with company_workforce_member_id: str.
- Extend durable run context with immutable agent_workforce_member_id.
- Every business-policy snapshot call receives that ID rather than a client-supplied capability-time value.

- [ ] **Step 1: Write failing identity-binding tests**

~~~python
async def test_assignment_requires_active_company_ai_workforce_member(founder_identity, app_client):
    response = await app_client.post(
        "/agent/workforce/assignments",
        json={"functional_key": "operations", "company_workforce_member_id": "999"},
        headers=founder_identity.headers(),
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "active AI workforce member is required"
~~~

- [ ] **Step 2: Run the tests to verify failure**

Run: PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/api/test_workforce_authority_routes.py tests/agent/workforce/test_company_workforce_member_binding.py -q

Expected: FAIL because local assignment has no Company workforce reference and create_assignment checks only local workspace operator.

- [ ] **Step 3: Persist reference and enforce founder creation**

Add a nullable Agent DB column first and make the read path compatible, then require it for all new assignments. POST /agent/workforce/assignments must call Company through a delegation-protected validator proving caller founder, target same workspace, target active AI_AGENT, and no direct Company DB access. Store only opaque Company ID. When worker creates/resumes a run, copy assignment ID and Company member ID to durable payload. Reject running assignment when it is retired, Company AI member is suspended or snapshot is absent.

~~~python
class WorkforceAssignmentRecord(BaseModel):
    assignment_id: UUID
    workspace_id: str
    company_workforce_member_id: str
    functional_key: str
    spec_id: str
    spec_version: str
    definition_hash: str
~~~

- [ ] **Step 4: Run workforce and worker tests**

Run: PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/api/test_workforce_authority_routes.py tests/agent/workforce/test_company_workforce_member_binding.py tests/apps/cosa/worker/test_automation_run_task.py -q

Expected: PASS; non-founder, foreign/inactive/human workforce member are rejected and run identity is immutable.

- [ ] **Step 5: Commit the workforce identity deliverable**

~~~bash
git add packages/agent/workforce packages/agent/migrations apps/cosa/api/{workforce_routes.py,workforce_schemas.py} apps/cosa/worker/handlers.py apps/cosa/policies/company_policy_client.py tests/apps/cosa/api/test_workforce_authority_routes.py tests/agent/workforce/test_company_workforce_member_binding.py
git commit -m "feat(workforce): bind agent runs to company identity"
~~~

### Task 6: Require a one-time live authorization ticket before agent side effects

**Files:**

- Create: services/company/identity/services/agent-authorization-ticket.service.ts
- Modify: services/company/identity/handlers/agent-authorization.handler.ts
- Modify: services/company/shared/auth/cosa-delegation.service.ts
- Create: apps/cosa/authorization/live_authorizer.py
- Modify: apps/cosa/composition/agent_plane.py
- Modify: packages/agent/capabilities/gateway.py
- Modify: apps/cosa/capabilities/client.py
- Create: services/company/identity/tests/agent-authorization-ticket.test.ts
- Create: tests/agent/capabilities/test_live_authorization_ticket.py

**Interfaces:**

- Expose delegation-only POST /identity/agent-authorization/tickets.
- Produce opaque AuthorizationTicket { ticketId, authorizationEpoch, expiresAt } bound to workspace/run/tool-call/checkpoint/capability/agent member.
- Produce injected LiveAuthorizationAuthorizer.authorize(req, capabilitySpec).
- Produce consumeAgentAuthorizationTicket(tx, ticketId, expected) for Company business handler transactions.

- [ ] **Step 1: Write failing revoke/ticket tests**

~~~python
async def test_revoked_grant_after_dispatch_cannot_obtain_ticket(gateway, revoke_grant):
    request = gateway_request(run_id="run-7", capability_id="finance.transaction.record")
    await revoke_grant(request.context["agent_capability_grant_id"])
    result = await gateway.execute(request)
    assert result.status == "denied"
    assert "AGENT_CAPABILITY_GRANT_REVOKED" in result.error_message
~~~

- [ ] **Step 2: Run ticket tests to verify failure**

Run: cd services/company && npx vitest run identity/tests/agent-authorization-ticket.test.ts

Run: PYTHONPATH=. .venv/bin/python -m pytest tests/agent/capabilities/test_live_authorization_ticket.py -q

Expected: FAIL because gateway has no live authorizer and Company has no one-time ticket record.

- [ ] **Step 3: Issue and consume opaque tickets without a new cross-plane secret**

The ticket endpoint verifies existing COSA_COMPANY_DELEGATION_SECRET claims, exact run/capability scope and current Company authority. It creates a random opaque record expiring in at most 60 seconds. It never trusts an agent-supplied principal; Company AI member must match Task 5 run assignment.

~~~ts
export async function issueAgentAuthorizationTicket(input: IssueTicketInput): Promise<AuthorizationTicket>;
export async function consumeAgentAuthorizationTicket(
  tx: DbTransaction,
  ticketId: string,
  expected: { workspaceId: string; runId: string; toolCallId: string; checkpointRef: string; capabilityId: string; authorizationEpoch: number },
): Promise<void>;
~~~

Inject live authorizer after policy/approval but before capability handler. It skips only READ and explicitly draft-only capability classes, puts ticketId in invocation context, and the Company transport sends X-Cosa-Authorization-Ticket. Company handler consumes ticket in the same transaction as side effect; replay, expiry, epoch mismatch, wrong run/tool/checkpoint/capability and concurrent consume deny.

- [ ] **Step 4: Run ticket, gateway and delegation tests**

Run: cd services/company && npx vitest run identity/tests/agent-authorization-ticket.test.ts shared/auth/cosa-delegation.test.ts && npm run typecheck

Run: PYTHONPATH=. .venv/bin/python -m pytest tests/agent/capabilities/test_live_authorization_ticket.py tests/agent/capabilities/test_gateway.py -q

Expected: PASS; ticket is issued only after approval, revoke blocks dispatched run and duplicate delivery cannot create a second effect.

- [ ] **Step 5: Commit the live-control deliverable**

~~~bash
git add services/company/shared/auth/cosa-delegation.service.ts services/company/identity/{handlers/agent-authorization.handler.ts,services/agent-authorization-ticket.service.ts,tests/agent-authorization-ticket.test.ts} apps/cosa/{authorization/live_authorizer.py,composition/agent_plane.py,capabilities/client.py} packages/agent/capabilities/gateway.py tests/agent/capabilities/test_live_authorization_ticket.py
git commit -m "feat(agent): require live authorization tickets"
~~~

### Task 7: Register persisted GraphQL workspaceAuthorityOverview as a read BFF

**Files:**

- Modify: apps/cosa/graphql/{schema,resolvers,persisted_operations}.py
- Modify: apps/cosa/capabilities/client.py
- Modify: tests/apps/cosa/api/test_graphql_routes.py
- Create: tests/apps/cosa/graphql/test_workspace_authority_overview.py

**Interfaces:**

- Extend OperationId with workspaceAuthorityOverview.
- Produce WorkspaceAuthorityOverviewOperation with allowed_variables = frozenset().
- Resolver consumes Company GET /identity/authorization/overview using authenticated identity; never accepts workspace/principal variable.

- [ ] **Step 1: Write failing persisted-operation tests**

~~~python
@pytest.mark.asyncio
async def test_member_cannot_read_workspace_authority_overview(test_app):
    app, _ = test_app
    override_authenticated_identity(app, workspace_id="ws-a", role_id="member")
    async with asgi_client(app) as client:
        response = await client.post("/agent/graphql", json={
            "operationId": "workspaceAuthorityOverview", "variables": {},
        })
    assert response.status_code == 403
~~~

- [ ] **Step 2: Run GraphQL tests to verify failure**

Run: PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/api/test_graphql_routes.py tests/apps/cosa/graphql/test_workspace_authority_overview.py -q

Expected: FAIL with 422 because workspaceAuthorityOverview is not a permitted operation ID.

- [ ] **Step 3: Register the read-only resolver**

Add literal operation ID and a no-variable resolver. It checks role only as preliminary boundary and asks Company for authoritative overview. Do not add mutation class, raw parser or dynamic selection set. Preserve current response envelope and audit only operation ID/principal/workspace/duration.

- [ ] **Step 4: Run route and resolver tests**

Run: PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/api/test_graphql_routes.py tests/apps/cosa/graphql/test_workspace_authority_overview.py -q

Expected: PASS; founder gets only tenant overview, member receives 403, raw query and unknown variable remain 422, and no mutation is registered.

- [ ] **Step 5: Commit the read-BFF deliverable**

~~~bash
git add apps/cosa/graphql/{schema.py,resolvers.py,persisted_operations.py} apps/cosa/capabilities/client.py tests/apps/cosa/api/test_graphql_routes.py tests/apps/cosa/graphql/test_workspace_authority_overview.py
git commit -m "feat(graphql): add founder authority overview"
~~~

### Task 8: Replace the unavailable Settings permissions shell with typed founder controls

**Files:**

- Modify: shared/contracts/mvp-surface.json
- Regenerate: services/company/shared/contracts/mvp-surface.generated.ts
- Regenerate: apps/cosa/api/mvp_contracts_generated.py
- Regenerate: frontend/lib/core/network/mvp_endpoints.g.dart
- Modify: frontend/lib/modules/settings/{models/permission_models.dart,services/permissions_service.dart,controllers/permissions_controller.dart,views/widgets/permissions_panel.dart}
- Create: frontend/lib/modules/settings/services/workspace_authority_graphql_client.dart
- Modify: frontend/test/modules/settings/permissions_panel_test.dart
- Create: frontend/test/modules/settings/permissions_service_test.dart

**Interfaces:**

- Add enabled Mvp capabilities identity.permissions.read, identity.permissions.write, identity.permissions.simulate, identity.agent_capability_grant.create and identity.agent_capability_grant.revoke with exact implemented routes/tests.
- Produce WorkspaceAuthorityGraphqlClient.fetchOverview(), always posting operationId workspaceAuthorityOverview and empty variables.
- PermissionsService stops calling MvpRequestClient.unavailable and calls only generated MvpEndpoint commands.

- [ ] **Step 1: Write failing Flutter transport/state tests**

~~~dart
test('founder loads persisted overview and sends grant command through generated endpoint', () async {
  final service = PermissionsService(client: fakeMvpClient, graphqlClient: fakeGraphqlClient);
  final result = await service.createAgentCapabilityGrant(
    agentWorkforceMemberId: '77', capabilityId: 'operations.task.list',
  );
  expect(result, isA<ApiSuccess<AgentCapabilityGrantModel>>());
  expect(fakeMvpClient.lastEndpoint, MvpEndpoint.identityAgentCapabilityGrantCreate);
  expect(fakeGraphqlClient.lastBody, {'operationId': 'workspaceAuthorityOverview', 'variables': {}});
});
~~~

- [ ] **Step 2: Run Flutter tests to verify failure**

Run: cd frontend && flutter test test/modules/settings/permissions_service_test.dart test/modules/settings/permissions_panel_test.dart

Expected: FAIL because PermissionsService returns unavailable and no GraphQL model/client exists.

- [ ] **Step 3: Implement truthful models, clients and panel**

Add decode models for subject type, allowed role types, grant scope/expiry/status, policy version/epoch, active runs, pending approvals and audit summary. Use MvpRequestClient.request for every mutation. Map 403 to founder-only state, 409 to reload-and-review state and 422 to inline fields. Do not offer a human-only role in an AI selector; backend remains authority.

Replace matrix-only panel with tabs Members, AI workforce, Policies, Live control and Audit. Keep it inside SettingsView; do not add a visible navigation destination before backend/contract tests pass. Disable save during request and retain draft on version conflict.

- [ ] **Step 4: Regenerate contracts and run UI/API gates**

Run: node scripts/gen-mvp-contracts.mjs && make contract-freeze-check && make frontend-api-contract-check

Run: cd frontend && flutter test test/modules/settings/permissions_service_test.dart test/modules/settings/permissions_panel_test.dart && flutter analyze --no-pub

Expected: PASS; UI has no literal route and error/conflict states are explicit rather than unavailable.

- [ ] **Step 5: Commit frontend deliverable**

~~~bash
git add shared/contracts/mvp-surface.json services/company/shared/contracts/mvp-surface.generated.ts apps/cosa/api/mvp_contracts_generated.py frontend/lib/core/network/mvp_endpoints.g.dart frontend/lib/modules/settings frontend/test/modules/settings
git commit -m "feat(frontend): connect founder authority controls"
~~~

### Task 9: Perform shadow cutover and prove authorization across four real planes

**Files:**

- Create: services/company/scripts/authorization-cutover-preflight.mjs
- Modify: services/company/identity/services/authorization.service.ts
- Modify: services/company/identity/tests/founder-authorization.test.ts
- Create: tests/e2e/scenarios/founder_authorization.py
- Modify: tests/e2e/test_cross_plane_smoke.py
- Modify: tests/e2e/seed/identity.py
- Modify: Makefile
- Modify: docs/superpowers/specs/2026-09-11-founder-controlled-workforce-authorization-design.md

**Interfaces:**

- Produce node services/company/scripts/authorization-cutover-preflight.mjs --check; it exits nonzero for workspace missing human founder assignment or invalid agent role/grant state.
- Produce test_s9_founder_authorization covering grant -> confirmed work package -> worker -> approval/effect -> audit, revoke and cross-tenant negative branches.
- Move exactly one preflight-clean workspace SHADOW -> ENFORCED only through a founder-confirmed audited Company command.

- [ ] **Step 1: Write failing process E2E**

~~~python
def test_s9_founder_authorization(real_cosa_stack, disposable_cluster) -> None:
    seeded = identity.seed_workspace(real_cosa_stack, disposable_cluster, with_member=True)
    scenario = founder_authorization.run(real_cosa_stack, seeded, disposable_cluster)
    assert scenario["agent_without_grant"] == "denied"
    assert scenario["revoked_after_dispatch"] == "denied_before_effect"
    assert scenario["approval_bound_to_checkpoint"] is True
    assert scenario["cross_tenant"] == "denied"
~~~

- [ ] **Step 2: Run E2E to verify failure before implementation**

Run: source scripts/load-dev-env.sh && make e2e-cross-plane-smoke

Expected: FAIL in S9 because scenario, preflight and enforcement transition do not yet exist. Do not print environment values; the loader must export PGPASSWORD.

- [ ] **Step 3: Implement preflight, shadow and explicit enforcement command**

Preflight reports only IDs/counts for zero human founder assignment, invalid founder subject, AI member in human-only role, orphan assignment reference, invalid capability binding, expired active grant and missing authorization state. It must not mutate in check mode. Keep SHADOW default for migrated workspaces; append discrepancy events for legacy vs new result. Add an audited founder command to move exactly one preflight-clean workspace to ENFORCED; never auto-promote during deploy. Mark the spec Implemented only after all evidence passes.

- [ ] **Step 4: Run release evidence in dependency order**

Run: cd services/company && npm run typecheck && encore test

Run: PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa tests/agent -q

Run: make frontend-test && make frontend-analyze && make contract-freeze-check && make frontend-api-contract-check

Run: source scripts/load-dev-env.sh && make e2e-cross-plane-smoke

Expected: PASS. E2E proves no agent direct business DB write, one high-risk effect only, checkpoint-bound human approval, immediate revoke before effect, tenant isolation and persisted audit evidence.

- [ ] **Step 5: Commit cutover evidence and documentation**

~~~bash
git add services/company/scripts/authorization-cutover-preflight.mjs services/company/identity/services/authorization.service.ts services/company/identity/tests/founder-authorization.test.ts tests/e2e/scenarios/founder_authorization.py tests/e2e/test_cross_plane_smoke.py tests/e2e/seed/identity.py Makefile docs/superpowers/specs/2026-09-11-founder-controlled-workforce-authorization-design.md
git commit -m "test(e2e): prove founder controlled agent authority"
~~~

## Plan self-review

### Spec coverage

- Founder-only role/policy/grant authority: Tasks 1-3 and 9.
- Shared WorkforceMember without parallel identity: Tasks 1 and 5.
- Exact agent grant, capability mapping and deny-by-intersection: Tasks 3-4.
- Delegation, live ticket, revoke and human approval: Task 6 and Task 9.
- Business truth and no direct agent DB write: Tasks 4-6 and Task 9 E2E.
- GraphQL read-only purpose: Task 7.
- Truthful Flutter and generated contract: Task 8.
- Additive migration, backfill, shadow mode and explicit cutover: Tasks 1, 2 and 9.

### Dependency check

Task 2 needs Task 1 tables/state. Task 3 needs founder authority. Task 4 consumes Task 3 mapping/grants. Task 5 binds runtime identity. Task 6 consumes Tasks 3-5. GraphQL and Flutter are downstream of authoritative commands. Cutover occurs only after all previous deliverables and process E2E evidence.

### Scope boundary

This plan does not rewrite every finance or operations role guard in one release. It creates the authority substrate and enforces live tickets on agent-exposed side effects; each new agent capability needs a reviewed catalog binding, grant/approval policy and E2E coverage.
