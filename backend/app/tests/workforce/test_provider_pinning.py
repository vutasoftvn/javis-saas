import pytest

# Giả lập configuration của hệ thống
PINNED_PROVIDERS = {
    "deepseek": "1.2",
    "codex": "2.4",
    "claude": "2024-02",
    "n8n": "1.0"
}

def validate_provider_config(provider_name: str, version: str):
    if provider_name not in PINNED_PROVIDERS:
        raise ValueError(f"Unknown provider {provider_name}")
    if PINNED_PROVIDERS[provider_name] != version:
        raise ValueError(f"Provider {provider_name} version {version} is not pinned. Expected {PINNED_PROVIDERS[provider_name]}")

def test_pinned_provider_startup():
    """Hệ thống phải chấp nhận cấu hình được ghim."""
    validate_provider_config("deepseek", "1.2")
    validate_provider_config("codex", "2.4")

def test_unpinned_provider_startup_fails():
    """Hệ thống phải từ chối cấu hình không được ghim (unpinned)."""
    with pytest.raises(ValueError, match="is not pinned"):
        validate_provider_config("deepseek", "1.3")
    
    with pytest.raises(ValueError, match="Unknown provider"):
        validate_provider_config("unknown_ai", "1.0")
