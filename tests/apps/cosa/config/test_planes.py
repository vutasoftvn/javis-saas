"""Unit tests for COSA plane resolvers (apps/cosa/config/planes.py).

Asserts:
- resolve_platform_control_plane_url priority:
  1. COSA_PLATFORM_CONTROL_PLANE_URL
  2. COSA_CONTROL_PLANE_URL (legacy fallback)
  3. Default http://127.0.0.1:4001
- resolve_execution_plane_url behavior:
  - In development: allows local or custom URLs.
  - In production / staging:
    - Loopback hosts (127.0.0.1, localhost, ::1) and *.local hosts PASS.
    - URL matching platform control plane URL raises RuntimeError.
    - Remote VPS / non-local hostname raises RuntimeError (ADR-LOCAL-FIRST-001).
"""

from __future__ import annotations

import pytest

from apps.cosa.config.planes import (
    resolve_execution_plane_url,
    resolve_platform_control_plane_url,
)


def test_platform_control_plane_url_resolution(monkeypatch):
    """Platform control plane URL resolves with correct precedence."""
    # 1. Default fallback
    monkeypatch.delenv("COSA_PLATFORM_CONTROL_PLANE_URL", raising=False)
    monkeypatch.delenv("COSA_CONTROL_PLANE_URL", raising=False)
    assert resolve_platform_control_plane_url() == "http://127.0.0.1:4001"

    # 2. Legacy fallback
    monkeypatch.setenv("COSA_CONTROL_PLANE_URL", "http://legacy.host:4001/")
    assert resolve_platform_control_plane_url() == "http://legacy.host:4001"

    # 3. Explicit platform control plane var wins
    monkeypatch.setenv(
        "COSA_PLATFORM_CONTROL_PLANE_URL", "https://platform.vps.cosa.internal:4001/"
    )
    assert resolve_platform_control_plane_url() == "https://platform.vps.cosa.internal:4001"


def test_execution_plane_url_dev_mode(monkeypatch):
    """In development mode, execution plane URL accepts local or custom endpoints."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("COSA_PLATFORM_CONTROL_PLANE_URL", raising=False)
    monkeypatch.delenv("COSA_CONTROL_PLANE_URL", raising=False)

    # Default
    monkeypatch.delenv("COSA_EXECUTION_PLANE_URL", raising=False)
    assert resolve_execution_plane_url() == "http://127.0.0.1:4001"

    # Custom
    monkeypatch.setenv("COSA_EXECUTION_PLANE_URL", "http://127.0.0.1:9090")
    assert resolve_execution_plane_url() == "http://127.0.0.1:9090"


def test_execution_plane_url_production_rules(monkeypatch):
    """In production mode, execution plane URL enforces local-first constraints."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("COSA_PLATFORM_CONTROL_PLANE_URL", "https://platform.cosa.internal")

    # 1. Valid local hosts pass
    monkeypatch.setenv("COSA_EXECUTION_PLANE_URL", "http://127.0.0.1:5001")
    assert resolve_execution_plane_url() == "http://127.0.0.1:5001"

    monkeypatch.setenv("COSA_EXECUTION_PLANE_URL", "http://localhost:5001")
    assert resolve_execution_plane_url() == "http://localhost:5001"

    monkeypatch.setenv("COSA_EXECUTION_PLANE_URL", "http://node-alpha.local:5001")
    assert resolve_execution_plane_url() == "http://node-alpha.local:5001"

    # 2. Equal to platform control plane -> raises RuntimeError
    monkeypatch.setenv("COSA_EXECUTION_PLANE_URL", "https://platform.cosa.internal")
    with pytest.raises(RuntimeError, match="must not equal the platform control-plane URL"):
        resolve_execution_plane_url()

    # 3. Remote VPS / non-local host -> raises RuntimeError
    monkeypatch.setenv("COSA_EXECUTION_PLANE_URL", "https://remote-vps.agency.com:4001")
    with pytest.raises(RuntimeError, match="must be local for a Workspace Runtime Node"):
        resolve_execution_plane_url()
