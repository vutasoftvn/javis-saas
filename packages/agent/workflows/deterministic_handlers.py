from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = [
    "WHITELISTED_DETERMINISTIC_HANDLERS",
    "DeterministicHandlerRegistry",
    "get_deterministic_handler",
    "list_deterministic_handlers",
    "register_deterministic_handler",
]

# Global registry of pure, deterministic functions (no I/O permitted)
_REGISTRY: dict[str, Callable[[dict[str, Any], dict[str, Any] | None], dict[str, Any]]] = {}


def register_deterministic_handler(
    handler_id: str,
    fn: Callable[[dict[str, Any], dict[str, Any] | None], dict[str, Any]],
) -> None:
    """Register a pure, deterministic handler by stable identifier."""
    _REGISTRY[handler_id] = fn


def get_deterministic_handler(
    handler_id: str,
) -> Callable[[dict[str, Any], dict[str, Any] | None], dict[str, Any]] | None:
    """Look up a deterministic handler by stable identifier."""
    return _REGISTRY.get(handler_id)


def list_deterministic_handlers() -> dict[str, Callable]:
    """Return all registered deterministic handlers."""
    return dict(_REGISTRY)


class DeterministicHandlerRegistry:
    """Registry instance for deterministic handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, Callable] = dict(_REGISTRY)

    def register(self, handler_id: str, fn: Callable) -> None:
        self._handlers[handler_id] = fn

    def get(self, handler_id: str) -> Callable | None:
        return self._handlers.get(handler_id)

    def all(self) -> dict[str, Callable]:
        return dict(self._handlers)


# Built-in pure deterministic transforms (no I/O):


def _pass_through(state: dict[str, Any], params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Passes state or specified inputs through."""
    if params and "output_key" in params:
        src_key = params.get("source_key", "input")
        return {params["output_key"]: state.get(src_key)}
    return {}


def _json_transform(state: dict[str, Any], params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Maps fields according to mapping dictionary."""
    if not params:
        return {}
    mapping = params.get("mapping", {})
    output_key = params.get("output_key", "transformed")
    result: dict[str, Any] = {}
    for target_field, source_field in mapping.items():
        if source_field in state:
            result[target_field] = state[source_field]
    return {output_key: result}


def _extract_fields(state: dict[str, Any], params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Extracts a list of keys from state into an output object."""
    if not params:
        return {}
    fields = params.get("fields", [])
    output_key = params.get("output_key", "extracted")
    return {output_key: {k: state.get(k) for k in fields if k in state}}


def _format_template(state: dict[str, Any], params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Formats a template string with state variables."""
    if not params:
        return {}
    template = params.get("template", "")
    output_key = params.get("output_key", "formatted_text")
    try:
        formatted = template.format(**state)
    except KeyError:
        formatted = template
    return {output_key: formatted}


# Register built-ins:
register_deterministic_handler("pass_through", _pass_through)
register_deterministic_handler("json_transform", _json_transform)
register_deterministic_handler("extract_fields", _extract_fields)
register_deterministic_handler("format_template", _format_template)
register_deterministic_handler("format_string", _format_template)

WHITELISTED_DETERMINISTIC_HANDLERS = _REGISTRY
