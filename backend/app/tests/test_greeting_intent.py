"""G2 P0.6 / G3 §10.1: greeting messages must classify as Intent.GREETING,
not GENERAL_CHAT — and the short-circuit in cosa_cofounder_service.py must
no longer depend on a fragile "greetings" in decision.reason string match.
"""
import pytest

from app.workforce.routing.deterministic import Intent, deterministic_intent
from app.workforce.routing.router import IntentRouter


@pytest.mark.parametrize("message", [
    "chào",
    "chào!",
    "xin chào",
    "hello",
    "hi",
    "hi cosa",
    "cảm ơn",
])
def test_greeting_messages_classify_as_greeting_intent(message):
    assert deterministic_intent(message) == Intent.GREETING


def test_empty_message_is_general_chat_not_greeting():
    assert deterministic_intent("") == Intent.GENERAL_CHAT


def test_non_greeting_message_returns_none_for_downstream_heuristics():
    assert deterministic_intent("tình hình doanh thu quý này thế nào") is None


@pytest.mark.asyncio
async def test_intent_router_returns_greeting_for_chao(monkeypatch):
    decision = await IntentRouter.route_message("chào")
    assert decision.intent == Intent.GREETING
