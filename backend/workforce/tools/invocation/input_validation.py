import json
import inspect
from typing import Any, Optional, Union, Dict
from jsonschema import validate, ValidationError

from core.tool_registry import ToolSpec
from workforce.agents.runtime.execution_scope import ExecutionScope

class InputValidationError(Exception):
    def __init__(self, message: str, details: Any = None):
        self.message = message
        self.details = details
        super().__init__(message)

# Server-derived parameters that must never be trusted from model input, even when a
# connector's discovered JSON schema declares them as a property - an extension manifest
# is attacker-influenced input, not a trust boundary.
INJECTED_PARAMS = (
    "db",
    "workspace_id",
    "company_id",
    "user_id",
    "chat_session_id",
    "agent_key",
    "agent_run_id",
    "endpoint",
    "approval",
    "governance_decision",
)

def strip_reserved_schema_properties(schema: Optional[dict]) -> Optional[dict]:
    """Remove reserved/injected parameter names from a JSON Schema's declared
    properties before it's ever advertised to a model. A discovered connector schema
    is attacker-influenced input - even just *declaring* "workspace_id" or "endpoint"
    as a property a caller can set is the gap, independent of whether a given call's
    argument values also get stripped by normalize_arguments() below."""
    if not isinstance(schema, dict):
        return schema
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        return schema
    filtered_properties = {k: v for k, v in properties.items() if k not in INJECTED_PARAMS}
    if filtered_properties == properties:
        return schema
    filtered = dict(schema)
    filtered["properties"] = filtered_properties
    required = schema.get("required")
    if isinstance(required, list):
        filtered["required"] = [name for name in required if name not in INJECTED_PARAMS]
    return filtered


def _get_callable_parameters(spec: ToolSpec) -> set[str]:
    try:
        return set(inspect.signature(spec.callable).parameters.keys())
    except (TypeError, ValueError):
        return set()

def normalize_arguments(spec: ToolSpec, arguments: Union[str, Dict[str, Any], None], scope: ExecutionScope) -> Dict[str, Any]:
    """Parse, validate and normalize tool input arguments."""
    
    # 1. Parse JSON if string
    if isinstance(arguments, str):
        try:
            raw_args = json.loads(arguments or "{}")
        except json.JSONDecodeError as exc:
            raise InputValidationError(f"Invalid JSON format: {exc}")
    elif isinstance(arguments, dict):
        raw_args = arguments
    elif arguments is None:
        raw_args = {}
    else:
        raise InputValidationError("Arguments must be a dict or a JSON string")
        
    if not isinstance(raw_args, dict):
        raise InputValidationError("Arguments must decode to a JSON object/dict")

    # 2. JSON Schema Validation if schema is present
    # Combine input_schema and chat_schema if input_schema is None (backward compat)
    schema = spec.input_schema or (spec.chat_schema.get("parameters") if spec.chat_schema else None)
    if schema:
        try:
            validate(instance=raw_args, schema=schema)
        except ValidationError as exc:
            raise InputValidationError(f"Validation failed: {exc.message}", details=exc.message)

    # 3. Strip unapproved/injected params
    callable_params = _get_callable_parameters(spec)
    schema_props = set(schema.get("properties", {}).keys()) if schema else set()
    
    allowed_params = callable_params.union(schema_props)
    
    normalized = {}
    for key, value in raw_args.items():
        if key in INJECTED_PARAMS:
            continue
            
        if allowed_params and key not in allowed_params:
            continue
            
        normalized[key] = value

    return normalized
