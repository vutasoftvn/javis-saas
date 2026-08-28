"""Phân giải URL cho hai plane tách bạch (SPEC-EXEC-PLANE-SPLIT):

- **Execution plane** — CHẠY TẠI LOCAL Workspace Runtime Node: durable run
  dispatch, run lease, scheduled task, durable child task. Không bao giờ được
  âm thầm trỏ ra platform VPS từ xa (ADR-LOCAL-FIRST-001 §Execution-plane rule).
- **Platform control plane** — CHẠY TẠI VPS: identity/license, connector
  policy/entitlement, company policy, document-ingestion control record.

`COSA_CONTROL_PLANE_URL` (biến cũ, một-cho-tất-cả) chỉ còn là fallback cấp 2
trong giai đoạn chuyển tiếp — không đọc trực tiếp ở nơi khác.
"""
from __future__ import annotations

import os
from urllib.parse import urlparse

__all__ = ["resolve_execution_plane_url", "resolve_platform_control_plane_url"]

_LEGACY_VAR = "COSA_CONTROL_PLANE_URL"
_DEFAULT = "http://127.0.0.1:4001"
_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
_PROD_ENVS = {"production", "staging", "prod"}


def _env_name() -> str:
    return os.environ.get("ENVIRONMENT", os.environ.get("APP_ENV", "development")).lower()


def resolve_platform_control_plane_url() -> str:
    """VPS platform control plane: identity/license, connector policy, company
    policy, document-ingestion control record."""
    return os.environ.get(
        "COSA_PLATFORM_CONTROL_PLANE_URL",
        os.environ.get(_LEGACY_VAR, _DEFAULT),
    ).rstrip("/")


def resolve_execution_plane_url() -> str:
    """Local Workspace Runtime Node execution plane: run dispatch, lease,
    scheduled task, durable child task.

    Fail-fast ở production/staging nếu URL bị trỏ ra platform từ xa — một local
    node không được queue business work lên VPS.
    """
    url = os.environ.get(
        "COSA_EXECUTION_PLANE_URL",
        os.environ.get(_LEGACY_VAR, _DEFAULT),
    ).rstrip("/")

    if _env_name() in _PROD_ENVS:
        platform = resolve_platform_control_plane_url()
        if url == platform:
            raise RuntimeError(
                "execution plane URL (COSA_EXECUTION_PLANE_URL) must not equal the platform "
                "control-plane URL (ADR-LOCAL-FIRST-001 §Execution-plane rule) — set it to the local node"
            )
        host = urlparse(url).hostname or ""
        if host not in _LOCAL_HOSTS and not host.endswith(".local"):
            raise RuntimeError(
                "execution plane URL (COSA_EXECUTION_PLANE_URL) must be local for a "
                f"Workspace Runtime Node, got host={host!r}"
            )
    return url
