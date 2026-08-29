from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

__all__ = ["ArtifactManager", "ArtifactRecord", "ArtifactReference"]


class ArtifactReference(BaseModel):
    """Tham chiếu gọn nhẹ tới Artifact Record (dùng trong RunResult/Event stream)."""

    artifact_id: str
    name: str
    media_type: str
    storage_uri: str
    checksum: str
    size_bytes: int


class ArtifactRecord(BaseModel):
    """Bản ghi vòng đời Artifact đầy đủ với Provenance metadata theo Master Guide §32 & §43.9."""

    artifact_id: str
    run_id: str
    name: str
    media_type: str
    storage_uri: str
    checksum: str
    size_bytes: int
    creator_principal: str
    spec_identity: dict[str, Any] | None = None
    source_inputs_hash: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_reference(self) -> ArtifactReference:
        return ArtifactReference(
            artifact_id=self.artifact_id,
            name=self.name,
            media_type=self.media_type,
            storage_uri=self.storage_uri,
            checksum=self.checksum,
            size_bytes=self.size_bytes,
        )


class ArtifactManager:
    """Quản trị vòng đời và truy xuất nguồn gốc (Provenance) của Artifacts."""

    def __init__(self) -> None:
        self._artifacts: dict[str, ArtifactRecord] = {}  # artifact_id -> ArtifactRecord
        self._run_artifacts: dict[str, list[str]] = {}  # run_id -> [artifact_id]

    async def register_artifact(
        self,
        *,
        run_id: str,
        name: str,
        content_bytes: bytes,
        media_type: str = "text/plain",
        storage_uri: str | None = None,
        creator_principal: str = "agent_system",
        spec_identity: dict[str, Any] | None = None,
        source_inputs: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ArtifactRecord:
        checksum = hashlib.sha256(content_bytes).hexdigest()
        artifact_id = f"art_{checksum[:16]}"
        uri = storage_uri or f"artifact://{run_id}/{artifact_id}"

        source_inputs_hash = None
        if source_inputs:
            source_inputs_hash = hashlib.sha256(
                json.dumps(source_inputs, sort_keys=True, default=str).encode("utf-8")
            ).hexdigest()

        rec = ArtifactRecord(
            artifact_id=artifact_id,
            run_id=run_id,
            name=name,
            media_type=media_type,
            storage_uri=uri,
            checksum=checksum,
            size_bytes=len(content_bytes),
            creator_principal=creator_principal,
            spec_identity=spec_identity,
            source_inputs_hash=source_inputs_hash,
            metadata=metadata or {},
        )

        self._artifacts[artifact_id] = rec
        self._run_artifacts.setdefault(run_id, []).append(artifact_id)
        return rec

    async def get_artifact(self, artifact_id: str) -> ArtifactRecord | None:
        return self._artifacts.get(artifact_id)

    async def list_by_run(self, run_id: str) -> list[ArtifactRecord]:
        art_ids = self._run_artifacts.get(run_id, [])
        return [self._artifacts[aid] for aid in art_ids if aid in self._artifacts]
