import asyncio
import json
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.snowflake import generate_snowflake_id
from app.core.tenancy import get_mvp_stage_scoped, get_project_scoped
from app.modules.chat.ai_router import ChatProvider, ChatTurn
from app.modules.chat.model_profiles import build_profile_provider, resolve_profile
from app.modules.chat.model_registry import is_provider_configured
from app.modules.strategy.cycle_governance_service import CycleGovernanceService
from app.modules.strategy.foundation_context import fetch_foundation_context
from app.modules.strategy.models import (
    KeyResult,
    ModelRunAudit,
    MvpStage,
    OkrCycle,
    OkrObjective,
    StageAssignment,
    StageRevision,
    StrategyAuditEvent,
    TwelveWeekCycle,
    WeeklyCommitment,
    WeeklyPlan,
    WorkspaceTemplate,
)
from app.modules.strategy.schemas.project_orchestration_schemas import (
    RoadmapDraft,
    StagePlanDraft,
    StageRevisionChange,
)
from app.modules.strategy.vault_artifact_service import create_stage_artifact
from app.modules.vault.models import VaultDocument

logger = logging.getLogger(__name__)

_ROADMAP_PROMPT = (
    "Bạn là chuyên gia tư vấn khởi nghiệp. Dựa trên Foundation chiến lược (vision, mission, "
    "core values - có thể trống nếu workspace chưa duyệt Foundation) và brief dự án dưới "
    "đây, hãy đề xuất một MVP roadmap gồm 2 đến 4 giai đoạn (stage) tuần tự, bám sát vision/"
    "mission/core values khi phù hợp. Mỗi giai đoạn cần có: title (ngắn gọn, tối đa 255 ký "
    "tự), hypothesis (giả thuyết cần kiểm chứng, tối thiểu 20 ký tự), scope (danh sách việc "
    "sẽ làm, ít nhất 1 mục), non_goals (danh sách việc KHÔNG làm), exit_criteria (tiêu chí đo "
    "lường được để coi giai đoạn hoàn thành, ít nhất 1 mục). Trả lời DUY NHẤT một khối JSON "
    "hợp lệ theo đúng cấu trúc sau, không kèm giải thích:\n"
    '{{"stages": [{{"title": "...", "hypothesis": "...", "scope": ["..."], '
    '"non_goals": ["..."], "exit_criteria": ["..."]}}]}}\n\n'
    "Foundation chiến lược: {foundation_json}\n"
    "Dữ liệu dự án: {project_json}"
)

_WEEK13_PROMPT = (
    "Bạn là cố vấn Week 13 cho một MVP stage. Dựa trên các số liệu thực tế dưới đây (đã "
    "tính toán sẵn, KHÔNG được bịa thêm số liệu), hãy đề xuất MỘT quyết định trong số: GO "
    "(tiến sang giai đoạn tiếp theo), ITERATE (giữ giai đoạn, sửa kế hoạch), HOLD (giữ "
    "nguyên, tiếp tục), STOP (dừng), PIVOT (đổi hướng giả thuyết). Trả lời DUY NHẤT JSON:\n"
    '{{"recommended_decision": "GO", "reasoning": "..."}}\n\n'
    "Số liệu: {facts}"
)


def _extract_roadmap_draft(raw_text: str) -> Optional[RoadmapDraft]:
    try:
        start = raw_text.index("{")
        end = raw_text.rindex("}") + 1
        data = json.loads(raw_text[start:end])
        return RoadmapDraft.model_validate(data)
    except Exception:
        logger.warning("generate_roadmap: AI response not a valid RoadmapDraft: %s", raw_text[:500])
        return None


class ProjectOrchestrationService:
    def __init__(self, db: Session, workspace_id: int, brain_id: int, user_id: int, role: str = "member"):
        self.db = db
        self.workspace_id = workspace_id
        self.brain_id = brain_id
        self.user_id = user_id
        self.role = role

    def generate_roadmap(self, project_id: int) -> RoadmapDraft:
        """AI-proposed MVP roadmap. Never persisted - the founder edits and
        saves it explicitly through save_roadmap_draft before it exists as
        MvpStage rows."""
        project = get_project_scoped(self.db, project_id, self.workspace_id)

        provider_name, model_name = resolve_profile("STRATEGIC_ANALYZER")
        if not is_provider_configured(provider_name):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI provider chưa cấu hình, hãy nhập MVP roadmap thủ công",
            )

        foundation = fetch_foundation_context(self.db, self.workspace_id)
        prompt = _ROADMAP_PROMPT.format(
            foundation_json=json.dumps(foundation, ensure_ascii=False),
            project_json=json.dumps(
                {"title": project.title, "description": project.description or "Không có mô tả"},
                ensure_ascii=False,
            ),
        )
        provider = build_profile_provider("STRATEGIC_ANALYZER")
        turns = [ChatTurn(role="user", content=prompt)]
        start = datetime.utcnow()
        raw_text = asyncio.run(self._consume_stream(provider, turns))
        latency_ms = int((datetime.utcnow() - start).total_seconds() * 1000)

        draft = _extract_roadmap_draft(raw_text)

        self.db.add(ModelRunAudit(
            id=generate_snowflake_id(),
            workspace_id=self.workspace_id,
            model_profile=f"STRATEGIC_ANALYZER:{provider_name}/{model_name}",
            prompt_tokens=len(prompt) // 4,
            completion_tokens=len(raw_text) // 4,
            latency_ms=latency_ms,
            status="success" if draft is not None else "invalid_output",
        ))
        self.db.commit()

        if draft is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="AI trả về MVP roadmap không hợp lệ, hãy nhập thủ công",
            )
        return draft

    @staticmethod
    async def _consume_stream(provider: ChatProvider, turns: List[ChatTurn]) -> str:
        chunks: List[str] = []
        async for event in provider.stream_chat(turns):
            if event.kind == "delta":
                chunks.append(event.content)
            elif event.kind == "failed":
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"AI provider lỗi: {event.error_code}",
                )
        return "".join(chunks)

    def save_roadmap_draft(self, project_id: int, draft: RoadmapDraft) -> List[MvpStage]:
        """Persist the founder's (possibly AI-seeded, possibly hand-edited)
        roadmap as DRAFT stages. Replaces only stages that are still DRAFT -
        a CONFIRMED-or-later roadmap must go through a stage revision instead."""
        get_project_scoped(self.db, project_id, self.workspace_id)
        self.db.query(MvpStage).filter(
            MvpStage.project_id == project_id, MvpStage.status == "DRAFT"
        ).delete()
        stages = [
            MvpStage(
                id=generate_snowflake_id(), workspace_id=self.workspace_id, brain_id=self.brain_id,
                project_id=project_id, sequence_no=index, title=item.title, hypothesis=item.hypothesis,
                scope_jsonb={"items": item.scope, "non_goals": item.non_goals},
                exit_criteria_jsonb={"items": item.exit_criteria}, status="DRAFT",
            )
            for index, item in enumerate(draft.stages, 1)
        ]
        self.db.add_all(stages)
        self.db.commit()
        return stages

    def confirm_roadmap(self, project_id: int) -> List[MvpStage]:
        """Locks in the saved DRAFT roadmap: DRAFT -> CONFIRMED, writes the
        Vault roadmap artefact, and records an audit event. A project with no
        saved draft has nothing to confirm."""
        project = get_project_scoped(self.db, project_id, self.workspace_id)
        stages = (
            self.db.query(MvpStage)
            .filter(MvpStage.project_id == project_id, MvpStage.status == "DRAFT")
            .order_by(MvpStage.sequence_no)
            .all()
        )
        if not stages:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Chưa có MVP roadmap nháp để xác nhận",
            )
        for stage in stages:
            stage.status = "CONFIRMED"

        markdown = self._render_roadmap_markdown(project.title, stages)
        revision = create_stage_artifact(
            self.db, self.user_id, self.brain_id, self.role,
            project_id=project_id, artifact_kind="mvp_roadmap", content=markdown,
        )

        self.db.add(StrategyAuditEvent(
            id=generate_snowflake_id(),
            workspace_id=self.workspace_id,
            project_id=project_id,
            event_type="FOUNDER_DECISION",
            actor_type="FOUNDER",
            actor_id=self.user_id,
            summary=f"Confirmed MVP roadmap with {len(stages)} stage(s)",
            payload_jsonb={"stage_ids": [str(s.id) for s in stages], "vault_revision_id": str(revision.id)},
        ))
        self.db.commit()
        for stage in stages:
            self.db.refresh(stage)
        return stages

    @staticmethod
    def _render_roadmap_markdown(project_title: str, stages: List[MvpStage]) -> str:
        lines = [f"# MVP Roadmap - {project_title}", ""]
        for stage in stages:
            lines.append(f"## Stage {stage.sequence_no}: {stage.title}")
            lines.append("")
            lines.append(f"**Hypothesis:** {stage.hypothesis}")
            lines.append("")
            lines.append("**Scope:**")
            lines.extend(f"- {item}" for item in stage.scope_jsonb.get("items", []))
            non_goals = stage.scope_jsonb.get("non_goals", [])
            if non_goals:
                lines.append("")
                lines.append("**Non-goals:**")
                lines.extend(f"- {item}" for item in non_goals)
            lines.append("")
            lines.append("**Exit criteria:**")
            lines.extend(f"- {item}" for item in stage.exit_criteria_jsonb.get("items", []))
            lines.append("")
        return "\n".join(lines)

    def activate_stage(self, project_id: int, stage_id: int, approved_plan: StagePlanDraft) -> dict:
        """Activates a CONFIRMED stage in one transaction: snapshots the
        workspace's local template versions, creates its OKR cycle/12WY
        cycle/12 weekly plans from the founder-approved plan, and sets it as
        the project's one active stage. Rejects a second active stage with
        409 instead of surfacing the partial-unique-index IntegrityError."""
        project = get_project_scoped(self.db, project_id, self.workspace_id)
        stage = get_mvp_stage_scoped(self.db, stage_id, self.workspace_id, self.brain_id)
        if stage.project_id != project_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="MVP stage not found")
        if stage.status != "CONFIRMED":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Only a CONFIRMED stage can be activated",
            )
        already_active = self.db.query(MvpStage).filter(
            MvpStage.project_id == project_id, MvpStage.status == "ACTIVE",
        ).first()
        if already_active is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Project already has an active stage",
            )

        template_snapshot = {
            str(t.id): t.active_version_no
            for t in self.db.query(WorkspaceTemplate).filter(WorkspaceTemplate.workspace_id == self.workspace_id).all()
        }

        now = datetime.utcnow()
        okr_cycle = OkrCycle(
            id=generate_snowflake_id(), workspace_id=self.workspace_id, brain_id=self.brain_id,
            mvp_stage_id=stage.id, name=f"{stage.title} OKRs", start_date=now, status="active",
        )
        self.db.add(okr_cycle)
        self.db.flush()

        for objective_draft in approved_plan.objectives:
            objective = OkrObjective(
                id=generate_snowflake_id(), workspace_id=self.workspace_id, cycle_id=okr_cycle.id,
                title=objective_draft.title, status="active",
            )
            self.db.add(objective)
            self.db.flush()
            for kr_draft in objective_draft.key_results:
                self.db.add(KeyResult(
                    id=generate_snowflake_id(), workspace_id=self.workspace_id, objective_id=objective.id,
                    title=kr_draft.title, target_value=kr_draft.target_value, unit=kr_draft.unit,
                    status="active",
                ))

        twelve_week_cycle = TwelveWeekCycle(
            id=generate_snowflake_id(), workspace_id=self.workspace_id, brain_id=self.brain_id,
            mvp_stage_id=stage.id, okr_cycle_id=okr_cycle.id, theme=stage.title,
            start_date=now, status="active",
        )
        self.db.add(twelve_week_cycle)
        self.db.flush()

        weekly_plans = [
            WeeklyPlan(
                id=generate_snowflake_id(), workspace_id=self.workspace_id, cycle_id=twelve_week_cycle.id,
                week_no=week_no, focus=focus,
            )
            for week_no, focus in enumerate(approved_plan.weekly_focus, 1)
        ]
        self.db.add_all(weekly_plans)

        stage.status = "ACTIVE"
        stage.template_snapshot_jsonb = template_snapshot
        stage.activated_at = now
        project.active_stage_id = stage.id

        self.db.add(StrategyAuditEvent(
            id=generate_snowflake_id(),
            workspace_id=self.workspace_id,
            project_id=project_id,
            mvp_stage_id=stage.id,
            event_type="FOUNDER_DECISION",
            actor_type="FOUNDER",
            actor_id=self.user_id,
            summary=f"Activated stage '{stage.title}'",
            payload_jsonb={"okr_cycle_id": str(okr_cycle.id), "twelve_week_cycle_id": str(twelve_week_cycle.id)},
        ))

        self.db.commit()
        self.db.refresh(stage)
        return {"stage": stage, "okr_cycle": okr_cycle, "weekly_plans": weekly_plans}

    # ------------------------------------------------------------------
    # Stage revision preview / apply
    # ------------------------------------------------------------------
    def _stage_snapshot(self, stage: MvpStage) -> dict:
        return {
            "hypothesis": stage.hypothesis,
            "scope": stage.scope_jsonb.get("items", []),
            "non_goals": stage.scope_jsonb.get("non_goals", []),
            "exit_criteria": stage.exit_criteria_jsonb.get("items", []),
        }

    def _latest_cycle_pair(self, stage_id: int):
        okr_cycle = (
            self.db.query(OkrCycle).filter(OkrCycle.mvp_stage_id == stage_id)
            .order_by(OkrCycle.id.desc()).first()
        )
        twelve_week_cycle = (
            self.db.query(TwelveWeekCycle).filter(TwelveWeekCycle.mvp_stage_id == stage_id)
            .order_by(TwelveWeekCycle.id.desc()).first()
        )
        return okr_cycle, twelve_week_cycle

    def _compute_revision_impact(self, stage: MvpStage, change_type: str) -> dict:
        preserve_evidence_document_ids = [
            str(d.id) for d in self.db.query(VaultDocument.id).filter(
                VaultDocument.brain_id == self.brain_id,
                VaultDocument.path.like(f"projects/%/stages/{stage.id}/%"),
            ).all()
        ]
        supersede_weekly_commitment_ids: List[str] = []
        supersede_assignment_ids: List[str] = []
        if change_type == "MATERIAL":
            _okr_cycle, twelve_week_cycle = self._latest_cycle_pair(stage.id)
            if twelve_week_cycle is not None:
                plan_ids = [
                    p.id for p in self.db.query(WeeklyPlan.id)
                    .filter(WeeklyPlan.cycle_id == twelve_week_cycle.id).all()
                ]
                if plan_ids:
                    unstarted = self.db.query(WeeklyCommitment).filter(
                        WeeklyCommitment.weekly_plan_id.in_(plan_ids),
                        WeeklyCommitment.status == "todo",
                    ).all()
                    supersede_weekly_commitment_ids = [str(c.id) for c in unstarted]
            unstarted_assignments = self.db.query(StageAssignment).filter(
                StageAssignment.mvp_stage_id == stage.id,
                StageAssignment.status.in_(["DRAFT", "APPROVED"]),
            ).all()
            supersede_assignment_ids = [str(a.id) for a in unstarted_assignments]

        return {
            "change_type": change_type,
            "supersede_weekly_commitment_ids": supersede_weekly_commitment_ids,
            "supersede_assignment_ids": supersede_assignment_ids,
            "preserve_evidence_document_ids": preserve_evidence_document_ids,
        }

    def preview_stage_revision(self, stage_id: int, changes: StageRevisionChange) -> StageRevision:
        stage = get_mvp_stage_scoped(self.db, stage_id, self.workspace_id, self.brain_id)
        if stage.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Only an active stage can be revised",
            )

        before = self._stage_snapshot(stage)
        after = dict(before)
        if changes.hypothesis is not None:
            after["hypothesis"] = changes.hypothesis
        if changes.scope is not None:
            after["scope"] = changes.scope
        if changes.non_goals is not None:
            after["non_goals"] = changes.non_goals
        if changes.exit_criteria is not None:
            after["exit_criteria"] = changes.exit_criteria

        material = (
            after["hypothesis"] != before["hypothesis"]
            or set(after["scope"]) != set(before["scope"])
            or set(after["exit_criteria"]) != set(before["exit_criteria"])
        )
        change_type = "MATERIAL" if material else "MINOR"
        impact = self._compute_revision_impact(stage, change_type)

        next_revision_no = (
            self.db.query(func.max(StageRevision.revision_no))
            .filter(StageRevision.mvp_stage_id == stage_id).scalar() or 0
        ) + 1
        revision = StageRevision(
            id=generate_snowflake_id(),
            workspace_id=self.workspace_id,
            brain_id=self.brain_id,
            mvp_stage_id=stage_id,
            revision_no=next_revision_no,
            change_type=change_type,
            before_snapshot_jsonb=before,
            after_snapshot_jsonb=after,
            impact_preview_jsonb=impact,
            status="PREVIEWED",
            created_by=self.user_id,
        )
        self.db.add(revision)
        self.db.commit()
        self.db.refresh(revision)
        return revision

    def apply_stage_revision(self, stage_id: int, revision_id: int) -> MvpStage:
        stage = get_mvp_stage_scoped(self.db, stage_id, self.workspace_id, self.brain_id)
        revision = self.db.query(StageRevision).filter(
            StageRevision.id == revision_id,
            StageRevision.mvp_stage_id == stage_id,
            StageRevision.workspace_id == self.workspace_id,
        ).first()
        if revision is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Stage revision not found")

        pending = self.db.query(StageRevision).filter(
            StageRevision.mvp_stage_id == stage_id, StageRevision.status == "PREVIEWED",
        ).order_by(StageRevision.revision_no.desc()).first()
        if pending is None or pending.id != revision.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Revision is not the current pending preview; generate a new preview",
            )

        after = revision.after_snapshot_jsonb
        stage.hypothesis = after["hypothesis"]
        stage.scope_jsonb = {"items": after["scope"], "non_goals": after["non_goals"]}
        stage.exit_criteria_jsonb = {"items": after["exit_criteria"]}

        impact = revision.impact_preview_jsonb
        for commitment_id in impact.get("supersede_weekly_commitment_ids", []):
            commitment = self.db.query(WeeklyCommitment).filter(WeeklyCommitment.id == int(commitment_id)).first()
            if commitment is not None:
                commitment.status = "cancelled"
        for assignment_id in impact.get("supersede_assignment_ids", []):
            assignment = self.db.query(StageAssignment).filter(StageAssignment.id == int(assignment_id)).first()
            if assignment is not None:
                assignment.status = "SUPERSEDED"

        revision.status = "APPLIED"
        revision.applied_at = datetime.utcnow()

        self.db.add(StrategyAuditEvent(
            id=generate_snowflake_id(),
            workspace_id=self.workspace_id,
            mvp_stage_id=stage.id,
            event_type="FOUNDER_DECISION",
            actor_type="FOUNDER",
            actor_id=self.user_id,
            summary=f"Applied {revision.change_type.lower()} revision #{revision.revision_no} to stage",
            payload_jsonb={"revision_id": str(revision.id)},
        ))

        self.db.commit()
        self.db.refresh(stage)
        return stage

    # ------------------------------------------------------------------
    # Week 13 gate
    # ------------------------------------------------------------------
    def generate_week13(self, stage_id: int) -> dict:
        stage = get_mvp_stage_scoped(self.db, stage_id, self.workspace_id, self.brain_id)
        okr_cycle, twelve_week_cycle = self._latest_cycle_pair(stage.id)

        kr_checkins = []
        if okr_cycle is not None:
            objectives = self.db.query(OkrObjective).filter(OkrObjective.cycle_id == okr_cycle.id).all()
            for objective in objectives:
                for kr in self.db.query(KeyResult).filter(KeyResult.objective_id == objective.id).all():
                    kr_checkins.append({
                        "title": kr.title, "target_value": kr.target_value, "current_value": kr.current_value,
                    })

        completed_commitments = 0
        total_commitments = 0
        if twelve_week_cycle is not None:
            plan_ids = [
                p.id for p in self.db.query(WeeklyPlan.id)
                .filter(WeeklyPlan.cycle_id == twelve_week_cycle.id).all()
            ]
            if plan_ids:
                commitments = self.db.query(WeeklyCommitment).filter(WeeklyCommitment.weekly_plan_id.in_(plan_ids)).all()
                total_commitments = len(commitments)
                completed_commitments = sum(1 for c in commitments if c.status == "done")

        evidence_document_count = self.db.query(VaultDocument).filter(
            VaultDocument.brain_id == self.brain_id,
            VaultDocument.path.like(f"projects/%/stages/{stage.id}/%"),
        ).count()

        facts = {
            "kr_checkins": kr_checkins,
            "completed_commitments": completed_commitments,
            "total_commitments": total_commitments,
            "missing_evidence": total_commitments > 0 and evidence_document_count == 0,
            "evidence_document_count": evidence_document_count,
        }
        return {"facts": facts, "ai_recommendation": self._ai_week13_recommendation(facts)}

    def _ai_week13_recommendation(self, facts: dict) -> Optional[dict]:
        """Best-effort only; a missing/invalid AI response leaves this None -
        Week 13 always shows calculated facts even without AI."""
        provider_name, model_name = resolve_profile("STRATEGIC_ANALYZER")
        if not is_provider_configured(provider_name):
            return None
        try:
            prompt = _WEEK13_PROMPT.format(facts=json.dumps(facts, ensure_ascii=False))
            provider = build_profile_provider("STRATEGIC_ANALYZER")
            raw_text = asyncio.run(self._consume_stream(provider, [ChatTurn(role="user", content=prompt)]))
            self.db.add(ModelRunAudit(
                id=generate_snowflake_id(), workspace_id=self.workspace_id,
                model_profile=f"STRATEGIC_ANALYZER:{provider_name}/{model_name}",
                prompt_tokens=len(prompt) // 4, completion_tokens=len(raw_text) // 4,
            ))
            self.db.commit()
            start = raw_text.index("{")
            end = raw_text.rindex("}") + 1
            parsed = json.loads(raw_text[start:end])
            decision = parsed.get("recommended_decision")
            if decision not in ("GO", "ITERATE", "HOLD", "STOP", "PIVOT"):
                return None
            return {"recommended_decision": decision, "reasoning": parsed.get("reasoning", "")}
        except Exception:
            logger.warning("generate_week13: AI recommendation unavailable, showing facts only", exc_info=True)
            return None

    def confirm_week13(self, stage_id: int, decision: str, rationale: str) -> dict:
        stage = get_mvp_stage_scoped(self.db, stage_id, self.workspace_id, self.brain_id)
        if stage.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Only an active stage has a Week 13 gate to confirm",
            )

        governance = CycleGovernanceService(self.db, self.workspace_id, self.user_id)
        gate = governance.record_gate_decision(
            project_id=stage.project_id, decision=decision, rationale=rationale, mvp_stage_id=stage.id,
        )

        decision_upper = decision.upper()
        if decision_upper == "GO":
            stage.status = "COMPLETED"
        elif decision_upper in ("STOP", "PIVOT"):
            stage.status = "STOPPED"
        # ITERATE / HOLD leave the stage ACTIVE - the founder follows up with
        # a stage revision (ITERATE) or simply keeps executing (HOLD).

        if decision_upper in ("GO", "STOP", "PIVOT"):
            okr_cycle, twelve_week_cycle = self._latest_cycle_pair(stage.id)
            if okr_cycle is not None:
                okr_cycle.status = "archived"
            if twelve_week_cycle is not None:
                twelve_week_cycle.status = "archived"

        self.db.commit()
        self.db.refresh(stage)
        return {"stage": stage, "gate_decision": gate}
