"""Vault Document and Version Record Models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class VaultClassification(StrEnum):
    """Phân loại nhạy cảm nội dung tài liệu (Task 2, plan local-first-enterprise-knowledge).

    Không dùng free text — chỉ policy resolution mới được quyết định permission
    dựa trên giá trị enum này, tránh lệch chuỗi giữa API/DB/policy code.
    """

    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


class VaultVisibility(StrEnum):
    """Phạm vi hiển thị mặc định của tài liệu trước khi tính grant tường minh."""

    PRIVATE = "PRIVATE"
    WORKSPACE = "WORKSPACE"
    ROLE = "ROLE"


class VaultGrantSubjectType(StrEnum):
    USER = "user"
    TEAM = "team"
    ROLE = "role"


class VaultPermission(StrEnum):
    """Hành động cụ thể mà 1 grant cấp cho subject trên 1 document.

    Thứ tự không ngụ ý cấp bậc — mỗi permission được kiểm tra riêng lẻ
    (KnowledgeAccessDecision.discover/read/download/manage/review/publish ở
    Task 6 map 1-nhiều từ các permission này, không suy diễn ngầm)."""

    READ = "read"
    REVIEW = "review"
    PUBLISH = "publish"
    MANAGE = "manage"


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
    classification: VaultClassification = VaultClassification.INTERNAL
    visibility: VaultVisibility = VaultVisibility.PRIVATE
    access_policy_version: int = 1
    retention_until: datetime | None = None
    legal_hold: bool = False


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
    classification: VaultClassification = VaultClassification.INTERNAL
    visibility: VaultVisibility = VaultVisibility.PRIVATE
    access_policy_version: int = 1
    retention_until: datetime | None = None
    legal_hold: bool = False


@dataclass(frozen=True)
class VaultAccessGrant:
    subject_type: VaultGrantSubjectType
    subject_id: str
    permission: VaultPermission
    granted_by: str
    grant_id: UUID | None = None
    created_at: datetime | None = None


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
