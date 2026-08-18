import logging
from typing import List, Dict, Any

from app.platform.vault.retrieval_service import hybrid_search

logger = logging.getLogger(__name__)

async def get_grounding_context(workspace_id: int, brain_id: int, query: str) -> str:
    """
    Tìm kiếm tài liệu từ Vault (thông qua retrieval_service) để đưa vào context cho chatbot.
    """
    logger.info(f"Retrieving grounding context for workspace {workspace_id}, query: {query}")
    try:
        results = await hybrid_search(workspace_id, brain_id, query, top_k=3)
        if not results:
            return ""
            
        context_parts = []
        for i, res in enumerate(results):
            # res is expected to be a dict with text and score
            text = res.get("text", "")
            context_parts.append(f"[{i+1}] {text}")
            
        return "\n\n".join(context_parts)
    except Exception as e:
        logger.error(f"Error getting grounding context: {e}")
        return ""
