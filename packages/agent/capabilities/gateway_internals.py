from __future__ import annotations

import logging
from typing import Any

from agent.capabilities.idempotency import IdempotencyClaimService, IdempotencyOutcome
from agent.contracts.capability import CapabilitySpec
from agent.contracts.errors import TenancyUnresolvedError
from agent.governance.contracts import ApprovalPolicy, CapabilityRisk

logger = logging.getLogger(__name__)

__all__ = ["IdempotencyCoordinator", "InputValidator", "TenancyVerifier"]


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


class IdempotencyCoordinator:
    """Phối hợp idempotency: claim, cached_completed, in_progress.

    Wraps IdempotencyClaimService.try_claim() nguyên trạng (atomic claim,
    INSERT ... ON CONFLICT DO NOTHING ở tầng repository đảm bảo đúng 1
    worker thắng claim cho mỗi (run_id, capability_id, idempotency_key)).
    Không tự ý retry/chờ — caller tự quyết định dựa trên outcome trả về.
    """

    def __init__(self, idempotency_service: IdempotencyClaimService) -> None:
        self._idempotency = idempotency_service

    async def coordinate(
        self,
        run_id: str,
        tool_call_id: str,
        capability_id: str,
        idempotency_key: str,
        payload_hash: str,
    ) -> tuple[IdempotencyOutcome, Any]:  # (outcome, claim)
        """Attempt idempotency claim. Returns (outcome, claim) or raises."""
        return await self._idempotency.try_claim(
            run_id=run_id,
            tool_call_id=tool_call_id,
            capability_id=capability_id,
            idempotency_key=idempotency_key,
            payload_hash=payload_hash,
        )

    def should_return_cached(self, outcome: IdempotencyOutcome) -> bool:
        """Check if should return cached result."""
        return outcome == IdempotencyOutcome.CACHED_COMPLETED

    def should_return_in_progress(self, outcome: IdempotencyOutcome) -> bool:
        """Check if should return in_progress."""
        return outcome == IdempotencyOutcome.IN_PROGRESS
