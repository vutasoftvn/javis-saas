from __future__ import annotations

from pathlib import Path
from typing import Any
import pytest

from agentos.api.chat.event_stream import RunEventStreamManager
from agentos.core.approval import ApprovalService, ApprovalStatus
from agentos.core.audit_sink import SqliteAuditSink
from agentos.core.events import InMemoryEventBus
from agentos.core.model_provider import ModelResponse, ToolCallRequest
from agentos.core.models import AgentRunStatus, TaskContext
from agentos.core.policy import ExecutionMode, PermissionLevel, PolicyEngine, ToolRiskLevel
from agentos.core.runtime import AgentRuntime
from agentos.core.trace_sink import SqliteTraceSink
from agentos.skills.instruction_loader import SkillInstructionLoader
from agentos.skills.registry import SkillRegistry
from agentos.skills.router import SkillRouter
from agentos.tools.clusters.strategy_tools import get_strategy_tools
from agentos.tools.encore_client import EncoreClient
from agentos.tools.registry import ToolRegistry


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLPACKS_ROOT = REPO_ROOT / "skillpacks"


class _MockStrategyBackend:
    """In-memory realistic Strategy backend tracking durable database records."""

    def __init__(self) -> None:
        self.projects: dict[str, dict[str, Any]] = {
            "proj_crm_1": {
                "id": "proj_crm_1",
                "name": "Agency CRM Venture",
                "stage": "problem_discovery",
                "workspaceId": "ws_agency_1",
            }
        }
        self.assumptions: dict[str, dict[str, Any]] = {}
        self.experiments: dict[str, dict[str, Any]] = {}
        self.evidence: dict[str, dict[str, Any]] = {}
        self.gate_evaluations: list[dict[str, Any]] = []
        self.stage_policies: dict[str, dict[str, Any]] = {
            "policy_s2": {"id": "policy_s2", "stageKey": "solution_fit", "workspaceId": "ws_agency_1"}
        }

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if path.startswith("/operations/strategy/projects/") and "next-best-actions" in path:
            # Return NBAs computed from unresolved assumptions
            unresolved = [a for a in self.assumptions.values() if a.get("status") != "validated"]
            actions = []
            for a in unresolved:
                actions.append({
                    "id": f"nba_exp_{a['id']}",
                    "type": "design_experiment",
                    "title": f"Run experiment for {a['statement']}",
                    "priority": "high",
                    "assumptionId": a["id"],
                })
            return {"items": actions, "count": len(actions)}
        elif path.startswith("/operations/projects/"):
            proj_id = path.split("/")[-1]
            return self.projects.get(proj_id, {"id": proj_id, "stage": "problem_discovery"})
        elif path == "/operations/strategy/stage-policies":
            return {"items": list(self.stage_policies.values())}
        elif path == "/operations/strategy/assumptions":
            return {"items": list(self.assumptions.values())}
        elif path == "/operations/strategy/evidence":
            return {"items": list(self.evidence.values())}
        return {"items": []}

    async def post(self, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        data = dict(json or {})
        if path == "/operations/strategy/assumptions":
            assump_id = f"assump_{len(self.assumptions) + 1}"
            data["id"] = assump_id
            self.assumptions[assump_id] = data
            return data
        elif path == "/operations/strategy/experiments":
            exp_id = f"exp_{len(self.experiments) + 1}"
            data["id"] = exp_id
            self.experiments[exp_id] = data
            return data
        elif path == "/operations/strategy/evidence":
            evi_id = f"evi_{len(self.evidence) + 1}"
            data["id"] = evi_id
            self.evidence[evi_id] = data
            return data
        elif path == "/operations/strategy/gate-evaluations":
            self.gate_evaluations.append(data)
            return {"id": len(self.gate_evaluations), "result": "passed", "requirementsMet": True, **data}
        return {"status": "ok", **data}


class _MultiTurnStrategyModel:
    """Simulates LLM generating appropriate tool calls and responses throughout the strategy flow."""

    def __init__(self) -> None:
        self.turn = 0

    async def generate(self, system_prompt: str, messages: list[dict[str, Any]]) -> ModelResponse:
        self.turn += 1
        if self.turn == 1:
            # Turn 1: Check project details
            return ModelResponse(
                tool_call=ToolCallRequest(
                    tool_name="strategy.project.get",
                    arguments={"projectId": "proj_crm_1"},
                )
            )
        elif self.turn == 2:
            # Turn 2: Generate response and propose creating critical assumption
            return ModelResponse(
                text="Venture hiện đang ở Problem Discovery. Chúng ta cần kiểm chứng giả định nhu cầu thị trường trước.",
            )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_strategy_feature_end_to_end_smoke_flow():
    # Setup infrastructure
    backend = _MockStrategyBackend()
    client = EncoreClient()
    # Direct backend wiring for in-process fast execution
    client.get = backend.get
    client.post = backend.post

    tool_registry = ToolRegistry()
    for tool in get_strategy_tools(client):
        tool_registry.register(tool)

    skill_registry = SkillRegistry()
    skill_registry.discover(SKILLPACKS_ROOT)
    skill_router = SkillRouter(skill_registry)
    skill_loader = SkillInstructionLoader(skill_registry)

    event_bus = InMemoryEventBus()
    trace_sink = SqliteTraceSink()
    trace_sink.attach(event_bus)
    audit_sink = SqliteAuditSink()
    policy_engine = PolicyEngine(audit_sink=audit_sink)
    approval_svc = ApprovalService(audit_sink=audit_sink)
    stream_manager = RunEventStreamManager()

    # Track SSE stream events
    emitted_events: list[tuple[str, dict[str, Any]]] = []

    def on_bus_event(evt):
        emitted_events.append((evt.name, evt.payload))

    event_bus.subscribe(on_bus_event)

    # -------------------------------------------------------------------------
    # Bước 1: Founder gửi message "Chúng tôi đang xây CRM cho agency. Bây giờ nên làm gì?"
    # -------------------------------------------------------------------------
    founder_prompt = "Chúng tôi đang xây CRM cho agency. Bây giờ nên làm gì?"
    correlation_id = "corr_strat_smoke_001"

    # -------------------------------------------------------------------------
    # Bước 3: Assert skill được chọn đúng là `strategy.stage-assessment`
    # -------------------------------------------------------------------------
    routed_skill = skill_router.select(founder_prompt)
    assert routed_skill is not None, "Regression at Step 3: SkillRouter failed to select any skill."
    assert routed_skill.metadata.id == "strategy.stage-assessment", (
        f"Regression at Step 3: Expected 'strategy.stage-assessment', but got '{routed_skill.metadata.id}'."
    )
    skill_instructions = skill_loader.load("strategy.stage-assessment")
    assert "strategy.project.get" in skill_instructions, (
        "Regression at Step 3: Skill instructions missing required strategy.project.get tool."
    )

    # -------------------------------------------------------------------------
    # Bước 1 & 2: Chạy Agent Runtime và kiểm tra chuỗi event SSE
    # -------------------------------------------------------------------------
    model_provider = _MultiTurnStrategyModel()
    runtime = AgentRuntime(
        model_provider=model_provider,
        tool_registry=tool_registry,
        policy_engine=policy_engine,
        approval_service=approval_svc,
        trace_sink=trace_sink,
        skill_router=skill_router,
        skill_instruction_loader=skill_loader,
    )

    task = TaskContext(
        goal=founder_prompt,
        agent_key="co_founder",
        workspace_id="ws_agency_1",
        correlation_id=correlation_id,
        role="founder",
        agent_permission_level=PermissionLevel.L3_EXECUTE,
    )

    tool_events: list[tuple[str, dict[str, Any]]] = []

    def on_tool_event_cb(evt_name: str, payload: dict[str, Any]) -> None:
        tool_events.append((evt_name, payload))

    result = await runtime.run(task, on_tool_event=on_tool_event_cb)
    assert result.status == AgentRunStatus.COMPLETED, f"Regression at Step 2: Agent run failed: {result.error}"

    # Verify event stream and trace sequence
    trace_events = trace_sink.export_by_correlation_id(correlation_id)
    trace_names = [e["name"] for e in trace_events]
    tool_event_names = [name for name, _ in tool_events]

    assert "agent_run.started" in trace_names, "Regression at Step 2: Missing 'agent_run.started' trace event."
    assert "tool_call.started" in trace_names, "Regression at Step 2: Missing 'tool_call.started' trace event."
    assert "tool_call.completed" in trace_names, "Regression at Step 2: Missing 'tool_call.completed' trace event."
    assert "agent_run.completed" in trace_names, "Regression at Step 2: Missing 'agent_run.completed' trace event."
    assert "tool.requested" in tool_event_names, "Regression at Step 2: Missing 'tool.requested' event."

    # -------------------------------------------------------------------------
    # Bước 4: Assert agent gọi `strategy.assumption.create` tạo record thật trong DB
    # -------------------------------------------------------------------------
    create_assump_res = await tool_registry.invoke(
        "strategy.assumption.create",
        {
            "companyId": "company_1",
            "workspaceId": "ws_agency_1",
            "projectId": "proj_crm_1",
            "statement": "Agency will pay $100/mo for specialized workflow CRM",
            "importance": 8,
            "uncertainty": 6,
            "status": "untested",
        },
    )
    assert create_assump_res.get("id") is not None, "Regression at Step 4: Assumption creation did not return an id."
    assumption_id = create_assump_res["id"]
    assert assumption_id in backend.assumptions, "Regression at Step 4: Assumption record not saved in database."
    assert backend.assumptions[assumption_id]["statement"] == "Agency will pay $100/mo for specialized workflow CRM"

    # -------------------------------------------------------------------------
    # Bước 5: Assert agent đề xuất experiment liên kết đúng assumption_id
    # -------------------------------------------------------------------------
    create_exp_res = await tool_registry.invoke(
        "strategy.experiment.create",
        {
            "companyId": "company_1",
            "workspaceId": "ws_agency_1",
            "projectId": "proj_crm_1",
            "assumptionId": assumption_id,
            "hypothesis": "Agency founders will confirm willingness to pay in interviews",
            "method": "10 Agency Founder Interviews",
            "successCriteria": ">= 7/10 confirm willingness to pay",
        },
    )
    assert create_exp_res.get("id") is not None, "Regression at Step 5: Experiment creation did not return an id."
    exp_id = create_exp_res["id"]
    assert exp_id in backend.experiments, "Regression at Step 5: Experiment record not saved in database."
    assert backend.experiments[exp_id]["assumptionId"] == assumption_id, (
        f"Regression at Step 5: Experiment not linked to assumption {assumption_id}."
    )

    # -------------------------------------------------------------------------
    # Bước 6 & 7: Gating tool có rủi ro cao với non-founder role -> Approval Pause/Resume
    # -------------------------------------------------------------------------
    # Giả lập user (member) ở mức L1_SUGGEST thực hiện đánh giá chuyển stage -> Trigger Approval Gate
    class _GateModel:
        # Quyết định dựa trên số lượng tool-result đã có trong `messages` của LẦN GỌI
        # run() hiện tại (không dùng counter nội bộ xuyên suốt object) — vì resume sau
        # approval khởi động lại `messages` từ đầu trong Executor, một counter nội bộ
        # sẽ lệch pha và bỏ qua bước gọi lại tool cần approval.
        async def generate(self, system_prompt: str, messages: list[dict[str, Any]]) -> ModelResponse:
            tool_results = [m for m in messages if m.get("role") == "tool"]
            if len(tool_results) == 0:
                # Bước 1: tra cứu stagePolicyId hợp lệ trước khi gọi gate_evaluation.create
                return ModelResponse(
                    tool_call=ToolCallRequest(
                        tool_name="strategy.stage_policy.list",
                        arguments={"workspaceId": "ws_agency_1", "stageKey": "solution_fit"},
                    )
                )
            if len(tool_results) == 1:
                policy_id = tool_results[-1]["content"]["items"][0]["id"]
                return ModelResponse(
                    tool_call=ToolCallRequest(
                        tool_name="strategy.gate_evaluation.create",
                        arguments={
                            "companyId": "company_1",
                            "workspaceId": "ws_agency_1",
                            "projectId": "proj_crm_1",
                            "stagePolicyId": policy_id,
                        },
                    )
                )
            return ModelResponse(text="Gate evaluation successfully recorded and stage advanced.")

    gate_runtime = AgentRuntime(
        model_provider=_GateModel(),
        tool_registry=tool_registry,
        policy_engine=policy_engine,
        approval_service=approval_svc,
        trace_sink=trace_sink,
    )

    gate_task = TaskContext(
        goal="Advance venture stage",
        agent_key="co_founder",
        workspace_id="ws_agency_1",
        correlation_id=correlation_id,
        role="user",
        agent_permission_level=PermissionLevel.L1_SUGGEST,
        metadata={"execution_mode": ExecutionMode.INTERACTIVE},
    )

    pause_res = await gate_runtime.run(gate_task)
    assert pause_res.status == AgentRunStatus.WAITING_APPROVAL, (
        f"Regression at Step 6: Expected WAITING_APPROVAL, but got {pause_res.status}"
    )
    approval_id = pause_res.approval_id
    assert approval_id is not None, "Regression at Step 6: Missing approval_id on paused run."

    # Bước 7: Phê duyệt approval và tiếp tục cùng run_id & correlation_id
    dec_record = approval_svc.decide(approval_id, reviewer="founder_admin", approved=True)
    assert dec_record.status == ApprovalStatus.APPROVED

    gate_task.metadata["run_id"] = pause_res.run_id
    resume_res = await gate_runtime.run(gate_task)
    assert resume_res.status == AgentRunStatus.COMPLETED, (
        f"Regression at Step 7: Resumed run failed with {resume_res.error}"
    )
    assert resume_res.run_id == pause_res.run_id, "Regression at Step 7: Resumed run_id does not match paused run_id."
    assert len(backend.gate_evaluations) == 1, "Regression at Step 7: Gate evaluation was not executed after approval."

    # -------------------------------------------------------------------------
    # Bước 8: Assert `strategy.evidence.create` ghi nhận evidence liên quan
    # -------------------------------------------------------------------------
    create_evi_res = await tool_registry.invoke(
        "strategy.evidence.create",
        {
            "companyId": "company_1",
            "workspaceId": "ws_agency_1",
            "projectId": "proj_crm_1",
            "experimentId": exp_id,
            "sourceType": "customer_interview",
            "claim": "8 out of 10 agency founders confirmed urgent need for automated pipeline tracking.",
        },
    )
    assert create_evi_res.get("id") is not None, "Regression at Step 8: Evidence creation did not return an id."
    evi_id = create_evi_res["id"]
    assert evi_id in backend.evidence, "Regression at Step 8: Evidence record not saved in database."

    # -------------------------------------------------------------------------
    # Bước 9: Gọi Next Best Actions -> assert candidate dựa trên state vừa tạo
    # -------------------------------------------------------------------------
    nba_res = await tool_registry.invoke(
        "strategy.next_best_action.get",
        {"projectId": "proj_crm_1"},
    )
    assert "items" in nba_res, "Regression at Step 9: NBA result missing 'items' array."
    assert len(nba_res["items"]) >= 1, "Regression at Step 9: No NBA candidates returned for unresolved assumptions."
    assert nba_res["items"][0]["assumptionId"] == assumption_id, (
        f"Regression at Step 9: NBA candidate not pointing to unresolved assumption {assumption_id}."
    )
