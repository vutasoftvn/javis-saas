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
    WorkforceEmployeeRecord,
)
from agent.workforce.outcome_analysis import (
    OUTCOME_ANALYSIS_SKILL_ID,
    OUTCOME_ANALYST_CAPABILITY_REFS,
    OutcomeAnalysisBinding,
    resolve_outcome_analysis_binding,
)
from agent.workforce.reporting import (
    ReportingLineError,
    check_reporting_line,
    direct_reports,
    manager_chain,
)
from agent.workforce.repository import (
    DuplicateEmployeeCodeError,
    EmployeeNotAssignableError,
    InMemoryWorkforceRepository,
    PostgresWorkforceRepository,
    WorkforceRepository,
)

__all__ = [
    "FUNCTIONAL_AGENT_CATALOG",
    "OUTCOME_ANALYSIS_SKILL_ID",
    "OUTCOME_ANALYST_CAPABILITY_REFS",
    "CapabilityBoundaryError",
    "CompositionInput",
    "DuplicateEmployeeCodeError",
    "EligibleAgent",
    "EmployeeNotAssignableError",
    "FunctionalAgentEntry",
    "InMemoryWorkforceRepository",
    "OutcomeAnalysisBinding",
    "PostgresWorkforceRepository",
    "ReportingLineError",
    "RunCostObservationRecord",
    "RuntimeSignalOutboxRecord",
    "WorkforceAssignment",
    "WorkforceAssignmentRecord",
    "WorkforceEmployeeRecord",
    "WorkforceRepository",
    "assert_within_capability_boundary",
    "build_functional_spec",
    "capability_change_requires_new_spec",
    "catalog_keys",
    "check_reporting_line",
    "compose_workforce",
    "direct_reports",
    "execution_capabilities",
    "manager_chain",
    "resolve_outcome_analysis_binding",
]
