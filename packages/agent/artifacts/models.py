from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from agent.ids import uuid7  # LeafId UUIDv7 cho artifact_id (M2 §3)

__all__ = [
    "ArtifactKind",
    "ArtifactStatus",
    "WorkspaceArtifact",
    "generate_artifact_id",
]

ArtifactKind = Literal["assistant_output", "report", "table", "file_export"]
ArtifactStatus = Literal["available", "failed", "archived"]


def generate_artifact_id() -> str:
    return f"art_{uuid7().hex}"


class WorkspaceArtifact(BaseModel):
    """Bản ghi artifact công việc trong agent_artifact.workspace_artifacts.

    workspace_id là khóa tenant duy nhất sau Task 7 (2026-08-27).
    """

    artifact_id: str = Field(default_factory=generate_artifact_id)
    workspace_id: str
    conversation_id: str
    run_id: str | None = None
    source_message_id: str | None = None
    artifact_kind: ArtifactKind = "assistant_output"
    display_name: str
    media_type: str
    object_ref: str
    checksum: str | None = None
    size_bytes: int = 0
    status: ArtifactStatus = "available"
    input_artifact_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    archived_at: datetime | None = None

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("display_name cannot be empty")
        return v.strip()

    @field_validator("media_type")
    @classmethod
    def validate_media_type(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("media_type cannot be empty")
        return v.strip()

    @field_validator("object_ref")
    @classmethod
    def validate_object_ref(cls, v: str) -> str:
        if not (v.startswith("object://") or v.startswith("artifact://")):
            raise ValueError("object_ref must start with 'object://' or 'artifact://'")
        return v
