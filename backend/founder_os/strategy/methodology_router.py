import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Session

from core.snowflake import generate_snowflake_id
from core.tenancy import get_project_scoped

from founder_os.strategy.models import Project, ProjectClassification, MethodologyPlan
from founder_os.strategy.project_classifier_service import PROJECT_TYPE_RECOMMENDED_METHODOLOGIES

logger = logging.getLogger(__name__)

ALL_METHODOLOGY_PRIMITIVES: Dict[str, Dict[str, str]] = {
    "VISION_MISSION": {"name": "Tầm nhìn / Sứ mệnh / Giá trị cốt lõi (1-1-3)", "category": "FOUNDATION"},
    "PESTEL": {"name": "Phân tích Môi trường Vĩ mô (PESTEL 6x3)", "category": "ANALYSIS"},
    "SWOT": {"name": "Ma trận Điểm mạnh / Yếu / Cơ hội / Thách thức (SWOT 4x3)", "category": "ANALYSIS"},
    "TOWS": {"name": "Chiến lược Kết hợp (TOWS SO/ST/WO/WT)", "category": "ANALYSIS"},
    "BSC": {"name": "Thẻ điểm Cân bằng (Balanced Scorecard 4 góc nhìn)", "category": "GOVERNANCE"},
    "OKR": {"name": "Mục tiêu & Kết quả Then chốt (Objectives & Key Results)", "category": "EXECUTION"},
    "12WY": {"name": "Kế hoạch Thực thi 12 Tuần (12 Week Year)", "category": "EXECUTION"},
    "STAGE_GATE": {"name": "Cổng Kiểm soát Giai đoạn (Stage-Gate GO/STOP/PIVOT)", "category": "GOVERNANCE"},
    "LEAN_VALIDATION": {"name": "Xác thực Tinh gọn (Lean Validation Loop)", "category": "EXPERIMENT"},
    "EXPERIMENT_GATE": {"name": "Cổng Thử nghiệm Giả thuyết (Hypothesis Gate)", "category": "EXPERIMENT"},
    "PLAYBOOK": {"name": "Cẩm nang Chiến dịch (Playbook Thực thi)", "category": "EXECUTION"},
    "SOP": {"name": "Quy trình Vận hành Chuẩn (Standard Operating Procedure)", "category": "OPERATIONS"},
    "PDCA": {"name": "Chu trình Cải tiến Liên tục (Plan-Do-Check-Act)", "category": "OPERATIONS"},
    "TECHNICAL_WORKFLOW": {"name": "Quy trình Phát triển Kỹ thuật & CI/CD", "category": "ENGINEERING"},
    "CLAUDE_CODE": {"name": "Lập trình Tự động với Claude Code Worker", "category": "ENGINEERING"},
    "CHECKLIST": {"name": "Danh mục Kiểm tra Tuân thủ (Compliance Checklist)", "category": "COMPLIANCE"},
    "EVIDENCE_AUDIT": {"name": "Kiểm toán & Lưu vết Bằng chứng Pháp lý", "category": "COMPLIANCE"},
}


class MethodologyRouterService:
    def __init__(self, db: Session, workspace_id: int, user_id: int):
        self.db = db
        self.workspace_id = workspace_id
        self.user_id = user_id

    def get_plan(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Get the active methodology plan for a project."""
        plan = (
            self.db.query(MethodologyPlan)
            .filter(
                MethodologyPlan.project_id == project_id,
                MethodologyPlan.workspace_id == self.workspace_id,
            )
            .first()
        )
        if not plan:
            return None
        return self._serialize_plan(plan)

    def route_methodology(
        self,
        project_id: int,
        custom_methodologies: Optional[List[str]] = None,
        custom_rules: Optional[Dict[str, Any]] = None,
        rationale_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Route and create/update a methodology plan for a project."""
        project = get_project_scoped(self.db, project_id, self.workspace_id)

        classification = (
            self.db.query(ProjectClassification)
            .filter(
                ProjectClassification.project_id == project_id,
                ProjectClassification.workspace_id == self.workspace_id,
            )
            .first()
        )

        ptype = project.project_type or (classification.project_type if classification else "STRATEGIC")

        if custom_methodologies and len(custom_methodologies) > 0:
            selected = custom_methodologies
            rationale = rationale_override or "Lộ trình phương pháp được tùy biến thủ công bởi nhà sáng lập."
        else:
            base_methods = PROJECT_TYPE_RECOMMENDED_METHODOLOGIES.get(
                ptype, ["VISION_MISSION", "PESTEL", "SWOT", "TOWS", "OKR", "12WY"]
            )
            selected = list(base_methods)
            rationale = (
                rationale_override
                or f"Lộ trình đề xuất tự động theo phân loại dự án [{ptype}]: "
                f"Tập trung vào {', '.join(selected)}."
            )

        now = datetime.utcnow()
        plan = (
            self.db.query(MethodologyPlan)
            .filter(
                MethodologyPlan.project_id == project_id,
                MethodologyPlan.workspace_id == self.workspace_id,
            )
            .first()
        )

        if plan:
            plan.selected_methodologies = selected
            plan.rationale = rationale
            plan.status = "active"
            if custom_rules is not None:
                plan.custom_rules = custom_rules
            plan.updated_at = now
        else:
            plan = MethodologyPlan(
                id=generate_snowflake_id(),
                workspace_id=self.workspace_id,

                project_id=project_id,
                selected_methodologies=selected,
                rationale=rationale,
                status="active",
                custom_rules=custom_rules or {},
                created_by=self.user_id,
                created_at=now,
                updated_at=now,
            )
            self.db.add(plan)

        self.db.commit()
        self.db.refresh(plan)
        return self._serialize_plan(plan)

    def _serialize_plan(self, plan: MethodologyPlan) -> Dict[str, Any]:
        return {
            "id": str(plan.id),
            "project_id": str(plan.project_id),
            "selected_methodologies": plan.selected_methodologies,
            "rationale": plan.rationale,
            "status": plan.status,
            "custom_rules": plan.custom_rules,
            "created_by": str(plan.created_by) if plan.created_by else None,
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
            "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
        }
