from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any, Protocol

from agent.contracts.run import RunRequest, RunResult, RunStatus
from agent.contracts.spec import AgentSpec
from agent.executive_board.models import (
    BindingCriteria,
    BoardroomMemo,
    DissentRecord,
    ExecutiveAnalysisOutcome,
    ExecutiveAnalysisRequest,
    ExecutiveBoardInputError,
)
from agent.registry.repository import SpecRegistryRepository

OverlayValidator = Callable[[AgentSpec, AgentSpec], list[str]]


class AdvisorKernel(Protocol):
    """Phần tối thiểu của `ExecutionKernel` mà runner dùng — kernel thật hay adapter đi qua
    compliance/model routing (`apps/cosa`) đều thỏa."""

    async def run(self, request: RunRequest, spec: AgentSpec) -> RunResult: ...


class ExecutiveBoardRunner:
    """Isolated runner for Executive Advisory Board analyses.
    Enforces no-peer-drafts, cross-project data fencing, and strict claim-evidence mapping.
    """

    def __init__(
        self,
        kernel: AdvisorKernel,
        spec_registry: SpecRegistryRepository,
        overlay_validator: OverlayValidator,
    ) -> None:
        self._kernel = kernel
        self._spec_registry = spec_registry
        # Kiểm tra overlay ⊆ profile do composition layer (apps/cosa) cung cấp — bắt buộc,
        # không có mặc định "cho qua" để không thể chạy overlay chưa được kiểm phạm vi.
        self._overlay_validator = overlay_validator

    async def run(self, req: ExecutiveAnalysisRequest) -> ExecutiveAnalysisOutcome:
        """Chạy phân tích và gắn hash 2 pin (deployment + overlay) vào outcome — kể cả khi
        thất bại — để Company đối chiếu callback với frame đã persist."""
        outcome = await self._run_analysis(req)
        return outcome.model_copy(
            update={
                "deployment_pin_hash": req.execution_pin.deployment.identity_hash(),
                "overlay_pin_hash": req.execution_pin.overlay.identity_hash(),
            }
        )

    async def _run_analysis(self, req: ExecutiveAnalysisRequest) -> ExecutiveAnalysisOutcome:
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
        run_id: str | None = None
        if req.mock_model_output is not None:
            output = req.mock_model_output
        else:
            output, run_id = await self._run_kernel(req)

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
            "execution_pin": req.execution_pin.model_dump(),
        }
        if run_id is not None:
            descriptor["run_id"] = run_id

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

    async def _resolve_exact_agent_spec(
        self, *, spec_id: str, version: str, expected_hash: str, drift_code: str
    ) -> AgentSpec:
        """Resolve AgentSpec theo đúng id+version và bắt buộc hash khớp pin — không dùng
        "latest", không tin object Python đang import (drift khi rolling deploy)."""
        record = await self._spec_registry.get(spec_kind="agent", spec_id=spec_id, version=version)
        if record is None or record.definition_hash != expected_hash:
            raise ExecutiveBoardInputError(
                f"{drift_code}: '{spec_id}@{version}' is missing from registry or its hash "
                f"differs from the pinned {expected_hash[:12]}"
            )
        spec = AgentSpec(**record.content)
        if spec.compute_hash() != expected_hash:
            raise ExecutiveBoardInputError(
                f"{drift_code}: registry content of '{spec_id}@{version}' does not hash to the pin"
            )
        return spec

    async def _run_kernel(self, req: ExecutiveAnalysisRequest) -> tuple[dict[str, Any] | None, str]:
        pin = req.execution_pin
        # Cả 2 pin phải resolve đúng exact hash TRƯỚC khi gọi model.
        overlay_spec = await self._resolve_exact_agent_spec(
            spec_id=pin.overlay.overlay_spec_id,
            version=pin.overlay.overlay_spec_version,
            expected_hash=pin.overlay.overlay_spec_hash,
            drift_code="OVERLAY_PIN_DRIFT",
        )
        deployment_spec = await self._resolve_exact_agent_spec(
            spec_id=pin.deployment.spec_id,
            version=pin.deployment.spec_version,
            expected_hash=pin.deployment.spec_hash,
            drift_code="DEPLOYMENT_PIN_DRIFT",
        )
        pinned_skills = [
            (s.skill_id, s.version, s.definition_hash) for s in overlay_spec.pinned_skills
        ]
        expected_skills = [
            (s.skill_id, s.version, s.definition_hash) for s in pin.overlay.skill_pins
        ]
        if pinned_skills != expected_skills:
            raise ExecutiveBoardInputError(
                "OVERLAY_PIN_DRIFT: overlay skill pins differ from the frame's pinned skills"
            )
        violations = self._overlay_validator(overlay_spec, deployment_spec)
        if violations:
            raise ExecutiveBoardInputError(f"OVERLAY_SCOPE_VIOLATION: {'; '.join(violations)}")

        evidence_text = (
            "\n".join(
                f"- {ref.source_ref} (hash={ref.source_hash}, classification={ref.classification})"
                for ref in req.evidence_refs
            )
            or "(không có evidence nào được đính kèm)"
        )

        run_req = RunRequest(
            run_id=f"run_exec_{uuid.uuid4().hex[:16]}",
            principal=f"executive_board:{req.role_key}",
            workspace_id=req.workspace_id,
            conversation_id=f"deliberation:{req.deliberation_id}",
            root_executable_ref=overlay_spec.to_pinned_identity(),
            correlation_id=f"{req.deliberation_id}:{req.frame_version}:{req.role_key}",
            # `input` là phần duy nhất RunRecord persist (input_payload) — đặt 2 pin + scope ở đây
            # để run durable truy ngược được overlay và deployment đã dùng.
            input={
                "prompt": (
                    f"Câu hỏi deliberation: {req.question}\n\nEvidence:\n{evidence_text}\n\n"
                    "Chỉ đọc và đề xuất (advisory, L1_PROPOSE), không tự thực thi hành động nào. "
                    "Trả lời bằng đúng cấu trúc JSON được yêu cầu, không thêm văn bản ngoài JSON."
                ),
                "advisor_execution": {
                    "project_id": req.project_id,
                    "deliberation_id": req.deliberation_id,
                    "frame_version": req.frame_version,
                    "role_key": req.role_key,
                    "deployment": pin.deployment.model_dump(),
                    "overlay": pin.overlay.model_dump(),
                },
            },
            metadata={
                "project_id": req.project_id,
                "deliberation_id": req.deliberation_id,
                "frame_version": req.frame_version,
                "role_key": req.role_key,
                "project_agent_deployment_id": pin.deployment.project_agent_deployment_id,
                "deployment_spec_id": pin.deployment.spec_id,
                "deployment_spec_version": pin.deployment.spec_version,
                "deployment_spec_hash": pin.deployment.spec_hash,
                "advisor_overlay_spec_hash": pin.overlay.overlay_spec_hash,
            },
        )

        result = await self._kernel.run(run_req, overlay_spec)
        if result.status != RunStatus.COMPLETED:
            return None, result.run_id
        if not isinstance(result.final_output, dict):
            return None, result.run_id
        return result.final_output, result.run_id
