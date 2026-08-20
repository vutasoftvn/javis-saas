from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import desc
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.founder_os.strategy.models import (
    Project,
    Hypothesis,
    Evidence,
    PestelSignal,
    SwotItem,
    TowsOption,
    BscGoal,
    StageTransitionAudit,
    PrematureScalingAlert,
    StrategicDecision,
)
from app.platform.auth.models import Workspace
from app.founder_os.strategy.schemas.stage_gate_schemas import (
    StageGateAuditResponse,
    PrematureScalingAlertResponse,
    AuditStatusEnum,
    AlertSeverityEnum,
)

STAGE_SUCCESSION: Dict[str, str] = {
    "S0_EXPLORE": "S1_PROBLEM_VALIDATION",
    "S1_PROBLEM_VALIDATION": "S2_SOLUTION_VALIDATION",
    "S2_SOLUTION_VALIDATION": "S3_BUSINESS_VALIDATION",
    "S3_BUSINESS_VALIDATION": "S4_GO_TO_MARKET",
    "S4_GO_TO_MARKET": "S5_OPERATE_GROWTH",
    "S5_OPERATE_GROWTH": "S6_SCALE_GOVERN",
}


class StageGateService:
    """Động cơ Thẩm Định Chuyển Giai Đoạn & Hàng Rào Phòng Vệ Anti-Premature Scaling."""

    @staticmethod
    def evaluate_stage_readiness(
        db: Session,
        workspace_id: int,
        project_id: int,
        target_stage: Optional[str] = None,
    ) -> StageTransitionAudit:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Không tìm thấy dự án.")

        from_stage = str(getattr(project, "project_stage", "S1_PROBLEM_VALIDATION")).upper()
        if not target_stage:
            target_stage = STAGE_SUCCESSION.get(from_stage, "S6_SCALE_GOVERN")

        # Thu thập dữ liệu chiến lược & bằng chứng
        hypos = db.query(Hypothesis).filter(Hypothesis.project_id == project_id).all()
        evidences = db.query(Evidence).filter(Evidence.project_id == project_id).all()
        pestels = db.query(PestelSignal).filter(PestelSignal.project_id == project_id).all()
        swots = db.query(SwotItem).filter(SwotItem.project_id == project_id).all()
        tows = db.query(TowsOption).filter(TowsOption.project_id == project_id).all()

        passed_criteria: List[Dict[str, Any]] = []
        missing_criteria: List[Dict[str, Any]] = []

        # --- Tiêu chí kiểm định theo từng cặp chuyển giai đoạn ---
        if from_stage == "S0_EXPLORE":
            # 1. Tín hiệu PESTEL vĩ mô
            if len(pestels) >= 2:
                passed_criteria.append({
                    "id": "S0_PESTEL_SIGNALS",
                    "title": "Tín hiệu vĩ mô PESTEL",
                    "description": f"Đã thu thập {len(pestels)} tín hiệu thị trường.",
                    "is_met": True,
                })
            else:
                missing_criteria.append({
                    "id": "S0_PESTEL_SIGNALS",
                    "title": "Tín hiệu vĩ mô PESTEL",
                    "description": f"Cần tối thiểu 2 tín hiệu vĩ mô (Hiện có: {len(pestels)}).",
                    "is_met": False,
                })

            # 2. Giả định phân khúc khách hàng
            has_cust_hypo = any(h.category in ("customer", "market") for h in hypos)
            if has_cust_hypo:
                passed_criteria.append({
                    "id": "S0_CUSTOMER_HYPO",
                    "title": "Giả định phân khúc khách hàng",
                    "description": "Đã xác định ít nhất 1 giả định phân khúc khách hàng mục tiêu.",
                    "is_met": True,
                })
            else:
                missing_criteria.append({
                    "id": "S0_CUSTOMER_HYPO",
                    "title": "Giả định phân khúc khách hàng",
                    "description": "Cần tạo ít nhất 1 giả định phân khúc khách hàng mục tiêu.",
                    "is_met": False,
                })

        elif from_stage == "S1_PROBLEM_VALIDATION":
            # 1. Giả định Nỗi đau có bằng chứng >= 0.5
            problem_hypos = [h for h in hypos if h.category in ("problem", "customer")]
            valid_problem_hypos = [h for h in problem_hypos if (h.evidence_score or 0.0) >= 0.5]

            if valid_problem_hypos:
                passed_criteria.append({
                    "id": "S1_PROBLEM_EVIDENCE",
                    "title": "Xác thực nỗi đau khách hàng (Problem Fit)",
                    "description": f"Có {len(valid_problem_hypos)} giả định nỗi đau đạt điểm bằng chứng >= 50%.",
                    "is_met": True,
                })
            else:
                missing_criteria.append({
                    "id": "S1_PROBLEM_EVIDENCE",
                    "title": "Xác thực nỗi đau khách hàng (Problem Fit)",
                    "description": "Cần ít nhất 1 giả định nỗi đau đạt điểm bằng chứng >= 50%.",
                    "is_met": False,
                })

            # 2. Bằng chứng thực tế cấp E2 (Observed Problem) trở lên
            e2_plus_evidences = [
                e for e in evidences
                if e.ladder_level in (
                    "E2_OBSERVED_PROBLEM", "E3_BEHAVIORAL_COMMITMENT",
                    "E4_ECONOMIC_COMMITMENT", "E5_REPEAT_BEHAVIOR", "E6_SCALABLE_EVIDENCE"
                )
            ]
            if len(e2_plus_evidences) >= 2:
                passed_criteria.append({
                    "id": "S1_E2_EVIDENCE_LADDER",
                    "title": "Thang đo Bằng chứng cấp E2+",
                    "description": f"Đã có {len(e2_plus_evidences)} bằng chứng từ quan sát thực tế (E2+) trở lên.",
                    "is_met": True,
                })
            else:
                missing_criteria.append({
                    "id": "S1_E2_EVIDENCE_LADDER",
                    "title": "Thang đo Bằng chứng cấp E2+",
                    "description": f"Cần tối thiểu 2 bằng chứng thực tế từ E2 trở lên (Hiện có: {len(e2_plus_evidences)}).",
                    "is_met": False,
                })

            # 3. Điểm mạnh / Yếu có bằng chứng minh chứng
            if any(s.category in ("STRENGTH", "WEAKNESS") and len(s.evidence_refs or []) > 0 for s in swots):
                passed_criteria.append({
                    "id": "S1_SWOT_EVIDENCE",
                    "title": "Chẩn đoán nội tại có bằng chứng",
                    "description": "Đã xác thực SWOT có liên kết dữ liệu thực tế.",
                    "is_met": True,
                })
            else:
                missing_criteria.append({
                    "id": "S1_SWOT_EVIDENCE",
                    "title": "Chẩn đoán nội tại có bằng chứng",
                    "description": "Cần cập nhật ít nhất 1 điểm Mạnh/Yếu có bằng chứng minh chứng.",
                    "is_met": False,
                })

        elif from_stage == "S2_SOLUTION_VALIDATION":
            # 1. Giả định Giải pháp / Giá có bằng chứng >= 0.6
            sol_hypos = [h for h in hypos if h.category in ("solution", "pricing", "product")]
            valid_sol = [h for h in sol_hypos if (h.evidence_score or 0.0) >= 0.6]

            if valid_sol:
                passed_criteria.append({
                    "id": "S2_SOLUTION_EVIDENCE",
                    "title": "Xác thực giải pháp MVP & Willingness-to-pay",
                    "description": f"Có {len(valid_sol)} giả định giải pháp đạt điểm bằng chứng >= 60%.",
                    "is_met": True,
                })
            else:
                missing_criteria.append({
                    "id": "S2_SOLUTION_EVIDENCE",
                    "title": "Xác thực giải pháp MVP & Willingness-to-pay",
                    "description": "Cần ít nhất 1 giả định giải pháp/giá đạt điểm bằng chứng >= 60%.",
                    "is_met": False,
                })

            # 2. Có bằng chứng cấp E3 (Behavioral) hoặc E4 (Economic)
            e3_e4 = [e for e in evidences if e.ladder_level in ("E3_BEHAVIORAL_COMMITMENT", "E4_ECONOMIC_COMMITMENT")]
            if len(e3_e4) >= 2:
                passed_criteria.append({
                    "id": "S2_E3_E4_COMMITMENT",
                    "title": "Cam kết hành vi / kinh tế (E3/E4)",
                    "description": f"Đã có {len(e3_e4)} bằng chứng cam kết sử dụng hoặc đặt cọc trả tiền.",
                    "is_met": True,
                })
            else:
                missing_criteria.append({
                    "id": "S2_E3_E4_COMMITMENT",
                    "title": "Cam kết hành vi / kinh tế (E3/E4)",
                    "description": "Cần ít nhất 2 bằng chứng cam kết hành vi (E3) hoặc đặt cọc (E4).",
                    "is_met": False,
                })

        else:
            # Giai đoạn S3, S4, S5
            if len(evidences) >= 3:
                passed_criteria.append({
                    "id": "GENERIC_EVIDENCE_ACCUMULATION",
                    "title": "Tích lũy bằng chứng thực tế",
                    "description": f"Đã tích lũy {len(evidences)} bằng chứng.",
                    "is_met": True,
                })
            else:
                missing_criteria.append({
                    "id": "GENERIC_EVIDENCE_ACCUMULATION",
                    "title": "Tích lũy bằng chứng thực tế",
                    "description": "Cần thêm bằng chứng để chuyển giai đoạn an toàn.",
                    "is_met": False,
                })

        total_criteria = len(passed_criteria) + len(missing_criteria)
        readiness_score = round(len(passed_criteria) / total_criteria, 2) if total_criteria > 0 else 0.0

        if readiness_score >= 0.75:
            audit_status = AuditStatusEnum.APPROVED.value
            rec_note = f"Dự án đủ điều kiện vững chắc để nâng cấp từ {from_stage} lên {target_stage}."
        elif readiness_score >= 0.50:
            audit_status = AuditStatusEnum.CONDITIONALLY_APPROVED.value
            rec_note = f"Dự án có thể nâng cấp lên {target_stage} nhưng cần hoàn thiện gấp các tiêu chí còn thiếu."
        else:
            audit_status = AuditStatusEnum.REJECTED.value
            rec_note = f"Chưa đủ cơ sở bằng chứng để chuyển sang {target_stage}. Hãy tiếp tục ở lại {from_stage} để kiểm chứng."

        # Quét cảnh báo rủi ro Premature Scaling
        alerts = StageGateService.check_anti_premature_guardrails(db, workspace_id, project_id)
        detected_risks = [
            {"severity": a.severity, "rule_code": a.rule_code, "message": a.message}
            for a in alerts
        ]

        audit = StageTransitionAudit(
            workspace_id=workspace_id,
            project_id=project_id,
            from_stage=from_stage,
            to_stage=target_stage,
            readiness_score=readiness_score,
            audit_status=audit_status,
            passed_criteria=passed_criteria,
            missing_criteria=missing_criteria,
            detected_risks=detected_risks,
            audited_by_agent="Stage Gate Auditor Agent",
            recommendation_note=rec_note,
        )
        db.add(audit)
        db.commit()
        db.refresh(audit)
        return audit

    @staticmethod
    def check_anti_premature_guardrails(
        db: Session,
        workspace_id: int,
        project_id: int,
    ) -> List[PrematureScalingAlert]:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return []

        stage = str(getattr(project, "project_stage", "S1_PROBLEM_VALIDATION")).upper()
        alerts: List[PrematureScalingAlert] = []

        # 1. Cảnh báo mở rộng marketing sớm ở S0/S1
        if "S0" in stage or "S1" in stage:
            tows = db.query(TowsOption).filter(TowsOption.project_id == project_id).all()
            for opt in tows:
                for tactic in (opt.tactics_12wy or []):
                    title = str(tactic.get("title", "")).lower()
                    if "chạy ads" in title or "paid marketing" in title or "quảng cáo ngân sách lớn" in title:
                        alert = PrematureScalingAlert(
                            workspace_id=workspace_id,
                            project_id=project_id,
                            current_stage=stage,
                            rule_code="NO_PAID_ADS_IN_EARLY_STAGE",
                            severity=AlertSeverityEnum.CRITICAL.value,
                            title="Rủi ro Đốt Tiền Quảng Cáo Sớm (Premature Paid Ads)",
                            message="Dự án đang ở giai đoạn Xác thực Nỗi Đau. Chi ngân sách chạy quảng cáo trước khi đạt Problem/Solution Fit có 80% nguy cơ lãng phí vốn.",
                        )
                        db.add(alert)
                        alerts.append(alert)

        # 2. Cảnh báo Over-engineering ở S0..S3
        if any(s in stage for s in ("S0", "S1", "S2", "S3")):
            bsc_goals = db.query(BscGoal).filter(BscGoal.project_id == project_id).all()
            if len(bsc_goals) > 0:
                alert = PrematureScalingAlert(
                    workspace_id=workspace_id,
                    project_id=project_id,
                    current_stage=stage,
                    rule_code="PREMATURE_BSC_OVERENGINEERING",
                    severity=AlertSeverityEnum.WARNING.value,
                    title="Cảnh báo Quản trị Vận hành Cồng Kềnh",
                    message=f"Dự án ở {stage} không nên vận hành bảng điểm BSC 4 trụ cột để tránh làm chậm tốc độ thử nghiệm.",
                )
                db.add(alert)
                alerts.append(alert)

        db.commit()
        return alerts

    @staticmethod
    def _is_primary_project(db: Session, workspace_id: int, project_id: int) -> bool:
        """Cùng quy ước với StageResolverService._resolve_project(): ưu tiên project
        active có strategic_priority P0, hết mới rơi về project mới nhất bất kể status."""
        primary = (
            db.query(Project)
            .filter(Project.workspace_id == workspace_id, Project.status == "active")
            .order_by(
                desc(Project.strategic_priority == "P0"),
                Project.created_at.desc(),
            )
            .first()
        )
        if not primary:
            primary = (
                db.query(Project)
                .filter(Project.workspace_id == workspace_id)
                .order_by(Project.created_at.desc())
                .first()
            )
        return primary is not None and primary.id == project_id

    @staticmethod
    def apply_stage_advancement(
        db: Session,
        workspace_id: int,
        audit_id: int,
        rationale: Optional[str] = None,
    ) -> Project:
        audit = db.query(StageTransitionAudit).filter(StageTransitionAudit.id == audit_id).first()
        if not audit or audit.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên thẩm định.")

        if audit.audit_status == AuditStatusEnum.REJECTED.value:
            raise HTTPException(
                status_code=400,
                detail=f"Không thể nâng cấp giai đoạn vì phiên thẩm định bị TỪ CHỐI (Readiness Score: {int(audit.readiness_score * 100)}%).",
            )

        project = db.query(Project).filter(Project.id == audit.project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Không tìm thấy dự án.")

        # G3 Phase 1D: xác định trước khi advance, vì query "primary project" đôi khi
        # đọc lại chính project này (created_at/strategic_priority không đổi bởi lệnh này).
        is_primary = StageGateService._is_primary_project(db, workspace_id, project.id)

        old_stage = project.project_stage
        project.project_stage = audit.to_stage

        # G3 Phase 1D (Stage Operating Engine): workspace.company_stage trước đây là
        # field tĩnh, không bao giờ đổi sau khi khởi tạo. Đồng bộ nó theo dự án chủ lực
        # (P0/mới nhất) mỗi khi dự án đó thật sự nâng cấp giai đoạn qua cổng thẩm định có
        # evidence - biến company_stage thành giá trị phái sinh có thật thay vì "S0_GENESIS"
        # đóng băng vĩnh viễn, mà không cần một engine chuyển giai đoạn thứ hai song song.
        if is_primary:
            workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
            if workspace is not None:
                workspace.company_stage = audit.to_stage

        # Ghi nhận quyết định chiến lược vào Company Memory
        decision = StrategicDecision(
            workspace_id=workspace_id,
            brain_id=project.brain_id,
            project_id=project.id,
            decision=f"Nâng cấp giai đoạn dự án từ {old_stage} lên {audit.to_stage}",
            question=f"Dự án {project.title} đã đạt đủ điều kiện để chuyển sang {audit.to_stage} chưa?",
            selected_option=audit.to_stage,
            rationale=rationale or audit.recommendation_note,
            stage=audit.to_stage,
            status="approved",
        )
        db.add(decision)
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def get_audit_history(
        db: Session,
        workspace_id: int,
        project_id: int,
    ) -> List[StageTransitionAudit]:
        return (
            db.query(StageTransitionAudit)
            .filter(
                StageTransitionAudit.workspace_id == workspace_id,
                StageTransitionAudit.project_id == project_id,
            )
            .order_by(StageTransitionAudit.created_at.desc())
            .all()
        )
