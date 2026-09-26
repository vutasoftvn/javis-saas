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
from typing import Any, ClassVar

from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.workflows.onboarding_dimensions import validate_dimension_data


class OnboardingSessionType(enum.StrEnum):
    INITIAL = "initial"
    PARTIAL_UPDATE = "partial_update"


class CadenceCategory(enum.StrEnum):
    FAST = "fast"  # 2 weeks (Bi-weekly sprint)
    MEDIUM = "medium"  # 8-12 weeks (12WY cycle)
    SLOW = "slow"  # 24 weeks (2x 12WY cycles / ~6 months)


@dataclass(frozen=True)
class OnboardingStep:
    step_index: int
    dimension: str
    cadence: CadenceCategory
    title: str
    prompt_vi: str
    guiding_questions: list[str]
    expected_schema_keys: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_index": self.step_index,
            "dimension": self.dimension,
            "cadence": self.cadence.value,
            "title": self.title,
            "prompt_vi": self.prompt_vi,
            "guiding_questions": list(self.guiding_questions),
            "expected_schema_keys": list(self.expected_schema_keys),
        }


@dataclass(frozen=True)
class EventTriggerResult:
    triggered: bool
    event_type: str | None = None
    suggested_dimension: str | None = None
    trigger_keywords: list[str] = field(default_factory=list)
    advisory_prompt: str | None = None


# --- 7-Dimension Interview Catalog configured for 12WY & Bookended Voice ---
#
# `expected_schema_keys` PHẢI là field Company lưu thật (onboarding_dimensions.py,
# đối chiếu với services/company qua contract test). Trước đây catalog dùng key tự
# đặt (`arr`, `burn_rate_weekly`, `runway_weeks`…) nên agent làm theo kịch bản thì
# Company bỏ âm thầm mọi giá trị và lưu bản ghi rỗng.

FULL_ONBOARD_STEPS: list[OnboardingStep] = [
    # 1. Fast: stage_scale
    OnboardingStep(
        step_index=1,
        dimension="stage_scale",
        cadence=CadenceCategory.FAST,
        title="Giai đoạn & Quy mô (Stage & Scale)",
        prompt_vi=(
            "Hãy chia sẻ hiện trạng quy mô và tài chính của startup. "
            "Con số chỉ cần ước lượng — Founder có thể bỏ qua câu chưa rõ."
        ),
        guiding_questions=[
            "Doanh thu năm quy đổi (ARR) hiện tại là bao nhiêu, theo đơn vị tiền tệ nào?",
            "Runway còn khoảng bao nhiêu tháng?",
            "Bao nhiêu nhân sự toàn thời gian và bao nhiêu cộng tác viên/hợp đồng?",
            "Startup đang ở giai đoạn nào: chưa đạt PMF, đang scale, hay tối ưu vận hành?",
            "Điều gì đã 'vỡ' hoặc trục trặc trong 90 ngày qua?",
        ],
        expected_schema_keys=[
            "revenueArr",
            "revenueCurrency",
            "runwayMonths",
            "headcountFt",
            "headcountContractor",
            "stage",
            "whatBrokeLast90d",
        ],
    ),
    # 2. Fast: challenges
    OnboardingStep(
        step_index=2,
        dimension="challenges",
        cadence=CadenceCategory.FAST,
        title="Thách thức & Quyết định khó khăn (Challenges & Hard Decisions)",
        prompt_vi=("Đâu là nút thắt đang ưu tiên nhất trong chu kỳ 12 tuần này?"),
        guiding_questions=[
            "Chấm mức ưu tiên từ 1 đến 5 cho: Sản phẩm, Tăng trưởng, Con người, Tiền, Vận hành.",
            "Quyết định khó nào Founder đang trì hoãn hoặc né tránh?",
            "Nếu có thêm một ngày mỗi tuần, Founder sẽ dành nó cho việc gì?",
        ],
        expected_schema_keys=[
            "priorityProduct",
            "priorityGrowth",
            "priorityPeople",
            "priorityMoney",
            "priorityOperations",
            "avoidedDecision",
            "extraDayAnswer",
        ],
    ),
    # 3. Medium: goals_ambition
    OnboardingStep(
        step_index=3,
        dimension="goals_ambition",
        cadence=CadenceCategory.MEDIUM,
        title="Mục tiêu & Tham vọng (Goals & Ambition)",
        prompt_vi=("Chiến thắng trông như thế nào sau 12 tháng và sau 36 tháng?"),
        guiding_questions=[
            "Mục tiêu dứt khoát trong 12 tháng tới là gì?",
            "Hình dung công ty sau 36 tháng?",
            "Định hướng dài hạn: hướng tới exit, xây dựng lâu dài, hay chưa quyết định?",
            "Với cá nhân Founder, thành công nghĩa là gì?",
        ],
        expected_schema_keys=[
            "goal12MonthsText",
            "goal36MonthsText",
            "exitOrientation",
            "personalSuccessDefinition",
        ],
    ),
    # 4. Medium: market
    OnboardingStep(
        step_index=4,
        dimension="market",
        cadence=CadenceCategory.MEDIUM,
        title="Thị trường & Cạnh tranh (Market & Competition)",
        prompt_vi=("Startup đang chơi ở thị trường nào và ai đang cạnh tranh trực tiếp?"),
        guiding_questions=[
            "Mô tả ngắn thị trường và khách hàng mục tiêu?",
            "Lợi thế không công bằng (unfair advantage) mà đối thủ khó sao chép?",
            "Mối đe doạ cạnh tranh lớn nhất hiện nay là gì?",
            "Kể tên các đối thủ chính, vì sao họ đang thắng và mức đe doạ (thấp/vừa/cao)?",
        ],
        expected_schema_keys=[
            "marketDescription",
            "unfairAdvantage",
            "competitiveThreat",
            "hasRealCompetition",
            "competitors",
        ],
    ),
    # 5. Medium: team_culture
    OnboardingStep(
        step_index=5,
        dimension="team_culture",
        cadence=CadenceCategory.MEDIUM,
        title="Đội ngũ & Văn hoá (Team & Culture)",
        prompt_vi=("Văn hoá đội ngũ thật sự vận hành thế nào khi có áp lực?"),
        guiding_questions=[
            "Ba từ mô tả đúng nhất văn hoá đội hiện tại?",
            "Xung đột thật gần nhất là gì và đã được giải quyết ra sao?",
            "Ai là người dẫn dắt mạnh nhất và vị trí lãnh đạo nào đang yếu nhất?",
        ],
        expected_schema_keys=[
            "threeWords",
            "lastRealConflict",
            "conflictResolution",
            "hasRealConflict",
            "strongestLeader",
            "weakestLeader",
        ],
    ),
    # 6. Slow: identity
    OnboardingStep(
        step_index=6,
        dimension="identity",
        cadence=CadenceCategory.SLOW,
        title="Căn tính & Giá trị (Identity & Values)",
        prompt_vi=("Startup làm gì, cho ai, vì sao tồn tại và giữ những giá trị nào?"),
        guiding_questions=[
            "Startup làm gì và phục vụ ai?",
            "Vì sao Founder bắt đầu công ty này?",
            "Pitch trong một câu?",
            "Những giá trị cốt lõi nào đủ quan trọng để sa thải người vi phạm (fire-worthy)?",
        ],
        expected_schema_keys=[
            "whatTheyDo",
            "whoTheyServe",
            "foundingWhy",
            "oneSentencePitch",
            "values",
        ],
    ),
    # 7. Slow: founder
    OnboardingStep(
        step_index=7,
        dimension="founder",
        cadence=CadenceCategory.SLOW,
        title="Hồ sơ Founder & Điểm mù (Founder Profile & Blind Spots)",
        prompt_vi=("Thế mạnh và điểm mù của Founder là gì để Hội đồng C-Suite phản biện đúng chỗ?"),
        guiding_questions=[
            "Tên và vai trò hiện tại của Founder?",
            "Thế mạnh vượt trội nhất (superpower)?",
            "Điểm mù hoặc thiên kiến Founder tự nhận thấy?",
            "Kiểu Founder: sản phẩm, bán hàng, kỹ thuật, vận hành hay lai?",
            "Điều gì khiến Founder mất ngủ, và co-founder hay phê bình Founder điều gì?",
        ],
        expected_schema_keys=[
            "founderName",
            "role",
            "superpower",
            "blindSpots",
            "archetype",
            "whatKeepsUp",
            "cofounderCritique",
        ],
    ),
]

MICRO_INTAKE_STEPS: list[OnboardingStep] = [
    FULL_ONBOARD_STEPS[0],  # stage_scale
    FULL_ONBOARD_STEPS[1],  # challenges
]


def steps_for_session(session_type: OnboardingSessionType | str) -> list[OnboardingStep]:
    """Kịch bản cho /cs:setup (initial, 7 chiều) hoặc /cs:update (partial_update, 2 chiều Fast)."""
    kind = (
        session_type
        if isinstance(session_type, OnboardingSessionType)
        else OnboardingSessionType(session_type)
    )
    if kind == OnboardingSessionType.PARTIAL_UPDATE:
        return list(MICRO_INTAKE_STEPS)
    return list(FULL_ONBOARD_STEPS)


class EventTriggerDetector:
    """Detects high-impact business events from Founder messages to suggest context updates."""

    PATTERNS: ClassVar[list[dict[str, Any]]] = [
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
        return steps_for_session(self.session_type)

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
        validate_dimension_data(dimension, data)

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
