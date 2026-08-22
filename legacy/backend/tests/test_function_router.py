import pytest

from core.function_router import route_function


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Review this contract for compliance", "LEGAL"),
        ("Plan a marketing campaign and SEO", "MARKETING"),
        ("Qualify the sales lead and pipeline", "SALES"),
        ("Fix the API deployment bug", "TECH"),
        ("Reconcile cash flow and accounting books", "FINANCE"),
    ],
)
def test_keyword_router_is_deterministic(text, expected):
    assert route_function(text) == expected


def test_ambiguous_request_uses_classifier_fallback():
    assert route_function("Help with this", classifier=lambda _: "sales") == "SALES"
