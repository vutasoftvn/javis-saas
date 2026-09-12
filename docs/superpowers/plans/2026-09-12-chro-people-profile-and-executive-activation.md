# CHRO People Profile + Executive Activation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` (or `superpowers:subagent-driven-development`) and execute tasks in order.

**Goal:** Tạo `people` profile với People Risk Dossier tối thiểu, privacy-first và mở `chro` chỉ để tư vấn organizational design, hiring process và people risk.

**Architecture:** Company owns Project People Risk Dossier: redacted workforce capacity/risk metadata, source provenance and Founder-reviewed revisions. Agent Platform reads only that snapshot. CHRO is a capability-empty advisor, never an HR system, applicant tracker, performance evaluator or hiring decision-maker.

**Tech Stack:** Company Operations/Drizzle/Encore, Python agent/capability registry, shared contracts, skillpacks, Flutter, Vitest/pytest/E2E.

**Spec:** `docs/superpowers/specs/2026-09-11-executive-advisory-board-completion-and-agent-platform-restructuring-design.md`.

## Global Constraints

- Never store/retrieve CVs, compensation, protected characteristics, performance notes, health data or contact PII in this dossier, skillpack, board frame or model prompt.
- A founder alone confirms a people policy/decision. CHRO can draft a rubric/risk question but cannot rank candidates, change a WorkforceMember, invite/terminate anyone or message a person.
- `people` and `chro` only become READY after Project isolation, PII rejection and Founder-confirmation process tests pass.

## File structure

| Unit | Files |
| --- | --- |
| Business record | `services/company/operations/{migrations,services,handlers,tests}/people-risk-dossier.*` |
| Read capability/specs | `apps/cosa/capabilities/people_risk_read.py`, `apps/cosa/agents/{specs,agent_profile_specs,seed}.py` |
| Identity/catalog | Company `ai-member.service.ts`, shared contracts/generators/generated files, `011_people_startup_profile.*` |
| Advisory/proof | `skillpacks/executive/chro-advisor/**`, Hologram Hub tests, `tests/e2e/test_chro_people_profile.py` |

### Task 1: Build a redacted People Risk Dossier

**Files:** Create the business record migration/service/handler/tests above.

**Interfaces:** `createPeopleRiskDossier(ctx, {projectId, capacityBands, riskSignals, sourceRefs})`; `appendPeopleRiskRevision(ctx, dossierId, expectedVersion, draft)`; `readPeopleRiskSnapshot(ctx, projectId)` returns only classified aggregate data.

- [ ] **Step 1: Write failing privacy/isolation tests**

```ts
it("rejects PII fields and foreign-project reads", async () => {
  await expect(createPeopleRiskDossier(ctx, { ...draft, candidateEmail: "a@b.test" } as never))
    .rejects.toMatchObject({ code: "invalid_argument" });
  await expect(readPeopleRiskSnapshot(foreignCtx, projectId)).rejects.toMatchObject({ code: "permission_denied" });
});
```

- [ ] **Step 2: Run red, implement additive CAS record, run green**

```bash
cd services/company && npx vitest run operations/tests/people-risk-dossier.test.ts && npm run typecheck
```

Validate a fixed allowlist schema, append immutable revisions, audit Founder confirmation and return no raw attachments. Do not create an HR CRUD surface.

- [ ] **Step 3: Commit**

```bash
git add services/company/operations
git commit -m "feat(people): add redacted people risk dossier"
```

### Task 2: Add explicit People/CHRO specs

**Files:** Create read capability/test; modify agent specs/maps/seed, Company mapping/tests.

**Interfaces:** `people.risk.read`; `COSA_PEOPLE_AGENT_SPEC = cosa.agents.people@1.0.0/L1_PROPOSE`; `COSA_EXECUTIVE_CHRO_AGENT_SPEC = cosa.executive.chro@1.0.0/L1_PROPOSE` with empty capabilities.

- [ ] **Step 1: Write red spec test**

```python
async def test_people_profile_cannot_read_pii_and_chro_cannot_mutate_workforce(gateway):
    assert AGENT_PROFILE_SPECS["people"].id == "cosa.agents.people"
    assert EXECUTIVE_AGENT_SPECS["cosa.executive.chro"].capability_refs == []
    with pytest.raises(CapabilityDenied): await gateway.execute(people_request(project_id="foreign"))
```

- [ ] **Step 2: Implement exact maps and run green**

Use only `people.risk.read`; compute Python hash then copy literal ID/version/hash into Company maps. Add no behavioral keyword fallback outside known profile routing.

```bash
PYTHONPATH=packages:. .venv/bin/python -m pytest apps/cosa/tests/test_people_profile.py -v
cd services/company && npx vitest run operations/tests/ai-member.test.ts
```

- [ ] **Step 3: Commit**

```bash
git add apps/cosa services/company/operations
git commit -m "feat(people): add pinned People and CHRO specs"
```

### Task 3: Catalog, skillpack and activation evidence

**Files:** shared contracts/generators/tests; `011_people_startup_profile.{up,down}.sql`; `skillpacks/executive/chro-advisor/**`; Company/Flutter/E2E tests.

- [ ] **Step 1: Write red readiness test**

```python
async def test_chro_needs_active_people_profile_and_never_auto_activates(client):
    assert (await client.activate_role("chro", people_template)).code == "PEOPLE_PROFILE_NOT_ACTIVE"
    assert (await client.role("chro")).display_state == "UNAVAILABLE"
```

- [ ] **Step 2: Implement and regenerate**

Add `people: TEMPLATE/READY`, `chro: READY`, generator mismatch guard, safe migration backfill/down guard and skillpack requiring aggregate source/revision plus discrimination/privacy caveats. Reuse Board activation; Flutter reloads Company truth after receipt.

- [ ] **Step 3: Verify/commit**

```bash
node scripts/gen-startup-team-profiles.mjs && node scripts/gen-executive-advisor-roles.mjs
make contracts-check && make skillpacks-validate && make services-test-company
PYTHONPATH=packages:. .venv/bin/python -m pytest tests/e2e/test_chro_people_profile.py -v
git add shared/contracts scripts services/company/operations apps/cosa skillpacks/executive/chro-advisor frontend tests/e2e
git commit -m "feat(executive-board): activate CHRO advisory path"
```
