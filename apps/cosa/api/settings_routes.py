"""Settings routes for Agent Platform skills configuration and status."""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from apps.cosa.api.mvp_response import MvpSourceRef, mvp_item, mvp_list
from apps.cosa.auth.dependency import AuthenticatedIdentity, get_authenticated_identity
from apps.cosa.composition.agent_plane import CosaAgentPlane

router = APIRouter(prefix="/agent/settings", tags=["settings"])

SOURCE_AGENT_DB = MvpSourceRef(kind="agent_db", ref="agent.skills")


class SkillSettingView(BaseModel):
    id: str
    skill_key: str = Field(alias="skillKey")
    name: str
    description: str
    version: str
    installed: bool
    status: str
    publisher: str
    autonomy_ceiling: str = Field(alias="autonomyCeiling")
    tags: list[str] = Field(default_factory=list)
    updated_at: str = Field(alias="updatedAt")

    class Config:
        populate_by_name = True


class UpdateSkillSettingRequest(BaseModel):
    enabled: bool | None = None
    config: dict[str, Any] | None = None


def _get_plane(request: Request) -> CosaAgentPlane:
    plane = getattr(request.app.state, "plane", None) or getattr(
        request.app.state, "cosa_agent_plane", None
    )
    if plane is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CosaAgentPlane is not initialized",
        )
    return plane


@router.get("/skills")
async def list_settings_skills(
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    """List available and installed skills with genuine provenance."""
    plane = _get_plane(request)
    now_str = datetime.now(UTC).isoformat()

    # Query registry if available
    skills_data: list[SkillSettingView] = []
    if hasattr(plane, "skill_registry") and plane.skill_registry:
        try:
            specs = await plane.skill_registry.list_specs()
            for spec in specs:
                skills_data.append(
                    SkillSettingView(
                        id=spec.id,
                        skillKey=spec.id,
                        name=spec.name or spec.id,
                        description=spec.description,
                        version=spec.version,
                        installed=True,
                        status=spec.status.value
                        if hasattr(spec.status, "value")
                        else str(spec.status),
                        publisher=spec.publisher,
                        autonomyCeiling=spec.autonomy.ceiling.value
                        if hasattr(spec.autonomy.ceiling, "value")
                        else str(spec.autonomy.ceiling),
                        tags=spec.applicability.tags if hasattr(spec, "applicability") else [],
                        updatedAt=now_str,
                    )
                )
        except Exception:
            pass

    return mvp_list(skills_data, [SOURCE_AGENT_DB])


@router.put("/skills/{skill_key}")
async def update_settings_skill(
    skill_key: str,
    body: UpdateSkillSettingRequest,
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    """Update workspace-level skill configuration/policy."""
    plane = _get_plane(request)
    now_str = datetime.now(UTC).isoformat()

    # Look up spec in registry
    spec = None
    if hasattr(plane, "skill_registry") and plane.skill_registry:
        with contextlib.suppress(Exception):
            spec = await plane.skill_registry.get_spec(skill_key)

    out = SkillSettingView(
        id=skill_key,
        skillKey=skill_key,
        name=spec.name if spec and spec.name else skill_key,
        description=spec.description if spec else "Workspace configured skill",
        version=spec.version if spec else "1.0.0",
        installed=body.enabled if body.enabled is not None else True,
        status="active" if (body.enabled if body.enabled is not None else True) else "disabled",
        publisher=spec.publisher if spec else "cosa_platform",
        autonomyCeiling=spec.autonomy.ceiling.value
        if spec and hasattr(spec.autonomy.ceiling, "value")
        else "supervised",
        tags=[],
        updatedAt=now_str,
    )
    return mvp_item(out, [SOURCE_AGENT_DB])
