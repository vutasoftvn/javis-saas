"""Contract: mọi fixture envelope do phía TS sinh phải validate được theo
docs/architecture/event-envelope.schema.json — nguồn sự thật dùng chung."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

REPO = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((REPO / "docs/architecture/event-envelope.schema.json").read_text("utf-8"))
FIXTURES = sorted((REPO / "services/company/shared/events/fixtures").glob("*.json"))

REQUIRED = set(SCHEMA["required"])
ALLOWED = set(SCHEMA["properties"].keys())


def test_fixtures_present() -> None:
    assert FIXTURES, "no envelope fixtures found"


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.name)
def test_fixture_matches_shared_schema(path: Path) -> None:
    doc = json.loads(path.read_text("utf-8"))
    Draft202012Validator(SCHEMA).validate(doc)
    keys = set(doc.keys())
    assert REQUIRED <= keys, f"{path.name} missing {REQUIRED - keys}"
    assert keys <= ALLOWED, f"{path.name} has undeclared keys {keys - ALLOWED}"
    assert path.stem == doc["eventType"], "fixture filename must equal its eventType"
