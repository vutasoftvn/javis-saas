"""RegistryBackedCapabilityChecker — pre-filter thô cho `required_capabilities`
của EventTriggerRule: capability phải được đăng ký trong CapabilityRegistry.

KHÔNG phải enforcement thật — Capability Gateway + connector grant + policy
kiểm tra đầy đủ (bao gồm workspace scope) tại thời điểm side effect trong run.
Ở đây chỉ chặn rule tham chiếu capability không tồn tại.
"""
from __future__ import annotations

from typing import Any

__all__ = ["RegistryBackedCapabilityChecker"]


class RegistryBackedCapabilityChecker:
    def __init__(self, capability_registry: Any) -> None:
        self._registry = capability_registry

    def has(self, workspace_id: str, capability: str) -> bool:
        return self._registry.get(capability) is not None
