from unittest.mock import MagicMock, patch

from app.core.tool_registry import available_tools, get_registered_tools, register


def test_registry_keeps_namespace_and_name_unique():
    @register("test", "sample")
    def sample():
        return "ok"

    assert get_registered_tools()["test.sample"].callable is sample


def test_available_tools_filters_disabled_flag():
    @register("test", "gated", flag_key="test_flag")
    def gated():
        return "hidden"

    with patch("app.core.tool_registry.is_enabled", return_value=False):
        names = {spec.qualified_name for spec in available_tools(MagicMock(), 1)}

    assert "test.gated" not in names
