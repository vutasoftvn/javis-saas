"""Contracts for the planned cross-plane MVP E2E stack.

This module deliberately does not start processes or provide a fallback
transport. Release tests must use the real stack fixture when that broader
program is implemented.
"""

from __future__ import annotations

import socket
from dataclasses import dataclass, field
from typing import Any

import httpx


def pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@dataclass
class ServiceClient:
    base_url: str
    token: str = ""
    workspace_id: str = ""

    def _headers(self, token: str | None = None, workspace_id: str | None = None) -> dict[str, str]:
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        effective_token = token if token is not None else self.token
        effective_workspace_id = workspace_id if workspace_id is not None else self.workspace_id
        if effective_token:
            headers["Authorization"] = f"Bearer {effective_token}"
        if effective_workspace_id:
            headers["X-Workspace-Id"] = effective_workspace_id
        return headers

    def get(
        self,
        path: str,
        *,
        token: str | None = None,
        workspace_id: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        with httpx.Client(base_url=self.base_url, timeout=10.0) as client:
            return client.get(path, headers=self._headers(token, workspace_id), params=params)

    def post(
        self,
        path: str,
        *,
        json: Any = None,
        token: str | None = None,
        workspace_id: str | None = None,
    ) -> httpx.Response:
        with httpx.Client(base_url=self.base_url, timeout=10.0) as client:
            return client.post(path, json=json, headers=self._headers(token, workspace_id))

    def put(
        self,
        path: str,
        *,
        json: Any = None,
        token: str | None = None,
        workspace_id: str | None = None,
    ) -> httpx.Response:
        with httpx.Client(base_url=self.base_url, timeout=10.0) as client:
            return client.put(path, json=json, headers=self._headers(token, workspace_id))

    def delete(
        self,
        path: str,
        *,
        token: str | None = None,
        workspace_id: str | None = None,
    ) -> httpx.Response:
        with httpx.Client(base_url=self.base_url, timeout=10.0) as client:
            return client.delete(path, headers=self._headers(token, workspace_id))


@dataclass
class MvpStack:
    company: ServiceClient
    platform: ServiceClient
    agent: ServiceClient
    uses_mock_transport: bool = False
    migration_versions: dict[str, str] = field(
        default_factory=lambda: {
            "company": "33_mvp_strategy_canvas_runtime",
            "agent": "022_workforce_assignments_and_runtime_outbox",
            "control_plane": "28_workspace_settings_audit",
        }
    )
