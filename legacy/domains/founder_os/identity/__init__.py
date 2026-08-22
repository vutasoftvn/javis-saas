"""Founder OS — Identity Subdomain

Quản lý các định hướng chiến lược dài hạn, bất biến của công ty:
- Vision (Tầm nhìn)
- Mission (Sứ mệnh)
- Core Values (Giá trị cốt lõi)
- Strategy Canvas
"""

from founder_os.strategy.strategy_canvas_service import StrategyCanvasService
from founder_os.strategy.foundation_ai_service import FoundationAIService
from founder_os.strategy.foundation_context import load_foundation_context

__all__ = [
    "StrategyCanvasService",
    "FoundationAIService",
    "load_foundation_context",
]
