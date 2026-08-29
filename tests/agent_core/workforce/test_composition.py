"""M7 §4 — stage-aware composition."""

from __future__ import annotations

from agent_core.workforce import (
    FUNCTIONAL_AGENT_CATALOG,
    CompositionInput,
    compose_workforce,
)

ALL_CAPS_READY = {ref: True for e in FUNCTIONAL_AGENT_CATALOG.values() for ref in e.capability_refs}
ALL_FEATURES = frozenset({"finance", "marketing", "legal"})


def _by_key(agents):
    return {a.functional_key: a for a in agents}


def test_w0_pack_excludes_campaign_planner():
    agents = _by_key(
        compose_workforce(
            CompositionInput(
                workspace_stage="W0_IDEA",
                entitled_features=ALL_FEATURES,
                capability_readiness=ALL_CAPS_READY,
            )
        )
    )
    assert agents["founder_office_orchestrator"].eligible is True
    assert agents["market_research_specialist"].eligible is True
    assert agents["campaign_planner"].eligible is False
    assert any("default pack" in r for r in agents["campaign_planner"].reasons)


def test_entitlement_gates_department():
    agents = _by_key(
        compose_workforce(
            CompositionInput(
                workspace_stage="W4_PRODUCT_MARKET_FIT",
                entitled_features=frozenset({"legal"}),  # thiếu finance + marketing
                capability_readiness=ALL_CAPS_READY,
            )
        )
    )
    assert agents["compliance_analyst"].eligible is True
    assert agents["cashflow_planner"].eligible is False
    assert any("finance" in r for r in agents["cashflow_planner"].reasons)
    assert agents["campaign_planner"].eligible is False


def test_capability_readiness_required():
    readiness = dict(ALL_CAPS_READY)
    readiness["finance.cashflow.forecast"] = False
    agents = _by_key(
        compose_workforce(
            CompositionInput(
                workspace_stage="W4_PRODUCT_MARKET_FIT",
                entitled_features=ALL_FEATURES,
                capability_readiness=readiness,
            )
        )
    )
    assert agents["cashflow_planner"].eligible is False
    assert any("chưa sẵn sàng" in r for r in agents["cashflow_planner"].reasons)


def test_project_p0_in_workspace_w4_still_gets_discovery_scope():
    agents = _by_key(
        compose_workforce(
            CompositionInput(
                workspace_stage="W4_PRODUCT_MARKET_FIT",
                project_stage="P0_DISCOVERY",
                entitled_features=ALL_FEATURES,
                capability_readiness=ALL_CAPS_READY,
            )
        )
    )
    # market_research thuộc cả W4 pack lẫn P0 discovery pack
    assert agents["market_research_specialist"].stage_scope == "workspace+project"
    # campaign_planner thuộc W4 nhưng KHÔNG thuộc P0
    assert agents["campaign_planner"].stage_scope == "workspace"
    assert agents["campaign_planner"].eligible is True  # vẫn eligible ở workspace scope


def test_unknown_stage_yields_no_workspace_pack():
    agents = _by_key(
        compose_workforce(
            CompositionInput(
                workspace_stage="W9_BOGUS",
                entitled_features=ALL_FEATURES,
                capability_readiness=ALL_CAPS_READY,
            )
        )
    )
    assert all(a.eligible is False for a in agents.values())
