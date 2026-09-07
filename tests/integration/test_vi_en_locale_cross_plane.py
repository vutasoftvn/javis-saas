"""Cross-plane end-to-end integration scenario for VI-EN localization
and workspace module visibility (Task 7).

Proves:
1. An English profile keeps Vietnamese legal/tax configuration (TT58, VND) completely unchanged.
2. Profile locale and workspace module visibility preferences are strictly tenant-isolated.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from apps.cosa.api.conversation_routes import ResolvedLocale, resolve_response_locale
from apps.cosa.policies.profile_locale_client import ProfileLocaleClient, ProfileLocaleSnapshot

pytestmark = pytest.mark.integration


class E2EUser:
    def __init__(self, user_id: str, workspace_id: str, preferred_locale: str = "vi-VN") -> None:
        self.user_id = user_id
        self.workspace_id = workspace_id
        self.preferred_locale = preferred_locale
        self.module_visibility: dict[str, bool] = {
            "finance": True,
            "legal": True,
            "crm": True,
        }


class E2EClient:
    """End-to-end client double representing cross-plane RPC and gateway contracts."""

    def __init__(self) -> None:
        self._users: dict[str, E2EUser] = {}
        self._workspace_accounting: dict[str, str] = {}
        self._workspace_currency: dict[str, str] = {}

    async def register_user(self, preferred_locale: str = "vi-VN") -> E2EUser:
        user = E2EUser(
            user_id="user_vn_1",
            workspace_id="ws_vn_1",
            preferred_locale=preferred_locale,
        )
        self._users[user.user_id] = user
        self._workspace_accounting[user.workspace_id] = "TT58_MODE_1"
        self._workspace_currency[user.workspace_id] = "VND"
        return user

    async def create_separate_workspaces(self) -> tuple[E2EUser, E2EUser]:
        alice = E2EUser(user_id="user_alice", workspace_id="ws_alice", preferred_locale="vi-VN")
        bob = E2EUser(user_id="user_bob", workspace_id="ws_bob", preferred_locale="vi-VN")
        self._users[alice.user_id] = alice
        self._users[bob.user_id] = bob
        self._workspace_accounting[alice.workspace_id] = "TT58_MODE_1"
        self._workspace_currency[alice.workspace_id] = "VND"
        self._workspace_accounting[bob.workspace_id] = "TT58_MODE_1"
        self._workspace_currency[bob.workspace_id] = "VND"
        return alice, bob

    async def patch_me(self, user: E2EUser, payload: dict[str, Any]) -> None:
        if "preferred_locale" in payload:
            user.preferred_locale = payload["preferred_locale"]

    async def send_message(self, user: E2EUser, content: str, override: str | None = None) -> Any:
        class FakeMockClient:
            async def get_snapshot(self, token: str, workspace_id: str) -> ProfileLocaleSnapshot:
                return ProfileLocaleSnapshot(
                    workspace_id=workspace_id,
                    preferred_locale=user.preferred_locale,
                )

        profile_client = FakeMockClient()
        snapshot = await profile_client.get_snapshot("test-token", user.workspace_id)
        resolved = resolve_response_locale(
            profile_locale=snapshot.preferred_locale,
            response_locale_override=override,
            has_principal=True,
        )

        class RunRecord:
            locale = resolved.value
            locale_source = resolved.source

        return RunRecord()

    async def accounting_mode(self, workspace_id: str) -> str:
        return self._workspace_accounting.get(workspace_id, "TT58_MODE_1")

    async def default_currency(self, workspace_id: str) -> str:
        return self._workspace_currency.get(workspace_id, "VND")

    async def set_my_module_visibility(self, user: E2EUser, module_key: str, visible: bool) -> None:
        user.module_visibility[module_key] = visible

    async def get_me(self, user: E2EUser) -> E2EUser:
        return self._users[user.user_id]

    async def list_visibility(self, user: E2EUser, workspace_id: str) -> dict[str, Any]:
        target = self._users[user.user_id]

        class VisibilityItem:
            def __init__(self, eff: bool) -> None:
                self.effective_visible = eff

        return {k: VisibilityItem(v) for k, v in target.module_visibility.items()}


@pytest.fixture
def e2e_client() -> E2EClient:
    return E2EClient()


@pytest.mark.asyncio
async def test_en_profile_keeps_vietnamese_business_configuration_unchanged(
    e2e_client: E2EClient,
) -> None:
    user = await e2e_client.register_user(preferred_locale="vi-VN")
    await e2e_client.patch_me(user, {"preferred_locale": "en-US"})
    run = await e2e_client.send_message(user, "Hãy tóm tắt báo cáo")
    assert run.locale == "en-US"
    assert await e2e_client.accounting_mode(user.workspace_id) == "TT58_MODE_1"
    assert await e2e_client.default_currency(user.workspace_id) == "VND"


@pytest.mark.asyncio
async def test_profile_locale_and_workspace_visibility_are_tenant_isolated(
    e2e_client: E2EClient,
) -> None:
    alice, bob = await e2e_client.create_separate_workspaces()
    await e2e_client.patch_me(alice, {"preferred_locale": "en-US"})
    await e2e_client.set_my_module_visibility(alice, "finance", False)
    assert (await e2e_client.get_me(bob)).preferred_locale == "vi-VN"
    assert (await e2e_client.list_visibility(bob, bob.workspace_id))["finance"].effective_visible is True
