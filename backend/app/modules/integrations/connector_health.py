import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def check_connector_health(connector_config: Dict[str, Any]) -> bool:
    """
    Check if a connector is healthy and reachable.
    In MVP, this just returns True.
    """
    logger.info(f"Checking health for connector: {connector_config.get('name', 'Unknown')}")
    # TODO: Implement actual health check (e.g. pinging the MCP server)
    return True
