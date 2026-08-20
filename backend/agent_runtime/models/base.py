"""
COSA Model Provider & Capability Policy Router Contracts
Trừu tượng hóa việc gọi LLM theo Capability Policy (Structure.md Mục 30).
Không hardcode tên Model bên trong Business Core.
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ModelCapabilityPolicy(str, Enum):
    """Chính sách năng lực Model (Structure.md Mục 30)"""
    FAST = "fast"                   # Model phản hồi nhanh, tác vụ đơn giản (Haiku, GPT-4o-mini)
    REASONING = "reasoning"         # Model tư duy sâu, phân tích chiến lược (Claude 3.7 Sonnet, DeepSeek R1)
    CODING = "coding"               # Model chuyên sâu lập trình và sinh mã
    VISION = "vision"               # Model xử lý hình ảnh / biểu đồ
    LOCAL_PRIVATE = "local-private" # Model cục bộ bảo mật cao (Ollama / Local vLLM)


class ModelCallPayload(BaseModel):
    """Tham số gọi LLM chuẩn hóa"""
    messages: List[Dict[str, Any]]
    policy: ModelCapabilityPolicy = ModelCapabilityPolicy.REASONING
    system_prompt: Optional[str] = None
    tools: Optional[List[Dict[str, Any]]] = None
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: Optional[int] = None


class ModelResponse(BaseModel):
    """Phản hồi chuẩn từ Model Provider"""
    content: str
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    model_name: str
    provider: str
    usage: Dict[str, int] = Field(default_factory=dict)  # prompt_tokens, completion_tokens
    duration_ms: int = 0


class ModelProviderInterface(ABC):
    """Giao diện trừu tượng cho các nhà cung cấp Model (Anthropic, DeepSeek, OpenAI, Local)"""

    @abstractmethod
    async def generate(self, payload: ModelCallPayload) -> ModelResponse:
        """Thực hiện gọi LLM theo payload chuẩn hóa"""
        pass
