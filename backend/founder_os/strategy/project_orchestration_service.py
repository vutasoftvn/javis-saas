import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.snowflake import generate_snowflake_id
from core.tenancy import get_mvp_stage_scoped, get_project_scoped
from workforce.chat.model_registry import DEFAULT_PROVIDER, is_provider_configured
from workforce.chat.worker_prompt import run_worker_prompt_sync
from founder_os.strategy.cycle_governance_service import CycleGovernanceService
from founder_os.strategy.foundation_context import fetch_foundation_context
from founder_os.strategy.models import (
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
from founder_os.strategy.schemas.project_orchestration_schemas import (
    RoadmapDraft,
    RoadmapStageDraft,
    StagePlanDraft,
    StageRevisionChange,
)
from founder_os.strategy.vault_artifact_service import create_stage_artifact
from platform_core.vault.models import VaultDocument

logger = logging.getLogger(__name__)

_ROADMAP_PROMPT = (
    "Bạn là chuyên gia tư vấn khởi nghiệp và quản trị chiến lược. Dựa trên Foundation chiến lược (vision, mission, "
    "core values - có thể trống nếu workspace chưa duyệt Foundation) và brief dự án dưới "
    "đây (bao gồm ngày bắt đầu và dự kiến kết thúc nếu có để tính toán số tuần và phân bổ lộ trình), hãy đề xuất một lộ trình MVP (MVP roadmap) gồm 2 đến 4 giai đoạn (stage) tuần tự, bám sát vision/"
    "mission/core values khi phù hợp. Mỗi giai đoạn cần có: title (tiêu đề tiếng Việt ngắn gọn, tối đa 255 ký "
    "tự), hypothesis (giả thuyết tiếng Việt cần kiểm chứng, tối thiểu 20 ký tự), scope (danh sách việc "
    "sẽ làm bằng tiếng Việt, ít nhất 1 mục), non_goals (danh sách việc KHÔNG làm), exit_criteria (tiêu chí đo "
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


def _normalize_stage(item: dict) -> dict:
    title = str(item.get("title") or "Giai đoạn MVP").strip()
    if len(title) < 2:
        title = "Giai đoạn MVP"
    hypothesis = item.get("hypothesis")
    if isinstance(hypothesis, list):
        hypothesis = " ".join(str(h) for h in hypothesis)
    elif hypothesis is None:
        hypothesis = ""
    else:
        hypothesis = str(hypothesis).strip()

    def _to_list(val) -> list[str]:
        if val is None:
            return []
        if isinstance(val, list):
            return [str(x).strip() for x in val if str(x).strip()]
        if isinstance(val, str):
            lines = [l.strip("-* \t") for l in val.splitlines() if l.strip("-* \t")]
            return lines if lines else [val.strip()]
        return [str(val).strip()]

    scope = _to_list(item.get("scope"))
    if not scope:
        scope = ["Thực thi kế hoạch giai đoạn"]
    non_goals = _to_list(item.get("non_goals"))
    exit_criteria = _to_list(item.get("exit_criteria"))
    if not exit_criteria:
        exit_criteria = ["Hoàn thành các mục tiêu đề ra"]

    return {
        "title": title[:255],
        "hypothesis": hypothesis[:2000],
        "scope": scope,
        "non_goals": non_goals,
        "exit_criteria": exit_criteria,
    }


def _extract_roadmap_draft(raw_text: str) -> Optional[RoadmapDraft]:
    if not raw_text or not raw_text.strip():
        return None
    import re

    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", raw_text, flags=re.IGNORECASE).strip()

    start_brace = cleaned.find("{")
    start_bracket = cleaned.find("[")

    if start_brace == -1 and start_bracket == -1:
        logger.warning("generate_roadmap: No JSON block found in AI response: %s", raw_text[:500])
        return None

    if start_bracket != -1 and (start_brace == -1 or start_bracket < start_brace):
        end_bracket = cleaned.rfind("]")
        if end_bracket != -1 and end_bracket > start_bracket:
            json_str = cleaned[start_bracket : end_bracket + 1]
        else:
            json_str = cleaned[start_brace : cleaned.rfind("}") + 1] if start_brace != -1 else ""
    else:
        end_brace = cleaned.rfind("}")
        if end_brace != -1:
            json_str = cleaned[start_brace : end_brace + 1]
        else:
            json_str = ""

    if not json_str:
        logger.warning("generate_roadmap: Incomplete JSON bounds in AI response: %s", raw_text[:500])
        return None

    json_str_clean = re.sub(r",\s*([\]}])", r"\1", json_str)
    try:
        data = json.loads(json_str_clean)
    except Exception:
        try:
            data = json.loads(json_str)
        except Exception:
            logger.warning("generate_roadmap: Failed to parse JSON in AI response: %s", raw_text[:500])
            return None

    if isinstance(data, list):
        stages_raw = data
    elif isinstance(data, dict):
        stages_raw = (
            data.get("stages")
            or data.get("roadmap")
            or data.get("mvp_stages")
            or data.get("phases")
            or data.get("data")
        )
        if not isinstance(stages_raw, list):
            if "title" in data:
                stages_raw = [data]
            else:
                logger.warning("generate_roadmap: No stages array found in parsed dict: %s", str(data)[:500])
                return None
    else:
        logger.warning("generate_roadmap: Unexpected JSON root type %s", type(data))
        return None

    if not stages_raw:
        logger.warning("generate_roadmap: stages_raw is empty")
        return None

    normalized_stages = [_normalize_stage(s) for s in stages_raw if isinstance(s, dict)]
    if not normalized_stages:
        logger.warning("generate_roadmap: No valid stage dicts in stages_raw")
        return None

    try:
        return RoadmapDraft(stages=[RoadmapStageDraft(**s) for s in normalized_stages])
    except Exception as exc:
        logger.warning("generate_roadmap: RoadmapDraft validation failed: %s", exc)
        return None


class ProjectOrchestrationService:
    def __init__(self, db: Session, workspace_id: int, brain_id: int, user_id: int, role: str = "member"):
        self.db = db
        self.workspace_id = workspace_id
        self.brain_id = brain_id
        self.user_id = user_id
        self.role = role

    def generate_roadmap(self, project_id: int, instruction: Optional[str] = None) -> RoadmapDraft:
        """AI-proposed MVP roadmap. Never persisted - the founder edits and
        saves it explicitly through save_roadmap_draft before it exists as
        MvpStage rows.

        Model chạy ở agent-worker chứ không phải ở đây: brain-api không giữ khoá
        provider (xem chat/worker_prompt.py)."""
        project = get_project_scoped(self.db, project_id, self.workspace_id)

        if not is_provider_configured(DEFAULT_PROVIDER):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI provider chưa cấu hình, hãy nhập MVP roadmap thủ công",
            )

        foundation = fetch_foundation_context(self.db, self.workspace_id)
        project_dict = {
            "title": project.title,
            "description": project.description or "Không có mô tả",
        }
        start_val = getattr(project, "start_date", None)
        end_val = getattr(project, "end_date", None)
        if isinstance(start_val, datetime):
            project_dict["start_date"] = start_val.strftime("%Y-%m-%d")
        if isinstance(end_val, datetime):
            project_dict["end_date"] = end_val.strftime("%Y-%m-%d")
        if isinstance(start_val, datetime) and isinstance(end_val, datetime):
            total_days = max(1, (end_val - start_val).days)
            project_dict["duration_weeks"] = max(1, round(total_days / 7))

        prompt = _ROADMAP_PROMPT.format(
            foundation_json=json.dumps(foundation, ensure_ascii=False),
            project_json=json.dumps(project_dict, ensure_ascii=False),
        )
        if instruction and instruction.strip():
            prompt += f"\n\nYêu cầu tuỳ chỉnh bổ sung từ người dùng:\n{instruction.strip()}"

        result = run_worker_prompt_sync(
            self.db,
            brain_id=self.brain_id,
            prompt=prompt,
            title="AI MVP Roadmap",
            manual_hint="hãy nhập MVP roadmap thủ công",
        )

        draft = _extract_roadmap_draft(result.text)

        self.db.add(ModelRunAudit(
            id=generate_snowflake_id(),
            workspace_id=self.workspace_id,
            model_profile=f"STRATEGIC_ANALYZER:{result.provider}/{result.model}",
            prompt_tokens=len(prompt) // 4,
            completion_tokens=len(result.text) // 4,
            latency_ms=result.latency_ms,
            status="success" if draft is not None else "invalid_output",
        ))
        self.db.commit()

        if draft is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="AI trả về MVP roadmap không hợp lệ, hãy nhập thủ công",
            )
        return draft

    def list_stages(self, project_id: int) -> List[MvpStage]:
        """Fetch all persisted MvpStage rows for a project in this workspace."""
        get_project_scoped(self.db, project_id, self.workspace_id)
        return (
            self.db.query(MvpStage)
            .filter(
                MvpStage.workspace_id == self.workspace_id,
                MvpStage.project_id == project_id,
            )
            .order_by(MvpStage.sequence_no)
            .all()
        )

    def save_roadmap_draft(self, project_id: int, draft: RoadmapDraft, replace_all: bool = False) -> List[MvpStage]:
        """Persist the founder's (possibly AI-seeded, possibly hand-edited)
        roadmap as DRAFT stages. Replaces DRAFT stages (or all un-activated stages if replace_all)."""
        get_project_scoped(self.db, project_id, self.workspace_id)
        if replace_all:
            self.db.query(MvpStage).filter(
                MvpStage.project_id == project_id, MvpStage.status.in_(["DRAFT", "CONFIRMED"])
            ).delete()
        else:
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
        status_display = {
            "DRAFT": "Bản nháp",
            "CONFIRMED": "Đã xác nhận",
            "ACTIVE": "Đang thực hiện",
            "COMPLETED": "Đã hoàn thành",
            "CANCELLED": "Đã hủy",
        }
        lines = [
            "---",
            "doc_type: mvp_roadmap",
            f"title: Lộ trình phát triển MVP - {project_title}",
            f"stages_count: {len(stages)}",
            "---",
            "",
            f"# Lộ trình phát triển MVP - {project_title}",
            "",
        ]
        for stage in stages:
            scope_data = stage.scope_jsonb or {}
            exit_data = stage.exit_criteria_jsonb or {}
            st_text = status_display.get(stage.status, stage.status)
            is_done = stage.status == "COMPLETED"
            check_box = "[x]" if is_done else "[ ]"

            # Clean stage title if it already contains "Giai đoạn"
            title = stage.title.strip()
            if title.lower().startswith("giai đoạn"):
                stage_header = f"## {title} [{st_text}]"
            else:
                stage_header = f"## Giai đoạn {stage.sequence_no}: {title} [{st_text}]"

            lines.append(stage_header)
            lines.append(f"- **Trạng thái thực thi:** {st_text}")
            lines.append(f"- **Giả thuyết kiểm chứng:** {stage.hypothesis}")
            lines.append("")
            lines.append("**Phạm vi công việc:**")
            for item in scope_data.get("items", []):
                lines.append(f"- {check_box} {item}")
            non_goals = scope_data.get("non_goals", [])
            if non_goals:
                lines.append("")
                lines.append("**Không thuộc phạm vi:**")
                lines.extend(f"- {item}" for item in non_goals)
            lines.append("")
            lines.append("**Tiêu chí hoàn thành (Exit Criteria):**")
            for item in exit_data.get("items", []):
                lines.append(f"- {check_box} {item}")
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

        # Calculate Monday start_date for cycle & weekly plans
        # Base date is project start_date (if specified) or today
        now = datetime.utcnow()
        start_val = getattr(project, "start_date", None)
        base_date = start_val if isinstance(start_val, datetime) else now
        # Find Monday of base_date (weekday 0 is Monday)
        monday_start = (base_date - timedelta(days=base_date.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        num_weeks = len(approved_plan.weekly_focus) if approved_plan.weekly_focus else 12
        cycle_end = monday_start + timedelta(weeks=num_weeks) - timedelta(seconds=1)

        okr_cycle = OkrCycle(
            id=generate_snowflake_id(), workspace_id=self.workspace_id, brain_id=self.brain_id,
            mvp_stage_id=stage.id, name=f"{stage.title} OKRs",
            start_date=monday_start, end_date=cycle_end, status="active",
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
            project_id=project_id,
            mvp_stage_id=stage.id, okr_cycle_id=okr_cycle.id, theme=stage.title,
            duration_weeks=num_weeks,
            start_date=monday_start, end_date=cycle_end, status="active",
        )
        self.db.add(twelve_week_cycle)
        self.db.flush()

        weekly_plans = [
            WeeklyPlan(
                id=generate_snowflake_id(), workspace_id=self.workspace_id, cycle_id=twelve_week_cycle.id,
                week_no=week_no,
                start_date=monday_start + timedelta(weeks=week_no - 1),
                end_date=monday_start + timedelta(weeks=week_no) - timedelta(seconds=1),
                focus=focus,
            )
            for week_no, focus in enumerate(approved_plan.weekly_focus, 1)
        ]
        self.db.add_all(weekly_plans)

        stage.status = "ACTIVE"
        stage.template_snapshot_jsonb = template_snapshot
        stage.activated_at = now
        project.active_stage_id = stage.id

        # Re-render and sync mvp_roadmap.md into Vault with ACTIVE status
        all_stages = (
            self.db.query(MvpStage)
            .filter(MvpStage.project_id == project_id)
            .order_by(MvpStage.sequence_no)
            .all()
        )
        updated_markdown = self._render_roadmap_markdown(project.title, all_stages)
        create_stage_artifact(
            self.db, self.user_id, self.brain_id, self.role,
            project_id=project_id, artifact_kind="mvp_roadmap", content=updated_markdown,
        )

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
        if not is_provider_configured(DEFAULT_PROVIDER):
            return None
        try:
            prompt = _WEEK13_PROMPT.format(facts=json.dumps(facts, ensure_ascii=False))
            result = run_worker_prompt_sync(
                self.db,
                brain_id=self.brain_id,
                prompt=prompt,
                title="AI Week 13 Review",
                manual_hint="hãy tự quyết định dựa trên số liệu bên dưới",
            )
            raw_text = result.text
            self.db.add(ModelRunAudit(
                id=generate_snowflake_id(), workspace_id=self.workspace_id,
                model_profile=f"STRATEGIC_ANALYZER:{result.provider}/{result.model}",
                prompt_tokens=len(prompt) // 4, completion_tokens=len(raw_text) // 4,
                latency_ms=result.latency_ms,
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
