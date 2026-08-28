"""PostgresTriggerRuleStore — persistence bền cho EventTriggerRule (bảng
`event_trigger_rules`, migration 020). Dùng asyncpg (khớp `inbox.py`).
"""
from __future__ import annotations

import json
from typing import Any, Optional

from apps.cosa.events.trigger_policy import EventTriggerRule, PinnedSpecIdentity

__all__ = ["PostgresTriggerRuleStore"]

_COLS = (
    "rule_id, workspace_id, event_type, agent_spec_id, agent_spec_version, agent_spec_hash, "
    "mode, max_runs_per_aggregate_per_day, required_capabilities, aggregate_filter, owner, "
    "enabled, eval_evidence_ref, event_schema_version"
)


def _row_to_rule(row: Any) -> EventTriggerRule:
    caps = row["required_capabilities"]
    if isinstance(caps, str):
        caps = json.loads(caps)
    agg = row["aggregate_filter"]
    if isinstance(agg, str):
        agg = json.loads(agg)
    return EventTriggerRule(
        rule_id=row["rule_id"],
        workspace_id=row["workspace_id"],
        event_type=row["event_type"],
        agent_spec=PinnedSpecIdentity(
            id=row["agent_spec_id"],
            version=row["agent_spec_version"],
            definition_hash=row["agent_spec_hash"],
        ),
        mode=row["mode"],
        max_runs_per_aggregate_per_day=row["max_runs_per_aggregate_per_day"],
        required_capabilities=tuple(caps or ()),
        aggregate_filter=agg,
        owner=row["owner"],
        enabled=row["enabled"],
        eval_evidence_ref=row["eval_evidence_ref"],
        event_schema_version=row["event_schema_version"],
    )


class PostgresTriggerRuleStore:
    def __init__(self, pool: Any) -> None:
        self._pool = pool

    async def find(
        self, workspace_id: str, event_type: str, aggregate: dict
    ) -> Optional[EventTriggerRule]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT {_COLS} FROM event_trigger_rules "
                f"WHERE workspace_id = $1 AND event_type = $2",
                workspace_id,
                event_type,
            )
        return _row_to_rule(row) if row else None

    async def get(self, rule_id: str) -> Optional[EventTriggerRule]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT {_COLS} FROM event_trigger_rules WHERE rule_id = $1", rule_id
            )
        return _row_to_rule(row) if row else None

    async def list_by_workspace(self, workspace_id: str) -> list[EventTriggerRule]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT {_COLS} FROM event_trigger_rules WHERE workspace_id = $1 "
                f"ORDER BY event_type",
                workspace_id,
            )
        return [_row_to_rule(r) for r in rows]

    async def upsert(self, rule: EventTriggerRule) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO event_trigger_rules (
                    rule_id, workspace_id, event_type, agent_spec_id, agent_spec_version,
                    agent_spec_hash, mode, max_runs_per_aggregate_per_day, required_capabilities,
                    aggregate_filter, owner, enabled, eval_evidence_ref, event_schema_version,
                    updated_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb,$10::jsonb,$11,$12,$13,$14, now())
                ON CONFLICT (rule_id) DO UPDATE SET
                    event_type = EXCLUDED.event_type,
                    agent_spec_id = EXCLUDED.agent_spec_id,
                    agent_spec_version = EXCLUDED.agent_spec_version,
                    agent_spec_hash = EXCLUDED.agent_spec_hash,
                    mode = EXCLUDED.mode,
                    max_runs_per_aggregate_per_day = EXCLUDED.max_runs_per_aggregate_per_day,
                    required_capabilities = EXCLUDED.required_capabilities,
                    aggregate_filter = EXCLUDED.aggregate_filter,
                    owner = EXCLUDED.owner,
                    eval_evidence_ref = EXCLUDED.eval_evidence_ref,
                    event_schema_version = EXCLUDED.event_schema_version,
                    updated_at = now()
                """,
                rule.rule_id,
                rule.workspace_id,
                rule.event_type,
                rule.agent_spec.id,
                rule.agent_spec.version,
                rule.agent_spec.definition_hash,
                rule.mode,
                rule.max_runs_per_aggregate_per_day,
                json.dumps(list(rule.required_capabilities)),
                json.dumps(rule.aggregate_filter) if rule.aggregate_filter is not None else None,
                rule.owner,
                rule.enabled,
                rule.eval_evidence_ref,
                rule.event_schema_version,
            )

    async def set_enabled(self, rule_id: str, enabled: bool) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE event_trigger_rules SET enabled = $1, updated_at = now() WHERE rule_id = $2",
                enabled,
                rule_id,
            )
