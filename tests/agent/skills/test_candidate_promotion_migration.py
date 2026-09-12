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
async def test_007_migration_columns_and_constraints() -> None:
    conn = await asyncpg.connect(_MIGRATOR_DSN)
    try:
        up_sql_path = Path("packages/agent/migrations/007_skill_candidate_promotion_cas.sql")
        assert up_sql_path.exists(), "007 migration sql must exist"
        up_sql = up_sql_path.read_text()
        await conn.execute(up_sql)

        # Verify columns in agent_skill_candidates
        cols = await conn.fetch(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'agent' AND table_name = 'agent_skill_candidates'
            """
        )
        col_names = {r["column_name"] for r in cols}
        assert "definition_hash" in col_names
        assert "promotion_approval_id" in col_names
        assert "promotion_definition_hash" in col_names
        assert "published_at" in col_names

        # Verify partial unique index exists
        idx = await conn.fetchval(
            """
            SELECT count(*)
            FROM pg_indexes
            WHERE schemaname = 'agent' AND tablename = 'agent_skill_candidates'
              AND indexname = 'ux_agent_skill_candidates_promotion_approval'
            """
        )
        assert idx > 0
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_007_down_migration_refuses_when_published_candidate_exists() -> None:
    conn = await asyncpg.connect(_MIGRATOR_DSN)
    try:
        # Ensure up migration applied
        up_sql = Path("packages/agent/migrations/007_skill_candidate_promotion_cas.sql").read_text()
        await conn.execute(up_sql)

        down_sql = Path("packages/agent/migrations/007_skill_candidate_promotion_cas.down.sql").read_text()

        # Insert a published candidate
        cid = f"cand_test_{uuid.uuid4().hex[:8]}"
        await conn.execute(
            """
            INSERT INTO agent.agent_skill_candidates (
                candidate_id, workspace_id, parent_run_id, skill_id,
                proposed_skill, eval_score, status, promotion_approval_id
            ) VALUES (
                $1, 'ws-test', 'run-test', 'skill-1',
                '{"id": "skill-1", "instructions": "test"}'::jsonb,
                1.0, 'PUBLISHED', 'appr-1'
            )
            """,
            cid,
        )

        with pytest.raises(asyncpg.PostgresError, match="migration 007 down refused"):
            await conn.execute(down_sql)

        # Cleanup test row
        await conn.execute("DELETE FROM agent.agent_skill_candidates WHERE candidate_id = $1", cid)
    finally:
        await conn.close()
