import pytest

from apps.cosa.agents.goal_intent import detect_weekly_goal_suggestion, looks_like_weekly_goal


@pytest.mark.parametrize(
    "msg",
    [
        "Tuần này tôi muốn chốt 3 buổi phỏng vấn khách hàng và hoàn thành landing page",
        "Mục tiêu tuần tới: triển khai chiến dịch quảng cáo thử nghiệm cho kênh Facebook",
        "This week we need to close the onboarding SOP and ship the pricing page",
        "Trọng tâm tuần này là hoàn thành tài liệu định vị sản phẩm",
    ],
)
def test_positive_goal_statements(msg):
    s = detect_weekly_goal_suggestion(msg)
    assert s.should_suggest is True
    assert s.normalized_goal


@pytest.mark.parametrize(
    "msg",
    [
        "Ai đang phụ trách task này vậy?",
        "Cảm ơn bạn nhiều nhé",
        "Chào buổi sáng",
        "Báo cáo doanh thu quý trước thế nào?",
        "ok",
        "Tuần này thời tiết đẹp",  # goal cue but no commit verb -> score 2
    ],
)
def test_negative_messages(msg):
    assert looks_like_weekly_goal(msg) is False
    assert detect_weekly_goal_suggestion(msg).should_suggest is False


def test_too_short_message_is_ignored():
    assert looks_like_weekly_goal("mục tiêu tuần này") is False


def test_very_long_message_is_ignored():
    assert looks_like_weekly_goal("tuần này tôi muốn " + "x " * 300) is False


def test_normalized_goal_collapses_whitespace():
    s = detect_weekly_goal_suggestion("Tuần này  tôi   muốn\n\nchốt 3 phỏng vấn khách hàng")
    assert s.normalized_goal == "Tuần này tôi muốn chốt 3 phỏng vấn khách hàng"
