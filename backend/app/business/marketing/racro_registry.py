"""
COSA RACRO Domain Registry & Mapping Specification.
Tuân thủ đặc tả COSA_AI_Marketing_System_Integration_Spec.md:
Business Capability > Skill > Workflow > Tool.
"""

from enum import Enum
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class RACROMove(str, Enum):
    RESEARCH = "research"
    ATTRACT = "attract"
    CONVERT = "convert"
    RETAIN = "retain"
    ORCHESTRATE = "orchestrate"


class RACROAction(str, Enum):
    KEEP = "keep"
    REFACTOR = "refactor"
    MERGE = "merge"
    HIDE_FROM_FOUNDER = "hide_from_founder"
    DEPRECATE = "deprecate"


class RACROCapabilityMapping(BaseModel):
    capability_id: str
    move: RACROMove
    name: str
    description: str
    canonical_entities: List[str]
    action: RACROAction
    primary_skills: List[str] = Field(default_factory=list)
    tool_adapters: List[str] = Field(default_factory=list)


# Bảng Registry chuẩn hóa toàn bộ 15 Capabilities thuộc 5 Khối RACRO
RACRO_CAPABILITY_REGISTRY: Dict[str, RACROCapabilityMapping] = {
    # --- 1. RESEARCH ---
    "market_intelligence": RACROCapabilityMapping(
        capability_id="market_intelligence",
        move=RACROMove.RESEARCH,
        name="Market Intelligence",
        description="Nghiên cứu quy mô thị trường, phân khúc khách hàng, ICP, Jobs-to-be-Done và xu hướng.",
        canonical_entities=["MarketingContext", "EvidenceItem", "Assumption"],
        action=RACROAction.REFACTOR,
        primary_skills=["market_intelligence", "icp_discovery"],
        tool_adapters=["web_search", "google_trends", "industry_reports"]
    ),
    "competitor_intelligence": RACROCapabilityMapping(
        capability_id="competitor_intelligence",
        move=RACROMove.RESEARCH,
        name="Competitor Intelligence",
        description="Theo dõi giá, offer, landing page, content, SEO và động thái của đối thủ cạnh tranh.",
        canonical_entities=["MarketingContext", "EvidenceItem"],
        action=RACROAction.REFACTOR,
        primary_skills=["competitor_intelligence"],
        tool_adapters=["web_search", "competitor_crawler", "social_listening"]
    ),
    "demand_intelligence": RACROCapabilityMapping(
        capability_id="demand_intelligence",
        move=RACROMove.RESEARCH,
        name="Demand Intelligence",
        description="Thu thập và phân tích các tín hiệu nhu cầu thực tế từ tìm kiếm, mạng xã hội và CRM.",
        canonical_entities=["MarketingSignal", "EvidenceItem"],
        action=RACROAction.REFACTOR,
        primary_skills=["demand_intelligence", "signal_detection"],
        tool_adapters=["search_trends", "crm_signals", "social_listening"]
    ),

    # --- 2. ATTRACT ---
    "search_discovery": RACROCapabilityMapping(
        capability_id="search_discovery",
        move=RACROMove.ATTRACT,
        name="Search & Discovery",
        description="Tối ưu khả năng tìm thấy qua SEO, Local SEO, Google Business Profile và các nền tảng phân phối.",
        canonical_entities=["CampaignAsset", "MarketingContext"],
        action=RACROAction.KEEP,
        primary_skills=["search_discovery", "local_seo"],
        tool_adapters=["google_business", "seo_analyzer"]
    ),
    "content_creative": RACROCapabilityMapping(
        capability_id="content_creative",
        move=RACROMove.ATTRACT,
        name="Content & Creative",
        description="Sản xuất nội dung, content pillars, bài viết, video/image briefs dựa trên Demand Signals.",
        canonical_entities=["CampaignAsset", "MarketingCampaign"],
        action=RACROAction.KEEP,
        primary_skills=["content_creative", "copywriting"],
        tool_adapters=["llm_content_generator", "media_formatter"]
    ),
    "distribution": RACROCapabilityMapping(
        capability_id="distribution",
        move=RACROMove.ATTRACT,
        name="Distribution",
        description="Phân phối nội dung đa kênh (Facebook, Zalo, Email, Website...) theo cấu hình công ty.",
        canonical_entities=["CampaignAsset", "MarketingCampaign"],
        action=RACROAction.REFACTOR,
        primary_skills=["distribution", "channel_publisher"],
        tool_adapters=["social_publisher", "email_sender", "zalo_adapter"]
    ),

    # --- 3. CONVERT ---
    "campaign_offer": RACROCapabilityMapping(
        capability_id="campaign_offer",
        move=RACROMove.CONVERT,
        name="Campaign & Offer",
        description="Thiết kế chiến dịch, cấu trúc ưu đãi (offer) và landing page chuyển đổi cao.",
        canonical_entities=["MarketingCampaign", "CampaignAsset", "LandingDeployment"],
        action=RACROAction.KEEP,
        primary_skills=["campaign_offer", "landing_page_builder"],
        tool_adapters=["nextjs_app_generator", "form_builder"]
    ),
    "speed_to_lead": RACROCapabilityMapping(
        capability_id="speed_to_lead",
        move=RACROMove.CONVERT,
        name="Speed-to-Lead",
        description="Tự động tiếp nhận và phản hồi lead tức thì (dưới 5 phút) để tối đa hóa tỷ lệ chuyển đổi.",
        canonical_entities=["SalesLead", "Contact"],
        action=RACROAction.MERGE,
        primary_skills=["speed_to_lead_check", "instant_responder"],
        tool_adapters=["zalo_bot", "telegram_bot", "email_responder", "webhook_adapter"]
    ),
    "intake_qualification": RACROCapabilityMapping(
        capability_id="intake_qualification",
        move=RACROMove.CONVERT,
        name="Intake & Qualification",
        description="Chuẩn hóa, lọc trùng, chấm điểm tiềm năng (lead score) và định tuyến vào Sales CRM.",
        canonical_entities=["SalesLead", "SalesOpportunity"],
        action=RACROAction.KEEP,
        primary_skills=["intake_qualification", "lead_scoring"],
        tool_adapters=["crm_pipeline_adapter"]
    ),

    # --- 4. RETAIN ---
    "follow_up": RACROCapabilityMapping(
        capability_id="follow_up",
        move=RACROMove.RETAIN,
        name="Follow-Up & Playbooks",
        description="Chăm sóc và tái kích hoạt khách hàng tự động dựa trên trạng thái vòng đời CRM.",
        canonical_entities=["SalesLead", "Account", "Contact"],
        action=RACROAction.REFACTOR,
        primary_skills=["follow_up", "reactivation"],
        tool_adapters=["email_sequence", "zalo_messaging"]
    ),
    "reputation": RACROCapabilityMapping(
        capability_id="reputation",
        move=RACROMove.RETAIN,
        name="Reputation & Reviews",
        description="Thu thập phản hồi, quản lý đánh giá và biến review tích cực thành Social Proof / Evidence.",
        canonical_entities=["EvidenceItem", "MarketingLearning"],
        action=RACROAction.MERGE,
        primary_skills=["reputation", "testimonial_collector"],
        tool_adapters=["review_crawler", "feedback_form"]
    ),
    "referral": RACROCapabilityMapping(
        capability_id="referral",
        move=RACROMove.RETAIN,
        name="Referral Loops",
        description="Xây dựng vòng lặp giới thiệu khách hàng mới từ khách hàng hiện tại có gắn mã định danh nguồn.",
        canonical_entities=["SalesLead", "Contact"],
        action=RACROAction.KEEP,
        primary_skills=["referral_engine"],
        tool_adapters=["referral_link_generator"]
    ),

    # --- 5. ORCHESTRATE ---
    "marketing_planner": RACROCapabilityMapping(
        capability_id="marketing_planner",
        move=RACROMove.ORCHESTRATE,
        name="Marketing Planner",
        description="Lập kế hoạch và điều phối chiến lược tiếp thị phù hợp với giai đoạn dự án (Stage-Aware).",
        canonical_entities=["MarketingObjective", "MarketingRecommendation"],
        action=RACROAction.KEEP,
        primary_skills=["marketing_planner", "budget_optimizer"],
        tool_adapters=["strategy_bridge"]
    ),
    "attribution": RACROCapabilityMapping(
        capability_id="attribution",
        move=RACROMove.ORCHESTRATE,
        name="Attribution Engine",
        description="Theo dõi dòng tiền và quy kết doanh thu theo chuỗi Campaign -> Lead -> Customer -> Revenue.",
        canonical_entities=["MarketingMetric", "SalesOpportunity", "SalesLead"],
        action=RACROAction.REFACTOR,
        primary_skills=["attribution", "roi_calculator"],
        tool_adapters=["analytics_adapter", "finance_ledger_bridge"]
    ),
    "founder_brief": RACROCapabilityMapping(
        capability_id="founder_brief",
        move=RACROMove.ORCHESTRATE,
        name="Founder Daily Brief",
        description="Tổng hợp báo cáo nhanh Marketing Pulse và các đề xuất cần Founder phê duyệt trên Hologram Hub.",
        canonical_entities=["MarketingRecommendation", "MarketingMetric"],
        action=RACROAction.REFACTOR,
        primary_skills=["founder_brief", "pulse_generator"],
        tool_adapters=["hologram_pulse_bridge"]
    ),
}


# Danh mục Sự kiện Chuẩn (Event Model)
RACRO_EVENT_NAMES = [
    "marketing.signal.detected",
    "marketing.campaign.created",
    "marketing.content.published",
    "marketing.lead.created",
    "marketing.lead.qualified",
    "marketing.lead.responded",
    "marketing.customer.converted",
    "marketing.followup.due",
    "marketing.review.received",
    "marketing.referral.created",
    "marketing.attribution.updated",
]
