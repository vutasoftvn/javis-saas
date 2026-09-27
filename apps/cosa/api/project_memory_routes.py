"""Fact dự án founder xác nhận (review 2026-09-27, G-8).

- GET    /agent/projects/{project_id}/memory/facts
- POST   /agent/projects/{project_id}/memory/facts            (founder ghi)
- DELETE /agent/projects/{project_id}/memory/facts/{fact_id}  (retract, không xoá)

Mọi route xác thực danh tính + verify Project qua Company TRƯỚC khi đọc/ghi.
Chỉ danh tính người dùng (không phải agent) ghi được — agent chỉ đề xuất qua
thẻ `memory_confirm` trong chat.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from apps.cosa.api.project_context import verify_project_context
from apps.cosa.auth.dependency import AuthenticatedIdentity, get_authenticated_identity
from apps.cosa.memory.project_facts import (
    MAX_FACT_CHARS,
    fact_view,
    list_project_facts,
    record_project_fact,
    retract_project_fact,
)

router = APIRouter(prefix="/agent", tags=["project-memory"])


class ProjectFactCreate(BaseModel):
    content: str = Field(min_length=1, max_length=MAX_FACT_CHARS)
    source_message_id: str | None = Field(default=None, max_length=128)


class ProjectFactRetract(BaseModel):
    reason: str | None = Field(default=None, max_length=200)


def _memory_service(request: Request) -> Any:
    plane = getattr(request.app.state, "plane", None)
    service = getattr(plane, "memory_service", None) if plane is not None else None
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Memory service unavailable"
        )
    return plane, service


@router.get("/projects/{project_id}/memory/facts")
async def list_facts(
    request: Request,
    project_id: str,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> dict[str, Any]:
    plane, service = _memory_service(request)
    await verify_project_context(plane, identity, project_id)
    facts = await list_project_facts(
        service, workspace_id=identity.workspace_id, project_id=project_id
    )
    return {"facts": [fact_view(f) for f in facts]}


@router.post("/projects/{project_id}/memory/facts", status_code=status.HTTP_201_CREATED)
async def create_fact(
    request: Request,
    project_id: str,
    body: ProjectFactCreate,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> dict[str, Any]:
    plane, service = _memory_service(request)
    await verify_project_context(plane, identity, project_id)
    try:
        item = await record_project_fact(
            service,
            workspace_id=identity.workspace_id,
            project_id=project_id,
            content=body.content,
            confirmed_by=identity.principal_id,
            source_message_id=body.source_message_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    return fact_view(item)


@router.delete("/projects/{project_id}/memory/facts/{fact_id}")
async def retract_fact(
    request: Request,
    project_id: str,
    fact_id: str,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> dict[str, Any]:
    plane, service = _memory_service(request)
    await verify_project_context(plane, identity, project_id)
    item = await retract_project_fact(
        service,
        workspace_id=identity.workspace_id,
        project_id=project_id,
        fact_id=fact_id,
        reason=None,
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="fact not found")
    return {"id": item.id, "status": item.status.value}


def create_project_memory_router() -> APIRouter:
    return router
