from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.agent_platform.identity.context import ExecutionContext
from app.modules.vault.models import VaultDocument


async def knowledge_search_handler(context: ExecutionContext, args: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """Tool R0: Tìm kiếm tài liệu và tri thức trong Vault."""
    query = args.get("query", "").strip().lower()
    stmt = select(VaultDocument)
    res = await db.execute(stmt)
    docs = res.scalars().all()

    matched = []
    for d in docs:
        title = getattr(d, "title", "") or ""
        if not query or query in title.lower():
            matched.append({
                "id": str(d.id),
                "title": title,
                "document_type": getattr(d, "document_type", "note"),
            })

    return {
        "status": "success",
        "total_matched": len(matched),
        "documents": matched[:5]
    }


async def system_help_handler(context: ExecutionContext, args: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """Tool R0: Tra cứu thông tin hỗ trợ và hướng dẫn COSA OS."""
    topic = args.get("topic", "overview")
    return {
        "status": "success",
        "topic": topic,
        "guide": "COSA OS là hệ điều hành doanh nghiệp tích hợp đa Agent (Founder, Sales, Finance, Dev) hỗ trợ quản trị và tự động hóa."
    }
