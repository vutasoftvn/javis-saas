"""Capability Gateway service: single chokepoint for capability authorization,
policy evaluation, dry-run simulation, execution, and observation logging.
"""

from datetime import datetime, timezone
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from cosa_core.capabilities.connector import get_connector
from cosa_core.capabilities.models import CapabilityGrant
from cosa_core.capabilities.registry import (
    CapabilityDefinition,
    RiskLevel,
    get_capability_definition,
)
from workforce.agents.governance.approval_service import ApprovalService
from workforce.agents.governance.models import AgentApproval, AgentToolCall
from workforce.agents.governance.policy_engine import (
    PermissionLevel,
    PolicyAction,
    PolicyEngine,
    PolicyDecision,
)
from core.snowflake import generate_snowflake_id
from core.tool_registry import ToolSpec
from founder_os.strategy.models import CapabilityDefinition as CanonicalCapabilityDefinition

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def resolve_capability_definition(db: Session, capability: str) -> Optional[CapabilityDefinition]:
    """G3 Phase 1B: the canonical `capability_definitions` table (admin-
    editable, seeded from CAPABILITY_CATALOG at startup) is now the source
    of truth for explicitly-registered capabilities. Falls back to
    registry.py's dynamic domain-primitive classifier (e.g. "sales.research",
    "*.read", "n8n.*") for capability strings that were never seeded — that
    classifier is live runtime behavior, not duplicated data, and stays in
    registry.py rather than being ported into the DB.
    """
    row = (
        db.query(CanonicalCapabilityDefinition)
        .filter(
            CanonicalCapabilityDefinition.capability_key == capability,
            CanonicalCapabilityDefinition.source == "runtime_registry",
            CanonicalCapabilityDefinition.workspace_id.is_(None),
        )
        .first()
    )
    if row is not None and row.metadata_jsonb:
        meta = row.metadata_jsonb
        try:
            risk_level = RiskLevel(meta["original_risk_level"])
            permission_level = PermissionLevel(meta["permission_level"])
        except (KeyError, ValueError):
            return get_capability_definition(capability)
        return CapabilityDefinition(
            name=row.capability_key,
            domain=meta.get("original_domain", row.domain),
            resource=meta.get("resource", ""),
            action=meta.get("action", ""),
            risk_level=risk_level,
            permission_level=permission_level,
            requires_approval=row.requires_approval,
            is_strong_approval=row.professional_review_required,
            description=row.description or "",
        )
    return get_capability_definition(capability)


class CapabilityCheckResult(BaseModel):
    allowed: bool
    action: str  # "allow", "deny", "require_approval"
    risk_level: str
    permission_level: str
    capability: str
    reason: Optional[str] = None
    grant_id: Optional[str] = None
    is_strong_approval: bool = False
    simulation: Optional[Dict[str, Any]] = None


class CapabilityGateway:
    """Central gateway for capability checking, simulation, grants, and observation."""

    @classmethod
    async def check(
        cls,
        db: Session,
        workspace_id: int,
        subject_type: str,
        subject_id: str,
        capability: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        permission_profile: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        company_id: Optional[int] = None,
    ) -> CapabilityCheckResult:
        """Evaluate capability authorization, policy rules, and simulate side-effects if needed."""
        now = utc_now()

        # 1. Lookup registered capability definition (canonical DB, G3 Phase 1B)
        definition = resolve_capability_definition(db, capability)

        # 2. Lookup active database grant for subject
        active_grant = (
            db.query(CapabilityGrant)
            .filter(
                CapabilityGrant.workspace_id == workspace_id,
                CapabilityGrant.subject_type == subject_type,
                CapabilityGrant.subject_id == subject_id,
                CapabilityGrant.capability.in_([capability, "*"]),
                CapabilityGrant.revoked_at.is_(None),
                (CapabilityGrant.expires_at.is_(None) | (CapabilityGrant.expires_at > now)),
            )
            .order_by(CapabilityGrant.created_at.desc())
            .first()
        )

        grant_id_str = str(active_grant.id) if active_grant else None

        # 3. Default deny if unregistered and no grant exists
        if not definition and not active_grant:
            return CapabilityCheckResult(
                allowed=False,
                action=PolicyAction.DENY.value,
                risk_level="unknown",
                permission_level="none",
                capability=capability,
                reason=f"Capability '{capability}' is unregistered and has no active grant (Default Deny).",
            )

        # 4. Determine base parameters from definition or fallback from grant
        risk_level_str = definition.risk_level.value if definition else "L3"
        perm_level = definition.permission_level if definition else PermissionLevel.L3_EXECUTE

        if definition:
            if definition.risk_level in (RiskLevel.L0_PUBLIC_READ, RiskLevel.L1_INTERNAL_READ):
                perm_str = "read_only"
                risk_str = "low"
            elif definition.risk_level == RiskLevel.L2_DRAFT_WRITE:
                perm_str = "scoped_write"
                risk_str = "low"
            elif definition.risk_level == RiskLevel.L3_OPERATIONAL_WRITE:
                perm_str = "scoped_write"
                risk_str = "medium"
            elif definition.risk_level == RiskLevel.L4_EXTERNAL_SIDE_EFFECT:
                perm_str = "scoped_write"
                risk_str = "high"
            else:  # L5
                perm_str = "scoped_write"
                risk_str = "critical"
            requires_approval = definition.requires_approval
            is_strong_approval = definition.is_strong_approval
        else:
            perm_str = "scoped_write"
            risk_str = "medium"
            requires_approval = False
            is_strong_approval = False

        # 5. Policy Engine evaluation
        tool_spec = ToolSpec(
            namespace=definition.domain if definition else "custom",
            name=capability,
            callable=lambda: None,
            permission_level=perm_str,
            risk_level=risk_str,
            requires_approval=requires_approval,
        )

        profile_to_use = permission_profile or (
            "l3_execute" if not requires_approval else "l3a_execute_with_approval"
        )

        evaluation: PolicyDecision = PolicyEngine.evaluate(
            agent_key=subject_id,
            tool_spec=tool_spec,
            permission_profile=profile_to_use,
            input_data=params,
        )

        # 6. Enforce INV-10: L5 capabilities cannot bypass approval
        effective_action = evaluation.action.value
        if is_strong_approval:
            effective_action = PolicyAction.REQUIRE_APPROVAL.value

        # 7. Simulate side effects if approval is required
        simulation_data = None
        if effective_action == PolicyAction.REQUIRE_APPROVAL.value:
            connector = get_connector(definition.domain if definition else "") or get_connector("n8n")
            if connector and hasattr(connector, "simulate"):
                try:
                    simulation_data = await connector.simulate(
                        db=db,
                        workspace_id=workspace_id,
                        capability=capability,
                        resource_type=resource_type or (definition.resource if definition else "generic"),
                        resource_id=resource_id,
                        params=params,
                    )
                except Exception as exc:
                    logger.warning(f"Dry-run simulation failed for capability {capability}: {exc}")
                    simulation_data = {"simulation_error": str(exc)}
            else:
                # Default generic simulation
                param_hash = hashlib.sha256(json.dumps(params or {}, sort_keys=True).encode()).hexdigest()
                simulation_data = {
                    "capability": capability,
                    "resource_type": resource_type or (definition.resource if definition else "generic"),
                    "resource_id": resource_id,
                    "content_hash": param_hash,
                    "simulated_at": now.isoformat(),
                    "params_preview": params,
                }

        is_allowed = effective_action == PolicyAction.ALLOW.value

        return CapabilityCheckResult(
            allowed=is_allowed,
            action=effective_action,
            risk_level=risk_level_str,
            permission_level=perm_level.value,
            capability=capability,
            reason=evaluation.reason,
            grant_id=grant_id_str,
            is_strong_approval=is_strong_approval,
            simulation=simulation_data,
        )

    @classmethod
    def grant(
        cls,
        db: Session,
        workspace_id: int,
        subject_type: str,
        subject_id: str,
        capability: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        scope: Optional[Dict[str, Any]] = None,
        granted_by: Optional[int] = None,
        company_id: Optional[int] = None,
        expires_at: Optional[datetime] = None,
        notes: Optional[str] = None,
    ) -> CapabilityGrant:
        """Create a new capability authorization grant."""
        grant_record = CapabilityGrant(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            company_id=company_id or workspace_id,
            subject_type=subject_type,
            subject_id=subject_id,
            capability=capability,
            resource_type=resource_type,
            resource_id=resource_id,
            scope_jsonb=scope or {},
            granted_by=granted_by,
            created_at=utc_now(),
            expires_at=expires_at,
            notes=notes,
        )
        db.add(grant_record)
        db.commit()
        db.refresh(grant_record)
        return grant_record

    @classmethod
    def revoke(
        cls,
        db: Session,
        workspace_id: int,
        grant_id: int,
        user_id: Optional[int] = None,
    ) -> Optional[CapabilityGrant]:
        """Revoke an active capability grant."""
        grant = (
            db.query(CapabilityGrant)
            .filter(
                CapabilityGrant.id == grant_id,
                CapabilityGrant.workspace_id == workspace_id,
            )
            .first()
        )
        if not grant:
            return None

        grant.revoked_at = utc_now()
        db.commit()
        db.refresh(grant)
        return grant

    @classmethod
    def list_grants(
        cls,
        db: Session,
        workspace_id: int,
        subject_id: Optional[str] = None,
        active_only: bool = True,
    ) -> List[CapabilityGrant]:
        """List capability grants within a workspace."""
        query = db.query(CapabilityGrant).filter(CapabilityGrant.workspace_id == workspace_id)
        if subject_id:
            query = query.filter(CapabilityGrant.subject_id == subject_id)
        if active_only:
            now = utc_now()
            query = query.filter(
                CapabilityGrant.revoked_at.is_(None),
                (CapabilityGrant.expires_at.is_(None) | (CapabilityGrant.expires_at > now)),
            )
        return query.order_by(CapabilityGrant.created_at.desc()).all()

    @classmethod
    def record_observation(
        cls,
        db: Session,
        agent_key: str,
        tool_name: str,
        run_id: Optional[int] = None,
        plan_id: Optional[int] = None,
        step_id: Optional[int] = None,
        status: str = "success",
        capability: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        approval_id: Optional[int] = None,
        latency_ms: Optional[int] = None,
        provenance: Optional[Dict[str, Any]] = None,
    ) -> AgentToolCall:
        """Record an observation tool call record with content hash and provenance."""
        now = utc_now()
        param_str = json.dumps(input_data or {}, sort_keys=True)
        content_hash = hashlib.sha256(param_str.encode("utf-8")).hexdigest()

        tool_call = AgentToolCall(
            id=generate_snowflake_id(),
            run_id=run_id,
            plan_id=plan_id,
            step_id=step_id,
            agent_key=agent_key,
            tool_name=tool_name,
            capability=capability,
            resource_type=resource_type,
            resource_id=resource_id,
            input_jsonb=input_data,
            output_jsonb=output_data,
            content_hash=content_hash,
            provenance_jsonb=provenance or {},
            status=status,
            approval_id=approval_id,
            started_at=now,
            finished_at=now,
            latency_ms=latency_ms,
        )
        db.add(tool_call)
        db.commit()
        db.refresh(tool_call)
        return tool_call

    @classmethod
    async def execute_with_capability(
        cls,
        db: Session,
        workspace_id: int,
        subject_type: str,
        subject_id: str,
        capability: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
        approval_id: Optional[int] = None,
        run_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute action with end-to-end authorization, idempotency, and observation logging."""
        now = utc_now()

        # INV-06: Idempotency verification
        if idempotency_key:
            existing_approval = ApprovalService.get_by_idempotency_key(db, workspace_id, idempotency_key)
            if existing_approval and existing_approval.status == "executed":
                return {
                    "idempotent_hit": True,
                    "status": "executed",
                    "execution_result": existing_approval.execution_result_jsonb,
                    "approval_id": str(existing_approval.id),
                }

        # INV-05: Re-validate capability authorization at execute time
        check_result = await cls.check(
            db=db,
            workspace_id=workspace_id,
            subject_type=subject_type,
            subject_id=subject_id,
            capability=capability,
            resource_type=resource_type,
            resource_id=resource_id,
            params=params,
        )

        if not check_result.allowed:
            # If requires approval, check if valid approval is already approved
            if check_result.action == PolicyAction.REQUIRE_APPROVAL.value:
                approval = None
                if approval_id:
                    approval = ApprovalService.get_approval(db, workspace_id, approval_id)
                elif idempotency_key:
                    approval = ApprovalService.get_by_idempotency_key(db, workspace_id, idempotency_key)

                if not approval or approval.status not in ("approved", "executed"):
                    # Create approval request if none exists
                    if not approval:
                        approval = ApprovalService.create_approval(
                            db=db,
                            workspace_id=workspace_id,
                            agent_key=subject_id,
                            action_type=capability,
                            tool_name=capability,
                            input_preview=params,
                            risk_level=check_result.risk_level,
                            run_id=run_id,
                            capability=capability,
                            resource_type=resource_type,
                            resource_id=resource_id,
                            simulation_result=check_result.simulation,
                            idempotency_key=idempotency_key,
                            is_strong_approval=check_result.is_strong_approval,
                        )
                    return {
                        "status": "awaiting_approval",
                        "approval_id": str(approval.id),
                        "capability": capability,
                        "simulation": check_result.simulation,
                    }
            else:
                return {
                    "status": "denied",
                    "reason": check_result.reason or "Capability authorization denied",
                }

        # Execute via connector if available
        definition = resolve_capability_definition(db, capability)
        domain_key = definition.domain if definition else "generic"
        connector = get_connector(domain_key) or get_connector("n8n")

        execution_output: Dict[str, Any] = {}
        if connector and hasattr(connector, "execute"):
            execution_output = await connector.execute(
                db=db,
                workspace_id=workspace_id,
                capability=capability,
                resource_type=resource_type or "generic",
                resource_id=resource_id,
                params=params,
                idempotency_key=idempotency_key,
            )
        else:
            execution_output = {
                "status": "completed",
                "capability": capability,
                "executed_at": now.isoformat(),
                "details": f"Direct capability execution completed for {capability}",
            }

        # Update approval record status if executing post-approval
        if approval_id:
            ApprovalService.approve(
                db=db,
                workspace_id=workspace_id,
                approval_id=approval_id,
                reviewed_by=user_id or 1,
                execution_result=execution_output,
            )

        # INV-09: Record observation
        if run_id:
            cls.record_observation(
                db=db,
                run_id=run_id,
                agent_key=subject_id,
                tool_name=capability,
                status="success" if execution_output.get("status") != "failed" else "failed",
                capability=capability,
                resource_type=resource_type,
                resource_id=resource_id,
                input_data=params,
                output_data=execution_output,
                approval_id=approval_id,
            )

        return execution_output
