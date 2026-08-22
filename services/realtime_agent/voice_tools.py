from __future__ import annotations

import logging
import os
from typing import Any, Callable, Optional
from livekit.agents import RunContext, function_tool

from event_bridge import publish_ui_command
from services_client import ServicesClient

logger = logging.getLogger("mcosa.voice_tools")

_default_client = ServicesClient()


def get_services_client() -> ServicesClient:
    return _default_client


NAVIGATION_TARGETS = {
    "dashboard",
    "home",
    "cycle",
    "tasks",
    "ai_team",
    "finance",
    "vault",
    "settings",
    "strategy",
    "next_actions",
    "needs_you",
    "blocked_work",
    "work_inspector",
    "timeline_detail",
    "report_detail",
    "proposal_detail",
}


def _open_navigation_impl(publish_fn: Callable[[str, str | None], None], target: str, project_name: str | None = None) -> dict:
    """UI Stream I/O for navigating Flutter screens."""
    if target not in NAVIGATION_TARGETS:
        return {"ok": False, "error": f"target không hợp lệ, chỉ chấp nhận: {sorted(NAVIGATION_TARGETS)}"}
    publish_fn(target, project_name)
    return {"ok": True}


async def _ask_agent_impl(
    conversation_id: str,
    query: str,
    workspace_id: int,
    user_id: int,
    client: Optional[ServicesClient] = None,
) -> dict:
    """Dispatches any business query or task to AgentOS Chat API (§17.2, §17.3)."""
    c = client or get_services_client()
    return await c.execute_agent_turn(
        conversation_id=conversation_id,
        content=query,
        workspace_id=workspace_id,
        user_id=user_id,
    )


async def _respond_to_approval_impl(
    approval_id: str,
    approved: bool,
    reason: Optional[str] = None,
    workspace_id: int = 1,
    user_id: int = 1,
    client: Optional[ServicesClient] = None,
) -> dict:
    """Resolves an AgentOS human approval gate via voice confirmation (§17.1.3, §17.2)."""
    c = client or get_services_client()
    return await c.decide_approval(
        approval_id=approval_id,
        approved=approved,
        reason=reason,
        workspace_id=workspace_id,
        user_id=user_id,
    )


def build_tools(
    *,
    room=None,
    workspace_id: int,
    user_id: int,
    conversation_id: Optional[str] = None,
    client: Optional[ServicesClient] = None,
):
    """Builds the LiveKit voice agent function tools.

    In Phase 6 (§17.2, §17.3, §5.5), all business actions and domain queries are routed
    strictly to the AgentOS API (agentos/api/), ensuring unified governance, RBAC,
    approvals, and memory across both Voice and Text Chat channels.
    """
    services_client = client or get_services_client()
    active_conv_id = conversation_id or f"voice-conv-{workspace_id}-{user_id}"

    def _publish_ui_command(target: str, project_name: str | None) -> None:
        if room is not None:
            publish_ui_command(room, target, project_name)

    @function_tool
    async def open_navigation(target: str, project_name: str | None = None) -> dict:
        """Điều hướng màn hình Flutter. `target` phải là một trong:
        'dashboard', 'tasks', 'vault', 'strategy', 'next_actions',
        'needs_you', 'blocked_work', 'work_inspector'."""
        return _open_navigation_impl(_publish_ui_command, target, project_name)

    @function_tool
    async def ask_agent(query: str) -> dict:
        """Gửi yêu cầu hoặc câu hỏi tới AgentOS API để thực thi với đầy đủ governance, skills, và tools."""
        return await _ask_agent_impl(
            conversation_id=active_conv_id,
            query=query,
            workspace_id=workspace_id,
            user_id=user_id,
            client=services_client,
        )

    @function_tool(on_duplicate="reject", duplicate_scope="name_and_args")
    async def respond_to_approval(approval_id: str, approved: bool, reason: str | None = None) -> dict:
        """Phản hồi quyết định phê duyệt (approve / reject) cho một yêu cầu phê duyệt qua giọng nói."""
        return await _respond_to_approval_impl(
            approval_id=approval_id,
            approved=approved,
            reason=reason,
            workspace_id=workspace_id,
            user_id=user_id,
            client=services_client,
        )

    tools_list = [
        open_navigation,
        ask_agent,
        respond_to_approval,
    ]
    return tools_list
