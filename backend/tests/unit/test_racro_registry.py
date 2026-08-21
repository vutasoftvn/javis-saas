import pytest
from business.marketing.racro_registry import (
    RACROMove,
    RACROAction,
    RACRO_CAPABILITY_REGISTRY,
    RACRO_EVENT_NAMES,
)


def test_racro_capability_registry_completeness():
    """Kiểm tra có đủ 15 capability chuẩn chia đều cho 5 khối RACRO."""
    assert len(RACRO_CAPABILITY_REGISTRY) == 15
    
    # 5 moves
    moves = {cap.move for cap in RACRO_CAPABILITY_REGISTRY.values()}
    assert moves == {
        RACROMove.RESEARCH,
        RACROMove.ATTRACT,
        RACROMove.CONVERT,
        RACROMove.RETAIN,
        RACROMove.ORCHESTRATE,
    }
    
    # Mỗi move có đúng 3 capabilities
    for move in RACROMove:
        caps_in_move = [cap for cap in RACRO_CAPABILITY_REGISTRY.values() if cap.move == move]
        assert len(caps_in_move) == 3, f"Move {move} phải có đúng 3 capabilities, nhưng có {len(caps_in_move)}"


def test_racro_capability_entities_and_actions():
    """Kiểm tra mọi capability đều có canonical entity và action hợp lệ."""
    for cap_id, mapping in RACRO_CAPABILITY_REGISTRY.items():
        assert mapping.capability_id == cap_id
        assert len(mapping.canonical_entities) > 0
        assert mapping.action in {
            RACROAction.KEEP,
            RACROAction.REFACTOR,
            RACROAction.MERGE,
            RACROAction.HIDE_FROM_FOUNDER,
            RACROAction.DEPRECATE,
        }
        assert len(mapping.primary_skills) > 0
        assert len(mapping.tool_adapters) > 0


def test_racro_event_names_format():
    """Kiểm tra định dạng danh mục sự kiện chuẩn."""
    assert len(RACRO_EVENT_NAMES) >= 10
    for event in RACRO_EVENT_NAMES:
        assert event.startswith("marketing.")
