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
    "integrations.realtime.tools",
    "platform_core.license.tools",
    "founder_os.strategy.tools",
    "platform_core.vault.vault_tools",
    "workforce.chat.proposal_tools",
    "founder_os.validation.validation_tools",
    "business.sales.sales_tools",
    "business.finance.finance_tools",
    "business.legal.legal_tools",
    "business.marketing.marketing_tools",
    "workforce.agents.execution.tools",
)


def load_all_tools() -> None:
    """Idempotent: import lần thứ hai chỉ là tra ``sys.modules``."""
    for module_name in _TOOL_MODULES:
        importlib.import_module(module_name)
