"""Conversational Onboarding Workflow for Startup OS (12-Week Year Multi-Cadence).

Supports two interactive modes:
1. Full Onboard Interview (`session_type = 'initial'`): Deep 7-dimension intake across
   Fast, Medium, and Slow cadences for new workspaces.
2. 2-Minute Micro-Intake (`session_type = 'partial_update'`): Lean check-in updating
   only the 2 Fast dimensions (`stage_scale` and `challenges`) to keep context fresh.

Also provides event-driven trigger detection to prompt the Founder when major
milestones occur (e.g. fundraising, key hiring/departures, market shifts).
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass, field
from typing import Any

from apps.cosa.capabilities.client import CompanyServiceClient


class OnboardingSessionType(str, enum.Enum):
    INITIAL = "initial"
    PARTIAL_UPDATE = "partial_update"


class CadenceCategory(str, enum.Enum):
    FAST = "fast"        # 2 weeks (Bi-weekly sprint)
    MEDIUM = "medium"    # 8-12 weeks (12WY cycle)
    SLOW = "slow"        # 24 weeks (2x 12WY cycles / ~6 months)


@dataclass(frozen=True)
class OnboardingStep:
    step_index: int
    dimension: str
    cadence: CadenceCategory
    title: str
    prompt_vi: str
    guiding_questions: list[str]
    expected_schema_keys: list[str]


@dataclass(frozen=True)
class EventTriggerResult:
    triggered: bool
    event_type: str | None = None
    suggested_dimension: str | None = None
    trigger_keywords: list[str] = field(default_factory=list)
    advisory_prompt: str | None = None


# --- 7-Dimension Interview Catalog configured for 12WY & Bookended Voice ---

FULL_ONBOARD_STEPS: list[OnboardingStep] = [
    # 1. Fast: stage_scale
    OnboardingStep(
        step_index=1,
        dimension="stage_scale",
        cadence=CadenceCategory.FAST,
        title="Giai đoạn & Quy mô (Stage & Scale)",
        prompt_vi=(
            "Hãy chia sẻ về hiện trạng tài chính và quy mô hiện tại của startup. "
            "Toàn bộ con số sẽ được tính toán theo nhịp tuần (12WY)."
        ),
        guiding_questions=[
            "Doanh thu hiện tại (ARR/MRR) là bao nhiêu?",
            "Lượng tiền mặt khả dụng (Cash in bank) và mức burn/tuần hiện tại?",
            "Số tuần Runway sinh tồn còn lại ước tính là bao nhiêu tuần?",
            "Tổng số lượng nhân sự toàn thời gian và bán thời gian?",
        ],
        expected_schema_keys=["arr", "mrr", "cash_in_bank", "burn_rate_weekly", "runway_weeks", "headcount"],
    ),
    # 2. Fast: challenges
    OnboardingStep(
        step_index=2,
        dimension="challenges",
        cadence=CadenceCategory.FAST,
        title="Thách thức & Quyết định khó khăn (Challenges & Hard Decisions)",
        prompt_vi=(
            "Đâu là nút thắt nhức nhối nhất mà startup đang đối mặt trong chu kỳ 12 tuần này?"
        ),
        guiding_questions=[
            "Vấn đề cấp bách nhất đe dọa trực tiếp đến mục tiêu chu kỳ 12 tuần?",
            "Quyết định khó khăn nào mà Founder đang cảm thấy phải trì hoãn hoặc né tránh?",
            "Điểm nghẽn vận hành hoặc kỹ thuật lớn nhất cần tháo gỡ ngay?",
        ],
        expected_schema_keys=["primary_bottleneck", "avoided_hard_decision", "operational_risk"],
    ),
    # 3. Medium: goals_ambition
    OnboardingStep(
        step_index=3,
        dimension="goals_ambition",
        cadence=CadenceCategory.MEDIUM,
        title="Mục tiêu chu kỳ 12 tuần (12WY Cycle Goals & Ambition)",
        prompt_vi=(
            "Xác định mục tiêu dứt khoát cho chu kỳ 12 tuần hiện tại. "
            "Điều gì định nghĩa chiến thắng ở Tuần thứ 12?"
        ),
        guiding_questions=[
            "Mục tiêu kết quả cốt lõi (Lag Indicator) ở Tuần 12 là gì?",
            "Các chỉ số hành động tiên phong (Lead Indicators) được đo lường hàng tuần?",
            "Kế hoạch tuần đệm (Week 13 buffer) dùng để tổng kết hay triển khai?",
        ],
        expected_schema_keys=["cycle_lag_goal", "weekly_lead_indicators", "week_13_plan"],
    ),
    # 4. Medium: market
    OnboardingStep(
        step_index=4,
        dimension="market",
        cadence=CadenceCategory.MEDIUM,
        title="Thị trường & Khách hàng mục tiêu (Market & ICP)",
        prompt_vi=(
            "Ai là khách hàng lý tưởng (ICP) và động thái cạnh tranh trên thị trường hiện nay ra sao?"
        ),
        guiding_questions=[
            "Chân dung khách hàng lý tưởng (ICP) sẵn sàng trả tiền ngay?",
            "Động thái đáng chú ý gần nhất của 2 đối thủ cạnh tranh chính?",
            "Lợi thế khác biệt cốt lõi (Moat) mà đối thủ khó sao chép trong 144 tuần tới?",
        ],
        expected_schema_keys=["icp_profile", "key_competitors", "competitive_moat"],
    ),
    # 5. Medium: team_culture
    OnboardingStep(
        step_index=5,
        dimension="team_culture",
        cadence=CadenceCategory.MEDIUM,
        title="Đội ngũ & Văn hoá thực thi (Team & Execution Culture)",
        prompt_vi=(
            "Cấu trúc đội ngũ hiện tại và văn hoá giao hàng của công ty như thế nào?"
        ),
        guiding_questions=[
            "Bộ máy lãnh đạo chủ chốt (Tech, Product, Growth)?",
            "Tốc độ onboarding nhân sự kỹ thuật mới (mất bao nhiêu tuần để có PR đầu tiên)?",
            "Xung đột hoặc khoảng trống năng lực lớn nhất trong đội ngũ hiện tại?",
        ],
        expected_schema_keys=["leadership_team", "onboarding_velocity_weeks", "team_gap"],
    ),
    # 6. Slow: identity
    OnboardingStep(
        step_index=6,
        dimension="identity",
        cadence=CadenceCategory.SLOW,
        title="Căn tính & Giá trị bất biến (Core Identity & Fireable Values)",
        prompt_vi=(
            "Sứ mệnh cốt lõi và những nguyên tắc bất di bất dịch của tổ chức là gì?"
        ),
        guiding_questions=[
            "Sứ mệnh tồn tại dài hạn (North Star Vision) trong 144 tuần tới?",
            "Các giá trị cốt lõi mà nếu nhân viên vi phạm sẽ bị sa thải ngay lập tức (Fireable Values)?",
            "Lĩnh vực hoặc nguyên tắc đạo đức mà startup quyết định không bao giờ tham gia?",
        ],
        expected_schema_keys=["mission_144_weeks", "fireable_values", "non_negotiables"],
    ),
    # 7. Slow: founder
    OnboardingStep(
        step_index=7,
        dimension="founder",
        cadence=CadenceCategory.SLOW,
        title="Hồ sơ & Điểm mù của Founder (Founder Profile & Blindspots)",
        prompt_vi=(
            "Thế mạnh vượt trội và điểm mù lớn nhất của Founder là gì để Hội đồng C-Suite phản biện hiệu quả?"
        ),
        guiding_questions=[
            "Thế mạnh chuyên môn nổi bật nhất của Founder (Engineering, Sales, Product)?",
            "Điểm mù hoặc thiên kiến nhận thức mà Founder tự nhận thấy mình hay mắc phải?",
            "Kỳ vọng cụ thể đối với phản biện từ AI C-Suite (muốn thẳng thắn hay ôn hoà)?",
        ],
        expected_schema_keys=["founder_superpower", "known_blindspots", "c_suite_candor_level"],
    ),
]

MICRO_INTAKE_STEPS: list[OnboardingStep] = [
    FULL_ONBOARD_STEPS[0],  # stage_scale
    FULL_ONBOARD_STEPS[1],  # challenges
]


class EventTriggerDetector:
    """Detects high-impact business events from Founder messages to suggest context updates."""

    PATTERNS: list[dict[str, Any]] = [
        {
            "event_type": "fundraising",
            "suggested_dimension": "stage_scale",
            "regex": r"(gọi vốn|đầu tư|investor|seed round|series a|term sheet|rót vốn|fundrais)",
            "advisory_prompt": (
                "Phát hiện tín hiệu về gọi vốn/dòng tiền. "
                "Bạn có muốn cập nhật lại chỉ số Runway và Ngân sách chu kỳ 12 tuần không?"
            ),
        },
        {
            "event_type": "key_personnel_change",
            "suggested_dimension": "team_culture",
            "regex": r"(tuyển|sa thải|nghỉ việc|hire|fire|cto mới|cpo mới|co-founder|rời công ty)",
            "advisory_prompt": (
                "Phát hiện biến động nhân sự chủ chốt. "
                "Bạn có muốn cập nhật chiều Đội ngũ & Văn hoá (team_culture) không?"
            ),
        },
        {
            "event_type": "competitor_move",
            "suggested_dimension": "market",
            "regex": r"(đối thủ|competitor|ra mắt|tính năng mới|hạ giá|giảm giá|tung sản phẩm)",
            "advisory_prompt": (
                "Phát hiện động thái mới từ đối thủ cạnh tranh. "
                "Bạn có muốn cập nhật chiều Thị trường & Khách hàng (market) không?"
            ),
        },
        {
            "event_type": "strategic_pivot",
            "suggested_dimension": "goals_ambition",
            "regex": r"(pivot|chuyển hướng|thay đổi chiến lược|đổi hướng đi|tái cấu trúc)",
            "advisory_prompt": (
                "Phát hiện tín hiệu thay đổi chiến lược lớn. "
                "Bạn có muốn làm mới mục tiêu chu kỳ 12 tuần (goals_ambition) không?"
            ),
        },
    ]

    @classmethod
    def detect(cls, text: str) -> EventTriggerResult:
        if not text:
            return EventTriggerResult(triggered=False)

        lower_text = text.lower()
        for pat in cls.PATTERNS:
            matches = re.findall(pat["regex"], lower_text)
            if matches:
                return EventTriggerResult(
                    triggered=True,
                    event_type=pat["event_type"],
                    suggested_dimension=pat["suggested_dimension"],
                    trigger_keywords=list(set(matches)),
                    advisory_prompt=pat["advisory_prompt"],
                )

        return EventTriggerResult(triggered=False)


class ConversationalOnboardingWorkflow:
    """Manages conversational onboarding sessions (Initial full or 2-min micro-intake)."""

    def __init__(
        self,
        workspace_id: str,
        session_type: OnboardingSessionType | str = OnboardingSessionType.INITIAL,
        client: CompanyServiceClient | None = None,
    ) -> None:
        self.workspace_id = str(workspace_id)
        self.session_type = (
            session_type
            if isinstance(session_type, OnboardingSessionType)
            else OnboardingSessionType(session_type)
        )
        self.client = client or CompanyServiceClient()
        self.active_session_id: str | None = None

    def get_steps(self) -> list[OnboardingStep]:
        if self.session_type == OnboardingSessionType.PARTIAL_UPDATE:
            return list(MICRO_INTAKE_STEPS)
        return list(FULL_ONBOARD_STEPS)

    async def start_session(self, summary: str | None = None) -> dict[str, Any]:
        default_summary = (
            "Khảo sát toàn diện 7 chiều Startup OS (12WY)"
            if self.session_type == OnboardingSessionType.INITIAL
            else "Micro-Intake 2 phút rà soát 2 chiều Fast"
        )
        payload = {
            "workspaceId": self.workspace_id,
            "sessionType": self.session_type.value,
            "summary": summary or default_summary,
        }
        resp = await self.client.post("/operations/onboard/sessions", json=payload)
        session_id = resp.get("sessionId") or resp.get("id")
        if session_id:
            self.active_session_id = str(session_id)
        return resp

    async def submit_dimension(
        self,
        dimension: str,
        data: dict[str, Any],
        session_id: str | None = None,
    ) -> dict[str, Any]:
        target_session = session_id or self.active_session_id
        if not target_session:
            raise ValueError("Cần khởi tạo phiên (start_session) hoặc truyền session_id hợp lệ")

        payload = {
            "workspaceId": self.workspace_id,
            "sessionId": target_session,
            "data": data,
        }
        return await self.client.post(f"/operations/onboard/dimensions/{dimension}", json=payload)

    async def complete_and_create_snapshot(
        self,
        change_reason: str,
        changed_dimensions: list[str] | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        target_session = session_id or self.active_session_id
        if not target_session:
            raise ValueError("Cần khởi tạo phiên (start_session) hoặc truyền session_id hợp lệ")

        dims = changed_dimensions or [s.dimension for s in self.get_steps()]
        payload = {
            "workspaceId": self.workspace_id,
            "sessionId": target_session,
            "changeReason": change_reason,
            "changedDimensions": dims,
        }
        return await self.client.post("/operations/onboard/snapshots", json=payload)

    def detect_event_trigger(self, founder_message: str) -> EventTriggerResult:
        return EventTriggerDetector.detect(founder_message)
