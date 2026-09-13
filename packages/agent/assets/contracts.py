from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class AssetKind(StrEnum):
    AGENT = "AGENT"
    SKILL = "SKILL"
    WORKFLOW = "WORKFLOW"


class AssetScopeKind(StrEnum):
    WORKSPACE = "WORKSPACE"
    PROJECT_SANDBOX = "PROJECT_SANDBOX"


class AssetLifecycle(StrEnum):
    DRAFT = "DRAFT"
    CANDIDATE = "CANDIDATE"
    EVALUATING = "EVALUATING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    PUBLISHED = "PUBLISHED"
    RETIRED = "RETIRED"


class AssetOriginKind(StrEnum):
    SCRATCH = "SCRATCH"
    CLONE = "CLONE"
    BUILTIN = "BUILTIN"


class AssetImmutableError(Exception):
    """Raised when attempting to modify an immutable published asset version."""


class AssetScopeError(Exception):
    """Raised when scope configuration is invalid."""


class AssetConflictError(Exception):
    """Raised when an asset or version conflict occurs (e.g. hash mismatch, duplicate)."""


class AssetNotFoundError(Exception):
    """Raised when an asset or version is not found."""


class BuiltinAssetReadOnlyError(Exception):
    """Raised when attempting to edit or delete a read-only built-in asset."""


class AssetNotEvaluatedError(Exception):
    """Raised when attempting to publish an asset without required passing evaluation."""


@dataclass(frozen=True)
class AssetScope:
    kind: str  # "WORKSPACE" | "PROJECT_SANDBOX"
    project_id: str | None = None

    def __post_init__(self) -> None:
        if self.kind in (AssetScopeKind.PROJECT_SANDBOX, "PROJECT_SANDBOX"):
            if not self.project_id:
                raise AssetScopeError("PROJECT_SANDBOX scope requires a non-empty project_id")
        elif self.kind in (AssetScopeKind.WORKSPACE, "WORKSPACE"):
            if self.project_id is not None:
                raise AssetScopeError("WORKSPACE scope must not have a project_id")
        else:
            raise AssetScopeError(f"Unknown scope kind: {self.kind}")

    @classmethod
    def workspace(cls) -> AssetScope:
        return cls(kind="WORKSPACE", project_id=None)

    @classmethod
    def project_sandbox(cls, project_id: str) -> AssetScope:
        return cls(kind="PROJECT_SANDBOX", project_id=project_id)


@dataclass(frozen=True)
class AssetOrigin:
    kind: str  # "SCRATCH" | "CLONE" | "BUILTIN"
    asset_id: str
    version: str
    definition_hash: str


@dataclass(frozen=True)
class PinnedAssetIdentity:
    kind: AssetKind
    asset_id: str
    version: str
    definition_hash: str


@dataclass
class WorkspaceAssetDraft:
    asset_id: str
    kind: AssetKind
    version: str
    name: str
    description: str | None
    content: dict[str, Any]
    scope: AssetScope
    created_by: str
    origin: AssetOrigin | None = None


@dataclass
class WorkspaceAssetVersion:
    workspace_id: str
    asset_id: str
    kind: AssetKind
    version: str
    definition_hash: str
    content_json: dict[str, Any]
    lifecycle: AssetLifecycle
    scope: AssetScope
    created_by: str
    origin: AssetOrigin | None = None
    evaluation_summary: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    published_at: datetime | None = None


@dataclass
class AssetEvaluationResult:
    evaluation_id: str
    workspace_id: str
    asset_id: str
    version: str
    definition_hash: str
    status: str  # "PASS" | "FAIL" | "REVIEW_REQUIRED"
    structural_result: dict[str, Any] = field(default_factory=dict)
    negative_policy_result: dict[str, Any] = field(default_factory=dict)
    scenario_suite_result: dict[str, Any] = field(default_factory=dict)
    evidence_refs: list[str] = field(default_factory=list)
    cost_latency_summary: dict[str, Any] = field(default_factory=dict)
    evaluator_version: str = "1.0.0"
    evaluated_at: datetime = field(default_factory=datetime.utcnow)
