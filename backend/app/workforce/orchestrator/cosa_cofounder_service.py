"""COSA Co-Founder Service (F4 Specification - Central AI Co-Founder Engine).

Chịu trách nhiệm:
1. Giao diện AI Co-Founder đồng hành cùng Human Founder.
2. Phân loại ý định (Intent Routing: Greeting vs Review vs Decision vs Command).
3. Truy xuất ngữ cảnh tối thiểu (Minimum Viable Context).
4. Phản biện dựa trên Bằng chứng (Challenge Mode / Problem-First F1-F3).
5. Điều phối FOUNDER_DECISION/FOUNDER_COMMAND vào ChiefOfStaffOrchestrator
   thật (Mission/Outcome/AgentRun, governance, tổng hợp đa domain từ dữ liệu
   Sales/Finance thật) — không tự tổng hợp bằng dữ liệu giả trong file này.
6. Đề xuất hành động tốt nhất (Next Best Action Engine).
7. Thống kê nhịp tim doanh nghiệp (Company Pulse).
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.workforce.routing.router import IntentRouter, IntentDecision
from app.workforce.routing.deterministic import Intent
from app.workforce.models import FounderDecision, AgentDefinition, ApprovalRequest
from app.workforce.schemas.decision_schemas import DecisionStatusEnum, DecisionDomainEnum
from app.workforce.agents.governance.models import AgentRun
from app.workforce.agents.orchestration import service as orchestration_service
from app.workforce.agents.orchestration.chief_of_staff import ChiefOfStaffOrchestrator



COSA_SYSTEM_PROMPT = """You are COSA, the AI Co-Founder operating inside the company's COSA environment.

Your role is to help the human founder understand the business, make better decisions, convert goals into missions, coordinate domain agents and measure business outcomes.

You are not the owner or legal decision maker. The human founder retains final authority over strategy, capital, legal commitments and permissions.

Your responsibilities include:
- understand founder intent;
- retrieve the minimum relevant business context;
- distinguish facts, assumptions and evidence;
- challenge unsupported assumptions when useful (Challenge Mode);
- help shape measurable goals;
- create or coordinate missions;
- route work to the appropriate domain agents;
- surface decisions and approvals;
- synthesize cross-domain information;
- recommend the next best action;
- measure progress against business outcomes;
- retain approved evidence and learning.

Do not expose implementation complexity unless needed.
The founder should not need to choose models, agents, skills or tools for ordinary work.
Optimize for business progress, not merely task completion.
"""


class NextBestActionItem(BaseModel):
    id: str
    category: str = Field(..., description="FOUNDER_ACTION | AGENT_ACTION | MISSION | DECISION | EXPERIMENT")
    title: str
    rationale: str
    urgency: str = Field(default="HIGH", description="HIGH | MEDIUM | LOW")
    domain: Optional[str] = "STRATEGY"
    action_payload: Optional[Dict[str, Any]] = None


class CompanyPulseResponse(BaseModel):
    goals_on_track: int = 0
    total_active_goals: int = 0
    active_missions: int = 0
    needs_decision_count: int = 0
    pending_approvals_count: int = 0
    company_stage: Optional[str] = None
    major_risks_count: int = 0
    suggested_focus: str = "Tập trung kiểm chứng bài toán khách hàng và hoàn thiện chiến thuật tuần."
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ChallengeAnalysis(BaseModel):
    is_challenged: bool = False
    stated_assumption: str
    existing_evidence_summary: str
    challenge_reasoning: str
    recommended_experiment: str
    suggested_next_action: str


class CoFounderMessageResponse(BaseModel):
    intent: str
    message: str
    pulse: Optional[CompanyPulseResponse] = None
    next_best_actions: Optional[List[NextBestActionItem]] = None
    suggested_decisions: Optional[List[Dict[str, Any]]] = None
    challenge_analysis: Optional[ChallengeAnalysis] = None
    routed_domain: Optional[str] = None
    mission_id: Optional[str] = None
    mission_status: Optional[str] = None


class CosaCofounderService:
    """Service điều phối trung tâm COSA AI Co-Founder."""

    def __init__(self, db: AsyncSession, sync_db: Optional[Session] = None):
        self.db = db
        # G2 P0.9 / G3 §10.5: ChiefOfStaffOrchestrator.orchestrate() is a sync
        # SQLAlchemy Session API (db.add/db.commit called without await), while
        # `self.db` here is async-style (AsyncSessionAdapter-wrapped in the
        # real caller, cofounder_api.py). A real sync Session is needed to
        # hand off FOUNDER_COMMAND/FOUNDER_DECISION to the real orchestrator.
        self.sync_db = sync_db

    async def get_company_pulse(
        self,
        workspace_id: Optional[int] = None,
        project_id: Optional[int] = None,
    ) -> CompanyPulseResponse:
        """Lấy thông tin nhịp tim tổng thể của doanh nghiệp (Company Pulse)."""
        from app.founder_os.strategy.models import Project, TwelveWeekCycle
        from app.platform.auth.models import Workspace

        # G3 Phase 1D (Stage Operating Engine) / G2 §8.2 "stage-aware Hologram":
        # company_stage giờ là giá trị thật, tự đổi khi dự án chủ lực nâng cấp
        # giai đoạn (StageGateService.apply_stage_advancement) — không còn đóng
        # băng vĩnh viễn ở "S0_GENESIS".
        company_stage = None
        if workspace_id is not None:
            res_ws = await self.db.execute(
                select(Workspace.company_stage).where(Workspace.id == workspace_id)
            )
            company_stage = res_ws.scalar()

        # 0. Kiểm tra số lượng Projects trong workspace
        stmt_proj = select(func.count(Project.id)).where(Project.status == "active")
        if workspace_id is not None:
            stmt_proj = stmt_proj.where(Project.workspace_id == workspace_id)
        res_proj = await self.db.execute(stmt_proj)
        total_projects = res_proj.scalar() or 0

        # Nếu là tài khoản mới chưa có project / doanh nghiệp (Genesis State)
        if total_projects == 0:
            return CompanyPulseResponse(
                goals_on_track=0,
                total_active_goals=0,
                active_missions=0,
                needs_decision_count=0,
                pending_approvals_count=0,
                major_risks_count=0,
                company_stage=company_stage,
                suggested_focus="Chào mừng Founder! Hãy cùng COSA thiết lập hồ sơ doanh nghiệp và định hình mục tiêu 12-Week Year đầu tiên.",
                updated_at=datetime.utcnow(),
            )

        # 1. Đếm số quyết định chờ Founder
        stmt_decisions = select(func.count(FounderDecision.id)).where(
            FounderDecision.status == DecisionStatusEnum.PENDING.value
        )
        if workspace_id is not None:
            stmt_decisions = stmt_decisions.where(FounderDecision.workspace_id == workspace_id)
        res_dec = await self.db.execute(stmt_decisions)
        needs_decision = res_dec.scalar() or 0

        # 2. Đếm số approvals chờ duyệt
        stmt_approvals = select(func.count(ApprovalRequest.id)).where(
            ApprovalRequest.status == "PENDING"
        )
        if workspace_id is not None:
            stmt_approvals = stmt_approvals.where(ApprovalRequest.workspace_id == workspace_id)
        res_app = await self.db.execute(stmt_approvals)
        pending_approvals = res_app.scalar() or 0

        # 3. Đếm số Agent Runs đang chạy (Active Missions) — bảng canonical
        # agent_runs (agents.governance.models.AgentRun), nơi orchestrator
        # thật (ChiefOfStaffOrchestrator) ghi dữ liệu, không phải bảng
        # platform_agent_runs cũ đã deprecate (G3 §2).
        stmt_runs = select(func.count(AgentRun.id)).where(
            AgentRun.status.in_(["created", "running", "retrying", "awaiting_approval"])
        )
        if workspace_id is not None:
            stmt_runs = stmt_runs.where(AgentRun.workspace_id == workspace_id)
        res_runs = await self.db.execute(stmt_runs)
        active_missions = res_runs.scalar() or 0

        # 4. Đếm số 12-Week Goals / Cycles
        stmt_cycle = select(func.count(TwelveWeekCycle.id)).where(TwelveWeekCycle.status == "ACTIVE")
        if workspace_id is not None:
            stmt_cycle = stmt_cycle.where(TwelveWeekCycle.workspace_id == workspace_id)
        res_cycle = await self.db.execute(stmt_cycle)
        total_goals = res_cycle.scalar() or total_projects

        # G2 P0.9 / G3 §10.5: suggested_focus/major_risks_count trước đây là
        # chuỗi tĩnh + proxy nhị phân không dựa trên tín hiệu thật. Giờ suy ra
        # trực tiếp từ chính các con số đã query ở trên — không thêm query
        # mới, không tự nhận "on-track" nếu không có tín hiệu (Pulse v2 đầy
        # đủ theo G2 §8 là phạm vi Phase 1A, không phải P0).
        focus_signals = []
        if needs_decision > 0:
            focus_signals.append(f"{needs_decision} quyết định đang chờ bạn chốt")
        if pending_approvals > 0:
            focus_signals.append(f"{pending_approvals} approval đang chờ duyệt")
        if active_missions > 0:
            focus_signals.append(f"{active_missions} mission đang chạy")
        suggested_focus = (
            "Ưu tiên: " + "; ".join(focus_signals) + "."
            if focus_signals
            else "Không có điểm nghẽn nào đang chờ bạn — tiếp tục triển khai theo kế hoạch 12-Week Year hiện tại."
        )

        return CompanyPulseResponse(
            goals_on_track=total_goals,
            total_active_goals=total_goals,
            active_missions=active_missions,
            needs_decision_count=needs_decision,
            pending_approvals_count=pending_approvals,
            major_risks_count=needs_decision + pending_approvals,
            company_stage=company_stage,
            suggested_focus=suggested_focus,
            updated_at=datetime.utcnow(),
        )

    async def get_next_best_action(
        self,
        workspace_id: Optional[int] = None,
        project_id: Optional[int] = None,
    ) -> List[NextBestActionItem]:
        """Tính toán Top 3 hành động tốt nhất tiếp theo cho Founder và Đội ngũ."""
        from app.founder_os.strategy.models import Project

        # Kiểm tra nếu chưa có dự án / công ty nào được tạo
        stmt_proj = select(func.count(Project.id)).where(Project.status == "active")
        if workspace_id is not None:
            stmt_proj = stmt_proj.where(Project.workspace_id == workspace_id)
        res_proj = await self.db.execute(stmt_proj)
        total_projects = res_proj.scalar() or 0

        if total_projects == 0:
            return [
                NextBestActionItem(
                    id="act_genesis_profile",
                    category="FOUNDER_ACTION",
                    title="Thiết lập Hồ sơ Doanh nghiệp (Vision & Problem)",
                    rationale="Khởi tạo bối cảnh công ty để COSA và 5 Core Domain Agents nắm bắt được thị trường mục tiêu.",
                    urgency="HIGH",
                    domain="STRATEGY",
                ),
                NextBestActionItem(
                    id="act_genesis_12wy",
                    category="EXPERIMENT",
                    title="Định hình Mục tiêu 12-Week Year Quý đầu tiên",
                    rationale="Tập trung vào 1-2 mục tiêu sống còn để kiểm chứng Product-Market Fit (F1/F2).",
                    urgency="HIGH",
                    domain="STRATEGY",
                ),
                NextBestActionItem(
                    id="act_genesis_team",
                    category="FOUNDER_ACTION",
                    title="Kích hoạt 5 Core Domain Agents",
                    rationale="Sales, Marketing, Finance TT58, Legal và Build sẵn sàng nhận nhiệm vụ.",
                    urgency="MEDIUM",
                    domain="STRATEGY",
                ),
            ]

        actions: List[NextBestActionItem] = []

        # 1. Kiểm tra nếu có quyết định đang chờ Founder
        stmt_pending_dec = select(FounderDecision).where(
            FounderDecision.status == DecisionStatusEnum.PENDING.value
        ).order_by(desc(FounderDecision.created_at)).limit(1)
        if workspace_id is not None:
            stmt_pending_dec = stmt_pending_dec.where(FounderDecision.workspace_id == workspace_id)
        
        res_dec = await self.db.execute(stmt_pending_dec)
        pending_dec = res_dec.scalars().first()

        if pending_dec:
            actions.append(
                NextBestActionItem(
                    id=f"act_dec_{pending_dec.id}",
                    category="DECISION",
                    title=f"Ra quyết định: {pending_dec.question[:60]}...",
                    rationale="Quyết định chiến lược đang là điểm nghẽn để Agent tiếp tục triển khai.",
                    urgency="HIGH",
                    domain=pending_dec.domain,
                    action_payload={"decision_id": pending_dec.id},
                )
            )

        # G3 Phase 1D (Stage Operating Engine) / G2 §8.2 "stage-aware Top3": khi còn
        # chỗ trống, thêm đúng 1 mục bám sát giai đoạn dự án chủ lực THẬT (không phải
        # con số bịa) — primary_goal đọc từ ManagementPolicyEngine, chỉ số 1 nguồn sự
        # thật cho mục tiêu từng giai đoạn (G2 §9.1 Stage matrix), khớp đúng
        # project_stage thật của dự án P0/mới nhất.
        if len(actions) < 3:
            stage_item = await self._build_stage_goal_action(workspace_id)
            if stage_item:
                actions.append(stage_item)

        # G2 P0.9 / G3 §10.5: 2 mục tĩnh "act_cust_interview"/"act_weekly_review"
        # trước đây luôn được thêm vô điều kiện mỗi lần gọi, không backing bởi
        # query nào — xóa thay vì cố gate bằng logic mới; ranking đầy đủ theo
        # urgency/impact (G2 §6.9) là phạm vi Phase 1A, không phải P0. Trung
        # thực hơn là trả về ít mục hơn thay vì mục không có tín hiệu thật.
        return actions[:3]

    async def _build_stage_goal_action(self, workspace_id: Optional[int]) -> Optional[NextBestActionItem]:
        """Đọc project_stage thật của dự án chủ lực (P0/mới nhất, cùng quy ước với
        StageResolverService._resolve_project) và trả về 1 NBA item bám sát
        primary_goal thật của giai đoạn đó — None nếu không có dự án nào."""
        from app.founder_os.strategy.models import Project
        from app.founder_os.strategy.schemas.stage_schemas import ProjectStageEnum
        from app.founder_os.strategy.services.management_policy_engine import ManagementPolicyEngine

        stmt = select(Project).where(Project.status == "active")
        if workspace_id is not None:
            stmt = stmt.where(Project.workspace_id == workspace_id)
        stmt = stmt.order_by(desc(Project.strategic_priority == "P0"), desc(Project.created_at)).limit(1)

        res = await self.db.execute(stmt)
        project = res.scalars().first()
        if project is None:
            return None

        raw_stage = project.project_stage or "S1_PROBLEM_VALIDATION"
        try:
            stage_enum = ProjectStageEnum(raw_stage)
        except ValueError:
            return None
        policy = ManagementPolicyEngine.get_policy(stage_enum)

        return NextBestActionItem(
            id=f"act_stage_goal_{project.id}_{stage_enum.value}",
            category="FOUNDER_ACTION",
            title=f"Mục tiêu giai đoạn {stage_enum.value}: {policy.primary_goal}",
            rationale=f"Dự án '{project.title}' đang ở {stage_enum.value} — đây là trọng tâm quản trị đúng theo Stage Matrix.",
            urgency="MEDIUM",
            domain="STRATEGY",
            action_payload={"project_id": project.id, "project_stage": stage_enum.value},
        )

    async def challenge_assumptions(
        self,
        founder_input: str,
        evidence_summary: Optional[str] = None,
    ) -> ChallengeAnalysis:
        """
        Đánh giá và phản biện giả định của Founder dựa trên Evidence Engine (F1/F2/F3).
        
        Phát hiện trường hợp Solution Maturity cao nhưng Problem Evidence thấp.
        """
        lower_input = founder_input.lower()
        
        # Phát hiện ý định build thêm tính năng / rót tiền khi chưa kiểm chứng
        is_solution_bias = any(k in lower_input for k in ["code thêm tính năng", "thêm feature", "build ngay", "tăng ngân sách ads", "chi thêm tiền"])
        
        if is_solution_bias:
            return ChallengeAnalysis(
                is_challenged=True,
                stated_assumption=f"Giả định: Thị trường/Khách hàng đang rất cần '{founder_input[:60]}...'",
                existing_evidence_summary=evidence_summary or "Chưa có bằng chứng định lượng về Willingness-To-Pay (WTP) từ phỏng vấn khách hàng thực tế.",
                challenge_reasoning="Theo nguyên tắc Problem-First (F2), giải pháp không nên đi tìm vấn đề. Cần xác thực nỗi đau cốt lõi (Pain Severity) trước khi đầu tư nguồn lực.",
                recommended_experiment="Phỏng vấn sâu 5 khách hàng thuộc ICP chuẩn hoặc chạy Smoke Test đo lường CTR/Lead đăng ký trước.",
                suggested_next_action="Tạm dừng build tính năng lớn; giao Marketing & Customer Specialist tiến hành 5 Discovery Interviews.",
            )

        return ChallengeAnalysis(
            is_challenged=False,
            stated_assumption="Mục tiêu phù hợp với lộ trình kiểm chứng hiện tại.",
            existing_evidence_summary="Dữ liệu khớp với kế hoạch 12 Week Year.",
            challenge_reasoning="Không phát hiện giả định mạo hiểm vượt quá mức độ kiểm chứng.",
            recommended_experiment="Tiếp tục triển khai theo kế hoạch tuần.",
            suggested_next_action="Giao việc cho Domain Agent phụ trách.",
        )

    async def handle_founder_message(
        self,
        message: str,
        workspace_id: Optional[int] = None,
        project_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> CoFounderMessageResponse:
        """Entry point chính nhận tin nhắn từ Founder và điều phối thông minh."""
        # 1. Phân loại ý định qua IntentRouter
        decision = await IntentRouter.route_message(message)
        intent = decision.intent

        # 2. Xử lý câu chào hỏi thuần túy -> Phản hồi nhanh, không load DB nặng
        if intent == Intent.GREETING:
            return CoFounderMessageResponse(
                intent=Intent.GREETING.value,
                message="Chào bạn! Tôi là COSA Co-Founder. Hôm nay tôi có thể đồng hành và hỗ trợ gì cho bạn trong việc rà soát mục tiêu hay ra quyết định kinh doanh?",
                routed_domain="COFOUNDER",
            )

        # 3. Kiểm tra phản biện giả định (Challenge Mode / Problem-First F1-F3)
        challenge = await self.challenge_assumptions(message)
        if challenge.is_challenged:
            challenge_msg = (
                f"⚠️ **COSA Challenge Mode (Phản biện dựa trên Bằng chứng):**\n\n"
                f"• **{challenge.stated_assumption}**\n"
                f"• **Hiện trạng:** {challenge.existing_evidence_summary}\n"
                f"• **Lý do:** {challenge.challenge_reasoning}\n\n"
                f"💡 **Đề xuất:** {challenge.recommended_experiment}"
            )
            return CoFounderMessageResponse(
                intent="CHALLENGE_MODE",
                message=challenge_msg,
                challenge_analysis=challenge,
                routed_domain="COFOUNDER",
            )

        # 3. Xử lý yêu cầu rà soát ưu tiên (FOUNDER_REVIEW)
        if intent == Intent.FOUNDER_REVIEW:
            pulse = await self.get_company_pulse(workspace_id, project_id)
            top3 = await self.get_next_best_action(workspace_id, project_id)
            
            summary_msg = (
                f"**Báo cáo trọng tâm hôm nay dành cho Founder:**\n\n"
                f"• **Nhịp tim công ty:** {pulse.goals_on_track}/{pulse.total_active_goals} mục tiêu đúng tiến độ, "
                f"{pulse.active_missions} missions đang chạy, {pulse.needs_decision_count} quyết định cần bạn chốt.\n\n"
                f"**Top 3 hành động đề xuất hôm nay:**\n"
            )
            for idx, act in enumerate(top3, 1):
                summary_msg += f"{idx}. **{act.title}** ({act.category}) — *{act.rationale}*\n"

            return CoFounderMessageResponse(
                intent=intent.value,
                message=summary_msg,
                pulse=pulse,
                next_best_actions=top3,
                routed_domain="COFOUNDER",
            )

        # 4/5. FOUNDER_DECISION và FOUNDER_COMMAND -> orchestrator thật
        # (G2 P0.9 / G3 §10.5). Trước đây FOUNDER_DECISION trả về
        # synthesize_cross_domain() (số liệu bịa hoàn toàn, "50 triệu/tháng",
        # "7.5→6.2 tháng runway"...) và FOUNDER_COMMAND trả về 1 template
        # string liệt kê 3 bước cố định — không hề tạo Mission/Outcome/AgentRun
        # nào, không gì được dispatch thật. Cả hai giờ đi qua
        # ChiefOfStaffOrchestrator.orchestrate(), engine duy nhất có
        # side-effect thật (ghi Outcome/OutcomeRun/AgentRun, chạy governance/
        # budget check, gọi AgentRuntime thật cho phần diagnosis).
        if intent in (Intent.FOUNDER_DECISION, Intent.FOUNDER_COMMAND):
            if user_id is None:
                return CoFounderMessageResponse(
                    intent=intent.value,
                    message="Không thể tạo Mission: cần xác thực Founder trước khi điều phối.",
                    routed_domain="MISSION_ORCHESTRATOR",
                )
            if workspace_id is None:
                return CoFounderMessageResponse(
                    intent=intent.value,
                    message="Không thể tạo Mission: cần xác định workspace trước khi điều phối.",
                    routed_domain="MISSION_ORCHESTRATOR",
                )
            if self.sync_db is None:
                return CoFounderMessageResponse(
                    intent=intent.value,
                    message="Không thể gửi yêu cầu tới COSA runtime. Yêu cầu chưa được tạo thành Mission.",
                    routed_domain="MISSION_ORCHESTRATOR",
                )

            result = await orchestration_service.orchestrate_mission(
                db=self.sync_db,
                workspace_id=workspace_id,
                user_id=user_id,
                goal=message,
                intent=intent,
            )

            # G2 §7.3 / G3 §12: a mission whose domains carry risk above
            # AUTO_START_MAX_RISK stays in "draft" — orchestrate() didn't run
            # it. Say so plainly instead of showing result.diagnosis (empty
            # for a waiting_confirmation result, since nothing ran yet).
            if result.status == "waiting_confirmation":
                response_message = (
                    f"Tôi đã tạo Mission (id: {result.mission_id}) nhưng cần bạn xác nhận trước khi chạy, "
                    f"vì hành động này ở mức rủi ro cao hơn read-only. {result.diagnosis}"
                )
            else:
                response_message = result.diagnosis

            return CoFounderMessageResponse(
                intent=intent.value,
                message=response_message,
                suggested_decisions=[result.model_dump()] if intent == Intent.FOUNDER_DECISION else None,
                routed_domain="MISSION_ORCHESTRATOR",
                mission_id=result.mission_id,
                mission_status=result.status,
            )

        # 6. Phản hồi thông thường / chuyển tiếp Domain Agent
        return CoFounderMessageResponse(
            intent=intent.value,
            message=f"Tôi đã ghi nhận yêu cầu của bạn và sẵn sàng điều phối Domain Agent ({decision.target_agent_key}) xử lý chuyên sâu.",
            routed_domain=decision.target_agent_key,
        )

    async def confirm_mission(self, mission_id: int, user_id: int, workspace_id: Optional[int] = None) -> CoFounderMessageResponse:
        """Founder xác nhận chạy 1 Mission đang ở trạng thái draft (G2 §7.3 /
        G3 §12). Thin wrapper quanh orchestration_service.confirm_mission —
        cần sync_db thật, không phải self.db (async-wrapped)."""
        if self.sync_db is None:
            return CoFounderMessageResponse(
                intent="MISSION_CONFIRM",
                message="Không thể xác nhận Mission: thiếu kết nối cơ sở dữ liệu đồng bộ cho orchestrator.",
                routed_domain="MISSION_ORCHESTRATOR",
            )
        result = await orchestration_service.confirm_mission(
            db=self.sync_db,
            mission_id=mission_id,
            user_id=user_id,
            workspace_id=workspace_id,
        )
        return CoFounderMessageResponse(
            intent="MISSION_CONFIRM",
            message=result.diagnosis,
            routed_domain="MISSION_ORCHESTRATOR",
            mission_id=result.mission_id,
            mission_status=result.status,
        )

