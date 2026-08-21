from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from business.marketing.models import MarketingContext
from business.marketing.models_validation import (
    Assumption,
    AssumptionStatus,
)


class CanvasEvaluatorService:
    """
    Canvas Epistemic Status Evaluator (§47 trong E3.md).
    Đánh giá trạng thái xác thực của từng Canvas:
    - draft (chưa cấu hình / thiếu dữ liệu)
    - hypothesis (đã có nội dung nhưng toàn giả định untested)
    - testing (đang có thử nghiệm hoặc phỏng vấn chạy)
    - evidence_backed (đã có bằng chứng thực tế xác thực)
    - contradicted (có bằng chứng mâu thuẫn cần founder xem lại)
    """

    @classmethod
    def evaluate_project_canvases(
        cls,
        db: Session,
        workspace_id: int,
        brain_id: int,
        project_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        # 1. Lấy Marketing Context
        query = db.query(MarketingContext).filter(
            MarketingContext.workspace_id == workspace_id,
            MarketingContext.brain_id == brain_id,
        )
        if project_id is not None:
            query = query.filter(MarketingContext.project_id == project_id)
        mkt_context = query.order_by(MarketingContext.updated_at.desc()).first()

        # 2. Lấy toàn bộ assumptions của workspace/project
        asm_query = db.query(Assumption).filter(Assumption.workspace_id == workspace_id)
        if project_id is not None:
            asm_query = asm_query.filter(Assumption.project_id == project_id)
        all_assumptions = asm_query.all()

        # Group assumptions theo canvas_id
        canvas_assumptions: Dict[str, List[Assumption]] = {
            "customer_research": [],
            "product_marketing": [],
            "offer_architecture": [],
            "brand_context": [],
        }

        for asm in all_assumptions:
            c_id = asm.canvas_id or ""
            if "customer" in c_id or asm.category in ("customer", "problem"):
                canvas_assumptions["customer_research"].append(asm)
            elif "product" in c_id or asm.category in ("positioning", "value_proposition", "solution"):
                canvas_assumptions["product_marketing"].append(asm)
            elif "offer" in c_id or asm.category in ("offer", "pricing"):
                canvas_assumptions["offer_architecture"].append(asm)
            else:
                canvas_assumptions["brand_context"].append(asm)

        canvases_status = {
            "customer_research": cls._evaluate_single_canvas(
                data=mkt_context.customer_research if mkt_context else None,
                assumptions=canvas_assumptions["customer_research"],
                canvas_name="Customer Research",
            ),
            "product_marketing": cls._evaluate_single_canvas(
                data=mkt_context.product_marketing if mkt_context else None,
                assumptions=canvas_assumptions["product_marketing"],
                canvas_name="Product Marketing & Positioning",
            ),
            "offer_architecture": cls._evaluate_single_canvas(
                data=mkt_context.offer_architecture if mkt_context else None,
                assumptions=canvas_assumptions["offer_architecture"],
                canvas_name="Offer Architecture",
            ),
            "brand_context": cls._evaluate_single_canvas(
                data=mkt_context.brand_voice if mkt_context else None,
                assumptions=canvas_assumptions["brand_context"],
                canvas_name="Brand Context & Constraints",
                is_brand=True,
            ),
        }

        return {
            "workspace_id": workspace_id,
            "brain_id": brain_id,
            "project_id": project_id,
            "canvases": canvases_status,
        }

    @classmethod
    def _evaluate_single_canvas(
        cls,
        data: Optional[Dict[str, Any]],
        assumptions: List[Assumption],
        canvas_name: str,
        is_brand: bool = False,
    ) -> Dict[str, Any]:
        has_content = bool(data and len(data) > 0)
        
        if not has_content:
            return {
                "name": canvas_name,
                "status": "draft",
                "badge_label": "Chưa cấu hình",
                "color": "grey",
                "assumptions_count": len(assumptions),
                "untested_count": 0,
                "evidence_backed_count": 0,
                "contradicted_count": 0,
            }

        if is_brand:
            return {
                "name": canvas_name,
                "status": "configured",
                "badge_label": "Đã cấu hình",
                "color": "blue",
                "assumptions_count": len(assumptions),
                "untested_count": 0,
                "evidence_backed_count": 0,
                "contradicted_count": 0,
            }

        untested = sum(1 for a in assumptions if a.status == AssumptionStatus.UNTESTED.value)
        testing = sum(1 for a in assumptions if a.status == AssumptionStatus.TESTING.value)
        supported = sum(1 for a in assumptions if a.status in (AssumptionStatus.SUPPORTED.value, AssumptionStatus.PARTIALLY_SUPPORTED.value))
        contradicted = sum(1 for a in assumptions if a.status == AssumptionStatus.CONTRADICTED.value)

        # Quyết định status theo ưu tiên
        if contradicted > 0:
            status = "contradicted"
            badge_label = f"Bị mâu thuẫn ({contradicted})"
            color = "red"
        elif testing > 0:
            status = "testing"
            badge_label = f"Đang kiểm chứng ({testing})"
            color = "amber"
        elif supported > 0 and untested == 0:
            status = "evidence_backed"
            badge_label = "Evidence-backed"
            color = "green"
        elif supported > 0:
            status = "partially_validated"
            badge_label = f"Có bằng chứng ({supported}/{len(assumptions)})"
            color = "teal"
        else:
            status = "hypothesis"
            badge_label = f"Giả định ({untested})"
            color = "orange"

        return {
            "name": canvas_name,
            "status": status,
            "badge_label": badge_label,
            "color": color,
            "assumptions_count": len(assumptions),
            "untested_count": untested,
            "testing_count": testing,
            "evidence_backed_count": supported,
            "contradicted_count": contradicted,
        }
