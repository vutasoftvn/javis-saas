import pytest
from pydantic import ValidationError

from agentos.memory.models import MemoryItem, MemoryKind


def test_memory_item_defaults():
    item = MemoryItem(workspace_id="ws1", agent_key="a1", kind=MemoryKind.EPISODIC, content="did X")
    assert item.importance == 0.5
    assert item.tags == []
    assert item.kind == MemoryKind.EPISODIC


def test_memory_item_rejects_importance_above_one():
    with pytest.raises(ValidationError):
        MemoryItem(workspace_id="ws1", agent_key="a1", kind=MemoryKind.EPISODIC, content="x", importance=1.5)


def test_memory_item_rejects_importance_below_zero():
    with pytest.raises(ValidationError):
        MemoryItem(workspace_id="ws1", agent_key="a1", kind=MemoryKind.EPISODIC, content="x", importance=-0.1)
