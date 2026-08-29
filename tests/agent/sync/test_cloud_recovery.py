"""M6 §5/§6 — cloud recovery guards: fail-closed missing key + MISSING_CREDENTIAL."""

from __future__ import annotations

import base64
import os

import pytest
from agent.sync import (
    CapabilityAvailability,
    CloudRecoveryError,
    ConnectorGrantView,
    assert_workspace_key_present,
    classify_connector_availability,
)
from agent.vault import WorkspaceKeyManager


@pytest.fixture(autouse=True)
def _master_key(monkeypatch):
    monkeypatch.setenv("COSA_VAULT_MASTER_KEY", base64.b64encode(os.urandom(32)).decode())


@pytest.fixture
def keys(tmp_path) -> WorkspaceKeyManager:
    return WorkspaceKeyManager(tmp_path / "data")


def test_missing_key_fails_closed_with_recovery_guidance(keys):
    with pytest.raises(CloudRecoveryError, match="KHÔNG tạo vault rỗng mới"):
        assert_workspace_key_present("1001", keys)
    # guard KHÔNG được tự tạo DEK
    assert keys._read_file("1001") is None


def test_present_key_passes(keys):
    keys.ensure_dek("1001")
    assert_workspace_key_present("1001", keys)  # no raise


def test_connector_ready_only_with_handle_and_cloud_secret():
    ready = ConnectorGrantView(
        connector_key="gmail", grant_handle="h-1", cloud_secret_provisioned=True
    )
    assert classify_connector_availability(ready) == CapabilityAvailability.READY


def test_connector_handle_but_no_cloud_secret_is_missing_credential():
    local_only = ConnectorGrantView(
        connector_key="gmail", grant_handle="h-1", cloud_secret_provisioned=False
    )
    assert classify_connector_availability(local_only) == CapabilityAvailability.MISSING_CREDENTIAL


def test_connector_no_grant_is_missing_credential():
    none = ConnectorGrantView(
        connector_key="gmail", grant_handle=None, cloud_secret_provisioned=False
    )
    assert classify_connector_availability(none) == CapabilityAvailability.MISSING_CREDENTIAL


def test_from_dict_camel_and_snake():
    a = ConnectorGrantView.from_dict(
        {"connector_key": "x", "grant_handle": "h", "cloud_secret_provisioned": True}
    )
    b = ConnectorGrantView.from_dict(
        {"connectorKey": "x", "grantHandle": "h", "cloudSecretProvisioned": True}
    )
    assert a == b
    assert classify_connector_availability(a) == CapabilityAvailability.READY
