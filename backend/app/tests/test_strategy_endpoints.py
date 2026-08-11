import uuid
from unittest.mock import MagicMock
import pytest
from app.modules.strategy.okrs_router import (
    OkrCycleCreate, OkrObjectiveCreate, KeyResultCreate,
    create_okr_cycle, create_okr_objective, create_key_result,
    list_okr_objectives, list_key_results
)
from app.modules.strategy.execution_router import (
    TwelveWeekCycleCreate, WeeklyPlanCreate, WeeklyCommitmentCreate,
    create_twelve_week_cycle, create_weekly_plan, create_weekly_commitment,
    list_weekly_plans, list_weekly_commitments
)
from app.modules.strategy.router import (
    PestelItemCreate, SwotItemCreate, TowsOptionCreate, ProjectCreate,
    create_pestel_item, create_swot_item, create_tows_option, create_project
)
from app.db.models import WorkspaceMember, OkrObjective, KeyResult, WeeklyPlan, WeeklyCommitment, PestelItem, SwotItem, TowsOption, Project, TwelveWeekCycle



def mock_member():
    m = MagicMock(spec=WorkspaceMember)
    m.user_id = uuid.uuid4()
    m.workspace_id = uuid.uuid4()
    m.role = "admin"
    return m


def test_create_and_list_okr():
    db = MagicMock()
    ws_id = uuid.uuid4()
    member = mock_member()
    
    # Mock brain
    db.query.return_value.filter.return_value.first.return_value = None
    
    cycle = create_okr_cycle(ws_id, OkrCycleCreate(name="Q3 OKR Cycle"), member, db)
    assert cycle["name"] == "Q3 OKR Cycle"
    assert db.add.called
    assert db.commit.called


def test_create_okr_objective_and_key_result():
    db = MagicMock()
    ws_id = uuid.uuid4()
    member = mock_member()
    
    # Objective
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = MagicMock(id=uuid.uuid4())
    obj_data = OkrObjectiveCreate(title="Increase MRR by 50%")
    obj = create_okr_objective(ws_id, obj_data, member, db)
    assert obj["title"] == "Increase MRR by 50%"

    # Key Result
    db.query.return_value.filter.return_value.first.return_value = MagicMock(id=uuid.uuid4())
    kr_data = KeyResultCreate(objective_id=uuid.uuid4(), baseline_value=10.0, current_value=25.0, target_value=50.0, unit="k$")
    kr = create_key_result(ws_id, kr_data, member, db)
    assert kr["target_value"] == 50.0
    assert kr["unit"] == "k$"


def test_create_execution_plan_and_commitment():
    db = MagicMock()
    ws_id = uuid.uuid4()
    member = mock_member()
    
    # 12-week cycle
    db.query.return_value.filter.return_value.first.return_value = None
    cycle = create_twelve_week_cycle(ws_id, TwelveWeekCycleCreate(theme="Product Market Fit"), member, db)
    assert cycle["theme"] == "Product Market Fit"

    # Weekly plan
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = MagicMock(id=uuid.uuid4())
    plan = create_weekly_plan(ws_id, WeeklyPlanCreate(week_no=1, focus="Core API integration"), member, db)
    assert plan["week_no"] == 1
    assert plan["focus"] == "Core API integration"

    # Weekly commitment
    db.query.return_value.filter.return_value.first.return_value = MagicMock(id=uuid.uuid4())
    comm = create_weekly_commitment(ws_id, WeeklyCommitmentCreate(weekly_plan_id=uuid.uuid4(), title="Ship Auth Flow", planned_effort="high"), member, db)
    assert comm["title"] == "Ship Auth Flow"
    assert comm["planned_effort"] == "high"


def test_create_analysis_items():
    db = MagicMock()
    ws_id = uuid.uuid4()
    member = mock_member()
    
    # PESTEL
    db.query.return_value.filter.return_value.first.return_value = None
    p_item = create_pestel_item(ws_id, PestelItemCreate(factor="Technological", statement="Adoption of LLM tooling", impact="Positive"), member, db)
    assert p_item["factor"] == "Technological"
    assert p_item["impact"] == "Positive"

    # SWOT
    s_item = create_swot_item(ws_id, SwotItemCreate(category="Strength", statement="Robust Architecture", impact="High"), member, db)
    assert s_item["category"] == "Strength"

    # TOWS
    t_item = create_tows_option(ws_id, TowsOptionCreate(quadrant="SO", title="Enterprise Growth", tradeoffs="Resource constraints"), member, db)
    assert t_item["quadrant"] == "SO"
    assert t_item["title"] == "Enterprise Growth"


def test_update_analysis_items():
    from app.modules.strategy.router import (
        PestelItemUpdate, SwotItemUpdate, TowsOptionUpdate,
        update_pestel_item, update_swot_item, update_tows_option
    )
    db = MagicMock()
    ws_id = uuid.uuid4()
    member = mock_member()
    item_id = uuid.uuid4()

    # Update PESTEL
    mock_pestel = MagicMock(id=item_id, workspace_id=ws_id, factor="Economic", statement="Old", impact="Low", horizon="short_term", confidence="medium", evidence_status="hypothesized")
    db.query.return_value.filter.return_value.first.return_value = mock_pestel
    res_p = update_pestel_item(item_id, ws_id, PestelItemUpdate(statement="New Statement", impact="High"), member, db)
    assert mock_pestel.statement == "New Statement"
    assert mock_pestel.impact == "High"

    # Update SWOT
    mock_swot = MagicMock(id=item_id, workspace_id=ws_id, category="Strength", statement="Old SWOT", impact="Low", likelihood="Medium", confidence="High", evidence_status="hypothesized")
    db.query.return_value.filter.return_value.first.return_value = mock_swot
    res_s = update_swot_item(item_id, ws_id, SwotItemUpdate(statement="Enhanced SWOT", impact="High"), member, db)
    assert mock_swot.statement == "Enhanced SWOT"
    assert mock_swot.impact == "High"

    # Update TOWS
    mock_tows = MagicMock(id=item_id, workspace_id=ws_id, quadrant="SO", title="Old TOWS", tradeoffs="None", expected_impact="Medium", confidence="High", status="draft")
    db.query.return_value.filter.return_value.first.return_value = mock_tows
    res_t = update_tows_option(item_id, ws_id, TowsOptionUpdate(title="Strategic Expansion", tradeoffs="CapEx increase"), member, db)
    assert mock_tows.title == "Strategic Expansion"
    assert mock_tows.tradeoffs == "CapEx increase"


def test_generate_ai_analysis_with_context():
    import asyncio
    from app.modules.strategy.router import generate_ai_analysis, AiAnalysisRequest
    db = MagicMock()
    ws_id = uuid.uuid4()
    member = mock_member()
    proj_id = uuid.uuid4()

    # Mock queries
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
    db.query.return_value.filter.return_value.all.return_value = []

    req = AiAnalysisRequest(project_id=proj_id, focus_area="AI automation", clear_existing=True)
    res = asyncio.run(generate_ai_analysis(ws_id, req, member, db))
    assert "pestel" in res
    assert "swot" in res
    assert "tows" in res
    assert len(res["pestel"]) >= 6
    assert len(res["swot"]) >= 4
    assert len(res["tows"]) >= 4


def test_create_project():
    db = MagicMock()
    ws_id = uuid.uuid4()
    member = mock_member()
    
    db.query.return_value.filter.return_value.first.return_value = None
    proj = create_project(ws_id, ProjectCreate(title="Javis Core Engine", phase="Phase 1", status="On Track"), member, db)
    assert proj["title"] == "Javis Core Engine"
    assert proj["status"] == "On Track"


def test_generate_ai_okrs():
    from app.modules.strategy.okrs_router import generate_ai_okrs, OkrAiGenerateRequest
    db = MagicMock()
    ws_id = uuid.uuid4()
    member = mock_member()

    db.query.return_value.filter.return_value.first.return_value = None
    req = OkrAiGenerateRequest(tows_id=None, objectives_count=3)
    res = generate_ai_okrs(ws_id, req, member, db)
    assert "objectives" in res
    assert len(res["objectives"]) == 3


def test_classify_and_methodology_endpoints():
    from app.modules.strategy.router import (
        classify_project_endpoint,
        route_methodology_endpoint,
        get_methodology_plan_endpoint,
        export_analysis_prompt_endpoint,
        import_analysis_result_endpoint,
        AnalysisImportRequest,
    )
    db = MagicMock()
    ws_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    member = mock_member()

    proj = Project(
        id=proj_id,
        workspace_id=ws_id,
        brain_id=uuid.uuid4(),
        title="Dự án AI Agent Platform",
        phase="Phase 1",
        status="active",
    )

    from app.modules.platform.models import FeatureFlag

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
    from app.modules.strategy.execution_router import (
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
    ws_id = uuid.uuid4()
    cycle_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    plan_id = uuid.uuid4()
    member = mock_member()

    cycle = TwelveWeekCycle(id=cycle_id, workspace_id=ws_id, theme="Q3 Target")
    proj = Project(id=proj_id, workspace_id=ws_id, title="App V12")
    plan = WeeklyPlan(id=plan_id, workspace_id=ws_id, cycle_id=cycle_id, week_no=1, focus="Week 1 Launch")

    from app.modules.platform.models import FeatureFlag

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
    from app.modules.strategy.execution_router import (
        compile_twelve_week_cycle,
        compile_weekly_plan,
        get_cycle_compilation_status,
    )
    db = MagicMock()
    ws_id = uuid.uuid4()
    cycle_id = uuid.uuid4()
    plan_id = uuid.uuid4()
    member = mock_member()

    cycle = TwelveWeekCycle(id=cycle_id, workspace_id=ws_id, theme="Active Cycle", status="active")
    plan = WeeklyPlan(id=plan_id, workspace_id=ws_id, cycle_id=cycle_id, week_no=1, focus="Week 1 MVP")
    c1 = WeeklyCommitment(id=uuid.uuid4(), workspace_id=ws_id, weekly_plan_id=plan_id, title="Commitment 1")

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
    from app.modules.strategy.execution_router import (
        create_or_update_weekly_review,
        WeeklyReviewCreate,
        finalize_week13,
        Week13FinalizeRequest,
        get_week13_readiness,
    )
    db = MagicMock()
    ws_id = uuid.uuid4()
    cycle_id = uuid.uuid4()
    plan_id = uuid.uuid4()
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
    from app.modules.strategy.portfolio_router import (
        detect_portfolio_necessity,
        create_portfolio,
        PortfolioCreate,
        list_portfolios,
        add_project_to_portfolio,
        PortfolioProjectAdd,
    )
    from app.modules.strategy.models import Portfolio, PortfolioProject, Project
    from app.modules.platform.models import FeatureFlag

    db = MagicMock()
    ws_id = uuid.uuid4()
    port_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    member = mock_member()

    p1 = Project(id=proj_id, workspace_id=ws_id, brain_id=uuid.uuid4(), title="Main Platform", status="active")
    p2 = Project(id=uuid.uuid4(), workspace_id=ws_id, brain_id=uuid.uuid4(), title="AI Assistant", status="active")
    portfolio = Portfolio(id=port_id, workspace_id=ws_id, name="Core Portfolio", status="active")
    pp = PortfolioProject(id=uuid.uuid4(), workspace_id=ws_id, portfolio_id=port_id, project_id=proj_id, strategic_priority="core")

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
    from app.modules.strategy.portfolio_router import (
        add_portfolio_swot_item,
        PortfolioSwotItemCreate,
        add_portfolio_synergy,
        PortfolioSynergyCreate,
        create_portfolio_option,
        PortfolioOptionCreate,
    )
    from app.modules.strategy.models import Portfolio, Project, SwotItem, PortfolioSynergy, PortfolioOption, ContextPack, StrategyAnalysis
    from app.modules.platform.models import FeatureFlag

    db = MagicMock()
    ws_id = uuid.uuid4()
    port_id = uuid.uuid4()
    p1_id = uuid.uuid4()
    p2_id = uuid.uuid4()
    member = mock_member()

    portfolio = Portfolio(id=port_id, workspace_id=ws_id, name="Advanced Portfolio", status="active")
    p1 = Project(id=p1_id, workspace_id=ws_id, brain_id=uuid.uuid4(), title="Project A", status="active")
    p2 = Project(id=p2_id, workspace_id=ws_id, brain_id=uuid.uuid4(), title="Project B", status="active")

    def query_mock(model):
        m = MagicMock()
        if model == Portfolio:
            m.filter.return_value.first.return_value = portfolio
        elif model == Project:
            m.filter.return_value.first.return_value = p1
        elif model == ContextPack:
            m.filter.return_value.first.return_value = ContextPack(id=uuid.uuid4(), workspace_id=ws_id, name="Pack")
        elif model == StrategyAnalysis:
            m.filter.return_value.first.return_value = StrategyAnalysis(id=uuid.uuid4(), workspace_id=ws_id, kind="SWOT")
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
    from app.modules.strategy.portfolio_router import (
        get_founder_profile,
        update_founder_profile,
        FounderProfileUpdate,
        create_portfolio_cycle,
        PortfolioCycleCreate,
        activate_portfolio_cycle,
    )
    from app.modules.strategy.models import FounderProfile, Portfolio, PortfolioCycle, PortfolioProject

    db = MagicMock()
    ws_id = uuid.uuid4()
    port_id = uuid.uuid4()
    cycle_id = uuid.uuid4()
    member = mock_member()

    profile = FounderProfile(id=uuid.uuid4(), workspace_id=ws_id, user_id=member.user_id, weekly_capacity_hours=40.0, max_active_strategic_projects=3)
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









