"""Client dùng chung cho các provider theo chuẩn OpenAI /chat/completions (OpenAI,
OpenRouter, DeepSeek, ApiAI.vn)."""

import json
import re
from typing import Any, AsyncIterator

import httpx

from app.modules.chat.ai_router import AIEvent, ChatTurn, ToolCall


def turn_to_payload(turn: ChatTurn) -> dict:
    """Một ChatTurn -> một message theo đúng hình dạng OpenAI mong đợi.

    Lượt tool phải giữ nguyên tool_call_id và lượt assistant phải giữ nguyên tool_calls:
    provider đối chiếu id giữa hai lượt đó, thiếu là cả hội thoại bị từ chối 400.
    """
    if turn.role == "tool":
        return {
            "role": "tool",
            "tool_call_id": turn.tool_call_id,
            "content": turn.content,
        }

    message: dict[str, Any] = {"role": turn.role, "content": turn.content}
    if turn.tool_calls:
        message["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.name, "arguments": call.arguments},
            }
            for call in turn.tool_calls
        ]
    return message


class _ToolCallAccumulator:
    """Tool call về theo từng mảnh giống hệt text: tên ở mảnh đầu, arguments nhỏ giọt qua
    nhiều chunk. Phải gom theo ``index`` rồi mới parse - đọc từng mảnh là JSON luôn dở dang."""

    def __init__(self):
        self._by_index: dict[int, dict] = {}

    def add(self, chunk: dict) -> None:
        index = chunk.get("index", 0)
        current = self._by_index.setdefault(index, {"id": "", "name": "", "arguments": ""})
        if chunk.get("id"):
            current["id"] = chunk["id"]
        function = chunk.get("function") or {}
        if function.get("name"):
            current["name"] = function["name"]
        if function.get("arguments"):
            current["arguments"] += function["arguments"]

    def finish(self) -> list[ToolCall]:
        return [
            ToolCall(
                id=item["id"] or f"call_{index}",
                name=item["name"],
                arguments=item["arguments"] or "{}",
            )
            for index, item in sorted(self._by_index.items())
            if item["name"]
        ]


_RAW_SPECIAL_TOKENS = re.compile(
    r"<\s*\|\s*[\s\S]*?\|\s*>|"
    r"<\s*\|\s*[\w\_\-\s]+?\s*>|"
    r"<\s*[\w\_\-\s]+?\s*\|\s*>|"
    r"\[\s*\/?TOOL_CALLS\s*\]|"
    r"<\s*\/?tool_calls?\s*>|"
    r"<\s*\/?think\s*>",
    re.IGNORECASE,
)
_INLINE_TOOL_CALL_TAG = re.compile(
    r"<tool_call>\s*([\s\S]*?)\s*</tool_call>",
    re.IGNORECASE,
)
_FOREIGN_PREFIX_ARTIFACTS = re.compile(
    r"[\u0E00-\u0E7F\u4E00-\u9FFF\u3040-\u30FF\u0600-\u06FF]+(?=\s*(?:<\s*\||function|tool_call|call|action|tool|[a-zA-Z0-9_\-]*propose_action))",
    re.IGNORECASE,
)
_TRAILING_FENCES = re.compile(r"^\s*`{1,4}", re.MULTILINE)

_FN_PATTERN = re.compile(
    r"(?:"
    r"(?:[\u0E00-\u0E7F\u4E00-\u9FFF\u3040-\u30FF\u0600-\u06FF\s]+|<\s*\|?\s*[^>]*?\s*\|?\s*>)+\s*"
    r"(?:function|tool_call|call|action|tool)?\s*[:\s]*"
    r"(?:<\s*\|?\s*[^>]*?\s*\|?\s*>)*\s*"
    r"([a-zA-Z0-9_\-]+)\s*"
    r"|"
    r"(?:\b(?:function|tool_call|action)\b)\s*[:\s]*\s*(?:<\s*\|?\s*[^>]*?\s*\|?\s*>)*\s*([a-zA-Z0-9_\-]+)\s*"
    r"|"
    r"\b([a-zA-Z0-9_\-]*propose_action|[a-zA-Z0-9_\-]*_list_[a-zA-Z0-9_\-]+)\s*"
    r")"
    r"(?:Action\s+Input\s*:\s*)?"
    r"(?:json|arguments)?\s*"
    r"(?:`{1,4}(?:json)?\s*)?"
    r"(?=\{)",
    re.IGNORECASE,
)


def _extract_balanced_json(text: str, start_idx: int = 0) -> tuple[str, int, int] | None:
    """Trích xuất chuỗi JSON hoàn chỉnh {...} hoặc [...] cân bằng dấu ngoặc.
    Trả về (json_str, start_pos, end_pos)."""
    first_brace = -1
    open_char = ""
    close_char = ""
    for i in range(start_idx, len(text)):
        if text[i] == "{":
            first_brace = i
            open_char, close_char = "{", "}"
            break
        elif text[i] == "[":
            first_brace = i
            open_char, close_char = "[", "]"
            break
    if first_brace == -1:
        return None

    depth = 0
    in_string = False
    escape = False
    for i in range(first_brace, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if not in_string:
            if ch == open_char:
                depth += 1
            elif ch == close_char:
                depth -= 1
                if depth == 0:
                    return text[first_brace : i + 1], first_brace, i + 1
    return None


def extract_inline_tool_calls(text: str) -> list[ToolCall]:
    """Parse tool call dạng thô (nếu mô hình tự sinh ra trong content thay vì delta.tool_calls).

    Hỗ trợ mọi định dạng:
    - Qwen / DeepSeek Chinese: 征求function和控制chat_propose_action json {...}
    - Qwen tool sep: function< | tool__sep | >strategy_list_projects\n```json\n{...}\n```
    - Tool call begin/end: หมู่< | tool__call__begin | >function< | tool__sep | >chat_propose_action {...}
    - Tool tag: <tool_call> {"name": "...", "arguments": {...}} </tool_call>
    - Mistral / Llama: [TOOL_CALLS] [{"name": "...", "arguments": {...}}]
    - Direct function name: chat_propose_action json {...}
    """
    calls: list[ToolCall] = []

    # 1. <tool_call> ... </tool_call>
    for idx, match in enumerate(_INLINE_TOOL_CALL_TAG.finditer(text)):
        tag_content = match.group(1).strip()
        extracted = _extract_balanced_json(tag_content, 0)
        if extracted:
            json_str, _, _ = extracted
            try:
                data = json.loads(json_str)
                if isinstance(data, dict):
                    func_name = data.get("name") or data.get("function")
                    args = data.get("arguments") or data.get("parameters") or {}
                    args_str = json.dumps(args) if isinstance(args, dict) else str(args)
                    if func_name:
                        calls.append(ToolCall(id=f"inline_tag_{idx}", name=func_name, arguments=args_str))
                        continue
            except Exception:
                pass
        m = re.search(r"([a-zA-Z0-9_\-]+)\s*(?:json)?\s*[\`\s]*", tag_content)
        if m and extracted:
            func_name = m.group(1).strip()
            calls.append(ToolCall(id=f"inline_tag_{idx}", name=func_name, arguments=extracted[0]))

    if calls:
        return calls

    # 2. [TOOL_CALLS] [...]
    mistral_pattern = re.compile(r"\[TOOL_CALLS\]\s*", re.IGNORECASE)
    m_match = mistral_pattern.search(text)
    if m_match:
        extracted = _extract_balanced_json(text, m_match.end())
        if extracted:
            json_str, _, _ = extracted
            try:
                data = json.loads(json_str)
                if isinstance(data, list):
                    for idx, item in enumerate(data):
                        if isinstance(item, dict) and "name" in item:
                            args = item.get("arguments") or {}
                            args_str = json.dumps(args) if isinstance(args, dict) else str(args)
                            calls.append(ToolCall(id=f"inline_tc_{idx}", name=item["name"], arguments=args_str))
                    if calls:
                        return calls
                elif isinstance(data, dict) and "name" in data:
                    args = data.get("arguments") or {}
                    args_str = json.dumps(args) if isinstance(args, dict) else str(args)
                    calls.append(ToolCall(id="inline_tc_0", name=data["name"], arguments=args_str))
                    return calls
            except Exception:
                pass

    # 3. Flexible pattern: function / tool_call / special tokens / prefix + function_name + optional fences + { ... }
    for idx, match in enumerate(_FN_PATTERN.finditer(text)):
        func_name = (match.group(1) or match.group(2) or match.group(3) or "").strip()
        if not func_name or func_name.lower() in ("the", "a", "an", "is", "for", "with", "this", "that", "json", "action", "function", "input"):
            continue
        extracted = _extract_balanced_json(text, match.end())
        if extracted:
            args_str, _, _ = extracted
            try:
                json.loads(args_str)
                calls.append(ToolCall(id=f"inline_call_{idx}", name=func_name, arguments=args_str))
            except Exception:
                pass

    return calls


def cleanse_text_content(text: str) -> str:
    """Lọc bỏ các token đặc biệt hoặc placeholder của tokenizer và cú pháp tool bị rò rỉ ra văn bản."""
    cleaned = text
    cleaned = re.sub(r"<tool_call>[\s\S]*?</tool_call>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\[TOOL_CALLS\]\s*\[[\s\S]*?\]", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\[TOOL_CALLS\]\s*\{[\s\S]*?\}", "", cleaned, flags=re.IGNORECASE)

    while True:
        match = _FN_PATTERN.search(cleaned)
        if not match:
            break
        func_name = (match.group(1) or match.group(2) or match.group(3) or "").strip()
        if not func_name or func_name.lower() in ("the", "a", "an", "is", "for", "with", "this", "that", "json", "action", "function", "input"):
            break
        extracted = _extract_balanced_json(cleaned, match.end())
        if extracted:
            _, _, end_pos = extracted
            trailing = cleaned[end_pos:]
            # Bỏ qua cả phần markdown backticks hoặc thẻ kết thúc phía sau nếu có
            trailing = re.sub(r"^\s*`{1,4}", "", trailing)
            trailing = _RAW_SPECIAL_TOKENS.sub("", trailing)
            cleaned = cleaned[:match.start()] + trailing
        else:
            # Nếu JSON chưa hoàn tất (đang stream dở)
            cleaned = cleaned[:match.start()]
            break

    cleaned = _RAW_SPECIAL_TOKENS.sub("", cleaned)
    cleaned = _FOREIGN_PREFIX_ARTIFACTS.sub("", cleaned)
    # Xoá bớt các dòng trống liên tiếp thừa
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned


_INCOMPLETE_SPECIAL_PREFIX = re.compile(
    r"(?:"
    r"[\u0E00-\u0E7F\u4E00-\u9FFF\u3040-\u30FF\u0600-\u06FF]+(?=\s*(?:<\s*\||function|tool_call|call|action|tool|[a-zA-Z0-9_\-]*propose_action))"
    r"|<\s*\|?[^>]*$"
    r"|<\s*\/?(?:tool_calls?|think)[^>]*$"
    r"|\[\s*\/?(?:TOOL_CALLS)[^\]]*$"
    r"|(?:\b(?:function|tool_call|action)\b|[a-zA-Z0-9_\-]*propose_action|[a-zA-Z0-9_\-]*_list_[a-zA-Z0-9_\-]+)[\s\S]*$"
    r")",
    re.IGNORECASE,
)


def safe_stream_text(raw_text: str) -> str:
    """Trả về phần văn bản an toàn đã làm sạch để stream ra cho client."""
    cleaned = cleanse_text_content(raw_text)
    safe = _INCOMPLETE_SPECIAL_PREFIX.sub("", cleaned)
    return safe


class OpenAICompatibleClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._transport = transport

    async def stream_chat(
        self, turns: list[ChatTurn], tools: list[dict[str, Any]] | None = None
    ) -> AsyncIterator[AIEvent]:
        if not self._api_key:
            yield AIEvent(kind="failed", error_code="provider_not_configured")
            return

        headers = {"Authorization": f"Bearer {self._api_key}"}
        payload = {
            "model": self._model,
            "messages": [turn_to_payload(turn) for turn in turns],
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        accumulator = _ToolCallAccumulator()
        accumulated_raw_content = ""
        emitted_safe_len = 0
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                transport=self._transport,
                timeout=60.0,
            ) as client:
                async with client.stream(
                    "POST", "/chat/completions", headers=headers, json=payload
                ) as response:
                    if response.status_code != 200:
                        yield AIEvent(kind="failed", error_code=f"provider_http_{response.status_code}")
                        return
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        raw = line[6:]
                        if raw == "[DONE]":
                            break
                        try:
                            data = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        choices = data.get("choices") or []
                        if choices:
                            delta = choices[0].get("delta") or {}
                            content = delta.get("content")
                            if content:
                                if not tools:
                                    # Không dùng tools: stream trực tiếp không cần lọc/buffer tool call
                                    yield AIEvent(kind="delta", content=content)
                                else:
                                    accumulated_raw_content += content
                                    safe_text = safe_stream_text(accumulated_raw_content)
                                    if len(safe_text) > emitted_safe_len:
                                        chunk_to_emit = safe_text[emitted_safe_len:]
                                        emitted_safe_len = len(safe_text)
                                        yield AIEvent(kind="delta", content=chunk_to_emit)
                            for chunk in delta.get("tool_calls") or []:
                                accumulator.add(chunk)
                            if choices[0].get("finish_reason"):
                                usage = data.get("usage") or {}
                                tool_calls = accumulator.finish()
                                if tools and not tool_calls and accumulated_raw_content:
                                    # Fallback: parse inline tool calls nếu mô hình tự format trong content
                                    tool_calls = extract_inline_tool_calls(accumulated_raw_content)
                                for call in tool_calls:
                                    yield AIEvent(kind="tool_call", tool_call=call)
                                if tools and not tool_calls and accumulated_raw_content:
                                    # Stream đã kết thúc và không có tool call: xả nốt phần text còn lại nếu còn
                                    final_text = cleanse_text_content(accumulated_raw_content)
                                    if len(final_text) > emitted_safe_len:
                                        yield AIEvent(kind="delta", content=final_text[emitted_safe_len:])
                                accumulator = _ToolCallAccumulator()
                                accumulated_raw_content = ""
                                emitted_safe_len = 0
                                yield AIEvent(
                                    kind="completed",
                                    input_tokens=usage.get("prompt_tokens"),
                                    output_tokens=usage.get("completion_tokens"),
                                )
        except httpx.HTTPError:
            yield AIEvent(kind="failed", error_code="provider_unavailable")

