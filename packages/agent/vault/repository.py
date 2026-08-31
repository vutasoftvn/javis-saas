"""Vault Repository: Workspace-isolated storage for Documents, Versions, and Knowledge Graph."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable
from uuid import UUID, uuid4

from sqlalchemy import text

from agent.vault.models import (
    VaultDocumentRecord,
    VaultDocumentVersionRecord,
    VaultKnowledgeGraph,
    VaultKnowledgeGraphEdge,
    VaultKnowledgeGraphNode,
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


class PostgresVaultRepository:
    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory

    async def create_draft(
        self,
        workspace_id: str,
        title: str,
        kind: str = "document",
        created_by: str = "system",
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
                        created_at, updated_at
                    ) VALUES (
                        :document_id, :workspace_id, :title, :kind, 'DRAFT',
                        NULL, NULL, :created_by, :created_at, :updated_at
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
    ) -> VaultDocumentVersionRecord:
        version_id = uuid4()
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
                           created_at, updated_at
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
                               created_at, updated_at
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
                               created_at, updated_at
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

    async def create_draft(
        self,
        workspace_id: str,
        title: str,
        kind: str = "document",
        created_by: str = "system",
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
        )
        self._documents[(workspace_id, document_id)] = rec
        return rec

    async def append_version(
        self,
        workspace_id: str,
        document_id: UUID,
        object_ref: dict[str, Any],
        checksum_sha256: str,
        size_bytes: int,
        source_uri: str,
        created_by: str = "system",
    ) -> VaultDocumentVersionRecord:
        doc = self._documents.get((workspace_id, document_id))
        if doc is None:
            raise KeyError(f"Document {document_id} not found in workspace {workspace_id}")

        version_id = uuid4()
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

        # Update doc
        self._documents[(workspace_id, document_id)] = VaultDocumentRecord(
            document_id=doc.document_id,
            workspace_id=doc.workspace_id,
            title=doc.title,
            kind=doc.kind,
            state=doc.state,
            current_version_id=version_id,
            knowledge_source_id=doc.knowledge_source_id,
            created_by=doc.created_by,
            created_at=doc.created_at,
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
        updated = VaultDocumentRecord(
            document_id=doc.document_id,
            workspace_id=doc.workspace_id,
            title=doc.title,
            kind=doc.kind,
            state=state,
            current_version_id=doc.current_version_id,
            knowledge_source_id=knowledge_source_id or doc.knowledge_source_id,
            created_by=doc.created_by,
            created_at=doc.created_at,
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
