"""Founder Asset Events (Task 6) — router intake for
`founder.asset.commanded.v1` and control-plane dispatch fencing."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass, field
from typing import Any

import pytest

from apps.cosa.events.router import PermissionDenied, Unauthenticated, handle_event
from apps.cosa.events.founder_asset_callback_outbox import InMemoryFounderAssetCallbackOutbox

SECRET = "test-secret"


def _raw(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _sig(payload: dict) -> str:
    return hmac.new(SECRET.encode("utf-8"), _raw(payload), hashlib.sha256).hexdigest()


def _command_payload(**over) -> dict:
    base = {
        "commandId": f"cmd_{uuid.uuid4().hex[:10]}",
        "workspaceId": "ws_1",
        "projectId": "p_1",
        "assetKind": "AGENT",
        "operation": "CLONE",
        "assetRef": {
            "assetId": "agent_builtin_analyst",
            "version": "1.0.0",
            "definitionHash": "sha256:analyst1",
        },
        "expectedVersion": 1,
        "idempotencyKey": "idem_123",
        "reason": "Customizing for marketing ops",
    }
    base.update(over)
    return base


def _env(payload: dict, *, event_type: str = "founder.asset.commanded.v1") -> dict:
    return {
        "eventId": uuid.uuid4().hex,
        "eventType": event_type,
        "schemaVersion": 1,
        "occurredAt": "2026-09-13T10:00:00.000Z",
        "workspaceId": "ws_1",
        "aggregateType": "founder_asset",
        "aggregateId": payload.get("commandId", "cmd_1"),
        "correlationId": "corr_1",
        "actor": {"kind": "user", "id": "u1"},
        "producer": {"service": "company.operations", "version": "1.0.0"},
        "classification": "internal",
        "payload": payload,
    }


class InMemoryLocalAuth:
    def verify(self, signature: str, raw_body: bytes) -> bool:
        return hmac.compare_digest(
            signature, hmac.new(SECRET.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        )


class InMemoryInboxStore:
    def __init__(self) -> None:
        self.records: dict[tuple, dict] = {}

    async def record(self, conn, **kw):
        key = (kw["workspace_id"], kw["event_id"], kw["consumer_name"])
        if key in self.records:
            return "duplicate"
        self.records[key] = dict(kw)
        return "recorded"

    async def set_outcome(self, conn, ws, eid, consumer, outcome, task_id=None):
        key = (ws, eid, consumer)
        if key in self.records:
            self.records[key]["outcome"] = outcome
            self.records[key]["scheduled_task_id"] = task_id


class DummyDb:
    class _Tx:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    def begin(self):
        return self._Tx()


class StubAssetAuthoringHandler:
    def __init__(self) -> None:
        self.commands: list[dict] = []

    async def handle_asset_command(self, payload: dict) -> dict:
        self.commands.append(payload)
        return {
            "status": "SUCCESS",
            "commandId": payload["commandId"],
            "assetRef": payload["assetRef"],
        }


@dataclass
class Deps:
    local_auth: InMemoryLocalAuth = field(default_factory=InMemoryLocalAuth)
    inbox_store: InMemoryInboxStore = field(default_factory=InMemoryInboxStore)
    founder_asset_handler: Any = field(default_factory=StubAssetAuthoringHandler)
    authoring_service: Any = None
    evaluation_service: Any = None
    status_callback_client: Any = None
    founder_asset_callback_outbox: Any = field(default_factory=InMemoryFounderAssetCallbackOutbox)
    db: DummyDb = field(default_factory=DummyDb)
    caller_workspace_id: str | None = None


class RecordingCallbackClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def send_status_callback(self, **kwargs: Any) -> bool:
        self.calls.append(kwargs)
        return True


class FailingCallbackClient:
    def __init__(self, error: Exception) -> None:
        self.error = error

    async def send_status_callback(self, **kwargs: Any) -> Any:
        raise self.error


class FailOnceCallbackClient:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.calls: list[dict[str, Any]] = []

    async def send_status_callback(self, **kwargs: Any) -> bool:
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            raise self.error
        return True



@pytest.mark.asyncio
async def test_replayed_signed_command_does_not_create_second_asset() -> None:
    deps = Deps()
    payload = _command_payload()
    env = _env(payload)
    raw = _raw(env)
    sig = _sig(env)

    first = await handle_event(deps, raw, sig)
    assert first.outcome == "accepted"

    second = await handle_event(deps, raw, sig)
    assert second.outcome == "duplicate"


@pytest.mark.asyncio
async def test_invalid_signature_is_rejected() -> None:
    deps = Deps()
    payload = _command_payload()
    env = _env(payload)
    raw = _raw(env)

    with pytest.raises(Unauthenticated, match="invalid local signature"):
        await handle_event(deps, raw, "bad-sig")


@pytest.mark.asyncio
async def test_foreign_workspace_envelope_is_rejected() -> None:
    deps = Deps(caller_workspace_id="ws_different")
    payload = _command_payload()
    env = _env(payload)
    raw = _raw(env)
    sig = _sig(env)

    with pytest.raises(PermissionDenied, match="cross-workspace envelope"):
        await handle_event(deps, raw, sig)


@pytest.mark.asyncio
async def test_production_wiring_create_evaluate_publish_lifecycle() -> None:
    from apps.cosa.assets.authoring_service import AuthoringService
    from apps.cosa.assets.evaluation_service import EvaluationService
    from packages.agent.assets.contracts import AssetLifecycle
    from packages.agent.assets.repository import InMemoryWorkspaceAssetRepository

    repo = InMemoryWorkspaceAssetRepository()
    eval_svc = EvaluationService(repo)
    auth_svc = AuthoringService(repo, eval_svc)
    callback_client = RecordingCallbackClient()

    deps = Deps(
        founder_asset_handler=None,
        authoring_service=auth_svc,
        evaluation_service=eval_svc,
        status_callback_client=callback_client,
    )

    # 1. CREATE draft
    create_payload = _command_payload(
        operation="CREATE",
        assetKind="AGENT",
        assetRef={"assetId": "agent.ops.specialist", "version": "0.1.0"},
        metadata={
            "name": "Operations Specialist",
            "content": {"system_prompt": "You specialize in operations", "capabilities": []},
        },
    )
    env1 = _env(create_payload)
    res1 = await handle_event(deps, _raw(env1), _sig(env1))
    assert res1.outcome == "accepted"
    assert len(callback_client.calls) == 1
    assert callback_client.calls[0]["status"] == "SUCCESS"
    assert callback_client.calls[0]["operation"] == "CREATE"
    assert callback_client.calls[0]["asset_ref"]["assetId"] == "agent.ops.specialist"

    draft = await repo.get_version("ws_1", "agent.ops.specialist", "0.1.0")
    assert draft is not None
    assert draft.lifecycle == AssetLifecycle.DRAFT

    # 2. EVALUATE draft
    eval_cmd_id = f"cmd_{uuid.uuid4().hex[:10]}"
    eval_payload = _command_payload(
        commandId=eval_cmd_id,
        operation="EVALUATE",
        assetKind="AGENT",
        assetRef={"assetId": "agent.ops.specialist", "version": "0.1.0"},
    )
    env2 = _env(eval_payload)
    res2 = await handle_event(deps, _raw(env2), _sig(env2))
    assert res2.outcome == "accepted"
    assert len(callback_client.calls) == 2
    assert callback_client.calls[1]["status"] == "SUCCESS"
    assert callback_client.calls[1]["operation"] == "EVALUATE"
    assert callback_client.calls[1]["evaluation_summary"] is not None
    assert callback_client.calls[1]["evaluation_summary"]["status"] == "PASS"

    # 3. PUBLISH asset
    pub_cmd_id = f"cmd_{uuid.uuid4().hex[:10]}"
    pub_payload = _command_payload(
        commandId=pub_cmd_id,
        operation="PUBLISH",
        assetKind="AGENT",
        assetRef={
            "assetId": "agent.ops.specialist",
            "version": "0.1.0",
            "definitionHash": draft.definition_hash,
        },
    )
    env3 = _env(pub_payload)
    res3 = await handle_event(deps, _raw(env3), _sig(env3))
    assert res3.outcome == "accepted"
    assert len(callback_client.calls) == 3
    assert callback_client.calls[2]["status"] == "SUCCESS"
    assert callback_client.calls[2]["operation"] == "PUBLISH"
    assert callback_client.calls[2]["command_id"] == pub_cmd_id

    published = await repo.get_version("ws_1", "agent.ops.specialist", "0.1.0")
    assert published is not None
    assert published.lifecycle == AssetLifecycle.PUBLISHED


@pytest.mark.asyncio
async def test_production_wiring_failure_dispatches_failed_status_callback() -> None:
    from apps.cosa.assets.authoring_service import AuthoringService
    from apps.cosa.assets.evaluation_service import EvaluationService
    from packages.agent.assets.repository import InMemoryWorkspaceAssetRepository

    repo = InMemoryWorkspaceAssetRepository()
    eval_svc = EvaluationService(repo)
    auth_svc = AuthoringService(repo, eval_svc)
    callback_client = RecordingCallbackClient()

    deps = Deps(
        founder_asset_handler=None,
        authoring_service=auth_svc,
        evaluation_service=eval_svc,
        status_callback_client=callback_client,
    )

    # PUBLISH non-existent asset -> should catch error and dispatch status=FAILED
    fail_payload = _command_payload(
        operation="PUBLISH",
        assetKind="AGENT",
        assetRef={"assetId": "agent.nonexistent", "version": "0.1.0", "definitionHash": "bad-hash"},
    )
    env = _env(fail_payload)
    res = await handle_event(deps, _raw(env), _sig(env))
    assert res.outcome == "accepted"  # event intake accepted the envelope
    assert len(callback_client.calls) == 1
    assert callback_client.calls[0]["status"] == "FAILED"
    assert callback_client.calls[0]["safe_reason_code"] is not None


@pytest.mark.asyncio
async def test_production_wiring_clone_builtin_asset() -> None:
    from apps.cosa.assets.authoring_service import AuthoringService
    from apps.cosa.assets.evaluation_service import EvaluationService
    from packages.agent.assets.contracts import AssetLifecycle
    from packages.agent.assets.repository import InMemoryWorkspaceAssetRepository

    repo = InMemoryWorkspaceAssetRepository()
    eval_svc = EvaluationService(repo)
    auth_svc = AuthoringService(repo, eval_svc)
    callback_client = RecordingCallbackClient()

    deps = Deps(
        founder_asset_handler=None,
        authoring_service=auth_svc,
        evaluation_service=eval_svc,
        status_callback_client=callback_client,
    )

    # Pre-seed the source asset so clone has an immutable default to copy from
    from packages.agent.assets.contracts import AssetKind, AssetScope, WorkspaceAssetDraft
    await repo.create_draft(
        workspace_id="ws_1",
        draft=WorkspaceAssetDraft(
            asset_id="agent.ops.analyst",
            version="1.0.0",
            name="Ops Analyst",
            description="Builtin analyst",
            kind=AssetKind.AGENT,
            content={"instructions": "analyst instructions", "model": "gpt-4o"},
            scope=AssetScope.workspace(),
            created_by="system",
        ),
    )

    clone_payload = _command_payload(
        operation="CLONE",
        assetKind="AGENT",
        assetRef={
            "assetId": "agent.ops.analyst",
            "version": "1.0.0",
            "definitionHash": "sha256:analyst",
        },
    )
    env = _env(clone_payload)
    res = await handle_event(deps, _raw(env), _sig(env))
    assert res.outcome == "accepted"
    assert len(callback_client.calls) == 1
    assert callback_client.calls[0]["status"] == "SUCCESS"
    assert callback_client.calls[0]["operation"] == "CLONE"
    assert callback_client.calls[0]["asset_ref"]["assetId"] == "clone.agent.ops.analyst"

    cloned = await repo.get_version("ws_1", "clone.agent.ops.analyst", "0.1.0")
    assert cloned is not None
    assert cloned.lifecycle == AssetLifecycle.DRAFT


@pytest.mark.asyncio
async def test_production_wiring_clone_nonexistent_asset_dispatches_failed_callback() -> None:
    from apps.cosa.assets.authoring_service import AuthoringService
    from apps.cosa.assets.evaluation_service import EvaluationService
    from packages.agent.assets.repository import InMemoryWorkspaceAssetRepository

    repo = InMemoryWorkspaceAssetRepository()
    eval_svc = EvaluationService(repo)
    auth_svc = AuthoringService(repo, eval_svc)
    callback_client = RecordingCallbackClient()

    deps = Deps(
        founder_asset_handler=None,
        authoring_service=auth_svc,
        evaluation_service=eval_svc,
        status_callback_client=callback_client,
    )

    # Attempt to clone non-existent asset without seeding
    clone_payload = _command_payload(
        operation="CLONE",
        assetKind="AGENT",
        assetRef={
            "assetId": "nonexistent.agent",
            "version": "1.0.0",
            "definitionHash": "sha256:missing",
        },
    )
    env = _env(clone_payload)
    res = await handle_event(deps, _raw(env), _sig(env))
    assert res.outcome == "accepted"
    assert len(callback_client.calls) == 1
    assert callback_client.calls[0]["status"] == "FAILED"
    assert "not found for clone" in callback_client.calls[0]["safe_reason_code"]



@pytest.mark.asyncio
async def test_callback_delivery_failure_marks_outcome_failed_in_inbox() -> None:
    from apps.cosa.assets.authoring_service import AuthoringService
    from apps.cosa.assets.evaluation_service import EvaluationService
    from apps.cosa.events.founder_asset_callback_client import FounderAssetCallbackDeliveryError
    from packages.agent.assets.repository import InMemoryWorkspaceAssetRepository

    repo = InMemoryWorkspaceAssetRepository()
    eval_svc = EvaluationService(repo)
    auth_svc = AuthoringService(repo, eval_svc)
    failing_client = FailingCallbackClient(FounderAssetCallbackDeliveryError("cmd_fail", "Connection refused"))

    deps = Deps(
        founder_asset_handler=None,
        authoring_service=auth_svc,
        evaluation_service=eval_svc,
        status_callback_client=failing_client,
    )

    create_payload = _command_payload(
        operation="CREATE",
        assetKind="AGENT",
        assetRef={"assetId": "agent.ops.failing_cb", "version": "0.1.0"},
        metadata={"name": "Test Agent", "content": {}},
    )
    env = _env(create_payload)
    res = await handle_event(deps, _raw(env), _sig(env))
    assert res.outcome == "failed"
    assert "callback delivery failed" in (res.reason or "")


@pytest.mark.asyncio
async def test_duplicate_command_retries_durable_callback_without_replaying_authoring() -> None:
    from apps.cosa.assets.authoring_service import AuthoringService
    from apps.cosa.assets.evaluation_service import EvaluationService
    from apps.cosa.events.founder_asset_callback_client import FounderAssetCallbackDeliveryError
    from apps.cosa.events.founder_asset_callback_outbox import InMemoryFounderAssetCallbackOutbox
    from packages.agent.assets.repository import InMemoryWorkspaceAssetRepository

    repo = InMemoryWorkspaceAssetRepository()
    eval_svc = EvaluationService(repo)
    base_authoring = AuthoringService(repo, eval_svc)

    class CountingCreateAuthoringService:
        def __init__(self) -> None:
            self.create_calls = 0

        async def create_agent_draft(self, **kwargs: Any):
            self.create_calls += 1
            return await base_authoring.create_agent_draft(**kwargs)

    auth_svc = CountingCreateAuthoringService()
    callback_outbox = InMemoryFounderAssetCallbackOutbox()
    callback_client = FailOnceCallbackClient(
        FounderAssetCallbackDeliveryError("cmd_retry_callback", "Connection refused")
    )
    deps = Deps(
        founder_asset_handler=None,
        authoring_service=auth_svc,
        evaluation_service=eval_svc,
        status_callback_client=callback_client,
        founder_asset_callback_outbox=callback_outbox,
    )
    command = _command_payload(
        commandId="cmd_retry_callback",
        operation="CREATE",
        assetKind="AGENT",
        assetRef={"assetId": "agent.ops.retry_callback", "version": "0.1.0"},
        metadata={"name": "Retry callback agent", "content": {}},
    )
    env = _env(command)
    raw = _raw(env)
    sig = _sig(env)

    first = await handle_event(deps, raw, sig)
    assert first.outcome == "failed"
    pending = await callback_outbox.get("ws_1", "cmd_retry_callback")
    assert pending is not None
    assert pending.delivery_status == "PENDING"
    assert pending.delivery_attempts == 1

    replay = await handle_event(deps, raw, sig)
    assert replay.outcome == "accepted"
    delivered = await callback_outbox.get("ws_1", "cmd_retry_callback")
    assert delivered is not None
    assert delivered.delivery_status == "DELIVERED"
    assert delivered.delivery_attempts == 2
    assert len(callback_client.calls) == 2
    assert auth_svc.create_calls == 1
    assert await repo.get_version("ws_1", "agent.ops.retry_callback", "0.1.0") is not None
