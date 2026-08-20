"""
Unit Tests for Phase 2: Event Store, Sessions Engine & Trajectory Builder
Kiểm tra tính toàn vẹn của Append-Only SQLite, Resume, Fork, Replay và Trajectory Narrative.
"""
import pytest
import os
import tempfile
from datetime import datetime

from storage.sqlite.connection import SQLiteManager
from agent_runtime.events.base import AgentEvent, EventType
from agent_runtime.events.sqlite_event_store import SQLiteEventStore
from agent_runtime.sessions.base import SessionStatus
from agent_runtime.sessions.session_manager import SessionManager
from agent_runtime.trajectory.trajectory_builder import TrajectoryBuilder
from agent_runtime.trajectory.models import TrajectoryStepType


@pytest.fixture
def temp_sqlite_manager():
    """Tạo SQLite db tạm thời trong /tmp để kiểm thử biệt lập"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    manager = SQLiteManager(db_path=db_path)
    yield manager
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.mark.asyncio
async def test_event_store_append_and_sequence(temp_sqlite_manager):
    """Kiểm tra SQLiteEventStore ghi nhận và tự động sinh sequence_num chuẩn xác"""
    store = SQLiteEventStore(temp_sqlite_manager)
    session_id = "ses_unit_test_01"

    ev1 = AgentEvent(
        session_id=session_id,
        type=EventType.USER_MESSAGE,
        actor={"type": "user", "id": "founder"},
        payload={"message": "Xin chào, hãy nghiên cứu thị trường EdTech"}
    )
    ev2 = AgentEvent(
        session_id=session_id,
        type=EventType.INTENT_DETECTED,
        actor={"type": "agent", "id": "orchestrator"},
        payload={"intent": "market.research", "risk_level": "LOW"}
    )

    await store.append(ev1)
    await store.append(ev2)

    events = await store.get_events_by_session(session_id)
    assert len(events) == 2
    assert events[0].type == EventType.USER_MESSAGE
    assert events[1].type == EventType.INTENT_DETECTED
    assert events[0].id == ev1.id
    assert events[1].id == ev2.id


@pytest.mark.asyncio
async def test_session_lifecycle_and_creation(temp_sqlite_manager):
    """Kiểm tra SessionManager tạo và truy vấn session"""
    session_mgr = SessionManager(temp_sqlite_manager)
    session = await session_mgr.create_session(
        company_id="comp_cosa_01",
        user_id="user_founder",
        profile_id="cmo",
        project_id="proj_mid"
    )

    assert session.id.startswith("ses_")
    assert session.status == SessionStatus.ACTIVE
    assert session.company_id == "comp_cosa_01"

    fetched = await session_mgr.get_session(session.id)
    assert fetched is not None
    assert fetched.id == session.id

    # Kiểm tra event session.started tự động sinh
    events = await session_mgr.event_store.get_events_by_session(session.id)
    assert len(events) == 1
    assert events[0].type == EventType.SESSION_STARTED


@pytest.mark.asyncio
async def test_session_forking_branching(temp_sqlite_manager):
    """Kiểm tra tính năng phân nhánh phiên làm việc (Session Forking)"""
    session_mgr = SessionManager(temp_sqlite_manager)
    parent = await session_mgr.create_session(
        company_id="comp_cosa_01",
        user_id="user_founder",
        profile_id="cmo"
    )

    # Thêm 3 events tiếp theo
    ev1 = AgentEvent(
        session_id=parent.id,
        type=EventType.USER_MESSAGE,
        actor={"type": "user", "id": "founder"},
        payload={"message": "Khảo sát chiến lược định giá"}
    )
    ev2 = AgentEvent(
        session_id=parent.id,
        type=EventType.INTENT_DETECTED,
        actor={"type": "agent", "id": "cmo"},
        payload={"intent": "pricing.strategy"}
    )
    ev3 = AgentEvent(
        session_id=parent.id,
        type=EventType.ASSISTANT_MESSAGE,
        actor={"type": "agent", "id": "cmo"},
        payload={"content": "Đề xuất 2 phương án: SaaS hoặc License"}
    )
    await session_mgr.event_store.append(ev1)
    await session_mgr.event_store.append(ev2)
    await session_mgr.event_store.append(ev3)

    # Phân nhánh session con tại điểm ev2 (Intent)
    child = await session_mgr.fork_session(parent_session_id=parent.id, from_event_id=ev2.id)

    assert child.id != parent.id
    assert child.parent_session_id == parent.id
    assert child.fork_event_id == ev2.id

    child_events = await session_mgr.event_store.get_events_by_session(child.id)
    # Gồm session.started, ev1, ev2 (3 events)
    assert len(child_events) == 3
    assert child_events[-1].type == EventType.INTENT_DETECTED


@pytest.mark.asyncio
async def test_session_state_restoration_and_safe_replay(temp_sqlite_manager):
    """Kiểm tra khôi phục trạng thái và Safe Replay (không chạy lại side effects)"""
    session_mgr = SessionManager(temp_sqlite_manager)
    session = await session_mgr.create_session(
        company_id="comp_cosa_01",
        user_id="user_founder",
        profile_id="marketing"
    )

    await session_mgr.event_store.append(
        AgentEvent(
            session_id=session.id,
            type=EventType.TOOL_COMPLETED,
            actor={"type": "agent", "id": "marketing"},
            payload={"tool_id": "crm.create_lead", "has_side_effects": True, "lead_id": "lead_123"}
        )
    )
    await session_mgr.event_store.append(
        AgentEvent(
            session_id=session.id,
            type=EventType.ARTIFACT_CREATED,
            actor={"type": "agent", "id": "marketing"},
            payload={"artifact_path": "docs/reports/market_report.md"}
        )
    )

    # Khôi phục trạng thái
    state = await session_mgr.restore_state(session.id)
    assert "crm.create_lead" in state["completed_tools"]
    assert "docs/reports/market_report.md" in state["artifacts"]

    # Replay an toàn
    replay_log = await session_mgr.replay_session(session.id)
    assert len(replay_log) == 3
    # Tool có side-effects phải được đánh dấu an toàn
    assert replay_log[1]["side_effect_prevented"] is True


def test_trajectory_builder_narrative():
    """Kiểm tra TrajectoryBuilder chuyển đổi AgentEvent thành Narrative Timeline cho Hologram Hub"""
    session_id = "ses_traj_test_01"
    events = [
        AgentEvent(
            id="evt_01",
            session_id=session_id,
            timestamp="2026-08-20T09:00:01Z",
            type=EventType.USER_MESSAGE,
            actor={"type": "user", "id": "founder"},
            payload={"message": "Nghiên cứu đối thủ cạnh tranh"}
        ),
        AgentEvent(
            id="evt_02",
            session_id=session_id,
            timestamp="2026-08-20T09:00:02Z",
            type=EventType.INTENT_DETECTED,
            actor={"type": "agent", "id": "cmo"},
            payload={"intent": "competitor.analysis", "risk_level": "LOW"}
        ),
        AgentEvent(
            id="evt_03",
            session_id=session_id,
            timestamp="2026-08-20T09:00:05Z",
            type=EventType.TOOL_COMPLETED,
            actor={"type": "agent", "id": "cmo"},
            payload={"tool_id": "web.search", "presenter_payload": {"sources": 8}},
            metadata={"duration_ms": 950}
        ),
        AgentEvent(
            id="evt_04",
            session_id=session_id,
            timestamp="2026-08-20T09:00:10Z",
            type=EventType.SESSION_COMPLETED,
            actor={"type": "agent", "id": "cmo"},
            payload={}
        )
    ]

    timeline = TrajectoryBuilder.build_timeline(
        session_id=session_id,
        profile_id="cmo",
        events=events
    )

    assert timeline.session_id == session_id
    assert timeline.status == "completed"
    assert len(timeline.steps) == 4
    assert timeline.steps[0].step_type == TrajectoryStepType.REQUEST_RECEIVED
    assert timeline.steps[1].step_type == TrajectoryStepType.INTENT_CLASSIFIED
    assert timeline.steps[2].step_type == TrajectoryStepType.TOOL_EXECUTED
    assert timeline.steps[2].duration_ms == 950
    assert timeline.summary_metrics["total_tools_executed"] == 1
