"""Dịch lỗi run thô (chuỗi từ LiteLLM/SDK/tool) sang mã + thông báo cho người
dùng theo locale. Đây là bộ dịch Ở BIÊN (chỉ dùng để hiển thị) — không dùng để
điều khiển workflow (xem packages/agent/contracts/errors.py). Chuỗi thô luôn
ở lại log server, không bao giờ vào `user_message`."""

from __future__ import annotations

from typing import NamedTuple

__all__ = ["ClassifiedError", "classify_run_error"]


class ClassifiedError(NamedTuple):
    code: str
    user_message: str


# (code, các mẫu nhận diện — so khớp lowercase, theo thứ tự ưu tiên)
_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "provider_insufficient_balance",
        ("insufficient balance", "insufficient_quota", "quota exceeded"),
    ),
    ("provider_auth", ("authenticationerror", "invalid api key", "incorrect api key", "401")),
    ("provider_rate_limited", ("ratelimiterror", "rate limit", "429", "too many requests")),
    (
        "provider_unavailable",
        (
            "serviceunavailable",
            "timeout",
            "timed out",
            "503",
            "502",
            "connection error",
            "apiconnectionerror",
        ),
    ),
    ("tool_input_invalid", ("error running tool", "unknown variables")),
    ("agent_max_turns", ("max turns",)),
)

_MESSAGES: dict[str, dict[str, str]] = {
    "vi": {
        "provider_insufficient_balance": "Dịch vụ AI tạm thời không khả dụng do nhà cung cấp model đã hết hạn mức. Vui lòng liên hệ quản trị viên để nạp thêm hoặc đổi model.",
        "provider_auth": "Không xác thực được với nhà cung cấp model. Vui lòng kiểm tra API key trong Cài đặt → Model Providers.",
        "provider_rate_limited": "Nhà cung cấp model đang giới hạn tốc độ. Vui lòng thử lại sau ít phút.",
        "provider_unavailable": "Nhà cung cấp model tạm thời không phản hồi. Vui lòng thử lại sau.",
        "tool_input_invalid": "Agent gọi công cụ với tham số không hợp lệ. Vui lòng thử lại.",
        "agent_max_turns": "Agent đã vượt quá số bước xử lý cho phép. Vui lòng chia nhỏ yêu cầu và thử lại.",
        "unknown": "Đã xảy ra lỗi khi xử lý yêu cầu. Vui lòng thử lại hoặc liên hệ hỗ trợ.",
    },
    "en": {
        "provider_insufficient_balance": "The AI service is temporarily unavailable because the model provider quota is exhausted. Please contact an administrator to top up or switch model.",
        "provider_auth": "Could not authenticate with the model provider. Please check the API key in Settings → Model Providers.",
        "provider_rate_limited": "The model provider is rate limiting requests. Please try again in a few minutes.",
        "provider_unavailable": "The model provider is temporarily not responding. Please try again later.",
        "tool_input_invalid": "The agent called a tool with invalid parameters. Please try again.",
        "agent_max_turns": "The agent exceeded the allowed number of steps. Please split the request and try again.",
        "unknown": "An error occurred while processing your request. Please try again or contact support.",
    },
}


def classify_run_error(message: str, locale: str = "vi-VN") -> ClassifiedError:
    lowered = (message or "").lower()
    code = "unknown"
    for rule_code, patterns in _RULES:
        if any(p in lowered for p in patterns):
            code = rule_code
            break
    lang = "en" if (locale or "").lower().startswith("en") else "vi"
    return ClassifiedError(code, _MESSAGES[lang][code])
