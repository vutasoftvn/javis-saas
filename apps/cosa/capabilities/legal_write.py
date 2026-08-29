from __future__ import annotations

from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import CapabilityRisk

from apps.cosa.capabilities._advisory_envelope import wrap_advisory
from apps.cosa.capabilities.client import CompanyServiceClient

__all__ = [
    "LEGAL_OBLIGATION_CREATE_DRAFT_SPEC",
    "create_legal_obligation_create_draft_handler",
]

LEGAL_OBLIGATION_CREATE_DRAFT_SPEC = CapabilitySpec(
    id="legal.obligation.create_draft",
    description="Tạo đề xuất nghĩa vụ pháp lý nháp (AI_PROPOSAL) cho doanh nghiệp duyệt.",
    risk=CapabilityRisk.MEDIUM,
    input_schema={
        "type": "object",
        "required": ["title"],
        "properties": {
            "workspace_id": {"type": "integer"},
            "template_id": {"type": "string"},
            "regulation_version_id": {"type": "string"},
            "title": {"type": "string"},
            "due_date": {"type": "string"},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "obligation_instance": {"type": "object"},
            "advisory": {"type": "object"},
        },
    },
)


def create_legal_obligation_create_draft_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any) -> dict[str, Any]:
        ws_id = payload.get("workspace_id") or getattr(context, "workspace_id", None)
        headers = {}
        if ws_id:
            headers["X-Workspace-Id"] = str(ws_id)

        body = {
            "title": payload["title"],
            "source": "AI_PROPOSAL",
            "dueDate": payload.get("due_date"),
            "templateId": payload.get("template_id"),
            "regulationVersionId": payload.get("regulation_version_id"),
        }

        instance = await client.post("/legal/obligation-instances", json=body, headers=headers)

        advisory = wrap_advisory(
            layer="CURRENT_LAW",
            label="proposal",
            content=f"Đã tạo đề xuất nghĩa vụ nháp: '{payload['title']}'. Cần Founder xác nhận trước khi đưa vào lịch thực hiện chính thức.",
            sources=[
                {
                    "template_id": payload.get("template_id"),
                    "regulation_version_id": payload.get("regulation_version_id"),
                }
            ],
            confidence=0.9,
            next_actions=["Founder kiểm tra và bấm chấp thuận nghĩa vụ trên màn hình Pháp lý"],
        )

        return {
            "obligation_instance": instance,
            "advisory": advisory,
        }

    return handler
