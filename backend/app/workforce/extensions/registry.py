from sqlalchemy.orm import Session
from app.workforce.extensions.models import ExtensionRegistration
from app.workforce.extensions.manifest import ExtensionManifest, ManifestValidationError
from app.workforce.extensions.seams import DiscoveredCapability
from pydantic import ValidationError

class ExtensionRegistry:
    def install(self, db: Session, workspace_id: int, manifest: dict) -> ExtensionRegistration:
        try:
            validated = ExtensionManifest(**manifest)
        except ValidationError as e:
            raise ManifestValidationError(str(e))

        registration = db.query(ExtensionRegistration).filter_by(
            workspace_id=workspace_id, extension_id=validated.extension_id
        ).first()

        if registration:
            manifest_changed = (
                registration.version != validated.version
                or registration.manifest_jsonb.get("provider_config") != validated.provider_config.model_dump()
            )
            registration.version = validated.version
            registration.manifest_jsonb = validated.model_dump()
            if manifest_changed:
                registration.capabilities_jsonb = None
            registration.status = "installed"
        else:
            registration = ExtensionRegistration(
                workspace_id=workspace_id,
                extension_id=validated.extension_id,
                version=validated.version,
                status="installed",
                manifest_jsonb=validated.model_dump(),
                capabilities_jsonb=None,
                health_jsonb={}
            )
            db.add(registration)

        db.commit()
        db.refresh(registration)
        return registration

    def get(self, db: Session, workspace_id: int, extension_id: str) -> ExtensionRegistration | None:
        return db.query(ExtensionRegistration).filter_by(
            workspace_id=workspace_id, extension_id=extension_id
        ).first()

    def get_all(self, db: Session, workspace_id: int) -> list[ExtensionRegistration]:
        return db.query(ExtensionRegistration).filter_by(workspace_id=workspace_id).all()

    def enable(self, db: Session, workspace_id: int, extension_id: str) -> ExtensionRegistration:
        registration = self.get(db, workspace_id, extension_id)
        if registration is None:
            raise LookupError(f"Extension registration not found: {extension_id}")

        registration.status = "enabled"
        registration.disabled_reason = None
        db.commit()
        db.refresh(registration)
        return registration

    def record_discovery(
        self,
        db: Session,
        workspace_id: int,
        extension_id: str,
        capabilities: list[DiscoveredCapability] | tuple[DiscoveredCapability, ...],
    ) -> ExtensionRegistration:
        registration = self.get(db, workspace_id, extension_id)
        if registration is None:
            raise LookupError(f"Extension registration not found: {extension_id}")

        registration.capabilities_jsonb = {
            "capabilities": [capability.model_dump(mode="json") for capability in capabilities]
        }
        registration.status = "enabled"
        registration.disabled_reason = None
        registration.health_jsonb = {"status": "ok"}
        db.commit()
        db.refresh(registration)
        return registration

    def record_discovery_failure(
        self,
        db: Session,
        workspace_id: int,
        extension_id: str,
    ) -> ExtensionRegistration:
        registration = self.get(db, workspace_id, extension_id)
        if registration is None:
            raise LookupError(f"Extension registration not found: {extension_id}")

        registration.health_jsonb = {"status": "unavailable"}
        db.commit()
        db.refresh(registration)
        return registration

    def get_capability(
        self,
        db: Session,
        workspace_id: int,
        capability_id: str,
    ) -> DiscoveredCapability | None:
        registrations = db.query(ExtensionRegistration).filter_by(
            workspace_id=workspace_id,
            status="enabled",
        ).all()
        for registration in registrations:
            snapshot = registration.capabilities_jsonb or {}
            if not isinstance(snapshot, dict):
                continue
            capability_records = snapshot.get("capabilities", [])
            if not isinstance(capability_records, list):
                continue
            for capability_data in capability_records:
                try:
                    capability = DiscoveredCapability.model_validate(capability_data)
                except (TypeError, ValidationError):
                    continue
                if capability.capability_id == capability_id:
                    return capability
        return None

    def disable(self, db: Session, workspace_id: int, extension_id: str, reason: str):
        registration = self.get(db, workspace_id, extension_id)
        if registration:
            registration.status = "disabled"
            registration.disabled_reason = reason
            db.commit()
            db.refresh(registration)
        return registration
