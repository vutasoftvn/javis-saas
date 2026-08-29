from __future__ import annotations

from pydantic import BaseModel

from agent.governance.hashing import definition_hash


class _Sample(BaseModel):
    id: str
    values: list[int]


def test_definition_hash_is_a_64_char_hex_sha256():
    result = definition_hash(_Sample(id="a", values=[1, 2]))

    assert len(result) == 64
    assert all(c in "0123456789abcdef" for c in result)


def test_definition_hash_is_identical_for_identical_content():
    a = definition_hash(_Sample(id="a", values=[1, 2]))
    b = definition_hash(_Sample(id="a", values=[1, 2]))

    assert a == b


def test_definition_hash_differs_when_content_differs():
    a = definition_hash(_Sample(id="a", values=[1, 2]))
    b = definition_hash(_Sample(id="a", values=[1, 3]))

    assert a != b


def test_definition_hash_is_not_affected_by_python_dict_construction_order():
    # Pydantic model fields are positional/keyword here, not a raw dict, but
    # the underlying JSON canonicalization must still sort keys so that two
    # equivalent models never hash differently due to incidental ordering.
    a = _Sample.model_validate({"id": "a", "values": [1, 2]})
    b = _Sample.model_validate({"values": [1, 2], "id": "a"})

    assert definition_hash(a) == definition_hash(b)
