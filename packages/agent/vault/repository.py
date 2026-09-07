"""Vault Repository: Workspace-isolated storage for Documents, Versions, and Knowledge Graph."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable
from uuid import UUID, uuid4

from sqlalchemy import text

from agent.vault.models import (
    VaultAccessGrant,
    VaultClassification,
    VaultDocumentRecord,
    VaultDocumentVersionRecord,
    VaultGrantSubjectType,
    VaultKnowledgeGraph,
    VaultKnowledgeGraphEdge,
    VaultKnowledgeGraphNode,
    VaultPermission,
    VaultVisibility,
)


@runtime_checkable
class VaultRepository(Protocol):
    async def create_draft(
        self,
        workspace_id: str,
        title: str,
        kind: str = "document",
        created_by: str = "system",
    ) -> VaultDocumentRecord: ...

    async def append_version(
        self,
        workspace_id: str,
        document_id: UUID,
        object_ref: dict[str, Any],
        checksum_sha256: str,
        size_bytes: int,
        source_uri: str,
        created_by: str = "system",
        version_id: UUID | None = None,
    ) -> VaultDocumentVersionRecord: ...

    async def get_document(
        self,
        workspace_id: str,
        document_id: UUID,
    ) -> VaultDocumentRecord | None: ...

    async def list_documents(
        self,
        workspace_id: str,
        state: str | None = None,
        limit: int = 50,
    ) -> list[VaultDocumentRecord]: ...

    async def update_document_state(
        self,
        workspace_id: str,
        document_id: UUID,
        state: str,
        knowledge_source_id: UUID | None = None,
    ) -> VaultDocumentRecord | None: ...

    async def delete_document(
        self,
        workspace_id: str,
        document_id: UUID,
    ) -> bool: ...

    async def list_versions(
        self,
        workspace_id: str,
        document_id: UUID,
    ) -> list[VaultDocumentVersionRecord]: ...

    async def get_version(
        self,
        workspace_id: str,
        version_id: UUID,
    ) -> VaultDocumentVersionRecord | None: ...

    async def get_knowledge_graph(
        self,
        workspace_id: str,
    ) -> VaultKnowledgeGraph: ...

    async def grant_access(
        self,
        workspace_id: str,
        document_id: UUID,
        grant: VaultAccessGrant,
    ) -> None: ...

    async def revoke_access(
        self,
        workspace_id: str,
        document_id: UUID,
        subject_type: VaultGrantSubjectType,
        subject_id: str,
    ) -> None: ...

    async def set_legal_hold(
        self,
        workspace_id: str,
        document_id: UUID,
        legal_hold: bool,
    ) -> VaultDocumentRecord | None: ...

    async def resolve_accessible_document_ids(
        self,
        workspace_id: str,
        principal_id: str,
        role_ids: set[str],
    ) -> set[UUID]: ...

    async def list_authorized_documents(
        self,
        workspace_id: str,
        principal_id: str,
        role_ids: set[str],
    ) -> list[VaultDocumentRecord]: ...

    async def has_explicit_grant(
        self,
        workspace_id: str,
        document_id: UUID,
        principal_id: str,
        role_ids: set[str],
        permission: VaultPermission,
    ) -> bool: ...


class PostgresVaultRepository:
    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory

    async def create_draft(
        self,
        workspace_id: str,
        title: str,
        kind: str = "document",
        created_by: str = "system",
        classification: VaultClassification = VaultClassification.INTERNAL,
        visibility: VaultVisibility = VaultVisibility.PRIVATE,
    ) -> VaultDocumentRecord:
        document_id = uuid4()
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            await session.execute(
                text("SELECT set_config('cosa.workspace_id', :workspace_id, true)"),
                {"workspace_id": workspace_id},
            )
            await session.execute(
                text(
                    """
                    INSERT INTO vault.documents (
                        document_id, workspace_id, title, kind, state,
                        current_version_id, knowledge_source_id, created_by,
                        created_at, updated_at, classification, visibility
                    ) VALUES (
                        :document_id, :workspace_id, :title, :kind, 'DRAFT',
                        NULL, NULL, :created_by, :created_at, :updated_at,
                        :classification, :visibility
                    )
                    """
                ),
                {
                    "document_id": document_id,
                    "workspace_id": workspace_id,
                    "title": title,
                    "kind": kind,
                    "created_by": created_by,
                    "created_at": now,
                    "updated_at": now,
                    "classification": classification.value,
                    "visibility": visibility.value,
                },
            )
            await session.commit()

        return VaultDocumentRecord(
            document_id=document_id,
            workspace_id=workspace_id,
            title=title,
            kind=kind,
            state="DRAFT",
            current_version_id=None,
            knowledge_source_id=None,
            created_by=created_by,
            created_at=now,
            updated_at=now,
            classification=classification,
            visibility=visibility,
        )

    async def append_version(
        self,
        workspace_id: str,
        document_id: UUID,
        object_ref: dict[str, Any],
        checksum_sha256: str,
        size_bytes: int,
        source_uri: str,
        created_by: str = "system",
        version_id: UUID | None = None,
    ) -> VaultDocumentVersionRecord:
        version_id = version_id or uuid4()
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            await session.execute(
                text("SELECT set_config('cosa.workspace_id', :workspace_id, true)"),
                {"workspace_id": workspace_id},
            )
            await session.execute(
                text(
                    """
                    INSERT INTO vault.document_versions (
                        version_id, workspace_id, document_id, object_ref,
                        checksum_sha256, size_bytes, source_uri, created_by, created_at
                    ) VALUES (
                        :version_id, :workspace_id, :document_id, :object_ref,
                        :checksum_sha256, :size_bytes, :source_uri, :created_by, :created_at
                    )
                    """
                ),
                {
                    "version_id": version_id,
                    "workspace_id": workspace_id,
                    "document_id": document_id,
                    "object_ref": json.dumps(object_ref),
                    "checksum_sha256": checksum_sha256,
                    "size_bytes": size_bytes,
                    "source_uri": source_uri,
                    "created_by": created_by,
                    "created_at": now,
                },
            )
            # Update current_version_id on document
            await session.execute(
                text(
                    """
                    UPDATE vault.documents
                    SET current_version_id = :version_id,
                        updated_at = :updated_at
                    WHERE workspace_id = :workspace_id AND document_id = :document_id
                    """
                ),
                {
                    "version_id": version_id,
                    "updated_at": now,
                    "workspace_id": workspace_id,
                    "document_id": document_id,
                },
            )
            await session.commit()

        return VaultDocumentVersionRecord(
            version_id=version_id,
            workspace_id=workspace_id,
            document_id=document_id,
            object_ref=object_ref,
            checksum_sha256=checksum_sha256,
            size_bytes=size_bytes,
            source_uri=source_uri,
            created_by=created_by,
            created_at=now,
        )

    async def get_document(
        self,
        workspace_id: str,
        document_id: UUID,
    ) -> VaultDocumentRecord | None:
        async with self._session_factory() as session:
            await session.execute(
                text("SELECT set_config('cosa.workspace_id', :workspace_id, true)"),
                {"workspace_id": workspace_id},
            )
            res = await session.execute(
                text(
                    """
                    SELECT document_id, workspace_id, title, kind, state,
                           current_version_id, knowledge_source_id, created_by,
                           created_at, updated_at, classification, visibility,
                           access_policy_version, retention_until, legal_hold
                    FROM vault.documents
                    WHERE workspace_id = :workspace_id AND document_id = :document_id
                    """
                ),
                {"workspace_id": workspace_id, "document_id": document_id},
            )
            row = res.mappings().first()
            if not row:
                return None
            return self._row_to_document(row)

    async def list_documents(
        self,
        workspace_id: str,
        state: str | None = None,
        limit: int = 50,
    ) -> list[VaultDocumentRecord]:
        async with self._session_factory() as session:
            await session.execute(
                text("SELECT set_config('cosa.workspace_id', :workspace_id, true)"),
                {"workspace_id": workspace_id},
            )
            if state:
                res = await session.execute(
                    text(
                        """
                        SELECT document_id, workspace_id, title, kind, state,
                               current_version_id, knowledge_source_id, created_by,
                               created_at, updated_at, classification, visibility,
                               access_policy_version, retention_until, legal_hold
                        FROM vault.documents
                        WHERE workspace_id = :workspace_id AND state = :state
                        ORDER BY updated_at DESC
                        LIMIT :limit
                        """
                    ),
                    {"workspace_id": workspace_id, "state": state, "limit": limit},
                )
            else:
                res = await session.execute(
                    text(
                        """
                        SELECT document_id, workspace_id, title, kind, state,
                               current_version_id, knowledge_source_id, created_by,
                               created_at, updated_at, classification, visibility,
                               access_policy_version, retention_until, legal_hold
                        FROM vault.documents
                        WHERE workspace_id = :workspace_id
                        ORDER BY updated_at DESC
                        LIMIT :limit
                        """
                    ),
                    {"workspace_id": workspace_id, "limit": limit},
                )
            return [self._row_to_document(r) for r in res.mappings().all()]

    async def update_document_state(
        self,
        workspace_id: str,
        document_id: UUID,
        state: str,
        knowledge_source_id: UUID | None = None,
    ) -> VaultDocumentRecord | None:
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            await session.execute(
                text("SELECT set_config('cosa.workspace_id', :workspace_id, true)"),
                {"workspace_id": workspace_id},
            )
            await session.execute(
                text(
                    """
                    UPDATE vault.documents
                    SET state = :state,
                        knowledge_source_id = COALESCE(:knowledge_source_id, knowledge_source_id),
                        updated_at = :updated_at
                    WHERE workspace_id = :workspace_id AND document_id = :document_id
                    """
                ),
                {
                    "state": state,
                    "knowledge_source_id": knowledge_source_id,
                    "updated_at": now,
                    "workspace_id": workspace_id,
                    "document_id": document_id,
                },
            )
            await session.commit()

        return await self.get_document(workspace_id, document_id)

    async def delete_document(
        self,
        workspace_id: str,
        document_id: UUID,
    ) -> bool:
        async with self._session_factory() as session:
            await session.execute(
                text("SELECT set_config('cosa.workspace_id', :workspace_id, true)"),
                {"workspace_id": workspace_id},
            )
            res = await session.execute(
                text(
                    """
                    DELETE FROM vault.documents
                    WHERE workspace_id = :workspace_id AND document_id = :document_id
                    """
                ),
                {"workspace_id": workspace_id, "document_id": document_id},
            )
            await session.commit()
            return (res.rowcount or 0) > 0

    async def list_versions(
        self,
        workspace_id: str,
        document_id: UUID,
    ) -> list[VaultDocumentVersionRecord]:
        async with self._session_factory() as session:
            await session.execute(
                text("SELECT set_config('cosa.workspace_id', :workspace_id, true)"),
                {"workspace_id": workspace_id},
            )
            res = await session.execute(
                text(
                    """
                    SELECT version_id, workspace_id, document_id, object_ref,
                           checksum_sha256, size_bytes, source_uri, created_by, created_at
                    FROM vault.document_versions
                    WHERE workspace_id = :workspace_id AND document_id = :document_id
                    ORDER BY created_at DESC
                    """
                ),
                {"workspace_id": workspace_id, "document_id": document_id},
            )
            return [self._row_to_version(r) for r in res.mappings().all()]

    async def get_version(
        self,
        workspace_id: str,
        version_id: UUID,
    ) -> VaultDocumentVersionRecord | None:
        async with self._session_factory() as session:
            await session.execute(
                text("SELECT set_config('cosa.workspace_id', :workspace_id, true)"),
                {"workspace_id": workspace_id},
            )
            res = await session.execute(
                text(
                    """
                    SELECT version_id, workspace_id, document_id, object_ref,
                           checksum_sha256, size_bytes, source_uri, created_by, created_at
                    FROM vault.document_versions
                    WHERE workspace_id = :workspace_id AND version_id = :version_id
                    """
                ),
                {"workspace_id": workspace_id, "version_id": version_id},
            )
            row = res.mappings().first()
            if not row:
                return None
            return self._row_to_version(row)

    async def get_knowledge_graph(
        self,
        workspace_id: str,
    ) -> VaultKnowledgeGraph:
        docs = await self.list_documents(workspace_id, limit=200)
        nodes: list[VaultKnowledgeGraphNode] = []
        edges: list[VaultKnowledgeGraphEdge] = []

        for d in docs:
            nodes.append(
                VaultKnowledgeGraphNode(
                    id=str(d.document_id),
                    label=d.title,
                    kind=d.kind,
                    source_ref=f"vault.documents:{d.document_id}",
                    metadata={"state": d.state, "created_at": d.created_at.isoformat()},
                )
            )

        return VaultKnowledgeGraph(nodes=nodes, edges=edges)

    async def grant_access(
        self,
        workspace_id: str,
        document_id: UUID,
        grant: VaultAccessGrant,
    ) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text("SELECT set_config('cosa.workspace_id', :workspace_id, true)"),
                {"workspace_id": workspace_id},
            )
            await session.execute(
                text(
                    """
                    INSERT INTO vault.document_access_grants (
                        workspace_id, document_id, subject_type, subject_id,
                        permission, granted_by
                    ) VALUES (
                        :workspace_id, :document_id, :subject_type, :subject_id,
                        :permission, :granted_by
                    )
                    ON CONFLICT (workspace_id, document_id, subject_type, subject_id, permission)
                    DO NOTHING
                    """
                ),
                {
                    "workspace_id": workspace_id,
                    "document_id": document_id,
                    "subject_type": grant.subject_type.value,
                    "subject_id": grant.subject_id,
                    "permission": grant.permission.value,
                    "granted_by": grant.granted_by,
                },
            )
            await session.commit()

    async def revoke_access(
        self,
        workspace_id: str,
        document_id: UUID,
        subject_type: VaultGrantSubjectType,
        subject_id: str,
    ) -> None:
        """Task 11 — xoá TOÀN BỘ grant (mọi permission) của đúng 1 subject trên
        1 document. Retrieval đọc grant trực tiếp mỗi lần gọi (không cache) —
        commit xong là ngay lập tức không còn match nữa, không cần bước
        "invalidate" riêng."""
        async with self._session_factory() as session:
            await session.execute(
                text("SELECT set_config('cosa.workspace_id', :workspace_id, true)"),
                {"workspace_id": workspace_id},
            )
            await session.execute(
                text(
                    """
                    DELETE FROM vault.document_access_grants
                    WHERE workspace_id = :workspace_id AND document_id = :document_id
                      AND subject_type = :subject_type AND subject_id = :subject_id
                    """
                ),
                {
                    "workspace_id": workspace_id,
                    "document_id": document_id,
                    "subject_type": subject_type.value,
                    "subject_id": subject_id,
                },
            )
            await session.commit()

    async def set_legal_hold(
        self,
        workspace_id: str,
        document_id: UUID,
        legal_hold: bool,
    ) -> VaultDocumentRecord | None:
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            await session.execute(
                text("SELECT set_config('cosa.workspace_id', :workspace_id, true)"),
                {"workspace_id": workspace_id},
            )
            await session.execute(
                text(
                    """
                    UPDATE vault.documents
                    SET legal_hold = :legal_hold, updated_at = :updated_at
                    WHERE workspace_id = :workspace_id AND document_id = :document_id
                    """
                ),
                {
                    "workspace_id": workspace_id,
                    "document_id": document_id,
                    "legal_hold": legal_hold,
                    "updated_at": now,
                },
            )
            await session.commit()
        return await self.get_document(workspace_id, document_id)

    async def resolve_accessible_document_ids(
        self,
        workspace_id: str,
        principal_id: str,
        role_ids: set[str],
    ) -> set[UUID]:
        async with self._session_factory() as session:
            await session.execute(
                text("SELECT set_config('cosa.workspace_id', :workspace_id, true)"),
                {"workspace_id": workspace_id},
            )
            res = await session.execute(
                text(
                    """
                    SELECT DISTINCT d.document_id
                    FROM vault.documents d
                    WHERE d.workspace_id = :workspace_id
                      AND (
                        (d.visibility = 'WORKSPACE' AND d.classification != 'RESTRICTED')
                        OR d.created_by = :principal_id
                        OR EXISTS (
                            SELECT 1 FROM vault.document_access_grants g
                            WHERE g.workspace_id = d.workspace_id
                              AND g.document_id = d.document_id
                              AND g.permission = 'read'
                              AND (
                                (g.subject_type = 'user' AND g.subject_id = :principal_id)
                                OR (g.subject_type = 'role' AND g.subject_id = ANY(:role_ids))
                              )
                        )
                      )
                    """
                ),
                {
                    "workspace_id": workspace_id,
                    "principal_id": principal_id,
                    "role_ids": list(role_ids),
                },
            )
            return {
                row["document_id"]
                if isinstance(row["document_id"], UUID)
                else UUID(str(row["document_id"]))
                for row in res.mappings().all()
            }

    async def list_authorized_documents(
        self,
        workspace_id: str,
        principal_id: str,
        role_ids: set[str],
    ) -> list[VaultDocumentRecord]:
        accessible_ids = await self.resolve_accessible_document_ids(
            workspace_id, principal_id, role_ids
        )
        if not accessible_ids:
            return []
        async with self._session_factory() as session:
            await session.execute(
                text("SELECT set_config('cosa.workspace_id', :workspace_id, true)"),
                {"workspace_id": workspace_id},
            )
            res = await session.execute(
                text(
                    """
                    SELECT document_id, workspace_id, title, kind, state,
                           current_version_id, knowledge_source_id, created_by,
                           created_at, updated_at, classification, visibility,
                           access_policy_version, retention_until, legal_hold
                    FROM vault.documents
                    WHERE workspace_id = :workspace_id AND document_id = ANY(:document_ids)
                    ORDER BY updated_at DESC
                    """
                ),
                {"workspace_id": workspace_id, "document_ids": list(accessible_ids)},
            )
            return [self._row_to_document(r) for r in res.mappings().all()]

    async def has_explicit_grant(
        self,
        workspace_id: str,
        document_id: UUID,
        principal_id: str,
        role_ids: set[str],
        permission: VaultPermission,
    ) -> bool:
        async with self._session_factory() as session:
            await session.execute(
                text("SELECT set_config('cosa.workspace_id', :workspace_id, true)"),
                {"workspace_id": workspace_id},
            )
            res = await session.execute(
                text(
                    """
                    SELECT 1 FROM vault.document_access_grants
                    WHERE workspace_id = :workspace_id AND document_id = :document_id
                      AND permission = :permission
                      AND (
                        (subject_type = 'user' AND subject_id = :principal_id)
                        OR (subject_type = 'role' AND subject_id = ANY(:role_ids))
                      )
                    LIMIT 1
                    """
                ),
                {
                    "workspace_id": workspace_id,
                    "document_id": document_id,
                    "permission": permission.value,
                    "principal_id": principal_id,
                    "role_ids": list(role_ids),
                },
            )
            return res.mappings().first() is not None

    @staticmethod
    def _row_to_document(row: Any) -> VaultDocumentRecord:
        return VaultDocumentRecord(
            document_id=row["document_id"]
            if isinstance(row["document_id"], UUID)
            else UUID(str(row["document_id"])),
            workspace_id=row["workspace_id"],
            title=row["title"],
            kind=row["kind"],
            state=row["state"],
            current_version_id=UUID(str(row["current_version_id"]))
            if row["current_version_id"]
            else None,
            knowledge_source_id=UUID(str(row["knowledge_source_id"]))
            if row["knowledge_source_id"]
            else None,
            created_by=row["created_by"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            classification=VaultClassification(row.get("classification"))
            if row.get("classification")
            else VaultClassification.INTERNAL,
            visibility=VaultVisibility(row.get("visibility"))
            if row.get("visibility")
            else VaultVisibility.PRIVATE,
            access_policy_version=row.get("access_policy_version")
            if row.get("access_policy_version") is not None
            else 1,
            retention_until=row.get("retention_until"),
            legal_hold=bool(row.get("legal_hold", False)),
        )

    @staticmethod
    def _row_to_version(row: Any) -> VaultDocumentVersionRecord:
        raw_ref = row["object_ref"]
        obj_ref = json.loads(raw_ref) if isinstance(raw_ref, str) else raw_ref
        return VaultDocumentVersionRecord(
            version_id=row["version_id"]
            if isinstance(row["version_id"], UUID)
            else UUID(str(row["version_id"])),
            workspace_id=row["workspace_id"],
            document_id=row["document_id"]
            if isinstance(row["document_id"], UUID)
            else UUID(str(row["document_id"])),
            object_ref=obj_ref if isinstance(obj_ref, dict) else {},
            checksum_sha256=row["checksum_sha256"],
            size_bytes=int(row["size_bytes"]),
            source_uri=row["source_uri"],
            created_by=row["created_by"],
            created_at=row["created_at"],
        )


class InMemoryVaultRepository:
    def __init__(self) -> None:
        self._documents: dict[tuple[str, UUID], VaultDocumentRecord] = {}
        self._versions: dict[tuple[str, UUID], VaultDocumentVersionRecord] = {}
        self._grants: dict[tuple[str, UUID], list[VaultAccessGrant]] = {}

    async def create_draft(
        self,
        workspace_id: str,
        title: str,
        kind: str = "document",
        created_by: str = "system",
        classification: VaultClassification = VaultClassification.INTERNAL,
        visibility: VaultVisibility = VaultVisibility.PRIVATE,
    ) -> VaultDocumentRecord:
        document_id = uuid4()
        now = datetime.now(UTC)
        rec = VaultDocumentRecord(
            document_id=document_id,
            workspace_id=workspace_id,
            title=title,
            kind=kind,
            state="DRAFT",
            current_version_id=None,
            knowledge_source_id=None,
            created_by=created_by,
            created_at=now,
            updated_at=now,
            classification=classification,
            visibility=visibility,
        )
        self._documents[(workspace_id, document_id)] = rec
        return rec

    async def grant_access(
        self,
        workspace_id: str,
        document_id: UUID,
        grant: VaultAccessGrant,
    ) -> None:
        key = (workspace_id, document_id)
        existing = self._grants.setdefault(key, [])
        if not any(
            g.subject_type == grant.subject_type
            and g.subject_id == grant.subject_id
            and g.permission == grant.permission
            for g in existing
        ):
            existing.append(grant)

    async def revoke_access(
        self,
        workspace_id: str,
        document_id: UUID,
        subject_type: VaultGrantSubjectType,
        subject_id: str,
    ) -> None:
        key = (workspace_id, document_id)
        existing = self._grants.get(key)
        if not existing:
            return
        self._grants[key] = [
            g
            for g in existing
            if not (g.subject_type == subject_type and g.subject_id == subject_id)
        ]

    async def set_legal_hold(
        self,
        workspace_id: str,
        document_id: UUID,
        legal_hold: bool,
    ) -> VaultDocumentRecord | None:
        doc = self._documents.get((workspace_id, document_id))
        if doc is None:
            return None
        updated = replace(doc, legal_hold=legal_hold, updated_at=datetime.now(UTC))
        self._documents[(workspace_id, document_id)] = updated
        return updated

    async def resolve_accessible_document_ids(
        self,
        workspace_id: str,
        principal_id: str,
        role_ids: set[str],
    ) -> set[UUID]:
        accessible: set[UUID] = set()
        for (ws, doc_id), doc in self._documents.items():
            if ws != workspace_id:
                continue
            workspace_wide_read = (
                doc.visibility == VaultVisibility.WORKSPACE
                and doc.classification != VaultClassification.RESTRICTED
            )
            if workspace_wide_read or doc.created_by == principal_id:
                accessible.add(doc_id)
                continue
            for grant in self._grants.get((workspace_id, doc_id), []):
                if grant.permission != VaultPermission.READ:
                    continue
                if (
                    grant.subject_type == VaultGrantSubjectType.USER
                    and grant.subject_id == principal_id
                ):
                    accessible.add(doc_id)
                    break
                if (
                    grant.subject_type == VaultGrantSubjectType.ROLE
                    and grant.subject_id in role_ids
                ):
                    accessible.add(doc_id)
                    break
        return accessible

    async def list_authorized_documents(
        self,
        workspace_id: str,
        principal_id: str,
        role_ids: set[str],
    ) -> list[VaultDocumentRecord]:
        accessible_ids = await self.resolve_accessible_document_ids(
            workspace_id, principal_id, role_ids
        )
        docs = [
            self._documents[(workspace_id, doc_id)]
            for doc_id in accessible_ids
            if (workspace_id, doc_id) in self._documents
        ]
        docs.sort(key=lambda x: x.updated_at, reverse=True)
        return docs

    async def append_version(
        self,
        workspace_id: str,
        document_id: UUID,
        object_ref: dict[str, Any],
        checksum_sha256: str,
        size_bytes: int,
        source_uri: str,
        created_by: str = "system",
        version_id: UUID | None = None,
    ) -> VaultDocumentVersionRecord:
        doc = self._documents.get((workspace_id, document_id))
        if doc is None:
            raise KeyError(f"Document {document_id} not found in workspace {workspace_id}")

        version_id = version_id or uuid4()
        now = datetime.now(UTC)
        v_rec = VaultDocumentVersionRecord(
            version_id=version_id,
            workspace_id=workspace_id,
            document_id=document_id,
            object_ref=object_ref,
            checksum_sha256=checksum_sha256,
            size_bytes=size_bytes,
            source_uri=source_uri,
            created_by=created_by,
            created_at=now,
        )
        self._versions[(workspace_id, version_id)] = v_rec

        # Cùng bug với update_document_state (Task 8) — dùng replace() để
        # không reset classification/visibility/access_policy_version khi
        # gán current_version_id mới.
        self._documents[(workspace_id, document_id)] = replace(
            doc,
            current_version_id=version_id,
            updated_at=now,
        )
        return v_rec

    async def get_document(
        self,
        workspace_id: str,
        document_id: UUID,
    ) -> VaultDocumentRecord | None:
        return self._documents.get((workspace_id, document_id))

    async def list_documents(
        self,
        workspace_id: str,
        state: str | None = None,
        limit: int = 50,
    ) -> list[VaultDocumentRecord]:
        docs = [
            d
            for d in self._documents.values()
            if d.workspace_id == workspace_id and (state is None or d.state == state)
        ]
        docs.sort(key=lambda x: x.updated_at, reverse=True)
        return docs[:limit]

    async def update_document_state(
        self,
        workspace_id: str,
        document_id: UUID,
        state: str,
        knowledge_source_id: UUID | None = None,
    ) -> VaultDocumentRecord | None:
        doc = self._documents.get((workspace_id, document_id))
        if doc is None:
            return None
        now = datetime.now(UTC)
        # Bug tìm thấy trong lúc làm Task 8: bản build cũ dựng lại
        # VaultDocumentRecord KHÔNG copy classification/visibility/
        # access_policy_version/retention_until/legal_hold — mỗi lần đổi state
        # (vd. publish) sẽ âm thầm reset các cột này về default (INTERNAL/
        # PRIVATE/1/None/False), khác hành vi PostgresVaultRepository (chỉ
        # UPDATE đúng state/knowledge_source_id/updated_at, không đụng cột
        # khác). Dùng dataclasses.replace() để không lặp lại lỗi tương tự nếu
        # sau này thêm field mới vào VaultDocumentRecord.
        updated = replace(
            doc,
            state=state,
            knowledge_source_id=knowledge_source_id or doc.knowledge_source_id,
            updated_at=now,
        )
        self._documents[(workspace_id, document_id)] = updated
        return updated

    async def delete_document(
        self,
        workspace_id: str,
        document_id: UUID,
    ) -> bool:
        if (workspace_id, document_id) in self._documents:
            del self._documents[(workspace_id, document_id)]
            # remove versions
            keys_to_del = [
                k
                for k, v in self._versions.items()
                if v.workspace_id == workspace_id and v.document_id == document_id
            ]
            for k in keys_to_del:
                del self._versions[k]
            return True
        return False

    async def list_versions(
        self,
        workspace_id: str,
        document_id: UUID,
    ) -> list[VaultDocumentVersionRecord]:
        vers = [
            v
            for v in self._versions.values()
            if v.workspace_id == workspace_id and v.document_id == document_id
        ]
        vers.sort(key=lambda x: x.created_at, reverse=True)
        return vers

    async def get_version(
        self,
        workspace_id: str,
        version_id: UUID,
    ) -> VaultDocumentVersionRecord | None:
        return self._versions.get((workspace_id, version_id))

    async def get_knowledge_graph(
        self,
        workspace_id: str,
    ) -> VaultKnowledgeGraph:
        docs = await self.list_documents(workspace_id, limit=200)
        nodes = [
            VaultKnowledgeGraphNode(
                id=str(d.document_id),
                label=d.title,
                kind=d.kind,
                source_ref=f"vault.documents:{d.document_id}",
                metadata={"state": d.state, "created_at": d.created_at.isoformat()},
            )
            for d in docs
        ]
        return VaultKnowledgeGraph(nodes=nodes, edges=[])

    async def has_explicit_grant(
        self,
        workspace_id: str,
        document_id: UUID,
        principal_id: str,
        role_ids: set[str],
        permission: VaultPermission,
    ) -> bool:
        for grant in self._grants.get((workspace_id, document_id), []):
            if grant.permission != permission:
                continue
            if (
                grant.subject_type == VaultGrantSubjectType.USER
                and grant.subject_id == principal_id
            ):
                return True
            if grant.subject_type == VaultGrantSubjectType.ROLE and grant.subject_id in role_ids:
                return True
        return False
