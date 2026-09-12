from __future__ import annotations

from agent.contracts.output import validate_output_payload
from agent.executive_board.models import EXECUTIVE_ANALYSIS_OUTPUT_SCHEMA


def test_valid_payload_passes_schema():
    payload = {
        "conclusion": "Runway hiện tại đủ 14 tháng nếu giữ nguyên burn rate.",
        "options": [
            {"title": "Giữ nguyên chi tiêu", "trade_off": "An toàn nhưng chậm tăng trưởng"},
        ],
        "evidence_claims": [
            {"claim": "Burn rate tháng 8 là 45,000 USD", "source_ref": "object://finance/burn-aug"},
        ],
        "assumptions": ["Doanh thu không đổi"],
        "risks_and_unknowns": ["Chưa tính đến vòng gọi vốn mới"],
        "confidence": 0.8,
        "human_review_required": True,
    }
    is_valid, parsed, errors = validate_output_payload(payload, EXECUTIVE_ANALYSIS_OUTPUT_SCHEMA)
    assert is_valid is True
    assert errors == []
    assert parsed["conclusion"] == payload["conclusion"]


def test_payload_missing_evidence_claims_fails_schema():
    payload = {
        "conclusion": "Thiếu evidence.",
        "options": [{"title": "A", "trade_off": "B"}],
    }
    is_valid, _parsed, errors = validate_output_payload(payload, EXECUTIVE_ANALYSIS_OUTPUT_SCHEMA)
    assert is_valid is False
    assert errors
