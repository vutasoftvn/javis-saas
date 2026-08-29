from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import text

from agent.knowledge.models import CitationProvenance, KnowledgeChunk, KnowledgeDocument

__all__ = ["PostgresKnowledgeStore"]


class ConfigurationError(Exception):
    """Lỗi cấu hình store — cùng mẫu với agent.memory.base.ConfigurationError."""


class PostgresKnowledgeStore:
    """PostgreSQL implementation của KnowledgeStore Protocol — CHƯA từng tồn
    tại trước Wave 8 (chỉ có InMemoryKnowledgeStore dù migration 003 đã tạo
    sẵn bảng `knowledge.knowledge_sources`/`knowledge_chunks` từ trước — schema
    tồn tại nhưng không ai ghi/đọc qua Postgres). Wire theo source→source_version
    →chunks→chunk_embeddings (Blueprint V2 §27, migration 010).

    Mỗi lần `save_document()` gọi lại cho CÙNG `document.id` sẽ tạo 1
    `source_version` MỚI nếu nội dung (content_hash tổng hợp từ toàn bộ chunk)
    đổi so với version gần nhất — giữ lịch sử version, không ghi đè.
    """

    def __init__(self, db_session_factory: Any = None) -> None:
        if db_session_factory is None:
            raise ConfigurationError(
                "PostgresKnowledgeStore requires a valid `db_session_factory`. "
                "For in-memory testing without a database, use `InMemoryKnowledgeStore`."
            )
        self._session_factory = db_session_factory

    @staticmethod
    def _compute_document_content_hash(doc: KnowledgeDocument) -> str:
        joined = "\n".join(c.content for c in sorted(doc.chunks, key=lambda c: c.chunk_index))
        return hashlib.sha256(joined.encode("utf-8")).hexdigest()

    async def save_document(self, doc: KnowledgeDocument) -> None:
        content_hash = self._compute_document_content_hash(doc)

        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO knowledge.knowledge_sources (
                        id, workspace_id, title, source_type, uri, authority_class,
                        status, metadata, created_at
                    ) VALUES (
                        :id, :workspace_id, :title, :source_type, :uri, :authority_class,
                        :status, :metadata, :created_at
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        authority_class = EXCLUDED.authority_class,
                        status = EXCLUDED.status,
                        metadata = EXCLUDED.metadata;
                    """
                ),
                {
                    "id": doc.id,
                    "workspace_id": doc.workspace_id,
                    "title": doc.title,
                    "source_type": doc.media_type,
                    "uri": doc.source_uri,
                    "authority_class": doc.authority_class,
                    "status": doc.ingest_status,
                    "metadata": json.dumps(doc.metadata),
                    "created_at": doc.created_at,
                },
            )

            existing_version = (
                (
                    await session.execute(
                        text(
                            """
                        SELECT id, version, content_hash FROM knowledge.source_versions
                        WHERE source_id = :source_id ORDER BY version DESC LIMIT 1
                        """
                        ),
                        {"source_id": doc.id},
                    )
                )
                .mappings()
                .first()
            )

            if existing_version and existing_version["content_hash"] == content_hash:
                source_version_id = existing_version["id"]
            else:
                next_version = (existing_version["version"] + 1) if existing_version else 1
                source_version_id = f"{doc.id}_v{next_version}"

                # Extract optional provenance fields from metadata
                # Note: metadata keys match what normalization.py sets:
                # - ingestion_id (metadata key) → ingestion_run_id (DB column)
                # - converter_name (metadata key) → parser_name (DB column)
                # - converter_version (metadata key) → parser_version (DB column)
                ingestion_run_id = doc.metadata.get("ingestion_id") if doc.metadata else None
                parser_name = doc.metadata.get("converter_name") if doc.metadata else None
                parser_version = doc.metadata.get("converter_version") if doc.metadata else None

                await session.execute(
                    text(
                        """
                        INSERT INTO knowledge.source_versions (id, source_id, version, content_hash, ingestion_run_id, parser_name, parser_version, created_at)
                        VALUES (:id, :source_id, :version, :content_hash, :ingestion_run_id, :parser_name, :parser_version, now())
                        ON CONFLICT (source_id, version) DO NOTHING;
                        """
                    ),
                    {
                        "id": source_version_id,
                        "source_id": doc.id,
                        "version": next_version,
                        "content_hash": content_hash,
                        "ingestion_run_id": ingestion_run_id,
                        "parser_name": parser_name,
                        "parser_version": parser_version,
                    },
                )

            for chunk in doc.chunks:
                await session.execute(
                    text(
                        """
                        INSERT INTO knowledge.knowledge_chunks (
                            id, source_id, workspace_id, source_version_id, chunk_index,
                            content, embedding_model, embedding_dimensions, embedding_version,
                            content_hash, chunker_name, chunker_version, metadata, created_at
                        ) VALUES (
                            :id, :source_id, :workspace_id, :source_version_id, :chunk_index,
                            :content, :embedding_model, :embedding_dimensions, :embedding_version,
                            :content_hash, :chunker_name, :chunker_version, :metadata, :created_at
                        )
                        ON CONFLICT (id) DO UPDATE SET
                            content = EXCLUDED.content,
                            source_version_id = EXCLUDED.source_version_id,
                            metadata = EXCLUDED.metadata;
                        """
                    ),
                    {
                        "id": chunk.id,
                        "source_id": doc.id,
                        "workspace_id": doc.workspace_id,
                        "source_version_id": source_version_id,
                        "chunk_index": chunk.chunk_index,
                        "content": chunk.content,
                        "embedding_model": chunk.embedding_model,
                        "embedding_dimensions": len(chunk.embedding) if chunk.embedding else None,
                        "embedding_version": chunk.embedding_version,
                        "content_hash": chunk.content_hash,
                        "chunker_name": chunk.chunker_name,
                        "chunker_version": chunk.chunker_version,
                        "metadata": json.dumps(chunk.metadata),
                        "created_at": chunk.created_at,
                    },
                )

                if chunk.embedding and chunk.embedding_model and chunk.embedding_version:
                    await session.execute(
                        text(
                            """
                            INSERT INTO knowledge.chunk_embeddings (
                                chunk_id, embedding_model, embedding_version, dimensions, embedding, created_at
                            ) VALUES (:chunk_id, :embedding_model, :embedding_version, :dimensions, :embedding, now())
                            ON CONFLICT (chunk_id, embedding_model, embedding_version) DO UPDATE SET
                                embedding = EXCLUDED.embedding;
                            """
                        ),
                        {
                            "chunk_id": chunk.id,
                            "embedding_model": chunk.embedding_model,
                            "embedding_version": chunk.embedding_version,
                            "dimensions": len(chunk.embedding),
                            "embedding": str(chunk.embedding),
                        },
                    )

            await session.commit()

    async def get_document(self, doc_id: str, workspace_id: str) -> KnowledgeDocument | None:
        async with self._session_factory() as session:
            # M3 §4 — bind workspace ở tầng query, không fetch-rồi-so-sánh.
            src_row = (
                (
                    await session.execute(
                        text(
                            """
                        SELECT id, workspace_id, title, source_type, uri, authority_class, status, metadata, created_at
                        FROM knowledge.knowledge_sources
                        WHERE id = :id AND workspace_id = :ws
                        """
                        ),
                        {"id": doc_id, "ws": workspace_id},
                    )
                )
                .mappings()
                .first()
            )
            if not src_row:
                return None

            chunk_rows = (
                (
                    await session.execute(
                        text(
                            """
                        SELECT id, source_id, workspace_id, chunk_index, content, content_hash,
                               chunker_name, chunker_version, embedding_model, embedding_version, metadata, created_at
                        FROM knowledge.knowledge_chunks
                        WHERE source_id = :source_id AND workspace_id = :ws
                        ORDER BY chunk_index ASC
                        """
                        ),
                        {"source_id": doc_id, "ws": workspace_id},
                    )
                )
                .mappings()
                .all()
            )

            chunks = [
                KnowledgeChunk(
                    id=r["id"],
                    document_id=r["source_id"],
                    workspace_id=r["workspace_id"],
                    chunk_index=r["chunk_index"],
                    content=r["content"],
                    content_hash=r["content_hash"],
                    chunker_name=r["chunker_name"],
                    chunker_version=r["chunker_version"],
                    embedding_model=r["embedding_model"],
                    embedding_version=r["embedding_version"],
                    metadata=self._parse_json(r["metadata"]) or {},
                    created_at=r["created_at"],
                )
                for r in chunk_rows
            ]

            return KnowledgeDocument(
                id=src_row["id"],
                workspace_id=src_row["workspace_id"],
                title=src_row["title"],
                source_uri=src_row["uri"],
                media_type=src_row["source_type"],
                authority_class=src_row["authority_class"],
                ingest_status=src_row["status"],
                chunks=chunks,
                metadata=self._parse_json(src_row["metadata"]) or {},
                created_at=src_row["created_at"],
            )

    async def search_chunks(
        self,
        *,
        workspace_id: str,
        query: str,
        limit: int = 5,
    ) -> list[CitationProvenance]:
        """Tìm kiếm từ khoá đơn giản (ILIKE) — KHÔNG phải semantic/vector
        search thật (đó cần chunk_embeddings + cosine distance query, để lại
        cho lúc có embedding model thật/pgvector index tuning cụ thể, tránh
        xây 1 vector search chưa được benchmark)."""
        async with self._session_factory() as session:
            rows = (
                (
                    await session.execute(
                        text(
                            """
                        SELECT c.id AS chunk_id, c.content, c.chunk_index,
                               s.id AS source_id, s.title AS source_title, s.uri AS source_uri
                        FROM knowledge.knowledge_chunks c
                        JOIN knowledge.knowledge_sources s ON s.id = c.source_id
                        WHERE c.workspace_id = :workspace_id AND c.content ILIKE :query
                        ORDER BY c.chunk_index ASC
                        LIMIT :limit
                        """
                        ),
                        {"workspace_id": workspace_id, "query": f"%{query}%", "limit": limit},
                    )
                )
                .mappings()
                .all()
            )

            return [
                CitationProvenance(
                    chunk_id=r["chunk_id"],
                    document_id=r["source_id"],
                    document_title=r["source_title"],
                    source_uri=r["source_uri"],
                    snippet=r["content"],
                    similarity_score=1.0,
                )
                for r in rows
            ]

    async def search_chunks_semantic(
        self,
        *,
        workspace_id: str,
        query_embedding: list[float],
        limit: int = 5,
    ) -> list[CitationProvenance]:
        """pgvector cosine distance trên `knowledge.knowledge_chunks.embedding`
        (inline vector, migration 010). Chỉ xét chunk cùng workspace VÀ có
        embedding. Chất lượng ngữ nghĩa tuỳ EmbeddingProvider đang wire —
        `retrieve()` gọi đường này chỉ khi eval score đạt ngưỡng."""
        vec_literal = "[" + ",".join(f"{float(x):.8f}" for x in query_embedding) + "]"
        async with self._session_factory() as session:
            rows = (
                (
                    await session.execute(
                        text(
                            """
                        SELECT c.id AS chunk_id, c.content,
                               s.id AS source_id, s.title AS source_title, s.uri AS source_uri,
                               1 - (c.embedding <=> CAST(:qvec AS vector)) AS similarity
                        FROM knowledge.knowledge_chunks c
                        JOIN knowledge.knowledge_sources s ON s.id = c.source_id
                        WHERE c.workspace_id = :workspace_id AND c.embedding IS NOT NULL
                        ORDER BY c.embedding <=> CAST(:qvec AS vector)
                        LIMIT :limit
                        """
                        ),
                        {"qvec": vec_literal, "workspace_id": workspace_id, "limit": limit},
                    )
                )
                .mappings()
                .all()
            )

            return [
                CitationProvenance(
                    chunk_id=r["chunk_id"],
                    document_id=r["source_id"],
                    document_title=r["source_title"],
                    source_uri=r["source_uri"],
                    snippet=r["content"],
                    similarity_score=float(r["similarity"]) if r["similarity"] is not None else 0.0,
                )
                for r in rows
            ]

    @staticmethod
    def _parse_json(val: Any) -> Any:
        if val is None:
            return None
        if isinstance(val, (dict, list)):
            return val
        if isinstance(val, str):
            try:
                return json.loads(val)
            except Exception:
                return val
        return val
