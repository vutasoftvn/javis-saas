from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from business.marketing.models import MarketingExperiment
from business.marketing.models_validation import (
    Assumption,
    Evidence,
    AssumptionCategory,
    AssumptionStatus,
    ConfidenceLevel,
    EvidenceSourceType,
    EvidenceStrength,
)
from business.marketing.schemas.validation_schemas import EvidenceCreate
from business.marketing.services.assumption_service import AssumptionService


SYSTEM_PROMPT_EXPERIMENT_DESIGNER = """SYSTEM ROLE
Bạn là COSA Experiment Designer (§27 trong E3.md).

Mục tiêu của bạn không phải chạy marketing nhiều nhất.
Mục tiêu là thiết kế thử nghiệm nhỏ nhất (smallest useful experiment) có thể tạo ra bằng chứng hữu ích cho critical assumption.

INPUT:
- project context
- assumption
- available channels / budget
- constraints

OUTPUT:
1. Hypothesis
2. Experiment method (interview, survey, landing_page, ab_test, prototype, pricing_test, concierge)
3. Metric
4. Success threshold (e.g. '>= 6/10 confirmed', '>= 8% cvr')
5. Minimum sample size
6. Timebox days
7. Required assets
8. Cost estimate
9. Risks
10. Human approval requirements

ƯU TIÊN:
- cheap before expensive;
- fast before slow;
- reversible before irreversible;
- evidence before scale.

Không đề xuất full campaign khi một interview, prototype hoặc landing-page test có thể kiểm chứng assumption với chi phí thấp hơn.
"""


class ExperimentDesignerService:
    """
    AI Experiment Designer & Lifecycle Management (§22 - §30 trong E3.md).
    """

    @classmethod
    def design_smallest_experiment(
        cls,
        assumption_statement: str,
        category: str,
        impact: int = 4,
        uncertainty: int = 4,
    ) -> Dict[str, Any]:
        """
        Thiết kế thử nghiệm nhỏ nhất dựa trên Category và Criticality của Giả định.
        """
        clean_cat = category.lower()
        
        if clean_cat in ("customer", "problem"):
            method = "interview"
            hypothesis = f"Ít nhất 60% đối tượng mục tiêu được phỏng vấn xác nhận vấn đề: '{assumption_statement}' là cấp thiết."
            metric = "problem_confirmation_rate"
            success_threshold = ">= 60% (>= 6/10 confirmed)"
            minimum_sample = 10
            timebox_days = 5
            cost_estimate = 0.0
            requires_approval = False
            required_assets = ["Interview script", "Target outreach list"]
            risks = "False positive do câu hỏi leading - cần áp dụng kỹ thuật The Mom Test."

        elif clean_cat in ("pricing", "business_model"):
            method = "pricing_test"
            hypothesis = f"Khách hàng sẵn sàng nhấn nút đặt cọc/mua với mức giá đề xuất khi thấy offer: '{assumption_statement}'."
            metric = "deposit_or_intent_cvr"
            success_threshold = ">= 5.0% intent click to payment"
            minimum_sample = 100
            timebox_days = 7
            cost_estimate = 500000.0  # 500k test ads
            requires_approval = True
            required_assets = ["Pricing page / fake-door button", "Tracking pixel"]
            risks = "Kỳ vọng khách hàng thất vọng nếu không có trang giải thích đặt trước rõ ràng."

        elif clean_cat in ("positioning", "value_proposition"):
            method = "landing_page"
            hypothesis = f"Thông điệp định vị '{assumption_statement}' tạo tỷ lệ đăng ký nhận tư vấn vượt trội so với baseline."
            metric = "lead_conversion_rate"
            success_threshold = ">= 8.0% conversion rate"
            minimum_sample = 200
            timebox_days = 7
            cost_estimate = 1000000.0
            requires_approval = True
            required_assets = ["Landing Page Spec", "Lead capture form UTM"]
            risks = "Lượng truy cập không đúng tệp ICP."

        elif clean_cat in ("channel", "conversion"):
            method = "campaign"
            hypothesis = f"Kênh phân phối tạo ra qualified lead với chi phí chấp nhận được cho giả định '{assumption_statement}'."
            metric = "cost_per_qualified_lead"
            success_threshold = "CPA <= 150,000 VND & CVR >= 4%"
            minimum_sample = 300
            timebox_days = 7
            cost_estimate = 2000000.0
            requires_approval = True
            required_assets = ["3 Ad creatives", "Targeting rule", "Landing page"]
            risks = "Chi phí quảng cáo tăng cao nếu chưa tối ưu nội dung."

        else:
            method = "ab_test"
            hypothesis = f"Phương án thử nghiệm chứng minh: '{assumption_statement}'."
            metric = "conversion_rate"
            success_threshold = ">= 5.0%"
            minimum_sample = 150
            timebox_days = 7
            cost_estimate = 500000.0
            requires_approval = False
            required_assets = ["Variant A copy", "Variant B copy"]
            risks = "Cỡ mẫu không đủ ý nghĩa thống kê."

        return {
            "system_prompt": SYSTEM_PROMPT_EXPERIMENT_DESIGNER,
            "assumption_statement": assumption_statement,
            "category": category,
            "hypothesis": hypothesis,
            "method": method,
            "metric": metric,
            "success_threshold": success_threshold,
            "minimum_sample": minimum_sample,
            "timebox_days": timebox_days,
            "cost_estimate": cost_estimate,
            "requires_external_action": requires_approval,
            "required_assets": required_assets,
            "risks": risks,
        }

    @classmethod
    def evaluate_scale_warning(
        cls,
        assumption: Optional[Assumption],
    ) -> Dict[str, Any]:
        """
        Kiểm tra rủi ro trước khi scale chiến dịch (§30, §52 trong E3.md).
        Nếu critical assumption chưa được validate -> đưa ra Soft Warning.
        """
        if not assumption:
            return {
                "allow_scale": True,
                "warning": None,
                "recommendation": "CAMPAIGN",
            }

        if assumption.status == AssumptionStatus.UNTESTED.value and assumption.criticality >= 15:
            return {
                "allow_scale": True,  # Soft warning, founder can Continue Anyway (§52)
                "has_warning": True,
                "warning_title": "⚠️ Critical Assumption Chưa Được Kiểm Chứng",
                "warning_message": (
                    f"Bạn đang chuẩn bị mở rộng chiến dịch nhưng giả định quan trọng: "
                    f"'{assumption.statement}' (Criticality {assumption.criticality}/25) "
                    f"chưa có bằng chứng thị trường xác nhận."
                ),
                "recommendation": "EXPERIMENT",
                "recommended_action": "Nên chạy thử nghiệm nhỏ (Customer Interview hoặc Pricing Test) trước khi chi tiêu lớn.",
                "options": ["Validate First (Recommended)", "Continue Anyway"],
            }

        return {
            "allow_scale": True,
            "has_warning": False,
            "recommendation": "CAMPAIGN",
            "message": "Giả định đã có bằng chứng xác thực, an toàn để mở rộng chiến dịch.",
        }

    @classmethod
    def complete_experiment(
        cls,
        db: Session,
        workspace_id: int,
        brain_id: int,
        experiment: MarketingExperiment,
        conclusion: str,  # supported, partially_supported, contradicted, inconclusive
        observations: Dict[str, Any],
        learning_summary: str,
    ) -> Tuple[MarketingExperiment, Optional[Evidence], Optional[Assumption]]:
        """
        Hoàn tất thử nghiệm, ghi nhận Evidence và tự động cập nhật Assumption liên kết (§25, §36, §102).
        """
        experiment.status = "completed"
        experiment.conclusion = conclusion
        experiment.learning = learning_summary
        
        # 1. Tạo Evidence từ kết quả thử nghiệm
        evidence = None
        updated_assumption = None

        if experiment.assumption_id:
            strength = EvidenceStrength.STRONG if conclusion in ("supported", "contradicted") else EvidenceStrength.MEDIUM
            supports_ids = [str(experiment.assumption_id)] if conclusion in ("supported", "partially_supported") else []
            contradicts_ids = [str(experiment.assumption_id)] if conclusion == "contradicted" else []

            ev_data = EvidenceCreate(
                statement=f"Kết quả thử nghiệm '{experiment.hypothesis}': {learning_summary}",
                source_type=EvidenceSourceType.EXPERIMENT,
                source_id=str(experiment.id),
                project_id=experiment.project_id,
                supports_assumption_ids=supports_ids,
                contradicts_assumption_ids=contradicts_ids,
                strength=strength,
                meta_data=observations,
            )
            evidence, updated_asms = AssumptionService.create_evidence(
                db=db,
                workspace_id=workspace_id,
                brain_id=brain_id,
                data=ev_data,
            )
            if updated_asms:
                updated_assumption = updated_asms[0]

        # 2. Cập nhật result dict trên experiment
        experiment.result = {
            "conclusion": conclusion,
            "observations": observations,
            "evidence_id": str(evidence.id) if evidence else None,
            "learning": learning_summary,
            "completed_at": datetime.utcnow().isoformat(),
        }

        db.flush()
        return experiment, evidence, updated_assumption
