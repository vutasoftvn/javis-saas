"""Snowflake ID contract tests (P1.2).

Verifies that Snowflake IDs larger than 2^53 - 1 (JavaScript MAX_SAFE_INTEGER: 9007199254740991)
are treated strictly as string / 64-bit integer across serialization boundaries without precision loss.
"""
from __future__ import annotations

import json
from pydantic import BaseModel, Field


class EntityWithSnowflakeId(BaseModel):
    id: str = Field(..., description="64-bit Snowflake ID serialized as string")
    workspace_id: str
    name: str


def test_snowflake_id_beyond_max_safe_integer_serialization():
    # 2^53 = 9007199254740992, test with IDs >= 2^53
    snowflake_ids = [
        "9007199254740993",        # 2^53 + 1
        "9007199254740994",        # 2^53 + 2
        "351020997941043206",      # Real Encore Snowflake format
        "18446744073709551615",    # Max uint64
    ]

    for sf_id in snowflake_ids:
        # Construct model
        entity = EntityWithSnowflakeId(id=sf_id, workspace_id="ws-1001", name="Test Entity")
        
        # Serialize to JSON
        json_str = entity.model_dump_json()
        raw_dict = json.loads(json_str)

        # Assert ID is serialized as string and matches exact character value
        assert isinstance(raw_dict["id"], str)
        assert raw_dict["id"] == sf_id

        # Deserialize back
        restored = EntityWithSnowflakeId.model_validate_json(json_str)
        assert restored.id == sf_id
        assert int(restored.id) == int(sf_id)


def test_snowflake_number_vs_string_precision():
    """Demonstrate why string serialization is required (JSON float64 cast loses precision)."""
    large_id_str = "9007199254740993"
    
    # In float64 / IEEE 754 (used in JS / standard JSON numbers):
    float_val = float(large_id_str)
    assert int(float_val) != int(large_id_str)  # Cast to float64 loses lowest bit (ends in 2 instead of 3)

    # With String encoding, precision is 100% exact
    assert int(large_id_str) == 9007199254740993
