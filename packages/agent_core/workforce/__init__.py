"""Functional AgentSpec catalog + workforce governance — M7 §1/§5.

Ba lớp identity (audit §7.2):
- **Capability** — `finance.transaction.read`, `finance.cashflow.forecast`, …
- **Functional AgentSpec** — "Cashflow Planner", "Compliance Analyst", … pin
  `capability_refs` + `definition_hash` = execution identity.
- **Workforce Assignment** — "Finance Copilot", "CFO", … CHỈ là role/persona
  overlay ở workspace level. Title KHÔNG cấp quyền (§7.4): capability thực thi
  luôn đến từ AgentSpec, không bao giờ từ `role_title`.

Không import `services/*`.
"""

from agent_core.workforce.catalog import (
    FUNCTIONAL_AGENT_CATALOG,
    FunctionalAgentEntry,
    build_functional_spec,
    catalog_keys,
)
from agent_core.workforce.governance import (
    CapabilityBoundaryError,
    WorkforceAssignment,
    assert_within_capability_boundary,
    capability_change_requires_new_spec,
    execution_capabilities,
)

__all__ = [
    "FUNCTIONAL_AGENT_CATALOG",
    "CapabilityBoundaryError",
    "FunctionalAgentEntry",
    "WorkforceAssignment",
    "assert_within_capability_boundary",
    "build_functional_spec",
    "capability_change_requires_new_spec",
    "catalog_keys",
    "execution_capabilities",
]
