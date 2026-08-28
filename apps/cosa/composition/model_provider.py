from __future__ import annotations

import os
from typing import Any

__all__ = ["build_deepseek_model"]


def build_deepseek_model() -> Any:
    """Dựng `agents.extensions.models.litellm_model.LitellmModel` trỏ tới
    DeepSeek THẬT từ `DEEPSEEK_API_KEY`/`DEEPSEEK_BASE_URL`/
    `DEEPSEEK_DEFAULT_MODEL` — đọc env một chỗ duy nhất tại composition root
    (COSA_PRODUCTION_RUNTIME_CLOSURE_ADJUSTMENT_2026-08-25.md §5.2), không
    rải rác trong kernel.

    Raise RuntimeError rõ ràng nếu thiếu DEEPSEEK_API_KEY — production
    không được silently chạy với model provider chưa cấu hình (§3.2/§5.1).
    """
    if os.environ.get("COSA_MODEL_PROVIDER", "").lower() == "fake":
        from agent_testkit.fake_sdk_model import FakeSDKModel

        return FakeSDKModel()

    # Check environment BEFORE importing LitellmModel, which may load API keys
    # from system config (litellm behavior). We must validate the intentional
    # environment configuration before triggering any external loads.
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError(
            "build_deepseek_model() requires DEEPSEEK_API_KEY to be set — "
            "production must not silently run with an unconfigured model "
            "provider. For tests, pass model=<FakeSDKModel instance> "
            "explicitly to build_cosa_agent_plane() or set COSA_MODEL_PROVIDER=fake."
        )

    # Now safe to import LitellmModel after validation
    from agents.extensions.models.litellm_model import LitellmModel

    base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    default_model = os.environ.get("DEEPSEEK_DEFAULT_MODEL", "deepseek-chat")

    return LitellmModel(
        model=f"deepseek/{default_model}",
        base_url=base_url,
        api_key=api_key,
    )
