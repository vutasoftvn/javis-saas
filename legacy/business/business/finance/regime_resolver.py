"""Accounting Regime Resolver Engine for Multi-Regime Financial Management (TT58 & TT199)."""
from datetime import date, datetime
from typing import Dict, List, Optional, Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from business.finance.models import (
    AccountingFiscalProfile,
    AccountingProfile,
)


REGIME_TT58 = "TT58_2026"
REGIME_TT199 = "TT199_2026"

AVAILABLE_REGIMES = [
    {
        "code": REGIME_TT58,
        "title": "Thông tư 58/2026/TT-BTC",
        "jurisdiction": "VN",
        "description": "Chế độ kế toán Doanh nghiệp siêu nhỏ & Startup hạt giống (Tối giản dòng tiền thu chi).",
        "target_scale": "Micro / Seed Startup (< 10 nhân sự)",
        "book_types": ["SỔ_NHẬT_KÝ_THU_CHI", "SỔ_DOANH_THU_CHI_PHÍ", "SỔ_THEO_DÕI_CÔNG_NỢ", "BÁO_CÁO_THUẾ_TỐI_GIẢN"],
    },
    {
        "code": REGIME_TT199,
        "title": "Thông tư 199/2026/TT-BTC (Thay thế TT 133/2016)",
        "jurisdiction": "VN",
        "description": "Chế độ kế toán Doanh nghiệp Nhỏ và Vừa (SME) chuẩn mực, hệ thống tài khoản kép Nợ/Có.",
        "target_scale": "Small & Medium Enterprise (SME / Scaleup)",
        "book_types": ["SỔ_CÁI_TỔNG_HỢP", "BẢNG_CÂN_ĐỐI_KẾ_TOÁN_B01", "KẾT_QUẢ_HĐKD_B02", "LƯU_CHUYỂN_TIỀN_TỆ_B03", "THUYẾT_MINH_B09"],
    },
]

# Chuẩn hệ thống tài khoản TT58 (Tối giản)
COA_TT58: Dict[str, Dict[str, Any]] = {
    "TIEN_MAT": {"name": "Tiền mặt tồn quỹ", "type": "ASSET", "category": "CASH"},
    "TIEN_GUI": {"name": "Tiền gửi ngân hàng", "type": "ASSET", "category": "BANK"},
    "CONG_NO_PHAI_THU": {"name": "Phải thu khách hàng", "type": "ASSET", "category": "RECEIVABLE"},
    "HANG_TON_KHO": {"name": "Hàng tồn kho & Vật tư", "type": "ASSET", "category": "INVENTORY"},
    "CONG_NO_PHAI_TRA": {"name": "Phải trả người bán & Đối tác", "type": "LIABILITY", "category": "PAYABLE"},
    "VON_CHU_SO_HUU": {"name": "Vốn góp của chủ sở hữu", "type": "EQUITY", "category": "CAPITAL"},
    "DOANH_THU": {"name": "Doanh thu bán hàng & Dịch vụ", "type": "REVENUE", "category": "INCOME"},
    "CHI_PHI_HOAT_DONG": {"name": "Chi phí hoạt động doanh nghiệp", "type": "EXPENSE", "category": "OPEX"},
}

# Chuẩn hệ thống tài khoản TT199 (Hệ thống tài khoản kép SME)
COA_TT199: Dict[str, Dict[str, Any]] = {
    "111": {"name": "Tiền mặt", "type": "ASSET", "category": "CASH", "parent": None},
    "1111": {"name": "Tiền Việt Nam", "type": "ASSET", "category": "CASH", "parent": "111"},
    "112": {"name": "Tiền gửi Ngân hàng", "type": "ASSET", "category": "BANK", "parent": None},
    "1121": {"name": "Tiền gửi VND", "type": "ASSET", "category": "BANK", "parent": "112"},
    "131": {"name": "Phải thu của khách hàng", "type": "ASSET", "category": "RECEIVABLE", "parent": None},
    "152": {"name": "Nguyên liệu, vật liệu", "type": "ASSET", "category": "INVENTORY", "parent": None},
    "156": {"name": "Hàng hóa", "type": "ASSET", "category": "INVENTORY", "parent": None},
    "211": {"name": "Tài sản cố định hữu hình", "type": "ASSET", "category": "FIXED_ASSET", "parent": None},
    "331": {"name": "Phải trả cho người bán", "type": "LIABILITY", "category": "PAYABLE", "parent": None},
    "333": {"name": "Thuế và các khoản phải nộp Nhà nước", "type": "LIABILITY", "category": "TAX", "parent": None},
    "334": {"name": "Phải trả người lao động", "type": "LIABILITY", "category": "PAYROLL", "parent": None},
    "411": {"name": "Vốn đầu tư của chủ sở hữu", "type": "EQUITY", "category": "CAPITAL", "parent": None},
    "4111": {"name": "Vốn góp của chủ sở hữu", "type": "EQUITY", "category": "CAPITAL", "parent": "411"},
    "421": {"name": "Lợi nhuận sau thuế chưa phân phối", "type": "EQUITY", "category": "RETAINED_EARNINGS", "parent": None},
    "511": {"name": "Doanh thu bán hàng và cung cấp dịch vụ", "type": "REVENUE", "category": "REVENUE", "parent": None},
    "642": {"name": "Chi phí quản lý kinh doanh", "type": "EXPENSE", "category": "OPEX", "parent": None},
    "6421": {"name": "Chi phí bán hàng", "type": "EXPENSE", "category": "SALES_EXPENSE", "parent": "642"},
    "6422": {"name": "Chi phí quản lý doanh nghiệp", "type": "EXPENSE", "category": "ADMIN_EXPENSE", "parent": "642"},
    "811": {"name": "Chi phí khác", "type": "EXPENSE", "category": "OTHER_EXPENSE", "parent": None},
    "911": {"name": "Xác định kết quả kinh doanh", "type": "CLEARING", "category": "PROFIT_LOSS", "parent": None},
}


class AccountingRegimeResolver:
    """Bộ máy phân giải chế độ kế toán theo Niên độ & Ngày giao dịch."""

    @staticmethod
    def get_available_regimes() -> List[Dict[str, Any]]:
        return AVAILABLE_REGIMES

    @staticmethod
    def get_chart_of_accounts(regulation_code: str) -> Dict[str, Dict[str, Any]]:
        if regulation_code == REGIME_TT199:
            return COA_TT199
        return COA_TT58

    async def get_or_create_fiscal_profile(
        self,
        db: AsyncSession,
        workspace_id: int,
        fiscal_year: int,
        default_regulation: str = REGIME_TT58,
    ) -> AccountingFiscalProfile:
        """Lấy hoặc tự động khởi tạo Fiscal Profile cho niên độ cụ thể."""
        stmt = select(AccountingFiscalProfile).where(
            and_(
                AccountingFiscalProfile.workspace_id == workspace_id,
                AccountingFiscalProfile.fiscal_year == fiscal_year,
            )
        )
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()

        if not profile:
            # Kiểm tra xem có cấu hình gốc trong accounting_profiles không
            legacy_stmt = select(AccountingProfile).where(AccountingProfile.workspace_id == workspace_id)
            legacy_res = await db.execute(legacy_stmt)
            legacy_prof = legacy_res.scalar_one_or_none()

            reg_code = default_regulation
            mode = "TT58_MODE_1"
            if legacy_prof and "199" in getattr(legacy_prof, "mode", ""):
                reg_code = REGIME_TT199
                mode = "TT199_SME_FULL"

            profile = AccountingFiscalProfile(
                workspace_id=workspace_id,
                fiscal_year=fiscal_year,
                regulation_code=reg_code,
                mode=mode,
                status="ACTIVE",
            )
            db.add(profile)
            await db.commit()
            await db.refresh(profile)

        return profile

    async def resolve_regime_for_date(
        self,
        db: AsyncSession,
        workspace_id: int,
        transaction_date: date,
    ) -> Dict[str, Any]:
        """Phân giải chế độ kế toán cho một ngày giao dịch cụ thể."""
        year = transaction_date.year
        profile = await self.get_or_create_fiscal_profile(db, workspace_id, year)

        return {
            "workspace_id": workspace_id,
            "fiscal_year": profile.fiscal_year,
            "regulation_code": profile.regulation_code,
            "mode": profile.mode,
            "status": profile.status,
            "is_locked": profile.status in ["LOCKED", "ARCHIVED"],
            "chart_of_accounts": self.get_chart_of_accounts(profile.regulation_code),
        }

    async def list_fiscal_year_history(
        self,
        db: AsyncSession,
        workspace_id: int,
    ) -> List[Dict[str, Any]]:
        """Liệt kê toàn bộ lịch sử các niên độ và chế độ kế toán của Workspace."""
        stmt = (
            select(AccountingFiscalProfile)
            .where(AccountingFiscalProfile.workspace_id == workspace_id)
            .order_by(AccountingFiscalProfile.fiscal_year.desc())
        )
        res = await db.execute(stmt)
        profiles = res.scalars().all()

        if not profiles:
            current_year = date.today().year
            init_prof = await self.get_or_create_fiscal_profile(db, workspace_id, current_year)
            profiles = [init_prof]

        result = []
        for p in profiles:
            reg_info = next((r for r in AVAILABLE_REGIMES if r["code"] == p.regulation_code), None)
            result.append({
                "id": str(p.id),
                "fiscal_year": p.fiscal_year,
                "regulation_code": p.regulation_code,
                "regulation_title": reg_info["title"] if reg_info else p.regulation_code,
                "mode": p.mode,
                "status": p.status,
                "is_locked": p.status in ["LOCKED", "ARCHIVED"],
                "locked_at": p.locked_at.isoformat() if p.locked_at else None,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            })
        return result
