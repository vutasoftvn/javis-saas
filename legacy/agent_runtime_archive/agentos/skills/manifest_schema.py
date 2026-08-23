# agentos/skills/manifest_schema.py
from __future__ import annotations

import enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


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
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    version: str
    description: str


class SkillPublisher(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    type: str


class SkillSource(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: str
    path: str
    repository: Optional[str] = None
    commit: Optional[str] = None
    license: Optional[str] = None


class SkillCapability(BaseModel):
    model_config = ConfigDict(extra="ignore")

    domain: str
    category: str
    intents: list[str] = Field(default_factory=list)


class SkillRuntime(BaseModel):
    model_config = ConfigDict(extra="ignore")

    environment: Optional[str] = "python"
    entrypoint: str = "SKILL.md"
    tools: list[str] = Field(default_factory=list)


class SkillPermissions(BaseModel):
    model_config = ConfigDict(extra="ignore")

    required: list[str] = Field(default_factory=list)
    filesystem: str = "none"
    network: str = "none"
    business_write: bool = False


class SkillRisk(BaseModel):
    model_config = ConfigDict(extra="ignore")

    level: str = "low"


class SkillTrust(BaseModel):
    model_config = ConfigDict(extra="ignore")

    tier: TrustTier = TrustTier.T0
    security_scan: str = "pending"


class SkillQuality(BaseModel):
    model_config = ConfigDict(extra="ignore")

    eval_score: float = Field(default=0.0, ge=0.0, le=1.0)
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0)


class SkillManifest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    api_version: str = Field(alias="apiVersion", default="agentos.ai/v1")
    kind: str = Field(default="Skill")
    metadata: SkillMetadata
    publisher: SkillPublisher
    source: SkillSource
    capability: SkillCapability
    runtime: SkillRuntime = Field(default_factory=SkillRuntime)
    permissions: SkillPermissions = Field(default_factory=SkillPermissions)
    risk: SkillRisk = Field(default_factory=SkillRisk)
    trust: SkillTrust = Field(default_factory=SkillTrust)
    quality: SkillQuality = Field(default_factory=SkillQuality)
