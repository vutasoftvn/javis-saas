# Orchestrator Project Cycle Command Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a Founder set up a Project + MVP roadmap + OKR cycle + N-week execution cycle (N chosen by the user, not fixed at 12/13) from chat or voice, routed through the existing `WorkOrchestratorService` → `AgentProposal` propose/approve/execute pipeline instead of asking a general chat LLM to freehand a roadmap/OKR JSON blob.

**Architecture:** Fix a live, reproducible crash where `WorkOrchestratorService` builds proposal payloads in a shape `ProposalCommand`'s strict allowlist rejects (unhandled `ValidationError`). Add one new allowlisted command type, `"project_cycle.setup"`, whose `apply_proposal` branch reuses the existing, already-tested `ProjectOrchestrationService`/`RoutingService` AI-drafting pipeline verbatim. Wire two entry points — a new LiveKit tool for voice, and a cheap deterministic pre-check in the Hub Chat turn loop for text — both calling the same `WorkOrchestratorService.handle_command`.

**Tech Stack:** Python, FastAPI, Pydantic v2, SQLAlchemy, pytest.

**Spec:** `docs/superpowers/specs/2026-08-15-orchestrator-project-cycle-command-design.md`

## Global Constraints

- Scope all resource access by authenticated `workspace_id`; serialize Snowflake IDs as strings at any API boundary.
- Do not execute material cycle/OKR changes before owner/admin approval — every `project_cycle.setup` command must go through `AgentProposal`'s pending → approved → applied lifecycle; never write the domain rows directly from the orchestrator or from chat/voice.
- Do not loosen `ProposalCommand`'s `extra="forbid"` / strict `Literal` allowlist — fix the mismatch on the orchestrator side, which is the newer/looser layer.
- Use `backend/app` only; preserve unrelated in-progress worktree changes (this repo has a large, separate, currently-uncommitted agentic-runtime gap-closure effort in `backend/app/agents/` — do not touch files outside what each task lists).

---

### Task 1: `RoutingService.plan_stage` accepts a custom week count

**Files:**
- Modify: `backend/app/modules/strategy/routing_service.py:28-39` (prompt), `:98-127` (method)
- Test: `backend/app/tests/test_routing_service.py`

**Interfaces:**
- Produces: `RoutingService.plan_stage(self, mvp_stage_id: int, desired_weeks: int = 12) -> StagePlanDraft` (was `plan_stage(self, mvp_stage_id: int)`) — Task 2 calls this with `desired_weeks=<from proposal arguments>`.

This test file requires a real migrated Postgres (`RUN_DB_INTEGRATION=1`); the project's docker-compose Postgres already satisfies this — confirm with `docker ps --filter name=javis_postgres` before running.

- [ ] **Step 1: Write the failing tests**

Add to `backend/app/tests/test_routing_service.py` (this file already defines `_setup()` and `_worker_reply()` helpers used below):

```python
def test_plan_stage_generates_the_requested_week_count():
    from app.modules.strategy.routing_service import RoutingService

    db, ws_id, brain_id, user_id, stage_id = _setup()
    try:
        service = RoutingService(db, ws_id, brain_id, user_id)
        ai_response = (
            '{"objectives": [{"title": "Kiểm chứng PMF", "key_results": '
            '[{"title": "10 khách hàng dùng thử", "target_value": 10, "unit": "khách"}]}], '
            '"weekly_focus": ["Tuần 1", "Tuần 2", "Tuần 3", "Tuần 4", "Tuần 5", "Tuần 6"]}'
        )
        with patch(f"{_MODULE}.is_provider_configured", return_value=True), \
             patch(f"{_MODULE}.run_worker_prompt_sync", side_effect=_worker_reply(ai_response)) as mock_run:
            draft = service.plan_stage(stage_id, desired_weeks=6)

        assert len(draft.weekly_focus) == 6
        sent_prompt = mock_run.call_args.kwargs["prompt"]
        assert "ĐÚNG 6 trọng tâm tuần" in sent_prompt
    finally:
        db.rollback()
        db.close()


def test_plan_stage_still_defaults_to_twelve_weeks():
    from app.modules.strategy.routing_service import RoutingService

    db, ws_id, brain_id, user_id, stage_id = _setup()
    try:
        service = RoutingService(db, ws_id, brain_id, user_id)
        weekly_focus = ", ".join(f'"Tuần {i}"' for i in range(1, 13))
        ai_response = (
            '{"objectives": [{"title": "Kiểm chứng PMF", "key_results": []}], '
            '"weekly_focus": [' + weekly_focus + ']}'
        )
        with patch(f"{_MODULE}.is_provider_configured", return_value=True), \
             patch(f"{_MODULE}.run_worker_prompt_sync", side_effect=_worker_reply(ai_response)):
            draft = service.plan_stage(stage_id)

        assert len(draft.weekly_focus) == 12
    finally:
        db.rollback()
        db.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && RUN_DB_INTEGRATION=1 .venv/bin/python -m pytest app/tests/test_routing_service.py::test_plan_stage_generates_the_requested_week_count app/tests/test_routing_service.py::test_plan_stage_still_defaults_to_twelve_weeks -v`
Expected: `test_plan_stage_generates_the_requested_week_count` FAILS with `TypeError: plan_stage() got an unexpected keyword argument 'desired_weeks'`; `test_plan_stage_still_defaults_to_twelve_weeks` currently PASSES (this is the pre-existing behavior — keep it passing throughout).

- [ ] **Step 3: Parametrize `_PLAN_PROMPT` and `plan_stage`**

In `backend/app/modules/strategy/routing_service.py`, replace lines 28-39:

```python
_PLAN_PROMPT = (
    "Bạn là chuyên gia tư vấn OKR và 12 Week Year. Dựa trên Foundation chiến lược (vision, "
    "mission, core values - có thể trống) và giả thuyết/phạm vi của một MVP stage dưới đây, "
    "hãy đề xuất kế hoạch thực thi gồm: 1-3 objectives bám sát vision/mission, mỗi objective "
    "có 2-5 key results đo lường được (title, target_value nếu có, unit nếu có), và ĐÚNG 12 "
    "trọng tâm tuần (weekly_focus) theo thứ tự tuần 1 đến 12. Trả lời DUY NHẤT một khối JSON "
    "hợp lệ theo cấu trúc sau, không kèm giải thích:\n"
    '{{"objectives": [{{"title": "...", "key_results": [{{"title": "...", '
    '"target_value": 0, "unit": "..."}}]}}], "weekly_focus": ["tuần 1 ...", ... 12 mục]}}\n\n'
    "Foundation chiến lược: {foundation_json}\n"
    "Dữ liệu stage: {stage_json}"
)
```

with:

```python
_PLAN_PROMPT = (
    "Bạn là chuyên gia tư vấn OKR và 12 Week Year. Dựa trên Foundation chiến lược (vision, "
    "mission, core values - có thể trống) và giả thuyết/phạm vi của một MVP stage dưới đây, "
    "hãy đề xuất kế hoạch thực thi gồm: 1-3 objectives bám sát vision/mission, mỗi objective "
    "có 2-5 key results đo lường được (title, target_value nếu có, unit nếu có), và ĐÚNG "
    "{desired_weeks} trọng tâm tuần (weekly_focus) theo thứ tự tuần 1 đến {desired_weeks}. "
    "Trả lời DUY NHẤT một khối JSON hợp lệ theo cấu trúc sau, không kèm giải thích:\n"
    '{{"objectives": [{{"title": "...", "key_results": [{{"title": "...", '
    '"target_value": 0, "unit": "..."}}]}}], "weekly_focus": ["tuần 1 ...", ... '
    '{desired_weeks} mục]}}\n\n'
    "Foundation chiến lược: {foundation_json}\n"
    "Dữ liệu stage: {stage_json}"
)
```

Then replace lines 98-127 (the `plan_stage` method):

```python
    def plan_stage(self, mvp_stage_id: int) -> StagePlanDraft:
        stage = get_mvp_stage_scoped(self.db, mvp_stage_id, self.workspace_id, self.brain_id)
        foundation = fetch_foundation_context(self.db, self.workspace_id)
        prompt = _PLAN_PROMPT.format(
            foundation_json=json.dumps(foundation, ensure_ascii=False),
            stage_json=json.dumps(
                {"title": stage.title, "hypothesis": stage.hypothesis, "scope": stage.scope_jsonb.get("items", [])},
                ensure_ascii=False,
            ),
        )
        raw_text = self._run_profile(
            "STRATEGIC_ANALYZER",
            prompt,
            title="AI Stage Plan",
            manual_hint="hãy nhập kế hoạch stage thủ công",
        )
        parsed = _extract_json_block(raw_text)
        draft = None
        if parsed is not None:
            try:
                draft = StagePlanDraft.model_validate(parsed)
            except Exception:
                draft = None
        self.db.commit()
        if draft is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="AI trả về kế hoạch stage không hợp lệ, hãy nhập thủ công",
            )
        return draft
```

with:

```python
    def plan_stage(self, mvp_stage_id: int, desired_weeks: int = 12) -> StagePlanDraft:
        stage = get_mvp_stage_scoped(self.db, mvp_stage_id, self.workspace_id, self.brain_id)
        foundation = fetch_foundation_context(self.db, self.workspace_id)
        prompt = _PLAN_PROMPT.format(
            desired_weeks=desired_weeks,
            foundation_json=json.dumps(foundation, ensure_ascii=False),
            stage_json=json.dumps(
                {"title": stage.title, "hypothesis": stage.hypothesis, "scope": stage.scope_jsonb.get("items", [])},
                ensure_ascii=False,
            ),
        )
        raw_text = self._run_profile(
            "STRATEGIC_ANALYZER",
            prompt,
            title="AI Stage Plan",
            manual_hint="hãy nhập kế hoạch stage thủ công",
        )
        parsed = _extract_json_block(raw_text)
        draft = None
        if parsed is not None:
            try:
                draft = StagePlanDraft.model_validate(parsed)
            except Exception:
                draft = None
        self.db.commit()
        if draft is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="AI trả về kế hoạch stage không hợp lệ, hãy nhập thủ công",
            )
        return draft
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && RUN_DB_INTEGRATION=1 .venv/bin/python -m pytest app/tests/test_routing_service.py -v`
Expected: all PASS, including the two new tests and every pre-existing test in the file (confirms the REST endpoint `POST /stages/{id}:plan`, which calls `plan_stage` with no `desired_weeks` argument, is unaffected).

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/modules/strategy/routing_service.py app/tests/test_routing_service.py
git commit -m "feat(strategy): let RoutingService.plan_stage generate a custom week count"
```

---

### Task 2: New `project_cycle.setup` proposal command, applied via the existing orchestration pipeline

**Files:**
- Modify: `backend/app/agents/proposals/command.py:32`
- Modify: `backend/app/agents/proposals/service.py:1-15` (imports), `:193-206` (new branch)
- Test: `backend/app/tests/agents/test_agent_proposal_bridge.py`

**Interfaces:**
- Consumes: `RoutingService.plan_stage(mvp_stage_id, desired_weeks=...)` from Task 1.
- Produces: `ProposalCommand.command_type` now also accepts `"project_cycle.setup"`. `AgentProposalService.apply_proposal` now handles `proposal.proposal_type == "project_cycle"`, reading `arguments = payload["command"]["arguments"]` with keys `title: str`, `description: str | None`, `desired_week_count: int`, `existing_project_id: str | None`. Task 3 creates proposals with this exact shape.

- [ ] **Step 1: Write the failing tests**

Add to `backend/app/tests/agents/test_agent_proposal_bridge.py` (this file already imports `AgentProposal`, `AgentProposalService`, `generate_snowflake_id`, and uses the `mock_query` dispatch-by-model pattern shown in `test_agent_proposal_service_apply_okr_objective`):

```python
def test_parse_proposal_command_accepts_project_cycle_setup():
    from app.agents.proposals.command import parse_proposal_command

    command = parse_proposal_command(
        {
            "command": {
                "command_type": "project_cycle.setup",
                "idempotency_key": "cycle-1",
                "arguments": {
                    "title": "mID - Nền tảng định danh",
                    "description": "Nền tảng SSO cho nhiều ứng dụng",
                    "desired_week_count": 6,
                    "existing_project_id": None,
                },
            }
        }
    )
    assert command.command_type == "project_cycle.setup"


def test_agent_proposal_service_apply_project_cycle_setup_runs_the_full_pipeline(monkeypatch):
    from unittest.mock import MagicMock, patch
    from app.agents.proposals import service as proposals_service
    from app.modules.strategy.models import MvpStage, Project
    from app.modules.strategy.schemas.project_orchestration_schemas import RoadmapDraft, StagePlanDraft
    from app.modules.vault.models import Brain

    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    brain_id = generate_snowflake_id()
    prop_id = generate_snowflake_id()

    proposal = AgentProposal(
        id=prop_id,
        workspace_id=ws_id,
        proposal_type="project_cycle",
        title="mID - Nền tảng định danh",
        payload_jsonb={
            "command": {
                "command_type": "project_cycle.setup",
                "idempotency_key": "cycle-1",
                "arguments": {
                    "title": "mID - Nền tảng định danh",
                    "description": "Nền tảng SSO cho nhiều ứng dụng",
                    "desired_week_count": 6,
                    "existing_project_id": None,
                },
            }
        },
        status="approved",
    )

    def mock_query(model):
        q = MagicMock()
        if model == AgentProposal:
            q.filter.return_value.first.return_value = proposal
        elif model == Brain:
            q.filter.return_value.first.return_value = Brain(id=brain_id, workspace_id=ws_id, name="Brain")
        return q

    mock_db = MagicMock()
    mock_db.query.side_effect = mock_query

    stage1 = MvpStage(id=111, workspace_id=ws_id, brain_id=brain_id, project_id=222, sequence_no=1, title="Stage 1", status="CONFIRMED")
    roadmap_draft = RoadmapDraft.model_validate({"stages": [
        {"title": "Stage 1", "hypothesis": "Giả thuyết đủ dài để qua validate", "scope": ["a"], "non_goals": [], "exit_criteria": ["done"]},
    ]})
    plan_draft = StagePlanDraft.model_validate({
        "objectives": [{"title": "Kiểm chứng PMF", "key_results": []}],
        "weekly_focus": ["Tuần 1", "Tuần 2", "Tuần 3", "Tuần 4", "Tuần 5", "Tuần 6"],
    })

    with patch.object(proposals_service.ProjectOrchestrationService, "generate_roadmap", return_value=roadmap_draft) as mock_generate, \
         patch.object(proposals_service.ProjectOrchestrationService, "save_roadmap_draft", return_value=[stage1]), \
         patch.object(proposals_service.ProjectOrchestrationService, "confirm_roadmap", return_value=[stage1]), \
         patch.object(proposals_service.RoutingService, "plan_stage", return_value=plan_draft) as mock_plan, \
         patch.object(proposals_service.ProjectOrchestrationService, "activate_stage", return_value={"stage": stage1, "okr_cycle": MagicMock(), "weekly_plans": []}):
        applied = AgentProposalService.apply_proposal(
            db=mock_db, workspace_id=ws_id, proposal_id=prop_id, reviewed_by=user_id,
        )

    assert applied["status"] == "applied"
    assert applied["resource_type"] == "project_cycle"
    assert proposal.status == "applied"
    mock_plan.assert_called_once()
    assert mock_plan.call_args.kwargs["desired_weeks"] == 6
    mock_generate.assert_called_once()


def test_agent_proposal_service_apply_project_cycle_setup_keeps_status_approved_on_ai_failure():
    """AI trả JSON hỏng ở bước roadmap không được để proposal báo 'applied' trong khi
    chưa có gì được thiết lập xong - founder phải thấy lỗi và thử áp dụng lại."""
    from unittest.mock import MagicMock, patch
    from fastapi import HTTPException
    from app.agents.proposals import service as proposals_service
    from app.modules.vault.models import Brain

    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    brain_id = generate_snowflake_id()
    prop_id = generate_snowflake_id()

    proposal = AgentProposal(
        id=prop_id,
        workspace_id=ws_id,
        proposal_type="project_cycle",
        title="mID - Nền tảng định danh",
        payload_jsonb={
            "command": {
                "command_type": "project_cycle.setup",
                "idempotency_key": "cycle-2",
                "arguments": {"title": "mID", "description": None, "desired_week_count": 6, "existing_project_id": None},
            }
        },
        status="approved",
    )

    def mock_query(model):
        q = MagicMock()
        if model == AgentProposal:
            q.filter.return_value.first.return_value = proposal
        elif model == Brain:
            q.filter.return_value.first.return_value = Brain(id=brain_id, workspace_id=ws_id, name="Brain")
        return q

    mock_db = MagicMock()
    mock_db.query.side_effect = mock_query

    with patch.object(
        proposals_service.ProjectOrchestrationService, "generate_roadmap",
        side_effect=HTTPException(status_code=422, detail="AI trả về MVP roadmap không hợp lệ"),
    ):
        with pytest.raises(HTTPException):
            AgentProposalService.apply_proposal(
                db=mock_db, workspace_id=ws_id, proposal_id=prop_id, reviewed_by=user_id,
            )

    assert proposal.status == "approved"
    # Project đã được tạo trước khi roadmap-generation hỏng: đánh dấu lại để lần apply sau
    # nối vào project này thay vì tạo trùng.
    assert proposal.applied_resource_id is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest app/tests/agents/test_agent_proposal_bridge.py::test_parse_proposal_command_accepts_project_cycle_setup app/tests/agents/test_agent_proposal_bridge.py::test_agent_proposal_service_apply_project_cycle_setup_runs_the_full_pipeline app/tests/agents/test_agent_proposal_bridge.py::test_agent_proposal_service_apply_project_cycle_setup_keeps_status_approved_on_ai_failure -v`
Expected: all three FAIL — `"project_cycle.setup"` is not yet a valid `command_type` literal, so even the first test fails at `parse_proposal_command`.

- [ ] **Step 3: Add the command type**

In `backend/app/agents/proposals/command.py`, replace line 32:

```python
    command_type: Literal["okr_objective.create", "strategy_task.create"]
```

with:

```python
    command_type: Literal["okr_objective.create", "strategy_task.create", "project_cycle.setup"]
```

- [ ] **Step 4: Add imports and the apply_proposal branch**

In `backend/app/agents/proposals/service.py`, replace lines 1-15:

```python
"""Service for Agent Proposal lifecycle and applying proposals to real OKRs and Tasks."""

from datetime import datetime, timezone
from copy import deepcopy
import logging
from typing import Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.agents.proposals.models import AgentProposal
from app.agents.proposals.command import parse_proposal_command
from app.core.snowflake import generate_snowflake_id
from app.modules.strategy.models import OkrCycle, OkrObjective
from app.modules.tasks.models import Task
from app.modules.vault.models import Brain

logger = logging.getLogger(__name__)
```

with:

```python
"""Service for Agent Proposal lifecycle and applying proposals to real OKRs and Tasks."""

from datetime import datetime, timezone
from copy import deepcopy
import logging
from typing import Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.agents.proposals.models import AgentProposal
from app.agents.proposals.command import parse_proposal_command
from app.core.snowflake import generate_snowflake_id
from app.modules.strategy.models import OkrCycle, OkrObjective, Project
from app.modules.strategy.project_orchestration_service import ProjectOrchestrationService
from app.modules.strategy.routing_service import RoutingService
from app.modules.tasks.models import Task
from app.modules.vault.models import Brain

logger = logging.getLogger(__name__)
```

Then, in the same file, replace lines 193-206 (the `strategy_task` branch):

```python
        elif proposal.proposal_type == "strategy_task":
            task = Task(
                id=generate_snowflake_id(),
                workspace_id=workspace_id,
                title=payload.get("title", proposal.title),
                status=payload.get("status", "TODO"),
                priority=payload.get("priority", "MEDIUM"),
                assignee_id=payload.get("assignee_id", reviewed_by),
                source="agent_proposal",
            )
            db.add(task)
            db.flush()
            applied_res_id = str(task.id)

```

with:

```python
        elif proposal.proposal_type == "strategy_task":
            task = Task(
                id=generate_snowflake_id(),
                workspace_id=workspace_id,
                title=payload.get("title", proposal.title),
                status=payload.get("status", "TODO"),
                priority=payload.get("priority", "MEDIUM"),
                assignee_id=payload.get("assignee_id", reviewed_by),
                source="agent_proposal",
            )
            db.add(task)
            db.flush()
            applied_res_id = str(task.id)

        elif proposal.proposal_type == "project_cycle":
            arguments = payload.get("command", {}).get("arguments", {})
            desired_week_count = int(arguments.get("desired_week_count") or 12)
            # applied_resource_id ưu tiên hơn arguments: nếu một lần apply trước đã tạo
            # Project rồi hỏng ở bước roadmap/plan (AI trả JSON không hợp lệ), lần apply
            # lại sau phải nối vào đúng Project đó, không tạo trùng.
            existing_project_id = proposal.applied_resource_id or arguments.get("existing_project_id")

            brain = db.query(Brain).filter(Brain.workspace_id == workspace_id).first()
            if not brain:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Workspace chưa có Brain, không thể tạo Project",
                )

            if existing_project_id:
                project_id = int(existing_project_id)
            else:
                project = Project(
                    id=generate_snowflake_id(),
                    workspace_id=workspace_id,
                    brain_id=brain.id,
                    title=arguments.get("title") or proposal.title,
                    description=arguments.get("description") or proposal.description,
                )
                db.add(project)
                db.commit()
                project_id = project.id
                proposal.applied_resource_id = str(project_id)
                db.commit()

            orchestration = ProjectOrchestrationService(db, workspace_id, brain.id, reviewed_by)
            routing = RoutingService(db, workspace_id, brain.id, reviewed_by)

            draft = orchestration.generate_roadmap(project_id)
            orchestration.save_roadmap_draft(project_id, draft)
            stages = orchestration.confirm_roadmap(project_id)
            first_stage = next(s for s in stages if s.sequence_no == 1)
            plan_draft = routing.plan_stage(first_stage.id, desired_weeks=desired_week_count)
            orchestration.activate_stage(project_id, first_stage.id, plan_draft)
            applied_res_id = str(project_id)

```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest app/tests/agents/test_agent_proposal_bridge.py -v`
Expected: all PASS, including the three new tests and every pre-existing test in the file.

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/agents/proposals/command.py app/agents/proposals/service.py app/tests/agents/test_agent_proposal_bridge.py
git commit -m "feat(agents): apply project_cycle.setup proposals through the existing roadmap/OKR pipeline"
```

---

### Task 3: Fix the orchestrator/proposal payload-shape crash

**Files:**
- Modify: `backend/app/agents/orchestrator/service.py:79-121`
- Test: `backend/app/tests/test_work_orchestrator.py`

**Interfaces:**
- Consumes: `"project_cycle.setup"` command type from Task 2.
- Produces: `WorkOrchestratorService.ACTION_TO_COMMAND_TYPE` (new class attribute, `dict[str, str]`) mapping `OrchestratorRequest.action` strings to `ProposalCommand.command_type` values. `handle_command`'s signature is unchanged. Tasks 4 and 5 both call `handle_command` with `action="activate_cycle"`.

- [ ] **Step 1: Write the failing test**

Add to `backend/app/tests/test_work_orchestrator.py` (this file already imports `CommandCategory`, `OrchestratorRequest`, `WorkOrchestratorService`, `generate_snowflake_id`):

```python
def test_orchestrator_activate_cycle_creates_an_applicable_proposal():
    """Bug đã tái hiện trực tiếp trước khi sửa: payload cũ {"action":..., "category":...}
    bị ProposalCommand's allowlist strict từ chối với ValidationError chưa bắt. Test này
    chạy qua AgentProposalService.create_proposal THẬT (không mock) để đảm bảo payload
    sinh ra khớp đúng shape ProposalCommand chờ đợi."""
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    db = MagicMock()
    db.refresh.side_effect = lambda proposal: None

    req = OrchestratorRequest(
        category=CommandCategory.PLAN_CYCLE_COMMAND,
        action="activate_cycle",
        payload={"title": "PMF validation cycle", "desired_week_count": 6},
    )
    resp = WorkOrchestratorService.handle_command(
        db=db, workspace_id=ws_id, user_id=user_id, request=req,
    )

    assert resp.status == "proposal_created"
    created_proposal = db.add.call_args.args[0]
    assert created_proposal.payload_jsonb["command"]["command_type"] == "project_cycle.setup"
    assert created_proposal.payload_jsonb["command"]["arguments"]["desired_week_count"] == 6


def test_orchestrator_rejects_unsupported_high_risk_action_cleanly():
    """Action không có trong bảng ánh xạ phải trả về 'rejected' sạch, không crash 500."""
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    db = MagicMock()

    req = OrchestratorRequest(
        category=CommandCategory.PLAN_CYCLE_COMMAND,
        action="an_action_with_no_mapped_command_type",
        payload={},
    )
    resp = WorkOrchestratorService.handle_command(
        db=db, workspace_id=ws_id, user_id=user_id, request=req,
    )

    assert resp.status == "rejected"
    assert "an_action_with_no_mapped_command_type" in resp.message
    db.add.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest app/tests/test_work_orchestrator.py::test_orchestrator_activate_cycle_creates_an_applicable_proposal app/tests/test_work_orchestrator.py::test_orchestrator_rejects_unsupported_high_risk_action_cleanly -v`
Expected: `test_orchestrator_activate_cycle_creates_an_applicable_proposal` FAILS with an unhandled `pydantic.ValidationError` (the exact crash already reproduced during design). `test_orchestrator_rejects_unsupported_high_risk_action_cleanly` FAILS because today every `requires_approval` action creates a proposal — there is no rejection path yet.

- [ ] **Step 3: Fix `WorkOrchestratorService.handle_command`**

In `backend/app/agents/orchestrator/service.py`, replace lines 79-121:

```python
class WorkOrchestratorService:
    """Core application orchestrator handling commands from Chat and Voice."""

    @staticmethod
    def handle_command(
        db: Session,
        workspace_id: int,
        user_id: int,
        request: OrchestratorRequest,
        brain_id: Optional[int] = None,
    ) -> OrchestratorResponse:
        command_id = generate_snowflake_str()
        policy = PolicyEngine.evaluate(request)

        if not policy.allowed:
            return OrchestratorResponse(
                command_id=command_id,
                status="rejected",
                category=request.category,
                action=request.action,
                message=f"Command rejected by policy: {policy.reason}",
            )

        # High-risk / requires approval -> Create AgentProposal
        if policy.requires_approval:
            proposal = AgentProposalService.create_proposal(
                db=db,
                workspace_id=workspace_id,
                proposal_type=request.action,
                title=request.payload.get("title", f"Proposal for {request.action}"),
                description=request.payload.get("description", policy.reason),
                payload={
                    "command": {
                        "action": request.action,
                        "category": request.category.value,
                        "target_resource_type": request.target_resource_type,
                        "target_resource_id": request.target_resource_id,
                        "payload": request.payload,
                        "idempotency_key": request.idempotency_key or command_id,
                    }
                },
                agent_key="work_orchestrator",
            )
            return OrchestratorResponse(
                command_id=command_id,
                status="proposal_created",
                category=request.category,
                action=request.action,
                proposal_id=str(proposal.id),
                message="Yêu cầu có rủi ro chiến lược/tài chính, đã tạo đề xuất chờ phê duyệt.",
                result={"proposal_id": str(proposal.id), "status": proposal.status},
            )
```

with:

```python
class WorkOrchestratorService:
    """Core application orchestrator handling commands from Chat and Voice."""

    # Bảng ánh xạ action (chuỗi tự do từ chat/voice) -> command_type (allowlist chặt,
    # frozen của ProposalCommand). Action không có trong bảng bị từ chối sạch ở đây thay vì
    # để ProposalCommand's Pydantic validation ném ValidationError chưa bắt lên tận FastAPI -
    # đây chính là bug đã tái hiện: mọi PLAN_CYCLE_COMMAND từng crash 500 vì payload cũ
    # {"action":..., "category":...} không khớp shape {"command_type":..., "arguments":...}
    # mà ProposalCommand (extra="forbid") chờ đợi.
    ACTION_TO_COMMAND_TYPE = {
        "activate_cycle": "project_cycle.setup",
        "setup_project_cycle": "project_cycle.setup",
    }

    @staticmethod
    def handle_command(
        db: Session,
        workspace_id: int,
        user_id: int,
        request: OrchestratorRequest,
        brain_id: Optional[int] = None,
    ) -> OrchestratorResponse:
        command_id = generate_snowflake_str()
        policy = PolicyEngine.evaluate(request)

        if not policy.allowed:
            return OrchestratorResponse(
                command_id=command_id,
                status="rejected",
                category=request.category,
                action=request.action,
                message=f"Command rejected by policy: {policy.reason}",
            )

        # High-risk / requires approval -> Create AgentProposal
        if policy.requires_approval:
            command_type = WorkOrchestratorService.ACTION_TO_COMMAND_TYPE.get(request.action)
            if command_type is None:
                return OrchestratorResponse(
                    command_id=command_id,
                    status="rejected",
                    category=request.category,
                    action=request.action,
                    message=f"Hành động '{request.action}' chưa được hỗ trợ để tạo đề xuất.",
                )
            proposal = AgentProposalService.create_proposal(
                db=db,
                workspace_id=workspace_id,
                proposal_type=command_type.split(".")[0],
                title=request.payload.get("title", f"Proposal for {request.action}"),
                description=request.payload.get("description", policy.reason),
                payload={
                    "command": {
                        "command_type": command_type,
                        "idempotency_key": request.idempotency_key or command_id,
                        "arguments": request.payload,
                    }
                },
                agent_key="work_orchestrator",
            )
            return OrchestratorResponse(
                command_id=command_id,
                status="proposal_created",
                category=request.category,
                action=request.action,
                proposal_id=str(proposal.id),
                message="Yêu cầu có rủi ro chiến lược/tài chính, đã tạo đề xuất chờ phê duyệt.",
                result={"proposal_id": str(proposal.id), "status": proposal.status},
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest app/tests/test_work_orchestrator.py -v`
Expected: all PASS, including the two new tests and the pre-existing `test_orchestrator_creates_proposal_for_high_risk_action` (still passes unchanged — it mocks `create_proposal` so it never exercised the real payload shape either way).

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/agents/orchestrator/service.py app/tests/test_work_orchestrator.py
git commit -m "fix(agents): stop the orchestrator crashing on PLAN_CYCLE_COMMAND, map action to a real command_type"
```

---

### Task 4: Voice entry point — LiveKit tool dispatches the confirmed cycle command

**Files:**
- Modify: `backend/app/modules/company_runtime/tools.py:1-23` (imports), end of file (new tool)
- Modify: `backend/app/tests/test_tool_registry.py:113-130` (`CHAT_EXCLUDED_TOOLS`)
- Test: `backend/app/tests/company_runtime/test_runtime_tools.py`

**Interfaces:**
- Consumes: `WorkOrchestratorService.handle_command`, `OrchestratorRequest`, `CommandCategory` from Task 3.
- Produces: `runtime_dispatch_cycle_command(db, workspace_id, user_id, duration_weeks, project_hint=None, existing_project_id=None) -> dict` registered as LiveKit tool `runtime.dispatch_cycle_command`.

- [ ] **Step 1: Write the failing test**

Add to `backend/app/tests/company_runtime/test_runtime_tools.py` (this file already imports `runtime_classify_intent` from `app.modules.company_runtime.tools` and uses plain `MagicMock` for `db`):

```python
def test_runtime_dispatch_cycle_command_calls_the_orchestrator(monkeypatch):
    from app.modules.company_runtime import tools as company_runtime_tools
    from app.agents.orchestrator.command import CommandCategory, OrchestratorResponse

    captured = {}

    class _FakeOrchestrator:
        @staticmethod
        def handle_command(db, workspace_id, user_id, request):
            captured["request"] = request
            return OrchestratorResponse(
                command_id="cmd-1",
                status="proposal_created",
                category=request.category,
                action=request.action,
                proposal_id="999",
                message="Đã tạo đề xuất chờ duyệt.",
            )

    monkeypatch.setattr(company_runtime_tools, "WorkOrchestratorService", _FakeOrchestrator)

    db = MagicMock()
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()

    result = company_runtime_tools.runtime_dispatch_cycle_command(
        db, ws_id, user_id, duration_weeks=6, project_hint="mID",
    )

    assert result["status"] == "proposal_created"
    assert result["proposal_id"] == "999"
    assert captured["request"].category == CommandCategory.PLAN_CYCLE_COMMAND
    assert captured["request"].action == "activate_cycle"
    assert captured["request"].payload["desired_week_count"] == 6
    assert captured["request"].payload["title"] == "mID"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest app/tests/company_runtime/test_runtime_tools.py::test_runtime_dispatch_cycle_command_calls_the_orchestrator -v`
Expected: FAIL with `AttributeError: module 'app.modules.company_runtime.tools' has no attribute 'WorkOrchestratorService'` (the tool doesn't exist yet).

- [ ] **Step 3: Add the tool**

In `backend/app/modules/company_runtime/tools.py`, replace lines 1-23:

```python
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.core.feature_flags import (
    FLAG_COMPANY_RUNTIME_V13_1,
    FLAG_DEPENDENCY_DAG_V13_1,
    FLAG_STRUCTURED_BLOCKER_V13_1,
    FLAG_NEEDS_YOU_QUEUE_V13_1,
    FLAG_STRUCTURED_HANDOFF_V13_1,
    FLAG_REVIEW_REWORK_V13_1,
    FLAG_WORK_INSPECTOR_V13_1,
    FLAG_RUNTIME_CHECKPOINT_V13_1,
    FLAG_WORK_INTENT_CLASSIFIER_V13_1,
    is_enabled,
)
from app.core.tool_registry import register
from app.modules.company_runtime.runtime_manager import CompanyRuntimeManager
from app.modules.company_runtime.blocker_router import BlockerRouter
from app.modules.company_runtime.needs_you_service import NeedsYouService
from app.modules.company_runtime.review_service import ReviewService
from app.modules.company_runtime.handoff_service import HandoffService
from app.modules.company_runtime.intent_classifier import WorkIntentClassifier


NO_ARGS_SCHEMA = {"type": "object", "properties": {}, "required": []}
```

with:

```python
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.agents.orchestrator.command import CommandCategory, OrchestratorRequest
from app.agents.orchestrator.service import WorkOrchestratorService
from app.core.feature_flags import (
    FLAG_COMPANY_RUNTIME_V13_1,
    FLAG_DEPENDENCY_DAG_V13_1,
    FLAG_STRUCTURED_BLOCKER_V13_1,
    FLAG_NEEDS_YOU_QUEUE_V13_1,
    FLAG_STRUCTURED_HANDOFF_V13_1,
    FLAG_REVIEW_REWORK_V13_1,
    FLAG_WORK_INSPECTOR_V13_1,
    FLAG_RUNTIME_CHECKPOINT_V13_1,
    FLAG_WORK_INTENT_CLASSIFIER_V13_1,
    is_enabled,
)
from app.core.tool_registry import register
from app.modules.company_runtime.runtime_manager import CompanyRuntimeManager
from app.modules.company_runtime.blocker_router import BlockerRouter
from app.modules.company_runtime.needs_you_service import NeedsYouService
from app.modules.company_runtime.review_service import ReviewService
from app.modules.company_runtime.handoff_service import HandoffService
from app.modules.company_runtime.intent_classifier import WorkIntentClassifier


NO_ARGS_SCHEMA = {"type": "object", "properties": {}, "required": []}
```

Then append this to the end of the file (after the existing `runtime_classify_intent` function):

```python


@register("runtime", "dispatch_cycle_command", flag_key=FLAG_WORK_INTENT_CLASSIFIER_V13_1)
def runtime_dispatch_cycle_command(
    db: Session,
    workspace_id: int,
    user_id: int,
    duration_weeks: int,
    project_hint: Optional[str] = None,
    existing_project_id: Optional[str] = None,
) -> dict:
    """LiveKit tool: dispatch a confirmed N-week cycle setup through the Shared Work
    Orchestrator. Gọi SAU KHI voice agent đã đọc confirmation_prompt (từ
    runtime_classify_intent) và người dùng xác nhận bằng lời - khác nhánh Hub Chat text,
    vốn không có bước hỏi-đáp riêng trước khi tạo đề xuất."""
    request = OrchestratorRequest(
        category=CommandCategory.PLAN_CYCLE_COMMAND,
        action="activate_cycle",
        payload={
            "title": project_hint or "Dự án mới",
            "desired_week_count": duration_weeks,
            "existing_project_id": existing_project_id,
        },
    )
    response = WorkOrchestratorService.handle_command(
        db=db, workspace_id=workspace_id, user_id=user_id, request=request,
    )
    return {
        "status": response.status,
        "message": response.message,
        "proposal_id": response.proposal_id,
    }
```

- [ ] **Step 4: Exclude the new tool from chat text (voice-only, same reasoning as `runtime.classify_intent`)**

In `backend/app/tests/test_tool_registry.py`, replace line 121:

```python
    "runtime.classify_intent": "chỉ dành cho caller nội bộ, không phải lệnh người dùng",
```

with:

```python
    "runtime.classify_intent": "chỉ dành cho caller nội bộ, không phải lệnh người dùng",
    "runtime.dispatch_cycle_command": "chỉ dành cho voice agent sau khi xác nhận bằng lời - hành động hệ quả",
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest app/tests/company_runtime/test_runtime_tools.py app/tests/test_tool_registry.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/modules/company_runtime/tools.py app/tests/company_runtime/test_runtime_tools.py app/tests/test_tool_registry.py
git commit -m "feat(voice): add runtime.dispatch_cycle_command LiveKit tool"
```

---

### Task 5: Hub Chat text entry point — deterministic short-circuit before the AI loop

**Files:**
- Modify: `backend/app/modules/chat/chat_execution_service.py:1-18` (imports), `:275-276` (insertion point), end of file (new helper)
- Test: `backend/app/tests/test_chat_execution_service.py`

**Interfaces:**
- Consumes: `WorkOrchestratorService.handle_command`, `OrchestratorRequest`, `CommandCategory` from Task 3; `WorkIntentClassifier.classify` (pre-existing, unmodified).
- Produces: `_dispatch_cycle_change_command(db, publisher, workspace_id, session, user_message, assistant, run) -> bool` — `True` means the turn was fully handled (caller must `return` immediately, matching the other early-return branches already in `_execute_turn`), `False` means fall through to the normal AI+tool loop.

- [ ] **Step 1: Write the failing tests**

Add to `backend/app/tests/test_chat_execution_service.py` (this file already defines `_make_pending`, `_FakeRouter`, and imports `chat_execution_service`, `MagicMock`, `asyncio`):

```python
def test_worker_short_circuits_cycle_change_messages_through_the_orchestrator(monkeypatch):
    """Tin nhắn kiểu 'lập chu kỳ 6 tuần cho dự án X' phải đi qua Shared Work Orchestrator -
    không được vào vòng lặp AI+tool chung, vì đó chính là chỗ dễ khiến AI tự bịa JSON
    roadmap/OKR thay vì dùng đúng prompt chuyên biệt đã có sẵn cho việc đó."""
    db = MagicMock()
    user_message = _make_pending(db)
    user_message.content = "Lập chu kỳ 6 tuần cho dự án Alpha"
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

    from app.agents.orchestrator.command import OrchestratorResponse

    class _FakeOrchestrator:
        calls = []

        @staticmethod
        def handle_command(db, workspace_id, user_id, request):
            _FakeOrchestrator.calls.append(request)
            return OrchestratorResponse(
                command_id="cmd-1",
                status="proposal_created",
                category=request.category,
                action=request.action,
                proposal_id="999",
                message="Đã tạo đề xuất chờ duyệt.",
            )

    monkeypatch.setattr(chat_execution_service, "WorkOrchestratorService", _FakeOrchestrator)
    db.query.return_value.filter.return_value.scalar.return_value = "streaming"
    router = _FakeRouter()

    processed = asyncio.run(process_pending_chat_messages(db, router))

    assert processed == 1
    assert router._seen_calls == []
    added = [call.args[0] for call in db.add.call_args_list]
    assistant = next(item for item in added if isinstance(item, ChatMessage))
    assert assistant.content == "Đã tạo đề xuất chờ duyệt."
    assert assistant.status == "delivered"
    assert user_message.status == "processed"
    assert len(_FakeOrchestrator.calls) == 1
    assert _FakeOrchestrator.calls[0].payload["desired_week_count"] == 6


def test_worker_leaves_ordinary_messages_in_the_normal_ai_loop():
    """Chốt chặn cho short-circuit ở trên: một câu hỏi thường vẫn phải đi qua vòng lặp
    AI+tool y hệt trước đây, không bị nhánh CYCLE_CHANGE nuốt mất."""
    db = MagicMock()
    _make_pending(db)
    db.query.return_value.filter.return_value.scalar.return_value = "streaming"
    router = _FakeRouter()

    processed = asyncio.run(process_pending_chat_messages(db, router))

    assert processed == 1
    assert len(router._seen_calls) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest app/tests/test_chat_execution_service.py::test_worker_short_circuits_cycle_change_messages_through_the_orchestrator app/tests/test_chat_execution_service.py::test_worker_leaves_ordinary_messages_in_the_normal_ai_loop -v`
Expected: `test_worker_short_circuits_cycle_change_messages_through_the_orchestrator` FAILS with `AttributeError: module 'app.modules.chat.chat_execution_service' has no attribute 'WorkOrchestratorService'`. `test_worker_leaves_ordinary_messages_in_the_normal_ai_loop` currently PASSES (pre-existing behavior — keep it passing).

- [ ] **Step 3: Add imports**

In `backend/app/modules/chat/chat_execution_service.py`, replace lines 1-18:

```python
import logging
import time
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.models import AIRun, Brain, ChatMessage, ChatSession, MCPConnection
from app.modules.chat import company_tools, gmail_tools
from app.modules.chat.ai_router import AIRouter, ChatTurn
from app.modules.chat.chat_stream_bus import ChatEventPublisher, NullChatEventPublisher
from app.modules.chat.model_registry import DEFAULT_MODEL, DEFAULT_PROVIDER, get_model
from app.modules.chat.models import ONESHOT_PURPOSE
from app.modules.integrations.google_connection_service import (
    CONNECTOR_TYPE as GOOGLE_CONNECTOR_TYPE,
    has_usable_google_connection,
)
from app.core.snowflake import generate_snowflake_id
```

with:

```python
import logging
import time
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.agents.orchestrator.command import CommandCategory, OrchestratorRequest
from app.agents.orchestrator.service import WorkOrchestratorService
from app.db.models import AIRun, Brain, ChatMessage, ChatSession, MCPConnection
from app.modules.chat import company_tools, gmail_tools
from app.modules.chat.ai_router import AIRouter, ChatTurn
from app.modules.chat.chat_stream_bus import ChatEventPublisher, NullChatEventPublisher
from app.modules.chat.model_registry import DEFAULT_MODEL, DEFAULT_PROVIDER, get_model
from app.modules.chat.models import ONESHOT_PURPOSE
from app.modules.company_runtime.intent_classifier import WorkIntentClassifier
from app.modules.integrations.google_connection_service import (
    CONNECTOR_TYPE as GOOGLE_CONNECTOR_TYPE,
    has_usable_google_connection,
)
from app.modules.strategy.models import Project
from app.core.snowflake import generate_snowflake_id
```

- [ ] **Step 4: Insert the short-circuit call and add the helper function**

In `backend/app/modules/chat/chat_execution_service.py`, replace lines 275-276:

```python
    one_shot = session.purpose == ONESHOT_PURPOSE

```

with:

```python
    one_shot = session.purpose == ONESHOT_PURPOSE

    if not one_shot and _dispatch_cycle_change_command(
        db, publisher, brain.workspace_id, session, user_message, assistant, run,
    ):
        return

```

Then append this function to the end of the file (after `process_pending_chat_messages`):

```python


def _dispatch_cycle_change_command(
    db: Session,
    publisher: ChatEventPublisher,
    workspace_id: int,
    session: ChatSession,
    user_message: ChatMessage,
    assistant: ChatMessage,
    run: AIRun,
) -> bool:
    """Rẻ, không tốn AI call: phân loại bằng regex trước khi vào vòng lặp AI+tool. Khớp
    CYCLE_CHANGE thì đi thẳng qua Shared Work Orchestrator (dùng đúng prompt chuyên biệt
    có sẵn cho roadmap/OKR ở agents/proposals) thay vì để general chat model tự bịa JSON.
    Trả về True nếu đã xử lý xong lượt này (caller phải return ngay), False nếu phải đi
    tiếp vào vòng lặp hội thoại thông thường."""
    classification = WorkIntentClassifier.classify(user_message.content)
    if classification["intent"] != "CYCLE_CHANGE":
        return False

    project_hint = classification.get("project_hint")
    existing_project = None
    if project_hint:
        existing_project = (
            db.query(Project)
            .filter(Project.workspace_id == workspace_id, Project.title.ilike(f"%{project_hint}%"))
            .order_by(Project.created_at.desc())
            .first()
        )

    request = OrchestratorRequest(
        category=CommandCategory.PLAN_CYCLE_COMMAND,
        action="activate_cycle",
        payload={
            "title": project_hint or "Dự án mới",
            "desired_week_count": classification["duration_weeks"],
            "existing_project_id": str(existing_project.id) if existing_project else None,
        },
    )
    response = WorkOrchestratorService.handle_command(
        db=db, workspace_id=workspace_id, user_id=session.user_id, request=request,
    )

    delivered = response.status != "rejected"
    assistant.content = response.message
    assistant.status = "delivered" if delivered else "error"
    user_message.status = "processed" if delivered else "error"
    run.status = "completed" if delivered else "failed"
    run.finished_at = datetime.utcnow()
    db.commit()
    publisher.status(session.id, assistant.id, assistant.status, len(assistant.content))
    return True
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest app/tests/test_chat_execution_service.py -v`
Expected: all PASS, including the two new tests and every pre-existing test in the file — confirms every intent other than `CYCLE_CHANGE` (`CHAT`, `QUICK_TASK`, `COMPANY_WORK`, `STRATEGIC`, `APPROVAL`) still falls through to the unchanged AI+tool loop.

- [ ] **Step 6: Run the full backend test suite for the touched areas**

Run: `cd backend && .venv/bin/python -m pytest app/tests/test_chat_execution_service.py app/tests/test_work_orchestrator.py app/tests/agents/test_agent_proposal_bridge.py app/tests/test_tool_registry.py app/tests/company_runtime/test_runtime_tools.py -v`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
cd backend
git add app/modules/chat/chat_execution_service.py app/tests/test_chat_execution_service.py
git commit -m "feat(chat): short-circuit CYCLE_CHANGE messages through the Shared Work Orchestrator"
```

## Known Limitation (accepted, not fixed in this plan)

`ProjectOrchestrationService`/`RoutingService`'s methods each commit internally (they are used standalone by the manual REST/UI flow today, and this plan deliberately reuses them unmodified). If `apply_proposal`'s new branch fails partway *after* `confirm_roadmap` has already committed (e.g. `plan_stage`'s AI call returns invalid JSON), a retry of the same proposal will hit `confirm_roadmap`'s existing 422 ("Chưa có MVP roadmap nháp để xác nhận") because there are no DRAFT stages left to confirm. `proposal.applied_resource_id` still correctly points at the already-created Project, so this is recoverable through the existing manual UI (`ProjectKickoffView`) — not a silent data-loss, but not a clean automatic retry either. Making the whole pipeline atomic (single outer transaction/savepoint) is out of scope here; flagging it explicitly so it isn't rediscovered as a surprise.

## Plan Self-Review

- **Spec coverage:** root-cause fix (Task 3), new command type + apply pipeline (Task 2), custom week count (Task 1), both entry points (Task 4 voice, Task 5 chat) — every section of the spec has a task. The spec's explicit "Out of Scope" items (loosening `ProposalCommand`, progress reporting/Hologram UX, the garbled-text bug, in-chat roadmap editing before approval) have no corresponding task, as intended.
- **Placeholder scan:** no TBD/TODO; every step has real code or an exact shell command.
- **Type/name consistency checked:** `proposal_type` is `"project_cycle"` everywhere (Task 2's branch check, Task 3's `command_type.split(".")[0]` derivation from `"project_cycle.setup"`); `desired_week_count` is the argument key used consistently by Task 2 (reads it), Task 3 (test asserts it), Task 4 and Task 5 (both write it into `request.payload`); `existing_project_id` is a string-or-None in every producer/consumer (Task 2 does `int(existing_project_id)` before use).
- **Task ordering respects dependencies:** Task 1 (independent) → Task 2 (needs Task 1's `plan_stage(desired_weeks=...)`) → Task 3 (needs Task 2's `"project_cycle.setup"` literal to exist before its test can create a valid proposal) → Task 4 and Task 5 (both need Task 3's fixed `handle_command`; independent of each other).
