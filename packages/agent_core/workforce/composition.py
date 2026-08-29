"""Stage-aware composition — M7 §4.

    eligible = workspace_stage_policy + project_stage_policy + entitlement
             + capability_readiness + connector/data availability

Hàm thuần: nhận trạng thái đã resolve ⇒ danh sách functional agent đủ điều kiện,
kèm lý do khi KHÔNG đủ (UI hiện rõ, không fake workforce). Đọc CẢ workspace stage
lẫn project stage (M4) — project P0 trong workspace W4 vẫn nhận Discovery pack cho
context project đó.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_core.workforce.catalog import FUNCTIONAL_AGENT_CATALOG

__all__ = [
    "CompositionInput",
    "EligibleAgent",
    "compose_workforce",
]

# Default packs theo Workspace stage (audit §7.3, rút gọn).
_WORKSPACE_STAGE_PACKS: dict[str, set[str]] = {
    "W0_IDEA": {"founder_office_orchestrator", "market_research_specialist", "compliance_analyst"},
    "W1_PROBLEM_VALIDATION": {
        "founder_office_orchestrator",
        "market_research_specialist",
        "compliance_analyst",
        "cashflow_planner",
    },
    "W2_SOLUTION_VALIDATION": {
        "founder_office_orchestrator",
        "market_research_specialist",
        "compliance_analyst",
        "cashflow_planner",
        "accounting_document_specialist",
    },
    "W3_MVP_BUILD": set(FUNCTIONAL_AGENT_CATALOG) - {"campaign_planner"},
    "W4_PRODUCT_MARKET_FIT": set(FUNCTIONAL_AGENT_CATALOG),
    "W5_SCALE": set(FUNCTIONAL_AGENT_CATALOG),
}

# Default packs theo Project stage.
_PROJECT_STAGE_PACKS: dict[str, set[str]] = {
    "P0_DISCOVERY": {"founder_office_orchestrator", "market_research_specialist"},
    "P1_PROBLEM_VALIDATION": {"founder_office_orchestrator", "market_research_specialist"},
    "P2_SOLUTION_VALIDATION": {
        "founder_office_orchestrator",
        "market_research_specialist",
        "compliance_analyst",
    },
    "P3_BUILD_VALIDATE": {
        "founder_office_orchestrator",
        "market_research_specialist",
        "compliance_analyst",
        "cashflow_planner",
    },
    "P4_GO_TO_MARKET": set(FUNCTIONAL_AGENT_CATALOG),
    "P5_OPERATE_GROWTH": set(FUNCTIONAL_AGENT_CATALOG),
    "P6_SCALE_GOVERN": set(FUNCTIONAL_AGENT_CATALOG),
}

# Entitlement feature cần cho từng department (khớp effectiveFeatures backend).
_DEPT_FEATURE: dict[str, str] = {
    "Finance": "finance",
    "Marketing": "marketing",
    "Legal": "legal",
}


@dataclass(frozen=True)
class CompositionInput:
    workspace_stage: str
    project_stage: str | None = None
    entitled_features: frozenset[str] = frozenset()
    # capability_ref -> sẵn sàng chưa (thiếu key ⇒ coi như chưa sẵn sàng)
    capability_readiness: dict[str, bool] = field(default_factory=dict)
    # connector_key -> có sẵn không (chỉ chặn khi entry yêu cầu — hiện chưa map cụ thể)
    connector_available: dict[str, bool] = field(default_factory=dict)


@dataclass(frozen=True)
class EligibleAgent:
    functional_key: str
    title: str
    eligible: bool
    stage_scope: str  # "workspace" | "project" | "workspace+project" | "none"
    reasons: tuple[str, ...]  # lý do khi KHÔNG eligible (rỗng khi eligible)


def _stage_scope(key: str, ws_pack: set[str], proj_pack: set[str] | None) -> str:
    in_ws = key in ws_pack
    in_proj = proj_pack is not None and key in proj_pack
    if in_ws and in_proj:
        return "workspace+project"
    if in_ws:
        return "workspace"
    if in_proj:
        return "project"
    return "none"


def compose_workforce(inp: CompositionInput) -> list[EligibleAgent]:
    ws_pack = _WORKSPACE_STAGE_PACKS.get(inp.workspace_stage, set())
    proj_pack = _PROJECT_STAGE_PACKS.get(inp.project_stage) if inp.project_stage else None

    out: list[EligibleAgent] = []
    for key in sorted(FUNCTIONAL_AGENT_CATALOG):
        entry = FUNCTIONAL_AGENT_CATALOG[key]
        reasons: list[str] = []

        scope = _stage_scope(key, ws_pack, proj_pack)
        if scope == "none":
            reasons.append(
                f"không thuộc default pack của stage {inp.workspace_stage}"
                + (f" / {inp.project_stage}" if inp.project_stage else "")
            )

        feature = _DEPT_FEATURE.get(entry.default_department)
        if feature and feature not in inp.entitled_features:
            reasons.append(f"entitlement thiếu feature '{feature}'")

        not_ready = [
            ref for ref in entry.capability_refs if not inp.capability_readiness.get(ref, False)
        ]
        if not_ready:
            reasons.append(f"capability chưa sẵn sàng: {not_ready}")

        out.append(
            EligibleAgent(
                functional_key=key,
                title=entry.title,
                eligible=not reasons,
                stage_scope=scope,
                reasons=tuple(reasons),
            )
        )
    return out
