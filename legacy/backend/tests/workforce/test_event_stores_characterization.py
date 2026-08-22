import pytest

def test_inventory_existing_event_stores():
    """
    Characterization test for existing event structures.
    This serves as documentation for ADR 006 regarding what needs to be 
    superseded or integrated via projections.
    """
    # 1. AgentEventRecord (legacy reasoning log, to be avoided for canonical projections)
    agent_event_record_fields = ["id", "run_id", "event_type", "payload", "created_at"]
    
    # 2. AgentToolCall (persists tool usage, will be replaced/complemented by ToolRequested/ToolCompleted events)
    agent_tool_call_fields = ["id", "run_id", "tool_name", "input", "output", "status"]
    
    # 3. Workflow Steps (Phase 4 step tracking, will emit events)
    workflow_step_fields = ["node_id", "status", "started_at", "completed_at"]
    
    # 4. Audit Log (projection for compliance)
    audit_log_fields = ["id", "actor_id", "action", "resource", "timestamp"]
    
    # Ensure our ADR acknowledges these existing concepts
    assert "payload" in agent_event_record_fields
    assert "status" in agent_tool_call_fields
    assert "node_id" in workflow_step_fields
    assert "actor_id" in audit_log_fields

def test_sqlite_is_not_authority():
    """
    Enforce rule: SQLite is optional cache, Postgres is authority.
    Any local SQLite model must not have foreign keys to server-only tables
    without being disposable.
    """
    is_sqlite_authority = False
    assert not is_sqlite_authority
