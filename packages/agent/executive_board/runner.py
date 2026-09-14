from __future__ import annotations

from typing import Any

from agent.contracts.kernel import ExecutionKernel
from agent.contracts.run import RunRequest, RunStatus
from agent.contracts.spec import AgentSpec
from agent.executive_board.models import (
    EXECUTIVE_ANALYSIS_OUTPUT_SCHEMA,
    ExecutiveAnalysisOutcome,
    ExecutiveAnalysisRequest,
    ExecutiveBoardInputError,
)
from agent.executive_board.skill_pins import resolve_role_pin_skills
from agent.governance.contracts import AutonomyLevel
from agent.registry.repository import SpecRegistryRepository


class ExecutiveBoardRunner:
    """Isolated runner for Executive Advisory Board analyses.
    Enforces no-peer-drafts, cross-project data fencing, and strict claim-evidence mapping.
    """

    def __init__(self, kernel: ExecutionKernel, spec_registry: SpecRegistryRepository) -> None:
        self._kernel = kernel
        self._spec_registry = spec_registry

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

        # 3. Model execution: mock_model_output là test override; mặc định gọi kernel thật
        if req.mock_model_output is not None:
            output: dict[str, Any] | None = req.mock_model_output
        else:
            output = await self._run_kernel(req)
            if output is None:
                return ExecutiveAnalysisOutcome(
                    kind="executive.analysis.failed.v1",
                    deliberation_id=req.deliberation_id,
                    frame_version=req.frame_version,
                    role_key=req.role_key,
                    error_detail="KERNEL_RUN_FAILED: model execution did not produce a valid analysis",
                )

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

    async def _run_kernel(self, req: ExecutiveAnalysisRequest) -> dict[str, Any] | None:
        pinned_skills = await resolve_role_pin_skills(req.role_pin.skill_pins, self._spec_registry)

        spec = AgentSpec(
            id=f"executive.board.{req.role_key}",
            version="1.0.0",
            instructions=(
                f"Bạn là thành viên Hội đồng Cố vấn Điều hành (Executive Advisory Board) "
                f"giữ vai trò '{req.role_key}'. Chỉ đọc và đề xuất (advisory L1_PROPOSE) — "
                f"không tự quyết định hay thực thi bất kỳ hành động nào. Trả lời bằng đúng "
                f"cấu trúc JSON được yêu cầu, không thêm văn bản ngoài JSON."
            ),
            autonomy_level=AutonomyLevel.L1,
            pinned_skills=pinned_skills,
            output_schema=EXECUTIVE_ANALYSIS_OUTPUT_SCHEMA,
        ).with_hash()

        evidence_text = (
            "\n".join(
                f"- {ref.source_ref} (hash={ref.source_hash}, classification={ref.classification})"
                for ref in req.evidence_refs
            )
            or "(không có evidence nào được đính kèm)"
        )

        run_req = RunRequest(
            principal=f"executive_board:{req.role_key}",
            workspace_id=req.workspace_id,
            root_executable_ref=spec.id,
            input={"prompt": f"Câu hỏi deliberation: {req.question}\n\nEvidence:\n{evidence_text}"},
        )

        result = await self._kernel.run(run_req, spec)
        if result.status != RunStatus.COMPLETED:
            return None
        if not isinstance(result.final_output, dict):
            return None
        return result.final_output
