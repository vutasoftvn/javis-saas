from decimal import Decimal


def calculate_management_metrics(*, opening_cash: Decimal, cash_in: Decimal, cash_out: Decimal, monthly_operating_expense: Decimal, budget: Decimal) -> dict[str, Decimal | None]:
    cash = opening_cash + cash_in - cash_out
    burn = monthly_operating_expense
    runway = cash / burn if burn > 0 else None
    return {"cash": cash, "burn": burn, "runway_months": runway, "budget_variance": budget - cash_out}
