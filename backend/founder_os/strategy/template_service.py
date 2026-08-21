from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.snowflake import generate_snowflake_id
from core.tenancy import get_workspace_template_scoped
from founder_os.strategy.models import CapabilityDefinition, WorkspaceTemplate, WorkspaceTemplateVersion
from founder_os.strategy.seed_templates import SEED_TEMPLATES, SEED_TEMPLATES_BY_KEY


class TemplateService:
    def __init__(self, db: Session, workspace_id: int, brain_id: int):
        self.db = db
        self.workspace_id = workspace_id
        self.brain_id = brain_id

    def provision_workspace_templates(self) -> list[WorkspaceTemplate]:
        """Copy any seed the workspace does not already have a local template for.

        Idempotent: a workspace that already owns all six seeds gets no new
        rows back on a repeat call.
        """
        existing_keys = {
            row[0]
            for row in self.db.query(WorkspaceTemplate.source_key)
            .filter(WorkspaceTemplate.workspace_id == self.workspace_id)
            .all()
        }

        created: list[WorkspaceTemplate] = []
        for seed in SEED_TEMPLATES:
            if seed["source_key"] in existing_keys:
                continue
            template = WorkspaceTemplate(
                id=generate_snowflake_id(),
                workspace_id=self.workspace_id,
                brain_id=self.brain_id,
                name=seed["name"],
                source_key=seed["source_key"],
                active_version_no=1,
            )
            self.db.add(template)
            self.db.flush()
            self.db.add(WorkspaceTemplateVersion(
                id=generate_snowflake_id(),
                workspace_id=self.workspace_id,
                template_id=template.id,
                version_no=1,
                config_jsonb={"capabilities": seed["capabilities"]},
                source_seed_key=seed["source_key"],
                status="ACTIVE",
            ))
            self._sync_capability_definitions(seed)
            created.append(template)

        self.db.commit()
        return created

    def _sync_capability_definitions(self, seed: dict) -> None:
        existing_keys = {
            row[0]
            for row in self.db.query(CapabilityDefinition.capability_key)
            .filter(CapabilityDefinition.workspace_id == self.workspace_id)
            .all()
        }
        for capability in seed["capabilities"]:
            if capability["capability_key"] in existing_keys:
                continue
            self.db.add(CapabilityDefinition(
                id=generate_snowflake_id(),
                workspace_id=self.workspace_id,
                brain_id=self.brain_id,
                capability_key=capability["capability_key"],
                name=capability["name"],
                expected_deliverables_jsonb=capability["expected_deliverables"],
                evidence_requirements_jsonb=capability["evidence_requirements"],
                supported_execution_modes_jsonb=capability["supported_execution_modes"],
                risk_level=capability["risk_level"],
                professional_review_required=capability["professional_review_required"],
            ))

    def list_templates(self) -> list[WorkspaceTemplate]:
        return (
            self.db.query(WorkspaceTemplate)
            .filter(WorkspaceTemplate.workspace_id == self.workspace_id)
            .order_by(WorkspaceTemplate.name)
            .all()
        )

    def get_active_version(self, template: WorkspaceTemplate) -> Optional[WorkspaceTemplateVersion]:
        return (
            self.db.query(WorkspaceTemplateVersion)
            .filter(
                WorkspaceTemplateVersion.template_id == template.id,
                WorkspaceTemplateVersion.version_no == template.active_version_no,
            )
            .first()
        )

    def reset_template(self, template_id: int, user_id: int) -> WorkspaceTemplate:
        """Archive the active local version and create a new one from the source seed.

        Never mutates a stage's already-recorded `template_snapshot_jsonb` -
        that snapshot references a specific, immutable version_no, and this
        only ever creates a new, higher version_no.
        """
        template = get_workspace_template_scoped(self.db, template_id, self.workspace_id)
        seed = SEED_TEMPLATES_BY_KEY.get(template.source_key)
        if seed is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Template has no system seed to reset from",
            )

        active_version = self.get_active_version(template)
        if active_version is not None:
            active_version.status = "ARCHIVED"

        new_version_no = template.active_version_no + 1
        self.db.add(WorkspaceTemplateVersion(
            id=generate_snowflake_id(),
            workspace_id=self.workspace_id,
            template_id=template.id,
            version_no=new_version_no,
            config_jsonb={"capabilities": seed["capabilities"]},
            source_seed_key=seed["source_key"],
            status="ACTIVE",
        ))
        template.active_version_no = new_version_no
        self.db.commit()
        self.db.refresh(template)
        return template

    def update_template(self, template_id: int, name: Optional[str] = None, capabilities: Optional[list] = None) -> WorkspaceTemplate:
        template = get_workspace_template_scoped(self.db, template_id, self.workspace_id)
        if name:
            template.name = name

        if capabilities is not None:
            active_version = self.get_active_version(template)
            if active_version is not None:
                new_config = dict(active_version.config_jsonb or {})
                new_config["capabilities"] = capabilities
                active_version.config_jsonb = new_config
            else:
                self.db.add(WorkspaceTemplateVersion(
                    id=generate_snowflake_id(),
                    workspace_id=self.workspace_id,
                    template_id=template.id,
                    version_no=template.active_version_no,
                    config_jsonb={"capabilities": capabilities},
                    source_seed_key=template.source_key,
                    status="ACTIVE",
                ))
        self.db.commit()
        self.db.refresh(template)
        return template
