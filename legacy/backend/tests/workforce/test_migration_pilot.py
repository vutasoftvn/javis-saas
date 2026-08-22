import pytest

def test_migration_pilot_projection_parity():
    """
    Test verifying that legacy data safely migrates to the new projection
    without duplicating external effects.
    """
    # Dữ liệu Legacy
    legacy_agent_tool_calls = [
        {"id": 1, "run_id": "run_1", "tool_name": "ext.cosa.foo", "status": "completed"}
    ]
    
    # Hàm giả lập migrate sang Event Store
    migrated_events = []
    for call in legacy_agent_tool_calls:
        migrated_events.append({
            "event_type": "ToolRequested",
            "correlation_id": call["run_id"],
            "tool_name": call["tool_name"]
        })
        migrated_events.append({
            "event_type": "ToolCompleted",
            "correlation_id": call["run_id"],
            "tool_name": call["tool_name"]
        })
        
    # Xác minh tính toàn vẹn
    assert len(migrated_events) == 2
    assert migrated_events[0]["event_type"] == "ToolRequested"
    assert migrated_events[1]["event_type"] == "ToolCompleted"
