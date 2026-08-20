import re
from dataclasses import fields
from typing import Any

from sqlalchemy.orm import Session

from app.core import tool_registry
from app.core.tool_registry import ToolSpec
from app.workforce.agents.runtime.execution_scope import ExecutionScope
from app.workforce.extensions.eligibility import (
    EligibleCapability,
    resolve_eligible_capabilities,
)
from app.workforce.extensions.registry import ExtensionRegistry
from app.workforce.extensions.seams import DiscoveredCapability
from app.workforce.tools.invocation.input_validation import strip_reserved_schema_properties


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

        candidate = extension_tool_spec(
            eligible, capability, registration.manifest_jsonb
        )

        registered_tools = tool_registry.get_registered_tools()
        existing = registered_tools.get(candidate.qualified_name)
        if (
            existing is not None
            and existing.backend_id != candidate.backend_id
            and not tool_specs_semantically_identical(existing, candidate)
        ):
            # Same qualified_name claimed by a different extension - refuse the
            # collision rather than pick a winner. A re-discovery of the SAME
            # extension (existing.backend_id == candidate.backend_id) always wins
            # below instead, since that's just a refresh, not a conflict.
            continue
        if any(
            registered.flat_name == candidate.flat_name
            and registered.qualified_name != candidate.qualified_name
            for registered in registered_tools.values()
        ):
            continue

        tool_registry.register_overlay_tool(candidate)
        registered_specs.append(candidate)

    return registered_specs


def _stable_namespace(extension_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "_", extension_id)


def extension_tool_spec(
    eligible: EligibleCapability,
    capability: DiscoveredCapability,
    manifest: dict,
) -> ToolSpec:
    supported_scopes = tuple(manifest.get("supported_scope_levels", ()))
    required_scope_level = supported_scopes[0] if len(supported_scopes) == 1 else None
    # A discovered connector schema can declare a reserved name (workspace_id,
    # endpoint, approval, ...) as one of its own properties - strip those before the
    # schema is ever advertised to a model, not just when a call's arguments are
    # normalized (see input_validation.normalize_arguments).
    input_schema = strip_reserved_schema_properties(eligible.input_schema)
    return ToolSpec(
        namespace=_stable_namespace(eligible.extension_id),
        name=eligible.name,
        callable=_connector_dispatch_marker,
        chat_schema={
            "description": capability.description or eligible.name,
            "parameters": input_schema
            or {"type": "object", "properties": {}, "required": []},
        },
        input_schema=input_schema,
        output_schema=eligible.output_schema,
        execution_backend="connector",
        required_scope_level=required_scope_level,
        required_secret_refs=list(eligible.required_secret_refs),
        backend_id=eligible.extension_id,
        # Governance metadata comes from the validated first-party manifest via
        # eligibility resolution (resolve_eligible_capabilities fails closed if it's
        # missing) - never defaulted here, so a manifest declaring "critical"/mutating
        # can't silently register as the ToolSpec default "low"/read_only.
        risk_level=eligible.risk_level,
        permission_level=eligible.permission_level,
        requires_approval=eligible.requires_approval,
        mutating=eligible.mutating,
        external=eligible.external,
    )


def tool_specs_semantically_identical(left: ToolSpec, right: ToolSpec) -> bool:
    return all(
        getattr(left, field.name) == getattr(right, field.name)
        for field in fields(ToolSpec)
        if field.name != "callable"
    )
