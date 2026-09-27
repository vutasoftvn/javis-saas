"""Vòng WGA đầy đủ phía worker với company giả lập TỐI THIỂU nhưng đúng luật:
- agent-claimable chỉ trả task có mọi dependency 'done' (như task.service.ts);
- advance('done') bắt buộc evidenceRefs (như advanceTaskByAgentService).

Chứng minh G1 (task phụ thuộc được mở khoá), G3 (project scope), G9 (tiến độ
về chat) cùng chạy với nhau — không thay cho E2E Encore thật (cần `encore` CLI).
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from agent.contracts.run import RunStatus

from apps.cosa.capabilities.client import CompanyServiceError
from apps.cosa.worker import wga_run

_PLAN = json.dumps(
    {
        "items": [
            {
                "title": "List open tasks",
                "decision_reason": "Know the current backlog",
                "evidence_refs": [],
                "suggested_domain": "operations",
                "expected_capability": "operations.task.list",
                "priority": "high",
            },
            {
                "title": "Draft follow-up tasks",
                "decision_reason": "Turn backlog into next steps",
                "evidence_refs": [],
                "suggested_domain": "operations",
                "expected_capability": "operations.task.create_draft",
                "depends_on_titles": ["List open tasks"],
            },
        ]
    }
)


class FakeCompany:
    def __init__(self) -> None:
        self.plan_body: dict | None = None
        self.tasks: dict[str, dict] = {}

    def accept(self) -> None:
        """Materialize như acceptExecutionPlanService (AUTO, gán AI member)."""
        assert self.plan_body is not None
        title_to_id: dict[str, str] = {}
        for i, it in enumerate(self.plan_body["items"], start=1):
            title_to_id[it["title"]] = str(i)
        for i, it in enumerate(self.plan_body["items"], start=1):
            self.tasks[str(i)] = {
                "taskId": str(i),
                "title": it["title"],
                "decisionReason": it["decisionReason"],
                "expectedCapability": it["expectedCapability"],
                "ownerAgentProfile": "operations",
                "autonomyClass": "AUTO",
                "planItemId": f"it{i}",
                "planId": "pl1",
                "projectId": self.plan_body["projectId"],
                "planOrigin": self.plan_body["origin"],
                "planOriginRef": self.plan_body["originRef"],
                "status": "todo",
                "deps": [title_to_id[d] for d in it["dependsOnTitles"]],
            }

    async def get(self, path, params=None, headers=None):
        assert path == "/operations/tasks/agent-claimable"
        out = []
        for t in self.tasks.values():
            if t["status"] != "todo":
                continue
            if params.get("projectId") and t["projectId"] != params["projectId"]:
                continue
            if any(self.tasks[d]["status"] != "done" for d in t["deps"]):
                continue
            out.append({k: v for k, v in t.items() if k not in ("status", "deps")})
        return {"tasks": out[: params.get("limit", 5)]}

    async def post(self, path, json=None, params=None, headers=None):
        if path == "/operations/execution-plans":
            self.plan_body = json
            return {"id": "pl1"}
        if path.endswith("/advance"):
            task = self.tasks[path.split("/")[3]]
            if json["toStatus"] == "done":
                if not json.get("evidenceRefs"):
                    raise CompanyServiceError("EVIDENCE_REQUIRED", status_code=400)
                if task["status"] not in ("in_progress", "waiting_approval"):
                    raise CompanyServiceError("bad transition", status_code=400)
            task["status"] = json["toStatus"]
            return {"status": task["status"]}
        raise AssertionError(f"unexpected POST {path}")


@pytest.fixture(autouse=True)
def _patch(monkeypatch):
    async def _fake_resolve_spec(plane, *, run_id, local_spec):
        return SimpleNamespace(to_pinned_identity=lambda: "cosa.agents.operations@x#h")

    monkeypatch.setattr("apps.cosa.worker.run_core.resolve_spec", _fake_resolve_spec)
    monkeypatch.setenv("COSA_COMPANY_DELEGATION_SECRET", "x" * 40)


def _plane(company: FakeCompany):
    kernel = AsyncMock()

    async def run(req, spec):
        if req.run_id.startswith("wga_decomp"):
            return SimpleNamespace(
                status=RunStatus.COMPLETED, final_output={"response": _PLAN}, errors=[]
            )
        return SimpleNamespace(
            status=RunStatus.COMPLETED, final_output={"response": f"did {req.run_id}"}, errors=[]
        )

    kernel.run.side_effect = run
    resolver = AsyncMock()
    resolver.resolve_for_run.return_value = {"_company_delegation_token": "jwt"}
    return SimpleNamespace(
        company_client=company,
        kernel=kernel,
        compliance_resolver=resolver,
        spec_registry=SimpleNamespace(),
        conversation_repository=AsyncMock(),
        artifact_repository=AsyncMock(),
        scheduler=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_chat_goal_to_done_tasks_with_dependency_and_progress_in_chat():
    company = FakeCompany()
    plane = _plane(company)

    await wga_run.execute_goal_decomposition_task(
        plane,
        None,
        {
            "run_id": "wga_decomp_1",
            "workspace_id": "ws1",
            "project_id": "proj1",
            "weekly_plan_id": "77",
            "goal_text": "Clean up the backlog",
            "origin": "chat",
            "origin_ref": "conv_9",
            "actor_id": "42",
        },
    )
    assert company.plan_body is not None
    company.accept()

    sweep = {"run_id": "s", "workspace_id": "ws1", "project_id": "proj1", "actor_id": "42"}
    # Lượt 1: chỉ A claimable (B phụ thuộc A) -> A done nhờ evidence.
    await wga_run.execute_workspace_task_sweep_task(plane, None, sweep)
    assert company.tasks["1"]["status"] == "done"
    assert company.tasks["2"]["status"] == "todo"
    # Lượt 2: A đã done -> B được mở khoá và cũng done (trước fix: kẹt mãi).
    await wga_run.execute_workspace_task_sweep_task(plane, None, sweep)
    assert company.tasks["2"]["status"] == "done"

    runs = [c.args[0] for c in plane.kernel.run.await_args_list]
    assert all(r.metadata["project_id"] == "proj1" for r in runs)

    chat_msgs = [c.args[0] for c in plane.conversation_repository.add_message.await_args_list]
    assert all(m.conversation_id == "conv_9" for m in chat_msgs)
    progress = [json.loads(m.content) for m in chat_msgs if m.content.startswith("{")]
    assert [p["done"] for p in progress] == [["List open tasks"], ["Draft follow-up tasks"]]
