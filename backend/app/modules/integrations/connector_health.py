import logging
from typing import Dict, Any
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

async def check_connector_health(connector_config: Dict[str, Any]) -> bool:
    """
    Check whether an explicitly configured HTTPS health endpoint is reachable.
    """
    logger.info(f"Checking health for connector: {connector_config.get('name', 'Unknown')}")
    endpoint = connector_config.get("health_url") or connector_config.get("url")
    if not isinstance(endpoint, str):
        return False
    parsed = urlparse(endpoint)
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
            response = await client.get(endpoint)
        return 200 <= response.status_code < 300
    except httpx.HTTPError as exc:
        logger.warning("Connector health check failed for %s: %s", connector_config.get("name", "Unknown"), exc)
        return False
