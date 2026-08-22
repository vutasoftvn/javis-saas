import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Session

from core.snowflake import generate_snowflake_id
from core.tenancy import get_project_scoped

from founder_os.strategy.models import Project, ProjectClassification
from workforce.chat.model_profiles import PROFILE_CONVERSATION_ROUTER, resolve_profile
from workforce.chat.model_registry import is_provider_configured
from workforce.chat.providers import build_provider

logger = logging.getLogger(__name__)

PROJECT_TYPE_RECOMMENDED_METHODOLOGIES: Dict[str, List[str]] = {
    "NEW_BUSINESS": ["VISION_MISSION", "PESTEL", "SWOT", "TOWS", "OKR", "12WY", "STAGE_GATE"],
    "PRODUCT": ["SWOT", "TOWS", "OKR", "12WY", "STAGE_GATE", "PLAYBOOK"],
    "GROWTH": ["SWOT", "OKR", "12WY", "PLAYBOOK"],
    "OPERATIONAL": ["SOP", "12WY", "PDCA"],
    "TECHNICAL": ["TECHNICAL_WORKFLOW", "CLAUDE_CODE", "STAGE_GATE"],
    "EXPERIMENT": ["LEAN_VALIDATION", "EXPERIMENT_GATE", "12WY"],
    "COMPLIANCE": ["CHECKLIST", "EVIDENCE_AUDIT", "STAGE_GATE"],
    "STRATEGIC": ["VISION_MISSION", "PESTEL", "SWOT", "TOWS", "BSC", "OKR", "12WY"],
}


class ProjectClassifierService:
    def __init__(self, db: Session, workspace_id: int, user_id: int):
        self.db = db
        self.workspace_id = workspace_id
        self.user_id = user_id

    def heuristic_classify(self, title: str, description: Optional[str] = None) -> Dict[str, Any]:
        """Rule-based heuristic classifier when offline or as fast baseline."""
        text = f"{title} {description or ''}".lower()

        if any(w in text for w in ["kinh doanh mới", "khởi nghiệp", "start-up", "thị trường mới", "new business", "new market"]):
            ptype = "NEW_BUSINESS"
            depth = "high"
            uncertainty = "high"
            risk = "high"
            research = True
            ext_ev = True
            human_areas = ["strategic_direction", "pricing_model", "investor_stakeholder"]
            rationale = "Dự án mở rộng hoặc khai phá thị trường/mô hình kinh doanh mới có độ bất định và rủi ro chiến lược cao."
        elif any(w in text for w in ["bug", "fix", "refactor", "database", "migration", "kỹ thuật", "tech", "ci/cd"]):
            ptype = "TECHNICAL"
            depth = "low"
            uncertainty = "low"
            risk = "low"
            research = False
            ext_ev = False
            human_areas = ["code_review_signoff"]
            rationale = "Dự án kỹ thuật / nâng cấp hệ thống tập trung vào workflow kỹ thuật và kiểm thử tự động."
        elif any(w in text for w in ["sản phẩm", "product", "tính năng", "feature", "mvp", "app", "ui/ux"]):
            ptype = "PRODUCT"
            depth = "medium"
            uncertainty = "medium"
            risk = "medium"
            research = True
            ext_ev = True
            human_areas = ["product_spec_approval", "ux_validation"]
            rationale = "Dự án phát triển sản phẩm/tính năng cần xác thực nhu cầu người dùng và cổng kiểm soát chất lượng."
        elif any(w in text for w in ["marketing", "tăng trưởng", "growth", "chiến dịch", "campaign", "lead", "seo", "ads"]):
            ptype = "GROWTH"
            depth = "medium"
            uncertainty = "medium"
            risk = "medium"
            research = True
            ext_ev = True
            human_areas = ["budget_allocation", "creative_direction"]
            rationale = "Dự án tiếp thị và tăng trưởng tập trung vào playbook chiến dịch và các chỉ số đo lường chuyển đổi."
        elif any(w in text for w in ["quy trình", "vận hành", "sop", "nội bộ", "operation", "training", "đào tạo"]):
            ptype = "OPERATIONAL"
            depth = "low"
            uncertainty = "low"
            risk = "low"
            research = False
            ext_ev = False
            human_areas = ["process_standard_approval"]
            rationale = "Dự án tối ưu hóa vận hành nội bộ theo phương pháp chuẩn hóa quy trình SOP và chu trình PDCA."
        elif any(w in text for w in ["thử nghiệm", "experiment", "giả thuyết", "pilot", "a/b test"]):
            ptype = "EXPERIMENT"
            depth = "medium"
            uncertainty = "high"
            risk = "low"
            research = True
            ext_ev = True
            human_areas = ["hypothesis_definition", "pivot_decision"]
            rationale = "Dự án thử nghiệm giả thuyết kinh doanh theo chu trình Lean Validation và cổng kiểm nghiệm dữ liệu."
        elif any(w in text for w in ["pháp lý", "tuân thủ", "luật", "compliance", "bảo mật", "security", "gdpr", "audit"]):
            ptype = "COMPLIANCE"
            depth = "low"
            uncertainty = "low"
            risk = "high"
            research = True
            ext_ev = True
            human_areas = ["legal_signoff", "risk_exception"]
            rationale = "Dự án tuân thủ và pháp chế đòi hỏi checklist nghiêm ngặt và lưu vết bằng chứng pháp lý."
        else:
            ptype = "STRATEGIC"
            depth = "high"
            uncertainty = "medium"
            risk = "medium"
            research = True
            ext_ev = True
            human_areas = ["strategic_tradeoffs", "goal_alignment"]
            rationale = "Dự án chiến lược trọng điểm đòi hỏi phân tích toàn diện 1-1-3 và theo dõi chu kỳ 12 tuần."

        methodologies = PROJECT_TYPE_RECOMMENDED_METHODOLOGIES.get(ptype, ["SWOT", "OKR", "12WY"])

        return {
            "project_type": ptype,
            "strategic_depth": depth,
            "uncertainty_level": uncertainty,
            "risk_level": risk,
            "research_required": research,
            "external_evidence_required": ext_ev,
            "internal_context_required": True,
            "recommended_methodologies": methodologies,
            "human_required_areas": human_areas,
            "rationale": rationale,
            "confidence_score": 0.88,
        }

    def classify_project(
        self,
        project_id: int,
        title_override: Optional[str] = None,
        description_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Classify a project, update project state and save classification record."""
        project = get_project_scoped(self.db, project_id, self.workspace_id)
        
        title = title_override or project.title
        description = description_override or project.phase or ""

        classification_data = None
        provider_name, model_name = resolve_profile(PROFILE_CONVERSATION_ROUTER)

        # Attempt structured AI classification if provider is configured
        if is_provider_configured(provider_name):
            try:
                provider = build_provider(provider_name, model_name, self.workspace_id)
                prompt = (
                    f"Bạn là AI phân loại dự án COSA OS. Phân loại dự án sau:\n"
                    f"Tên: {title}\n"
                    f"Mô tả/Giai đoạn: {description}\n\n"
                    f"Trả về JSON hợp lệ theo định dạng sau (không giải thích thêm):\n"
                    f'{{"project_type": "STRATEGIC|NEW_BUSINESS|PRODUCT|GROWTH|OPERATIONAL|TECHNICAL|EXPERIMENT|COMPLIANCE", '
                    f'"strategic_depth": "high|medium|low", '
                    f'"uncertainty_level": "high|medium|low", '
                    f'"risk_level": "high|medium|low", '
                    f'"research_required": true|false, '
                    f'"external_evidence_required": true|false, '
                    f'"internal_context_required": true|false, '
                    f'"recommended_methodologies": ["string"], '
                    f'"human_required_areas": ["string"], '
                    f'"rationale": "string", '
                    f'"confidence_score": 0.9}}\n'
                )
                response = provider.chat([{"role": "user", "content": prompt}], temperature=0.1)
                text_content = response.content.strip()
                if "```json" in text_content:
                    text_content = text_content.split("```json")[1].split("```")[0].strip()
                elif "```" in text_content:
                    text_content = text_content.split("```")[1].split("```")[0].strip()
                parsed = json.loads(text_content)
                if "project_type" in parsed:
                    classification_data = parsed
            except Exception as exc:
                logger.warning("AI classification failed, falling back to heuristic: %s", exc)

        if not classification_data:
            classification_data = self.heuristic_classify(title, description)

        now = datetime.utcnow()
        # Find existing classification or create new
        classification = (
            self.db.query(ProjectClassification)
            .filter(
                ProjectClassification.project_id == project_id,
                ProjectClassification.workspace_id == self.workspace_id,
            )
            .first()
        )

        ptype = classification_data.get("project_type", "STRATEGIC")

        if classification:
            classification.project_type = ptype
            classification.strategic_depth = classification_data.get("strategic_depth")
            classification.uncertainty_level = classification_data.get("uncertainty_level")
            classification.risk_level = classification_data.get("risk_level")
            classification.research_required = classification_data.get("research_required", False)
            classification.external_evidence_required = classification_data.get("external_evidence_required", False)
            classification.internal_context_required = classification_data.get("internal_context_required", True)
            classification.recommended_methodologies = classification_data.get("recommended_methodologies", [])
            classification.human_required_areas = classification_data.get("human_required_areas", [])
            classification.rationale = classification_data.get("rationale")
            classification.confidence_score = classification_data.get("confidence_score", 0.85)
            classification.classified_by = self.user_id
            classification.updated_at = now
        else:
            classification = ProjectClassification(
                id=generate_snowflake_id(),
                workspace_id=self.workspace_id,

                project_id=project_id,
                project_type=ptype,
                strategic_depth=classification_data.get("strategic_depth"),
                uncertainty_level=classification_data.get("uncertainty_level"),
                risk_level=classification_data.get("risk_level"),
                research_required=classification_data.get("research_required", False),
                external_evidence_required=classification_data.get("external_evidence_required", False),
                internal_context_required=classification_data.get("internal_context_required", True),
                recommended_methodologies=classification_data.get("recommended_methodologies", []),
                human_required_areas=classification_data.get("human_required_areas", []),
                rationale=classification_data.get("rationale"),
                confidence_score=classification_data.get("confidence_score", 0.85),
                classified_by=self.user_id,
                created_at=now,
                updated_at=now,
            )
            self.db.add(classification)

        # Sync project.project_type
        project.project_type = ptype

        self.db.commit()
        self.db.refresh(classification)

        return {
            "id": str(classification.id),
            "project_id": str(project.id),
            "project_type": classification.project_type,
            "strategic_depth": classification.strategic_depth,
            "uncertainty_level": classification.uncertainty_level,
            "risk_level": classification.risk_level,
            "research_required": classification.research_required,
            "external_evidence_required": classification.external_evidence_required,
            "internal_context_required": classification.internal_context_required,
            "recommended_methodologies": classification.recommended_methodologies,
            "human_required_areas": classification.human_required_areas,
            "rationale": classification.rationale,
            "confidence_score": classification.confidence_score,
            "classified_by": str(classification.classified_by) if classification.classified_by else None,
            "created_at": classification.created_at.isoformat() if classification.created_at else None,
            "updated_at": classification.updated_at.isoformat() if classification.updated_at else None,
        }
