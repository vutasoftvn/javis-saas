"""Pydantic schemas for COSA Business Knowledge Pack standard (Spec E1)."""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class PackSource(BaseModel):
    type: str = "cosa-factory"
    references: List[str] = Field(default_factory=list)
    inspired_by: Optional[List[Dict[str, Any]]] = None


class PackScope(BaseModel):
    company_types: List[str] = Field(default_factory=lambda: ["startup", "sme"])
    jurisdictions: List[str] = Field(default_factory=lambda: ["VN"])


class PackFeatures(BaseModel):
    auto_enable: bool = True
    company_override: bool = True
    factory_reset: bool = True


class PackContentsDir(BaseModel):
    capabilities_dir: str = "capabilities"
    skills_dir: str = "skills"
    sops_dir: str = "sops"
    templates_dir: str = "templates"
    references_dir: str = "references"
    legal_dir: str = "legal"


class PackUpdatePolicy(BaseModel):
    channel: str = "stable"
    preserve_company_override: bool = True
    require_admin_review_on_conflict: bool = True


class PackManifest(BaseModel):
    id: str
    name: Dict[str, str] = Field(default_factory=dict)
    version: str = "1.0.0"
    schema_version: str = "1"
    status: str = "active"
    domain: Optional[str] = None
    description: Optional[str] = None
    source: PackSource = Field(default_factory=PackSource)
    scope: PackScope = Field(default_factory=PackScope)
    features: PackFeatures = Field(default_factory=PackFeatures)
    contents: PackContentsDir = Field(default_factory=PackContentsDir)
    update_policy: PackUpdatePolicy = Field(default_factory=PackUpdatePolicy)


class CapabilityRisk(BaseModel):
    level: str = "low"  # low, medium, high, critical
    admin_review: bool = False


class CapabilityUses(BaseModel):
    skill: Optional[str] = None
    sop: Optional[str] = None
    template: Optional[str] = None


class CapabilityLegalContext(BaseModel):
    required: bool = False
    jurisdiction: str = "VN"
    relevant_tags: List[str] = Field(default_factory=list)


class CapabilityOutput(BaseModel):
    canonical_format: str = "structured_document"
    allowed_exports: List[str] = Field(default_factory=lambda: ["md", "docx", "pdf"])


class CapabilityDefinition(BaseModel):
    id: str
    name: Dict[str, str] = Field(default_factory=dict)
    domain: str
    execution_mode: str = "assisted"  # direct, assisted, autonomous
    artifact_type: str = "POL"  # POL, MAN, SOP, FRM, RPT
    risk: CapabilityRisk = Field(default_factory=CapabilityRisk)
    required_context: List[str] = Field(default_factory=list)
    inputs: Dict[str, List[str]] = Field(default_factory=lambda: {"required": [], "optional": []})
    uses: CapabilityUses = Field(default_factory=CapabilityUses)
    legal_context: CapabilityLegalContext = Field(default_factory=CapabilityLegalContext)
    output: CapabilityOutput = Field(default_factory=CapabilityOutput)


class SOPStep(BaseModel):
    id: Optional[str] = None
    action: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    condition: Optional[str] = None


class SOPDefinition(BaseModel):
    id: str
    version: str = "1.0.0"
    objective: str
    steps: List[Any] = Field(default_factory=list)
    business_rules: List[str] = Field(default_factory=list)
    stages: Optional[List[str]] = None
    metrics: Optional[List[str]] = None
    system_of_record: Optional[str] = None
    hologram: Optional[Dict[str, Any]] = None


class SkillDefinition(BaseModel):
    id: str
    name: str
    domain: str
    version: str = "1.0.0"
    risk: str = "low"
    body_markdown: str = ""



class TemplateMetadata(BaseModel):
    id: str
    name: str
    type: str = "FRM"  # POL, MAN, SOP, FRM, RPT
    version: str = "1.0.0"
    status: str = "active"
    jurisdiction: str = "VN"
    source: str = "cosa-factory"
    editable_copy: bool = True
    company_override_key: Optional[str] = None
    legal_refs: List[str] = Field(default_factory=list)
    variables: List[str] = Field(default_factory=list)
    sections: List[str] = Field(default_factory=list)


class TemplateBundle(BaseModel):
    metadata: TemplateMetadata
    body_markdown: str
    is_override: bool = False
    override_version: Optional[str] = None


class LegalSourceMetadata(BaseModel):
    id: str
    jurisdiction: str = "VN"
    title: str
    document_type: str = "law"  # law, decree, circular, standard
    identifier: str = ""
    issuer: str = ""
    issued_date: Optional[str] = None
    effective_date: Optional[str] = None
    expiry_date: Optional[str] = None
    status: str = "current"  # current, amended, superseded, expired, unknown
    version: str = "1"
    source_url: Optional[str] = None
    source_file: Optional[str] = None
    text_file: Optional[str] = None
    last_verified_at: Optional[str] = None
    verified_by: Optional[str] = None
    supersedes: List[str] = Field(default_factory=list)
    superseded_by: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    checksum: Optional[str] = None


class CompanyLegalAnnotation(BaseModel):
    legal_source_id: str
    workspace_id: int
    applicability_status: str = "applicable"  # applicable, partially_applicable, exempt, unknown
    business_areas: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    linked_sops: List[str] = Field(default_factory=list)
    linked_templates: List[str] = Field(default_factory=list)
    reviewed_at: Optional[str] = None
    reviewed_by: Optional[int] = None


class CompanyAssetOverride(BaseModel):
    workspace_id: int
    asset_id: str
    asset_type: str  # template, sop, capability, reference
    version: str = "1.0.0"
    content_override: Dict[str, Any] = Field(default_factory=dict)
    body_override: Optional[str] = None
    notes: Optional[str] = None
    updated_by: Optional[int] = None
    updated_at: Optional[str] = None


class UpdateConflictRecord(BaseModel):
    id: str
    asset_id: str
    old_factory_version: str
    new_factory_version: str
    company_override_version: str
    status: str = "pending"  # pending, resolved
    resolution: Optional[str] = None  # KEEP_COMPANY, ACCEPT_FACTORY, MERGE, RESET_FACTORY
