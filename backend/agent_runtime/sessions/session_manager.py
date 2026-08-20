"""
COSA Session Manager Implementation
Hiện thực quản lý vòng đời Session, State Restoration, Forking và Safe Replay (Structure.md Mục 19, 21, 22, 23).
"""
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from agent.events.base import AgentEvent, EventType
from agent.events.sqlite_event_store import SQLiteEventStore
from agent.sessions.base import SessionManagerInterface, SessionMetadata, SessionStatus
from storage.sqlite.connection import SQLiteManager


class SessionManager(SessionManagerInterface):
    """Hiện thực động cơ quản lý phiên làm việc của COSA Agent Harness"""

    def __init__(
        self, 
        db_manager: Optional[SQLiteManager] = None, 
        event_store: Optional[SQLiteEventStore] = None
    ):
        self.db = db_manager or SQLiteManager()
        self.event_store = event_store or SQLiteEventStore(self.db)

    async def create_session(
        self, 
        company_id: str, 
        user_id: str, 
        profile_id: str, 
        project_id: Optional[str] = None
    ) -> SessionMetadata:
        """Khởi tạo phiên làm việc mới và phát sinh event session.started"""
        await self.db.ensure_initialized()
        session_id = f"ses_{uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        session = SessionMetadata(
            id=session_id,
            company_id=company_id,
            user_id=user_id,
            profile_id=profile_id,
            project_id=project_id,
            status=SessionStatus.ACTIVE,
            created_at=now,
            updated_at=now
        )

        await self.db.execute_write(
            """
            INSERT INTO sessions (id, company_id, user_id, profile_id, project_id, parent_session_id, fork_event_id, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session.id,
                session.company_id,
                session.user_id,
                session.profile_id,
                session.project_id,
                session.parent_session_id,
                session.fork_event_id,
                session.status.value,
                session.created_at,
                session.updated_at
            )
        )

        # Phát sinh event session.started vào Event Store
        await self.event_store.append(
            AgentEvent(
                session_id=session.id,
                type=EventType.SESSION_STARTED,
                actor={"type": "user", "id": user_id},
                payload={"company_id": company_id, "profile_id": profile_id, "project_id": project_id}
            )
        )

        return session

    async def get_session(self, session_id: str) -> Optional[SessionMetadata]:
        """Truy vấn thông tin chi tiết của phiên"""
        row = await self.db.fetch_one("SELECT * FROM sessions WHERE id = ?", (session_id,))
        if not row:
            return None
        return SessionMetadata(
            id=row["id"],
            company_id=row["company_id"],
            user_id=row["user_id"],
            profile_id=row["profile_id"],
            project_id=row["project_id"],
            parent_session_id=row["parent_session_id"],
            fork_event_id=row["fork_event_id"],
            status=SessionStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

    async def update_status(self, session_id: str, status: SessionStatus) -> bool:
        """Cập nhật trạng thái của phiên (active, paused, completed, failed)"""
        now = datetime.now(timezone.utc).isoformat()
        await self.db.execute_write(
            "UPDATE sessions SET status = ?, updated_at = ? WHERE id = ?",
            (status.value, now, session_id)
        )
        return True

    async def fork_session(self, parent_session_id: str, from_event_id: str) -> SessionMetadata:
        """
        Phân nhánh phiên làm việc (Structure.md Mục 22):
        Sao chép toàn bộ lịch sử từ đầu tới from_event_id sang session mới.
        """
        parent = await self.get_session(parent_session_id)
        if not parent:
            raise ValueError(f"Parent session '{parent_session_id}' not found")

        all_events = await self.event_store.get_events_by_session(parent_session_id)
        cutoff_index = -1
        for idx, ev in enumerate(all_events):
            if ev.id == from_event_id:
                cutoff_index = idx
                break

        if cutoff_index == -1:
            raise ValueError(f"Event '{from_event_id}' not found in parent session")

        forked_events = all_events[: cutoff_index + 1]

        # Khởi tạo session con
        new_session_id = f"ses_{uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        child_session = SessionMetadata(
            id=new_session_id,
            company_id=parent.company_id,
            user_id=parent.user_id,
            profile_id=parent.profile_id,
            project_id=parent.project_id,
            parent_session_id=parent_session_id,
            fork_event_id=from_event_id,
            status=SessionStatus.ACTIVE,
            created_at=now,
            updated_at=now
        )

        await self.db.execute_write(
            """
            INSERT INTO sessions (id, company_id, user_id, profile_id, project_id, parent_session_id, fork_event_id, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                child_session.id,
                child_session.company_id,
                child_session.user_id,
                child_session.profile_id,
                child_session.project_id,
                child_session.parent_session_id,
                child_session.fork_event_id,
                child_session.status.value,
                child_session.created_at,
                child_session.updated_at
            )
        )

        # Sao chép các events lịch sử sang session mới
        for ev in forked_events:
            cloned_event = AgentEvent(
                session_id=new_session_id,
                timestamp=ev.timestamp,
                type=ev.type,
                actor=ev.actor,
                payload=ev.payload,
                metadata={**ev.metadata, "forked_from_event_id": ev.id}
            )
            await self.event_store.append(cloned_event)

        return child_session

    async def replay_session(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Tái hiện lại phiên làm việc từ Event Log (Structure.md Mục 23).
        Quy tắc an toàn: Không thực thi lại các side-effects (send_email, deploy, payment).
        """
        events = await self.event_store.get_events_by_session(session_id)
        replay_log: List[Dict[str, Any]] = []

        for ev in events:
            replay_item = {
                "event_id": ev.id,
                "type": ev.type.value,
                "timestamp": ev.timestamp,
                "actor": ev.actor,
                "summary": ev.payload.get("summary") or ev.payload.get("title") or ev.type.value,
                "side_effect_prevented": ev.type == EventType.TOOL_COMPLETED and ev.payload.get("has_side_effects", False)
            }
            replay_log.append(replay_item)

        return replay_log

    async def restore_state(self, session_id: str) -> Dict[str, Any]:
        """Khôi phục trạng thái làm việc (Working State) từ Event Stream (Structure.md Mục 21)"""
        events = await self.event_store.get_events_by_session(session_id)
        state: Dict[str, Any] = {
            "session_id": session_id,
            "accumulated_context": {},
            "active_intent": None,
            "last_active_skill": None,
            "completed_tools": [],
            "artifacts": [],
            "pending_approval": None
        }

        for ev in events:
            if ev.type == EventType.INTENT_DETECTED:
                state["active_intent"] = ev.payload.get("intent")
            elif ev.type == EventType.CONTEXT_LOADED:
                state["accumulated_context"].update(ev.payload.get("data", {}))
            elif ev.type == EventType.SKILL_LOADED:
                state["last_active_skill"] = ev.payload.get("skill_id")
            elif ev.type == EventType.TOOL_COMPLETED:
                state["completed_tools"].append(ev.payload.get("tool_id"))
            elif ev.type == EventType.ARTIFACT_CREATED:
                state["artifacts"].append(ev.payload.get("artifact_path"))
            elif ev.type == EventType.APPROVAL_REQUESTED:
                state["pending_approval"] = ev.payload
            elif ev.type in (EventType.APPROVAL_GRANTED, EventType.APPROVAL_REJECTED):
                state["pending_approval"] = None

        return state
