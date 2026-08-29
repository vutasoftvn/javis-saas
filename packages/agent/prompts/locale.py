from __future__ import annotations

__all__ = ["DEFAULT_LOCALE", "FALLBACK_LOCALE", "render_locale_policy"]

# Blueprint V2 §68.3, §67.2 — canonical English instruction, locale-aware output.
DEFAULT_LOCALE = "vi-VN"
FALLBACK_LOCALE = "en-US"

_LOCALE_POLICY_TEMPLATE = (
    "The user's preferred locale is {locale}.\n"
    "Respond in that locale unless the user explicitly requests another language.\n"
    "Preserve official product names, code identifiers, API names, schema fields,\n"
    "and technical terms when translation would reduce precision."
)


def render_locale_policy(locale: str = DEFAULT_LOCALE) -> str:
    """Render canonical English locale directive theo Blueprint V2 §68.3 — chính
    prompt này luôn tiếng Anh (canonical instruction language), chỉ `{locale}`
    thay đổi để điều khiển ngôn ngữ output cho user."""
    return _LOCALE_POLICY_TEMPLATE.format(locale=locale or DEFAULT_LOCALE)
