from __future__ import annotations

from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import CapabilityRisk

from apps.cosa.capabilities._advisory_envelope import wrap_advisory
from apps.cosa.capabilities.client import CompanyServiceClient

__all__ = [
    "OPERATIONS_TASK_ADVANCE_SPEC",
    "OPERATIONS_TASK_CREATE_DRAFT_SPEC",
    "create_operations_task_advance_handler",
    "create_operations_task_create_draft_handler",
]

OPERATIONS_TASK_CREATE_DRAFT_SPEC = CapabilitySpec(
    id="operations.task.create_draft",
    description="Tạo một tác vụ điều hành nháp kèm lý do căn cứ theo bằng chứng/giai đoạn dự án.",
    risk=CapabilityRisk.MEDIUM,
    metadata={"action_class": "B"},
    input_schema={
        "type": "object",
        "required": ["title", "project_id", "decision_reason", "evidence_refs"],
        "properties": {
            "workspace_id": {"type": "string"},
            "project_id": {"type": "string", "minLength": 1},
            "title": {"type": "string", "minLength": 1},
            "priority": {"type": "string", "enum": ["urgent", "high", "medium", "low"]},
            "decision_reason": {"type": "string", "minLength": 5},
            "evidence_refs": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
            },
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
        ws_id = (
            context.get("workspace_id")
            if isinstance(context, dict)
            else getattr(context, "workspace_id", None)
        ) or payload.get("workspace_id")

        if not ws_id:
            raise ValueError("operations.task.create_draft: workspace_id is required")

        headers = {"X-Workspace-Id": str(ws_id)}

        project_id = payload.get("project_id")
        if not project_id or not str(project_id).strip():
            raise ValueError("project_id is required to propose an operations task")

        # Require decision reason for accountability
        decision_reason = payload.get("decision_reason")
        if not decision_reason or not str(decision_reason).strip():
            raise ValueError("decision_reason is required to propose an operations task")

        evidence_refs = payload.get("evidence_refs")
        if not isinstance(evidence_refs, list) or len(evidence_refs) == 0:
            raise ValueError("evidence_refs with at least 1 reference is required")

        # Reject cross-workspace evidence references
        for ref in evidence_refs:
            ref_str = str(ref)
            if ref_str.startswith("artifact://") and f"artifact://{ws_id}/" not in ref_str:
                raise ValueError(f"Cross-workspace evidence reference rejected: {ref_str}")
            if (
                ref_str.startswith("ws-")
                and not ref_str.startswith(f"{ws_id}:")
                and not ref_str.startswith(f"{ws_id}/")
            ):
                # if prefix is another ws
                parts = ref_str.split(":", 1)
                if len(parts) == 2 and parts[0] != str(ws_id):
                    raise ValueError(f"Cross-workspace evidence reference rejected: {ref_str}")

        body = {
            "projectId": str(project_id),
            "title": payload["title"],
            "priority": payload.get("priority", "medium"),
            "status": "todo",
            "decisionReason": str(decision_reason),
            "evidenceRefs": [str(r) for r in evidence_refs],
            "source": "ai_agent_proposal",
        }
        task = await client.post("/operations/tasks", json=body, headers=headers)

        advisory = wrap_advisory(
            layer="CURRENT_LAW",
            label="proposal",
            content=f"Đã lập tác vụ điều hành: {payload['title']}. Căn cứ: {decision_reason}",
            sources=list(evidence_refs),
            confidence=0.9,
            next_actions=["Người phụ trách thực hiện tác vụ và đánh dấu hoàn thành khi xong"],
        )

        return {"task": task, "advisory": advisory}

    return handler


OPERATIONS_TASK_ADVANCE_SPEC = CapabilitySpec(
    id="operations.task.advance",
    description=(
        "Cập nhật trạng thái một tác vụ do AI đảm nhận (in_progress/done/blocked) "
        "trong phạm vi run hiện tại."
    ),
    risk=CapabilityRisk.MEDIUM,
    metadata={"action_class": "B"},
    input_schema={
        "type": "object",
        "required": ["task_id", "to_status", "run_id"],
        "properties": {
            "workspace_id": {"type": "string"},
            "task_id": {"type": "string", "minLength": 1},
            "to_status": {"type": "string", "enum": ["in_progress", "done", "blocked"]},
            "run_id": {"type": "string", "minLength": 1},
            "note": {"type": "string"},
        },
    },
    output_schema={
        "type": "object",
        "properties": {"task": {"type": "object"}},
    },
)


def create_operations_task_advance_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = (
            context.get("workspace_id")
            if isinstance(context, dict)
            else getattr(context, "workspace_id", None)
        ) or payload.get("workspace_id")
        if not ws_id:
            raise ValueError("operations.task.advance: workspace_id is required")

        task_id = payload.get("task_id")
        if not task_id or not str(task_id).strip():
            raise ValueError("operations.task.advance: task_id is required")

        to_status = payload.get("to_status")
        if to_status not in ("in_progress", "done", "blocked"):
            raise ValueError("operations.task.advance: to_status must be in_progress|done|blocked")

        run_id = payload.get("run_id")
        if not run_id or not str(run_id).strip():
            raise ValueError("operations.task.advance: run_id is required")

        headers = {"X-Workspace-Id": str(ws_id)}
        body: dict[str, Any] = {"toStatus": to_status, "runId": str(run_id)}
        note = payload.get("note")
        if note:
            body["note"] = str(note)

        task = await client.post(f"/operations/tasks/{task_id}/advance", json=body, headers=headers)
        return {"task": task}

    return handler
