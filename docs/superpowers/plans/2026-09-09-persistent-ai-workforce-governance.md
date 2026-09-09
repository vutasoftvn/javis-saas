# Persistent AI Workforce, Task Outcome & Skill Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây workforce AI có nhân sự cố định, Outcome Contract bắt buộc ngay khi tạo task, phân tích outcome cho mọi task, queue/review có trách nhiệm rõ ràng và Skill Governance do founder kiểm soát.

**Architecture:** Company Plane là nguồn sự thật cho task, Outcome Contract, task result, KR contribution, work package, review và thứ tự queue. Agent Platform giữ identity AI employee, assignment/spec/skill pin, run governance, deterministic outcome-analysis dispatch và read model scorecard. Hai plane liên kết bằng opaque IDs, signed events và delegation hẹp; không có foreign key xuyên database hay Agent Platform ghi trực tiếp business DB.

**Tech Stack:** Encore TypeScript + Drizzle/PostgreSQL, FastAPI/Python + SQLAlchemy/PostgreSQL, Flutter/GetX + MvpRequestClient, signed Company outbox/COSA intake, pytest, Vitest và Flutter widget tests.

**Spec:** [Persistent AI Workforce Governance design](../specs/2026-09-09-persistent-ai-workforce-governance-design.md)

## Global Constraints

- Làm trực tiếp trên `main`; không sửa thay đổi sẵn có ngoài phạm vi.
- Migration only expand-first. Run/assignment lịch sử vẫn đọc được; có down migration cho mọi cột/bảng mới.
- Business truth nằm tại `services/company`; `apps/cosa` chỉ dispatch bằng delegation có scope workspace/run/capability.
- `agent_instance_id` unique trong workspace, bền vững và không tái sử dụng. Display name/functional key không là authority.
- Một attempt chỉ có một employee. Reassign tạo attempt mới, không đổi attempt cũ.
- DRAFT chỉ dành cho AI proposal hoặc input thiếu. Manager/founder create với contract hợp lệ, hoặc xác nhận AI proposal, phải atomically tạo task + CONFIRMED contract + initial work package QUEUED; exception founder có expiry/audit.
- Non-BAU task phải liên kết KR qua Initiative được approved; BAU phải có service objective/SLO. Không tự cộng hoặc ghi `KR.actualValue` từ LLM assessment.
- `AUTO_ALL_TASKS` tạo một `TASK_OUTCOME` analysis request cho mỗi result revision hợp lệ. Router server chọn exact employee/assignment/spec/skill; agent không tự nhận job bằng prompt/tool discovery.
- Outcome Analyst chỉ có read capability và narrow assessment record capability; không advance task, review thay người, đổi priority hay write KR.
- Manager tạo package hợp lệ vào queue. Scheduler chỉ dùng `effective_priority`; founder override lưu event bất biến gồm actor/reason.
- Không auto-accept. Review của manager/founder mới tạo outcome nghiệp vụ và scorecard.
- Server suy workspace/principal/role từ identity; mọi command dùng idempotency key và optimistic/CAS version.
- Không đưa credential, raw prompt nhạy cảm hoặc delegation token vào event, scorecard hay UI.
- Không kết luận release-ready từ lint/mock; final gate dùng disposable PostgreSQL và process E2E.

## File Map

| Vùng | File | Vai trò |
|---|---|---|
| Employee | `packages/agent/migrations/033_persistent_workforce_employees.sql`, `packages/agent/workforce/{models,repository}.py` | Identity bền vững, assignment pin, suspend/retire. |
| Outcome contract | `services/company/operations/migrations/51_task_outcome_contracts.*`, `services/company/operations/services/task-outcome-contract.service.ts` | Expected outcome, KR lineage, criteria, evidence, revision và queue gate. |
| Work | `services/company/operations/migrations/52_ai_work_packages.*`, `services/company/operations/services/work-package.service.ts` | Package, attempt, queue, review và event là business truth. |
| Outcome analysis | `skillpacks/operations/task-outcome-analysis/*`, `services/company/operations/services/task-result.service.ts`, `apps/cosa/worker/outcome_analysis_run.py` | Result revision, request/assessment, pinned skill và narrow capability. |
| Runtime | `apps/cosa/events/*`, `apps/cosa/worker/work_package_run.py`, `packages/agent/runs/*` | Signed dispatch, lease, attribution, checkpoint-safe reassign. |
| Governance | `apps/cosa/api/workforce_*.py`, `apps/cosa/api/skill_registry_routes.py`, `packages/agent/workforce/*` | Delegation, scorecard, investigation và skill publish governance. |
| Experience | `shared/contracts/mvp-surface.json`, `frontend/lib/modules/agents/*`, `frontend/lib/modules/hologram_hub/*` | Task outcome, queue, review, employee profile, founder escalation và Skill Governance. |

---

### Task 1: Persistent AI employee identity and assignment linkage

**Files:**
- Create: `packages/agent/migrations/033_persistent_workforce_employees.sql`
- Create: `packages/agent/migrations/033_persistent_workforce_employees.down.sql`
- Modify: `packages/agent/workforce/models.py`
- Modify: `packages/agent/workforce/repository.py`
- Test: `tests/agent/workforce/test_employee_repository.py`

**Interfaces:**

```python
@dataclass(frozen=True)
class WorkforceEmployeeRecord:
    agent_instance_id: UUID
    workspace_id: str
    employee_code: str
    display_name: str
    status: Literal["ACTIVE", "SUSPENDED", "RETIRED"]
    created_by: str

async def create_employee(workspace_id: str, employee_code: str, display_name: str, created_by: str) -> WorkforceEmployeeRecord:
    raise NotImplementedError

async def suspend_employee(workspace_id: str, agent_instance_id: UUID | str) -> WorkforceEmployeeRecord | None:
    raise NotImplementedError

async def retire_employee(workspace_id: str, agent_instance_id: UUID | str) -> WorkforceEmployeeRecord | None:
    raise NotImplementedError
```

- [ ] **Step 1: Write failing repository tests.**

```python
async def test_employee_code_is_unique_and_identity_is_not_reused() -> None:
    first = await repo.create_employee("ws_a", "AGT-FIN-001", "Finance Analyst #1", "founder_a")
    with pytest.raises(DuplicateEmployeeCodeError):
        await repo.create_employee("ws_a", "AGT-FIN-001", "Other", "founder_a")
    retired = await repo.retire_employee("ws_a", first.agent_instance_id)
    assert retired.status == "RETIRED"
    assert await repo.get_employee("ws_a", first.agent_instance_id) == retired
```

- [ ] **Step 2: Run test red.**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/workforce/test_employee_repository.py -v`

Expected: FAIL because employee persistence does not exist.

- [ ] **Step 3: Add Agent DB migration and typed repository.**

Create `agent.workforce_employees` with `agent_instance_id UUID PRIMARY KEY`, workspace, code, display name, status, creator and timestamps, plus `UNIQUE(workspace_id, employee_code)`. Add nullable `agent_instance_id` to `agent.workforce_assignments`, status indexes and deterministic backfill `LEGACY-<assignment UUID>` only for active assignments. Implement the exact CRUD methods in the protocol plus in-memory/Postgres repositories. `create_assignment` requires an ACTIVE employee.

- [ ] **Step 4: Verify persistence and commit.**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/workforce/test_employee_repository.py -q`

Expected: uniqueness and lifecycle persist; suspended/retired employee cannot receive a new assignment. Public API is intentionally deferred to Task 6 because exact founder delegation must exist first.

Commit: `feat(workforce): add persistent AI employee identity`

---

### Task 1A: Outcome Contract atomically created with every task

**Files:**
- Create: `services/company/operations/migrations/51_task_outcome_contracts.up.sql`
- Create: `services/company/operations/migrations/51_task_outcome_contracts.down.sql`
- Modify: `services/company/shared/db/schema/operations.ts`
- Create: `services/company/operations/services/task-outcome-contract.service.ts`
- Modify: `services/company/operations/services/task.service.ts`
- Modify: `services/company/operations/handlers/task.handler.ts`
- Modify: `services/company/operations/strategy/services/project-kickoff-materialize.service.ts`
- Test: `services/company/operations/tests/task-outcome-contract.service.test.ts`
- Test: `services/company/operations/tests/task.service.test.ts`
- Test: `services/company/operations/tests/project-kickoff-materialize.test.ts`

**Interfaces:**

```ts
export type TaskOutcomeType = "DIRECT_KR" | "ENABLING_KR" | "VALIDATION" | "BAU";
export type TaskOutcomeContractStatus = "DRAFT" | "CONFIRMED" | "SUPERSEDED";

export interface CreateTaskOutcomeContractInput {
  workspaceId: string;
  taskId: string;
  outcomeType: TaskOutcomeType;
  expectedOutcome: string;
  acceptanceCriteria: Record<string, unknown>;
  expectedEvidenceRefs: string[];
  impactHypothesis: string;
  primaryKrId?: string;
  secondaryKrLinks?: Array<{ keyResultId: string; relationType: "DIRECT" | "ENABLING" | "VALIDATION" }>;
  serviceObjective?: string;
}

export async function createTaskOutcomeProposal(
  input: CreateTaskOutcomeContractInput & { proposedByAgentInstanceId: string },
  ctx: TenantContext,
): Promise<TaskOutcomeContractView>;

export async function validateTaskOutcomeContractForQueue(
  contractId: string,
  ctx: TenantContext,
): Promise<ValidatedTaskOutcomeContract>;
```

- [ ] **Step 1: Write failing transaction and policy tests.**

```ts
it("stores an AI suggestion as a draft proposal with no queue entry", async () => {
  const proposal = await createTaskOutcomeProposal({
    workspaceId: wsId,
    taskId: proposedTaskId,
    outcomeType: "VALIDATION",
    expectedOutcome: "Ten interview records and one evidence-backed decision",
    acceptanceCriteria: { interviews: 10, decision: true },
    expectedEvidenceRefs: [],
    impactHypothesis: "Validate the highest-risk onboarding assumption",
    primaryKrId: krId,
    proposedByAgentInstanceId: "agent_1",
  }, systemProposalCtx);
  expect(proposal).toMatchObject({
    status: "DRAFT", outcomeType: "VALIDATION", primaryKrId: krId,
  });
  await expect(assertTaskCanEnterQueue(proposedTaskId, managerCtx)).rejects.toThrow(/Outcome Contract/i);
});

it("validates a strategic contract but does not expose confirmation before atomic queue creation exists", async () => {
  const proposal = await seedDraftOutcomeProposal({ initiativeId, primaryKrId: krId });
  await expect(validateTaskOutcomeContractForQueue(proposal.id, managerCtx)).resolves.toMatchObject({
    initiativeId, primaryKrId: krId,
  });
  await expect(assertTaskCanEnterQueue(proposal.taskId, managerCtx)).rejects.toThrow(/Outcome Contract/i);
});

it("requires a service objective for BAU and does not invent one for legacy tasks", async () => {
  await expect(createDraftContract({ outcomeType: "BAU", serviceObjective: undefined })).rejects.toThrow(/service objective/i);
  expect((await loadLegacyTask(legacyTaskId)).outcomeContract).toBeNull();
});
```

- [ ] **Step 2: Run the tests to verify they fail.**

Run: `cd services/company && encore test operations/tests/task-outcome-contract.service.test.ts operations/tests/task.service.test.ts operations/tests/project-kickoff-materialize.test.ts`

Expected: FAIL because the contract schema, queue gate and typed input do not exist.

- [ ] **Step 3: Add the expand-only Company schema and typed contract service.**

Create `operating.task_outcome_contracts` with Snowflake ID, workspace/task,
revision, status, outcome type, expected outcome, structured acceptance criteria,
evidence refs, measurement plan, impact hypothesis, service objective, creator,
confirmer, timestamps, `supersedes_contract_id` and version. Create
`operating.task_outcome_kr_links` with workspace, contract, KR, relation type and
one partial unique primary-KR index. Add nullable `active_outcome_contract_id` to
`operating.tasks` and `draft` to the task status constraint. Do not backfill a
fictional contract for historical rows.

Implement the functions in `task-outcome-contract.service.ts`: validate all KR
IDs against workspace; require an APPROVED Initiative for non-BAU tasks; require
one primary KR for non-BAU and `serviceObjective` for BAU; reject a KR not linked
to the Initiative; create AI-origin revision one as `DRAFT`; and append a new
revision, never update confirmed fields in place. `validateTaskOutcomeContractForQueue`
returns the validated immutable contract facts without changing status. Public
manager/founder confirmation remains disabled until Task 2 can atomically create
the initial queue package.

- [ ] **Step 4: Wire creation, kickoff materialization and the queue guard.**

Add the internal AI proposal path only: it inserts a task proposal and its DRAFT
contract, never a queue item. Materialize each week-one AI-suggested action as
its own DRAFT VALIDATION proposal derived from the week outcome; do not reuse the
project outcome as a task outcome. Add `assertTaskCanEnterQueue` to reject a
missing, draft, superseded or foreign contract, and reject any confirmed task
without an initial work package. Task 2 is the first public manager/founder
creation/confirmation command, precisely so a confirmed task never pauses at
TODO/DRAFT.

- [ ] **Step 5: Run focused green tests and Company safety gates.**

Run: `cd services/company && encore test operations/tests/task-outcome-contract.service.test.ts operations/tests/task.service.test.ts operations/tests/project-kickoff-materialize.test.ts && npm run typecheck && cd ../.. && make company-boundary-check && make encore-handler-boundary-check && make ts-suppression-check`

Expected: PASS. AI proposals remain drafts with no queue item, contract validation
is tenant/CAS safe, BAU/non-BAU constraints hold, kickoff suggestions receive
independent contracts and no historical task is silently rewritten.

- [ ] **Step 6: Commit the independently reviewable slice.**

Commit: `feat(operations): require versioned outcome contracts for tasks`

---

### Task 2: Company-owned work packages, attempts and immutable events

**Files:**
- Create: `services/company/operations/migrations/52_ai_work_packages.up.sql`
- Create: `services/company/operations/migrations/52_ai_work_packages.down.sql`
- Modify: `services/company/shared/db/schema/operations.ts`
- Modify: `services/company/operations/services/task.service.ts`
- Create: `services/company/operations/services/work-package.service.ts`
- Modify: `services/company/operations/handlers/task.handler.ts`
- Create: `services/company/operations/handlers/work-package.handler.ts`
- Modify: `services/company/operations/handlers/index.ts`
- Test: `services/company/operations/tests/work-package.service.test.ts`
- Test: `services/company/operations/tests/work-package.handler.test.ts`

**Interfaces:**

```ts
type WorkPackageStatus =
  | "QUEUED" | "LEASED" | "RUNNING" | "VALIDATION_PASSED"
  | "PENDING_MANAGER_REVIEW" | "ESCALATED_TO_FOUNDER"
  | "ACCEPTED" | "REWORK" | "REJECTED" | "BLOCKED" | "ON_HOLD" | "CANCELLED";

createWorkPackage(input: {
  taskId: string; outcomeContractId: string; assignedAgentInstanceId: string;
  requestedPriority: "P0" | "P1" | "P2" | "P3"; objective: string;
  outputContract: Record<string, unknown>; acceptanceRubric: Record<string, number>;
  idempotencyKey: string;
}, ctx: TenantContext): Promise<WorkPackageView>

createConfirmedTaskAndQueue(input: {
  task: { title: string; initiativeId?: string; priority: "P0" | "P1" | "P2" | "P3" };
  contract: CreateTaskOutcomeContractInput;
  initialPackage: { assignedAgentInstanceId: string; objective: string; outputContract: Record<string, unknown>; acceptanceRubric: Record<string, number> };
  idempotencyKey: string;
}, ctx: TenantContext): Promise<{ task: Task; contract: TaskOutcomeContractView; workPackage: WorkPackageView }>;

confirmAiProposalAndQueue(input: {
  proposalTaskId: string; draftContractId: string;
  contractPatch: Partial<CreateTaskOutcomeContractInput>;
  initialPackage: { assignedAgentInstanceId: string; objective: string; outputContract: Record<string, unknown>; acceptanceRubric: Record<string, number> };
  expectedVersion: number; idempotencyKey: string;
}, ctx: TenantContext): Promise<{ task: Task; contract: TaskOutcomeContractView; workPackage: WorkPackageView }>;
reassignWorkPackage(input, ctx): Promise<WorkPackageView>
```

- [ ] **Step 1: Write failing state-machine tests.**

```ts
it("queues one package with one accountable first attempt only after a confirmed task contract", async () => {
  const item = await createWorkPackage({ taskId, outcomeContractId, assignedAgentInstanceId: "agent_1", requestedPriority: "P1", objective: "x", outputContract: { evidence: ["artifact"] }, acceptanceRubric: { correct: 5 }, idempotencyKey: "wp-1" }, managerCtx);
  expect(item).toMatchObject({ status: "QUEUED", requestedPriority: "P1", effectivePriority: "P1" });
  expect(await listAttempts(item.workPackageId)).toHaveLength(1);
});

it("does not permit two active attempts", async () => {
  await expect(createAttemptForActivePackage(packageId)).rejects.toThrow(/active attempt/i);
});

it("queues a manager-confirmed AI proposal without leaving a confirmed task in draft", async () => {
  const result = await confirmAiProposalAndQueue({
    proposalTaskId, draftContractId, contractPatch: {},
    initialPackage: { assignedAgentInstanceId: "agent_1", objective: "Interview 10 users", outputContract: { evidence: ["interview"] }, acceptanceRubric: { completeness: 5 } },
    expectedVersion: 1, idempotencyKey: "confirm-proposal-1",
  }, managerCtx);
  expect(result.contract.status).toBe("CONFIRMED");
  expect(result.workPackage.status).toBe("QUEUED");
  expect(await listWorkPackagesForTask(result.task.id)).toHaveLength(1);
});
```

- [ ] **Step 2: Run test red.**

Run: `cd services/company && encore test operations/tests/work-package.service.test.ts`

Expected: FAIL because the work-package module is absent.

- [ ] **Step 3: Add schema and service.**

Create `operating.task_work_packages`, `operating.work_package_attempts`, and `operating.work_package_events`. Keep Company IDs as Snowflake `BIGINT`; store Agent references as opaque `TEXT`. Require `outcome_contract_id` to be the task's current CONFIRMED contract in the same workspace. Add partial unique index `work_package_id WHERE ended_at IS NULL` and queue index `(workspace_id, status, effective_priority, due_at, queued_at)`. `work_package_events` is append-only: type, actor, before/after JSON, reason, correlation ID and timestamp.

- [ ] **Step 4: Implement commands and handlers.**

`createConfirmedTaskAndQueue` is the public manager/founder command: in one Company transaction it creates a normal task, creates or promotes its exact Outcome Contract to CONFIRMED, inserts initial work package status QUEUED, creates attempt sequence one and writes task/contract/package events. `confirmAiProposalAndQueue` first applies the manager's patch as a new confirmed contract revision, then follows the same transaction; it never leaves a confirmed proposal at DRAFT or TODO. Queue is physically represented by the initial work package, so the task UI is immediately labelled Queued. `createWorkPackage` calls `assertTaskCanEnterQueue` first and validates workspace task ownership, exact confirmed contract, objective/output contract/rubric, P0–P3 priority, dependencies and budget. It records `agent_instance_id` as opaque attribution but no live dispatch is enabled until Task 3 adds the eligibility fact. `reassignWorkPackage` checks expected version, closes old unleased attempt, creates next attempt and writes old/new attribution. If leased/running it records only `reassignment_requested`. Handlers use `requireWorkspaceAccess`; they never accept caller ID/workspace as authority.

- [ ] **Step 5: Verify and commit.**

Run: `cd services/company && encore test operations/tests/work-package.service.test.ts operations/tests/work-package.handler.test.ts`

Expected: direct manager/founder creation and AI-proposal confirmation each create one confirmed contract plus one queued package atomically; duplicate idempotency returns the original result; foreign manager is denied; concurrent active attempt conflicts.

Commit: `feat(operations): add accountable AI work packages`

---

### Task 3: Eligibility projection and signed Company-to-Agent dispatch

**Files:**
- Create: `apps/cosa/events/workforce_employee_contract.py`
- Modify: `apps/cosa/events/router.py`
- Modify: `apps/cosa/events/event_run_contract.py`
- Modify: `services/company/events/event-types.ts`
- Modify: `services/company/events/outbox-relay.service.ts`
- Modify: `services/company/operations/services/work-package.service.ts`
- Test: `tests/apps/cosa/events/test_workforce_employee_contract.py`
- Test: `services/company/operations/tests/work-package-dispatch.test.ts`

**Interfaces:**

```python
@dataclass(frozen=True)
class WorkPackageDispatch:
    workspace_id: str
    work_package_id: str
    work_attempt_id: str
    agent_instance_id: str
    assignment_id: str
    effective_priority: str
    correlation_id: str

def adapt_work_package_dispatch(payload: dict[str, object]) -> tuple[WorkPackageDispatch | None, str | None]:
    raise NotImplementedError
```

- [ ] **Step 1: Write signed-dispatch negative tests.**

```python
def test_rejects_missing_or_mismatched_workforce_attribution() -> None:
    dispatch, error = adapt_work_package_dispatch({"work_package_id": "wp_1"})
    assert dispatch is None
    assert error == "missing_workforce_attribution"

def test_duplicate_signed_event_creates_one_scheduled_attempt() -> None:
    assert schedule_once(signed_event) == "scheduled"
    assert schedule_once(signed_event) == "duplicate"
```

- [ ] **Step 2: Run test red.**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/events/test_workforce_employee_contract.py -v`

Expected: FAIL because the adapter does not exist.

- [ ] **Step 3: Introduce event and eligibility fact.**

Add `operating.work_package.queued.v1` and `operating.work_package.reassign_requested.v1`. Payload only carries opaque IDs, priority, expected capability refs and correlation ID. Existing HMAC intake verifies signature/schema/workspace and deduplicates inbox. Add an authenticated internal lookup returning exact employee lifecycle, assignment/spec pin, capability boundary and capacity. It returns facts, never runtime credentials.

- [ ] **Step 4: Fail closed before Company queues.**

Company calls the existing allowlisted Control Plane client before creating or reassigning an attempt. Timeout, foreign employee, missing capability or non-ACTIVE status returns typed 409/503 and writes no new attempt. Persist the returned assignment/spec snapshot on the attempt.

- [ ] **Step 5: Verify and commit.**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/events/test_workforce_employee_contract.py -q && cd services/company && encore test operations/tests/work-package-dispatch.test.ts events/tests/outbox-relay.test.ts`

Expected: invalid attribution is rejected; duplicate delivery creates one dispatch; Company cannot queue a suspended or foreign employee.

Commit: `feat(workforce): dispatch queued packages with pinned attribution`

---

### Task 4: Queue lease, durable run provenance and checkpoint-safe reassignment

**Files:**
- Create: `apps/cosa/worker/work_package_run.py`
- Modify: `apps/cosa/worker/handlers.py`
- Modify: `apps/cosa/worker/run_core.py`
- Modify: `packages/agent/runs/models.py`
- Modify: `packages/agent/runs/repository.py`
- Create: `packages/agent/migrations/034_run_workforce_attribution.sql`
- Create: `packages/agent/migrations/034_run_workforce_attribution.down.sql`
- Test: `tests/apps/cosa/worker/test_work_package_run.py`
- Test: `tests/agent/runs/test_workforce_attribution.py`

**Interfaces:**

```python
class WorkforceRunAttribution(BaseModel):
    agent_instance_id: str
    assignment_id: str
    work_package_id: str
    work_attempt_id: str

async def execute_work_package_task(plane: CosaAgentPlane, stream_mgr: Any, payload: dict[str, object]) -> None:
    raise NotImplementedError
```

- [ ] **Step 1: Write failing worker tests.**

```python
async def test_run_keeps_exact_employee_package_attempt_attribution() -> None:
    await execute_work_package_task(plane, stream, valid_payload)
    run = await plane.repository.get_run(valid_payload["run_id"])
    assert run.workforce_attribution.work_attempt_id == valid_payload["work_attempt_id"]

async def test_reassignment_waits_checkpoint_and_does_not_transfer_approval() -> None:
    await run_until_waiting_approval(plane=plane, run_id=old_attempt_run_id)
    await request_reassign(work_package_id="wp_1", target_employee_id="agent_2")
    assert old_approval.run_id == old_attempt_run_id
    assert new_attempt.run_id != old_attempt_run_id
```

- [ ] **Step 2: Run test red.**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/worker/test_work_package_run.py tests/agent/runs/test_workforce_attribution.py -v`

Expected: FAIL because attribution/worker path do not exist.

- [ ] **Step 3: Implement durable linkage and worker lifecycle.**

Add nullable attribution columns to `agent.runs` and every Postgres mapping. Existing non-workforce runs remain null. The worker rejects a workforce payload without all four IDs or mismatched signed assignment. It claims exact work attempt through short-lived `operations.work_package.claim` delegation, calls `LEASED → RUNNING`, runs kernel and transitions only to `VALIDATION_PASSED → PENDING_MANAGER_REVIEW` or `BLOCKED`; it never calls business `ACCEPTED`.

- [ ] **Step 4: Apply hold/cancel/reassign at safe boundaries.**

Before external/write tool calls and at checkpoints, read current attempt control state. `ON_HOLD`/`CANCELLED` use durable CAS stop. `reassignment_requested` ends old attempt after checkpoint and emits new dispatch; pending approval remains bound to old `run_id + tool_call_id + checkpoint_ref`.

- [ ] **Step 5: Verify and commit.**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/worker/test_work_package_run.py tests/agent/runs/test_workforce_attribution.py tests/apps/cosa/wga/test_wga_run.py -q`

Expected: one lease, immutable provenance, technical completion awaits review, WGA regression suite passes.

Commit: `feat(agent): run work packages with durable employee attribution`

---

### Task 4A: Versioned task results and deterministic Outcome Analysis dispatch

**Files:**
- Create: `services/company/operations/migrations/53_task_outcome_analysis.up.sql`
- Create: `services/company/operations/migrations/53_task_outcome_analysis.down.sql`
- Create: `packages/agent/migrations/035_outcome_analysis_bindings.sql`
- Create: `packages/agent/migrations/035_outcome_analysis_bindings.down.sql`
- Create: `packages/agent/workforce/outcome_analysis.py`
- Modify: `packages/agent/workforce/repository.py`
- Modify: `services/company/shared/db/schema/operations.ts`
- Create: `services/company/operations/services/task-result.service.ts`
- Create: `services/company/operations/services/task-outcome-analysis.service.ts`
- Create: `services/company/operations/handlers/task-result.handler.ts`
- Create: `services/company/operations/handlers/task-outcome-analysis.handler.ts`
- Modify: `services/company/operations/handlers/index.ts`
- Create: `skillpacks/operations/task-outcome-analysis/manifest.yaml`
- Create: `skillpacks/operations/task-outcome-analysis/SKILL.md`
- Modify: `apps/cosa/agents/skillpack_seed.py`
- Modify: `apps/cosa/agents/specs.py`
- Modify: `apps/cosa/composition/capability_registration.py`
- Modify: `apps/cosa/events/contracts.py`
- Modify: `apps/cosa/events/router.py`
- Modify: `apps/cosa/worker/handlers.py`
- Create: `apps/cosa/worker/outcome_analysis_run.py`
- Test: `services/company/operations/tests/task-result.service.test.ts`
- Test: `services/company/operations/tests/task-outcome-analysis.service.test.ts`
- Test: `tests/apps/cosa/agents/test_task_outcome_analysis_skillpack.py`
- Test: `tests/apps/cosa/worker/test_outcome_analysis_run.py`
- Test: `tests/agent/workforce/test_outcome_analysis_binding.py`

**Interfaces:**

```ts
export type AnalysisPolicy = "AUTO_ALL_TASKS" | "AUTO_BY_RULE" | "MANUAL";
export type AnalysisKind = "TASK_OUTCOME" | "PROJECT_OUTCOME_SYNTHESIS";

export async function submitTaskResult(input: {
  taskId: string; contractId: string; workAttemptIds: string[];
  summary: string; artifactRefs: string[]; evidenceRefs: string[];
  claimedMeasurements: Record<string, number | string>; idempotencyKey: string;
}, ctx: TenantContext): Promise<TaskResultView>;

export async function recordOutcomeAssessment(input: {
  requestId: string; taskResultId: string; contractId: string;
  evidenceUsedRefs: string[]; missingEvidenceRefs: string[];
  criterionScores: Record<string, number>; confidence: number;
  recommendation: "ACCEPT" | "REWORK" | "REJECT" | "NEEDS_HUMAN_DECISION";
}, delegated: DelegatedCapabilityContext): Promise<OutcomeAssessmentView>;
```

```python
async def resolve_outcome_analysis_binding(
    workspace_id: str, task_result_id: str, analysis_kind: str
) -> OutcomeAnalysisBinding | None:
    raise NotImplementedError
```

- [ ] **Step 1: Write failing result, idempotency and capability tests.**

```ts
it("creates one TASK_OUTCOME request for each result revision in AUTO_ALL_TASKS", async () => {
  const first = await submitTaskResult(validResultInput, managerCtx);
  const retry = await submitTaskResult(validResultInput, managerCtx);
  expect(retry.id).toBe(first.id);
  expect(await listOutcomeAnalysisRequests(first.id)).toHaveLength(1);

  const rework = await submitTaskResult({ ...validResultInput, idempotencyKey: "result-2" }, managerCtx);
  expect(rework.revision).toBe(2);
  expect(await listOutcomeAnalysisRequests(rework.id)).toHaveLength(1);
  expect((await loadAssessmentForResult(first.id)).status).toBe("SUPERSEDED");
});

it("rejects an assessment record from an agent or run not selected by the router", async () => {
  await expect(recordOutcomeAssessment(validAssessment, delegatedForOtherRun)).rejects.toThrow(/request attribution/i);
  await expect(recordOutcomeAssessment(validAssessment, delegatedWithoutCapability)).rejects.toThrow(/capability/i);
});
```

```python
def test_outcome_skill_manifest_allows_only_read_and_assessment_record() -> None:
    manifest = load_skillpack("operations/task-outcome-analysis")
    assert manifest.required_capability_refs == {
        "operations.task.read", "operations.task-result.read",
        "operations.work-package.read", "operations.evidence.read",
        "agent.artifact.read", "operations.outcome-assessment.record",
    }
    assert "operations.task.advance" not in manifest.required_capability_refs
```

- [ ] **Step 2: Run the focused tests red.**

Run: `cd services/company && encore test operations/tests/task-result.service.test.ts operations/tests/task-outcome-analysis.service.test.ts && cd ../.. && source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/agents/test_task_outcome_analysis_skillpack.py tests/apps/cosa/worker/test_outcome_analysis_run.py -v`

Expected: FAIL because result revisions, analysis requests, the skillpack and the worker path do not exist.

- [ ] **Step 3: Persist Company-owned result, request, assessment and contribution records.**

Add `operating.task_results`, `operating.outcome_analysis_requests`,
`operating.outcome_assessments` and `operating.kr_contribution_assessments`. Make
result revision unique per task and request idempotency unique on workspace,
result, analysis kind and contract revision. Store exact contract/result revision,
employee/assignment/run, skill id/version/hash, rubric version, evidence used,
evidence missing, scores, confidence, risk, causal limit, recommendation and
status. Assessment record accepts only the request selected by the router. A new
result revision marks the former assessment `SUPERSEDED`; it never deletes it.

Implement `submitTaskResult` to verify the current confirmed contract, linked
work attempts and artifact/evidence ownership, then append the result and outbox
event in one transaction. AUTO_ALL_TASKS creates the request transactionally;
AUTO_BY_RULE evaluates a stored, versioned policy; MANUAL creates none. Do not
update task status or KR actual value in either path. In Agent Platform, add
`agent.outcome_analysis_bindings` keyed by workspace and analysis kind, carrying
the active analyst employee, exact assignment, policy, pinned skill reference and
version. The repository resolver returns one exact binding or `None`; it never
chooses a generic operations employee. Direct repository setup is allowed only in
tests until Task 7A exposes founder-governed policy commands.

- [ ] **Step 4: Add the pinned skillpack, capability boundary and router/worker path.**

Define the skillpack input as contract, task result, work attempts, artifacts and
evidence references; define output as expected-versus-actual, criterion scores,
missing evidence, risks, causal limits and next-action proposals. Seed and publish
it only after manifest/schema/capability validation. Register exactly six allowed
capabilities: task read, task-result read, work-package read, evidence read,
artifact read and narrow outcome-assessment record. Add a distinct
`outcome_analysis` profile mapping to an AgentSpec that pins this skill; no
fallback to the generic operations profile.

The event router receives `operating.task.result_submitted.v1`, resolves the
preselected Outcome Analyst employee/assignment/spec/skill snapshot through
`resolve_outcome_analysis_binding` and schedules `execute_outcome_analysis_run`.
A binding set to MANUAL produces no automatic request; a missing or mismatched
binding marks the request `BLOCKED_CONFIGURATION` and raises a visible event. The
worker refuses a missing/mismatched request, calls only the six granted
capabilities and records the assessment through the narrow Company endpoint. It
cannot call task advance, task creation, project-stage transition, KR write,
external send or finance write.

- [ ] **Step 5: Run green tests, skill validation and boundary gates.**

Run: `cd services/company && encore test operations/tests/task-result.service.test.ts operations/tests/task-outcome-analysis.service.test.ts && npm run typecheck && cd ../.. && source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/workforce/test_outcome_analysis_binding.py tests/apps/cosa/agents/test_task_outcome_analysis_skillpack.py tests/apps/cosa/worker/test_outcome_analysis_run.py -q && make skillpacks-validate && make apps-cosa-test && make company-boundary-check && make encore-handler-boundary-check`

Expected: PASS. Duplicate delivery creates one request/run, rework creates a new
revision, the old assessment remains superseded, unsupported profile fails closed
and the analyzer cannot mutate task/KR state.

- [ ] **Step 6: Commit the analysis pipeline.**

Commit: `feat(outcomes): analyze versioned task results with pinned AI skill`

---

### Task 5: Founder priority control, manager review and overdue escalation

**Files:**
- Create: `services/company/operations/migrations/54_work_package_review_governance.up.sql`
- Create: `services/company/operations/migrations/54_work_package_review_governance.down.sql`
- Modify: `services/company/shared/db/schema/operations.ts`
- Modify: `services/company/operations/services/work-package.service.ts`
- Modify: `services/company/operations/handlers/work-package.handler.ts`
- Create: `services/company/operations/services/work-package-review.service.ts`
- Create: `services/company/operations/services/task-outcome-review.service.ts`
- Create: `services/company/operations/handlers/task-outcome-review.handler.ts`
- Modify: `services/company/operations/handlers/index.ts`
- Test: `services/company/operations/tests/work-package-review.test.ts`
- Test: `services/company/operations/tests/work-package-priority.test.ts`
- Test: `services/company/operations/tests/task-outcome-review.service.test.ts`

**Interfaces:**

```ts
reviewWorkPackage(input: {
  workPackageId: string; workAttemptId: string; artifactVersionRef: string;
  decision: "ACCEPT" | "REWORK" | "REJECT"; rubricScores: Record<string, number>;
  reasonCode: string; narrative: string; expectedVersion: number;
}, ctx: TenantContext): Promise<WorkPackageReviewView>

overrideWorkPackagePriority(input: {
  workPackageId: string; effectivePriority: "P0" | "P1" | "P2" | "P3";
  reason: string; expectedVersion: number;
}, ctx: TenantContext): Promise<WorkPackageView>

reviewTaskOutcome(input: {
  taskResultId: string; assessmentId: string;
  decision: "ACCEPT" | "REWORK" | "REJECT";
  expectedResultRevision: number; reasonCode: string; narrative: string;
}, ctx: TenantContext): Promise<TaskOutcomeReviewView>

verifyKrContribution(input: {
  contributionId: string; decision: "VERIFIED" | "REJECTED" | "INSUFFICIENT_EVIDENCE";
  reason: string; expectedVersion: number;
}, ctx: TenantContext): Promise<KrContributionView>
```

- [ ] **Step 1: Write failing review/priority tests.**

```ts
it("counts business outcome only after owning manager review", async () => {
  await markValidationPassed(packageId, attemptId);
  expect(await readScorecard(employeeId)).toMatchObject({ acceptedCount: 0 });
  await reviewWorkPackage(validAcceptReview, owningManagerCtx);
  expect(await loadPackage(packageId)).toMatchObject({ status: "ACCEPTED" });
});

it("escalates overdue review but never auto-accepts", async () => {
  await runReviewEscalationSweep(clock.after(reviewDueAt));
  expect(await loadPackage(packageId)).toMatchObject({ status: "ESCALATED_TO_FOUNDER" });
});

it("requires the latest ready assessment before business outcome acceptance", async () => {
  await expect(reviewTaskOutcome({ ...validOutcomeReview, assessmentId: failedAssessmentId }, owningManagerCtx)).rejects.toThrow(/assessment/i);
  await reviewTaskOutcome({ ...validOutcomeReview, assessmentId: readyAssessmentId }, owningManagerCtx);
  expect(await loadTaskOutcomeReview(taskResultId)).toMatchObject({ decision: "ACCEPT" });
});

it("records verified KR contribution without mutating the KR actual value", async () => {
  const before = (await getKeyResult(krId, managerCtx)).currentValue;
  await verifyKrContribution({ contributionId, decision: "VERIFIED", reason: "source metric verified", expectedVersion: 1 }, managerCtx);
  expect((await getKeyResult(krId, managerCtx)).currentValue).toBe(before);
});
```

- [ ] **Step 2: Run tests red.**

Run: `cd services/company && encore test operations/tests/work-package-review.test.ts operations/tests/work-package-priority.test.ts operations/tests/task-outcome-review.service.test.ts`

Expected: FAIL because review and priority commands do not exist.

- [ ] **Step 3: Add immutable review and priority records.**

Add `operating.work_package_reviews` containing reviewer, exact artifact version, rubric JSON, decision, reason and `supersedes_review_id`; add `operating.task_outcome_reviews` binding a decision to an exact task result revision and READY assessment; and store contribution verification as an append-only decision. Add `version INTEGER NOT NULL` to package and use `WHERE version = :expectedVersion` for every manager/founder mutation. Priority command writes `work_package.reprioritized` event with requested, prior effective and new effective priority. It does not overwrite requested priority.

- [ ] **Step 4: Enforce command authority.**

Owning manager may create, reassign and review their package/result, and verify or reject a proposed KR contribution within their owned Initiative. Founder may reprioritize, hold, cancel, override review or assign reviewer. Generic `member` is insufficient. Task 6 adds exact, revocable founder delegation; do not expose delegated controls until Task 6 completes.

- [ ] **Step 5: Implement review outcomes and SLA sweep.**

`ACCEPT` only succeeds for the current artifact/result version after the latest assessment is READY; an analysis failure requires founder override with explicit reason. Work-package acceptance completes a parent task only after every required package accepts and the task-level outcome review accepts its current result. `REWORK` ends the attempt and queues a new attempt for an eligible manager-selected employee. `REJECT` closes the package/result with evidence. Contribution verification records VERIFIED, REJECTED or INSUFFICIENT_EVIDENCE; it never writes KR actual value. A deterministic sweep moves overdue `PENDING_MANAGER_REVIEW` to `ESCALATED_TO_FOUNDER`, appends `review.overdue`, and emits an outbox signal. Founder timeout remains blocker.

- [ ] **Step 6: Verify and commit.**

Run: `cd services/company && encore test operations/tests/work-package-review.test.ts operations/tests/work-package-priority.test.ts operations/tests/task-outcome-review.service.test.ts && npm run typecheck`

Expected: non-owner review fails, stale commands return 409, analysis cannot self-accept or update KR, founder override is auditable and no deadline auto-accepts.

Commit: `feat(operations): govern package review and queue priority`

---

### Task 6: Founder delegation, scorecards and real run investigation

**Files:**
- Create: `packages/agent/migrations/036_workforce_delegations.sql`
- Create: `packages/agent/migrations/036_workforce_delegations.down.sql`
- Create: `packages/agent/workforce/scorecard.py`
- Modify: `packages/agent/workforce/repository.py`
- Modify: `apps/cosa/api/workforce_schemas.py`
- Modify: `apps/cosa/api/workforce_routes.py`
- Modify: `packages/agent/runs/repository.py`
- Create: `services/company/operations/services/workforce-delegation.client.ts`
- Modify: `services/company/operations/services/work-package.service.ts`
- Test: `tests/agent/workforce/test_scorecard.py`
- Test: `tests/apps/cosa/test_workforce_routes.py`
- Test: `services/company/operations/tests/workforce-delegation-client.test.ts`

**Interfaces:**

```python
async def require_founder_or_delegate(
    workspace_id: str, principal_id: str, action: str, functional_key: str | None
) -> None:
    raise NotImplementedError

async def get_employee_scorecard(
    workspace_id: str, agent_instance_id: str, window_start: datetime, window_end: datetime
) -> EmployeeScorecard:
    raise NotImplementedError

async def get_scoped_run_investigation(run_id: str, workspace_id: str) -> RunInvestigation:
    raise NotImplementedError
```

- [ ] **Step 1: Write failing scorecard/investigation tests.**

```python
async def test_scorecard_counts_only_reviewed_attempt_outcomes() -> None:
    await seed_attempt(run_status="COMPLETED", review=None)
    assert (await get_employee_scorecard("ws_a", employee_id, start, end)).accepted_count == 0
    await seed_review(decision="ACCEPT", attempt_id=attempt_id)
    assert (await get_employee_scorecard("ws_a", employee_id, start, end)).accepted_count == 1

async def test_investigation_reads_governance_ledger_not_sse() -> None:
    response = await client.get(f"/agent/workforce/runs/{run_id}/investigation", headers=ws_a_headers)
    assert response.status_code == 200
    assert response.json()["data"]["tool_calls"][0]["tool_call_id"] == tool_call_id
```

- [ ] **Step 2: Run tests red.**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/workforce/test_scorecard.py tests/apps/cosa/test_workforce_routes.py -q`

Expected: FAIL because the delegation, scorecard and investigation APIs are absent.

- [ ] **Step 3: Persist explicit founder delegation.**

Create a revocable record with workspace, grantor, principal, action scope (`evaluation`, `queue_control`, `review_override`), functional-key scope, expiry and immutable grant/revoke event. `require_founder_or_delegate` checks exact principal plus scope. Existing `approval.requirement.role` remains for tool approval; it is not reused as workforce delegation. Add a separate internal authorization endpoint using a new single-purpose `COSA_WORKFORCE_AUTHZ_SERVICE_TOKEN`, never a browser token or general worker secret.

Create `workforce-delegation.client.ts` in Company. It passes the authenticated Company principal mapping, workspace, requested action and functional-key scope to that internal endpoint. It rejects timeout, unverified mapping, mismatched workspace and a deny result. Wire this client into founder-control commands from Task 5 so a delegate is authorized by the same persisted source, not a UI flag.

- [ ] **Step 4: Build evidence-derived scorecards.**

Aggregate accepted/rework/reject, review latency, retry count, token/cost, SLA and escalation rate by employee, functional key, spec id/version/hash, package type and time window. Read Company attempts/reviews through authenticated API plus Agent run/cost ledger. If Company evidence is unavailable return `unavailable` with source reason, not zero. Create a parallel manager scorecard for review latency and overdue rate only.

- [ ] **Step 5: Expose tenant-scoped APIs.**

Add employee profile/timeline/scorecard and `GET /agent/workforce/runs/{run_id}/investigation`. Investigation returns scoped run, checkpoints, tool calls, approvals, run events and artifacts. It must not reuse `/events`, which is SSE fanout. Founder/Evaluation Owner reads permitted records; manager reads only package they own; foreign user gets 403/404 without existence leak.

- [ ] **Step 6: Verify and commit.**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/workforce/test_scorecard.py tests/apps/cosa/test_workforce_routes.py -q && cd services/company && encore test operations/tests/workforce-delegation-client.test.ts`

Expected: completed run alone has no business score; metrics pin employee/spec; foreign tenant cannot inspect employee/run ledger; expired/out-of-scope founder delegate is denied by Company command path.

Commit: `feat(workforce): add governed scorecards and run investigation`

---

### Task 7: Controlled improvement proposals and safe promotion

**Files:**
- Create: `packages/agent/migrations/037_workforce_improvement_proposals.sql`
- Create: `packages/agent/migrations/037_workforce_improvement_proposals.down.sql`
- Create: `packages/agent/workforce/improvements.py`
- Modify: `packages/agent/workforce/repository.py`
- Modify: `apps/cosa/api/workforce_schemas.py`
- Modify: `apps/cosa/api/workforce_routes.py`
- Test: `tests/agent/workforce/test_improvements.py`
- Test: `tests/apps/cosa/test_workforce_routes.py`

**Interfaces:**

```python
class ImprovementProposal(BaseModel):
    proposal_id: str
    agent_instance_id: str
    baseline_evidence_refs: list[str]
    proposed_revision: dict[str, object]
    risk_cost_impact: dict[str, object]
    status: Literal["DRAFT", "PENDING_FOUNDER_REVIEW", "CANARY", "APPROVED", "REJECTED", "ROLLED_BACK"]
```

- [ ] **Step 1: Write failing safety tests.**

```python
async def test_evaluation_owner_can_propose_but_not_activate_capability_change() -> None:
    proposal = await create_proposal(evaluation_owner, capability_change)
    with pytest.raises(FounderApprovalRequired):
        await promote_proposal(proposal.proposal_id, evaluation_owner)

async def test_canary_pins_candidate_and_rollback_preserves_baseline() -> None:
    await approve_canary(proposal_id, founder)
    assert (await created_run()).root_definition_hash == candidate_hash
    await rollback(proposal_id, founder)
    assert (await active_assignment()).definition_hash == baseline_hash
```

- [ ] **Step 2: Run tests red.**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/workforce/test_improvements.py -v`

Expected: FAIL because proposal lifecycle is absent.

- [ ] **Step 3: Persist proposal and promotion evidence.**

Store baseline cohort/evidence, hypothesis, candidate pinned revision, cost/risk impact, canary selection, rollback plan, actor and timestamps. Reject credential, raw delegation and prompt-secret fields. Use append-only proposal revision/events.

- [ ] **Step 4: Enforce staged activation.**

Evaluation Owner may create proposal and change rubric/tag/SLA guidance in delegated functional scope. Any capability, autonomy, provider/model cost limit, external write or workspace-wide rollout needs founder approval. Canary creates new pinned assignment/revision only for selected attempts; historical run attribution is never mutated.

- [ ] **Step 5: Verify and commit.**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/workforce/test_improvements.py tests/apps/cosa/test_workforce_routes.py -q`

Expected: no self-modification; scope violations are 403; rollback disables candidate scheduling without deleting evidence.

Commit: `feat(workforce): govern AI employee improvements`

---

### Task 7A: Founder-controlled analysis policy and Skill Governance lifecycle

**Files:**
- Create: `packages/agent/migrations/038_skill_governance_policies.sql`
- Create: `packages/agent/migrations/038_skill_governance_policies.down.sql`
- Create: `packages/agent/workforce/skill_governance.py`
- Modify: `packages/agent/workforce/models.py`
- Modify: `packages/agent/workforce/repository.py`
- Modify: `apps/cosa/api/workforce_schemas.py`
- Modify: `apps/cosa/api/workforce_routes.py`
- Modify: `apps/cosa/api/skill_registry_routes.py`
- Modify: `apps/cosa/events/router.py`
- Test: `tests/agent/workforce/test_skill_governance.py`
- Test: `tests/apps/cosa/test_workforce_routes.py`
- Test: `tests/apps/cosa/api/test_skill_registry_routes.py`

**Interfaces:**

```python
class OutcomeAnalysisPolicy(BaseModel):
    workspace_id: str
    policy: Literal["AUTO_ALL_TASKS", "AUTO_BY_RULE", "MANUAL"]
    analyst_employee_id: str
    analyst_assignment_id: str
    deep_priority: Literal["P0", "P1", "P2", "P3"]
    standard_priority: Literal["P0", "P1", "P2", "P3"]
    light_priority: Literal["P0", "P1", "P2", "P3"]
    version: int

async def publish_outcome_analysis_policy(
    draft_id: str, expected_version: int, founder_id: str
) -> OutcomeAnalysisPolicy:
    raise NotImplementedError

async def resolve_outcome_analysis_binding(
    workspace_id: str, task_result_id: str, analysis_kind: str
) -> OutcomeAnalysisBinding | None:
    raise NotImplementedError
```

- [ ] **Step 1: Write failing policy, version and authority tests.**

```python
async def test_founder_publish_binds_exact_active_employee_assignment_and_pinned_skill() -> None:
    draft = await create_policy_draft(founder, auto_all_payload(analyst_employee_id, analyst_assignment_id))
    published = await publish_outcome_analysis_policy(draft.id, draft.version, founder.id)
    binding = await resolve_outcome_analysis_binding(workspace_id, task_result_id, "TASK_OUTCOME")
    assert binding.agent_instance_id == analyst_employee_id
    assert binding.assignment_id == analyst_assignment_id
    assert binding.skill_id == "operations/task-outcome-analysis"

async def test_manager_cannot_publish_or_add_write_capability_to_outcome_skill() -> None:
    draft = await create_policy_draft(founder, auto_all_payload(analyst_employee_id, analyst_assignment_id))
    with pytest.raises(FounderApprovalRequired):
        await publish_outcome_analysis_policy(draft.id, draft.version, manager.id)
    with pytest.raises(InvalidCapabilityBoundary):
        await create_skill_change_draft(founder, {"add_capability": "operations.task.advance"})
```

- [ ] **Step 2: Run tests red.**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/workforce/test_skill_governance.py tests/apps/cosa/test_workforce_routes.py tests/apps/cosa/api/test_skill_registry_routes.py -v`

Expected: FAIL because workspace policy, founder publish authority and exact binding resolution do not exist.

- [ ] **Step 3: Persist draft/publish/rollback governance records.**

Create append-only policy draft, policy version, policy event and skill-governance
proposal records. Each policy version records workspace, analysis policy, task
scope/depth/SLA/budget rules, exact analyst employee and assignment, pinned skill
reference, effective timestamp, creator, approver and rollback target. Store the
capability allowlist snapshot and reject any capability outside the six-item
Outcome Analyst boundary. Validate employee ACTIVE, assignment effective and
skill version PUBLISHED before a founder can publish.

- [ ] **Step 4: Implement safe control-plane APIs and bind router behavior.**

Expose tenant-scoped endpoints to list catalog/version/evaluation metadata, create
a founder-owned draft, request an evaluation, publish, rollback and read policy
history. Manager endpoints are read-only plus improvement-request creation. A
publish changes only future request binding; it never rewrites a queued/running
request or historical assessment. Update the router from Task 4A to call
`resolve_outcome_analysis_binding`; when the policy is MANUAL it records no
automatic request, and when the selected employee/assignment is unavailable it
fails closed with a visible configuration error rather than falling back.

Do not expose a raw production prompt or static AgentSpec edit control. For a
built-in skill, raw prompt/model/capability changes create a proposal with eval
cohort and rollback plan; only the existing registry publish path may make a new
validated, pinned skill version effective.

- [ ] **Step 5: Run green tests and registry safety checks.**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/workforce/test_skill_governance.py tests/apps/cosa/test_workforce_routes.py tests/apps/cosa/api/test_skill_registry_routes.py -q && make skillpacks-validate && make apps-cosa-test`

Expected: PASS. A founder can publish a valid, versioned binding; manager cannot
alter it; unsafe capability additions fail; stale drafts return conflict; rollback
affects only future runs and the router never chooses an implicit fallback agent.

- [ ] **Step 6: Commit the Skill Governance backend.**

Commit: `feat(workforce): govern outcome analysis skill policies`

---

### Task 8: Canonical contracts and truthful Flutter management UI

**Files:**
- Modify: `shared/contracts/mvp-surface.json`
- Regenerate: `frontend/lib/core/network/mvp_endpoints.g.dart`
- Modify: `frontend/lib/modules/workforce/services/workforce_mvp_service.dart`
- Modify: `frontend/lib/modules/workforce/models/workforce_mvp_models.dart`
- Create: `frontend/lib/modules/workforce/models/task_outcome_models.dart`
- Create: `frontend/lib/modules/workforce/controllers/workforce_governance_controller.dart`
- Create: `frontend/lib/modules/workforce/views/workforce_queue_board.dart`
- Create: `frontend/lib/modules/workforce/views/task_outcome_contract_panel.dart`
- Create: `frontend/lib/modules/workforce/views/employee_profile_view.dart`
- Create: `frontend/lib/modules/workforce/views/manager_review_inbox_view.dart`
- Create: `frontend/lib/modules/workforce/views/founder_escalations_view.dart`
- Create: `frontend/lib/modules/workforce/views/skill_governance_view.dart`
- Modify: `frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart`
- Modify: `frontend/lib/modules/hologram_hub/widgets/your_tasks_widget.dart`
- Modify: `frontend/lib/modules/agents/views/widgets/agents_runs_history_tab.dart`
- Test: `frontend/test/modules/workforce/workforce_mvp_service_test.dart`
- Test: `frontend/test/modules/workforce/workforce_governance_controller_test.dart`
- Test: `frontend/test/modules/workforce/workforce_queue_board_test.dart`
- Test: `frontend/test/modules/workforce/task_outcome_contract_panel_test.dart`
- Test: `frontend/test/modules/workforce/skill_governance_view_test.dart`
- Test: `frontend/test/modules/agents/agent_run_investigation_test.dart`

**Interfaces:**

```dart
enum AsyncSurfaceState { loading, loaded, empty, unavailable, forbidden }

class WorkPackageCardModel {
  final String workPackageId;
  final String requestedPriority;
  final String effectivePriority;
  final String assignedEmployeeId;
  final String status;
  final int version;
}

class TaskOutcomeCardModel {
  final String contractId;
  final String contractStatus;
  final String outcomeType;
  final String expectedOutcome;
  final String analysisStatus;
  final String contributionStatus;
}
```

- [ ] **Step 1: Add contract endpoints before client calls.**

Declare every new Company and Agent endpoint in `shared/contracts/mvp-surface.json` with schema, source, frontend symbol, backend test and Flutter test. Regenerate `mvp_endpoints.g.dart`. No raw literal legacy workforce path is introduced.

- [ ] **Step 2: Write failing service/controller tests.**

```dart
test('queue preserves requested and effective priority', () {
  final card = WorkPackageCardModel.fromJson({'requested_priority': 'P2', 'effective_priority': 'P0', 'work_package_id': 'wp_1', 'assigned_employee_id': 'a_1', 'status': 'QUEUED', 'version': 1});
  expect(card.requestedPriority, 'P2');
  expect(card.effectivePriority, 'P0');
});

testWidgets('manager cannot accept without rubric and reason', (tester) async {
  await tester.pumpWidget(reviewInboxWithPendingItem());
  await tester.tap(find.text('Accept'));
  expect(find.text('Chọn rubric và lý do'), findsOneWidget);
});

testWidgets('confirming an AI proposal queues it instead of leaving it as a draft task', (tester) async {
  await tester.pumpWidget(taskOutcomePanelWithAiProposal());
  await tester.tap(find.text('Confirm & queue'));
  expect(find.text('Queued'), findsOneWidget);
  expect(find.text('Contract confirmed'), findsOneWidget);
  expect(find.text('Draft'), findsNothing);
});

testWidgets('shows proposed KR contribution separately from verified contribution', (tester) async {
  await tester.pumpWidget(taskOutcomePanelWithContribution(status: 'PROPOSED'));
  expect(find.text('KR proposed'), findsOneWidget);
  expect(find.text('KR verified'), findsNothing);
});
```

- [ ] **Step 3: Implement typed UI surfaces.**

Services return `ApiResult<T>` intact. Task Outcome Contract Panel shows Initiative/KR relation, expected outcome, evidence criteria, contract revision, result revision, assessment and contribution state. It has distinct actions: `Confirm & queue` for an AI proposal; `Create & queue` for a complete manager/founder task; and `Request changes`/`Reject proposal`. It must not present a confirmation action that merely changes a label to DRAFT/TODO.

Queue Board shows requested/effective priority, dependency, employee, attempt,
review deadline, contract completeness, analysis state and founder override reason.
Review Inbox requires rubric/reason, displays evidence/result/assessment side by
side, and offers KR contribution verification without any button to alter KR
actual value. Employee Profile shows stable code/name/status, spec trend and
scorecard. Founder Escalations shows overdue review, held/cancelled/reprioritized
packages. Skill Governance shows catalog/version, policy, analyst binding,
capability matrix, draft/evaluation/publish/rollback controls appropriate to the
current principal. Render `loading`, `empty`, `unavailable`, `forbidden` and
`not configured` separately.

- [ ] **Step 4: Repair legacy run history during the same contract migration.**

Use canonical `run_id` and investigation endpoint. Remove reliance on legacy `trace_id`, `id`, `duration_ms` and unbacked cost/provider defaults. SSE `/events` must not be presented as an audit trail.

- [ ] **Step 5: Verify and commit.**

Run: `cd frontend && flutter test test/modules/workforce/workforce_mvp_service_test.dart test/modules/workforce/workforce_governance_controller_test.dart test/modules/workforce/workforce_queue_board_test.dart test/modules/agents/agent_run_investigation_test.dart && flutter analyze && cd .. && make frontend-api-contract-check && make contract-freeze-check`

Expected: UI states differ; manager sees only permitted actions; direct create and
proposal confirmation each result in Queued; override keeps reason; proposed and
verified KR contribution never collapse; no fabricated metric is rendered.

Commit: `feat(frontend): manage persistent AI workforce`

---

### Task 9: Disposable cross-plane E2E, rollout guard and operational evidence

**Files:**
- Create: `tests/e2e/test_persistent_ai_workforce.py`
- Create: `tests/e2e/stack/workforce_fixture.py`
- Modify: `tests/e2e/stack/subprocess_stack.py` only after confirming it does not overlap the existing user change
- Modify: `Makefile`
- Create: `docs/architecture/AI_WORKFORCE_OPERATIONS.md`
- Modify: `docs/architecture/CODEBASE_HARDENING_2026-09-08.md`

**Interfaces:**

```python
def seed_workforce_workspace(stack: SubprocessStack, *, managers: int, employees: int) -> WorkforceFixture:
    raise NotImplementedError

async def wait_for_work_package_state(client: AsyncClient, work_package_id: str, expected: str) -> None:
    raise NotImplementedError
```

- [ ] **Step 1: Write the E2E acceptance matrix first.**

```python
async def test_two_managers_queue_work_for_one_employee_and_capacity_serializes(stack: SubprocessStack) -> None:
    fixture = seed_workforce_workspace(stack, managers=2, employees=1)
    first, second = await fixture.queue_same_employee_packages(priorities=("P1", "P2"))
    await fixture.wait_for_running(first.work_package_id)
    assert await fixture.package_status(second.work_package_id) == "QUEUED"

async def test_overdue_review_escalates_founder_without_auto_accept(stack: SubprocessStack) -> None:
    fixture = seed_workforce_workspace(stack, managers=1, employees=1)
    package = await fixture.create_validation_passed_package()
    await fixture.advance_clock_past_review_due(package.work_package_id)
    assert await fixture.package_status(package.work_package_id) == "ESCALATED_TO_FOUNDER"
```

```python
async def test_direct_create_and_ai_proposal_confirmation_both_atomically_queue(stack: SubprocessStack) -> None:
    fixture = seed_workforce_workspace(stack, managers=1, employees=2)
    direct = await fixture.manager_create_confirmed_task_and_queue()
    proposal = await fixture.agent_create_task_proposal()
    confirmed = await fixture.manager_confirm_proposal_and_queue(proposal.task_id)
    assert direct.contract.status == "CONFIRMED"
    assert confirmed.contract.status == "CONFIRMED"
    assert await fixture.package_status(direct.work_package_id) == "QUEUED"
    assert await fixture.package_status(confirmed.work_package_id) == "QUEUED"
    assert await fixture.count_packages_for_task(proposal.task_id) == 1

async def test_result_revision_creates_one_pinned_analysis_and_never_writes_kr_actual(stack: SubprocessStack) -> None:
    fixture = seed_workforce_workspace(stack, managers=1, employees=2)
    item = await fixture.create_confirmed_task_with_accepted_package()
    before = await fixture.kr_actual_value(item.primary_kr_id)
    result = await fixture.submit_task_result(item.task_id)
    await fixture.deliver_result_event_twice(result.id)
    assessment = await fixture.wait_for_outcome_assessment(result.id)
    assert assessment.agent_instance_id == fixture.outcome_analyst_id
    assert assessment.skill_id == "operations/task-outcome-analysis"
    assert await fixture.analysis_request_count(result.id) == 1
    assert await fixture.kr_actual_value(item.primary_kr_id) == before

async def test_founder_hold_or_reprioritize_races_safely_with_lease(stack: SubprocessStack) -> None:
    fixture = seed_workforce_workspace(stack, managers=1, employees=1)
    package = await fixture.manager_create_confirmed_task_and_queue()
    lease, override = await fixture.race_lease_with_founder_hold(package.work_package_id)
    assert sorted([lease.status_code, override.status_code]) in ([200, 409], [202, 409])
    assert await fixture.count_package_events(package.work_package_id, "work_package.held") == 1
    assert await fixture.package_version(package.work_package_id) == 2

async def test_reassign_at_checkpoint_preserves_old_approval_and_creates_one_new_attempt(stack: SubprocessStack) -> None:
    fixture = seed_workforce_workspace(stack, managers=1, employees=2)
    package = await fixture.create_running_package_waiting_for_approval()
    old = await fixture.current_attempt(package.work_package_id)
    await fixture.request_reassignment(package.work_package_id, fixture.second_employee_id)
    new = await fixture.wait_for_next_attempt(package.work_package_id)
    assert new.sequence_no == old.sequence_no + 1
    assert new.run_id != old.run_id
    assert (await fixture.approval_for_attempt(old.id)).run_id == old.run_id
    assert await fixture.active_attempt_count(package.work_package_id) == 1

async def test_foreign_workspace_cannot_read_or_control_employee_contract_result_or_run(stack: SubprocessStack) -> None:
    fixture = seed_workforce_workspace(stack, managers=1, employees=1)
    item = await fixture.manager_create_confirmed_task_and_queue()
    for response in await fixture.workspace_b_attempts(["employee", "contract", "result", "package", "investigation"], item):
        assert response.status_code in (403, 404)

async def test_scorecard_changes_only_after_review_and_pins_spec_revision(stack: SubprocessStack) -> None:
    fixture = seed_workforce_workspace(stack, managers=1, employees=2)
    item = await fixture.create_validation_passed_package()
    before = await fixture.employee_scorecard(item.employee_id)
    await fixture.submit_task_result(item.task_id)
    assert await fixture.employee_scorecard(item.employee_id) == before
    await fixture.manager_accept_latest_task_outcome(item.task_id)
    after = await fixture.employee_scorecard(item.employee_id)
    assert after.accepted_by_spec[item.spec_hash] == before.accepted_by_spec.get(item.spec_hash, 0) + 1

async def test_duplicate_outbox_delivery_and_worker_restart_do_not_duplicate_attempt_or_side_effect(stack: SubprocessStack) -> None:
    fixture = seed_workforce_workspace(stack, managers=1, employees=1)
    item = await fixture.manager_create_confirmed_task_and_queue()
    await fixture.deliver_package_event_twice(item.work_package_id)
    await fixture.restart_worker()
    await fixture.wait_for_terminal_worker_state(item.work_package_id)
    assert await fixture.active_attempt_count(item.work_package_id) == 1
    assert await fixture.run_lease_count(item.work_package_id) == 1
    assert await fixture.company_completion_callback_count(item.work_package_id) == 1
```

- [ ] **Step 2: Run E2E red.**

Run: `make e2e-persistent-ai-workforce`

Expected: FAIL until migration, worker dispatch and all command paths are wired.

- [ ] **Step 3: Build a hermetic process fixture.**

Use a disposable PostgreSQL DSN and separate Company/COSA/worker processes. Apply both migration sets and configure test-only HMAC/delegation environment values. Fail if fixture falls back to developer database/credentials. Restart worker inside tests to prove lease/recovery rather than simulating it in memory.

- [ ] **Step 4: Add safe rollout gate and runbook.**

Default `AI_WORKFORCE_V2_ENABLED=false`. Enable only a named pilot workspace after E2E passes. Emit readiness for unattributed new workforce runs, stuck leases, overdue reviews, denied foreign-tenant commands and unavailable scorecard sources. The runbook names owner, evidence query and safe action for each condition. Rollback disables dispatch but preserves attempts/reviews/events.

- [ ] **Step 5: Run complete evidence set.**

Run: `make skillpacks-validate && make apps-cosa-test && make services-test-company && make frontend-api-contract-check && make contract-freeze-check && cd frontend && flutter test && flutter analyze && cd .. && make e2e-persistent-ai-workforce`

Expected: focused and full gates pass, all nine acceptance cases run against disposable infrastructure, and no integration test skips because of an unavailable local PostgreSQL.

- [ ] **Step 6: Commit.**

Commit: `test(workforce): prove persistent AI workforce lifecycle`

## Plan Self-review

- **Spec coverage:** Task 1 delivers persistent identity. Task 1A creates the versioned outcome/KR/evidence foundation for AI proposals without exposing a false confirmation path. Task 2 makes direct manager/founder creation and AI-proposal confirmation atomically create a CONFIRMED contract plus QUEUED package. Tasks 3–4 deliver eligibility, signed dispatch, one-owner attempts and durable provenance. Task 4A adds versioned result, automatic analysis request, pinned skill and narrow capability boundary. Task 5 adds result/assessment review and verified-but-not-automatic KR contribution. Tasks 6–7 deliver delegation, evidence scorecards and controlled improvement; Task 7A adds founder Skill Governance policy/version/binding. Task 8 makes the full audit chain truthful in Flutter. Task 9 proves atomic queue, recovery, concurrency, analysis idempotency and tenancy before pilot release.
- **Safety coverage:** all mutations are tenant-scoped, idempotent/CAS protected, append audit events, preserve attempt/result/assessment history, never auto-accept and never write KR actual value from an AI assessment.
- **Sequencing:** public confirmation is introduced only with atomic queue creation in Task 2; no queue UI or scorecard is enabled before provenance/evidence exists; no outcome-analysis dispatch is enabled before its read-only capability boundary and pinned employee binding exist. The pilot flags remain off until multi-process E2E passes.
