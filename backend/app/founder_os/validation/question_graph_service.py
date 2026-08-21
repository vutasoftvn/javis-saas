"""Deterministic selection trên Question Graph (Supplement §14.2): thứ tự trong
``question_graph.py`` là ưu tiên mặc định; chỉ lệch khi một assumption cùng dimension có
risk_score ở mức "tử huyệt" (>=16, ngưỡng đã dùng sẵn cho Critical Risk quadrant trong
``risk_service.py``, không tự bịa ngưỡng mới).

Đây là lớp chọn CÂU HỎI, không phải lớp hỏi: kết quả được nhét vào prompt của
``ValidationInterviewService`` làm gợi ý ưu tiên, LLM vẫn diễn đạt tự nhiên và có thể đi
hướng khác nếu hội thoại thật sự cần — đúng nguyên tắc "code quyết định độ ưu tiên, LLM
diễn giải trong phạm vi cho phép".
"""

from typing import Any, Optional

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.founder_os.strategy.models import Project
from app.founder_os.strategy.schemas.stage_schemas import ProjectStageEnum
from app.founder_os.validation.models import ValidationAssumption, ValidationSession
from app.founder_os.validation.question_graph import QuestionNode, get_graph_for_stage

CRITICAL_RISK_THRESHOLD = 16  # khớp Critical Risk quadrant: importance>=4 & uncertainty>=4
SESSION_METADATA_ANSWERED_KEY = "question_graph_answered"


def _answered_ids(session: Optional[ValidationSession]) -> set[str]:
    if session is None:
        return set()
    return set((session.session_metadata or {}).get(SESSION_METADATA_ANSWERED_KEY, []))


def _critical_dimensions(db: Session, workspace_id: int, project_id: int) -> dict[str, int]:
    """Điểm risk_score cao nhất mỗi category, chỉ giữ lại các mức >= ngưỡng tử huyệt."""
    assumptions = db.scalars(
        select(ValidationAssumption).where(
            and_(
                ValidationAssumption.workspace_id == workspace_id,
                ValidationAssumption.project_id == project_id,
                ValidationAssumption.risk_score >= CRITICAL_RISK_THRESHOLD,
            )
        )
    ).all()
    result: dict[str, int] = {}
    for a in assumptions:
        result[a.category] = max(result.get(a.category, 0), a.risk_score)
    return result


class QuestionGraphService:
    @staticmethod
    def select_next_question(
        db: Session,
        workspace_id: int,
        project_id: int,
        session: Optional[ValidationSession] = None,
    ) -> Optional[dict[str, Any]]:
        project = db.get(Project, project_id)
        stage = project.project_stage if project else ProjectStageEnum.S0_EXPLORE.value
        graph = get_graph_for_stage(stage)
        if not graph:
            return None

        answered = _answered_ids(session)
        candidates = [(idx, node) for idx, node in enumerate(graph) if node["id"] not in answered]
        if not candidates:
            return {
                "node": None,
                "rationale": "Đã hỏi hết Question Graph cho stage này.",
                "answered_count": len(answered),
                "total": len(graph),
            }

        critical = _critical_dimensions(db, workspace_id, project_id)
        critical_candidates = [(idx, node) for idx, node in candidates if node["dimension"] in critical]

        if critical_candidates:
            idx, node = min(critical_candidates, key=lambda pair: pair[0])
            rationale = (
                f"Assumption thuộc dimension {node['dimension']} đang ở mức rủi ro tử huyệt "
                f"({critical[node['dimension']]}/25) — ưu tiên trước thứ tự mặc định."
            )
        else:
            idx, node = min(candidates, key=lambda pair: pair[0])
            rationale = "Câu hỏi tiếp theo theo đúng thứ tự Question Graph mặc định."

        return {
            "node": node,
            "rationale": rationale,
            "answered_count": len(answered),
            "total": len(graph),
        }

    @staticmethod
    def mark_answered(session: ValidationSession, node_id: str) -> None:
        metadata = dict(session.session_metadata or {})
        answered = list(metadata.get(SESSION_METADATA_ANSWERED_KEY, []))
        if node_id not in answered:
            answered.append(node_id)
        metadata[SESSION_METADATA_ANSWERED_KEY] = answered
        session.session_metadata = metadata

    @staticmethod
    def mark_answered_for_dimension(session: ValidationSession, dimension: str, stage: str) -> Optional[str]:
        """Đánh dấu node ĐẦU TIÊN chưa trả lời khớp dimension này là đã hỏi.

        Heuristic v1: một claim mới được trích xuất với dimension X coi như đã chạm tới
        node Question Graph đầu tiên chưa trả lời của dimension X. Không hoàn hảo về mặt
        epistemic (claim có thể chỉ trả lời một phần câu hỏi) nhưng không cần schema mới
        và đủ để tránh hỏi lặp lại nguyên văn cùng một câu.
        """
        graph = get_graph_for_stage(stage)
        answered = _answered_ids(session)
        for node in graph:
            if node["dimension"] == dimension and node["id"] not in answered:
                QuestionGraphService.mark_answered(session, node["id"])
                return node["id"]
        return None
