from datetime import datetime, timedelta
from app.core.snowflake import generate_snowflake_id
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException

from app.db.models import WorkspaceMember
from app.modules.devices.models import Device, DeviceCredential, DeveloperJob, JobLease
from app.modules.devices import service
from app.modules.devices.router import (
    enroll_new_device,
    list_workspace_devices,
    device_heartbeat,
    create_job,
    list_jobs,
    claim_job_endpoint,
    submit_job_results_endpoint,
    DeviceEnrollRequest,
    DeveloperJobCreate,
    JobClaimRequest,
    JobSubmitResultsRequest,
)
from app.core.auth import get_current_device


def test_device_enrollment_and_heartbeat():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()

    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = ws_id
    member.user_id = user_id

    db = MagicMock()

    data = DeviceEnrollRequest(
        name="MacBook Pro M3 Max",
        platform="macos",
        capabilities=["claude_code", "git", "filesystem", "browser"],
        trust_level="elevated"
    )

    res = enroll_new_device(data=data, workspace_id=ws_id, member=member, db=db)
    assert res["name"] == "MacBook Pro M3 Max"
    assert res["platform"] == "macos"
    assert "enrollment_token" in res
    assert res["enrollment_token"].startswith("mcosa_dev_")
    assert db.add.called
    assert db.commit.called


def test_enrollment_token_is_hashed_not_stored_raw():
    """The raw token returned to the caller must never be what lands in the
    DB - only its SHA-256 hash. This is what makes a leaked DB backup useless
    for impersonating a device."""
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    db = MagicMock()

    device, raw_token = service.enroll_device(
        db=db, workspace_id=ws_id, user_id=user_id, name="Test Node", platform="linux",
    )

    stored_cred = next(
        call.args[0] for call in db.add.call_args_list
        if isinstance(call.args[0], DeviceCredential)
    )
    assert stored_cred.token_hash == service.hash_device_token(raw_token)
    assert not hasattr(stored_cred, "enrollment_token")


def test_resolve_device_from_token_rejects_revoked_and_expired():
    db = MagicMock()
    device_id = generate_snowflake_id()

    # A revoked credential must not satisfy the `is_revoked == False` DB
    # filter - simulate that by having the query return no match at all.
    db.query.return_value.filter.return_value.first.return_value = None
    assert service.resolve_device_from_token(db, "mcosa_dev_bogus") is None

    expired_cred = MagicMock(spec=DeviceCredential)
    expired_cred.is_revoked = False
    expired_cred.expires_at = datetime.utcnow() - timedelta(days=1)
    expired_cred.device_id = device_id
    db.query.return_value.filter.return_value.first.return_value = expired_cred
    assert service.resolve_device_from_token(db, "mcosa_dev_expired") is None


def test_get_current_device_rejects_missing_or_malformed_header():
    db = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        get_current_device(authorization="NotBearer xyz", db=db)
    assert exc_info.value.status_code == 401

    with pytest.raises(HTTPException) as exc_info:
        get_current_device(authorization="Bearer ", db=db)
    assert exc_info.value.status_code == 401


def test_developer_job_lifecycle():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    device_id = generate_snowflake_id()
    job_id = generate_snowflake_id()

    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = ws_id
    member.user_id = user_id

    caller_device = MagicMock(spec=Device)
    caller_device.id = device_id
    caller_device.workspace_id = ws_id

    db = MagicMock()

    # 1. Create Job (human-authenticated, via Flutter)
    job_data = DeveloperJobCreate(
        title="Refactor auth middleware to support device tokens",
        required_capabilities=["claude_code", "git"]
    )
    created_res = create_job(data=job_data, workspace_id=ws_id, member=member, db=db)
    assert created_res["title"] == "Refactor auth middleware to support device tokens"
    assert created_res["status"] == "QUEUED"

    # 2. Claim Job (device-authenticated, via the worker's own enrollment token)
    mock_job = MagicMock(spec=DeveloperJob)
    mock_job.id = job_id
    mock_job.workspace_id = ws_id
    mock_job.status = "QUEUED"
    mock_job.assigned_device_id = None

    db.query.return_value.filter.return_value.first.return_value = mock_job

    claim_data = JobClaimRequest(worker_id="local-fastapi-worker-1", lease_duration_minutes=20)
    claim_res = claim_job_endpoint(
        device_id=device_id, job_id=job_id, workspace_id=ws_id, data=claim_data,
        caller_device=caller_device, db=db,
    )
    assert claim_res["status"] == "claimed"
    assert mock_job.status == "CLAIMED"

    # 3. Submit Results - the mock job must now appear assigned to the
    # claiming device, mirroring what claim_job just set server-side.
    mock_job.assigned_device_id = device_id

    submit_data = JobSubmitResultsRequest(
        status="SUCCEEDED",
        diff_summary="+ 15 lines in auth_middleware.dart",
        test_results={"passed": 5, "failed": 0}
    )
    submit_res = submit_job_results_endpoint(
        job_id=job_id, workspace_id=ws_id, data=submit_data,
        caller_device=caller_device, db=db,
    )
    assert submit_res["status"] == "updated"
    assert submit_res["job_status"] == "SUCCEEDED"


def test_create_developer_job_idempotent_on_workspace_and_key():
    """A retried/reconnected voice command passing the same idempotency_key
    must return the existing job, not create a second one (mCOSA V12.2
    §70/§90.11)."""
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()

    db = MagicMock()
    existing_job = MagicMock(spec=DeveloperJob)
    db.query.return_value.filter.return_value.first.return_value = existing_job

    result = service.create_developer_job(
        db, ws_id, user_id, "Implement Portfolio Impact Matrix", idempotency_key="call_abc123"
    )

    assert result is existing_job
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_create_developer_job_without_idempotency_key_always_creates():
    """The HTTP-created path (Flutter, no idempotency_key) must not perform
    the idempotency lookup at all - it always creates a new job."""
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()

    db = MagicMock()

    service.create_developer_job(db, ws_id, user_id, "Refactor auth middleware")

    db.query.assert_not_called()
    assert db.add.called
    assert db.commit.called


def test_device_cross_tenant_isolation_forbidden():
    ws_id_a = generate_snowflake_id()
    ws_id_b = generate_snowflake_id()

    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = ws_id_a

    db = MagicMock()

    data = DeviceEnrollRequest(
        name="Attacker Device",
        platform="linux"
    )

    with pytest.raises(HTTPException) as exc_info:
        enroll_new_device(data=data, workspace_id=ws_id_b, member=member, db=db)

    assert exc_info.value.status_code == 403


def test_device_cannot_impersonate_another_device_id():
    """A device authenticated with its own valid token must not be able to
    heartbeat/claim/submit as a *different* device_id, even within the same
    workspace - the enrollment token only proves identity for itself."""
    ws_id = generate_snowflake_id()
    real_device_id = generate_snowflake_id()
    spoofed_device_id = generate_snowflake_id()

    caller_device = MagicMock(spec=Device)
    caller_device.id = real_device_id
    caller_device.workspace_id = ws_id

    db = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        device_heartbeat(
            device_id=spoofed_device_id, workspace_id=ws_id, data=None,
            caller_device=caller_device, db=db,
        )
    assert exc_info.value.status_code == 403

    with pytest.raises(HTTPException) as exc_info:
        claim_job_endpoint(
            device_id=spoofed_device_id, job_id=generate_snowflake_id(), workspace_id=ws_id,
            data=JobClaimRequest(worker_id="w1"), caller_device=caller_device, db=db,
        )
    assert exc_info.value.status_code == 403


def test_submit_results_rejected_for_job_assigned_to_other_device():
    """Even with a valid device credential and matching workspace, a device
    must not be able to overwrite the results of a job claimed by a
    different device."""
    ws_id = generate_snowflake_id()
    job_id = generate_snowflake_id()
    claiming_device_id = generate_snowflake_id()
    other_device_id = generate_snowflake_id()

    mock_job = MagicMock(spec=DeveloperJob)
    mock_job.id = job_id
    mock_job.workspace_id = ws_id
    mock_job.assigned_device_id = claiming_device_id

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = mock_job

    with pytest.raises(PermissionError):
        service.submit_job_results(
            db=db, job_id=job_id, workspace_id=ws_id, device_id=other_device_id,
            status="SUCCEEDED",
        )
