import uuid
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.modules.marketing.models import MarketingContext
from app.modules.strategy.models import StrategyRevision, StrategyFoundation, CoreValue

class ContextAdapter:
    """
    Context Adapter (§20, §41, §42 Progressive Context Slicing).
    Cắt lát bối cảnh chiến lược và bối cảnh Marketing thành Minimal Context Package
    phù hợp riêng cho từng Skill cụ thể.
    Giảm chi phí token, loại bỏ nhiễu, tăng độ tập trung và ngăn lộ dữ liệu nhạy cảm.
    """

    @staticmethod
    def get_minimal_context_package(
        db: Session,
        workspace_id: uuid.UUID,
        brain_id: uuid.UUID,
        capability: str
    ) -> Dict[str, Any]:
        # 1. Lấy Marketing Context mới nhất của Workspace & Brain
        mkt_context = db.query(MarketingContext).filter(
            MarketingContext.workspace_id == workspace_id,
            MarketingContext.brain_id == brain_id
        ).order_by(MarketingContext.updated_at.desc()).first()

        context_package: Dict[str, Any] = {
            "workspace_id": str(workspace_id),
            "brain_id": str(brain_id),
            "capability": capability,
            "slice_profile": "general",
        }

        if not mkt_context:
            return context_package

        # 2. Toàn bộ context data có sẵn trong Javis Core
        full_ctx = {
            "market": mkt_context.market or {},
            "category": mkt_context.category or "",
            "icp": mkt_context.icp or {},
            "personas": mkt_context.personas or [],
            "jobs_to_be_done": mkt_context.jobs_to_be_done or [],
            "positioning": mkt_context.positioning or {},
            "value_proposition": mkt_context.value_proposition or {},
            "brand_voice": mkt_context.brand_voice or {},
            "competitors": mkt_context.competitors or [],
            "pricing": mkt_context.pricing or {},
            "constraints": mkt_context.constraints or [],
            "customer_research": mkt_context.customer_research or {},
            "product_marketing": mkt_context.product_marketing or {},
            "offer_architecture": mkt_context.offer_architecture or {},
            "proofs": mkt_context.proofs or [],
            "channels": mkt_context.channels or [],
        }

        # 3. Progressive Context Slicing (§20, §42) theo họ capability
        sliced_marketing_context: Dict[str, Any] = {}
        include_strategy_foundation = False

        if capability in ("marketing.cro", "marketing.signup", "marketing.onboarding"):
            # Nhóm CRO / Chuyển đổi: chỉ cần ICP, Offer, Giá trị và Rào cản
            context_package["slice_profile"] = "conversion_cro"
            sliced_marketing_context = {
                "icp": full_ctx["icp"],
                "offer": full_ctx["offer_architecture"] or full_ctx["value_proposition"],
                "pricing": full_ctx["pricing"],
                "constraints": full_ctx["constraints"],
            }

        elif capability in ("marketing.copywriting", "marketing.content", "marketing.social", "marketing.email"):
            # Nhóm Nội dung & Copywriting: ICP, Giọng điệu, Định vị, Giá trị và Bằng chứng
            context_package["slice_profile"] = "copywriting_content"
            sliced_marketing_context = {
                "icp": full_ctx["icp"],
                "personas": full_ctx["personas"],
                "positioning": full_ctx["positioning"],
                "brand_voice": full_ctx["brand_voice"],
                "value_proposition": full_ctx["value_proposition"],
                "offer": full_ctx["offer_architecture"],
                "proofs": full_ctx["proofs"],
            }

        elif capability in ("marketing.ads", "marketing.ad_creative"):
            # Nhóm Quảng cáo trả phí: ICP, Offer, Đối thủ, Kênh và Thông điệp
            context_package["slice_profile"] = "paid_ads"
            sliced_marketing_context = {
                "icp": full_ctx["icp"],
                "offer": full_ctx["offer_architecture"],
                "value_proposition": full_ctx["value_proposition"],
                "competitors": full_ctx["competitors"],
                "channels": full_ctx["channels"],
            }

        elif capability in ("marketing.seo", "marketing.aeo"):
            # Nhóm SEO / AI Search: Ngành hàng, Đối thủ, Bằng chứng bảo chứng E-E-A-T
            context_package["slice_profile"] = "search_aeo"
            sliced_marketing_context = {
                "category": full_ctx["category"],
                "competitors": full_ctx["competitors"],
                "value_proposition": full_ctx["value_proposition"],
                "proofs": full_ctx["proofs"],
            }

        elif capability in ("marketing.research", "marketing.product", "marketing.positioning", "marketing.plan"):
            # Nhóm Chiến lược / Nghiên cứu: Nạp Foundation + Research + Product Marketing
            context_package["slice_profile"] = "strategic_research"
            include_strategy_foundation = True
            sliced_marketing_context = {
                "market": full_ctx["market"],
                "category": full_ctx["category"],
                "customer_research": full_ctx["customer_research"],
                "product_marketing": full_ctx["product_marketing"],
                "competitors": full_ctx["competitors"],
                "positioning": full_ctx["positioning"],
            }

        else:
            # Fallback: nạp bối cảnh cơ bản
            context_package["slice_profile"] = "standard"
            sliced_marketing_context = {
                "icp": full_ctx["icp"],
                "positioning": full_ctx["positioning"],
                "value_proposition": full_ctx["value_proposition"],
                "brand_voice": full_ctx["brand_voice"],
                "pricing": full_ctx["pricing"],
            }

        context_package["marketing_context"] = sliced_marketing_context

        # 4. Đính kèm Strategy Foundation (Vision, Mission, Core Values) nếu cần thiết
        if include_strategy_foundation and mkt_context.strategy_revision_id:
            revision = db.query(StrategyRevision).filter(
                StrategyRevision.id == mkt_context.strategy_revision_id
            ).first()
            if revision:
                foundation = db.query(StrategyFoundation).filter(
                    StrategyFoundation.strategy_revision_id == revision.id
                ).first()
                if foundation:
                    core_values = db.query(CoreValue).filter(
                        CoreValue.foundation_id == foundation.id
                    ).all()
                    context_package["strategy_foundation"] = {
                        "vision": foundation.vision,
                        "mission": foundation.mission,
                        "core_values": [
                            {"slot": cv.slot_no, "title": cv.title, "rule": cv.decision_rule}
                            for cv in core_values
                        ]
                    }

        return context_package

