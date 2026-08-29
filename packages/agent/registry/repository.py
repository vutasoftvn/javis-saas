from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

from sqlalchemy import text

from agent.registry.models import PublishedSpecRecord

__all__ = [
    "InMemorySpecRegistryRepository",
    "PostgresSpecRegistryRepository",
    "SpecDependencyMissingError",
    "SpecRegistryRepository",
    "SpecVersionHashConflictError",
]


class SpecVersionHashConflictError(Exception):
    """Raised khi publish 1 (spec_kind, spec_id, version) đã tồn tại với
    definition_hash KHÁC — published version bất biến (Blueprint V2 §56
    anti-pattern "published spec edited in place"). Muốn đổi nội dung phải
    tăng version, không được ghi đè version cũ."""

    def __init__(
        self,
        spec_kind: str,
        spec_id: str,
        version: str,
        existing_hash: str | None = None,
        new_hash: str | None = None,
    ) -> None:
        super().__init__(
            f"Spec '{spec_kind}/{spec_id}@{version}' đã publish với hash "
            f"'{existing_hash}', không thể publish lại với hash khác '{new_hash}' — "
            f"tăng version thay vì ghi đè."
        )
        self.spec_kind = spec_kind
        self.spec_id = spec_id
        self.version = version
        self.existing_hash = existing_hash
        self.new_hash = new_hash


class SpecDependencyMissingError(Exception):
    """Raised khi AgentSpec pin 1 dependency (prompt_ref/model_policy_ref)
    chưa publish trong registry, hoặc đã publish nhưng với definition_hash
    khác — publish_agent_spec() không được ghi 1 spec có floating/broken
    dependency ref (Wave M2, tương đương INV-A3 của
    COSA_MARIN_PATTERNS_INTEGRATION_AND_ADJUSTMENT_PLAN_2026-08-26.md)."""

    def __init__(
        self, dependency_kind: str, dependency_id: str, dependency_version: str, reason: str
    ) -> None:
        super().__init__(
            f"AgentSpec pins {dependency_kind} '{dependency_id}@{dependency_version}' "
            f"({reason}) — publish {dependency_kind} trước khi publish AgentSpec."
        )
        self.dependency_kind = dependency_kind
        self.dependency_id = dependency_id
        self.dependency_version = dependency_version
        self.reason = reason


@runtime_checkable
class SpecRegistryRepository(Protocol):
    """Protocol cho registry lưu published spec bất biến theo Blueprint V2 §25."""

    async def publish(self, record: PublishedSpecRecord) -> PublishedSpecRecord: ...
    async def get(
        self, spec_kind: str, spec_id: str, version: str
    ) -> PublishedSpecRecord | None: ...
    async def get_by_hash(
        self, spec_kind: str, spec_id: str, definition_hash: str
    ) -> PublishedSpecRecord | None: ...
    async def list_versions(self, spec_kind: str, spec_id: str) -> list[PublishedSpecRecord]: ...
    async def list_all(self, spec_kind: str | None = None) -> list[PublishedSpecRecord]: ...
    async def update_status(
        self, spec_kind: str, spec_id: str, version: str, status: str
    ) -> PublishedSpecRecord | None: ...


class InMemorySpecRegistryRepository:
    """In-memory implementation — chỉ dùng test/local dev, không dùng production
    (không durable qua restart, vi phạm chính mục đích của registry)."""

    def __init__(self) -> None:
        self._by_version: dict[tuple[str, str, str], PublishedSpecRecord] = {}

    async def publish(self, record: PublishedSpecRecord) -> PublishedSpecRecord:
        key = (record.spec_kind, record.spec_id, record.version)
        existing = self._by_version.get(key)
        if existing is not None:
            if existing.definition_hash != record.definition_hash:
                raise SpecVersionHashConflictError(
                    record.spec_kind,
                    record.spec_id,
                    record.version,
                    existing.definition_hash,
                    record.definition_hash,
                )
            return existing.model_copy(deep=True)
        stored = record.model_copy(deep=True)
        self._by_version[key] = stored
        return stored.model_copy(deep=True)

    async def get(self, spec_kind: str, spec_id: str, version: str) -> PublishedSpecRecord | None:
        r = self._by_version.get((spec_kind, spec_id, version))
        return r.model_copy(deep=True) if r else None

    async def get_by_hash(
        self, spec_kind: str, spec_id: str, definition_hash: str
    ) -> PublishedSpecRecord | None:
        for r in self._by_version.values():
            if (
                r.spec_kind == spec_kind
                and r.spec_id == spec_id
                and r.definition_hash == definition_hash
            ):
                return r.model_copy(deep=True)
        return None

    async def list_versions(self, spec_kind: str, spec_id: str) -> list[PublishedSpecRecord]:
        return [
            r.model_copy(deep=True)
            for r in self._by_version.values()
            if r.spec_kind == spec_kind and r.spec_id == spec_id
        ]

    async def list_all(self, spec_kind: str | None = None) -> list[PublishedSpecRecord]:
        return [
            r.model_copy(deep=True)
            for r in self._by_version.values()
            if spec_kind is None or r.spec_kind == spec_kind
        ]

    async def update_status(
        self, spec_kind: str, spec_id: str, version: str, status: str
    ) -> PublishedSpecRecord | None:
        key = (spec_kind, spec_id, version)
        r = self._by_version.get(key)
        if r is None:
            return None
        updated = r.model_copy(deep=True)
        updated.status = status
        if status == "retired":
            updated.retired_at = datetime.now(UTC)
        self._by_version[key] = updated
        return updated.model_copy(deep=True)


class PostgresSpecRegistryRepository:
    """PostgreSQL implementation persisting to agent_registry.published_specs (migration 007)."""

    def __init__(self, db_session_factory: Any) -> None:
        if db_session_factory is None:
            raise ValueError("PostgresSpecRegistryRepository requires a valid db_session_factory.")
        self._session_factory = db_session_factory

    async def publish(self, record: PublishedSpecRecord) -> PublishedSpecRecord:
        existing = await self.get(record.spec_kind, record.spec_id, record.version)
        if existing is not None:
            if existing.definition_hash != record.definition_hash:
                raise SpecVersionHashConflictError(
                    record.spec_kind,
                    record.spec_id,
                    record.version,
                    existing.definition_hash,
                    record.definition_hash,
                )
            return existing

        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO agent_registry.published_specs (
                        spec_kind, spec_id, version, definition_hash, content, status,
                        publisher, created_at, published_at, retired_at
                    ) VALUES (
                        :spec_kind, :spec_id, :version, :definition_hash, :content, :status,
                        :publisher, :created_at, :published_at, :retired_at
                    )
                    ON CONFLICT (spec_kind, spec_id, version) DO NOTHING
                    """
                ),
                {
                    "spec_kind": record.spec_kind,
                    "spec_id": record.spec_id,
                    "version": record.version,
                    "definition_hash": record.definition_hash,
                    "content": json.dumps(record.content),
                    "status": record.status,
                    "publisher": record.publisher,
                    "created_at": record.created_at,
                    "published_at": record.published_at,
                    "retired_at": record.retired_at,
                },
            )
            await session.commit()

        # Đọc lại — nếu 2 process cùng publish đồng thời (ON CONFLICT DO NOTHING),
        # bản ghi thắng cuộc đua mới là sự thật, không phải `record` ta vừa gửi.
        stored = await self.get(record.spec_kind, record.spec_id, record.version)
        if stored is None:
            # Không nên xảy ra (vừa INSERT hoặc đã tồn tại), nhưng phòng thủ.
            return record
        if stored.definition_hash != record.definition_hash:
            raise SpecVersionHashConflictError(
                record.spec_kind,
                record.spec_id,
                record.version,
                stored.definition_hash,
                record.definition_hash,
            )
        return stored

    async def get(self, spec_kind: str, spec_id: str, version: str) -> PublishedSpecRecord | None:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    SELECT spec_kind, spec_id, version, definition_hash, content, status,
                           publisher, created_at, published_at, retired_at
                    FROM agent_registry.published_specs
                    WHERE spec_kind = :spec_kind AND spec_id = :spec_id AND version = :version
                    """
                ),
                {"spec_kind": spec_kind, "spec_id": spec_id, "version": version},
            )
            row = res.mappings().first()
            return self._row_to_record(row) if row else None

    async def get_by_hash(
        self, spec_kind: str, spec_id: str, definition_hash: str
    ) -> PublishedSpecRecord | None:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    SELECT spec_kind, spec_id, version, definition_hash, content, status,
                           publisher, created_at, published_at, retired_at
                    FROM agent_registry.published_specs
                    WHERE spec_kind = :spec_kind AND spec_id = :spec_id AND definition_hash = :definition_hash
                    """
                ),
                {"spec_kind": spec_kind, "spec_id": spec_id, "definition_hash": definition_hash},
            )
            row = res.mappings().first()
            return self._row_to_record(row) if row else None

    async def list_versions(self, spec_kind: str, spec_id: str) -> list[PublishedSpecRecord]:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    SELECT spec_kind, spec_id, version, definition_hash, content, status,
                           publisher, created_at, published_at, retired_at
                    FROM agent_registry.published_specs
                    WHERE spec_kind = :spec_kind AND spec_id = :spec_id
                    ORDER BY created_at ASC
                    """
                ),
                {"spec_kind": spec_kind, "spec_id": spec_id},
            )
            return [self._row_to_record(r) for r in res.mappings().all()]

    async def list_all(self, spec_kind: str | None = None) -> list[PublishedSpecRecord]:
        async with self._session_factory() as session:
            if spec_kind:
                res = await session.execute(
                    text(
                        """
                        SELECT spec_kind, spec_id, version, definition_hash, content, status,
                               publisher, created_at, published_at, retired_at
                        FROM agent_registry.published_specs
                        WHERE spec_kind = :spec_kind
                        ORDER BY created_at ASC
                        """
                    ),
                    {"spec_kind": spec_kind},
                )
            else:
                res = await session.execute(
                    text(
                        """
                        SELECT spec_kind, spec_id, version, definition_hash, content, status,
                               publisher, created_at, published_at, retired_at
                        FROM agent_registry.published_specs
                        ORDER BY created_at ASC
                        """
                    )
                )
            return [self._row_to_record(r) for r in res.mappings().all()]

    async def update_status(
        self, spec_kind: str, spec_id: str, version: str, status: str
    ) -> PublishedSpecRecord | None:
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            if status == "retired":
                res = await session.execute(
                    text(
                        """
                        UPDATE agent_registry.published_specs
                        SET status = :status, retired_at = :retired_at
                        WHERE spec_kind = :spec_kind AND spec_id = :spec_id AND version = :version
                        RETURNING spec_kind, spec_id, version, definition_hash, content, status,
                                  publisher, created_at, published_at, retired_at
                        """
                    ),
                    {
                        "spec_kind": spec_kind,
                        "spec_id": spec_id,
                        "version": version,
                        "status": status,
                        "retired_at": now,
                    },
                )
            else:
                res = await session.execute(
                    text(
                        """
                        UPDATE agent_registry.published_specs
                        SET status = :status
                        WHERE spec_kind = :spec_kind AND spec_id = :spec_id AND version = :version
                        RETURNING spec_kind, spec_id, version, definition_hash, content, status,
                                  publisher, created_at, published_at, retired_at
                        """
                    ),
                    {
                        "spec_kind": spec_kind,
                        "spec_id": spec_id,
                        "version": version,
                        "status": status,
                    },
                )
            await session.commit()
            row = res.mappings().first()
            return self._row_to_record(row) if row else None

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

    @classmethod
    def _row_to_record(cls, row: Any) -> PublishedSpecRecord:
        return PublishedSpecRecord(
            spec_kind=row["spec_kind"],
            spec_id=row["spec_id"],
            version=row["version"],
            definition_hash=row["definition_hash"],
            content=cls._parse_json(row["content"]) or {},
            status=row["status"],
            publisher=row["publisher"],
            created_at=row["created_at"],
            published_at=row["published_at"],
            retired_at=row["retired_at"],
        )
