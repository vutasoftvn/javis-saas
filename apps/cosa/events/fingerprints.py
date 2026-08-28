"""SpecFingerprintProvider — definition_hash HIỆN TẠI của AgentSpec mà một
EventTriggerRule pin. Dùng để phát hiện drift: nếu hash trong registry khác
hash lúc tạo evidence ⇒ evidence stale ⇒ trigger bị reject (DoD #5).
"""

from __future__ import annotations

from typing import Any

__all__ = ["SpecFingerprintProvider"]

_MISSING = "<missing>"


class SpecFingerprintProvider:
    def __init__(self, spec_registry: Any) -> None:
        self._registry = spec_registry

    async def current(self, rule: Any) -> dict[str, str]:
        spec = rule.agent_spec
        rec = await self._registry.get("agent", spec.id, spec.version)
        return {spec.id: rec.definition_hash if rec is not None else _MISSING}
