"""Durable store for Company -> COSA AI Initiative promotion snapshots (Task 6,
plan 2026-09-28-stage-adaptive-ai-operating-system).

`AiInitiativePromotionSnapshotStore.consume()` is the idempotent write path:
storing a snapshot the first time a `decision_id` is seen for a given
workspace/initiative, and returning the already-stored snapshot (not
re-inserting) on redelivery. `get_current()` is the read path Task 8's
`assert_initiative_run_allowed()` uses to fetch the authoritative snapshot for
an Initiative at run time — it must survive process restart, which an
in-memory dict cannot do.
"""

from __future__ import annotations

import json
from typing import Any, Protocol

from pydantic import BaseModel, Field
from sqlalchemy import text


class AiInitiativePromotionSnapshot(BaseModel):
    workspace_id: str
    project_id: str
    initiative_id: str
    initiative_revision: int
    decision_id: str
    decision_hash: str
    lifecycle_state: str
    risk_tier: str
    autonomy_tier: str
    pins: dict[str, Any] = Field(default_factory=dict)
    value_contract_revision: int | None = None
    data_readiness_revision: int | None = None
    budget_policy_revision: int | None = None
    evaluation_suite_revision: int | None = None
    # Task 11 — carried alongside data_readiness_revision so the knowledge
    # readiness gate (apps/cosa/knowledge/initiative_readiness.py) can decide
    # without a cross-plane lookup into Company's data-readiness assessment table.
    data_readiness_status: str | None = None
    retrieval_mode: str | None = None


class AiInitiativePromotionSnapshotStore(Protocol):
    async def consume(
        self, idempotency_key: str, snapshot: AiInitiativePromotionSnapshot
    ) -> tuple[AiInitiativePromotionSnapshot, bool]:
        """Store `snapshot` under `idempotency_key` unless already consumed.

        Returns `(stored_snapshot, already_consumed)`. `already_consumed=True`
        means the key was already present and `stored_snapshot` is the
        previously-stored value (the new `snapshot` is discarded, matching
        outbox-redelivery idempotency — never overwrite a consumed decision).
        """
        ...

    async def get_current(
        self, workspace_id: str, initiative_id: str
    ) -> AiInitiativePromotionSnapshot | None:
        """Latest (highest `initiative_revision`) snapshot for this Initiative."""
        ...


class InMemoryAiInitiativePromotionSnapshotStore:
    def __init__(self) -> None:
        self._by_key: dict[str, AiInitiativePromotionSnapshot] = {}

    async def consume(
        self, idempotency_key: str, snapshot: AiInitiativePromotionSnapshot
    ) -> tuple[AiInitiativePromotionSnapshot, bool]:
        existing = self._by_key.get(idempotency_key)
        if existing is not None:
            return existing, True
        self._by_key[idempotency_key] = snapshot
        return snapshot, False

    async def get_current(
        self, workspace_id: str, initiative_id: str
    ) -> AiInitiativePromotionSnapshot | None:
        candidates = [
            s
            for s in self._by_key.values()
            if s.workspace_id == workspace_id and s.initiative_id == initiative_id
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda s: s.initiative_revision)


def _row_to_snapshot(row: Any) -> AiInitiativePromotionSnapshot:
    """Raw `text()` queries don't get SQLAlchemy's typed jsonb decoding, so
    `pins` may come back as the driver's raw JSON text instead of a dict —
    parse it defensively rather than let pydantic reject a `str` for a
    `dict[str, Any]` field."""
    data = dict(row)
    if isinstance(data.get("pins"), str):
        data["pins"] = json.loads(data["pins"])
    return AiInitiativePromotionSnapshot(**data)


class PostgresAiInitiativePromotionSnapshotStore:
    def __init__(self, session_factory: Any) -> None:
        if session_factory is None:
            raise ValueError(
                "PostgresAiInitiativePromotionSnapshotStore requires a session_factory"
            )
        self._session_factory = session_factory

    async def consume(
        self, idempotency_key: str, snapshot: AiInitiativePromotionSnapshot
    ) -> tuple[AiInitiativePromotionSnapshot, bool]:
        async with self._session_factory() as session:
            existing_row = (
                (
                    await session.execute(
                        text(
                            """
                        SELECT workspace_id, project_id, initiative_id, initiative_revision,
                               decision_id, decision_hash, lifecycle_state, risk_tier, autonomy_tier,
                               pins, value_contract_revision, data_readiness_revision,
                               budget_policy_revision, evaluation_suite_revision,
                               data_readiness_status, retrieval_mode
                        FROM models.ai_initiative_promotion_snapshots
                        WHERE idempotency_key = :idempotency_key
                        """
                        ),
                        {"idempotency_key": idempotency_key},
                    )
                )
                .mappings()
                .first()
            )

            if existing_row is not None:
                return _row_to_snapshot(existing_row), True

            await session.execute(
                text(
                    """
                    INSERT INTO models.ai_initiative_promotion_snapshots (
                        idempotency_key, workspace_id, project_id, initiative_id, initiative_revision,
                        decision_id, decision_hash, lifecycle_state, risk_tier, autonomy_tier, pins,
                        value_contract_revision, data_readiness_revision, budget_policy_revision,
                        evaluation_suite_revision, data_readiness_status, retrieval_mode
                    ) VALUES (
                        :idempotency_key, :workspace_id, :project_id, :initiative_id, :initiative_revision,
                        :decision_id, :decision_hash, :lifecycle_state, :risk_tier, :autonomy_tier, CAST(:pins AS jsonb),
                        :value_contract_revision, :data_readiness_revision, :budget_policy_revision,
                        :evaluation_suite_revision, :data_readiness_status, :retrieval_mode
                    )
                    ON CONFLICT (idempotency_key) DO NOTHING
                    """
                ),
                {
                    "idempotency_key": idempotency_key,
                    **{
                        **snapshot.model_dump(mode="json"),
                        "pins": json.dumps(snapshot.pins),
                    },
                },
            )
            await session.commit()
            return snapshot, False

    async def get_current(
        self, workspace_id: str, initiative_id: str
    ) -> AiInitiativePromotionSnapshot | None:
        async with self._session_factory() as session:
            row = (
                (
                    await session.execute(
                        text(
                            """
                        SELECT workspace_id, project_id, initiative_id, initiative_revision,
                               decision_id, decision_hash, lifecycle_state, risk_tier, autonomy_tier,
                               pins, value_contract_revision, data_readiness_revision,
                               budget_policy_revision, evaluation_suite_revision,
                               data_readiness_status, retrieval_mode
                        FROM models.ai_initiative_promotion_snapshots
                        WHERE workspace_id = :workspace_id AND initiative_id = :initiative_id
                        ORDER BY initiative_revision DESC
                        LIMIT 1
                        """
                        ),
                        {"workspace_id": workspace_id, "initiative_id": initiative_id},
                    )
                )
                .mappings()
                .first()
            )

            if row is None:
                return None
            return _row_to_snapshot(row)
