import pytest

from app.core.id_types import parse_snowflake_id, serialize_id


@pytest.mark.parametrize("raw", ["123456789", 123456789])
def test_parse_snowflake_id_accepts_decimal_api_values(raw):
    assert parse_snowflake_id(raw) == 123456789


@pytest.mark.parametrize("raw", ["", "12.3", "abc", "-1", 2**63, True])
def test_parse_snowflake_id_rejects_non_positive_or_non_decimal_values(raw):
    with pytest.raises(ValueError):
        parse_snowflake_id(raw)


def test_serialize_id_always_returns_decimal_string():
    assert serialize_id(123456789) == "123456789"
