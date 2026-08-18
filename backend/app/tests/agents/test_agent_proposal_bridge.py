from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.workforce.agents.proposals.models import AgentProposal
from app.workforce.agents.proposals.command import parse_proposal_command
from app.workforce.agents.proposals.service import AgentProposalService
from app.core.auth import get_current_workspace_member
from app.core.snowflake import generate_snowflake_id
from app.db.session import get_db
from app.main import app
from app.platform.auth.models import WorkspaceMember
from app.founder_os.strategy.models import OkrObjective, OkrCycle
from app.founder_os.tasks.models import Task


def test_parse_proposal_command_requires_command_payload():
    with pytest.raises(ValueError):
        parse_proposal_command({"title": "missing command"})


def test_parse_proposal_command_rejects_unknown_command_type():
    with pytest.raises(ValueError):
        parse_proposal_command(
            {
                "command": {
                    "command_type": "calendar_event.create",
                    "idempotency_key": "event-1",
                    "arguments": {},
                }
            }
        )


def test_parse_proposal_command_deep_freezes_arguments():
    command = parse_proposal_command(
        {
            "command": {
                "command_type": "strategy_task.create",
                "idempotency_key": "task-1",
                "arguments": {"labels": ["urgent"]},
            }
        }
    )

    with pytest.raises(TypeError):
        command.arguments["labels"] = []
    with pytest.raises(AttributeError):
        command.arguments["labels"].append("security")


def test_create_proposal_validates_and_retains_typed_command_without_mutating_payload():
    ws_id = generate_snowflake_id()
    payload = {
        "command": {
            "command_type": "okr_objective.create",
            "idempotency_key": "okr-1",
            "arguments": {"title": "Increase retention"},
        },
        "display": {"title": "Increase retention"},
    }
    original_payload = payload.copy()
    mock_db = MagicMock()
    mock_db.refresh.side_effect = lambda proposal: None

    proposal = AgentProposalService.create_proposal(
        db=mock_db,
        workspace_id=ws_id,
        proposal_type="okr_objective",
        title="Increase retention",
        payload=payload,
    )

    assert payload == original_payload
    assert proposal.payload_jsonb == payload
    assert proposal.payload_jsonb is not payload
    assert proposal.payload_jsonb["command"]["command_type"] == "okr_objective.create"


def test_agent_proposal_service_crud_and_review():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    prop_id = generate_snowflake_id()

    mock_db = MagicMock()
    proposal = AgentProposal(
        id=prop_id,
        workspace_id=ws_id,
        proposal_type="okr_objective",
        title="Increase Lead Conversion",
        payload_jsonb={"title": "Increase Lead Conversion", "target": 25},
        status="pending",
    )

    mock_db.query.return_value.filter.return_value.first.return_value = proposal
    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [proposal]

    # 1. List proposals
    listed = AgentProposalService.list_proposals(mock_db, ws_id)
    assert len(listed) == 1

    # 2. Get proposal
    fetched = AgentProposalService.get_proposal(mock_db, ws_id, prop_id)
    assert fetched is not None
    assert fetched.id == prop_id

    # 3. Review proposal (approve)
    approved = AgentProposalService.review_proposal(
        mock_db, workspace_id=ws_id, proposal_id=prop_id, reviewed_by=user_id, action="approve"
    )
    assert approved.status == "approved"
    assert approved.reviewed_by == user_id


def test_agent_proposal_service_apply_okr_objective():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    prop_id = generate_snowflake_id()
    cycle_id = generate_snowflake_id()

    mock_db = MagicMock()
    proposal = AgentProposal(
        id=prop_id,
        workspace_id=ws_id,
        proposal_type="okr_objective",
        title="Double Organic Traffic",
        payload_jsonb={"title": "Double Organic Traffic", "cycle_id": cycle_id},
        status="approved",
    )

    def mock_query(model):
        q = MagicMock()
        if model == AgentProposal:
            q.filter.return_value.first.return_value = proposal
        elif model == OkrCycle:
            q.filter.return_value.order_by.return_value.first.return_value = OkrCycle(id=cycle_id, workspace_id=ws_id)
        return q

    mock_db.query.side_effect = mock_query

    applied_res = AgentProposalService.apply_proposal(
        db=mock_db,
        workspace_id=ws_id,
        proposal_id=prop_id,
        reviewed_by=user_id,
    )

    assert applied_res["status"] == "applied"
    assert applied_res["resource_type"] == "okr_objective"
    assert applied_res["resource_id"] is not None
    assert proposal.status == "applied"
    assert mock_db.commit.called


def test_agent_proposal_service_apply_strategy_task():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    prop_id = generate_snowflake_id()

    mock_db = MagicMock()
    proposal = AgentProposal(
        id=prop_id,
        workspace_id=ws_id,
        proposal_type="strategy_task",
        title="Audit pricing page dropoff",
        payload_jsonb={"title": "Audit pricing page dropoff", "priority": "HIGH"},
        status="pending",
    )

    mock_db.query.return_value.filter.return_value.first.return_value = proposal

    applied_res = AgentProposalService.apply_proposal(
        db=mock_db,
        workspace_id=ws_id,
        proposal_id=prop_id,
        reviewed_by=user_id,
    )

    assert applied_res["status"] == "applied"
    assert applied_res["resource_type"] == "strategy_task"
    assert applied_res["resource_id"] is not None
    assert proposal.status == "applied"


def test_agent_proposal_endpoints(client: TestClient):
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    prop_id = generate_snowflake_id()

    member = MagicMock()
    member.workspace_id = ws_id
    member.user_id = user_id

    app.dependency_overrides[get_current_workspace_member] = lambda: member

    proposal = AgentProposal(
        id=prop_id,
        workspace_id=ws_id,
        proposal_type="okr_objective",
        title="REST Endpoint OKR Proposal",
        payload_jsonb={"title": "REST Endpoint OKR Proposal"},
        status="pending",
    )

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [proposal]
    mock_db.query.return_value.filter.return_value.first.return_value = proposal
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        # GET /api/v1/agents/proposals
        res_list = client.get("/api/v1/agents/proposals")
        assert res_list.status_code == 200
        data = res_list.json()
        assert len(data) == 1
        assert data[0]["id"] == str(prop_id)

        # POST /api/v1/agents/proposals/{id}/review
        res_rev = client.post(
            f"/api/v1/agents/proposals/{prop_id}/review",
            json={"action": "approve"},
        )
        assert res_rev.status_code == 200
        assert res_rev.json()["status"] == "approved"

        # POST /api/v1/agents/proposals/{id}/apply
        res_apply = client.post(f"/api/v1/agents/proposals/{prop_id}/apply")
        assert res_apply.status_code == 200
        assert res_apply.json()["status"] == "applied"
    finally:
        app.dependency_overrides.pop(get_current_workspace_member, None)
        app.dependency_overrides.pop(get_db, None)


def test_parse_proposal_command_accepts_project_cycle_setup():
    from app.workforce.agents.proposals.command import parse_proposal_command

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
    from app.workforce.agents.proposals import service as proposals_service
    from app.founder_os.strategy.models import MvpStage, Project
    from app.founder_os.strategy.schemas.project_orchestration_schemas import RoadmapDraft, StagePlanDraft
    from app.platform.vault.models import Brain

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
        {"title": "Stage 2", "hypothesis": "Giả thuyết đủ dài để qua validate 2", "scope": ["b"], "non_goals": [], "exit_criteria": ["done2"]},
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
    from app.workforce.agents.proposals import service as proposals_service
    from app.platform.vault.models import Brain

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

