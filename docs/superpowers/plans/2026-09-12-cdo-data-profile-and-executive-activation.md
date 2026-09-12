# CDO Data Profile + Executive Activation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` (or `superpowers:subagent-driven-development`) and execute tasks in order.

**Goal:** Tạo `data` profile dựa trên Data Asset & Quality Dossier và mở CDO advisor cho governance, quality, rights-management và knowledge-integrity assessment.

**Architecture:** Company records catalog metadata, owner, classification, retention/right status, quality checks and Project provenance. Agent Platform reads a bounded snapshot only; it never queries raw Company tables, embeddings, Vault raw files or personal data. CDO advisor is capability-empty and cannot change classification, ACL, retention or deletion state.

**Tech Stack:** Company Operations/metadata contracts, Agent Platform read capability, shared generators, skillpacks, Flutter, Vitest/pytest/E2E.

**Spec:** `docs/superpowers/specs/2026-09-11-executive-advisory-board-completion-and-agent-platform-restructuring-design.md`.

## Global Constraints

- Metadata is not a backdoor to data: deny values, field samples, embeddings, raw file URI, API credentials and cross-Project lineage.
- Only authorized founder data stewards confirm classification/retention/access changes; CDO proposes a gap/remediation draft, never mutates ACL or deletes records.
- Missing provenance/classification must be returned as missing, not inferred by LLM.

## File structure

| Unit | Files |
| --- | --- |
| Business dossier | `services/company/operations/{migrations,services,handlers,tests}/data-governance-dossier.*` |
| Read/profile | `apps/cosa/capabilities/data_governance_read.py`, agent specs/maps/seed, Company mapping |
| Catalog | shared contracts/generators, `014_data_startup_profile.*` |
| Advisory/proof | `skillpacks/executive/cdo-advisor/**`, Hologram Hub tests, `tests/e2e/test_cdo_data_profile.py` |

### Task 1: Add metadata-only Data Governance Dossier

**Files:** Create listed migration/service/handler/tests.

**Interfaces:** `appendDataGovernanceRevision(ctx, {projectId, assets, classifications, qualitySignals, sourceRefs})`; `readDataGovernanceSnapshot(ctx, projectId)` returns `{revision, assets: [{assetId, classification, qualityStatus}], sourceRefs}`.

- [ ] **Step 1: Write red data-boundary test**

```ts
it("rejects raw values and hides foreign-project metadata", async () => {
  await expect(appendDataGovernanceRevision(ctx, { ...draft, fieldSample: "PII" } as never)).rejects.toMatchObject({ code: "invalid_argument" });
  await expect(readDataGovernanceSnapshot(foreignCtx, projectId)).rejects.toMatchObject({ code: "permission_denied" });
});
```

- [ ] **Step 2: Implement additive/CAS record, run, commit**

```bash
cd services/company && npx vitest run operations/tests/data-governance-dossier.test.ts && npm run typecheck
git add services/company/operations && git commit -m "feat(data): add metadata governance dossier"
```

### Task 2: Register Data/CDO exact identity

**Files:** Create read capability/test; modify registry/seed/maps/Company mapping tests.

**Interfaces:** `data.governance.read`; `cosa.agents.data@1.0.0/L1_PROPOSE`; `cosa.executive.cdo@1.0.0/L1_PROPOSE`, capability-empty.

- [ ] **Step 1: Red test, implement, green run**

```python
def test_cdo_cannot_read_raw_data_or_change_governance():
    assert EXECUTIVE_AGENT_SPECS["cosa.executive.cdo"].capability_refs == []
    assert "data.asset.raw.read" not in AGENT_PROFILE_SPECS["data"].capability_refs
```

```bash
PYTHONPATH=packages:. .venv/bin/python -m pytest apps/cosa/tests/test_data_profile.py -v
cd services/company && npx vitest run operations/tests/ai-member.test.ts
```

- [ ] **Step 2: Commit**

```bash
git add apps/cosa services/company/operations && git commit -m "feat(data): add pinned Data and CDO specs"
```

### Task 3: Catalog, advisory and process proof

**Files:** shared contracts/generators/tests; `014_data_startup_profile.{up,down}.sql`; CDO skillpack; board/Flutter/E2E tests.

- [ ] **Step 1: Add red E2E**

```python
async def test_cdo_requires_active_data_and_classified_metadata(client):
    assert (await client.activate_role("cdo", data_template)).code == "DATA_PROFILE_NOT_ACTIVE"
    assert (await client.deliberate("cdo", unclassified_asset)).code == "DATA_EVIDENCE_REQUIRED"
```

- [ ] **Step 2: Implement/regenerate/validate/commit**

Add `data: TEMPLATE/READY`, `cdo: READY`, pair invariant, protected template backfill and skill requiring classification/provenance/quality status. Map/reload state in Flutter.

```bash
node scripts/gen-startup-team-profiles.mjs && node scripts/gen-executive-advisor-roles.mjs
make contracts-check && make skillpacks-validate && make services-test-company
PYTHONPATH=packages:. .venv/bin/python -m pytest tests/e2e/test_cdo_data_profile.py -v
git add shared/contracts scripts services/company/operations apps/cosa skillpacks/executive/cdo-advisor frontend tests/e2e
git commit -m "feat(executive-board): activate CDO advisory path"
```
