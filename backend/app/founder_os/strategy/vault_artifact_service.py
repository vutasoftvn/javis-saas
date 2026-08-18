from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import Project
from app.db.repositories.vault_repo import VaultRepository
from app.platform.vault.models import VaultRevision


def create_stage_artifact(
    db: Session,
    user_id: int,
    brain_id: int,
    role: str,
    project_id: int,
    artifact_kind: str,
    content: str,
    stage_id: Optional[int] = None,
) -> VaultRevision:
    """Writes a stage or project artefact through the existing VaultRepository.
    Uses the project title or code as the folder name instead of raw snowflake ID.
    """
    proj = db.query(Project).filter(Project.id == project_id).first()
    folder = (proj.title.strip() if proj and proj.title else f"projects/{project_id}")

    path = (
        f"{folder}/stages/{stage_id}/{artifact_kind}.md"
        if stage_id is not None
        else f"{folder}/{artifact_kind}.md"
    )
    repo = VaultRepository(db, user_id, brain_id, role)
    existing = repo.get_document(path)
    base_revision_id = existing.current_revision_id if existing else None
    return repo.update_document(path, "strategy", content.encode("utf-8"), base_revision_id)

