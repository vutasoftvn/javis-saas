# COSA Phase 2 Governed Extension Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable reviewed first-party plugins, tools, skills, connectors, and executors through a governed metadata registry without adding a privileged extension execution path.

**Architecture:** The Extension Registry owns manifests, installation state, enablement, secret readiness and health projections; it never imports or calls extension code. Capability execution remains with the canonical provider seam and, in Phase 3, the unified Tool Invocation Pipeline; until then every MCP call must use the existing `GovernanceKernel`/registered-tool dispatch boundary. MCP is a `ConnectorProvider`, not a special plugin channel.

**Tech Stack:** Python, FastAPI, SQLAlchemy/Alembic PostgreSQL JSONB, Pydantic, httpx, pytest, Flutter/GetX.

**Spec:** `docs/superpowers/plans/2026-08-20-cosa-extensible-harness-visual-workflows-rebuild.md` Phase 2; `docs/architecture/COSA_HARNESS_CONTRIBUTOR_EXTENSION_MAP.md`; `docs/superpowers/plans/2026-08-20-cosa-phase1-company-portfolio-scope.md`.

## Global Constraints

- `ExecutionScope` from Phase 1 is mandatory for all extension-facing capability resolution; UI scope is never authority.
- `PluginHost` becomes a compatibility facade only. It must not execute plugin actions or make arbitrary HTTP calls.
- No extension runs user/model-supplied Python, JavaScript, shell, Docker image, or dynamic server code.
- Only reviewed first-party package manifests with `trust_level == "first_party"` can be installed in Phase 2.
- A manifest may expose capability metadata but no secret value, callback, Python import path, policy decision, or executable payload to model/UI clients.
- A disabled extension, unhealthy extension, unsupported scope, or missing required secret is ineligible for new calls and workflow-palette visibility; historical records remain readable.
- Canonical seams live under `backend/app/workforce`; do not add production code to root scaffolds or `backend/agent_runtime/runtime`.
- Do not build a plugin marketplace, dynamic plugin installer, workflow graph compiler, or duplicate policy engine.

---

## Stable contracts

```python
class ExtensionManifest(BaseModel):
    extension_id: str                 # reverse-DNS, e.g. com.cosa.mcp.github
    version: str                      # PEP 440
    compatibility: str                # COSA version range
    trust_level: Literal["first_party"]
    owner: str
    capabilities: tuple[CapabilityManifest, ...]
    required_permissions: tuple[str, ...]
    required_secret_refs: tuple[str, ...]
    supported_scope_levels: tuple[Literal["company", "operating_unit", "offering", "initiative"], ...]
    health_check: HealthCheckManifest
    disable_behavior: Literal["block_new_calls_preserve_history"]

class ExtensionRegistration(Base):
    workspace_id: int
    extension_id: str
    version: str
    status: Literal["installed", "enabled", "disabled", "unhealthy"]
    disabled_reason: str | None
    manifest_jsonb: dict
    health_jsonb: dict
```

```text
extension manifest -> validate -> registry persistence -> eligibility resolver
  -> provider-specific discovery/dispatch -> GovernanceKernel -> audit/event
```

### Task 1: Define seam contracts and contract-test matrix

**Files:**
- Create: `backend/app/workforce/extensions/seams.py`
- Create: `backend/app/workforce/extensions/contracts.py`
- Create: `backend/app/tests/extensions/test_seam_contracts.py`
- Create: `docs/architecture/COSA_HARNESS_SEAM_CATALOG.md`

**Produces:** Protocols for `ModelProvider`, `ToolBackend`, `ConnectorProvider`, `ExecutorProvider`, `SandboxProvider`, `KnowledgeProvider`, `EventStore`, and `RuntimeAdapter`; one reusable contract suite per seam.

- [ ] **Step 1: Write failing contract tests**

```python
def test_connector_provider_contract_rejects_unhealthy_discovery():
    provider = FakeConnectorProvider(healthy=False)
    with pytest.raises(ProviderUnavailableError):
        asyncio.run(assert_connector_provider_contract(provider))

def test_every_seam_has_interface_provider_consumer_and_contract_entry():
    catalog = seam_catalog()
    assert set(catalog) == {"model", "tool", "connector", "executor", "sandbox", "knowledge", "event_store", "runtime"}
    assert all(item.contract_test for item in catalog.values())
```

- [ ] **Step 2: Verify RED**

Run: `cd backend && pytest app/tests/extensions/test_seam_contracts.py -q`

Expected: FAIL because seam catalog and contracts do not exist.

- [ ] **Step 3: Implement explicit protocols**

Define typed methods: `ConnectorProvider.discover(scope, config) -> tuple[DiscoveredCapability, ...]`, `ConnectorProvider.invoke(scope, capability_id, arguments) -> ProviderResult`, and `health(scope) -> ProviderHealth`. The other seams use the equivalent `health`, capability enumeration, and typed operation methods. `contracts.py` invokes only fake providers; it never contacts a real network endpoint.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && pytest app/tests/extensions/test_seam_contracts.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/workforce/extensions backend/app/tests/extensions docs/architecture/COSA_HARNESS_SEAM_CATALOG.md
git commit -m "feat: define governed harness seam contracts"
```

### Task 2: Add manifest validation and registry persistence

**Files:**
- Create: `backend/app/workforce/extensions/models.py`
- Create: `backend/app/workforce/extensions/manifest.py`
- Create: `backend/app/workforce/extensions/registry.py`
- Modify: `backend/app/db/base.py`
- Create: `backend/alembic/versions/v13_060_extension_registry.py`
- Create: `backend/app/tests/extensions/test_extension_registry.py`

**Produces:** immutable validated manifest data and workspace-scoped registrations.

- [ ] **Step 1: Write failing tests**

```python
def test_registry_rejects_non_first_party_manifest(db):
    with pytest.raises(ManifestValidationError, match="first_party"):
        registry.install(db, workspace_id=101, manifest={"extension_id": "org.x", "trust_level": "community"})

def test_registry_preserves_manifest_version_when_disabled(db, manifest):
    registration = registry.install(db, 101, manifest)
    registry.disable(db, 101, registration.extension_id, "maintenance")
    assert registry.get(db, 101, registration.extension_id).manifest_jsonb["version"] == manifest["version"]
```

- [ ] **Step 2: Verify RED**

Run: `cd backend && pytest app/tests/extensions/test_extension_registry.py -q`

Expected: FAIL because registry is missing.

- [ ] **Step 3: Implement schema and migration**

Create `extension_registrations` with unique `(workspace_id, extension_id)`, `manifest_jsonb`, `health_jsonb`, status, disable reason and timestamps. `ExtensionManifest` rejects unknown executable keys (`entrypoint`, `script`, `callback`, `command`) and validates reverse-DNS IDs, PEP440 versions, declared scopes, permissions, capability IDs and `disable_behavior` exactly equal to `block_new_calls_preserve_history`. Migration is additive and downgrade drops only this table.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && alembic upgrade head && pytest app/tests/extensions/test_extension_registry.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/workforce/extensions backend/app/db/base.py backend/alembic/versions/v13_060_extension_registry.py backend/app/tests/extensions
git commit -m "feat: add extension manifest registry"
```

### Task 3: Resolve extension eligibility from scope, state and secret readiness

**Files:**
- Create: `backend/app/workforce/extensions/eligibility.py`
- Create: `backend/app/tests/extensions/test_extension_eligibility.py`
- Verify: `backend/app/workforce/agents/runtime/execution_scope.py`

**Produces:** `resolve_eligible_capabilities(db, scope)` and explicit unavailable reasons.

- [ ] **Step 1: Write failing tests**

```python
def test_disabled_extension_is_not_eligible(db, enabled_scope, installed_extension):
    registry.disable(db, enabled_scope.workspace_id, installed_extension.extension_id, "operator disabled")
    assert resolve_eligible_capabilities(db, enabled_scope) == ()

def test_missing_secret_returns_reason_without_secret_value(db, enabled_scope, extension_requiring_secret):
    result = resolve_eligible_capabilities(db, enabled_scope)
    assert result[0].eligible is False
    assert result[0].reason_code == "SECRET_UNAVAILABLE"
    assert "secret" not in result[0].model_dump_json().lower()
```

- [ ] **Step 2: Verify RED**

Run: `cd backend && pytest app/tests/extensions/test_extension_eligibility.py -q`

Expected: FAIL because eligibility resolver is absent.

- [ ] **Step 3: Implement deterministic checks**

Check in this order: registration status, manifest supported scope level, secret-reference readiness through the existing secret/config service, then health status. Return an `EligibleCapability` containing capability metadata and reason code only. Do not call provider code, return a secret reference, or infer a wider scope.

- [ ] **Step 4: Verify GREEN and tampering guard**

Run: `cd backend && pytest app/tests/extensions/test_extension_eligibility.py -q`

Expected: PASS, including an Offering-scoped manifest rejected for a company-only scope request.

- [ ] **Step 5: Commit**

```bash
git add backend/app/workforce/extensions/eligibility.py backend/app/tests/extensions/test_extension_eligibility.py
git commit -m "feat: resolve governed extension eligibility"
```

### Task 4: Replace PluginHost with a registry-only compatibility facade

**Files:**
- Modify: `backend/app/integrations/channels/plugins/plugin_host.py`
- Create: `backend/app/tests/extensions/test_plugin_host_facade.py`

**Produces:** legacy callers can list eligible extension metadata; execution is refused with a migration error.

- [ ] **Step 1: Write failing tests**

```python
async def test_plugin_host_lists_registry_metadata_without_transport_calls(monkeypatch):
    host = PluginHost(workspace_id=101)
    assert (await host.load_plugins())[0]["extension_id"] == "com.cosa.mcp.github"

async def test_plugin_host_cannot_execute_plugin_directly():
    with pytest.raises(PluginExecutionRemovedError):
        await PluginHost(101).execute_plugin("github", "search", {})
```

- [ ] **Step 2: Verify RED**

Run: `cd backend && pytest app/tests/extensions/test_plugin_host_facade.py -q`

Expected: FAIL because PluginHost returns stubs.

- [ ] **Step 3: Implement facade**

Inject the registry query into `PluginHost.load_plugins()`. Map only `extension_id`, version, status, capabilities, health summary and disabled reason. Replace `execute_plugin()` success stub with `PluginExecutionRemovedError("Use registered capability dispatch")`; it must make no HTTP request.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && pytest app/tests/extensions/test_plugin_host_facade.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/integrations/channels/plugins/plugin_host.py backend/app/tests/extensions/test_plugin_host_facade.py
git commit -m "refactor: route plugin host through extension registry"
```

### Task 5: Implement MCP discovery as a ConnectorProvider

**Files:**
- Modify: `backend/app/workforce/tools/transports/mcp_adapter.py`
- Create: `backend/app/workforce/extensions/mcp_provider.py`
- Create: `backend/app/tests/extensions/test_mcp_provider.py`

**Produces:** initialize → tools/list discovery and typed `tools/call`; no simulated successful fallback.

- [ ] **Step 1: Write mocked JSON-RPC tests**

```python
async def test_mcp_provider_discovers_tools_after_initialize(respx, scope):
    respx.post("https://mcp.test/rpc").respond(json={"jsonrpc":"2.0","id":"init","result":{"protocolVersion":"2025-03-26"}})
    respx.post("https://mcp.test/rpc").respond(json={"jsonrpc":"2.0","id":"list","result":{"tools":[{"name":"search","inputSchema":{"type":"object"}}]}})
    tools = await provider.discover(scope, config)
    assert tools[0].capability_id == "com.cosa.mcp.github:search"

async def test_mcp_error_is_provider_failure_not_fake_success(respx, scope):
    respx.post("https://mcp.test/rpc").respond(status_code=503)
    with pytest.raises(ProviderUnavailableError):
        await provider.discover(scope, config)
```

- [ ] **Step 2: Verify RED**

Run: `cd backend && pytest app/tests/extensions/test_mcp_provider.py -q`

Expected: FAIL because MCP discovery does not exist.

- [ ] **Step 3: Implement JSON-RPC protocol behavior**

Send `initialize` with a generated correlation ID, validate `result.protocolVersion`, send `notifications/initialized`, then request `tools/list`. Convert each MCP tool schema to `DiscoveredCapability` with namespaced stable ID, input schema, no output schema claim when absent, and transport config stored server-side. `tools/call` must return `ProviderResult` or raise `ProviderUnavailableError`/`ProviderProtocolError`; remove the current fallback/simulated success branch.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && pytest app/tests/extensions/test_mcp_provider.py -q`

Expected: PASS, including malformed result and duplicate tool-name tests.

- [ ] **Step 5: Commit**

```bash
git add backend/app/workforce/tools/transports/mcp_adapter.py backend/app/workforce/extensions/mcp_provider.py backend/app/tests/extensions/test_mcp_provider.py
git commit -m "feat: discover MCP capabilities through connector seam"
```

### Task 6: Govern MCP registration and invocation

**Files:**
- Create: `backend/app/workforce/extensions/capability_bridge.py`
- Modify: `backend/app/workforce/tools/auto_register.py`
- Create: `backend/app/tests/extensions/test_mcp_governance_bridge.py`

**Produces:** discovered MCP capabilities are registered as tools and execute only after governance decision.

- [ ] **Step 1: Write failing non-execution tests**

```python
async def test_denied_mcp_call_never_invokes_provider(mocker, scope, capability):
    provider = mocker.AsyncMock()
    kernel = DenyKernel()
    result = await bridge.invoke(scope, capability, {"query": "x"}, kernel, provider)
    assert result.status == "denied"
    provider.invoke.assert_not_awaited()

async def test_approval_required_mcp_call_never_invokes_provider(mocker, scope, capability):
    provider = mocker.AsyncMock()
    result = await bridge.invoke(scope, capability, {"query": "x"}, RequireApprovalKernel(), provider)
    assert result.status == "approval_required"
    provider.invoke.assert_not_awaited()
```

- [ ] **Step 2: Verify RED**

Run: `cd backend && pytest app/tests/extensions/test_mcp_governance_bridge.py -q`

Expected: FAIL because capability bridge is absent.

- [ ] **Step 3: Implement bridge**

Resolve capability eligibility first, validate JSON input against discovered schema, create the canonical registered ToolSpec, and call `GovernanceKernel.evaluate_and_audit_tool_call()` before `ConnectorProvider.invoke()`. ALLOW invokes once; DENY and REQUIRE_APPROVAL return typed result with correlation ID and no provider call. Preserve the existing audit record and add no MCP-specific policy bypass.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && pytest app/tests/extensions/test_mcp_governance_bridge.py app/tests/agents/test_governance_policy_approval.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/workforce/extensions/capability_bridge.py backend/app/workforce/tools/auto_register.py backend/app/tests/extensions/test_mcp_governance_bridge.py
git commit -m "feat: govern MCP capability invocation"
```

### Task 7: Expose authorized extension Settings APIs

**Files:**
- Create: `backend/app/integrations/channels/plugins/router.py`
- Modify: `backend/app/integrations/router.py`
- Create: `backend/app/tests/extensions/test_extension_router.py`

**Produces:** list/detail/enable/disable/health endpoints; only admin/owner may mutate state.

- [ ] **Step 1: Write failing route tests**

```python
def test_member_cannot_enable_extension(client, member_auth):
    assert client.post("/api/v1/plugins/com.cosa.mcp.github/enable?workspace_id=101", headers=member_auth).status_code == 403

def test_disable_blocks_new_calls_but_returns_historical_metadata(client, owner_auth):
    assert client.post("/api/v1/plugins/com.cosa.mcp.github/disable?workspace_id=101", json={"reason":"maintenance"}, headers=owner_auth).status_code == 200
    assert client.get("/api/v1/plugins/com.cosa.mcp.github?workspace_id=101", headers=owner_auth).json()["status"] == "disabled"
```

- [ ] **Step 2: Verify RED**

Run: `cd backend && pytest app/tests/extensions/test_extension_router.py -q`

Expected: FAIL because routes do not exist.

- [ ] **Step 3: Implement routes**

Use `get_current_workspace_member`, workspace match and `authorize(member, "tool.configure")` for enable/disable. Return only safe manifest projection: capability IDs, labels, schemas, scopes, permissions, health status, disabled reason and secret readiness boolean. Never return secret reference names or raw health exception stack traces.

- [ ] **Step 4: Verify GREEN**

Run: `cd backend && pytest app/tests/extensions/test_extension_router.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/integrations/channels/plugins/router.py backend/app/integrations/router.py backend/app/tests/extensions/test_extension_router.py
git commit -m "feat: add governed extension settings API"
```

### Task 8: Build Flutter Extension Settings and palette metadata consumer

**Files:**
- Create: `frontend/lib/modules/settings/extensions/extensions_service.dart`
- Create: `frontend/lib/modules/settings/extensions/extensions_controller.dart`
- Create: `frontend/lib/modules/settings/extensions/extensions_view.dart`
- Modify: existing settings route/binding file identified by `rg -n "Settings|Connectors" frontend/lib/modules/settings`
- Modify: `frontend/lib/modules/workflows/services/workflows_service.dart`
- Create: `frontend/test/modules/settings/extensions_controller_test.dart`

**Produces:** authorized extension status UI and workflow metadata feed; no local execution.

- [ ] **Step 1: Write failing Flutter tests**

```dart
test('disabled extension is displayed but excluded from eligible palette capabilities', () async {
  final controller = ExtensionsController(service: FakeExtensionsService(disabledGithub));
  await controller.load();
  expect(controller.extensions.single.status, 'disabled');
  expect(controller.eligibleNodeMetadata, isEmpty);
});
```

- [ ] **Step 2: Verify RED**

Run: `cd frontend && flutter test test/modules/settings/extensions_controller_test.dart`

Expected: FAIL because extension module does not exist.

- [ ] **Step 3: Implement UI**

Render installed version, health, disabled reason, permissions, secret-readiness boolean and provided capability labels. Enable/disable actions call only the server API and refresh data. `WorkflowsService` consumes server-projected eligible node metadata; it does not construct nodes, inspect secrets or call MCP endpoints.

- [ ] **Step 4: Verify GREEN**

Run: `cd frontend && flutter test test/modules/settings/extensions_controller_test.dart && flutter analyze lib/modules/settings/extensions lib/modules/workflows`

Expected: PASS with no analyzer errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/modules/settings frontend/lib/modules/workflows frontend/test/modules/settings
git commit -m "feat: show governed extension settings"
```

### Task 9: Document and verify the Phase 2 vertical slice

**Files:**
- Create: `docs/architecture/COSA_PHASE2_EXTENSION_REGISTRY.md`
- Modify: `backend/app/tests/test_architectural_invariants.py`

- [ ] **Step 1: Write final invariant**

```python
def test_extension_registry_has_no_direct_plugin_execution_path():
    root = Path(__file__).resolve().parents[3]
    host = (root / "backend/app/integrations/channels/plugins/plugin_host.py").read_text()
    assert "PluginExecutionRemovedError" in host
    assert 'return {"status": "success", "result": None}' not in host
    assert (root / "backend/app/workforce/extensions/registry.py").exists()
```

- [ ] **Step 2: Verify GREEN**

Run: `cd backend && pytest app/tests/test_architectural_invariants.py app/tests/extensions -q && pytest -q`

Expected: all tests PASS, with only pre-existing skips/warnings.

- [ ] **Step 3: Document operational behavior**

Document installation/enable/disable lifecycle, first-party trust restriction, scope/secret/health eligibility reasons, MCP protocol behavior, direct-execution prohibition, audit/approval guarantees and Phase 3 handoff.

- [ ] **Step 4: Verify Flutter**

Run: `cd frontend && flutter test test/modules/settings/extensions && flutter analyze lib/modules/settings/extensions lib/modules/workflows`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/architecture/COSA_PHASE2_EXTENSION_REGISTRY.md backend/app/tests/test_architectural_invariants.py
git commit -m "docs: complete governed extension registry phase two"
```

## Acceptance checklist

- [ ] Mocked MCP server completes initialize and tools/list discovery.
- [ ] Disabled/unhealthy/missing-secret extensions expose no eligible capability for new work.
- [ ] Native and MCP operations both require governance; deny/approval has zero provider-body calls.
- [ ] Direct PluginHost execution is impossible.
- [ ] Historical extension/run/artifact metadata remains readable after disable.
- [ ] Settings and workflow consumers use server-projected metadata only.
- [ ] No user/model-supplied extension server code is accepted.
