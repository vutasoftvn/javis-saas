# GENERATED FILE — DO NOT MODIFY DIRECTLY
# Source: shared/contracts/startup-team-profiles.json · Generator: scripts/gen-startup-team-profiles.mjs
# To update: edit shared/contracts/startup-team-profiles.json and run `node scripts/gen-startup-team-profiles.mjs`
from __future__ import annotations

from typing import Final, Literal

StartupTeamProfileKey = Literal[
    "founder_assistant",
    "operations",
    "research_intelligence",
    "strategy",
    "marketing",
    "finance",
    "crm",
    "sales",
    "coding",
    "product",
    "customer_support",
]

RuntimeReadiness = Literal[
    'READY',
    'PENDING_CRM_FOUNDATION',
    'PENDING_PROJECT_KNOWLEDGE',
    'DEFERRED_CODING',
]

STARTUP_TEAM_PROFILE_KEYS: Final[tuple[StartupTeamProfileKey, ...]] = (
    "founder_assistant",
    "operations",
    "research_intelligence",
    "strategy",
    "marketing",
    "finance",
    "crm",
    "sales",
    "coding",
    "product",
    "customer_support",
)

STARTUP_TEAM_PROFILES: Final[list[dict[str, str]]] = [
    {"key":"founder_assistant","label":"Co-Founder","defaultMode":"CHAT_READY","runtimeReadiness":"READY"},
    {"key":"operations","label":"Operations","defaultMode":"TEMPLATE","runtimeReadiness":"READY"},
    {"key":"research_intelligence","label":"Research & Intelligence","defaultMode":"TEMPLATE","runtimeReadiness":"READY"},
    {"key":"strategy","label":"Strategy","defaultMode":"TEMPLATE","runtimeReadiness":"READY"},
    {"key":"marketing","label":"Marketing","defaultMode":"TEMPLATE","runtimeReadiness":"READY"},
    {"key":"finance","label":"Finance","defaultMode":"TEMPLATE","runtimeReadiness":"READY"},
    {"key":"crm","label":"CRM","defaultMode":"TEMPLATE","runtimeReadiness":"PENDING_CRM_FOUNDATION"},
    {"key":"sales","label":"Sales","defaultMode":"TEMPLATE","runtimeReadiness":"READY"},
    {"key":"coding","label":"Coding","defaultMode":"TEMPLATE","runtimeReadiness":"READY"},
    {"key":"product","label":"Product","defaultMode":"TEMPLATE","runtimeReadiness":"READY"},
    {"key":"customer_support","label":"Customer Support","defaultMode":"TEMPLATE","runtimeReadiness":"READY"},
]

STARTUP_TEAM_PROFILES_MAP: Final[dict[str, dict[str, str]]] = {
    "founder_assistant": {"key":"founder_assistant","label":"Co-Founder","defaultMode":"CHAT_READY","runtimeReadiness":"READY"},
    "operations": {"key":"operations","label":"Operations","defaultMode":"TEMPLATE","runtimeReadiness":"READY"},
    "research_intelligence": {"key":"research_intelligence","label":"Research & Intelligence","defaultMode":"TEMPLATE","runtimeReadiness":"READY"},
    "strategy": {"key":"strategy","label":"Strategy","defaultMode":"TEMPLATE","runtimeReadiness":"READY"},
    "marketing": {"key":"marketing","label":"Marketing","defaultMode":"TEMPLATE","runtimeReadiness":"READY"},
    "finance": {"key":"finance","label":"Finance","defaultMode":"TEMPLATE","runtimeReadiness":"READY"},
    "crm": {"key":"crm","label":"CRM","defaultMode":"TEMPLATE","runtimeReadiness":"PENDING_CRM_FOUNDATION"},
    "sales": {"key":"sales","label":"Sales","defaultMode":"TEMPLATE","runtimeReadiness":"READY"},
    "coding": {"key":"coding","label":"Coding","defaultMode":"TEMPLATE","runtimeReadiness":"READY"},
    "product": {"key":"product","label":"Product","defaultMode":"TEMPLATE","runtimeReadiness":"READY"},
    "customer_support": {"key":"customer_support","label":"Customer Support","defaultMode":"TEMPLATE","runtimeReadiness":"READY"},
}
