import re
from dataclasses import fields
from typing import Any

from sqlalchemy.orm import Session

from app.core import tool_registry
from app.core.tool_registry import ToolSpec
from app.workforce.agents.runtime.execution_scope import ExecutionScope
from app.workforce.extensions.eligibility import resolve_eligible_capabilities
from app.workforce.extensions.registry import ExtensionRegistry


async def _connector_dispatch_marker(**arguments: Any) -> Any:
    raise RuntimeError("Connector tools must be dispatched by ToolInvocationService")


def register_extension_tools(
    db: Session, scope: ExecutionScope
) -> list[ToolSpec]:
    registered_specs: list[ToolSpec] = []
    registry = ExtensionRegistry()
    registrations = {
        registration.extension_id: registration
        for registration in registry.get_all(db, scope.workspace_id)
    }

    for eligible in resolve_eligible_capabilities(db, scope):
        if not eligible.eligible:
            continue

        registration = registrations.get(eligible.extension_id)
        if registration is None:
            continue

        capability = registry.get_capability(
            db, scope.workspace_id, eligible.capability_id
        )
        if capability is None:
            continue

        manifest = registration.manifest_jsonb
        supported_scopes = tuple(manifest.get("supported_scope_levels", ()))
        required_scope_level = (
            supported_scopes[0] if len(supported_scopes) == 1 else None
        )
        candidate = ToolSpec(
            namespace=_stable_namespace(eligible.extension_id),
            name=eligible.name,
            callable=_connector_dispatch_marker,
            chat_schema={
                "description": capability.description or eligible.name,
                "parameters": eligible.input_schema
                or {"type": "object", "properties": {}, "required": []},
            },
            input_schema=eligible.input_schema,
            output_schema=eligible.output_schema,
            execution_backend="connector",
            required_scope_level=required_scope_level,
            required_secret_refs=list(eligible.required_secret_refs),
            backend_id=eligible.extension_id,
        )

        existing = tool_registry.get_registered_tools().get(candidate.qualified_name)
        if existing is not None and not _semantically_identical(existing, candidate):
            continue

        tool_registry.register(
            namespace=candidate.namespace,
            name=candidate.name,
            chat_schema=candidate.chat_schema,
            input_schema=candidate.input_schema,
            output_schema=candidate.output_schema,
            execution_backend=candidate.execution_backend,
            required_scope_level=candidate.required_scope_level,
            required_secret_refs=candidate.required_secret_refs,
            backend_id=candidate.backend_id,
        )(_connector_dispatch_marker)
        registered_specs.append(
            tool_registry.get_registered_tools()[candidate.qualified_name]
        )

    return registered_specs


def _stable_namespace(extension_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "_", extension_id)


def _semantically_identical(left: ToolSpec, right: ToolSpec) -> bool:
    return all(
        getattr(left, field.name) == getattr(right, field.name)
        for field in fields(ToolSpec)
        if field.name != "callable"
    )
