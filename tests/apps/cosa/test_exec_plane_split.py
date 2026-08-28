"""SPEC-EXEC-PLANE-SPLIT: execution plane (local Workspace Runtime Node) phải
tách bạch platform control plane (VPS). Helper fail-fast ngăn một local node
âm thầm queue business work lên platform từ xa (ADR-LOCAL-FIRST-001)."""
import pathlib
import subprocess

import pytest

from apps.cosa.config.planes import (
    resolve_execution_plane_url,
    resolve_platform_control_plane_url,
)

_PLANE_VARS = (
    "COSA_EXECUTION_PLANE_URL",
    "COSA_PLATFORM_CONTROL_PLANE_URL",
    "COSA_CONTROL_PLANE_URL",
    "ENVIRONMENT",
    "APP_ENV",
)


def _clear(monkeypatch):
    for v in _PLANE_VARS:
        monkeypatch.delenv(v, raising=False)


def test_defaults_to_loopback(monkeypatch):
    _clear(monkeypatch)
    assert resolve_execution_plane_url() == "http://127.0.0.1:4001"
    assert resolve_platform_control_plane_url() == "http://127.0.0.1:4001"


def test_legacy_var_is_fallback_for_both(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("COSA_CONTROL_PLANE_URL", "http://legacy:9000")
    assert resolve_execution_plane_url() == "http://legacy:9000"
    assert resolve_platform_control_plane_url() == "http://legacy:9000"


def test_new_vars_win_over_legacy(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("COSA_CONTROL_PLANE_URL", "http://legacy:9000")
    monkeypatch.setenv("COSA_EXECUTION_PLANE_URL", "http://127.0.0.1:4001")
    monkeypatch.setenv("COSA_PLATFORM_CONTROL_PLANE_URL", "http://platform:4001")
    assert resolve_execution_plane_url() == "http://127.0.0.1:4001"
    assert resolve_platform_control_plane_url() == "http://platform:4001"


def test_production_rejects_execution_equal_to_platform(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("COSA_EXECUTION_PLANE_URL", "https://platform.example.com")
    monkeypatch.setenv("COSA_PLATFORM_CONTROL_PLANE_URL", "https://platform.example.com")
    with pytest.raises(RuntimeError, match="must not equal the platform"):
        resolve_execution_plane_url()


def test_production_rejects_remote_execution_host(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("COSA_EXECUTION_PLANE_URL", "https://remote.example.com")
    monkeypatch.setenv("COSA_PLATFORM_CONTROL_PLANE_URL", "https://platform.example.com")
    with pytest.raises(RuntimeError, match="must be local"):
        resolve_execution_plane_url()


def test_production_allows_loopback_and_dot_local(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("COSA_PLATFORM_CONTROL_PLANE_URL", "https://platform.example.com")
    monkeypatch.setenv("COSA_EXECUTION_PLANE_URL", "http://127.0.0.1:4001")
    assert resolve_execution_plane_url() == "http://127.0.0.1:4001"
    monkeypatch.setenv("COSA_EXECUTION_PLANE_URL", "http://node1.local:4001")
    assert resolve_execution_plane_url() == "http://node1.local:4001"


def test_no_direct_legacy_env_reads_outside_helper():
    repo = pathlib.Path(__file__).resolve().parents[3]
    out = subprocess.run(
        ["grep", "-rn", "COSA_CONTROL_PLANE_URL", str(repo / "apps/cosa"), "--include=*.py"],
        capture_output=True, text=True,
    ).stdout
    offenders = [
        line for line in out.splitlines()
        if "config/planes.py" not in line
        and "/test" not in line
        and "_test" not in line
        and "__pycache__" not in line
    ]
    assert not offenders, "direct COSA_CONTROL_PLANE_URL reads remain:\n" + "\n".join(offenders)
