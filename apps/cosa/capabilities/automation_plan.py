"""Capability `automation.plan.propose` (plan hub vận hành đợt 2 B4).

Agent chat đề xuất một NHÁP kế hoạch tự động hoá (agent tái dùng trong Project, skill, connector,
kênh nhận của founder, lịch, ngân sách token/lần chạy). Bước gọi tool KHÔNG tạo gì thật: company
(`POST /operations/projects/:projectId/automation-plans/proposals`) lưu nháp + trả readiness để thẻ
kế hoạch (B6) khoá nút Duyệt khi còn blocker; B5 duyệt theo `proposalId` mới tạo lịch.

Bậc T1 (`access_matrix`, quyết định controller Task 5): nháp, không tác động ngoài — thẻ kế hoạch
mới là bước founder duyệt, để T2 sẽ bắt founder duyệt hai lần.

Bất biến an toàn (ADR-FOUNDER-CHANNEL-001, Consequences B4):
- Schema KHÔNG có field bí mật / chat id / người nhận; kênh chỉ chọn theo loại (`channel_kind`).
- `project_id` lấy từ context run (conversation đã verify), không nhận từ model.
- Trạng thái connector do handler tự kiểm với control plane (`ConnectorGrantHttpClient`), model
  không khai báo được `connected`. Không tự mở OAuth thay founder.
- Output thêm `"kind": "automation_plan_proposal"` để B6 nhận diện và phát SSE
  `automation.plan.proposed`.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Coroutine
from typing import Any

from agent.capabilities.grants import ConnectorGrantDeniedError
from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import ApprovalPolicy, CapabilityRisk

from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.capabilities.connector_grant_client import ConnectorGrantHttpClient
from apps.cosa.capabilities.startup_os_onboard import context_workspace_id

__all__ = [
    "AUTOMATION_PLAN_PROPOSE_SPEC",
    "OUTPUT_KIND",
    "create_automation_plan_propose_handler",
]

logger = logging.getLogger(__name__)

CAPABILITY_ID = "automation.plan.propose"
OUTPUT_KIND = "automation_plan_proposal"
MAX_TOKEN_BUDGET_PER_RUN = 200_000
_PATH = "/operations/projects/{project_id}/automation-plans/proposals"
_PROJECT_ID_RE = re.compile(r"[0-9]{1,20}")

# Skill tự động hoá được phép đề xuất → connector skill cần (khớp company
# AUTOMATION_PLAN_SKILLS và manifest skill operations.email-digest).
_SKILL_CONNECTORS: dict[str, tuple[str, ...]] = {"operations.email-digest": ("email-read",)}
# Connector → (action, required_scope) khi assert grant: action = capability id sẽ dùng connector
# (hợp đồng allowedActions của session grant, Task 4), scope = scope authorization của capability.
_CONNECTOR_ASSERT: dict[str, tuple[str, str]] = {"email-read": ("email.digest.read", "mail:read")}
_CHANNEL_KINDS = ("telegram",)
_SCHEDULE_KINDS = ("one_time", "daily", "weekdays")

_ALLOWED_ARGS = frozenset(
    {
        "agent_deployment_id",
        "propose_new_agent",
        "skill_id",
        "connector_keys",
        "channel_kind",
        "schedule",
        "token_budget_per_run",
    }
)
_ALLOWED_SCHEDULE_ARGS = frozenset({"kind", "hour", "minute", "weekdays", "timezone", "run_at"})

AUTOMATION_PLAN_PROPOSE_SPEC = CapabilitySpec(
    id=CAPABILITY_ID,
    description=(
        "Propose a DRAFT automation plan for the founder to review (nothing is scheduled or "
        "executed by this call). Reuse the agent already deployed in the Project (omit "
        "agent_deployment_id to let the server pick it); set propose_new_agent=true ONLY when the "
        "server reports no suitable agent. The result includes readiness blockers (unverified "
        "founder channel, missing connector, new agent needed): explain them and point the founder "
        "to the right tab — never try to connect accounts yourself. Never include secrets, tokens "
        "or chat ids."
    ),
    # Cùng risk/approval với T1 ghi qua company hiện có (operations.task.create_draft): policy
    # engine vẫn đánh giá (tenant policy có thể siết), chat không buộc duyệt vì không nằm trong
    # CHAT_T2_CAPABILITIES — founder duyệt ở thẻ kế hoạch (B6).
    risk=CapabilityRisk.MEDIUM,
    approval_policy=ApprovalPolicy.POLICY_DRIVEN,
    metadata={"risk_class": "DRAFT", "action_class": "A"},
    input_schema={
        "type": "object",
        "required": ["skill_id", "schedule", "token_budget_per_run"],
        "additionalProperties": False,
        "properties": {
            "agent_deployment_id": {"type": "string", "pattern": "^[0-9]{1,20}$"},
            "propose_new_agent": {"type": "boolean"},
            "skill_id": {"type": "string", "enum": sorted(_SKILL_CONNECTORS)},
            "connector_keys": {
                "type": "array",
                "items": {"type": "string", "enum": sorted(_CONNECTOR_ASSERT)},
                "uniqueItems": True,
            },
            "channel_kind": {"type": "string", "enum": list(_CHANNEL_KINDS)},
            "schedule": {
                "type": "object",
                "required": ["kind", "timezone"],
                "additionalProperties": False,
                "properties": {
                    "kind": {"type": "string", "enum": list(_SCHEDULE_KINDS)},
                    "hour": {"type": "integer", "minimum": 0, "maximum": 23},
                    "minute": {"type": "integer", "minimum": 0, "maximum": 59},
                    "weekdays": {
                        "type": "array",
                        "items": {"type": "integer", "minimum": 1, "maximum": 7},
                        "uniqueItems": True,
                        "description": "1=Monday … 7=Sunday (only for kind=weekdays)",
                    },
                    "timezone": {"type": "string", "description": "IANA, e.g. Asia/Ho_Chi_Minh"},
                    "run_at": {
                        "type": "string",
                        "description": "ISO 8601 datetime, only for kind=one_time",
                    },
                },
            },
            "token_budget_per_run": {
                "type": "integer",
                "minimum": 1,
                "maximum": MAX_TOKEN_BUDGET_PER_RUN,
            },
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "kind": {"type": "string", "const": OUTPUT_KIND},
            "proposalId": {"type": "string"},
            "status": {"type": "string"},
            "plan": {"type": "object"},
            "readiness": {"type": "object"},
        },
    },
)


def _ctx_value(context: Any, key: str) -> Any:
    if isinstance(context, dict):
        return context.get(key)
    value = getattr(context, key, None)
    if value is None:
        metadata = getattr(context, "metadata", None)
        if isinstance(metadata, dict):
            value = metadata.get(key)
    return value


def _context_project_id(context: Any) -> str:
    project_id = _ctx_value(context, "project_id")
    if not project_id or not str(project_id).strip():
        raise ValueError(f"{CAPABILITY_ID}: project_id missing from invocation context")
    project_id = str(project_id).strip()
    if not _PROJECT_ID_RE.fullmatch(project_id):
        raise ValueError(f"{CAPABILITY_ID}: project_id trong context không hợp lệ")
    return project_id


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _validate(payload: dict[str, Any]) -> None:
    unknown = sorted(set(payload) - _ALLOWED_ARGS)
    if unknown:
        raise ValueError(f"{CAPABILITY_ID}: tham số không được phép: {', '.join(unknown)}")
    skill_id = payload.get("skill_id")
    if skill_id not in _SKILL_CONNECTORS:
        raise ValueError(f"{CAPABILITY_ID}: skill_id không được hỗ trợ")
    keys = payload.get("connector_keys", [])
    if not isinstance(keys, list) or any(k not in _SKILL_CONNECTORS[skill_id] for k in keys):
        raise ValueError(f"{CAPABILITY_ID}: connector_keys chỉ nhận connector của skill")
    channel_kind = payload.get("channel_kind")
    if channel_kind is not None and channel_kind not in _CHANNEL_KINDS:
        raise ValueError(f"{CAPABILITY_ID}: channel_kind không được hỗ trợ")
    budget = payload.get("token_budget_per_run")
    if not _is_int(budget) or not 1 <= budget <= MAX_TOKEN_BUDGET_PER_RUN:
        raise ValueError(
            f"{CAPABILITY_ID}: token_budget_per_run phải là số nguyên 1-{MAX_TOKEN_BUDGET_PER_RUN}"
        )
    for flag, kind in (("propose_new_agent", bool), ("agent_deployment_id", str)):
        if flag in payload and not isinstance(payload[flag], kind):
            raise ValueError(f"{CAPABILITY_ID}: {flag} sai kiểu")
    schedule = payload.get("schedule")
    if not isinstance(schedule, dict):
        raise ValueError(f"{CAPABILITY_ID}: schedule phải là object")
    unknown_schedule = sorted(set(schedule) - _ALLOWED_SCHEDULE_ARGS)
    if unknown_schedule:
        raise ValueError(
            f"{CAPABILITY_ID}: schedule có tham số không được phép: {', '.join(unknown_schedule)}"
        )
    if schedule.get("kind") not in _SCHEDULE_KINDS:
        raise ValueError(f"{CAPABILITY_ID}: schedule.kind không hợp lệ")
    if not isinstance(schedule.get("timezone"), str) or not schedule["timezone"].strip():
        raise ValueError(f"{CAPABILITY_ID}: schedule.timezone là bắt buộc")


def _schedule_body(schedule: dict[str, Any]) -> dict[str, Any]:
    body: dict[str, Any] = {"kind": schedule["kind"], "timezone": schedule["timezone"]}
    for src, dst in (
        ("hour", "hour"),
        ("minute", "minute"),
        ("weekdays", "weekdays"),
        ("run_at", "runAt"),
    ):
        if src in schedule and schedule[src] is not None:
            body[dst] = schedule[src]
    return body


def create_automation_plan_propose_handler(
    client: CompanyServiceClient,
    grant_client: ConnectorGrantHttpClient | None = None,
) -> Callable[[dict[str, Any], Any], Coroutine[Any, Any, dict[str, Any]]]:
    resolved_grant_client: list[ConnectorGrantHttpClient] = [grant_client] if grant_client else []

    def _grants() -> ConnectorGrantHttpClient:
        if not resolved_grant_client:
            resolved_grant_client.append(ConnectorGrantHttpClient())
        return resolved_grant_client[0]

    async def _connector_status(
        connector_key: str, *, workspace_id: str, conversation_id: str | None
    ) -> str:
        # Không có conversation (grant theo phiên chat) ⇒ không assert được ⇒ coi như chưa nối.
        if not conversation_id:
            return "missing"
        action, scope = _CONNECTOR_ASSERT[connector_key]
        try:
            await _grants().assert_usable(
                connector_key,
                workspace_id=workspace_id,
                conversation_id=conversation_id,
                action=action,
                required_scope=scope,
            )
        except ConnectorGrantDeniedError as exc:
            logger.info(
                "automation.plan.propose: connector %s chưa sẵn sàng (%s)", connector_key, exc.code
            )
            return "missing"
        return "connected"

    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        _validate(payload)
        workspace_id = context_workspace_id(context, CAPABILITY_ID)
        project_id = _context_project_id(context)
        conversation_id = _ctx_value(context, "conversation_id")
        run_id = _ctx_value(context, "run_id")

        skill_id = payload["skill_id"]
        connector_keys = list(payload.get("connector_keys") or _SKILL_CONNECTORS[skill_id])
        # Kiểm MỌI connector skill cần (không chỉ những gì model liệt kê).
        connector_status = {
            key: await _connector_status(
                key,
                workspace_id=workspace_id,
                conversation_id=str(conversation_id) if conversation_id else None,
            )
            for key in _SKILL_CONNECTORS[skill_id]
        }

        body: dict[str, Any] = {
            "skillId": skill_id,
            "connectorKeys": connector_keys,
            "connectorStatus": connector_status,
            "schedule": _schedule_body(payload["schedule"]),
            "tokenBudgetPerRun": payload["token_budget_per_run"],
        }
        if payload.get("agent_deployment_id"):
            body["agentDeploymentId"] = payload["agent_deployment_id"]
        if payload.get("propose_new_agent") is True:
            body["proposeNewAgent"] = True
        if payload.get("channel_kind"):
            body["channelKind"] = payload["channel_kind"]

        headers = {"X-Workspace-Id": workspace_id}
        if run_id:
            headers["X-COSA-Run-Id"] = str(run_id)
        res = await client.post(_PATH.format(project_id=project_id), json=body, headers=headers)
        data = res.get("data") if isinstance(res, dict) else None
        if not isinstance(data, dict):
            raise ValueError(f"{CAPABILITY_ID}: company trả về không đúng định dạng")
        return {"kind": OUTPUT_KIND, **data}

    return handler
