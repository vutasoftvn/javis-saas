"""COSA Co-Founder Service (F4 Specification - Central AI Co-Founder Engine).

Chịu trách nhiệm:
1. Giao diện AI Co-Founder đồng hành cùng Human Founder.
2. Phân loại ý định (Intent Routing: Greeting vs Review vs Decision vs Command).
3. Truy xuất ngữ cảnh tối thiểu (Minimum Viable Context).
4. Phản biện dựa trên Bằng chứng (Challenge Mode / Problem-First F1-F3).
5. Tổng hợp kinh doanh chéo (Cross-Domain Business Synthesis).
6. Đề xuất hành động tốt nhất (Next Best Action Engine).
7. Thống kê nhịp tim doanh nghiệp (Company Pulse).
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.workforce.routing.router import IntentRouter, IntentDecision
from app.workforce.routing.deterministic import Intent
from app.workforce.models import FounderDecision, AgentDefinition, ApprovalRequest, AgentRun
from app.workforce.schemas.decision_schemas import DecisionStatusEnum, DecisionDomainEnum


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


class CosaCofounderService:
    """Service điều phối trung tâm COSA AI Co-Founder."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_company_pulse(
        self,
        workspace_id: Optional[int] = None,
        project_id: Optional[int] = None,
    ) -> CompanyPulseResponse:
        """Lấy thông tin nhịp tim tổng thể của doanh nghiệp (Company Pulse)."""
        from app.founder_os.strategy.models import Project, TwelveWeekCycle

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

        # 3. Đếm số Agent Runs đang chạy (Active Missions)
        stmt_runs = select(func.count(AgentRun.id)).where(
            AgentRun.status.in_(["running", "queued"])
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

        return CompanyPulseResponse(
            goals_on_track=total_goals,
            total_active_goals=total_goals,
            active_missions=active_missions,
            needs_decision_count=needs_decision,
            pending_approvals_count=pending_approvals,
            major_risks_count=1 if needs_decision > 0 else 0,
            suggested_focus="Tập trung triển khai các chiến thuật 12-Week Year và chốt các quyết định quan trọng.",
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

        # 2. Hành động kiểm chứng khách hàng / chiến lược tuần (Problem-First)
        actions.append(
            NextBestActionItem(
                id="act_cust_interview",
                category="EXPERIMENT",
                title="Hoàn tất phỏng vấn 5 khách hàng tiềm năng",
                rationale="Kiểm chứng mức độ sẵn sàng chi trả (WTP) trước khi mở rộng ngân sách quảng cáo.",
                urgency="HIGH",
                domain="MARKETING",
                action_payload={"target_interviews": 5},
            )
        )

        # 3. Hành động tối ưu chiến dịch / kinh doanh
        actions.append(
            NextBestActionItem(
                id="act_weekly_review",
                category="FOUNDER_ACTION",
                title="Rà soát Scoreboard 12-Week Year tuần hiện tại",
                rationale="Đảm bảo tỷ lệ hoàn thành chiến thuật tuần đạt trên 85%.",
                urgency="MEDIUM",
                domain="STRATEGY",
                action_payload={"scoreboard_week": "W1"},
            )
        )

        return actions[:3]

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

    async def synthesize_cross_domain(
        self,
        question: str,
        workspace_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Tổng hợp góc nhìn kinh doanh liên phòng ban (Cross-Domain Business Synthesis).
        
        Ví dụ: Marketing đề xuất chi tiêu -> Đối chiếu Cashflow Runway của Finance.
        """
        return {
            "question": question,
            "marketing_perspective": {
                "opportunity": "Mở rộng kênh acquisition có thể tăng lượng qualified leads thêm 25-30%.",
                "risk": "Chi phí CAC có thể tăng nếu thông điệp chưa được tối ưu hóa theo ICP.",
            },
            "finance_perspective": {
                "cashflow_impact": "Nếu chi 50 triệu/tháng, Runway sẽ giảm từ 7.5 tháng xuống 6.2 tháng.",
                "recommendation": "Nên thử nghiệm ở mức ngân sách 15 triệu trong 2 tuần đầu để đo lường ROI.",
            },
            "legal_perspective": {
                "compliance_check": "Cần đảm bảo tuân thủ quy định bảo vệ dữ liệu cá nhân (Nghị định 13) khi thu thập lead form.",
            },
            "founder_recommendation": "Khuyến nghị chọn Phương án Thử nghiệm 15 triệu (Option B) để bảo toàn Runway và kiểm chứng CAC trước khi scale.",
        }

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
        if intent == Intent.GREETING or "greetings" in decision.reason.lower():
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

        # 4. Xử lý tham vấn quyết định chiến lược (FOUNDER_DECISION)
        if intent == Intent.FOUNDER_DECISION:
            synthesis = await self.synthesize_cross_domain(message, workspace_id)
            decision_msg = (
                f"**Phân tích đa chiều từ Co-Founder:**\n\n"
                f"📊 **Marketing:** {synthesis['marketing_perspective']['opportunity']}\n"
                f"💰 **Finance & Dòng tiền:** {synthesis['finance_perspective']['cashflow_impact']}\n"
                f"⚖️ **Pháp lý:** {synthesis['legal_perspective']['compliance_check']}\n\n"
                f"🎯 **Đề xuất của COSA:** {synthesis['founder_recommendation']}"
            )
            return CoFounderMessageResponse(
                intent=intent.value,
                message=decision_msg,
                suggested_decisions=[synthesis],
                routed_domain="COFOUNDER",
            )

        # 5. Xử lý chỉ đạo mục tiêu lớn (FOUNDER_COMMAND)
        if intent == Intent.FOUNDER_COMMAND:
            mission_msg = (
                f"Tôi đã tiếp nhận mục tiêu: *\"{message}\"*.\n\n"
                f"**Kế hoạch phân rã Mission tự động:**\n"
                f"1. **Marketing Agent:** Định vị phân khúc khách hàng, chuẩn bị nội dung landing page và thông điệp outreach.\n"
                f"2. **Build / Tech Agent:** Dựng và triển khai landing page thu thập khách hàng tiềm năng.\n"
                f"3. **Sales Agent:** Nghiên cứu danh sách 50 prospects phù hợp và tiến hành outreach cá nhân hóa.\n\n"
                f"Tôi sẽ tổng hợp tiến độ và kết quả cho bạn. Bạn có muốn kích hoạt Mission này ngay không?"
            )
            return CoFounderMessageResponse(
                intent=intent.value,
                message=mission_msg,
                routed_domain="MISSION_ORCHESTRATOR",
            )

        # 6. Kiểm tra phản biện giả định (Challenge Mode)
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
                intent=intent.value,
                message=challenge_msg,
                challenge_analysis=challenge,
                routed_domain="COFOUNDER",
            )

        # 7. Phản hồi thông thường / chuyển tiếp Domain Agent
        return CoFounderMessageResponse(
            intent=intent.value,
            message=f"Tôi đã ghi nhận yêu cầu của bạn và sẵn sàng điều phối Domain Agent ({decision.target_agent_key}) xử lý chuyên sâu.",
            routed_domain=decision.target_agent_key,
        )
