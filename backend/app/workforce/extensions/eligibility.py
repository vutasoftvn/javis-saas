from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.integrations.channels.models import WorkspaceSecret
from app.workforce.agents.runtime.execution_scope import ExecutionScope
from app.workforce.extensions.models import ExtensionRegistration
from app.workforce.extensions.seams import DiscoveredCapability


class EligibleCapability(BaseModel):
    extension_id: str
    capability_id: str
    name: str
    input_schema: dict | None = None
    output_schema: dict | None = None
    required_secret_refs: tuple[str, ...] = ()
    eligible: bool
    reason_code: str | None = None


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

        if scope_level not in supported_scopes:
            results.extend(
                _eligible_capability(registration, capability, required_secret_refs, False, "SCOPE_MISMATCH")
                for capability in capabilities
            )
            continue

        if required_secret_refs and not _secrets_are_available(db, scope.workspace_id, required_secret_refs):
            results.extend(
                _eligible_capability(registration, capability, required_secret_refs, False, "SECRET_UNAVAILABLE")
                for capability in capabilities
            )
            continue

        results.extend(
            _eligible_capability(registration, capability, required_secret_refs, True)
            for capability in capabilities
        )

    return tuple(results)


def _discovered_capabilities(registration: ExtensionRegistration) -> tuple[DiscoveredCapability, ...]:
    snapshot = registration.capabilities_jsonb
    if not isinstance(snapshot, dict):
        return ()

    records = snapshot.get("capabilities")
    if not isinstance(records, list):
        return ()

    capabilities = []
    for record in records:
        try:
            capabilities.append(DiscoveredCapability.model_validate(record))
        except (TypeError, ValidationError):
            continue
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
    eligible: bool,
    reason_code: str | None = None,
) -> EligibleCapability:
    return EligibleCapability(
        extension_id=registration.extension_id,
        capability_id=capability.capability_id,
        name=capability.name,
        input_schema=capability.input_schema,
        output_schema=capability.output_schema,
        required_secret_refs=required_secret_refs,
        eligible=eligible,
        reason_code=reason_code,
    )
