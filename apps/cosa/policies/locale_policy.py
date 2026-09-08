from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SUPPORTED_LOCALES: frozenset[str] = frozenset({"vi-VN", "en-US"})
SUPPORTED_LOCALES_TUPLE: tuple[str, ...] = ("vi-VN", "en-US")

LocaleSource = Literal["profile", "turn_override", "system_fallback"]


@dataclass(frozen=True)
class ResolvedLocale:
    value: str
    source: LocaleSource


def validate_supported_locale(locale: str | None) -> str:
    """Validates that locale belongs to the strict VI-EN supported set.

    Raises ValueError if locale is None, empty, or not in SUPPORTED_LOCALES.
    """
    if not locale or locale not in SUPPORTED_LOCALES:
        raise ValueError(
            f"unsupported locale '{locale}', expected one of {sorted(SUPPORTED_LOCALES)}"
        )
    return locale


class ProfileLocaleUnavailable(RuntimeError):
    """Raised when profile locale cannot be resolved for a user principal."""


def resolve_response_locale(
    *,
    profile_locale: str | None,
    response_locale_override: str | None,
    has_principal: bool,
) -> ResolvedLocale:
    """Resolves response locale following strict priority and provenance.

    1. response_locale_override (turn override) takes precedence if present (must be valid).
    2. profile_locale takes precedence if user principal is present and profile locale is set.
    3. If user principal is present but profile_locale is missing/failed, raise ProfileLocaleUnavailable.
       (Only background system tasks without a user principal are permitted to use system_fallback).
    4. System tasks default to 'vi-VN' with provenance 'system_fallback'.
    """
    if response_locale_override is not None:
        validated = validate_supported_locale(response_locale_override)
        return ResolvedLocale(value=validated, source="turn_override")

    if has_principal:
        if profile_locale is not None:
            validated = validate_supported_locale(profile_locale)
            return ResolvedLocale(value=validated, source="profile")
        raise ProfileLocaleUnavailable(
            "user principal requires a valid profile locale; silent fallback is forbidden"
        )

    return ResolvedLocale(value="vi-VN", source="system_fallback")


def build_copilot_prompt(
    locale: str,
    thread_id: str,
    intent: str,
    identity_verified: bool,
) -> str:
    """Builds standard localized user prompt for customer support copilot.

    Enforces that locale is strictly one of SUPPORTED_LOCALES.
    """
    validated = validate_supported_locale(locale)
    if validated == "en-US":
        return (
            f"Analyze thread {thread_id} with intent '{intent}'. "
            f"Customer identity_verified={identity_verified}. "
            "Generate a summary artifact, extract evidence, and draft a recommended response."
        )
    return (
        f"Hãy phân tích thread {thread_id} với intent '{intent}'. "
        f"Khách hàng identity_verified={identity_verified}. "
        "Tạo artifact tóm tắt, trích xuất căn cứ, và bản nháp phản hồi đề xuất."
    )
