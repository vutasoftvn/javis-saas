# Phần B.1 + B.3: Workflow Multi-agent Chuẩn hoá và Unified Approval — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sau khi Giai đoạn 1 chứng minh Executive Board gọi model thật, hợp nhất orchestration workflow về `WorkflowEngine` đã được composition-root wire và thay direct skill promotion bằng unified approval bền vững, Founder-controlled.

**Architecture:** `WorkflowEngine` là executor DAG duy nhất. Worker lấy engine từ `CosaAgentPlane`; mọi tool effect đi qua `CapabilityGateway`. `agent.approvals` nhận hai binding: `TOOL_CALL` giữ exact tuple `run_id + tool_call_id + checkpoint_ref + manifest_hash`, `CHANGE_REQUEST` bind `workspace_id + action + subject_kind + subject_ref + subject_hash`. Promotion route chỉ tạo approval. Founder decision atomically tạo outbox; worker revalidates exact hash then publishes exactly once.

**Boundary discovered during planning:** `Workflow`/`APPROVAL_GATE` is currently an in-memory library object: there is no durable workflow-instance repository or restart-safe generic resume endpoint. This phase corrects its obsolete approval API and keeps it library/test-only; it must not be wired to automatic production resume until a separate plan persists the workflow instance and defines a hash-bound resume contract. The first production `CHANGE_REQUEST` consumer here is only `promote_skill_candidate`.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy async/PostgreSQL, pytest, disposable PostgreSQL/process E2E.

**Spec:** `docs/superpowers/specs/2026-09-11-executive-advisory-board-completion-and-agent-platform-restructuring-design.md` (Phần B mục 1 và 3), corrected by Task 1.

## Global Constraints

- Start only after every Giai đoạn 1 gate in `docs/superpowers/plans/2026-09-11-executive-board-real-execution-and-cco-role.md` passes. A failed or environment-blocked gate stops this plan.
- Preserve all unrelated working-tree changes; do not modify or stage Phase 1 implementation work outside the declared Task 1 entry gate.
- Scope excludes `SkillOptimizationLab`, feedback-driven learning, functional profiles and new executive roles. Those are B.2/B.4 and role plans.
- Do not synthesize a Run, ToolCall or Checkpoint for a skill promotion. It is a `CHANGE_REQUEST`.
- Founder is the sole reviewer for `promote_skill_candidate`. An operator may request review but cannot decide it.
- No direct handler/tool execution. All tool effects stay behind `CapabilityGateway`.
- A generic `APPROVAL_GATE` may not enqueue a worker action or auto-resume an in-memory `Workflow`; only the allow-listed promotion action gets an approval-action outbox in this phase.
- Candidate instructions, prompts, secrets and PII never enter approval/audit payloads.
- Historical migrations are immutable. Down migration must refuse to remove any persisted `CHANGE_REQUEST` evidence.

## File structure

| Unit | Files | Responsibility |
| --- | --- | --- |
| Source truth | `docs/superpowers/specs/2026-09-11-executive-advisory-board-completion-and-agent-platform-restructuring-design.md` | Correct B.1 deletion inventory and freeze scope. |
| Ledger | `packages/agent/migrations/006_unified_governance_approvals.*`, `packages/agent/runs/{models,repository}.py` | Canonical bindings, CAS, event and action outbox. |
| Approval domain | `packages/agent/capabilities/approval_service.py` | Creation, decision, verification split by binding kind. |
| Workflow | `apps/cosa/composition/workflow_orchestration.py`, `apps/cosa/worker/handlers.py`, `packages/agent/workflows/*.py` | Composed engine and Gateway-only execution. |
| Promotion | `apps/cosa/api/{skill_schemas,skill_registry_routes,workforce_routes}.py`, `apps/cosa/worker/{approval_actions,main}.py`, `packages/agent/migrations/007_skill_candidate_promotion_cas.*` | Request, decision, durable relay, exactly-once hash-pinned publish. |
| Cleanup | `packages/agent/coordination/*.py` | Delete only the seven proven-unused duplicate primitives. |
| Proof | `tests/agent/**`, `tests/apps/cosa/**`, `tests/e2e/**`, `Makefile` | Contract, migration, cross-tenant and restart evidence. |

## Interfaces

```python
ApprovalBindingKind = Literal["TOOL_CALL", "CHANGE_REQUEST"]

class ApprovalSubject(BaseModel):
    kind: str
    ref: str
    definition_hash: str

class RunApprovalRecord(BaseModel):
    approval_id: str
    workspace_id: str | None
    project_id: str | None
    binding_kind: ApprovalBindingKind = "TOOL_CALL"
    run_id: str | None
    tool_call_id: str | None
    checkpoint_ref: str | None
    action: str
    subject_kind: str | None
    subject_ref: str | None
    subject_hash: str | None
    status: str
    requirement: dict[str, Any]
```

```python
async def create_change_approval_request(
    self, *, workspace_id: str, project_id: str | None, action: str,
    subject: ApprovalSubject, requirement: dict[str, Any], requester: str,
) -> tuple[RunApprovalRecord, WaitDescriptor]: ...

async def verify_change_execution(
    self, *, approval_id: str, workspace_id: str, action: str,
    subject: ApprovalSubject,
) -> ApprovalChangeExecutionResult: ...
```

```python
async def publish_candidate_if_approved(
    self, *, workspace_id: str, candidate_id: str,
    expected_definition_hash: str, approval_id: str, publisher: str,
) -> SkillCandidate: ...
```

The candidate-store method may transition only `EVALUATED -> PUBLISHED` when hash matches. A retry with the same `promotion_approval_id` returns the record; a different hash or approval refuses.

---

### Task 1: Lock phase entry and correct the B.1 source of truth

**Files:**

- Modify: `docs/superpowers/specs/2026-09-11-executive-advisory-board-completion-and-agent-platform-restructuring-design.md`

**Interfaces:**

- Consumes: Giai đoạn 1 implementation and current import graph.
- Produces: exact retain/delete scope for the following tasks.

- [ ] **Step 1: Run the entry gate without staging unrelated work**

```bash
git status --short
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/executive_board/ -v
make skillpacks-validate
make contracts-check
cd services/company && npx vitest run operations/tests/executive-role-activation.service.test.ts operations/tests/executive-deliberation.service.test.ts operations/tests/project-startup-team.service.test.ts
```

Expected: all pass. If a phase-1 file is dirty, record its owner/commit and do not stage it. If a test or environment prerequisite fails, stop here.

- [ ] **Step 2: Capture code-traced inventory**

```bash
rg -n -g '*.py' 'from agent\.coordination\.(approval_gate|delegate|parallel|quality_gate|risk_classification|supervisor|synthesis)|import agent\.coordination' apps packages tests
rg -n -g '*.py' 'from agent\.coordination\.(scheduler|control_plane_scheduler_client)' apps packages tests
rg -n -g '*.py' 'WorkflowEngine\(' apps/cosa
rg -n -g '*.py' 'request_approval\(|find_by_run_and_action\(|\.get\(approval_id\)' packages/agent/workflows
```

Expected: duplicate primitives have only self/test callers; `scheduler.py` remains a contract for `control_plane_scheduler_client.py`; automation worker constructs a naked engine; workflow code calls obsolete approval APIs.

- [ ] **Step 3: Amend the design with this exact decision**

```markdown
### Quyết định thực thi B.1 + B.3 (2026-09-12)

WorkflowEngine là đường orchestration workflow duy nhất. Chỉ xoá primitive không
có production caller: approval_gate.py, delegate.py, parallel.py, quality_gate.py,
risk_classification.py, supervisor.py và synthesis.py. Giữ scheduler.py,
control_plane_scheduler_client.py, delegation_envelope.py, durable_supervisor.py,
expansion.py và wait_resolver.py.

B.1 chỉ wire worker vào CosaAgentPlane.workflow_orchestration; không mở endpoint
spawn agent, prompt tự do hay role tự chọn. B.3 dùng một ledger approval cho
TOOL_CALL và CHANGE_REQUEST. Promotion workspace_custom bind candidate ID + exact
definition hash, Founder quyết định, worker recheck trước publish. B.2/B.4 deferred.
```

- [ ] **Step 4: Validate and commit**

```bash
rg -n 'xoá.*scheduler\.py|delete.*scheduler\.py|scheduler\.py.*0 caller' docs/superpowers/specs/2026-09-11-executive-advisory-board-completion-and-agent-platform-restructuring-design.md
git diff --check
git add docs/superpowers/specs/2026-09-11-executive-advisory-board-completion-and-agent-platform-restructuring-design.md
git commit -m "docs(agent): correct multi-agent consolidation scope"
```

Expected: search returns no stale deletion direction and whitespace check passes.

---

### Task 2: Expand the canonical approval ledger for tool and change bindings

**Files:**

- Create: `packages/agent/migrations/006_unified_governance_approvals.sql`
- Create: `packages/agent/migrations/006_unified_governance_approvals.down.sql`
- Modify: `packages/agent/runs/models.py`
- Modify: `packages/agent/runs/repository.py`
- Test: `tests/agent/runs/test_unified_approval_repository.py`
- Test: `tests/agent/runs/test_unified_approval_migration.py`

**Interfaces:**

- Consumes: `agent.approvals` and existing `RunApprovalRecord`.
- Produces: scoped generic approvals, append-only event history and claimable action outbox.

- [ ] **Step 1: Write failing binding tests**

```python
@pytest.mark.asyncio
async def test_change_request_is_scoped_without_a_run() -> None:
    repo = InMemoryRunRepository()
    approval = RunApprovalRecord(
        approval_id="appr_change_1", workspace_id="ws-a",
        binding_kind="CHANGE_REQUEST", run_id=None, tool_call_id=None,
        checkpoint_ref=None, action="promote_skill_candidate",
        subject_kind="skill_candidate", subject_ref="cand_1",
        subject_hash="sha256:candidate-v1", requirement={"role": "founder"},
        status="pending",
    )
    await repo.create_approval(approval)
    assert await repo.get_scoped_approval("appr_change_1", "ws-a") == approval
    assert await repo.get_scoped_approval("appr_change_1", "ws-b") is None
    assert await repo.get_approval_by_tool_call("call_any") is None
```

Add a tool case that creates one run, checkpoint and tool-call ledger row, then proves a changed tool-call ID or checkpoint cannot match. Migration test migrates an old tool approval and asserts `workspace_id` backfill plus `binding_kind == "TOOL_CALL"`.

- [ ] **Step 2: Run the red tests**

```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/runs/test_unified_approval_repository.py tests/agent/runs/test_unified_approval_migration.py -v
```

Expected: fail because model fields and migration do not yet exist.

- [ ] **Step 3: Implement one expand-compatible schema**

```sql
ALTER TABLE agent.approvals
    ADD COLUMN IF NOT EXISTS workspace_id varchar(64),
    ADD COLUMN IF NOT EXISTS binding_kind varchar(32) NOT NULL DEFAULT 'TOOL_CALL',
    ADD COLUMN IF NOT EXISTS subject_kind varchar(128),
    ADD COLUMN IF NOT EXISTS subject_ref varchar(256),
    ADD COLUMN IF NOT EXISTS subject_hash varchar(128);

UPDATE agent.approvals AS a
SET workspace_id = r.workspace_id
FROM agent.runs AS r
WHERE a.run_id = r.run_id AND a.workspace_id IS NULL;

ALTER TABLE agent.approvals
    ALTER COLUMN run_id DROP NOT NULL,
    ALTER COLUMN tool_call_id DROP NOT NULL,
    ALTER COLUMN checkpoint_ref DROP NOT NULL;

ALTER TABLE agent.approvals ADD CONSTRAINT chk_agent_approvals_binding
CHECK (
  (binding_kind = 'TOOL_CALL'
   AND run_id IS NOT NULL AND tool_call_id IS NOT NULL AND checkpoint_ref IS NOT NULL)
  OR
  (binding_kind = 'CHANGE_REQUEST' AND workspace_id IS NOT NULL
   AND run_id IS NULL AND tool_call_id IS NULL AND checkpoint_ref IS NULL
   AND subject_kind IS NOT NULL AND subject_ref IS NOT NULL AND subject_hash IS NOT NULL)
) NOT VALID;
ALTER TABLE agent.approvals VALIDATE CONSTRAINT chk_agent_approvals_binding;

CREATE UNIQUE INDEX IF NOT EXISTS ux_agent_approvals_pending_change_subject
ON agent.approvals (workspace_id, action, subject_kind, subject_ref, subject_hash)
WHERE binding_kind = 'CHANGE_REQUEST' AND status = 'pending';
```

Create `agent.approval_events` with `event_id, approval_id FK, workspace_id, event_type, actor_id, payload, created_at` and `agent.approval_action_outbox` with unique `approval_id`, `workspace_id, action, subject_hash, state, attempt_count, next_attempt_at, claim_token, created_at, delivered_at`. Index events by `(workspace_id, created_at)` and outbox by `(state, next_attempt_at)`. The down migration must refuse when generic requests/events/outbox records exist.

- [ ] **Step 4: Update both repository implementations**

Add and implement for in-memory and PostgreSQL:

```python
async def create_or_get_pending_change_approval(self, approval): ...
async def append_approval_event(self, *, approval_id, workspace_id, event_type, actor_id, payload): ...
async def decide_change_approval_and_enqueue(self, *, approval_id, reviewer, approved, reason, evidence): ...
async def claim_approval_actions(self, *, limit, worker_id, now): ...
```

`decide_change_approval_and_enqueue` must use one PostgreSQL transaction: CAS `status = 'pending'`, append `approval.decided`, and insert exactly one outbox row only when the approved generic action is the server allow-listed `promote_skill_candidate`. A generic workflow gate is decided without an outbox; it has no durable resume owner in this phase. `get_scoped_approval` and `list_pending_approvals` query `a.workspace_id` directly, not an inner join to runs.

- [ ] **Step 5: Verify and commit**

```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/runs/test_unified_approval_repository.py tests/agent/runs/test_unified_approval_migration.py tests/agent/runs/test_repository.py tests/agent/runs/test_project_scoped_records.py -v
make migration-compat-check
git add packages/agent/migrations/006_unified_governance_approvals.sql packages/agent/migrations/006_unified_governance_approvals.down.sql packages/agent/runs/models.py packages/agent/runs/repository.py tests/agent/runs/test_unified_approval_repository.py tests/agent/runs/test_unified_approval_migration.py
git commit -m "feat(approval): add unified tool and change-request ledger"
```

Expected: migration, exact tool binding, tenant isolation, pending deduplication and CAS pass.

---

### Task 3: Split the durable approval service by binding kind

**Files:**

- Modify: `packages/agent/capabilities/approval_service.py`
- Modify: `packages/agent/capabilities/__init__.py`
- Test: `tests/agent/capabilities/test_approval_service.py`
- Test: `tests/agent/capabilities/test_change_request_approval.py`

**Interfaces:**

- Consumes: Task 2.
- Produces: `create_change_approval_request`, `verify_change_execution`, and tool-only `verify_and_prepare_resume`.

- [ ] **Step 1: Write red tests**

```python
@pytest.mark.asyncio
async def test_change_approval_is_idempotent() -> None:
    service = DurableApprovalService(InMemoryRunRepository())
    subject = ApprovalSubject(kind="skill_candidate", ref="cand_a", definition_hash="sha256:one")
    first, _ = await service.create_change_approval_request(
        workspace_id="ws-a", project_id=None, action="promote_skill_candidate",
        subject=subject, requirement={"role": "founder"}, requester="user:operator",
    )
    second, _ = await service.create_change_approval_request(
        workspace_id="ws-a", project_id=None, action="promote_skill_candidate",
        subject=subject, requirement={"role": "founder"}, requester="user:operator",
    )
    assert second.approval_id == first.approval_id
    assert first.tool_call_id is None
```

Also assert changed hash yields `APPROVAL_SUBJECT_STALE`, wrong action yields `APPROVAL_ACTION_MISMATCH`, non-approved/expired records cannot execute, and a `CHANGE_REQUEST` passed to `verify_and_prepare_resume` is denied with `APPROVAL_BINDING_KIND_MISMATCH`.

- [ ] **Step 2: Run red**

```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/capabilities/test_change_request_approval.py tests/agent/capabilities/test_approval_service.py -v
```

Expected: failure because service only understands tool calls.

- [ ] **Step 3: Implement strict verification**

```python
class ApprovalChangeExecutionResult(BaseModel):
    can_execute: bool
    reason_code: str
    approval_record: RunApprovalRecord | None = None

async def verify_change_execution(self, *, approval_id, workspace_id, action, subject):
    approval = await self._repo.get_scoped_approval(approval_id, workspace_id)
    if approval is None:
        return ApprovalChangeExecutionResult(False, "APPROVAL_NOT_FOUND_OR_FORBIDDEN")
    if approval.binding_kind != "CHANGE_REQUEST":
        return ApprovalChangeExecutionResult(False, "APPROVAL_BINDING_KIND_MISMATCH", approval)
    if (approval.action, approval.subject_kind, approval.subject_ref, approval.subject_hash) != (
        action, subject.kind, subject.ref, subject.definition_hash,
    ):
        return ApprovalChangeExecutionResult(False, "APPROVAL_SUBJECT_STALE", approval)
    if approval.status != "approved":
        return ApprovalChangeExecutionResult(False, "APPROVAL_NOT_APPROVED", approval)
    return ApprovalChangeExecutionResult(True, "APPROVAL_VALID", approval)
```

Existing `create_approval_request` loads RunRecord and always writes `TOOL_CALL`. `submit_decision` uses the Task-2 atomic change method only for generic bindings. No request body can set binding kind, requirement or subject hash.

- [ ] **Step 4: Verify and commit**

```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/capabilities/test_change_request_approval.py tests/agent/capabilities/test_approval_service.py tests/agent/capabilities/test_approval_process_resume.py tests/agent/capabilities/test_live_authorization_ticket.py tests/agent/drift/test_case_g_same_tool_twice.py tests/agent/drift/test_case_h_target_drift.py -v
git add packages/agent/capabilities/approval_service.py packages/agent/capabilities/__init__.py tests/agent/capabilities/test_approval_service.py tests/agent/capabilities/test_change_request_approval.py
git commit -m "feat(approval): verify hash-bound change requests"
```

---

### Task 4: Remove workflow approval shims and use the composed engine

**Files:**

- Modify: `packages/agent/workflows/{engine,approval_step,tool_step}.py`
- Modify: `apps/cosa/composition/workflow_orchestration.py`
- Modify: `apps/cosa/worker/handlers.py`
- Test: `tests/agent/workflows/{test_approval_step,test_workflow_governance}.py`
- Test: `tests/apps/cosa/worker/test_automation_uses_composed_workflow_engine.py`

**Interfaces:**

- Consumes: Task 3 and `CapabilityGateway`.
- Produces: Gateway-only tool effects, a durable approval-service adapter for library gates, and concrete `WorkflowOrchestration.execute_spec`; generic workflow-gate restart recovery remains explicitly out of scope.

- [ ] **Step 1: Write red tests**

```python
@pytest.mark.asyncio
async def test_engine_refuses_tool_call_without_gateway() -> None:
    engine = WorkflowEngine(tool_registry=object())
    with pytest.raises(RuntimeError, match="CapabilityGateway"):
        engine.build_steps_from_spec(tool_call_workflow_spec)

@pytest.mark.asyncio
async def test_approval_gate_creates_durable_change_request() -> None:
    outcome = await ApprovalGateStep(
        name="publish", approval_service=service, action="publish_report",
        subject_key="report_ref", subject_hash_key="report_hash",
    ).run({"workspace_id": "ws-a", "report_ref": "report-7", "report_hash": "sha256:r7"})
    assert outcome.status is StepStatus.WAITING_APPROVAL
```

Worker test injects a spy `workflow_engine` into a plane, invokes `execute_automation_run_task` and asserts the spy executes the spec. Add a regression that an `APPROVAL_GATE` decision does not schedule a generic worker action or claim restart-safe completion: the `Workflow` object is still library-only until a persisted workflow-instance design exists.

- [ ] **Step 2: Run red**

```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/workflows/test_approval_step.py tests/agent/workflows/test_workflow_governance.py tests/apps/cosa/worker/test_automation_uses_composed_workflow_engine.py -v
```

Expected: legacy workflow code calls absent `request_approval/get/find_by_run_and_action` and worker constructs a private engine.

- [ ] **Step 3: Implement the only execution path**

In `WorkflowEngine.build_steps_from_spec`:

```python
if step_spec.type == StepType.TOOL_CALL:
    if self._gateway is None:
        raise RuntimeError(
            f"WorkflowEngine cannot compile TOOL_CALL step '{step_name}': CapabilityGateway is required"
        )
    compiled_steps.append(GatewayToolCallStep(...))
```

Remove `ToolCallStep` if the caller scan proves no production use. At `execute_spec`, set private state keys from values the engine owns: `_workflow_instance_id = workflow.id`, `_workflow_definition_hash = spec.definition_hash or spec.compute_hash()`, and `_workflow_step_id`. `ApprovalGateStep.run` requires trusted `workspace_id` and a non-empty `subject_key`; it creates `ApprovalSubject(kind="workflow_gate", ref="<workflow_instance_id>:<step_id>", definition_hash=hash({workflow_definition_hash, step_id, subject_value}))` through `create_change_approval_request`. Only the hash is persisted. `check_pending` is async and both `WorkflowEngine.resume` and `resume_spec` await it before changing state; no substring status parsing. A missing context fails closed rather than manufacturing a Run, ToolCall or Checkpoint.

Do not attach this generic approval to `approval_action_outbox` or `cosa.resume`. The current `Workflow` instance is not persisted; automatic handling would claim recovery that the system does not possess. Keep this behavior covered by library tests only, and state it as a blocked dependency in the runbook for the later durable workflow-instance plan.

Add:

```python
async def execute_spec(self, spec, *, initial_state, custom_step_builders=None):
    return await self.workflow_engine.execute_spec(
        spec, initial_state=initial_state, custom_step_builders=custom_step_builders
    )
```

to `WorkflowOrchestration`. Replace `WorkflowEngine(gateway=plane.gateway)` in automation handler with `plane.workflow_orchestration.execute_spec(...)`.

- [ ] **Step 4: Verify and commit**

```bash
rg -n -g '*.py' 'request_approval\(|find_by_run_and_action\(|\.get\(approval_id\)' packages/agent/workflows apps/cosa
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/workflows/test_approval_step.py tests/agent/workflows/test_workflow_governance.py tests/agent/workflows/test_full_workflow_integration.py tests/agent/workflows/test_automation_lifecycle.py tests/apps/cosa/worker/test_automation_uses_composed_workflow_engine.py -v
git add packages/agent/workflows/engine.py packages/agent/workflows/approval_step.py packages/agent/workflows/tool_step.py apps/cosa/composition/workflow_orchestration.py apps/cosa/worker/handlers.py tests/agent/workflows/test_approval_step.py tests/agent/workflows/test_workflow_governance.py tests/apps/cosa/worker/test_automation_uses_composed_workflow_engine.py
git commit -m "refactor(workflow): use composed gateway and durable approvals"
```

Expected: search is empty and Gateway still owns tool approval semantics.

---

### Task 5: Replace direct skill promotion with a Founder-reviewed change request

**Files:**

- Modify: `apps/cosa/api/skill_schemas.py`
- Modify: `apps/cosa/api/skill_registry_routes.py`
- Modify: `apps/cosa/api/workforce_routes.py`
- Test: `tests/apps/cosa/test_skill_registry_routes.py`
- Test: `tests/apps/cosa/test_workspace_custom_skill_isolation.py`
- Test: `tests/apps/cosa/api/test_workforce_authority_routes.py`

**Interfaces:**

- Consumes: Task 3 generic approval path.
- Produces: `POST /agent/skills/:skill_id/promote` returns `202 PENDING_APPROVAL` and never publishes synchronously.

- [ ] **Step 1: Write red API/authority tests**

```python
def test_promote_requests_approval_not_direct_publish(client: TestClient) -> None:
    skill_id = create_and_evaluate_candidate(client)
    response = client.post(f"/agent/skills/{skill_id}/promote", json={})
    assert response.status_code == 202
    assert response.json()["status"] == "PENDING_APPROVAL"
    assert get_candidate_status(client, skill_id) == "EVALUATED"

def test_only_founder_decides_promotion(client, app) -> None:
    approval_id = request_promotion(client)
    authenticate(app, workspace_id="ws-a", role_id="admin")
    assert client.post(decision_path(approval_id), json={"approved": True}).status_code == 403
    authenticate(app, workspace_id="ws-a", role_id="founder")
    assert client.post(decision_path(approval_id), json={"approved": True}).status_code == 200
```

Add negatives: foreign workspace 404; not evaluated, low-score, and unknown-capability candidates create no approval; repeated request returns same ID; request body `approved_by`, `approval_reason` or version is 422.

- [ ] **Step 2: Run red**

```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/test_skill_registry_routes.py tests/apps/cosa/test_workspace_custom_skill_isolation.py tests/apps/cosa/api/test_workforce_authority_routes.py -v
```

Expected: current route returns `PUBLISHED` in the HTTP request.

- [ ] **Step 3: Implement request-only contract**

Replace request schema with:

```python
class RequestSkillPromotionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
```

Require workspace operator, verify candidate/evaluation/capability inventory, compute server-side definition hash, then call `create_change_approval_request` with `requirement={"role": "founder"}`. Return:

```json
{"approval_id":"appr_...","status":"PENDING_APPROVAL","action":"promote_skill_candidate","candidate_id":"cand_...","definition_hash":"sha256:..."}
```

Do not mutate status, publisher, version or instructions. Decision endpoint retains `require_approval_authority` before persistence and may report `binding_kind/dispatch_state`, never `PUBLISHED`.

Split the existing decision endpoint by binding kind after its scoped lookup and authority check. For `TOOL_CALL`, preserve the current run stream event and `cosa.resume` scheduling behavior. For `CHANGE_REQUEST`, never call `get_scoped_run(None, ...)`, never emit a run stream event, and never schedule `cosa.resume`; return the persisted generic decision and its safe dispatch state. The Task-2 transaction is the only place a promotion approval gets its action outbox.

- [ ] **Step 4: Verify and commit**

```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/test_skill_registry_routes.py tests/apps/cosa/test_workspace_custom_skill_isolation.py tests/apps/cosa/api/test_workforce_authority_routes.py tests/apps/cosa/test_tenant_isolation.py -v
git add apps/cosa/api/skill_schemas.py apps/cosa/api/skill_registry_routes.py apps/cosa/api/workforce_routes.py tests/apps/cosa/test_skill_registry_routes.py tests/apps/cosa/test_workspace_custom_skill_isolation.py tests/apps/cosa/api/test_workforce_authority_routes.py
git commit -m "feat(skills): require founder approval before promotion"
```

---

### Task 6: Deliver approved promotion through a durable, idempotent worker action

**Files:**

- Create: `apps/cosa/worker/approval_actions.py`
- Modify: `apps/cosa/worker/main.py`
- Create: `packages/agent/migrations/007_skill_candidate_promotion_cas.sql`
- Create: `packages/agent/migrations/007_skill_candidate_promotion_cas.down.sql`
- Modify: `packages/agent/skills/contracts.py`
- Modify: `packages/agent/skills/candidate_store.py`
- Test: `tests/apps/cosa/worker/test_approval_actions.py`
- Test: `tests/apps/cosa/worker/test_main.py`
- Test: `tests/agent/skills/test_candidate_promotion_cas.py`
- Test: `tests/agent/skills/test_candidate_promotion_migration.py`

**Interfaces:**

- Consumes: Task-2 outbox, Task-3 verifier, Task-5 decision.
- Produces: `relay_approved_actions` and `execute_skill_candidate_promotion`.

- [ ] **Step 1: Write red retry and stale-subject tests**

```python
@pytest.mark.asyncio
async def test_retry_publishes_once(plane) -> None:
    approval_id = await approved_promotion(plane, workspace_id="ws-a", candidate_id="cand-1")
    await relay_approved_actions(plane, worker_id="relay-a", limit=10)
    payload = await only_scheduled_task(plane.scheduler, task_type="approval_action")
    await execute_skill_candidate_promotion(plane, payload)
    await execute_skill_candidate_promotion(plane, payload)
    candidate = await candidate_store.get_candidate("ws-a", "cand-1")
    assert candidate.status is SkillStatus.PUBLISHED
    assert candidate.promotion_approval_id == approval_id
    assert candidate.definition_hash == "sha256:candidate-v1"

@pytest.mark.asyncio
async def test_worker_refuses_changed_candidate(plane) -> None:
    payload = await approved_promotion(plane, workspace_id="ws-a", candidate_id="cand-1")
    await replace_candidate_instruction("ws-a", "cand-1", "different")
    assert (await execute_skill_candidate_promotion(plane, payload)).reason_code == "APPROVAL_SUBJECT_STALE"
```

Add concurrent relay, rejected approval, foreign workspace payload and one-event-after-retry tests.

- [ ] **Step 2: Run red**

```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/worker/test_approval_actions.py tests/apps/cosa/worker/test_main.py tests/agent/skills/test_candidate_promotion_cas.py -v
```

Expected: relay, runless worker branch and candidate CAS do not exist.

- [ ] **Step 3: Create the candidate persistence contract before worker code**

`PostgresSkillCandidateStore` already references `agent_skill_candidates`, but no agent-plane migration creates it. Create the table if absent and safely add the following columns when a manually-provisioned older table exists: `definition_hash`, `promotion_approval_id`, `promotion_definition_hash`, `published_at`, `created_at`, and `updated_at`. Give `(workspace_id, candidate_id)` a unique key and `promotion_approval_id` a partial unique index. Do the same schema baseline for `agent_skill_feedback` because the store writes it.

Extend `SkillCandidate` with metadata fields outside `proposed_skill`:

```python
definition_hash: str | None = None
promotion_approval_id: str | None = None
promotion_definition_hash: str | None = None
```

`save_candidate` must compute and persist the canonical `proposed_skill.compute_hash()` on every create or semantic update; route code always uses this server-computed value as the approval subject hash. The down migration refuses if a promotion approval, published candidate, or feedback evidence exists; it must not destroy audit/promotion evidence.

- [ ] **Step 4: Implement relay and worker**

Relay claims outbox rows with fencing and schedules:

```python
{
    "task_type": "approval_action",
    "approval_id": approval.approval_id,
    "workspace_id": approval.workspace_id,
    "action": approval.action,
    "subject_kind": approval.subject_kind,
    "subject_ref": approval.subject_ref,
    "subject_hash": approval.subject_hash,
}
```

Use coalescing key `approval-action:<approval_id>` and mark delivered only after scheduling succeeds. In `dispatch_one_task` handle `approval_action` before `run_id` is mandatory. Reject any action other than `promote_skill_candidate/skill_candidate` with `UNSUPPORTED_APPROVAL_ACTION`.

The action handler calls `verify_change_execution`, recomputes candidate hash, repeats evaluation/capability validation and invokes `publish_candidate_if_approved`. The Postgres store uses one transaction with `UPDATE ... WHERE workspace_id = :workspace_id AND candidate_id = :candidate_id AND status = 'EVALUATED' AND definition_hash = :expected_definition_hash AND promotion_approval_id IS NULL`; it sets the top-level promotion metadata and the proposed skill's published status without adding approval data to `SkillSpec.references` (which would change its hash). An already-published row is success only if both approval ID and definition hash match; all other rows refuse. Append only opaque `approval.action.completed` or `approval.action.rejected` events.

- [ ] **Step 5: Verify and commit**

```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/worker/test_approval_actions.py tests/apps/cosa/worker/test_main.py tests/agent/skills/test_candidate_promotion_cas.py tests/agent/skills/test_candidate_promotion_migration.py tests/apps/cosa/test_workspace_custom_skill_isolation.py -v
make migration-compat-check
git add apps/cosa/worker/approval_actions.py apps/cosa/worker/main.py packages/agent/migrations/007_skill_candidate_promotion_cas.sql packages/agent/migrations/007_skill_candidate_promotion_cas.down.sql packages/agent/skills/contracts.py packages/agent/skills/candidate_store.py tests/apps/cosa/worker/test_approval_actions.py tests/apps/cosa/worker/test_main.py tests/agent/skills/test_candidate_promotion_cas.py tests/agent/skills/test_candidate_promotion_migration.py
git commit -m "feat(skills): dispatch approved promotions durably"
```

---

### Task 7: Delete only proven duplicate coordination primitives

**Files:**

- Delete: `packages/agent/coordination/{approval_gate,delegate,parallel,quality_gate,risk_classification,supervisor,synthesis}.py`
- Modify: `packages/agent/coordination/__init__.py`
- Delete: `tests/agent/coordination/test_coordination_primitives.py`
- Modify: `tests/agent/workflows/test_dag_engine.py`

**Interfaces:**

- Consumes: Tasks 4–6.
- Produces: no duplicate supervisor/delegate/parallel/approval surface; scheduler and retained modules untouched.

- [ ] **Step 1: Write a failing import-boundary test**

```python
def test_application_has_no_legacy_coordination_imports() -> None:
    forbidden = (
        "agent.coordination.approval_gate", "agent.coordination.delegate",
        "agent.coordination.parallel", "agent.coordination.quality_gate",
        "agent.coordination.risk_classification", "agent.coordination.supervisor",
        "agent.coordination.synthesis",
    )
    text = "\n".join(
        path.read_text() for root in (Path("apps"), Path("packages"))
        for path in root.rglob("*.py") if "coordination" not in path.parts
    )
    assert not any(name in text for name in forbidden)
```

- [ ] **Step 2: Confirm zero production callers**

```bash
rg -n -g '*.py' 'agent\.coordination\.(approval_gate|delegate|parallel|quality_gate|risk_classification|supervisor|synthesis)' apps packages --glob '!packages/agent/coordination/**'
```

Expected: no output. Any caller stops deletion; replace it through its own red-green change, never with a compatibility export.

- [ ] **Step 3: Delete scoped modules only**

Set `__init__.py` to:

```python
"""Coordination support modules retained outside the workflow orchestration path."""

from __future__ import annotations
```

Do not delete `scheduler.py`, `control_plane_scheduler_client.py`, `delegation_envelope.py`, `durable_supervisor.py`, `expansion.py` or `wait_resolver.py`.

- [ ] **Step 4: Verify and commit**

```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/workflows/test_steps.py tests/agent/workflows/test_dag_engine.py tests/agent/workflows/test_engine.py tests/agent/coordination/test_control_plane_scheduler_client.py tests/agent/coordination/test_durable_supervisor_workflow.py tests/agent/p1/test_wait_resolver.py tests/agent/p1/test_expansion_fingerprint.py -v
rg -n -g '*.py' 'agent\.coordination\.(approval_gate|delegate|parallel|quality_gate|risk_classification|supervisor|synthesis)' apps packages tests
git add -u packages/agent/coordination tests/agent/coordination
git add tests/agent/workflows/test_dag_engine.py
git commit -m "refactor(agent): remove duplicate coordination primitives"
```

Expected: all tests pass and final search has no output.

---

### Task 8: Prove recovery with disposable PostgreSQL and real process restart

**Files:**

- Create: `tests/e2e/test_unified_approval_process_recovery.py`
- Modify: `Makefile`
- Modify: `docs/operations/executive-advisory-board-runbook.md`
- Modify: `docs/features/approvals.md`
- Test: `tests/e2e/test_event_approval_restart.py`

**Interfaces:**

- Consumes: Tasks 2–7.
- Produces: `make unified-approval-verify` and truthful operator states.

- [ ] **Step 1: Write three process E2E cases**

```python
def test_tool_call_resume_only_runs_matching_invocation(stack):
    # Create two tool calls, approve one exact tuple, restart API/worker.
    # Only that invocation may execute.

def test_promotion_recovers_between_decision_and_action(stack):
    # Stop after durable outbox insert, restart API/worker, relay and execute.
    # Assert PUBLISHED once and exactly one completion event.

def test_promotion_rejects_foreign_or_stale_subject_after_restart(stack):
    # Forge foreign workspace payload and mutate candidate after approval.
    # Neither may publish.
```

The fixture must use disposable Postgres plus separate API and worker subprocesses. A second repository instance inside one process is not restart evidence.

- [ ] **Step 2: Run red**

```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/e2e/test_unified_approval_process_recovery.py -v
```

Expected: fails until Tasks 2–7 exist.

- [ ] **Step 3: Add the narrow gate and runbook state model**

```make
unified-approval-verify:
	$(VENV_PYTHON) -m pytest tests/agent/capabilities/test_change_request_approval.py tests/agent/runs/test_unified_approval_repository.py tests/agent/runs/test_unified_approval_migration.py tests/apps/cosa/worker/test_approval_actions.py tests/e2e/test_unified_approval_process_recovery.py -v
```

Document:

```text
PENDING_APPROVAL -> APPROVED_DISPATCH_PENDING -> ACTION_RUNNING -> PUBLISHED
PENDING_APPROVAL -> REJECTED
APPROVED_DISPATCH_PENDING | ACTION_RUNNING -> FAILED_REQUIRES_ATTENTION
```

`APPROVED` never means `PUBLISHED`. Runbook queries only IDs, actor, status, hash and safe reason from approvals/events/outbox.

- [ ] **Step 4: Final verification and commit**

```bash
make unified-approval-verify
make agent-test
make apps-cosa-test
make migration-compat-check
make boundary-check
make ts-suppression-check
git diff --check
git status --short
git add tests/e2e/test_unified_approval_process_recovery.py Makefile docs/operations/executive-advisory-board-runbook.md docs/features/approvals.md
git commit -m "test(approval): prove unified approval recovery"
```

Expected: all gates pass. If subprocess/Postgres proof is blocked, report the exact prerequisite and do not claim durable recovery.

---

## Coverage review

| Requirement | Tasks |
| --- | --- |
| Giai đoạn 1 hard precondition | 1 |
| Preserve live scheduler contract | 1, 7 |
| One composed workflow engine | 4 |
| Gateway is the only tool-effect path | 4 |
| One ledger for tool and change approval | 2, 3 |
| Exact tool binding is retained | 2, 3, 4, 8 |
| Founder-reviewed hash-pinned promotion | 3, 5, 6 |
| Stale, tenant, retry and recovery proof | 2, 5, 6, 8 |
| Generic workflow gate stays library-only until durable instance design | Global Constraints, 4 |
| No B.2/B.4 or role scope leak | Global Constraints, 1 |

## Execution order

1. Task 1 is a hard stop gate.
2. Tasks 2–3 establish durable state before public contract changes.
3. Task 4 removes broken workflow approval shims without widening authority.
4. Tasks 5–6 create the first real non-tool approval consumer.
5. Task 7 is an isolated destructive cleanup commit.
6. Task 8 is the only sufficient evidence for recovery; static/unit checks are not substitutes.
