# COSA Extension Registry & Governance

The Extension Registry is the central authority for external MCP extensions in COSA OS.

## 1. Registry Schema
The `ExtensionRegistration` table stores the state of installed extensions per workspace:
- `workspace_id`: The owning workspace.
- `extension_id`: The unique domain-style ID (e.g., `com.cosa.mcp.github`).
- `status`: Current status (`installed`, `enabled`, `disabled`, `unhealthy`).
- `manifest_jsonb`: Validated `ExtensionManifest` describing required scopes, secrets, and capabilities.

## 2. Scope Resolution Rules
The `eligibility.py` module strictly filters which capabilities are eligible for execution:
1. **Status**: `disabled` or `unhealthy` extensions expose no capabilities.
2. **Scope**: The `ExecutionScope` must match the `supported_scope_levels` in the manifest.
3. **Secrets**: Required secrets listed in `required_secret_refs` must exist in `WorkspaceSecret`.

If any check fails, the capability is flagged as ineligible with a specific `reason_code`.

## 3. ConnectorProvider Extension Boundary
The `CapabilityBridge` enforces governance before invoking extensions.
When a capability is invoked:
1. `GovernanceKernel.evaluate_and_audit_tool_call()` evaluates the request.
2. If `denied` or `approval_required`, the invocation is blocked.
3. If allowed, `MCPProvider.invoke()` dispatches the JSON-RPC request to the extension endpoint.
