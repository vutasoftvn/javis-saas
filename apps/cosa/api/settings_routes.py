"""Settings routes for Agent Platform skills configuration and status.

Task 4 (Truthful MVP Hardening) — trước đây route này có 2 lỗi "thành công
giả": (1) GET `except Exception: pass` khiến registry lỗi bị báo cáo thành
"danh sách rỗng" nguồn `agent_db` thay vì lỗi rõ ràng; (2) PUT không hề
persist gì cả — chỉ echo lại request thành 1 `SkillSettingView` giả rồi trả
`200 OK`. Từ Task 4: GET/PUT merge published skill registry (`plane.spec_
registry`, nguồn sự thật của Agent Platform cho danh mục skill) với policy
đã persist thật ở COSA Control Plane (`services/cosa`, bảng
`control_plane.workspace_skill_policies`, qua `WorkspaceSettingsClient`).
apps/cosa CHỈ validate `skillKey` với registry của mình rồi delegate side
effect thật sang control plane — không tự lưu policy.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from apps.cosa.api.mvp_response import MvpSourceRef, MvpSuccess, mvp_item, mvp_list
from apps.cosa.auth import (
    AuthenticatedIdentity,
    get_authenticated_identity,
    require_workspace_operator,
)
from apps.cosa.capabilities.workspace_settings_client import WorkspaceSettingsClientError
from apps.cosa.composition.agent_plane import CosaAgentPlane

logger = logging.getLogger("cosa.api.settings")

router = APIRouter(prefix="/agent/settings", tags=["settings"])

# Task 4 — source_kind authoritative đổi từ `agent_db` sang `control_plane`:
# `enabled`/`config`/`revision` của 1 skill (state có thể mutate) giờ đọc/ghi
# thật ở COSA Control Plane, KHÔNG còn là dữ liệu tại chỗ của Agent Platform.
SOURCE_CONTROL_PLANE = MvpSourceRef(kind="control_plane", ref="control_plane.skill_policies")


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
    # Task 4 — Flutter (`SettingsMvpService.updateSkill`) chỉ áp state cục bộ
    # khi `revision` trả về LỚN HƠN revision đã biết, chặn 1 response cũ/lặp
    # bị coi là thành công. Skill chưa từng persist policy có revision 0.
    revision: int = 0

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


async def _list_published_skill_specs(plane: CosaAgentPlane) -> list[Any]:
    """Đọc danh mục skill đã publish từ registry của Agent Platform.

    Lỗi ở đây (DB registry mất kết nối, v.v.) PHẢI thành 503 rõ ràng — KHÔNG
    được nuốt lỗi rồi coi như "chưa có skill nào" (bug cũ)."""
    try:
        return await plane.spec_registry.list_all(spec_kind="skill")
    except Exception as exc:  # boundary dịch lỗi hạ tầng registry -> 503 rõ ràng
        logger.exception("skill registry unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="skill registry unavailable",
        ) from exc


def _skill_view_from_spec(
    spec: Any, *, policy: dict[str, Any] | None, now_str: str
) -> SkillSettingView:
    content = spec.content or {}
    autonomy = content.get("autonomy") or {}
    applicability = content.get("applicability") or {}
    enabled = bool(policy["enabled"]) if policy else True
    return SkillSettingView(
        id=spec.spec_id,
        skillKey=spec.spec_id,
        name=content.get("name") or spec.spec_id,
        description=content.get("description") or "",
        version=spec.version,
        installed=enabled,
        status="active" if enabled else "disabled",
        publisher=spec.publisher or "cosa_platform",
        autonomyCeiling=autonomy.get("ceiling", "supervised")
        if isinstance(autonomy, dict)
        else str(autonomy),
        tags=list(applicability.get("tags", [])) if isinstance(applicability, dict) else [],
        updatedAt=str(policy["updatedAt"]) if policy else now_str,
        revision=int(policy["revision"]) if policy else 0,
    )


@router.get("/skills")
async def list_settings_skills(
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[list[SkillSettingView]]:
    """List available skills with genuine provenance: danh mục skill từ
    registry Agent Platform, policy (enabled/config/revision) từ COSA Control
    Plane (authoritative)."""
    plane = _get_plane(request)
    now_str = datetime.now(UTC).isoformat()

    specs = await _list_published_skill_specs(plane)

    try:
        policies = await plane.workspace_settings_client.list_policies(
            workspace_id=identity.workspace_id, bearer_token=identity.bearer_token
        )
    except WorkspaceSettingsClientError as exc:
        logger.exception("workspace settings control plane unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="workspace settings control plane unavailable",
        ) from exc

    policy_by_key = {
        p.get("skillKey"): p for p in policies if isinstance(p, dict) and p.get("skillKey")
    }

    skills_data = [
        _skill_view_from_spec(spec, policy=policy_by_key.get(spec.spec_id), now_str=now_str)
        for spec in specs
    ]

    return mvp_list(skills_data, [SOURCE_CONTROL_PLANE])


@router.put("/skills/{skill_key}")
async def update_settings_skill(
    skill_key: str,
    body: UpdateSkillSettingRequest,
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> MvpSuccess[SkillSettingView]:
    """Update workspace-level skill configuration/policy.

    Chỉ workspace operator được mutate (khớp `require_workspace_operator`
    dùng chung với các route ghi khác — vault/workforce/event_rule). Skill
    key phải tồn tại trong registry Agent Platform TRƯỚC khi cho phép ghi
    policy — không cho phép workspace tạo policy cho 1 skill không tồn tại.
    """
    require_workspace_operator(identity)
    plane = _get_plane(request)

    specs = await _list_published_skill_specs(plane)
    spec = next((s for s in specs if s.spec_id == skill_key), None)
    if spec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"unknown skill '{skill_key}'",
        )

    enabled = body.enabled if body.enabled is not None else True
    config = body.config or {}

    try:
        await plane.workspace_settings_client.put_policy(
            workspace_id=identity.workspace_id,
            skill_key=skill_key,
            enabled=enabled,
            config=config,
            bearer_token=identity.bearer_token,
        )
        # Read-after-write: KHÔNG tin thẳng response của chính PUT — đọc lại
        # từ control plane để trả giá trị đã thật sự persist (đúng yêu cầu
        # "không echo body thành success").
        policies_after = await plane.workspace_settings_client.list_policies(
            workspace_id=identity.workspace_id, bearer_token=identity.bearer_token
        )
    except WorkspaceSettingsClientError as exc:
        logger.exception("workspace settings control plane unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="workspace settings control plane unavailable",
        ) from exc

    saved = next(
        (p for p in policies_after if isinstance(p, dict) and p.get("skillKey") == skill_key),
        None,
    )
    if saved is None:
        # Control plane trả 2xx cho PUT nhưng đọc lại không thấy — coi là
        # unavailable thay vì fabricate thành công.
        logger.error("skill policy PUT succeeded but read-after-write found nothing")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="workspace settings control plane did not persist skill policy",
        )

    now_str = datetime.now(UTC).isoformat()
    out = _skill_view_from_spec(spec, policy=saved, now_str=now_str)
    return mvp_item(out, [SOURCE_CONTROL_PLANE])
