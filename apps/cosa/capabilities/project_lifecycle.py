from __future__ import annotations

from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import CapabilityRisk

from apps.cosa.capabilities._advisory_envelope import wrap_advisory
from apps.cosa.capabilities.client import CompanyServiceClient

__all__ = [
    "STRATEGY_EVIDENCE_CREATE_SPEC",
    "STRATEGY_EVIDENCE_LIST_SPEC",
    "STRATEGY_GATE_EVALUATION_CREATE_SPEC",
    "STRATEGY_NEXT_BEST_ACTION_GET_SPEC",
    "STRATEGY_PROJECT_GET_SPEC",
    "create_strategy_evidence_create_handler",
    "create_strategy_evidence_list_handler",
    "create_strategy_gate_evaluation_create_handler",
    "create_strategy_next_best_action_get_handler",
    "create_strategy_project_get_handler",
]


def _extract_workspace_id(payload: dict[str, Any], context: Any = None) -> str:
    ctx_ws_id = None
    if context is not None:
        if isinstance(context, dict):
            ctx_ws_id = context.get("workspace_id")
        else:
            ctx_ws_id = getattr(context, "workspace_id", None)

    payload_ws_id = payload.get("workspace_id")

    if ctx_ws_id and payload_ws_id and str(ctx_ws_id) != str(payload_ws_id):
        raise ValueError(
            f"Cross-tenant workspace_id mismatch: context='{ctx_ws_id}', payload='{payload_ws_id}'"
        )

    ws_id = ctx_ws_id or payload_ws_id
    if not ws_id:
        raise ValueError("workspace_id is required")
    return str(ws_id)


STRATEGY_PROJECT_GET_SPEC = CapabilitySpec(
    id="strategy.project.get",
    description="Lấy thông tin lifecycle stage và context của dự án trong workspace.",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "required": ["project_id"],
        "properties": {
            "workspace_id": {"type": ["string", "integer"]},
            "project_id": {"type": ["string", "integer"]},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "project": {"type": "object"},
            "advisory": {"type": "object"},
        },
    },
)

STRATEGY_EVIDENCE_LIST_SPEC = CapabilitySpec(
    id="strategy.evidence.list",
    description="Liệt kê bằng chứng (evidence) đã thu thập của dự án.",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "required": ["project_id"],
        "properties": {
            "workspace_id": {"type": ["string", "integer"]},
            "project_id": {"type": ["string", "integer"]},
            "experiment_id": {"type": ["string", "integer"]},
            "status": {"type": "string"},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "items": {"type": "array"},
            "advisory": {"type": "object"},
        },
    },
)

STRATEGY_EVIDENCE_CREATE_SPEC = CapabilitySpec(
    id="strategy.evidence.create",
    description="Đề xuất bản ghi bằng chứng mới (candidate evidence) cho dự án để founder review.",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "required": ["project_id", "source_type", "claim"],
        "properties": {
            "workspace_id": {"type": ["string", "integer"]},
            "project_id": {"type": ["string", "integer"]},
            "experiment_id": {"type": ["string", "integer"]},
            "source_type": {"type": "string"},
            "claim": {"type": "string"},
            "sample_size": {"type": "integer"},
            "raw_strength": {"type": "number"},
            "raw_confidence": {"type": "number"},
            "supports_or_refutes": {"type": "string"},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "evidence": {"type": "object"},
            "advisory": {"type": "object"},
        },
    },
)

STRATEGY_GATE_EVALUATION_CREATE_SPEC = CapabilitySpec(
    id="strategy.gate_evaluation.create",
    description="Thực hiện đánh giá gate khuyến nghị (recommendation-only) theo stage policy của dự án.",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "required": ["project_id", "stage_policy_id"],
        "properties": {
            "workspace_id": {"type": ["string", "integer"]},
            "project_id": {"type": ["string", "integer"]},
            "stage_policy_id": {"type": ["string", "integer"]},
            "blocking_risks": {"type": "array"},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "evaluation": {"type": "object"},
            "advisory": {"type": "object"},
        },
    },
)

STRATEGY_NEXT_BEST_ACTION_GET_SPEC = CapabilitySpec(
    id="strategy.next_best_action.get",
    description="Lấy danh sách các hành động tối ưu tiếp theo (Next Best Actions) cho dự án.",
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "required": ["project_id"],
        "properties": {
            "workspace_id": {"type": ["string", "integer"]},
            "project_id": {"type": ["string", "integer"]},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "actions": {"type": "object"},
            "advisory": {"type": "object"},
        },
    },
)


def create_strategy_project_get_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = _extract_workspace_id(payload, context)
        headers = {"X-Workspace-Id": ws_id}
        project_id = str(payload["project_id"])

        res = await client.get(
            "/operations/strategy/stage-context",
            params={"projectId": project_id},
            headers=headers,
        )

        advisory = wrap_advisory(
            layer="CURRENT_LAW",
            label="insight",
            content=f"Thông tin stage context cho project {project_id}.",
            sources=[f"project:{project_id}"],
            confidence=1.0,
            next_actions=["Xem xét bằng chứng và các yêu cầu gate của giai đoạn hiện tại"],
        )

        return {"project": res, "advisory": advisory}

    return handler


def create_strategy_evidence_list_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = _extract_workspace_id(payload, context)
        headers = {"X-Workspace-Id": ws_id}
        params: dict[str, Any] = {"projectId": str(payload["project_id"])}

        if payload.get("experiment_id"):
            params["experimentId"] = str(payload["experiment_id"])
        if payload.get("status"):
            params["status"] = str(payload["status"])

        res = await client.get("/operations/strategy/evidence", params=params, headers=headers)
        items = res.get("items", []) if isinstance(res, dict) else []

        advisory = wrap_advisory(
            layer="CURRENT_LAW",
            label="insight",
            content=f"Đã tìm thấy {len(items)} bằng chứng cho project {payload['project_id']}.",
            sources=[f"evidence_list:{payload['project_id']}"],
            confidence=1.0,
            next_actions=[],
        )

        return {"items": items, "advisory": advisory}

    return handler


def create_strategy_evidence_create_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = _extract_workspace_id(payload, context)
        headers = {"X-Workspace-Id": ws_id}

        post_body = {
            "projectId": str(payload["project_id"]),
            "sourceType": payload["source_type"],
            "claim": payload["claim"],
            "status": "candidate",  # Agents can only propose candidate evidence
        }
        if payload.get("experiment_id"):
            post_body["experimentId"] = str(payload["experiment_id"])
        if "sample_size" in payload and payload["sample_size"] is not None:
            post_body["sampleSize"] = payload["sample_size"]
        if "raw_strength" in payload and payload["raw_strength"] is not None:
            post_body["rawStrength"] = payload["raw_strength"]
        if "raw_confidence" in payload and payload["raw_confidence"] is not None:
            post_body["rawConfidence"] = payload["raw_confidence"]
        if payload.get("supports_or_refutes"):
            post_body["supportsOrRefutes"] = payload["supports_or_refutes"]

        res = await client.post("/operations/strategy/evidence", json=post_body, headers=headers)

        advisory = wrap_advisory(
            layer="CURRENT_LAW",
            label="proposal",
            content=f"Đã tạo candidate evidence cho project {payload['project_id']}: '{payload['claim']}'. Đang chờ founder phê duyệt.",
            sources=[f"evidence:{res.get('id', '')}"],
            confidence=0.95,
            next_actions=[
                "Founder xem xét và phê duyệt candidate evidence trước khi đánh giá gate"
            ],
        )

        return {"evidence": res, "advisory": advisory}

    return handler


def create_strategy_gate_evaluation_create_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = _extract_workspace_id(payload, context)
        headers = {"X-Workspace-Id": ws_id}

        post_body = {
            "projectId": str(payload["project_id"]),
            "stagePolicyId": str(payload["stage_policy_id"]),
            "blockingRisks": payload.get("blocking_risks", []),
        }

        res = await client.post(
            "/operations/strategy/gate-evaluations",
            json=post_body,
            headers=headers,
        )

        result_status = res.get("result", "pending")
        req_met = res.get("requirementsMet", False)

        advisory = wrap_advisory(
            layer="CURRENT_LAW",
            label="insight",
            content=(
                f"Đánh giá gate khuyến nghị cho project {payload['project_id']}: "
                f"Kết quả: {result_status}, Yêu cầu đạt: {req_met}. "
                "Lưu ý: Đánh giá gate chỉ mang tính khuyến nghị, không tự động chuyển giai đoạn."
            ),
            sources=[f"gate_eval:{res.get('id', '')}"],
            confidence=1.0,
            next_actions=["Chuyển giai đoạn chính thức qua endpoint transition nếu đạt điều kiện"],
        )

        return {"evaluation": res, "advisory": advisory}

    return handler


def create_strategy_next_best_action_get_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        ws_id = _extract_workspace_id(payload, context)
        headers = {"X-Workspace-Id": ws_id}
        project_id = str(payload["project_id"])

        res = await client.get(
            f"/operations/strategy/projects/{project_id}/next-best-actions",
            headers=headers,
        )

        advisory = wrap_advisory(
            layer="CURRENT_LAW",
            label="insight",
            content=f"Đã truy vấn Next Best Actions cho project {project_id}.",
            sources=[f"project_nba:{project_id}"],
            confidence=1.0,
            next_actions=[],
        )

        return {"actions": res, "advisory": advisory}

    return handler
