from __future__ import annotations

from typing import Any, Callable


async def format_string_handler(state: dict[str, Any], params: dict[str, Any] | None = None) -> dict[str, Any]:
    params = params or {}
    template = params.get("template", "")
    try:
        formatted = template.format(**state)
    except Exception:
        formatted = template
    out_key = params.get("output_key", "formatted")
    return {out_key: formatted}


async def pass_through_handler(state: dict[str, Any]) -> dict[str, Any]:
    return {}


WHITELISTED_DETERMINISTIC_HANDLERS: dict[str, Callable[..., Any]] = {
    "format_string": format_string_handler,
    "pass_through": pass_through_handler,
    "done": pass_through_handler,
}
