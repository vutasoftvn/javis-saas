from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from agent_core.contracts.capability import CapabilitySpec

__all__ = ["CapabilityHandler", "CapabilityRegistration", "CapabilityRegistry"]

CapabilityHandler = Callable[[dict[str, Any], dict[str, Any]], Any | Coroutine[Any, Any, Any]]


class CapabilityRegistration:
    def __init__(self, spec: CapabilitySpec, handler: CapabilityHandler) -> None:
        self.spec = spec
        self.handler = handler


class CapabilityRegistry:
    """Registry quản lý CapabilitySpec và Handlers theo Master Guide §16.3."""

    def __init__(self) -> None:
        self._capabilities: dict[str, CapabilityRegistration] = {}

    def register(self, spec: CapabilitySpec, handler: CapabilityHandler) -> None:
        self._capabilities[spec.id] = CapabilityRegistration(spec=spec, handler=handler)

    def get(self, capability_id: str) -> CapabilityRegistration | None:
        return self._capabilities.get(capability_id)

    def list_specs(self) -> list[CapabilitySpec]:
        return [reg.spec for reg in self._capabilities.values()]

    def validate_input(self, spec: CapabilitySpec, payload: dict[str, Any]) -> list[str]:
        """Validate input payload against CapabilitySpec.input_schema (required fields, types)."""
        errors: list[str] = []
        schema = spec.input_schema or {}
        required_fields = schema.get("required", [])

        for field in required_fields:
            if field not in payload or payload[field] is None:
                errors.append(f"Missing required field: '{field}'")

        properties = schema.get("properties", {})
        for k, val in payload.items():
            if k in properties:
                prop_type = properties[k].get("type")
                if prop_type in {"number", "integer"}:
                    if not isinstance(val, (int, float)) or isinstance(val, bool):
                        errors.append(
                            f"Field '{k}' expected type {prop_type}, got {type(val).__name__}"
                        )
                elif prop_type == "string":
                    if not isinstance(val, str):
                        errors.append(f"Field '{k}' expected string, got {type(val).__name__}")
                elif prop_type == "array":
                    if not isinstance(val, list):
                        errors.append(f"Field '{k}' expected array, got {type(val).__name__}")
                elif prop_type == "object" and not isinstance(val, dict):
                    errors.append(f"Field '{k}' expected object, got {type(val).__name__}")

        return errors
