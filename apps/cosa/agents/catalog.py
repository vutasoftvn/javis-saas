"""Canonical Agent runtime catalog for COSA.

Single source of truth for:
- profile routing (AGENT_PROFILE_SPECS)
- prompt & agent seeding order (seed_cosa_agent_specs)
- deployed runtime validation (seed_cosa_runtime_specs)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from agent.contracts.prompt import PromptSpec
from agent.contracts.spec import AgentSpec

from apps.cosa.agents.specs import (
    COSA_AI_GOVERNANCE_AGENT_SPEC,
    COSA_AI_GOVERNANCE_PROMPT,
    COSA_CODING_AGENT_SPEC,
    COSA_CODING_PROMPT,
    COSA_COFOUNDER_ASSISTANT_AGENT_SPEC,
    COSA_COFOUNDER_ASSISTANT_PROMPT,
    COSA_CUSTOMER_SUPPORT_AGENT_SPEC,
    COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC,
    COSA_CUSTOMER_SUPPORT_AUTOPILOT_PROMPT,
    COSA_CUSTOMER_SUPPORT_PROMPT,
    COSA_DATA_AGENT_SPEC,
    COSA_DATA_PROMPT,
    COSA_EXECUTIVE_CAIO_AGENT_SPEC,
    COSA_EXECUTIVE_CAIO_PROMPT,
    COSA_EXECUTIVE_CCO_AGENT_SPEC,
    COSA_EXECUTIVE_CCO_PROMPT,
    COSA_EXECUTIVE_CDO_AGENT_SPEC,
    COSA_EXECUTIVE_CDO_PROMPT,
    COSA_EXECUTIVE_CEO_AGENT_SPEC,
    COSA_EXECUTIVE_CEO_PROMPT,
    COSA_EXECUTIVE_CFO_AGENT_SPEC,
    COSA_EXECUTIVE_CFO_PROMPT,
    COSA_EXECUTIVE_CHIEF_OF_STAFF_AGENT_SPEC,
    COSA_EXECUTIVE_CHIEF_OF_STAFF_PROMPT,
    COSA_EXECUTIVE_CHRO_AGENT_SPEC,
    COSA_EXECUTIVE_CHRO_PROMPT,
    COSA_EXECUTIVE_CISO_AGENT_SPEC,
    COSA_EXECUTIVE_CISO_PROMPT,
    COSA_EXECUTIVE_CMO_AGENT_SPEC,
    COSA_EXECUTIVE_CMO_PROMPT,
    COSA_EXECUTIVE_COO_AGENT_SPEC,
    COSA_EXECUTIVE_COO_PROMPT,
    COSA_EXECUTIVE_CPO_AGENT_SPEC,
    COSA_EXECUTIVE_CPO_PROMPT,
    COSA_EXECUTIVE_CRO_AGENT_SPEC,
    COSA_EXECUTIVE_CRO_PROMPT,
    COSA_EXECUTIVE_CTO_AGENT_SPEC,
    COSA_EXECUTIVE_CTO_PROMPT,
    COSA_EXECUTIVE_GC_AGENT_SPEC,
    COSA_EXECUTIVE_GC_PROMPT,
    COSA_EXECUTIVE_VPE_AGENT_SPEC,
    COSA_EXECUTIVE_VPE_PROMPT,
    COSA_FINANCE_AGENT_SPEC,
    COSA_FINANCE_PROMPT,
    COSA_KICKOFF_SUGGESTION_AGENT_SPEC,
    COSA_KICKOFF_SUGGESTION_PROMPT,
    COSA_LEGAL_AGENT_SPEC,
    COSA_LEGAL_PROMPT,
    COSA_MARKETING_AGENT_SPEC,
    COSA_MARKETING_PROMPT,
    COSA_OPERATIONS_AGENT_SPEC,
    COSA_OPERATIONS_PROMPT,
    COSA_PEOPLE_AGENT_SPEC,
    COSA_PEOPLE_PROMPT,
    COSA_PRODUCT_AGENT_SPEC,
    COSA_PRODUCT_PROMPT,
    COSA_RESEARCH_INTELLIGENCE_AGENT_SPEC,
    COSA_RESEARCH_INTELLIGENCE_PROMPT,
    COSA_SALES_AGENT_SPEC,
    COSA_SALES_PROMPT,
    COSA_SECURITY_AGENT_SPEC,
    COSA_SECURITY_PROMPT,
    COSA_STRATEGY_AGENT_SPEC,
    COSA_STRATEGY_PROMPT,
)

AvailabilityKind = Literal["public", "deployed_not_public", "declared_only"]
DeploymentKind = Literal["operating", "executive", "system"]


@dataclass(frozen=True)
class RuntimeAgentCatalogEntry:
    profile_key: str
    agent_spec: AgentSpec
    prompt_spec: PromptSpec
    availability: AvailabilityKind
    deployment_kind: DeploymentKind = "operating"


_RAW_ENTRIES: tuple[RuntimeAgentCatalogEntry, ...] = (
    # Public operating agents
    RuntimeAgentCatalogEntry(
        profile_key="operations",
        agent_spec=COSA_OPERATIONS_AGENT_SPEC,
        prompt_spec=COSA_OPERATIONS_PROMPT,
        availability="public",
        deployment_kind="operating",
    ),
    RuntimeAgentCatalogEntry(
        profile_key="founder_assistant",
        agent_spec=COSA_COFOUNDER_ASSISTANT_AGENT_SPEC,
        prompt_spec=COSA_COFOUNDER_ASSISTANT_PROMPT,
        availability="public",
        deployment_kind="operating",
    ),
    RuntimeAgentCatalogEntry(
        profile_key="finance",
        agent_spec=COSA_FINANCE_AGENT_SPEC,
        prompt_spec=COSA_FINANCE_PROMPT,
        availability="public",
        deployment_kind="operating",
    ),
    RuntimeAgentCatalogEntry(
        profile_key="marketing",
        agent_spec=COSA_MARKETING_AGENT_SPEC,
        prompt_spec=COSA_MARKETING_PROMPT,
        availability="public",
        deployment_kind="operating",
    ),
    RuntimeAgentCatalogEntry(
        profile_key="research_intelligence",
        agent_spec=COSA_RESEARCH_INTELLIGENCE_AGENT_SPEC,
        prompt_spec=COSA_RESEARCH_INTELLIGENCE_PROMPT,
        availability="public",
        deployment_kind="operating",
    ),
    RuntimeAgentCatalogEntry(
        profile_key="strategy",
        agent_spec=COSA_STRATEGY_AGENT_SPEC,
        prompt_spec=COSA_STRATEGY_PROMPT,
        availability="public",
        deployment_kind="operating",
    ),
    RuntimeAgentCatalogEntry(
        profile_key="customer_support",
        agent_spec=COSA_CUSTOMER_SUPPORT_AGENT_SPEC,
        prompt_spec=COSA_CUSTOMER_SUPPORT_PROMPT,
        availability="public",
        deployment_kind="operating",
    ),
    RuntimeAgentCatalogEntry(
        profile_key="sales",
        agent_spec=COSA_SALES_AGENT_SPEC,
        prompt_spec=COSA_SALES_PROMPT,
        availability="public",
        deployment_kind="operating",
    ),
    RuntimeAgentCatalogEntry(
        profile_key="coding",
        agent_spec=COSA_CODING_AGENT_SPEC,
        prompt_spec=COSA_CODING_PROMPT,
        availability="public",
        deployment_kind="operating",
    ),
    RuntimeAgentCatalogEntry(
        profile_key="product",
        agent_spec=COSA_PRODUCT_AGENT_SPEC,
        prompt_spec=COSA_PRODUCT_PROMPT,
        availability="public",
        deployment_kind="operating",
    ),
    RuntimeAgentCatalogEntry(
        profile_key="people",
        agent_spec=COSA_PEOPLE_AGENT_SPEC,
        prompt_spec=COSA_PEOPLE_PROMPT,
        availability="public",
        deployment_kind="operating",
    ),
    RuntimeAgentCatalogEntry(
        profile_key="security",
        agent_spec=COSA_SECURITY_AGENT_SPEC,
        prompt_spec=COSA_SECURITY_PROMPT,
        availability="public",
        deployment_kind="operating",
    ),
    RuntimeAgentCatalogEntry(
        profile_key="legal",
        agent_spec=COSA_LEGAL_AGENT_SPEC,
        prompt_spec=COSA_LEGAL_PROMPT,
        availability="public",
        deployment_kind="operating",
    ),
    RuntimeAgentCatalogEntry(
        profile_key="data",
        agent_spec=COSA_DATA_AGENT_SPEC,
        prompt_spec=COSA_DATA_PROMPT,
        availability="public",
        deployment_kind="operating",
    ),
    RuntimeAgentCatalogEntry(
        profile_key="ai_governance",
        agent_spec=COSA_AI_GOVERNANCE_AGENT_SPEC,
        prompt_spec=COSA_AI_GOVERNANCE_PROMPT,
        availability="public",
        deployment_kind="operating",
    ),
    # Public executive agents
    RuntimeAgentCatalogEntry(
        profile_key="cro",
        agent_spec=COSA_EXECUTIVE_CRO_AGENT_SPEC,
        prompt_spec=COSA_EXECUTIVE_CRO_PROMPT,
        availability="public",
        deployment_kind="executive",
    ),
    RuntimeAgentCatalogEntry(
        profile_key="cto",
        agent_spec=COSA_EXECUTIVE_CTO_AGENT_SPEC,
        prompt_spec=COSA_EXECUTIVE_CTO_PROMPT,
        availability="public",
        deployment_kind="executive",
    ),
    RuntimeAgentCatalogEntry(
        profile_key="vpe",
        agent_spec=COSA_EXECUTIVE_VPE_AGENT_SPEC,
        prompt_spec=COSA_EXECUTIVE_VPE_PROMPT,
        availability="public",
        deployment_kind="executive",
    ),
    RuntimeAgentCatalogEntry(
        profile_key="cpo",
        agent_spec=COSA_EXECUTIVE_CPO_AGENT_SPEC,
        prompt_spec=COSA_EXECUTIVE_CPO_PROMPT,
        availability="public",
        deployment_kind="executive",
    ),
    RuntimeAgentCatalogEntry(
        profile_key="chro",
        agent_spec=COSA_EXECUTIVE_CHRO_AGENT_SPEC,
        prompt_spec=COSA_EXECUTIVE_CHRO_PROMPT,
        availability="public",
        deployment_kind="executive",
    ),
    RuntimeAgentCatalogEntry(
        profile_key="ciso",
        agent_spec=COSA_EXECUTIVE_CISO_AGENT_SPEC,
        prompt_spec=COSA_EXECUTIVE_CISO_PROMPT,
        availability="public",
        deployment_kind="executive",
    ),
    RuntimeAgentCatalogEntry(
        profile_key="gc",
        agent_spec=COSA_EXECUTIVE_GC_AGENT_SPEC,
        prompt_spec=COSA_EXECUTIVE_GC_PROMPT,
        availability="public",
        deployment_kind="executive",
    ),
    RuntimeAgentCatalogEntry(
        profile_key="cdo",
        agent_spec=COSA_EXECUTIVE_CDO_AGENT_SPEC,
        prompt_spec=COSA_EXECUTIVE_CDO_PROMPT,
        availability="public",
        deployment_kind="executive",
    ),
    RuntimeAgentCatalogEntry(
        profile_key="caio",
        agent_spec=COSA_EXECUTIVE_CAIO_AGENT_SPEC,
        prompt_spec=COSA_EXECUTIVE_CAIO_PROMPT,
        availability="public",
        deployment_kind="executive",
    ),
    # Advisor overlay (seeded + published; không public như profile độc lập)
    RuntimeAgentCatalogEntry(
        profile_key="chief_of_staff",
        agent_spec=COSA_EXECUTIVE_CHIEF_OF_STAFF_AGENT_SPEC,
        prompt_spec=COSA_EXECUTIVE_CHIEF_OF_STAFF_PROMPT,
        availability="deployed_not_public",
        deployment_kind="executive",
    ),
    RuntimeAgentCatalogEntry(
        profile_key="cfo",
        agent_spec=COSA_EXECUTIVE_CFO_AGENT_SPEC,
        prompt_spec=COSA_EXECUTIVE_CFO_PROMPT,
        availability="deployed_not_public",
        deployment_kind="executive",
    ),
    RuntimeAgentCatalogEntry(
        profile_key="cmo",
        agent_spec=COSA_EXECUTIVE_CMO_AGENT_SPEC,
        prompt_spec=COSA_EXECUTIVE_CMO_PROMPT,
        availability="deployed_not_public",
        deployment_kind="executive",
    ),
    RuntimeAgentCatalogEntry(
        profile_key="coo",
        agent_spec=COSA_EXECUTIVE_COO_AGENT_SPEC,
        prompt_spec=COSA_EXECUTIVE_COO_PROMPT,
        availability="deployed_not_public",
        deployment_kind="executive",
    ),
    RuntimeAgentCatalogEntry(
        profile_key="cco",
        agent_spec=COSA_EXECUTIVE_CCO_AGENT_SPEC,
        prompt_spec=COSA_EXECUTIVE_CCO_PROMPT,
        availability="deployed_not_public",
        deployment_kind="executive",
    ),
    # Deployed but not public agents
    RuntimeAgentCatalogEntry(
        profile_key="customer_support_autopilot",
        agent_spec=COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC,
        prompt_spec=COSA_CUSTOMER_SUPPORT_AUTOPILOT_PROMPT,
        availability="deployed_not_public",
        deployment_kind="system",
    ),
    RuntimeAgentCatalogEntry(
        profile_key="kickoff_suggestion",
        agent_spec=COSA_KICKOFF_SUGGESTION_AGENT_SPEC,
        prompt_spec=COSA_KICKOFF_SUGGESTION_PROMPT,
        availability="deployed_not_public",
        deployment_kind="system",
    ),
    # Advisor overlay CEO
    RuntimeAgentCatalogEntry(
        profile_key="ceo",
        agent_spec=COSA_EXECUTIVE_CEO_AGENT_SPEC,
        prompt_spec=COSA_EXECUTIVE_CEO_PROMPT,
        availability="deployed_not_public",
        deployment_kind="executive",
    ),
)


def _validate_catalog(entries: tuple[RuntimeAgentCatalogEntry, ...]) -> None:
    seen_profiles: set[str] = set()
    seen_agent_ids: set[str] = set()
    for entry in entries:
        if entry.profile_key in seen_profiles:
            raise ValueError(f"Duplicate profile_key in catalog: {entry.profile_key}")
        seen_profiles.add(entry.profile_key)

        if entry.agent_spec.id in seen_agent_ids:
            raise ValueError(f"Duplicate agent_spec.id in catalog: {entry.agent_spec.id}")
        seen_agent_ids.add(entry.agent_spec.id)

        # Enforce prompt reference integrity
        prompt_ref = entry.agent_spec.prompt_ref
        if prompt_ref is None or prompt_ref.spec_id != entry.prompt_spec.id:
            raise ValueError(
                f"Entry {entry.profile_key} prompt_ref.spec_id "
                f"{prompt_ref.spec_id if prompt_ref else None} "
                f"does not match prompt_spec.id {entry.prompt_spec.id}"
            )
        if prompt_ref.spec_version != entry.prompt_spec.version:
            raise ValueError(
                f"Entry {entry.profile_key} prompt_ref.spec_version {prompt_ref.spec_version} "
                f"does not match prompt_spec.version {entry.prompt_spec.version}"
            )


_validate_catalog(_RAW_ENTRIES)

CATALOG_BY_PROFILE: dict[str, RuntimeAgentCatalogEntry] = {e.profile_key: e for e in _RAW_ENTRIES}

PUBLIC_PROFILE_KEYS: frozenset[str] = frozenset(
    e.profile_key for e in _RAW_ENTRIES if e.availability == "public"
)


def public_profile_specs() -> dict[str, AgentSpec]:
    """Exposes all public profile specs keyed by profile_key."""
    return {e.profile_key: e.agent_spec for e in _RAW_ENTRIES if e.availability == "public"}


def seeded_entries() -> tuple[RuntimeAgentCatalogEntry, ...]:
    """Exposes all entries that must be published into the spec registry."""
    return _RAW_ENTRIES


def deployed_entries() -> tuple[RuntimeAgentCatalogEntry, ...]:
    """Exposes all entries actively deployed in the runtime."""
    return tuple(e for e in _RAW_ENTRIES if e.availability in ("public", "deployed_not_public"))
