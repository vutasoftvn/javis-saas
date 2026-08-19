"""Danh sách model được phép chọn, kèm capability khai báo tĩnh (không đoán theo tên
model). Dùng để lọc model picker ở frontend và validate lựa chọn khi tạo chat session -
một provider/model không có trong danh sách này không được phép dùng, kể cả khi client
tự gửi thẳng tên model lên."""

import logging
import os
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelInfo:
    provider: str
    model: str
    label: str
    supports_tools: bool = False
    supports_vision: bool = False
    context_window: int | None = None


MODELS: list[ModelInfo] = [
    # Kira AI Gateway Models (Default Vietnam AI Gateway)
    ModelInfo("kira_ai", "deepseek-v4-pro-free", "DeepSeek V4 Pro Free (Kira AI)", supports_tools=True, context_window=128_000),
    ModelInfo("kira_ai", "deepseek-chat", "DeepSeek V3 (Kira AI)", supports_tools=True, context_window=64_000),
    ModelInfo("kira_ai", "deepseek-reasoner", "DeepSeek R1 (Kira AI)", context_window=64_000),
    ModelInfo("kira_ai", "claude-3-7-sonnet", "Claude 3.7 Sonnet (Kira AI)", supports_vision=True, supports_tools=True, context_window=200_000),
    ModelInfo("kira_ai", "claude-3-5-sonnet", "Claude 3.5 Sonnet (Kira AI)", supports_vision=True, supports_tools=True, context_window=200_000),
    ModelInfo("kira_ai", "claude-3-5-haiku", "Claude 3.5 Haiku (Kira AI)", context_window=200_000),
    ModelInfo("kira_ai", "gpt-4o", "GPT-4o (Kira AI)", supports_vision=True, supports_tools=True, context_window=128_000),
    ModelInfo("kira_ai", "gpt-4o-mini", "GPT-4o mini (Kira AI)", supports_vision=True, supports_tools=True, context_window=128_000),
    ModelInfo("kira_ai", "gemini-2.0-flash", "Gemini 2.0 Flash (Kira AI)", supports_vision=True, supports_tools=True, context_window=1_000_000),
    ModelInfo("deepseek", "deepseek-chat", "DeepSeek Chat", supports_tools=True, context_window=64_000),
    ModelInfo("deepseek", "deepseek-reasoner", "DeepSeek Reasoner", context_window=64_000),
    ModelInfo("openai", "gpt-4o", "GPT-4o", supports_vision=True, supports_tools=True, context_window=128_000),
    ModelInfo("openai", "gpt-4o-mini", "GPT-4o mini", supports_vision=True, supports_tools=True, context_window=128_000),
    ModelInfo(
        "anthropic",
        "claude-3-5-sonnet-latest",
        "Claude 3.5 Sonnet",
        supports_vision=True,
        context_window=200_000,
    ),
    ModelInfo(
        "anthropic",
        "claude-3-5-haiku-latest",
        "Claude 3.5 Haiku",
        context_window=200_000,
    ),
    ModelInfo(
        "gemini",
        "gemini-1.5-pro",
        "Gemini 1.5 Pro",
        supports_vision=True,
        context_window=1_000_000,
    ),
    ModelInfo(
        "gemini",
        "gemini-1.5-flash",
        "Gemini 1.5 Flash",
        supports_vision=True,
        context_window=1_000_000,
    ),
    # supports_tools ở đây có nghĩa: "đường đi tới model NÀY gọi được tool trong
    # COSA OS". Nhóm openrouter, openai, deepseek, apiai_vn, kira_ai dùng chung OpenAICompatibleClient
    # (đã nối tool-calling và tự động gom tool calls).
    ModelInfo("openrouter", "openrouter/auto", "OpenRouter Auto", supports_tools=True),
    ModelInfo("openrouter", "deepseek/deepseek-chat", "DeepSeek Chat (OpenRouter)", supports_tools=True, context_window=64_000),
    ModelInfo("openrouter", "anthropic/claude-sonnet-4.5", "Claude Sonnet 4.5 (OpenRouter)", supports_tools=True, supports_vision=True, context_window=200_000),
    ModelInfo("openrouter", "anthropic/claude-haiku-4.5", "Claude Haiku 4.5 (OpenRouter)", supports_tools=True, context_window=200_000),
    ModelInfo("openrouter", "openai/gpt-4o", "GPT-4o (OpenRouter)", supports_tools=True, supports_vision=True, context_window=128_000),
    ModelInfo("openrouter", "openai/gpt-4o-mini", "GPT-4o mini (OpenRouter)", supports_tools=True, supports_vision=True, context_window=128_000),
    ModelInfo("openrouter", "google/gemini-2.5-flash", "Gemini 2.5 Flash (OpenRouter)", supports_tools=True, supports_vision=True, context_window=1_000_000),
    ModelInfo("apiai_vn", "apiai-fast", "ApiAI Fast (Vietnam)", supports_tools=True, context_window=64_000),
    ModelInfo("apiai_vn", "apiai-pro", "ApiAI Pro (Vietnam)", supports_tools=True, supports_vision=True, context_window=128_000),
]

_PROVIDER_KEY_ENV = {
    "kira_ai": "KIRAAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "apiai_vn": "APIAIVN_API_KEY",
}


def _workspace_secret_configured(workspace_id: Optional[int] = None, provider: str = "openrouter") -> bool:
    """Return whether a secret is available for this workspace and provider."""
    try:
        from app.db.session import SessionLocal
        from app.integrations.channels.models import WorkspaceSecret

        db = SessionLocal()
        try:
            target_keys = ["openrouter"] if provider == "openrouter" else ["kira_ai", "kiraai"]
            query = db.query(WorkspaceSecret).filter(WorkspaceSecret.key.in_(target_keys))
            if workspace_id:
                query = query.filter(WorkspaceSecret.workspace_id == workspace_id)
            ws_secret = query.first()
            return bool(ws_secret and ws_secret.encrypted_value)
        finally:
            db.close()
    except Exception:
        return False


def is_provider_configured(provider: str, workspace_id: Optional[int] = None) -> bool:
    """Provider đã có khoá để gọi thật hay chưa."""
    key_env = _PROVIDER_KEY_ENV.get(provider)
    if key_env and (os.environ.get(key_env, "").strip() or (provider == "kira_ai" and os.environ.get("KIRA_API_KEY", "").strip())):
        return True
    if bool(os.environ.get(f"PROVIDER_CONFIGURED_{provider.upper()}", "").strip()):
        return True
    if provider in {"openrouter", "kira_ai"}:
        try:
            return _workspace_secret_configured(workspace_id, provider=provider)
        except TypeError:
            return _workspace_secret_configured(workspace_id)
    return False




def is_selectable(provider: str, model: str) -> bool:
    """Cặp provider/model có được phép gắn vào một chat session mới hay không."""
    return is_known(provider, model) and is_provider_configured(provider)


_FALLBACK_PROVIDER = "kira_ai"
_FALLBACK_MODEL = "deepseek-v4-pro-free"



def list_models() -> list[ModelInfo]:
    return MODELS


def get_model(provider: str, model: str) -> ModelInfo | None:
    for entry in MODELS:
        if entry.provider == provider and entry.model == model:
            return entry
    return None


def is_known(provider: str, model: str) -> bool:
    return get_model(provider, model) is not None


def _first_configured() -> tuple[str, str] | None:
    for entry in MODELS:
        if is_provider_configured(entry.provider):
            return entry.provider, entry.model
    return None


def _resolve_defaults() -> tuple[str, str]:
    provider = os.environ.get("CHAT_DEFAULT_PROVIDER", _FALLBACK_PROVIDER)
    model = os.environ.get("CHAT_DEFAULT_MODEL", _FALLBACK_MODEL)
    if not is_known(provider, model):
        logger.warning(
            "CHAT_DEFAULT_PROVIDER/CHAT_DEFAULT_MODEL=%s/%s không có trong model registry",
            provider, model,
        )
    elif not is_provider_configured(provider):
        # Mặc định trỏ vào provider chưa có khoá là hỏng cả sản phẩm chứ không chỉ một
        # lượt: session mới nào cũng tạo với cặp này rồi chết ở câu đầu tiên.
        logger.warning(
            "CHAT_DEFAULT_PROVIDER=%s chưa có API key nên không dùng làm mặc định được",
            provider,
        )
    else:
        return provider, model

    replacement = _first_configured()
    if replacement:
        logger.warning("Dùng %s/%s làm mặc định thay thế", *replacement)
        return replacement
    logger.warning(
        "Không provider nào có API key, giữ %s/%s - chat sẽ báo lỗi cho tới khi cấu hình khoá",
        _FALLBACK_PROVIDER, _FALLBACK_MODEL,
    )
    return _FALLBACK_PROVIDER, _FALLBACK_MODEL


DEFAULT_PROVIDER, DEFAULT_MODEL = _resolve_defaults()
