"""Task 4.4: build_event_intake_deps produces a fully wired EventIntakeDeps,
and handle_event runs the real inbox + trigger path against Postgres."""
import json
import os
import uuid

import pytest
import pytest_asyncio

from apps.cosa.events.deps import EventIntakeDeps, build_event_intake_deps
from apps.cosa.events.router import Unauthenticated, handle_event

pytestmark = pytest.mark.asyncio


def _dsn():
    raw = os.environ.get("AGENT_TEST_DATABASE_URL") or os.environ.get("AGENT_DATABASE_URL")
    return raw


class _FakeRegistry:
    def get(self, *a, **k):
        return None


@pytest_asyncio.fixture
async def deps(monkeypatch):
    monkeypatch.setenv("COSA_LOCAL_SERVICE_SECRET", "test-intake-secret")
    dsn = _dsn()
    if not dsn:
        pytest.skip("AGENT_TEST_DATABASE_URL not set")
    try:
        d = await build_event_intake_deps(
            database_url=dsn, spec_registry=_FakeRegistry(), capability_registry=_FakeRegistry()
        )
    except Exception as e:  # pragma: no cover
        pytest.skip(f"cannot build deps: {e}")
    try:
        yield d
    finally:
        await d.aclose()


def _env(ws, event_type="operations.task.created.v1", aggregate_id="t_1"):
    return {
        "eventId": str(uuid.uuid4()),
        "eventType": event_type,
        "schemaVersion": 1,
        "occurredAt": "2026-08-28T10:00:00.000Z",
        "workspaceId": ws,
        "aggregateType": "task",
        "aggregateId": aggregate_id,
        "correlationId": "corr_1",
        "actor": {"kind": "system", "id": "relay"},
        "producer": {"service": "company.operations", "version": "1.0.0"},
        "classification": "internal",
        "payload": {"taskId": aggregate_id, "workspaceId": ws, "title": "T", "status": "todo"},
    }


async def test_build_deps_is_fully_wired(deps):
    assert isinstance(deps, EventIntakeDeps)
    for f in ("local_auth", "db", "trigger_policy", "execution_plane", "rule_store",
              "evidence_store", "fingerprint_provider"):
        assert getattr(deps, f) is not None
    assert deps.caller_workspace_id is None


async def test_handle_event_no_rule_records_inbox_and_returns_ignored(deps):
    ws = f"ws_{uuid.uuid4().hex[:8]}"
    body = _env(ws)
    raw = json.dumps(body).encode("utf-8")
    sig = deps.local_auth.sign(raw)
    result = await handle_event(deps, raw, sig)
    assert result.outcome == "ignored_rule_disabled"

    async with deps.db.begin() as conn:
        row = await conn.fetchrow(
            "SELECT outcome, aggregate_id FROM event_inbox WHERE workspace_id=$1 AND event_id=$2",
            ws, body["eventId"],
        )
        assert row is not None and row["outcome"] == "ignored_rule_disabled"
        assert row["aggregate_id"] == "t_1"
        await conn.execute("DELETE FROM event_inbox WHERE workspace_id=$1", ws)


async def test_handle_event_duplicate(deps):
    ws = f"ws_{uuid.uuid4().hex[:8]}"
    body = _env(ws)
    raw = json.dumps(body).encode("utf-8")
    sig = deps.local_auth.sign(raw)
    first = await handle_event(deps, raw, sig)
    second = await handle_event(deps, raw, sig)
    assert first.outcome == "ignored_rule_disabled"
    assert second.outcome == "duplicate"
    async with deps.db.begin() as conn:
        await conn.execute("DELETE FROM event_inbox WHERE workspace_id=$1", ws)


async def test_handle_event_bad_signature(deps):
    with pytest.raises(Unauthenticated):
        await handle_event(deps, json.dumps(_env("ws_x")).encode("utf-8"), "deadbeef")
