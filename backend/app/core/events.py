import asyncio
from collections import defaultdict
from datetime import datetime
import uuid
from typing import Optional, Dict, Any, Set, AsyncGenerator
from pydantic import BaseModel


class EventEnvelope(BaseModel):
    """Gói tin sự kiện thời gian thực theo chuẩn Blueprint §106."""
    event_id: str
    event_type: str
    workspace_id: str
    actor_id: Optional[str] = None
    correlation_id: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    timestamp: str


class EventBroker:
    """Bộ điều phối sự kiện thời gian thực theo từng workspace."""
    def __init__(self):
        self._subscribers: Dict[str, Set[asyncio.Queue]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def subscribe(self, workspace_id: str) -> AsyncGenerator[EventEnvelope, None]:
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        async with self._lock:
            self._subscribers[workspace_id].add(queue)
        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            async with self._lock:
                self._subscribers[workspace_id].discard(queue)
                if not self._subscribers[workspace_id]:
                    del self._subscribers[workspace_id]

    async def publish(self, envelope: EventEnvelope):
        async with self._lock:
            queues = list(self._subscribers.get(envelope.workspace_id, []))
        for q in queues:
            try:
                q.put_nowait(envelope)
            except asyncio.QueueFull:
                pass


event_broker = EventBroker()


def publish_event(
    event_type: str,
    workspace_id: int,
    actor_id: Optional[int] = None,
    payload: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
) -> EventEnvelope:
    """Hàm phát tán sự kiện thời gian thực tới tất cả client đang kết nối trong workspace."""
    envelope = EventEnvelope(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        workspace_id=str(workspace_id),
        actor_id=str(actor_id) if actor_id else None,
        correlation_id=correlation_id,
        payload=payload or {},
        timestamp=datetime.utcnow().isoformat(),
    )
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(event_broker.publish(envelope))
    except RuntimeError:
        pass
    return envelope
