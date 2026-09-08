from __future__ import annotations

from apps.cosa.policies.profile_locale_client import ProfileLocaleSnapshot

__all__ = ["FakeProfileLocaleClient"]


class FakeProfileLocaleClient:
    """Test double for the Control Plane profile-locale dependency."""

    def __init__(self, preferred_locale: str = "vi-VN") -> None:
        self.preferred_locale = preferred_locale
        self.calls: list[dict[str, str]] = []

    async def get_snapshot(self, bearer_token: str, workspace_id: str) -> ProfileLocaleSnapshot:
        self.calls.append({"bearer_token": bearer_token, "workspace_id": workspace_id})
        return ProfileLocaleSnapshot(
            workspace_id=workspace_id,
            preferred_locale=self.preferred_locale,
        )
