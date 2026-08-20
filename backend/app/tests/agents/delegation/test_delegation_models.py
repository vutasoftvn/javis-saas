import importlib.util

from agent_runtime.sessions.models import AgentRun
from app.founder_os.outcomes.models import RunEvent, RunStep
from app.integrations.devices.models import DeveloperJob, JobLease


def test_phase_c_persistence_contract_is_registered():
    """Removing any durable correlation field breaks restart-safe delegation."""
    assert importlib.util.find_spec("app.workforce.agents.delegation.models") is not None

    from app.workforce.agents.delegation.models import DelegationJob

    assert {
        "assigned_agent_profile_id",
        "assigned_runtime",
        "delegated_run_id",
        "result_jsonb",
    } <= set(RunStep.__table__.columns.keys())
    assert {"sequence", "event_key"} <= set(RunEvent.__table__.columns.keys())
    assert {
        "lease_token",
        "lease_expires_at",
        "provider_handle_jsonb",
        "root_agent_run_id",
    } <= set(DelegationJob.__table__.columns.keys())
    assert {
        "agent_run_id",
        "run_step_id",
        "executor_kind",
        "request_jsonb",
        "result_jsonb",
        "cancel_requested_at",
    } <= set(DeveloperJob.__table__.columns.keys())
    assert {"lease_token_hash", "renewed_at"} <= set(JobLease.__table__.columns.keys())
    assert any(
        foreign_key.target_fullname == "agent_runs.id"
        for foreign_key in AgentRun.__table__.c.parent_run_id.foreign_keys
    )


def test_phase_c_models_use_canonical_defaults_and_uniqueness():
    """Wrong risk/job defaults or absent idempotency keys permit unsafe replay."""
    from app.workforce.agents.delegation.models import DelegationJob

    assert RunStep.__table__.c.risk_level.default.arg == "R0"
    assert DelegationJob.__table__.c.status.default.arg == "queued"

    constraint_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in DelegationJob.__table__.constraints
        if hasattr(constraint, "columns")
    }
    assert ("run_step_id", "attempt_no") in constraint_columns
    assert ("workspace_id", "idempotency_key") in constraint_columns
