from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from core.feature_flags import FLAG_AGENT_MEMORY_V12_3, is_enabled
from workforce.memory.adapters.null_adapter import NullAgentMemoryAdapter
from workforce.memory.adapters.tencentdb_adapter import TencentDBAgentMemoryAdapter
from workforce.memory.gateway import AgentMemoryGateway
from workforce.memory.models import AgentMemoryEntry

_null_adapter = NullAgentMemoryAdapter()

# G3 Phase 1E: hard ceiling regardless of what a caller requests - a query
# must never be able to dump the whole table by passing an absurd limit.
MAX_MEMORY_RESULTS = 200


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
        domain: Optional[str] = None,
        provenance: Optional[Dict[str, Any]] = None,
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
            if domain is not None:
                existing.domain = domain
            if provenance is not None:
                existing.provenance_jsonb = provenance
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
            domain=domain,
            provenance_jsonb=provenance,
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
        """G3 Phase 1E: ranked by `relevance_score` first, recency as
        tiebreaker - `relevance_score` already existed on every row (default
        1.0) but was never read by any query, so this was a silent no-op
        column. `limit` is always clamped to MAX_MEMORY_RESULTS regardless of
        what the caller requests - no query here can ever dump the table."""
        capped_limit = max(1, min(limit, MAX_MEMORY_RESULTS))
        return (
            db.query(AgentMemoryEntry)
            .filter(
                AgentMemoryEntry.workspace_id == workspace_id,
                AgentMemoryEntry.layer == layer,
            )
            .order_by(AgentMemoryEntry.relevance_score.desc(), AgentMemoryEntry.last_accessed_at.desc())
            .limit(capped_limit)
            .all()
        )

    @staticmethod
    def get_founder_rules(
        db: Session,
        workspace_id: int,
        limit: int = MAX_MEMORY_RESULTS,
    ) -> List[Dict[str, Any]]:
        """Retrieve L2 Founder Decision Rules to inject into AI Context.

        G3 Phase 1E: used to run with no `LIMIT` at all - a workspace with
        many founder rules would inject its entire table into every AI
        context. Now ranked/budgeted like list_layer_memories()."""
        return [e.value_jsonb for e in FiveLayerMemoryManager.list_layer_memories(db, workspace_id, "L2_FOUNDER", limit=limit)]

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

