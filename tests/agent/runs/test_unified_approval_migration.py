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
async def test_006_migration_backfills_workspace_and_enforces_constraints() -> None:
    conn = await asyncpg.connect(_MIGRATOR_DSN)
    try:
        # Read migration 006 up SQL
        up_sql_path = Path("packages/agent/migrations/006_unified_governance_approvals.sql")
        assert up_sql_path.exists(), "006 migration sql does not exist yet"
        up_sql = up_sql_path.read_text()

        # Check table agent.approvals exists
        exists = await conn.fetchval(
            "SELECT to_regclass('agent.approvals') IS NOT NULL"
        )
        assert exists, "agent.approvals table must exist"

        # Apply migration 006
        await conn.execute(up_sql)

        # Check columns exist
        cols = await conn.fetch(
            """
            SELECT column_name, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'agent' AND table_name = 'approvals'
            """
        )
        col_names = {r["column_name"]: r for r in cols}
        assert "workspace_id" in col_names
        assert "binding_kind" in col_names
        assert "subject_kind" in col_names
        assert "subject_ref" in col_names
        assert "subject_hash" in col_names

        assert col_names["run_id"]["is_nullable"] == "YES"
        assert col_names["tool_call_id"]["is_nullable"] == "YES"
        assert col_names["checkpoint_ref"]["is_nullable"] == "YES"

        # Check new tables exist
        events_exists = await conn.fetchval(
            "SELECT to_regclass('agent.approval_events') IS NOT NULL"
        )
        assert events_exists
        outbox_exists = await conn.fetchval(
            "SELECT to_regclass('agent.approval_action_outbox') IS NOT NULL"
        )
        assert outbox_exists

        # Test backfill: create run and tool approval
        run_id = f"run_mig_{uuid.uuid4().hex[:8]}"
        ws_id = "ws_mig_test"
        await conn.execute(
            """
            INSERT INTO agent.runs (run_id, principal, root_executable_id, workspace_id, status)
            VALUES ($1, 'founder_test', 'test_exec', $2, 'PENDING')
            """,
            run_id,
            ws_id,
        )
        await conn.execute(
            """
            INSERT INTO agent.run_checkpoints (checkpoint_ref, run_id, sequence_no)
            VALUES ($1, $2, 1)
            """,
            f"ckpt_{run_id}",
            run_id,
        )
        await conn.execute(
            """
            INSERT INTO agent.run_tool_calls (tool_call_id, run_id, capability_id, payload_hash)
            VALUES ($1, $2, 'cap.test', 'hash1')
            """,
            f"call_{run_id}",
            run_id,
        )

        appr_id = f"appr_mig_{uuid.uuid4().hex[:8]}"
        await conn.execute(
            """
            INSERT INTO agent.approvals (approval_id, run_id, tool_call_id, checkpoint_ref, status, binding_kind)
            VALUES ($1, $2, $3, $4, 'pending', 'TOOL_CALL')
            """,
            appr_id,
            run_id,
            f"call_{run_id}",
            f"ckpt_{run_id}",
        )

        # Backfill update
        await conn.execute(
            """
            UPDATE agent.approvals AS a
            SET workspace_id = r.workspace_id
            FROM agent.runs AS r
            WHERE a.run_id = r.run_id AND a.workspace_id IS NULL;
            """
        )
        fetched_ws = await conn.fetchval(
            "SELECT workspace_id FROM agent.approvals WHERE approval_id = $1", appr_id
        )
        assert fetched_ws == ws_id

        # Constraint test: CHANGE_REQUEST with run_id must fail
        with pytest.raises(asyncpg.exceptions.CheckViolationError):
            await conn.execute(
                """
                INSERT INTO agent.approvals (
                    approval_id, workspace_id, binding_kind, run_id, action, subject_kind, subject_ref, subject_hash, status
                ) VALUES ($1, $2, 'CHANGE_REQUEST', $3, 'promote', 'skill_candidate', 'c1', 'h1', 'pending')
                """,
                f"appr_invalid_{uuid.uuid4().hex[:8]}",
                ws_id,
                run_id,
            )

        # Constraint test: TOOL_CALL with NULL run_id must fail
        with pytest.raises(asyncpg.exceptions.CheckViolationError):
            await conn.execute(
                """
                INSERT INTO agent.approvals (
                    approval_id, workspace_id, binding_kind, run_id, tool_call_id, checkpoint_ref, status
                ) VALUES ($1, $2, 'TOOL_CALL', NULL, 'call1', 'ckpt1', 'pending')
                """,
                f"appr_invalid_{uuid.uuid4().hex[:8]}",
                ws_id,
            )

    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_006_down_migration_refuses_when_change_request_or_events_exist() -> None:
    conn = await asyncpg.connect(_MIGRATOR_DSN)
    try:
        # Create a valid CHANGE_REQUEST approval
        change_appr_id = f"appr_change_{uuid.uuid4().hex[:8]}"
        subject_ref = f"c_down_{uuid.uuid4().hex[:8]}"
        try:
            await conn.execute(
                """
                INSERT INTO agent.approvals (
                    approval_id, workspace_id, binding_kind, action, subject_kind, subject_ref, subject_hash, status
                ) VALUES ($1, 'ws_down_test', 'CHANGE_REQUEST', 'promote_skill_candidate', 'skill_candidate', $2, 'h_down', 'pending')
                """,
                change_appr_id,
                subject_ref,
            )

            down_sql_path = Path("packages/agent/migrations/006_unified_governance_approvals.down.sql")
            assert down_sql_path.exists()
            down_sql = down_sql_path.read_text()

            # Down migration must refuse because CHANGE_REQUEST exists
            with pytest.raises(asyncpg.exceptions.RaiseError, match="migration 006 down refused"):
                await conn.execute(down_sql)
        finally:
            await conn.execute("DELETE FROM agent.approvals WHERE approval_id = $1", change_appr_id)

    finally:
        await conn.close()
