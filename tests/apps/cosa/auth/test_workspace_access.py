from __future__ import annotations

import pytest
from fastapi import HTTPException

from apps.cosa.auth import require_workspace_operator, resolve_identity_workspace
from apps.cosa.auth.dependency import AuthenticatedIdentity


def make_identity(*, workspace_id: str = "ws-a", role_id: str = "founder") -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        principal_id="user:test",
        platform_user_id="test",
        workspace_id=workspace_id,
        role_id=role_id,
        bearer_token="test-token",
    )


def test_workspace_scope_cannot_be_overridden():
    identity = make_identity(workspace_id="ws-a", role_id="member")
    assert resolve_identity_workspace(identity) == "ws-a"
    with pytest.raises(HTTPException) as error:
        resolve_identity_workspace(identity, "ws-b")
    assert error.value.status_code == 404


def test_workspace_operator_requires_privileged_role():
    with pytest.raises(HTTPException) as error:
        require_workspace_operator(make_identity(role_id="member"))
    assert error.value.status_code == 403
