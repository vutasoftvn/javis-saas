"""COSA Automation MVP (Task 6) — Agent → Company outcome projection.

The Agent Platform never writes the Company database. It signs a compact
reference event (ids + state + manifest hash, no business content) and POSTs it
to the Company-owned projection endpoint, authed by the worker service token.
Company treats the payload as non-authoritative for any business mutation.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from apps.cosa.auth.jwt import mint_worker_service_jwt

__all__ = ["AutomationOutcomeClient", "build_automation_outcome_client"]

_OUTCOME_PATH = "/operations/automation/internal/outcome"


class AutomationOutcomeClient:
    def __init__(
        self,
        base_url: str | None = None,
        service_token: str | None = None,
        client: httpx.AsyncClient | None = None,
        timeout_sec: float = 5.0,
    ) -> None:
        self._base_url = (
            base_url or os.getenv("COMPANY_SERVICE_URL") or "http://localhost:4000"
        ).rstrip("/")
        self._token = service_token or mint_worker_service_jwt(
            worker_id="automation-outcome-worker"
        )
        self._client = client or httpx.AsyncClient(timeout=timeout_sec)

    def _headers(self) -> dict[str, str]:
        return {"X-Service-Token": self._token, "Content-Type": "application/json"}

    async def _post(self, event: dict[str, Any]) -> dict[str, Any]:
        resp = await self._client.post(
            f"{self._base_url}{_OUTCOME_PATH}", json={"event": event}, headers=self._headers()
        )
        resp.raise_for_status()
        return resp.json()

    async def report_state_changed(
        self,
        *,
        invocation_id: str,
        run_id: str,
        workspace_id: str,
        state: str,
        sequence: int,
        manifest_hash: str,
        correlation_id: str,
        observed_at: str,
    ) -> dict[str, Any]:
        return await self._post(
            {
                "eventType": "automation.run.state_changed.v1",
                "invocationId": invocation_id,
                "runId": run_id,
                "workspaceId": workspace_id,
                "state": state,
                "sequence": sequence,
                "observedAt": observed_at,
                "manifestHash": manifest_hash,
                "correlationId": correlation_id,
            }
        )

    async def report_outcome(
        self,
        *,
        invocation_id: str,
        run_id: str,
        workspace_id: str,
        outcome: str,
        sequence: int,
        manifest_hash: str,
        correlation_id: str,
        observed_at: str,
        evidence_refs: list[str] | None = None,
        blocked_cause: str | None = None,
        failure_reason: str | None = None,
    ) -> dict[str, Any]:
        event: dict[str, Any] = {
            "eventType": "automation.run.outcome.v1",
            "invocationId": invocation_id,
            "runId": run_id,
            "workspaceId": workspace_id,
            "outcome": outcome,
            "sequence": sequence,
            "observedAt": observed_at,
            "manifestHash": manifest_hash,
            "correlationId": correlation_id,
            "evidenceRefs": evidence_refs or [],
        }
        if blocked_cause is not None:
            event["blockedCause"] = blocked_cause
        if failure_reason is not None:
            event["failureReason"] = failure_reason
        return await self._post(event)

    async def aclose(self) -> None:
        await self._client.aclose()


def build_automation_outcome_client() -> AutomationOutcomeClient:
    return AutomationOutcomeClient()
