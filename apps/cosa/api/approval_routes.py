"""Approval routes for COSA Agent Platform (stub — consolidated onto workforce_routes.py).

Canonical approval endpoints are hosted under /agent/workforce/approvals in workforce_routes.py.
"""

from __future__ import annotations

from fastapi import APIRouter

__all__ = ["create_approval_router", "router"]

router = APIRouter(prefix="/agent/approvals", tags=["approvals"], deprecated=True)


def create_approval_router() -> APIRouter:
    """Stub router for backward compatibility."""
    return router
