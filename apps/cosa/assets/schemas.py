from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AuthoringCommand(BaseModel):
    workspace_id: str
    operation: str  # "CREATE" | "CLONE" | "EDIT_DRAFT" | "EVALUATE" | "PUBLISH" | "RETIRE"
    asset_kind: str | None = None  # "AGENT" | "SKILL" | "WORKFLOW"
    asset_id: str | None = None
    version: str | None = None
    name: str | None = None
    description: str | None = None
    content: dict[str, Any] | None = None
    scope_kind: str | None = "WORKSPACE"
    project_id: str | None = None
    source_asset_id: str | None = None
    source_version: str | None = None
    source_definition_hash: str | None = None
    expected_hash: str | None = None
    company_command_ref: str | None = None
    created_by: str = "system"


class AuthoringResponse(BaseModel):
    asset_id: str
    version: str
    definition_hash: str
    status: str
    lifecycle: str
    details: dict[str, Any] = Field(default_factory=dict)
