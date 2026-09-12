# CISO Security Profile + Executive Activation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` (or `superpowers:subagent-driven-development`) and execute tasks in order.

**Goal:** Tạo `security` profile từ Security Posture Dossier không chứa secret, rồi kích hoạt CISO advisor cho threat-model/privacy/compliance gap assessment có provenance.

**Architecture:** Company owns Project security posture revisions and remediation proposal status; Agent Platform gets only redacted control metadata, severity and source references. CISO has no scanner, shell, credential, policy-write or incident-response capability; it is an advisory lens over evidence already ingested by a governed path.

**Tech Stack:** Company Operations, agent capability/registry, shared contracts, skillpack, Flutter, Vitest/pytest/disposable E2E.

**Spec:** `docs/superpowers/specs/2026-09-11-executive-advisory-board-completion-and-agent-platform-restructuring-design.md`.

## Global Constraints

- Reject passwords, tokens, private keys, full request headers, raw vulnerability payloads and infrastructure topology from all dossier inputs/logs.
- CISO may propose risk/control gaps only; it cannot scan a target, rotate secret, disable user, patch/deploy or declare compliance/certification.
- Security evidence requires Project scope and classification. Cross-project, stale or unclassified evidence produces `SECURITY_EVIDENCE_REQUIRED`, never a guessed model conclusion.

## File structure

| Unit | Files |
| --- | --- |
| Posture record | `services/company/operations/{migrations,services,handlers,tests}/security-posture.*` |
| Read/spec | `apps/cosa/capabilities/security_posture_read.py`, agent specs/maps/seed |
| Catalog | shared contracts/generators, `012_security_startup_profile.*` |
| Advisory/proof | `skillpacks/executive/ciso-advisor/**`, Hologram Hub tests, `tests/e2e/test_ciso_security_profile.py` |

### Task 1: Create secret-free Security Posture Dossier

**Files:** Create the listed migration/service/handler/tests.

**Interfaces:** `appendSecurityPostureRevision(ctx, {projectId, controls, findings, evidenceRefs})` and `readSecurityPostureSnapshot(ctx, projectId)` return `{revision, severity, controlStates, evidenceRefs}`.

- [ ] **Step 1: Write red rejection/isolation cases**

```ts
it("rejects secret-bearing input and foreign workspace snapshot", async () => {
  await expect(appendSecurityPostureRevision(ctx, { ...draft, token: "secret" } as never)).rejects.toMatchObject({ code: "invalid_argument" });
  await expect(readSecurityPostureSnapshot(foreignCtx, projectId)).rejects.toMatchObject({ code: "permission_denied" });
});
```

- [ ] **Step 2: Implement and run green**

```bash
cd services/company && npx vitest run operations/tests/security-posture.test.ts && npm run typecheck
```

Fixed metadata schema, append-only revision/CAS, source provenance and audit only; no target/scanner integration.

- [ ] **Step 3: Commit**

```bash
git add services/company/operations && git commit -m "feat(security): add secret-free posture dossier"
```

### Task 2: Register Security/CISO with no effect capability

**Files:** Create read capability/test; modify specs/maps/seed/Company mapping tests.

**Interfaces:** `security.posture.read`; `cosa.agents.security@1.0.0/L1_PROPOSE`; `cosa.executive.ciso@1.0.0/L1_PROPOSE` with `capability_refs=[]`.

- [ ] **Step 1: Red test**

```python
def test_ciso_is_capability_empty_and_security_cannot_scan_or_access_secret():
    assert EXECUTIVE_AGENT_SPECS["cosa.executive.ciso"].capability_refs == []
    assert "security.scan" not in AGENT_PROFILE_SPECS["security"].capability_refs
```

- [ ] **Step 2: Implement exact pins, run and commit**

```bash
PYTHONPATH=packages:. .venv/bin/python -m pytest apps/cosa/tests/test_security_profile.py -v
cd services/company && npx vitest run operations/tests/ai-member.test.ts
git add apps/cosa services/company/operations && git commit -m "feat(security): add pinned Security and CISO specs"
```

### Task 3: Release catalog truth and prove Board boundary

**Files:** shared contracts/generators/tests; `012_security_startup_profile.{up,down}.sql`; CISO skillpack; Company/Flutter/E2E tests.

- [ ] **Step 1: Add red E2E**

```python
async def test_ciso_requires_active_security_and_classified_snapshot(client):
    assert (await client.activate_role("ciso", security_template)).code == "SECURITY_PROFILE_NOT_ACTIVE"
    assert (await client.deliberate("ciso", unclassified_evidence)).code == "SECURITY_EVIDENCE_REQUIRED"
```

- [ ] **Step 2: Implement source changes**

Add `security: TEMPLATE/READY`, `ciso: READY`, generator invariant, template-only backfill and protected down. Skillpack states it is not a security certification or incident response, asks for evidence/scope/revision and reports uncertainty. UI reloads Company response.

- [ ] **Step 3: Validate/commit**

```bash
node scripts/gen-startup-team-profiles.mjs && node scripts/gen-executive-advisor-roles.mjs
make contracts-check && make skillpacks-validate && make services-test-company
PYTHONPATH=packages:. .venv/bin/python -m pytest tests/e2e/test_ciso_security_profile.py -v
git add shared/contracts scripts services/company/operations apps/cosa skillpacks/executive/ciso-advisor frontend tests/e2e
git commit -m "feat(executive-board): activate CISO advisory path"
```
