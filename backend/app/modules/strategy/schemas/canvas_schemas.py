from typing import List, Optional
from pydantic import BaseModel, Field


class ObjectiveCreate(BaseModel):
    title: str
    description: Optional[str] = None
    perspective: Optional[str] = "financial"
    target_value: Optional[float] = 100.0
    unit: Optional[str] = "%"
    scorecard_id: Optional[str] = None


class CanvasCreate(BaseModel):
    name: str
    description: Optional[str] = None


class CanvasUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class RevisionCreate(BaseModel):
    base_revision_id: Optional[str] = None


class ApproveRevisionBody(BaseModel):
    note: Optional[str] = None


class RequestChangesBody(BaseModel):
    reason: str


class CoreValueIn(BaseModel):
    slot_no: int
    title: str
    description: str
    decision_rule: str


class FoundationSave(BaseModel):
    vision: str
    mission: str
    values: List[CoreValueIn]
