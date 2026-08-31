"""Tests cho DocumentIngestionControlPlaneClient — test lớp REAL, không AsyncMock.

Các test này verify rằng DocumentIngestionControlPlaneClient:
1. Makes correct HTTP POST calls tới control plane endpoints
2. Builds proper request bodies với headers auth
3. Parses successful responses (200, 202)
4. Handles HTTP errors (400, 401, 404, 500, etc.)
5. Validates failure_code trong mark_rejected_or_failed
6. Validates state parameter trong mark_rejected_or_failed
7. Handles network errors gracefully
8. Close behavior with http_client lifetime
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import Mock

import httpx
import pytest

from apps.cosa.knowledge_ingestion.control_plane_client import (
    DocumentIngestionControlPlaneClient,
)


def _client_with_transport(handler) -> DocumentIngestionControlPlaneClient:
    """Tạo client với mock HTTP transport."""
    transport = httpx.MockTransport(handler)
    inner = httpx.AsyncClient(transport=transport)
    return DocumentIngestionControlPlaneClient(
        control_plane_url="http://control-plane.internal",
        worker_service_token="test-token-12345",
        http_client=inner,
    )


# ============ claim_for_conversion tests ============


@pytest.mark.asyncio
async def test_claim_for_conversion_success():
    """Happy path — claim_for_conversion gọi endpoint đúng với payload."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "ing_123",
                "state": "VALIDATING",
                "workspaceId": "ws_alpha",
                "originalObjectKey": "quarantine/ws_alpha/ing_123/obj",
                "detectedMediaType": "text/plain",
                "sourceSha256": "abc123def456",
                "sizeBytes": 1024,
            },
        )

    client = _client_with_transport(handler)

    result = await client.claim_for_conversion("ing_123", "claim_token_xyz")

    assert captured["url"] == "http://control-plane.internal/cosa/document-ingestions/ing_123/transition"
    # Check authorization header (case-insensitive)
    auth_header = captured["headers"].get("authorization") or captured["headers"].get("Authorization")
    assert auth_header == "Bearer test-token-12345"
    assert captured["body"] == {
        "claimToken": "claim_token_xyz",
        "expectedStates": ["QUEUED"],
        "nextState": "VALIDATING",
    }
    assert result["state"] == "VALIDATING"
    assert result["id"] == "ing_123"


@pytest.mark.asyncio
async def test_claim_for_conversion_202_accepted():
    """HTTP 202 Accepted cũng là success."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["status_sent"] = True
        return httpx.Response(202, json={"id": "ing_456", "state": "VALIDATING"})

    client = _client_with_transport(handler)

    result = await client.claim_for_conversion("ing_456", "token_abc")

    assert captured["status_sent"] is True
    assert result["state"] == "VALIDATING"


@pytest.mark.asyncio
async def test_claim_for_conversion_http_error_400():
    """HTTP 400 → ValueError."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="Bad Request: invalid ingestion_id")

    client = _client_with_transport(handler)

    with pytest.raises(ValueError, match="Control plane error 400"):
        await client.claim_for_conversion("ing_bad", "token")


@pytest.mark.asyncio
async def test_claim_for_conversion_http_error_401():
    """HTTP 401 → ValueError."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="Unauthorized: invalid token")

    client = _client_with_transport(handler)

    with pytest.raises(ValueError, match="Control plane error 401"):
        await client.claim_for_conversion("ing_123", "bad_token")


@pytest.mark.asyncio
async def test_claim_for_conversion_http_error_409():
    """HTTP 409 (state conflict) → ValueError."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(409, text="Conflict: already claimed")

    client = _client_with_transport(handler)

    with pytest.raises(ValueError, match="Control plane error 409"):
        await client.claim_for_conversion("ing_already_claimed", "token")


@pytest.mark.asyncio
async def test_claim_for_conversion_http_error_500():
    """HTTP 500 → ValueError."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    client = _client_with_transport(handler)

    with pytest.raises(ValueError, match="Control plane error 500"):
        await client.claim_for_conversion("ing_123", "token")


# ============ record_candidate tests ============


@pytest.mark.asyncio
async def test_record_candidate_success():
    """Happy path — record_candidate sends knowledge_source_id và manifest."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "ing_789",
                "state": "REVIEW_PENDING",
                "knowledgeSourceId": "ks_999",
            },
        )

    client = _client_with_transport(handler)

    result = await client.record_candidate(
        "ing_789",
        "claim_token_record",
        "ks_999",
        manifest_json={"chunks": 42, "title": "Test Doc"},
    )

    assert captured["url"] == "http://control-plane.internal/cosa/document-ingestions/ing_789/transition"
    assert captured["body"]["claimToken"] == "claim_token_record"
    assert captured["body"]["expectedStates"] == ["VALIDATING"]
    assert captured["body"]["nextState"] == "REVIEW_PENDING"
    assert captured["body"]["patch"]["knowledgeSourceId"] == "ks_999"
    assert captured["body"]["patch"]["manifestJson"] == {"chunks": 42, "title": "Test Doc"}
    assert result["state"] == "REVIEW_PENDING"
    assert result["knowledgeSourceId"] == "ks_999"


@pytest.mark.asyncio
async def test_record_candidate_without_manifest():
    """record_candidate with optional manifest_json=None."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"id": "ing_555", "state": "REVIEW_PENDING"})

    client = _client_with_transport(handler)

    result = await client.record_candidate(
        "ing_555",
        "claim_token_no_manifest",
        "ks_111",
        manifest_json=None,
    )

    assert captured["body"]["patch"]["knowledgeSourceId"] == "ks_111"
    assert captured["body"]["patch"]["manifestJson"] is None
    assert result["id"] == "ing_555"


@pytest.mark.asyncio
async def test_record_candidate_http_error_400():
    """HTTP 400 → ValueError."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="Bad Request")

    client = _client_with_transport(handler)

    with pytest.raises(ValueError, match="Control plane error 400"):
        await client.record_candidate("ing_bad", "token", "ks_bad")


@pytest.mark.asyncio
async def test_record_candidate_http_error_409_wrong_state():
    """HTTP 409 (not in VALIDATING state) → ValueError."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(409, text="Conflict: not in VALIDATING state")

    client = _client_with_transport(handler)

    with pytest.raises(ValueError, match="Control plane error 409"):
        await client.record_candidate("ing_wrong_state", "token", "ks_id")


# ============ mark_rejected_or_failed tests ============


@pytest.mark.asyncio
async def test_mark_rejected_success():
    """Happy path — mark_rejected_or_failed with state=REJECTED."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "ing_rej",
                "state": "REJECTED",
                "failureCode": "malware_detected",
            },
        )

    client = _client_with_transport(handler)

    result = await client.mark_rejected_or_failed(
        "ing_rej",
        "claim_token_rej",
        "REJECTED",
        "malware_detected",
    )

    assert captured["body"]["claimToken"] == "claim_token_rej"
    assert captured["body"]["nextState"] == "REJECTED"
    assert captured["body"]["patch"]["failureCode"] == "malware_detected"
    assert result["state"] == "REJECTED"


@pytest.mark.asyncio
async def test_mark_failed_success():
    """Happy path — mark_rejected_or_failed with state=FAILED."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "ing_fail",
                "state": "FAILED",
                "failureCode": "conversion_timeout",
            },
        )

    client = _client_with_transport(handler)

    result = await client.mark_rejected_or_failed(
        "ing_fail",
        "claim_token_fail",
        "FAILED",
        "conversion_timeout",
    )

    assert captured["body"]["nextState"] == "FAILED"
    assert captured["body"]["patch"]["failureCode"] == "conversion_timeout"
    assert result["state"] == "FAILED"


@pytest.mark.asyncio
async def test_mark_rejected_invalid_state():
    """Invalid state parameter → ValueError."""
    client = _client_with_transport(lambda req: httpx.Response(200, json={}))

    with pytest.raises(ValueError, match="Invalid state"):
        await client.mark_rejected_or_failed(
            "ing_123",
            "token",
            "INVALID_STATE",
            "malware_detected",
        )


@pytest.mark.asyncio
async def test_mark_rejected_invalid_failure_code():
    """Invalid failure_code → ValueError before HTTP call."""
    client = _client_with_transport(lambda req: httpx.Response(200, json={}))

    with pytest.raises(ValueError, match="Invalid failure_code"):
        await client.mark_rejected_or_failed(
            "ing_123",
            "token",
            "REJECTED",
            "not_a_valid_code_xyz",
        )


@pytest.mark.asyncio
async def test_mark_rejected_valid_failure_codes():
    """All valid FailureCode literals should be accepted."""
    valid_codes = [
        "unsupported_media_type",
        "mime_mismatch",
        "file_too_large",
        "archive_limit_exceeded",
        "malware_detected",
        "scanner_unavailable",
        "checksum_mismatch",
        "conversion_timeout",
        "conversion_output_too_large",
        "conversion_parser_error",
    ]

    for code in valid_codes:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"id": "ing_123", "state": "REJECTED"})

        client = _client_with_transport(handler)
        result = await client.mark_rejected_or_failed("ing_123", "token", "REJECTED", code)
        assert result is not None


@pytest.mark.asyncio
async def test_mark_rejected_http_error():
    """HTTP error in mark_rejected_or_failed."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Server Error")

    client = _client_with_transport(handler)

    with pytest.raises(ValueError, match="Control plane error 500"):
        await client.mark_rejected_or_failed(
            "ing_123",
            "token",
            "REJECTED",
            "malware_detected",
        )


# ============ Network and connection error tests ============


@pytest.mark.asyncio
async def test_connection_error_on_claim_for_conversion():
    """Network error → httpx.ConnectError (not caught, propagates)."""
    client = DocumentIngestionControlPlaneClient(
        control_plane_url="http://127.0.0.1:59999"  # Port không có ai nghe
    )

    with pytest.raises(httpx.ConnectError):
        await client.claim_for_conversion("ing_123", "token")


@pytest.mark.asyncio
async def test_connection_error_on_record_candidate():
    """Network error → httpx.ConnectError."""
    client = DocumentIngestionControlPlaneClient(
        control_plane_url="http://127.0.0.1:59999"
    )

    with pytest.raises(httpx.ConnectError):
        await client.record_candidate("ing_123", "token", "ks_123")


@pytest.mark.asyncio
async def test_connection_error_on_mark_rejected():
    """Network error → httpx.ConnectError."""
    client = DocumentIngestionControlPlaneClient(
        control_plane_url="http://127.0.0.1:59999"
    )

    with pytest.raises(httpx.ConnectError):
        await client.mark_rejected_or_failed("ing_123", "token", "REJECTED", "malware_detected")


# ============ HTTP client lifecycle tests ============


@pytest.mark.asyncio
async def test_uses_provided_http_client():
    """Nếu http_client được cung cấp, nó được dùng."""
    captured_requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(str(request.url))
        return httpx.Response(200, json={"id": "ing_123", "state": "VALIDATING"})

    transport = httpx.MockTransport(handler)
    inner = httpx.AsyncClient(transport=transport)
    client = DocumentIngestionControlPlaneClient(
        control_plane_url="http://control-plane.internal",
        worker_service_token="token-abc",
        http_client=inner,
    )

    await client.claim_for_conversion("ing_123", "ct_1")

    assert len(captured_requests) == 1
    # inner client được tái sử dụng


@pytest.mark.asyncio
async def test_creates_temporary_client_when_none_provided():
    """Nếu http_client=None, một client tạm thời được tạo cho mỗi gọi."""
    # Không thể easily test with MockTransport nếu không có client,
    # nhưng verify constructor logic không crash
    client = DocumentIngestionControlPlaneClient(
        control_plane_url="http://127.0.0.1:9999",
        worker_service_token="token-123",
    )

    # Việc này sẽ fail do connection error, nhưng client được tạo ok
    with pytest.raises(httpx.ConnectError):
        await client.claim_for_conversion("ing_123", "token")


@pytest.mark.asyncio
async def test_authorization_header_set_from_worker_service_token():
    """Authorization header được set từ worker_service_token."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, json={"id": "ing_123", "state": "VALIDATING"})

    transport = httpx.MockTransport(handler)
    inner = httpx.AsyncClient(transport=transport)
    client = DocumentIngestionControlPlaneClient(
        control_plane_url="http://control-plane.internal",
        worker_service_token="my-secret-token-xyz",
        http_client=inner,
    )

    await client.claim_for_conversion("ing_123", "claim_token")

    assert captured["auth"] == "Bearer my-secret-token-xyz"


@pytest.mark.asyncio
async def test_uses_default_control_plane_url_if_not_provided(monkeypatch):
    """Nếu control_plane_url không cho, resolve_platform_control_plane_url() được gọi."""
    monkeypatch.setenv("COSA_PLATFORM_CONTROL_PLANE_URL", "http://resolved-url.internal")

    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"id": "ing_123", "state": "VALIDATING"})

    transport = httpx.MockTransport(handler)
    inner = httpx.AsyncClient(transport=transport)

    client = DocumentIngestionControlPlaneClient(
        http_client=inner,
        worker_service_token="token",
    )

    await client.claim_for_conversion("ing_123", "claim_token")

    # URL should use resolved value
    assert "http://resolved-url.internal" in captured["url"]


@pytest.mark.asyncio
async def test_invalid_response_json():
    """Response with invalid JSON → raises json.JSONDecodeError (not caught)."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not-json-at-all")

    client = _client_with_transport(handler)

    with pytest.raises(json.JSONDecodeError):
        await client.claim_for_conversion("ing_123", "token")


# ============ Multiple calls in sequence ============


@pytest.mark.asyncio
async def test_full_ingestion_workflow_sequence():
    """Simulate full workflow: claim → record → success."""
    call_log = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        next_state = body.get("nextState")
        call_log.append(next_state)

        if next_state == "VALIDATING":
            return httpx.Response(200, json={"id": "ing_full", "state": "VALIDATING"})
        elif next_state == "REVIEW_PENDING":
            return httpx.Response(
                200,
                json={"id": "ing_full", "state": "REVIEW_PENDING", "knowledgeSourceId": "ks_full"},
            )
        else:
            return httpx.Response(500, text="Unknown state")

    client = _client_with_transport(handler)

    # Step 1: claim
    claimed = await client.claim_for_conversion("ing_full", "claim_token_full")
    assert claimed["state"] == "VALIDATING"

    # Step 2: record
    recorded = await client.record_candidate(
        "ing_full", "claim_token_full", "ks_full", manifest_json=None
    )
    assert recorded["state"] == "REVIEW_PENDING"

    assert call_log == ["VALIDATING", "REVIEW_PENDING"]
