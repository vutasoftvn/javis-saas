"""Kickoff wizard Bước 3 — headless task run của AI suggestion (outcome +
1-3 việc tuần đầu). KHÔNG gọi capability nào (thuần suy luận từ context
Founder đã nhập ở Bước 1/2, giống execute_goal_decomposition_task của WGA khi
không gọi capability). Kết quả callback thẳng về services/company qua
service token (giống pattern copilot_run.py), KHÔNG qua mint_company_delegation
— route callback không phải capability-scoped, chỉ webhook 1 chiều.

Khác WGA goal_decomposition (im lặng return khi lỗi): task này LUÔN callback
company (completed/failed) vì company đang poll `ai_suggestion_status` để
biết khi nào dừng — im lặng return sẽ khiến FE poll treo tới hết timeout.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from agent.contracts.run import RunStatus

from apps.cosa.agents.kickoff_suggestion import (
    SuggestionSchemaError,
    build_suggestion_prompt,
    parse_suggestion_output,
)
from apps.cosa.agents.specs import COSA_OPERATIONS_AGENT_SPEC
from apps.cosa.composition.agent_plane import CosaAgentPlane
from apps.cosa.config.service_identity import require_internal_url, require_service_token
from apps.cosa.worker.run_core import RunCoreError, prepare_run, run_kernel

logger = logging.getLogger(__name__)

__all__ = ["callback_kickoff_result", "execute_kickoff_suggestion_task"]


def _extract_text(run_result: Any) -> str:
    fo = getattr(run_result, "final_output", None)
    if isinstance(fo, dict):
        return str(fo.get("response", fo))
    return str(fo or "")


async def callback_kickoff_result(
    project_id: str,
    run_id: str,
    status: str,
    outcome: str | None = None,
    actions: list[str] | None = None,
) -> None:
    company_base_url = require_internal_url(
        "COMPANY_SERVICE_URL", purpose="kickoff suggestion callback", default_dev="http://127.0.0.1:4000"
    )
    service_token = require_service_token("COSA_SERVICE_TOKEN", purpose="kickoff suggestion callback")

    url = f"{company_base_url}/operations/projects/{project_id}/kickoff-suggestion/result"
    headers = {
        "Content-Type": "application/json",
        "X-Cosa-Service-Token": service_token,
    }
    body: dict[str, Any] = {"runId": run_id, "status": status}
    if outcome is not None:
        body["outcome"] = outcome
    if actions is not None:
        body["actions"] = actions

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=body, headers=headers)
            if resp.status_code >= 400:
                logger.warning(
                    "Failed to callback company kickoff-suggestion result for run %s: status %s",
                    run_id,
                    resp.status_code,
                )
    except Exception as e:
        logger.warning("Exception during kickoff-suggestion callback for run %s: %s", run_id, e)


async def execute_kickoff_suggestion_task(
    plane: CosaAgentPlane,
    stream_mgr: Any,
    payload: dict[str, Any],
) -> None:
    run_id = payload["run_id"]
    workspace_id = payload["workspace_id"]
    project_id = payload["project_id"]

    prompt = build_suggestion_prompt(
        target_customer=payload.get("target_customer", ""),
        problem_statement=payload.get("problem_statement", ""),
        evidence_level=payload.get("evidence_level", ""),
        selected_stage=payload.get("selected_stage", ""),
        stage_duration_weeks=int(payload.get("stage_duration_weeks") or 2),
    )

    try:
        prep = await prepare_run(
            plane,
            run_id=run_id,
            local_spec=COSA_OPERATIONS_AGENT_SPEC,
            prompt=prompt,
            principal=f"system:kickoff_suggestion:{workspace_id}",
            workspace_id=workspace_id,
            conversation_id=f"kickoff_suggestion_{run_id}",
            policy_snapshot=None,
        )
    except RunCoreError as exc:
        logger.error("kickoff_suggestion prep failed run=%s reason=%s", run_id, exc.reason_code)
        await callback_kickoff_result(project_id, run_id, "failed")
        return

    run_result, _ = await run_kernel(plane, prep, workspace_id=workspace_id, run_id=run_id)
    if run_result.status != RunStatus.COMPLETED:
        logger.error("kickoff_suggestion kernel run=%s status=%s", run_id, run_result.status)
        await callback_kickoff_result(project_id, run_id, "failed")
        return

    try:
        suggestion = parse_suggestion_output(_extract_text(run_result))
    except SuggestionSchemaError as exc:
        logger.error("kickoff_suggestion schema_invalid run=%s: %s", run_id, exc)
        await callback_kickoff_result(project_id, run_id, "failed")
        return

    await callback_kickoff_result(
        project_id, run_id, "completed", outcome=suggestion.outcome, actions=suggestion.actions
    )
