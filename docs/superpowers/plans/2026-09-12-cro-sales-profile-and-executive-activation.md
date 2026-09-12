# CRO Sales Profile + Executive Activation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` (or `superpowers:subagent-driven-development`) and execute tasks in order.

**Goal:** Chuyển `sales` từ placeholder `PENDING_CRM_FOUNDATION` thành Project Sales profile có evidence thật, rồi cho Founder kích hoạt `cro` advisory role một cách tường minh.

**Architecture:** CRM plan tạo business records và redacted knowledge/evidence; Sales profile chỉ đọc Project CRM snapshot đã được phân loại và tạo proposal/draft qua capability đã governed. CRO AgentSpec là capability-empty advisor, dùng Sales assignment exact pin cùng `cro-advisor` skillpin khi Board tạo frame. Company quyết định activation/readiness, không runtime Python nào tự nâng state.

**Tech Stack:** Existing CRM/Sales Company module, shared contracts/generators, AgentSpec registry/seed, skillpacks, Encore/Vitest, pytest and Flutter/GetX.

**Spec:** `docs/superpowers/specs/2026-09-11-executive-advisory-board-completion-and-agent-platform-restructuring-design.md`; predecessor `docs/superpowers/plans/2026-09-11-project-crm-and-sales-support-knowledge.md`.

## Global Constraints

- Do not mark `crm` or `sales` `READY` from static catalog or UI evidence. Require the CRM plan's Project-scope, consent, dedupe, knowledge publication and process-E2E gates.
- Sales reads only approved/redacted Project data; no contact raw PII, consent override, merge, pricing change, email/send action or external CRM mutation through this profile or CRO advisor.
- CRO is `advisoryOnly: true`, `L1_PROPOSE`, capability-empty, and must state evidence gaps/assumptions in every board response.
- Founder activation is explicit and CAS-protected. Backfill creates only `TEMPLATE`; existing leads and legacy null-project records keep their legacy behavior.

## File structure

| Unit | Files |
| --- | --- |
| CRM entry proof | `docs/superpowers/plans/2026-09-11-project-crm-and-sales-support-knowledge.md`, its Company/Agent E2E tests |
| Profile identity | `apps/cosa/agents/{specs,agent_profile_specs,seed}.py`, `services/company/operations/services/ai-member.service.ts` |
| Catalog/role | `shared/contracts/{startup-team-profiles,executive-advisor-roles}.json`, `scripts/gen-*.mjs`, generated contracts |
| Advisory content | `skillpacks/executive/cro-advisor/{manifest.yaml,SKILL.md}` |
| Company/Flutter truth | `services/company/operations/{migrations,services,tests}`, `frontend/lib/modules/hologram_hub/**`, corresponding tests |
| E2E | `tests/e2e/test_cro_sales_profile.py` |

### Task 1: Prove the Sales foundation before changing catalog state

**Files:** Test/modify predecessor plan's acceptance runbook only if its evidence is absent; do not change role catalog in this task.

**Interfaces:** Consumes Project CRM read contract with immutable `workspace_id`, `project_id`, consent/provenance and published knowledge revision. Produces a signed-off `SalesProfileReadiness` evidence record for the following tasks.

- [ ] **Step 1: Write the negative readiness test**

```ts
it("keeps CRO unavailable when sales has no published project CRM evidence", async () => {
  await expect(listExecutiveRoles(ctxWithoutPublishedSalesEvidence))
    .resolves.toContainEqual(expect.objectContaining({ roleKey: "cro", displayState: "UNAVAILABLE" }));
});
```

- [ ] **Step 2: Run it red**

```bash
cd services/company && npx vitest run operations/tests/executive-role-activation.service.test.ts
```

Expected: FAIL until the real CRM foundation publishes the Project-bound evidence contract; do not replace it with a fixture-only `READY` profile.

- [ ] **Step 3: Verify predecessor end-to-end evidence**

```bash
make services-test-company
PYTHONPATH=packages:. .venv/bin/python -m pytest tests/e2e/test_project_crm_sales_support_knowledge.py -v
```

Expected: Project isolation, consent/provenance, no raw PII projection and approved knowledge snapshot tests pass. If the named E2E has not been implemented, stop the CRO plan at this gate.

- [ ] **Step 4: Commit only any missing predecessor proof**

```bash
git add tests/e2e services/company/commercial apps/cosa
git commit -m "test(sales): prove project CRM readiness"
```

### Task 2: Add an exact Sales functional profile

**Files:** Modify `apps/cosa/agents/{specs,agent_profile_specs,seed}.py`, `services/company/operations/services/{ai-member,autonomy-classifier}.ts`; create `apps/cosa/tests/test_sales_profile_spec.py`; modify Company service tests.

**Interfaces:** Produces `COSA_SALES_AGENT_SPEC` (`id="cosa.agents.sales"`, `version="1.0.0"`, `L1_PROPOSE`) and exact Company ID/version/hash mapping for profile key `sales`.

- [ ] **Step 1: Write red identity and authorization tests**

```python
def test_sales_profile_has_explicit_spec_and_no_external_write_capability():
    spec = AGENT_PROFILE_SPECS["sales"]
    assert spec.id == "cosa.agents.sales"
    assert spec.autonomy_level is AutonomyLevel.L1_PROPOSE
    assert "engagement.message.send" not in spec.capability_refs
```

```ts
it("pins the Sales workforce member to the Python spec hash", async () => {
  const auth = await activateStartupTeamProfile(ctx, "sales", 1);
  expect(auth.spec.id).toBe("cosa.agents.sales");
  expect(auth.spec.hash).toMatch(/^[a-f0-9]{64}$/);
});
```

- [ ] **Step 2: Run them red**

```bash
PYTHONPATH=packages:. .venv/bin/python -m pytest apps/cosa/tests/test_sales_profile_spec.py -v
cd services/company && npx vitest run operations/tests/ai-member.test.ts operations/tests/project-startup-team.service.test.ts
```

Expected: FAIL because `sales` has no AgentSpec/mapping.

- [ ] **Step 3: Implement the bounded profile**

Define Sales with only existing read/proposal capabilities verified in the CRM plan; pin project-knowledge read and a new capability-empty `sales.pipeline-review` skill if needed. Add `sales` to every explicit registry/map, compute its `AgentSpec` hash, and copy the literal ID/version/hash into Company. Extend deterministic autonomy classification only for known sales evidence vocabulary; unknown requests remain `null`/manual routing.

- [ ] **Step 4: Run green and commit profile identity**

```bash
PYTHONPATH=packages:. .venv/bin/python -m pytest apps/cosa/tests/test_sales_profile_spec.py -v
cd services/company && npx vitest run operations/tests/ai-member.test.ts operations/tests/project-startup-team.service.test.ts && npm run typecheck
git add apps/cosa/agents apps/cosa/tests/test_sales_profile_spec.py services/company/operations
git commit -m "feat(sales): add pinned sales functional profile"
```

### Task 3: Catalog, migration, CRO skillpack and role readiness

**Files:** Modify shared source contracts and `scripts/gen-executive-advisor-roles.mjs`; create `services/company/operations/migrations/008_sales_startup_profile.{up,down}.sql`, `skillpacks/executive/cro-advisor/{manifest.yaml,SKILL.md}`; modify generated artifacts and contract tests.

**Interfaces:** Produces `sales: TEMPLATE/READY`, `cro: READY`, and `skillpack:executive/cro-advisor@1.0.0` with a hash accepted by the seed registry.

- [ ] **Step 1: Write red catalog/skill tests**

```python
def test_cro_requires_ready_sales_and_its_own_advisory_skill():
    assert STARTUP_TEAM_PROFILES["sales"].runtime_readiness == "READY"
    role = EXECUTIVE_ROLE_CATALOG["cro"]
    assert role.runtime_readiness == "READY"
    assert role.required_skill_pins == ("skillpack:executive/cro-advisor@1.0.0",)
```

- [ ] **Step 2: Run red**

```bash
PYTHONPATH=packages:. .venv/bin/python -m pytest tests/contracts/test_executive_advisor_role_catalog.py -v
make skillpacks-validate
```

Expected: FAIL until source catalog, generated contracts and manifest exist.

- [ ] **Step 3: Implement source-of-truth transition**

Change only `sales` and `cro` readiness after Task 1 proof. Generator must reject `cro: READY` unless catalog contains `sales: READY`; retain generic ready-requires-profile invariant. Migration inserts missing per-Project Sales template/assignment idempotently, never changes an existing row, and its down rejects non-template assignment or board-frame reference. CRO SKILL.md requires pipeline source/revision, labels forecast/pricing as assumptions, and forbids execution/legal/financial commitments.

- [ ] **Step 4: Regenerate, verify and commit**

```bash
node scripts/gen-startup-team-profiles.mjs
node scripts/gen-executive-advisor-roles.mjs
make contracts-check && make skillpacks-validate
git add shared/contracts scripts services/company/operations/migrations skillpacks/executive/cro-advisor apps/cosa/agents services/company/shared/contracts
git commit -m "feat(executive-board): make CRO sales-ready"
```

### Task 4: Prove activation, deliberation and Flutter truth

**Files:** Modify Company activation/deliberation tests; modify Hologram Hub model/service/controller/view tests; create `tests/e2e/test_cro_sales_profile.py`.

**Interfaces:** Company role list uses `{roleKey,label,advisoryRemit,displayState,runtimeReadiness,requiredProfileKey,version}`; mutation receipt is reloaded before Flutter replaces a card.

- [ ] **Step 1: Write cross-plane negative cases**

```python
async def test_cro_cannot_activate_or_deliberate_without_active_sales_or_foreign_project(client):
    assert (await client.activate_role("cro", sales_template)).code == "SALES_PROFILE_NOT_ACTIVE"
    assert (await client.deliberate("cro", foreign_project_evidence)).code == "CROSS_PROJECT_EVIDENCE_FORBIDDEN"
```

- [ ] **Step 2: Run red, then implement only state wiring**

```bash
PYTHONPATH=packages:. .venv/bin/python -m pytest tests/e2e/test_cro_sales_profile.py -v
```

Implement no new CRO endpoint: use existing role/profile activation and deliberation services. Flutter maps Company fields, renders unavailable reason from server state, and GET-reloads after activation receipt.

- [ ] **Step 3: Run green release gates**

```bash
make services-test-company
make agent-test
cd frontend && flutter test test/modules/hologram_hub/services/executive_advisory_board_service_test.dart test/modules/hologram_hub/views/executive_advisory_board_view_test.dart
cd .. && make frontend-api-contract-check
```

- [ ] **Step 4: Commit and record evidence**

```bash
git add services/company/operations frontend tests/e2e
git commit -m "test(executive-board): prove CRO activation boundary"
```
