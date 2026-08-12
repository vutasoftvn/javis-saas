from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.modules.finance.domain.accounting_profile_service import activate_profile
from app.modules.finance.domain.management_metrics_service import calculate_management_metrics
from app.modules.finance.domain.period_service import transition_period
from app.modules.finance.regulations.tt58_2026.registry import get_book_templates


def test_management_metrics_are_decimal_and_deterministic():
    metrics = calculate_management_metrics(
        opening_cash=Decimal("100000000"),
        cash_in=Decimal("30000000"),
        cash_out=Decimal("20000000"),
        monthly_operating_expense=Decimal("10000000"),
        budget=Decimal("25000000"),
    )
    assert metrics == {
        "cash": Decimal("110000000"),
        "burn": Decimal("10000000"),
        "runway_months": Decimal("11"),
        "budget_variance": Decimal("5000000"),
    }


def test_profile_needs_human_confirmation_and_mode_one():
    profile = SimpleNamespace(status="PENDING_CONFIRMATION", mode="TT58_MODE_1", confirmed_by=None)
    with pytest.raises(ValueError, match="human confirmation"):
        activate_profile(profile, confirmed_by=None)
    activate_profile(profile, confirmed_by=123)
    assert profile.status == "ACTIVE"


def test_unsupported_tt58_mode_rejects_activation():
    profile = SimpleNamespace(status="PENDING_CONFIRMATION", mode="TT58_MODE_2", confirmed_by=None)
    with pytest.raises(ValueError, match="Mode 1"):
        activate_profile(profile, confirmed_by=123)


def test_locked_period_requires_explicit_reopen_authorization():
    period = SimpleNamespace(status="LOCKED")
    with pytest.raises(PermissionError):
        transition_period(period, "OPEN", can_reopen_locked=False)
    transition_period(period, "OPEN", can_reopen_locked=True)
    assert period.status == "OPEN"


def test_tt58_mode_one_has_production_ready_s1_template():
    templates = get_book_templates("TT58_MODE_1")
    assert templates[0]["code"] == "S1-DNSN"
    assert templates[0]["status"] == "PRODUCTION_READY"
