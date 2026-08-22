import json
from unittest.mock import MagicMock, AsyncMock, patch
import pytest
from fastapi import HTTPException
from founder_os.strategy.okrs_router import (
    OkrCycleCreate, OkrObjectiveCreate, KeyResultCreate,
    create_okr_cycle, create_okr_objective, create_key_result,
    list_okr_objectives, list_key_results
)
from founder_os.strategy.execution_router import (
    TwelveWeekCycleCreate, WeeklyPlanCreate, WeeklyCommitmentCreate,
    create_twelve_week_cycle, create_weekly_plan, create_weekly_commitment,
    list_weekly_plans, list_weekly_commitments
)
from founder_os.strategy.router import (
    ProjectCreate, create_project
)
from founder_os.strategy.routers.canvas_router import (
    CanvasCreate, create_canvas, get_canvas_detail, delete_canvas, generate_ai_foundation,
)
from founder_os.strategy.schemas.canvas_schemas import (
    RevisionCreate, ApproveRevisionBody, RequestChangesBody, FoundationSave,
)
from db.models import WorkspaceMember, OkrObjective, KeyResult, WeeklyPlan, WeeklyCommitment, Project, TwelveWeekCycle, Brain, StrategyCanvas, StrategyRevision
from core.snowflake import generate_snowflake_id



def mock_member():
    m = MagicMock(spec=WorkspaceMember)
    m.user_id = generate_snowflake_id()
    m.workspace_id = generate_snowflake_id()
    m.role = "admin"
    return m


def test_create_and_list_okr():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    member = mock_member()
    
    # Mock brain
    db.query.return_value.filter.return_value.first.return_value = None
    
    cycle = create_okr_cycle(ws_id, OkrCycleCreate(name="Q3 OKR Cycle"), member, db)
    assert cycle["name"] == "Q3 OKR Cycle"
    assert db.add.called
    assert db.commit.called


def test_create_okr_objective_and_key_result():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    member = mock_member()
    
    # Objective
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = MagicMock(id=generate_snowflake_id())
    obj_data = OkrObjectiveCreate(title="Increase MRR by 50%")
    obj = create_okr_objective(ws_id, obj_data, member, db)
    assert obj["title"] == "Increase MRR by 50%"

    # Key Result
    db.query.return_value.filter.return_value.first.return_value = MagicMock(id=generate_snowflake_id())
    kr_data = KeyResultCreate(objective_id=generate_snowflake_id(), baseline_value=10.0, current_value=25.0, target_value=50.0, unit="k$")
    kr = create_key_result(ws_id, kr_data, member, db)
    assert kr["target_value"] == 50.0
    assert kr["unit"] == "k$"


def test_create_canvas_endpoint_accepts_name_field():
    # Regression test: CanvasCreate used to declare `title` while the router read
    # `data.name` and the frontend sent `name` - a schema/handler mismatch that
    # produced a 422 "title Field required" for every real create-canvas request.
    db = MagicMock()
    ws_id = generate_snowflake_id()
    member = mock_member()

    db.query.return_value.filter.return_value.first.return_value = MagicMock(spec=Brain, id=generate_snowflake_id())

    canvas = create_canvas(
        ws_id,
        CanvasCreate(name="MIVA Corp", description="Nen tang dinh danh"),
        member,
        db,
    )
    assert canvas["name"] == "MIVA Corp"
    assert canvas["description"] == "Nen tang dinh danh"
    assert db.commit.called


def test_get_canvas_detail_lists_revisions_and_active_revision():
    # Regression test: get_canvas_detail called svc.list_revisions()/svc.get_active_revision(),
    # neither of which existed on StrategyCanvasService - every canvas detail fetch (the
    # request the UI fires right after creating a canvas) 500'd with AttributeError.
    db = MagicMock()
    ws_id = generate_snowflake_id()
    member = mock_member()
    canvas_id = generate_snowflake_id()

    mock_canvas = MagicMock(spec=StrategyCanvas, id=canvas_id, description=None, status="draft", created_at=None)
    mock_canvas.name = "Company Strategy"
    mock_revision = MagicMock(spec=StrategyRevision, id=generate_snowflake_id(), canvas_id=canvas_id, revision_no=1, status="draft", parent_revision_id=None, approved_by=None, approved_at=None, created_at=None)

    def query_side_effect(model):
        m = MagicMock()
        if model is StrategyCanvas:
            m.filter.return_value.first.return_value = mock_canvas
        elif model is StrategyRevision:
            m.filter.return_value.order_by.return_value.all.return_value = [mock_revision]
            m.filter.return_value.first.return_value = None
        return m

    db.query.side_effect = query_side_effect

    result = get_canvas_detail(canvas_id, ws_id, member, db)
    assert result["canvas"]["name"] == "Company Strategy"
    assert len(result["revisions"]) == 1
    assert result["revisions"][0]["revision_no"] == 1
    assert result["active_revision"] is None


def test_delete_canvas_endpoint_succeeds_without_false_404():
    # Regression test: StrategyCanvasService.delete_canvas() returns None on success
    # (it either raises 404 via _get_canvas or completes and falls off the end).
    # The router used to do `ok = svc.delete_canvas(canvas_id); if not ok: raise 404`,
    # which misread that None as failure and 404'd on every successful delete - the
    # canvas was actually removed from the DB while the client was told it wasn't found.
    db = MagicMock()
    ws_id = generate_snowflake_id()
    member = mock_member()
    canvas_id = generate_snowflake_id()

    mock_canvas = MagicMock(spec=StrategyCanvas, id=canvas_id, name="Company Strategy")

    def query_side_effect(model):
        m = MagicMock()
        if model is StrategyCanvas:
            m.filter.return_value.first.return_value = mock_canvas
        elif model is StrategyRevision:
            m.filter.return_value.all.return_value = []
        return m

    db.query.side_effect = query_side_effect

    result = delete_canvas(canvas_id, ws_id, member, db)
    assert result == {"status": "deleted", "id": str(canvas_id)}
    assert db.delete.called
    assert db.commit.called


def _mock_canvas_and_brain_query(mock_canvas, mock_brain):
    def query_side_effect(model):
        m = MagicMock()
        if model is StrategyCanvas:
            m.filter.return_value.first.return_value = mock_canvas
        elif model is Brain:
            m.filter.return_value.first.return_value = mock_brain
        return m
    return query_side_effect


@pytest.mark.asyncio
async def test_generate_ai_foundation_endpoint_returns_suggestion():
    # Regression test for the missing generate-ai-foundation endpoint (404 Not Found on
    # every call - the route never existed) and for the follow-up finding that brain-api
    # cannot call an AI provider directly (it never receives the real provider API key,
    # only agent-worker does - see docker-compose.yml). The real implementation routes
    # through the existing chat session/message/NOTIFY pipeline and polls for the reply;
    # this test mocks that poll (_wait_for_reply) to isolate prompt/response wiring.
    db = MagicMock()
    ws_id = generate_snowflake_id()
    member = mock_member()
    canvas_id = generate_snowflake_id()

    mock_canvas = MagicMock(spec=StrategyCanvas, id=canvas_id, description="Nen tang dinh danh")
    mock_canvas.name = "MIVA Corp"
    mock_brain = MagicMock(spec=Brain, id=generate_snowflake_id())
    db.query.side_effect = _mock_canvas_and_brain_query(mock_canvas, mock_brain)

    ai_payload = {
        "vision": "V" * 25,
        "mission": "M" * 25,
        "values": [
            {"slot_no": 1, "title": "Minh bach", "description": "Ro rang", "decision_rule": "Khong giau"},
            {"slot_no": 2, "title": "Toc do", "description": "Nhanh", "decision_rule": "Uu tien tuan nay"},
            {"slot_no": 3, "title": "Ky luat", "description": "Giu cam ket", "decision_rule": "Khong nhan them"},
        ],
    }
    fake_reply = MagicMock(status="delivered", content=json.dumps(ai_payload))

    with patch(
        "workforce.chat.worker_prompt._wait_for_reply",
        new_callable=AsyncMock,
        return_value=fake_reply,
    ):
        result = await generate_ai_foundation(canvas_id, ws_id, member, db)

    assert result["foundation"]["vision"] == ai_payload["vision"]
    assert result["foundation"]["mission"] == ai_payload["mission"]
    assert len(result["foundation"]["values"]) == 3
    assert result["foundation"]["values"][0]["title"] == "Minh bach"


@pytest.mark.asyncio
async def test_generate_ai_foundation_raises_clear_error_when_worker_reports_failure():
    # Regression guard for the anti-pattern found in generate_ai_analysis (PESTEL/SWOT/
    # TOWS): silently falling back to fake canned data when the AI call fails. A failed
    # worker job here must surface as an error so the user knows to fill the form
    # manually, not return fabricated content disguised as an AI suggestion.
    db = MagicMock()
    ws_id = generate_snowflake_id()
    member = mock_member()
    canvas_id = generate_snowflake_id()

    mock_canvas = MagicMock(spec=StrategyCanvas, id=canvas_id, description=None)
    mock_canvas.name = "MIVA Corp"
    mock_brain = MagicMock(spec=Brain, id=generate_snowflake_id())
    db.query.side_effect = _mock_canvas_and_brain_query(mock_canvas, mock_brain)

    fake_reply = MagicMock(status="error", content="")

    with patch(
        "workforce.chat.worker_prompt._wait_for_reply",
        new_callable=AsyncMock,
        return_value=fake_reply,
    ):
        with pytest.raises(HTTPException) as exc:
            await generate_ai_foundation(canvas_id, ws_id, member, db)

    # 502: provider/worker trả lỗi là lỗi upstream. 503 chỉ dành riêng cho trường hợp
    # worker chưa có khoá - hai thứ này người vận hành xử lý khác nhau.
    assert exc.value.status_code == 502
    assert "hãy nhập Vision/Mission/Core Values thủ công" in exc.value.detail


@pytest.mark.asyncio
async def test_generate_ai_foundation_raises_timeout_when_worker_never_replies():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    member = mock_member()
    canvas_id = generate_snowflake_id()

    mock_canvas = MagicMock(spec=StrategyCanvas, id=canvas_id, description=None)
    mock_canvas.name = "MIVA Corp"
    mock_brain = MagicMock(spec=Brain, id=generate_snowflake_id())
    db.query.side_effect = _mock_canvas_and_brain_query(mock_canvas, mock_brain)

    with patch(
        "workforce.chat.worker_prompt._wait_for_reply",
        new_callable=AsyncMock,
        return_value=None,
    ):
        with pytest.raises(HTTPException) as exc:
            await generate_ai_foundation(canvas_id, ws_id, member, db)

    assert exc.value.status_code == 504


def test_foundation_schemas_accept_frontend_field_names():
    # Regression test: RevisionCreate/ApproveRevisionBody/RequestChangesBody/FoundationSave
    # used field names (title/notes, comments, feedback, vision_statement/mission_statement/
    # core_values) that matched neither the Flutter client (strategy_service.dart) nor
    # StrategyCanvasService's actual parameter names (base_revision_id, note, reason,
    # vision/mission/values) - every one of these requests failed with a 422 or TypeError.
    rev = RevisionCreate(**{"base_revision_id": "123"})
    assert rev.base_revision_id == "123"

    approve = ApproveRevisionBody(**{"note": "looks good"})
    assert approve.note == "looks good"

    changes = RequestChangesBody(**{"reason": "needs more detail"})
    assert changes.reason == "needs more detail"

    foundation = FoundationSave(**{
        "vision": "V" * 25,
        "mission": "M" * 25,
        "values": [
            {"slot_no": 1, "title": "Minh bạch", "description": "Rõ ràng", "decision_rule": "Không giấu số liệu"},
            {"slot_no": 2, "title": "Tốc độ", "description": "Nhanh", "decision_rule": "Ưu tiên tuần này"},
            {"slot_no": 3, "title": "Kỷ luật", "description": "Giữ cam kết", "decision_rule": "Không nhận thêm việc"},
        ],
    })
    assert foundation.vision == "V" * 25
    assert foundation.values[0].slot_no == 1
    assert foundation.values[0].decision_rule == "Không giấu số liệu"


def test_create_execution_plan_and_commitment():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    member = mock_member()
    
    # 12-week cycle
    db.query.return_value.filter.return_value.first.return_value = None
    cycle = create_twelve_week_cycle(ws_id, TwelveWeekCycleCreate(theme="Product Market Fit"), member, db)
    assert cycle["theme"] == "Product Market Fit"

    # Weekly plan
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = MagicMock(id=generate_snowflake_id())
    plan = create_weekly_plan(ws_id, WeeklyPlanCreate(week_no=1, focus="Core API integration"), member, db)
    assert plan["week_no"] == 1
    assert plan["focus"] == "Core API integration"

    # Weekly commitment
    db.query.return_value.filter.return_value.first.return_value = MagicMock(id=generate_snowflake_id())
    comm = create_weekly_commitment(ws_id, WeeklyCommitmentCreate(weekly_plan_id=generate_snowflake_id(), title="Ship Auth Flow", planned_effort="high"), member, db)
    assert comm["title"] == "Ship Auth Flow"
    assert comm["planned_effort"] == "high"




def test_create_project():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    member = mock_member()
    
    db.query.return_value.filter.return_value.first.return_value = None
    proj = create_project(ws_id, ProjectCreate(title="Javis Core Engine", phase="Phase 1", status="On Track"), member, db)
    assert proj["title"] == "Javis Core Engine"
    assert proj["status"] == "On Track"


def _mock_stage_context(stage_value: str):
    from founder_os.strategy.schemas.stage_schemas import ProjectStageEnum
    from founder_os.strategy.services.management_policy_engine import ManagementPolicyEngine
    from founder_os.strategy.services.stage_resolver_service import StageContextResponse

    stage_enum = ProjectStageEnum(stage_value)
    return StageContextResponse(
        workspace_id=1,
        company_stage="S5_OPERATE_GROWTH",
        company_vision=None,
        company_mission=None,
        company_values=[],
        project_id=None,
        project_title=None,
        project_type=None,
        project_stage=stage_enum,
        stage_started_at=None,
        stage_goal=None,
        critical_constraints=[],
        exit_criteria={},
        stage_metadata={},
        policy=ManagementPolicyEngine.get_policy(stage_enum),
    )


def test_generate_ai_okrs():
    from founder_os.strategy.okrs_router import generate_ai_okrs, OkrAiGenerateRequest
    db = MagicMock()
    ws_id = generate_snowflake_id()
    member = mock_member()

    db.query.return_value.filter.return_value.first.return_value = None
    req = OkrAiGenerateRequest(tows_id=None, objectives_count=3)
    with patch(
        "founder_os.strategy.okrs_router.StageResolverService.resolve_context",
        return_value=_mock_stage_context("S1_PROBLEM_VALIDATION"),
    ):
        res = generate_ai_okrs(ws_id, req, member, db)
    assert "objectives" in res
    assert len(res["objectives"]) == 3


def test_generate_ai_okrs_is_stage_aware():
    """P2.2: OKR sinh ra phải đổi theo Project Stage thay vì luôn dùng 3 template cứng."""
    from founder_os.strategy.okrs_router import generate_ai_okrs, OkrAiGenerateRequest

    db = MagicMock()
    ws_id = generate_snowflake_id()
    member = mock_member()
    db.query.return_value.filter.return_value.first.return_value = None

    with patch(
        "founder_os.strategy.okrs_router.StageResolverService.resolve_context",
        return_value=_mock_stage_context("S1_PROBLEM_VALIDATION"),
    ):
        s1_res = generate_ai_okrs(ws_id, OkrAiGenerateRequest(objectives_count=1), member, db)
    s1_titles = " ".join(o["title"] for o in s1_res["objectives"])
    assert "nỗi đau" in s1_titles or "phỏng vấn" in s1_titles.lower() or "Learning" in s1_titles

    with patch(
        "founder_os.strategy.okrs_router.StageResolverService.resolve_context",
        return_value=_mock_stage_context("S5_OPERATE_GROWTH"),
    ):
        s5_res = generate_ai_okrs(ws_id, OkrAiGenerateRequest(objectives_count=1), member, db)
    s5_titles = " ".join(o["title"] for o in s5_res["objectives"])
    assert "doanh thu" in s5_titles or "retention" in s5_titles.lower() or "Operating" in s5_titles

    assert s1_titles != s5_titles


def test_classify_and_methodology_endpoints():
    from founder_os.strategy.router import (
        classify_project_endpoint,
        route_methodology_endpoint,
        get_methodology_plan_endpoint,
        export_analysis_prompt_endpoint,
        import_analysis_result_endpoint,
        AnalysisImportRequest,
    )
    db = MagicMock()
    ws_id = generate_snowflake_id()
    proj_id = generate_snowflake_id()
    member = mock_member()

    proj = Project(
        id=proj_id,
        workspace_id=ws_id,
        brain_id=generate_snowflake_id(),
        title="Dự án AI Agent Platform",
        phase="Phase 1",
        status="active",
    )

    from platform_core.core.models import FeatureFlag

    def query_mock(model):
        m = MagicMock()
        if model == Project:
            m.filter.return_value.first.return_value = proj
        elif model == FeatureFlag:
            flag = FeatureFlag(key="project_classifier_v12", enabled=True)
            m.filter.return_value.first.return_value = flag


        else:
            m.filter.return_value.first.return_value = None
            m.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        return m


    db.query.side_effect = query_mock

    # 1. Classify
    cls_res = classify_project_endpoint(proj_id, ws_id, None, member, db)
    assert "project_type" in cls_res
    assert "recommended_methodologies" in cls_res

    # 2. Methodology
    method_res = route_methodology_endpoint(proj_id, ws_id, None, member, db)
    assert "selected_methodologies" in method_res
    assert method_res["status"] == "active"

    # 3. Export
    exp_res = export_analysis_prompt_endpoint(ws_id, None, member, db)
    assert "ChatGPT Terra" in exp_res["prompt_text"]

    # 4. Import
    import_req = AnalysisImportRequest(
        raw_input='{"schema_version": "1.0", "pestel": [{"factor": "Tech", "statement": "AI gen", "impact": "high", "horizon": "short", "confidence": "high", "evidence_status": "verified"}], "swot": [], "tows": [], "strategic_options": [], "recommended_goals": []}',
        project_id=proj_id,
    )
    imp_res = import_analysis_result_endpoint(ws_id, import_req, member, db)
    assert imp_res["status"] == "success"
    assert imp_res["pestel_count"] == 1


def test_stage_gate_governance_endpoints():
    from founder_os.strategy.execution_router import (
        generate_standard_cycle_stages,
        create_milestone,
        MilestoneCreate,
        record_gate_decision,
        GateDecisionCreate,
        upsert_cycle_contract,
        CycleContractUpsert,
        update_weekly_mission,
        WeeklyMissionUpdate,
    )
    db = MagicMock()
    ws_id = generate_snowflake_id()
    cycle_id = generate_snowflake_id()
    proj_id = generate_snowflake_id()
    plan_id = generate_snowflake_id()
    member = mock_member()

    cycle = TwelveWeekCycle(id=cycle_id, workspace_id=ws_id, theme="Q3 Target")
    proj = Project(id=proj_id, workspace_id=ws_id, title="App V12")
    plan = WeeklyPlan(id=plan_id, workspace_id=ws_id, cycle_id=cycle_id, week_no=1, focus="Week 1 Launch")

    from platform_core.core.models import FeatureFlag

    def query_mock(model):
        m = MagicMock()
        if model == TwelveWeekCycle:
            m.filter.return_value.first.return_value = cycle
        elif model == Project:
            m.filter.return_value.first.return_value = proj
        elif model == WeeklyPlan:
            m.filter.return_value.first.return_value = plan
        elif model == FeatureFlag:
            m.filter.return_value.first.return_value = FeatureFlag(key="cycle_13week_v12", enabled=True)
        else:
            m.filter.return_value.first.return_value = None
            m.filter.return_value.all.return_value = []
        return m


    db.query.side_effect = query_mock

    # 1. Generate Stages
    stages_res = generate_standard_cycle_stages(cycle_id, ws_id, member, db)
    assert len(stages_res["stages"]) == 5

    # 2. Create Milestone
    ms_data = MilestoneCreate(name="Architecture Signoff", cycle_id=cycle_id, due_week=3)
    ms_res = create_milestone(ws_id, ms_data, member, db)
    assert ms_res["name"] == "Architecture Signoff"

    # 3. Gate Decision
    gate_data = GateDecisionCreate(project_id=proj_id, decision="GO", rationale="Approved by Founder")
    gate_res = record_gate_decision(ws_id, gate_data, member, db)
    assert gate_res["decision"] == "GO"

    # 4. Upsert Contract
    contract_data = CycleContractUpsert(success_definition="Launch 3 features", founder_capacity_per_week=40.0)
    contract_res = upsert_cycle_contract(cycle_id, ws_id, contract_data, member, db)
    assert contract_res["success_definition"] == "Launch 3 features"

    # 5. Weekly Mission
    mission_data = WeeklyMissionUpdate(mission="Complete Sprint 3 implementation", outcome_score=1.0)
    mission_res = update_weekly_mission(plan_id, ws_id, mission_data, member, db)
    assert mission_res["mission"] == "Complete Sprint 3 implementation"


def test_planning_compiler_endpoints():
    from founder_os.strategy.execution_router import (
        compile_twelve_week_cycle,
        compile_weekly_plan,
        get_cycle_compilation_status,
    )
    db = MagicMock()
    ws_id = generate_snowflake_id()
    cycle_id = generate_snowflake_id()
    plan_id = generate_snowflake_id()
    member = mock_member()

    cycle = TwelveWeekCycle(id=cycle_id, workspace_id=ws_id, theme="Active Cycle", status="active")
    plan = WeeklyPlan(id=plan_id, workspace_id=ws_id, cycle_id=cycle_id, week_no=1, focus="Week 1 MVP")
    c1 = WeeklyCommitment(id=generate_snowflake_id(), workspace_id=ws_id, weekly_plan_id=plan_id, title="Commitment 1")

    def query_mock(model):
        m = MagicMock()
        if model == TwelveWeekCycle:
            m.filter.return_value.first.return_value = cycle
        elif model == WeeklyPlan:
            m.filter.return_value.all.return_value = [plan]
            m.filter.return_value.first.return_value = plan
        elif model == WeeklyCommitment:
            m.filter.return_value.all.return_value = [c1]
        else:
            m.filter.return_value.first.return_value = None
            m.filter.return_value.all.return_value = []
            m.filter.return_value.count.return_value = 0
        return m

    db.query.side_effect = query_mock

    # 1. Compile Cycle
    compile_res = compile_twelve_week_cycle(cycle_id, ws_id, member, db)
    assert compile_res["status"] == "compiled"
    assert compile_res["tasks_created"] == 1

    # 2. Compile Weekly Plan
    plan_compile_res = compile_weekly_plan(plan_id, ws_id, member, db)
    assert plan_compile_res["status"] == "compiled"

    # 3. Status
    status_res = get_cycle_compilation_status(cycle_id, ws_id, member, db)
    assert status_res["is_active"] is True


def test_weekly_review_and_week13_endpoints():
    from founder_os.strategy.execution_router import (
        create_or_update_weekly_review,
        WeeklyReviewCreate,
        finalize_week13,
        Week13FinalizeRequest,
        get_week13_readiness,
    )
    db = MagicMock()
    ws_id = generate_snowflake_id()
    cycle_id = generate_snowflake_id()
    plan_id = generate_snowflake_id()
    member = mock_member()

    cycle = TwelveWeekCycle(id=cycle_id, workspace_id=ws_id, theme="Active Cycle", status="active")
    plan = WeeklyPlan(id=plan_id, workspace_id=ws_id, cycle_id=cycle_id, week_no=1, focus="Week 1 MVP")

    def query_mock(model):
        m = MagicMock()
        if model == TwelveWeekCycle:
            m.filter.return_value.first.return_value = cycle
        elif model == WeeklyPlan:
            m.filter.return_value.first.return_value = plan
            m.filter.return_value.all.return_value = [plan]
        else:
            m.filter.return_value.first.return_value = None
            m.filter.return_value.all.return_value = []
        return m

    db.query.side_effect = query_mock

    # 1. Create Weekly Review
    rev_data = WeeklyReviewCreate(
        weekly_plan_id=plan_id,
        execution_score=0.9,
        outcome_score=0.95,
        recommendation="CONTINUE",
    )
    rev_res = create_or_update_weekly_review(cycle_id, ws_id, rev_data, member, db)
    assert rev_res["execution_score"] == 0.9
    assert rev_res["recommendation"] == "CONTINUE"

    # 2. Finalize Week 13
    f_data = Week13FinalizeRequest(
        overall_execution_score=0.9,
        overall_outcome_score=0.9,
        okr_achievement_rate=0.88,
        celebration_title="V12 Release Party",
    )
    fin_res = finalize_week13(cycle_id, ws_id, f_data, member, db)
    assert fin_res["celebration"]["title"] == "V12 Release Party"

    # 3. Readiness
    readiness_res = get_week13_readiness(cycle_id, ws_id, member, db)
    assert readiness_res["week13_mandatory"] is True


def test_portfolio_endpoints():
    from founder_os.strategy.portfolio_router import (
        detect_portfolio_necessity,
        create_portfolio,
        PortfolioCreate,
        list_portfolios,
        add_project_to_portfolio,
        PortfolioProjectAdd,
    )
    from founder_os.strategy.models import Portfolio, PortfolioProject, Project
    from platform_core.core.models import FeatureFlag

    db = MagicMock()
    ws_id = generate_snowflake_id()
    port_id = generate_snowflake_id()
    proj_id = generate_snowflake_id()
    member = mock_member()

    p1 = Project(id=proj_id, workspace_id=ws_id, brain_id=generate_snowflake_id(), title="Main Platform", status="active")
    p2 = Project(id=generate_snowflake_id(), workspace_id=ws_id, brain_id=generate_snowflake_id(), title="AI Assistant", status="active")
    portfolio = Portfolio(id=port_id, workspace_id=ws_id, name="Core Portfolio", status="active")
    pp = PortfolioProject(id=generate_snowflake_id(), workspace_id=ws_id, portfolio_id=port_id, project_id=proj_id, strategic_priority="core")

    def query_mock(model):
        m = MagicMock()
        if model == Project:
            m.filter.return_value.all.return_value = [p1, p2]
            m.filter.return_value.first.return_value = p1
        elif model == Portfolio:
            m.filter.return_value.count.return_value = 1
            m.filter.return_value.first.return_value = portfolio
            m.filter.return_value.order_by.return_value.all.return_value = [portfolio]
        elif model == PortfolioProject:
            m.filter.return_value.first.return_value = None
            m.filter.return_value.count.return_value = 1
            m.filter.return_value.all.return_value = [pp]
        elif model == FeatureFlag:
            m.filter.return_value.first.return_value = FeatureFlag(key="portfolio_v12", enabled=True)
        else:
            m.filter.return_value.all.return_value = []
            m.filter.return_value.first.return_value = None
        return m

    db.query.side_effect = query_mock

    # 1. Detect
    detect_res = detect_portfolio_necessity(ws_id, member, db)
    assert detect_res["needs_portfolio"] is True

    # 2. Create Portfolio
    create_res = create_portfolio(ws_id, PortfolioCreate(name="Core Portfolio"), member, db)
    assert create_res["name"] == "Core Portfolio"

    # 3. List
    list_res = list_portfolios(ws_id, member, db)
    assert len(list_res["portfolios"]) == 1

    # 4. Add project
    add_res = add_project_to_portfolio(
        port_id,
        ws_id,
        PortfolioProjectAdd(project_id=proj_id, strategic_priority="core", capacity_allocation=50.0),
        member,
        db,
    )
    assert add_res["strategic_priority"] == "core"


def test_portfolio_advanced_endpoints():
    from founder_os.strategy.portfolio_router import (
        add_portfolio_swot_item,
        PortfolioSwotItemCreate,
        add_portfolio_synergy,
        PortfolioSynergyCreate,
        create_portfolio_option,
        PortfolioOptionCreate,
    )
    from founder_os.strategy.models import Portfolio, Project, SwotItem, PortfolioSynergy, PortfolioOption, ContextPack, StrategyAnalysis
    from platform_core.core.models import FeatureFlag

    db = MagicMock()
    ws_id = generate_snowflake_id()
    port_id = generate_snowflake_id()
    p1_id = generate_snowflake_id()
    p2_id = generate_snowflake_id()
    member = mock_member()

    portfolio = Portfolio(id=port_id, workspace_id=ws_id, name="Advanced Portfolio", status="active")
    p1 = Project(id=p1_id, workspace_id=ws_id, brain_id=generate_snowflake_id(), title="Project A", status="active")
    p2 = Project(id=p2_id, workspace_id=ws_id, brain_id=generate_snowflake_id(), title="Project B", status="active")

    def query_mock(model):
        m = MagicMock()
        if model == Portfolio:
            m.filter.return_value.first.return_value = portfolio
        elif model == Project:
            m.filter.return_value.first.return_value = p1
        elif model == ContextPack:
            m.filter.return_value.first.return_value = ContextPack(id=generate_snowflake_id(), workspace_id=ws_id, name="Pack")
        elif model == StrategyAnalysis:
            m.filter.return_value.first.return_value = StrategyAnalysis(id=generate_snowflake_id(), workspace_id=ws_id, kind="SWOT")
        elif model == FeatureFlag:
            m.filter.return_value.first.return_value = FeatureFlag(key="portfolio_swot_tows_v12", enabled=True)
        else:
            m.filter.return_value.first.return_value = None
            m.filter.return_value.all.return_value = []
        return m

    db.query.side_effect = query_mock

    # 1. Add SWOT
    swot_res = add_portfolio_swot_item(
        port_id, ws_id, PortfolioSwotItemCreate(category="STRENGTH", statement="High R&D Speed"), member, db
    )
    assert swot_res["category"] == "STRENGTH"

    # 2. Add Synergy
    syn_res = add_portfolio_synergy(
        port_id,
        ws_id,
        PortfolioSynergyCreate(source_project_id=p1_id, target_project_id=p2_id, description="Shared GPU Infrastructure"),
        member,
        db,
    )
    assert syn_res["synergy_type"] == "SHARED_CAPABILITY"

    # 3. Create Option
    opt_res = create_portfolio_option(
        port_id,
        ws_id,
        PortfolioOptionCreate(title="Expand to APAC", strategic_fit_score=0.95),
        member,
        db,
    )
    assert opt_res["title"] == "Expand to APAC"


def test_portfolio_cycle_endpoints():
    from founder_os.strategy.portfolio_router import (
        get_founder_profile,
        update_founder_profile,
        FounderProfileUpdate,
        create_portfolio_cycle,
        PortfolioCycleCreate,
        activate_portfolio_cycle,
    )
    from founder_os.strategy.models import FounderProfile, Portfolio, PortfolioCycle, PortfolioProject

    db = MagicMock()
    ws_id = generate_snowflake_id()
    port_id = generate_snowflake_id()
    cycle_id = generate_snowflake_id()
    member = mock_member()

    profile = FounderProfile(id=generate_snowflake_id(), workspace_id=ws_id, user_id=member.user_id, weekly_capacity_hours=40.0, max_active_strategic_projects=3)
    portfolio = Portfolio(id=port_id, workspace_id=ws_id, name="Cycle Portfolio")
    cycle = PortfolioCycle(id=cycle_id, workspace_id=ws_id, portfolio_id=port_id, title="12WY Q1", status="draft")

    def query_mock(model):
        m = MagicMock()
        if model == FounderProfile:
            m.filter.return_value.first.return_value = profile
        elif model == Portfolio:
            m.filter.return_value.first.return_value = portfolio
        elif model == PortfolioCycle:
            m.filter.return_value.first.return_value = cycle
        elif model == PortfolioProject:
            m.filter.return_value.count.return_value = 2  # 2 active <= WIP Limit (3)
        return m

    db.query.side_effect = query_mock

    # 1. Get & Update Founder Profile
    fp = get_founder_profile(ws_id, member, db)
    assert fp["max_active_strategic_projects"] == 3

    up_fp = update_founder_profile(ws_id, FounderProfileUpdate(max_active_strategic_projects=4), member, db)
    assert up_fp["max_active_strategic_projects"] == 4

    # 2. Create Cycle
    c_res = create_portfolio_cycle(port_id, ws_id, PortfolioCycleCreate(title="12WY Q1"), member, db)
    assert c_res["title"] == "12WY Q1"

    # 3. Activate Cycle
    act_res = activate_portfolio_cycle(cycle_id, ws_id, member, db)
    assert act_res["status"] == "active"








