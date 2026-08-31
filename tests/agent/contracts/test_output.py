"""Unit tests for output schema contracts and validation.

Kiểm tra:
- Validation thành công với payload đúng định dạng
- Validation thất bại với payload không khớp schema
- Parsing JSON từ string (với markdown code blocks)
- Tất cả loại output contract (SupportDraftV1, ResearchBriefV1, ActionProposalV1)
- Edge cases: missing fields, wrong types, null schema
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent.contracts.output import (
    ActionProposalV1,
    ResearchBriefV1,
    SupportDraftV1,
    ValidationFailure,
    validate_output_payload,
)


class TestSupportDraftV1Contract:
    """Unit tests cho SupportDraftV1 output contract."""

    def test_support_draft_v1_valid_minimal(self):
        """Tạo SupportDraftV1 với required fields."""
        draft = SupportDraftV1(draft_body="Response to customer inquiry", intent="HELP")
        assert draft.draft_body == "Response to customer inquiry"
        assert draft.intent == "HELP"
        assert draft.evidence_refs == []
        assert draft.uncertainty == 0.0
        assert draft.escalation_reason is None

    def test_support_draft_v1_valid_full(self):
        """Tạo SupportDraftV1 với đầy đủ fields."""
        draft = SupportDraftV1(
            draft_body="Escalated response",
            intent="ESCALATE",
            evidence_refs=["ref_1", "ref_2"],
            uncertainty=0.3,
            escalation_reason="Agent unable to resolve",
        )
        assert draft.draft_body == "Escalated response"
        assert draft.intent == "ESCALATE"
        assert len(draft.evidence_refs) == 2
        assert draft.uncertainty == 0.3
        assert draft.escalation_reason == "Agent unable to resolve"

    def test_support_draft_v1_missing_required_field_fails(self):
        """SupportDraftV1 phải có draft_body — thiếu sẽ raise ValidationError."""
        with pytest.raises(ValidationError):
            SupportDraftV1(intent="HELP")

    def test_support_draft_v1_missing_intent_fails(self):
        """SupportDraftV1 phải có intent — thiếu sẽ raise ValidationError."""
        with pytest.raises(ValidationError):
            SupportDraftV1(draft_body="Text")


class TestResearchBriefV1Contract:
    """Unit tests cho ResearchBriefV1 output contract."""

    def test_research_brief_v1_valid_minimal(self):
        """Tạo ResearchBriefV1 với required fields."""
        brief = ResearchBriefV1(claim="COVID-19 vaccines are effective")
        assert brief.claim == "COVID-19 vaccines are effective"
        assert brief.source_url is None
        assert brief.supporting_excerpt is None
        assert brief.retrieved_at is None
        assert brief.confidence == 1.0
        assert brief.insufficient_evidence is False

    def test_research_brief_v1_valid_full(self):
        """Tạo ResearchBriefV1 với đầy đủ fields."""
        brief = ResearchBriefV1(
            claim="COVID-19 vaccines are effective",
            source_url="https://example.com/study",
            supporting_excerpt="Our study shows 95% efficacy...",
            retrieved_at="2026-08-01T12:00:00Z",
            confidence=0.95,
            insufficient_evidence=False,
        )
        assert brief.claim == "COVID-19 vaccines are effective"
        assert brief.source_url == "https://example.com/study"
        assert brief.confidence == 0.95

    def test_research_brief_v1_missing_claim_fails(self):
        """ResearchBriefV1 phải có claim."""
        with pytest.raises(ValidationError):
            ResearchBriefV1()


class TestActionProposalV1Contract:
    """Unit tests cho ActionProposalV1 output contract."""

    def test_action_proposal_v1_valid_minimal(self):
        """Tạo ActionProposalV1 với required fields."""
        proposal = ActionProposalV1(capability="finance.payout.execute", payload_hash="sha256_abc123")
        assert proposal.capability == "finance.payout.execute"
        assert proposal.payload_hash == "sha256_abc123"
        assert proposal.policy_decision == "REQUIRE_APPROVAL"
        assert proposal.required_approval is True
        assert proposal.rollback_steps == []
        assert proposal.evidence_refs == []

    def test_action_proposal_v1_valid_full(self):
        """Tạo ActionProposalV1 với đầy đủ fields."""
        proposal = ActionProposalV1(
            capability="finance.payout.execute",
            payload_hash="sha256_def456",
            policy_decision="REQUIRE_APPROVAL",
            required_approval=True,
            rollback_steps=["Reverse transaction", "Notify vendor"],
            evidence_refs=["approval_001"],
        )
        assert proposal.capability == "finance.payout.execute"
        assert len(proposal.rollback_steps) == 2
        assert len(proposal.evidence_refs) == 1

    def test_action_proposal_v1_missing_capability_fails(self):
        """ActionProposalV1 phải có capability."""
        with pytest.raises(ValidationError):
            ActionProposalV1(payload_hash="hash")

    def test_action_proposal_v1_missing_payload_hash_fails(self):
        """ActionProposalV1 phải có payload_hash."""
        with pytest.raises(ValidationError):
            ActionProposalV1(capability="finance.payout.execute")


class TestValidationFailureContract:
    """Unit tests cho ValidationFailure contract."""

    def test_validation_failure_minimal(self):
        """Tạo ValidationFailure với default state."""
        failure = ValidationFailure()
        assert failure.is_valid is False
        assert failure.errors == []
        assert failure.raw_output is None

    def test_validation_failure_with_errors(self):
        """Tạo ValidationFailure với error messages."""
        failure = ValidationFailure(
            is_valid=False, errors=["'score' is required", "'verdict' must be string"], raw_output='{"score": 99}'
        )
        assert failure.is_valid is False
        assert len(failure.errors) == 2
        assert "score" in failure.errors[0]
        assert failure.raw_output == '{"score": 99}'

    def test_validation_failure_model_dump(self):
        """ValidationFailure serializes correctly to dict."""
        failure = ValidationFailure(
            is_valid=False, errors=["Field required"], raw_output="invalid json"
        )
        dumped = failure.model_dump()
        assert dumped["is_valid"] is False
        assert dumped["errors"] == ["Field required"]
        assert dumped["raw_output"] == "invalid json"


class TestValidateOutputPayload:
    """Unit tests cho validate_output_payload function."""

    def test_validate_output_payload_no_schema_returns_success(self):
        """Nếu schema là None, validate luôn trả success."""
        is_valid, parsed, errors = validate_output_payload("any output", None)
        assert is_valid is True
        assert parsed == "any output"
        assert errors == []

    def test_validate_output_payload_empty_schema_returns_success(self):
        """Nếu schema là {}, validate cũng trả success."""
        is_valid, parsed, errors = validate_output_payload("output", {})
        assert is_valid is True

    def test_validate_output_payload_valid_json_dict(self):
        """Valid JSON dict payload passes validation."""
        schema = {
            "type": "object",
            "required": ["score"],
            "properties": {"score": {"type": "integer"}},
        }
        payload = {"score": 100}
        is_valid, parsed, errors = validate_output_payload(payload, schema)
        assert is_valid is True
        assert parsed == payload
        assert errors == []

    def test_validate_output_payload_valid_json_string(self):
        """Valid JSON string được parse và validate."""
        schema = {
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}},
        }
        payload_str = '{"name": "Alice"}'
        is_valid, parsed, errors = validate_output_payload(payload_str, schema)
        assert is_valid is True
        assert parsed == {"name": "Alice"}
        assert errors == []

    def test_validate_output_payload_json_string_with_markdown_code_block_json(self):
        """JSON string wrapped in ```json ... ``` được extract và parse."""
        schema = {
            "type": "object",
            "required": ["value"],
            "properties": {"value": {"type": "integer"}},
        }
        payload_str = '```json\n{"value": 42}\n```'
        is_valid, parsed, errors = validate_output_payload(payload_str, schema)
        assert is_valid is True
        assert parsed == {"value": 42}
        assert errors == []

    def test_validate_output_payload_json_string_with_markdown_code_block_generic(self):
        """JSON string wrapped in ``` ... ``` (generic code block) được extract và parse."""
        schema = {
            "type": "object",
            "required": ["x"],
            "properties": {"x": {"type": "number"}},
        }
        payload_str = "```\n{\"x\": 3.14}\n```"
        is_valid, parsed, errors = validate_output_payload(payload_str, schema)
        assert is_valid is True
        assert parsed == {"x": 3.14}
        assert errors == []

    def test_validate_output_payload_invalid_json_string_not_parseable(self):
        """Invalid JSON string không parse được — validate fail."""
        schema = {
            "type": "object",
            "required": ["key"],
            "properties": {"key": {"type": "string"}},
        }
        payload_str = '{"key": malformed}'
        is_valid, parsed, errors = validate_output_payload(payload_str, schema)
        assert is_valid is False
        # parsed vẫn là original string nếu không parse được
        assert parsed == payload_str
        assert len(errors) > 0

    def test_validate_output_payload_missing_required_field(self):
        """Payload thiếu required field — validate fail."""
        schema = {
            "type": "object",
            "required": ["score", "verdict"],
            "properties": {"score": {"type": "integer"}, "verdict": {"type": "string"}},
        }
        payload = {"score": 95}  # Missing 'verdict'
        is_valid, parsed, errors = validate_output_payload(payload, schema)
        assert is_valid is False
        assert parsed == payload
        assert len(errors) > 0
        assert "verdict" in errors[0].lower() or "required" in errors[0].lower()

    def test_validate_output_payload_wrong_type(self):
        """Payload có field với type sai — validate fail."""
        schema = {
            "type": "object",
            "required": ["count"],
            "properties": {"count": {"type": "integer"}},
        }
        payload = {"count": "not_a_number"}
        is_valid, parsed, errors = validate_output_payload(payload, schema)
        assert is_valid is False
        assert len(errors) > 0

    def test_validate_output_payload_array_schema(self):
        """Validate array payload theo array schema."""
        schema = {
            "type": "array",
            "items": {"type": "object", "properties": {"id": {"type": "string"}}},
        }
        payload = [{"id": "item_1"}, {"id": "item_2"}]
        is_valid, parsed, errors = validate_output_payload(payload, schema)
        assert is_valid is True
        assert parsed == payload
        assert errors == []

    def test_validate_output_payload_complex_nested_schema(self):
        """Validate complex nested object payload."""
        schema = {
            "type": "object",
            "required": ["status"],
            "properties": {
                "status": {"type": "string"},
                "details": {
                    "type": "object",
                    "properties": {"reason": {"type": "string"}, "code": {"type": "integer"}},
                },
            },
        }
        payload = {"status": "error", "details": {"reason": "Network timeout", "code": 504}}
        is_valid, parsed, errors = validate_output_payload(payload, schema)
        assert is_valid is True
        assert parsed == payload

    def test_validate_output_payload_preserves_raw_on_error(self):
        """Khi validation fail, raw payload được trả lại trong error message."""
        schema = {
            "type": "object",
            "required": ["value"],
            "properties": {"value": {"type": "integer"}},
        }
        payload = {"value": "text"}
        is_valid, parsed, errors = validate_output_payload(payload, schema)
        assert is_valid is False
        assert parsed == payload  # Parsed vẫn là invalid payload
        assert errors  # Có error message

    def test_validate_output_payload_json_array_string(self):
        """JSON array trong string được parse."""
        schema = {
            "type": "array",
            "items": {"type": "string"},
        }
        payload_str = '["a", "b", "c"]'
        is_valid, parsed, errors = validate_output_payload(payload_str, schema)
        assert is_valid is True
        assert parsed == ["a", "b", "c"]
        assert errors == []

    def test_validate_output_payload_whitespace_handling(self):
        """Whitespace quanh JSON được xử lý."""
        schema = {
            "type": "object",
            "required": ["x"],
            "properties": {"x": {"type": "integer"}},
        }
        payload_str = "  \n  {\"x\": 5}  \n  "
        is_valid, parsed, errors = validate_output_payload(payload_str, schema)
        assert is_valid is True
        assert parsed == {"x": 5}
