from __future__ import annotations

from typing import Any

from agent.contracts.kernel import ExecutionKernel
from agent.contracts.run import RunRequest, RunStatus
from agent.contracts.spec import AgentSpec
from agent.executive_board.models import (
    EXECUTIVE_ANALYSIS_OUTPUT_SCHEMA,
    BindingCriteria,
    BoardroomMemo,
    DissentRecord,
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
        output: dict[str, Any] | None
        if req.mock_model_output is not None:
            output = req.mock_model_output
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

        evidence_tag: str | None = None
        if req.context_snapshot_age_weeks > 2:
            evidence_tag = (
                f"🟡 Snapshot {req.context_snapshot_age_weeks}w old (Founder deferred review)"
            )
        elif req.context_snapshot_age_weeks > 0:
            evidence_tag = f"🟢 Snapshot {req.context_snapshot_age_weeks}w old (Fresh)"

        return ExecutiveAnalysisOutcome(
            kind="executive.analysis.completed.v1",
            deliberation_id=req.deliberation_id,
            frame_version=req.frame_version,
            role_key=req.role_key,
            descriptor=descriptor,
            context_snapshot_age_weeks=req.context_snapshot_age_weeks,
            evidence_tag=evidence_tag,
        )

    @staticmethod
    def synthesize_boardroom_deliberation(
        deliberation_id: str,
        question: str,
        outcomes: list[ExecutiveAnalysisOutcome],
        context_snapshot_id: str | None = None,
        context_snapshot_age_weeks: int = 0,
        devils_advocate_concerns: list[str] | None = None,
        binding_criteria: BindingCriteria | None = None,
        favored_option: str | None = None,
    ) -> BoardroomMemo:
        """Tổng hợp các phân tích độc lập (Phase 2 Isolation) thành Boardroom Memo hoàn chỉnh.
        Ghi nhận biểu quyết, phát hiện và lưu trữ nguyên văn ý kiến bảo lưu bất đồng (Preserved Dissent).
        """
        vote_tally: dict[str, str] = {}
        preserved_dissent: list[DissentRecord] = []
        option_support_count: dict[str, int] = {}

        for oc in outcomes:
            if oc.kind != "executive.analysis.completed.v1" or not oc.descriptor:
                continue
            role = oc.role_key
            options = oc.descriptor.get("options", [])
            chosen_title = (
                options[0]["title"] if options else oc.descriptor.get("conclusion", "Unknown")
            )
            vote_tally[role] = chosen_title
            option_support_count[chosen_title] = option_support_count.get(chosen_title, 0) + 1

        if favored_option:
            top_option = favored_option
        elif option_support_count:
            top_option = max(option_support_count.items(), key=lambda x: x[1])[0]
        else:
            top_option = "Chưa xác định phương án đa số"

        for oc in outcomes:
            if oc.kind != "executive.analysis.completed.v1" or not oc.descriptor:
                continue
            role = oc.role_key
            chosen = vote_tally.get(role)
            risks = oc.descriptor.get("risks_and_unknowns", [])
            confidence = oc.descriptor.get("confidence", 1.0)

            if chosen != top_option or confidence < 0.7:
                concern_text = "; ".join(risks) if risks else f"Ủng hộ phương án thay thế: {chosen}"
                preserved_dissent.append(
                    DissentRecord(
                        role_key=role,
                        advisor_name=f"{role.upper()} Advisor",
                        unresolved_concern=concern_text,
                        recommended_alternative=chosen if chosen != top_option else None,
                        preserved_at_week=context_snapshot_age_weeks,
                    )
                )

        if context_snapshot_age_weeks <= 2:
            memo_evidence_tag = f"🟢 Fresh Snapshot (W{context_snapshot_age_weeks})"
        else:
            memo_evidence_tag = (
                f"🟡 Assumed from Snapshot W{context_snapshot_age_weeks} (Founder deferred review)"
            )

        return BoardroomMemo(
            deliberation_id=deliberation_id,
            question=question,
            recommended_option=top_option,
            vote_tally=vote_tally,
            preserved_dissent=preserved_dissent,
            devils_advocate_concerns=devils_advocate_concerns or [],
            binding_criteria=binding_criteria or BindingCriteria(),
            status="AWAITING_FOUNDER_DECISION",
            context_snapshot_id=context_snapshot_id,
            context_snapshot_age_weeks=context_snapshot_age_weeks,
            evidence_tag=memo_evidence_tag,
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
