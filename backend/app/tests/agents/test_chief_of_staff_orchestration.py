import asyncio
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import get_current_workspace_member
from app.core.events import cross_process_event_listener, EventEnvelope
from app.core.snowflake import generate_snowflake_id
from app.workforce.agents.orchestration.chief_of_staff import ChiefOfStaffOrchestrator
from app.workforce.agents.orchestration.mission_control_bus import mission_control_bus
from app.workforce.agents.runtime.adapters.mock import MockRuntime
from app.business.finance.models import AccountingProfile, FinanceManagementSnapshot


def _create_mock_db(runway_months=Decimal("12.5")):
    db = MagicMock()
    snapshot = FinanceManagementSnapshot(
        id=generate_snowflake_id(),
        workspace_id=generate_snowflake_id(),
        as_of=date(2026, 8, 1),
        cash=Decimal("1500000000"),
        burn=Decimal("120000000"),
        runway_months=runway_months,
        revenue=Decimal("200000000"),
        expenses=Decimal("120000000"),
        budget_variance=Decimal("10000000"),
    )
    profile = AccountingProfile(
        id=generate_snowflake_id(),
        workspace_id=generate_snowflake_id(),
        mode="TT58_MODE_1",
        status="CONFIRMED",
    )

    def query_mock(*entities, **kwargs):
        model = entities[0] if entities else None
        m = MagicMock()
        m.filter.return_value = m
        m.order_by.return_value = m
        m.scalar.return_value = 0
        m.all.return_value = []
        m.limit.return_value.all.return_value = []
        if model is FinanceManagementSnapshot:
            m.first.return_value = snapshot
        elif model is AccountingProfile:
            m.first.return_value = profile
        else:
            m.first.return_value = None
        return m

    db.query.side_effect = query_mock
    return db


def _mock_funnel_metrics(monkeypatch, qualified_leads: int, total_leads: int):
    metrics = {
        "total_leads": total_leads,
        "qualified_leads": qualified_leads,
        "converted_leads": 1,
        "total_opportunities": 4,
        "won_opportunities": 1,
        "pipeline_value": 45000000.0,
    }
    monkeypatch.setattr(
        "app.business.sales.sales_tools.FunnelMetricsService.get_funnel_metrics",
        lambda db, workspace_id: metrics,
    )
    return metrics


@pytest.mark.asyncio
async def test_chief_of_staff_orchestration_flow(monkeypatch):
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    db = _create_mock_db()
    _mock_funnel_metrics(monkeypatch, qualified_leads=3, total_leads=5)

    goal = "Doanh thu quý này đang chậm. Hãy phân tích CRM và tài chính để lập kế hoạch tăng tốc."

    result = await ChiefOfStaffOrchestrator.orchestrate(
        db=db,
        workspace_id=ws_id,
        user_id=user_id,
        goal=goal,
        runtime=MockRuntime(),
    )

    # MockRuntime cannot produce valid structured JSON, so the honest outcome is "partial" with
    # the raw synthesis text - not a polished "completed" plan invented client-side. That is the
    # point of this fix: no more hardcoded fake reasoning presented as if an LLM produced it.
    assert result.status == "partial"
    assert goal in result.diagnosis
    assert result.workspace_id == str(ws_id)
    assert "sales" in result.specialist_reports
    assert "finance" in result.specialist_reports
    assert len(result.priorities) > 0

    # priorities/action_plan are derived from the real (mocked) data, not invented: qualified
    # leads > 0 is the only condition that fires here (runway 12.5mo is above the 6mo trigger).
    assert len(result.action_plan) == 1
    assert result.action_plan[0]["automation_key"] == "sales.followup_email"

    # A real AgentApproval row must exist for the automation-bound action.
    assert len(result.required_approvals) == 1
    assert result.required_approvals[0]["tool_name"] == "sales.followup_email"
    assert result.required_approvals[0]["status"] == "pending"


# --- G3 Phase 1A: generalized N-agent dispatch ---
# orchestrate() used to hardcode exactly 2 delegations (sales, finance) as
# direct in-process function calls with no child AgentRun row ever inserted.
# These tests prove: (1) a 3rd domain (legal) dispatches through the same
# loop with zero new hardcoded branches, and (2) each delegation now creates
# a real child `agent_runs` row with the correct parent_run_id.

@pytest.mark.asyncio
async def test_orchestrate_dispatches_a_third_domain_without_new_branch(monkeypatch):
    from app.workforce.agents.orchestration.chief_of_staff import SPECIALIST_REGISTRY

    assert "legal" in SPECIALIST_REGISTRY, "legal must be a real SPECIALIST_REGISTRY entry, not a hardcoded branch"

    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    db = _create_mock_db()
    _mock_funnel_metrics(monkeypatch, qualified_leads=1, total_leads=2)

    result = await ChiefOfStaffOrchestrator.orchestrate(
        db=db,
        workspace_id=ws_id,
        user_id=user_id,
        goal="Rà soát rủi ro pháp lý và tài chính trước khi ký hợp đồng lớn",
        runtime=MockRuntime(),
        domains=["sales", "finance", "legal"],
    )

    assert "sales" in result.specialist_reports
    assert "finance" in result.specialist_reports
    assert "legal" in result.specialist_reports
    assert result.specialist_reports["legal"]["status"] == "success"
    assert "checklist_items" in result.specialist_reports["legal"]


def test_marketing_specialist_registered_and_tool_resolves():
    """Marketing has a real domain (workforce/agents/domains/marketing/) with
    production callers, but was missing from SPECIALIST_REGISTRY — chief_of_staff
    could delegate to sales/finance/legal but never marketing. Verifies the fix:
    registry membership + the declared tool_flat_name resolves to a real,
    registered ToolSpec (not just a string chief_of_staff would silently fail on)."""
    from app.workforce.agents.orchestration.chief_of_staff import SPECIALIST_REGISTRY
    from app.core.tool_bootstrap import load_all_tools
    from app.core.tool_registry import get_tool_by_flat_name

    assert "marketing" in SPECIALIST_REGISTRY, "marketing must be a real SPECIALIST_REGISTRY entry"
    spec = SPECIALIST_REGISTRY["marketing"]
    assert spec.domain == "marketing"

    load_all_tools()
    tool_spec = get_tool_by_flat_name(spec.tool_flat_name)
    assert tool_spec is not None, f"SPECIALIST_REGISTRY['marketing'].tool_flat_name={spec.tool_flat_name!r} must resolve to a registered tool"
    assert tool_spec.namespace == "marketing"


@pytest.mark.asyncio
async def test_orchestrate_inserts_real_child_agent_run_per_delegation(monkeypatch):
    from app.workforce.agents.governance.models import AgentRun as CanonicalAgentRun

    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    db = _create_mock_db()
    _mock_funnel_metrics(monkeypatch, qualified_leads=1, total_leads=2)

    result = await ChiefOfStaffOrchestrator.orchestrate(
        db=db,
        workspace_id=ws_id,
        user_id=user_id,
        goal="Kiểm tra pháp lý và CRM",
        runtime=MockRuntime(),
        domains=["sales", "legal"],
    )

    mission_id = int(result.mission_id)
    added_runs = [
        call.args[0] for call in db.add.call_args_list
        if isinstance(call.args[0], CanonicalAgentRun) and call.args[0].id != mission_id
    ]
    child_agent_keys = {run.agent_key for run in added_runs}

    assert child_agent_keys == {"sales_specialist", "legal_specialist"}
    for run in added_runs:
        assert run.parent_run_id == mission_id
        assert run.status == "completed"
        assert run.finished_at is not None


@pytest.mark.asyncio
async def test_orchestrate_marks_child_run_failed_when_snapshot_fetch_raises(monkeypatch):
    from app.workforce.agents.governance.models import AgentRun as CanonicalAgentRun

    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    db = _create_mock_db()
    _mock_funnel_metrics(monkeypatch, qualified_leads=1, total_leads=2)

    def _boom(db, workspace_id):
        raise RuntimeError("legal snapshot backend unavailable")

    from app.workforce.agents.orchestration import chief_of_staff as cos_module
    original_spec = cos_module.SPECIALIST_REGISTRY["legal"]
    broken_spec = original_spec.__class__(
        domain=original_spec.domain,
        agent_key=original_spec.agent_key,
        task=original_spec.task,
        tool_flat_name=original_spec.tool_flat_name,
        fetch_snapshot=_boom,
        quality_gate_compatible=original_spec.quality_gate_compatible,
    )
    monkeypatch.setitem(cos_module.SPECIALIST_REGISTRY, "legal", broken_spec)

    result = await ChiefOfStaffOrchestrator.orchestrate(
        db=db,
        workspace_id=ws_id,
        user_id=user_id,
        goal="Kiểm tra pháp lý",
        runtime=MockRuntime(),
        domains=["legal"],
    )

    assert result.specialist_reports["legal"]["status"] == "error"
    mission_id = int(result.mission_id)
    child_runs = [
        call.args[0] for call in db.add.call_args_list
        if isinstance(call.args[0], CanonicalAgentRun) and call.args[0].id != mission_id
    ]
    assert len(child_runs) == 1
    assert child_runs[0].status == "failed"


@pytest.mark.asyncio
async def test_orchestrate_skips_unknown_domain_without_crashing(monkeypatch):
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    db = _create_mock_db()
    _mock_funnel_metrics(monkeypatch, qualified_leads=1, total_leads=2)

    result = await ChiefOfStaffOrchestrator.orchestrate(
        db=db,
        workspace_id=ws_id,
        user_id=user_id,
        goal="Test unknown domain",
        runtime=MockRuntime(),
        domains=["sales", "not_a_real_domain"],
    )

    assert "sales" in result.specialist_reports
    assert "not_a_real_domain" not in result.specialist_reports


@pytest.mark.asyncio
async def test_chief_of_staff_diagnosis_depends_on_goal(monkeypatch):
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    _mock_funnel_metrics(monkeypatch, qualified_leads=0, total_leads=0)

    result_a = await ChiefOfStaffOrchestrator.orchestrate(
        db=_create_mock_db(),
        workspace_id=ws_id,
        user_id=user_id,
        goal="Tại sao doanh thu giảm trong tháng này?",
        runtime=MockRuntime(),
    )
    result_b = await ChiefOfStaffOrchestrator.orchestrate(
        db=_create_mock_db(),
        workspace_id=ws_id,
        user_id=user_id,
        goal="Kế hoạch marketing quý tới nên ưu tiên gì?",
        runtime=MockRuntime(),
    )

    # Regression guard for the original bug: diagnosis used to be identical hardcoded text
    # regardless of what the Founder actually asked.
    assert result_a.diagnosis != result_b.diagnosis
    assert "doanh thu giảm" in result_a.diagnosis
    assert "marketing" in result_b.diagnosis


@pytest.mark.asyncio
async def test_chief_of_staff_low_runway_creates_finance_action_without_automation_approval(monkeypatch):
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    db = _create_mock_db(runway_months=Decimal("3.0"))
    _mock_funnel_metrics(monkeypatch, qualified_leads=0, total_leads=0)

    result = await ChiefOfStaffOrchestrator.orchestrate(
        db=db,
        workspace_id=ws_id,
        user_id=user_id,
        goal="Tình hình tài chính công ty hiện tại thế nào?",
        runtime=MockRuntime(),
    )

    assert any(a["owner"] == "finance_specialist" for a in result.action_plan)
    # The finance review action has no automation_key (it is an internal review, not an
    # external dispatch), so it must not create an automation approval.
    assert len(result.required_approvals) == 0


@pytest.mark.asyncio
async def test_chief_of_staff_runtime_failure_degrades_without_crashing(monkeypatch):
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    _mock_funnel_metrics(monkeypatch, qualified_leads=0, total_leads=0)

    crashing_runtime = MockRuntime()
    crashing_runtime.set_healthy(False)

    result = await ChiefOfStaffOrchestrator.orchestrate(
        db=_create_mock_db(),
        workspace_id=ws_id,
        user_id=user_id,
        goal="Phân tích tổng quan công ty",
        runtime=crashing_runtime,
    )

    assert result.status == "failed"
    assert "unavailable" in result.diagnosis.lower()


@pytest.mark.asyncio
async def test_mission_control_bus_subscription():
    run_id = "test_run_123"
    ws_id = "test_ws_456"

    async def emit_events():
        await asyncio.sleep(0.01)
        mission_control_bus.emit_event(run_id, ws_id, "mission_started", {"goal": "Test goal"})
        await asyncio.sleep(0.01)
        mission_control_bus.emit_event(run_id, ws_id, "mission_completed", {"status": "completed"})

    asyncio.create_task(emit_events())

    received = []
    async for event in mission_control_bus.subscribe(run_id):
        received.append(event)

    assert len(received) == 2
    assert received[0]["event_type"] == "mission_started"
    assert received[1]["event_type"] == "mission_completed"


def test_mission_control_bus_registers_as_cross_process_raw_subscriber():
    """P0.4 wiring check: mission_control_bus must hook into CrossProcessEventListener so that
    a NOTIFY received on ANY process (not just the one that called emit_event) gets forwarded
    into this process's local _subscribers queues. Without this registration,
    MissionControlBus.subscribe() only ever sees same-process events."""
    assert mission_control_bus._on_cross_process_envelope in cross_process_event_listener._raw_subscribers


@pytest.mark.asyncio
async def test_mission_control_bus_delivers_cross_process_envelope_to_local_subscriber():
    """P0.4: a mission event that arrives via the cross-process NOTIFY path (i.e. NOT through
    a direct in-process emit_event() call - simulating a different process, e.g. a
    worker_main.py background job, having emitted it) must still reach a local subscribe(run_id)
    caller. This exercises the exact callback CrossProcessEventListener._on_notify would invoke,
    without needing a real Postgres LISTEN/NOTIFY connection."""
    run_id = f"cross_process_run_{generate_snowflake_id()}"
    ws_id = str(generate_snowflake_id())

    def _remote_envelope(event_type: str, data: dict) -> EventEnvelope:
        remote_event = {
            "event_id": f"remote-{generate_snowflake_id()}",
            "run_id": run_id,
            "workspace_id": ws_id,
            "agent_key": "chief_of_staff",
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        return EventEnvelope(
            event_id=str(generate_snowflake_id()),
            event_type=f"mission.{event_type}",
            workspace_id=ws_id,
            correlation_id=run_id,
            payload=remote_event,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    async def deliver_via_cross_process_bridge():
        await asyncio.sleep(0.01)
        # This is what CrossProcessEventListener._on_notify calls when a NOTIFY arrives from a
        # DIFFERENT process - never mission_control_bus.emit_event() directly.
        mission_control_bus._on_cross_process_envelope(
            _remote_envelope("mission_started", {"goal": "goal from another process"})
        )
        await asyncio.sleep(0.01)
        mission_control_bus._on_cross_process_envelope(
            _remote_envelope("mission_completed", {"status": "completed"})
        )

    asyncio.create_task(deliver_via_cross_process_bridge())

    received = []
    async for event in mission_control_bus.subscribe(run_id):
        received.append(event)

    assert len(received) == 2
    assert received[0]["event_type"] == "mission_started"
    assert received[0]["data"]["goal"] == "goal from another process"
    assert received[1]["event_type"] == "mission_completed"


def test_mission_control_bus_ignores_non_mission_envelopes():
    """The bridge must only forward envelopes published by mission_control_bus (event_type
    prefixed "mission."); it shares CrossProcessEventListener with unrelated platform events
    (e.g. chat/approval events published via app.core.events.publish_event directly) and must
    not leak those into mission subscriber queues."""
    run_id = f"unrelated_run_{generate_snowflake_id()}"
    queue = asyncio.Queue()
    mission_control_bus._subscribers.setdefault(run_id, set()).add(queue)
    try:
        envelope = EventEnvelope(
            event_id=str(generate_snowflake_id()),
            event_type="approval.resolved",
            workspace_id=str(generate_snowflake_id()),
            correlation_id=run_id,
            payload={"event_id": "x", "event_type": "approval.resolved", "data": {}},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        mission_control_bus._on_cross_process_envelope(envelope)
        assert queue.qsize() == 0
    finally:
        mission_control_bus._subscribers[run_id].discard(queue)
        if not mission_control_bus._subscribers[run_id]:
            mission_control_bus._subscribers.pop(run_id, None)


def test_mission_control_bus_dedupes_self_emitted_event_loopback():
    """Postgres NOTIFY is delivered to every session listening on the channel in the database,
    including a listener running in the SAME process that sent it (see _notifier vs
    cross_process_event_listener in app/core/events.py - two separate connections in what is
    typically the same OS process). Without dedup, a subscriber on the emitting process would
    see every event twice: once from emit_event()'s direct local dispatch, and once again a
    moment later when that same event loops back through the cross-process bridge."""
    run_id = f"dedup_run_{generate_snowflake_id()}"
    ws_id = "not-an-int-workspace-id"  # forces publish_event's cross-process leg to no-op safely
    queue = asyncio.Queue()
    mission_control_bus._subscribers.setdefault(run_id, set()).add(queue)
    try:
        event = mission_control_bus.emit_event(run_id, ws_id, "mission_started", {"goal": "dedup test"})
        assert queue.qsize() == 1  # delivered once, directly, by emit_event's local dispatch

        # Simulate the NOTIFY loop-back of that exact same event arriving back on this process.
        loopback_envelope = EventEnvelope(
            event_id=str(generate_snowflake_id()),
            event_type="mission.mission_started",
            workspace_id=ws_id,
            correlation_id=run_id,
            payload=event,
            timestamp=event["timestamp"],
        )
        mission_control_bus._on_cross_process_envelope(loopback_envelope)

        assert queue.qsize() == 1  # still 1 - the loop-back was recognized as a duplicate
    finally:
        mission_control_bus._subscribers[run_id].discard(queue)
        if not mission_control_bus._subscribers[run_id]:
            mission_control_bus._subscribers.pop(run_id, None)


def test_mission_control_rest_endpoint(client: TestClient, monkeypatch):
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()

    member = MagicMock()
    member.workspace_id = ws_id
    member.user_id = user_id

    app.dependency_overrides[get_current_workspace_member] = lambda: member
    _mock_funnel_metrics(monkeypatch, qualified_leads=3, total_leads=5)

    try:
        from app.db.session import get_db
        mock_db = _create_mock_db()
        app.dependency_overrides[get_db] = lambda: mock_db

        payload = {
            "goal": "Phân tích tăng trưởng doanh số và đề xuất kế hoạch 4 tuần",
        }
        res = client.post("/api/v1/agents/mission-control/orchestrate", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "partial"
        assert len(data["priorities"]) > 0
        assert len(data["action_plan"]) == 1

    finally:
        app.dependency_overrides.pop(get_current_workspace_member, None)


@pytest.mark.asyncio
async def test_chief_of_staff_budget_steps_exceeded_aborts_run(monkeypatch):
    """Safety Invariant: Run exceeding max_steps must abort immediately."""
    from app.workforce.agents.governance.budget import MissionBudget

    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    db = _create_mock_db()
    _mock_funnel_metrics(monkeypatch, qualified_leads=2, total_leads=5)

    # Set budget with max_steps=2 so post-sales step (seq=3) triggers limit
    tiny_budget = MissionBudget(max_steps=2, max_api_cost_usd=10.0, max_tool_calls=50)

    result = await ChiefOfStaffOrchestrator.orchestrate(
        db=db,
        workspace_id=ws_id,
        user_id=user_id,
        goal="Tăng trưởng doanh thu",
        runtime=MockRuntime(),
        budget=tiny_budget,
    )

    assert result.status == "failed"
    assert "Step limit" in result.diagnosis
    assert result.action_plan == []


@pytest.mark.asyncio
async def test_chief_of_staff_stuck_loop_aborts_run(monkeypatch):
    """Safety Invariant: Run encountering stuck action loop must abort."""
    from app.workforce.agents.governance.models import AgentToolCall

    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    db = _create_mock_db()
    _mock_funnel_metrics(monkeypatch, qualified_leads=2, total_leads=5)

    # Mock StuckDetector returning ABORT_RUN
    with patch("app.workforce.agents.governance.stuck_detector.StuckDetector.analyze_run") as mock_stuck:
        from app.workforce.agents.governance.stuck_detector import StuckAnalysisResult
        mock_stuck.return_value = StuckAnalysisResult(
            is_stuck=True,
            loop_type="SAME_ACTION_LOOP",
            repeated_count=5,
            suggested_action="ABORT_RUN",
            detail="Repeated 5 times",
        )

        result = await ChiefOfStaffOrchestrator.orchestrate(
            db=db,
            workspace_id=ws_id,
            user_id=user_id,
            goal="Thử lặp vô tận",
            runtime=MockRuntime(),
        )

        assert result.status == "failed"
        assert "Stuck loop detected" in result.diagnosis
        assert result.action_plan == []


# --- G1/G3 §10.6: mission_control_bus global (process-wide) listeners ---
# Before this existed, there was no way to observe "a mission somewhere just
# completed" without already knowing its run_id up front — subscribe(run_id)
# is scoped to one SSE client. This is the trigger point the Learning Review
# Worker (G1's spec) needs.

@pytest.mark.asyncio
async def test_global_listener_receives_locally_emitted_mission_event():
    received = []
    listener = received.append
    mission_control_bus.add_global_listener(listener)
    try:
        run_id = f"global_listener_run_{generate_snowflake_id()}"
        ws_id = str(generate_snowflake_id())
        mission_control_bus.emit_event(run_id, ws_id, "mission_started", {"goal": "test"})
        mission_control_bus.emit_event(run_id, ws_id, "mission_completed", {"status": "completed"})
    finally:
        mission_control_bus._global_listeners.remove(listener)

    event_types = [e["event_type"] for e in received if e["run_id"] == run_id]
    assert event_types == ["mission_started", "mission_completed"]
    assert received[-1]["workspace_id"] == ws_id


def test_global_listener_receives_cross_process_mission_event():
    """A mission completed on a DIFFERENT process (only observed here via
    the NOTIFY bridge, never a direct emit_event() call) must still reach
    a global listener on this process — this is the whole point of the
    mechanism: the Learning Review Worker shouldn't care which process ran
    the mission."""
    received = []
    listener = received.append
    mission_control_bus.add_global_listener(listener)
    try:
        run_id = f"global_listener_cross_run_{generate_snowflake_id()}"
        ws_id = str(generate_snowflake_id())
        remote_event = {
            "event_id": f"remote-{generate_snowflake_id()}",
            "run_id": run_id,
            "workspace_id": ws_id,
            "agent_key": "chief_of_staff",
            "event_type": "mission_completed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {"status": "completed"},
        }
        envelope = EventEnvelope(
            event_id=str(generate_snowflake_id()),
            event_type="mission.mission_completed",
            workspace_id=ws_id,
            correlation_id=run_id,
            payload=remote_event,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        mission_control_bus._on_cross_process_envelope(envelope)
    finally:
        mission_control_bus._global_listeners.remove(listener)

    assert len(received) == 1
    assert received[0]["run_id"] == run_id
    assert received[0]["event_type"] == "mission_completed"


def test_global_listener_exception_does_not_break_delivery_to_others():
    """One misbehaving listener must not stop other listeners (or the
    run_id-scoped SSE subscriber path) from receiving the event."""
    received = []

    def _bad_listener(event):
        raise RuntimeError("boom")

    good_listener = received.append
    mission_control_bus.add_global_listener(_bad_listener)
    mission_control_bus.add_global_listener(good_listener)
    try:
        run_id = f"global_listener_bad_run_{generate_snowflake_id()}"
        ws_id = str(generate_snowflake_id())
        event = mission_control_bus.emit_event(run_id, ws_id, "mission_completed", {"status": "completed"})
    finally:
        mission_control_bus._global_listeners.remove(_bad_listener)
        mission_control_bus._global_listeners.remove(good_listener)

    assert received == [event]


def test_default_terminal_event_logger_ignores_intermediate_events(caplog):
    from app.workforce.agents.orchestration.mission_control_bus import _log_terminal_mission_event

    with caplog.at_level("INFO"):
        _log_terminal_mission_event({"event_type": "subagent_delegated", "run_id": "r1", "workspace_id": "w1"})
    assert "terminal mission event" not in caplog.text

    with caplog.at_level("INFO"):
        _log_terminal_mission_event({"event_type": "mission_completed", "run_id": "r1", "workspace_id": "w1"})
    assert "terminal mission event" in caplog.text


# --- G2 §7.3 / G3 §12: Mission DRAFT -> founder confirm -> ACTIVE ---
# orchestrate() used to always run the full delegation+synthesis pipeline
# immediately and unconditionally, regardless of risk. These tests prove:
# a mission whose specialist domains carry risk above AUTO_START_MAX_RISK is
# created as a `draft` Outcome and returned WITHOUT executing anything, and
# confirm_mission() is the only way to actually run it afterward — replaying
# the originally-stashed goal, never a caller-supplied one.

def _create_stateful_mock_db(runway_months=Decimal("12.5")):
    """Like _create_mock_db, but Outcome/OutcomeRun/AgentRun rows added via
    db.add() are tracked and served back through db.query(...).first() —
    needed so confirm_mission() can look up the draft mission created by an
    earlier orchestrate() call against the same mock db."""
    from app.founder_os.outcomes.models import Outcome, OutcomeRun
    from app.workforce.agents.governance.models import AgentRun as CanonicalAgentRun

    db = MagicMock()
    stored: dict[str, list] = {"outcomes": [], "outcome_runs": [], "agent_runs": []}

    snapshot = FinanceManagementSnapshot(
        id=generate_snowflake_id(),
        workspace_id=generate_snowflake_id(),
        as_of=date(2026, 8, 1),
        cash=Decimal("1500000000"),
        burn=Decimal("120000000"),
        runway_months=runway_months,
        revenue=Decimal("200000000"),
        expenses=Decimal("120000000"),
        budget_variance=Decimal("10000000"),
    )
    profile = AccountingProfile(
        id=generate_snowflake_id(),
        workspace_id=generate_snowflake_id(),
        mode="TT58_MODE_1",
        status="CONFIRMED",
    )

    original_add = db.add

    def mock_add(instance):
        if isinstance(instance, Outcome):
            stored["outcomes"].append(instance)
        elif isinstance(instance, OutcomeRun):
            stored["outcome_runs"].append(instance)
        elif isinstance(instance, CanonicalAgentRun):
            stored["agent_runs"].append(instance)

    db.add.side_effect = mock_add

    def query_mock(*entities, **kwargs):
        model = entities[0] if entities else None
        m = MagicMock()
        m.filter.return_value = m
        m.order_by.return_value = m
        m.scalar.return_value = 0
        m.all.return_value = []
        m.limit.return_value.all.return_value = []

        if model is FinanceManagementSnapshot:
            m.first.return_value = snapshot
        elif model is AccountingProfile:
            m.first.return_value = profile
        elif model is Outcome:
            m.first.return_value = stored["outcomes"][-1] if stored["outcomes"] else None
        elif model is OutcomeRun:
            m.first.return_value = stored["outcome_runs"][-1] if stored["outcome_runs"] else None
        elif model is CanonicalAgentRun:
            m.first.return_value = stored["agent_runs"][-1] if stored["agent_runs"] else None
        else:
            m.first.return_value = None
        return m

    db.query.side_effect = query_mock
    return db, stored


@pytest.mark.asyncio
async def test_high_risk_mission_waits_for_confirmation(monkeypatch):
    from app.workforce.agents.orchestration import chief_of_staff as cos_module

    original_spec = cos_module.SPECIALIST_REGISTRY["finance"]
    risky_spec = original_spec.__class__(
        domain=original_spec.domain,
        agent_key=original_spec.agent_key,
        task=original_spec.task,
        tool_flat_name=original_spec.tool_flat_name,
        fetch_snapshot=original_spec.fetch_snapshot,
        quality_gate_compatible=original_spec.quality_gate_compatible,
        risk_level="R2",
    )
    monkeypatch.setitem(cos_module.SPECIALIST_REGISTRY, "finance", risky_spec)

    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    db, stored = _create_stateful_mock_db()

    result = await ChiefOfStaffOrchestrator.orchestrate(
        db=db,
        workspace_id=ws_id,
        user_id=user_id,
        goal="Đề xuất kế hoạch tài chính rủi ro cao",
        runtime=MockRuntime(),
        domains=["finance"],
    )

    assert result.status == "waiting_confirmation"
    assert result.specialist_reports == {}
    assert stored["outcomes"][-1].status == "draft"
    # Only the parent mission run was created — the delegation loop never ran.
    assert len(stored["agent_runs"]) == 1


@pytest.mark.asyncio
async def test_confirm_mission_executes_the_originally_stashed_goal(monkeypatch):
    from app.workforce.agents.orchestration import chief_of_staff as cos_module

    original_spec = cos_module.SPECIALIST_REGISTRY["finance"]
    risky_spec = original_spec.__class__(
        domain=original_spec.domain,
        agent_key=original_spec.agent_key,
        task=original_spec.task,
        tool_flat_name=original_spec.tool_flat_name,
        fetch_snapshot=original_spec.fetch_snapshot,
        quality_gate_compatible=original_spec.quality_gate_compatible,
        risk_level="R2",
    )
    monkeypatch.setitem(cos_module.SPECIALIST_REGISTRY, "finance", risky_spec)

    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    db, stored = _create_stateful_mock_db()

    original_goal = "Đề xuất kế hoạch tài chính rủi ro cao"
    draft_result = await ChiefOfStaffOrchestrator.orchestrate(
        db=db,
        workspace_id=ws_id,
        user_id=user_id,
        goal=original_goal,
        runtime=MockRuntime(),
        domains=["finance"],
    )
    assert draft_result.status == "waiting_confirmation"

    confirmed_result = await ChiefOfStaffOrchestrator.confirm_mission(
        db=db,
        mission_id=int(draft_result.mission_id),
        user_id=user_id,
        runtime=MockRuntime(),
    )

    assert confirmed_result.status in ("completed", "partial")
    assert confirmed_result.mission_id == draft_result.mission_id
    # The executed goal is the one stashed at draft time, not something the
    # confirm call could have substituted.
    assert confirmed_result.goal == original_goal
    assert "finance" in confirmed_result.specialist_reports
    # MockRuntime cannot produce valid structured JSON, so "partial" (mapped
    # to Outcome.status="planning", same as the non-draft flow) is the
    # honest, expected outcome here — see test_chief_of_staff_orchestration_flow.
    # The one thing this test must prove either way: execution actually ran,
    # i.e. the mission moved out of "draft".
    assert stored["outcomes"][-1].status != "draft"


@pytest.mark.asyncio
async def test_confirm_mission_rejects_non_draft_mission(monkeypatch):
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    db, stored = _create_stateful_mock_db()

    # A normal (R0) mission auto-executes and is never left in "draft".
    result = await ChiefOfStaffOrchestrator.orchestrate(
        db=db,
        workspace_id=ws_id,
        user_id=user_id,
        goal="Rà soát CRM",
        runtime=MockRuntime(),
        domains=["sales"],
    )
    assert result.status in ("completed", "partial")

    with pytest.raises(ValueError, match="not awaiting confirmation"):
        await ChiefOfStaffOrchestrator.confirm_mission(
            db=db,
            mission_id=int(result.mission_id),
            user_id=user_id,
        )


@pytest.mark.asyncio
async def test_confirm_mission_rejects_a_workspace_mismatch(monkeypatch):
    """Defense in depth: confirming another workspace's mission must be
    rejected even if the caller correctly guesses/knows its mission_id."""
    from app.workforce.agents.orchestration import chief_of_staff as cos_module

    original_spec = cos_module.SPECIALIST_REGISTRY["finance"]
    risky_spec = original_spec.__class__(
        domain=original_spec.domain,
        agent_key=original_spec.agent_key,
        task=original_spec.task,
        tool_flat_name=original_spec.tool_flat_name,
        fetch_snapshot=original_spec.fetch_snapshot,
        quality_gate_compatible=original_spec.quality_gate_compatible,
        risk_level="R2",
    )
    monkeypatch.setitem(cos_module.SPECIALIST_REGISTRY, "finance", risky_spec)

    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    db, stored = _create_stateful_mock_db()

    draft_result = await ChiefOfStaffOrchestrator.orchestrate(
        db=db,
        workspace_id=ws_id,
        user_id=user_id,
        goal="Mission thuộc workspace A",
        runtime=MockRuntime(),
        domains=["finance"],
    )
    assert draft_result.status == "waiting_confirmation"

    other_workspace_id = generate_snowflake_id()
    with pytest.raises(PermissionError):
        await ChiefOfStaffOrchestrator.confirm_mission(
            db=db,
            mission_id=int(draft_result.mission_id),
            user_id=user_id,
            workspace_id=other_workspace_id,
        )


@pytest.mark.asyncio
async def test_orchestrate_refuses_to_delegate_from_an_already_nested_subrun(monkeypatch):
    """G3 Phase 1E (Subrun hardening): nothing today can construct a mission
    whose own AgentRun has parent_run_id set through orchestrate()'s public
    API (no delegation path recurses into orchestrate() itself yet) - so this
    exercises the guard the same way `_resume` lets confirm_mission() reuse
    an already-built AgentRun: by handing orchestrate() one directly with
    parent_run_id already set, proving MAX_SUBRUN_DEPTH=1 is enforced at the
    exact point a future recursive specialist would first hit it."""
    from app.founder_os.outcomes.models import Outcome, OutcomeRun
    from app.workforce.agents.governance.models import AgentRun as CanonicalAgentRun

    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    mission_id = generate_snowflake_id()
    fake_parent_run_id = generate_snowflake_id()
    db, stored = _create_stateful_mock_db()

    outcome = Outcome(
        id=generate_snowflake_id(), workspace_id=ws_id, function="strategy",
        title="Nested subrun attempt", desired_result="test", requested_by=user_id,
        status="draft",
    )
    outcome_run = OutcomeRun(
        id=generate_snowflake_id(), outcome_id=outcome.id, agent_run_id=mission_id,
        status="queued", verification_status="UNKNOWN",
    )
    agent_run = CanonicalAgentRun(
        id=mission_id, workspace_id=ws_id, user_id=user_id,
        parent_run_id=fake_parent_run_id,  # this mission is itself a subrun
        agent_key="chief_of_staff", runtime="pending", status="created",
        permission_profile="chief_of_staff_suggest",
        started_at=datetime.now(timezone.utc),
    )

    result = await ChiefOfStaffOrchestrator.orchestrate(
        db=db,
        workspace_id=ws_id,
        user_id=user_id,
        goal="Nested subrun attempt",
        runtime=MockRuntime(),
        domains=["sales", "finance"],
        _resume=(mission_id, outcome, outcome_run, agent_run, ["sales", "finance"]),
    )

    assert result.specialist_reports == {}
    # No child agent_runs row was created for either requested domain.
    assert len(stored["agent_runs"]) == 0

