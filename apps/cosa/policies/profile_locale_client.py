from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import httpx

from apps.cosa.config.planes import resolve_platform_control_plane_url
from apps.cosa.policies.locale_policy import (
    SUPPORTED_LOCALES,
    ProfileLocaleUnavailable,
)

__all__ = [
    "SUPPORTED_LOCALES",
    "ProfileLocaleClient",
    "ProfileLocaleSnapshot",
    "ProfileLocaleUnavailable",
    "SupportedLocale",
]

SupportedLocale = Literal["vi-VN", "en-US"]


@dataclass(frozen=True)
class ProfileLocaleSnapshot:
    workspace_id: str
    preferred_locale: str  # "vi-VN" | "en-US"


class ProfileLocaleClient:
    """Client for GET /platform/auth/me/locale-snapshot on Control Plane.

    Fetches the caller's preferred locale with workspace delegation token.
    """

    def __init__(
        self,
        base_url: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = (base_url or resolve_platform_control_plane_url()).rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            transport=transport,
            timeout=10.0,
        )

    async def get_snapshot(self, bearer_token: str, workspace_id: str) -> ProfileLocaleSnapshot:
        try:
            resp = await self._client.get(
                "/platform/auth/me/locale-snapshot",
                params={"workspaceId": workspace_id},
                headers={"Authorization": f"Bearer {bearer_token}"},
            )
        except httpx.HTTPError as exc:
            raise ProfileLocaleUnavailable(f"failed to call COSA control plane: {exc}") from exc

        if resp.status_code != 200:
            raise ProfileLocaleUnavailable(
                f"COSA control plane returned error {resp.status_code}: {resp.text[:200]}"
            )

        try:
            data = resp.json()
        except ValueError as exc:
            raise ProfileLocaleUnavailable(
                f"COSA control plane returned non-JSON response: {exc}"
            ) from exc

        locale = data.get("preferred_locale")
        if locale not in SUPPORTED_LOCALES:
            raise ProfileLocaleUnavailable(
                f"unsupported or missing preferred_locale '{locale}' in response"
            )

        resp_ws = data.get("workspace_id")
        if not resp_ws or str(resp_ws) != str(workspace_id):
            raise ProfileLocaleUnavailable(
                f"workspace_id mismatch or missing: expected {workspace_id}, got {resp_ws}"
            )

        return ProfileLocaleSnapshot(
            workspace_id=str(resp_ws),
            preferred_locale=locale,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> ProfileLocaleClient:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.aclose()
