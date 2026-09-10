# COSA MetaSkill Candidate Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing workspace skill candidate flow into a durable, evaluated and human-reviewed MetaSkill lifecycle that cannot self-publish, self-grant capabilities or execute an unpinned candidate.

**Architecture:** Reuse the existing SkillCandidate store, skill registry routes, static skill contract and exact hash pinning. Add explicit candidate/evaluation/reviewer transitions and immutable evidence; evaluation runs only against synthetic/redacted fixtures plus registered low-risk capability stubs. Flutter presents review evidence and state, not an LLM-trust shortcut.

**Tech Stack:** Python 3.12, Pydantic, PostgreSQL/RLS, FastAPI, existing `agent.skills` registry/candidate store, Flutter/GetX.

**Spec:** `docs/superpowers/specs/2026-09-10-cosa-agent-harness-efficiency-safety-design.md`

## Global Constraints

- Only human publisher authority can transition `REVIEW_REQUIRED` to `PUBLISHED`; published versions are immutable and hash-pinned by runs.
- Candidate/evaluation data is workspace-scoped, sourceable and retention-safe; raw customer transcript/Vault text is never auto-exported into a skill.
- Candidates cannot execute in production, alter AgentSpec/model policy/connector grant or acquire a capability.
- Workspace-custom candidate boundary remains L0/L1 and R/A only; connector, payout, transaction, external send, lifecycle and permission capabilities remain rejected.
- Evaluation result is evidence, not a publish authority; evaluator crash/timeout never promotes a candidate.

---

## File structure and dependency map

| Path | Responsibility |
|---|---|
| `packages/agent/skills/contracts.py` | Lifecycle enum/immutable provenance/evaluation contracts. |
| `packages/agent/skills/candidate_store.py` | Postgres candidate/evaluation transitions with workspace isolation. |
| `packages/agent/migrations/008_metaskill_candidate_lifecycle.sql` | Expand-only evaluation/review evidence tables/indexes. |
| `packages/agent/skills/evaluator.py` | Isolated deterministic evaluator orchestration. |
| `apps/cosa/api/skill_schemas.py` | Typed candidate/evaluate/review/publish schema responses. |
| `apps/cosa/api/skill_registry_routes.py` | Authenticated lifecycle guards and exact publish/pin calls. |
| `apps/cosa/agents/skillpack_seed.py` | Only if a reviewed low-risk built-in fixture is needed; no dynamic seed path. |
| `frontend/lib/modules/skills/**` | Candidate review/evaluation state and immutable evidence view. |
| `tests/agent/skills/**`, `apps/cosa/tests/test_skill_registry_lifecycle.py` | Lifecycle, security, persistence and API evidence. |

### Task 1: Make candidate lifecycle explicit and durable

**Files:**
- Modify: `packages/agent/skills/contracts.py`
- Modify: `packages/agent/skills/candidate_store.py`
- Create: `packages/agent/migrations/008_metaskill_candidate_lifecycle.sql`
- Create: `tests/agent/skills/test_candidate_lifecycle.py`

**Interfaces:**
- Produces `MetaSkillCandidateStatus`, `SkillEvaluationRecord`, `transition_candidate(...)`, `append_evaluation(...)` and `record_review(...)`.

- [ ] **Step 1: Write failing transition tests**

```python
async def test_candidate_cannot_skip_review_to_published(store):
    candidate = await store.create_candidate(_candidate(status="CANDIDATE"))
    with pytest.raises(SkillLifecycleError, match="REVIEW_REQUIRED"):
        await store.transition_candidate(candidate.id, workspace_id="ws-1", to_status="PUBLISHED")


async def test_workspace_cannot_read_or_review_foreign_candidate(store):
    candidate = await store.create_candidate(_candidate(workspace_id="ws-a"))
    assert await store.get_candidate(candidate.id, workspace_id="ws-b") is None
```

- [ ] **Step 2: Run to verify red**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/skills/test_candidate_lifecycle.py -q`

Expected: FAIL because lifecycle/evaluation persistence does not expose the transition contract.

- [ ] **Step 3: Implement immutable records and legal transitions**

Define `DRAFT → CANDIDATE → EVALUATING → REVIEW_REQUIRED → PUBLISHED → PINNED → RETIRED`, plus `REJECTED` from CANDIDATE/EVALUATING/REVIEW_REQUIRED. Store source-reference hash, candidate manifest hash, evaluator version/result hash, reviewer ID/reason and timestamps. Enforce transition SQL with current status predicate and workspace setting; a published record creates a new immutable SkillSpec version rather than rewriting candidate content.

- [ ] **Step 4: Run lifecycle tests**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/skills/test_candidate_lifecycle.py -q`

Expected: PASS for legal/illegal transitions, stale compare-and-set, workspace isolation and immutable review evidence.

- [ ] **Step 5: Commit lifecycle substrate**

```bash
git add packages/agent/skills/contracts.py packages/agent/skills/candidate_store.py packages/agent/migrations/008_metaskill_candidate_lifecycle.sql tests/agent/skills/test_candidate_lifecycle.py
git commit -m "feat: persist metaskill candidate lifecycle"
```

### Task 2: Build isolated, policy-bound candidate evaluation

**Files:**
- Create: `packages/agent/skills/evaluator.py`
- Create: `tests/agent/skills/test_evaluator.py`
- Modify: `apps/cosa/api/skill_registry_routes.py`
- Create: `apps/cosa/tests/test_skill_candidate_evaluation.py`

**Interfaces:**
- Consumes candidate manifest, registered capability IDs and synthetic fixture suite.
- Produces `SkillEvaluationRecord` with `REVIEW_REQUIRED` or `REJECTED`, never `PUBLISHED`.

- [ ] **Step 1: Write failing isolation/security tests**

```python
async def test_evaluator_rejects_external_send_even_if_candidate_claims_read_only():
    result = await evaluate_candidate(_candidate(capabilities=("message.send",)), fixture_suite=_fixtures())
    assert result.status == "REJECTED"
    assert "CAPABILITY_FORBIDDEN" in result.reason_codes


async def test_evaluator_uses_synthetic_fixture_not_candidate_source_text():
    result = await evaluate_candidate(_candidate(source_ref="vault://private-doc"), fixture_suite=_fixtures())
    assert "private-doc" not in result.serialized_report
```

- [ ] **Step 2: Run to verify red**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/skills/test_evaluator.py apps/cosa/tests/test_skill_candidate_evaluation.py -q`

Expected: FAIL because no evaluator/evaluation endpoint integration exists.

- [ ] **Step 3: Implement deterministic evaluation orchestration**

Validate autonomy/side-effect/capability boundary before fixture execution. Run only synthetic/redacted test cases with stubs or explicitly read-only registered capability. Write evaluator version, fixture-suite hash, policy result, quality score, token/cost/latency evidence and reason codes. On timeout/crash write a terminal evaluation failure and transition to `REVIEW_REQUIRED` only with visible failure report; never retry/publish in a background loop without an explicit request.

- [ ] **Step 4: Run evaluator tests**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/skills/test_evaluator.py apps/cosa/tests/test_skill_candidate_evaluation.py -q`

Expected: PASS for forbidden capabilities, evaluator crash, redaction, result persistence and no implicit promotion.

- [ ] **Step 5: Commit evaluator**

```bash
git add packages/agent/skills/evaluator.py tests/agent/skills/test_evaluator.py apps/cosa/api/skill_registry_routes.py apps/cosa/tests/test_skill_candidate_evaluation.py
git commit -m "feat: evaluate metaskill candidates safely"
```

### Task 3: Enforce reviewer publish and exact run pinning at API boundary

**Files:**
- Modify: `apps/cosa/api/skill_schemas.py`
- Modify: `apps/cosa/api/skill_registry_routes.py`
- Modify: `apps/cosa/api/app.py`
- Modify: `shared/contracts/mvp-surface.json`
- Create: `apps/cosa/tests/test_skill_registry_lifecycle.py`
- Create: `tests/contracts/test_skill_registry_lifecycle_surface.py`

**Interfaces:**
- Produces explicit candidate create/evaluate/review/publish/read operations; publish returns `skill_id`, `version`, `definition_hash` only after exact review.

- [ ] **Step 1: Write failing role/pinning tests**

```python
async def test_operator_without_publisher_role_cannot_publish_candidate(client, operator_token):
    response = await client.post("/agent/skills/candidates/c-1/publish", headers=operator_token)
    assert response.status_code == 403


async def test_published_version_is_pinned_not_latest_for_run(plane):
    pinned = await plane.spec_registry.get_exact("skill", "research", "1.0.0", _hash_v1)
    assert pinned.definition_hash == _hash_v1
```

- [ ] **Step 2: Run to verify red**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest apps/cosa/tests/test_skill_registry_lifecycle.py tests/contracts/test_skill_registry_lifecycle_surface.py -q`

Expected: FAIL because schemas/endpoints do not enforce reviewer lifecycle/pinning.

- [ ] **Step 3: Implement explicit role and contract checks**

Use existing authenticated identity/workspace resolution and add a narrowly named publisher guard; do not equate workspace membership with publisher authority. Publish verifies candidate workspace/status, at least one completed evaluation, evaluator suite/hash, reviewer decision and candidate manifest hash, then uses existing registry publisher to create an exact version/hash. Candidate routes return `404` for foreign workspace and never expose source content beyond redacted provenance.

- [ ] **Step 4: Run API/contract tests**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest apps/cosa/tests/test_skill_registry_lifecycle.py tests/contracts/test_skill_registry_lifecycle_surface.py -q && make frontend-api-contract-check`

Expected: PASS for missing role, stale candidate, foreign workspace, failed evaluation, duplicate publish and exact pin lookup.

- [ ] **Step 5: Commit API lifecycle guard**

```bash
git add apps/cosa/api/skill_schemas.py apps/cosa/api/skill_registry_routes.py apps/cosa/api/app.py shared/contracts/mvp-surface.json apps/cosa/tests/test_skill_registry_lifecycle.py tests/contracts/test_skill_registry_lifecycle_surface.py
git commit -m "feat: require reviewed metaskill publication"
```

### Task 4: Add truthful Skill Review UI and qualification suite

**Files:**
- Create: `frontend/lib/modules/skills/models/skill_registry_models.dart`
- Modify: `frontend/lib/modules/skills/services/skill_registry_service.dart`
- Modify: `frontend/lib/modules/skills/controllers/skill_registry_controller.dart`
- Modify: `frontend/lib/modules/skills/views/skill_registry_view.dart`
- Create: `frontend/lib/modules/skills/views/widgets/skill_candidate_review_panel.dart`
- Create: `frontend/test/modules/skills/skill_candidate_review_test.dart`
- Create: `tests/e2e/test_metaskill_candidate_lifecycle.py`
- Modify: `Makefile`

**Interfaces:**
- Consumes lifecycle API models and evaluation projection.
- Produces a review UI with no direct capability edit/auto-publish control and `make metaskill-candidate-e2e`.

- [ ] **Step 1: Write failing UI/E2E tests**

```dart
testWidgets('candidate with failed evaluation cannot show publish action', (tester) async {
  await tester.pumpWidget(reviewPanel(status: SkillCandidateStatus.reviewRequired, evaluationPassed: false));
  expect(find.text('Publish'), findsNothing);
  expect(find.text('Evaluation failed'), findsOneWidget);
});
```

```python
def test_candidate_cannot_execute_before_reviewed_publish(stack):
    candidate = stack.create_candidate_with_safe_manifest()
    assert stack.invoke_candidate(candidate.id).error_code == "SKILL_NOT_PUBLISHED"
    assert stack.publish_as_non_reviewer(candidate.id).status_code == 403
```

- [ ] **Step 2: Run to verify red**

Run: `cd frontend && flutter test test/modules/skills/skill_candidate_review_test.dart`

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/e2e/test_metaskill_candidate_lifecycle.py -q`

Expected: FAIL because review panel/process target does not exist.

- [ ] **Step 3: Implement evidence-first UI and E2E target**

Show candidate status, manifest/capability diff, evaluator/fixture version, score/cost/latency, redacted provenance, reviewer reason and pinned published hash. Publish control appears only when backend returns `canPublish=true`; client does not derive it. E2E uses disposable Postgres, distinct author/reviewer/foreign principals, synthetic fixtures and a real AgentSpec resolution to prove candidate rejection then exact published pinning.

- [ ] **Step 4: Run qualification gates**

Run: `make metaskill-candidate-e2e && make agent-test && make apps-cosa-test && cd frontend && flutter test test/modules/skills/skill_candidate_review_test.dart`

Expected: PASS. Failure or an unavailable disposable stack blocks feature enablement and does not allow manual UI bypass.

- [ ] **Step 5: Commit reviewed lifecycle delivery**

```bash
git add frontend/lib/modules/skills frontend/test/modules/skills tests/e2e/test_metaskill_candidate_lifecycle.py Makefile
git commit -m "feat: review metaskill candidates in workspace UI"
```
