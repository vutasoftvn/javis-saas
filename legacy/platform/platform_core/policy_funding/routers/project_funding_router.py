from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from core.auth import get_current_workspace_member
from db.models import WorkspaceMember
from db.session import get_db
from founder_os.strategy.models import Project, TwelveWeekCycle, WeeklyCommitment
from founder_os.tasks.models import Task
from platform_core.policy_funding.models import (
    PolicyProgram,
    ProjectStageAssessment,
    TrlAssessment,
    FundingNeed,
    ProjectProgramMatch,
    MissingRequirement,
    FundingAward,
)
from platform_core.policy_funding.schemas import (
    FundingOverviewResponse,
    ProjectProgramMatchResponse,
    MissingRequirementResponse,
    ProjectStageAssessmentCreate,
    ProjectStageAssessmentResponse,
    TrlAssessmentCreate,
    TrlAssessmentResponse,
    Create12wyTaskRequest,
    DoubleFundingCheckRequest,
    DoubleFundingWarning,
)
from platform_core.policy_funding.services.matching_service import PolicyMatchingService

router = APIRouter()


def _guard(workspace_id: int, member: WorkspaceMember) -> None:
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")


@router.get("/projects/{project_id}/funding-overview", response_model=FundingOverviewResponse)
def get_project_funding_overview(
    project_id: int,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Trả về toàn diện thông tin nguồn lực, chính sách và cơ hội cho Project.
    """
    _guard(workspace_id, member)

    project = db.scalar(
        select(Project).where(
            Project.id == project_id,
            Project.workspace_id == workspace_id,
        )
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    stage_assessment = db.scalar(
        select(ProjectStageAssessment)
        .where(
            ProjectStageAssessment.project_id == project_id,
            ProjectStageAssessment.workspace_id == workspace_id,
        )
        .order_by(ProjectStageAssessment.created_at.desc())
    )

    trl_assessment = db.scalar(
        select(TrlAssessment)
        .where(
            TrlAssessment.project_id == project_id,
            TrlAssessment.workspace_id == workspace_id,
        )
        .order_by(TrlAssessment.created_at.desc())
    )

    # Lấy danh sách match
    matches = db.scalars(
        select(ProjectProgramMatch)
        .where(
            ProjectProgramMatch.project_id == project_id,
            ProjectProgramMatch.workspace_id == workspace_id,
        )
        .order_by(ProjectProgramMatch.match_score.desc())
    ).all()

    # Nếu chưa có match nào, tự động kích hoạt matching lần đầu
    if not matches:
        matches = PolicyMatchingService.run_full_matching_for_project(
            db=db,
            project_id=project_id,
            workspace_id=workspace_id,
            brain_id=member.workspace_id,
        )

    match_responses: List[ProjectProgramMatchResponse] = []
    for m in matches:
        prog = db.scalar(select(PolicyProgram).where(PolicyProgram.id == m.program_id))
        match_responses.append(
            ProjectProgramMatchResponse(
                id=m.id,
                id_str=str(m.id),
                project_id=m.project_id,
                program_id=m.program_id,
                program_name=prog.name if prog else "Unknown Program",
                program_status=prog.status if prog else "UNKNOWN",
                program_authority=prog.authority if prog else None,
                program_type=prog.program_type if prog else None,
                eligibility_status=m.eligibility_status,
                match_score=m.match_score,
                readiness_score=m.readiness_score,
                pipeline_stage=m.pipeline_stage,
                passed_rules_count=m.passed_rules_count,
                total_rules_count=m.total_rules_count,
                ai_summary=m.ai_summary,
                calculated_at=m.calculated_at,
            )
        )

    missing_reqs = db.scalars(
        select(MissingRequirement)
        .where(
            MissingRequirement.project_id == project_id,
            MissingRequirement.workspace_id == workspace_id,
            MissingRequirement.is_resolved == False,
        )
    ).all()

    missing_responses = [
        MissingRequirementResponse(
            id=r.id,
            id_str=str(r.id),
            project_id=r.project_id,
            program_id=r.program_id,
            category=r.category,
            title=r.title,
            description=r.description,
            is_resolved=r.is_resolved,
            linked_task_id=r.linked_task_id,
            created_at=r.created_at,
        )
        for r in missing_reqs
    ]

    active_awards_count = db.query(FundingAward).filter(
        FundingAward.project_id == project_id,
        FundingAward.workspace_id == workspace_id,
        FundingAward.status == "ACTIVE",
    ).count()

    readiness_avg = (
        sum(m.readiness_score for m in match_responses) / len(match_responses)
        if match_responses else 0.0
    )

    alerts: List[str] = []
    if not stage_assessment:
        alerts.append("Cần xác nhận phân loại doanh nghiệp và giai đoạn dự án.")
    if not trl_assessment:
        alerts.append("Cần cập nhật mức sẵn sàng công nghệ (TRL) cho dự án.")
    if missing_reqs:
        alerts.append(f"Có {len(missing_reqs)} minh chứng/yêu cầu cần bổ sung trước khi nộp hồ sơ.")

    return FundingOverviewResponse(
        project_id=project.id,
        project_id_str=str(project.id),
        project_title=project.title,
        company_type=stage_assessment.company_type if stage_assessment else "STARTUP",
        project_stage=stage_assessment.stage if stage_assessment else "MVP",
        trl_current=trl_assessment.trl_current if trl_assessment else 3,
        readiness_score_avg=round(readiness_avg, 1),
        top_matches=match_responses[:5],
        missing_requirements=missing_responses,
        active_awards_count=active_awards_count,
        urgent_alerts=alerts,
    )


@router.post("/projects/{project_id}/policy-match")
def trigger_policy_matching(
    project_id: int,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Kích hoạt chạy lại matching toàn bộ danh mục chính sách cho Project.
    """
    _guard(workspace_id, member)
    matches = PolicyMatchingService.run_full_matching_for_project(
        db=db,
        project_id=project_id,
        workspace_id=workspace_id,
        brain_id=member.workspace_id,
    )
    return {
        "status": "success",
        "matched_programs_count": len(matches),
        "message": "Matching hoàn tất thành công",
    }


@router.post("/projects/{project_id}/assess-stage", response_model=ProjectStageAssessmentResponse)
def assess_project_stage(
    project_id: int,
    payload: ProjectStageAssessmentCreate,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Cập nhật và xác nhận Company Type + Project Stage cho Project.
    """
    _guard(workspace_id, member)
    record = ProjectStageAssessment(
        workspace_id=workspace_id,
        project_id=project_id,
        company_type=payload.company_type,
        stage=payload.stage,
        is_founder_confirmed=payload.is_founder_confirmed,
        notes=payload.notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return ProjectStageAssessmentResponse(
        id=record.id,
        id_str=str(record.id),
        project_id=record.project_id,
        company_type=record.company_type,
        stage=record.stage,
        ai_suggested_type=record.ai_suggested_type,
        ai_suggested_stage=record.ai_suggested_stage,
        ai_confidence_score=record.ai_confidence_score,
        is_founder_confirmed=record.is_founder_confirmed,
        notes=record.notes,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.post("/projects/{project_id}/assess-trl", response_model=TrlAssessmentResponse)
def assess_project_trl(
    project_id: int,
    payload: TrlAssessmentCreate,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Cập nhật đánh giá mức độ sẵn sàng công nghệ (TRL 1-9) cho Project.
    """
    _guard(workspace_id, member)
    record = TrlAssessment(
        workspace_id=workspace_id,
        project_id=project_id,
        trl_current=payload.trl_current,
        trl_target=payload.trl_target,
        explanation=payload.explanation,
        evidence_artifact_id=payload.evidence_artifact_id,
        evidence_notes=payload.evidence_notes,
        assessed_by=member.user_id,
        verified_at=datetime.utcnow(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return TrlAssessmentResponse(
        id=record.id,
        id_str=str(record.id),
        project_id=record.project_id,
        trl_current=record.trl_current,
        trl_target=record.trl_target,
        explanation=record.explanation,
        evidence_artifact_id=record.evidence_artifact_id,
        evidence_notes=record.evidence_notes,
        assessed_by=record.assessed_by,
        verified_at=record.verified_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.post("/projects/{project_id}/create-12wy-task")
def create_12wy_task_from_missing_req(
    project_id: int,
    payload: Create12wyTaskRequest,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Chuyển một điều kiện còn thiếu thành nhiệm vụ / cam kết trong 12 Week Year.
    """
    _guard(workspace_id, member)
    req = db.scalar(
        select(MissingRequirement).where(
            MissingRequirement.id == payload.missing_requirement_id,
            MissingRequirement.workspace_id == workspace_id,
        )
    )
    if not req:
        raise HTTPException(status_code=404, detail="Missing requirement not found")

    title = payload.custom_title or f"[Hồ sơ Nguồn lực] {req.title}"

    # Tạo Task
    task = Task(
        workspace_id=workspace_id,
        title=title,
        description=req.description or f"Hoàn thiện minh chứng cho điều kiện: {req.title}",
        status="TODO",
    )
    db.add(task)
    db.flush()

    req.linked_task_id = task.id
    db.commit()

    return {
        "status": "success",
        "task_id": str(task.id),
        "task_title": task.title,
        "message": "Đã tạo nhiệm vụ thành công cho 12 Week Year",
    }


@router.post("/projects/{project_id}/check-double-funding", response_model=DoubleFundingWarning)
def check_project_double_funding(
    project_id: int,
    payload: DoubleFundingCheckRequest,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Kiểm tra xung đột chi phí / hạng mục giữa nhiều nguồn tài trợ (Double Funding Guard).
    """
    _guard(workspace_id, member)
    conflict, msg, award_ids, app_ids = PolicyMatchingService.check_double_funding(
        db=db,
        project_id=project_id,
        work_package=payload.work_package,
        cost_category=payload.cost_category,
        purpose=payload.purpose,
        period_start=payload.period_start,
        period_end=payload.period_end,
    )
    return DoubleFundingWarning(
        conflict_found=conflict,
        message=msg,
        conflicting_award_ids=award_ids,
        conflicting_application_ids=app_ids,
    )


class DispatchAlertRequest(BaseModel):
    title: str
    message: str
    channel: str = "IN_APP"
    destination: Optional[str] = None


@router.post("/projects/{project_id}/dispatch-alert")
def dispatch_project_policy_alert(
    project_id: int,
    payload: DispatchAlertRequest,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """
    Phát cảnh báo khẩn về nguồn lực/deadline qua đa kênh (Telegram, Zalo, Email, In-app).
    """
    _guard(workspace_id, member)
    from platform_core.policy_funding.services.automation_service import PolicyAutomationService
    entry = PolicyAutomationService.dispatch_critical_policy_alert(
        db=db,
        workspace_id=workspace_id,
        project_id=project_id,
        alert_title=payload.title,
        alert_message=payload.message,
        channel=payload.channel,
        target_destination=payload.destination,
    )
    return {
        "status": "success",
        "outbox_id": str(entry.id),
        "channel": entry.channel,
        "message": "Cảnh báo khẩn đã được đưa vào hàng đợi phát tin.",
    }
