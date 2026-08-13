from typing import Optional

from sqlalchemy.orm import Session

from app.db.repositories.vault_repo import VaultRepository
from app.modules.vault.models import VaultRevision


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
    """Writes a stage or project artefact through the existing VaultRepository -
    never a new object-store client. Always targets the document's latest
    revision, since this is the system creating/replacing its own generated
    artefact rather than a client racing a concurrent edit.

    `artifact_kind` (e.g. "mvp_roadmap", "service_assessment") names the file
    under the path; VaultDocument.kind stays the coarse module category
    ("strategy") that the rest of the Vault already groups documents by.
    """
    # No leading slash: VaultRepository builds its object key as
    # f"{brain_id}/{path}/{sha256}" - a leading slash here produces a
    # double slash (empty path segment) that MinIO rejects outright.
    path = (
        f"projects/{project_id}/stages/{stage_id}/{artifact_kind}.md"
        if stage_id is not None
        else f"projects/{project_id}/{artifact_kind}.md"
    )
    repo = VaultRepository(db, user_id, brain_id, role)
    existing = repo.get_document(path)
    base_revision_id = existing.current_revision_id if existing else None
    return repo.update_document(path, "strategy", content.encode("utf-8"), base_revision_id)
