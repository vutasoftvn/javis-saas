from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.workforce.extensions.models import ExtensionRegistration
from app.workforce.agents.runtime.execution_scope import ExecutionScope
from app.integrations.channels.models import WorkspaceSecret

class EligibleCapability(BaseModel):
    capability_id: str
    name: str
    eligible: bool
    reason_code: str | None = None

def resolve_eligible_capabilities(db: Session, scope: ExecutionScope) -> tuple[EligibleCapability, ...]:
    registrations = db.query(ExtensionRegistration).filter_by(workspace_id=scope.workspace_id).all()
    results = []
    
    for reg in registrations:
        if reg.status in ("disabled", "unhealthy"):
            continue
            
        manifest = reg.manifest_jsonb
        capabilities = manifest.get("capabilities", [])

        # 2. Scope level
        supported_scopes = manifest.get("supported_scope_levels", [])
        
        scope_level = "company"
        if scope.initiative_id is not None:
            scope_level = "initiative"
        elif scope.offering_id is not None:
            scope_level = "offering"
        elif scope.operating_unit_id is not None:
            scope_level = "operating_unit"
            
        if scope_level not in supported_scopes:
            for cap in capabilities:
                results.append(EligibleCapability(
                    capability_id=cap["id"],
                    name=cap["name"],
                    eligible=False,
                    reason_code="SCOPE_MISMATCH"
                ))
            continue

        # 3. Secret readiness
        required_secrets = manifest.get("required_secret_refs", [])
        if required_secrets:
            existing_secrets = db.query(WorkspaceSecret.key).filter(
                WorkspaceSecret.workspace_id == scope.workspace_id,
                WorkspaceSecret.key.in_(required_secrets)
            ).all()
            existing_keys = {s[0] for s in existing_secrets}
            if not set(required_secrets).issubset(existing_keys):
                for cap in capabilities:
                    results.append(EligibleCapability(
                        capability_id=cap["id"],
                        name=cap["name"],
                        eligible=False,
                        reason_code="SECRET_UNAVAILABLE"
                    ))
                continue

        # Eligible
        for cap in capabilities:
            results.append(EligibleCapability(
                capability_id=cap["id"],
                name=cap["name"],
                eligible=True,
                reason_code=None
            ))

    return tuple(results)
