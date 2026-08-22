from unittest.mock import MagicMock, patch

from core.snowflake import generate_snowflake_id
from workforce.memory.adapters.null_adapter import NullAgentMemoryAdapter
from workforce.memory.adapters.tencentdb_adapter import TencentDBAgentMemoryAdapter
from workforce.memory.service import get_gateway


def test_get_gateway_returns_null_adapter_when_flag_off():
    db = MagicMock()
    ws_id = generate_snowflake_id()

    with patch("workforce.memory.service.is_enabled", return_value=False):
        gateway = get_gateway(db, ws_id)

    assert isinstance(gateway, NullAgentMemoryAdapter)


def test_get_gateway_returns_tencentdb_adapter_when_flag_on():
    db = MagicMock()
    ws_id = generate_snowflake_id()

    with patch("workforce.memory.service.is_enabled", return_value=True):
        gateway = get_gateway(db, ws_id)

    assert isinstance(gateway, TencentDBAgentMemoryAdapter)
