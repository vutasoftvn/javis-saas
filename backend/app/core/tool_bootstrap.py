"""Nạp mọi module có ``@register`` vào tool_registry.

Registry chỉ chứa tool khi module khai báo nó ĐÃ được import. Trước đây chỉ
``services/realtime_agent`` import ``app.integrations.realtime.tools``, nên trong tiến trình
brain-api và agent-worker registry rỗng hoàn toàn - bất cứ ai đọc registry ở đó đều nhận
danh sách trống mà không có lỗi nào để lần ra. Mọi nơi cần đọc registry phải gọi
``load_all_tools()`` trước, thay vì trông chờ một module khác đã import hộ.
"""

import importlib

# Thứ tự không quan trọng (decorator chạy khi import), nhưng danh sách thì có: thiếu một
# dòng ở đây là cả nhóm tool trong module đó biến mất trong im lặng.
_TOOL_MODULES = (
    "app.integrations.realtime.tools",
    "app.platform.license.tools",
    "app.founder_os.strategy.tools",
    "app.platform.vault.vault_tools",
    "app.workforce.chat.proposal_tools",
    "app.business.sales.sales_tools",
    "app.business.finance.finance_tools",
    "app.business.legal.legal_tools",
    "app.business.marketing.marketing_tools",
    "app.workforce.agents.execution.tools",
)


def load_all_tools() -> None:
    """Idempotent: import lần thứ hai chỉ là tra ``sys.modules``."""
    for module_name in _TOOL_MODULES:
        importlib.import_module(module_name)
