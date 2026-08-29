from __future__ import annotations

import json
from typing import Any
import jsonschema
from pydantic import BaseModel, Field

__all__ = [
    "ActionProposalV1",
    "PreAuthorizationEvidence",
    "ResearchBriefV1",
    "SupportDraftV1",
    "ValidationFailure",
    "validate_output_payload",
]


class SupportDraftV1(BaseModel):
    """Output contract for customer support drafts."""

    draft_body: str
    intent: str
    evidence_refs: list[str] = Field(default_factory=list)
    uncertainty: float = 0.0
    escalation_reason: str | None = None


class ResearchBriefV1(BaseModel):
    """Output contract for research and marketing briefs."""

    claim: str
    source_url: str | None = None
    supporting_excerpt: str | None = None
    retrieved_at: str | None = None
    confidence: float = 1.0
    insufficient_evidence: bool = False


class ActionProposalV1(BaseModel):
    """Output contract for proposed actions/side-effects."""

    capability: str
    payload_hash: str
    policy_decision: str = "REQUIRE_APPROVAL"
    required_approval: bool = True
    rollback_steps: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class PreAuthorizationEvidence(BaseModel):
    """Pre-authorization evidence token for verifiable cross-plane approvals."""

    id: str
    workspace_id: str
    capability_id: str
    scope_kind: str = "TEMPLATE"
    template_version: str | None = None
    payload_hash: str | None = None
    issuer: str
    expires_at: str
    is_revoked: bool = False


class ValidationFailure(BaseModel):
    """Thông báo lỗi có cấu trúc khi output payload không khớp output_schema."""

    is_valid: bool = False
    errors: list[str] = Field(default_factory=list)
    raw_output: Any = None


def validate_output_payload(
    raw_output: Any,
    schema: dict[str, Any] | None,
) -> tuple[bool, Any, list[str]]:
    """Kiểm tra và chuẩn hoá output payload theo output_schema.

    Trả về:
        (is_valid, parsed_payload, list_of_errors)
    """
    if not schema:
        return True, raw_output, []

    parsed = raw_output
    if isinstance(raw_output, str):
        trimmed = raw_output.strip()
        # Parse JSON string if enclosed in braces or markdown code block
        if trimmed.startswith("```json") and trimmed.endswith("```"):
            trimmed = trimmed[7:-3].strip()
        elif trimmed.startswith("```") and trimmed.endswith("```"):
            trimmed = trimmed[3:-3].strip()

        if (trimmed.startswith("{") and trimmed.endswith("}")) or (
            trimmed.startswith("[") and trimmed.endswith("]")
        ):
            try:
                parsed = json.loads(trimmed)
            except Exception:
                pass

    try:
        jsonschema.validate(instance=parsed, schema=schema)
        return True, parsed, []
    except jsonschema.ValidationError as exc:
        return False, parsed, [exc.message]
    except Exception as exc:
        return False, parsed, [str(exc)]
