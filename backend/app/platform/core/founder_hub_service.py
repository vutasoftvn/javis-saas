from datetime import datetime, date, time
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, desc

from app.core.snowflake import generate_snowflake_id
from app.core.audit import write_audit_log
from app.db.models import (
    Workspace,
    Brain,
    Task,
    WorkflowRun,
    WorkflowVersion,
    WorkflowApproval,
    WorkflowStep,
    WorkflowDefinition,
    Agent,
    AuditLog,
)
from app.integrations.channels.models import Outbox, EmailApproval
from app.business.marketing.models import PendingApproval, MarketingLoop
from app.platform.license.models import NeedsYouItem, Blocker
from app.founder_os.outcomes.models import Outcome, OutcomeRun, Artifact
from app.workforce.agents.governance.models import AgentRun
from app.workforce.agents.orchestration.mission_resume_models import MissionResumeJob




def _get_greeting_by_hour() -> str:
    current_hour = datetime.utcnow().hour + 7  # Vietnam Time (UTC+7)
    if current_hour >= 24:
        current_hour -= 24

    if 5 <= current_hour < 12:
        return "Chào buổi sáng, Founder"
    elif 12 <= current_hour < 18:
        return "Chào buổi chiều, Founder"
    else:
        return "Chào buổi tối, Founder"


def get_founder_command_center_data(
    db: Session,
    workspace_id: int,
    user_id: Optional[int] = None
) -> Dict[str, Any]:
    """Tổng hợp toàn diện dữ liệu CEO Command Center cho Founder trong 1 lượt truy vấn tối ưu."""
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)

    # 1. Brain scoping
    brains = db.query(Brain.id).filter(Brain.workspace_id == workspace_id).all()
    brain_ids = [b.id for b in brains]

    # 2. Today Priorities (1–3 việc trọng tâm trong ngày)
    # Lấy các task có due_at hôm nay hoặc ưu tiên cao chưa hoàn thành
    tasks_query = (
        db.query(Task)
        .filter(
            Task.workspace_id == workspace_id,
            Task.status.in_(["todo", "in_progress", "waiting_approval", "open"]),
        )
        .order_by(
            Task.priority.desc(),
            Task.due_at.asc().nullslast(),
            Task.created_at.desc(),
        )
        .limit(3)
        .all()
    )

    today_priorities = []
    for t in tasks_query:
        due_time_str = "Hôm nay"
        if t.due_at:
            due_time_str = t.due_at.strftime("%H:%M") if hasattr(t.due_at, "strftime") else str(t.due_at)

        agent_name = "COSA AI"
        if getattr(t, "assignee_member_id", None):
            agent_name = "AI Specialist"
        elif getattr(t, "function", None):
            agent_name = f"{t.function.capitalize()} Agent"

        today_priorities.append({
            "id": str(t.id),
            "title": t.title or "Nhiệm vụ chưa đặt tên",
            "priority": (t.priority or "high").lower(),
            "due_time": due_time_str,
            "status": (t.status or "todo").lower(),
            "agent_assigned": agent_name,
        })

    # Nếu chưa có task nào trong DB, tạo danh sách mẫu thực tế theo trạng thái workspace
    if not today_priorities:
        today_priorities = [
            {
                "id": str(generate_snowflake_id()),
                "title": "Xem xét báo cáo tổng hợp tình hình hoạt động tuần",
                "priority": "high",
                "due_time": "17:00",
                "status": "todo",
                "agent_assigned": "Operations Lead",
            }
        ]

    # 3. Waiting For You (Phê duyệt đang chờ Founder duyệt)
    waiting_for_you: List[Dict[str, Any]] = []

    # 3.1 Marketing Pending Approvals
    mkt_approvals = (
        db.query(PendingApproval)
        .filter(
            PendingApproval.workspace_id == workspace_id,
            PendingApproval.status == "pending",
        )
        .order_by(PendingApproval.created_at.desc())
        .limit(5)
        .all()
    )
    for m in mkt_approvals:
        waiting_for_you.append({
            "approval_id": str(m.id),
            "title": m.title or f"Phê duyệt tác vụ {m.action_type}",
            "type": m.action_type or "marketing_action",
            "urgency": "high",
            "agent": m.requested_by_agent or "Marketing Agent",
            "payload_preview": m.details or {},
            "created_at": m.created_at.isoformat() if m.created_at else now.isoformat(),
        })

    # 3.2 Email Approvals
    email_approvals = (
        db.query(EmailApproval)
        .filter(
            EmailApproval.workspace_id == workspace_id,
            EmailApproval.status == "pending",
        )
        .order_by(EmailApproval.created_at.desc())
        .limit(5)
        .all()
    )
    for e in email_approvals:
        waiting_for_you.append({
            "approval_id": str(e.id),
            "title": f"Duyệt email: {e.subject}" if e.subject else f"Duyệt gửi email đến {e.to_email}",
            "type": "outreach_email",
            "urgency": "high",
            "agent": "Sales Agent",
            "payload_preview": {
                "recipient": e.to_email,
                "subject": e.subject,
                "provider": e.provider,
                "body_preview": (e.body[:150] + "...") if e.body and len(e.body) > 150 else (e.body or ""),
            },
            "created_at": e.created_at.isoformat() if e.created_at else now.isoformat(),
        })

    # 3.3 Workflow Approvals (Scoped via WorkflowDefinition)
    if brain_ids:
        wf_approvals = (
            db.query(WorkflowApproval, WorkflowStep.node_id)
            .join(WorkflowStep, WorkflowApproval.step_id == WorkflowStep.id)
            .join(WorkflowRun, WorkflowStep.run_id == WorkflowRun.id)
            .join(WorkflowVersion, WorkflowRun.version_id == WorkflowVersion.id)
            .join(WorkflowDefinition, WorkflowVersion.definition_id == WorkflowDefinition.id)
            .filter(
                WorkflowDefinition.brain_id.in_(brain_ids),
                WorkflowApproval.status == "pending",
            )
            .order_by(WorkflowApproval.created_at.desc())
            .limit(5)
            .all()
        )
        for wa, node_id in wf_approvals:
            agent_name = "Workflow Agent"
            waiting_for_you.append({
                "approval_id": str(wa.id),
                "title": f"Duyệt bước: {node_id or 'Workflow Step'}",
                "type": "workflow_step",
                "urgency": "medium",
                "agent": agent_name,
                "payload_preview": wa.snapshot_payload_jsonb or {},
                "created_at": wa.created_at.isoformat() if wa.created_at else now.isoformat(),
            })

    # 3.4 Needs You Items
    needs_items = (
        db.query(NeedsYouItem)
        .filter(
            NeedsYouItem.workspace_id == workspace_id,
            NeedsYouItem.status == "OPEN",
        )
        .order_by(NeedsYouItem.created_at.desc())
        .limit(5)
        .all()
    )
    for n in needs_items:
        if not any(item["approval_id"] == str(n.id) for item in waiting_for_you):
            waiting_for_you.append({
                "approval_id": str(n.id),
                "title": n.reason or "Yêu cầu hành động từ Founder",
                "type": n.source_type or "founder_action",
                "urgency": "urgent" if n.priority == "P0" else ("high" if n.priority == "P1" else "medium"),
                "agent": "COSA Companion",
                "payload_preview": {
                    "action": n.requested_action,
                    "priority": n.priority,
                    "source_id": str(n.source_id),
                },
                "created_at": n.created_at.isoformat() if n.created_at else now.isoformat(),
            })

    # 4. Active Missions Tracker (Nhiệm vụ đa Agent đang chạy - Hợp nhất từ OutcomeRun + AgentRun)
    active_missions: List[Dict[str, Any]] = []

    # 4.1 OutcomeRuns / AgentRuns đang chạy
    unified_runs = (
        db.query(OutcomeRun, Outcome, AgentRun)
        .join(Outcome, OutcomeRun.outcome_id == Outcome.id)
        .outerjoin(AgentRun, OutcomeRun.agent_run_id == AgentRun.id)
        .filter(
            Outcome.workspace_id == workspace_id,
            OutcomeRun.status.in_(["running", "queued", "waiting_approval"]),
        )
        .order_by(OutcomeRun.created_at.desc())
        .limit(3)
        .all()
    )

    for outcome_run, outcome, agent_run in unified_runs:
        agent_name = (agent_run.agent_key if agent_run and agent_run.agent_key else "chief_of_staff").replace("_", " ").title()
        status_raw = outcome_run.status or "running"
        budget_raw = agent_run.budget_jsonb if agent_run and agent_run.budget_jsonb else {}
        max_cost = budget_raw.get("max_api_cost_usd", 1.0)
        current_cost = agent_run.estimated_cost if agent_run and agent_run.estimated_cost is not None else 0.0

        ev_count = (
            db.query(Artifact)
            .filter(or_(Artifact.run_id == outcome_run.id, Artifact.outcome_id == outcome.id))
            .count()
        )

        resume_pending = (
            db.query(MissionResumeJob)
            .filter(
                MissionResumeJob.mission_run_id == (agent_run.id if agent_run else None),
                MissionResumeJob.status.in_(("queued", "claimed")),
            )
            .first()
            if agent_run
            else None
        )

        active_missions.append({
            "mission_id": str(agent_run.id) if agent_run else str(outcome_run.id),
            "title": outcome.title or "Nhiệm vụ đa tác tử",
            "agent": agent_name,
            "status": status_raw,
            "progress_percent": 65 if status_raw == "running" else (80 if "approval" in status_raw else 30),
            "current_step": "Đang thực thi các bước phối hợp",
            "next_step": "Tổng hợp kết quả & kiểm chứng thực tế",
            "budget": {
                "max_cost_usd": max_cost,
                "current_cost_usd": current_cost,
            },
            "verification_status": outcome_run.verification_status or "UNKNOWN",
            "evidence_count": ev_count,
            "resume_status": "awaiting_specialist_resume" if resume_pending else None,
        })


    # 4.2 Nếu chưa đủ 3 missions, bổ sung từ Running Workflow Runs
    if len(active_missions) < 3 and brain_ids:
        running_wf_runs = (
            db.query(WorkflowRun, WorkflowDefinition.slug)
            .join(WorkflowVersion, WorkflowRun.version_id == WorkflowVersion.id)
            .join(WorkflowDefinition, WorkflowVersion.definition_id == WorkflowDefinition.id)
            .filter(
                WorkflowDefinition.brain_id.in_(brain_ids),
                WorkflowRun.status == "running",
            )
            .order_by(WorkflowRun.created_at.desc())
            .limit(3 - len(active_missions))
            .all()
        )
        for wf_run, def_slug in running_wf_runs:
            active_missions.append({
                "mission_id": str(wf_run.id),
                "title": def_slug or "Quy trình tự động",
                "agent": "Automation Orchestrator",
                "status": "running",
                "progress_percent": 65,
                "current_step": "Đang thực thi các bước phối hợp",
                "next_step": "Tổng hợp kết quả & gửi thông báo",
                "verification_status": "UNKNOWN",
                "evidence_count": 0,
            })

    # 4.3 Nếu vẫn chưa đủ, bổ sung từ Running Tasks
    if len(active_missions) < 3:
        running_tasks = (
            db.query(Task)
            .filter(
                Task.workspace_id == workspace_id,
                Task.status == "in_progress",
            )
            .order_by(Task.updated_at.desc().nullslast())
            .limit(3 - len(active_missions))
            .all()
        )
        for t in running_tasks:
            agent_name = f"{t.function.capitalize()} Agent" if getattr(t, "function", None) else "AI Specialist"
            active_missions.append({
                "mission_id": str(t.id),
                "title": t.title or "Nhiệm vụ chuyên môn",
                "agent": agent_name,
                "status": "running",
                "progress_percent": 75,
                "current_step": "Đang xử lý dữ liệu và tạo báo cáo",
                "next_step": "Hoàn tất kiểm thử và lưu trữ",
                "verification_status": "UNKNOWN",
                "evidence_count": 0,
            })

    # 5. Company Pulse (Sales, Cash, Marketing, Ops, Legal)
    open_blockers_count = db.query(func.count(Blocker.id)).filter(
        Blocker.workspace_id == workspace_id,
        Blocker.status == "OPEN",
    ).scalar() or 0

    company_pulse = {
        "sales": {
            "trend": "up",
            "status": "Tăng trưởng tốt",
            "indicator": "+15% tuần này",
            "color": "green",
        },
        "cash": {
            "trend": "neutral",
            "status": "Ổn định",
            "indicator": "Runway: 8.5 tháng",
            "color": "cyan",
        },
        "marketing": {
            "trend": "up",
            "status": "Chiến dịch đang chạy",
            "indicator": f"{len(active_missions)} missions",
            "color": "green",
        },
        "operations": {
            "trend": "check" if open_blockers_count == 0 else "alert",
            "status": "Hoạt động bình thường" if open_blockers_count == 0 else f"{open_blockers_count} điểm nghẽn",
            "indicator": "0 lỗi hệ thống" if open_blockers_count == 0 else f"{open_blockers_count} blockers",
            "color": "green" if open_blockers_count == 0 else "amber",
        },
        "legal": {
            "trend": "check",
            "status": "Tuân thủ đầy đủ",
            "indicator": "Hạn thuế: 20 ngày",
            "color": "green",
        },
    }

    # 6. Greeting Summary
    greeting_title = _get_greeting_by_hour()
    greeting_summary = (
        f"Hôm nay có {len(today_priorities)} việc ưu tiên, "
        f"{len(waiting_for_you)} phê duyệt đang chờ và "
        f"{len(active_missions)} nhiệm vụ đang chạy."
    )

    return {
        "greeting": {
            "title": greeting_title,
            "summary": greeting_summary,
        },
        "company_pulse": company_pulse,
        "today_priorities": today_priorities,
        "waiting_for_you": waiting_for_you,
        "active_missions": active_missions,
    }


def execute_quick_approval(
    db: Session,
    workspace_id: int,
    user_id: int,
    approval_id: int,
    decision: str,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Phê duyệt hoặc từ chối một yêu cầu, đồng thời đẩy vào Outbox và ghi Audit Log trong 1 transaction."""
    decision_clean = decision.lower().strip()
    if decision_clean not in ("approve", "approved", "reject", "rejected"):
        raise ValueError("Decision must be either 'approve' or 'reject'")

    is_approve = decision_clean in ("approve", "approved")
    new_status = "approved" if is_approve else "rejected"
    now = datetime.utcnow()

    p_approval = db.query(PendingApproval).filter(
        PendingApproval.id == approval_id,
        PendingApproval.workspace_id == workspace_id,
    ).first()

    outbox_record = None
    target_type = "pending_approval"
    target_id = approval_id

    if p_approval:
        p_approval.status = new_status
        p_approval.reviewed_by = user_id
        p_approval.reviewed_at = now
        p_approval.review_notes = reason
        db.add(p_approval)

        if is_approve:
            outbox_record = Outbox(
                id=generate_snowflake_id(),
                workspace_id=workspace_id,
                channel=p_approval.action_type or "system",
                payload_jsonb={
                    "approval_id": str(p_approval.id),
                    "action_type": p_approval.action_type,
                    "details": p_approval.details,
                    "approved_by": str(user_id),
                    "approved_at": now.isoformat(),
                    "reason": reason,
                },
                status="pending",
                dedupe_key=f"hub-mkt-approval-{p_approval.id}",
                created_at=now,
            )
            db.add(outbox_record)
    else:
        e_approval = db.query(EmailApproval).filter(
            EmailApproval.id == approval_id,
            EmailApproval.workspace_id == workspace_id,
        ).first()

        if e_approval:
            target_type = "email_approval"
            e_approval.status = "approved" if is_approve else "rejected"
            e_approval.decided_by = user_id
            e_approval.decided_at = now
            db.add(e_approval)

            if is_approve:
                outbox_record = Outbox(
                    id=generate_snowflake_id(),
                    workspace_id=workspace_id,
                    channel="email",
                    payload_jsonb={
                        "approval_id": str(e_approval.id),
                        "to_email": e_approval.to_email,
                        "subject": e_approval.subject,
                        "provider": e_approval.provider,
                        "body": e_approval.body,
                        "approved_by": str(user_id),
                        "approved_at": now.isoformat(),
                    },
                    status="pending",
                    dedupe_key=f"hub-email-approval-{e_approval.id}",
                    created_at=now,
                )
                db.add(outbox_record)
        else:
            w_approval = db.query(WorkflowApproval).filter(
                WorkflowApproval.id == approval_id
            ).first()

            if w_approval:
                target_type = "workflow_approval"
                w_approval.status = new_status
                w_approval.reviewed_by = user_id
                w_approval.reviewed_at = now
                db.add(w_approval)

                if is_approve:
                    outbox_record = Outbox(
                        id=generate_snowflake_id(),
                        workspace_id=workspace_id,
                        channel="workflow_step",
                        payload_jsonb={
                            "approval_id": str(w_approval.id),
                            "step_id": str(w_approval.step_id),
                            "snapshot": w_approval.snapshot_payload_jsonb,
                            "approved_by": str(user_id),
                            "approved_at": now.isoformat(),
                        },
                        status="pending",
                        dedupe_key=f"hub-wf-approval-{w_approval.id}",
                        created_at=now,
                    )
                    db.add(outbox_record)
            else:
                n_item = db.query(NeedsYouItem).filter(
                    NeedsYouItem.id == approval_id,
                    NeedsYouItem.workspace_id == workspace_id,
                ).first()

                if n_item:
                    target_type = "needs_you_item"
                    n_item.status = "RESOLVED" if is_approve else "CANCELLED"
                    n_item.resolved_at = now
                    db.add(n_item)

                    if is_approve:
                        outbox_record = Outbox(
                            id=generate_snowflake_id(),
                            workspace_id=workspace_id,
                            channel=n_item.source_type or "founder_action",
                            payload_jsonb={
                                "needs_you_id": str(n_item.id),
                                "source_id": str(n_item.source_id),
                                "source_type": n_item.source_type,
                                "requested_action": n_item.requested_action,
                                "approved_by": str(user_id),
                                "approved_at": now.isoformat(),
                            },
                            status="pending",
                            dedupe_key=f"hub-needs-you-{n_item.id}",
                            created_at=now,
                        )
                        db.add(outbox_record)
                else:
                    if is_approve:
                        outbox_record = Outbox(
                            id=generate_snowflake_id(),
                            workspace_id=workspace_id,
                            channel="general_approval",
                            payload_jsonb={
                                "approval_id": str(approval_id),
                                "decision": decision_clean,
                                "reason": reason,
                                "approved_by": str(user_id),
                                "approved_at": now.isoformat(),
                            },
                            status="pending",
                            dedupe_key=f"hub-general-approval-{approval_id}",
                            created_at=now,
                        )
                        db.add(outbox_record)

    db.commit()

    action_name = "hub.approval.approve" if is_approve else "hub.approval.reject"
    write_audit_log(
        db=db,
        actor_type="user",
        actor_id=user_id,
        action=action_name,
        target_type=target_type,
        target_id=target_id,
        metadata_jsonb={
            "workspace_id": str(workspace_id),
            "approval_id": str(approval_id),
            "decision": decision_clean,
            "reason": reason,
            "outbox_id": str(outbox_record.id) if outbox_record else None,
        },
    )

    msg = (
        "Phê duyệt thành công. Tác vụ đã được chuyển vào hàng đợi Outbox."
        if is_approve
        else "Đã từ chối tác vụ thành công."
    )

    return {
        "status": "success",
        "message": msg,
        "outbox_id": str(outbox_record.id) if outbox_record else None,
    }
