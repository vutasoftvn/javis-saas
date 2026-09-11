from __future__ import annotations

import pytest
from agent.executive_board.models import (
    ExecutiveAnalysisRequest,
    ExecutiveBoardInputError,
    RolePin,
    EvidenceRef,
)
from agent.executive_board.runner import ExecutiveBoardRunner


def make_request(**kwargs) -> ExecutiveAnalysisRequest:
    defaults = {
        "workspace_id": "ws_1001",
        "project_id": "proj_1001",
        "deliberation_id": "delib_1001",
        "frame_version": 1,
        "role_key": "cfo",
        "question": "Assess Q3 cash runway with 20% burn increase",
        "role_pin": RolePin(
            role_key="cfo",
            assignment_id="assign_1",
            spec_id="cosa.executive.cfo",
            spec_version="1.0.0",
            spec_hash="hash_cfo",
            skill_pins=("skillpack:executive/cfo-advisor@1.0.0",),
        ),
        "evidence_refs": (
            EvidenceRef(
                source_ref="object://finance/q2-report",
                source_hash="sha256:abc",
                classification="internal",
            ),
        ),
    }
    defaults.update(kwargs)
    return ExecutiveAnalysisRequest(**defaults)


@pytest.mark.asyncio
async def test_peer_draft_is_forbidden():
    runner = ExecutiveBoardRunner()
    with pytest.raises(ExecutiveBoardInputError, match="PEER_DRAFT_FORBIDDEN"):
        await runner.run(make_request(peer_drafts=[{"claim": "spend $20k"}]))


@pytest.mark.asyncio
async def test_missing_claim_evidence_mapping_fails():
    runner = ExecutiveBoardRunner()
    # Model output missing claim-to-evidence mapping or options
    result = await runner.run(
        make_request(mock_model_output={"conclusion": "expand", "options": []})
    )
    assert result.kind == "executive.analysis.failed.v1"
    assert "EVIDENCE_MAPPING_REQUIRED" in result.error_detail or "OPTIONS_REQUIRED" in result.error_detail


@pytest.mark.asyncio
async def test_cross_project_evidence_fails():
    runner = ExecutiveBoardRunner()
    with pytest.raises(ExecutiveBoardInputError, match="CROSS_PROJECT_EVIDENCE_FORBIDDEN"):
        await runner.run(
            make_request(
                evidence_refs=(
                    EvidenceRef(
                        source_ref="object://finance/q2-report",
                        source_hash="sha256:abc",
                        classification="internal",
                        project_id="foreign_proj",
                    ),
                )
            )
        )


@pytest.mark.asyncio
async def test_successful_isolated_analysis_produces_completed_descriptor():
    runner = ExecutiveBoardRunner()
    mock_output = {
        "conclusion": "Runway is 9 months under base case; drops to 5.5 months under 20% burn stress.",
        "options": [
            {
                "title": "Maintain planned hiring",
                "trade_off": "Higher burn, runway reduced to 5.5 months",
            },
            {
                "title": "Defer non-critical marketing hires",
                "trade_off": "Preserves 7.5 months runway",
            },
        ],
        "evidence_claims": [
            {
                "claim": "Current cash balance is $450k",
                "source_ref": "object://finance/q2-report",
            }
        ],
        "assumptions": ["Revenue growth rate remains flat at 5% MoM"],
        "risks_and_unknowns": ["Uncollected receivables over 60 days"],
        "confidence": 0.85,
        "human_review_required": True,
    }

    result = await runner.run(make_request(mock_model_output=mock_output))
    assert result.kind == "executive.analysis.completed.v1"
    assert result.descriptor is not None
    assert result.descriptor["role_key"] == "cfo"
    assert result.descriptor["confidence"] == 0.85
    assert len(result.descriptor["options"]) == 2
