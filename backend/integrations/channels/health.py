import logging
import asyncio
import ipaddress
import socket
from typing import Dict, Any
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)


async def _resolves_to_public_address(hostname: str) -> bool:
    """Reject endpoints that resolve to loopback or private network space."""
    try:
        addresses = await asyncio.to_thread(socket.getaddrinfo, hostname, 443, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return False
    return bool(addresses) and all(
        ipaddress.ip_address(address[4][0]).is_global
        for address in addresses
    )

async def check_connector_health(connector_config: Dict[str, Any]) -> bool:
    """
    Check whether an explicitly configured HTTPS health endpoint is reachable.
    """
    logger.info(f"Checking health for connector: {connector_config.get('name', 'Unknown')}")
    endpoint = connector_config.get("health_url") or connector_config.get("url")
    if not isinstance(endpoint, str):
        return False
    parsed = urlparse(endpoint)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return False
    if not await _resolves_to_public_address(parsed.hostname):
        logger.warning("Connector health check rejected non-public endpoint for %s", connector_config.get("name", "Unknown"))
        return False
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
            response = await client.get(endpoint)
        return 200 <= response.status_code < 300
    except httpx.HTTPError as exc:
        logger.warning("Connector health check failed for %s: %s", connector_config.get("name", "Unknown"), exc)
        return False
