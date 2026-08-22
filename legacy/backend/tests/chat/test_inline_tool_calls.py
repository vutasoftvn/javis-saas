import json
from integrations.llm_providers._openai_compatible import extract_inline_tool_calls, cleanse_text_content


def test_extract_inline_qwen_chinese_tool_call():
    text = (
        '征求function和控制chat_propose_action json {"priority":"P1",'
        '"reason":"Thiết kế lại roadmap để triển khai trong 4 tuần theo yêu cầu của người dùng.",'
        '"requested_action":"Thiết kế lại MVP Roadmap mID với timeline rút gọn (4 tuần), gộp các giai đoạn chính thành 1 phase tập trung vào core features."}'
    )
    calls = extract_inline_tool_calls(text)
    assert len(calls) == 1
    assert calls[0].name == "chat_propose_action"
    args = json.loads(calls[0].arguments)
    assert args["priority"] == "P1"
    assert "4 tuần" in args["reason"]
    assert "Thiết kế lại MVP Roadmap" in args["requested_action"]

    cleaned = cleanse_text_content(text)
    assert "chat_propose_action" not in cleaned
    assert "{" not in cleaned


def test_extract_inline_tool_sep_format():
    text = (
        '<|placeholder_123|>function<|tool_sep|>chat_propose_action json '
        '{"requested_action": "Tạo dự án mới", "reason": "Founder yêu cầu", "priority": "P0"}'
    )
    calls = extract_inline_tool_calls(text)
    assert len(calls) == 1
    assert calls[0].name == "chat_propose_action"
    args = json.loads(calls[0].arguments)
    assert args["priority"] == "P0"

    cleaned = cleanse_text_content(text)
    assert "chat_propose_action" not in cleaned
    assert "<|" not in cleaned


def test_extract_inline_tool_call_tags():
    text = (
        '<tool_call>\n'
        '{"name": "chat_propose_action", "arguments": {"requested_action": "Duyệt đơn", "reason": "Hợp lệ"}}\n'
        '</tool_call>'
    )
    calls = extract_inline_tool_calls(text)
    assert len(calls) == 1
    assert calls[0].name == "chat_propose_action"
    args = json.loads(calls[0].arguments)
    assert args["requested_action"] == "Duyệt đơn"

    cleaned = cleanse_text_content(text)
    assert "<tool_call>" not in cleaned
    assert "chat_propose_action" not in cleaned


def test_extract_inline_direct_function():
    text = 'chat_propose_action json {"requested_action": "Cập nhật milestone", "reason": "Xong sprint 1"}'
    calls = extract_inline_tool_calls(text)
    assert len(calls) == 1
    assert calls[0].name == "chat_propose_action"
    args = json.loads(calls[0].arguments)
    assert args["reason"] == "Xong sprint 1"


def test_extract_inline_thai_special_tokens_artifact_with_markdown_fences():
    text = (
        "Tôi đã hiểu nhầm yêu cầu của bạn. Tôi sẽ tạo một đề xuất cụ thể.\n\n"
        "หมู่< | tool__call__begin | >function< | tool__sep | >chat_propose_action\n\n"
        '{"priority":"P1","reason":"Người dùng yêu cầu thiết kế lại roadmap 4 tuần.","requested_action":"Cập nhật MVP Roadmap 4 tuần"}'
        "```< | tool__call__end | >< | tool__calls__end >\n\n"
        'Bạn vui lòng kiểm tra mục **"Cần bạn xử lý"**.'
    )
    calls = extract_inline_tool_calls(text)
    assert len(calls) == 1
    assert calls[0].name == "chat_propose_action"
    args = json.loads(calls[0].arguments)
    assert args["priority"] == "P1"
    assert "roadmap 4 tuần" in args["reason"]
    assert args["requested_action"] == "Cập nhật MVP Roadmap 4 tuần"

    cleaned = cleanse_text_content(text)
    assert "chat_propose_action" not in cleaned
    assert "< |" not in cleaned
    assert "| >" not in cleaned
    assert "หมู่" not in cleaned
    assert "priority" not in cleaned
    assert "Tôi đã hiểu nhầm yêu cầu của bạn" in cleaned
    assert 'Bạn vui lòng kiểm tra mục **"Cần bạn xử lý"**.' in cleaned


def test_safe_stream_text_buffering():
    from integrations.llm_providers._openai_compatible import safe_stream_text

    raw_1 = "Tôi đã hiểu nhầm yêu cầu của bạn."
    assert safe_stream_text(raw_1) == "Tôi đã hiểu nhầm yêu cầu của bạn."

    raw_2 = raw_1 + "\n\nหมู่< | tool__call__begin | >function< | tool__sep | >chat_propose_action\n\n{\"priority\": \"P1\","
    assert "chat_propose_action" not in safe_stream_text(raw_2)
    assert "< |" not in safe_stream_text(raw_2)
    assert safe_stream_text(raw_2) == "Tôi đã hiểu nhầm yêu cầu của bạn."

    raw_3 = (
        raw_1
        + '\n\nหมู่< | tool__call__begin | >function< | tool__sep | >chat_propose_action\n\n{"priority":"P1","reason":"test"}```< | tool__call__end | >< | tool__calls__end >\n\n'
        + 'Bạn vui lòng kiểm tra mục **"Cần bạn xử lý"**.'
    )
    res = safe_stream_text(raw_3)
    assert "Tôi đã hiểu nhầm yêu cầu của bạn." in res
    assert 'Bạn vui lòng kiểm tra mục **"Cần bạn xử lý"**.' in res
    assert "chat_propose_action" not in res
    assert "หมู่" not in res


def test_extract_inline_strategy_list_projects_user_reported_case():
    # Trường hợp người dùng gặp phải: model sinh function< | tool__sep | >strategy_list_projects
    raw = 'function< | tool__sep | >strategy_list_projects\n\n{"query":"mID"}'
    calls = extract_inline_tool_calls(raw)
    assert len(calls) == 1
    assert calls[0].name == "strategy_list_projects"
    args = json.loads(calls[0].arguments)
    assert args["query"] == "mID"

    cleaned = cleanse_text_content(raw)
    assert cleaned == ""


def test_extract_inline_with_markdown_code_fences():
    raw = 'function< | tool__sep | >strategy_list_projects\n```json\n{"query":"mID"}\n```'
    calls = extract_inline_tool_calls(raw)
    assert len(calls) == 1
    assert calls[0].name == "strategy_list_projects"
    args = json.loads(calls[0].arguments)
    assert args["query"] == "mID"

    cleaned = cleanse_text_content(raw)
    assert cleaned == ""


def test_extract_inline_with_backticks():
    raw = 'function< | tool__sep | >strategy_list_projects\n`{"query":"mID"}`'
    calls = extract_inline_tool_calls(raw)
    assert len(calls) == 1
    assert calls[0].name == "strategy_list_projects"
    args = json.loads(calls[0].arguments)
    assert args["query"] == "mID"

    cleaned = cleanse_text_content(raw)
    assert cleaned == ""


def test_extract_inline_mistral_tool_calls():
    raw = '[TOOL_CALLS] [{"name": "strategy_list_projects", "arguments": {"query": "mID"}}]'
    calls = extract_inline_tool_calls(raw)
    assert len(calls) == 1
    assert calls[0].name == "strategy_list_projects"
    args = json.loads(calls[0].arguments)
    assert args["query"] == "mID"

    cleaned = cleanse_text_content(raw)
    assert cleaned == ""


def test_safe_stream_text_tool_chunk_leak_prevention():
    from integrations.llm_providers._openai_compatible import safe_stream_text

    chunks = [
        "function",
        "< | tool__sep | >",
        "strategy_list_projects",
        "\n\n",
        "```json\n",
        '{"query":',
        '"mID"}',
        "\n```",
    ]
    accum = ""
    emitted = ""
    for c in chunks:
        accum += c
        safe = safe_stream_text(accum)
        if len(safe) > len(emitted):
            emitted += safe[len(emitted):]

    assert emitted == ""


