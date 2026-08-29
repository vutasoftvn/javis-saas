from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent.governance.contracts import PinnedSpecIdentity, SpecDependencyEdge


def _identity(kind: str, spec_id: str, version: str = "1") -> PinnedSpecIdentity:
    return PinnedSpecIdentity(spec_kind=kind, spec_id=spec_id, spec_version=version, definition_hash="a" * 64)


def test_spec_dependency_edge_holds_owner_dependency_and_relation():
    owner = _identity("agent", "cofounder")
    dependency = _identity("prompt", "cofounder/system")

    edge = SpecDependencyEdge(owner=owner, dependency=dependency, relation="uses_prompt")

    assert edge.owner == owner
    assert edge.dependency == dependency
    assert edge.relation == "uses_prompt"


def test_spec_dependency_edge_is_frozen():
    owner = _identity("agent", "cofounder")
    dependency = _identity("skill", "research", version="12")
    edge = SpecDependencyEdge(owner=owner, dependency=dependency, relation="pins_skill")

    with pytest.raises(ValidationError):
        edge.relation = "changed"


def test_spec_dependency_edge_equality_is_value_based():
    owner = _identity("agent", "cofounder")
    dependency = _identity("prompt", "cofounder/system")

    a = SpecDependencyEdge(owner=owner, dependency=dependency, relation="uses_prompt")
    b = SpecDependencyEdge(owner=owner, dependency=dependency, relation="uses_prompt")

    assert a == b
