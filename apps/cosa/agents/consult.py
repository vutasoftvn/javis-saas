"""`agent.consult` — Co-Founder hỏi ý kiến agent chuyên môn ngay trong chat
(review 2026-09-27, G-7).

Mỗi lần gọi là 1 CHILD RUN riêng:
- `run_id` riêng; spec agent đích resolve exact-hash qua registry (prepare_run);
- capability + company delegation của CHÍNH agent đích (compliance mint theo
  spec đích) — không kế thừa, không nới quyền của run cha;
- mang `project_id` của run cha (quy tắc 14 — thiếu thì fail closed);
- CHỈ ĐỌC: metadata `READ_ONLY_RUN_KEY` làm CosaPolicyEngine DENY mọi capability
  ghi. Hành động thật đi qua kế hoạch/approval như cũ;
- sâu tối đa 1 cấp (agent đích không có `agent.consult` + guard `consult_depth`).
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.contracts.run import RunStatus
from agent.governance.contracts import CapabilityRisk

from apps.cosa.agents.agent_profile_specs import AGENT_PROFILE_SPECS
from apps.cosa.agents.catalog import seeded_entries
from apps.cosa.policies.evaluator import READ_ONLY_RUN_KEY

__all__ = [
    "AGENT_CONSULT_SPEC",
    "CONSULTABLE_PROFILES",
    "create_agent_consult_handler",
]

logger = logging.getLogger(__name__)

_MAX_ANSWER_CHARS = 4000

# Agent vận hành công khai, trừ chính Co-Founder (không tự hỏi mình).
CONSULTABLE_PROFILES: tuple[str, ...] = tuple(
    e.profile_key
    for e in seeded_entries()
    if e.availability == "public"
    and e.deployment_kind == "operating"
    and e.profile_key != "founder_assistant"
)

AGENT_CONSULT_SPEC = CapabilitySpec(
    id="agent.consult",
    description=(
        "Hỏi ý kiến một agent chuyên môn của Project (finance, marketing, strategy, "
        "sales, legal…) và nhận câu trả lời của agent đó. Agent được hỏi chỉ ĐỌC dữ "
        "liệu trong phạm vi quyền của chính nó, không thực hiện hành động ghi. Dùng khi "
        "câu hỏi của founder cần chuyên môn/dữ liệu của lĩnh vực khác."
    ),
    risk=CapabilityRisk.LOW,
    input_schema={
        "type": "object",
        "required": ["agent_profile", "question"],
        "properties": {
            "agent_profile": {"type": "string", "enum": list(CONSULTABLE_PROFILES)},
            "question": {"type": "string", "minLength": 5, "maxLength": 4000},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "agent_profile": {"type": "string"},
            "run_id": {"type": "string"},
            "status": {"type": "string"},
            "answer": {"type": "string"},
        },
    },
)


def _extract_text(result: Any) -> str:
    fo = getattr(result, "final_output", None)
    if isinstance(fo, dict):
        return str(fo.get("response", fo))
    return str(fo or "")


def create_agent_consult_handler(plane: Any):
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        from apps.cosa.worker.run_core import RunCoreError, prepare_run, run_kernel

        ctx = context if isinstance(context, dict) else {}
        if int(ctx.get("consult_depth") or 0) >= 1:
            raise ValueError("agent.consult: nested consultation is not allowed")
        workspace_id = str(ctx.get("workspace_id") or "")
        project_id = str(ctx.get("project_id") or "")
        if not workspace_id or not project_id:
            raise ValueError("agent.consult: workspace_id/project_id missing from run context")
        profile = str(payload.get("agent_profile") or "")
        if profile not in CONSULTABLE_PROFILES:
            raise ValueError(
                f"agent.consult: agent_profile must be one of {list(CONSULTABLE_PROFILES)}"
            )
        question = str(payload.get("question") or "").strip()
        if len(question) < 5:
            raise ValueError("agent.consult: question is required")

        child_run_id = f"consult_{uuid.uuid4().hex[:16]}"
        parent_ref = str(ctx.get("correlation_id") or ctx.get("conversation_id") or "")
        try:
            prep = await prepare_run(
                plane,
                run_id=child_run_id,
                local_spec=AGENT_PROFILE_SPECS[profile],
                prompt=question,
                principal=str(ctx.get("principal") or "system:consult"),
                workspace_id=workspace_id,
                conversation_id=f"consult_{parent_ref or child_run_id}",
                policy_snapshot=None,
                locale=str(ctx.get("locale") or "vi-VN"),
                extra_metadata={
                    READ_ONLY_RUN_KEY: True,
                    "consult_depth": 1,
                    "consult_parent_ref": parent_ref,
                },
                project_id=project_id,
            )
        except RunCoreError as exc:
            logger.warning("agent.consult prep failed profile=%s: %s", profile, exc.reason_code)
            return {
                "agent_profile": profile,
                "run_id": child_run_id,
                "status": "unavailable",
                "answer": f"Agent {profile} hiện không sẵn sàng ({exc.reason_code}).",
            }

        result, _ = await run_kernel(plane, prep, workspace_id=workspace_id, run_id=child_run_id)
        status = getattr(result, "status", None)
        if status == RunStatus.COMPLETED:
            answer = _extract_text(result).strip()
            if len(answer) > _MAX_ANSWER_CHARS:
                answer = answer[:_MAX_ANSWER_CHARS] + " …(đã rút gọn)"
            return {
                "agent_profile": profile,
                "run_id": child_run_id,
                "status": "completed",
                "answer": answer,
            }
        return {
            "agent_profile": profile,
            "run_id": child_run_id,
            "status": str(getattr(status, "value", status) or "failed").lower(),
            "answer": f"Agent {profile} không trả lời được lần này.",
        }

    return handler
