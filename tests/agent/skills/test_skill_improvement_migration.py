from __future__ import annotations

import os
from pathlib import Path
import uuid
import pytest
import asyncpg

_MIGRATOR_URL = os.environ.get("AGENT_TEST_MIGRATOR_DATABASE_URL")
if not _MIGRATOR_URL and os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            if line.startswith("AGENT_TEST_MIGRATOR_DATABASE_URL="):
                _MIGRATOR_URL = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

if _MIGRATOR_URL and _MIGRATOR_URL.startswith("postgresql+asyncpg://"):
    _MIGRATOR_DSN = _MIGRATOR_URL.replace("postgresql+asyncpg://", "postgresql://", 1)
else:
    _MIGRATOR_DSN = _MIGRATOR_URL

pytestmark = pytest.mark.skipif(
    not _MIGRATOR_DSN,
    reason="AGENT_TEST_MIGRATOR_DATABASE_URL not set — skipping migration test",
)


@pytest.mark.asyncio
async def test_008_migration_tables_columns_and_constraints() -> None:
    conn = await asyncpg.connect(_MIGRATOR_DSN)
    try:
        up_sql_path = Path("packages/agent/migrations/008_skill_improvement_feedback_loop.sql")
        assert up_sql_path.exists(), "008 migration sql must exist"
        up_sql = up_sql_path.read_text()
        await conn.execute(up_sql)

        # 1. Verify tables in agent schema
        tables = await conn.fetch(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'agent' AND table_name IN (
                'skill_usage_observations',
                'skill_feedback_aggregates',
                'skill_improvement_requests',
                'skill_improvement_outbox',
                'skill_improvement_evaluations',
                'skill_improvement_mutations'
            )
            """
        )
        table_names = {r["table_name"] for r in tables}
        assert "skill_usage_observations" in table_names
        assert "skill_feedback_aggregates" in table_names
        assert "skill_improvement_requests" in table_names
        assert "skill_improvement_outbox" in table_names
        assert "skill_improvement_evaluations" in table_names
        assert "skill_improvement_mutations" in table_names

        # 2. Verify columns in agent_skill_feedback
        cols = await conn.fetch(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'agent' AND table_name = 'agent_skill_feedback'
            """
        )
        col_names = {r["column_name"] for r in cols}
        assert "skill_version" in col_names
        assert "definition_hash" in col_names
        assert "run_id" in col_names
        assert "idempotency_key" in col_names
        assert "source_kind" in col_names

        # 3. Verify unique index on idempotency_key
        idx = await conn.fetchval(
            """
            SELECT count(*)
            FROM pg_indexes
            WHERE schemaname = 'agent' AND tablename = 'agent_skill_feedback'
              AND indexname = 'ux_agent_skill_feedback_ws_idempotency'
            """
        )
        assert idx > 0

        # 4. Verify partial unique index for single live request
        idx_req = await conn.fetchval(
            """
            SELECT count(*)
            FROM pg_indexes
            WHERE schemaname = 'agent' AND tablename = 'skill_improvement_requests'
              AND indexname = 'ux_agent_skill_improvement_requests_live'
            """
        )
        assert idx_req > 0
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_008_down_migration_refuses_when_evidence_exists() -> None:
    conn = await asyncpg.connect(_MIGRATOR_DSN)
    try:
        up_sql = Path("packages/agent/migrations/008_skill_improvement_feedback_loop.sql").read_text()
        await conn.execute(up_sql)

        down_sql = Path("packages/agent/migrations/008_skill_improvement_feedback_loop.down.sql").read_text()

        # Insert a dummy run for FK
        run_id = f"run_test_{uuid.uuid4().hex[:8]}"
        await conn.execute(
            """
            INSERT INTO agent.runs (run_id, workspace_id, principal, root_executable_id, status)
            VALUES ($1, 'ws-test', 'user:test', 'exec-1', 'COMPLETED')
            ON CONFLICT DO NOTHING
            """,
            run_id,
        )

        # Insert observation evidence
        obs_id = f"obs_test_{uuid.uuid4().hex[:8]}"
        await conn.execute(
            """
            INSERT INTO agent.skill_usage_observations (
                observation_id, workspace_id, run_id, skill_id, skill_version,
                definition_hash, root_spec_id, root_definition_hash
            ) VALUES (
                $1, 'ws-test', $2, 'skill-1', '1.0.0',
                'sha256:def1', 'spec-root', 'sha256:root1'
            )
            """,
            obs_id,
            run_id,
        )

        with pytest.raises(asyncpg.PostgresError, match="migration 008 down refused"):
            await conn.execute(down_sql)

        # Cleanup test observation
        await conn.execute("DELETE FROM agent.skill_usage_observations WHERE observation_id = $1", obs_id)
    finally:
        await conn.close()
