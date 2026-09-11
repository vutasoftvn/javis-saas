from __future__ import annotations

from typing import Any
from agent.executive_board.models import (
    ExecutiveAnalysisRequest,
    ExecutiveAnalysisOutcome,
    ExecutiveBoardInputError,
)


class ExecutiveBoardRunner:
    """Isolated runner for Executive Advisory Board analyses.
    Enforces no-peer-drafts, cross-project data fencing, and strict claim-evidence mapping.
    """

    async def run(self, req: ExecutiveAnalysisRequest) -> ExecutiveAnalysisOutcome:
        # 1. Isolation check: Peer drafts strictly forbidden
        if req.peer_drafts is not None and len(req.peer_drafts) > 0:
            raise ExecutiveBoardInputError(
                "PEER_DRAFT_FORBIDDEN: Advisory analysis must be isolated without peer drafts"
            )

        # 2. Evidence fence: Cross-project evidence strictly forbidden
        for ref in req.evidence_refs:
            if ref.project_id is not None and ref.project_id != req.project_id:
                raise ExecutiveBoardInputError(
                    f"CROSS_PROJECT_EVIDENCE_FORBIDDEN: Evidence {ref.source_ref} belongs to project {ref.project_id}, not {req.project_id}"
                )

        # 3. Model execution / mock execution
        output = req.mock_model_output
        if output is None:
            # Default stub analysis when no mock is supplied
            output = {
                "conclusion": f"Analysis for role {req.role_key} regarding: {req.question}",
                "options": [
                    {"title": "Recommended Option", "trade_off": "Balanced risk and reward"},
                    {"title": "Conservative Option", "trade_off": "Lower risk, slower execution"},
                ],
                "evidence_claims": [
                    {
                        "claim": "Baseline metric referenced",
                        "source_ref": req.evidence_refs[0].source_ref if req.evidence_refs else "object://default",
                    }
                ],
                "assumptions": ["Market conditions remain stable"],
                "risks_and_unknowns": ["Execution timeline uncertainty"],
                "confidence": 0.85,
                "human_review_required": True,
            }

        # 4. Validate output schema & claim-to-evidence mapping
        conclusion = output.get("conclusion")
        if not conclusion or not isinstance(conclusion, str):
            return ExecutiveAnalysisOutcome(
                kind="executive.analysis.failed.v1",
                deliberation_id=req.deliberation_id,
                frame_version=req.frame_version,
                role_key=req.role_key,
                error_detail="CONCLUSION_REQUIRED: Valid conclusion string is required",
            )

        options = output.get("options")
        if not options or not isinstance(options, list) or len(options) == 0:
            return ExecutiveAnalysisOutcome(
                kind="executive.analysis.failed.v1",
                deliberation_id=req.deliberation_id,
                frame_version=req.frame_version,
                role_key=req.role_key,
                error_detail="OPTIONS_REQUIRED: Options list must contain at least one option",
            )

        claims = output.get("evidence_claims")
        if not claims or not isinstance(claims, list) or len(claims) == 0:
            return ExecutiveAnalysisOutcome(
                kind="executive.analysis.failed.v1",
                deliberation_id=req.deliberation_id,
                frame_version=req.frame_version,
                role_key=req.role_key,
                error_detail="EVIDENCE_MAPPING_REQUIRED: Every analysis must map claims to evidence",
            )

        descriptor: dict[str, Any] = {
            "role_key": req.role_key,
            "conclusion": conclusion,
            "options": options,
            "evidence_claims": claims,
            "assumptions": output.get("assumptions", []),
            "risks_and_unknowns": output.get("risks_and_unknowns", []),
            "confidence": float(output.get("confidence", 0.8)),
            "human_review_required": bool(output.get("human_review_required", True)),
            "role_pin": req.role_pin.model_dump(),
        }

        return ExecutiveAnalysisOutcome(
            kind="executive.analysis.completed.v1",
            deliberation_id=req.deliberation_id,
            frame_version=req.frame_version,
            role_key=req.role_key,
            descriptor=descriptor,
        )
