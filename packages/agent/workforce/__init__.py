"""Functional AgentSpec catalog + workforce governance — M7 §1/§5."""

from agent.workforce.catalog import (
    FUNCTIONAL_AGENT_CATALOG,
    FunctionalAgentEntry,
    build_functional_spec,
    catalog_keys,
)
from agent.workforce.composition import (
    CompositionInput,
    EligibleAgent,
    compose_workforce,
)
from agent.workforce.governance import (
    CapabilityBoundaryError,
    WorkforceAssignment,
    assert_within_capability_boundary,
    capability_change_requires_new_spec,
    execution_capabilities,
)
from agent.workforce.models import (
    RunCostObservationRecord,
    RuntimeSignalOutboxRecord,
    WorkforceAssignmentRecord,
)
from agent.workforce.repository import (
    InMemoryWorkforceRepository,
    PostgresWorkforceRepository,
    WorkforceRepository,
)

__all__ = [
    "FUNCTIONAL_AGENT_CATALOG",
    "CapabilityBoundaryError",
    "CompositionInput",
    "EligibleAgent",
    "FunctionalAgentEntry",
    "InMemoryWorkforceRepository",
    "PostgresWorkforceRepository",
    "RunCostObservationRecord",
    "RuntimeSignalOutboxRecord",
    "WorkforceAssignment",
    "WorkforceAssignmentRecord",
    "WorkforceRepository",
    "assert_within_capability_boundary",
    "build_functional_spec",
    "capability_change_requires_new_spec",
    "catalog_keys",
    "compose_workforce",
    "execution_capabilities",
]
