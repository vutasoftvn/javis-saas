from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field

from agentos.core.models import TaskContext
from agentos.core.policy import PermissionLevel
from agentos.knowledge.models import KnowledgeCitation


class AgentContext(BaseModel):
    task: TaskContext
    system_policy: str
    tool_names: list[str] = Field(default_factory=list)
    memory_snippets: list[str] = Field(default_factory=list)
    knowledge_snippets: list[str] = Field(default_factory=list)
    knowledge_citations: list[KnowledgeCitation] = Field(default_factory=list)
    conversation_messages: list[dict[str, Any]] = Field(default_factory=list)
    skill_instructions: list[str] = Field(default_factory=list)
    role: Optional[str] = None
    agent_permission_level: Optional[PermissionLevel] = None
    company_id: Optional[str] = None
    workspace_id: Optional[str] = None
    user_id: Optional[str] = None
    workforce_member_id: Optional[str] = None
    correlation_id: Optional[str] = None
