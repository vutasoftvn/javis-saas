"""Tool đọc dữ liệu vòng lặp Validation cho chat chung (chief_of_staff).

Trước đây founder phải tự mở Validation Studio để biết dự án đang ở đâu trong vòng lặp
kiểm chứng (risk matrix, next best action, role coverage...); màn hình chat chính không
nhìn thấy gì cả. Tool này chỉ ĐỌC — không tạo/sửa assumption, hypothesis hay evidence, vì
đó là việc của `/validation/chat` (interview mode, người dùng chủ động bật). Chat chung
chỉ tóm tắt trạng thái và, nếu cần hành động, dùng `chat.propose_action` sẵn có — không tự
ghi gì vào chain, giữ đúng ranh giới read-only mà company_tools.py đã đặt ra.

Không gắn ``flag_key``: xem cảnh báo trong founder_os/strategy/tools.py về
``company.next_best_actions`` từng biến mất vì gắn nhầm flag chưa ai seed.
"""

from typing import Optional

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from core.tool_registry import register
from founder_os.strategy.models import Project
from founder_os.validation.models import ValidationSession
from founder_os.validation.problem_intelligence_service import ProblemIntelligenceService
from founder_os.validation.question_graph_service import QuestionGraphService
from founder_os.validation.risk_service import RiskPrioritizationService
from founder_os.validation.review_service import ValidationReviewService
from founder_os.validation.service import ValidationEngineService


def _resolve_project(db: Session, workspace_id: int, project_id: str):
    try:
        pid = int(project_id)
    except (TypeError, ValueError):
        return None, {"found": False, "error": "ID dự án không hợp lệ"}
    project = db.query(Project).filter(Project.id == pid, Project.workspace_id == workspace_id).first()
    if not project:
        return None, {"found": False, "error": f"Không tìm thấy dự án với ID {project_id}"}
    return project, None


@register(
    "validation",
    "get_snapshot",
    chat_schema={
        "description": (
            "Xem tổng hợp trạng thái vòng lặp Validation (kiểm chứng giả định) của một dự án: "
            "độ tự tin theo từng khía cạnh (Customer/Problem/Solution/Pricing/Channel...), "
            "giả định rủi ro cao nhất, hành động ưu tiên tiếp theo trong vòng lặp kiểm chứng, "
            "độ bao phủ vai trò phỏng vấn (User/Buyer/Decision Maker/Influencer), và câu hỏi "
            "ưu tiên cao nhất nên hỏi tiếp theo (Question Graph). Dùng khi "
            "người dùng hỏi dự án đang kiểm chứng tới đâu, giả định nào rủi ro nhất, hoặc nên "
            "làm gì tiếp theo để validate. Nếu chưa có project_id, gọi strategy.list_projects "
            "trước để tìm theo tên."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "ID của dự án cần xem trạng thái kiểm chứng.",
                },
            },
            "required": ["project_id"],
        },
    },
    risk_level="low",
    permission_level="read_only",
    idempotency=True,
    allowed_agent_keys=["chief_of_staff"],
)
def get_snapshot(db: Session, workspace_id: int, project_id: str) -> dict:
    """Co-founder State Snapshot read-only: state vector + riskiest assumption + NBA + role coverage."""
    project, err = _resolve_project(db, workspace_id, project_id)
    if err:
        return err

    state_vector = ValidationEngineService.get_state_vector(db, project.id)
    riskiest = RiskPrioritizationService.get_riskiest_assumptions(
        db, workspace_id=workspace_id, project_id=project.id, limit=1
    )
    top_risk = riskiest[0] if riskiest else None
    next_action = ValidationReviewService.synthesize_single_next_best_action(
        db, workspace_id=workspace_id, project_id=project.id
    )
    role_coverage = ProblemIntelligenceService.evaluate_role_coverage(
        db, workspace_id=workspace_id, project_id=project.id
    )
    session = db.scalars(
        select(ValidationSession)
        .where(
            ValidationSession.workspace_id == workspace_id,
            ValidationSession.project_id == project.id,
        )
        .order_by(desc(ValidationSession.created_at))
    ).first()
    question_suggestion = QuestionGraphService.select_next_question(
        db, workspace_id=workspace_id, project_id=project.id, session=session,
    )

    return {
        "found": True,
        "project_id": str(project.id),
        "project_title": project.title,
        "project_stage": state_vector.project_stage,
        "overall_confidence": state_vector.overall_confidence,
        "dimensions": {
            name: {"state": d.state, "confidence": d.confidence, "summary": d.summary}
            for name, d in state_vector.dimensions.items()
        },
        "top_risk_assumption": (
            {
                "id": str(top_risk.id),
                "category": top_risk.category,
                "statement": top_risk.statement,
                "risk_score": top_risk.risk_score,
                "status": top_risk.status,
            }
            if top_risk
            else None
        ),
        "next_best_action": {
            "title": next_action.title,
            "why": next_action.why,
            "priority": next_action.priority,
        },
        "role_coverage": {
            "user_count": role_coverage.user_count,
            "buyer_count": role_coverage.buyer_count,
            "decision_maker_count": role_coverage.decision_maker_count,
            "influencer_count": role_coverage.influencer_count,
            "has_decision_maker_gap": role_coverage.has_decision_maker_gap,
            "warning_message": role_coverage.warning_message,
        },
        "next_question": (
            {
                "prompt_vi": question_suggestion["node"]["prompt_vi"],
                "rationale": question_suggestion["rationale"],
            }
            if question_suggestion and question_suggestion.get("node")
            else None
        ),
    }
