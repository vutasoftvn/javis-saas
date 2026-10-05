"""Capability OKR cho agent chat (spec 2026-09-27-chat-business-actions): đọc Objective kèm
Key Result, tạo Key Result, check-in Key Result — bọc API OKR sẵn có của company
(`/operations/objectives`, `/operations/key-results`, màn OKR của frontend dùng cùng API).

Tạo và check-in là T2 (ghi thật) nên chat run buộc founder duyệt trước khi chạy
(`access_matrix.CHAT_T2_CAPABILITIES`). Scope workspace luôn lấy từ run, không từ model.
Kết quả trả kèm nhãn trạng thái bằng lời để model không đọc enum thô cho người dùng.
"""

from __future__ import annotations

from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import ApprovalPolicy, CapabilityRisk

from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.capabilities.startup_os_onboard import context_workspace_id

__all__ = [
    "OKR_KEY_RESULT_CHECKIN_SPEC",
    "OKR_KEY_RESULT_CREATE_SPEC",
    "OKR_KEY_RESULT_UPDATE_SPEC",
    "OKR_OBJECTIVE_LIST_SPEC",
    "create_okr_key_result_checkin_handler",
    "create_okr_key_result_create_handler",
    "create_okr_key_result_update_handler",
    "create_okr_objective_list_handler",
]

_SCORING_TYPES = ["LINEAR_INCREASE", "LINEAR_DECREASE", "MILESTONE", "RANGE"]

_STATUS_LABELS: dict[str, dict[str, str]] = {
    "draft": {"vi": "Nháp", "en": "Draft"},
    "published": {"vi": "Đã công bố", "en": "Published"},
    "active": {"vi": "Đang thực hiện", "en": "Active"},
    "on_track": {"vi": "Đúng tiến độ", "en": "On track"},
    "at_risk": {"vi": "Có rủi ro", "en": "At risk"},
    "off_track": {"vi": "Chậm tiến độ", "en": "Off track"},
    "completed": {"vi": "Hoàn thành", "en": "Completed"},
    "archived": {"vi": "Đã lưu trữ", "en": "Archived"},
}

OKR_OBJECTIVE_LIST_SPEC = CapabilitySpec(
    id="okr.objective.list",
    description=(
        "List the workspace OKR Objectives with their Key Results (title, current/target "
        "value, unit, status label), plus each Objective's scope (company/project) and the "
        "goal/parent it is aligned to. Use it before proposing or checking in a Key Result."
    ),
    risk=CapabilityRisk.LOW,
    approval_policy=ApprovalPolicy.NEVER,
    input_schema={"type": "object", "properties": {}},
    output_schema={"type": "object", "properties": {"objectives": {"type": "array"}}},
)

OKR_KEY_RESULT_CREATE_SPEC = CapabilitySpec(
    id="okr.key_result.create",
    description=(
        "Create a Key Result under an existing Objective (founder must approve in chat before "
        "it runs; an Objective holds at most 3 Key Results). Take objective_id from "
        "okr.objective.list. Refer to Objectives/Key Results by title, never by id."
    ),
    risk=CapabilityRisk.MEDIUM,
    approval_policy=ApprovalPolicy.POLICY_DRIVEN,
    input_schema={
        "type": "object",
        "required": ["objective_id", "title", "target_value"],
        "properties": {
            "objective_id": {"type": "string", "minLength": 1},
            "title": {"type": "string", "minLength": 1, "maxLength": 300},
            "target_value": {"type": "number"},
            "baseline_value": {"type": "number"},
            "unit": {"type": "string", "maxLength": 40},
            "scoring_type": {"type": "string", "enum": _SCORING_TYPES},
        },
    },
    output_schema={"type": "object", "properties": {"key_result": {"type": "object"}}},
)

OKR_KEY_RESULT_CHECKIN_SPEC = CapabilitySpec(
    id="okr.key_result.checkin",
    description=(
        "Record a new current value for a Key Result (founder must approve in chat before it "
        "runs). Take key_result_id from okr.objective.list."
    ),
    risk=CapabilityRisk.MEDIUM,
    approval_policy=ApprovalPolicy.POLICY_DRIVEN,
    input_schema={
        "type": "object",
        "required": ["key_result_id", "value"],
        "properties": {
            "key_result_id": {"type": "string", "minLength": 1},
            "value": {"type": "number"},
        },
    },
    output_schema={"type": "object", "properties": {"key_result": {"type": "object"}}},
)

_STATUS_CHOICES = list(_STATUS_LABELS.keys())

OKR_KEY_RESULT_UPDATE_SPEC = CapabilitySpec(
    id="okr.key_result.update",
    description=(
        "Update an existing Key Result status, target value, current value, or unit (founder "
        "must approve in chat before it runs). Take key_result_id from okr.objective.list."
    ),
    risk=CapabilityRisk.MEDIUM,
    approval_policy=ApprovalPolicy.POLICY_DRIVEN,
    input_schema={
        "type": "object",
        "required": ["key_result_id"],
        "properties": {
            "key_result_id": {"type": "string", "minLength": 1},
            "status": {"type": "string", "enum": _STATUS_CHOICES},
            "target_value": {"type": "number"},
            "current_value": {"type": "number"},
            "unit": {"type": "string", "maxLength": 40},
        },
    },
    output_schema={"type": "object", "properties": {"key_result": {"type": "object"}}},
)


def _context_value(context: Any, key: str) -> Any:
    if isinstance(context, dict):
        return context.get(key)
    value = getattr(context, key, None)
    if value is None:
        metadata = getattr(context, "metadata", None)
        if isinstance(metadata, dict):
            value = metadata.get(key)
    return value


def _status_label(status: Any, locale: Any) -> str:
    lang = "en" if str(locale or "").lower().startswith("en") else "vi"
    entry = _STATUS_LABELS.get(str(status or "").strip().lower())
    if entry is None:
        return "Other" if lang == "en" else "Khác"
    return entry[lang]


def _items(res: Any) -> list[dict[str, Any]]:
    data = res.get("data") if isinstance(res, dict) else res
    return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []


def _key_result_view(kr: dict[str, Any], locale: Any) -> dict[str, Any]:
    return {
        "id": kr.get("id"),
        "title": kr.get("title"),
        "currentValue": kr.get("currentValue"),
        "targetValue": kr.get("targetValue"),
        "baselineValue": kr.get("baselineValue"),
        "unit": kr.get("unit"),
        "statusLabel": _status_label(kr.get("status"), locale),
    }


def create_okr_objective_list_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        headers = {"X-Workspace-Id": context_workspace_id(context, OKR_OBJECTIVE_LIST_SPEC.id)}
        locale = _context_value(context, "locale")
        objectives = _items(await client.get("/operations/objectives", headers=headers))
        key_results = _items(await client.get("/operations/key-results", headers=headers))
        by_objective: dict[str, list[dict[str, Any]]] = {}
        for kr in key_results:
            by_objective.setdefault(str(kr.get("objectiveId")), []).append(
                _key_result_view(kr, locale)
            )
        return {
            "objectives": [
                {
                    "id": obj.get("id"),
                    "title": obj.get("title"),
                    "why": obj.get("why"),
                    "scope": obj.get("scope"),
                    "projectId": obj.get("projectId"),
                    "goalId": obj.get("goalId"),
                    "parentObjectiveId": obj.get("parentObjectiveId"),
                    "statusLabel": _status_label(obj.get("status"), locale),
                    "keyResults": by_objective.get(str(obj.get("id")), []),
                }
                for obj in objectives
            ]
        }

    return handler


def create_okr_key_result_create_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        headers = {"X-Workspace-Id": context_workspace_id(context, OKR_KEY_RESULT_CREATE_SPEC.id)}
        objective_id = str(payload["objective_id"]).strip()
        # Tên trường theo AddKeyResultParams (services/company/operations/services/okr.service.ts).
        body: dict[str, Any] = {
            "title": str(payload["title"]).strip(),
            "targetValue": payload["target_value"],
        }
        if payload.get("baseline_value") is not None:
            body["baselineValue"] = payload["baseline_value"]
        if payload.get("unit"):
            body["unit"] = str(payload["unit"])
        if payload.get("scoring_type"):
            body["scoringType"] = payload["scoring_type"]
        res = await client.post(
            f"/operations/objectives/{objective_id}/key-results", json=body, headers=headers
        )
        return {"key_result": _key_result_view(res, _context_value(context, "locale"))}

    return handler


def create_okr_key_result_checkin_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        headers = {"X-Workspace-Id": context_workspace_id(context, OKR_KEY_RESULT_CHECKIN_SPEC.id)}
        key_result_id = str(payload["key_result_id"]).strip()
        res = await client.post(
            f"/operations/key-results/{key_result_id}/checkin",
            json={"value": payload["value"]},
            headers=headers,
        )
        return {"key_result": _key_result_view(res, _context_value(context, "locale"))}

    return handler

def create_okr_key_result_update_handler(client: CompanyServiceClient):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        headers = {"X-Workspace-Id": context_workspace_id(context, OKR_KEY_RESULT_UPDATE_SPEC.id)}
        key_result_id = str(payload["key_result_id"]).strip()
        body: dict[str, Any] = {}
        if payload.get("status"):
            body["status"] = str(payload["status"]).strip()
        if payload.get("target_value") is not None:
            body["targetValue"] = payload["target_value"]
        if payload.get("current_value") is not None:
            body["currentValue"] = payload["current_value"]
        if payload.get("unit"):
            body["unit"] = str(payload["unit"]).strip()
        res = await client.put(
            f"/operations/key-results/{key_result_id}",
            json=body,
            headers=headers,
        )
        return {"key_result": _key_result_view(res, _context_value(context, "locale"))}

    return handler

