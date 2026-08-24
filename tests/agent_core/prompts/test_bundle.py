from __future__ import annotations

from agent_core.prompts.bundle import PLATFORM_POLICY, PromptBundle
from agent_core.prompts.locale import DEFAULT_LOCALE, render_locale_policy


def test_prompt_bundle_renders_platform_policy_instructions_and_locale_in_order():
    bundle = PromptBundle(agent_instructions="Bạn là trợ lý vận hành.", locale="en-US")
    rendered = bundle.render()

    assert rendered.startswith(PLATFORM_POLICY)
    assert "Bạn là trợ lý vận hành." in rendered
    assert "The user's preferred locale is en-US." in rendered
    # Thứ tự: platform policy -> agent instructions -> locale policy
    assert rendered.index(PLATFORM_POLICY) < rendered.index("Bạn là trợ lý vận hành.")
    assert rendered.index("Bạn là trợ lý vận hành.") < rendered.index("preferred locale is en-US")


def test_prompt_bundle_defaults_to_vi_vn_locale():
    bundle = PromptBundle(agent_instructions="x")
    assert bundle.locale == DEFAULT_LOCALE
    assert "preferred locale is vi-VN" in bundle.render()


def test_render_locale_policy_falls_back_to_default_on_empty_string():
    assert "vi-VN" in render_locale_policy("")
    assert "vi-VN" in render_locale_policy(None)  # type: ignore[arg-type]
