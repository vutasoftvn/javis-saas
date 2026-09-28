"""C1 E2E (phía apps/cosa) — agent workspace clone từ built-in `operations`.

CLONE → EDIT_DRAFT (tên + addendum + bỏ 1 capability) → EVALUATE PASS → PUBLISH đi qua đúng
đường lệnh company: envelope `founder.asset.commanded.v1` đã ký → `handle_event` (router) →
`dispatch_founder_asset_command` → AuthoringService/EvaluationService thật → callback outbox bền →
callback client (thu lại payload gửi về company). Sau đó worker chạy run chat với
`project_agent_deployment_id`: authority lấy từ company (mock HTTP client), asset PUBLISHED load
theo exact hash, spec hiệu lực có override, capability bị bỏ không phải tool của run.

Phía company (biên nhận publish, createWorkspaceAgent, deployAgentToProject, grant) được kiểm ở
services/company/operations/tests/founder-agent-clone.service.test.ts.
Spec: docs/superpowers/specs/2026-09-27-agent-clone-executor-design.md.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass, field
from typing import Any

import pytest
from agent.assets.contracts import AssetLifecycle
from agent.assets.repository import InMemoryWorkspaceAssetRepository
from agent_testkit.fake_sdk_model import FakeSDKModel, text_response, tool_call_response

from apps.cosa.agents.agent_profile_specs import AGENT_PROFILE_SPECS
from apps.cosa.agents.seed import seed_cosa_runtime_specs
from apps.cosa.api.event_stream import CosaEventStreamManager
from apps.cosa.assets.authoring_service import AuthoringService
from apps.cosa.assets.evaluation_service import EvaluationService
from apps.cosa.events.founder_asset_callback_outbox import InMemoryFounderAssetCallbackOutbox
from apps.cosa.events.router import handle_event
from apps.cosa.worker.handlers import execute_run_task
from tests.apps.cosa.worker.test_handlers import _payload, _plane

SECRET = "test-secret"
WS = "ws_1"
PROJECT = "proj_1"
DEPLOYMENT = "dep_custom_1"
MEMBER = "wm_custom_ops"
OPS = AGENT_PROFILE_SPECS["operations"]
DROPPED = "operations.task.advance"
ADDENDUM = "Luôn trả lời bằng ba gạch đầu dòng, ưu tiên việc tuần này của Sao Mai."
PROMPT = "Liệt kê các việc tuần này của dự án"


def _tool(capability_id: str) -> str:
    """Tên tool kernel đưa cho model (dấu chấm → gạch dưới)."""
    return capability_id.replace(".", "_")


# --- Harness router (cùng dạng tests/apps/cosa/events/test_founder_asset_events.py) --------


def _raw(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _sig(payload: dict) -> str:
    return hmac.new(SECRET.encode("utf-8"), _raw(payload), hashlib.sha256).hexdigest()


class _LocalAuth:
    def verify(self, signature: str, raw_body: bytes) -> bool:
        expected = hmac.new(SECRET.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected)


class _Inbox:
    def __init__(self) -> None:
        self.records: dict[tuple, dict] = {}

    async def record(self, conn, **kw):
        key = (kw["workspace_id"], kw["event_id"], kw["consumer_name"])
        if key in self.records:
            return "duplicate"
        self.records[key] = dict(kw)
        return "recorded"

    async def set_outcome(self, conn, ws, eid, consumer, outcome, task_id=None):
        self.records.setdefault((ws, eid, consumer), {})["outcome"] = outcome


class _Db:
    class _Tx:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    def begin(self):
        return self._Tx()


class _Callbacks:
    """Đứng vị trí HTTP callback về company: thu payload đúng như gửi đi."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def send_status_callback(self, **kwargs: Any) -> bool:
        self.calls.append(kwargs)
        return True


@dataclass
class _Deps:
    authoring_service: Any
    evaluation_service: Any
    status_callback_client: _Callbacks = field(default_factory=_Callbacks)
    local_auth: _LocalAuth = field(default_factory=_LocalAuth)
    inbox_store: _Inbox = field(default_factory=_Inbox)
    founder_asset_handler: Any = None
    founder_asset_callback_outbox: Any = field(default_factory=InMemoryFounderAssetCallbackOutbox)
    db: _Db = field(default_factory=_Db)
    caller_workspace_id: str | None = None


def _command(operation: str, asset_ref: dict, metadata: dict | None = None) -> dict:
    """Payload giống hệt `commandFounderAsset` (company) đặt vào outbox."""
    command_id = str(uuid.uuid4().int)[:18]
    return {
        "commandId": command_id,
        "workspaceId": WS,
        "projectId": PROJECT,
        "assetKind": "AGENT",
        "operation": operation,
        "assetRef": asset_ref,
        "expectedVersion": 1,
        "idempotencyKey": f"idem-{command_id}",
        "reason": "Founder tạo agent vận hành riêng",
        "metadata": metadata or {},
    }


async def _send(deps: _Deps, payload: dict) -> dict[str, Any]:
    env = {
        "eventId": uuid.uuid4().hex,
        "eventType": "founder.asset.commanded.v1",
        "schemaVersion": 1,
        "occurredAt": "2026-09-28T10:00:00.000Z",
        "workspaceId": WS,
        "projectId": PROJECT,
        "aggregateType": "founder_asset",
        "aggregateId": payload["commandId"],
        "correlationId": payload["commandId"],
        "actor": {"kind": "user", "id": "u_founder"},
        "producer": {"service": "company.operations", "version": "1.0.0"},
        "classification": "internal",
        "payload": payload,
    }
    before = len(deps.status_callback_client.calls)
    res = await handle_event(deps, _raw(env), _sig(env))
    assert res.outcome == "accepted", res
    [callback] = deps.status_callback_client.calls[before:]
    assert callback["command_id"] == payload["commandId"]
    return callback


class _RecordingModel(FakeSDKModel):
    """FakeSDKModel + ghi lại system prompt và tên tool mà kernel đưa cho model."""

    def __init__(self, responses: list[Any]) -> None:
        super().__init__(responses=responses)
        self.seen: list[dict[str, Any]] = []

    async def get_response(self, *args, **kwargs):
        system = kwargs.get("system_instructions", args[0] if args else None)
        tools = kwargs.get("tools", args[3] if len(args) > 3 else [])
        self.seen.append({"system": system or "", "tools": [t.name for t in tools or []]})
        return await super().get_response(*args, **kwargs)


# --- Kịch bản -------------------------------------------------------------------------------


async def _publish_custom_agent(repo: InMemoryWorkspaceAssetRepository, plane: Any) -> dict:
    evaluation = EvaluationService(repo, spec_registry=plane.spec_registry)
    deps = _Deps(
        authoring_service=AuthoringService(repo, evaluation, spec_registry=plane.spec_registry),
        evaluation_service=evaluation,
    )

    clone = await _send(
        deps,
        _command(
            "CLONE",
            {"assetId": OPS.id},
            {"name": "Vận hành Sao Mai", "description": "Agent vận hành riêng của Sao Mai"},
        ),
    )
    assert clone["status"] == "SUCCESS", clone
    ref = clone["asset_ref"]
    draft = await repo.get_version(WS, ref["assetId"], ref["version"])
    assert draft.origin.asset_id == OPS.id and draft.lifecycle == AssetLifecycle.DRAFT

    content = {
        **draft.content_json,
        "name": "Vận hành gọn",
        "instructions_addendum": ADDENDUM,
        "capability_refs": [c for c in OPS.capability_refs if c != DROPPED],
    }
    edit = await _send(deps, _command("EDIT_DRAFT", ref, {"content": content}))
    assert edit["status"] == "SUCCESS", edit
    ref = edit["asset_ref"]
    assert ref["definitionHash"] != clone["asset_ref"]["definitionHash"]

    evaluate = await _send(deps, _command("EVALUATE", ref))
    assert evaluate["status"] == "SUCCESS", evaluate
    assert evaluate["evaluation_summary"]["status"] == "PASS"

    publish = await _send(deps, _command("PUBLISH", ref))
    assert publish["status"] == "SUCCESS", publish
    assert publish["asset_ref"] == ref
    assert publish["agent_manifest"] == {
        "originProfileKey": "operations",
        "originSpec": {"id": OPS.id, "version": OPS.version, "definitionHash": OPS.compute_hash()},
        "capabilityRefs": content["capability_refs"],
        "displayName": "Vận hành gọn",
    }
    published = await repo.get_version(WS, ref["assetId"], ref["version"])
    assert published.lifecycle == AssetLifecycle.PUBLISHED
    return ref


def _authority(ref: dict, **over: Any) -> dict:
    """Đúng shape `getProjectDeploymentAuthority` của company."""
    base = {
        "workspaceId": WS,
        "projectAgentDeploymentId": DEPLOYMENT,
        "workspaceAgentId": "wa_custom_1",
        "workforceMemberId": MEMBER,
        "agentSpec": {
            "id": ref["assetId"],
            "version": ref["version"],
            "definitionHash": ref["definitionHash"],
        },
        "roleIds": [],
        "projectId": PROJECT,
        "state": "ACTIVE",
        "capabilityRestrictions": [],
    }
    base.update(over)
    return base


async def _plane_with(responses: list[Any]) -> tuple[Any, InMemoryWorkspaceAssetRepository]:
    plane = _plane()
    plane.kernel._model = _RecordingModel(responses)
    await seed_cosa_runtime_specs(
        spec_registry=plane.spec_registry, capability_registry=plane.capability_registry
    )
    repo = InMemoryWorkspaceAssetRepository()
    plane.workspace_asset_repository = repo
    plane.company_client.get.side_effect = lambda path, *a, **k: {"data": []}
    return plane, repo


async def _events(plane: Any, run_id: str, event_type: str) -> list[dict]:
    events = await plane.stream_event_repository.list_since(run_id)
    return [e.payload for e in events if e.event_type == event_type]


async def _run(plane: Any, run_id: str, **payload: Any) -> None:
    await execute_run_task(
        plane,
        CosaEventStreamManager(),
        _payload(
            run_id=run_id,
            user_prompt=PROMPT,
            project_agent_deployment_id=DEPLOYMENT,
            **payload,
        ),
    )


@pytest.mark.asyncio
async def test_clone_edit_evaluate_publish_then_run_custom_agent() -> None:
    plane, repo = await _plane_with(
        [
            tool_call_response("call_read", _tool("business.read"), '{"domain": "okr"}'),
            text_response("- Việc 1\n- Việc 2\n- Việc 3"),
        ]
    )
    ref = await _publish_custom_agent(repo, plane)
    plane.company_client.get_project_agent_deployment_authority.return_value = _authority(ref)
    compliance_specs: list[str] = []
    real_resolve = plane.compliance_resolver.resolve_for_run

    async def _spy_resolve(req: Any, spec: Any) -> Any:
        compliance_specs.append(spec.id)
        return await real_resolve(req, spec)

    plane.compliance_resolver.resolve_for_run = _spy_resolve

    # Client gửi agent_profile khác: worker phải bỏ qua và dùng profile của agent gốc.
    await _run(plane, "run_custom_ok", agent_profile="finance")

    assert await _events(plane, "run_custom_ok", "run.completed")
    assert not await _events(plane, "run_custom_ok", "run.failed")
    plane.company_client.get_project_agent_deployment_authority.assert_awaited_with(
        WS, PROJECT, DEPLOYMENT
    )

    run = await plane.repository.get_run("run_custom_ok")
    assert run.root_executable_id == f"workspace.{WS}.{ref['assetId']}"
    assert run.root_executable_version == ref["version"]

    first_call = plane.kernel._model.seen[0]
    assert ADDENDUM in first_call["system"]
    # Tool của run = đúng capability của agent gốc trừ capability bị bỏ, không thêm gì.
    assert set(first_call["tools"]) == {_tool(c) for c in OPS.capability_refs if c != DROPPED}
    # Compliance đánh giá theo spec built-in gốc (catalog AI system của agent gốc).
    assert compliance_specs == [OPS.id]
    get_paths = [c.args[0] for c in plane.company_client.get.await_args_list]
    assert "/operations/objectives" in get_paths


@pytest.mark.asyncio
async def test_dropped_capability_cannot_be_used_by_the_custom_agent() -> None:
    plane, repo = await _plane_with(
        [
            tool_call_response("call_adv", _tool(DROPPED), '{"task_id": "t1", "status": "done"}'),
            text_response("Không thể chuyển trạng thái công việc."),
        ]
    )
    ref = await _publish_custom_agent(repo, plane)
    plane.company_client.get_project_agent_deployment_authority.return_value = _authority(ref)

    await _run(plane, "run_custom_dropped")

    assert _tool(DROPPED) not in plane.kernel._model.seen[0]["tools"]
    # Không có ticket live authorization, không có ghi nào tới company, không chờ duyệt.
    post_paths = [c.args[0] for c in plane.company_client.post.await_args_list]
    assert "/identity/agent-authorization/tickets" not in post_paths
    assert not plane.company_client.patch.await_args_list
    assert not await _events(plane, "run_custom_dropped", "approval.required")


@pytest.mark.asyncio
async def test_clone_adding_capability_outside_origin_is_rejected() -> None:
    plane, repo = await _plane_with([])
    evaluation = EvaluationService(repo, spec_registry=plane.spec_registry)
    deps = _Deps(
        authoring_service=AuthoringService(repo, evaluation, spec_registry=plane.spec_registry),
        evaluation_service=evaluation,
    )
    clone = await _send(deps, _command("CLONE", {"assetId": OPS.id}, {"name": "Leo quyền"}))
    draft = await repo.get_version(WS, clone["asset_ref"]["assetId"], "0.1.0")
    content = {
        **draft.content_json,
        "capability_refs": [*OPS.capability_refs, "finance.transaction.record"],
    }
    edit = await _send(deps, _command("EDIT_DRAFT", clone["asset_ref"], {"content": content}))

    evaluate = await _send(deps, _command("EVALUATE", edit["asset_ref"]))
    assert evaluate["status"] == "REJECTED"
    assert evaluate["safe_reason_code"] == "AGENT_CAPABILITY_ESCALATION"

    publish = await _send(deps, _command("PUBLISH", edit["asset_ref"]))
    assert publish["status"] == "FAILED"
    assert "agent_manifest" not in publish
    stored = await repo.get_version(WS, edit["asset_ref"]["assetId"], "0.1.0")
    assert stored.lifecycle != AssetLifecycle.PUBLISHED


@pytest.mark.parametrize(
    ("authority_over", "tamper", "code"),
    [
        ({"state": "PAUSED"}, None, "deployment_not_active"),
        ({"projectId": "proj_other"}, None, "deployment_scope_mismatch"),
        ({"workspaceId": "ws_other"}, None, "deployment_scope_mismatch"),
        (
            {
                "agentSpec": {
                    "id": OPS.id,
                    "version": OPS.version,
                    "definitionHash": OPS.compute_hash(),
                }
            },
            None,
            "deployment_not_workspace_agent",
        ),
        ({}, "hash", "workspace_agent_hash_mismatch"),
        ({}, "unpublish", "workspace_agent_not_published"),
        ({}, "retire", "workspace_agent_not_published"),
        ({}, "missing", "workspace_agent_not_found"),
    ],
)
@pytest.mark.asyncio
async def test_custom_run_fails_closed(authority_over, tamper, code) -> None:
    plane, repo = await _plane_with([text_response("không được chạy")])
    ref = await _publish_custom_agent(repo, plane)
    authority = _authority(ref, **authority_over)
    key = (WS, ref["assetId"], ref["version"])
    if tamper == "hash":
        authority["agentSpec"] = {**authority["agentSpec"], "definitionHash": "sha256:other"}
    elif tamper == "unpublish":
        repo._versions[key].lifecycle = AssetLifecycle.REVIEW_REQUIRED
    elif tamper == "retire":
        repo._versions[key].lifecycle = AssetLifecycle.RETIRED
    elif tamper == "missing":
        authority["agentSpec"] = {**authority["agentSpec"], "version": "9.9.9"}
    plane.company_client.get_project_agent_deployment_authority.return_value = authority

    await _run(plane, f"run_fail_{code}")

    [failed] = await _events(plane, f"run_fail_{code}", "run.failed")
    assert failed["error"] == code
    assert plane.kernel._model.call_count == 0


@pytest.mark.asyncio
async def test_custom_run_rejects_when_company_is_unreachable() -> None:
    plane, repo = await _plane_with([])
    await _publish_custom_agent(repo, plane)
    plane.company_client.get_project_agent_deployment_authority.side_effect = RuntimeError("down")

    await _run(plane, "run_fail_unreachable")

    [failed] = await _events(plane, "run_fail_unreachable", "run.failed")
    assert failed["error"] == "deployment_authority_unavailable"


@pytest.mark.asyncio
async def test_model_route_of_custom_agent_is_the_origin_agent_route() -> None:
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from apps.cosa.worker.run_core import bind_route_to_run

    resolver = AsyncMock()
    spec = OPS.model_copy(
        update={
            "id": f"workspace.{WS}.custom.operations.1",
            "metadata": {**OPS.metadata, "origin_agent_spec_id": OPS.id},
        }
    )
    await bind_route_to_run(resolver, SimpleNamespace(workspace_id=WS), spec)
    resolver.resolve_route.assert_awaited_once_with(WS, OPS.id)
