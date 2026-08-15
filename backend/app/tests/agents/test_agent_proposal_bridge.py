from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.agents.proposals.models import AgentProposal
from app.agents.proposals.command import parse_proposal_command
from app.agents.proposals.service import AgentProposalService
from app.core.auth import get_current_workspace_member
from app.core.snowflake import generate_snowflake_id
from app.db.session import get_db
from app.main import app
from app.modules.iam.models import WorkspaceMember
from app.modules.strategy.models import OkrObjective, OkrCycle
from app.modules.tasks.models import Task


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
