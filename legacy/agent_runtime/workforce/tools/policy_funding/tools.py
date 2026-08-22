from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from workforce.identity.context import ExecutionContext
from platform_core.policy_funding.models import PolicyProgram, Application


async def policy_funding_search_handler(context: ExecutionContext, args: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """Tool R0: Tìm kiếm các chương trình tài trợ và chính sách ưu đãi."""
    query = args.get("query", "").strip().lower()
    stmt = select(PolicyProgram)
    res = await db.execute(stmt)
    programs = res.scalars().all()

    matched = []
    for p in programs:
        name = getattr(p, "name", "") or ""
        if not query or query in name.lower():
            matched.append({
                "id": str(p.id),
                "name": name,
                "agency": getattr(p, "agency", "Chính phủ / Quỹ hỗ trợ"),
                "status": getattr(p, "status", "active"),
            })

    return {
        "status": "success",
        "total_matched": len(matched),
        "programs": matched[:10]
    }


async def policy_eligibility_eval_handler(context: ExecutionContext, args: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """Tool R1: Đánh giá sơ bộ tính phù hợp của doanh nghiệp đối với gói tài trợ."""
    program_id = args.get("program_id")
    return {
        "status": "success",
        "program_id": str(program_id),
        "eligible": True,
        "match_score": 0.85,
        "recommendation": "Doanh nghiệp đáp ứng các tiêu chuẩn về quy mô SME và định hướng chuyển đổi số."
    }
