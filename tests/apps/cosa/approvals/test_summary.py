from __future__ import annotations

from apps.cosa.approvals.summary import capability_id_for_tool, summarize_action
from apps.cosa.capabilities.access_matrix import CHAT_T2_CAPABILITIES


def test_key_result_checkin_vi_uses_names_not_ids() -> None:
    s = summarize_action(
        "okr.key_result.checkin",
        {"key_result_id": "kr1", "value": 12},
        "vi-VN",
        project_name="COSA",
    )
    assert s["title"] == "Ghi nhận tiến độ Key Result cho COSA"
    assert "12" in s["detail"]
    assert "kr1" not in s["title"] + s["detail"]


def test_key_result_create_en() -> None:
    s = summarize_action(
        "okr.key_result.create",
        {"objective_id": "o-123", "title": "MRR", "target_value": 10},
        "en-US",
        project_name=None,
    )
    assert s["title"] == "Create a Key Result for this project"
    assert s["detail"] == "MRR — target 10"
    assert "o-123" not in s["detail"]


def test_enum_values_are_translated_not_raw() -> None:
    s = summarize_action(
        "operations.task.advance", {"task_id": "t9", "to_status": "done"}, "vi", project_name="P"
    )
    assert s["detail"] == "Trạng thái mới: hoàn thành"
    g = summarize_action(
        "startup_os.goal.create", {"title": "Q4", "goal_type": "tactical"}, "vi", project_name="P"
    )
    assert "tactical" not in g["detail"] and "chiến thuật" in g["detail"]


def test_every_t2_capability_has_a_dedicated_template_in_both_languages() -> None:
    for cap in CHAT_T2_CAPABILITIES:
        for locale in ("vi-VN", "en-US"):
            s = summarize_action(cap, {}, locale, project_name="X")
            assert s["title"] and "approval" not in s["title"].lower(), cap
            assert "duyệt" not in s["title"], cap


def test_unknown_capability_falls_back_without_technical_name() -> None:
    s = summarize_action("x.secret.cap", {"a": 1}, "vi", project_name=None)
    assert "x.secret.cap" not in s["title"] and s["detail"] == ""


def test_tool_name_maps_back_to_capability_id() -> None:
    ids = ["okr.key_result.create", "operations.task.list"]
    assert capability_id_for_tool("okr_key_result_create", ids) == "okr.key_result.create"
    assert capability_id_for_tool("okr.key_result.create", ids) == "okr.key_result.create"
    assert capability_id_for_tool("nope", ids) is None


def test_founder_notify_send_vi_shows_channel_label_and_short_content() -> None:
    s = summarize_action(
        "founder.notify.send",
        {"content": "Tóm tắt 3 email chưa đọc", "channel_kind": "telegram"},
        "vi-VN",
        project_name="COSA",
    )
    assert s["title"] == "Gửi thông báo vào kênh Telegram của bạn"
    assert s["detail"] == "Tóm tắt 3 email chưa đọc"


def test_founder_notify_send_en_without_kind_uses_verified_label() -> None:
    s = summarize_action("founder.notify.send", {"content": "Hi"}, "en-US", project_name=None)
    assert s["title"] == "Send a notification to your verified channel"
    assert s["detail"] == "Hi"
    vi = summarize_action("founder.notify.send", {"content": "Chào"}, "vi", project_name=None)
    assert vi["title"] == "Gửi thông báo vào kênh đã xác minh của bạn"


def test_founder_notify_send_truncates_long_content_and_never_shows_raw_kind() -> None:
    long = "Dòng một\n\n" + "x" * 300
    s = summarize_action(
        "founder.notify.send",
        {"content": long, "channel_kind": "telegram"},
        "vi",
        project_name=None,
    )
    assert s["detail"].endswith("…")
    assert len(s["detail"]) <= 121
    assert s["detail"].startswith("Dòng một x")
    assert "telegram" not in s["title"]  # nhãn đã dịch, không phải enum thô
    short = summarize_action("founder.notify.send", {"content": "y" * 120}, "vi", project_name=None)
    assert short["detail"] == "y" * 120

def test_key_result_update_summary() -> None:
    s = summarize_action(
        "okr.key_result.update",
        {"key_result_id": "kr1", "status": "active"},
        "vi-VN",
        project_name="COSA",
    )
    assert s["title"] == "Cập nhật Key Result cho COSA"
    assert s["detail"] == "Trạng thái mới: đang thực hiện"
    assert "kr1" not in s["title"] + s["detail"]
    assert "active" not in s["detail"]

