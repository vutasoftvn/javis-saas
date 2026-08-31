"""Tests cho RegistryBackedCapabilityChecker — test lớp REAL, không InMemoryCapabilityChecker.

Các test này verify rằng RegistryBackedCapabilityChecker:
1. Đúng gọi registry.get(capability) để check exist
2. Trả True khi capability tồn tại trong registry
3. Trả False khi capability không tồn tại hoặc None
4. Không cache kết quả giữa lần gọi
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from apps.cosa.events.capability_checker import RegistryBackedCapabilityChecker


class _FakeRegistry:
    """Mock registry object."""

    def __init__(self, capabilities: dict | None = None):
        self.capabilities = capabilities or {}
        self.get_calls = []

    def get(self, key: str):
        self.get_calls.append(key)
        return self.capabilities.get(key)


@pytest.mark.asyncio
async def test_has_returns_true_when_capability_exists():
    """Capability trong registry → has() trả True."""
    registry = _FakeRegistry({"operations.task.read": {"id": "cap_1"}})
    checker = RegistryBackedCapabilityChecker(registry)

    result = checker.has("ws_test", "operations.task.read")

    assert result is True
    assert registry.get_calls == ["operations.task.read"]


@pytest.mark.asyncio
async def test_has_returns_false_when_capability_missing():
    """Capability không trong registry → has() trả False."""
    registry = _FakeRegistry({})
    checker = RegistryBackedCapabilityChecker(registry)

    result = checker.has("ws_test", "operations.task.read")

    assert result is False
    assert registry.get_calls == ["operations.task.read"]


@pytest.mark.asyncio
async def test_has_returns_false_when_registry_returns_none():
    """registry.get() trả None → has() trả False."""
    registry = _FakeRegistry()
    registry.capabilities = {"operations.task.read": None}
    checker = RegistryBackedCapabilityChecker(registry)

    result = checker.has("ws_test", "operations.task.read")

    assert result is False


@pytest.mark.asyncio
async def test_has_ignores_workspace_id():
    """has() không dùng workspace_id trong check — chỉ capability name."""
    registry = _FakeRegistry({"finance.read": {"id": "cap_f1"}})
    checker = RegistryBackedCapabilityChecker(registry)

    # workspace_id bị ignore
    result = checker.has("ws_alpha", "finance.read")

    assert result is True
    assert registry.get_calls == ["finance.read"]  # chỉ có capability


@pytest.mark.asyncio
async def test_has_multiple_calls_not_cached():
    """Multiple gọi has() không cache — call registry mỗi lần."""
    registry = _FakeRegistry({"finance.read": {"id": "cap_1"}})
    checker = RegistryBackedCapabilityChecker(registry)

    result1 = checker.has("ws_1", "finance.read")
    result2 = checker.has("ws_1", "finance.read")
    result3 = checker.has("ws_2", "finance.read")

    assert result1 is True
    assert result2 is True
    assert result3 is True
    # Mỗi lần gọi dẫn đến registry.get()
    assert len(registry.get_calls) == 3


@pytest.mark.asyncio
async def test_has_with_mock_object():
    """Dùng Mock object cho registry."""
    registry = Mock()
    registry.get.return_value = {"id": "cap_123"}
    checker = RegistryBackedCapabilityChecker(registry)

    result = checker.has("ws_test", "operations.task.write")

    assert result is True
    registry.get.assert_called_once_with("operations.task.write")


@pytest.mark.asyncio
async def test_has_with_mock_returning_none():
    """Mock registry.get() returning None."""
    registry = Mock()
    registry.get.return_value = None
    checker = RegistryBackedCapabilityChecker(registry)

    result = checker.has("ws_test", "unknown.capability")

    assert result is False
    registry.get.assert_called_once_with("unknown.capability")


@pytest.mark.asyncio
async def test_constructor_stores_registry():
    """Constructor lưu trữ registry đúng."""
    registry = _FakeRegistry({"test.cap": {}})
    checker = RegistryBackedCapabilityChecker(registry)

    # Access private _registry to verify storage
    assert checker._registry is registry
