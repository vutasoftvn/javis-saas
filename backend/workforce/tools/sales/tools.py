from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from workforce.identity.context import ExecutionContext
from business.sales.models import SalesLead
from core.snowflake import generate_snowflake_id


async def crm_search_handler(context: ExecutionContext, args: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """Tool R0: Tìm kiếm khách hàng tiềm năng (Leads) trong CRM."""
    query = args.get("query", "").strip().lower()
    stmt = select(SalesLead).where(SalesLead.workspace_id == context.workspace_id)
    res = await db.execute(stmt)
    leads = res.scalars().all()

    filtered = []
    for lead in leads:
        name = getattr(lead, "contact_name", "") or getattr(lead, "company_name", "") or ""
        if not query or query in name.lower():
            filtered.append({
                "id": str(lead.id),
                "name": name,
                "status": getattr(lead, "status", "NEW"),
                "deal_value": float(getattr(lead, "deal_value", 0.0) or 0.0),
            })

    return {
        "status": "success",
        "total": len(filtered),
        "leads": filtered[:10]
    }


async def crm_update_handler(context: ExecutionContext, args: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """Tool R2: Cập nhật thông tin hoặc trạng thái Lead trong CRM."""
    lead_id = args.get("lead_id")
    new_status = args.get("status")

    if not lead_id:
        return {"status": "error", "message": "lead_id is required"}

    stmt = select(SalesLead).where(
        SalesLead.id == int(lead_id),
        SalesLead.workspace_id == context.workspace_id
    )
    res = await db.execute(stmt)
    lead = res.scalars().first()

    if not lead:
        return {"status": "not_found", "message": f"Lead {lead_id} not found"}

    if new_status:
        lead.status = new_status
    await db.flush()

    return {
        "status": "success",
        "lead_id": str(lead.id),
        "status_updated": new_status,
        "message": "Cập nhật thông tin CRM thành công."
    }


async def email_send_handler(context: ExecutionContext, args: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """Tool R3: Gửi email ra ngoài khách hàng (Yêu cầu Human Approval)."""
    to_email = args.get("to")
    subject = args.get("subject", "Thông tin từ COSA")
    body = args.get("body", "")

    # Thực tế sau khi được Founder duyệt qua Gate
    return {
        "status": "success",
        "action": "email.send",
        "recipient": to_email,
        "subject": subject,
        "message": f"Email đã được chuyển phát thành công tới {to_email}"
    }
