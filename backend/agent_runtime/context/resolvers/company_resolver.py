"""
COSA Company Scope Resolver
Nạp thông tin cơ cấu tổ chức và hồ sơ doanh nghiệp.
"""
from typing import Any, Dict


class CompanyScopeResolver:
    """Nạp thông tin ngữ cảnh công ty"""

    @staticmethod
    async def resolve(company_id: str, db_session: Any = None) -> Dict[str, Any]:
        return {
            "company_id": company_id,
            "company_name": "COSA Enterprise",
            "industry": "Software / B2B SaaS",
            "country": "Vietnam",
            "currency": "VND",
            "tax_model": "TT58"
        }
