import os
from typing import Dict, Any, Optional

from workforce.adapters.base import BaseRuntimeAdapter
from workforce.adapters.claude_adapter import ClaudeCodeAdapter
from workforce.adapters.gemini_adapter import GeminiAdapter
from workforce.adapters.deepseek_adapter import DeepSeekAdapter
from workforce.adapters.http_generic_adapter import GenericHttpAdapter


class RuntimeAdapterFactory:
    """Factory tự động phân giải Provider & Khởi tạo Runtime Adapter phù hợp."""

    # Map model profile -> default provider & model
    PROFILE_MAPPINGS = {
        "fast": {"provider": "gemini", "model": "gemini-2.0-flash"},
        "reasoning": {"provider": "claude", "model": "claude-3-5-sonnet-20241022"},
        "coding": {"provider": "claude", "model": "claude-3-5-sonnet-20241022"},
        "deep_reasoning": {"provider": "deepseek", "model": "deepseek-reasoner"},
        "local": {"provider": "http", "model": "llama3.2:latest"},
    }

    @classmethod
    def get_adapter(
        cls,
        provider: Optional[str] = None,
        model_profile: Optional[str] = None,
        custom_config: Optional[Dict[str, Any]] = None,
    ) -> BaseRuntimeAdapter:
        config = custom_config or {}
        
        # Nếu chỉ định model_profile mà không có provider, dùng profile mapping
        if not provider and model_profile:
            mapping = cls.PROFILE_MAPPINGS.get(model_profile, cls.PROFILE_MAPPINGS["reasoning"])
            provider = mapping["provider"]

        provider = (provider or "claude").lower()

        if provider in ["claude", "anthropic", "claudecode"]:
            api_key = config.get("api_key") or os.getenv("ANTHROPIC_API_KEY")
            base_url = config.get("base_url") or os.getenv("ANTHROPIC_BASE_URL")
            return ClaudeCodeAdapter(api_key=api_key, base_url=base_url, config=config)

        elif provider in ["gemini", "google", "adk"]:
            api_key = config.get("api_key") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            base_url = config.get("base_url")
            return GeminiAdapter(api_key=api_key, base_url=base_url, config=config)

        elif provider in ["deepseek"]:
            api_key = config.get("api_key") or os.getenv("DEEPSEEK_API_KEY")
            base_url = config.get("base_url") or os.getenv("DEEPSEEK_BASE_URL")
            return DeepSeekAdapter(api_key=api_key, base_url=base_url, config=config)

        else:
            api_key = config.get("api_key") or os.getenv("LOCAL_LLM_API_KEY")
            base_url = config.get("base_url") or os.getenv("LOCAL_LLM_BASE_URL")
            return GenericHttpAdapter(api_key=api_key, base_url=base_url, config=config)

    @classmethod
    def get_fallback_chain(cls, primary_provider: str) -> list:
        """Trả về danh sách fallback provider theo thứ tự ưu tiên."""
        primary = primary_provider.lower()
        if primary in ["claude", "anthropic", "claudecode"]:
            return ["deepseek", "gemini", "http"]
        elif primary in ["deepseek"]:
            return ["claude", "gemini", "http"]
        elif primary in ["gemini", "google", "adk"]:
            return ["claude", "deepseek", "http"]
        else:
            return ["claude", "deepseek", "gemini"]

    @classmethod
    async def resolve_adapter_with_fallback(
        cls,
        primary_provider: Optional[str] = None,
        model_profile: Optional[str] = None,
        custom_config: Optional[Dict[str, Any]] = None,
    ) -> BaseRuntimeAdapter:
        """Khởi tạo adapter với cơ chế kiểm tra capability và tự động fallback nếu cần."""
        adapter = cls.get_adapter(provider=primary_provider, model_profile=model_profile, custom_config=custom_config)
        cap = await adapter.check_capability()
        
        # Nếu adapter chính ok (hoặc mock ok), trả về luôn
        if cap.get("installed", False):
            return adapter

        # Ngược lại thử fallback chain
        fallback_providers = cls.get_fallback_chain(primary_provider or "claude")
        for fb_prov in fallback_providers:
            fb_adapter = cls.get_adapter(provider=fb_prov, custom_config=custom_config)
            fb_cap = await fb_adapter.check_capability()
            if fb_cap.get("installed", False):
                return fb_adapter

        return adapter

    @classmethod
    def resolve_model_name(cls, model_profile: str, custom_model: Optional[str] = None) -> str:
        if custom_model:
            return custom_model
        mapping = cls.PROFILE_MAPPINGS.get(model_profile, cls.PROFILE_MAPPINGS["reasoning"])
        return mapping["model"]
