"""Functional AgentSpec catalog — M7 §1.

Danh mục các Functional AgentSpec chuẩn hoá (registry-publishable). Mỗi entry pin
một tập `capability_refs` cố định + một `capability boundary` (prefix cho phép) để
không thể silent-widen quyền qua chỉnh sửa lẻ.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agent.contracts.spec import AgentSpec

__all__ = [
    "FUNCTIONAL_AGENT_CATALOG",
    "FunctionalAgentEntry",
    "build_functional_spec",
    "catalog_keys",
]


@dataclass(frozen=True)
class FunctionalAgentEntry:
    functional_key: str
    version: str
    title: str
    description: str
    # Capability được pin vào spec (execution identity).
    capability_refs: tuple[str, ...]
    # Ranh giới: mọi capability_ref phải khớp một trong các prefix này.
    allowed_capability_prefixes: tuple[str, ...]
    # Gợi ý persona/department cho workforce assignment overlay (KHÔNG cấp quyền).
    suggested_personas: tuple[str, ...] = field(default_factory=tuple)
    default_department: str = ""


_ENTRIES: tuple[FunctionalAgentEntry, ...] = (
    FunctionalAgentEntry(
        functional_key="cashflow_planner",
        version="1.0.0",
        title="Cashflow Planner",
        description="Đọc giao dịch, dự báo dòng tiền, đề xuất (không thực thi) thanh toán.",
        capability_refs=(
            "finance.transaction.read",
            "finance.cashflow.forecast",
            "finance.payment.propose",
        ),
        allowed_capability_prefixes=(
            "finance.transaction.",
            "finance.cashflow.",
            "finance.payment.propose",
        ),
        suggested_personas=("Finance Copilot", "CFO"),
        default_department="Finance",
    ),
    FunctionalAgentEntry(
        functional_key="accounting_document_specialist",
        version="1.0.0",
        title="Accounting Document Specialist",
        description="Chuẩn hoá chứng từ kế toán, đối chiếu đề xuất (human accept).",
        capability_refs=(
            "finance.transaction.read",
            "finance.document.normalize",
            "finance.reconciliation.propose",
        ),
        allowed_capability_prefixes=(
            "finance.transaction.",
            "finance.document.",
            "finance.reconciliation.propose",
        ),
        suggested_personas=("Finance Copilot",),
        default_department="Finance",
    ),
    FunctionalAgentEntry(
        functional_key="market_research_specialist",
        version="1.0.0",
        title="Market Research Specialist",
        description="Thu thập + phân tích tín hiệu thị trường, tổng hợp bằng chứng.",
        capability_refs=(
            "research.signal.collect",
            "research.evidence.synthesize",
            "knowledge.document.read",
        ),
        allowed_capability_prefixes=("research.", "knowledge.document.read"),
        suggested_personas=("CMO", "Chief of Staff"),
        default_department="Strategy",
    ),
    FunctionalAgentEntry(
        functional_key="campaign_planner",
        version="1.0.0",
        title="Campaign Planner",
        description="Lập kế hoạch chiến dịch marketing; publish/chi tiêu cần human approval.",
        capability_refs=(
            "marketing.campaign.plan",
            "marketing.audience.analyze",
        ),
        allowed_capability_prefixes=("marketing.campaign.plan", "marketing.audience."),
        suggested_personas=("CMO",),
        default_department="Marketing",
    ),
    FunctionalAgentEntry(
        functional_key="compliance_analyst",
        version="1.0.0",
        title="Compliance Analyst",
        description="Đánh giá nghĩa vụ pháp lý, lập checklist tuân thủ (không tự nộp hồ sơ).",
        capability_refs=(
            "legal.obligation.assess",
            "legal.regulation.read",
            "legal.checklist.compose",
        ),
        allowed_capability_prefixes=(
            "legal.obligation.",
            "legal.regulation.read",
            "legal.checklist.",
        ),
        suggested_personas=("Compliance Officer", "Chief of Staff"),
        default_department="Legal",
    ),
    FunctionalAgentEntry(
        functional_key="founder_office_orchestrator",
        version="1.0.0",
        title="Founder Office Orchestrator",
        description="Chief of Staff: điều phối, không tự thực thi hành động rủi ro cao.",
        capability_refs=(
            "orchestration.mission.decompose",
            "orchestration.task.route",
            "knowledge.document.read",
        ),
        allowed_capability_prefixes=("orchestration.", "knowledge.document.read"),
        suggested_personas=("Chief of Staff", "Founder Copilot"),
        default_department="Founder Office",
    ),
)

FUNCTIONAL_AGENT_CATALOG: dict[str, FunctionalAgentEntry] = {e.functional_key: e for e in _ENTRIES}


def catalog_keys() -> list[str]:
    return sorted(FUNCTIONAL_AGENT_CATALOG)


def build_functional_spec(functional_key: str) -> AgentSpec:
    """Dựng `AgentSpec` (đã gắn `definition_hash`) từ 1 entry catalog."""
    entry = FUNCTIONAL_AGENT_CATALOG.get(functional_key)
    if entry is None:
        raise KeyError(f"functional_key '{functional_key}' không có trong catalog")
    spec = AgentSpec(
        id=f"functional.{entry.functional_key}",
        version=entry.version,
        instructions="",
        capability_refs=list(entry.capability_refs),
        model_input_capability_ref="model.input.direct-user-message",
        metadata={
            "functional_key": entry.functional_key,
            "title": entry.title,
            "description": entry.description,
            "default_department": entry.default_department,
            "suggested_personas": list(entry.suggested_personas),
        },
    )
    return spec.with_hash()
