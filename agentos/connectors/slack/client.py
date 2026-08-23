from __future__ import annotations

import asyncio
from typing import Any, Optional
import httpx

from agentos.connectors.vault import InMemoryVaultStore, SecretStore


class SlackApiError(Exception):
    """Raised when Slack API request fails."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(f"Slack API error ({status_code}): {message}")
        self.status_code = status_code
        self.message = message


class SlackConnectorClient:
    """Transport client for Slack Web API with automated bounded retries (§16.2).
    
    Responsibilities:
    - Token resolution via SecretStore (Vault)
    - Transport request with auth header
    - Bounded exponential backoff retry on transient 5xx/429/timeout errors
    - Zero business logic or persistence
    """

    def __init__(
        self,
        secret_store: Optional[SecretStore] = None,
        *,
        base_url: str = "https://slack.com/api",
        max_retries: int = 3,
        retry_delay_seconds: float = 0.05,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._secret_store = secret_store or InMemoryVaultStore()
        self._base_url = base_url.rstrip("/")
        self._max_retries = max_retries
        self._retry_delay_seconds = retry_delay_seconds
        self._http_client = http_client

    async def post_message(
        self,
        *,
        channel: str,
        text: str,
        workspace_id: Optional[str] = None,
        token: Optional[str] = None,
    ) -> dict[str, Any]:
        """Post a message to a Slack channel with retry on transient server errors."""
        auth_token = token
        if not auth_token:
            auth_token = await self._secret_store.get_secret("slack_bot_token", workspace_id=workspace_id)

        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        payload = {"channel": channel, "text": text}
        url = f"{self._base_url}/chat.postMessage"

        attempts = 0
        last_exception = None

        while attempts < self._max_retries:
            attempts += 1
            try:
                if self._http_client is not None:
                    resp = await self._http_client.post(url, headers=headers, json=payload)
                else:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        resp = await client.post(url, headers=headers, json=payload)

                if resp.status_code == 200:
                    data = resp.json()
                    if not data.get("ok", True):
                        raise SlackApiError(200, data.get("error", "slack_error"))
                    return data
                elif resp.status_code in (429, 500, 502, 503, 504):
                    if attempts < self._max_retries:
                        await asyncio.sleep(self._retry_delay_seconds * (2 ** (attempts - 1)))
                        continue
                    raise SlackApiError(resp.status_code, resp.text)
                else:
                    raise SlackApiError(resp.status_code, resp.text)

            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_exception = exc
                if attempts < self._max_retries:
                    await asyncio.sleep(self._retry_delay_seconds * (2 ** (attempts - 1)))
                    continue
                raise SlackApiError(504, f"Network/Timeout error after {attempts} attempts: {exc}") from exc

        if last_exception:
            raise SlackApiError(500, str(last_exception)) from last_exception
        raise SlackApiError(500, "Max retries exceeded")
