import pytest

def test_profile_imports_from_workforce():
    """
    Test đảm bảo các module có thể import canonical profile assets từ
    `app.workforce.agents.profiles` thay vì `agent_runtime`.
    """
    try:
        from app.workforce.agents.profiles.schemas import AgentProfile
        from app.workforce.agents.profiles.registry import agent_profile_registry
        
        assert AgentProfile is not None
        assert agent_profile_registry is not None
    except ImportError as e:
        pytest.fail(f"Failed to import from workforce paths: {e}")
