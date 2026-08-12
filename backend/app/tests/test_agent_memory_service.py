from unittest.mock import MagicMock, patch

from app.core.snowflake import generate_snowflake_id
from app.modules.agent_memory.adapters.null_adapter import NullAgentMemoryAdapter
from app.modules.agent_memory.adapters.tencentdb_adapter import TencentDBAgentMemoryAdapter
from app.modules.agent_memory.service import get_gateway


def test_get_gateway_returns_null_adapter_when_flag_off():
    db = MagicMock()
    ws_id = generate_snowflake_id()

    with patch("app.modules.agent_memory.service.is_enabled", return_value=False):
        gateway = get_gateway(db, ws_id)

    assert isinstance(gateway, NullAgentMemoryAdapter)


def test_get_gateway_returns_tencentdb_adapter_when_flag_on():
    db = MagicMock()
    ws_id = generate_snowflake_id()

    with patch("app.modules.agent_memory.service.is_enabled", return_value=True):
        gateway = get_gateway(db, ws_id)

    assert isinstance(gateway, TencentDBAgentMemoryAdapter)
