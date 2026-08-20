# COSA Phase B — Governed Extension Execution Design

**Status:** Proposed

## Goal

Make a first-party MCP extension executable end-to-end through COSA's canonical
tool registry and governance boundary. An extension capability must be
discoverable, eligible for a request scope, offered as a `ToolSpec`, and invoked
through JSON-RPC `tools/call` only after the canonical governance decision.

Phase B does not create a new agent runtime, tool registry, policy vocabulary,
skill lifecycle, workflow engine, or multi-agent capability.

## Non-negotiable boundaries

- `GovernanceKernel` remains the only authority that returns allow, deny, or
  approval-required for an operational action.
- `app.core.tool_registry` remains the only registry exposed to runtime agents.
- `workforce/gateway/AgentGateway` is not used for production extension work.
- Endpoint, credentials, and registration state are resolved for the current
  workspace at invocation time; no extension closure may retain another
  workspace's configuration.
- A denied or approval-required request never reaches MCP `tools/call`.
- Extension calls produce the same governance/audit behavior as native runtime
  tool calls. Phase B does not reimplement the Phase 3 pipeline.

## Data model

Add nullable `capabilities_jsonb` to `ExtensionRegistration` through an
additive Alembic migration. It contains the last successful per-workspace
discovery snapshot:

```json
{
  "provider": "mcp",
  "endpoint_config": {"endpoint": "https://connector.example/rpc"},
  "capabilities": [{
    "capability_id": "com.cosa.example:search",
    "name": "search",
    "description": "Search records",
    "input_schema": {"type": "object"},
    "output_schema": null,
    "endpoint_config": {"endpoint": "https://connector.example/rpc"}
  }]
}
```

`manifest_jsonb` remains declarative extension metadata and is not overwritten
by discovery. Installing or updating a manifest invalidates stale capabilities;
only discovery stores a new snapshot. A missing snapshot is fail-closed: the
capability is not eligible or offered.

## Contracts and execution flow

`DiscoveredCapability` gains `endpoint_config: dict`. `ConnectorProvider.invoke`
becomes `invoke(scope, capability, arguments)`, so MCP receives the exact tool
name and endpoint configuration selected for this workspace.

```text
request + server-derived ExecutionScope
  -> eligible snapshot lookup (workspace scoped)
  -> canonical ToolSpec selection
  -> dispatch_tool_call / GovernanceKernel
  -> connector dispatcher + CapabilityBridge
  -> registration re-lookup by scope.workspace_id
  -> MCPProvider.tools/call
  -> existing output/audit result path
```

The connector dispatcher receives the already-derived request scope and must
not accept workspace, user, registration, endpoint, or approval values from
model arguments. `CapabilityBridge` converts the existing governance decision
to the existing result statuses; it does not use a `.status` field or await the
synchronous kernel.

The runtime entrypoint must pass the successful governance decision into the
connector dispatcher. If `ToolInvocationService` is invoked independently, it
owns one policy evaluation; when it is called after `dispatch_tool_call`, it
receives the existing decision and must not evaluate policy a second time.

## Dynamic canonical ToolSpecs

`register_extension_tools` moves out of the `AgentGateway` path. It registers
only capabilities that are eligible for the current server-derived scope into
`app.core.tool_registry`, with `execution_backend="connector"` and
`backend_id=extension_id`.

The registration operation is idempotent per canonical qualified name. Its
callable/dispatcher resolves `ExtensionRegistration` and `capabilities_jsonb`
again at call time using `scope.workspace_id`; it never captures endpoint data
or a SQLAlchemy session. Disabled, unhealthy, absent, stale, or scope-ineligible
registrations fail closed.

Toolset construction, not process startup, triggers registration. The runtime
and any schema-producing path invoke it using the request's workspace and
scope, then call the normal `resolve_toolset` filtering before exposing schemas.

## Registry and API

`ExtensionRegistry.enable(db, workspace_id, extension_id)` becomes the sole
state transition for enablement. It clears the disabled reason and rejects an
unknown registration. The router delegates both enable and disable mutations to
registry methods, after its existing authorization dependency.

Discovery is an explicit server-side lifecycle operation. It validates the
manifest/provider, runs MCP `initialize`, `notifications/initialized`, and
`tools/list`, writes `capabilities_jsonb` only on success, and records a safe
health failure on transport/protocol failure. It never exposes endpoint config,
credentials, raw provider errors, or secrets to a model/UI surface.

## Profile composition

`ProfileCompositionService` receives repository dependencies explicitly. It
uses `resolve_eligible_capabilities` for extension tool IDs and profile grants
for native tools. It reports deterministic exclusion reasons. This phase only
returns activated extension-tool capability identifiers; `active_skill_versions`
remains untouched until the separate skill-lifecycle audit.

## Tests and acceptance

Tests are written red-green in layers:

1. Contract/unit tests for discovery snapshot persistence, `tools/call`,
   protocol/transport errors, enable transition, scope eligibility, and dynamic
   registration idempotence.
2. Runtime dispatch tests verify one governance decision, no provider invocation
   for deny/approval, and workspace re-resolution instead of closure capture.
3. Opt-in PostgreSQL E2E creates an extension registration and a fake MCP HTTP
   server, then executes `eligible -> ToolSpec -> dispatch_tool_call ->
   tools/call`. It asserts an `AgentToolCall` audit row and verifies that a
   tampered offering/workspace argument cannot select another registration.

Phase B is accepted only when an allowed capability calls MCP once, a denied or
approval-required capability calls MCP zero times, disabled/secret-unavailable
capabilities are absent from the offered toolset, and all changes preserve the
current native-tool behavior.

## Out of scope

- Arbitrary third-party or model-supplied extension code.
- Dynamic skill execution/version promotion.
- Workflow node execution changes beyond consuming the canonical tool path.
- Executor bridge and subagent delegation (Phase C).
- Replacing the legacy invocation pipeline globally (Phase 3 follow-up).
