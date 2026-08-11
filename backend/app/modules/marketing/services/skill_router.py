from typing import Dict, Any, Optional, Tuple, List
from sqlalchemy.orm import Session

from app.modules.marketing.models import SkillRegistry, PendingApproval, SkillExecution
from app.modules.marketing.services.context_adapter import ContextAdapter

class SkillRouter:
    """
    Capability-based Skill Router (ADR-MKT-002, JAVIS_MARKETING_OS_V2.md).
    Routes tasks by capability ID (e.g. marketing.copywriting, marketing.cro, marketing.aeo).
    - Default Skill Core: coreyhaines31/marketingskills (Corey)
    - Specialist Extensions / Fallback: Alireza Marketing Skills, Python Analytics, Javis Native.
    Enforces human approval gates for external actions (external_write / spend).
    """
    
    DEFAULT_CAPABILITIES = {
        # 1. Foundation
        "marketing.research": {
            "title": "Nghiên cứu Khách hàng & Thị trường (Customer Research)",
            "description": "Phân tích ICP, JTBD, nỗi đau, động lực, rào cản và phân loại Fact/Hypothesis.",
            "primary": {"type": "corey_skill", "source": "corey", "skill": "customer-research"},
            "fallback": {"type": "agent_skill", "source": "alireza", "skill": "market-research"},
            "permissions": {"external_write": False, "spend": False}
        },
        "marketing.product": {
            "title": "Product Marketing & Differentiators",
            "description": "Xác định Category, giải pháp thay thế, điểm khác biệt và giá trị độc bản.",
            "primary": {"type": "corey_skill", "source": "corey", "skill": "product-marketing"},
            "fallback": {"type": "native", "source": "javis", "skill": "product-canvas"},
            "permissions": {"external_write": False, "spend": False}
        },
        "marketing.positioning": {
            "title": "Định vị Thương hiệu & Value Proposition",
            "description": "Xây dựng khung định vị thương hiệu, thông điệp cốt lõi và tuyên ngôn giá trị.",
            "primary": {"type": "corey_skill", "source": "corey", "skill": "positioning"},
            "fallback": {"type": "agent_skill", "source": "alireza", "skill": "brand-positioning"},
            "permissions": {"external_write": False, "spend": False}
        },
        "marketing.offer": {
            "title": "Kiến trúc Ưu đãi (Offer Architecture)",
            "description": "Thiết kế ưu đãi cốt lõi, bảo chứng giá trị, quà tặng kèm, cam kết và CTA.",
            "primary": {"type": "corey_skill", "source": "corey", "skill": "offers"},
            "fallback": {"type": "native", "source": "javis", "skill": "offer-canvas"},
            "permissions": {"external_write": False, "spend": False}
        },
        "marketing.plan": {
            "title": "Kế hoạch Marketing 12 Tuần (Marketing Plan)",
            "description": "Lập chiến lược kênh, danh mục chiến dịch, ngân sách và lịch trình 12 tuần.",
            "primary": {"type": "corey_skill", "source": "corey", "skill": "marketing-plan"},
            "fallback": {"type": "agent_skill", "source": "alireza", "skill": "marketing-plan"},
            "permissions": {"external_write": False, "spend": False}
        },

        # 2. Content & Search
        "marketing.content": {
            "title": "Chiến lược Nội dung (Content Strategy)",
            "description": "Xây dựng chiến lược nội dung đa kênh, lịch biên tập và trụ cột chủ đề.",
            "primary": {"type": "corey_skill", "source": "corey", "skill": "content-strategy"},
            "fallback": {"type": "agent_skill", "source": "alireza", "skill": "content-strategy"},
            "permissions": {"external_write": False, "spend": False}
        },
        "marketing.copywriting": {
            "title": "Viết Copywriting Bán hàng & Landing Page",
            "description": "Soạn thảo văn bản thuyết phục cho trang đích, quảng cáo và email.",
            "primary": {"type": "corey_skill", "source": "corey", "skill": "copywriting"},
            "fallback": {"type": "agent_skill", "source": "alireza", "skill": "copywriting"},
            "permissions": {"external_write": False, "spend": False}
        },
        "marketing.social": {
            "title": "Mạng Xã hội & Phân phối Nội dung",
            "description": "Sáng tạo bài viết mạng xã hội, thông điệp lan toả và kế hoạch phân phối.",
            "primary": {"type": "corey_skill", "source": "corey", "skill": "social"},
            "fallback": {"type": "agent_skill", "source": "alireza", "skill": "social"},
            "permissions": {"external_write": True, "spend": False}
        },
        "marketing.seo": {
            "title": "SEO Audit & Tối ưu Tìm kiếm",
            "description": "Kiểm toán kỹ thuật SEO, cấu trúc on-page, từ khoá và liên kết.",
            "primary": {"type": "corey_skill", "source": "corey", "skill": "seo-audit"},
            "fallback": {"type": "agent_skill", "source": "alireza", "skill": "seo-strategy"},
            "permissions": {"external_write": False, "spend": False}
        },
        "marketing.aeo": {
            "title": "AEO (AI Search & Citation Optimization)",
            "description": "Tối ưu hóa khả năng trích dẫn thương hiệu trên LLMs, ChatGPT, Perplexity.",
            "primary": {"type": "corey_skill", "source": "corey", "skill": "ai-seo"},
            "fallback": {"type": "agent_skill", "source": "alireza", "skill": "aeo-optimization"},
            "permissions": {"external_write": False, "spend": False}
        },

        # 3. Conversion & Growth
        "marketing.cro": {
            "title": "Tối ưu Tỷ lệ Chuyển đổi (CRO)",
            "description": "Phân tích rào cản chuyển đổi, luồng người dùng và đề xuất cải tiến UI/UX.",
            "primary": {"type": "corey_skill", "source": "corey", "skill": "cro"},
            "fallback": {"type": "agent_skill", "source": "alireza", "skill": "cro"},
            "permissions": {"external_write": False, "spend": False}
        },
        "marketing.signup": {
            "title": "Tối ưu Luồng Đăng ký (Signup Flow)",
            "description": "Giảm ma sát trong quá trình đăng ký, dùng thử và onboarding ban đầu.",
            "primary": {"type": "corey_skill", "source": "corey", "skill": "signup"},
            "fallback": {"type": "native", "source": "javis", "skill": "signup-optimization"},
            "permissions": {"external_write": False, "spend": False}
        },
        "marketing.onboarding": {
            "title": "Kích hoạt & Trải nghiệm Người dùng Mới (Onboarding)",
            "description": "Xây dựng hành trình đạt khoảnh khắc giá trị đầu tiên (Aha moment).",
            "primary": {"type": "corey_skill", "source": "corey", "skill": "onboarding"},
            "fallback": {"type": "native", "source": "javis", "skill": "onboarding-journey"},
            "permissions": {"external_write": False, "spend": False}
        },
        "marketing.email": {
            "title": "Email Lifecycle & Nurturing Sequences",
            "description": "Xây dựng các chuỗi email tự động theo vòng đời khách hàng.",
            "primary": {"type": "corey_skill", "source": "corey", "skill": "emails"},
            "fallback": {"type": "agent_skill", "source": "alireza", "skill": "email"},
            "permissions": {"external_write": True, "spend": False}
        },
        "marketing.churn": {
            "title": "Chống Rời bỏ & Giữ chân (Churn Prevention)",
            "description": "Phát hiện tín hiệu rời bỏ sớm và triển khai can thiệp giữ chân người dùng.",
            "primary": {"type": "corey_skill", "source": "corey", "skill": "churn-prevention"},
            "fallback": {"type": "native", "source": "javis", "skill": "retention-engine"},
            "permissions": {"external_write": False, "spend": False}
        },
        "marketing.referrals": {
            "title": "Giới thiệu & Lan toả (Referrals)",
            "description": "Thiết kế cơ chế giới thiệu, chương trình đối tác và động lực lan toả.",
            "primary": {"type": "corey_skill", "source": "corey", "skill": "referrals"},
            "fallback": {"type": "native", "source": "javis", "skill": "referral-program"},
            "permissions": {"external_write": False, "spend": False}
        },

        # 4. Performance & Revenue
        "marketing.ads": {
            "title": "Quản lý Quảng cáo Trả phí (Paid Ads)",
            "description": "Thiết lập cấu trúc chiến dịch quảng cáo Google Ads, Meta Ads và ngân sách.",
            "primary": {"type": "corey_skill", "source": "corey", "skill": "ads"},
            "fallback": {"type": "agent_skill", "source": "alireza", "skill": "ads"},
            "permissions": {"external_write": True, "spend": True}
        },
        "marketing.ad_creative": {
            "title": "Sáng tạo Mẫu Quảng cáo (Ad Creatives)",
            "description": "Sáng tạo kịch bản, headline, visual concept và biến thể A/B cho quảng cáo.",
            "primary": {"type": "corey_skill", "source": "corey", "skill": "ad-creative"},
            "fallback": {"type": "agent_skill", "source": "alireza", "skill": "ad-copy"},
            "permissions": {"external_write": False, "spend": False}
        },
        "marketing.pricing": {
            "title": "Chiến lược Giá & Đóng gói (Pricing & Packaging)",
            "description": "Phân tích mô hình định giá, gói dịch vụ và mức độ sẵn sàng chi trả.",
            "primary": {"type": "corey_skill", "source": "corey", "skill": "pricing"},
            "fallback": {"type": "native", "source": "javis", "skill": "pricing-strategy"},
            "permissions": {"external_write": True, "spend": False}
        },
        "marketing.sales_enablement": {
            "title": "Tài liệu Hỗ trợ Bán hàng (Sales Enablement)",
            "description": "Battlecards, case studies, bản trình bày giải pháp và bảng so sánh đối thủ.",
            "primary": {"type": "corey_skill", "source": "corey", "skill": "sales-enablement"},
            "fallback": {"type": "native", "source": "javis", "skill": "sales-collateral"},
            "permissions": {"external_write": False, "spend": False}
        },
        "marketing.revops": {
            "title": "Vận hành Doanh thu (RevOps)",
            "description": "Tối ưu hóa pipeline bán hàng, chuyển giao lead từ Marketing sang Sales.",
            "primary": {"type": "corey_skill", "source": "corey", "skill": "revops"},
            "fallback": {"type": "native", "source": "javis", "skill": "revops-pipeline"},
            "permissions": {"external_write": False, "spend": False}
        },
        "marketing.prospecting": {
            "title": "Tìm kiếm & Khai thác Khách hàng Tiềm năng (Prospecting)",
            "description": "Xác định danh sách mục tiêu B2B, kịch bản tiếp cận và thông điệp cá nhân hoá.",
            "primary": {"type": "corey_skill", "source": "corey", "skill": "prospecting"},
            "fallback": {"type": "native", "source": "javis", "skill": "lead-sourcing"},
            "permissions": {"external_write": False, "spend": False}
        },

        # 5. Measurement & Agentic Loops
        "marketing.analytics": {
            "title": "Phân tích Chỉ số Hiệu quả (Deterministic Analytics)",
            "description": "Tính toán CAC, LTV, ROAS, Funnel drop-offs và Cohort bằng Python.",
            "primary": {"type": "python_engine", "source": "javis_python", "skill": "metrics-calculator"},
            "fallback": {"type": "corey_skill", "source": "corey", "skill": "analytics"},
            "permissions": {"external_write": False, "spend": False}
        },
        "marketing.attribution": {
            "title": "Mô hình Phân bổ Chuyển đổi (Attribution Engine)",
            "description": "Phân tích đa chạm First-touch, Last-touch, Linear và Time-decay.",
            "primary": {"type": "python_engine", "source": "javis_python", "skill": "attribution-engine"},
            "fallback": {"type": "corey_skill", "source": "corey", "skill": "attribution"},
            "permissions": {"external_write": False, "spend": False}
        },
        "marketing.experiment": {
            "title": "Thử nghiệm A/B & Kiểm định Thống kê Z-Test",
            "description": "Thiết lập giả thuyết, chạy thử nghiệm A/B và tính toán độ tin cậy thống kê.",
            "primary": {"type": "native", "source": "javis_analytics", "skill": "z-test-evaluator"},
            "fallback": {"type": "corey_skill", "source": "corey", "skill": "ab-testing"},
            "permissions": {"external_write": False, "spend": False}
        },
        "marketing.loops": {
            "title": "Vòng lặp Marketing Khép kín (Marketing Loops)",
            "description": "Tự động hóa chu kỳ Content Loop, Paid Ads Loop, Conversion Loop, Retention Loop.",
            "primary": {"type": "corey_skill", "source": "corey", "skill": "marketing-loops"},
            "fallback": {"type": "native", "source": "javis", "skill": "growth-loops"},
            "permissions": {"external_write": True, "spend": False}
        }
    }

    # Tên gọi cũ/đồng nghĩa map về capability chuẩn.
    CAPABILITY_ALIASES = {
        "marketing.paid_ads": "marketing.ads",
        "marketing.social.publish": "marketing.social",
        "marketing.churn_prevention": "marketing.churn",
        "marketing.ab_testing": "marketing.experiment",
    }

    @classmethod
    def canonical_capability_id(cls, capability_id: str) -> str:
        return cls.CAPABILITY_ALIASES.get(capability_id, capability_id)

    @classmethod
    def list_capabilities(cls, db: Session, workspace_id: int) -> List[Dict[str, Any]]:
        registries = db.query(SkillRegistry).filter(
            SkillRegistry.workspace_id == workspace_id,
            SkillRegistry.is_active == True
        ).all()
        
        custom_map = {r.capability_id: r for r in registries}
        
        results = []
        for cap_id, def_config in cls.DEFAULT_CAPABILITIES.items():
            if cap_id in custom_map:
                r = custom_map[cap_id]
                results.append({
                    "capability_id": r.capability_id,
                    "title": def_config.get("title", cap_id),
                    "description": def_config.get("description", ""),
                    "primary": r.primary_provider,
                    "fallback": r.fallback_provider,
                    "permissions": r.permissions
                })
            else:
                results.append({
                    "capability_id": cap_id,
                    "title": def_config.get("title", cap_id),
                    "description": def_config.get("description", ""),
                    "primary": def_config["primary"],
                    "fallback": def_config.get("fallback"),
                    "permissions": def_config.get("permissions", {})
                })
        return results

    @classmethod
    def resolve_capability(
        cls,
        db: Session,
        workspace_id: int,
        capability_id: str
    ) -> Dict[str, Any]:
        capability_id = cls.canonical_capability_id(capability_id)
        registry = db.query(SkillRegistry).filter(
            SkillRegistry.workspace_id == workspace_id,
            SkillRegistry.capability_id == capability_id,
            SkillRegistry.is_active == True
        ).first()

        if registry:
            # Registry chỉ ghi đè provider/permission; tiêu đề mô tả vẫn lấy từ catalog mặc
            # định để thông báo phê duyệt không bị rơi về mã capability trơ trọi.
            defaults = cls.DEFAULT_CAPABILITIES.get(capability_id, {})
            return {
                "capability_id": registry.capability_id,
                "title": defaults.get("title", registry.capability_id),
                "description": defaults.get("description", ""),
                "primary": registry.primary_provider,
                "fallback": registry.fallback_provider,
                "permissions": registry.permissions or {}
            }

        default_config = cls.DEFAULT_CAPABILITIES.get(capability_id, {
            "title": capability_id,
            "description": "Skill tự động theo yêu cầu",
            "primary": {"type": "native", "source": "javis", "skill": capability_id},
            "fallback": None,
            "permissions": {"external_write": False, "spend": False}
        })
        return {
            "capability_id": capability_id,
            "title": default_config.get("title", capability_id),
            "description": default_config.get("description", ""),
            "primary": default_config["primary"],
            "fallback": default_config.get("fallback"),
            "permissions": default_config.get("permissions", {})
        }

    @classmethod
    def execute_or_enqueue_approval(
        cls,
        db: Session,
        workspace_id: int,
        brain_id: int,
        capability_id: str,
        task_input: Dict[str, Any],
        requested_by_agent: str = "Marketing Director"
    ) -> Tuple[str, Dict[str, Any]]:
        cap_info = cls.resolve_capability(db, workspace_id, capability_id)
        capability_id = cap_info["capability_id"]
        permissions = cap_info.get("permissions", {})

        requires_approval = permissions.get("external_write", False) or permissions.get("spend", False)

        if requires_approval:
            approval = PendingApproval(
                workspace_id=workspace_id,
                brain_id=brain_id,
                action_type=capability_id,
                title=f"Thực thi {cap_info.get('title', capability_id)}: {task_input.get('title', 'Tác vụ Marketing')}",
                details={
                    "task_input": task_input,
                    "provider": cap_info["primary"],
                    "permissions": permissions
                },
                status="pending",
                requested_by_agent=requested_by_agent
            )
            db.add(approval)
            db.commit()
            db.refresh(approval)
            
            return "pending_approval", {
                "approval_id": str(approval.id),
                "message": f"Hành động '{cap_info.get('title', capability_id)}' có tác động ra bên ngoài và yêu cầu Người dùng phê duyệt trước khi thực thi.",
                "capability_id": capability_id
            }
            
        return "executed", cls._run_capability(
            db=db,
            workspace_id=workspace_id,
            brain_id=brain_id,
            cap_info=cap_info,
            task_input=task_input,
            requested_by_agent=requested_by_agent,
        )

    @classmethod
    def _run_capability(
        cls,
        db: Session,
        workspace_id: int,
        brain_id: int,
        cap_info: Dict[str, Any],
        task_input: Dict[str, Any],
        requested_by_agent: str,
        approval_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Nạp context tối thiểu, ghi SkillExecution (§25) và trả kết quả.

        Runtime provider (OpenClaw / Alireza / Python) CHƯA được đấu nối - xem
        docs/architecture/MARKETING_OS_GAP_ANALYSIS.md giai đoạn B. Vì vậy bản ghi mang
        trạng thái `simulated` và output nói rõ điều đó; tuyệt đối không báo "đã thực thi
        thành công" cho một việc chưa chạy ở đâu cả.
        """
        capability_id = cap_info["capability_id"]
        context_pack = ContextAdapter.get_minimal_context_package(db, workspace_id, brain_id, capability_id)
        provider = cap_info["primary"]

        output = {
            "capability_id": capability_id,
            "title": cap_info.get("title", capability_id),
            "provider_used": provider,
            "context_injected": bool(context_pack.get("marketing_context")),
            "context_keys": sorted(context_pack.keys()),
            "runtime_bound": False,
            "message": (
                f"Kernel đã định tuyến '{cap_info.get('title', capability_id)}' tới provider "
                f"'{provider.get('source')}' ({provider.get('type')}). Runtime thi hành chưa được "
                f"đấu nối nên chưa có kết quả nội dung thật."
            ),
        }

        execution = SkillExecution(
            workspace_id=workspace_id,
            brain_id=brain_id,
            approval_id=approval_id,
            capability_id=capability_id,
            provider=provider,
            task_input=task_input,
            output=output,
            status="simulated",
            requested_by_agent=requested_by_agent,
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)

        return {**output, "execution_id": str(execution.id), "status": execution.status}

    @classmethod
    def execute_approved_action(
        cls,
        db: Session,
        approval: PendingApproval,
    ) -> Dict[str, Any]:
        """Chạy hành động sau khi con người bấm duyệt.

        Đây là mắt xích còn thiếu của §20: trước đây duyệt xong chỉ đổi trạng thái bản ghi
        và không có gì được thi hành. Người duyệt phải là người quyết định thời điểm chạy.
        """
        cap_info = cls.resolve_capability(db, approval.workspace_id, approval.action_type)
        details = approval.details or {}
        return cls._run_capability(
            db=db,
            workspace_id=approval.workspace_id,
            brain_id=approval.brain_id,
            cap_info=cap_info,
            task_input=details.get("task_input", {}),
            requested_by_agent=approval.requested_by_agent or "Marketing Director",
            approval_id=approval.id,
        )

    @classmethod
    def list_executions(
        cls,
        db: Session,
        workspace_id: int,
        brain_id: int,
        limit: int = 50,
    ) -> List[SkillExecution]:
        return db.query(SkillExecution).filter(
            SkillExecution.workspace_id == workspace_id,
            SkillExecution.brain_id == brain_id,
        ).order_by(SkillExecution.created_at.desc()).limit(limit).all()
