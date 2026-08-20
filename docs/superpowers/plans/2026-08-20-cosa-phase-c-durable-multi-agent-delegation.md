# COSA Phase C Durable Multi-Agent Delegation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Build durable asynchronous RunStep delegation across AgentRuntime, Codex, Claude Code, n8n, and OpenSandbox while preserving COSA governance, shared mission limits, tenant isolation, and legacy Chief of Staff behavior.

**Architecture:** RunStep remains the business source of truth and a new DelegationJob owns queue, lease, retry, provider correlation, and recovery. TaskBoardService dispatches through DelegationProvider; agent-worker is the only durable polling loop; generalized long-running adapters wrap DeveloperJob, AutomationProvider, and ExecutionJob rather than merging those provider-native models.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2/Alembic, PostgreSQL JSONB and FOR UPDATE SKIP LOCKED, Pydantic v2, asyncio, pytest/pytest-asyncio.

**Spec:** docs/superpowers/specs/2026-08-20-cosa-phase-c-durable-multi-agent-delegation-design.md

## Global Constraints

- Work directly on main, but stage and commit only files named by the active task.
- Phase B critical governance findings are a production enablement gate; all Phase C feature flags remain disabled until the Phase B regression suite passes.
- Do not create another AgentRuntime, tool registry, approval service, policy vocabulary, event log, or process-level polling runtime.
- agent-worker is the only durable delegation loop.
- RunStep owns business state; DelegationJob owns coordination state; provider-native rows own provider execution state.
- Tool calls inside AgentRuntime continue through GovernanceKernel.
- Requested but unknown or unhealthy runtimes/providers fail closed and never fall back to mock.
- Risk uses R0–R4; permission uses L0–L3.
- Child effective permission cannot exceed the parent permission.
- Budget and depth apply to the full AgentRun tree.
- No SQLAlchemy transaction remains open across model, CLI, sandbox, or HTTP awaits.
- Delivery is at-least-once; provider side effects must be effectively-once through idempotency.
- Every row lookup and callback validation is workspace-scoped.
- Four legacy Chief of Staff specialists remain unchanged while delegation flags are off.
- No provider is production-ready until its real contract suite passes; mock-only evidence is insufficient.

---

## File Structure

| File | Responsibility |
|---|---|
| backend/alembic/versions/c3e01c5a0003_phase_c_delegation.py | Add RunStep, RunEvent, DeveloperJob, AgentRun constraints and delegation_jobs. |
| backend/app/founder_os/outcomes/models.py | RunStep assignment/result fields and ordered idempotent RunEvent fields. |
| backend/app/workforce/agents/delegation/models.py | DelegationJob ORM model only. |
| backend/app/workforce/agents/delegation/types.py | Status enums, handles, requests, results, health and capability types. |
| backend/app/workforce/agents/delegation/states.py | DelegationJob and RunStep transition validation. |
| backend/app/workforce/agents/delegation/events.py | Atomic ordered RunEvent writer. |
| backend/app/workforce/agents/delegation/policy.py | Assignment-specific policy returning canonical PolicyDecision. |
| backend/app/workforce/agents/delegation/limits.py | Shared depth traversal and MAX_SUBRUN_DEPTH. |
| backend/app/workforce/agents/delegation/budget.py | Root-run aggregation and reservation settlement. |
| backend/app/workforce/agents/delegation/provider.py | DelegationProvider contract. |
| backend/app/workforce/agents/delegation/manager.py | Fail-closed delegation provider registry. |
| backend/app/workforce/agents/delegation/providers/in_process.py | AgentRuntime-backed delegation provider. |
| backend/app/workforce/agents/delegation/providers/executor_bridge.py | Bridge to long-running executor manager. |
| backend/app/workforce/agents/delegation/task_board.py | Assignment, dependency, execution, cancellation and result aggregation. |
| backend/app/workforce/agents/delegation/worker.py | Claim, poll, reconcile and recovery functions called by agent-worker. |
| backend/app/workforce/agents/execution/long_running/* | General long-running contract, manager and provider adapters. |
| backend/app/integrations/devices/models.py | Hardened DeveloperJob and JobLease correlation fields. |
| backend/app/integrations/devices/service.py | Atomic capability-aware claim, renewal, cancel and lease-bound result submit. |
| backend/app/integrations/devices/router.py | Device renewal/cancel/submit API contracts. |
| backend/app/scripts/device_executor_worker.py | Reference Codex/Claude device worker using argv-only subprocess execution. |
| backend/app/workforce/automation/runtime/adapters/n8n.py | Idempotent signed status/cancel support used by the n8n bridge. |
| backend/app/workforce/agents/orchestration/chief_of_staff.py | Feature-gated delegation and idempotent continuation. |
| backend/app/core/feature_flags.py | Phase C flags, disabled by default. |
| backend/app/worker_main.py | Start managers and run delegation loop. |
| backend/app/db/base.py | Register DelegationJob metadata. |
| docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md | Canonical delegation and long-running executor ownership. |
| docs/architecture/COSA_PHASE_C_DELEGATION_RUNBOOK.md | Inspect, cancel, retry and dead-letter operations. |

## Milestone 1 — Durable Core and In-Process Delegation

### Task 1: Add the durable schema and canonical models

**Files:**
- Create: backend/alembic/versions/c3e01c5a0003_phase_c_delegation.py
- Create: backend/app/workforce/agents/delegation/models.py
- Modify: backend/app/founder_os/outcomes/models.py
- Modify: backend/app/integrations/devices/models.py
- Modify: backend/agent_runtime/sessions/models.py
- Modify: backend/app/db/base.py
- Test: backend/app/tests/agents/delegation/test_delegation_models.py

**Interfaces:**
- Produces DelegationJob ORM fields defined in the design spec.
- Produces RunStep.assigned_agent_profile_id, assigned_runtime, delegated_run_id and result_jsonb.
- Produces RunEvent.sequence and event_key.
- Produces DeveloperJob.agent_run_id, run_step_id, executor_kind, request_jsonb, result_jsonb and cancel_requested_at.

- [ ] **Step 1: Write failing model metadata tests**

~~~python
def test_phase_c_models_expose_durable_columns():
    from agent_runtime.sessions.models import AgentRun
    from app.founder_os.outcomes.models import RunEvent, RunStep
    from app.integrations.devices.models import DeveloperJob, JobLease
    from app.workforce.agents.delegation.models import DelegationJob

    assert {"assigned_agent_profile_id", "assigned_runtime", "delegated_run_id", "result_jsonb"} <= set(RunStep.__table__.columns.keys())
    assert {"sequence", "event_key"} <= set(RunEvent.__table__.columns.keys())
    assert {"lease_token", "lease_expires_at", "provider_handle_jsonb", "root_agent_run_id"} <= set(DelegationJob.__table__.columns.keys())
    assert {"agent_run_id", "run_step_id", "executor_kind", "request_jsonb", "result_jsonb", "cancel_requested_at"} <= set(DeveloperJob.__table__.columns.keys())
    assert {"lease_token_hash", "renewed_at"} <= set(JobLease.__table__.columns.keys())
    assert any(fk.target_fullname == "agent_runs.id" for fk in AgentRun.__table__.c.parent_run_id.foreign_keys)
~~~

- [ ] **Step 2: Run the model test to verify RED**

Run: cd backend && ./.venv/bin/python -m pytest app/tests/agents/delegation/test_delegation_models.py -q

Expected: FAIL because app.workforce.agents.delegation and the columns do not exist.

- [ ] **Step 3: Add ORM models and migration**

Use revision c3e01c5a0003 with down_revision b2e01c5a0002. Define DelegationJob with explicit BigInteger foreign keys, JSONB, Numeric(12, 6) reserved cost, indexed due-time/status fields, unique (run_step_id, attempt_no), and unique (workspace_id, idempotency_key).

Migration data normalization:

~~~python
op.execute(
    "UPDATE run_steps SET risk_level = 'R' || substring(risk_level from 2) "
    "WHERE risk_level IN ('L0','L1','L2','L3','L4')"
)
op.alter_column("run_steps", "risk_level", server_default="R0")
~~~

Before adding the self-referential AgentRun foreign key, execute a PostgreSQL DO block that raises an exception when parent_run_id references a missing row or a row in another workspace. Add the self-FK only after the audit passes. Add RunEvent unique constraints uq_run_events_run_sequence and uq_run_events_run_event_key. Add DeveloperJob and RunStep correlation columns as nullable for backward compatibility. Add JobLease.lease_token_hash and renewed_at; never persist the raw token. Register DelegationJob in app/db/base.py.

- [ ] **Step 4: Verify migration and models**

Run: cd backend && ./.venv/bin/python -m pytest app/tests/agents/delegation/test_delegation_models.py app/tests/test_outcomes.py app/tests/test_devices.py -q

Run: cd backend && ./.venv/bin/alembic upgrade head && ./.venv/bin/alembic current

Expected: tests PASS and Alembic reports c3e01c5a0003.

- [ ] **Step 5: Commit the durable schema**

~~~bash
git add backend/alembic/versions/c3e01c5a0003_phase_c_delegation.py backend/app/founder_os/outcomes/models.py backend/app/integrations/devices/models.py backend/agent_runtime/sessions/models.py backend/app/workforce/agents/delegation/models.py backend/app/db/base.py backend/app/tests/agents/delegation/test_delegation_models.py
git commit -m "feat: add durable delegation schema"
~~~

### Task 2: Define delegation types, transitions, ordered events, profiles and feature flags

**Files:**
- Create: backend/app/workforce/agents/delegation/__init__.py
- Create: backend/app/workforce/agents/delegation/types.py
- Create: backend/app/workforce/agents/delegation/states.py
- Create: backend/app/workforce/agents/delegation/events.py
- Modify: backend/app/workforce/agents/profiles/schemas.py
- Modify: backend/app/core/feature_flags.py
- Test: backend/app/tests/agents/delegation/test_delegation_states.py
- Test: backend/app/tests/agents/delegation/test_delegation_events.py
- Test: backend/app/tests/unit/test_phase6_agent_profiles.py

**Interfaces:**
- Produces DelegationStatus, DelegationRequest, DelegationHandle, DelegationResult, ProviderHealth and ProviderCapabilities.
- Produces transition_delegation(current, target) and transition_step(current, target).
- Produces append_run_event(db, run_id, event_type, payload, event_key) -> RunEvent.
- Extends AgentProfile with permission_profile, preferred_runtime and delegation_provider defaults.

- [ ] **Step 1: Write transition and event idempotency tests**

~~~python
def test_terminal_delegation_state_cannot_reopen():
    with pytest.raises(ValueError, match="terminal"):
        transition_delegation("succeeded", "queued")

def test_append_run_event_is_idempotent(db_session, outcome_run):
    first = append_run_event(db_session, outcome_run.id, "step.assigned", {"step_id": "1"}, "assign:1:1")
    second = append_run_event(db_session, outcome_run.id, "step.assigned", {"step_id": "1"}, "assign:1:1")
    assert first.id == second.id
    assert first.sequence == 1
~~~

- [ ] **Step 2: Run focused tests to verify RED**

Run: cd backend && ./.venv/bin/python -m pytest app/tests/agents/delegation/test_delegation_states.py app/tests/agents/delegation/test_delegation_events.py app/tests/unit/test_phase6_agent_profiles.py -q

Expected: FAIL on missing types/functions/profile fields.

- [ ] **Step 3: Implement canonical types, transition maps and ordered event writer**

DelegationStatus values are queued, waiting_approval, denied, claimed, dispatching, running, retry_scheduled, cancel_requested, succeeded, failed and cancelled. append_run_event locks OutcomeRun, returns an existing event for the same event_key, assigns max(sequence)+1, flushes, and leaves commit ownership to its caller.

Add profile defaults:

~~~python
permission_profile: str = "read_only"
preferred_runtime: Optional[str] = None
delegation_provider: str = "agent_runtime"
~~~

Add disabled flag constants:

~~~python
FLAG_AGENT_DELEGATION = "agent_delegation"
FLAG_AGENT_DELEGATION_CHIEF_OF_STAFF = "agent_delegation_chief_of_staff"
FLAG_AGENT_DELEGATION_DEVICE_EXECUTORS = "agent_delegation_device_executors"
FLAG_AGENT_DELEGATION_N8N = "agent_delegation_n8n"
FLAG_AGENT_DELEGATION_SANDBOX = "agent_delegation_sandbox"
~~~

- [ ] **Step 4: Verify types, events and backward-compatible profiles**

Run: cd backend && ./.venv/bin/python -m pytest app/tests/agents/delegation/test_delegation_states.py app/tests/agents/delegation/test_delegation_events.py app/tests/unit/test_phase6_agent_profiles.py -q

Expected: PASS, including existing 12 profile definitions without changes.

- [ ] **Step 5: Commit state contracts**

~~~bash
git add backend/app/workforce/agents/delegation backend/app/workforce/agents/profiles/schemas.py backend/app/core/feature_flags.py backend/app/tests/agents/delegation backend/app/tests/unit/test_phase6_agent_profiles.py
git commit -m "feat: define delegation state contracts"
~~~

### Task 3: Add fail-closed provider resolution and assignment governance

**Files:**
- Create: backend/app/workforce/agents/delegation/policy.py
- Create: backend/app/workforce/agents/delegation/provider.py
- Create: backend/app/workforce/agents/delegation/manager.py
- Modify: backend/app/workforce/agents/runtime/manager.py
- Modify: backend/app/workforce/agents/governance/policy_engine.py
- Modify: backend/app/workforce/agents/governance/approval_service.py
- Test: backend/app/tests/agents/delegation/test_delegation_policy.py
- Test: backend/app/tests/agents/delegation/test_provider_manager.py
- Test: backend/app/tests/agents/runtime_contract/test_runtime_endpoints.py

**Interfaces:**
- DelegationProvider.delegate/poll/cancel/health.
- DelegationProviderManager.get(name) -> DelegationProvider and raises DelegationProviderUnknown.
- AgentRuntimeManager.get_runtime(name, allow_default=False) raises AgentRuntimeError for explicit unknown names.
- DelegationPolicyEngine.evaluate(...) -> PolicyDecision.
- ApprovalService.get_matching_delegation_approval(...).

- [ ] **Step 1: Write fail-closed and policy tests**

~~~python
def test_explicit_unknown_runtime_never_falls_back_to_mock():
    manager = AgentRuntimeManager()
    manager.register(MockRuntime())
    with pytest.raises(AgentRuntimeError):
        manager.get_runtime("missing", allow_default=False)

def test_child_cannot_escalate_parent_permission():
    decision = DelegationPolicyEngine.evaluate(
        parent_permission="read_only",
        child_permission="l3_execute",
        risk_level="R2",
        provider_name="deepseek_harness",
        provider_healthy=True,
    )
    assert decision.action == PolicyAction.DENY
~~~

- [ ] **Step 2: Run tests to verify RED**

Run: cd backend && ./.venv/bin/python -m pytest app/tests/agents/delegation/test_delegation_policy.py app/tests/agents/delegation/test_provider_manager.py app/tests/agents/runtime_contract/test_runtime_endpoints.py -q

Expected: FAIL because explicit runtime lookup still falls back and delegation policy is missing.

- [ ] **Step 3: Implement shared risk normalization and assignment policy**

Extract normalize_risk_level(risk: str) -> tuple[str, str] from PolicyEngine so tool and delegation policy map R0/R1 to low, R2 to medium, R3 to high and R4 to critical. DelegationPolicyEngine returns PolicyDecision; it does not construct a fake ToolSpec.

Approval matching must require run_id, capability agent.delegate, resource_type run_step, resource_id, and idempotency key. Add commit: bool = True to ApprovalService.create_approval; TaskBoard passes commit=False so approval, step state, DelegationJob and RunEvent commit atomically. Preserve the default commit behavior and all existing tool approval methods.

- [ ] **Step 4: Verify policy and runtime regressions**

Run: cd backend && ./.venv/bin/python -m pytest app/tests/agents/delegation/test_delegation_policy.py app/tests/agents/delegation/test_provider_manager.py app/tests/agents/runtime_contract -q

Expected: PASS.

- [ ] **Step 5: Commit fail-closed governance**

~~~bash
git add backend/app/workforce/agents/delegation backend/app/workforce/agents/runtime/manager.py backend/app/workforce/agents/governance/policy_engine.py backend/app/workforce/agents/governance/approval_service.py backend/app/tests/agents/delegation backend/app/tests/agents/runtime_contract
git commit -m "feat: govern delegation assignments"
~~~

### Task 4: Enforce full-chain depth and shared mission budget

**Files:**
- Create: backend/app/workforce/agents/delegation/limits.py
- Create: backend/app/workforce/agents/delegation/budget.py
- Modify: backend/app/workforce/agents/governance/budget.py
- Modify: backend/app/workforce/agents/orchestration/chief_of_staff.py
- Modify: backend/app/workforce/agents/runtime/tool_bridge.py
- Test: backend/app/tests/agents/delegation/test_delegation_limits.py
- Test: backend/app/tests/agents/delegation/test_shared_budget.py
- Test: backend/app/tests/agents/test_chief_of_staff_orchestration.py

**Interfaces:**
- MAX_SUBRUN_DEPTH = 1.
- resolve_run_chain(db, workspace_id, run_id) -> list[AgentRun].
- assert_can_delegate(db, workspace_id, parent_run_id) -> int depth.
- MissionBudgetService.reserve/settle/release.
- BudgetTracker.check_tree(db, root_run, budget, current_step=0).

- [ ] **Step 1: Write cycle, tenant and concurrent reservation tests**

~~~python
def test_depth_fails_closed_on_cross_workspace_parent(db_session, run_a, run_b):
    run_b.parent_run_id = run_a.id
    run_b.workspace_id = run_a.workspace_id + 1
    db_session.commit()
    with pytest.raises(DelegationDepthError, match="workspace"):
        resolve_run_chain(db_session, run_b.workspace_id, run_b.id)

def test_concurrent_reservations_cannot_exceed_root_budget(db_session, root_run, queued_jobs):
    budget = MissionBudget(max_steps=2, max_tool_calls=2, max_api_cost_usd=1)
    MissionBudgetService.reserve(db_session, root_run.id, queued_jobs[0].id, steps=1, tool_calls=1, cost_usd=0.6, budget=budget)
    with pytest.raises(MissionBudgetExceeded):
        MissionBudgetService.reserve(db_session, root_run.id, queued_jobs[1].id, steps=1, tool_calls=1, cost_usd=0.6, budget=budget)
~~~

- [ ] **Step 2: Run focused tests to verify RED**

Run: cd backend && ./.venv/bin/python -m pytest app/tests/agents/delegation/test_delegation_limits.py app/tests/agents/delegation/test_shared_budget.py -q

Expected: FAIL because tree traversal and reservations do not exist.

- [ ] **Step 3: Implement recursive checks and reservations**

resolve_run_chain iteratively loads parent rows with workspace filters, tracks visited IDs, and raises on cycle, orphan, cross-workspace chain, or depth greater than MAX_SUBRUN_DEPTH.

reserve locks root AgentRun with FOR UPDATE, aggregates descendant AgentToolCall count, estimated cost, completed/running RunStep count, and active DelegationJob reservations. It updates the current job reservation only when the total remains within MissionBudget.

BudgetTracker.check_tree returns the existing BudgetCheckResult shape. tool_bridge uses root-aware checking when AgentRun.metadata_jsonb contains root_agent_run_id.

After each child poll or in-process completion, call StuckDetector.analyze_run(child_run_id). WARN_CHANGE_STRATEGY appends a warning event; ABORT_RUN requests cancellation and fails the attempt without creating a retry side effect.

- [ ] **Step 4: Verify limits and legacy depth behavior**

Run: cd backend && ./.venv/bin/python -m pytest app/tests/agents/delegation/test_delegation_limits.py app/tests/agents/delegation/test_shared_budget.py app/tests/agents/test_chief_of_staff_orchestration.py -q

Expected: PASS.

- [ ] **Step 5: Commit shared limits**

~~~bash
git add backend/app/workforce/agents/delegation/{limits.py,budget.py} backend/app/workforce/agents/governance/budget.py backend/app/workforce/agents/orchestration/chief_of_staff.py backend/app/workforce/agents/runtime/tool_bridge.py backend/app/tests/agents/delegation backend/app/tests/agents/test_chief_of_staff_orchestration.py
git commit -m "feat: enforce delegation tree limits"
~~~

### Task 5: Implement InProcessSubagentProvider and TaskBoardService

**Files:**
- Create: backend/app/workforce/agents/delegation/providers/__init__.py
- Create: backend/app/workforce/agents/delegation/providers/in_process.py
- Create: backend/app/workforce/agents/delegation/task_board.py
- Test: backend/app/tests/agents/delegation/test_in_process_provider.py
- Test: backend/app/tests/agents/delegation/test_task_board.py

**Interfaces:**
- InProcessSubagentProvider.delegate(...) -> DelegationHandle.
- TaskBoardService.assign_step(db, workspace_id, step_id, profile_id, runtime_name, provider_name, actor_agent_key) -> DelegationJob.
- TaskBoardService.complete_job(...), cancel_step(...), report_result(...).

- [ ] **Step 1: Write dependency, approval and result tests**

~~~python
@pytest.mark.asyncio
async def test_assign_step_waits_for_dependencies(db_session, pending_step, profile_registry):
    with pytest.raises(DependencyNotReady):
        await TaskBoardService.assign_step(
            db_session, workspace_id_for_step(db_session, pending_step.id), pending_step.id,
            "marketing", "mock", "in_process", "chief_of_staff",
        )

def test_report_result_preserves_specialist_shape(db_session, completed_marketing_step):
    report = TaskBoardService.report_result(db_session, completed_marketing_step.run_id)
    assert report == {"marketing": completed_marketing_step.result_jsonb}
~~~

- [ ] **Step 2: Run tests to verify RED**

Run: cd backend && ./.venv/bin/python -m pytest app/tests/agents/delegation/test_in_process_provider.py app/tests/agents/delegation/test_task_board.py -q

Expected: FAIL because provider and service are missing.

- [ ] **Step 3: Implement minimal provider and task board**

assign_step locks the step, verifies its Outcome workspace, validates completed dependencies, resolves the profile, evaluates policy, creates one idempotent DelegationJob attempt, creates matching approval when required, and appends step.assigned plus step.delegation_queued or step.waiting_approval.

InProcessSubagentProvider builds AgentRunRequest from the step/profile, calls get_runtime(runtime_name, allow_default=False), and returns normalized DelegationResult. It does not create a polling loop.

- [ ] **Step 4: Verify service behavior**

Run: cd backend && ./.venv/bin/python -m pytest app/tests/agents/delegation/test_in_process_provider.py app/tests/agents/delegation/test_task_board.py -q

Expected: PASS including deny, approval and cross-workspace cases.

- [ ] **Step 5: Commit TaskBoard core**

~~~bash
git add backend/app/workforce/agents/delegation backend/app/tests/agents/delegation
git commit -m "feat: add governed delegation task board"
~~~

### Task 6: Add durable worker claim, polling, cancellation and recovery

**Files:**
- Create: backend/app/workforce/agents/delegation/worker.py
- Modify: backend/app/worker_main.py
- Test: backend/app/tests/agents/delegation/test_delegation_worker.py
- Test: backend/app/tests/test_worker_runtime.py

**Interfaces:**
- claim_due_job(db, worker_id, now) -> int | None.
- process_delegation_job(job_id, worker_id) -> None.
- reconcile_expired_jobs(db, now) -> int.
- delegation_loop() called from worker_main._run_all.

- [ ] **Step 1: Write lease and crash-recovery tests**

~~~python
def test_expired_job_with_handle_is_polled_not_started_again(db_session, running_job, fake_provider):
    running_job.lease_expires_at = utc_now() - timedelta(seconds=1)
    db_session.commit()
    reconcile_expired_jobs(db_session, utc_now())
    process_delegation_job_sync(running_job.id, "worker-b")
    assert fake_provider.start_calls == 0
    assert fake_provider.poll_calls == 1

def test_lease_token_prevents_stale_worker_completion(db_session, claimed_job):
    with pytest.raises(LeaseLost):
        persist_provider_result(db_session, claimed_job.id, "stale-token", succeeded_result())
~~~

- [ ] **Step 2: Run worker tests to verify RED**

Run: cd backend && ./.venv/bin/python -m pytest app/tests/agents/delegation/test_delegation_worker.py app/tests/test_worker_runtime.py -q

Expected: FAIL because worker functions are missing.

- [ ] **Step 3: Implement DB-backed processing**

Claim only due queued, retry_scheduled, running-poll or cancel_requested jobs. Keep transactions short. Persist provider handle using job id plus lease token. For in-process work, renew heartbeat while AgentRuntime.run is active. For long-running work, store next_poll_at and release claim.

reconcile_expired_jobs requeues pre-handle jobs, schedules poll for jobs with handles, releases abandoned reservations only for terminal/non-dispatched jobs, and never reopens terminal state.

Register delegation_provider_manager.start() and delegation_loop() in worker_main._run_all.

- [ ] **Step 4: Verify worker and existing worker loops**

Run: cd backend && ./.venv/bin/python -m pytest app/tests/agents/delegation/test_delegation_worker.py app/tests/test_worker_runtime.py app/tests/test_health.py app/tests/test_compose_contract.py -q

Expected: PASS.

- [ ] **Step 5: Commit durable worker**

~~~bash
git add backend/app/workforce/agents/delegation/worker.py backend/app/worker_main.py backend/app/tests/agents/delegation/test_delegation_worker.py backend/app/tests/test_worker_runtime.py
git commit -m "feat: process delegation jobs durably"
~~~

## Milestone 2 — Generalized Long-Running Executors

### Task 7: Define the long-running executor contract and bridge

**Files:**
- Create: backend/app/workforce/agents/execution/long_running/__init__.py
- Create: backend/app/workforce/agents/execution/long_running/base.py
- Create: backend/app/workforce/agents/execution/long_running/types.py
- Create: backend/app/workforce/agents/execution/long_running/manager.py
- Create: backend/app/workforce/agents/delegation/providers/executor_bridge.py
- Test: backend/app/tests/agents/delegation/test_long_running_contract.py

**Interfaces:**
- LongRunningWorkProvider.start/poll/cancel/health/capabilities.
- LongRunningWorkProviderManager.get(name) fail-closed.
- LongRunningExecutorBridge implements DelegationProvider.

- [ ] **Step 1: Write shared contract tests**

~~~python
@pytest.mark.asyncio
async def test_all_registered_long_running_providers_are_idempotent(provider, request):
    first = await provider.start(context(), request, "same-key")
    second = await provider.start(context(), request, "same-key")
    assert first.external_id == second.external_id

def test_unknown_long_running_provider_is_rejected(manager):
    with pytest.raises(LongRunningProviderUnknown):
        manager.get("missing")
~~~

- [ ] **Step 2: Run to verify RED**

Run: cd backend && ./.venv/bin/python -m pytest app/tests/agents/delegation/test_long_running_contract.py -q

Expected: FAIL because the package does not exist.

- [ ] **Step 3: Implement types, manager and bridge**

WorkHandle contains provider_name, external_id, native_job_id and safe metadata. WorkStatus contains normalized state, progress, structured_result, metrics, retryable, error_code, error_message and next_poll_after_seconds.

The bridge resolves provider_name from DelegationRequest, converts WorkHandle/WorkStatus to DelegationHandle/DelegationStatus, and never imports provider implementation modules directly.

- [ ] **Step 4: Verify contract and manager**

Run: cd backend && ./.venv/bin/python -m pytest app/tests/agents/delegation/test_long_running_contract.py -q

Expected: PASS with a contract fake provider.

- [ ] **Step 5: Commit executor seam**

~~~bash
git add backend/app/workforce/agents/execution/long_running backend/app/workforce/agents/delegation/providers/executor_bridge.py backend/app/tests/agents/delegation/test_long_running_contract.py
git commit -m "feat: add long-running executor seam"
~~~

### Task 8: Harden DeveloperJob and add Codex/Claude device adapters

**Files:**
- Modify: backend/app/integrations/devices/service.py
- Modify: backend/app/integrations/devices/router.py
- Create: backend/app/workforce/agents/execution/long_running/providers/__init__.py
- Create: backend/app/workforce/agents/execution/long_running/providers/device.py
- Create: backend/app/workforce/agents/execution/long_running/providers/codex_device.py
- Create: backend/app/workforce/agents/execution/long_running/providers/claude_device.py
- Create: backend/app/scripts/device_executor_worker.py
- Modify: backend/app/tests/test_devices.py
- Test: backend/app/tests/agents/delegation/test_device_executors.py
- Test: backend/app/tests/agents/delegation/test_device_executor_worker.py

**Interfaces:**
- claim_job(..., lease_token) atomically validates capabilities and returns one active lease.
- renew_job_lease(..., lease_token) -> JobLease.
- request_job_cancel(...).
- submit_job_results(..., lease_token, ...).
- CodexDeviceExecutor and ClaudeDeviceExecutor implement LongRunningWorkProvider.
- device_executor_worker.run_once claims one compatible job, creates an isolated worktree, invokes a configured CLI with argv and submits lease-bound results.

- [ ] **Step 1: Write race, capability and lease-bound submit tests**

~~~python
def test_device_without_codex_capability_cannot_claim_codex_job(db_session, python_only_device, codex_job):
    with pytest.raises(PermissionError, match="capabilities"):
        claim_job(db_session, python_only_device.id, codex_job.id, codex_job.workspace_id, "w1")

def test_expired_lease_cannot_submit_results(db_session, claimed_job, expired_lease):
    with pytest.raises(PermissionError, match="lease"):
        submit_job_results(
            db_session, claimed_job.id, claimed_job.workspace_id,
            claimed_job.assigned_device_id, lease_token=expired_lease.lease_token,
            status="SUCCEEDED",
        )

def test_reference_worker_never_uses_shell_true(fake_http, fake_runner):
    run_once(fake_http, fake_runner, executor_kind="codex")
    assert fake_runner.calls[0].shell is False
    assert fake_runner.calls[0].argv[0] == "codex"
~~~

- [ ] **Step 2: Run device tests to verify RED**

Run: cd backend && ./.venv/bin/python -m pytest app/tests/test_devices.py app/tests/agents/delegation/test_device_executors.py app/tests/agents/delegation/test_device_executor_worker.py -q

Expected: FAIL because capability checks, renewal and lease-token submit do not exist.

- [ ] **Step 3: Implement atomic device protocol and adapters**

Lock DeveloperJob during claim, reject non-available state, verify Device workspace/status/trust/allowed_projects/required_capabilities, create a random hashed lease token, and commit once. Add renew and cancel endpoints authenticated by get_current_device.

Device provider start creates one DeveloperJob per idempotency key. Codex uses required capabilities codex and git; Claude uses claude_code and git. poll maps uppercase DeveloperJob states to WorkStatus. cancel requests cancellation and reports cancel_supported true.

The reference worker accepts an enrolled device endpoint and token, claims only declared capabilities, creates a temporary git worktree, invokes codex or claude with subprocess argv and shell=False, enforces timeout, captures redacted excerpts and artifact references, observes cancel requests, and submits using the raw lease token returned once by claim. It never logs the enrollment or lease token.

- [ ] **Step 4: Verify real contract mapping**

Run: cd backend && ./.venv/bin/python -m pytest app/tests/test_devices.py app/tests/agents/delegation/test_device_executors.py app/tests/agents/delegation/test_device_executor_worker.py -q

Expected: PASS including wrong-device, wrong-workspace, expired-lease and duplicate-start cases.

- [ ] **Step 5: Commit device executors**

~~~bash
git add backend/app/integrations/devices/{service.py,router.py} backend/app/workforce/agents/execution/long_running/providers backend/app/scripts/device_executor_worker.py backend/app/tests/test_devices.py backend/app/tests/agents/delegation/test_device_executors.py backend/app/tests/agents/delegation/test_device_executor_worker.py
git commit -m "feat: delegate coding work to device executors"
~~~

### Task 9: Add governed n8n and OpenSandbox long-running adapters

**Files:**
- Create: backend/app/workforce/agents/execution/long_running/providers/n8n.py
- Create: backend/app/workforce/agents/execution/long_running/providers/sandbox.py
- Modify: backend/app/workforce/automation/runtime/adapters/n8n.py
- Modify: backend/app/workforce/automation/router.py
- Modify: backend/app/workforce/agents/execution/service.py
- Test: backend/app/tests/agents/delegation/test_n8n_executor.py
- Test: backend/app/tests/agents/delegation/test_sandbox_executor.py
- Test: backend/app/tests/agents/test_execution_endpoints.py

**Interfaces:**
- N8nExecutor implements LongRunningWorkProvider using AutomationProvider.
- SandboxExecutor implements LongRunningWorkProvider using ExecutionJob.
- process_n8n_delegation_callback validates signature/replay/workspace/correlation.

- [ ] **Step 1: Write callback replay and explicit-provider tests**

~~~python
@pytest.mark.asyncio
async def test_n8n_callback_replay_is_rejected(client, signed_callback):
    first = await post_callback(client, signed_callback)
    second = await post_callback(client, signed_callback)
    assert first.status_code == 200
    assert second.status_code == 409

def test_sandbox_executor_never_uses_default_mock(db_session, request):
    with pytest.raises(LongRunningProviderUnknown):
        SandboxExecutor(provider_name=None).start_sync(context(), request, "key")
~~~

- [ ] **Step 2: Run adapter tests to verify RED**

Run: cd backend && ./.venv/bin/python -m pytest app/tests/agents/delegation/test_n8n_executor.py app/tests/agents/delegation/test_sandbox_executor.py -q

Expected: FAIL because adapters and callback do not exist.

- [ ] **Step 3: Implement adapters and signed callback**

N8nExecutor creates an AutomationRequest only after assignment approval, passes correlation and idempotency metadata, stores external_run_id, and maps get_status/cancel capabilities honestly. Callback verifies HMAC, timestamp window, nonce/event key, workspace, provider and external run correlation before updating DelegationJob.

SandboxExecutor creates ExecutionJob with explicit provider, stores child agent_run_id, polls its state, maps artifact rows to references, and delegates sandbox lifecycle entirely to the existing execution worker.

- [ ] **Step 4: Verify adapters and native regressions**

Run: cd backend && ./.venv/bin/python -m pytest app/tests/agents/delegation/test_n8n_executor.py app/tests/agents/delegation/test_sandbox_executor.py app/tests/agents/test_execution_endpoints.py app/tests/agents/test_coding_agent_execution.py -q

Expected: PASS.

- [ ] **Step 5: Commit external adapters**

~~~bash
git add backend/app/workforce/agents/execution/long_running/providers/{n8n.py,sandbox.py} backend/app/workforce/automation/runtime/adapters/n8n.py backend/app/workforce/automation/router.py backend/app/workforce/agents/execution/service.py backend/app/tests/agents/delegation backend/app/tests/agents
git commit -m "feat: bridge n8n and sandbox delegation"
~~~

## Milestone 3 — Chief of Staff Integration and Production Gates

### Task 10: Add async Chief of Staff delegation and idempotent continuation

**Files:**
- Create: backend/app/workforce/agents/orchestration/continuation.py
- Modify: backend/app/workforce/agents/orchestration/chief_of_staff.py
- Modify: backend/app/workforce/agents/delegation/worker.py
- Test: backend/app/tests/agents/test_chief_of_staff_delegation.py
- Modify: backend/app/tests/agents/test_chief_of_staff_orchestration.py

**Interfaces:**
- SpecialistSpec.delegate_via_profile_id: str | None.
- ChiefOfStaffOrchestrator.resume_after_delegation(db, mission_id, runtime=None) -> ChiefOfStaffResult.
- maybe_resume_mission(db, outcome_run_id) -> bool.

- [ ] **Step 1: Write flag-off, queue and continuation tests**

~~~python
@pytest.mark.asyncio
async def test_legacy_specialists_remain_synchronous_when_flag_off(monkeypatch, db_session):
    result = await orchestrate_marketing(db_session, delegation_flag=False)
    assert result.status != "delegating"
    assert db_session.query(DelegationJob).count() == 0

@pytest.mark.asyncio
async def test_async_specialist_resumes_synthesis_once(monkeypatch, db_session):
    first = await orchestrate_marketing(db_session, delegation_flag=True)
    assert first.status == "delegating"
    complete_all_delegations(db_session, first.mission_id)
    await asyncio.gather(
        ChiefOfStaffOrchestrator.resume_after_delegation(db_session, int(first.mission_id)),
        ChiefOfStaffOrchestrator.resume_after_delegation(db_session, int(first.mission_id)),
    )
    assert count_synthesis_events(db_session, first.mission_id) == 1
~~~

- [ ] **Step 2: Run Chief of Staff tests to verify RED**

Run: cd backend && ./.venv/bin/python -m pytest app/tests/agents/test_chief_of_staff_delegation.py app/tests/agents/test_chief_of_staff_orchestration.py -q

Expected: FAIL because the field and continuation do not exist.

- [ ] **Step 3: Extract synthesis continuation and add feature-gated queue path**

Add delegate_via_profile_id default None. When both spec field and workspace flag are active, create one RunStep per domain with report_key, required/failure policy and dependencies in inputs_jsonb, assign it through TaskBoardService, set OutcomeRun running, and return ChiefOfStaffResult(status="delegating").

resume_after_delegation locks OutcomeRun, returns the already materialized result if completion event exists, waits for required steps, builds specialist_reports, applies pre-synthesis budget/stuck checks, and calls the existing synthesis logic.

- [ ] **Step 4: Verify legacy and async behavior**

Run: cd backend && ./.venv/bin/python -m pytest app/tests/agents/test_chief_of_staff_delegation.py app/tests/agents/test_chief_of_staff_orchestration.py -q

Expected: PASS with legacy output unchanged while the flag is disabled.

- [ ] **Step 5: Commit Chief of Staff integration**

~~~bash
git add backend/app/workforce/agents/orchestration/{chief_of_staff.py,continuation.py} backend/app/workforce/agents/delegation/worker.py backend/app/tests/agents/test_chief_of_staff_delegation.py backend/app/tests/agents/test_chief_of_staff_orchestration.py
git commit -m "feat: delegate chief of staff steps asynchronously"
~~~

### Task 11: Add operational APIs, metrics, ownership and runbook

**Files:**
- Create: backend/app/workforce/agents/delegation/router.py
- Create: backend/app/workforce/agents/delegation/metrics.py
- Modify: backend/app/main.py
- Modify: docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md
- Create: docs/architecture/COSA_PHASE_C_DELEGATION_RUNBOOK.md
- Test: backend/app/tests/agents/delegation/test_delegation_api.py
- Modify: backend/app/tests/test_architectural_invariants.py

**Interfaces:**
- GET /api/v1/agents/delegations/{job_id}.
- POST /api/v1/agents/delegations/{job_id}/cancel.
- POST /api/v1/agents/delegations/{job_id}/retry creates a new attempt.
- delegation_metrics_snapshot(db) -> dict.

- [ ] **Step 1: Write workspace isolation and ownership tests**

~~~python
def test_workspace_cannot_inspect_another_workspace_delegation(client, auth_a, job_b):
    response = client.get(f"/api/v1/agents/delegations/{job_b.id}", headers=auth_a)
    assert response.status_code == 404

def test_canonical_ownership_map_names_delegation_owners():
    text = Path("../docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md").read_text()
    assert "TaskBoardService" in text
    assert "LongRunningWorkProviderManager" in text
~~~

- [ ] **Step 2: Run API and architecture tests to verify RED**

Run: cd backend && ./.venv/bin/python -m pytest app/tests/agents/delegation/test_delegation_api.py app/tests/test_architectural_invariants.py -q

Expected: FAIL because the router, metrics and ownership entries do not exist.

- [ ] **Step 3: Implement scoped operations and documentation**

All endpoints derive workspace from authentication, never accept workspace_id as authority, return 404 across tenant boundaries, and use TaskBoardService transitions. Retry creates attempt_no + 1 and a new idempotency key; it never mutates a terminal attempt.

Metrics expose queue depth/age, lease expiry, retries/dead letters, provider latency, approval wait, root budget reservations, depth and continuation lag without labels containing secrets or unbounded IDs.

The runbook gives exact SQL/read-only API checks, cancel behavior, operator retry conditions, dead-letter diagnosis, kill switch behavior and provider-specific caveats.

- [ ] **Step 4: Verify APIs and ownership**

Run: cd backend && ./.venv/bin/python -m pytest app/tests/agents/delegation/test_delegation_api.py app/tests/test_architectural_invariants.py -q

Expected: PASS.

- [ ] **Step 5: Commit operational surface**

~~~bash
git add backend/app/workforce/agents/delegation/{router.py,metrics.py} backend/app/main.py backend/app/tests/agents/delegation/test_delegation_api.py backend/app/tests/test_architectural_invariants.py docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md docs/architecture/COSA_PHASE_C_DELEGATION_RUNBOOK.md
git commit -m "docs: operationalize phase c delegation"
~~~

### Task 12: Run migration, security, crash and full regression gates

**Files:**
- Create: backend/app/tests/agents/delegation/test_delegation_e2e.py
- Create: backend/app/tests/agents/delegation/test_delegation_crash_matrix.py
- Create: backend/app/tests/agents/delegation/test_delegation_tenant_security.py
- Modify: backend/app/tests/test_compose_contract.py
- Modify: scripts/report_harness_ownership.py
- Modify: docs/architecture/COSA_HARNESS_STABILITY_AND_MULTIAGENT_DELEGATION_ROADMAP.md

**Interfaces:**
- Produces executable acceptance evidence; no new runtime interface.

- [ ] **Step 1: Add real-Postgres end-to-end scenarios**

~~~python
@pytest.mark.asyncio
async def test_worker_restart_recovers_without_duplicate_side_effect(postgres_session, idempotent_provider):
    job = seed_queued_delegation(postgres_session)
    idempotent_provider.crash_after_start_once = True
    await process_delegation_job(job.id, "worker-a")
    await process_delegation_job(job.id, "worker-b")
    refreshed = postgres_session.get(DelegationJob, job.id)
    assert refreshed.status == "succeeded"
    assert idempotent_provider.native_start_count == 1

def test_cross_workspace_child_run_is_rejected(postgres_session, workspace_a_step, workspace_b_run):
    with pytest.raises(TenantBoundaryViolation):
        attach_child_run(postgres_session, workspace_a_step, workspace_b_run)
~~~

- [ ] **Step 2: Run focused acceptance tests**

Run: cd backend && COSA_TEST_DATABASE_URL="${COSA_TEST_DATABASE_URL:?set real PostgreSQL test database}" ./.venv/bin/python -m pytest app/tests/agents/delegation/test_delegation_e2e.py app/tests/agents/delegation/test_delegation_crash_matrix.py app/tests/agents/delegation/test_delegation_tenant_security.py -q

Expected: PASS with real PostgreSQL.

- [ ] **Step 3: Run migration round-trip and focused Phase C suite**

Run: cd backend && ./.venv/bin/alembic upgrade head && ./.venv/bin/alembic downgrade b2e01c5a0002 && ./.venv/bin/alembic upgrade head

Run: cd backend && ./.venv/bin/python -m pytest app/tests/agents/delegation app/tests/agents/test_chief_of_staff_delegation.py app/tests/agents/test_chief_of_staff_orchestration.py app/tests/test_devices.py app/tests/agents/test_execution_endpoints.py app/tests/agents/runtime_contract -q

Expected: migration round-trip exits 0 and all focused tests PASS.

- [ ] **Step 4: Run architecture, Phase B gate and full backend regression**

Run: cd backend && ./.venv/bin/python -m pytest app/tests/test_architectural_invariants.py app/tests/test_harness_ownership_report.py app/tests/extensions app/tests/agents/test_extension_mcp_governance_e2e.py app/tests/tools/test_invocation_input_validation.py -q

Run: cd backend && ./.venv/bin/python -m pytest app/tests -q

Run: git diff --check

Expected: all tests PASS and diff check exits 0. If the Phase B gate fails, keep every Phase C production flag disabled and report the exact failures; do not claim production readiness.

- [ ] **Step 5: Update evidence and commit verification artifacts**

Record exact commands, timestamp, test counts, migration revision and disabled/enabled flags in the roadmap Phase C evidence section. Update the ownership reporter for the delegation and long-running packages.

~~~bash
git add backend/app/tests/agents/delegation backend/app/tests/test_compose_contract.py scripts/report_harness_ownership.py docs/architecture/COSA_HARNESS_STABILITY_AND_MULTIAGENT_DELEGATION_ROADMAP.md
git commit -m "test: verify phase c durable delegation"
~~~

## Final Acceptance Checklist

- [ ] Alembic has one head and current is c3e01c5a0003.
- [ ] Fresh install and downgrade/upgrade round-trip pass.
- [ ] DelegationJob state and RunEvent transition commit atomically.
- [ ] Runtime/provider unknown fails closed.
- [ ] Approval is resource- and idempotency-bound.
- [ ] Full parent chain rejects cycle, orphan and cross-workspace references.
- [ ] Concurrent reservations cannot exceed root MissionBudget.
- [ ] Tool calls use root-aware budget checking.
- [ ] Worker crash at each matrix point does not duplicate native side effects.
- [ ] Device submit requires an active lease token.
- [ ] n8n callback rejects replay and cross-workspace correlation.
- [ ] OpenSandbox result uses artifact references.
- [ ] Legacy Chief of Staff output remains unchanged with flags disabled.
- [ ] Async Chief of Staff continuation runs synthesis once.
- [ ] Phase B governance regression gate passes before any production flag is enabled.
- [ ] Ownership map and runbook name canonical owners and recovery commands.
- [ ] Full backend test suite and git diff --check pass.
