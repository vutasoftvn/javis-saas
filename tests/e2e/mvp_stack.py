"""Contracts for the cross-plane MVP E2E stack.

`MvpStack` chỉ là bó `ServiceClient` trỏ vào các plane đang chạy thật; nó không
tự khởi động process. Có hai chế độ boot, cả hai đều tạo ra một `MvpStack` qua
`MvpStack.from_base_urls(...)`:

- subprocess: các helper trong `tests/e2e/stack/` (`_process`, `disposable_postgres`)
  spawn `services/*` + worker cục bộ rồi truyền base URL vào đây.
- compose: một `docker compose` bên ngoài dựng nguyên stack, test chỉ đọc base URL
  từ môi trường và gọi `from_base_urls`.

Bất biến: dàn E2E cross-plane KHÔNG bao giờ dùng transport giả — xem `__post_init__`.
"""

from __future__ import annotations

import socket
from dataclasses import dataclass
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
    apps_cosa: ServiceClient
    worker_health_url: str
    uses_mock_transport: bool = False

    def __post_init__(self) -> None:
        # Bất biến: dàn E2E cross-plane KHÔNG bao giờ dùng transport giả.
        if self.uses_mock_transport:
            raise ValueError("MvpStack.uses_mock_transport must stay False for the real stack")

    @classmethod
    def from_base_urls(
        cls,
        *,
        company: str,
        platform: str,
        agent: str,
        apps_cosa: str,
        worker_health_url: str,
    ) -> MvpStack:
        return cls(
            company=ServiceClient(base_url=company.rstrip("/")),
            platform=ServiceClient(base_url=platform.rstrip("/")),
            agent=ServiceClient(base_url=agent.rstrip("/")),
            apps_cosa=ServiceClient(base_url=apps_cosa.rstrip("/")),
            worker_health_url=worker_health_url,
        )
