from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.platform.license.models import NeedsYouItem, Blocker, WorkReview
from app.founder_os.tasks.models import Task


from app.core.snowflake import generate_snowflake_id
from app.db.models import Brain
from app.founder_os.strategy.models import Project


class NeedsYouService:
    """Read-composition service for the founder's unified 'Needs You' queue."""

    # Đề xuất do AI soạn trong chat. Tách riêng khỏi "approval"/"blocker" để người dùng
    # nhìn hàng đợi là phân biệt được ngay: đây là thứ AI nghĩ nên làm, chưa ai làm cả.
    AI_PROPOSAL_SOURCE_TYPE = "ai_proposal"

    @classmethod
    def create_item(
        cls,
        db: Session,
        workspace_id: int,
        source_type: str,
        source_id: int,
        reason: str,
        requested_action: Optional[str] = None,
        priority: str = "P1",
        cycle_id: Optional[int] = None,
        due_at: Optional[datetime] = None,
    ) -> NeedsYouItem:
        """Đưa một việc vào hàng đợi của founder.

        Trước đây mỗi nơi cần đẩy việc vào hàng đợi lại tự ``NeedsYouItem(...)`` (xem
        blocker_router và review_service), nên không có chỗ nào duy nhất để siết giá trị
        hợp lệ - gom về đây trước khi có thêm nguồn thứ ba là chat.
        """
        item = NeedsYouItem(
            workspace_id=workspace_id,
            cycle_id=cycle_id,
            source_type=source_type,
            source_id=source_id,
            priority=priority if priority in ("P0", "P1", "P2") else "P1",
            reason=reason,
            requested_action=requested_action,
            due_at=due_at,
            status="OPEN",
            created_at=datetime.utcnow(),
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @classmethod
    def list_items(
        cls,
        db: Session,
        workspace_id: int,
        include_snoozed: bool = False,
    ) -> List[Dict[str, Any]]:
        now = datetime.utcnow()
        filters = [
            NeedsYouItem.workspace_id == workspace_id,
            NeedsYouItem.status != "RESOLVED",
            NeedsYouItem.status != "CANCELLED",
        ]

        if not include_snoozed:
            filters.append(
                (NeedsYouItem.snooze_until.is_(None)) | (NeedsYouItem.snooze_until <= now)
            )

        items = (
            db.query(NeedsYouItem)
            .filter(*filters)
            .order_by(NeedsYouItem.priority.asc(), NeedsYouItem.created_at.desc())
            .all()
        )

        results = []
        for item in items:
            results.append({
                "id": str(item.id),
                "workspace_id": str(item.workspace_id),
                "cycle_id": str(item.cycle_id) if item.cycle_id else None,
                "source_type": item.source_type,
                "source_id": str(item.source_id),
                "priority": item.priority,
                "reason": item.reason,
                "requested_action": item.requested_action,
                "due_at": item.due_at.isoformat() if item.due_at else None,
                "status": item.status,
                "snooze_until": item.snooze_until.isoformat() if item.snooze_until else None,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            })
        return results

    @classmethod
    def resolve_item(
        cls,
        db: Session,
        workspace_id: int,
        item_id: int,
    ) -> NeedsYouItem:
        item = (
            db.query(NeedsYouItem)
            .filter(NeedsYouItem.id == item_id, NeedsYouItem.workspace_id == workspace_id)
            .first()
        )
        if not item:
            raise ValueError(f"NeedsYou item {item_id} not found in workspace {workspace_id}")

        item.status = "RESOLVED"
        item.resolved_at = datetime.utcnow()

        # Tự động thực thi hành động đã đề xuất nếu là dạng khởi tạo (VD: Tạo dự án)
        if item.source_type == cls.AI_PROPOSAL_SOURCE_TYPE and item.requested_action:
            action_text = item.requested_action.strip()
            lower_action = action_text.lower()
            if any(lower_action.startswith(prefix) for prefix in ("tạo dự án", "tạo project", "create project")):
                title_part = action_text
                for prefix in ("Tạo dự án", "tạo dự án", "Tạo project", "tạo project", "Create project", "create project"):
                    if title_part.startswith(prefix):
                        title_part = title_part[len(prefix):].strip(" :-–—")
                        break
                title = title_part
                desc = item.reason or ""
                if " - " in title_part:
                    parts = title_part.split(" - ", 1)
                    title = parts[0].strip()
                    desc = parts[1].strip() + (f"\n{item.reason}" if item.reason else "")
                elif " – " in title_part:
                    parts = title_part.split(" – ", 1)
                    title = parts[0].strip()
                    desc = parts[1].strip() + (f"\n{item.reason}" if item.reason else "")

                if title:
                    existing_proj = (
                        db.query(Project)
                        .filter(Project.workspace_id == workspace_id, Project.title == title)
                        .first()
                    )
                    if not existing_proj:
                        brain = db.query(Brain).filter(Brain.workspace_id == workspace_id).first()
                        new_proj = Project(
                            workspace_id=workspace_id,
                            brain_id=brain.id if brain else generate_snowflake_id(),
                            title=title,
                            description=desc.strip(),
                            status="active",
                            phase="Phase 1",
                        )
                        db.add(new_proj)

        db.add(item)
        db.commit()
        db.refresh(item)
        return item


    @classmethod
    def snooze_item(
        cls,
        db: Session,
        workspace_id: int,
        item_id: int,
        until: datetime,
    ) -> NeedsYouItem:
        item = (
            db.query(NeedsYouItem)
            .filter(NeedsYouItem.id == item_id, NeedsYouItem.workspace_id == workspace_id)
            .first()
        )
        if not item:
            raise ValueError(f"NeedsYou item {item_id} not found in workspace {workspace_id}")

        item.status = "SNOOZED"
        item.snooze_until = until
        db.add(item)
        db.commit()
        db.refresh(item)
        return item
