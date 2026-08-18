from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.core.feature_flags import FLAG_AGENT_MEMORY_V12_3, is_enabled
from app.workforce.memory.adapters.null_adapter import NullAgentMemoryAdapter
from app.workforce.memory.adapters.tencentdb_adapter import TencentDBAgentMemoryAdapter
from app.workforce.memory.gateway import AgentMemoryGateway
from app.workforce.memory.models import AgentMemoryEntry

_null_adapter = NullAgentMemoryAdapter()


def get_gateway(db: Session, workspace_id: int) -> AgentMemoryGateway:
    """Resolve the active AgentMemoryGateway for this workspace (ADR-MEM-001,
    ADR-MEM-002). Returns the null adapter whenever the flag is off - callers
    never need to check the flag themselves, only ask for a gateway and use
    it (every gateway method already degrades gracefully on its own)."""
    if not is_enabled(db, FLAG_AGENT_MEMORY_V12_3, workspace_id):
        return _null_adapter
    return TencentDBAgentMemoryAdapter()


class FiveLayerMemoryManager:
    """Manager for COSA 5-Layer Memory Architecture (§b1, §P0.4).
    L0: Session, L1: Working, L2: Founder, L3: Knowledge, L4: Learning.
    """

    @staticmethod
    def store_memory(
        db: Session,
        workspace_id: int,
        layer: str,
        key: str,
        value: Dict[str, Any],
        brain_id: Optional[int] = None,
        relevance_score: float = 1.0,
    ) -> AgentMemoryEntry:
        existing = (
            db.query(AgentMemoryEntry)
            .filter(
                AgentMemoryEntry.workspace_id == workspace_id,
                AgentMemoryEntry.layer == layer,
                AgentMemoryEntry.key == key,
            )
            .first()
        )
        if existing:
            existing.value_jsonb = value
            existing.relevance_score = relevance_score
            existing.last_accessed_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing

        entry = AgentMemoryEntry(
            workspace_id=workspace_id,
            brain_id=brain_id,
            layer=layer,
            key=key,
            value_jsonb=value,
            relevance_score=relevance_score,
            last_accessed_at=datetime.utcnow(),
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    @staticmethod
    def get_memory(
        db: Session,
        workspace_id: int,
        layer: str,
        key: str,
    ) -> Optional[AgentMemoryEntry]:
        entry = (
            db.query(AgentMemoryEntry)
            .filter(
                AgentMemoryEntry.workspace_id == workspace_id,
                AgentMemoryEntry.layer == layer,
                AgentMemoryEntry.key == key,
            )
            .first()
        )
        if entry:
            entry.last_accessed_at = datetime.utcnow()
            db.commit()
        return entry

    @staticmethod
    def list_layer_memories(
        db: Session,
        workspace_id: int,
        layer: str,
        limit: int = 50,
    ) -> List[AgentMemoryEntry]:
        return (
            db.query(AgentMemoryEntry)
            .filter(
                AgentMemoryEntry.workspace_id == workspace_id,
                AgentMemoryEntry.layer == layer,
            )
            .order_by(AgentMemoryEntry.last_accessed_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_founder_rules(db: Session, workspace_id: int) -> List[Dict[str, Any]]:
        """Retrieve L2 Founder Decision Rules to inject into AI Context."""
        entries = (
            db.query(AgentMemoryEntry)
            .filter(
                AgentMemoryEntry.workspace_id == workspace_id,
                AgentMemoryEntry.layer == "L2_FOUNDER",
            )
            .all()
        )
        return [e.value_jsonb for e in entries]

    @staticmethod
    def record_learning(
        db: Session,
        workspace_id: int,
        domain: str,
        takeaway: Dict[str, Any],
    ) -> AgentMemoryEntry:
        """Record an operational learning or pattern into L4 Learning Memory."""
        key = f"{domain}.learning.{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        return FiveLayerMemoryManager.store_memory(
            db=db,
            workspace_id=workspace_id,
            layer="L4_LEARNING",
            key=key,
            value=takeaway,
        )

