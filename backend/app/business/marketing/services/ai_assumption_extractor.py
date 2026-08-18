import re
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.business.marketing.models_validation import (
    EpistemicStatus,
    KnowledgeOrigin,
    ConfidenceLevel,
    AssumptionCategory,
    AssumptionStatus,
)
from app.business.marketing.schemas.validation_schemas import (
    AssumptionCreate,
    KnowledgeStatementCreate,
)
from app.business.marketing.services.assumption_service import AssumptionService


SYSTEM_PROMPT_ASSUMPTION_EXTRACTOR = """SYSTEM ROLE
Bạn là COSA Business Assumption Analyst (§18 trong E3.md).

Nhiệm vụ:
Phân tích business context và xác định những statement nào là:
- fact (sự thật quan sát hoặc đo lường trực tiếp)
- evidence (bằng chứng từ khách hàng/thị trường)
- inference (kết luận suy luận logic)
- assumption (giả định chưa có đủ bằng chứng)

Quy tắc bắt buộc:
1. Không được coi thông tin do AI hoặc founder suy đoán là fact nếu không có bằng chứng xác thực. Mặc định là assumption với confidence low.
2. Với mỗi assumption:
   - Xác định category (customer, problem, solution, value_proposition, positioning, offer, pricing, channel, conversion, retention, business_model);
   - Đánh giá impact 1-5;
   - Đánh giá uncertainty 1-5;
   - Tính criticality = impact * uncertainty;
   - Giải thích tại sao assumption này quan trọng (rationale);
   - Đề xuất có cần test hay không (should_test).
3. Ưu tiên các assumption có thể làm sụp đổ mô hình:
   - customer & problem pain;
   - willingness to pay & pricing;
   - solution feasibility;
   - distribution channel;
   - business model.
"""


class AIAssumptionExtractor:
    """
    AI Assumption Extractor Service (§17, §18 trong E3.md).
    Trích xuất và phân loại các giả định & tri thức từ Canvas hoặc Founder Brief.
    """

    @classmethod
    def extract_from_text(
        cls,
        text: str,
        project_id: Optional[int] = None,
        canvas_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Trích xuất và phân loại claims từ văn bản tự do / hội thoại founder.
        """
        clean_text = text.strip()
        if not clean_text:
            return {"knowledge_statements": [], "assumptions": []}

        # Phân tích các câu/đoạn
        sentences = [s.strip() for s in re.split(r"[\n\.\?\!]+", clean_text) if len(s.strip()) > 5]
        if not sentences:
            sentences = [clean_text]

        extracted_statements: List[Dict[str, Any]] = []
        extracted_assumptions: List[Dict[str, Any]] = []

        for sentence in sentences:
            epistemic_status = cls._classify_epistemic_status(sentence)
            category = cls._detect_category(sentence)
            impact, uncertainty, rationale = cls._score_impact_and_uncertainty(sentence, category)
            criticality = AssumptionService.calculate_criticality(impact, uncertainty)

            # Statement
            extracted_statements.append({
                "statement": sentence,
                "epistemic_status": epistemic_status.value,
                "origin": KnowledgeOrigin.AI_GENERATED.value,
                "confidence": ConfidenceLevel.LOW.value,
                "evidence_ids": [],
            })

            # Nếu là assumption hoặc inference quan trọng -> Đưa vào Assumption Register
            if epistemic_status in (EpistemicStatus.ASSUMPTION, EpistemicStatus.INFERENCE):
                extracted_assumptions.append({
                    "statement": sentence,
                    "category": category.value,
                    "impact": impact,
                    "uncertainty": uncertainty,
                    "criticality": criticality,
                    "confidence": ConfidenceLevel.LOW.value,
                    "status": AssumptionStatus.UNTESTED.value,
                    "rationale": rationale,
                    "project_id": project_id,
                    "canvas_id": canvas_id,
                    "should_test": criticality >= 9,
                })

        # Sắp xếp assumption theo criticality giảm dần
        extracted_assumptions.sort(key=lambda a: a["criticality"], reverse=True)

        return {
            "system_prompt": SYSTEM_PROMPT_ASSUMPTION_EXTRACTOR,
            "knowledge_statements": extracted_statements,
            "assumptions": extracted_assumptions,
            "total_extracted": len(extracted_assumptions),
        }

    @classmethod
    def extract_from_canvas(
        cls,
        canvas_type: str,
        canvas_data: Dict[str, Any],
        project_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Trích xuất assumptions từ dữ liệu có cấu trúc của một Canvas (§9, §10, §19, §20).
        """
        assumptions: List[Dict[str, Any]] = []

        if canvas_type == "customer_research":
            # 1. ICP & Persona
            icp = canvas_data.get("icp")
            if isinstance(icp, dict):
                desc = icp.get("description") or icp.get("segment") or str(icp)
                assumptions.append(cls._build_assumption_item(
                    statement=f"Phân khúc khách hàng mục tiêu: {desc}",
                    category=AssumptionCategory.CUSTOMER,
                    impact=5, uncertainty=4,
                    rationale="Nếu xác định sai ICP, toàn bộ chiến dịch marketing và sản phẩm sẽ không chuyển đổi.",
                    project_id=project_id, canvas_id="customer_research",
                ))

            # 2. Jobs to be done
            jobs = canvas_data.get("jobs_to_be_done") or canvas_data.get("jobs") or []
            if isinstance(jobs, list):
                for job in jobs:
                    if isinstance(job, str) and job.strip():
                        assumptions.append(cls._build_assumption_item(
                            statement=f"Khách hàng cần hoàn thành việc: {job.strip()}",
                            category=AssumptionCategory.PROBLEM,
                            impact=5, uncertainty=4,
                            rationale="Cần kiểm chứng đây là việc cấp bách (urgent) hay chỉ là nice-to-have.",
                            project_id=project_id, canvas_id="customer_research",
                        ))

            # 3. Pains
            pains = canvas_data.get("pains") or []
            if isinstance(pains, list):
                for pain in pains:
                    if isinstance(pain, str) and pain.strip():
                        assumptions.append(cls._build_assumption_item(
                            statement=f"Khách hàng gặp nỗi đau: {pain.strip()}",
                            category=AssumptionCategory.PROBLEM,
                            impact=5, uncertainty=5,
                            rationale="Nỗi đau cốt lõi quyết định mức độ sẵn sàng chuyển đổi và chi trả.",
                            project_id=project_id, canvas_id="customer_research",
                        ))

        elif canvas_type == "product_marketing":
            # Positioning
            pos = canvas_data.get("positioning")
            if isinstance(pos, dict) and pos.get("statement"):
                assumptions.append(cls._build_assumption_item(
                    statement=str(pos.get("statement")),
                    category=AssumptionCategory.POSITIONING,
                    impact=4, uncertainty=4,
                    rationale="Định vị cần được khách hàng xác nhận sự khác biệt so với giải pháp thay thế.",
                    project_id=project_id, canvas_id="product_marketing",
                ))
            elif isinstance(pos, str) and pos.strip():
                assumptions.append(cls._build_assumption_item(
                    statement=pos.strip(),
                    category=AssumptionCategory.POSITIONING,
                    impact=4, uncertainty=4,
                    rationale="Định vị giả định cần được kiểm chứng thông điệp.",
                    project_id=project_id, canvas_id="product_marketing",
                ))

            # Value proposition
            vp = canvas_data.get("value_proposition")
            if isinstance(vp, dict) and vp.get("core_value"):
                assumptions.append(cls._build_assumption_item(
                    statement=str(vp.get("core_value")),
                    category=AssumptionCategory.VALUE_PROPOSITION,
                    impact=5, uncertainty=4,
                    rationale="Giá trị cốt lõi phải giải quyết trực tiếp pain point của ICP.",
                    project_id=project_id, canvas_id="product_marketing",
                ))

        elif canvas_type == "offer_architecture":
            # Pricing & Offer
            pricing = canvas_data.get("pricing")
            if pricing:
                price_str = pricing.get("model") or pricing.get("price") or str(pricing)
                assumptions.append(cls._build_assumption_item(
                    statement=f"Khách hàng chấp nhận mức giá và mô hình: {price_str}",
                    category=AssumptionCategory.PRICING,
                    impact=5, uncertainty=5,
                    rationale="Willingness-to-pay là rủi ro chí mạng, cần kiểm chứng trước khi scale chi phí.",
                    project_id=project_id, canvas_id="offer_architecture",
                ))

            # Core Offer
            core_offer = canvas_data.get("core_offer") or canvas_data.get("offer")
            if isinstance(core_offer, str) and core_offer.strip():
                assumptions.append(cls._build_assumption_item(
                    statement=f"Gói ưu đãi cốt lõi hấp dẫn khách hàng: {core_offer.strip()}",
                    category=AssumptionCategory.OFFER,
                    impact=4, uncertainty=3,
                    rationale="Offer cần đủ sức thuyết phục và giảm rủi ro cảm nhận cho khách hàng.",
                    project_id=project_id, canvas_id="offer_architecture",
                ))

        assumptions.sort(key=lambda a: a["criticality"], reverse=True)
        return assumptions

    # --- Internal Helpers ---

    @staticmethod
    def _build_assumption_item(
        statement: str,
        category: AssumptionCategory,
        impact: int,
        uncertainty: int,
        rationale: str,
        project_id: Optional[int] = None,
        canvas_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        criticality = AssumptionService.calculate_criticality(impact, uncertainty)
        return {
            "statement": statement,
            "category": category.value,
            "impact": impact,
            "uncertainty": uncertainty,
            "criticality": criticality,
            "confidence": ConfidenceLevel.LOW.value,
            "status": AssumptionStatus.UNTESTED.value,
            "rationale": rationale,
            "project_id": project_id,
            "canvas_id": canvas_id,
            "should_test": criticality >= 9,
        }

    @staticmethod
    def _classify_epistemic_status(sentence: str) -> EpistemicStatus:
        s = sentence.lower()
        # Nếu có số liệu đo lường cụ thể hoặc thời gian đo trực tiếp
        if re.search(r"\b(\d+\s*(lượt|người|khách|đơn|%|vnd|usd|triệu|leads?|cvr|cac|roas))\b", s):
            return EpistemicStatus.FACT
        # Nếu là kết luận suy đoán
        if any(w in s for w in ("có thể", "dường như", "suy ra", "cho thấy", "có khả năng")):
            return EpistemicStatus.INFERENCE
        # Mặc định là assumption (§5: AI-generated != Validated)
        return EpistemicStatus.ASSUMPTION

    @staticmethod
    def _detect_category(sentence: str) -> AssumptionCategory:
        s = sentence.lower()
        if any(w in s for w in ("giá", "trả tiền", "phí", "pricing", "gói", "subscription", "thanh toán", "willingness")):
            return AssumptionCategory.PRICING
        if any(w in s for w in ("khách hàng", "icp", "founder", "doanh nghiệp", "sme", "người dùng", "chủ")):
            return AssumptionCategory.CUSTOMER
        if any(w in s for w in ("nỗi đau", "khó khăn", "vấn đề", "pain", "problem", "tắc nghẽn")):
            return AssumptionCategory.PROBLEM
        if any(w in s for w in ("giải pháp", "tính năng", "công cụ", "nền tảng", "ai local", "hệ thống", "solution")):
            return AssumptionCategory.SOLUTION
        if any(w in s for w in ("định vị", "khác biệt", "thông điệp", "positioning", "messaging")):
            return AssumptionCategory.POSITIONING
        if any(w in s for w in ("ưu đãi", "offer", "bonus", "quà", "bảo hành", "guarantee")):
            return AssumptionCategory.OFFER
        if any(w in s for w in ("kênh", "quảng cáo", "ads", "facebook", "google", "tiktok", "zalo", "channel", "phân phối")):
            return AssumptionCategory.CHANNEL
        if any(w in s for w in ("chuyển đổi", "đăng ký", "conversion", "cvr", "landing")):
            return AssumptionCategory.CONVERSION
        if any(w in s for w in ("giữ chân", "retention", "rời bỏ", "churn", "lặp lại")):
            return AssumptionCategory.RETENTION
        return AssumptionCategory.VALUE_PROPOSITION

    @staticmethod
    def _score_impact_and_uncertainty(sentence: str, category: AssumptionCategory) -> tuple[int, int, str]:
        # Customer pain & Pricing have highest impact & uncertainty by default (§14, §18)
        if category in (AssumptionCategory.PRICING, AssumptionCategory.PROBLEM, AssumptionCategory.CUSTOMER):
            return 5, 5, "Giả định cốt lõi về khách hàng, nỗi đau hoặc khả năng chi trả. Nếu sai sẽ làm hỏng toàn bộ mô hình."
        if category in (AssumptionCategory.SOLUTION, AssumptionCategory.VALUE_PROPOSITION, AssumptionCategory.POSITIONING):
            return 4, 4, "Giả định quan trọng về sản phẩm và định vị thị trường."
        if category in (AssumptionCategory.CHANNEL, AssumptionCategory.OFFER):
            return 4, 3, "Giả định về kênh phân phối và cấu trúc gói chào hàng."
        return 3, 3, "Giả định vận hành hoặc tối ưu hóa."
