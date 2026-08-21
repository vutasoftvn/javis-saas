# backend/app/workforce/agents/orchestration/specialist_registry.py
"""Nguồn sự thật duy nhất cho SPECIALIST_REGISTRY/risk-tier — dùng chung bởi
chief_of_staff.py (cho tới khi bị xoá, Quyết định 1 Task 36) và
orchestration/adk/* (AdkCofounderWorkflow). Trích ra từ chief_of_staff.py để
tránh 2 nguồn sự thật khi cả 2 đường orchestration cùng tồn tại trong giai đoạn
chuyển tiếp."""
from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.business.finance.finance_tools import get_financial_summary
from app.business.legal.legal_tools import get_legal_posture_summary
from app.business.marketing.marketing_tools import get_marketing_overview
from app.business.sales.sales_tools import get_pipeline_summary

# Ordered so max() by index picks the higher-risk tier (G2 §7.6 R0-R4 policy).
RISK_ORDER = ("R0", "R1", "R2", "R3", "R4")
# Missions at or below this risk auto-start; anything higher stays in "draft"
# until a founder explicitly confirms (G2 §7.3).
AUTO_START_MAX_RISK = "R1"


@dataclass(frozen=True)
class SpecialistSpec:
    """One entry in SPECIALIST_REGISTRY — everything the delegation loop needs
    to dispatch a domain specialist generically, without a new
    `if domain == "...":` branch per domain."""
    domain: str
    agent_key: str
    task: str
    tool_flat_name: str
    fetch_snapshot: Callable[[Session, int], dict[str, Any]]
    quality_gate_compatible: bool = True
    risk_level: str = "R0"
    delegate_via_profile_id: str | None = None


SPECIALIST_REGISTRY: dict[str, SpecialistSpec] = {
    "sales": SpecialistSpec(
        domain="sales",
        agent_key="sales_specialist",
        task="Analyze CRM pipeline",
        tool_flat_name="sales_get_pipeline_summary",
        fetch_snapshot=lambda db, ws: get_pipeline_summary(db, ws),
        delegate_via_profile_id="sales",
    ),
    "finance": SpecialistSpec(
        domain="finance",
        agent_key="finance_specialist",
        task="Analyze cashflow and runway",
        tool_flat_name="finance_get_financial_summary",
        fetch_snapshot=lambda db, ws: get_financial_summary(db, ws),
        delegate_via_profile_id="finance",
    ),
    "legal": SpecialistSpec(
        domain="legal",
        agent_key="legal_specialist",
        task="Review legal posture and obligations",
        tool_flat_name="legal_get_legal_posture_summary",
        fetch_snapshot=lambda db, ws: get_legal_posture_summary(db, ws),
        quality_gate_compatible=False,
        delegate_via_profile_id="legal",
    ),
    "marketing": SpecialistSpec(
        domain="marketing",
        agent_key="marketing_specialist",
        task="Analyze marketing funnel and scorecard",
        tool_flat_name="marketing_get_marketing_overview",
        fetch_snapshot=lambda db, ws: get_marketing_overview(db, ws),
        delegate_via_profile_id="marketing",
    ),
}

DEFAULT_ORCHESTRATION_DOMAINS: tuple[str, ...] = ("sales", "finance")


def classify_mission_risk(domains: list[str]) -> str:
    """Highest risk tier among the specialists this mission would delegate
    to — see SpecialistSpec.risk_level / AUTO_START_MAX_RISK."""
    highest = "R0"
    for domain in domains:
        spec = SPECIALIST_REGISTRY.get(domain)
        if spec is None:
            continue
        if RISK_ORDER.index(spec.risk_level) > RISK_ORDER.index(highest):
            highest = spec.risk_level
    return highest
