import json
from pathlib import Path

import pytest

from agent.contracts.done_criteria import DoneCriteriaError, parse_done_criteria

_FIXTURES = json.loads(
    (Path(__file__).resolve().parents[3] / "shared/contracts/done-criteria.fixtures.json").read_text(
        encoding="utf-8"
    )
)


@pytest.mark.parametrize("case", _FIXTURES["valid"], ids=lambda c: c["name"])
def test_valid_cases_normalize_like_typescript(case):
    assert parse_done_criteria(case["input"]) == case["normalized"]


@pytest.mark.parametrize("case", _FIXTURES["invalid"], ids=lambda c: c["name"])
def test_invalid_cases_raise_with_shared_message(case):
    with pytest.raises(DoneCriteriaError, match=case["error"]):
        parse_done_criteria(case["input"])
