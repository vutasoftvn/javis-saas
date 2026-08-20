from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

class ManifestValidationError(Exception):
    pass

class HealthCheckManifest(BaseModel):
    type: str

class CapabilityManifest(BaseModel):
    id: str
    name: str
    # Governance metadata is required, not optional: eligibility resolution fails
    # closed (GOVERNANCE_METADATA_UNAVAILABLE) for any discovered capability whose
    # manifest entry lacks it, so a manifest that omits these fields can never be
    # installed in the first place.
    risk_level: str
    permission_level: str
    requires_approval: bool
    mutating: bool
    external: bool


class MCPProviderConfig(BaseModel):
    endpoint: str


class ExtensionManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    extension_id: str
    version: str
    compatibility: str
    trust_level: Literal["first_party"]
    owner: str
    capabilities: tuple[CapabilityManifest, ...] = Field(default_factory=tuple)
    required_permissions: tuple[str, ...] = Field(default_factory=tuple)
    required_secret_refs: tuple[str, ...] = Field(default_factory=tuple)
    supported_scope_levels: tuple[Literal["company", "operating_unit", "offering", "initiative"], ...] = Field(default_factory=tuple)
    health_check: HealthCheckManifest
    disable_behavior: Literal["block_new_calls_preserve_history"]
    provider_type: Literal["mcp"]
    provider_config: MCPProviderConfig
