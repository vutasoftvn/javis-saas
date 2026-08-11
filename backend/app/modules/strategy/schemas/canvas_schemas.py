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
    title: str
    description: Optional[str] = None


class CanvasUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class RevisionCreate(BaseModel):
    title: Optional[str] = None
    notes: Optional[str] = None


class ApproveRevisionBody(BaseModel):
    comments: Optional[str] = None


class RequestChangesBody(BaseModel):
    feedback: str


class CoreValueIn(BaseModel):
    title: str
    description: Optional[str] = None


class FoundationSave(BaseModel):
    vision_statement: Optional[str] = None
    mission_statement: Optional[str] = None
    core_values: Optional[List[CoreValueIn]] = None
