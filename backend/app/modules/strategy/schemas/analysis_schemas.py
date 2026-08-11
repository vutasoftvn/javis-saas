from typing import List, Optional
import uuid
from pydantic import BaseModel, Field


class PestelItemCreate(BaseModel):
    factor: str
    statement: str
    impact: Optional[str] = "Medium"
    horizon: Optional[str] = "medium_term"
    confidence: Optional[str] = "medium"
    evidence_status: Optional[str] = "hypothesized"


class PestelItemUpdate(BaseModel):
    factor: Optional[str] = None
    statement: Optional[str] = None
    impact: Optional[str] = None
    horizon: Optional[str] = None
    confidence: Optional[str] = None
    evidence_status: Optional[str] = None


class SwotItemCreate(BaseModel):
    category: str
    statement: str
    impact: Optional[str] = "High"
    likelihood: Optional[str] = "High"
    confidence: Optional[str] = "High"
    evidence_status: Optional[str] = "hypothesized"


class SwotItemUpdate(BaseModel):
    category: Optional[str] = None
    statement: Optional[str] = None
    impact: Optional[str] = None
    likelihood: Optional[str] = None
    confidence: Optional[str] = None
    evidence_status: Optional[str] = None


class TowsOptionCreate(BaseModel):
    quadrant: str
    title: str
    tradeoffs: str
    expected_impact: Optional[str] = "High"
    confidence: Optional[str] = "High"
    status: Optional[str] = "draft"


class TowsOptionUpdate(BaseModel):
    quadrant: Optional[str] = None
    title: Optional[str] = None
    tradeoffs: Optional[str] = None
    expected_impact: Optional[str] = None
    confidence: Optional[str] = None
    status: Optional[str] = None


class PromptTemplateUpdate(BaseModel):
    template_content: Optional[str] = None
    pestel_items_per_factor: Optional[int] = Field(None, ge=1, le=5)
    swot_items_per_category: Optional[int] = Field(None, ge=1, le=5)
    tows_items_per_quadrant: Optional[int] = Field(None, ge=1, le=5)


class AiAnalysisRequest(BaseModel):
    project_id: Optional[uuid.UUID] = None
    focus_area: Optional[str] = None
    focus_note: Optional[str] = None
    project_context: Optional[str] = None
    clear_existing: Optional[bool] = True
    pestel_items_per_factor: Optional[int] = Field(None, ge=1, le=5)
    swot_items_per_category: Optional[int] = Field(None, ge=1, le=5)
    tows_items_per_quadrant: Optional[int] = Field(None, ge=1, le=5)
    override_pestel_count: Optional[int] = Field(None, ge=1, le=5)
    override_swot_count: Optional[int] = Field(None, ge=1, le=5)
    override_tows_count: Optional[int] = Field(None, ge=1, le=5)


class AnalysisExportRequest(BaseModel):
    format: Optional[str] = "json"
    project_id: Optional[uuid.UUID] = None
    canvas_id: Optional[uuid.UUID] = None


class AnalysisImportRequest(BaseModel):
    raw_input: Optional[str] = None
    import_data: Optional[dict] = None
    project_id: Optional[uuid.UUID] = None
    canvas_id: Optional[uuid.UUID] = None
