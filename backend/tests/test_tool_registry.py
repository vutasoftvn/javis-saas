from unittest.mock import MagicMock, patch

from core.tool_registry import (
    ToolSpec,
    available_tools,
    chat_tools,
    get_registered_tools,
    get_tool_by_flat_name,
    register,
)


def test_registry_keeps_namespace_and_name_unique():
    @register("test", "sample")
    def sample():
        return "ok"

    assert get_registered_tools()["test.sample"].callable is sample


def test_available_tools_filters_disabled_flag():
    @register("test", "gated", flag_key="test_flag")
    def gated():
        return "hidden"

    with patch("cosa_core.tools.registry.is_enabled", return_value=False):
        names = {spec.qualified_name for spec in available_tools(MagicMock(), 1)}

    assert "test.gated" not in names


def test_flat_name_drops_the_dot_provider_rejects():
    spec = ToolSpec(namespace="company", name="ceo_brief", callable=lambda: None)
    assert spec.flat_name == "company_ceo_brief"


def test_openai_spec_carries_description_and_parameters():
    params = {"type": "object", "properties": {"limit": {"type": "integer"}}, "required": []}
    spec = ToolSpec(
        namespace="company",
        name="ceo_brief",
        callable=lambda: None,
        chat_schema={"description": "Tổng quan công ty", "parameters": params},
    )

    assert spec.to_openai_spec() == {
        "type": "function",
        "function": {
            "name": "company_ceo_brief",
            "description": "Tổng quan công ty",
            "parameters": params,
        },
    }


def test_openai_spec_defaults_to_an_empty_object_when_the_tool_takes_no_argument():
    """Bỏ trống "parameters" thì một số provider từ chối cả request - luôn phải có object
    rỗng hợp lệ chứ không phải None."""
    spec = ToolSpec(
        namespace="cycle", name="status", callable=lambda: None, chat_schema={"description": "x"}
    )
    assert spec.to_openai_spec()["function"]["parameters"] == {
        "type": "object", "properties": {}, "required": []
    }


def test_chat_tools_hides_tools_without_a_chat_schema():
    """Tool ghi/hành động cố tình không có chat_schema: model chat không được nhìn thấy
    chúng, chứ không phải nhìn thấy rồi bị dặn đừng gọi."""
    @register("test", "write_action")
    def write_action():
        return "danger"

    @register("test", "readable", chat_schema={"description": "đọc được"})
    def readable():
        return "ok"

    with patch("cosa_core.tools.registry.is_enabled", return_value=True):
        names = {spec.qualified_name for spec in chat_tools(MagicMock(), 1)}

    assert "test.readable" in names
    assert "test.write_action" not in names


def test_chat_tools_hides_mutating_tools_even_with_a_chat_schema():
    """company_tools.py gọi execute_tool_spec thẳng, không qua GovernanceKernel - nên
    mutating=True phải chặn ở đây bằng cấu trúc, không được phép chỉ dựa vào việc ai đó
    nhớ bỏ trống chat_schema."""
    @register(
        "test", "mutating_but_schema", mutating=True,
        chat_schema={"description": "lỡ khai schema"},
    )
    def mutating_but_schema():
        return "danger"

    with patch("cosa_core.tools.registry.is_enabled", return_value=True):
        names = {spec.qualified_name for spec in chat_tools(MagicMock(), 1)}

    assert "test.mutating_but_schema" not in names


def test_chat_tools_still_respects_the_feature_flag():
    @register("test", "gated_chat", flag_key="test_flag", chat_schema={"description": "x"})
    def gated_chat():
        return "hidden"

    with patch("cosa_core.tools.registry.is_enabled", return_value=False):
        names = {spec.qualified_name for spec in chat_tools(MagicMock(), 1)}

    assert "test.gated_chat" not in names


def test_get_tool_by_flat_name_round_trips():
    @register("test", "round_trip", chat_schema={"description": "x"})
    def round_trip():
        return "ok"

    spec = get_tool_by_flat_name("test_round_trip")
    assert spec is not None and spec.callable is round_trip


def test_get_tool_by_flat_name_returns_none_for_a_hallucinated_name():
    assert get_tool_by_flat_name("company_no_such_tool") is None


# Tool cố tình KHÔNG cấp cho chat text, kèm lý do. Chat đọc email và tài liệu do người
# ngoài gửi tới, nên mọi tool thay đổi trạng thái hệ thống đều chỉ có ở voice - nơi người
# dùng đang nói trực tiếp và nghe được từng hành động. Chat muốn hành động thì đi qua
# chat.propose_action: tạo mục chờ người thật bấm duyệt.
CHAT_EXCLUDED_TOOLS = {
    "approval.approve": "duyệt workflow step - hành động hệ quả",
    "approval.reject": "từ chối workflow step - hành động hệ quả",
    "tech.request_developer_job": "chạy Claude Code trên máy thật",
    "runtime.resolve_blocker": "đóng blocker - hành động hệ quả",
    "runtime.create_handoff": "tạo handoff giữa các function - hành động hệ quả",
    "work.review": "duyệt outcome - hành động hệ quả",
    "work.rework": "bắt làm lại outcome - hành động hệ quả",
    "runtime.classify_intent": "chỉ dành cho caller nội bộ, không phải lệnh người dùng",
    "runtime.dispatch_cycle_command": "chỉ dành cho voice agent sau khi xác nhận bằng lời - hành động hệ quả",
    "company.portfolio_status": "portfolio_v12 đang tắt có chủ đích, chưa có UI đi kèm",
    "sales.analyze_sales_data": "chạy phân tích CSV trong sandbox cô lập",
    "sales.outreach_dispatch": "gửi outreach qua n8n/outbox - hành động ngoại vi cần phê duyệt",
    "finance.analyze_financial_data": "chạy phân tích CSV trong sandbox cô lập",
    "execution.run_python": "chạy python trong sandbox cô lập",
    "execution.run_browser_research": "chạy nghiên cứu web trong sandbox cô lập",
    "execution.run_coding_task": "chạy tác vụ code và sinh patch trong sandbox cô lập",
    "execution.generate_landing_project": "sinh mã nguồn Next.js modular trong sandbox cô lập",
    "execution.run_skill": "chạy skill tùy biến trong sandbox cô lập",
}


def _real_tool_specs() -> dict[str, ToolSpec]:
    """Chỉ lấy tool khai báo trong app/modules, bỏ tool giả các test khác vừa đăng ký."""
    from core.tool_bootstrap import load_all_tools
    load_all_tools()

    return {
        name: spec
        for name, spec in get_registered_tools().items()
        if getattr(spec.callable, "__module__", "").startswith("")
    }


def test_every_tool_declares_whether_chat_can_use_it():
    """Chặn kiểu hỏng âm thầm: thêm tool mới mà quên chat_schema thì nó lặng lẽ vô hình
    với chat text, đúng thứ đã khiến chat không đọc được project/OKR nào."""
    undecided = [
        name
        for name, spec in _real_tool_specs().items()
        if spec.chat_schema is None and name not in CHAT_EXCLUDED_TOOLS
    ]
    assert not undecided, (
        f"Tool {undecided} chưa quyết định cho chat dùng hay không - thêm chat_schema, "
        f"hoặc thêm vào CHAT_EXCLUDED_TOOLS kèm lý do"
    )


def test_excluded_tools_all_still_exist():
    """Đổi tên/xoá tool mà quên dọn danh sách loại trừ thì danh sách đó âm thầm hết tác
    dụng - lần sau tool cùng tên xuất hiện lại sẽ lọt vào chat mà không ai để ý."""
    specs = _real_tool_specs()
    stale = [name for name in CHAT_EXCLUDED_TOOLS if name not in specs]
    assert not stale, f"CHAT_EXCLUDED_TOOLS trỏ tới tool không còn tồn tại: {stale}"


def test_no_excluded_tool_leaks_a_chat_schema():
    specs = _real_tool_specs()
    leaked = [name for name in CHAT_EXCLUDED_TOOLS if specs[name].chat_schema is not None]
    assert not leaked, f"Tool nằm trong danh sách loại trừ nhưng vẫn có chat_schema: {leaked}"


def test_chat_tool_names_are_valid_provider_function_names():
    """Tên có dấu chấm/khoảng trắng/quá 64 ký tự là provider trả 400 và hỏng nguyên lượt
    chat, không phải chỉ bỏ qua một tool."""
    import re

    pattern = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
    bad = [
        spec.flat_name
        for spec in _real_tool_specs().values()
        if spec.chat_schema and not pattern.match(spec.flat_name)
    ]
    assert not bad, f"Tên tool không hợp lệ với provider: {bad}"
