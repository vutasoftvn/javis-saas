"""Unit tests for Multi-Regime Accounting Engine (TT58 & TT199) and Fiscal Period Transition."""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from app.business.finance.regime_resolver import (
    AccountingRegimeResolver,
    REGIME_TT58,
    REGIME_TT199,
    COA_TT58,
    COA_TT199,
)
from app.business.finance.transition_engine import AccountingTransitionEngine
from app.business.finance.models import AccountingFiscalProfile


@pytest.mark.asyncio
async def test_regime_resolver_available_regimes_and_coa():
    resolver = AccountingRegimeResolver()
    regimes = resolver.get_available_regimes()
    assert len(regimes) == 2
    codes = [r["code"] for r in regimes]
    assert REGIME_TT58 in codes
    assert REGIME_TT199 in codes

    # Test COA distinctions
    coa_tt58 = resolver.get_chart_of_accounts(REGIME_TT58)
    assert "TIEN_MAT" in coa_tt58
    assert "DOANH_THU" in coa_tt58

    coa_tt199 = resolver.get_chart_of_accounts(REGIME_TT199)
    assert "111" in coa_tt199
    assert "1111" in coa_tt199
    assert "511" in coa_tt199
    assert "642" in coa_tt199


@pytest.mark.asyncio
async def test_regime_transition_preview_balanced():
    engine = AccountingTransitionEngine()
    mock_db = AsyncMock()

    # Mock from profile
    mock_from_profile = AccountingFiscalProfile(
        id=101,
        workspace_id=1,
        fiscal_year=2025,
        regulation_code=REGIME_TT58,
        mode="TT58_MODE_1",
        status="ACTIVE",
    )

    engine.resolver.get_or_create_fiscal_profile = AsyncMock(return_value=mock_from_profile)
    engine.get_closing_balances = AsyncMock(
        return_value={
            "TIEN_MAT": Decimal("50000000.00"),
            "TIEN_GUI": Decimal("250000000.00"),
            "CONG_NO_PHAI_THU": Decimal("80000000.00"),
            "HANG_TON_KHO": Decimal("70000000.00"),
            "CONG_NO_PHAI_TRA": Decimal("150000000.00"),
            "VON_CHU_SO_HUU": Decimal("300000000.00"),
        }
    )

    preview = await engine.preview_transition(
        db=mock_db,
        workspace_id=1,
        from_year=2025,
        to_year=2026,
        to_regulation=REGIME_TT199,
    )

    assert preview["from_fiscal_year"] == 2025
    assert preview["to_fiscal_year"] == 2026
    assert preview["to_regulation"] == REGIME_TT199
    assert preview["is_balanced"] is True
    assert preview["total_debit"] == 450000000.00
    assert preview["total_credit"] == 450000000.00
    assert len(preview["mappings"]) == 6


@pytest.mark.asyncio
async def test_regime_transition_execution_locks_old_year():
    engine = AccountingTransitionEngine()
    mock_db = AsyncMock()

    mock_from_profile = AccountingFiscalProfile(
        id=101,
        workspace_id=1,
        fiscal_year=2025,
        regulation_code=REGIME_TT58,
        mode="TT58_MODE_1",
        status="ACTIVE",
    )

    engine.preview_transition = AsyncMock(
        return_value={
            "workspace_id": 1,
            "from_fiscal_year": 2025,
            "to_fiscal_year": 2026,
            "is_balanced": True,
            "total_debit": 450000000.00,
            "total_credit": 450000000.00,
        }
    )

    mock_res_from = MagicMock()
    mock_res_from.scalar_one_or_none.return_value = mock_from_profile
    mock_res_to = MagicMock()
    mock_res_to.scalar_one_or_none.return_value = None

    mock_db.execute.side_effect = [mock_res_from, mock_res_to]

    result = await engine.execute_transition(
        db=mock_db,
        workspace_id=1,
        from_year=2025,
        to_year=2026,
        to_regulation=REGIME_TT199,
        user_id=999,
        notes="Nâng cấp lên chế độ kế toán SME TT199",
    )

    assert result["status"] == "success"
    assert result["from_year"] == 2025
    assert result["to_year"] == 2026
    assert result["to_regulation"] == REGIME_TT199
    # Old profile locked
    assert mock_from_profile.status == "LOCKED"
    assert mock_from_profile.locked_by == 999
