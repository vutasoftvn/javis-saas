import json
import time
from unittest.mock import AsyncMock, patch
import pytest

from workforce.agents.execution.n8n_bridge import (
    dispatch_job_callback,
    generate_hmac_signature,
    verify_hmac_signature,
)
from workforce.agents.execution.types import ArtifactRef, ExecutionJobResult, ExecutionStatus


def test_hmac_signature_generation_and_verification():
    secret = "test-secret-key-123"
    payload = json.dumps({"job_id": "12345", "status": "completed"})
    timestamp = str(int(time.time()))

    sig = generate_hmac_signature(secret, payload, timestamp)
    assert isinstance(sig, str)
    assert len(sig) == 64

    # Correct verification
    assert verify_hmac_signature(secret, payload, timestamp, sig) is True

    # Tampered payload fails
    tampered_payload = json.dumps({"job_id": "12345", "status": "failed"})
    assert verify_hmac_signature(secret, tampered_payload, timestamp, sig) is False

    # Wrong secret fails
    assert verify_hmac_signature("wrong-secret", payload, timestamp, sig) is False


def test_hmac_replay_window_protection():
    secret = "test-secret"
    payload = "{}"
    old_timestamp = str(int(time.time()) - 600)  # 10 minutes ago
    sig = generate_hmac_signature(secret, payload, old_timestamp)

    # Replay protection blocks timestamp > 300s old
    assert verify_hmac_signature(secret, payload, old_timestamp, sig, max_age_seconds=300) is False


@pytest.mark.asyncio
async def test_dispatch_job_callback_sends_authenticated_post():
    job_result = ExecutionJobResult(
        job_id="99999",
        workspace_id=123,
        status=ExecutionStatus.COMPLETED,
        provider="mock",
        artifacts=[
            ArtifactRef(
                name="sales_summary.json",
                relative_path="sales_summary.json",
                size_bytes=512,
                content_hash="sha256fake",
                object_storage_uri="s3://workspaces/123/execution/99999/sales_summary.json",
            )
        ],
    )

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = "ok"

        success = await dispatch_job_callback(
            callback_url="https://n8n.example.com/webhook/execution-done",
            webhook_secret="test-n8n-secret",
            job_result=job_result,
        )

        assert success is True
        assert mock_post.called
        call_kwargs = mock_post.call_args.kwargs
        headers = call_kwargs["headers"]
        assert "X-COSA-Signature" in headers
        assert "X-COSA-Timestamp" in headers
        assert headers["User-Agent"] == "COSA-Execution-Runtime/13.2"
