"""Vault API Pydantic Schemas."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class VaultDocumentOut(BaseModel):
    document_id: str
    workspace_id: str
    title: str
    kind: str
    state: str
    current_version_id: str | None = None
    knowledge_source_id: str | None = None
    created_by: str
    created_at: str
    updated_at: str


class VaultDocumentVersionOut(BaseModel):
    version_id: str
    workspace_id: str
    document_id: str
    object_ref: dict[str, Any]
    checksum_sha256: str
    size_bytes: int
    source_uri: str
    created_by: str
    created_at: str


class VaultDocumentDetailOut(BaseModel):
    document_id: str
    workspace_id: str
    title: str
    kind: str
    state: str
    current_version_id: str | None = None
    knowledge_source_id: str | None = None
    created_by: str
    created_at: str
    updated_at: str
    versions: list[VaultDocumentVersionOut] = Field(default_factory=list)


class CreateUploadTicketRequest(BaseModel):
    file_name: str
    media_type: str
    size_bytes: int


class UploadTicketOut(BaseModel):
    ticket_id: str
    document_id: str
    upload_url: str
    expires_at: str
    max_bytes: int
    media_type: str


class ConfirmUploadRequest(BaseModel):
    checksum_sha256: str
    size_bytes: int


class DeleteDocumentOut(BaseModel):
    document_id: str
    deleted: bool


class KnowledgeGraphNodeOut(BaseModel):
    id: str
    label: str
    kind: str
    source_ref: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeGraphEdgeOut(BaseModel):
    source_id: str
    target_id: str
    relation: str
    weight: float = 1.0


class VaultKnowledgeGraphOut(BaseModel):
    nodes: list[KnowledgeGraphNodeOut] = Field(default_factory=list)
    edges: list[KnowledgeGraphEdgeOut] = Field(default_factory=list)


class VaultIndexedSourceOut(BaseModel):
    source_id: str
    workspace_id: str
    title: str
    source_type: str
    status: str
    chunk_count: int = 0
    indexed_at: str | None = None


class RetrievalQueryRequest(BaseModel):
    query: str
    limit: int = 10
    min_score: float = 0.0


class RetrievalHitOut(BaseModel):
    source_id: str
    title: str
    content: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)
