import json
import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


def parse_structured_output(text: str) -> Optional[dict[str, Any]]:
    """Parse structured JSON from model output with graceful recovery from
    markdown blocks or surrounding text.
    """
    if not text or not isinstance(text, str):
        return None

    clean = text.strip()
    # 1. Direct JSON parse
    try:
        data = json.loads(clean)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # 2. Markdown fenced block: ```json ... ``` or ``` ... ```
    fenced_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", clean, re.DOTALL | re.IGNORECASE)
    if fenced_match:
        try:
            data = json.loads(fenced_match.group(1).strip())
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    # 3. Outer bracket extraction
    match = re.search(r"\{[\s\S]*\}", clean, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    return None


def parse_tool_calls(text: str) -> list[dict[str, Any]]:
    """Extract tool calls from model structured response.

    Supports:
    - {"tool_call": {"name": "...", "arguments": {...}}}
    - {"tool_calls": [{"name": "...", "arguments": {...}}]}
    - {"action": "call_tool", "tool": "...", "args": {...}}
    """
    parsed = parse_structured_output(text)
    if not parsed:
        return []

    calls: list[dict[str, Any]] = []

    if "tool_call" in parsed and isinstance(parsed["tool_call"], dict):
        tc = parsed["tool_call"]
        name = tc.get("name") or tc.get("tool") or tc.get("function")
        args = tc.get("arguments") or tc.get("args") or {}
        if name:
            calls.append({"name": str(name), "arguments": args if isinstance(args, dict) else {}})

    elif "tool_calls" in parsed and isinstance(parsed["tool_calls"], list):
        for tc in parsed["tool_calls"]:
            if isinstance(tc, dict):
                name = tc.get("name") or tc.get("tool") or tc.get("function")
                if isinstance(tc.get("function"), dict):
                    name = tc["function"].get("name", name)
                    args = tc["function"].get("arguments", {})
                else:
                    args = tc.get("arguments") or tc.get("args") or {}
                if name:
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {}
                    calls.append({"name": str(name), "arguments": args if isinstance(args, dict) else {}})

    elif parsed.get("action") in ("call_tool", "tool_call") and ("tool" in parsed or "name" in parsed):
        name = parsed.get("tool") or parsed.get("name")
        args = parsed.get("args") or parsed.get("arguments") or {}
        if name:
            calls.append({"name": str(name), "arguments": args if isinstance(args, dict) else {}})

    return calls
