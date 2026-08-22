# backend/agentos/core/context.py
from __future__ import annotations

from pydantic import BaseModel, Field

from agentos.core.models import TaskContext


class AgentContext(BaseModel):
    task: TaskContext
    system_policy: str
    tool_names: list[str] = Field(default_factory=list)
    memory_snippets: list[str] = Field(default_factory=list)
    skill_instructions: list[str] = Field(default_factory=list)
