import logging
import time
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger("mcosa.agent_memory.health")

HEALTHY = "HEALTHY"
DEGRADED = "DEGRADED"
UNAVAILABLE = "UNAVAILABLE"
REBUILDING = "REBUILDING"


@dataclass
class AgentMemoryHealth:
    status: str
    latency_ms: Optional[float]
    backend: str
    last_error: Optional[str] = None


async def check_sidecar_health(
    base_url: str = "http://127.0.0.1:8765", timeout_seconds: float = 2.0
) -> AgentMemoryHealth:
    """mCOSA V12.3 §180 - health check for the local memory sidecar.

    Never raises - an unreachable sidecar is a normal, expected state (spec
    §181 graceful degradation: mCOSA "must continue operating without Agent
    Memory"), not an error condition for the caller.
    """
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=timeout_seconds) as client:
            response = await client.get("/v1/health")
            latency_ms = (time.monotonic() - start) * 1000
            if response.status_code == 200:
                return AgentMemoryHealth(status=HEALTHY, latency_ms=latency_ms, backend="tencentdb_agent_memory")
            return AgentMemoryHealth(
                status=DEGRADED,
                latency_ms=latency_ms,
                backend="tencentdb_agent_memory",
                last_error=f"HTTP {response.status_code}",
            )
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        logger.info("Agent Memory sidecar unreachable: %s", exc)
        return AgentMemoryHealth(
            status=UNAVAILABLE, latency_ms=None, backend="tencentdb_agent_memory", last_error=str(exc)
        )
