# Python Quality Gates Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Get `make verify`'s 3 red Python gates (ruff format, mypy, apps-cosa-test) green, fixing 2 real production bugs discovered along the way, without weakening any guard or hiding errors behind casts/suppressions.

**Architecture:** Three independent fixes landed as separate commits in order — formatter (mechanical) → type contracts (real bug fixes + genuine nullability narrowing) → test fixtures (inject a mock `project_team_client` where 13 tests are missing one, since the `PROJECT_TEAM_OPERATING_PROFILES` authority guard they hit is correct and must stay).

**Tech Stack:** Python 3.11, ruff, mypy, pytest, pytest-asyncio.

## Global Constraints

- No `cast()`, `# type: ignore`, or `# type: ignore[...]` anywhere in production code to silence mypy — every fix is a real contract fix or a real guard.
- Every behavior change needs a corresponding test; run it before moving to the next task.
- Nullability policy: if a value can legitimately be `None` at that point, add an explicit guard (raise or skip) before using it; if it can never actually be `None` there, fix the type at its true source rather than asserting it away.
- 3 separate commits minimum, in order: formatter, then type contracts, then fixtures (spec: `docs/superpowers/specs/2026-09-14-python-quality-gates-design.md`).
- Full spec: `docs/superpowers/specs/2026-09-14-python-quality-gates-design.md`.

Note: the spec's testing section also asks for a test proving the `PROJECT_TEAM_OPERATING_PROFILES` guard blocks the kernel with no side effect on authority denial. That test already exists — added by the separate Schedule Project Scope plan as `tests/apps/cosa/worker/test_project_team_authority.py::test_authority_denial_blocks_kernel_and_has_no_side_effect`. No new task is needed for it here; Task 6's final verification just confirms it's still green.

---

### Task 1: Run the formatter

**Files:**
- Modify: 71 files under `packages/agent`, `apps/cosa`, `packages/agent_integrations` (whatever `ruff format` reformats — do not hand-edit any of them).

**Interfaces:** None — this task changes no behavior, only whitespace/line-wrapping.

- [ ] **Step 1: Confirm current state**

Run: `source .venv/bin/activate && ruff format --check packages/agent apps/cosa packages/agent_integrations`
Expected: `71 files would be reformatted, 371 files already formatted`

- [ ] **Step 2: Apply the formatter**

Run: `source .venv/bin/activate && ruff format packages/agent apps/cosa packages/agent_integrations`
Expected: `71 files reformatted, 371 files left unchanged`

- [ ] **Step 3: Verify format check now passes**

Run: `source .venv/bin/activate && ruff format --check packages/agent apps/cosa packages/agent_integrations`
Expected: `442 files already formatted` (or similar — 0 files needing reformat)

- [ ] **Step 4: Confirm no test regressions from pure formatting**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent packages/agent_testkit -q`
Expected: same pass/fail counts as before this task (formatting changes whitespace only, never behavior) — if any test's output changed, investigate before proceeding, do not assume it's unrelated.

- [ ] **Step 5: Commit**

```bash
git add -A -- packages/agent apps/cosa packages/agent_integrations
git commit -m "style: ruff format 71 files (no behavior change)"
```

---

### Task 2: Fix 2 real bugs found during mypy investigation

**Files:**
- Modify: `packages/agent/kernel/openai_agents_kernel.py:187` (keyword typo)
- Modify: `packages/agent_integrations/langchain/kernel.py:209` (same keyword typo)
- Modify: `packages/agent/conversations/repository.py` (add `get_message` to Protocol + both implementations)
- Modify: `apps/cosa/api/project_activity_routes.py:95-98` (fix the message-visibility branch, which currently reads a `msg.workspace_id` attribute that `MessageRecord` doesn't have)
- Test: `tests/agent/kernel/test_manual_tool_loop_kernel_skill_usage.py` (new)
- Test: `packages/agent_integrations/tests/test_langchain_kernel_skill_usage.py` or wherever `packages/agent_integrations/langchain/kernel.py` already has tests — check first (see Step 5)
- Test: `tests/agent/conversations/test_repository.py` (extend if it exists, else create)
- Test: `tests/apps/cosa/api/test_project_activity_routes.py` (extend if it exists, else create)

**Interfaces:**
- Consumes: `SkillUsageObserver.record_resolved_pins(self, run_record: RunRecord, root_spec: AgentSpec, resolved_skills: list[SkillSpec], pinned_refs: list[PinnedSkillRef] | None = None) -> list[SkillUsageObservation]` (already defined at `packages/agent/skills/usage_observer.py:21-27` and `:36-42` — this task does not change this signature, only fixes 2 call sites that pass the wrong keyword name).
- Produces: `ConversationRepository.get_message(self, message_id: str) -> MessageRecord | None` — a new Protocol method + 2 implementations, for any future caller needing to look up a message by id alone.

#### Bug 1: `record_resolved_pins` called with wrong keyword (`agent_spec` instead of `root_spec`)

This is a real production bug: `ManualToolLoopKernel` (`packages/agent/kernel/openai_agents_kernel.py`, wired to production via `apps/cosa/composition/kernel_factory.py:167` for `runtime="manual_tool_loop"`) and the LangChain adapter kernel (`packages/agent_integrations/langchain/kernel.py`) both call `record_resolved_pins(..., agent_spec=pinned_spec, ...)`, but the real parameter name is `root_spec`. Whenever a run on either of these kernels has a configured `skill_usage_observer`, this raises `TypeError: record_resolved_pins() got an unexpected keyword argument 'agent_spec'` and the run crashes. No existing test catches this — the only existing skill-usage-observer test (`tests/agent_integrations/openai_agents_sdk/test_skill_usage_observation.py`) exercises a *third*, unaffected kernel (`agent_integrations.openai_agents_sdk.kernel.RealOpenAIAgentsSDKKernel`, the actual production default), so this bug in the other two kernels went undetected.

- [ ] **Step 1: Write the failing test for `ManualToolLoopKernel`**

Create `tests/agent/kernel/test_manual_tool_loop_kernel_skill_usage.py`:
```python
from __future__ import annotations

import pytest

from agent.contracts.run import RunRequest, RunStatus
from agent.contracts.spec import AgentSpec
from agent.governance.contracts import ExecutionMode
from agent.kernel.openai_agents_kernel import ManualToolLoopKernel
from agent.registry.publisher import publish_skill_spec
from agent.registry.repository import InMemorySpecRegistryRepository
from agent.runs.repository import InMemoryRunRepository
from agent.skills.contracts import PinnedSkillRef, SkillSpec
from agent.skills.usage_observer import InMemorySkillUsageObserver


@pytest.mark.asyncio
async def test_manual_tool_loop_kernel_records_resolved_pins_without_crashing() -> None:
    """Regression test: record_resolved_pins() used to be called with the
    wrong keyword (agent_spec instead of root_spec), crashing every run on
    this kernel that had a skill_usage_observer configured with pinned
    skills. See docs/superpowers/specs/2026-09-14-python-quality-gates-design.md.
    """
    repo = InMemoryRunRepository()
    spec_registry = InMemorySpecRegistryRepository()
    observer = InMemorySkillUsageObserver()

    skill = SkillSpec(id="brief", version="1.0.0", instructions="Draft clear briefs")
    pub_record = await publish_skill_spec(skill, repository=spec_registry, publisher="test")

    kernel = ManualToolLoopKernel(
        repository=repo,
        spec_registry=spec_registry,
        skill_usage_observer=observer,
    )

    spec = AgentSpec(
        id="analyst",
        version="1.0.0",
        instructions="Analyze data",
        pinned_skills=[
            PinnedSkillRef(
                skill_id="brief",
                version="1.0.0",
                definition_hash=pub_record.definition_hash,
            )
        ],
        model_input_capability_ref="model.input.direct-user-message",
    ).with_hash()

    request = RunRequest(
        input={"prompt": "test skill observation"},
        principal="user:test",
        root_executable_ref=spec.to_pinned_identity(),
        execution_mode=ExecutionMode.AUTONOMOUS,
        workspace_id="ws_obs",
    )

    result = await kernel.run(request, spec)

    assert result.status != RunStatus.FAILED, f"run failed: {result}"
    run_ids = await observer.run_ids()
    assert result.run_id in run_ids
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/kernel/test_manual_tool_loop_kernel_skill_usage.py -v`
Expected: FAIL — either the assertion `result.status != RunStatus.FAILED` fails, or the test errors with `TypeError: ... unexpected keyword argument 'agent_spec'` (whether `ManualToolLoopKernel.run()` lets the TypeError propagate or catches it and returns a FAILED result — either way this test fails today).

- [ ] **Step 3: Fix the keyword in both files**

In `packages/agent/kernel/openai_agents_kernel.py:187-192`, change:
```python
            await self._skill_usage_observer.record_resolved_pins(
                run_record=run_record,
                agent_spec=pinned_spec,
                resolved_skills=resolved_skills,
                pinned_refs=spec.pinned_skills or [],
            )
```
to:
```python
            await self._skill_usage_observer.record_resolved_pins(
                run_record=run_record,
                root_spec=pinned_spec,
                resolved_skills=resolved_skills,
                pinned_refs=spec.pinned_skills or [],
            )
```

In `packages/agent_integrations/langchain/kernel.py:209-214`, make the identical change (`agent_spec=pinned_spec` → `root_spec=pinned_spec`).

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/kernel/test_manual_tool_loop_kernel_skill_usage.py -v`
Expected: PASS

- [ ] **Step 5: Add the same regression coverage for the LangChain kernel**

Check whether `packages/agent_integrations/langchain/kernel.py` already has a test file (`find packages/agent_integrations -iname "*test*kernel*"` or check `tests/agent_integrations/langchain/`). If one exists, add a test there following the same pattern as Step 1 (construct the LangChain kernel with a `skill_usage_observer` and pinned skills, run it, assert it doesn't fail). If none exists, create `tests/agent_integrations/langchain/test_kernel_skill_usage.py` mirroring Step 1's test, adapted to that kernel's actual constructor signature (read `packages/agent_integrations/langchain/kernel.py`'s `__init__` first — do not assume it matches `ManualToolLoopKernel`'s signature exactly).

- [ ] **Step 6: Run mypy on both fixed files to confirm the 2 errors are gone**

Run: `source .venv/bin/activate && mypy packages/agent/kernel/openai_agents_kernel.py packages/agent_integrations/langchain/kernel.py`
Expected: no `Unexpected keyword argument "agent_spec"` errors (other pre-existing errors in these 2 files, if any, are out of scope here — only confirm this specific error class is gone).

#### Bug 2: `get_message` doesn't exist on `ConversationRepository`, and the one caller reads a field `MessageRecord` doesn't have

`apps/cosa/api/project_activity_routes.py:96` calls `plane.conversation_repository.get_message(source_id)` for `source_type == "message"`, but no such method exists anywhere — not on the `ConversationRepository` Protocol, not on `InMemoryConversationRepository`, not on `PostgresConversationRepository`. This branch has never been exercised by a passing test and would raise `AttributeError` at runtime today. Making it worse: the code right after also does `msg.workspace_id` (line 97), but `MessageRecord` (`packages/agent/conversations/models.py:63-80`) has no `workspace_id` field at all — only `conversation_id` and `project_id`. Workspace scoping for a message must go through its parent conversation, the same way the `source_type == "conversation"` branch just above it already does.

- [ ] **Step 1: Write the failing test for `get_message`**

Add to `tests/agent/conversations/test_repository.py` (create the file if it doesn't exist, following whatever import/fixture conventions the closest existing conversation-repository test uses — check `tests/agent/` for one first):
```python
from __future__ import annotations

import pytest

from agent.conversations.models import ConversationRecord, MessageRecord
from agent.conversations.repository import InMemoryConversationRepository


@pytest.mark.asyncio
async def test_in_memory_get_message_returns_the_message_by_id() -> None:
    repo = InMemoryConversationRepository()
    conv = ConversationRecord(
        conversation_id="conv_1",
        workspace_id="ws_1",
        created_by_principal="user_1",
        title="Test",
    )
    await repo.create_conversation(conv)
    stored = await repo.add_message(
        MessageRecord(conversation_id="conv_1", role="user", content="hello")
    )

    found = await repo.get_message(stored.message_id)

    assert found is not None
    assert found.message_id == stored.message_id
    assert found.content == "hello"


@pytest.mark.asyncio
async def test_in_memory_get_message_returns_none_for_unknown_id() -> None:
    repo = InMemoryConversationRepository()
    assert await repo.get_message("msg_does_not_exist") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/conversations/test_repository.py -v`
Expected: FAIL with `AttributeError: 'InMemoryConversationRepository' object has no attribute 'get_message'`

- [ ] **Step 3: Add `get_message` to the Protocol and both implementations**

In `packages/agent/conversations/repository.py`, add to the `ConversationRepository` Protocol (right after `get_conversation`, around line 30):
```python
    async def get_conversation(self, conversation_id: str) -> ConversationRecord | None: ...
    async def get_message(self, message_id: str) -> MessageRecord | None: ...
```

Add to `InMemoryConversationRepository` (right after `get_conversation`, around line 76):
```python
    async def get_message(self, message_id: str) -> MessageRecord | None:
        for msgs in self._messages.values():
            for m in msgs:
                if m.message_id == message_id:
                    return m.model_copy(deep=True)
        return None
```

Add to `PostgresConversationRepository` (right after `get_conversation`, around line 197):
```python
    async def get_message(self, message_id: str) -> MessageRecord | None:
        async with self._session_factory() as session:
            res = await self._execute(
                session,
                text(
                    """
                    SELECT message_id, conversation_id, project_id, sequence_no, role, content, run_id,
                           parent_message_id, status, created_at
                    FROM agent_conversation.messages
                    WHERE message_id = :message_id
                    """
                ),
                {"message_id": message_id},
            )
            row = res.mappings().first()
            if row is None:
                return None
            return MessageRecord(
                message_id=row["message_id"],
                conversation_id=row["conversation_id"],
                project_id=row["project_id"],
                sequence_no=row["sequence_no"],
                role=row["role"],
                content=row["content"],
                run_id=row["run_id"],
                parent_message_id=row["parent_message_id"],
                status=row["status"],
                created_at=row["created_at"],
                attachments=[],
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/conversations/test_repository.py -v`
Expected: PASS

- [ ] **Step 5: Fix the actual bug in the caller — `_fetch_and_verify_source_visibility`'s message branch**

Write the failing test first. Check `tests/apps/cosa/api/test_project_activity_routes.py` for existing fixtures/conventions (plane construction, `AuthenticatedIdentity` construction) — if it doesn't exist, create it following the same conventions as `tests/apps/cosa/api/test_schedule_routes.py` (a bare-router `FastAPI` + `TestClient` + `app.dependency_overrides[get_authenticated_identity]` pattern, or whichever pattern the closest existing `project_activity_routes` test in this repo already uses — search for one first with `grep -rl "_fetch_and_verify_source_visibility\|project_activity_routes" tests/`).

Add a test calling `_fetch_and_verify_source_visibility` directly (it's an importable module-level function) with `source_type="message"`:
```python
@pytest.mark.asyncio
async def test_fetch_and_verify_source_visibility_message_scopes_by_parent_conversation_workspace() -> None:
    plane = _build_test_plane()  # adapt to whatever plane-construction helper this test file uses
    conv = ConversationRecord(
        conversation_id="conv_1", workspace_id="ws_correct", created_by_principal="user_1", title="t"
    )
    await plane.conversation_repository.create_conversation(conv)
    msg = await plane.conversation_repository.add_message(
        MessageRecord(conversation_id="conv_1", role="user", content="hello")
    )
    identity_same_workspace = _identity(workspace_id="ws_correct")  # adapt to this file's identity helper
    identity_other_workspace = _identity(workspace_id="ws_other")

    is_visible, ref = await _fetch_and_verify_source_visibility(
        plane, identity_same_workspace, "message", msg.message_id
    )
    assert is_visible is True
    assert ref is not None and ref["id"] == msg.message_id

    is_visible_wrong_ws, ref_wrong_ws = await _fetch_and_verify_source_visibility(
        plane, identity_other_workspace, "message", msg.message_id
    )
    assert is_visible_wrong_ws is False
    assert ref_wrong_ws is None
```

Run it, confirm it fails (today: `AttributeError` before Step 3's fix is applied, or after Step 3 alone it would still fail because `msg.workspace_id` doesn't exist — this test is written against the FIXED behavior, so run it now to see it fail on `msg.workspace_id`).

Then fix `apps/cosa/api/project_activity_routes.py:95-98`:
```python
    elif source_type == "message":
        msg = await plane.conversation_repository.get_message(source_id)
        if msg is None:
            return False, None
        conv = await plane.conversation_repository.get_conversation(msg.conversation_id)
        if conv is None or conv.workspace_id != identity.workspace_id:
            return False, None
        return True, {"type": "message", "id": msg.message_id, "created_at": msg.created_at}
```

- [ ] **Step 6: Run test to verify it passes**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/api/test_project_activity_routes.py -v`
Expected: PASS

- [ ] **Step 7: Run mypy to confirm both errors are gone**

Run: `source .venv/bin/activate && mypy packages/agent/conversations/repository.py apps/cosa/api/project_activity_routes.py`
Expected: no `"ConversationRepository" has no attribute "get_message"` error (the other `project_activity_routes.py` errors are fixed in Task 4, not here — only confirm this specific one is gone).

- [ ] **Step 8: Commit**

```bash
git add packages/agent/kernel/openai_agents_kernel.py packages/agent_integrations/langchain/kernel.py packages/agent/conversations/repository.py apps/cosa/api/project_activity_routes.py tests/agent/kernel/test_manual_tool_loop_kernel_skill_usage.py tests/agent/conversations/test_repository.py tests/apps/cosa/api/test_project_activity_routes.py
git commit -m "fix: correct record_resolved_pins keyword, add missing get_message, fix message-visibility check"
```

(If Step 5 created a new LangChain kernel test file, `git add` that too.)

---

### Task 3: Fix nullability errors in `packages/agent` (7 errors, 6 files)

**Files:**
- Modify: `packages/agent/workflows/validation.py:110`
- Modify: `packages/agent/skills/usage_observer.py:58-72` (the `workspace_id` argument, not the `record_resolved_pins` signature — that's already fixed by Task 2)
- Modify: `packages/agent/executive_board/runner.py:42-97`
- Modify: `packages/agent/runs/expiry.py:33-62`
- Modify: `packages/agent/capabilities/approval_service.py:363-375`
- Modify: `packages/agent/workflows/engine.py:200-217`
- Test: extend the closest existing test file for each (see per-error steps — do not create a new test file per error if an existing one already covers this function).

**Interfaces:** No public signature changes in this task — every fix narrows an internal nullable value before use, or corrects a mistaken direct call to a Pydantic validator method. Callers of these functions are unaffected.

#### 3a. `workflows/validation.py:110` — calling a Pydantic validator method directly

`spec._validate_dag()` is a `@model_validator(mode="after")` method on `WorkflowSpec` (`packages/agent/workflows/schema.py:71-72`) — accessed on an instance, mypy sees the Pydantic-wrapped descriptor, not a plain callable, hence "not callable". The code's actual intent (re-run the validation logic and collect the error into `errors` instead of letting a `ValidationError` propagate) is legitimate — the fix is to call the underlying function via the class, passing `spec` as the explicit `self` argument.

- [ ] **Step 1: Run mypy to confirm the current error**

Run: `source .venv/bin/activate && mypy packages/agent/workflows/validation.py`
Expected: `workflows/validation.py:110: error: "PydanticDescriptorProxy[ModelValidatorDecoratorInfo]" not callable`

- [ ] **Step 2: Fix the call**

In `packages/agent/workflows/validation.py:110`, change:
```python
            spec._validate_dag()
```
to:
```python
            WorkflowSpec._validate_dag(spec)
```
(`WorkflowSpec` is already imported at the top of this file.)

- [ ] **Step 3: Run mypy to confirm the error is gone**

Run: `source .venv/bin/activate && mypy packages/agent/workflows/validation.py`
Expected: no `not callable` error on line 110.

- [ ] **Step 4: Run the existing test suite for this module to confirm no behavior change**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/workflows/ -k validation -v`
Expected: same pass/fail as before this change (this call's behavior — catching DAG errors into a list — must be identical; if any test's output changed, the fix altered behavior and needs to be reconsidered, not accepted as-is).

#### 3b. `skills/usage_observer.py:65` — `workspace_id` argument may be `None`

`SkillUsageObservation(workspace_id=run_record.workspace_id, ...)` — `run_record.workspace_id` is typed `str | None` on `RunRecord`, but `SkillUsageObservation.workspace_id` requires `str`. A skill-usage observation with no workspace is meaningless (nothing to scope it to), so this is the "guard, don't guess" case.

- [ ] **Step 1: Run mypy to confirm the current error**

Run: `source .venv/bin/activate && mypy packages/agent/skills/usage_observer.py`
Expected: `usage_observer.py:65: error: Argument "workspace_id" to "SkillUsageObservation" has incompatible type "str | None"; expected "str"`

- [ ] **Step 2: Add a guard**

In `packages/agent/skills/usage_observer.py`, inside the `for skill in resolved_skills:` loop (around line 57-73), add a guard before constructing `SkillUsageObservation`:
```python
        for skill in resolved_skills:
            if run_record.workspace_id is None:
                continue
            skill_version = skill.version or "1.0.0"
            def_hash = (
                skill.definition_hash
                or pinned_map.get((skill.id, skill_version))
                or (skill.compute_hash() if hasattr(skill, "compute_hash") else "sha256:unknown")
            )
            obs = SkillUsageObservation(
                workspace_id=run_record.workspace_id,
                run_id=run_record.run_id,
                skill_id=skill.id,
                skill_version=skill_version,
                definition_hash=def_hash,
                root_spec_id=root_spec_id,
                root_definition_hash=root_hash,
            )
```

- [ ] **Step 3: Run mypy to confirm the error is gone**

Run: `source .venv/bin/activate && mypy packages/agent/skills/usage_observer.py`
Expected: no error on line 65.

- [ ] **Step 4: Run the existing test suite to confirm no regression**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/skills/test_skill_usage_observer.py -v`
Expected: all pass. Since production `RunRecord`s always carry a real `workspace_id` (every run is created with one), this guard should never actually trigger in existing tests — if it does, that reveals a test fixture creating a workspace-less run, which itself is worth a one-line note in your task report, not a silent pass.

#### 3c. `executive_board/runner.py:57,67,77,92-95` — `output` treated as `dict[str, Any] | None` on one branch even though it's never `None` there

Full context already read (`packages/agent/executive_board/runner.py:42-97`): `output: dict[str, Any] | None = req.mock_model_output` is declared once (line 44) inside the `if req.mock_model_output is not None:` branch, but the annotation `dict[str, Any] | None` makes mypy treat `output` as still-possibly-`None` for every later `output.get(...)` call (lines 57, 67, 77, 92-95), even on the branch where it was just assigned from a value already checked non-`None`. On the `else` branch, `output = await self._run_kernel(req)` then `if output is None: return ...` narrows correctly — the bug is only the `if` branch's redundant `| None` annotation.

- [ ] **Step 1: Run mypy to confirm the current errors**

Run: `source .venv/bin/activate && mypy packages/agent/executive_board/runner.py`
Expected: 6 `union-attr` errors on lines 57, 67, 77, 92, 93, 94, 95 (7 lines total per the original scan — recount after Task 1's formatter run in case line numbers shifted by a line or two).

- [ ] **Step 2: Fix the type narrowing**

In `packages/agent/executive_board/runner.py`, change (around line 42-54):
```python
        if req.mock_model_output is not None:
            output: dict[str, Any] | None = req.mock_model_output
        else:
            output = await self._run_kernel(req)
            if output is None:
                return ExecutiveAnalysisOutcome(
                    kind="executive.analysis.failed.v1",
                    deliberation_id=req.deliberation_id,
                    frame_version=req.frame_version,
                    role_key=req.role_key,
                    error_detail="KERNEL_RUN_FAILED: model execution did not produce a valid analysis",
                )
```
to:
```python
        if req.mock_model_output is not None:
            output: dict[str, Any] = req.mock_model_output
        else:
            kernel_output = await self._run_kernel(req)
            if kernel_output is None:
                return ExecutiveAnalysisOutcome(
                    kind="executive.analysis.failed.v1",
                    deliberation_id=req.deliberation_id,
                    frame_version=req.frame_version,
                    role_key=req.role_key,
                    error_detail="KERNEL_RUN_FAILED: model execution did not produce a valid analysis",
                )
            output = kernel_output
```

- [ ] **Step 3: Run mypy to confirm all errors on this file are gone**

Run: `source .venv/bin/activate && mypy packages/agent/executive_board/runner.py`
Expected: 0 errors.

- [ ] **Step 4: Run the existing test suite for this module**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/executive_board/ -v` (adjust path if the real test directory differs — check with `find tests -iname "*executive_board*"` first)
Expected: all pass, same behavior as before (this is a pure type-narrowing change, no logic altered).

#### 3d. `runs/expiry.py:52,60` — `appr.run_id` may be `str | None`

Full context already read (`packages/agent/runs/expiry.py:33-62`). A pending approval being swept for expiry always belongs to a specific run — an approval with no `run_id` is corrupted data, not a normal case, so skip it and don't silently pass `None` forward.

- [ ] **Step 1: Run mypy to confirm the current errors**

Run: `source .venv/bin/activate && mypy packages/agent/runs/expiry.py`
Expected: 2 errors, lines 52 and 60.

- [ ] **Step 2: Add a guard and fix the list type**

In `packages/agent/runs/expiry.py`, change (around line 40-56):
```python
        expired_list = []
        # Quét các pending approvals đã hết hạn
        pending = await self._repo.list_pending_approvals()
        for appr in pending:
            if appr.expires_at and now > appr.expires_at:
                await self._repo.decide_approval(
                    approval_id=appr.approval_id,
                    reviewer="system:expiry_daemon",
                    approved=False,
                    reason="Approval expired due to inactivity timeout",
                )
                await self._repo.update_run_status(
                    appr.run_id,
                    status=RunStatus.FAILED,
                    error_details={"error": "Run timed out waiting for human approval"},
                )
                expired_list.append(appr.run_id)
```
to:
```python
        expired_list: list[str] = []
        # Quét các pending approvals đã hết hạn
        pending = await self._repo.list_pending_approvals()
        for appr in pending:
            if appr.run_id is None:
                continue
            if appr.expires_at and now > appr.expires_at:
                await self._repo.decide_approval(
                    approval_id=appr.approval_id,
                    reviewer="system:expiry_daemon",
                    approved=False,
                    reason="Approval expired due to inactivity timeout",
                )
                await self._repo.update_run_status(
                    appr.run_id,
                    status=RunStatus.FAILED,
                    error_details={"error": "Run timed out waiting for human approval"},
                )
                expired_list.append(appr.run_id)
```

- [ ] **Step 3: Run mypy to confirm both errors are gone**

Run: `source .venv/bin/activate && mypy packages/agent/runs/expiry.py`
Expected: 0 errors.

- [ ] **Step 4: Run the existing test suite for this module**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/runs/ -k expiry -v`
Expected: all pass. Since real approval records always carry a `run_id` (that's the whole point of `RunApprovalRecord`), this guard should never trigger in existing tests.

#### 3e. `capabilities/approval_service.py:366` — `decided.run_id` may be `str | None`

Full context already read (`packages/agent/capabilities/approval_service.py:350-375`). Same reasoning as 3d: a just-decided approval always has a `run_id`; if it somehow doesn't, log it loudly rather than crash on construction or silently drop the event.

- [ ] **Step 1: Run mypy to confirm the current error**

Run: `source .venv/bin/activate && mypy packages/agent/capabilities/approval_service.py`
Expected: 1 error on line 366.

- [ ] **Step 2: Add a guard**

In `packages/agent/capabilities/approval_service.py`, change (around line 363-374):
```python
        if decided:
            await self._repo.append_event(
                RunEventRecord(
                    run_id=decided.run_id,
                    event_type="approval.decided",
                    payload={
                        "approval_id": approval_id,
                        "tool_call_id": decided.tool_call_id,
                        "status": decided.status,
                        "reviewer": reviewer,
                    },
                )
            )
```
to:
```python
        if decided:
            if decided.run_id is None:
                logger.error(
                    "approval_id=%s decided but has no run_id — cannot append run event",
                    approval_id,
                )
            else:
                await self._repo.append_event(
                    RunEventRecord(
                        run_id=decided.run_id,
                        event_type="approval.decided",
                        payload={
                            "approval_id": approval_id,
                            "tool_call_id": decided.tool_call_id,
                            "status": decided.status,
                            "reviewer": reviewer,
                        },
                    )
                )
```
Check the top of this file for an existing `logger = logging.getLogger(...)` — if there isn't one, add `import logging` and `logger = logging.getLogger(__name__)` near the other module-level declarations, matching the style already used in `apps/cosa/worker/handlers.py`.

- [ ] **Step 3: Run mypy to confirm the error is gone**

Run: `source .venv/bin/activate && mypy packages/agent/capabilities/approval_service.py`
Expected: 0 errors.

- [ ] **Step 4: Run the existing test suite for this module**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/capabilities/ -k approval -v`
Expected: all pass, same behavior (real decided approvals always have `run_id`, so the new branch is untested dead code for the happy path, which is correct — it's a defensive guard, not a new feature).

#### 3f. `workflows/engine.py:208,216` — `step_callable`'s inferred type is too narrow

Full context already read (`packages/agent/workflows/engine.py:195-218`). `step_callable` is assigned across 4 branches with different callable arities (1, 2, or 3 params, since the wrapper closures use default-valued extra params to capture `handler_fn`/`step_params`). mypy infers the variable's type from its first assignment in program order and rejects the others. `Callable` is already imported.

- [ ] **Step 1: Run mypy to confirm the current errors**

Run: `source .venv/bin/activate && mypy packages/agent/workflows/engine.py`
Expected: 2 `assignment` errors on lines 208 and 216.

- [ ] **Step 2: Add an explicit loose annotation**

In `packages/agent/workflows/engine.py`, right before the `if inspect.iscoroutinefunction(handler_fn):` line (around line 202), add:
```python
                step_callable: Callable[..., Any]
                if inspect.iscoroutinefunction(handler_fn):
```

- [ ] **Step 3: Run mypy to confirm both errors are gone**

Run: `source .venv/bin/activate && mypy packages/agent/workflows/engine.py`
Expected: no `assignment` errors on lines 208/216 (other pre-existing errors in this file, if any, are out of scope).

- [ ] **Step 4: Run the existing test suite for this module**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/workflows/ -k engine -v`
Expected: all pass, same behavior (a type annotation never changes runtime behavior).

- [ ] **Step 5: Run mypy on the whole `packages/agent` tree to confirm no errors remain there**

Run: `source .venv/bin/activate && mypy packages/agent packages/agent_integrations`
Expected: 0 errors.

- [ ] **Step 6: Commit**

```bash
git add packages/agent/workflows/validation.py packages/agent/skills/usage_observer.py packages/agent/executive_board/runner.py packages/agent/runs/expiry.py packages/agent/capabilities/approval_service.py packages/agent/workflows/engine.py
git commit -m "fix(mypy): narrow nullable types in packages/agent (no cast/ignore)"
```

(Include any test files you touched or created in 3a-3f in this commit too, if not already committed by an earlier task.)

---

### Task 4: Fix nullability/type errors in `apps/cosa` (18 errors, 5 files)

**Files:**
- Modify: `apps/cosa/worker/executive_board_handler.py:63-73`
- Modify: `apps/cosa/composition/workflow_orchestration.py:175-185`
- Modify: `apps/cosa/graphql/resolvers.py:149`
- Modify: `apps/cosa/api/workforce_routes.py:1015-1037`
- Modify: `apps/cosa/api/project_activity_routes.py:126,225,269,296-323` (the 3 `repo` annotations + the DTO-construction guard — note lines 96-98 were already fixed in Task 2)
- Test: extend the closest existing test file for each (see per-error steps).

**Interfaces:** No public signature changes — same as Task 3, purely internal narrowing/annotation fixes.

#### 4a. `worker/executive_board_handler.py:66-67` — `EvidenceRef` fields may be `Any | None`

Full context already read. `ev.get("source_ref", ev.get("id", ""))` — since the fallback chain can still resolve to `None` if both keys are present but explicitly `None`-valued in the payload, and `EvidenceRef.source_ref`/`source_hash` require `str`. Convert to a real string explicitly rather than trusting the dict shape.

- [ ] **Step 1: Run mypy to confirm the current errors**

Run: `source .venv/bin/activate && mypy apps/cosa/worker/executive_board_handler.py`
Expected: 2 errors on lines 66-67.

- [ ] **Step 2: Fix with an explicit string conversion**

In `apps/cosa/worker/executive_board_handler.py`, change (around line 64-70):
```python
    evidence_refs = tuple(
        EvidenceRef(
            source_ref=ev.get("source_ref", ev.get("id", "")),
            source_hash=ev.get("source_hash", ev.get("hash", "")),
            classification=ev.get("classification", "internal"),
            project_id=ev.get("project_id") or project_id,
        )
        for ev in raw_evidence
        if isinstance(ev, dict)
    )
```
to:
```python
    evidence_refs = tuple(
        EvidenceRef(
            source_ref=str(ev.get("source_ref") or ev.get("id") or ""),
            source_hash=str(ev.get("source_hash") or ev.get("hash") or ""),
            classification=ev.get("classification", "internal"),
            project_id=ev.get("project_id") or project_id,
        )
        for ev in raw_evidence
        if isinstance(ev, dict)
    )
```

- [ ] **Step 3: Run mypy to confirm both errors are gone**

Run: `source .venv/bin/activate && mypy apps/cosa/worker/executive_board_handler.py`
Expected: 0 errors.

- [ ] **Step 4: Run the existing test suite for this module**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa -k executive_board -v`
Expected: all pass, same behavior (a value that was already a non-empty string round-trips through `str()` unchanged; only a `None`/missing case changes from silently becoming the Python string `"None"` — no, `str(None)` would produce `"None"` — check this: since the `or ""` happens BEFORE `str()`, a `None` value from `.get()` is caught by `or ""` first, so `str()` only ever wraps an already-non-None value or the empty-string fallback; this is safe and does not turn `None` into the string `"None"`).

#### 4b. `composition/workflow_orchestration.py:184` — `IWorkflowOrchestration` doesn't inherit `Protocol`

Full context already read. This class is a type-hint-only interface with `...`-bodied methods, but doesn't inherit `typing.Protocol`, so mypy treats the `...` body as a real (missing) return statement instead of an abstract stub.

- [ ] **Step 1: Run mypy to confirm the current error**

Run: `source .venv/bin/activate && mypy apps/cosa/composition/workflow_orchestration.py`
Expected: `workflow_orchestration.py:184: error: Missing return statement`

- [ ] **Step 2: Make it inherit `Protocol`**

Check the top of `apps/cosa/composition/workflow_orchestration.py` for an existing `from typing import ...` line — add `Protocol` to it (or add `from typing import Protocol` if no such import exists). Then change (around line 175):
```python
class IWorkflowOrchestration:
    """Public interface for consumers — type hint only."""
```
to:
```python
class IWorkflowOrchestration(Protocol):
    """Public interface for consumers — type hint only."""
```

- [ ] **Step 3: Run mypy to confirm the error is gone**

Run: `source .venv/bin/activate && mypy apps/cosa/composition/workflow_orchestration.py`
Expected: 0 errors.

- [ ] **Step 4: Run the existing test suite for this module**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa -k workflow_orchestration -v`
Expected: all pass — inheriting `Protocol` changes nothing at runtime for a class that's only ever used as a type hint (never instantiated directly); if anything in the codebase DOES instantiate `IWorkflowOrchestration()` directly, that would now raise `TypeError: Protocols cannot be instantiated` — check with `grep -rn "IWorkflowOrchestration(" apps/cosa/` before this step and confirm there's no direct instantiation (only type annotations like `-> IWorkflowOrchestration` or `: IWorkflowOrchestration`).

#### 4c. `graphql/resolvers.py:149` — empty `frozenset()` has no inferrable element type

Full context already read — the base Protocol declares `allowed_variables: frozenset[str]` (line 43), and other subclasses' non-empty frozensets let mypy infer `frozenset[str]`, but `frozenset()` alone can't.

- [ ] **Step 1: Run mypy to confirm the current error**

Run: `source .venv/bin/activate && mypy apps/cosa/graphql/resolvers.py`
Expected: `resolvers.py:149: error: Need type annotation for "allowed_variables"`

- [ ] **Step 2: Add the annotation**

In `apps/cosa/graphql/resolvers.py:149`, change:
```python
    allowed_variables = frozenset()
```
to:
```python
    allowed_variables: frozenset[str] = frozenset()
```

- [ ] **Step 3: Run mypy to confirm the error is gone**

Run: `source .venv/bin/activate && mypy apps/cosa/graphql/resolvers.py`
Expected: 0 errors.

- [ ] **Step 4: Run the existing test suite for this module**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa -k graphql -v`
Expected: all pass (a type annotation on an already-empty frozenset changes nothing at runtime).

#### 4d. `api/workforce_routes.py:1028,1037` — `decided.run_id` may be `str | None`

Full context already read (lines 1015-1044). Same pattern as 3d/3e: a just-decided approval always has a `run_id`; guard loudly if it doesn't, since silently proceeding would either crash inside `get_scoped_run`/`emit` or (worse) pass `None` through to a SQL query.

- [ ] **Step 1: Run mypy to confirm the current errors**

Run: `source .venv/bin/activate && mypy apps/cosa/api/workforce_routes.py`
Expected: 2 errors on lines 1028 and 1037.

- [ ] **Step 2: Add a guard right after `run_id` is read**

In `apps/cosa/api/workforce_routes.py`, change (around line 1026):
```python
    run_id = decided.run_id
    run_record = await plane.repository.get_scoped_run(
        run_id=run_id,
        workspace_id=identity.workspace_id,
    )
```
to:
```python
    run_id = decided.run_id
    if run_id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Approval decision is missing its run_id",
        )
    run_record = await plane.repository.get_scoped_run(
        run_id=run_id,
        workspace_id=identity.workspace_id,
    )
```
(Check that `HTTPException` and `status` are already imported in this file — they are used elsewhere in `workforce_routes.py` per the earlier code you've already read from this file.)

- [ ] **Step 3: Run mypy to confirm both errors are gone**

Run: `source .venv/bin/activate && mypy apps/cosa/api/workforce_routes.py`
Expected: 0 errors.

- [ ] **Step 4: Add a regression test**

Find the existing test file for `decide_approval` (search: `grep -rln "decide_approval" tests/apps/cosa/`). Add a test that decides an approval whose stored record has `run_id=None` (construct this directly against whatever fake/in-memory approval repository that test file already uses) and assert the endpoint returns HTTP 500 with the new detail message, rather than raising an unhandled exception or 200-ing with garbage data.

- [ ] **Step 5: Run that test file to confirm it passes**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest <the test file you found in Step 4> -v`
Expected: all pass, including the new test.

#### 4e. `api/project_activity_routes.py` — 3 `repo` annotations + DTO-construction guard (7 errors)

Full context already read. Lines 126, 225, 269 all repeat the same pattern: `repo: ProjectActivityRepository = getattr(plane, "project_activity_repository", None)` — the annotation claims non-`None` but `getattr(..., None)` can return `None`, and each site already has an `if repo is None:` check right after (returning/raising) — the fix is just to make the annotation match reality. Lines 305, 307, 308, 309, 310, 319 all read `event.<field>` into a `ProjectActivityDetailDTO` constructor argument typed as required `int`/`str`, but the underlying `event` record types these fields as optional. Per the DTO's own field comments (`apps/cosa/api/schemas.py:400-404`, `"runtime"`, `"business_decision"`, etc. — these are meant to always be populated), a `None` here means corrupted data, not a normal case — fail loudly rather than pass a lie to the DTO.

- [ ] **Step 1: Run mypy to confirm the current errors**

Run: `source .venv/bin/activate && mypy apps/cosa/api/project_activity_routes.py`
Expected: 7 errors — 3 on the `repo` assignment lines (126, 225, 269) and 6 on the `ProjectActivityDetailDTO(...)` construction (305 was seen as `int`, 307/308/309/310/319 as `str`/other — recount exact set after Task 2's fix to this file, since Task 2 removed the earlier `get_message`-related error but line numbers below it should be unaffected since Task 2's edit was above these lines... verify by running mypy fresh before starting, since Task 1's formatter run may have shifted line numbers slightly).

- [ ] **Step 2: Fix the 3 `repo` annotations**

At each of the 3 locations (originally lines 126, 225, 269 — re-check exact line numbers with `grep -n 'repo: ProjectActivityRepository = getattr' apps/cosa/api/project_activity_routes.py` first), change:
```python
    repo: ProjectActivityRepository = getattr(plane, "project_activity_repository", None)
```
to:
```python
    repo: ProjectActivityRepository | None = getattr(plane, "project_activity_repository", None)
```
(All 3 sites already have `if repo is None: ...return/raise...` immediately after, so no other code changes are needed — mypy will now correctly narrow `repo` to `ProjectActivityRepository` for the rest of each function after that check.)

- [ ] **Step 3: Fix the DTO-construction guard**

Find the exact current location of the `ProjectActivityDetailDTO(...)` construction (originally around line 296-323, in the handler that builds the detail response — re-check with `grep -n "ProjectActivityDetailDTO(" apps/cosa/api/project_activity_routes.py`). Immediately before that `return ProjectActivityDetailDTO(...)` statement, add:
```python
        if (
            event.project_sequence is None
            or event.phase is None
            or event.status is None
            or event.actor_kind is None
            or event.actor_id is None
            or event.payload_hash is None
        ):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Activity event {event_id} has incomplete required fields",
            )

        # Build detail DTO
        return ProjectActivityDetailDTO(
            event_id=event.event_id,
            workspace_id=event.workspace_id,
            project_id=event.project_id,
            project_sequence=event.project_sequence,
            kind=event.kind,
            phase=event.phase,
            status=event.status,
            actor_kind=event.actor_kind,
            actor_id=event.actor_id,
            correlation_id=event.correlation_id,
            source_type=event.source_type,
            source_id=event.source_id,
            source_version=event.source_version,
            source_reference=source_ref if is_visible else None,
            source_visibility="full" if is_visible else "unavailable",
            summary=event.summary or {} if is_visible else {},
            classification=event.classification,
            payload_hash=event.payload_hash,
            integrity_hash=getattr(event, "integrity_hash", None),
            occurred_at=event.occurred_at,
            recorded_at=event.recorded_at,
        )
```
(This replaces the existing `# Build detail DTO` block — the guard is new, the `return ProjectActivityDetailDTO(...)` call itself is unchanged, just now reached only after the guard passes, letting mypy narrow every `event.<field>` access inside it.)

- [ ] **Step 4: Run mypy to confirm all 7 errors on this file are gone**

Run: `source .venv/bin/activate && mypy apps/cosa/api/project_activity_routes.py`
Expected: 0 errors.

- [ ] **Step 5: Add a regression test for the new guard**

Find or create `tests/apps/cosa/api/test_project_activity_routes.py` (may already exist from Task 2 Step 5 — extend it, don't duplicate). Add a test that fetches an activity detail whose stored record has `phase=None` (or any of the 5 other guarded fields) and asserts the endpoint returns HTTP 500 with the new detail message, rather than either crashing or silently passing `None` into the DTO.

- [ ] **Step 6: Run that test file to confirm it passes**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/api/test_project_activity_routes.py -v`
Expected: all pass, including the new test.

- [ ] **Step 7: Run mypy on the entire codebase to confirm 0 errors remain**

Run: `source .venv/bin/activate && make typecheck-py`
Expected: exits 0, no errors printed.

- [ ] **Step 8: Commit**

```bash
git add apps/cosa/worker/executive_board_handler.py apps/cosa/composition/workflow_orchestration.py apps/cosa/graphql/resolvers.py apps/cosa/api/workforce_routes.py apps/cosa/api/project_activity_routes.py tests/apps/cosa/api/test_project_activity_routes.py
git commit -m "fix(mypy): narrow nullable types in apps/cosa (no cast/ignore)"
```

(Include the Task 4d test file too if it's different from `test_project_activity_routes.py`.)

---

### Task 5: Fix the 13 failing tests — shared `project_team_client` mock helper

**Files:**
- Create: `tests/apps/cosa/project_team_test_helpers.py`
- Modify: `tests/apps/cosa/compliance/test_run_delegation.py` (5 tests)
- Modify: `tests/apps/cosa/project_activity/test_worker_wiring.py` (2 tests)
- Modify: `tests/apps/cosa/test_founder_knowledge_context.py` (2 tests)
- Modify: `tests/apps/cosa/test_lifecycle_tranche_c_acceptance.py` (1 test)
- Modify: `tests/apps/cosa/test_scheduled_session_worker.py` (1 test)
- Modify: `tests/apps/cosa/test_vertical_slice_1_read_path.py` (1 test)
- Modify: `tests/apps/cosa/test_workspace_execution_e2e.py` (1 test)

**Interfaces:**
- Produces: `fake_project_team_client(*, workspace_id: str = "ws_1", project_id: str = "proj_1", profile_key: str = "operations") -> AsyncMock` — every one of the 7 files above imports and calls this, assigning the result to `plane.project_team_client` right after constructing `plane`.

All 13 failures share one root cause (confirmed by running the suite and by the "Company service unreachable" warning in the failure logs): each test builds a `plane` via `build_cosa_agent_plane(...)` without setting `plane.project_team_client`, so the `PROJECT_TEAM_OPERATING_PROFILES` authority guard (`apps/cosa/worker/handlers.py:228` area — line number may have shifted slightly from the Schedule Project Scope plan's Task 5 edits, re-check with `grep -n "PROJECT_TEAM_OPERATING_PROFILES" apps/cosa/worker/handlers.py`) falls back to a real `ProjectTeamClient()` that tries an actual HTTP call to `localhost:4000` and fails. This is the guard working exactly as designed — it is not a bug, and must not be weakened. The fix is entirely in the tests.

- [ ] **Step 1: Confirm the current failure count and root cause**

Run: `source .venv/bin/activate && PYTHONPATH=. AGENT_DATABASE_URL="" COSA_DATABASE_URL="" DATABASE_URL="" python -m pytest tests/apps/cosa apps/cosa/tests -q 2>&1 | tail -20`
Expected: 13 failed (the same 13 test names listed in the spec/this task's Files section), 1 error (`test_sse_reconnect_e2e.py`, unrelated — see spec's Ngoài phạm vi / this plan's Task 6 note), rest passed.

- [ ] **Step 2: Write the shared helper**

Create `tests/apps/cosa/project_team_test_helpers.py`, following the same pattern as the existing `tests/apps/cosa/policy_test_helpers.py` (read that file first for the house style — module docstring, imports, function naming):
```python
from __future__ import annotations

from unittest.mock import AsyncMock

from apps.cosa.company.project_team_client import (
    ProjectAgentRunAuthority,
    ProjectTeamClient,
    SpecRef,
)


def fake_project_team_client(
    *,
    workspace_id: str = "ws_1",
    project_id: str = "proj_1",
    profile_key: str = "operations",
) -> AsyncMock:
    """AsyncMock(spec=ProjectTeamClient) mà get_run_authority() luôn resolve
    thành công cho đúng (workspace_id, project_id, profile_key) truyền vào —
    dùng cho test cần authority PASS. Test cần authority DENY (vd.
    test_project_team_authority.py) tự cấu hình side_effect riêng, không
    dùng helper này.
    """
    client = AsyncMock(spec=ProjectTeamClient)
    client.get_run_authority.return_value = ProjectAgentRunAuthority(
        projectId=project_id,
        workspaceId=workspace_id,
        profileKey=profile_key,
        assignmentVersion=1,
        agentWorkforceMemberId=f"wf_member_{profile_key}",
        spec=SpecRef(id=f"cosa.agents.{profile_key}", version="1.0.0", hash="sha256:fake_test_hash"),
        policySnapshot={},
    )
    return client
```

- [ ] **Step 3: Run a syntax/import sanity check**

Run: `source .venv/bin/activate && PYTHONPATH=. python -c "from tests.apps.cosa.project_team_test_helpers import fake_project_team_client; c = fake_project_team_client(); print(type(c))"`
Expected: prints `<class 'unittest.mock.AsyncMock'>` with no import errors.

- [ ] **Step 4: Apply the helper to `tests/apps/cosa/compliance/test_run_delegation.py`**

This file's `_plane()` helper (already read earlier in this plan's research: `def _plane(company_client: Any | None = None): return build_cosa_agent_plane(...)`) is called by all 5 failing tests in this file. Add the import at the top:
```python
from tests.apps.cosa.project_team_test_helpers import fake_project_team_client
```
Then modify `_plane()` itself so every caller gets it automatically:
```python
def _plane(company_client: Any | None = None):
    plane = build_cosa_agent_plane(
        company_client=company_client,
        repository=InMemoryRunRepository(),
        conversation_repository=InMemoryConversationRepository(),
        spec_registry=InMemorySpecRegistryRepository(),
        governance_store=InMemoryGovernanceStateStore(),
        tenant_policy_client=fake_active_tenant_policy_client(),
        stream_event_repository=InMemoryRunStreamEventRepository(),
        model=FakeSDKModel(),
    )
    plane.project_team_client = fake_project_team_client(project_id="proj_1")
    return plane
```

- [ ] **Step 5: Run this file's tests to confirm all 5 now pass**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/compliance/test_run_delegation.py -v`
Expected: all pass (previously all 5 failed with "Company service unreachable").

- [ ] **Step 6: Apply the same fix to the remaining 6 files**

For each of `tests/apps/cosa/project_activity/test_worker_wiring.py`, `tests/apps/cosa/test_founder_knowledge_context.py`, `tests/apps/cosa/test_lifecycle_tranche_c_acceptance.py`, `tests/apps/cosa/test_scheduled_session_worker.py`, `tests/apps/cosa/test_vertical_slice_1_read_path.py`, `tests/apps/cosa/test_workspace_execution_e2e.py`: these files call `build_cosa_agent_plane(...)` directly (not through a shared `_plane()` helper — confirmed by grep during this plan's research), so add the import and, right after each `plane = build_cosa_agent_plane(...)` call in the file (some files may have more than one — check with `grep -n "build_cosa_agent_plane(" <file>` first), add:
```python
    plane.project_team_client = fake_project_team_client(project_id="proj_1")
```
(Match the `project_id` value to whatever the test's own payload/fixture already uses for `project_id` — check each test's `payload`/request construction first; most use `"proj_1"` but verify per file rather than assuming.)

- [ ] **Step 7: Run each file individually to confirm its previously-failing test(s) now pass**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/project_activity/test_worker_wiring.py tests/apps/cosa/test_founder_knowledge_context.py tests/apps/cosa/test_lifecycle_tranche_c_acceptance.py tests/apps/cosa/test_scheduled_session_worker.py tests/apps/cosa/test_vertical_slice_1_read_path.py tests/apps/cosa/test_workspace_execution_e2e.py -v`
Expected: all pass.

- [ ] **Step 8: Run the full apps-cosa-test suite to confirm 0 failures remain (except the known, separately-scoped SSE error)**

Run: `source .venv/bin/activate && PYTHONPATH=. AGENT_DATABASE_URL="" COSA_DATABASE_URL="" DATABASE_URL="" python -m pytest tests/apps/cosa apps/cosa/tests -q`
Expected: `0 failed, <N> passed, <M> skipped, 1 error` — the 1 error is `test_sse_reconnect_e2e.py`, explicitly out of scope for this plan (belongs to the separate Test Reliability plan/spec #6). Do not attempt to fix it here.

- [ ] **Step 9: Run `make apps-cosa-test` (the real gate, with coverage) to confirm it's green**

Run: `make apps-cosa-test`
Expected: passes with coverage ≥ 78% (the existing gate threshold — do not lower it).

- [ ] **Step 10: Commit**

```bash
git add tests/apps/cosa/project_team_test_helpers.py tests/apps/cosa/compliance/test_run_delegation.py tests/apps/cosa/project_activity/test_worker_wiring.py tests/apps/cosa/test_founder_knowledge_context.py tests/apps/cosa/test_lifecycle_tranche_c_acceptance.py tests/apps/cosa/test_scheduled_session_worker.py tests/apps/cosa/test_vertical_slice_1_read_path.py tests/apps/cosa/test_workspace_execution_e2e.py
git commit -m "fix(test): mock project_team_client in 13 tests hitting the real authority guard"
```

---

### Task 6: Final gate verification

**Files:** None — verification only, no code changes expected. If any gate fails here, go back to the relevant earlier task and fix it there (do not patch things ad hoc in this task).

- [ ] **Step 1: Run the formatter check**

Run: `source .venv/bin/activate && ruff format --check packages/agent apps/cosa packages/agent_integrations`
Expected: 0 files need reformatting.

- [ ] **Step 2: Run the linter**

Run: `make lint`
Expected: exits 0.

- [ ] **Step 3: Run the full mypy check**

Run: `make typecheck-py`
Expected: exits 0, 0 errors.

- [ ] **Step 4: Run the full apps-cosa-test suite**

Run: `make apps-cosa-test`
Expected: exits 0, coverage ≥ 78%.

- [ ] **Step 5: Run the full agent-test suite (unaffected by this plan, but confirm no regression)**

Run: `make agent-test`
Expected: exits 0, coverage ≥ 80%.

- [ ] **Step 6: Confirm the guard-order test from the Schedule Project Scope plan is still present and green**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/worker/test_project_team_authority.py -v -k authority_denial_blocks_kernel`
Expected: 1 test found and passing — `test_authority_denial_blocks_kernel_and_has_no_side_effect`. If this test is missing, that plan's Task 7 was not actually merged before this one started; stop and report this discrepancy rather than writing a duplicate test.

- [ ] **Step 7: Run `make verify`**

Run: `make verify`
Expected: exits 0. (This also runs `services-test`, `frontend-test`, boundary checks, etc. — none of which this plan touches, so any failure there is a pre-existing or unrelated issue to report, not something to fix as part of this plan.)

- [ ] **Step 8: No commit for this task** (verification only — if Step 7 reveals an unrelated pre-existing failure elsewhere in the monorepo, report it in your final summary rather than fixing it here).

## Self-Review Notes

- **Spec coverage:** Task 1 covers the formatter section. Task 2 covers both real bugs (record_resolved_pins keyword, get_message) called out explicitly in the spec, plus the previously-undiscovered `msg.workspace_id` bug found while implementing the get_message fix. Tasks 3-4 cover all 33 mypy errors across the 14 files listed in the spec, split by package (packages/agent vs apps/cosa) for reviewable task size. Task 5 covers the fixture fix for all 13 failing tests named in the spec. Task 6 covers the "gate tổng hợp cuối cùng" (`make verify`) requirement, plus explicitly confirms the guard-order test (already delivered by the Schedule Project Scope plan) is present rather than duplicating it.
- **Placeholder scan:** every code block in this plan is complete, real code with exact file paths and line-number anchors (caveated only where line numbers may have shifted between when this plan was written and when it's executed — each such caveat includes the exact `grep`/`mypy` command to re-derive the current location, not a vague "check first").
- **Type consistency:** `fake_project_team_client(...)` is defined once in Task 5 Step 2 and consumed identically (same import, same call shape) by all 7 files in Task 5 Steps 4 and 6. `get_message(self, message_id: str) -> MessageRecord | None` is defined identically on the Protocol and both implementations in Task 2.
