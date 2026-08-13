import asyncio
import json
import logging
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.snowflake import generate_snowflake_id
from app.core.tenancy import get_mvp_stage_scoped, get_stage_service_assessment_scoped
from app.modules.chat.ai_router import ChatTurn
from app.modules.chat.model_profiles import build_profile_provider, resolve_profile
from app.modules.chat.model_registry import is_provider_configured
from app.modules.strategy.ai_prompt_utils import consume_ai_stream
from app.modules.strategy.foundation_context import fetch_foundation_context
from app.modules.strategy.models import (
    CapabilityDefinition,
    ModelRunAudit,
    StageAssignment,
    StageServiceAssessment,
    StrategyAuditEvent,
    WorkspaceAgent,
)
from app.modules.strategy.schemas.project_orchestration_schemas import (
    ServiceAssessmentDecision,
    StagePlanDraft,
)

logger = logging.getLogger(__name__)

_PLAN_PROMPT = (
    "Bạn là chuyên gia tư vấn OKR và 12 Week Year. Dựa trên Foundation chiến lược (vision, "
    "mission, core values - có thể trống) và giả thuyết/phạm vi của một MVP stage dưới đây, "
    "hãy đề xuất kế hoạch thực thi gồm: 1-3 objectives bám sát vision/mission, mỗi objective "
    "có 2-5 key results đo lường được (title, target_value nếu có, unit nếu có), và ĐÚNG 12 "
    "trọng tâm tuần (weekly_focus) theo thứ tự tuần 1 đến 12. Trả lời DUY NHẤT một khối JSON "
    "hợp lệ theo cấu trúc sau, không kèm giải thích:\n"
    '{{"objectives": [{{"title": "...", "key_results": [{{"title": "...", '
    '"target_value": 0, "unit": "..."}}]}}], "weekly_focus": ["tuần 1 ...", ... 12 mục]}}\n\n'
    "Foundation chiến lược: {foundation_json}\n"
    "Dữ liệu stage: {stage_json}"
)

_ASSESSMENT_PROMPT = (
    "Bạn là bộ điều phối năng lực AI cho một MVP stage. Dựa trên Foundation chiến lược (vision, "
    "mission, core values - có thể trống) và danh sách năng lực (capability) dưới đây, hãy "
    "phân loại mỗi năng lực là REQUIRED, RECOMMENDED hoặc OPTIONAL cho stage này, kèm lý do "
    "ngắn gọn (reason) và kết quả kỳ vọng (expected_output). Chỉ liệt kê năng lực thực sự liên "
    "quan đến giả thuyết/phạm vi stage. Trả lời DUY NHẤT JSON:\n"
    '{{"assessments": [{{"capability_key": "...", "disposition": "REQUIRED", '
    '"reason": "...", "expected_output": "..."}}]}}\n\n'
    "Foundation chiến lược: {foundation_json}\n"
    "Dữ liệu stage và năng lực khả dụng: {routing_json}"
)


def _extract_json_block(raw_text: str) -> Optional[dict]:
    try:
        start = raw_text.index("{")
        end = raw_text.rindex("}") + 1
        return json.loads(raw_text[start:end])
    except Exception:
        return None


class RoutingService:
    def __init__(self, db: Session, workspace_id: int, brain_id: int, user_id: int):
        self.db = db
        self.workspace_id = workspace_id
        self.brain_id = brain_id
        self.user_id = user_id

    def _run_profile(self, profile: str, prompt: str) -> str:
        provider_name, model_name = resolve_profile(profile)
        if not is_provider_configured(provider_name):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI provider chưa cấu hình",
            )
        provider = build_profile_provider(profile)
        raw_text = asyncio.run(consume_ai_stream(provider, [ChatTurn(role="user", content=prompt)]))
        self.db.add(ModelRunAudit(
            id=generate_snowflake_id(),
            workspace_id=self.workspace_id,
            model_profile=f"{profile}:{provider_name}/{model_name}",
            prompt_tokens=len(prompt) // 4,
            completion_tokens=len(raw_text) // 4,
        ))
        return raw_text

    # ------------------------------------------------------------------
    # Stage plan preview (never persisted - only :activate persists it)
    # ------------------------------------------------------------------
    def plan_stage(self, mvp_stage_id: int) -> StagePlanDraft:
        stage = get_mvp_stage_scoped(self.db, mvp_stage_id, self.workspace_id, self.brain_id)
        foundation = fetch_foundation_context(self.db, self.workspace_id)
        prompt = _PLAN_PROMPT.format(
            foundation_json=json.dumps(foundation, ensure_ascii=False),
            stage_json=json.dumps(
                {"title": stage.title, "hypothesis": stage.hypothesis, "scope": stage.scope_jsonb.get("items", [])},
                ensure_ascii=False,
            ),
        )
        raw_text = self._run_profile("STRATEGIC_ANALYZER", prompt)
        parsed = _extract_json_block(raw_text)
        draft = None
        if parsed is not None:
            try:
                draft = StagePlanDraft.model_validate(parsed)
            except Exception:
                draft = None
        self.db.commit()
        if draft is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="AI trả về kế hoạch stage không hợp lệ, hãy nhập thủ công",
            )
        return draft

    # ------------------------------------------------------------------
    # Capability routing / service assessment
    # ------------------------------------------------------------------
    def _available_capability_keys(self) -> set:
        rows = (
            self.db.query(WorkspaceAgent.capability_keys_jsonb)
            .filter(WorkspaceAgent.workspace_id == self.workspace_id, WorkspaceAgent.is_active.is_(True))
            .all()
        )
        keys = set()
        for (capability_keys,) in rows:
            keys.update(capability_keys or [])
        return keys

    def generate_assessment(self, mvp_stage_id: int) -> List[StageServiceAssessment]:
        stage = get_mvp_stage_scoped(self.db, mvp_stage_id, self.workspace_id, self.brain_id)
        capabilities = (
            self.db.query(CapabilityDefinition)
            .filter(CapabilityDefinition.workspace_id == self.workspace_id)
            .all()
        )
        if not capabilities:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Workspace chưa có capability nào, hãy provision template trước",
            )
        by_key = {c.capability_key: c for c in capabilities}
        available_keys = self._available_capability_keys()

        dispositions = self._ai_dispositions(stage, capabilities)

        self.db.query(StageServiceAssessment).filter(
            StageServiceAssessment.mvp_stage_id == mvp_stage_id,
            StageServiceAssessment.status == "DRAFT",
        ).delete()

        assessments: List[StageServiceAssessment] = []
        for capability_key, (disposition, reason, expected_output) in dispositions.items():
            capability = by_key.get(capability_key)
            if capability is None:
                continue
            execution_mode = capability.supported_execution_modes_jsonb[0] if capability.supported_execution_modes_jsonb else "MANUAL"
            if capability.professional_review_required:
                execution_mode = "MANUAL"
            if capability.risk_level in ("HIGH", "REGULATED") and execution_mode == "AUTONOMOUS":
                execution_mode = "MANUAL"
            assessment = StageServiceAssessment(
                id=generate_snowflake_id(),
                workspace_id=self.workspace_id,
                brain_id=self.brain_id,
                mvp_stage_id=mvp_stage_id,
                capability_id=capability.id,
                disposition=disposition,
                reason=reason,
                risk_level=capability.risk_level,
                expected_output=expected_output,
                execution_mode=execution_mode,
                professional_review_required=capability.professional_review_required,
                is_available=capability_key in available_keys,
                status="DRAFT",
            )
            self.db.add(assessment)
            assessments.append(assessment)

        self.db.commit()
        for a in assessments:
            self.db.refresh(a)
        return assessments

    def _ai_dispositions(self, stage, capabilities: List[CapabilityDefinition]) -> dict:
        """capability_key -> (disposition, reason, expected_output).

        Falls back to a deterministic rule (Core Startup capabilities
        REQUIRED, everything else OPTIONAL) whenever the provider is
        unconfigured or returns output that fails schema validation - the
        assessment step must never be blocked by AI availability."""
        foundation = fetch_foundation_context(self.db, self.workspace_id)
        prompt = _ASSESSMENT_PROMPT.format(
            foundation_json=json.dumps(foundation, ensure_ascii=False),
            routing_json=json.dumps({
                "hypothesis": stage.hypothesis,
                "scope": stage.scope_jsonb.get("items", []),
                "capabilities": [{"capability_key": c.capability_key, "name": c.name} for c in capabilities],
            }, ensure_ascii=False),
        )
        provider_name, _ = resolve_profile("STRATEGIC_ANALYZER")
        if is_provider_configured(provider_name):
            try:
                raw_text = self._run_profile("STRATEGIC_ANALYZER", prompt)
                parsed = _extract_json_block(raw_text)
                if parsed and isinstance(parsed.get("assessments"), list):
                    valid_keys = {c.capability_key for c in capabilities}
                    result = {}
                    for item in parsed["assessments"]:
                        key = item.get("capability_key")
                        disposition = item.get("disposition")
                        if key in valid_keys and disposition in ("REQUIRED", "RECOMMENDED", "OPTIONAL"):
                            result[key] = (disposition, item.get("reason", ""), item.get("expected_output"))
                    if result:
                        return result
            except HTTPException:
                logger.warning("generate_assessment: AI routing call failed, using deterministic fallback")

        return {
            c.capability_key: (
                "REQUIRED" if c.capability_key.startswith("core_startup.") else "OPTIONAL",
                "Deterministic fallback: AI routing unavailable or returned invalid output",
                None,
            )
            for c in capabilities
        }

    def confirm_assessment(
        self, mvp_stage_id: int, decisions: List[ServiceAssessmentDecision]
    ) -> List[StageServiceAssessment]:
        get_mvp_stage_scoped(self.db, mvp_stage_id, self.workspace_id, self.brain_id)
        confirmed: List[StageServiceAssessment] = []
        assignments: List[StageAssignment] = []
        for decision in decisions:
            assessment = get_stage_service_assessment_scoped(self.db, int(decision.assessment_id), self.workspace_id)
            if assessment.mvp_stage_id != mvp_stage_id:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Stage service assessment not found")
            if not decision.approved:
                assessment.status = "REJECTED"
                continue
            if decision.execution_mode is not None:
                if assessment.risk_level in ("HIGH", "REGULATED") and decision.execution_mode == "AUTONOMOUS":
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="High-risk capability cannot run autonomously",
                    )
                if assessment.professional_review_required and decision.execution_mode == "AUTONOMOUS":
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Capability requiring professional review cannot run autonomously",
                    )
                assessment.execution_mode = decision.execution_mode
            assessment.status = "CONFIRMED"
            confirmed.append(assessment)

            capability = self.db.query(CapabilityDefinition).filter(
                CapabilityDefinition.id == assessment.capability_id
            ).first()
            assignment = StageAssignment(
                id=generate_snowflake_id(),
                workspace_id=self.workspace_id,
                brain_id=self.brain_id,
                mvp_stage_id=mvp_stage_id,
                assessment_id=assessment.id,
                title=f"{capability.name} - {assessment.disposition.lower()}" if capability else "Stage assignment",
                execution_mode=assessment.execution_mode,
                status="DRAFT",
            )
            self.db.add(assignment)
            assignments.append(assignment)

        self.db.add(StrategyAuditEvent(
            id=generate_snowflake_id(),
            workspace_id=self.workspace_id,
            mvp_stage_id=mvp_stage_id,
            event_type="FOUNDER_DECISION",
            actor_type="FOUNDER",
            actor_id=self.user_id,
            summary=f"Confirmed {len(confirmed)} service assessment(s)",
            payload_jsonb={"assessment_ids": [str(a.id) for a in confirmed]},
        ))
        self.db.commit()
        for a in confirmed:
            self.db.refresh(a)
        return confirmed
