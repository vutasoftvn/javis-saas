from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from agentos.core.models import TaskContext
from agentos.core.policy import PermissionLevel


class AgentContext(BaseModel):
    task: TaskContext
    system_policy: str
    tool_names: list[str] = Field(default_factory=list)
    memory_snippets: list[str] = Field(default_factory=list)
    knowledge_snippets: list[str] = Field(default_factory=list)
    conversation_messages: list[dict[str, Any]] = Field(default_factory=list)
    skill_instructions: list[str] = Field(default_factory=list)
    role: str | None = None
    agent_permission_level: PermissionLevel | None = None
    company_id: str | None = None
    workspace_id: str | None = None
    user_id: str | None = None
    workforce_member_id: str | None = None
    correlation_id: str | None = None
