from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator

__all__ = [
    "ArtifactKind",
    "ArtifactStatus",
    "WorkspaceArtifact",
    "generate_artifact_id",
]

ArtifactKind = Literal["assistant_output", "report", "table", "file_export"]
ArtifactStatus = Literal["available", "failed", "archived"]


def generate_artifact_id() -> str:
    return f"art_{uuid.uuid4().hex[:12]}"


class WorkspaceArtifact(BaseModel):
    artifact_id: str = Field(default_factory=generate_artifact_id)
    company_id: str
    workspace_id: str
    conversation_id: str
    run_id: Optional[str] = None
    source_message_id: Optional[str] = None
    artifact_kind: ArtifactKind = "assistant_output"
    display_name: str
    media_type: str
    object_ref: str
    checksum: Optional[str] = None
    size_bytes: int = 0
    status: ArtifactStatus = "available"
    input_artifact_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    archived_at: Optional[datetime] = None

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
