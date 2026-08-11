import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.snowflake import generate_snowflake_id
from app.core.tenancy import (

    get_cycle_scoped,
    get_stage_scoped,
    get_milestone_scoped,
    get_cycle_contract_scoped,
    get_gate_decision_scoped,
    get_project_scoped,
)
from app.modules.strategy.models import (
    TwelveWeekCycle,
    WeeklyPlan,
    WeeklyCommitment,
    CycleContract,
    CycleStage,
    Milestone,
    MilestoneEvidence,
    GateDecision,
    EvidenceItem,
    Project,
)

logger = logging.getLogger(__name__)

STANDARD_13WEEK_STAGES = [
    {
        "name": "Khám phá & Xác định Giả thuyết (Discovery)",
        "purpose": "Nghiên cứu thị trường, kiểm chứng giả thuyết ban đầu và định hình phạm vi",
        "start_week": 1,
        "end_week": 3,
        "order_no": 1,
        "expected_outcomes": {"artifacts": ["Market Research Doc", "Hypothesis Matrix"], "gates": ["Gate 1: Thẩm định"]},
    },
    {
        "name": "Xây dựng & Thử nghiệm MVP (Building)",
        "purpose": "Phát triển tính năng cốt lõi và kiểm thử vòng trong (Internal Beta)",
        "start_week": 4,
        "end_week": 7,
        "order_no": 2,
        "expected_outcomes": {"artifacts": ["Working MVP", "Beta User Feedback"], "gates": ["Gate 2: MVP Alpha"]},
    },
    {
        "name": "Xác thực & Tăng trưởng (Validation & Scale)",
        "purpose": "Mở rộng người dùng thử nghiệm, đo lường chỉ số kích hoạt và giữ chân",
        "start_week": 8,
        "end_week": 11,
        "order_no": 3,
        "expected_outcomes": {"artifacts": ["Growth Metrics Report", "Case Studies"], "gates": ["Gate 3: Sẵn sàng Scale"]},
    },
    {
        "name": "Đóng gói & Đánh giá Chu kỳ (Closing & Retrospective)",
        "purpose": "Tổng kết kết quả thực thi chu kỳ 12 tuần, đánh giá OKRs và lưu bài học kinh nghiệm",
        "start_week": 12,
        "end_week": 12,
        "order_no": 4,
        "expected_outcomes": {"artifacts": ["Cycle Retrospective Doc", "Final OKR Scorecard"], "gates": ["Gate 4: Đánh giá hoàn tất"]},
    },
    {
        "name": "Tuần 13 — Chuyển dịch Chiến lược (Week 13 Strategic Transition)",
        "purpose": "Tái cân bằng năng lực sáng lập, rà soát danh mục dự án và hoạch định chu kỳ 12 tuần kế tiếp",
        "start_week": 13,
        "end_week": 13,
        "order_no": 5,
        "expected_outcomes": {"artifacts": ["New Cycle Contract Draft", "Portfolio Rebalance Plan"], "gates": ["Gate 5: Ký hợp đồng chu kỳ mới"]},
    },
]


class CycleGovernanceService:
    def __init__(self, db: Session, workspace_id: int, user_id: int):
        self.db = db
        self.workspace_id = workspace_id
        self.user_id = user_id

    # ------------------------------------------------------------------
    # Cycle Contract
    # ------------------------------------------------------------------

    def get_cycle_contract(self, cycle_id: int) -> Optional[Dict[str, Any]]:
        get_cycle_scoped(self.db, cycle_id, self.workspace_id)
        contract = (
            self.db.query(CycleContract)
            .filter(
                CycleContract.cycle_id == cycle_id,
                CycleContract.workspace_id == self.workspace_id,
            )
            .first()
        )
        if not contract:
            return None
        return self._serialize_contract(contract)

    def upsert_cycle_contract(
        self,
        cycle_id: int,
        success_definition: str,
        founder_capacity_per_week: Optional[float] = 40.0,
        reserved_buffer_percent: Optional[float] = 20.0,
        ai_budget: Optional[float] = 0.0,
        operating_budget: Optional[float] = 0.0,
        goal_ids: Optional[List[str]] = None,
        kr_ids: Optional[List[str]] = None,
        risk_constraints: Optional[Dict[str, Any]] = None,
        status_val: str = "draft",
    ) -> Dict[str, Any]:
        cycle = get_cycle_scoped(self.db, cycle_id, self.workspace_id)

        contract = (
            self.db.query(CycleContract)
            .filter(
                CycleContract.cycle_id == cycle_id,
                CycleContract.workspace_id == self.workspace_id,
            )
            .first()
        )

        now = datetime.utcnow()
        if contract:
            contract.success_definition = success_definition
            contract.founder_capacity_per_week = founder_capacity_per_week
            contract.reserved_buffer_percent = reserved_buffer_percent
            contract.ai_budget = ai_budget
            contract.operating_budget = operating_budget
            if goal_ids is not None:
                contract.goal_ids = goal_ids
            if kr_ids is not None:
                contract.kr_ids = kr_ids
            if risk_constraints is not None:
                contract.risk_constraints = risk_constraints
            contract.status = status_val
            if status_val == "approved":
                contract.approved_by = self.user_id
                contract.approved_at = now
            contract.updated_at = now
        else:
            contract = CycleContract(
                id=generate_snowflake_id(),
                workspace_id=self.workspace_id,
                cycle_id=cycle_id,
                success_definition=success_definition,
                founder_capacity_per_week=founder_capacity_per_week,
                reserved_buffer_percent=reserved_buffer_percent,
                ai_budget=ai_budget,
                operating_budget=operating_budget,
                goal_ids=goal_ids or [],
                kr_ids=kr_ids or [],
                risk_constraints=risk_constraints or {},
                status=status_val,
                approved_by=self.user_id if status_val == "approved" else None,
                approved_at=now if status_val == "approved" else None,
                created_at=now,
                updated_at=now,
            )
            self.db.add(contract)

        # Sync cycle.cycle_contract_id
        cycle.cycle_contract_id = contract.id

        self.db.commit()
        self.db.refresh(contract)
        return self._serialize_contract(contract)

    # ------------------------------------------------------------------
    # Cycle Stages
    # ------------------------------------------------------------------

    def list_stages(self, cycle_id: int) -> List[Dict[str, Any]]:
        get_cycle_scoped(self.db, cycle_id, self.workspace_id)
        stages = (
            self.db.query(CycleStage)
            .filter(
                CycleStage.cycle_id == cycle_id,
                CycleStage.workspace_id == self.workspace_id,
            )
            .order_by(CycleStage.order_no.asc())
            .all()
        )
        return [self._serialize_stage(s) for s in stages]

    def create_stage(
        self,
        cycle_id: int,
        name: str,
        start_week: int,
        end_week: int,
        order_no: int,
        purpose: Optional[str] = None,
        expected_outcomes: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        get_cycle_scoped(self.db, cycle_id, self.workspace_id)
        stage = CycleStage(
            id=generate_snowflake_id(),
            workspace_id=self.workspace_id,
            cycle_id=cycle_id,
            name=name,
            purpose=purpose,
            start_week=start_week,
            end_week=end_week,
            order_no=order_no,
            expected_outcomes=expected_outcomes or {},
            status="pending",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.db.add(stage)
        self.db.commit()
        self.db.refresh(stage)
        return self._serialize_stage(stage)

    def generate_standard_stages(self, cycle_id: int) -> List[Dict[str, Any]]:
        get_cycle_scoped(self.db, cycle_id, self.workspace_id)
        # Delete existing stages if any
        self.db.query(CycleStage).filter(
            CycleStage.cycle_id == cycle_id,
            CycleStage.workspace_id == self.workspace_id,
        ).delete()

        created = []
        for s in STANDARD_13WEEK_STAGES:
            stage = CycleStage(
                id=generate_snowflake_id(),
                workspace_id=self.workspace_id,
                cycle_id=cycle_id,
                name=s["name"],
                purpose=s["purpose"],
                start_week=s["start_week"],
                end_week=s["end_week"],
                order_no=s["order_no"],
                expected_outcomes=s["expected_outcomes"],
                status="pending",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self.db.add(stage)
            created.append(stage)

        self.db.commit()
        return [self._serialize_stage(s) for s in created]

    def update_stage(
        self,
        stage_id: int,
        name: Optional[str] = None,
        purpose: Optional[str] = None,
        start_week: Optional[int] = None,
        end_week: Optional[int] = None,
        status_val: Optional[str] = None,
        expected_outcomes: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        stage = get_stage_scoped(self.db, stage_id, self.workspace_id)
        if name is not None:
            stage.name = name
        if purpose is not None:
            stage.purpose = purpose
        if start_week is not None:
            stage.start_week = start_week
        if end_week is not None:
            stage.end_week = end_week
        if status_val is not None:
            stage.status = status_val
        if expected_outcomes is not None:
            stage.expected_outcomes = expected_outcomes
        stage.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(stage)
        return self._serialize_stage(stage)

    def delete_stage(self, stage_id: int) -> None:
        stage = get_stage_scoped(self.db, stage_id, self.workspace_id)
        self.db.delete(stage)
        self.db.commit()

    # ------------------------------------------------------------------
    # Milestones & Milestone Evidence
    # ------------------------------------------------------------------

    def list_milestones(
        self,
        cycle_id: Optional[int] = None,
        stage_id: Optional[int] = None,
        project_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        query = self.db.query(Milestone).filter(Milestone.workspace_id == self.workspace_id)
        if cycle_id:
            query = query.filter(Milestone.cycle_id == cycle_id)
        if stage_id:
            query = query.filter(Milestone.stage_id == stage_id)
        if project_id:
            query = query.filter(Milestone.project_id == project_id)
        milestones = query.order_by(Milestone.due_week.asc(), Milestone.created_at.asc()).all()
        return [self._serialize_milestone(m) for m in milestones]

    def create_milestone(
        self,
        name: str,
        cycle_id: Optional[int] = None,
        stage_id: Optional[int] = None,
        project_id: Optional[int] = None,
        description: Optional[str] = None,
        due_week: Optional[int] = None,
        due_date: Optional[datetime] = None,
        required_artifacts: Optional[Dict[str, Any]] = None,
        required_metrics: Optional[Dict[str, Any]] = None,
        acceptance_criteria: Optional[str] = None,
    ) -> Dict[str, Any]:
        if cycle_id:
            get_cycle_scoped(self.db, cycle_id, self.workspace_id)
        if stage_id:
            get_stage_scoped(self.db, stage_id, self.workspace_id)
        if project_id:
            get_project_scoped(self.db, project_id, self.workspace_id)

        milestone = Milestone(
            id=generate_snowflake_id(),
            workspace_id=self.workspace_id,
            cycle_id=cycle_id,
            stage_id=stage_id,
            project_id=project_id,
            name=name,
            description=description,
            due_week=due_week,
            due_date=due_date,
            required_artifacts=required_artifacts or {},
            required_metrics=required_metrics or {},
            acceptance_criteria=acceptance_criteria,
            status="pending",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.db.add(milestone)
        self.db.commit()
        self.db.refresh(milestone)
        return self._serialize_milestone(milestone)

    def update_milestone(
        self,
        milestone_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        due_week: Optional[int] = None,
        due_date: Optional[datetime] = None,
        status_val: Optional[str] = None,
        required_artifacts: Optional[Dict[str, Any]] = None,
        required_metrics: Optional[Dict[str, Any]] = None,
        acceptance_criteria: Optional[str] = None,
    ) -> Dict[str, Any]:
        milestone = get_milestone_scoped(self.db, milestone_id, self.workspace_id)
        if name is not None:
            milestone.name = name
        if description is not None:
            milestone.description = description
        if due_week is not None:
            milestone.due_week = due_week
        if due_date is not None:
            milestone.due_date = due_date
        if status_val is not None:
            milestone.status = status_val
        if required_artifacts is not None:
            milestone.required_artifacts = required_artifacts
        if required_metrics is not None:
            milestone.required_metrics = required_metrics
        if acceptance_criteria is not None:
            milestone.acceptance_criteria = acceptance_criteria
        milestone.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(milestone)
        return self._serialize_milestone(milestone)

    def delete_milestone(self, milestone_id: int) -> None:
        milestone = get_milestone_scoped(self.db, milestone_id, self.workspace_id)
        self.db.delete(milestone)
        self.db.commit()

    def link_evidence(
        self,
        milestone_id: int,
        evidence_id: int,
        relevance_note: Optional[str] = None,
    ) -> Dict[str, Any]:
        get_milestone_scoped(self.db, milestone_id, self.workspace_id)
        # Verify evidence exists in workspace
        ev = (
            self.db.query(EvidenceItem)
            .filter(
                EvidenceItem.id == evidence_id,
                EvidenceItem.workspace_id == self.workspace_id,
            )
            .first()
        )
        if not ev:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EvidenceItem not found")

        link = (
            self.db.query(MilestoneEvidence)
            .filter(
                MilestoneEvidence.milestone_id == milestone_id,
                MilestoneEvidence.evidence_id == evidence_id,
                MilestoneEvidence.workspace_id == self.workspace_id,
            )
            .first()
        )
        if not link:
            link = MilestoneEvidence(
                id=generate_snowflake_id(),
                workspace_id=self.workspace_id,
                milestone_id=milestone_id,
                evidence_id=evidence_id,
                relevance_note=relevance_note,
                created_at=datetime.utcnow(),
            )
            self.db.add(link)
            self.db.commit()
            self.db.refresh(link)
        return {
            "id": str(link.id),
            "milestone_id": str(link.milestone_id),
            "evidence_id": str(link.evidence_id),
            "evidence_title": ev.title,
            "relevance_note": link.relevance_note,
        }

    def unlink_evidence(self, milestone_id: int, evidence_id: int) -> None:
        get_milestone_scoped(self.db, milestone_id, self.workspace_id)
        self.db.query(MilestoneEvidence).filter(
            MilestoneEvidence.milestone_id == milestone_id,
            MilestoneEvidence.evidence_id == evidence_id,
            MilestoneEvidence.workspace_id == self.workspace_id,
        ).delete()
        self.db.commit()

    # ------------------------------------------------------------------
    # Gate Decisions
    # ------------------------------------------------------------------

    def list_gate_decisions(
        self,
        project_id: Optional[int] = None,
        stage_id: Optional[int] = None,
        milestone_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        query = self.db.query(GateDecision).filter(GateDecision.workspace_id == self.workspace_id)
        if project_id:
            query = query.filter(GateDecision.project_id == project_id)
        if stage_id:
            query = query.filter(GateDecision.stage_id == stage_id)
        if milestone_id:
            query = query.filter(GateDecision.milestone_id == milestone_id)
        decisions = query.order_by(GateDecision.decided_at.desc()).all()
        return [self._serialize_gate_decision(d) for d in decisions]

    def record_gate_decision(
        self,
        project_id: int,
        decision: str,
        rationale: str,
        milestone_id: Optional[int] = None,
        stage_id: Optional[int] = None,
        evidence_summary: Optional[str] = None,
        evidence_refs: Optional[Dict[str, Any]] = None,
        next_step_instructions: Optional[str] = None,
    ) -> Dict[str, Any]:
        project = get_project_scoped(self.db, project_id, self.workspace_id)
        if milestone_id:
            get_milestone_scoped(self.db, milestone_id, self.workspace_id)
        if stage_id:
            get_stage_scoped(self.db, stage_id, self.workspace_id)

        valid_decisions = {"GO", "ITERATE", "HOLD", "STOP", "PIVOT"}
        if decision.upper() not in valid_decisions:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Quyết định không hợp lệ. Phải thuộc một trong: {valid_decisions}",
            )

        gate_decision = GateDecision(
            id=generate_snowflake_id(),
            workspace_id=self.workspace_id,
            project_id=project_id,
            milestone_id=milestone_id,
            stage_id=stage_id,
            decision=decision.upper(),
            rationale=rationale,
            evidence_summary=evidence_summary,
            evidence_refs=evidence_refs or {},
            next_step_instructions=next_step_instructions,
            decided_by=self.user_id,
            decided_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        self.db.add(gate_decision)

        # If decision is GO/ITERATE/HOLD/STOP/PIVOT, update project current_gate or status
        if decision.upper() == "STOP":
            project.status = "Stopped"
        elif decision.upper() == "HOLD":
            project.status = "On Hold"
        elif decision.upper() == "PIVOT":
            project.status = "Pivoting"

        self.db.commit()
        self.db.refresh(gate_decision)
        return self._serialize_gate_decision(gate_decision)

    # ------------------------------------------------------------------
    # Weekly Missions & Commitments
    # ------------------------------------------------------------------

    def update_weekly_mission(
        self,
        plan_id: int,
        mission: Optional[str] = None,
        success_criteria: Optional[Dict[str, Any]] = None,
        stage_id: Optional[int] = None,
        outcome_score: Optional[float] = None,
    ) -> Dict[str, Any]:
        plan = (
            self.db.query(WeeklyPlan)
            .filter(
                WeeklyPlan.id == plan_id,
                WeeklyPlan.workspace_id == self.workspace_id,
            )
            .first()
        )
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WeeklyPlan not found")

        if stage_id:
            get_stage_scoped(self.db, stage_id, self.workspace_id)
            plan.stage_id = stage_id
        if mission is not None:
            plan.mission = mission
        if success_criteria is not None:
            plan.success_criteria = success_criteria
        if outcome_score is not None:
            plan.outcome_score = outcome_score

        self.db.commit()
        self.db.refresh(plan)

        commitments = (
            self.db.query(WeeklyCommitment)
            .filter(WeeklyCommitment.weekly_plan_id == plan.id)
            .all()
        )

        return {
            "id": str(plan.id),
            "cycle_id": str(plan.cycle_id),
            "week_no": plan.week_no,
            "week_number": plan.week_no,
            "focus": plan.focus,
            "theme": plan.focus,
            "mission": plan.mission,
            "success_criteria": plan.success_criteria,
            "stage_id": str(plan.stage_id) if plan.stage_id else None,
            "outcome_score": plan.outcome_score,
            "execution_score": plan.execution_score,
            "commitments": [

                {
                    "id": str(c.id),
                    "title": c.title,
                    "status": c.status,
                    "planned_effort": c.planned_effort,
                    "commitment_owner_type": c.commitment_owner_type,
                    "execution_mode": c.execution_mode,
                }
                for c in commitments
            ],
        }

    # ------------------------------------------------------------------
    # Serializers
    # ------------------------------------------------------------------

    def _serialize_contract(self, c: CycleContract) -> Dict[str, Any]:
        return {
            "id": str(c.id),
            "cycle_id": str(c.cycle_id),
            "success_definition": c.success_definition,
            "goal_ids": c.goal_ids or [],
            "kr_ids": c.kr_ids or [],
            "founder_capacity_per_week": c.founder_capacity_per_week,
            "reserved_buffer_percent": c.reserved_buffer_percent,
            "ai_budget": c.ai_budget,
            "operating_budget": c.operating_budget,
            "risk_constraints": c.risk_constraints or {},
            "status": c.status,
            "approved_by": str(c.approved_by) if c.approved_by else None,
            "approved_at": c.approved_at.isoformat() if c.approved_at else None,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }

    def _serialize_stage(self, s: CycleStage) -> Dict[str, Any]:
        milestones = (
            self.db.query(Milestone)
            .filter(
                Milestone.stage_id == s.id,
                Milestone.workspace_id == self.workspace_id,
            )
            .all()
        )
        return {
            "id": str(s.id),
            "cycle_id": str(s.cycle_id),
            "name": s.name,
            "purpose": s.purpose,
            "start_week": s.start_week,
            "end_week": s.end_week,
            "order_no": s.order_no,
            "expected_outcomes": s.expected_outcomes or {},
            "status": s.status,
            "milestone_count": len(milestones),
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }

    def _serialize_milestone(self, m: Milestone) -> Dict[str, Any]:
        evidence_links = (
            self.db.query(MilestoneEvidence)
            .filter(
                MilestoneEvidence.milestone_id == m.id,
                MilestoneEvidence.workspace_id == self.workspace_id,
            )
            .all()
        )
        return {
            "id": str(m.id),
            "cycle_id": str(m.cycle_id) if m.cycle_id else None,
            "stage_id": str(m.stage_id) if m.stage_id else None,
            "project_id": str(m.project_id) if m.project_id else None,
            "name": m.name,
            "description": m.description,
            "due_week": m.due_week,
            "due_date": m.due_date.isoformat() if m.due_date else None,
            "required_artifacts": m.required_artifacts or {},
            "required_metrics": m.required_metrics or {},
            "acceptance_criteria": m.acceptance_criteria,
            "status": m.status,
            "evidence_count": len(evidence_links),
            "evidence_items": [
                {
                    "id": str(el.id),
                    "evidence_id": str(el.evidence_id),
                    "relevance_note": el.relevance_note,
                }
                for el in evidence_links
            ],
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }

    def _serialize_gate_decision(self, g: GateDecision) -> Dict[str, Any]:
        return {
            "id": str(g.id),
            "project_id": str(g.project_id),
            "milestone_id": str(g.milestone_id) if g.milestone_id else None,
            "stage_id": str(g.stage_id) if g.stage_id else None,
            "decision": g.decision,
            "rationale": g.rationale,
            "evidence_summary": g.evidence_summary,
            "evidence_refs": g.evidence_refs or {},
            "next_step_instructions": g.next_step_instructions,
            "decided_by": str(g.decided_by),
            "decided_at": g.decided_at.isoformat() if g.decided_at else None,
            "created_at": g.created_at.isoformat() if g.created_at else None,
        }
