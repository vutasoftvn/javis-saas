"""Project Knowledge Search API Routes for COSA Agent Platform."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from apps.cosa.api.mvp_response import MvpSourceRef
from apps.cosa.auth.dependency import AuthenticatedIdentity, get_authenticated_identity

logger = logging.getLogger("cosa.api.project_knowledge_routes")

router = APIRouter(prefix="/agent", tags=["project-knowledge"])

_KNOWLEDGE_SOURCE = MvpSourceRef(kind="agent_db", ref="knowledge.projects")


class ProjectKnowledgeSearchRequest(BaseModel):
    query: str
    limit: int = 5


class ProjectKnowledgeCitation(BaseModel):
    document_id: str = Field(alias="documentId")
    version_id: str = Field(alias="versionId")
    chunk_id: str = Field(alias="chunkId")
    title: str
    excerpt: str

    model_config = ConfigDict(populate_by_name=True)


class ProjectKnowledgeItem(BaseModel):
    text: str
    citations: list[ProjectKnowledgeCitation] = Field(default_factory=list)


def create_project_knowledge_router() -> APIRouter:
    return router


@router.post(
    "/knowledge/projects/{project_id}/search",
    response_model=None,
)
async def search_project_knowledge(
    request: Request,
    project_id: str,
    payload: ProjectKnowledgeSearchRequest,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> dict[str, Any]:
    plane = getattr(request.app.state, "plane", None)
    if plane is None:
        raise RuntimeError("CosaAgentPlane chưa sẵn sàng — app.state.plane rỗng.")

    # 1. Scope project to workspace
    # If company_client is available, check if the project belongs to the caller's workspace
    company_client = getattr(plane, "company_client", None)
    if company_client is not None:
        try:
            resp = await company_client.get(
                f"/operations/projects/{project_id}",
                headers={
                    "Authorization": f"Bearer {identity.bearer_token}",
                    "X-Workspace-Id": identity.workspace_id,
                },
            )
            if not resp:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
            data = resp.get("data", resp) if isinstance(resp, dict) else {}
            ws_id = data.get("workspaceId") or data.get("workspace_id")
            if ws_id and str(ws_id) != str(identity.workspace_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
        except HTTPException:
            raise
        except Exception as e:
            logger.warning("Project lookup error: %s", e)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found") from e

    # 2. Retrieve authorized citations
    service = getattr(plane, "knowledge_ingestion_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge service unavailable",
        )

    roles = {identity.role_id} if identity.role_id else set()
    raw_citations = await service.retrieve_authorized_citations(
        workspace_id=identity.workspace_id,
        principal_id=identity.principal_id,
        role_ids=roles,
        query=payload.query,
        limit=payload.limit,
    )

    # 3. Filter by project if document has project metadata
    citations_list: list[dict[str, str]] = []
    store = getattr(service, "_store", None)
    for c in raw_citations:
        doc = await store.get_document(c.document_id, identity.workspace_id) if store else None
        if doc is not None:
            doc_proj = doc.metadata.get("projectId") or doc.metadata.get("project_id")
            if doc_proj and str(doc_proj) != str(project_id):
                continue
            v_doc_id = str(doc.vault_document_id or doc.id)
            v_ver_id = str(c.vault_version_id or doc.vault_version_id or "1")
        else:
            v_doc_id = str(c.document_id)
            v_ver_id = str(c.vault_version_id or "1")

        citations_list.append({
            "documentId": v_doc_id,
            "versionId": v_ver_id,
            "chunkId": str(c.chunk_id),
            "title": str(c.document_title),
            "excerpt": str(c.snippet),
        })

    items = [
        {
            "text": cit["excerpt"],
            "citations": [cit],
        }
        for cit in citations_list
    ]

    now_iso = datetime.now(UTC).isoformat()
    return {
        "data": {
            "items": items,
            "citations": citations_list,
        },
        "meta": {
            "data_state": "populated" if items else "empty",
            "observed_at": now_iso,
            "sources": [{"kind": "agent_db", "ref": "knowledge.projects"}],
        },
        "items": items,
        "citations": citations_list,
    }
