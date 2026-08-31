"""Workforce persistence repository: assignments, cost observations, and runtime signal outbox."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from agent.workforce.models import (
    RunCostObservationRecord,
    RuntimeSignalOutboxRecord,
    WorkforceAssignmentRecord,
)

__all__ = [
    "InMemoryWorkforceRepository",
    "PostgresWorkforceRepository",
    "WorkforceRepository",
]


@runtime_checkable
class WorkforceRepository(Protocol):
    async def create_assignment(
        self,
        workspace_id: str,
        functional_key: str,
        spec_id: str,
        spec_version: str,
        definition_hash: str,
        configured_by: str,
        reports_to_assignment_id: UUID | str | None = None,
        assignment_id: UUID | str | None = None,
    ) -> WorkforceAssignmentRecord: ...

    async def get_assignment(
        self, workspace_id: str, assignment_id: UUID | str
    ) -> WorkforceAssignmentRecord | None: ...

    async def list_assignments(
        self, workspace_id: str, status: str | None = None
    ) -> list[WorkforceAssignmentRecord]: ...

    async def retire_assignment(
        self, workspace_id: str, assignment_id: UUID | str
    ) -> WorkforceAssignmentRecord | None: ...

    async def list_cost_observations(
        self, workspace_id: str, run_id: str | None = None, limit: int = 100
    ) -> list[RunCostObservationRecord]: ...

    async def record_cost_observation(
        self,
        workspace_id: str,
        run_id: str,
        provider_key: str,
        model_key: str,
        observed_at: datetime,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        cost_amount: Decimal | float | None = None,
        currency: str | None = None,
        observation_id: UUID | str | None = None,
    ) -> RunCostObservationRecord: ...

    async def enqueue_runtime_signal(
        self,
        workspace_id: str,
        source_kind: str,
        source_id: str,
        sequence: int,
        state: str,
        observed_at: datetime,
        correlation_id: str | None = None,
        payload_hash: str | None = None,
        outbox_id: UUID | str | None = None,
    ) -> RuntimeSignalOutboxRecord: ...

    async def claim_pending_signals(
        self, limit: int = 50, max_attempts: int = 10
    ) -> list[RuntimeSignalOutboxRecord]: ...

    async def mark_signal_delivered(
        self, outbox_id: UUID | str, delivered_at: datetime | None = None
    ) -> None: ...

    async def mark_signal_failed(
        self, outbox_id: UUID | str, next_attempt_at: datetime
    ) -> None: ...

    async def is_signal_delivered(
        self, workspace_id: str, source_kind: str, source_id: str, sequence: int
    ) -> bool: ...


class PostgresWorkforceRepository:
    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create_assignment(
        self,
        workspace_id: str,
        functional_key: str,
        spec_id: str,
        spec_version: str,
        definition_hash: str,
        configured_by: str,
        reports_to_assignment_id: UUID | str | None = None,
        assignment_id: UUID | str | None = None,
    ) -> WorkforceAssignmentRecord:
        aid = UUID(str(assignment_id)) if assignment_id else uuid4()
        rid = UUID(str(reports_to_assignment_id)) if reports_to_assignment_id else None
        now = datetime.now(UTC)

        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO agent.workforce_assignments (
                        assignment_id, workspace_id, functional_key, spec_id, spec_version,
                        definition_hash, reports_to_assignment_id, configured_by, status,
                        created_at, retired_at
                    ) VALUES (
                        :assignment_id, :workspace_id, :functional_key, :spec_id, :spec_version,
                        :definition_hash, :reports_to_assignment_id, :configured_by, 'ACTIVE',
                        :created_at, NULL
                    )
                    ON CONFLICT (workspace_id, functional_key, spec_id, spec_version, definition_hash)
                    DO UPDATE SET
                        status = 'ACTIVE',
                        retired_at = NULL,
                        reports_to_assignment_id = EXCLUDED.reports_to_assignment_id,
                        configured_by = EXCLUDED.configured_by
                    """
                ),
                {
                    "assignment_id": str(aid),
                    "workspace_id": workspace_id,
                    "functional_key": functional_key,
                    "spec_id": spec_id,
                    "spec_version": spec_version,
                    "definition_hash": definition_hash,
                    "reports_to_assignment_id": str(rid) if rid else None,
                    "configured_by": configured_by,
                    "created_at": now,
                },
            )
            await session.commit()

            # Re-select the row to return the exact assignment_id
            res = await session.execute(
                text(
                    """
                    SELECT assignment_id, workspace_id, functional_key, spec_id, spec_version,
                           definition_hash, reports_to_assignment_id, configured_by, status,
                           created_at, retired_at
                    FROM agent.workforce_assignments
                    WHERE workspace_id = :workspace_id
                      AND functional_key = :functional_key
                      AND spec_id = :spec_id
                      AND spec_version = :spec_version
                      AND definition_hash = :definition_hash
                    """
                ),
                {
                    "workspace_id": workspace_id,
                    "functional_key": functional_key,
                    "spec_id": spec_id,
                    "spec_version": spec_version,
                    "definition_hash": definition_hash,
                },
            )
            row = res.mappings().first()
            assert row is not None
            return self._row_to_assignment(row)

    async def get_assignment(
        self, workspace_id: str, assignment_id: UUID | str
    ) -> WorkforceAssignmentRecord | None:
        aid = UUID(str(assignment_id))
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    SELECT assignment_id, workspace_id, functional_key, spec_id, spec_version,
                           definition_hash, reports_to_assignment_id, configured_by, status,
                           created_at, retired_at
                    FROM agent.workforce_assignments
                    WHERE workspace_id = :workspace_id AND assignment_id = :assignment_id
                    """
                ),
                {"workspace_id": workspace_id, "assignment_id": str(aid)},
            )
            row = res.mappings().first()
            return self._row_to_assignment(row) if row else None

    async def list_assignments(
        self, workspace_id: str, status: str | None = None
    ) -> list[WorkforceAssignmentRecord]:
        async with self._session_factory() as session:
            if status:
                res = await session.execute(
                    text(
                        """
                        SELECT assignment_id, workspace_id, functional_key, spec_id, spec_version,
                               definition_hash, reports_to_assignment_id, configured_by, status,
                               created_at, retired_at
                        FROM agent.workforce_assignments
                        WHERE workspace_id = :workspace_id AND status = :status
                        ORDER BY created_at ASC
                        """
                    ),
                    {"workspace_id": workspace_id, "status": status},
                )
            else:
                res = await session.execute(
                    text(
                        """
                        SELECT assignment_id, workspace_id, functional_key, spec_id, spec_version,
                               definition_hash, reports_to_assignment_id, configured_by, status,
                               created_at, retired_at
                        FROM agent.workforce_assignments
                        WHERE workspace_id = :workspace_id
                        ORDER BY created_at ASC
                        """
                    ),
                    {"workspace_id": workspace_id},
                )
            return [self._row_to_assignment(r) for r in res.mappings().all()]

    async def retire_assignment(
        self, workspace_id: str, assignment_id: UUID | str
    ) -> WorkforceAssignmentRecord | None:
        aid = UUID(str(assignment_id))
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    UPDATE agent.workforce_assignments
                    SET status = 'RETIRED', retired_at = :now
                    WHERE workspace_id = :workspace_id AND assignment_id = :assignment_id
                    RETURNING assignment_id, workspace_id, functional_key, spec_id, spec_version,
                              definition_hash, reports_to_assignment_id, configured_by, status,
                              created_at, retired_at
                    """
                ),
                {"workspace_id": workspace_id, "assignment_id": str(aid), "now": now},
            )
            await session.commit()
            row = res.mappings().first()
            return self._row_to_assignment(row) if row else None

    async def list_cost_observations(
        self, workspace_id: str, run_id: str | None = None, limit: int = 100
    ) -> list[RunCostObservationRecord]:
        async with self._session_factory() as session:
            if run_id:
                res = await session.execute(
                    text(
                        """
                        SELECT observation_id, workspace_id, run_id, provider_key, model_key,
                               input_tokens, output_tokens, cost_amount, currency, observed_at
                        FROM agent.run_cost_observations
                        WHERE workspace_id = :workspace_id AND run_id = :run_id
                        ORDER BY observed_at DESC
                        LIMIT :limit
                        """
                    ),
                    {"workspace_id": workspace_id, "run_id": run_id, "limit": limit},
                )
            else:
                res = await session.execute(
                    text(
                        """
                        SELECT observation_id, workspace_id, run_id, provider_key, model_key,
                               input_tokens, output_tokens, cost_amount, currency, observed_at
                        FROM agent.run_cost_observations
                        WHERE workspace_id = :workspace_id
                        ORDER BY observed_at DESC
                        LIMIT :limit
                        """
                    ),
                    {"workspace_id": workspace_id, "limit": limit},
                )
            return [self._row_to_cost_observation(r) for r in res.mappings().all()]

    async def record_cost_observation(
        self,
        workspace_id: str,
        run_id: str,
        provider_key: str,
        model_key: str,
        observed_at: datetime,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        cost_amount: Decimal | float | None = None,
        currency: str | None = None,
        observation_id: UUID | str | None = None,
    ) -> RunCostObservationRecord:
        oid = UUID(str(observation_id)) if observation_id else uuid4()
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO agent.run_cost_observations (
                        observation_id, workspace_id, run_id, provider_key, model_key,
                        input_tokens, output_tokens, cost_amount, currency, observed_at
                    ) VALUES (
                        :observation_id, :workspace_id, :run_id, :provider_key, :model_key,
                        :input_tokens, :output_tokens, :cost_amount, :currency, :observed_at
                    )
                    ON CONFLICT (workspace_id, run_id, provider_key, model_key, observed_at)
                    DO UPDATE SET
                        input_tokens = EXCLUDED.input_tokens,
                        output_tokens = EXCLUDED.output_tokens,
                        cost_amount = EXCLUDED.cost_amount,
                        currency = EXCLUDED.currency
                    """
                ),
                {
                    "observation_id": str(oid),
                    "workspace_id": workspace_id,
                    "run_id": run_id,
                    "provider_key": provider_key,
                    "model_key": model_key,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cost_amount": cost_amount,
                    "currency": currency,
                    "observed_at": observed_at,
                },
            )
            await session.commit()
            return RunCostObservationRecord(
                observation_id=oid,
                workspace_id=workspace_id,
                run_id=run_id,
                provider_key=provider_key,
                model_key=model_key,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_amount=cost_amount,
                currency=currency,
                observed_at=observed_at,
            )

    async def enqueue_runtime_signal(
        self,
        workspace_id: str,
        source_kind: str,
        source_id: str,
        sequence: int,
        state: str,
        observed_at: datetime,
        correlation_id: str | None = None,
        payload_hash: str | None = None,
        outbox_id: UUID | str | None = None,
    ) -> RuntimeSignalOutboxRecord:
        oid = UUID(str(outbox_id)) if outbox_id else uuid4()
        cid = correlation_id or f"{source_kind}:{source_id}:{sequence}"
        phash = (
            payload_hash
            or hashlib.sha256(f"{source_kind}:{source_id}:{sequence}:{state}".encode()).hexdigest()
        )
        now = datetime.now(UTC)

        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO agent.runtime_signal_outbox (
                        outbox_id, workspace_id, source_kind, source_id, sequence, state,
                        observed_at, correlation_id, payload_hash, state_delivery,
                        attempt_count, next_attempt_at, delivered_at
                    ) VALUES (
                        :outbox_id, :workspace_id, :source_kind, :source_id, :sequence, :state,
                        :observed_at, :correlation_id, :payload_hash, 'PENDING',
                        0, :now, NULL
                    )
                    ON CONFLICT (workspace_id, source_kind, source_id, sequence)
                    DO NOTHING
                    """
                ),
                {
                    "outbox_id": str(oid),
                    "workspace_id": workspace_id,
                    "source_kind": source_kind,
                    "source_id": source_id,
                    "sequence": sequence,
                    "state": state,
                    "observed_at": observed_at,
                    "correlation_id": cid,
                    "payload_hash": phash,
                    "now": now,
                },
            )
            await session.commit()

            res = await session.execute(
                text(
                    """
                    SELECT outbox_id, workspace_id, source_kind, source_id, sequence, state,
                           observed_at, correlation_id, payload_hash, state_delivery,
                           attempt_count, next_attempt_at, delivered_at
                    FROM agent.runtime_signal_outbox
                    WHERE workspace_id = :workspace_id
                      AND source_kind = :source_kind
                      AND source_id = :source_id
                      AND sequence = :sequence
                    """
                ),
                {
                    "workspace_id": workspace_id,
                    "source_kind": source_kind,
                    "source_id": source_id,
                    "sequence": sequence,
                },
            )
            row = res.mappings().first()
            assert row is not None
            return self._row_to_outbox(row)

    async def claim_pending_signals(
        self, limit: int = 50, max_attempts: int = 10
    ) -> list[RuntimeSignalOutboxRecord]:
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    SELECT outbox_id, workspace_id, source_kind, source_id, sequence, state,
                           observed_at, correlation_id, payload_hash, state_delivery,
                           attempt_count, next_attempt_at, delivered_at
                    FROM agent.runtime_signal_outbox
                    WHERE state_delivery = 'PENDING'
                      AND next_attempt_at <= :now
                      AND attempt_count < :max_attempts
                    ORDER BY observed_at ASC
                    LIMIT :limit
                    """
                ),
                {"now": now, "max_attempts": max_attempts, "limit": limit},
            )
            return [self._row_to_outbox(r) for r in res.mappings().all()]

    async def mark_signal_delivered(
        self, outbox_id: UUID | str, delivered_at: datetime | None = None
    ) -> None:
        oid = UUID(str(outbox_id))
        now = delivered_at or datetime.now(UTC)
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    UPDATE agent.runtime_signal_outbox
                    SET state_delivery = 'DELIVERED', delivered_at = :now
                    WHERE outbox_id = :outbox_id
                    """
                ),
                {"outbox_id": str(oid), "now": now},
            )
            await session.commit()

    async def mark_signal_failed(self, outbox_id: UUID | str, next_attempt_at: datetime) -> None:
        oid = UUID(str(outbox_id))
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    UPDATE agent.runtime_signal_outbox
                    SET attempt_count = attempt_count + 1, next_attempt_at = :next_attempt_at
                    WHERE outbox_id = :outbox_id
                    """
                ),
                {"outbox_id": str(oid), "next_attempt_at": next_attempt_at},
            )
            await session.commit()

    async def is_signal_delivered(
        self, workspace_id: str, source_kind: str, source_id: str, sequence: int
    ) -> bool:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    SELECT state_delivery
                    FROM agent.runtime_signal_outbox
                    WHERE workspace_id = :workspace_id
                      AND source_kind = :source_kind
                      AND source_id = :source_id
                      AND sequence = :sequence
                    """
                ),
                {
                    "workspace_id": workspace_id,
                    "source_kind": source_kind,
                    "source_id": source_id,
                    "sequence": sequence,
                },
            )
            row = res.mappings().first()
            return row is not None and row["state_delivery"] == "DELIVERED"

    @staticmethod
    def _row_to_assignment(row: Any) -> WorkforceAssignmentRecord:
        return WorkforceAssignmentRecord(
            assignment_id=UUID(str(row["assignment_id"])),
            workspace_id=row["workspace_id"],
            functional_key=row["functional_key"],
            spec_id=row["spec_id"],
            spec_version=row["spec_version"],
            definition_hash=row["definition_hash"],
            reports_to_assignment_id=UUID(str(row["reports_to_assignment_id"]))
            if row["reports_to_assignment_id"]
            else None,
            configured_by=row["configured_by"],
            status=row["status"],
            created_at=row["created_at"],
            retired_at=row["retired_at"],
        )

    @staticmethod
    def _row_to_cost_observation(row: Any) -> RunCostObservationRecord:
        return RunCostObservationRecord(
            observation_id=UUID(str(row["observation_id"])),
            workspace_id=row["workspace_id"],
            run_id=row["run_id"],
            provider_key=row["provider_key"],
            model_key=row["model_key"],
            input_tokens=row["input_tokens"],
            output_tokens=row["output_tokens"],
            cost_amount=row["cost_amount"],
            currency=row["currency"],
            observed_at=row["observed_at"],
        )

    @staticmethod
    def _row_to_outbox(row: Any) -> RuntimeSignalOutboxRecord:
        return RuntimeSignalOutboxRecord(
            outbox_id=UUID(str(row["outbox_id"])),
            workspace_id=row["workspace_id"],
            source_kind=row["source_kind"],
            source_id=row["source_id"],
            sequence=row["sequence"],
            state=row["state"],
            observed_at=row["observed_at"],
            correlation_id=row["correlation_id"],
            payload_hash=row["payload_hash"],
            state_delivery=row["state_delivery"],
            attempt_count=row["attempt_count"],
            next_attempt_at=row["next_attempt_at"],
            delivered_at=row["delivered_at"],
        )


class InMemoryWorkforceRepository:
    def __init__(self) -> None:
        self.assignments: dict[UUID, WorkforceAssignmentRecord] = {}
        self.cost_observations: list[RunCostObservationRecord] = []
        self.outbox: dict[UUID, RuntimeSignalOutboxRecord] = {}

    async def create_assignment(
        self,
        workspace_id: str,
        functional_key: str,
        spec_id: str,
        spec_version: str,
        definition_hash: str,
        configured_by: str,
        reports_to_assignment_id: UUID | str | None = None,
        assignment_id: UUID | str | None = None,
    ) -> WorkforceAssignmentRecord:
        rid = UUID(str(reports_to_assignment_id)) if reports_to_assignment_id else None

        # Check unique constraint (workspace_id, functional_key, spec_id, spec_version, definition_hash)
        for existing in self.assignments.values():
            if (
                existing.workspace_id == workspace_id
                and existing.functional_key == functional_key
                and existing.spec_id == spec_id
                and existing.spec_version == spec_version
                and existing.definition_hash == definition_hash
            ):
                updated = WorkforceAssignmentRecord(
                    assignment_id=existing.assignment_id,
                    workspace_id=workspace_id,
                    functional_key=functional_key,
                    spec_id=spec_id,
                    spec_version=spec_version,
                    definition_hash=definition_hash,
                    reports_to_assignment_id=rid,
                    configured_by=configured_by,
                    status="ACTIVE",
                    created_at=existing.created_at,
                    retired_at=None,
                )
                self.assignments[existing.assignment_id] = updated
                return updated

        aid = UUID(str(assignment_id)) if assignment_id else uuid4()
        record = WorkforceAssignmentRecord(
            assignment_id=aid,
            workspace_id=workspace_id,
            functional_key=functional_key,
            spec_id=spec_id,
            spec_version=spec_version,
            definition_hash=definition_hash,
            reports_to_assignment_id=rid,
            configured_by=configured_by,
            status="ACTIVE",
            created_at=datetime.now(UTC),
            retired_at=None,
        )
        self.assignments[aid] = record
        return record

    async def get_assignment(
        self, workspace_id: str, assignment_id: UUID | str
    ) -> WorkforceAssignmentRecord | None:
        aid = UUID(str(assignment_id))
        rec = self.assignments.get(aid)
        if rec and rec.workspace_id == workspace_id:
            return rec
        return None

    async def list_assignments(
        self, workspace_id: str, status: str | None = None
    ) -> list[WorkforceAssignmentRecord]:
        return [
            a
            for a in self.assignments.values()
            if a.workspace_id == workspace_id and (status is None or a.status == status)
        ]

    async def retire_assignment(
        self, workspace_id: str, assignment_id: UUID | str
    ) -> WorkforceAssignmentRecord | None:
        aid = UUID(str(assignment_id))
        rec = self.assignments.get(aid)
        if rec and rec.workspace_id == workspace_id:
            retired = WorkforceAssignmentRecord(
                assignment_id=rec.assignment_id,
                workspace_id=rec.workspace_id,
                functional_key=rec.functional_key,
                spec_id=rec.spec_id,
                spec_version=rec.spec_version,
                definition_hash=rec.definition_hash,
                reports_to_assignment_id=rec.reports_to_assignment_id,
                configured_by=rec.configured_by,
                status="RETIRED",
                created_at=rec.created_at,
                retired_at=datetime.now(UTC),
            )
            self.assignments[aid] = retired
            return retired
        return None

    async def list_cost_observations(
        self, workspace_id: str, run_id: str | None = None, limit: int = 100
    ) -> list[RunCostObservationRecord]:
        return [
            c
            for c in sorted(self.cost_observations, key=lambda x: x.observed_at, reverse=True)
            if c.workspace_id == workspace_id and (run_id is None or c.run_id == run_id)
        ][:limit]

    async def record_cost_observation(
        self,
        workspace_id: str,
        run_id: str,
        provider_key: str,
        model_key: str,
        observed_at: datetime,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        cost_amount: Decimal | float | None = None,
        currency: str | None = None,
        observation_id: UUID | str | None = None,
    ) -> RunCostObservationRecord:
        oid = UUID(str(observation_id)) if observation_id else uuid4()
        record = RunCostObservationRecord(
            observation_id=oid,
            workspace_id=workspace_id,
            run_id=run_id,
            provider_key=provider_key,
            model_key=model_key,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_amount=cost_amount,
            currency=currency,
            observed_at=observed_at,
        )
        self.cost_observations.append(record)
        return record

    async def enqueue_runtime_signal(
        self,
        workspace_id: str,
        source_kind: str,
        source_id: str,
        sequence: int,
        state: str,
        observed_at: datetime,
        correlation_id: str | None = None,
        payload_hash: str | None = None,
        outbox_id: UUID | str | None = None,
    ) -> RuntimeSignalOutboxRecord:
        for existing in self.outbox.values():
            if (
                existing.workspace_id == workspace_id
                and existing.source_kind == source_kind
                and existing.source_id == source_id
                and existing.sequence == sequence
            ):
                return existing

        oid = UUID(str(outbox_id)) if outbox_id else uuid4()
        cid = correlation_id or f"{source_kind}:{source_id}:{sequence}"
        phash = (
            payload_hash
            or hashlib.sha256(f"{source_kind}:{source_id}:{sequence}:{state}".encode()).hexdigest()
        )
        now = datetime.now(UTC)

        rec = RuntimeSignalOutboxRecord(
            outbox_id=oid,
            workspace_id=workspace_id,
            source_kind=source_kind,
            source_id=source_id,
            sequence=sequence,
            state=state,
            observed_at=observed_at,
            correlation_id=cid,
            payload_hash=phash,
            state_delivery="PENDING",
            attempt_count=0,
            next_attempt_at=now,
            delivered_at=None,
        )
        self.outbox[oid] = rec
        return rec

    async def claim_pending_signals(
        self, limit: int = 50, max_attempts: int = 10
    ) -> list[RuntimeSignalOutboxRecord]:
        now = datetime.now(UTC)
        return [
            s
            for s in sorted(self.outbox.values(), key=lambda x: x.observed_at)
            if s.state_delivery == "PENDING"
            and s.next_attempt_at <= now
            and s.attempt_count < max_attempts
        ][:limit]

    async def mark_signal_delivered(
        self, outbox_id: UUID | str, delivered_at: datetime | None = None
    ) -> None:
        oid = UUID(str(outbox_id))
        rec = self.outbox.get(oid)
        if rec:
            self.outbox[oid] = RuntimeSignalOutboxRecord(
                outbox_id=rec.outbox_id,
                workspace_id=rec.workspace_id,
                source_kind=rec.source_kind,
                source_id=rec.source_id,
                sequence=rec.sequence,
                state=rec.state,
                observed_at=rec.observed_at,
                correlation_id=rec.correlation_id,
                payload_hash=rec.payload_hash,
                state_delivery="DELIVERED",
                attempt_count=rec.attempt_count,
                next_attempt_at=rec.next_attempt_at,
                delivered_at=delivered_at or datetime.now(UTC),
            )

    async def mark_signal_failed(self, outbox_id: UUID | str, next_attempt_at: datetime) -> None:
        oid = UUID(str(outbox_id))
        rec = self.outbox.get(oid)
        if rec:
            self.outbox[oid] = RuntimeSignalOutboxRecord(
                outbox_id=rec.outbox_id,
                workspace_id=rec.workspace_id,
                source_kind=rec.source_kind,
                source_id=rec.source_id,
                sequence=rec.sequence,
                state=rec.state,
                observed_at=rec.observed_at,
                correlation_id=rec.correlation_id,
                payload_hash=rec.payload_hash,
                state_delivery="PENDING",
                attempt_count=rec.attempt_count + 1,
                next_attempt_at=next_attempt_at,
                delivered_at=None,
            )

    async def is_signal_delivered(
        self, workspace_id: str, source_kind: str, source_id: str, sequence: int
    ) -> bool:
        for s in self.outbox.values():
            if (
                s.workspace_id == workspace_id
                and s.source_kind == source_kind
                and s.source_id == source_id
                and s.sequence == sequence
            ):
                return s.state_delivery == "DELIVERED"
        return False
