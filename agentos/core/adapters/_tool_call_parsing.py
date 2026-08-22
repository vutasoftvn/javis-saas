from __future__ import annotations

import json
import re
from typing import Optional

from agentos.core.model_provider import ToolCallRequest


def parse_tool_call(text: str) -> Optional[ToolCallRequest]:
    """Best-effort extraction of the `{"tool_call": {"name": ..., "arguments": {...}}}`
    convention from raw model text (direct JSON, fenced code block, or embedded
    object). Shared by every ModelProvider adapter so all providers agree on
    the same tool-call convention regardless of the underlying API shape.
    """
    if not text:
        return None
    candidates = [text.strip()]
    fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        candidates.append(fenced.group(1).strip())
    brace = re.search(r"\{[\s\S]*\}", text, re.DOTALL)
    if brace:
        candidates.append(brace.group(0))

    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        call = data.get("tool_call")
        if isinstance(call, dict) and "name" in call:
            return ToolCallRequest(tool_name=call["name"], arguments=call.get("arguments") or {})
    return None
