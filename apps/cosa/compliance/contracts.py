from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ComplianceSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    workspace_id: str
    deployment_id: str
    assessment_id: str
    mode: Literal["ADVISORY_ONLY"]
    status: Literal["APPROVED_FOR_USE"]
    allowed_capabilities: frozenset[str] = Field(default_factory=frozenset)
    provider_profile_version: str
    data_profile_version: str
    snapshot_hash: str
    expires_at: datetime
    policy_snapshot_hash: str = ""
    evidence_hashes: list[str] = Field(default_factory=list)
    rule_version_ids: list[str] = Field(default_factory=list)


class AiComplianceUnavailable(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or f"AI compliance unavailable: {code}")
        self.code = code


class ComplianceDenied(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or f"AI compliance denied: {code}")
        self.code = code
