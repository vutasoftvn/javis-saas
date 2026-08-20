from typing import List, Optional
from app.workforce.events.contracts import BaseEvent
from app.workforce.events.redaction import redact_payload

class EventStore:
    """
    Mock Postgres append-only event store.
    """
    def __init__(self):
        self._events: List[BaseEvent] = []
        
    def append(self, event: BaseEvent) -> None:
        """
        Append a new event to the store. Applies redaction before saving.
        """
        if hasattr(event, "payload"):
            event.payload = redact_payload(event.payload)
        self._events.append(event)
        
    def read(self, correlation_id: str, after_cursor: Optional[int] = None, limit: int = 100) -> List[BaseEvent]:
        """
        Read events sequentially for a given run (correlation_id).
        """
        run_events = [e for e in self._events if e.correlation_id == correlation_id]
        if after_cursor is not None:
            # Fake cursor logic based on index
            run_events = run_events[after_cursor:]
        return run_events[:limit]
