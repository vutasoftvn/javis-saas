# VPE Coding Profile + Executive Activation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` (or `superpowers:subagent-driven-development`) and execute tasks in order.

**Goal:** Bổ sung `coding` functional profile chỉ dựa trên sandboxed executor có grant/receipt, rồi mở `vpe` advisory role để đánh giá feasibility/release risk mà không cấp shell, deploy hay write quyền cho Board.

**Architecture:** `safe-local-executor` là executor duy nhất; Coding profile có thể đọc manifests, bounded receipts và artifact metadata qua capability gateway, không có API generic command. VPE là AgentSpec riêng, capability-empty, pin `vpe-advisor` và snapshot Coding assignment. Company giữ Project activation/frame; node receipt không thể tự hoàn tất business action hay làm role active.

**Tech Stack:** Python AgentSpec/Capability Gateway, Control Plane runtime node policy, Company Startup Team/Board, shared generators, skillpacks, Flutter, pytest/Vitest/disposable-process E2E.

**Spec:** `docs/superpowers/specs/2026-09-11-executive-advisory-board-completion-and-agent-platform-restructuring-design.md`; predecessor `docs/superpowers/plans/2026-09-10-cosa-safe-local-executor.md`.

## Global Constraints

- Do not expose `run(command: str)`, arbitrary repository path, mount, network target, environment variable, provider token or raw stderr to Coding/VPE.
- Grant must bind workspace, Project run/tool-call/checkpoint, node, capability, template, canonical input hash, manifest hash, expiry and one-time nonce; revoked/mismatched grant fails closed.
- Coding/VPE cannot deploy, merge, alter runtime-node policy, write business data or make network calls. Any future effect goes through an independently governed capability/approval, outside this plan.
- `coding` becomes READY only after process proof of sandbox containment, receipt binding and cross-workspace denial. Catalog status or a green unit mock is insufficient.

## File structure

| Unit | Files |
| --- | --- |
| Executor entry proof | `packages/agent/local_executor/**`, `apps/cosa/{local_executor,runtime_node}/**`, predecessor E2E |
| Profile identity | `apps/cosa/agents/{specs,agent_profile_specs,seed}.py`, `services/company/operations/services/ai-member.service.ts` |
| Catalog/board | shared contracts, generators, `services/company/operations/migrations/009_coding_startup_profile.*` |
| Advisory | `skillpacks/executive/vpe-advisor/{manifest.yaml,SKILL.md}` |
| Evidence | Agent/Company/Flutter tests and `tests/e2e/test_vpe_coding_profile.py` |

### Task 1: Prove a safe Engineering evidence boundary

**Files:** Add/modify predecessor executor process test and `tests/e2e/test_vpe_coding_profile.py`.

**Interfaces:** Consumes a verified `LocalExecutionReceipt` with `grant_id`, `workspace_id`, `tool_call_id`, `status`, bounded artifact metadata and `manifest_hash`. Produces `EngineeringEvidenceSnapshot` without command text, secrets or source contents.

- [ ] **Step 1: Write red process cases**

```python
async def test_vpe_evidence_rejects_foreign_or_unbound_receipt(client):
    assert (await client.engineering_evidence(receipt_for("ws-b"))).code == "CROSS_WORKSPACE_ACCESS_DENIED"
    assert (await client.engineering_evidence(receipt_for("ws-a", tool_call_id="other"))).code == "RECEIPT_BINDING_MISMATCH"
```

- [ ] **Step 2: Run red**

```bash
PYTHONPATH=packages:. .venv/bin/python -m pytest tests/e2e/test_vpe_coding_profile.py -v
```

Expected: FAIL until safe executor receipts are durable, signed/bound and exposed only through a read-only projection.

- [ ] **Step 3: Implement projection boundary**

Use the predecessor's receipt repository and capability gateway; add a read-only projection that validates all binding fields and returns only status, limits, hashed artifact IDs and manifest/version. Do not add an executor transport endpoint or allow a model to nominate a template.

- [ ] **Step 4: Verify and commit entry proof**

```bash
make agent-test
PYTHONPATH=packages:. .venv/bin/python -m pytest tests/e2e/test_vpe_coding_profile.py -v
git add packages/agent apps/cosa tests/e2e
git commit -m "test(coding): prove bounded engineering evidence"
```

### Task 2: Register Coding and VPE exact-hash specifications

**Files:** Modify `apps/cosa/agents/{specs,agent_profile_specs,seed}.py`, Company `ai-member.service.ts`; create `apps/cosa/tests/test_coding_vpe_specs.py`; modify Company identity tests.

**Interfaces:** Produces `COSA_CODING_AGENT_SPEC` (`cosa.agents.coding`, `1.0.0`, `L1_PROPOSE`) and `COSA_EXECUTIVE_VPE_AGENT_SPEC` (`cosa.executive.vpe`, `1.0.0`, `L1_PROPOSE`, `capability_refs=[]`).

- [ ] **Step 1: Write failing registry tests**

```python
def test_vpe_is_advisory_only_and_coding_cannot_receive_generic_shell():
    assert AGENT_PROFILE_SPECS["coding"].id == "cosa.agents.coding"
    assert EXECUTIVE_AGENT_SPECS["cosa.executive.vpe"].capability_refs == []
    assert "local.shell.run" not in AGENT_PROFILE_SPECS["coding"].capability_refs
```

- [ ] **Step 2: Run red**

```bash
PYTHONPATH=packages:. .venv/bin/python -m pytest apps/cosa/tests/test_coding_vpe_specs.py -v
```

- [ ] **Step 3: Implement explicit mappings**

Give Coding only the read-only engineering-evidence capability from Task 1. Add exact mappings/seed placement and regenerated literal Company ID/version/hash; no founder-assistant alias or prefix routing. Executive VPE reads only the serialized board context, not the node or runtime policy directly.

- [ ] **Step 4: Verify and commit**

```bash
PYTHONPATH=packages:. .venv/bin/python -m pytest apps/cosa/tests/test_coding_vpe_specs.py -v
cd services/company && npx vitest run operations/tests/ai-member.test.ts && npm run typecheck
git add apps/cosa/agents apps/cosa/tests services/company/operations
git commit -m "feat(coding): add pinned coding and VPE specs"
```

### Task 3: Make catalog and VPE advisory content truthful

**Files:** Modify shared contracts/generator/tests; create `services/company/operations/migrations/009_coding_startup_profile.{up,down}.sql` and `skillpacks/executive/vpe-advisor/{manifest.yaml,SKILL.md}`.

**Interfaces:** Produces `coding: TEMPLATE/READY`, `vpe: READY`, and `skillpack:executive/vpe-advisor@1.0.0`.

- [ ] **Step 1: Write red catalog test**

```python
def test_vpe_ready_requires_coding_profile_and_own_skillpin():
    assert STARTUP_TEAM_PROFILES["coding"].runtime_readiness == "READY"
    assert EXECUTIVE_ROLE_CATALOG["vpe"].runtime_readiness == "READY"
    assert EXECUTIVE_ROLE_CATALOG["vpe"].required_skill_pins == ("skillpack:executive/vpe-advisor@1.0.0",)
```

- [ ] **Step 2: Implement catalog/migration/skill**

The generator rejects `vpe: READY` unless `coding` exists and is READY. Migration backfills only missing Coding templates and rejects down when non-template/board reference evidence exists. VPE skill requires provenance-bearing receipt/manifest, calls out unverified build/test/deploy assertions, and explicitly forbids deployment or repository mutation.

- [ ] **Step 3: Regenerate, validate, commit**

```bash
node scripts/gen-startup-team-profiles.mjs && node scripts/gen-executive-advisor-roles.mjs
make contracts-check && make skillpacks-validate
git add shared/contracts scripts services/company/operations/migrations skillpacks/executive/vpe-advisor apps/cosa/agents services/company/shared/contracts
git commit -m "feat(executive-board): make VPE coding-ready"
```

### Task 4: Prove Founder activation and UI state

**Files:** Company role/deliberation tests; Hologram Hub model/service/controller/view and tests; `tests/e2e/test_vpe_coding_profile.py`.

- [ ] **Step 1: Add red activation test**

```python
async def test_vpe_requires_active_coding_and_never_activates_from_receipt(client):
    assert (await client.activate_role("vpe", coding_template)).code == "CODING_PROFILE_NOT_ACTIVE"
    await client.publish_engineering_receipt(bound_receipt)
    assert (await client.role("vpe")).display_state == "AVAILABLE_NOT_ACTIVATED"
```

- [ ] **Step 2: Implement only existing activation/frame wiring and authoritative reload**

Use the existing Company activation and deliberation services. Flutter renders Company `displayState`/reason and reloads GET after a mutation receipt; never infer a role from executor success.

- [ ] **Step 3: Run release evidence and commit**

```bash
make services-test-company && make agent-test && make frontend-api-contract-check
cd frontend && flutter test test/modules/hologram_hub
git add services/company/operations frontend tests/e2e
git commit -m "test(executive-board): prove VPE activation boundary"
```
