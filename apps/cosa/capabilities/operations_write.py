from __future__ import annotations

from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import CapabilityRisk

from apps.cosa.capabilities._advisory_envelope import wrap_advisory
from apps.cosa.capabilities.client import CompanyServiceClient

__all__ = [
    "OPERATIONS_TASK_CREATE_DRAFT_SPEC",
    "create_operations_task_create_draft_handler",
]

OPERATIONS_TASK_CREATE_DRAFT_SPEC = CapabilitySpec(
    id="operations.task.create_draft",
    description="Tạo một tác vụ điều hành nháp kèm lý do căn cứ theo bằng chứng/giai đoạn dự án.",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "required": ["title", "decision_reason"],
        "properties": {
            "workspace_id": {"type": "integer"},
            "title": {"type": "string", "minLength": 1},
            "priority": {"type": "string", "enum": ["urgent", "high", "medium", "low"]},
            "decision_reason": {"type": "string", "minLength": 5},
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
            "due_date": {"type": "string"},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "task": {"type": "object"},
            "advisory": {"type": "object"},
        },
    },
)


def create_operations_task_create_draft_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = payload.get("workspace_id") or (
            context.get("workspace_id") if isinstance(context, dict) else getattr(context, "workspace_id", None)
        )
        headers = {}
        if ws_id:
            headers["X-Workspace-Id"] = str(ws_id)

        # Require decision reason for accountability
        if not payload.get("decision_reason"):
            raise ValueError("decision_reason is required to propose an operations task")

        body = {
            "title": payload["title"],
            "priority": payload.get("priority", "medium"),
            "status": "todo",
            "source": "ai_agent_proposal",
        }
        task = await client.post("/operations/tasks", json=body, headers=headers)

        advisory = wrap_advisory(
            layer="CURRENT_LAW",
            label="proposal",
            content=f"Đã lập tác vụ điều hành: {payload['title']}. Căn cứ: {payload['decision_reason']}",
            sources=[],
            confidence=0.9,
            next_actions=["Người phụ trách thực hiện tác vụ và đánh dấu hoàn thành khi xong"],
        )

        return {"task": task, "advisory": advisory}

    return handler
