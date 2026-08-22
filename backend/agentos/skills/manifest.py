# backend/agentos/skills/manifest.py
from __future__ import annotations

import enum

from pydantic import BaseModel, Field


class TrustTier(str, enum.Enum):
    T0 = "T0"
    T1 = "T1"
    T2 = "T2"
    T3 = "T3"
    T4 = "T4"


class SkillLifecycleStatus(str, enum.Enum):
    DISCOVERED = "DISCOVERED"
    IMPORTED = "IMPORTED"
    SCANNED = "SCANNED"
    VERIFIED = "VERIFIED"
    STAGED = "STAGED"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    QUARANTINED = "QUARANTINED"
    REJECTED = "REJECTED"


class SkillMetadata(BaseModel):
    id: str
    name: str
    version: str
    description: str


class SkillPublisher(BaseModel):
    name: str
    type: str


class SkillSource(BaseModel):
    type: str
    path: str
    repository: str | None = None
    commit: str | None = None
    license: str | None = None


class SkillCapability(BaseModel):
    domain: str
    category: str
    intents: list[str] = Field(default_factory=list)


class SkillRuntime(BaseModel):
    entrypoint: str = "SKILL.md"
    tools: list[str] = Field(default_factory=list)


class SkillPermissions(BaseModel):
    filesystem: str = "none"
    network: str = "none"
    business_write: bool = False


class SkillRisk(BaseModel):
    level: str = "low"


class SkillTrust(BaseModel):
    tier: TrustTier = TrustTier.T2
    security_scan: str = "pending"


class SkillQuality(BaseModel):
    eval_score: float = Field(default=0.0, ge=0.0, le=1.0)
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0)


class SkillManifest(BaseModel):
    model_config = {"populate_by_name": True}

    api_version: str = Field(alias="apiVersion")
    kind: str
    metadata: SkillMetadata
    publisher: SkillPublisher
    source: SkillSource
    capability: SkillCapability
    runtime: SkillRuntime
    permissions: SkillPermissions
    risk: SkillRisk = Field(default_factory=SkillRisk)
    trust: SkillTrust = Field(default_factory=SkillTrust)
    quality: SkillQuality = Field(default_factory=SkillQuality)
