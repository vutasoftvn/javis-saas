import workforce.chat.model_registry as model_registry
from workforce.chat.model_registry import (
    DEFAULT_MODEL,
    DEFAULT_PROVIDER,
    _PROVIDER_KEY_ENV,
    _resolve_defaults,
    is_provider_configured,
    is_known,
    is_selectable,
    list_models,
)


def _forget_every_provider_key(monkeypatch):
    """Xoá mọi dấu vết khoá thật của máy chạy test - nếu không, kết quả _resolve_defaults()
    đổi theo việc máy đó có .env nào."""
    for provider, key_env in _PROVIDER_KEY_ENV.items():
        monkeypatch.delenv(key_env, raising=False)
        monkeypatch.delenv(f"PROVIDER_CONFIGURED_{provider.upper()}", raising=False)


def test_default_provider_and_model_are_registered():
    """create_chat_session validate cặp mặc định bằng is_known() rồi mới tạo session -
    mặc định không nằm trong registry nghĩa là không tạo được cuộc chat nào."""
    assert is_known(DEFAULT_PROVIDER, DEFAULT_MODEL)


def test_unknown_provider_model_pair_is_rejected():
    assert is_known("openai", "does-not-exist") is False
    assert is_known("does-not-exist", "gpt-4o") is False


def test_list_models_has_no_duplicate_provider_model_pairs():
    pairs = [(m.provider, m.model) for m in list_models()]
    assert len(pairs) == len(set(pairs))


def test_env_can_point_defaults_at_another_provider(monkeypatch):
    _forget_every_provider_key(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-abc")
    monkeypatch.setenv("CHAT_DEFAULT_PROVIDER", "openrouter")
    monkeypatch.setenv("CHAT_DEFAULT_MODEL", "deepseek/deepseek-chat")

    assert _resolve_defaults() == ("openrouter", "deepseek/deepseek-chat")


def test_unknown_env_defaults_fall_back_instead_of_breaking_chat(monkeypatch):
    """Gõ sai tên model trong env không được làm chết API - lùi về mặc định dựng sẵn."""
    _forget_every_provider_key(monkeypatch)
    monkeypatch.setattr(model_registry, "_workspace_secret_configured", lambda _workspace_id: False)
    monkeypatch.setenv("CHAT_DEFAULT_PROVIDER", "openrouter")
    monkeypatch.setenv("CHAT_DEFAULT_MODEL", "khong-ton-tai")

    assert _resolve_defaults() == ("kira_ai", "deepseek-v4-pro-free")



def test_defaults_move_to_a_provider_that_actually_has_a_key(monkeypatch):
    """Mặc định trỏ vào provider chưa có khoá thì MỌI đoạn chat mới đều hỏng ngay từ câu
    đầu tiên. Có provider khác dùng được thì lấy provider đó, đừng tạo session chết."""
    _forget_every_provider_key(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-abc")
    monkeypatch.setenv("CHAT_DEFAULT_PROVIDER", "deepseek")
    monkeypatch.setenv("CHAT_DEFAULT_MODEL", "deepseek-chat")

    provider, model = _resolve_defaults()

    assert provider == "openrouter"
    assert is_known(provider, model)


def test_is_selectable_requires_both_registry_entry_and_api_key(monkeypatch):
    _forget_every_provider_key(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-abc")

    assert is_selectable("openrouter", "deepseek/deepseek-chat") is True
    # Có trong registry nhưng chưa có khoá - không được phép gắn vào session mới.
    assert is_selectable("deepseek", "deepseek-chat") is False
    assert is_selectable("openrouter", "khong-ton-tai") is False


def test_provider_is_configured_when_its_own_key_is_present(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-abc")

    assert is_provider_configured("openrouter") is True


def test_provider_is_not_configured_when_key_is_blank(monkeypatch):
    """Khoá để trống (hoặc chỉ có khoảng trắng) phải tính là chưa cấu hình - chọn phải nó
    thì mọi câu chat trong session đều hỏng với provider_not_configured."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "   ")
    monkeypatch.delenv("PROVIDER_CONFIGURED_DEEPSEEK", raising=False)

    assert is_provider_configured("deepseek") is False


def test_flag_marks_provider_configured_without_holding_the_key(monkeypatch):
    """brain-api không giữ khoá nào; docker-compose truyền cho nó cờ suy ra từ khoá."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("PROVIDER_CONFIGURED_ANTHROPIC", "1")

    assert is_provider_configured("anthropic") is True
