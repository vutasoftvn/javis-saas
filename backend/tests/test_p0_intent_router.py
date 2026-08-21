"""Pytest suite for Phase P0: Conversation Intent Router & Fast-Path Classifier."""

import pytest
from workforce.chat.conversation_gate import resolve, GateIntent


def test_greeting_fast_path():
    """Greetings must resolve immediately without requiring tools or project lookups."""
    greeting_samples = [
        "chào bạn",
        "xin chào",
        "hello",
        "hi",
        "hey cosa",
        "bạn là ai",
        "cảm ơn bạn",
        "tạm biệt",
        "bạn khỏe không",
    ]
    for text in greeting_samples:
        decision = resolve(text)
        assert decision.intent == GateIntent.SOCIAL_CHAT, f"Failed on '{text}': got {decision.intent}"
        assert decision.needs_tools is False, f"'{text}' should not need tools"
        assert decision.needs_project is False, f"'{text}' should not need project lookup"
        assert len(decision.allowed_namespaces) == 0, f"'{text}' should have 0 namespaces"


def test_founder_brief_routing():
    """Founder status queries must route to FOUNDER_BRIEF with appropriate namespaces."""
    brief_samples = [
        "hôm nay thế nào",
        "hôm nay có gì",
        "tình hình công ty",
        "báo cáo hôm nay",
        "founder brief",
        "daily brief",
        "báo cáo nhanh",
    ]
    for text in brief_samples:
        decision = resolve(text)
        assert decision.intent == GateIntent.FOUNDER_BRIEF, f"Failed on '{text}': got {decision.intent}"
        assert decision.needs_tools is True
        assert "runtime" in decision.allowed_namespaces
        assert "tasks" in decision.allowed_namespaces


def test_knowledge_search_routing():
    """Vault and policy questions must route to KNOWLEDGE_SEARCH with vault namespace."""
    knowledge_samples = [
        "tìm trong vault tài liệu quy trình",
        "chính sách làm việc từ xa",
        "tra cứu sop bán hàng",
    ]
    for text in knowledge_samples:
        decision = resolve(text)
        assert decision.intent == GateIntent.KNOWLEDGE_SEARCH, f"Failed on '{text}': got {decision.intent}"
        assert "vault" in decision.allowed_namespaces


def test_mission_command_routing():
    """Goal/Mission commands must route to MISSION_COMMAND with sales/marketing namespaces."""
    mission_samples = [
        "tìm 20 khách hàng cho sản phẩm mới",
        "lên chiến dịch marketing tháng 8",
        "lập landing page giới thiệu sản phẩm",
    ]
    for text in mission_samples:
        decision = resolve(text)
        assert decision.intent == GateIntent.MISSION_COMMAND, f"Failed on '{text}': got {decision.intent}"
        assert "sales" in decision.allowed_namespaces or "marketing" in decision.allowed_namespaces
