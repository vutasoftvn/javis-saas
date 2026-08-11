from typing import Union


SnowflakeId = int


def parse_snowflake_id(value: Union[str, int]) -> SnowflakeId:
    if isinstance(value, bool):
        raise ValueError("Snowflake ID must be a positive decimal integer")
    text = str(value)
    if not text.isdecimal():
        raise ValueError("Snowflake ID must be a positive decimal integer")
    parsed = int(text)
    if not 0 < parsed < 2**63:
        raise ValueError("Snowflake ID is outside signed BIGINT range")
    return parsed


def serialize_id(value: SnowflakeId) -> str:
    return str(value)
