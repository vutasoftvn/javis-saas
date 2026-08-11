import uuid
from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException

from app.modules.strategy.models import (
    NextActionCandidate,
    NextActionRanking,
    GateDecision,
    ProjectPestelImpact,
    PortfolioDependency,
    CycleStage,
)
from app.modules.platform.models import FeatureFlag
from app.modules.strategy.next_best_action_service import NextBestActionService
from app.modules.chat.ai_router import AIEvent, ChatTurn


def test_r0_score_computation():
    # Urgency 0.9, Impact 0.8, Effort 0.4 -> (0.9*0.4)+(0.8*0.4)+((1-0.4)*0.2) = 0.36 + 0.32 + 0.12 = 0.80
    score = NextBestActionService.compute_r0_score(0.9, 0.8, 0.4)
    assert score == 0.80


def test_generate_and_evaluate_next_actions():
    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    db = MagicMock()

    gate_dec = GateDecision(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        project_id=proj_id,
        decision="HOLD",
        rationale="Waiting for MVP metric evidence",
        decided_by=user_id,
    )
    pestel_imp = ProjectPestelImpact(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        project_id=proj_id,
        pestel_item_id=uuid.uuid4(),
        impact_type="NEGATIVE",
        impact_magnitude="HIGH",
        mitigation_or_leverage=None,
    )

    def query_mock(model):
        m = MagicMock()
        m.filter.return_value = m
        if model == GateDecision:
            m.all.return_value = [gate_dec]
        elif model == ProjectPestelImpact:
            m.all.return_value = [pestel_imp]
        elif model == NextActionCandidate:
            m.all.return_value = []
        return m


    db.query.side_effect = query_mock


    service = NextBestActionService(db, ws_id, user_id)

    # Evaluate and rank candidates (AI rerank off -> deterministic R1 order, no network call)
    rankings = service.evaluate_and_rank(project_id=proj_id, use_ai_rerank=False)
    assert len(rankings) == 2
    assert rankings[0]["rank_position"] == 1
    assert rankings[0]["composite_score"] >= rankings[1]["composite_score"]


def test_update_next_action_status():
    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()
    act_id = uuid.uuid4()
    db = MagicMock()

    cand = NextActionCandidate(
        id=act_id,
        workspace_id=ws_id,
        title="Approve Gate",
        category="STAGE_GATE_REVIEW",
        status="proposed",
    )

    def query_mock(model):
        m = MagicMock()
        if model == NextActionCandidate:
            m.filter.return_value.first.return_value = cand
        return m

    db.query.side_effect = query_mock

    service = NextBestActionService(db, ws_id, user_id)

    res = service.update_action_status(act_id, "accepted")
    assert res["status"] == "accepted"


def test_next_action_endpoints():
    from app.modules.strategy.next_action_router import (
        get_ceo_next_actions,
        evaluate_ceo_next_actions,
        update_next_action_status,
        NextActionStatusUpdate,
    )
    from app.tests.test_strategy_endpoints import mock_member

    ws_id = uuid.uuid4()
    act_id = uuid.uuid4()
    member = mock_member()
    db = MagicMock()

    cand = NextActionCandidate(
        id=act_id,
        workspace_id=ws_id,
        title="CEO Strategic Review",
        category="GOVERNANCE_DECISION",
        urgency_score=0.9,
        impact_score=0.9,
        effort_score=0.2,
        r0_score=0.88,
        status="proposed",
    )

    def query_mock(model):
        m = MagicMock()
        if model == NextActionCandidate:
            m.filter.return_value.first.return_value = cand
            m.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [cand]
        elif model == CycleStage:
            m.filter.return_value.all.return_value = []
        elif model == ProjectPestelImpact:
            m.filter.return_value.all.return_value = []
        elif model == FeatureFlag:
            m.filter.return_value.first.return_value = FeatureFlag(key="next_best_action_v12", enabled=True)
        return m

    db.query.side_effect = query_mock

    # 1. Get CEO Next Actions
    actions_res = get_ceo_next_actions(ws_id, limit=5, member=member, db=db)
    assert len(actions_res["next_actions"]) == 1
    assert actions_res["next_actions"][0]["title"] == "CEO Strategic Review"

    # 2. Update Status
    up_res = update_next_action_status(act_id, ws_id, NextActionStatusUpdate(status="executed"), member, db)
    assert up_res["status"] == "executed"


def _make_candidate(ws_id, r0=0.5, category="GENERIC", project_id=None):
    return NextActionCandidate(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        project_id=project_id,
        title=f"Candidate {category}",
        category=category,
        urgency_score=r0, impact_score=r0, effort_score=1 - r0,
        r0_score=r0,
        status="proposed",
    )


def test_r1_rules_dependency_unlock_and_governance_bonus():
    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()
    unlock_proj_id = uuid.uuid4()
    db = MagicMock()

    dep = PortfolioDependency(id=uuid.uuid4(), workspace_id=ws_id, predecessor_project_id=unlock_proj_id, successor_project_id=uuid.uuid4())

    def query_mock(model):
        m = MagicMock()
        m.filter.return_value = m
        if model == PortfolioDependency:
            m.all.return_value = [dep]
        return m

    db.query.side_effect = query_mock
    service = NextBestActionService(db, ws_id, user_id)

    plain = _make_candidate(ws_id, r0=0.5, category="GENERIC")
    unlocking = _make_candidate(ws_id, r0=0.5, category="GENERIC", project_id=unlock_proj_id)
    governance = _make_candidate(ws_id, r0=0.5, category="GOVERNANCE_DECISION")

    scored = service._apply_r1_rules([plain, unlocking, governance])
    by_cand = {c.id: (score, reasoning) for c, score, reasoning in scored}

    assert by_cand[plain.id][0] == 0.5
    assert by_cand[unlocking.id][0] == 0.55
    assert "Dependency Unlock" in by_cand[unlocking.id][1]
    assert by_cand[governance.id][0] == 0.53
    assert "GOVERNANCE_DECISION" in by_cand[governance.id][1]
    # Sorted descending by R1 score
    assert [c.id for c, _, _ in scored] == [unlocking.id, governance.id, plain.id]


def test_ai_rerank_skipped_when_provider_not_configured():
    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()
    db = MagicMock()
    service = NextBestActionService(db, ws_id, user_id)

    cand = _make_candidate(ws_id)
    r1_scored = [(cand, 0.5, "R0=0.5; R1=0.5")]

    with patch("app.modules.strategy.next_best_action_service.is_provider_configured", return_value=False):
        result, round_used = service._maybe_ai_rerank(r1_scored)

    assert round_used == "R1_RULES"
    assert result == r1_scored


class _FakeChatProvider:
    def __init__(self, response_text: str, fail: bool = False):
        self.response_text = response_text
        self.fail = fail

    async def stream_chat(self, turns, tools=None):
        if self.fail:
            yield AIEvent(kind="failed", error_code="provider_error")
            return
        yield AIEvent(kind="delta", content=self.response_text)
        yield AIEvent(kind="completed")


def test_ai_rerank_reorders_shortlist_on_valid_response():
    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()
    db = MagicMock()
    service = NextBestActionService(db, ws_id, user_id)

    cand_a = _make_candidate(ws_id, r0=0.6, category="A")
    cand_b = _make_candidate(ws_id, r0=0.5, category="B")
    r1_scored = [(cand_a, 0.6, "R0=0.6"), (cand_b, 0.5, "R0=0.5")]

    # AI flips the order: b then a
    ai_response = (
        '{"ranking": ['
        f'{{"id": "{cand_b.id}", "reasoning": "Chặn đường tới hạn"}}, '
        f'{{"id": "{cand_a.id}", "reasoning": "Ít khẩn cấp hơn dự kiến"}}'
        ']}'
    )
    fake_provider = _FakeChatProvider(ai_response)

    with patch("app.modules.strategy.next_best_action_service.resolve_profile", return_value=("openai", "gpt-4o")), \
         patch("app.modules.strategy.next_best_action_service.is_provider_configured", return_value=True), \
         patch("app.modules.strategy.next_best_action_service.build_profile_provider", return_value=fake_provider):
        result, round_used = service._maybe_ai_rerank(r1_scored)

    assert round_used == "R2_AI_TERRA"
    assert [c.id for c, _, _ in result] == [cand_b.id, cand_a.id]
    assert "Chặn đường tới hạn" in result[0][2]
    assert db.add.called  # ModelRunAudit ghi lại


def test_ai_rerank_falls_back_to_r1_on_malformed_response():
    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()
    db = MagicMock()
    service = NextBestActionService(db, ws_id, user_id)

    cand = _make_candidate(ws_id)
    r1_scored = [(cand, 0.5, "R0=0.5")]

    fake_provider = _FakeChatProvider("not valid json at all")

    with patch("app.modules.strategy.next_best_action_service.resolve_profile", return_value=("openai", "gpt-4o")), \
         patch("app.modules.strategy.next_best_action_service.is_provider_configured", return_value=True), \
         patch("app.modules.strategy.next_best_action_service.build_profile_provider", return_value=fake_provider):
        result, round_used = service._maybe_ai_rerank(r1_scored)

    assert round_used == "R1_RULES"
    assert result == r1_scored


def test_ai_rerank_falls_back_to_r1_on_provider_stream_failure():
    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()
    db = MagicMock()
    service = NextBestActionService(db, ws_id, user_id)

    cand = _make_candidate(ws_id)
    r1_scored = [(cand, 0.5, "R0=0.5")]

    fake_provider = _FakeChatProvider("", fail=True)

    with patch("app.modules.strategy.next_best_action_service.resolve_profile", return_value=("openai", "gpt-4o")), \
         patch("app.modules.strategy.next_best_action_service.is_provider_configured", return_value=True), \
         patch("app.modules.strategy.next_best_action_service.build_profile_provider", return_value=fake_provider):
        result, round_used = service._maybe_ai_rerank(r1_scored)

    assert round_used == "R1_RULES"
    assert result == r1_scored
