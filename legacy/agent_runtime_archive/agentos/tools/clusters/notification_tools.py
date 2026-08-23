from __future__ import annotations

from typing import Any, Optional
from agentos.connectors.slack.client import SlackConnectorClient
from agentos.core.policy import PermissionClass, ToolPermission, ToolRiskLevel
from agentos.tools.spec import ToolSpecV2


def get_notification_tools(slack_client: Optional[SlackConnectorClient] = None) -> list[ToolSpecV2]:
    client = slack_client or SlackConnectorClient()

    async def slack_send(args: dict[str, Any]) -> dict[str, Any]:
        channel = args.get("channel", "")
        text = args.get("text", "")
        workspace_id = args.get("workspace_id")
        return await client.post_message(channel=channel, text=text, workspace_id=workspace_id)

    return [
        ToolSpecV2(
            name="commercial.notification.slack_send",
            version="1.0.0",
            description="Send a notification message to a Slack channel via Slack API connector",
            input_schema={
                "type": "object",
                "properties": {
                    "channel": {"type": "string", "description": "Target Slack channel ID or name"},
                    "text": {"type": "string", "description": "Message content to post"},
                    "workspace_id": {"type": "string", "description": "Tenant workspace ID for credential resolution"},
                },
                "required": ["channel", "text"],
            },
            output_schema={"type": "object"},
            handler=slack_send,
            risk_level=ToolRiskLevel.HIGH,
            tool_permission=ToolPermission.SCOPED_WRITE,
            permission_class=PermissionClass.SEND_MESSAGE,
            approval_policy="conditional",
        ),
    ]
