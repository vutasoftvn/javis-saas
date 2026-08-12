from sqlalchemy.orm import Session

from app.core.feature_flags import FLAG_AGENT_MEMORY_V12_3, is_enabled
from app.modules.agent_memory.adapters.null_adapter import NullAgentMemoryAdapter
from app.modules.agent_memory.adapters.tencentdb_adapter import TencentDBAgentMemoryAdapter
from app.modules.agent_memory.gateway import AgentMemoryGateway

_null_adapter = NullAgentMemoryAdapter()


def get_gateway(db: Session, workspace_id: int) -> AgentMemoryGateway:
    """Resolve the active AgentMemoryGateway for this workspace (ADR-MEM-001,
    ADR-MEM-002). Returns the null adapter whenever the flag is off - callers
    never need to check the flag themselves, only ask for a gateway and use
    it (every gateway method already degrades gracefully on its own)."""
    if not is_enabled(db, FLAG_AGENT_MEMORY_V12_3, workspace_id):
        return _null_adapter
    return TencentDBAgentMemoryAdapter()
