from __future__ import annotations

import pytest

from apps.cosa.policies.locale_policy import (
    SUPPORTED_LOCALES,
    ResolvedLocale,
    build_copilot_prompt,
    resolve_response_locale,
    validate_supported_locale,
)


def test_supported_locales_invariant():
    assert frozenset({"vi-VN", "en-US"}) == SUPPORTED_LOCALES
    assert validate_supported_locale("vi-VN") == "vi-VN"
    assert validate_supported_locale("en-US") == "en-US"

    with pytest.raises(ValueError, match="unsupported locale"):
        validate_supported_locale("fr-FR")

    with pytest.raises(ValueError, match="unsupported locale"):
        validate_supported_locale(None)


def test_resolve_response_locale_priorities():
    # 1. Turn override has highest priority
    res = resolve_response_locale(
        profile_locale="vi-VN",
        response_locale_override="en-US",
        has_principal=True,
    )
    assert res == ResolvedLocale(value="en-US", source="turn_override")

    # 2. Profile locale has second priority
    res = resolve_response_locale(
        profile_locale="en-US",
        response_locale_override=None,
        has_principal=True,
    )
    assert res == ResolvedLocale(value="en-US", source="profile")

    # 3. User principal without profile locale fails closed (cannot silently fallback)
    from apps.cosa.policies.locale_policy import ProfileLocaleUnavailable

    with pytest.raises(ProfileLocaleUnavailable):
        resolve_response_locale(
            profile_locale=None,
            response_locale_override=None,
            has_principal=True,
        )

    # 4. System task without user principal defaults to vi-VN system_fallback
    res_sys = resolve_response_locale(
        profile_locale=None,
        response_locale_override=None,
        has_principal=False,
    )
    assert res_sys == ResolvedLocale(value="vi-VN", source="system_fallback")


def test_build_copilot_prompt_en():
    prompt = build_copilot_prompt(
        locale="en-US",
        thread_id="th_123",
        intent="summarize",
        identity_verified=True,
    )
    assert "Analyze thread th_123" in prompt
    assert "identity_verified=True" in prompt


def test_build_copilot_prompt_vi():
    prompt = build_copilot_prompt(
        locale="vi-VN",
        thread_id="th_123",
        intent="faq",
        identity_verified=False,
    )
    assert "Hãy phân tích thread th_123" in prompt
    assert "identity_verified=False" in prompt


def test_build_copilot_prompt_invalid():
    with pytest.raises(ValueError):
        build_copilot_prompt(
            locale="es-ES",
            thread_id="th_123",
            intent="faq",
            identity_verified=False,
        )
