"""B5 (Task 6b, plan hub vận hành đợt 2) — `execute_scheduled_session_task`: uỷ quyền trước
theo snapshot (Task 6), preflight founder-notify/connector TRƯỚC khi tạo conversation/gọi
model, `blocked_reauth`.

Dùng chung fixture `worker_setup` với `test_scheduled_session_worker.py` (không định nghĩa
lại DB/plane giả). Mock `CompanyServiceClient`/`ConnectorGrantHttpClient` ở đúng module
`apps.cosa.worker.scheduled_tasks` (không mock httpx trần cho 2 client này — chỉ mock httpx
cho snapshot fetch + completion report, đúng cách các test khác trong repo đã làm)."""

from unittest.mock import AsyncMock, patch

import pytest

from apps.cosa.api.event_stream import CosaEventStreamManager
from apps.cosa.capabilities.client import CompanyServiceError
from apps.cosa.worker.handlers import execute_scheduled_session_task
from tests.apps.cosa.test_scheduled_session_worker import worker_setup  # noqa: F401


def _snapshot_response(
    *,
    pre_authorized_capability_ids: list[str],
    founder_member_id: str | None = "member_1",
    founder_user_id: str | None = "user_1",
    token_budget_per_run: int | None = None,
):
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json = lambda: {
        "organizationId": "ws_sched",
        "promptTemplateSnapshot": "Run digest",
        "agentProfileSnapshot": "operations",
        "projectIdSnapshot": "proj_test_1",
        "preAuthorizedCapabilityIdsSnapshot": pre_authorized_capability_ids,
        "founderMemberIdSnapshot": founder_member_id,
        "founderUserIdSnapshot": founder_user_id,
        "tokenBudgetPerRunSnapshot": token_budget_per_run,
    }
    return mock_resp


@pytest.mark.asyncio
async def test_missing_founder_identity_in_snapshot_blocks_reauth_before_conversation(
    worker_setup,  # noqa: F811
):
    plane = worker_setup["plane"]
    conv_repo = worker_setup["conv_repo"]
    stream_mgr = CosaEventStreamManager()

    mock_post = AsyncMock()
    with (
        patch(
            "apps.cosa.worker.scheduled_tasks.resolve_platform_control_plane_url",
            return_value="http://cp",
        ),
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
        patch("httpx.AsyncClient.post", new=mock_post),
    ):
        mock_get.return_value = _snapshot_response(
            pre_authorized_capability_ids=["founder.notify.send"],
            founder_user_id=None,
        )
        with pytest.raises(ValueError, match="preauthorization_snapshot_invalid"):
            await execute_scheduled_session_task(
                plane,
                stream_mgr,
                {"schedule_execution_id": "exec_no_founder", "workspace_id": "ws_sched"},
                run_id="run_no_founder",
            )

    _, total = await conv_repo.list_conversations(workspace_id="ws_sched", project_id="proj_test_1")
    assert total == 0
    assert mock_post.await_count == 1
    sent = mock_post.call_args.kwargs["json"]
    assert sent["state"] == "blocked_reauth"
    assert "preauthorization_snapshot_invalid" in sent["error"]


@pytest.mark.asyncio
async def test_founder_notify_preflight_unavailable_blocks_reauth(worker_setup):  # noqa: F811
    plane = worker_setup["plane"]
    conv_repo = worker_setup["conv_repo"]
    stream_mgr = CosaEventStreamManager()

    mock_post = AsyncMock()
    mock_company_get = AsyncMock(
        side_effect=CompanyServiceError(
            "Company Service Error (400): founder_channel_unavailable: no verified channel",
            status_code=400,
        )
    )
    with (
        patch(
            "apps.cosa.worker.scheduled_tasks.resolve_platform_control_plane_url",
            return_value="http://cp",
        ),
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
        patch("httpx.AsyncClient.post", new=mock_post),
        patch("apps.cosa.worker.scheduled_tasks.CompanyServiceClient") as mock_client_cls,
    ):
        mock_get.return_value = _snapshot_response(
            pre_authorized_capability_ids=["founder.notify.send"]
        )
        mock_client_cls.return_value.get = mock_company_get

        with pytest.raises(ValueError, match="founder_channel_unavailable"):
            await execute_scheduled_session_task(
                plane,
                stream_mgr,
                {"schedule_execution_id": "exec_no_channel", "workspace_id": "ws_sched"},
                run_id="run_no_channel",
            )

    mock_company_get.assert_awaited_once()
    called_headers = mock_company_get.call_args.kwargs["headers"]
    assert called_headers["Authorization"].startswith("Bearer ")
    assert called_headers["X-Workspace-Id"] == "ws_sched"

    _, total = await conv_repo.list_conversations(workspace_id="ws_sched", project_id="proj_test_1")
    assert total == 0, "không được tạo conversation khi preflight chặn"
    sent = mock_post.call_args.kwargs["json"]
    assert sent["state"] == "blocked_reauth"
    assert "founder_channel_unavailable" in sent["error"]


@pytest.mark.asyncio
async def test_founder_notify_preflight_ambiguous_is_failed_not_blocked_reauth(worker_setup):  # noqa: F811
    plane = worker_setup["plane"]
    stream_mgr = CosaEventStreamManager()

    mock_post = AsyncMock()
    mock_company_get = AsyncMock(
        side_effect=CompanyServiceError(
            "Company Service Error (400): founder_channel_ambiguous: nhiều kênh dùng được",
            status_code=400,
        )
    )
    with (
        patch(
            "apps.cosa.worker.scheduled_tasks.resolve_platform_control_plane_url",
            return_value="http://cp",
        ),
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
        patch("httpx.AsyncClient.post", new=mock_post),
        patch("apps.cosa.worker.scheduled_tasks.CompanyServiceClient") as mock_client_cls,
    ):
        mock_get.return_value = _snapshot_response(
            pre_authorized_capability_ids=["founder.notify.send"]
        )
        mock_client_cls.return_value.get = mock_company_get

        with pytest.raises(ValueError, match="founder_channel_ambiguous"):
            await execute_scheduled_session_task(
                plane,
                stream_mgr,
                {"schedule_execution_id": "exec_ambiguous", "workspace_id": "ws_sched"},
                run_id="run_ambiguous",
            )

    sent = mock_post.call_args.kwargs["json"]
    assert sent["state"] == "failed"
    assert "founder_channel_ambiguous" in sent["error"]


@pytest.mark.asyncio
async def test_founder_owner_not_authorized_blocks_reauth(worker_setup):  # noqa: F811
    plane = worker_setup["plane"]
    stream_mgr = CosaEventStreamManager()

    mock_post = AsyncMock()
    mock_company_get = AsyncMock(
        side_effect=CompanyServiceError(
            "Company Service Error (403): founder_owner_not_authorized: role revoked",
            status_code=403,
        )
    )
    with (
        patch(
            "apps.cosa.worker.scheduled_tasks.resolve_platform_control_plane_url",
            return_value="http://cp",
        ),
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
        patch("httpx.AsyncClient.post", new=mock_post),
        patch("apps.cosa.worker.scheduled_tasks.CompanyServiceClient") as mock_client_cls,
    ):
        mock_get.return_value = _snapshot_response(
            pre_authorized_capability_ids=["founder.notify.send"]
        )
        mock_client_cls.return_value.get = mock_company_get

        with pytest.raises(ValueError, match="founder_owner_not_authorized"):
            await execute_scheduled_session_task(
                plane,
                stream_mgr,
                {"schedule_execution_id": "exec_not_founder", "workspace_id": "ws_sched"},
                run_id="run_not_founder",
            )

    sent = mock_post.call_args.kwargs["json"]
    assert sent["state"] == "blocked_reauth"


@pytest.mark.asyncio
async def test_missing_email_grant_blocks_reauth_with_connector_code(worker_setup):  # noqa: F811
    plane = worker_setup["plane"]
    conv_repo = worker_setup["conv_repo"]
    stream_mgr = CosaEventStreamManager()

    mock_post = AsyncMock()
    mock_assert = AsyncMock(return_value={"ok": False, "error": "connector_reauth_required"})
    with (
        patch(
            "apps.cosa.worker.scheduled_tasks.resolve_platform_control_plane_url",
            return_value="http://cp",
        ),
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
        patch("httpx.AsyncClient.post", new=mock_post),
        patch("apps.cosa.worker.scheduled_tasks.ConnectorGrantHttpClient") as mock_connector_cls,
    ):
        mock_get.return_value = _snapshot_response(
            pre_authorized_capability_ids=["email.digest.read"]
        )
        mock_connector_cls.return_value.assert_usable_for_execution = mock_assert

        with pytest.raises(ValueError, match="connector_reauth_required"):
            await execute_scheduled_session_task(
                plane,
                stream_mgr,
                {"schedule_execution_id": "exec_no_grant", "workspace_id": "ws_sched"},
                run_id="run_no_grant",
            )

    mock_assert.assert_awaited_once()
    kwargs = mock_assert.call_args.kwargs
    assert kwargs["execution_id"] == "exec_no_grant"
    assert kwargs["action"] == "email.digest.read"

    _, total = await conv_repo.list_conversations(workspace_id="ws_sched", project_id="proj_test_1")
    assert total == 0
    sent = mock_post.call_args.kwargs["json"]
    assert sent["state"] == "blocked_reauth"
    assert sent["error"] == "connector_reauth_required"


@pytest.mark.asyncio
async def test_payload_pre_authorized_ids_applied_to_run_payload_and_principal_becomes_founder(
    worker_setup,  # noqa: F811
):
    """Cả 2 preflight qua -> run tiếp tục; `execute_run_task` nhận đúng
    `pre_authorized_capability_ids`/`_scheduler_dispatch`/`principal=user:<founderUserId>`."""
    plane = worker_setup["plane"]
    stream_mgr = CosaEventStreamManager()

    captured_payload: dict = {}

    async def fake_execute_run_task(_plane, _stream_mgr, run_payload):
        captured_payload.update(run_payload)
        from apps.cosa.worker.handlers import RunTaskResult

        return RunTaskResult(status="completed", run_id=run_payload["run_id"])

    mock_post = AsyncMock()
    mock_company_get = AsyncMock(
        return_value={"ok": True, "channelKind": "telegram", "channelLabel": "Ops"}
    )
    mock_assert = AsyncMock(return_value={"ok": True, "secretRef": "secret://x", "error": None})
    with (
        patch(
            "apps.cosa.worker.scheduled_tasks.resolve_platform_control_plane_url",
            return_value="http://cp",
        ),
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
        patch("httpx.AsyncClient.post", new=mock_post),
        patch("apps.cosa.worker.scheduled_tasks.CompanyServiceClient") as mock_client_cls,
        patch("apps.cosa.worker.scheduled_tasks.ConnectorGrantHttpClient") as mock_connector_cls,
        patch("apps.cosa.worker.handlers.execute_run_task", fake_execute_run_task),
    ):
        mock_get.return_value = _snapshot_response(
            pre_authorized_capability_ids=["founder.notify.send", "email.digest.read"],
            founder_member_id="member_42",
            founder_user_id="user_42",
        )
        mock_client_cls.return_value.get = mock_company_get
        mock_connector_cls.return_value.assert_usable_for_execution = mock_assert

        await execute_scheduled_session_task(
            plane,
            stream_mgr,
            {"schedule_execution_id": "exec_ok", "workspace_id": "ws_sched"},
            run_id="run_ok",
        )

    assert captured_payload["principal"] == "user:user_42"
    assert captured_payload["_scheduler_dispatch"] is True
    assert set(captured_payload["pre_authorized_capability_ids"]) == {
        "founder.notify.send",
        "email.digest.read",
    }
    sent = mock_post.call_args.kwargs["json"]
    assert sent["state"] == "succeeded"


@pytest.mark.asyncio
async def test_legacy_empty_snapshot_skips_preflight_entirely(worker_setup):  # noqa: F811
    """Lịch cũ (snapshot rỗng) — KHÔNG gọi preflight founder-notify/connector, principal
    vẫn 'service:scheduler', hành vi hoàn toàn như trước Task 6b."""
    plane = worker_setup["plane"]
    stream_mgr = CosaEventStreamManager()

    captured_payload: dict = {}

    async def fake_execute_run_task(_plane, _stream_mgr, run_payload):
        captured_payload.update(run_payload)
        from apps.cosa.worker.handlers import RunTaskResult

        return RunTaskResult(status="completed", run_id=run_payload["run_id"])

    mock_post = AsyncMock()
    mock_company_get = AsyncMock()
    mock_assert = AsyncMock()
    with (
        patch(
            "apps.cosa.worker.scheduled_tasks.resolve_platform_control_plane_url",
            return_value="http://cp",
        ),
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
        patch("httpx.AsyncClient.post", new=mock_post),
        patch("apps.cosa.worker.scheduled_tasks.CompanyServiceClient") as mock_client_cls,
        patch("apps.cosa.worker.scheduled_tasks.ConnectorGrantHttpClient") as mock_connector_cls,
        patch("apps.cosa.worker.handlers.execute_run_task", fake_execute_run_task),
    ):
        mock_get.return_value = _snapshot_response(
            pre_authorized_capability_ids=[], founder_member_id=None, founder_user_id=None
        )
        mock_client_cls.return_value.get = mock_company_get
        mock_connector_cls.return_value.assert_usable_for_execution = mock_assert

        await execute_scheduled_session_task(
            plane,
            stream_mgr,
            {"schedule_execution_id": "exec_legacy", "workspace_id": "ws_sched"},
            run_id="run_legacy",
        )

    mock_company_get.assert_not_awaited()
    mock_assert.assert_not_awaited()
    assert captured_payload["principal"] == "service:scheduler"
    assert "pre_authorized_capability_ids" not in captured_payload
    assert "_scheduler_dispatch" not in captured_payload
