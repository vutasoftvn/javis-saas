"""Task 4 (plan local-first-enterprise-knowledge) — factory duy nhất dựng
dependency cho knowledge ingestion pipeline (local storage + scanner +
isolated converter + service), dùng chung giữa API process và worker process.

Production KHÔNG được âm thầm dùng `FakeDocumentMalwareScanner` hay
`InProcessConversionSandbox` — `assert_production_scanner_ready`/
`assert_production_conversion_ready` (đã có từ trước) raise nếu thiếu
attestation hoặc instance test-only bị truyền vào production.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent.knowledge.service import KnowledgeIngestionService

from apps.cosa.knowledge_ingestion.conversion_sandbox import (
    DocumentConversionSandbox,
    InProcessConversionSandbox,
    assert_production_conversion_ready,
)
from apps.cosa.knowledge_ingestion.scanner import (
    DocumentMalwareScanner,
    FakeDocumentMalwareScanner,
)
from apps.cosa.knowledge_ingestion.workspace_store import (
    InMemoryUploadTicketRepository,
    PostgresUploadTicketRepository,
    UploadTicketRepository,
    WorkspaceDocumentStore,
)

__all__ = ["KnowledgeIngestionDependencies", "build_knowledge_ingestion_dependencies"]


@dataclass(frozen=True)
class KnowledgeIngestionDependencies:
    store: WorkspaceDocumentStore
    scanner: DocumentMalwareScanner
    sandbox: DocumentConversionSandbox
    service: KnowledgeIngestionService
    ticket_repository: UploadTicketRepository


def _current_environment() -> str:
    return os.environ.get("ENVIRONMENT", os.environ.get("APP_ENV", "development")).lower()


def build_knowledge_ingestion_dependencies(
    *,
    database_url: str | None = None,
    session_factory: Any | None = None,
    storage_root: Path | None = None,
    scanner: DocumentMalwareScanner | None = None,
    sandbox: DocumentConversionSandbox | None = None,
    knowledge_service: KnowledgeIngestionService | None = None,
) -> KnowledgeIngestionDependencies:
    """Dựng đúng 1 bộ dependency cho vòng đời process (API hoặc worker).

    Production yêu cầu TẤT CẢ: `scanner`/`sandbox` thật được truyền vào tường
    minh (factory này không tự bịa ra adapter thật — đó là trách nhiệm của
    composition root khi operator đã wire 1 scanner/sandbox process boundary
    thật) + attestation env var qua `assert_production_conversion_ready`.
    """
    env = _current_environment()

    resolved_root = storage_root or (
        Path(os.environ["COSA_WORKSPACE_STORAGE_ROOT"])
        if os.environ.get("COSA_WORKSPACE_STORAGE_ROOT")
        else None
    )

    if env == "production":
        missing = [
            name
            for name, val in (("scanner", scanner), ("sandbox", sandbox), ("storage_root", resolved_root))
            if val is None
        ]
        if missing:
            raise RuntimeError(
                f"knowledge ingestion dependencies must be injected in production: {missing}"
            )
        if session_factory is None and not database_url:
            raise RuntimeError(
                "knowledge ingestion dependencies must be injected in production: "
                "['session_factory' or 'database_url']"
            )

    assert_production_conversion_ready(sandbox, scanner, env)

    if resolved_root is None:
        # Dev/test — chưa cấu hình storage root thật, dùng thư mục tạm cục bộ
        # tiến trình (không phải production path, không phải S3).
        import tempfile

        resolved_root = Path(tempfile.mkdtemp(prefix="cosa-knowledge-store-"))

    ticket_repository: UploadTicketRepository
    if session_factory is not None:
        ticket_repository = PostgresUploadTicketRepository(session_factory)
    elif database_url:
        from apps.cosa.composition.storage_factory import build_postgres_session_factory

        _, sf = build_postgres_session_factory(database_url)
        ticket_repository = PostgresUploadTicketRepository(sf)
    else:
        ticket_repository = InMemoryUploadTicketRepository()

    store = WorkspaceDocumentStore(resolved_root, ticket_repository)
    resolved_scanner = scanner or FakeDocumentMalwareScanner(verdict="clean")
    resolved_sandbox = sandbox or InProcessConversionSandbox()

    if knowledge_service is None:
        if session_factory is not None:
            from agent.knowledge.providers.postgres import PostgresKnowledgeStore

            knowledge_service = KnowledgeIngestionService(PostgresKnowledgeStore(session_factory))
        elif database_url:
            from agent.knowledge.store import get_knowledge_store

            knowledge_service = KnowledgeIngestionService(get_knowledge_store(database_url))
        else:
            from agent.knowledge.store import InMemoryKnowledgeStore

            knowledge_service = KnowledgeIngestionService(InMemoryKnowledgeStore())

    return KnowledgeIngestionDependencies(
        store=store,
        scanner=resolved_scanner,
        sandbox=resolved_sandbox,
        service=knowledge_service,
        ticket_repository=ticket_repository,
    )
