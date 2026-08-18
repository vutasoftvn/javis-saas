from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.workforce.identity.context import ExecutionContext
from app.platform.license.models import Blocker, Handoff
from app.core.snowflake import generate_snowflake_id


async def runtime_blocker_create_handler(context: ExecutionContext, args: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """Tool R2: Báo cáo điểm nghẽn (Blocker) trong vận hành."""
    title = args.get("title", "Điểm nghẽn vận hành")
    impact = args.get("impact", "high")
    description = args.get("description", "")

    blocker = Blocker(
        id=generate_snowflake_id(),
        workspace_id=context.workspace_id,
        title=title,
        status="open",
    )
    db.add(blocker)
    await db.flush()

    return {
        "status": "success",
        "blocker_id": str(blocker.id),
        "title": title,
        "message": f"Ghi nhận điểm nghẽn '{title}' thành công."
    }


async def runtime_handoff_create_handler(context: ExecutionContext, args: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """Tool R2: Tạo phiên bàn giao công việc (Handoff)."""
    to_agent = args.get("to_agent", "sales")
    summary = args.get("summary", "Bàn giao công việc")

    handoff = Handoff(
        id=generate_snowflake_id(),
        workspace_id=context.workspace_id,
        summary=summary,
        status="pending",
    )
    db.add(handoff)
    await db.flush()

    return {
        "status": "success",
        "handoff_id": str(handoff.id),
        "to_agent": to_agent,
        "summary": summary,
        "message": f"Tạo bàn giao công việc sang '{to_agent}' thành công."
    }
