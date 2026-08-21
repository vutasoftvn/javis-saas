"""Tests cho COSA app factory (Quyết định 3 - self-host + central control-plane
role split). Xem docs/architecture/COSA_ADK_ORCHESTRATOR_UUID7_PROPOSAL.md,
Quyết định 3.
"""
import pytest


def test_resolve_app_role_defaults_to_full_when_unset():
    from app.bootstrap.create_app import resolve_app_role, FULL_ROLE

    assert resolve_app_role({}) == FULL_ROLE


def test_resolve_app_role_defaults_to_full_when_blank():
    from app.bootstrap.create_app import resolve_app_role, FULL_ROLE

    assert resolve_app_role({"APP_ROLE": "   "}) == FULL_ROLE


def test_resolve_app_role_accepts_central_control_plane():
    from app.bootstrap.create_app import resolve_app_role, CENTRAL_CONTROL_PLANE_ROLE

    assert resolve_app_role({"APP_ROLE": "central_control_plane"}) == CENTRAL_CONTROL_PLANE_ROLE
    assert resolve_app_role({"APP_ROLE": " Central_Control_Plane "}) == CENTRAL_CONTROL_PLANE_ROLE


def test_resolve_app_role_rejects_unknown_value():
    from app.bootstrap.create_app import resolve_app_role

    with pytest.raises(ValueError, match="Unknown APP_ROLE"):
        resolve_app_role({"APP_ROLE": "central"})
