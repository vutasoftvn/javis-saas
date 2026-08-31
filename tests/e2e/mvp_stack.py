"""Cross-plane real MVP test stack harness.

Boots real local Company, Control Plane, and Agent Platform services on isolated
loopback ports with real migrations and zero MockTransport.
"""
from __future__ import annotations

import os
import socket
import time
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
        eff_token = token if token is not None else self.token
        eff_ws = workspace_id if workspace_id is not None else self.workspace_id
        if eff_token:
            headers["Authorization"] = f"Bearer {eff_token}"
        if eff_ws:
            headers["X-Workspace-Id"] = eff_ws
        return headers

    def get(self, path: str, *, token: str | None = None, workspace_id: str | None = None, params: dict[str, Any] | None = None) -> httpx.Response:
        with httpx.Client(base_url=self.base_url, timeout=10.0) as client:
            return client.get(path, headers=self._headers(token, workspace_id), params=params)

    def post(self, path: str, *, json: Any = None, token: str | None = None, workspace_id: str | None = None) -> httpx.Response:
        with httpx.Client(base_url=self.base_url, timeout=10.0) as client:
            return client.post(path, json=json, headers=self._headers(token, workspace_id))

    def put(self, path: str, *, json: Any = None, token: str | None = None, workspace_id: str | None = None) -> httpx.Response:
        with httpx.Client(base_url=self.base_url, timeout=10.0) as client:
            return client.put(path, json=json, headers=self._headers(token, workspace_id))

    def delete(self, path: str, *, token: str | None = None, workspace_id: str | None = None) -> httpx.Response:
        with httpx.Client(base_url=self.base_url, timeout=10.0) as client:
            return client.delete(path, headers=self._headers(token, workspace_id))


@dataclass
class MvpStack:
    company: ServiceClient
    platform: ServiceClient
    agent: ServiceClient
    uses_mock_transport: bool = False
    migration_versions: dict[str, str] = field(default_factory=lambda: {
        "company": "33_mvp_strategy_canvas_runtime",
        "agent": "022_workforce_assignments_and_runtime_outbox",
        "control_plane": "28_workspace_settings_audit",
    })
