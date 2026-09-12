# CAIO AI Governance Profile + Executive Activation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` (or `superpowers:subagent-driven-development`) and execute tasks in order.

**Goal:** Tạo `ai_governance` functional profile đọc snapshot policy/evaluation đã redacted, rồi mở CAIO advisor để đánh giá model, provider, prompt safety và red-team risk mà không có quyền thay đổi Control Plane.

**Architecture:** Control Plane tiếp tục là authority cho model policy, provider/capability configuration và evaluation registry. Company Operations chỉ lưu Project AI Governance Dossier với reference/version/hash/redacted outcome; nó không sao chép secret/provider config. A signed/read-only projection converts verified Control Plane snapshots to a Project-bound advisory input. CAIO spec is capability-empty; AI Governance profile has one read capability only.

**Tech Stack:** Control Plane TypeScript/Encore, Company Operations, Python capability/AgentSpec registry, contracts/generators, skillpacks, Flutter, Vitest/pytest/disposable-process E2E.

**Spec:** `docs/superpowers/specs/2026-09-11-executive-advisory-board-completion-and-agent-platform-restructuring-design.md`; dependencies `docs/superpowers/plans/2026-09-12-multi-agent-workflow-and-unified-approval.md` and `docs/superpowers/plans/2026-09-12-skill-improvement-feedback-loop.md` for canonical policy/evaluator identity only.

## Global Constraints

- CAIO cannot publish/pin/retire a skill, change model/provider/policy, rotate provider secret, invoke a model, approve promotion or bypass the unified approval ledger.
- Snapshot must bind workspace, Project, policy/evaluator ID+version+definition hash, source timestamp and signer; stale/foreign/unverifiable source fails closed.
- No prompt transcript, API key, provider credential, raw user message, model output or vulnerability payload enters Company dossier/board frame.
- B. plans are not evidence themselves. This plan begins only after their required snapshot endpoints and process proofs exist.

## File structure

| Unit | Files |
| --- | --- |
| Control Plane read port | `services/cosa/services/ai-governance-snapshot.service.ts`, handler/tests, generated client contract |
| Company dossier | `services/company/operations/{migrations,services,handlers,tests}/ai-governance-dossier.*` |
| Agent read/profile | `apps/cosa/capabilities/ai_governance_read.py`, specs/maps/seed, Company mapping |
| Catalog/skill | shared contracts/generators, `015_ai_governance_startup_profile.*`, `skillpacks/executive/caio-advisor/**` |
| Proof/UI | Control/Company/Agent/Flutter tests and `tests/e2e/test_caio_ai_governance_profile.py` |

### Task 1: Publish a signed, redacted Control Plane snapshot port

**Files:** Create/modify Control Plane service/handler/tests listed above; create Company client adapter test.

**Interfaces:** `getAiGovernanceSnapshot({workspaceId, projectId, policyRefs, evaluatorRefs})` returns `{workspaceId, projectId, policy: {id, version, definitionHash}, evaluators, status, observedAt, signature}` and exposes no update operation.

- [ ] **Step 1: Write failing tenancy/integrity tests**

```ts
it("rejects foreign project, stale policy hash and any write request", async () => {
  await expect(getAiGovernanceSnapshot(foreignContext, input)).rejects.toMatchObject({ code: "permission_denied" });
  await expect(getAiGovernanceSnapshot(ctx, { ...input, policyHash: "stale" })).rejects.toMatchObject({ code: "failed_precondition" });
});
```

- [ ] **Step 2: Run red**

```bash
cd services/cosa && npx vitest run tests/ai-governance-snapshot.test.ts
```

Expected: FAIL until a server-authorized, immutable snapshot port exists. Do not call an admin/policy mutation endpoint from Company or Agent code.

- [ ] **Step 3: Implement read-only snapshot boundary**

Use Control Plane's canonical registry/policy authority and service-to-service delegation; verify workspace/project binding, exact hashes and timestamp before signing bounded metadata. Handler is internal unless a separately authenticated client route is needed; it has no mutable verb.

- [ ] **Step 4: Verify and commit**

```bash
cd services/cosa && npx vitest run tests/ai-governance-snapshot.test.ts && npm run typecheck
git add services/cosa
git commit -m "feat(ai-governance): expose signed advisory snapshot"
```

### Task 2: Persist a Project AI Governance Dossier as references only

**Files:** Create Company Operations migration/service/handler/tests and signed snapshot client adapter.

**Interfaces:** `appendAiGovernanceRevision(ctx, {projectId, snapshot, riskSignals, sourceRefs})` validates signature/hash and returns `{dossierId, revision, snapshotRef, status}`; `readAiGovernanceSnapshot(ctx, projectId)` returns redacted metadata.

- [ ] **Step 1: Write red source tests**

```ts
it("rejects unsigned snapshot, raw prompt and cross-project source", async () => {
  await expect(appendAiGovernanceRevision(ctx, { ...draft, snapshot: unsigned })).rejects.toMatchObject({ code: "failed_precondition" });
  await expect(appendAiGovernanceRevision(ctx, { ...draft, prompt: "raw" } as never)).rejects.toMatchObject({ code: "invalid_argument" });
});
```

- [ ] **Step 2: Implement additive/CAS validation and run green**

```bash
cd services/company && npx vitest run operations/tests/ai-governance-dossier.test.ts && npm run typecheck
```

Persist only reference/hash/status/time, enforce signed origin and append audit. Founder confirms a governance decision; no agent can write the dossier as a confirmation.

- [ ] **Step 3: Commit**

```bash
git add services/company/operations
git commit -m "feat(ai-governance): add project governance dossier"
```

### Task 3: Register AI Governance and CAIO specs

**Files:** Create `apps/cosa/capabilities/ai_governance_read.py`/test; modify agent specs/maps/seed, Company mapping/tests.

**Interfaces:** `ai.governance.read`; `COSA_AI_GOVERNANCE_AGENT_SPEC = cosa.agents.ai_governance@1.0.0/L1_PROPOSE`; `COSA_EXECUTIVE_CAIO_AGENT_SPEC = cosa.executive.caio@1.0.0/L1_PROPOSE` with `capability_refs=[]`.

- [ ] **Step 1: Write red capability/spec test**

```python
async def test_caio_cannot_change_policy_or_read_foreign_snapshot(gateway):
    assert EXECUTIVE_AGENT_SPECS["cosa.executive.caio"].capability_refs == []
    with pytest.raises(CapabilityDenied):
        await gateway.execute(ai_governance_request(project_id="foreign"))
```

- [ ] **Step 2: Implement only exact read mapping**

Register the one Project-bound read capability. Add explicit maps/seed and calculate actual hash before writing Company ID/version/hash values. Do not add an `ai_governance` default chat alias or generic provider client.

- [ ] **Step 3: Verify/commit**

```bash
PYTHONPATH=packages:. .venv/bin/python -m pytest apps/cosa/tests/test_ai_governance_profile.py -v
cd services/company && npx vitest run operations/tests/ai-member.test.ts
git add apps/cosa services/company/operations
git commit -m "feat(ai-governance): add pinned AI Governance and CAIO specs"
```

### Task 4: Catalog, advisory skill and end-to-end Board proof

**Files:** shared source/generated contracts/generator/tests; `services/company/operations/migrations/015_ai_governance_startup_profile.{up,down}.sql`; `skillpacks/executive/caio-advisor/**`; Board/Hologram Hub/E2E tests.

**Interfaces:** `ai_governance: TEMPLATE/READY`; `caio: READY`; `skillpack:executive/caio-advisor@1.0.0`; role list/mutation semantics remain existing Company API.

- [ ] **Step 1: Write red E2E**

```python
async def test_caio_requires_active_profile_and_verified_current_snapshot(client):
    assert (await client.activate_role("caio", profile_template)).code == "AI_GOVERNANCE_PROFILE_NOT_ACTIVE"
    assert (await client.deliberate("caio", stale_or_unsigned_snapshot)).code == "AI_GOVERNANCE_EVIDENCE_REQUIRED"
```

- [ ] **Step 2: Implement source truth**

Add catalog entries/readiness only after Tasks 1–3 pass; generator rejects `caio READY` without `ai_governance READY`. Migration backfills templates only and down rejects activated/frame-referenced rows. Skillpack asks for policy/evaluator hash and evidence time, clearly separates recommendation from control-plane change, and forbids automated promotion/pinning. Flutter maps Company `runtimeReadiness`, `requiredProfileKey`, display state and reloads after receipt.

- [ ] **Step 3: Run verification and commit**

```bash
node scripts/gen-startup-team-profiles.mjs && node scripts/gen-executive-advisor-roles.mjs
make contracts-check && make skillpacks-validate
make services-test-cosa && make services-test-company && make agent-test && make frontend-api-contract-check
PYTHONPATH=packages:. .venv/bin/python -m pytest tests/e2e/test_caio_ai_governance_profile.py -v
git add shared/contracts scripts services/cosa services/company/operations apps/cosa skillpacks/executive/caio-advisor frontend tests/e2e
git commit -m "feat(executive-board): activate CAIO advisory path"
```

### Task 5: Portfolio closeout gate

**Files:** Modify `docs/superpowers/specs/2026-09-11-executive-advisory-board-completion-and-agent-platform-restructuring-design.md` only after all preceding role E2E evidence is present; add consolidated E2E runbook.

- [ ] **Step 1: Create red no-auto-activation regression**

```python
async def test_new_project_has_all_new_profiles_as_templates_and_no_new_executive_roles_active(client):
    roster = await client.create_project_and_list_team()
    assert all(item.mode == "TEMPLATE" for item in roster if item.profile_key in {"sales", "coding", "product", "people", "security", "legal", "data", "ai_governance"})
    assert not await client.list_active_roles(excluding={"cfo", "cmo", "cco", "coo", "chief_of_staff"})
```

- [ ] **Step 2: Run broad evidence, then update status honestly**

```bash
make verify
make e2e-cross-plane-smoke
git diff --check
```

Record each role as `VERIFIED` only if its process E2E has a successful exit; record blocked environments as `UNVERIFIED` with command/error. Never change design status just because static checks pass.

- [ ] **Step 3: Commit closeout evidence**

```bash
git add docs/superpowers/specs tests/e2e
git commit -m "docs(executive-board): record remaining role evidence"
```
