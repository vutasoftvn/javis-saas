"""ResourceConnector Protocol and Implementations for the Capability Gateway.

Connectors provide standardized observe, simulate, and execute interfaces for external
and internal resources (e.g., n8n workflows, CRM endpoints, sandbox executors).
"""

from datetime import datetime, timezone
import hashlib
import json
import logging
from typing import Any, Dict, Optional, Protocol, runtime_checkable

from sqlalchemy.orm import Session

from app.core.snowflake import generate_snowflake_id

logger = logging.getLogger(__name__)


@runtime_checkable
class ResourceConnector(Protocol):
    """Protocol defining observe, simulate, and execute capabilities for resources."""

    async def observe(
        self,
        db: Session,
        workspace_id: int,
        resource_type: str,
        resource_id: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Read resource state or metadata without side effects."""
        ...

    async def simulate(
        self,
        db: Session,
        workspace_id: int,
        capability: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Simulate execution outcome, returning dry-run preview and affected entities."""
        ...

    async def execute(
        self,
        db: Session,
        workspace_id: int,
        capability: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute the capability against the resource with side effects."""
        ...


class N8nResourceConnector:
    """ResourceConnector wrapper around the n8n automation adapter."""

    def __init__(self, adapter: Optional[Any] = None) -> None:
        self._adapter = adapter

    @property
    def adapter(self) -> Any:
        if self._adapter is None:
            from app.automations.runtime.adapters.n8n import N8nAdapter
            self._adapter = N8nAdapter()
        return self._adapter

    async def observe(
        self,
        db: Session,
        workspace_id: int,
        resource_type: str,
        resource_id: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if resource_id:
            status = await self.adapter.get_status(resource_id)
            return {
                "resource_type": resource_type,
                "resource_id": resource_id,
                "status": status.status,
                "details": status.output_payload,
            }
        health = await self.adapter.health()
        return {
            "resource_type": "n8n_instance",
            "status": health.status,
            "details": health.details,
        }

    async def simulate(
        self,
        db: Session,
        workspace_id: int,
        capability: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Preview side-effects without dispatching network call to n8n webhook."""
        params = params or {}
        automation_key = resource_id or params.get("automation_key") or capability
        payload_summary = {k: v for k, v in params.items() if k not in ("secret", "token", "password")}

        param_str = json.dumps(params, sort_keys=True)
        content_hash = hashlib.sha256(param_str.encode("utf-8")).hexdigest()

        return {
            "capability": capability,
            "resource_type": resource_type,
            "resource_id": automation_key,
            "target_webhook": f"/webhook/cosa/{automation_key}",
            "payload_summary": payload_summary,
            "param_count": len(params),
            "content_hash": content_hash,
            "estimated_side_effects": [
                f"External webhook trigger on n8n for '{automation_key}'",
                "Potential downstream CRM, notification, or database updates",
            ],
            "simulated_at": datetime.now(timezone.utc).isoformat(),
            "simulation_status": "ready_for_review",
        }

    async def execute(
        self,
        db: Session,
        workspace_id: int,
        capability: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        from app.automations.runtime.types import AutomationRequest

        params = params or {}
        automation_key = resource_id or params.get("automation_key") or capability
        execution_id = generate_snowflake_id()
        now_iso = datetime.now(timezone.utc).isoformat()

        req = AutomationRequest(
            automation_key=automation_key,
            execution_id=str(execution_id),
            workspace_id=workspace_id,
            company_id=workspace_id,
            payload=params,
            idempotency_key=idempotency_key or f"cap_n8n_{execution_id}",
            requested_at=now_iso,
        )

        result = await self.adapter.execute(req)
        return {
            "execution_id": str(execution_id),
            "provider_execution_id": result.provider_execution_id,
            "status": result.status,
            "error": result.error,
            "executed_at": now_iso,
        }


# Connector Registry
_CONNECTORS: Dict[str, ResourceConnector] = {}


def get_connector(key: str) -> Optional[ResourceConnector]:
    if not _CONNECTORS:
        _CONNECTORS["n8n"] = N8nResourceConnector()
        _CONNECTORS["automation"] = _CONNECTORS["n8n"]
    return _CONNECTORS.get(key)


def register_connector(key: str, connector: ResourceConnector) -> None:
    _CONNECTORS[key] = connector
