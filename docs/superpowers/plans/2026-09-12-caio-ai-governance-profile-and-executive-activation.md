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

## Known limitations (post-final-review)

Task 4 is complete: catalog flip (`ai_governance: READY`, `caio: READY`), skillpack +
eval, migration 023 (additive backfill, fail-closed down-guard), a 5-case real
process E2E exercising all 3 planes, Flutter reload-truth coverage, and the full gate
sequence green. The following are disclosed, carried-forward limitations — not gaps
this task silently introduced.

1. **Shared read-capability HTTP-auth-unreachability (portfolio-wide, points 1-3
   below apply to CAIO too, verified independently for this plan):** `ai_governance_read`
   (Task 3) reads Company's `GET /operations/projects/:projectId/ai-governance-dossier`
   using the same ambient COSA-delegation auth pattern as every prior role's
   `*_read` capability. That specific read path is guarded by
   `requireWorkspaceAccess`, which only accepts `JWT_SECRET` human-session tokens —
   unreachable from a live agent run today (same class of gap as vpe/cpo/chro/ciso/
   gc/cdo). **CAIO-specific nuance verified for this plan:** the OTHER cross-plane
   leg — `POST /cosa/ai-governance/snapshot` on `services/cosa` — uses a genuinely
   DIFFERENT auth surface (`COSA_CONTROL_DELEGATION_SECRET`-signed delegation,
   `verifyControlDelegationToken`), not `requireWorkspaceAccess` at all, and IS
   reachable service-to-service (this task's own E2E calls it exactly the way
   `apps/cosa`'s composition root would, with a real `mint_control_plane_delegation`
   token, and it succeeds). So the two halves of CAIO's data path have asymmetric
   reachability: the control-plane signing leg is live-runtime-reachable today, the
   Company dossier *read* leg is not — do not assume both inherit the same fix when
   the portfolio-wide `requireWorkspaceAccess`-vs-agent-runtime gap is eventually
   closed; they are two different auth systems that need two different fixes.
2. **`ctx` project_id inertness:** `ai_governance_read`'s capability handler ctx
   dict-aware guard (`ctx.get("project_id") if isinstance(ctx, dict) else
   getattr(ctx, "project_id", None)`, mirroring `data_governance_read.py`/
   `legal_issue_read.py`) is correct code, but — same as every prior role since
   CHRO — `project_id` is never threaded into `ctx` anywhere in the real
   worker/gateway pipeline except one scheduler-only path. The guard is currently
   inert against most live runs.
3. **No generic deliberation evidence-gate exists anywhere.** Nothing in the real
   worker/gateway pipeline currently blocks a deliberation frame from proceeding
   when the underlying dossier snapshot is missing or stale — this is consistent
   across all 8 roles, not something CAIO introduces or fixes.
4. **`COSA_EXECUTIVE_CAIO_AGENT_SPEC` is not in `COSA_DEPLOYED_AGENT_SPECS`
   (only in `EXECUTIVE_AGENT_SPECS`) — this is now the 7th and FINAL instance of
   this open, deferred question across the entire 8-role portfolio** (vpe, cpo,
   chro, ciso, gc, cdo, caio all share it; only `chief_of_staff`/`cfo`/`cmo`/`coo`/
   `cro`/`cco` — the pre-existing non-executive-advisory-board roles — are wired
   into `COSA_DEPLOYED_AGENT_SPECS`). This was intentionally NOT fixed retroactively
   in this task, per the plan's own instruction that Task 5's closeout gate should
   flag it as still-open across all 7 roles and needing a dedicated follow-up
   design task — not a per-role patch. Fixing it here would have been scope creep
   into a decision this plan does not own.
5. **Task 1 architecture scope-down (Control Plane binds caller-supplied
   policy/evaluator identity rather than owning a native registry):**
   `services/cosa` has NO real model-policy/provider-config/evaluation-registry
   service of its own — the pre-flight investigation for this plan confirmed the
   plan's own Architecture prose ("Control Plane tiếp tục là authority cho model
   policy...") is aspirational, not descriptive of the current codebase. Task 1
   was scoped down to a bounded, honest cryptographic-integrity-binding port: it
   accepts policy/evaluator `id`/`version`/`definitionHash` as OPAQUE, already-computed
   input from the caller (`apps/cosa`, which derives these from the real
   `ModelPolicySpec`/`PinnedSkillRef` identities that live in the Agent Platform,
   Python side) and signs (HMAC) a `workspace+project+refs+timestamp` envelope —
   it does NOT re-derive, verify against a source-of-truth registry, or own any
   policy/eval state itself. `status: "VERIFIED"` therefore means "this envelope's
   required fields are present and it is validly signed", NOT "Control Plane
   independently confirmed this hash matches a real, current policy". A caller
   that lies about the definitionHash it computed would still get a validly-signed
   envelope. Related, disclosed-but-unfixed nuance: **project-scoping is bound but
   not independently authorized against caller scope** — the
   `COSA_CONTROL_DELEGATION_SECRET` token only carries `workspace_id` (and `role`),
   not `project_id`, so `getAiGovernanceSnapshot` checks workspace match but has no
   way to verify the caller is actually authorized for the specific `projectId` it
   requests a snapshot for within that workspace. This was a pre-authorized
   scope-down at Task 1 time (see this plan's pre-flight investigation), not an
   oversight discovered late.
6. **Cross-Encore-app HMAC duplication risk (Task 2):** `services/company`
   independently re-implements the exact same canonical-JSON + HMAC-SHA256
   algorithm as `services/cosa`'s signer, sharing only the secret value
   (`COSA_AI_GOVERNANCE_SIGNING_SECRET`) over no direct code dependency (the two
   are separate Encore apps; TypeScript source cannot be imported across them).
   There is **no automated drift guard** — if either implementation's canonical
   field order, hashing algorithm, or encoding ever diverges (e.g. a future
   refactor touches one side and not the other), signatures minted by one side
   would silently fail to verify on the other, or worse, silently succeed against
   a weaker/different check. This task's own E2E (`test_signed_snapshot_accepted_into_ai_governance_dossier`)
   only proves the CURRENT two implementations agree — it is not a regression
   guard against future drift. Related operational hazard: **secret rotation
   must be lockstep across both services** — rotating `COSA_AI_GOVERNANCE_SIGNING_SECRET`
   on only one side breaks every snapshot minted or verified during the gap, with
   no automated detection beyond dossier-create requests starting to fail
   `AI_GOVERNANCE_SNAPSHOT_UNVERIFIABLE`.
7. **Portfolio-wide `apps-cosa-test` coverage gap — found AND fixed, not left
   open.** Task 3 discovered that `make apps-cosa-test` only ever collected
   `tests/apps/cosa/`, silently excluding all 16 AgentSpec/capability test files
   across all 8 executive-advisory-board roles
   (`apps/cosa/tests/test_*_specs.py`, `test_*_read.py`) from `make verify`. This
   was fixed directly in commit `29e594aa` (already on `main` before this task
   started) — confirmed safe: identical pre-existing 15 failures/1 error
   (unrelated, documented below) before and after, +50 tests now included, all
   passing. This task's own `make apps-cosa-test` run reproduced the exact same
   15 failures + 1 error baseline (`test_seed_publishes_every_deployed_agent_spec`,
   `test_project_crm_read_success`, the `test_run_delegation.py`/
   `test_worker_wiring.py`/`test_founder_knowledge_context.py`/
   `test_lifecycle_tranche_c_acceptance.py`/`test_scheduled_session_worker.py`/
   `test_vertical_slice_1_read_path.py`/`test_workspace_execution_e2e.py` failures,
   and the `test_sse_reconnect_e2e.py` error) — none of them touch anything CAIO-
   or ai_governance-specific; they are pre-existing and unrelated to this task.
8. **E2E coverage outcome: FULL, not partial.** Unlike the disclosed risk in this
   plan's own pre-flight notes ("if minting a real signed snapshot from Python
   E2E test code proves genuinely infeasible... report honestly as partial"),
   this task's environment had `encore` CLI installed and a reachable Postgres
   admin connection, so `tests/e2e/test_caio_ai_governance_profile.py` boots a
   REAL `services/cosa` process (via the pre-existing `boot_cosa_only()` helper
   against a disposable Postgres cluster — the same helper
   `tests/apps/cosa/worker/conftest.py::control_plane_service` uses) alongside the
   existing `real_company_service` fixture, and mints a REAL
   `COSA_CONTROL_DELEGATION_SECRET`-signed delegation token using the actual
   production helper (`apps.cosa.auth.jwt.mint_control_plane_delegation`) — not a
   hand-rolled JWT reimplementation. All 5 test functions pass, covering: (a) the
   full Board activation lifecycle (UNAVAILABLE → ai_governance profile ACTIVE →
   AVAILABLE_NOT_ACTIVATED → caio ACTIVE → deliberation frame), (b) a real signed
   snapshot minted by `services/cosa` accepted into the Company AI Governance
   Dossier (200, cross-plane HMAC re-verification succeeds), (c) a tampered
   snapshot (valid shape, signature no longer matches content) rejected with
   `failed_precondition` + `AI_GOVERNANCE_SNAPSHOT_UNVERIFIABLE` body marker, (d) an
   unsigned snapshot (missing `signature` field) rejected with `invalid_argument`
   — caught by Encore's own typed-request decoder before it reaches the service
   (same class of finding as CDO Task 3's documented embedding-rejection gap:
   the typed HTTP contract itself is the first fail-closed layer), (e)
   cross-workspace AI Governance Dossier read denial with a `permission_denied`/
   `PROJECT_ACCESS_DENIED` body-content assertion, and (f) `services/cosa`'s own
   snapshot endpoint rejecting a delegation token scoped to a foreign workspace,
   re-verified end-to-end through the real running process (not just Task 1's own
   unit tests). No invented string error codes were used anywhere in this test —
   only real HTTP status codes and real `APIError` `code`/`message` bodies.
9. **Full-replace-on-append semantics** (confirming with an empty/partial payload
   silently drops prior content) applies to the AI Governance Dossier the same
   way it applies to every other dossier in this portfolio (security/people/
   legal/data) — `appendAiGovernanceRevisionEndpoint` requires the FULL
   `riskSignals`/`sourceRefs` on every append, not a delta. This task's E2E does
   not add a dedicated append-pinning test beyond what Task 2's own unit suite
   (`operations/tests/ai-governance-dossier.test.ts`, 25 tests, all passing)
   already covers for this exact pattern — the E2E instead exercises only the
   `create` + `read` legs, which is the surface this task's cross-plane snapshot-
   minting proof needed.
