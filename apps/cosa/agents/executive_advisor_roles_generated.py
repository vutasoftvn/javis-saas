# GENERATED FILE — DO NOT MODIFY DIRECTLY
# Source: shared/contracts/executive-advisor-roles.json · Generator: scripts/gen-executive-advisor-roles.mjs
# To update: edit shared/contracts/executive-advisor-roles.json and run `node scripts/gen-executive-advisor-roles.mjs`
from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

StartupCorePresetKey = Literal[
    'startup-discovery',
    'startup-build-launch',
]

ExecutiveRoleKey = Literal[
    "chief_of_staff",
    "cfo",
    "cmo",
    "coo",
    "cro",
    "cpo",
    "cco",
    "chro",
    "ciso",
    "gc",
    "cdo",
    "caio",
    "vpe",
]

ExecutiveRuntimeReadiness = Literal[
    'READY',
    'PENDING_OPERATIONS_PROFILE',
    'PENDING_SALES_PROFILE',
    'PENDING_PRODUCT_PROFILE',
    'PENDING_CUSTOMER_SUPPORT_PROFILE',
    'PENDING_PEOPLE_PROFILE',
    'PENDING_SECURITY_PROFILE',
    'PENDING_LEGAL_PROFILE',
    'PENDING_DATA_PROFILE',
    'PENDING_AI_GOVERNANCE_PROFILE',
    'PENDING_ENGINEERING_PROFILE',
]

EXECUTIVE_ROLE_KEYS: Final[tuple[ExecutiveRoleKey, ...]] = (
    "chief_of_staff",
    "cfo",
    "cmo",
    "coo",
    "cro",
    "cpo",
    "cco",
    "chro",
    "ciso",
    "gc",
    "cdo",
    "caio",
    "vpe",
)

STARTUP_CORE_PRESET_KEYS: Final[tuple[StartupCorePresetKey, ...]] = (
    "startup-discovery",
    "startup-build-launch",
)

@dataclass(frozen=True)
class ExecutiveAdvisorRoleDef:
    key: ExecutiveRoleKey
    label: str
    advisory_remit: str
    required_profile_key: str
    required_agent_spec: str
    required_skill_pins: tuple[str, ...]
    advisory_only: bool
    runtime_readiness: ExecutiveRuntimeReadiness
    source_provenance: str

@dataclass(frozen=True)
class StartupCorePresetDef:
    key: StartupCorePresetKey
    label: str
    description: str
    default_role_keys: tuple[ExecutiveRoleKey, ...]

EXECUTIVE_ROLE_CATALOG: Final[dict[ExecutiveRoleKey, ExecutiveAdvisorRoleDef]] = {
    "chief_of_staff": ExecutiveAdvisorRoleDef(key="chief_of_staff", label="Chief of Staff", advisory_remit="Deliberation framing, cross-functional routing, synthesis, decision-log hygiene", required_profile_key="operations", required_agent_spec="cosa.executive.chief_of_staff", required_skill_pins=("skillpack:executive/board-protocol@1.0.0", "skillpack:executive/chief-of-staff@1.0.0",), advisory_only=True, runtime_readiness="READY", source_provenance="superpowers:executive-advisory-board"),
    "cfo": ExecutiveAdvisorRoleDef(key="cfo", label="Chief Financial Officer", advisory_remit="Cash runway, scenario modeling, budget guardrails, unit economics", required_profile_key="finance", required_agent_spec="cosa.executive.cfo", required_skill_pins=("skillpack:executive/cfo-advisor@1.0.0",), advisory_only=True, runtime_readiness="READY", source_provenance="superpowers:executive-advisory-board"),
    "cmo": ExecutiveAdvisorRoleDef(key="cmo", label="Chief Marketing Officer", advisory_remit="Positioning, demand generation, messaging, growth experiment strategy", required_profile_key="marketing", required_agent_spec="cosa.executive.cmo", required_skill_pins=("skillpack:executive/cmo-advisor@1.0.0",), advisory_only=True, runtime_readiness="READY", source_provenance="superpowers:executive-advisory-board"),
    "coo": ExecutiveAdvisorRoleDef(key="coo", label="Chief Operating Officer", advisory_remit="Operational cadence, process constraints, delivery dependency mapping", required_profile_key="operations", required_agent_spec="cosa.executive.coo", required_skill_pins=("skillpack:executive/coo-advisor@1.0.0",), advisory_only=True, runtime_readiness="READY", source_provenance="superpowers:executive-advisory-board"),
    "cro": ExecutiveAdvisorRoleDef(key="cro", label="Chief Revenue Officer", advisory_remit="Revenue pipeline, sales enablement, pricing guardrails, RevOps alignment", required_profile_key="sales", required_agent_spec="cosa.executive.cro", required_skill_pins=("skillpack:executive/cro-advisor@1.0.0",), advisory_only=True, runtime_readiness="READY", source_provenance="superpowers:executive-advisory-board"),
    "cpo": ExecutiveAdvisorRoleDef(key="cpo", label="Chief Product Officer", advisory_remit="Customer problem validation, product bets, PRD and backlog priority review", required_profile_key="product", required_agent_spec="cosa.executive.cpo", required_skill_pins=("skillpack:executive/cpo-advisor@1.0.0",), advisory_only=True, runtime_readiness="READY", source_provenance="superpowers:executive-advisory-board"),
    "cco": ExecutiveAdvisorRoleDef(key="cco", label="Chief Customer Officer", advisory_remit="Customer retention, lifecycle health, support pattern learning", required_profile_key="customer_support", required_agent_spec="cosa.executive.cco", required_skill_pins=("skillpack:executive/cco-advisor@1.0.0",), advisory_only=True, runtime_readiness="READY", source_provenance="superpowers:executive-advisory-board"),
    "chro": ExecutiveAdvisorRoleDef(key="chro", label="Chief Human Resources Officer", advisory_remit="Organizational design, hiring process evaluation, team and people risk", required_profile_key="people", required_agent_spec="cosa.executive.chro", required_skill_pins=("skillpack:executive/chro-advisor@1.0.0",), advisory_only=True, runtime_readiness="READY", source_provenance="superpowers:executive-advisory-board"),
    "ciso": ExecutiveAdvisorRoleDef(key="ciso", label="Chief Information Security Officer", advisory_remit="Security threat modeling, privacy controls, compliance gap assessment", required_profile_key="security", required_agent_spec="cosa.executive.ciso", required_skill_pins=("skillpack:executive/ciso-advisor@1.0.0",), advisory_only=True, runtime_readiness="READY", source_provenance="superpowers:executive-advisory-board"),
    "gc": ExecutiveAdvisorRoleDef(key="gc", label="General Counsel", advisory_remit="Legal and regulatory issue spotting, policy risk resolution, escalation", required_profile_key="legal", required_agent_spec="cosa.executive.gc", required_skill_pins=("skillpack:executive/gc-advisor@1.0.0",), advisory_only=True, runtime_readiness="READY", source_provenance="superpowers:executive-advisory-board"),
    "cdo": ExecutiveAdvisorRoleDef(key="cdo", label="Chief Data Officer", advisory_remit="Data governance, quality, rights management, scoped knowledge integrity", required_profile_key="data", required_agent_spec="cosa.executive.cdo", required_skill_pins=("skillpack:executive/cdo-advisor@1.0.0",), advisory_only=True, runtime_readiness="PENDING_DATA_PROFILE", source_provenance="superpowers:executive-advisory-board"),
    "caio": ExecutiveAdvisorRoleDef(key="caio", label="Chief AI Officer", advisory_remit="Model evaluation, provider governance, prompt safety, red-team assessment", required_profile_key="ai_governance", required_agent_spec="cosa.executive.caio", required_skill_pins=("skillpack:executive/caio-advisor@1.0.0",), advisory_only=True, runtime_readiness="PENDING_AI_GOVERNANCE_PROFILE", source_provenance="superpowers:executive-advisory-board"),
    "vpe": ExecutiveAdvisorRoleDef(key="vpe", label="VP Engineering", advisory_remit="Technical feasibility, architecture constraints, release readiness, delivery risks", required_profile_key="coding", required_agent_spec="cosa.executive.vpe", required_skill_pins=("skillpack:executive/vpe-advisor@1.0.0",), advisory_only=True, runtime_readiness="READY", source_provenance="superpowers:executive-advisory-board"),
}

STARTUP_CORE_PRESETS: Final[dict[StartupCorePresetKey, StartupCorePresetDef]] = {
    "startup-discovery": StartupCorePresetDef(key="startup-discovery", label="Startup Discovery Core", description="Giữ focus quyết định, kiểm chứng nhu cầu/thông điệp và kiểm soát runway sớm.", default_role_keys=("chief_of_staff", "cmo", "cfo",)),
    "startup-build-launch": StartupCorePresetDef(key="startup-build-launch", label="Startup Build & Launch Core", description="Bổ sung điều phối vận hành khi Founder đã chủ động vào giai đoạn build/launch.", default_role_keys=("chief_of_staff", "cmo", "cfo", "coo",)),
}

def is_executive_role_key(val: object) -> bool:
    return isinstance(val, str) and val in EXECUTIVE_ROLE_KEYS

def is_startup_core_preset_key(val: object) -> bool:
    return isinstance(val, str) and val in STARTUP_CORE_PRESET_KEYS
