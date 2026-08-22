"""Skill Manifest Schema for COSA OS.

Defines structured metadata for skills independent of underlying LLM models and capability providers.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class FailurePolicy(BaseModel):
    retry_count: int = 1
    is_blocking: bool = False
    fallback_skill: Optional[str] = None


class SkillManifest(BaseModel):
    id: str
    name: str
    domain: str = "general"
    version: int = 1
    description: str = ""
    intents: List[str] = Field(default_factory=list)
    requires_context: List[str] = Field(default_factory=lambda: ["company"])
    requires_capabilities: List[str] = Field(default_factory=list)
    optional_capabilities: List[str] = Field(default_factory=list)
    outputs: List[str] = Field(default_factory=list)
    risk_level: str = "low"  # low, medium, high, critical
    failure_policy: FailurePolicy = Field(default_factory=FailurePolicy)
    metadata: Dict[str, Any] = Field(default_factory=dict)
