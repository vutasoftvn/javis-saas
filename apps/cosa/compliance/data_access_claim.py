from __future__ import annotations

from pydantic import BaseModel, Field


class DataAccessClaim(BaseModel):
    workspace_id: str
    deployment_id: str
    capability_id: str
    source_ref: str
    source_hash: str
    categories: frozenset[str] = Field(default_factory=frozenset)
    purpose_id: str
    subject_reference: str | None = None
    provider_key: str
    model_key: str
    retention_policy_id: str | None = None

    class Config:
        frozen = True
