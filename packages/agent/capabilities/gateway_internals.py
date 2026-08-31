from __future__ import annotations

import logging
from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.contracts.errors import TenancyUnresolvedError
from agent.governance.contracts import ApprovalPolicy, CapabilityRisk

logger = logging.getLogger(__name__)

__all__ = ["InputValidator", "TenancyVerifier"]


class TenancyVerifier:
    """Phụ trách kiểm tra tenancy fail-closed: workspace_id + principal phải hợp lệ
    cho capability có risk cao hoặc approval policy yêu cầu luôn duyệt."""

    def __init__(self, logger_: logging.Logger | None = None) -> None:
        self._logger = logger_ or logger

    async def verify(
        self,
        spec: CapabilitySpec,
        req: Any,  # GatewayExecutionRequest
    ) -> tuple[str, str]:
        """Verify tenancy for capability execution.

        Args:
            spec: CapabilitySpec with risk/approval_policy
            req: GatewayExecutionRequest with workspace_id, principal, context

        Returns:
            Tuple of (resolved_workspace_id, resolved_principal)

        Raises:
            TenancyUnresolvedError: nếu tenancy không đủ cho capability risk.
        """
        needs_tenancy = (
            spec.risk in (CapabilityRisk.HIGH, CapabilityRisk.CRITICAL, CapabilityRisk.MEDIUM)
            or spec.approval_policy == ApprovalPolicy.ALWAYS
        )

        resolved_workspace = req.workspace_id
        resolved_principal: str | None = req.principal

        # Fallback to context nếu req không chỉ định
        if not resolved_workspace:
            if isinstance(req.context, dict):
                resolved_workspace = req.context.get("workspace_id")
            elif hasattr(req.context, "workspace_id"):
                resolved_workspace = req.context.workspace_id
        if not resolved_principal:
            if isinstance(req.context, dict):
                resolved_principal = req.context.get("principal")
            elif hasattr(req.context, "principal"):
                resolved_principal = req.context.principal

        if needs_tenancy and (
            not resolved_workspace
            or str(resolved_workspace).strip() in ("", "default", "default_workspace")
            or not resolved_principal
            or str(resolved_principal).strip() in ("", "default")
        ):
            err_msg = (
                f"Execution of '{req.capability_id}' failed: tenancy unresolved "
                f"(workspace_id={resolved_workspace!r}, principal={resolved_principal!r})"
            )
            raise TenancyUnresolvedError(err_msg, details={"capability": req.capability_id})

        return resolved_workspace or "", resolved_principal or ""


class InputValidator:
    """Kiểm tra input payload khớp với spec schema (delegate cho CapabilityRegistry)."""

    def __init__(self, registry: Any) -> None:  # CapabilityRegistry
        self._registry = registry

    def validate(self, spec: CapabilitySpec, input_payload: dict[str, Any]) -> list[str]:
        """Validate input against spec schema.

        Returns:
            List of error messages (empty = valid).
        """
        return self._registry.validate_input(spec, input_payload)
