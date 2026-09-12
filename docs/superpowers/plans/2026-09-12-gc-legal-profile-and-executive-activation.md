# General Counsel Legal Profile + Executive Activation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` (or `superpowers:subagent-driven-development`) and execute tasks in order.

**Goal:** Bổ sung `legal` functional profile qua Legal Issue Dossier Project-bound và mở `gc` advisor để issue-spotting/escalation, không tạo tư vấn pháp lý có thẩm quyền hay thay đổi Company legal records.

**Architecture:** Finance-Legal remains business truth for legal entity/applicability. A Company Operations dossier holds only Project-scoped questions, applicable-record references, risk category, provenance and Founder decision status. Legal profile reads the redacted snapshot; GC is capability-empty and labels every output “not legal advice; seek qualified counsel”.

**Tech Stack:** Company Finance-Legal + Operations, Python registry/capability, contracts/generators, skillpacks, Flutter, Vitest/pytest/process E2E.

**Spec:** `docs/superpowers/specs/2026-09-11-executive-advisory-board-completion-and-agent-platform-restructuring-design.md`.

## Global Constraints

- GC cannot create/alter legal entity, sign/approve a contract, set legal applicability, file/regulator-contact, retain counsel or make a legal conclusion. Existing finance-legal services remain authoritative.
- Do not project contract bodies, personal data or privileged advice; retain a classification, source reference, jurisdiction/applicability status and redacted question only.
- `legal`/`gc` are READY only when source reference integrity and tenant/project E2E pass; missing applicability is an explicit unknown/escalation.

## File structure

| Unit | Files |
| --- | --- |
| Dossier | `services/company/operations/{migrations,services,handlers,tests}/legal-issue-dossier.*` |
| Read/profile | `apps/cosa/capabilities/legal_issue_read.py`, agent specs/maps/seed, Company `ai-member.service.ts` |
| Catalog/skill | shared contracts/generators, `013_legal_startup_profile.*`, `skillpacks/executive/gc-advisor/**` |
| Proof | Board/Hologram Hub tests, `tests/e2e/test_gc_legal_profile.py` |

### Task 1: Add a non-authoritative Legal Issue Dossier

**Files:** Create listed Operations migration/service/handler/tests; use existing Finance-Legal read service, not SQL cross-schema access.

**Interfaces:** `createLegalIssueDossier(ctx, {projectId, issueCategory, legalRecordRefs, redactedQuestion})`; `readLegalIssueSnapshot(ctx, projectId)` returns `{revision, issueCategory, applicabilityStatus, sourceRefs}`.

- [ ] **Step 1: Write failing authority tests**

```ts
it("rejects foreign/legal-body input and cannot change legal applicability", async () => {
  await expect(createLegalIssueDossier(foreignCtx, draft)).rejects.toMatchObject({ code: "permission_denied" });
  await expect(createLegalIssueDossier(ctx, { ...draft, contractBody: "private" } as never)).rejects.toMatchObject({ code: "invalid_argument" });
});
```

- [ ] **Step 2: Implement append-only reference record and green run**

```bash
cd services/company && npx vitest run operations/tests/legal-issue-dossier.test.ts finance-legal/tests/legal-applicability-integrity.test.ts && npm run typecheck
```

Validate referenced legal records through a service port, maintain CAS/audit and surface unavailable applicability as an explicit state.

- [ ] **Step 3: Commit**

```bash
git add services/company/operations services/company/finance-legal && git commit -m "feat(legal): add project legal issue dossier"
```

### Task 2: Register read-only Legal and GC specs

**Files:** Create `legal_issue_read.py` and tests; modify agent registry/map/seed and Company mappings/tests.

**Interfaces:** `legal.issue.read`; `cosa.agents.legal@1.0.0/L1_PROPOSE`; `cosa.executive.gc@1.0.0/L1_PROPOSE` capability-empty.

- [ ] **Step 1: Red test**

```python
async def test_legal_profile_has_no_write_and_gc_has_no_capability(gateway):
    assert EXECUTIVE_AGENT_SPECS["cosa.executive.gc"].capability_refs == []
    with pytest.raises(CapabilityDenied): await gateway.execute(legal_request(project_id="foreign"))
```

- [ ] **Step 2: Implement pins and commit**

```bash
PYTHONPATH=packages:. .venv/bin/python -m pytest apps/cosa/tests/test_legal_profile.py -v
cd services/company && npx vitest run operations/tests/ai-member.test.ts
git add apps/cosa services/company/operations && git commit -m "feat(legal): add pinned Legal and GC specs"
```

### Task 3: Catalog/skill/activation release proof

**Files:** shared contracts/generators/tests; `013_legal_startup_profile.{up,down}.sql`; GC skillpack; Board/Flutter/E2E tests.

- [ ] **Step 1: Red E2E**

```python
async def test_gc_requires_active_legal_and_never_resolves_unknown_applicability(client):
    assert (await client.activate_role("gc", legal_template)).code == "LEGAL_PROFILE_NOT_ACTIVE"
    assert (await client.deliberate("gc", unknown_applicability)).code == "LEGAL_EVIDENCE_REQUIRED"
```

- [ ] **Step 2: Implement and verify**

Set `legal: TEMPLATE/READY`, `gc: READY`; generator enforces pairing; migration is template-only with active/frame-referenced down guard. Skill requires jurisdiction/source/revision and legal-counsel caveat. Flutter maps/reloads Company truth.

```bash
node scripts/gen-startup-team-profiles.mjs && node scripts/gen-executive-advisor-roles.mjs
make contracts-check && make skillpacks-validate && make services-test-company
PYTHONPATH=packages:. .venv/bin/python -m pytest tests/e2e/test_gc_legal_profile.py -v
git add shared/contracts scripts services/company/operations apps/cosa skillpacks/executive/gc-advisor frontend tests/e2e
git commit -m "feat(executive-board): activate GC advisory path"
```
