from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from agent_core.contracts.capability import CapabilitySpec

__all__ = ["PluginCapabilityGrant", "PluginManifest", "PluginRegistry"]


class PluginCapabilityGrant(BaseModel):
    capability_id: str
    required_risk: str = "LOW"
    allowed_domains: tuple[str, ...] = Field(default_factory=tuple)


class PluginManifest(BaseModel):
    """Manifest định nghĩa Plugin mở rộng độc lập cho Agent Platform."""

    plugin_id: str
    name: str
    version: str
    publisher: str
    description: str = ""
    capabilities: list[CapabilitySpec] = Field(default_factory=list)
    permissions: list[PluginCapabilityGrant] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PluginRegistry:
    """Registry quản trị các Plugin mở rộng của bên thứ ba."""

    def __init__(self) -> None:
        self._plugins: dict[str, PluginManifest] = {}

    def register_plugin(self, manifest: PluginManifest) -> None:
        self._plugins[manifest.plugin_id] = manifest

    def get_plugin(self, plugin_id: str) -> PluginManifest | None:
        return self._plugins.get(plugin_id)

    def list_plugins(self) -> list[PluginManifest]:
        return list(self._plugins.values())
