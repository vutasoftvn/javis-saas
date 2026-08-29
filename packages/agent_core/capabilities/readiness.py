"""Capability Readiness Checking Subsystem.

Theo Hermes/LangGraph Integration Plan §3 (Phase 4, Phase 9 Track 9C):
Tách biệt rõ ràng giữa Technical Readiness (sẵn sàng kỹ thuật) và Governance/Authorization (thẩm quyền).
Readiness kiểm tra trạng thái hoạt động của connector, credentials, network health mà không quyết định quyền truy cập.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable

from agent_core.capabilities.registry import CapabilityRegistry
from agent_core.contracts.capability import (
    CapabilityReadiness,
    CapabilityReadinessReason,
    CapabilitySpec,
)

logger = logging.getLogger(__name__)

__all__ = [
    "CapabilityReadinessChecker",
    "CapabilityReadinessError",
    "RegistryCapabilityReadinessChecker",
]


class CapabilityReadinessError(Exception):
    """Lỗi phát sinh khi capability thiếu credential hoặc backend bị lỗi chặn cứng."""

    def __init__(self, readiness: CapabilityReadiness) -> None:
        self.readiness = readiness
        super().__init__(
            f"Capability '{readiness.capability_id}' is not ready: {readiness.reason_code.value} (details: {readiness.details})"
        )


@runtime_checkable
class CapabilityReadinessChecker(Protocol):
    """Protocol kiểm tra trạng thái sẵn sàng kỹ thuật của capability."""

    async def check(
        self, capability_id: str, run_context: dict[str, Any] | None = None
    ) -> CapabilityReadiness:
        """Kiểm tra technical readiness cho một capability cụ thể."""
        ...


class RegistryCapabilityReadinessChecker:
    """Implementation kiểm tra cấu hình connector trong registry và health check."""

    def __init__(
        self,
        registry: CapabilityRegistry,
        connector_health_override: dict[str, CapabilityReadinessReason] | None = None,
        company_client: Any | None = None,
    ) -> None:
        self._registry = registry
        self._overrides = connector_health_override or {}
        self._company_client = company_client

    async def check(
        self, capability_id: str, run_context: dict[str, Any] | None = None
    ) -> CapabilityReadiness:
        reg = self._registry.get(capability_id)
        if not reg:
            return CapabilityReadiness(
                capability_id=capability_id,
                ready=False,
                reason_code=CapabilityReadinessReason.DEPENDENCY_MISSING,
                details={"error": "Capability not found in registry"},
            )

        spec: CapabilitySpec = reg.spec
        connector_id = spec.connector_requirements.get("connector_id")

        # Kiểm tra override giả lập / health status
        if capability_id in self._overrides:
            reason = self._overrides[capability_id]
            return CapabilityReadiness(
                capability_id=capability_id,
                ready=(reason == CapabilityReadinessReason.READY),
                reason_code=reason,
                connector_ref=connector_id,
                details={"source": "override_table"},
            )

        if connector_id and connector_id in self._overrides:
            reason = self._overrides[connector_id]
            return CapabilityReadiness(
                capability_id=capability_id,
                ready=(reason == CapabilityReadinessReason.READY),
                reason_code=reason,
                connector_ref=connector_id,
                details={"source": "connector_override_table"},
            )

        # Kiểm tra health thực tế qua company_client nếu được cấu hình
        if self._company_client is not None and connector_id in (
            "company_service",
            "company_service_client",
            "commercial",
            "operations",
            "finance",
        ):
            health_fn = getattr(self._company_client, "health_check", None) or getattr(
                self._company_client, "check_health", None
            )
            if callable(health_fn):
                try:
                    healthy = await health_fn()
                    if not healthy:
                        return CapabilityReadiness(
                            capability_id=capability_id,
                            ready=False,
                            reason_code=CapabilityReadinessReason.CONNECTOR_OFFLINE,
                            connector_ref=connector_id,
                            details={"error": "Company service health check reported offline"},
                        )
                except Exception as exc:
                    logger.warning(
                        f"Failed to probe company service health for {capability_id}: {exc}"
                    )
                    return CapabilityReadiness(
                        capability_id=capability_id,
                        ready=False,
                        reason_code=CapabilityReadinessReason.CONNECTOR_OFFLINE,
                        connector_ref=connector_id,
                        details={"error": str(exc)},
                    )

        # Mặc định: Nếu có khai báo connector và có handler -> READY
        return CapabilityReadiness(
            capability_id=capability_id,
            ready=True,
            reason_code=CapabilityReadinessReason.READY,
            connector_ref=connector_id,
        )
