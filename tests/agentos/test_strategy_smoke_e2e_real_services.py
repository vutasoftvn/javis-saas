"""Smoke test Strategy feature qua HTTP thật + services/operations/strategy thật + Postgres
thật (roadmap phase-11-feature-tree-smoke-tests.md, 11b) — KHÔNG mock ở tầng service, khác
với `test_strategy_smoke_e2e.py` (dùng `_MockStrategyBackend`, chỉ test tầng agentos).

Yêu cầu 1 Encore dev server thật đang chạy (`cd services && encore run`), có route
`/operations/projects`, `/operations/strategy/*` thật, backed bởi Postgres thật do Encore
quản lý. Gate bằng `AGENTOS_REAL_ENCORE_URL` (mặc định thử `http://127.0.0.1:4000`, skip nếu
không kết nối được — CI không có Encore chạy vẫn chạy được suite còn lại).
"""
from __future__ import annotations

import os
import time

import httpx
import pytest

from agentos.core.approval import ApprovalService, ApprovalStatus
from agentos.core.models import AgentRunStatus, TaskContext
from agentos.core.model_provider import ModelResponse, ToolCallRequest
from agentos.core.policy import ExecutionMode, PermissionLevel, PolicyEngine
from agentos.core.runtime import AgentRuntime
from agentos.tools.clusters.strategy_tools import get_strategy_tools
from agentos.tools.encore_client import EncoreClient
from agentos.tools.registry import ToolRegistry

REAL_ENCORE_URL = os.environ.get("AGENTOS_REAL_ENCORE_URL", "http://127.0.0.1:4000")


def _encore_is_reachable() -> bool:
    try:
        httpx.get(REAL_ENCORE_URL, timeout=1.0)
        return True
    except httpx.RequestError:
        return False


pytestmark = pytest.mark.skipif(
    not _encore_is_reachable(),
    reason=f"Real Encore dev server not reachable at {REAL_ENCORE_URL} — skipping no-mock smoke test",
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_strategy_flow_against_real_encore_service_and_postgres():
    client = EncoreClient(base_url=REAL_ENCORE_URL)
    workspace_id = int(time.time())  # unique-ish per run, avoids collisions across test runs
    company_id = workspace_id

    # Bước 0 (setup thật, không mock): tạo Project thật qua services/operations thật.
    project = await client.post("/operations/projects", json={"workspaceId": workspace_id, "title": "Agency CRM Venture"})
    project_id = project["id"]

    tool_registry = ToolRegistry()
    for tool in get_strategy_tools(client):
        tool_registry.register(tool)

    # Bước 1: strategy.project.get gọi thẳng service thật -> phải trả đúng record vừa tạo.
    fetched = await tool_registry.invoke("strategy.project.get", {"id": project_id})
    assert fetched["id"] == project_id, "Regression: strategy.project.get không khớp project thật vừa tạo qua service."
    assert fetched["title"] == "Agency CRM Venture"

    # Bước 4: strategy.assumption.create ghi record thật vào Postgres thật (field khớp
    # đúng DTO thật: statement/importance/uncertainty, không phải title/category/criticality).
    assumption = await tool_registry.invoke(
        "strategy.assumption.create",
        {
            "companyId": company_id,
            "workspaceId": workspace_id,
            "projectId": project_id,
            "statement": "Agency will pay $100/mo for specialized workflow CRM",
            "importance": 8,
            "uncertainty": 6,
            "status": "untested",
        },
    )
    assumption_id = assumption.get("id")
    assert assumption_id is not None, "Regression Step 4: assumption.create không trả về id thật từ Postgres."
    assert assumption["riskScore"] == 8 * 6, "Regression Step 4: backend không tự tính riskScore = importance*uncertainty."

    # Xác nhận đọc lại được từ chính service thật (không phải echo lại input).
    assumptions_list = await tool_registry.invoke("strategy.assumption.list", {"projectId": project_id})
    assumption_ids = [a.get("id") for a in assumptions_list.get("items", [])]
    assert assumption_id in assumption_ids, "Regression Step 4: assumption vừa tạo không đọc lại được từ service thật."

    # Bước 5: strategy.experiment.create liên kết đúng assumption_id, ghi thật vào Postgres
    # (field khớp DTO thật: hypothesis/method/successCriteria, không phải title/type/criteria).
    experiment = await tool_registry.invoke(
        "strategy.experiment.create",
        {
            "companyId": company_id,
            "workspaceId": workspace_id,
            "projectId": project_id,
            "assumptionId": assumption_id,
            "hypothesis": "Agency founders will confirm willingness to pay in interviews",
            "method": "10 Agency Founder Interviews",
            "successCriteria": ">= 7/10 confirm willingness to pay",
        },
    )
    exp_id = experiment.get("id")
    assert exp_id is not None, "Regression Step 5: experiment.create không trả về id thật."
    assert experiment["assumptionId"] == assumption_id

    # Bước 8: strategy.evidence.create ghi evidence thật, liên kết đúng experiment
    # (field khớp DTO thật: sourceType/claim, không phải type/summary — strength/confidence
    # backend tự tính tất định từ sourceType).
    evidence = await tool_registry.invoke(
        "strategy.evidence.create",
        {
            "companyId": company_id,
            "workspaceId": workspace_id,
            "projectId": project_id,
            "experimentId": exp_id,
            "sourceType": "customer_interview",
            "claim": "8/10 agency founders confirmed urgent need.",
        },
    )
    assert evidence.get("id") is not None, "Regression Step 8: evidence.create không trả về id thật."
    assert evidence["strength"] is not None, "Regression Step 8: backend không tự tính strength từ sourceType."

    # Bước 9: next-best-actions phải phản ánh đúng state thật vừa tạo trên Postgres thật.
    nba = await tool_registry.invoke("strategy.next_best_action.get", {"projectId": project_id})
    assert "items" in nba, "Regression Step 9: NBA response thiếu 'items'."


@pytest.mark.integration
@pytest.mark.asyncio
async def test_strategy_gate_evaluation_approval_pause_resume_against_real_service():
    """Bước 6/7 roadmap 11b: tool risk cao trigger approval.required, resume đúng
    run_id sau khi POST /agent/approvals/{approval_id}/decision — chạy với tool call
    thật ghi vào services/operations/strategy thật (không mock), chỉ model provider
    là stub (LLM thật không cần thiết để chứng minh đúng luồng governance+service)."""
    client = EncoreClient(base_url=REAL_ENCORE_URL)
    workspace_id = int(time.time()) + 1
    company_id = workspace_id
    project = await client.post("/operations/projects", json={"workspaceId": workspace_id, "title": "Gate Test Venture"})
    project_id = project["id"]

    # Gate evaluation cần 1 Stage Policy thật tồn tại trước (backend yêu cầu stagePolicyId hợp lệ).
    stage_policy = await client.post(
        "/operations/strategy/stage-policies",
        json={"companyId": company_id, "workspaceId": workspace_id, "stageKey": "solution_fit"},
    )
    stage_policy_id = stage_policy["id"]

    tool_registry = ToolRegistry()
    for tool in get_strategy_tools(client):
        tool_registry.register(tool)

    class _GateModel:
        # Quyết định dựa trên số tool-result đã có trong `messages` của lần gọi hiện tại
        # (không dùng counter nội bộ) — resume sau approval khởi động lại `messages` từ đầu.
        async def generate(self, system_prompt, messages):
            tool_results = [m for m in messages if m.get("role") == "tool"]
            if len(tool_results) >= 1:
                return ModelResponse(text="Gate evaluation recorded.")
            return ModelResponse(
                tool_call=ToolCallRequest(
                    tool_name="strategy.gate_evaluation.create",
                    arguments={
                        "companyId": company_id,
                        "workspaceId": workspace_id,
                        "projectId": project_id,
                        "stagePolicyId": stage_policy_id,
                    },
                )
            )

    policy_engine = PolicyEngine()
    approval_svc = ApprovalService()
    runtime = AgentRuntime(model_provider=_GateModel(), tool_registry=tool_registry, policy_engine=policy_engine, approval_service=approval_svc)

    task = TaskContext(
        goal="Advance venture stage",
        agent_key="co_founder",
        workspace_id=str(workspace_id),
        role="user",
        agent_permission_level=PermissionLevel.L1_SUGGEST,
        metadata={"execution_mode": ExecutionMode.INTERACTIVE},
    )

    pause_res = await runtime.run(task)
    assert pause_res.status == AgentRunStatus.WAITING_APPROVAL, f"Regression Step 6: expected WAITING_APPROVAL, got {pause_res.status}"
    approval_id = pause_res.approval_id
    assert approval_id is not None

    dec = approval_svc.decide(approval_id, reviewer="founder_admin", approved=True)
    assert dec.status == ApprovalStatus.APPROVED

    task.metadata["run_id"] = pause_res.run_id
    resume_res = await runtime.run(task)
    assert resume_res.status == AgentRunStatus.COMPLETED, f"Regression Step 7: resumed run failed: {resume_res.error}"
    assert resume_res.run_id == pause_res.run_id, "Regression Step 7: resume tạo run_id mới thay vì tiếp tục run gốc."

    # Xác nhận gate evaluation thật đã được ghi vào Postgres thật qua service thật.
    gate_list = await client.get("/operations/strategy/gate-evaluations", params={"projectId": project_id})
    items = gate_list.get("items", [])
    assert len(items) >= 1, "Regression Step 7: gate evaluation không được ghi vào service thật sau approval."
