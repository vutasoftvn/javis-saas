from datetime import datetime, date
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_

logger = logging.getLogger(__name__)

from core.snowflake import generate_snowflake_id
from core.audit import write_audit_log
from business.sales.models import (
    Account,
    Contact,
    SalesLead,
    SalesOpportunity,
    SalesActivity,
    Customer,
)
from business.marketing.models import (
    MarketingContext,
    MarketingCampaign,
    CampaignAsset,
    PendingApproval,
)
from integrations.channels.models import EmailApproval, Outbox


# =========================================================================
# 1. ICP & Marketing Context
# =========================================================================

def get_icp_context(db: Session, workspace_id: int) -> Dict[str, Any]:
    """Lấy thông tin ICP, Persona, và Value Proposition hiện tại của Workspace."""
    ctx = db.query(MarketingContext).filter(
        MarketingContext.workspace_id == workspace_id
    ).first()

    if not ctx:
        return {
            "icp": {
                "target_industry": "Công nghệ & Dịch vụ B2B",
                "company_size": "10-100 nhân sự",
                "decision_maker": "Founder, CEO, COO, Trưởng phòng Kinh doanh",
                "pain_points": [
                    "Chi phí vận hành và nhân sự tăng cao",
                    "Quy trình bán hàng thủ công, thất thoát cơ hội",
                    "Thiếu báo cáo quản trị theo thời gian thực"
                ]
            },
            "brand_voice": {
                "tone": "Chuyên nghiệp, tin cậy, giải pháp trực diện",
                "values": ["Tối ưu hiệu suất", "Đồng hành lâu dài", "Minh bạch"]
            },
            "positioning": {
                "tagline": "Hệ Điều Hành Doanh Nghiệp Toàn Diện Cho Founder",
                "core_diff": "Tích hợp đa Agent tự động hóa khép kín từ Marketing đến Kế toán TT58"
            }
        }

    return {
        "icp": ctx.icp or {},
        "brand_voice": ctx.brand_voice or {},
        "positioning": ctx.positioning or {},
        "personas": ctx.personas or [],
        "value_proposition": ctx.value_proposition or {},
    }


def update_icp_context(
    db: Session,
    workspace_id: int,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Cập nhật thông tin ICP và Brand Voice."""
    ctx = db.query(MarketingContext).filter(
        MarketingContext.workspace_id == workspace_id
    ).first()

    if not ctx:
        # Get first brain if available
        brain = db.query(MarketingContext.brain_id).filter(
            MarketingContext.workspace_id == workspace_id
        ).first()
        brain_id = getattr(brain, "brain_id", None) or workspace_id

        ctx = MarketingContext(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            brain_id=brain_id,
            icp=payload.get("icp"),
            brand_voice=payload.get("brand_voice"),
            positioning=payload.get("positioning"),
            personas=payload.get("personas"),
            value_proposition=payload.get("value_proposition"),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(ctx)
    else:
        if "icp" in payload:
            ctx.icp = payload["icp"]
        if "brand_voice" in payload:
            ctx.brand_voice = payload["brand_voice"]
        if "positioning" in payload:
            ctx.positioning = payload["positioning"]
        if "personas" in payload:
            ctx.personas = payload["personas"]
        if "value_proposition" in payload:
            ctx.value_proposition = payload["value_proposition"]
        ctx.updated_at = datetime.utcnow()
        db.add(ctx)

    db.commit()
    db.refresh(ctx)
    return get_icp_context(db, workspace_id)


# =========================================================================
# 2. Campaign Management
# =========================================================================

def list_campaigns(db: Session, workspace_id: int) -> List[Dict[str, Any]]:
    """Lấy danh sách các chiến dịch Marketing đang chạy kèm thống kê."""
    campaigns = (
        db.query(MarketingCampaign)
        .filter(MarketingCampaign.workspace_id == workspace_id)
        .order_by(MarketingCampaign.created_at.desc())
        .all()
    )

    results = []
    for c in campaigns:
        lead_count = db.query(func.count(SalesLead.id)).filter(
            SalesLead.source_campaign_id == c.id
        ).scalar() or 0

        results.append({
            "id": str(c.id),
            "name": c.name,
            "funnel_stage": c.funnel_stage,
            "channels": c.channels or [],
            "budget": c.budget,
            "status": c.status,
            "owner": c.owner or "Growth Lead",
            "lead_count": lead_count,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })
    return results


def create_campaign(
    db: Session,
    workspace_id: int,
    name: str,
    funnel_stage: str = "discover",
    channels: Optional[List[str]] = None,
    budget: float = 0.0,
    owner: Optional[str] = None,
) -> Dict[str, Any]:
    """Tạo mới một chiến dịch Marketing."""
    brain = db.query(MarketingContext.brain_id).filter(
        MarketingContext.workspace_id == workspace_id
    ).first()
    brain_id = getattr(brain, "brain_id", None) or workspace_id

    campaign = MarketingCampaign(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        brain_id=brain_id,
        name=name,
        funnel_stage=funnel_stage,
        channels=channels or ["email", "landing_page"],
        budget=budget,
        status="active",
        owner=owner or "Growth Agent",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    return {
        "id": str(campaign.id),
        "name": campaign.name,
        "funnel_stage": campaign.funnel_stage,
        "status": campaign.status,
        "budget": campaign.budget,
    }


# =========================================================================
# 3. Modular Landing Page & Public Lead Ingestion
# =========================================================================

def get_or_create_landing_page(
    db: Session,
    workspace_id: int,
    slug: str = "default-landing",
) -> Dict[str, Any]:
    """Lấy hoặc khởi tạo cấu hình Modular Landing Page."""
    asset = db.query(CampaignAsset).filter(
        CampaignAsset.workspace_id == workspace_id,
        CampaignAsset.asset_type == "landing_page",
        CampaignAsset.title == slug,
    ).first()

    if not asset:
        modules = {
            "hero": {
                "headline": "Tối Ưu Hóa Vận Hành Doanh Nghiệp Với AI Agent",
                "subheadline": "Hệ điều hành tích hợp giúp Founder tự động hóa bán hàng, quản lý và kế toán TT58.",
                "cta_text": "Trải Nghiệm Ngay Miễn Phí",
            },
            "features": [
                {"title": "Cỗ Máy Doanh Thu Khép Kín", "desc": "Tự động thu thập, chấm điểm lead và soạn thảo thư chào hàng."},
                {"title": "Kế Toán TT58 Chuẩn Hóa", "desc": "Ghi sổ tự động, quản lý kho bình quân và BCTC B01/B02."},
                {"title": "CEO Command Center", "desc": "Tổng quan nhịp đập công ty và phê duyệt tác vụ 1-click."}
            ],
            "lead_form": {
                "fields": ["name", "email", "phone", "company", "message"],
                "submit_button": "Gửi Yêu Cầu Tư Vấn"
            }
        }
        return {
            "slug": slug,
            "title": "Trang Đích Giới Thiệu Giải Pháp",
            "modules": modules,
            "status": "published",
        }

    return {
        "slug": slug,
        "title": asset.title,
        "modules": asset.meta_data or {},
        "status": asset.approval_status,
    }


def ingest_public_lead(
    db: Session,
    slug: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Xử lý tiếp nhận Lead từ Public Webhook / Landing Page Form."""
    name = (payload.get("name") or "Khách hàng quan tâm").strip()
    email = (payload.get("email") or "").strip().lower()
    phone = (payload.get("phone") or "").strip()
    company_name = (payload.get("company") or "").strip()
    message = payload.get("message") or ""
    utm_source = payload.get("utm_source") or "landing_page"
    utm_campaign = payload.get("utm_campaign") or slug

    # Tìm workspace qua slug hoặc default
    asset = db.query(CampaignAsset).filter(
        CampaignAsset.asset_type == "landing_page",
        CampaignAsset.title == slug,
    ).first()

    workspace_id = asset.workspace_id if asset else None
    if not workspace_id:
        # Lấy workspace đầu tiên nếu là form demo
        first_lead = db.query(SalesLead.workspace_id).first()
        workspace_id = first_lead.workspace_id if first_lead else generate_snowflake_id()

    # 1. Tìm hoặc tạo Account
    account_id = None
    if company_name:
        account = db.query(Account).filter(
            Account.workspace_id == workspace_id,
            Account.name.ilike(company_name),
        ).first()
        if not account:
            account = Account(
                id=generate_snowflake_id(),
                workspace_id=workspace_id,
                name=company_name,
                source=utm_source,
                lifecycle_status="PROSPECT",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(account)
            db.flush()
        account_id = account.id

    # 2. Tìm hoặc tạo Contact
    contact_id = None
    if email or phone:
        contact = None
        if email:
            contact = db.query(Contact).filter(
                Contact.workspace_id == workspace_id,
                Contact.email == email,
            ).first()
        if not contact:
            contact = Contact(
                id=generate_snowflake_id(),
                workspace_id=workspace_id,
                account_id=account_id,
                name=name,
                email=email if email else None,
                phone=phone if phone else None,
                source=utm_source,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(contact)
            db.flush()
        contact_id = contact.id

    # 3. Tạo SalesLead
    # Tính điểm khởi tạo dựa trên thông tin cung cấp
    fit_score = 60.0
    if company_name and len(company_name) > 3:
        fit_score += 15.0
    if email and ("@" in email and not email.endswith("@gmail.com")):
        fit_score += 15.0
    if phone:
        fit_score += 10.0

    lead = SalesLead(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        account_id=account_id,
        contact_id=contact_id,
        name=name,
        company=company_name or "Doanh nghiệp",
        stage="NEW",
        source=utm_source,
        utm_source=utm_source,
        utm_campaign=utm_campaign,
        fit_score=min(fit_score, 100.0),
        intent_score=70.0 if message else 40.0,
        engagement_score=50.0,
        qualification_status="QUALIFIED" if fit_score >= 70 else "NURTURE",
        disqualification_reason=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    return {
        "status": "success",
        "lead_id": str(lead.id),
        "name": lead.name,
        "company": lead.company,
        "fit_score": lead.fit_score,
        "qualification_status": lead.qualification_status,
        "message": "Cảm ơn bạn đã gửi thông tin! Đội ngũ tư vấn sẽ liên hệ trong thời gian sớm nhất.",
    }


# =========================================================================
# 4. AI Lead Scoring Classifier & List
# =========================================================================

def list_crm_leads(
    db: Session,
    workspace_id: int,
    stage: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Lấy danh sách khách hàng tiềm năng kèm chỉ số AI Score."""
    q = db.query(SalesLead).filter(SalesLead.workspace_id == workspace_id)
    if stage:
        q = q.filter(SalesLead.stage == stage)

    leads = q.order_by(SalesLead.fit_score.desc().nullslast(), SalesLead.created_at.desc()).limit(limit).all()

    results = []
    for l in leads:
        contact_email = None
        contact_phone = None
        if l.contact_id:
            c = db.query(Contact).filter(Contact.id == l.contact_id).first()
            if c:
                contact_email = c.email
                contact_phone = c.phone

        results.append({
            "id": str(l.id),
            "name": l.name,
            "company": l.company or "N/A",
            "email": contact_email,
            "phone": contact_phone,
            "stage": l.stage,
            "fit_score": l.fit_score or 50.0,
            "intent_score": l.intent_score or 50.0,
            "qualification_status": l.qualification_status or "NURTURE",
            "source": l.source or "Direct",
            "created_at": l.created_at.isoformat() if l.created_at else None,
        })
    return results


def score_lead_with_ai(
    db: Session,
    workspace_id: int,
    lead_id: int,
) -> Dict[str, Any]:
    """AI Classifier phân tích dữ liệu Lead và cập nhật Fit Score & Intent Score."""
    lead = db.query(SalesLead).filter(
        SalesLead.id == lead_id,
        SalesLead.workspace_id == workspace_id,
    ).first()

    if not lead:
        raise ValueError("Lead not found in this workspace")

    # Thu thập ngữ cảnh
    company = lead.company or ""
    fit_score = 50.0

    if company and len(company) > 3:
        fit_score += 20.0

    if lead.contact_id:
        c = db.query(Contact).filter(Contact.id == lead.contact_id).first()
        if c:
            if c.email and not c.email.endswith("@gmail.com"):
                fit_score += 20.0
            if c.phone:
                fit_score += 10.0

    lead.fit_score = min(fit_score, 100.0)
    lead.intent_score = 80.0 if lead.fit_score >= 80 else 60.0
    lead.qualification_status = "QUALIFIED" if lead.fit_score >= 70 else "NURTURE"
    lead.updated_at = datetime.utcnow()

    db.add(lead)
    db.commit()
    db.refresh(lead)

    return {
        "lead_id": str(lead.id),
        "fit_score": lead.fit_score,
        "intent_score": lead.intent_score,
        "qualification_status": lead.qualification_status,
    }


# =========================================================================
# 5. Sales Opportunity Pipeline (Deal Kanban)
# =========================================================================

STAGES_ORDER = [
    ("DISCOVERY", "Khám Phá & Nhu Cầu", 0.2),
    ("PROPOSAL", "Báo Giá & Đề Xuất", 0.5),
    ("NEGOTIATION", "Đàm Phán Hợp Đồng", 0.8),
    ("WON", "Thành Công (Closed Won)", 1.0),
    ("LOST", "Thất Bại (Closed Lost)", 0.0),
]


def get_pipeline_kanban(db: Session, workspace_id: int) -> Dict[str, Any]:
    """Lấy dữ liệu toàn bộ cơ hội bán hàng theo cột Kanban."""
    opportunities = (
        db.query(SalesOpportunity)
        .filter(SalesOpportunity.workspace_id == workspace_id)
        .order_by(SalesOpportunity.created_at.desc())
        .all()
    )

    stage_map: Dict[str, List[Dict[str, Any]]] = {code: [] for code, _, _ in STAGES_ORDER}
    total_pipeline_value = 0.0
    weighted_pipeline_value = 0.0

    for opp in opportunities:
        stage = (opp.stage or "DISCOVERY").upper()
        if stage not in stage_map:
            stage = "DISCOVERY"

        val = opp.estimated_value or 0.0
        prob = opp.probability if opp.probability is not None else 0.3
        total_pipeline_value += val
        weighted_pipeline_value += (val * prob)

        # Lấy tên công ty
        company_name = "Khách hàng B2B"
        if opp.account_id:
            acc = db.query(Account.name).filter(Account.id == opp.account_id).first()
            if acc and acc.name:
                company_name = acc.name

        stage_map[stage].append({
            "id": str(opp.id),
            "title": opp.title if hasattr(opp, "title") else f"Hợp đồng {company_name}",
            "company_name": company_name,
            "product": opp.product or "Giải pháp COSA",
            "value": val,
            "probability": prob,
            "stage": stage,
            "next_action": opp.next_action or "Lên lịch trao đổi tiếp theo",
            "created_at": opp.created_at.isoformat() if opp.created_at else None,
        })

    # Render chuẩn cấu trúc stages
    stages_list = []
    for code, name, default_prob in STAGES_ORDER:
        deals = stage_map.get(code, [])
        stage_val = sum(d["value"] for d in deals)
        stages_list.append({
            "id": code,
            "name": name,
            "default_probability": default_prob,
            "deal_count": len(deals),
            "stage_value": stage_val,
            "deals": deals,
        })

    return {
        "stages": stages_list,
        "summary": {
            "total_value": total_pipeline_value,
            "weighted_value": weighted_pipeline_value,
            "total_deals": len(opportunities),
        }
    }


def convert_lead_to_opportunity(
    db: Session,
    workspace_id: int,
    user_id: int,
    lead_id: int,
    title: Optional[str] = None,
    estimated_value: float = 50000000.0,
) -> Dict[str, Any]:
    """Chuyển đổi một Lead tiềm năng thành một Opportunity trong Pipeline."""
    lead = db.query(SalesLead).filter(
        SalesLead.id == lead_id,
        SalesLead.workspace_id == workspace_id,
    ).first()

    if not lead:
        raise ValueError("Lead not found in this workspace")

    # Đảm bảo có Account
    account_id = lead.account_id
    if not account_id:
        acc = Account(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            name=lead.company or lead.name,
            lifecycle_status="OPPORTUNITY",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(acc)
        db.flush()
        account_id = acc.id
        lead.account_id = account_id

    # Tạo SalesOpportunity
    opp = SalesOpportunity(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        account_id=account_id,
        primary_contact_id=lead.contact_id,
        source_lead_id=lead.id,
        owner_id=user_id,
        stage="DISCOVERY",
        estimated_value=estimated_value,
        probability=0.2,
        product="Giải pháp Doanh nghiệp",
        next_action="Gửi bản thảo giới thiệu & đặt lịch họp",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(opp)

    lead.stage = "QUALIFIED"
    db.add(lead)
    db.commit()
    db.refresh(opp)

    return {
        "status": "success",
        "opportunity_id": str(opp.id),
        "stage": opp.stage,
        "estimated_value": opp.estimated_value,
    }


def update_opportunity_stage(
    db: Session,
    workspace_id: int,
    user_id: int,
    opportunity_id: int,
    stage: str,
    lost_reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Cập nhật Stage cơ hội bán hàng và xác suất thành công tương ứng."""
    opp = db.query(SalesOpportunity).filter(
        SalesOpportunity.id == opportunity_id,
        SalesOpportunity.workspace_id == workspace_id,
    ).first()

    if not opp:
        raise ValueError("Opportunity not found in this workspace")

    stage_clean = stage.upper().strip()
    opp.stage = stage_clean

    # Tự động cập nhật xác suất
    for code, _, prob in STAGES_ORDER:
        if code == stage_clean:
            opp.probability = prob
            break

    if stage_clean == "LOST":
        opp.lost_reason = lost_reason or "Chưa rõ lý do"

    opp.updated_at = datetime.utcnow()
    db.add(opp)
    db.commit()

    # Ghi nhận Audit Log
    write_audit_log(
        db=db,
        actor_type="user",
        actor_id=user_id,
        action="opportunity.stage_change",
        target_type="sales_opportunity",
        target_id=opportunity_id,
        metadata_jsonb={
            "workspace_id": str(workspace_id),
            "opportunity_id": str(opportunity_id),
            "stage": stage_clean,
            "lost_reason": lost_reason,
        }
    )

    return {
        "status": "success",
        "opportunity_id": str(opp.id),
        "stage": opp.stage,
        "probability": opp.probability,
    }


# =========================================================================
# 6. AI Outreach Generator & Approval Bridge
# =========================================================================

def generate_outreach_draft(
    db: Session,
    workspace_id: int,
    user_id: int,
    lead_id: int,
    channel: str = "email",
    tone: str = "professional",
    focus_pain_point: Optional[str] = None,
) -> Dict[str, Any]:
    """AI sinh bản nháp tiếp cận cá nhân hóa và đẩy vào PendingApproval/EmailApproval."""
    lead = db.query(SalesLead).filter(
        SalesLead.id == lead_id,
        SalesLead.workspace_id == workspace_id,
    ).first()

    if not lead:
        raise ValueError("Lead not found in this workspace")

    recipient_email = "khachhang@example.com"
    if lead.contact_id:
        c = db.query(Contact.email).filter(Contact.id == lead.contact_id).first()
        if c and c.email:
            recipient_email = c.email

    company_name = lead.company or "Quý Công ty"
    pain = focus_pain_point or "tối ưu hóa quy trình làm việc và tự động hóa vận hành"

    # AI Template generator
    subject = f"Giải pháp tối ưu thời gian và chi phí vận hành cho {company_name}"
    body = (
        f"Kính gửi {lead.name},\n\n"
        f"Chúng tôi nhận thấy {company_name} đang tìm kiếm giải pháp nhằm {pain}.\n\n"
        f"COSA OS cung cấp nền tảng AI Agent phối hợp khép kín, giúp doanh nghiệp cắt giảm tới 40% khối lượng công việc thủ công trong bán hàng và quản trị.\n\n"
        f"Chúng tôi có thể mời {lead.name} một buổi demo trực tiếp trong 15 phút vào tuần này để chia sẻ chi tiết hơn không?\n\n"
        f"Trân trọng,\nĐội ngũ Tăng Trưởng COSA"
    )

    # 1. Tạo EmailApproval (Để gửi qua Outbox)
    email_approval = EmailApproval(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        provider="resend",
        to_email=recipient_email,
        subject=subject,
        body=body,
        status="pending",
        created_at=datetime.utcnow(),
    )
    db.add(email_approval)

    # 2. Tạo PendingApproval (Để hiển thị đồng bộ trên Hologram Hub Command Center)
    brain = db.query(MarketingContext.brain_id).filter(
        MarketingContext.workspace_id == workspace_id
    ).first()
    brain_id = getattr(brain, "brain_id", None) or workspace_id

    pending_app = PendingApproval(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        brain_id=brain_id,
        action_type="outreach_email",
        title=f"Duyệt email tiếp cận: {lead.name} ({company_name})",
        details={
            "recipient": recipient_email,
            "subject": subject,
            "channel": channel,
            "tone": tone,
            "lead_id": str(lead.id),
            "email_approval_id": str(email_approval.id),
            "body_preview": body[:120] + "...",
        },
        status="pending",
        requested_by_agent="Sales Agent",
        created_at=datetime.utcnow(),
    )
    db.add(pending_app)
    db.commit()

    return {
        "status": "success",
        "approval_id": str(pending_app.id),
        "email_approval_id": str(email_approval.id),
        "subject": subject,
        "body_preview": body,
        "recipient": recipient_email,
        "message": "Đã tạo bản nháp tiếp cận. Tác vụ đã được đẩy vào Hàng đợi Phê duyệt của Founder.",
    }


# =========================================================================
# 7. Comprehensive Account & Partner Management
# =========================================================================

def list_crm_accounts(
    db: Session,
    workspace_id: int,
    account_type: Optional[str] = None,
    lifecycle_status: Optional[str] = None,
    search: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Lấy danh sách Khách hàng, Đối tác, Nhà cung cấp kèm thông tin người liên hệ và tags."""
    query = db.query(Account).filter(Account.workspace_id == workspace_id)

    if lifecycle_status:
        query = query.filter(Account.lifecycle_status == lifecycle_status)
    if search:
        query = query.filter(
            or_(
                Account.name.ilike(f"%{search}%"),
                Account.domain.ilike(f"%{search}%"),
                Account.industry.ilike(f"%{search}%"),
            )
        )

    accounts = query.order_by(Account.created_at.desc()).limit(limit).all()

    results = []
    for acc in accounts:
        # Lấy primary contact
        contact = (
            db.query(Contact)
            .filter(Contact.account_id == acc.id)
            .order_by(Contact.created_at.asc())
            .first()
        )
        
        # Đếm số deals & tổng giá trị
        deals = (
            db.query(SalesOpportunity)
            .filter(SalesOpportunity.account_id == acc.id)
            .all()
        )
        total_value = sum(d.estimated_value or 0.0 for d in deals)
        won_value = sum(d.estimated_value or 0.0 for d in deals if d.stage == "WON")

        tags_list = acc.tags or []
        # Filter theo tag nếu có
        if tag and tag not in tags_list:
            continue

        # Xác định category (Khách hàng vs Đối tác vs Nhà cung cấp)
        category = "CUSTOMER"
        if acc.lifecycle_status in ("PARTNER", "AGENT") or "Đối tác" in tags_list or "Partner" in tags_list:
            category = "PARTNER"
        elif acc.lifecycle_status == "VENDOR" or "Nhà cung cấp" in tags_list:
            category = "VENDOR"

        if account_type and account_type != "ALL" and category != account_type:
            continue

        results.append({
            "id": str(acc.id),
            "name": acc.name,
            "domain": acc.domain,
            "industry": acc.industry or "Doanh nghiệp",
            "size_segment": acc.size_segment or "Tiêu chuẩn",
            "country": acc.country,
            "source": acc.source or "Trực tiếp",
            "category": category,
            "lifecycle_status": acc.lifecycle_status,
            "tags": tags_list,
            "contact_name": contact.name if contact else None,
            "contact_phone": contact.phone if contact else None,
            "contact_email": contact.email if contact else None,
            "deals_count": len(deals),
            "total_deal_value": total_value,
            "won_revenue": won_value,
            "created_at": acc.created_at.isoformat() if acc.created_at else None,
        })
    return results


def create_crm_account(
    db: Session,
    workspace_id: int,
    name: str,
    category: str = "CUSTOMER",
    domain: Optional[str] = None,
    industry: Optional[str] = None,
    size_segment: Optional[str] = None,
    source: Optional[str] = None,
    lifecycle_status: Optional[str] = None,
    tags: Optional[List[str]] = None,
    contact_name: Optional[str] = None,
    contact_phone: Optional[str] = None,
    contact_email: Optional[str] = None,
) -> Dict[str, Any]:
    """Tạo mới một Khách hàng / Đối tác / Nhà cung cấp kèm người liên hệ."""
    acc_id = generate_snowflake_id()
    
    # Xác định lifecycle status mặc định theo category
    effective_status = lifecycle_status
    if not effective_status:
        if category == "PARTNER":
            effective_status = "PARTNER"
        elif category == "VENDOR":
            effective_status = "VENDOR"
        else:
            effective_status = "ACTIVE"

    tags_list = list(tags or [])
    if category == "PARTNER" and "Đối tác" not in tags_list:
        tags_list.append("Đối tác")
    elif category == "VENDOR" and "Nhà cung cấp" not in tags_list:
        tags_list.append("Nhà cung cấp")

    acc = Account(
        id=acc_id,
        workspace_id=workspace_id,
        name=name.strip(),
        domain=domain.strip() if domain else None,
        industry=industry.strip() if industry else "Công nghệ / Dịch vụ",
        size_segment=size_segment or "Tiêu chuẩn",
        source=source or "Nhập thủ công",
        lifecycle_status=effective_status,
        tags=tags_list,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(acc)

    # Tạo Contact nếu có thông tin
    if contact_name or contact_phone or contact_email:
        contact = Contact(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            account_id=acc_id,
            name=(contact_name or name).strip(),
            phone=contact_phone.strip() if contact_phone else None,
            email=contact_email.strip() if contact_email else None,
            source=source or "Nhập thủ công",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(contact)

    # Nếu là Customer và trạng thái ACTIVE, tạo luôn bản ghi Customer để quản trị sức khỏe
    if category == "CUSTOMER":
        cust = Customer(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            account_id=acc_id,
            lifecycle_status=effective_status,
            health_status="HEALTHY",
            first_purchase_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        db.add(cust)

    db.commit()
    db.refresh(acc)

    return {
        "status": "success",
        "id": str(acc.id),
        "name": acc.name,
        "category": category,
        "lifecycle_status": acc.lifecycle_status,
        "tags": acc.tags,
        "message": f"Đã thêm thành công {category.lower()} '{acc.name}'",
    }


# =========================================================================
# 8. End-to-End Revenue Pipeline Orchestration (§P2, C1/C2 Spec)
# =========================================================================

def execute_prospect_to_qualified_lead_pipeline(
    db: Session,
    workspace_id: int,
    user_id: int,
    raw_prospects: List[Dict[str, Any]],
    campaign_id: Optional[int] = None,
    generate_drafts: bool = True,
) -> Dict[str, Any]:
    """Orchestrate the End-to-End P2 Revenue Engine Flow.

    Sequence:
    1. Prospect Scoring & Qualification (SalesReasoningCapability)
    2. CRM Lead Ingestion & Upsert (SalesLead in PostgreSQL)
    3. Reality Verification of Lead state (RealityVerifier.verify_crm_lead)
    4. Outreach Draft Generation & Governance Routing (PendingApproval + EmailApproval)
    """
    from workforce.agents.domains.sales.reasoning import SalesReasoningCapability
    from workforce.agents.verification.reality_verifier import RealityVerifier

    # 1. Scoring & Qualification
    scoring_result = SalesReasoningCapability.score_prospects(raw_prospects)
    qualified = scoring_result.get("qualified_prospects", [])

    created_leads = []
    verifications = []
    approvals = []

    for item in qualified:
        # 2. Ingest into CRM
        lead_id = generate_snowflake_id()
        lead = SalesLead(
            id=lead_id,
            workspace_id=workspace_id,
            name=item.get("name", "Vô danh"),
            company=item.get("company", "Chưa rõ"),
            source="outbound_ai_prospecting",
            stage="NEW",
            qualification_status="QUALIFIED" if item.get("fit_score", 0) >= 80 else "NURTURE",
            fit_score=float(item.get("fit_score", 70)),
            source_campaign_id=campaign_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)

        # 3. Reality Verification
        v_res = RealityVerifier.verify_crm_lead(
            db=db,
            workspace_id=workspace_id,
            lead_id=lead.id,
            expected_company=lead.company,
            expected_stage="NEW",
        )
        verifications.append(v_res.model_dump())

        # 4. Generate Outreach Draft (if qualified and requested)
        draft_info = None
        if generate_drafts and item.get("fit_score", 0) >= 80:
            try:
                draft_res = generate_outreach_draft(
                    db=db,
                    workspace_id=workspace_id,
                    user_id=user_id,
                    lead_id=lead.id,
                    channel="email",
                    tone="consultative_expert",
                    focus_pain_point=item.get("recommended_angle"),
                )
                draft_info = {
                    "approval_id": draft_res.get("approval_id"),
                    "email_approval_id": draft_res.get("email_approval_id"),
                    "subject": draft_res.get("subject"),
                }
                approvals.append(draft_info)
            except Exception as e:
                logger.warning(f"Failed to generate outreach draft for lead {lead.id}: {e}")

        created_leads.append({
            "lead_id": str(lead.id),
            "name": lead.name,
            "company": lead.company,
            "fit_score": lead.fit_score,
            "qualification_status": lead.qualification_status,
            "draft": draft_info,
        })

    all_verified = all(v.get("verdict") == "VERIFIED" for v in verifications)

    return {
        "status": "success",
        "processed_count": len(raw_prospects),
        "qualified_count": len([l for l in created_leads if l["qualification_status"] == "QUALIFIED"]),
        "leads": created_leads,
        "verifications": verifications,
        "all_verified": all_verified,
        "pending_approvals_count": len(approvals),
        "summary": f"End-to-End Revenue Flow processed {len(raw_prospects)} prospects: {len(created_leads)} leads ingested, {len(approvals)} outreach approvals queued.",
    }

