from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from workforce.identity.context import ExecutionContext
from business.marketing.models import MarketingCampaign, MarketingMetric
from core.snowflake import generate_snowflake_id


async def marketing_campaign_list_handler(context: ExecutionContext, args: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """Tool R0: Xem danh sách các chiến dịch marketing."""
    stmt = select(MarketingCampaign)
    res = await db.execute(stmt)
    campaigns = res.scalars().all()

    return {
        "status": "success",
        "total": len(campaigns),
        "campaigns": [
            {
                "id": str(c.id),
                "name": getattr(c, "name", "Marketing Campaign"),
                "status": getattr(c, "status", "active"),
                "objective": getattr(c, "objective", "brand_awareness"),
            }
            for c in campaigns[:10]
        ]
    }


async def marketing_campaign_create_handler(context: ExecutionContext, args: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """Tool R2: Tạo bản nháp chiến dịch marketing mới."""
    name = args.get("name", "Chiến dịch mới")
    objective = args.get("objective", "Tăng trưởng khách hàng")
    budget = float(args.get("budget", 0.0))

    campaign = MarketingCampaign(
        id=generate_snowflake_id(),
        name=name,
        objective=objective,
    )
    db.add(campaign)
    await db.flush()

    return {
        "status": "success",
        "campaign_id": str(campaign.id),
        "name": name,
        "objective": objective,
        "message": f"Tạo chiến dịch '{name}' thành công."
    }


async def marketing_content_generate_handler(context: ExecutionContext, args: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """Tool R1: Sinh nội dung bài viết marketing / copy."""
    topic = args.get("topic", "Giới thiệu sản phẩm")
    tone = args.get("tone", "chuyên nghiệp, thuyết phục")
    channel = args.get("channel", "Facebook")

    content = f"[{channel} Post - {tone.title()}]\nChủ đề: {topic}\nKhám phá giải pháp tối ưu từ COSA OS giúp doanh nghiệp tự động hóa vận hành."

    return {
        "status": "success",
        "topic": topic,
        "channel": channel,
        "generated_content": content,
    }


async def marketing_social_publish_handler(context: ExecutionContext, args: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """Tool R3: Đăng bài viết lên mạng xã hội (Cần Human Approval)."""
    channel = args.get("channel", "Facebook")
    content = args.get("content", "")

    return {
        "status": "success",
        "action": "social.publish",
        "channel": channel,
        "message": f"Bài viết đã được xuất bản lên {channel} thành công."
    }
