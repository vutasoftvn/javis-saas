"""Business Domain — Nghiệp vụ Thực chiến Doanh nghiệp

Bao gồm 5 phân hệ nghiệp vụ cốt lõi:
1. Sales & CRM (Pipeline, Leads, Deals, Quản lý quan hệ khách hàng)
2. Marketing (Chiến dịch đa kênh, Content, Chuyển đổi)
3. Finance (Dòng tiền, Chi phí, Kế toán chuẩn Việt Nam)
4. Legal (Hợp đồng kinh tế, Rà soát pháp lý theo luật VN)
5. Learning (Knowledge Base, SOPs đào tạo nội bộ)
"""

from app.business.sales.models import *
from app.business.finance.models import *
from app.business.legal.models import *
from app.business.marketing.models import *
from app.business.learning.models import *
from app.business.packs.models import *

__all__ = ["sales", "marketing", "finance", "legal", "learning", "packs"]
