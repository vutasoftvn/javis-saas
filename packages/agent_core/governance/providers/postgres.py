from __future__ import annotations

import json
import uuid
from typing import Any, Optional

from sqlalchemy import text

from agent_core.governance.accumulator import InvocationGovernanceState
from agent_core.governance.contracts import (
    PinnedSpecIdentity,
    PolicyDecision,
    SpecResolutionManifest,
)
from agent_core.governance.exceptions import GovernanceStoreConfigurationError


class PostgresGovernanceStateStore:
    """PostgreSQL implementation của GovernanceStateStore — theo đúng mẫu
    agentos/memory/providers/postgres.py::PostgresMemoryStore (constructor
    nhận db_session_factory, raw SQL qua sqlalchemy.text(), JSON serialize
    thủ công). Schema: agent_core_governance (xem
    agentos/migrations/002_governance_temporal_model.sql)."""

    def __init__(self, db_session_factory: Any = None) -> None:
        if db_session_factory is None:
            raise GovernanceStoreConfigurationError(
                "PostgresGovernanceStateStore requires a valid `db_session_factory`."
            )
        self._session_factory = db_session_factory

    async def save_manifest_entry(self, run_id: str, entry: PinnedSpecIdentity) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO agent_core_governance.spec_resolution_manifest_entries
                        (run_id, spec_kind, spec_id, spec_version, definition_hash)
                    VALUES (:run_id, :spec_kind, :spec_id, :spec_version, :definition_hash)
                    ON CONFLICT (run_id, spec_kind, spec_id, definition_hash) DO NOTHING;
                    """
                ),
                {
                    "run_id": run_id,
                    "spec_kind": entry.spec_kind,
                    "spec_id": entry.spec_id,
                    "spec_version": entry.spec_version,
                    "definition_hash": entry.definition_hash,
                },
            )
            await session.commit()

    async def load_manifest(self, run_id: str) -> SpecResolutionManifest:
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    """
                    SELECT spec_kind, spec_id, spec_version, definition_hash
                    FROM agent_core_governance.spec_resolution_manifest_entries
                    WHERE run_id = :run_id
                    ORDER BY resolved_at ASC;
                    """
                ),
                {"run_id": run_id},
            )
            rows = result.fetchall()
            entries = tuple(
                PinnedSpecIdentity(spec_kind=r[0], spec_id=r[1], spec_version=r[2], definition_hash=r[3])
                for r in rows
            )
            return SpecResolutionManifest(entries=entries)

    async def save_governance_state(
        self, state: InvocationGovernanceState, *, observation: PolicyDecision, source: str
    ) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO agent_core_governance.invocation_governance_state
                        (run_id, tool_call_id, accumulated, updated_at)
                    VALUES (:run_id, :tool_call_id, :accumulated, now())
                    ON CONFLICT (run_id, tool_call_id) DO UPDATE SET
                        accumulated = EXCLUDED.accumulated,
                        updated_at = EXCLUDED.updated_at;
                    """
                ),
                {
                    "run_id": state.run_id,
                    "tool_call_id": state.tool_call_id,
                    "accumulated": json.dumps(state.accumulated.model_dump(mode="json")),
                },
            )
            await session.execute(
                text(
                    """
                    INSERT INTO agent_core_governance.invocation_governance_history
                        (id, run_id, tool_call_id, observation, source)
                    VALUES (:id, :run_id, :tool_call_id, :observation, :source);
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "run_id": state.run_id,
                    "tool_call_id": state.tool_call_id,
                    "observation": json.dumps(observation.model_dump(mode="json")),
                    "source": source,
                },
            )
            await session.commit()

    async def load_governance_state(
        self, run_id: str, tool_call_id: str
    ) -> Optional[InvocationGovernanceState]:
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    """
                    SELECT accumulated FROM agent_core_governance.invocation_governance_state
                    WHERE run_id = :run_id AND tool_call_id = :tool_call_id;
                    """
                ),
                {"run_id": run_id, "tool_call_id": tool_call_id},
            )
            row = result.fetchone()
            if row is None:
                return None
            accumulated_val = row[0]
            if isinstance(accumulated_val, str):
                accumulated_val = json.loads(accumulated_val)
            return InvocationGovernanceState(
                run_id=run_id,
                tool_call_id=tool_call_id,
                accumulated=PolicyDecision.model_validate(accumulated_val),
            )

