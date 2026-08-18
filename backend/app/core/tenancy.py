from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import (
    Brain,
    ContextPack,
    EvidenceItem,
    StrategyCanvas,
    StrategyRevision,
    Task,
    WorkflowDefinition,
    WorkflowRun,
    WorkflowVersion,
    Project,
    MvpStage,
    WorkspaceTemplate,
    WorkspaceTemplateVersion,
    CapabilityDefinition,
    WorkspaceAgent,
    StageRevision,
    StageServiceAssessment,
    TwelveWeekCycle,
    CycleStage,
    Milestone,
    CycleContract,
    GateDecision,
    ProjectClassification,
    MethodologyPlan,
    Portfolio,
    PortfolioProject,
)



def resolve_workflow_run_workspace_id(db: Session, run: WorkflowRun) -> Optional[int]:
    """Workspace thực sự sở hữu một workflow_run.

    `workflow_runs` không có cột `workspace_id` trực tiếp (đúng schema §6.1 gốc) -
    phải suy ra qua task_id -> tasks.workspace_id, hoặc nếu run không gắn task thì
    qua version_id -> workflow_versions -> workflow_definitions -> brains.workspace_id.
    Trả None nếu không suy ra được (an toàn hơn là gán bừa một workspace).

    QUAN TRỌNG: dùng hàm này ở MỌI endpoint đọc/ghi theo run_id hoặc step_id, so sánh
    kết quả với workspace_id đã xác thực trước khi trả dữ liệu - thiếu bước này,
    workflows.py trước đó cho phép user bất kỳ đọc run và DUYỆT step (approve external
    action) của workspace khác chỉ bằng cách biết ID (đã tái hiện thực tế).
    """
    if run.task_id:
        task = db.query(Task).filter(Task.id == run.task_id).first()
        if task:
            return task.workspace_id

    version = db.query(WorkflowVersion).filter(WorkflowVersion.id == run.version_id).first()
    if version:
        definition = db.query(WorkflowDefinition).filter(
            WorkflowDefinition.id == version.definition_id
        ).first()
        if definition:
            brain = db.query(Brain).filter(Brain.id == definition.brain_id).first()
            if brain:
                return brain.workspace_id

    return None


# ==========================================
# Strategic Canvas 1-1-3 scoping helpers
# ==========================================
#
# Cùng một lớp lỗi cross-tenant đã lặp lại 4 lần (vault -> chat -> strategy -> workflows,
# xem docs/architecture/IMPLEMENTATION_ROADMAP.md): endpoint nhận id từ client mà không
# verify entity đó thuộc đúng workspace_id đã xác thực. Mọi lookup của StrategyCanvasService
# phải đi qua các hàm dưới đây thay vì tự viết filter riêng lẻ ở từng chỗ - không phân biệt
# "không tồn tại" với "thuộc workspace khác" (luôn trả 404 chung, tránh lộ thông tin).

def get_canvas_scoped(db: Session, canvas_id: int, workspace_id: int) -> StrategyCanvas:
    canvas = db.query(StrategyCanvas).filter(
        StrategyCanvas.id == canvas_id,
        StrategyCanvas.workspace_id == workspace_id,
    ).first()
    if not canvas:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Canvas not found")
    return canvas


def get_revision_scoped(db: Session, revision_id: int, workspace_id: int) -> StrategyRevision:
    # strategy_revisions không có workspace_id trực tiếp - phải join qua strategy_canvases,
    # đúng nguyên tắc của resolve_workflow_run_workspace_id ở trên.
    revision = db.query(StrategyRevision).join(
        StrategyCanvas, StrategyRevision.canvas_id == StrategyCanvas.id
    ).filter(
        StrategyRevision.id == revision_id,
        StrategyCanvas.workspace_id == workspace_id,
    ).first()
    if not revision:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Revision not found")
    return revision


def get_context_pack_scoped(db: Session, context_pack_id: int, workspace_id: int) -> ContextPack:
    pack = db.query(ContextPack).filter(
        ContextPack.id == context_pack_id,
        ContextPack.workspace_id == workspace_id,
    ).first()
    if not pack:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Context pack not found")
    return pack


def get_evidence_items_scoped(
    db: Session, evidence_ids: list[int], workspace_id: int
) -> list[EvidenceItem]:
    """Trả về evidence hợp lệ thuộc đúng workspace. Raise 404 nếu BẤT KỲ id nào không
    khớp - không âm thầm bỏ qua id sai workspace và link phần còn lại."""
    if not evidence_ids:
        return []
    unique_ids = set(evidence_ids)
    items = db.query(EvidenceItem).filter(
        EvidenceItem.id.in_(unique_ids),
        EvidenceItem.workspace_id == workspace_id,
    ).all()
    if len(items) != len(unique_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    return items


# ==========================================
# mCOSA V12 scoping helpers
# ==========================================

def get_project_scoped(db: Session, project_id: int, workspace_id: int) -> Project:
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.workspace_id == workspace_id,
    ).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def get_mvp_stage_scoped(db: Session, stage_id: int, workspace_id: int, brain_id: int) -> MvpStage:
    stage = db.query(MvpStage).filter(
        MvpStage.id == stage_id,
        MvpStage.workspace_id == workspace_id,
        MvpStage.brain_id == brain_id,
    ).first()
    if not stage:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MVP stage not found")
    return stage


def get_cycle_scoped(db: Session, cycle_id: int, workspace_id: int) -> TwelveWeekCycle:
    cycle = db.query(TwelveWeekCycle).filter(
        TwelveWeekCycle.id == cycle_id,
        TwelveWeekCycle.workspace_id == workspace_id,
    ).first()
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found")
    return cycle


def get_stage_scoped(db: Session, stage_id: int, workspace_id: int) -> CycleStage:
    stage = db.query(CycleStage).filter(
        CycleStage.id == stage_id,
        CycleStage.workspace_id == workspace_id,
    ).first()
    if not stage:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle stage not found")
    return stage


def get_milestone_scoped(db: Session, milestone_id: int, workspace_id: int) -> Milestone:
    milestone = db.query(Milestone).filter(
        Milestone.id == milestone_id,
        Milestone.workspace_id == workspace_id,
    ).first()
    if not milestone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found")
    return milestone


def get_cycle_contract_scoped(db: Session, contract_id: int, workspace_id: int) -> CycleContract:
    contract = db.query(CycleContract).filter(
        CycleContract.id == contract_id,
        CycleContract.workspace_id == workspace_id,
    ).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle contract not found")
    return contract


def get_gate_decision_scoped(db: Session, decision_id: int, workspace_id: int) -> GateDecision:
    decision = db.query(GateDecision).filter(
        GateDecision.id == decision_id,
        GateDecision.workspace_id == workspace_id,
    ).first()
    if not decision:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gate decision not found")
    return decision


def get_classification_scoped(db: Session, classification_id: int, workspace_id: int) -> ProjectClassification:
    classification = db.query(ProjectClassification).filter(
        ProjectClassification.id == classification_id,
        ProjectClassification.workspace_id == workspace_id,
    ).first()
    if not classification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project classification not found")
    return classification


def get_methodology_plan_scoped(db: Session, plan_id: int, workspace_id: int) -> MethodologyPlan:
    plan = db.query(MethodologyPlan).filter(
        MethodologyPlan.id == plan_id,
        MethodologyPlan.workspace_id == workspace_id,
    ).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Methodology plan not found")
    return plan


def get_portfolio_scoped(db: Session, portfolio_id: int, workspace_id: int) -> Portfolio:
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.workspace_id == workspace_id,
    ).first()
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    return portfolio


def get_portfolio_project_scoped(
    db: Session, portfolio_id: int, project_id: int, workspace_id: int
) -> PortfolioProject:
    pp = db.query(PortfolioProject).filter(
        PortfolioProject.portfolio_id == portfolio_id,
        PortfolioProject.project_id == project_id,
        PortfolioProject.workspace_id == workspace_id,
    ).first()
    if not pp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio project not found")
    return pp


# ==========================================
# Project stage orchestration scoping helpers
# ==========================================

def get_workspace_template_scoped(db: Session, template_id: int, workspace_id: int) -> WorkspaceTemplate:
    template = db.query(WorkspaceTemplate).filter(
        WorkspaceTemplate.id == template_id,
        WorkspaceTemplate.workspace_id == workspace_id,
    ).first()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace template not found")
    return template


def get_workspace_template_version_scoped(
    db: Session, version_id: int, workspace_id: int
) -> WorkspaceTemplateVersion:
    version = db.query(WorkspaceTemplateVersion).filter(
        WorkspaceTemplateVersion.id == version_id,
        WorkspaceTemplateVersion.workspace_id == workspace_id,
    ).first()
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace template version not found")
    return version


def get_capability_definition_scoped(
    db: Session, capability_id: int, workspace_id: int
) -> CapabilityDefinition:
    capability = db.query(CapabilityDefinition).filter(
        CapabilityDefinition.id == capability_id,
        CapabilityDefinition.workspace_id == workspace_id,
    ).first()
    if not capability:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capability not found")
    return capability


def get_workspace_agent_scoped(db: Session, agent_id: int, workspace_id: int) -> WorkspaceAgent:
    agent = db.query(WorkspaceAgent).filter(
        WorkspaceAgent.id == agent_id,
        WorkspaceAgent.workspace_id == workspace_id,
    ).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace agent not found")
    return agent


def get_stage_service_assessment_scoped(
    db: Session, assessment_id: int, workspace_id: int
) -> StageServiceAssessment:
    assessment = db.query(StageServiceAssessment).filter(
        StageServiceAssessment.id == assessment_id,
        StageServiceAssessment.workspace_id == workspace_id,
    ).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stage service assessment not found")
    return assessment


def get_execution_job_scoped(db: Session, job_id: int, workspace_id: int):
    """Retrieve execution job strictly scoped to workspace. Raises 404 on tenant mismatch."""
    from app.workforce.agents.execution.models import ExecutionJob

    job = db.query(ExecutionJob).filter(
        ExecutionJob.id == job_id,
        ExecutionJob.workspace_id == workspace_id,
    ).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution job not found")
    return job
