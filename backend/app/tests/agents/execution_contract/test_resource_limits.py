import pytest
from app.workforce.agents.execution.policies import DEFAULT_PRESETS


def test_preset_resource_limits():
    safe = DEFAULT_PRESETS["safe_analysis"]
    assert safe.cpu == 1.0
    assert safe.memory_mb == 1024
    assert safe.disk_mb == 1024
    assert safe.timeout_seconds == 300
    assert safe.network_default == "deny"
    assert safe.network_allow == []

    coding = DEFAULT_PRESETS["coding"]
    assert coding.cpu == 2.0
    assert coding.memory_mb == 2048
    assert coding.timeout_seconds == 600
    assert "github.com" in coding.network_allow
