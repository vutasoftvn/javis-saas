"""Compatibility import for the canonical workforce AgentProfile schema."""

from workforce.agents.profiles.schemas import (
    AgentProfile,
    AgentProfileRegistryInterface,
)

__all__ = ["AgentProfile", "AgentProfileRegistryInterface"]
