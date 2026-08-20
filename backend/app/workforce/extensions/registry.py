from sqlalchemy.orm import Session
from app.workforce.extensions.models import ExtensionRegistration
from app.workforce.extensions.manifest import ExtensionManifest, ManifestValidationError
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
            registration.version = validated.version
            registration.manifest_jsonb = validated.model_dump()
            registration.status = "installed"
        else:
            registration = ExtensionRegistration(
                workspace_id=workspace_id,
                extension_id=validated.extension_id,
                version=validated.version,
                status="installed",
                manifest_jsonb=validated.model_dump(),
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

    def disable(self, db: Session, workspace_id: int, extension_id: str, reason: str):
        registration = self.get(db, workspace_id, extension_id)
        if registration:
            registration.status = "disabled"
            registration.disabled_reason = reason
            db.commit()
            db.refresh(registration)
        return registration
