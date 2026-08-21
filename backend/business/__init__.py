"""Business Domain — Nghiệp vụ Thực chiến Doanh nghiệp

Bao gồm 5 phân hệ nghiệp vụ cốt lõi:
1. Sales & CRM (Pipeline, Leads, Deals, Quản lý quan hệ khách hàng)
2. Marketing (Chiến dịch đa kênh, Content, Chuyển đổi)
3. Finance (Dòng tiền, Chi phí, Kế toán chuẩn Việt Nam)
4. Legal (Hợp đồng kinh tế, Rà soát pháp lý theo luật VN)
5. Learning (Knowledge Base, SOPs đào tạo nội bộ)
"""

from business.sales.models import *
from business.finance.models import *
from business.legal.models import *
from business.marketing.models import *
from business.learning.models import *
from business.packs.models import *

__all__ = ["sales", "marketing", "finance", "legal", "learning", "packs"]
