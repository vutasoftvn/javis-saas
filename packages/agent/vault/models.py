"""Vault Document and Version Record Models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class VaultDocumentRecord:
    document_id: UUID
    workspace_id: str
    title: str
    kind: str
    state: str
    current_version_id: UUID | None
    knowledge_source_id: UUID | None
    created_by: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class VaultDocumentVersionRecord:
    version_id: UUID
    workspace_id: str
    document_id: UUID
    object_ref: dict[str, Any]
    checksum_sha256: str
    size_bytes: int
    source_uri: str
    created_by: str
    created_at: datetime


@dataclass(frozen=True)
class VaultKnowledgeGraphNode:
    id: str
    label: str
    kind: str
    source_ref: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VaultKnowledgeGraphEdge:
    source_id: str
    target_id: str
    relation: str
    weight: float = 1.0


@dataclass(frozen=True)
class VaultKnowledgeGraph:
    nodes: list[VaultKnowledgeGraphNode] = field(default_factory=list)
    edges: list[VaultKnowledgeGraphEdge] = field(default_factory=list)
