# agentos/profiles/schema.py
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

from agentos.core.policy import PermissionLevel


class AgentProfile(BaseModel):
    """Pydantic schema for Agent Profiles (§12.2-12.3).
    Defines mission, allowed skills, allowed tools, runtime configuration,
    and governance constraints for specialized agent profiles.
    """
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    name: str
    version: str
    mission: str
    skills: list[str] = Field(default_factory=list)              # Skill IDs, must exist in SkillRegistry
    tools_allow: list[str] = Field(default_factory=list)         # Tool names, must exist in ToolRegistry
    permission_level: PermissionLevel = PermissionLevel.L2_DRAFT
    preferred_runtime: Literal["native", "deepseek_harness", "adk"] = "native"
    fallback_runtime: Literal["native", "deepseek_harness", "adk"] = "deepseek_harness"
    max_tool_calls: int = 10
    max_cost_usd: float = 1.0
    max_runtime_seconds: int = 60
