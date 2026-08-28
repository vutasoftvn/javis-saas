"""Control plane client for document ingestion state management.

Lệnh gọi từ worker (apps/cosa) đến control plane (services/cosa) để:
- Claim ingestion cho conversion (QUEUED → VALIDATING)
- Record candidate sau khi normalized (VALIDATING → REVIEW_PENDING + set knowledge_source_id)
- Mark rejected hoặc failed (terminal states + failure_code)

Tất cả lệnh gọi dùng worker service auth + claim token để đảm bảo fencing.
"""

from __future__ import annotations

import os
from typing import get_args

import httpx

from apps.cosa.config.planes import resolve_platform_control_plane_url
from apps.cosa.knowledge_ingestion.contracts import FailureCode

__all__ = ["DocumentIngestionControlPlaneClient"]


class DocumentIngestionControlPlaneClient:
    """Client for document ingestion orchestration via services/cosa."""

    def __init__(
        self,
        control_plane_url: str | None = None,
        worker_service_token: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ):
        """Initialize control plane client.

        Args:
            control_plane_url: Base URL of services/cosa (default via resolve_platform_control_plane_url()).
            worker_service_token: Worker service auth token (default from COSA_WORKER_SERVICE_TOKEN env).
            http_client: Optional reusable AsyncClient; if None, creates one for each call.
        """
        self.control_plane_url = control_plane_url or resolve_platform_control_plane_url()
        self.worker_service_token = worker_service_token or os.environ.get(
            "COSA_WORKER_SERVICE_TOKEN", ""
        )
        self._http_client = http_client
        self._should_close_client = http_client is None

    async def _call_endpoint(
        self,
        method: str,
        path: str,
        json: dict | None = None,
    ) -> dict:
        """Make authenticated call to control plane endpoint.

        Args:
            method: HTTP method (POST, GET, etc.)
            path: Endpoint path (e.g., /cosa/document-ingestions/ing_123/transition)
            json: Request body (optional)

        Returns:
            Parsed JSON response

        Raises:
            ValueError: On HTTP error or invalid response
        """
        url = f"{self.control_plane_url}{path}"
        headers = {"Authorization": f"Bearer {self.worker_service_token}"}

        client = self._http_client
        should_close = False
        if client is None:
            client = httpx.AsyncClient(timeout=10.0)
            should_close = True

        try:
            if method == "POST":
                resp = await client.post(url, json=json, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            if resp.status_code not in (200, 202):
                raise ValueError(f"Control plane error {resp.status_code}: {resp.text}")

            return resp.json()
        finally:
            if should_close:
                await client.aclose()

    async def claim_for_conversion(
        self,
        ingestion_id: str,
        claim_token: str,
    ) -> dict:
        """Claim QUEUED ingestion for conversion processing.

        Transitions: QUEUED → VALIDATING
        Fencing: expectedStates=['QUEUED'] rejects if already claimed/converted.

        Args:
            ingestion_id: Ingestion ID from control plane.
            claim_token: Scheduler task claim token for fencing.

        Returns:
            Updated ingestion record {id, state, ...}

        Raises:
            ValueError: If already claimed, state invalid, or network error.
        """
        return await self._call_endpoint(
            "POST",
            f"/cosa/document-ingestions/{ingestion_id}/transition",
            json={
                "claimToken": claim_token,
                "expectedStates": ["QUEUED"],  # CAS: only claim from QUEUED
                "nextState": "VALIDATING",
            },
        )

    async def record_candidate(
        self,
        ingestion_id: str,
        claim_token: str,
        knowledge_source_id: str,
        manifest_json: dict | None = None,
    ) -> dict:
        """Record normalized document candidate and transition to REVIEW_PENDING.

        After successful conversion + normalization + ingest, record the
        knowledge_source_id and manifest in the ingestion record, then
        transition to REVIEW_PENDING for human review.

        Transitions: VALIDATING → REVIEW_PENDING

        Args:
            ingestion_id: Ingestion ID.
            claim_token: Task claim token for fencing.
            knowledge_source_id: Knowledge source ID (doc.id from agent_core).
            manifest_json: Extraction manifest (optional, for audit).

        Returns:
            Updated ingestion record {id, state, knowledgeSourceId, ...}

        Raises:
            ValueError: If not in VALIDATING, network error, etc.
        """
        return await self._call_endpoint(
            "POST",
            f"/cosa/document-ingestions/{ingestion_id}/transition",
            json={
                "claimToken": claim_token,
                "expectedStates": ["VALIDATING"],  # Must be in VALIDATING state
                "nextState": "REVIEW_PENDING",
                "patch": {
                    "knowledgeSourceId": knowledge_source_id,
                    "manifestJson": manifest_json,
                },
            },
        )

    async def mark_rejected_or_failed(
        self,
        ingestion_id: str,
        claim_token: str,
        state: str,  # "REJECTED" or "FAILED"
        failure_code: str,  # One of FailureCode literal values
    ) -> dict:
        """Mark ingestion as rejected (terminal) or failed (transient).

        Terminal failures (scan, parse, unsupported type) → REJECTED
        Transient failures (network, store error) → FAILED (scheduler retries)

        Failure code must be sanitized and allowlisted (never raw traceback/object key/URL).

        Args:
            ingestion_id: Ingestion ID.
            claim_token: Task claim token for fencing.
            state: "REJECTED" or "FAILED".
            failure_code: Allowlisted failure code (e.g., "malware_detected", "conversion_timeout").

        Returns:
            Updated ingestion record {id, state, failureCode, ...}

        Raises:
            ValueError: If invalid state/code, network error, etc.
        """
        if state not in ("REJECTED", "FAILED"):
            raise ValueError(f"Invalid state: {state}")

        # Validate failure_code against canonical FailureCode literal
        allowed_codes = set(get_args(FailureCode))
        if failure_code not in allowed_codes:
            raise ValueError(f"Invalid failure_code: {failure_code} (allowed: {allowed_codes})")

        return await self._call_endpoint(
            "POST",
            f"/cosa/document-ingestions/{ingestion_id}/transition",
            json={
                "claimToken": claim_token,
                # No expectedStates restriction for rejection (can be from any non-terminal state)
                # but most likely VALIDATING or CONVERTING
                "expectedStates": ["VALIDATING", "CONVERTING"],
                "nextState": state,
                "patch": {
                    "failureCode": failure_code,
                },
            },
        )
