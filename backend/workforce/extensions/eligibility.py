from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from core.tool_registry import FLAT_NAME_PATTERN
from integrations.channels.models import WorkspaceSecret
from workforce.agents.runtime.execution_scope import ExecutionScope
from workforce.extensions.models import ExtensionRegistration
from workforce.extensions.seams import DiscoveredCapability

_GOVERNANCE_FIELDS = ("risk_level", "permission_level", "requires_approval", "mutating", "external")


class EligibleCapability(BaseModel):
    extension_id: str
    capability_id: str
    name: str
    input_schema: dict | None = None
    output_schema: dict | None = None
    required_secret_refs: tuple[str, ...] = ()
    eligible: bool
    reason_code: str | None = None
    risk_level: str | None = None
    permission_level: str | None = None
    requires_approval: bool | None = None
    mutating: bool | None = None
    external: bool | None = None


def resolve_eligible_capabilities(db: Session, scope: ExecutionScope) -> tuple[EligibleCapability, ...]:
    registrations = db.query(ExtensionRegistration).filter_by(workspace_id=scope.workspace_id).all()
    results = []

    for registration in registrations:
        capabilities = _discovered_capabilities(registration)
        if not capabilities or registration.status != "enabled" or not _is_healthy(registration):
            continue

        manifest = registration.manifest_jsonb
        required_secret_refs = tuple(manifest.get("required_secret_refs", ()))
        scope_level = _scope_level(scope)
        supported_scopes = manifest.get("supported_scope_levels", ())
        scope_supported = scope_level in supported_scopes
        secrets_available = not required_secret_refs or _secrets_are_available(
            db, scope.workspace_id, required_secret_refs
        )

        for capability in capabilities:
            governance = _governance_metadata(manifest, capability.capability_id)
            if governance is None:
                results.append(_eligible_capability(
                    registration, capability, required_secret_refs, None, False, "GOVERNANCE_METADATA_UNAVAILABLE"
                ))
            elif not scope_supported:
                results.append(_eligible_capability(
                    registration, capability, required_secret_refs, governance, False, "SCOPE_MISMATCH"
                ))
            elif not secrets_available:
                results.append(_eligible_capability(
                    registration, capability, required_secret_refs, governance, False, "SECRET_UNAVAILABLE"
                ))
            else:
                results.append(_eligible_capability(
                    registration, capability, required_secret_refs, governance, True
                ))

    return tuple(results)


def _governance_metadata(manifest: dict, capability_id: str) -> dict | None:
    """Governance metadata is trusted only from the validated first-party manifest,
    never from the discovered snapshot - a manifest entry missing any required field
    fails closed rather than falling back to a permissive default."""
    for entry in manifest.get("capabilities", ()):
        if isinstance(entry, dict) and entry.get("id") == capability_id:
            if all(field in entry for field in _GOVERNANCE_FIELDS):
                return {field: entry[field] for field in _GOVERNANCE_FIELDS}
            return None
    return None


def _discovered_capabilities(registration: ExtensionRegistration) -> tuple[DiscoveredCapability, ...]:
    snapshot = registration.capabilities_jsonb
    if not isinstance(snapshot, dict):
        return ()

    endpoint_config = snapshot.get("endpoint_config")
    if not isinstance(endpoint_config, dict) or not endpoint_config.get("endpoint"):
        # No trusted transport recorded for this snapshot - fail closed rather than
        # dispatching a tool call with nowhere safe to send it.
        return ()

    records = snapshot.get("capabilities")
    if not isinstance(records, list):
        return ()

    capabilities = []
    for record in records:
        try:
            capability = DiscoveredCapability.model_validate(record)
        except (TypeError, ValidationError):
            # One malformed record invalidates the whole snapshot rather than
            # silently dropping just the bad entry - a snapshot that failed to
            # write atomically should not be trusted piecemeal.
            return ()
        if not FLAT_NAME_PATTERN.match(capability.name):
            return ()
        if not isinstance(capability.endpoint_config, dict) or not capability.endpoint_config.get("endpoint"):
            # No trusted transport recorded for this specific capability - the
            # provider dispatch path reads capability.endpoint_config directly.
            return ()
        capabilities.append(capability)
    return tuple(capabilities)


def _is_healthy(registration: ExtensionRegistration) -> bool:
    return isinstance(registration.health_jsonb, dict) and registration.health_jsonb.get("status") == "ok"


def _scope_level(scope: ExecutionScope) -> str:
    if scope.initiative_id is not None:
        return "initiative"
    if scope.offering_id is not None:
        return "offering"
    if scope.operating_unit_id is not None:
        return "operating_unit"
    return "company"


def _secrets_are_available(db: Session, workspace_id: int, required_secret_refs: tuple[str, ...]) -> bool:
    existing_secrets = db.query(WorkspaceSecret.key).filter(
        WorkspaceSecret.workspace_id == workspace_id,
        WorkspaceSecret.key.in_(required_secret_refs),
    ).all()
    existing_keys = {secret[0] for secret in existing_secrets}
    return set(required_secret_refs).issubset(existing_keys)


def _eligible_capability(
    registration: ExtensionRegistration,
    capability: DiscoveredCapability,
    required_secret_refs: tuple[str, ...],
    governance: dict | None,
    eligible: bool,
    reason_code: str | None = None,
) -> EligibleCapability:
    governance = governance or {}
    return EligibleCapability(
        extension_id=registration.extension_id,
        capability_id=capability.capability_id,
        name=capability.name,
        input_schema=capability.input_schema,
        output_schema=capability.output_schema,
        required_secret_refs=required_secret_refs,
        eligible=eligible,
        reason_code=reason_code,
        risk_level=governance.get("risk_level"),
        permission_level=governance.get("permission_level"),
        requires_approval=governance.get("requires_approval"),
        mutating=governance.get("mutating"),
        external=governance.get("external"),
    )
