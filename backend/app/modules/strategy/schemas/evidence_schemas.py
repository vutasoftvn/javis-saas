from typing import List, Optional
from pydantic import BaseModel


class ContextPackCreate(BaseModel):
    name: str
    description: Optional[str] = None
    industry: Optional[str] = None
    region: Optional[str] = None


class ContextPackUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    region: Optional[str] = None


class EvidenceLinkRequest(BaseModel):
    evidence_ids: List[int]


class EvidenceCreate(BaseModel):
    title: str
    content: str
    source_type: Optional[str] = "internal_doc"
    source_url: Optional[str] = None
    author: Optional[str] = None
    tags: Optional[List[str]] = None
