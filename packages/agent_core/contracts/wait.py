from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field

__all__ = ["WaitKind", "WaitDescriptor"]


class WaitKind(str, enum.Enum):
    """Phân loại trạng thái tạm dừng chờ theo Master Guide §19."""
    APPROVAL = "approval"
    EVENT = "event"
    INPUT = "input"
    TIMER = "timer"
    EXTERNAL_DEPENDENCY = "external_dependency"


class WaitDescriptor(BaseModel):
    """Mô tả có khả năng định tuyến (routable) cho trạng thái chờ/bị chặn.
    
    Nguyên tắc Master Guide §19: Không chấp nhận trạng thái chờ chỉ dựa vào câu chữ
    chung chung (prose). Mọi waiting state phải trả lời được:
    - kind: Chờ cái gì (approval, external event, human input, timer)?
    - reason: Lý do cụ thể.
    - owner_responder: Ai hoặc hệ thống nào có thẩm quyền unblock?
    - resume_trigger: Event hoặc tín hiệu nào sẽ kích hoạt tiếp tục?
    - checkpoint_ref: Checkpoint nào cần được nạp lại để resume?
    - related_ref: Tham chiếu tới approval_id, task_id hoặc external entity liên quan.
    - created_at / expires_at: Thời điểm tạo và thời hạn hết hạn tuỳ chọn.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    kind: WaitKind = WaitKind.APPROVAL
    reason: str
    owner_responder: Optional[str] = None
    resume_trigger: str = "approval.decided"
    checkpoint_ref: str
    related_ref: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None

