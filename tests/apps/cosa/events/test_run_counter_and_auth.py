"""Task 4.2: PostgresRunCounter + LocalServiceAuth."""
import uuid

import pytest

from apps.cosa.events.local_auth import LocalServiceAuth
from apps.cosa.events.run_counter import PostgresRunCounter


def test_local_auth_sign_verify_roundtrip():
    auth = LocalServiceAuth(secret="s3cr3t")
    body = {"eventId": "e1", "payload": {"a": 1}}
    assert auth.verify(auth.sign(body), body) is True


def test_local_auth_rejects_empty_and_tampered():
    auth = LocalServiceAuth(secret="s3cr3t")
    body = {"eventId": "e1"}
    assert auth.verify("", body) is False
    assert auth.verify(auth.sign(body), {"eventId": "e2"}) is False


def test_local_auth_no_secret_rejects_all():
    auth = LocalServiceAuth(secret="")
    assert auth.verify("anything", {"x": 1}) is False


@pytest.mark.asyncio
async def test_run_counter_counts_accepted_today(pg_pool):
    counter = PostgresRunCounter(pg_pool)
    ws = f"ws_{uuid.uuid4().hex[:8]}"
    agg = f"t_{uuid.uuid4().hex[:8]}"
    assert await counter.today(ws, "r1", agg) == 0

    async with pg_pool.acquire() as conn:
        for i in range(2):
            await conn.execute(
                """INSERT INTO event_inbox
                   (workspace_id, event_id, consumer_name, event_type, correlation_id,
                    outcome, aggregate_type, aggregate_id)
                   VALUES ($1,$2,'agentos.event_intake','operations.task.created.v1','c',
                           'accepted','task',$3)""",
                ws,
                uuid.uuid4(),
                agg,
            )
        # một row outcome khác — không tính
        await conn.execute(
            """INSERT INTO event_inbox
               (workspace_id, event_id, consumer_name, event_type, correlation_id,
                outcome, aggregate_type, aggregate_id)
               VALUES ($1,$2,'agentos.event_intake','operations.task.created.v1','c',
                       'ignored_rule_disabled','task',$3)""",
            ws,
            uuid.uuid4(),
            agg,
        )

    assert await counter.today(ws, "r1", agg) == 2

    async with pg_pool.acquire() as conn:
        await conn.execute("DELETE FROM event_inbox WHERE workspace_id = $1", ws)
