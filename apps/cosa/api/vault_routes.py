"""Vault API Routes for COSA Agent Platform.

Task 5 (Truthful MVP Hardening, 2026-09-01) — Vault (lưu trữ tài liệu + tri
thức) chưa có storage layer thật: không có object store, không có pipeline
scan/ingest, không có embedding/retrieval thật. Các route dưới đây TRƯỚC ĐÂY
giả lập vòng đời "ticket → confirm → INDEXED → retrieval hit" bằng cách ghi
row DB tạm và trả state giả (`state=INDEXED`, `score=0.95`,
`content=f"Document content for {title}"`...) — khiến client tưởng nhầm có
tài liệu thật đã được lưu trữ và index. Route giờ trả 501 trung thực, không
tạo bất kỳ draft/version/index state giả nào, và không tin checksum/size do
client tự khai báo (không còn storage thật để đối chiếu chúng).

Route vẫn được đăng ký (không bị gỡ khỏi router) vì `test_router_registration`
xác nhận đường dẫn `/agent/vault/documents` còn tồn tại — endpoint tồn tại,
chỉ hành vi trung thực hơn.

Điều kiện mở lại tính năng: xem "Exit decision for reopening Vault" trong
`.superpowers/sdd/2026-09-01-truthful-mvp-hardening/task-5-brief.md`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from apps.cosa.api.vault_schemas import (
    ConfirmUploadRequest,
    CreateUploadTicketRequest,
    RetrievalQueryRequest,
)
from apps.cosa.auth.dependency import (
    AuthenticatedIdentity,
    get_authenticated_identity,
)

router = APIRouter(prefix="/agent/vault", tags=["vault"])

# Message cố tình chung chung — không tiết lộ storage topology (tên bucket,
# provider, schema DB...) cho client.
_NOT_RELEASED_DETAIL = "Vault document ingestion is not released"


def _not_released() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=_NOT_RELEASED_DETAIL,
    )


# ─── Documents ───


@router.get("/documents")
async def list_documents(
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    raise _not_released()


@router.post("/documents/upload-ticket")
async def create_upload_ticket(
    req: CreateUploadTicketRequest,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    raise _not_released()


@router.get("/documents/{document_id}")
async def get_document(
    document_id: str,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    raise _not_released()


@router.post("/documents/{document_id}/confirm")
async def confirm_upload(
    document_id: str,
    req: ConfirmUploadRequest,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    raise _not_released()


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    raise _not_released()


# ─── Knowledge Graph & Sources & Retrieval ───


@router.get("/knowledge/graph")
async def get_knowledge_graph(
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    raise _not_released()


@router.get("/knowledge/sources")
async def list_indexed_sources(
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    raise _not_released()


@router.post("/retrieval/query")
async def retrieval_query(
    req: RetrievalQueryRequest,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
):
    raise _not_released()
