"""Sync scope policy — M6 §3 (audit §5.6 bảng)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "ConflictPolicy",
    "SyncScope",
    "SyncScopeError",
    "SyncScopePolicy",
    "scope_for",
]


class SyncScopeError(Exception):
    """Entity không được phép sync (credentials / transient / chưa opt-in)."""


class SyncScope(StrEnum):
    CONTROL_METADATA = "CONTROL_METADATA"
    BUSINESS_MODULE = "BUSINESS_MODULE"
    FINANCE_LEGAL = "FINANCE_LEGAL"  # + approval / lifecycle / policy — critical
    CREDENTIALS = "CREDENTIALS"
    RUNS_MEMORY_ARTIFACTS = "RUNS_MEMORY_ARTIFACTS"
    TRANSIENT = "TRANSIENT"  # quarantine / temp / cache


class ConflictPolicy(StrEnum):
    OPTIMISTIC = "OPTIMISTIC"  # revision-based; diverge ⇒ apply + ghi audit
    HUMAN_RESOLVE = "HUMAN_RESOLVE"  # diverge ⇒ đưa vào sync/conflicts/, KHÔNG tự merge
    NEVER = "NEVER"  # không sync payload này qua kênh sync


class WhenPolicy(StrEnum):
    LINK_PLATFORM = "LINK_PLATFORM"  # sync khi workspace link platform
    OPT_IN = "OPT_IN"  # chỉ khi module + workspace bật
    NEVER = "NEVER"


@dataclass(frozen=True)
class SyncScopePolicy:
    scope: SyncScope
    syncs: bool
    conflict_policy: ConflictPolicy
    when: WhenPolicy
    note: str = ""


_POLICIES: dict[SyncScope, SyncScopePolicy] = {
    SyncScope.CONTROL_METADATA: SyncScopePolicy(
        SyncScope.CONTROL_METADATA, True, ConflictPolicy.OPTIMISTIC, WhenPolicy.LINK_PLATFORM
    ),
    SyncScope.BUSINESS_MODULE: SyncScopePolicy(
        SyncScope.BUSINESS_MODULE, True, ConflictPolicy.OPTIMISTIC, WhenPolicy.OPT_IN
    ),
    SyncScope.FINANCE_LEGAL: SyncScopePolicy(
        SyncScope.FINANCE_LEGAL,
        True,
        ConflictPolicy.HUMAN_RESOLVE,
        WhenPolicy.OPT_IN,
        note="critical: approval/lifecycle/policy — không LWW",
    ),
    SyncScope.CREDENTIALS: SyncScopePolicy(
        SyncScope.CREDENTIALS,
        False,
        ConflictPolicy.NEVER,
        WhenPolicy.NEVER,
        note="chỉ connector grant handle, KHÔNG raw secret",
    ),
    SyncScope.RUNS_MEMORY_ARTIFACTS: SyncScopePolicy(
        SyncScope.RUNS_MEMORY_ARTIFACTS,
        False,
        ConflictPolicy.NEVER,
        WhenPolicy.NEVER,
        note="local mặc định; optional encrypted backup riêng",
    ),
    SyncScope.TRANSIENT: SyncScopePolicy(
        SyncScope.TRANSIENT, False, ConflictPolicy.NEVER, WhenPolicy.NEVER
    ),
}

# entity_type (chuỗi ổn định) → scope. Prefix match cho các họ entity.
_ENTITY_SCOPE: dict[str, SyncScope] = {
    # control metadata
    "workspace": SyncScope.CONTROL_METADATA,
    "workspace_membership": SyncScope.CONTROL_METADATA,
    "workspace_slug": SyncScope.CONTROL_METADATA,
    "license": SyncScope.CONTROL_METADATA,
    "entitlement": SyncScope.CONTROL_METADATA,
    "workforce_member": SyncScope.CONTROL_METADATA,
    # business modules
    "task": SyncScope.BUSINESS_MODULE,
    "project": SyncScope.BUSINESS_MODULE,
    "portfolio": SyncScope.BUSINESS_MODULE,
    "okr_objective": SyncScope.BUSINESS_MODULE,
    "okr_cycle": SyncScope.BUSINESS_MODULE,
    "initiative": SyncScope.BUSINESS_MODULE,
    "customer": SyncScope.BUSINESS_MODULE,
    "opportunity": SyncScope.BUSINESS_MODULE,
    "sales_lead": SyncScope.BUSINESS_MODULE,
    "knowledge_document": SyncScope.BUSINESS_MODULE,
    "sop_definition": SyncScope.BUSINESS_MODULE,
    # finance / legal / approval / lifecycle / policy — critical
    "financial_transaction": SyncScope.FINANCE_LEGAL,
    "finance_snapshot": SyncScope.FINANCE_LEGAL,
    "invoice": SyncScope.FINANCE_LEGAL,
    "legal_entity_profile": SyncScope.FINANCE_LEGAL,
    "legal_verification_approval": SyncScope.FINANCE_LEGAL,
    "legal_obligation": SyncScope.FINANCE_LEGAL,
    "approval_record": SyncScope.FINANCE_LEGAL,
    "workspace_stage_transition": SyncScope.FINANCE_LEGAL,
    "project_stage_transition": SyncScope.FINANCE_LEGAL,
    "stage_transition_policy": SyncScope.FINANCE_LEGAL,
    "decision_record": SyncScope.FINANCE_LEGAL,
    # credentials
    "connector_authorization": SyncScope.CREDENTIALS,
    "connector_secret": SyncScope.CREDENTIALS,
    "secret": SyncScope.CREDENTIALS,
    "session_connector_grant": SyncScope.CREDENTIALS,
    # runs / memory / artifacts
    "run": SyncScope.RUNS_MEMORY_ARTIFACTS,
    "conversation": SyncScope.RUNS_MEMORY_ARTIFACTS,
    "memory_item": SyncScope.RUNS_MEMORY_ARTIFACTS,
    "artifact": SyncScope.RUNS_MEMORY_ARTIFACTS,
    # transient
    "quarantine_object": SyncScope.TRANSIENT,
    "temp_file": SyncScope.TRANSIENT,
    "cache_entry": SyncScope.TRANSIENT,
    "ingestion": SyncScope.TRANSIENT,
}

_PREFIX_SCOPE: list[tuple[str, SyncScope]] = [
    ("finance_", SyncScope.FINANCE_LEGAL),
    ("legal_", SyncScope.FINANCE_LEGAL),
    ("approval_", SyncScope.FINANCE_LEGAL),
    ("connector_", SyncScope.CREDENTIALS),
    ("secret_", SyncScope.CREDENTIALS),
    ("run_", SyncScope.RUNS_MEMORY_ARTIFACTS),
    ("memory_", SyncScope.RUNS_MEMORY_ARTIFACTS),
    ("artifact_", SyncScope.RUNS_MEMORY_ARTIFACTS),
    ("temp_", SyncScope.TRANSIENT),
    ("cache_", SyncScope.TRANSIENT),
    ("quarantine_", SyncScope.TRANSIENT),
]


def scope_for(entity_type: str) -> SyncScopePolicy:
    """Trả policy cho `entity_type`. Không nhận diện được ⇒ mặc định fail-closed:
    coi như FINANCE_LEGAL (critical, human-resolve, opt-in) — an toàn hơn là
    optimistic-merge một entity lạ."""
    key = (entity_type or "").strip().lower()
    scope = _ENTITY_SCOPE.get(key)
    if scope is None:
        for prefix, s in _PREFIX_SCOPE:
            if key.startswith(prefix):
                scope = s
                break
    if scope is None:
        scope = SyncScope.FINANCE_LEGAL  # fail-closed
    return _POLICIES[scope]
