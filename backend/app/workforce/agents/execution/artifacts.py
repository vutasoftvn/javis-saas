import hashlib
import mimetypes
import os
from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session

from app.workforce.agents.execution.base import ExecutionProvider
from app.workforce.agents.execution.errors import ExecutionErrorCode, ExecutionRuntimeError
from app.workforce.agents.execution.types import ArtifactRef, SandboxPolicy
from app.integrations.storage.s3_client import put_object
from app.founder_os.outcomes.models import Artifact


async def collect_and_store_artifacts(
    db: Session,
    workspace_id: int,
    user_id: int,
    job_id: int,
    sandbox_id: str,
    provider: ExecutionProvider,
    policy: SandboxPolicy,
) -> List[ArtifactRef]:
    """Collect artifacts from sandbox output directory, validate, upload to S3/MinIO, and insert into DB."""
    output_files = await provider.list_outputs(sandbox_id, prefix="/output")
    if not output_files:
        return []

    # 1. Validate artifact count
    if len(output_files) > policy.max_artifact_count:
        raise ExecutionRuntimeError(
            code=ExecutionErrorCode.EXEC_ARTIFACT_LIMIT_EXCEEDED,
            message=f"Artifact count {len(output_files)} exceeds maximum allowed {policy.max_artifact_count}",
        )

    results: List[ArtifactRef] = []

    for file_path in output_files:
        # 2. Path Traversal & Normalization Check
        if ".." in file_path.split(os.sep) or ".." in file_path:
            raise ExecutionRuntimeError(
                code=ExecutionErrorCode.EXEC_ARTIFACT_INVALID_PATH,
                message=f"Illegal path traversal detected in artifact path: {file_path}",
            )

        clean_path = os.path.normpath(file_path)
        if clean_path.startswith("/output/"):
            rel_path = clean_path[len("/output/"):]
        elif clean_path == "/output":
            continue
        elif not clean_path.startswith("/output"):
            raise ExecutionRuntimeError(
                code=ExecutionErrorCode.EXEC_ARTIFACT_INVALID_PATH,
                message=f"Artifact path outside /output directory: {file_path}",
            )
        else:
            rel_path = clean_path[len("/output"):].lstrip("/")

        if not rel_path:
            continue

        # 3. Download raw bytes from sandbox
        data = await provider.download_file(sandbox_id, clean_path)

        # 4. Validate artifact size
        if len(data) > policy.max_artifact_bytes:
            raise ExecutionRuntimeError(
                code=ExecutionErrorCode.EXEC_ARTIFACT_LIMIT_EXCEEDED,
                message=f"Artifact {rel_path} size {len(data)} bytes exceeds limit {policy.max_artifact_bytes}",
            )

        # 5. Compute SHA-256 hash
        content_hash = hashlib.sha256(data).hexdigest()

        # 6. Upload to MinIO/S3 object storage
        mime_type, _ = mimetypes.guess_type(rel_path)
        mime_type = mime_type or "application/octet-stream"
        storage_key = f"workspaces/{workspace_id}/execution/{job_id}/{rel_path}"

        try:
            put_object(storage_key, data, mime_type)
        except Exception as e:
            # If MinIO put fails, raise file error
            raise ExecutionRuntimeError(
                code=ExecutionErrorCode.EXEC_FILE_ERROR,
                message=f"Failed to store artifact {rel_path} to object storage: {e}",
            )

        # Determine outcome artifact type
        ext = Path(rel_path).suffix.lower()
        if ext in [".py", ".sh", ".js", ".ts", ".diff", ".patch"]:
            artifact_type = "code"
        elif ext in [".csv", ".xlsx", ".tsv"]:
            artifact_type = "spreadsheet"
        elif ext in [".md", ".txt", ".json", ".pdf", ".html"]:
            artifact_type = "document"
        elif ext in [".png", ".jpg", ".jpeg", ".svg"]:
            artifact_type = "media"
        else:
            artifact_type = "research_bundle"

        # 7. Record in PostgreSQL artifacts table
        artifact_record = Artifact(
            workspace_id=workspace_id,
            execution_job_id=job_id,
            type=artifact_type,
            title=Path(rel_path).name,
            object_storage_uri=storage_key,
            content_hash=content_hash,
            status="draft",
            created_by=user_id,
        )
        db.add(artifact_record)
        db.flush()

        results.append(
            ArtifactRef(
                name=Path(rel_path).name,
                relative_path=rel_path,
                size_bytes=len(data),
                content_hash=content_hash,
                mime_type=mime_type,
                object_storage_uri=storage_key,
                artifact_id=str(artifact_record.id),
            )
        )

    db.commit()
    return results
