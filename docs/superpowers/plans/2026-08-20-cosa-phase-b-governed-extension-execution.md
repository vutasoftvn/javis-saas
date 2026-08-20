# COSA Phase B Governed Extension Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a first-party MCP extension discoverable and executable through COSA's canonical tool registry and governance boundary.

**Architecture:** Persist each workspace's discovery snapshot in `ExtensionRegistration.capabilities_jsonb`, while retaining `manifest_jsonb` as declarative metadata. Register eligible extension capabilities as canonical `ToolSpec`s, resolve the registration again at call time from server-derived scope, and dispatch `tools/call` only after exactly one `GovernanceKernel` decision.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy/Alembic, Pydantic v2, pytest/pytest-asyncio, httpx.

**Spec:** `docs/superpowers/specs/2026-08-20-cosa-phase-b-governed-extension-execution-design.md`

## Global Constraints

- Do not use `workforce/gateway/AgentGateway` for any production extension behavior.
- Do not add an agent runtime, tool registry, policy vocabulary, or approval service.
- `GovernanceKernel` is the only allow/deny/approval authority; an extension call must be evaluated exactly once.
- Resolve registration, endpoint configuration, and capability snapshot from `scope.workspace_id` at invocation time; never capture a workspace config or database session in a global `ToolSpec` closure.
- Deny and approval-required decisions call MCP zero times.
- `manifest_jsonb` is declarative; discovery data is stored only in `capabilities_jsonb`.
- Discovery and offered-tool resolution fail closed when a registration is disabled, unhealthy, lacks a snapshot, lacks required secrets, or is outside the request scope.
- Preserve native tool behavior and keep dynamic skills/workflow-node execution/subagent delegation out of scope.

---

## File Structure

| File | Responsibility |
|---|---|
| `backend/alembic/versions/b1e01c5a0001_extension_capability_snapshots.py` | Add nullable `capabilities_jsonb` to extension registrations. |
| `backend/app/workforce/extensions/models.py` | Expose the persisted discovery snapshot. |
| `backend/app/workforce/extensions/manifest.py` | Validate first-party MCP provider configuration. |
| `backend/app/workforce/extensions/seams.py` | Define capability endpoint metadata and provider invocation contract. |
| `backend/app/workforce/extensions/mcp_provider.py` | Perform MCP discovery and `tools/call`. |
| `backend/app/workforce/extensions/registry.py` | Own install, discovery-snapshot, enable, disable, and runtime lookup lifecycle. |
| `backend/app/workforce/extensions/eligibility.py` | Filter persisted capabilities by status, scope, and secret readiness. |
| `backend/app/workforce/extensions/capability_bridge.py` | Convert one canonical governance decision into connector dispatch. |
| `backend/app/workforce/extensions/tool_registration.py` | Register idempotent canonical connector `ToolSpec`s and resolve them at execution time. |
| `backend/app/workforce/tools/invocation/service.py` | Dispatch connector backends without a second policy evaluation. |
| `backend/app/workforce/tools/invocation/contracts.py` | Carry optional pre-evaluated governance decision through the invocation path. |
| `backend/app/workforce/extensions/router.py` | Delegate enable/disable/discovery lifecycle actions to `ExtensionRegistry`. |
| `backend/app/workforce/composition/service.py` | Resolve extension tool visibility from real eligibility. |
| `backend/app/tests/extensions/*` | Contract, lifecycle, eligibility, bridge, and registration regression tests. |
| `backend/app/tests/agents/test_extension_mcp_governance_e2e.py` | Opt-in real-Postgres governed MCP E2E. |

---

### Task 1: Persist and validate workspace capability snapshots

**Files:**
- Create: `backend/alembic/versions/b1e01c5a0001_extension_capability_snapshots.py`
- Modify: `backend/app/workforce/extensions/models.py`
- Modify: `backend/app/workforce/extensions/manifest.py`
- Modify: `backend/app/tests/extensions/test_extension_registry.py`

**Interfaces:**
- Produces `ExtensionRegistration.capabilities_jsonb: dict | None`.
- Produces `ExtensionManifest.provider_type: Literal["mcp"]` and `provider_config: MCPProviderConfig`.

- [ ] **Step 1: Write failing model/manifest tests**

```python
def test_install_accepts_first_party_mcp_provider_config(session):
    registration = ExtensionRegistry().install(session, 1, {
        "extension_id": "com.cosa.crm", "version": "1.0.0", "compatibility": ">=1",
        "trust_level": "first_party", "owner": "cosa", "capabilities": (),
        "required_permissions": (), "required_secret_refs": (),
        "supported_scope_levels": ("company",), "health_check": {"type": "mcp"},
        "disable_behavior": "block_new_calls_preserve_history",
        "provider_type": "mcp", "provider_config": {"endpoint": "https://mcp.test/rpc"},
    })
    assert registration.capabilities_jsonb is None
    assert registration.manifest_jsonb["provider_config"]["endpoint"] == "https://mcp.test/rpc"
```

- [ ] **Step 2: Run the targeted test to verify RED**

Run: `cd backend && ./.venv/bin/python -m pytest app/tests/extensions/test_extension_registry.py::test_install_accepts_first_party_mcp_provider_config -q`

Expected: FAIL because `ExtensionManifest` rejects `provider_type` and `provider_config`.

- [ ] **Step 3: Add the additive migration and validated fields**

```python
# b1e01c5a0001_extension_capability_snapshots.py
revision = "b1e01c5a0001"
down_revision = "ad6a74ebb1c7"

# upgrade
op.add_column("extension_registrations", sa.Column("capabilities_jsonb", sa.JSON(), nullable=True))

# manifest.py
class MCPProviderConfig(BaseModel):
    endpoint: str

class ExtensionManifest(BaseModel):
    # existing fields remain unchanged
    provider_type: Literal["mcp"]
    provider_config: MCPProviderConfig
```

Add `capabilities_jsonb = Column(JSON, nullable=True)` to the model. In `install`, set
`registration.capabilities_jsonb = None` whenever the manifest version or provider
configuration changes.

- [ ] **Step 4: Run model/manifest tests to verify GREEN**

Run: `cd backend && ./.venv/bin/python -m pytest app/tests/extensions/test_extension_registry.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the schema boundary**

```bash
git add backend/alembic/versions backend/app/workforce/extensions/{models.py,manifest.py,registry.py} backend/app/tests/extensions/test_extension_registry.py
git commit -m "feat: persist extension capability snapshots"
```

### Task 2: Make MCP discovery and invocation a complete provider contract

**Files:**
- Modify: `backend/app/workforce/extensions/seams.py`
- Modify: `backend/app/workforce/extensions/mcp_provider.py`
- Modify: `backend/app/tests/extensions/test_mcp_provider.py`

**Interfaces:**
- `DiscoveredCapability(..., endpoint_config: dict)`.
- `ConnectorProvider.invoke(scope, capability: DiscoveredCapability, arguments: dict) -> ProviderResult`.
- `MCPProvider.invoke` sends JSON-RPC `tools/call` with `{"name": capability.name, "arguments": arguments}`.

- [ ] **Step 1: Write failing `tools/call` tests**

```python
@pytest.mark.asyncio
async def test_mcp_provider_calls_discovered_tool(monkeypatch, scope, config):
    provider, requests = configured_mcp_provider(monkeypatch, tools_call_result={"content": [{"type": "text", "text": "ok"}]})
    capability = DiscoveredCapability(
        capability_id="com.cosa.crm:search", name="search", endpoint_config=config,
    )
    result = await provider.invoke(scope, capability, {"query": "Ada"})
    assert result.status == "success"
    assert requests[-1]["method"] == "tools/call"
    assert requests[-1]["params"] == {"name": "search", "arguments": {"query": "Ada"}}
```

- [ ] **Step 2: Run to verify RED**

Run: `cd backend && ./.venv/bin/python -m pytest app/tests/extensions/test_mcp_provider.py::test_mcp_provider_calls_discovered_tool -q`

Expected: FAIL because the current invoke signature accepts an ID and raises `NotImplementedError`.

- [ ] **Step 3: Implement the contract without hidden config lookup**

```python
class DiscoveredCapability(BaseModel):
    capability_id: str
    name: str
    description: str | None = None
    input_schema: dict | None = None
    output_schema: dict | None = None
    endpoint_config: dict = Field(default_factory=dict)

async def invoke(self, scope, capability, arguments):
    endpoint = capability.endpoint_config.get("endpoint")
    if not endpoint:
        raise ProviderUnavailableError("Missing MCP endpoint configuration")
    payload = {"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": "tools/call",
               "params": {"name": capability.name, "arguments": arguments}}
    # POST, reject non-200 and JSON-RPC error; return ProviderResult(status="success", result=result)
```

Populate `endpoint_config` during discovery from the validated provider configuration. Do not return raw response data for an MCP JSON-RPC error; raise `ProviderProtocolError`.

- [ ] **Step 4: Run provider tests to verify GREEN**

Run: `cd backend && ./.venv/bin/python -m pytest app/tests/extensions/test_mcp_provider.py app/tests/extensions/test_seam_contracts.py -q`

Expected: PASS, including existing initialize/tools-list and transport-error cases.

- [ ] **Step 5: Commit the provider contract**

```bash
git add backend/app/workforce/extensions/{seams.py,mcp_provider.py} backend/app/tests/extensions/test_mcp_provider.py
git commit -m "feat: invoke discovered MCP capabilities"
```

### Task 3: Own extension state and discovery snapshot lifecycle in the registry

**Files:**
- Modify: `backend/app/workforce/extensions/registry.py`
- Modify: `backend/app/workforce/extensions/router.py`
- Modify: `backend/app/tests/extensions/test_extension_registry.py`

**Interfaces:**
- `ExtensionRegistry.enable(db, workspace_id, extension_id) -> ExtensionRegistration`.
- `ExtensionRegistry.record_discovery(db, workspace_id, extension_id, capabilities) -> ExtensionRegistration`.
- `ExtensionRegistry.get_capability(db, workspace_id, capability_id) -> DiscoveredCapability | None`.

- [ ] **Step 1: Write failing lifecycle tests**

```python
def test_enable_clears_disabled_reason(session, installed_registration):
    installed_registration.status = "disabled"
    installed_registration.disabled_reason = "operator disabled"
    session.commit()
    enabled = ExtensionRegistry().enable(session, installed_registration.workspace_id, installed_registration.extension_id)
    assert enabled.status == "enabled"
    assert enabled.disabled_reason is None

def test_record_discovery_keeps_manifest_and_stores_snapshot(session, installed_registration):
    manifest_before = dict(installed_registration.manifest_jsonb)
    saved = ExtensionRegistry().record_discovery(session, 1, "com.cosa.crm", [
        DiscoveredCapability(capability_id="com.cosa.crm:search", name="search", endpoint_config={"endpoint": "https://mcp.test/rpc"})
    ])
    assert saved.manifest_jsonb == manifest_before
    assert saved.capabilities_jsonb["capabilities"][0]["name"] == "search"
```

- [ ] **Step 2: Run to verify RED**

Run: `cd backend && ./.venv/bin/python -m pytest app/tests/extensions/test_extension_registry.py -q`

Expected: FAIL because `enable` and `record_discovery` do not exist.

- [ ] **Step 3: Implement registry transitions and route delegation**

`enable` raises `LookupError` for an absent registration and commits only the enabled state. `record_discovery` serializes Pydantic capabilities with `model_dump(mode="json")`, sets `status="enabled"`, writes safe health metadata, and commits atomically. The router must call `registry.enable` or `registry.disable`; remove direct `reg.status` mutation. Add an authenticated discovery endpoint that loads the registration manifest, calls `MCPProvider.discover`, and calls `record_discovery` only after success.

- [ ] **Step 4: Run lifecycle and router tests to verify GREEN**

Run: `cd backend && ./.venv/bin/python -m pytest app/tests/extensions/test_extension_registry.py app/tests/extensions/test_plugin_host_facade.py -q`

Expected: PASS.

- [ ] **Step 5: Commit lifecycle changes**

```bash
git add backend/app/workforce/extensions/{registry.py,router.py} backend/app/tests/extensions/test_extension_registry.py
git commit -m "feat: manage extension discovery snapshots"
```

### Task 4: Derive eligibility from persisted capability snapshots

**Files:**
- Modify: `backend/app/workforce/extensions/eligibility.py`
- Modify: `backend/app/tests/extensions/test_extension_eligibility.py`

**Interfaces:**
- `EligibleCapability` gains `extension_id`, `input_schema`, `output_schema`, and `required_secret_refs`.
- `resolve_eligible_capabilities(db, scope)` returns only persisted discovered capabilities, with explicit non-eligible reasons for scope and secrets.

- [ ] **Step 1: Write failing snapshot and fail-closed tests**

```python
def test_eligibility_uses_discovered_snapshot_not_manifest(session, enabled_registration, scope):
    enabled_registration.capabilities_jsonb = {"capabilities": [{
        "capability_id": "com.cosa.crm:search", "name": "search",
        "endpoint_config": {"endpoint": "https://mcp.test/rpc"}, "input_schema": {"type": "object"},
    }]}
    session.commit()
    assert [c.capability_id for c in resolve_eligible_capabilities(session, scope)] == ["com.cosa.crm:search"]

def test_eligibility_is_empty_without_discovery_snapshot(session, enabled_registration, scope):
    enabled_registration.capabilities_jsonb = None
    session.commit()
    assert resolve_eligible_capabilities(session, scope) == ()
```

- [ ] **Step 2: Run to verify RED**

Run: `cd backend && ./.venv/bin/python -m pytest app/tests/extensions/test_extension_eligibility.py -q`

Expected: FAIL because current eligibility reads `manifest_jsonb["capabilities"]`.

- [ ] **Step 3: Implement snapshot-first eligibility**

Read only `reg.capabilities_jsonb["capabilities"]` after confirming an enabled, healthy registration. Continue using `manifest_jsonb` only for supported-scope and required-secret metadata. Build returned capability metadata from the stored snapshot and do not synthesize a capability from manifest declarations.

- [ ] **Step 4: Run eligibility tests to verify GREEN**

Run: `cd backend && ./.venv/bin/python -m pytest app/tests/extensions/test_extension_eligibility.py -q`

Expected: PASS.

- [ ] **Step 5: Commit eligibility changes**

```bash
git add backend/app/workforce/extensions/eligibility.py backend/app/tests/extensions/test_extension_eligibility.py
git commit -m "feat: resolve extension eligibility from discovery snapshots"
```

### Task 5: Register and dispatch canonical connector ToolSpecs once-governed

**Files:**
- Create: `backend/app/workforce/extensions/tool_registration.py`
- Modify: `backend/app/workforce/extensions/capability_bridge.py`
- Modify: `backend/app/workforce/tools/invocation/contracts.py`
- Modify: `backend/app/workforce/tools/invocation/service.py`
- Modify: `backend/app/workforce/tools/auto_register.py`
- Modify: `backend/app/tests/extensions/test_mcp_governance_bridge.py`
- Create: `backend/app/tests/extensions/test_extension_tool_registration.py`

**Interfaces:**
- `register_extension_tools(db: Session, scope: ExecutionScope) -> list[ToolSpec]`.
- `CapabilityBridge.invoke(db, scope, request, run_id, capability, provider, decision=None) -> ProviderResult | dict`.
- `ToolInvocationRequest.governance_decision: GovernanceDecision | None = None`.

- [ ] **Step 1: Write failing tenant and governance tests**

```python
@pytest.mark.asyncio
async def test_denied_connector_never_invokes_provider(session, denied_request, capability, provider):
    result = await CapabilityBridge().invoke(session, denied_scope, denied_request, None, capability, provider)
    assert result["status"] == "blocked"
    provider.invoke.assert_not_awaited()

def test_registration_is_idempotent_and_does_not_capture_workspace_endpoint(session, scope_a, scope_b):
    specs_a = register_extension_tools(session, scope_a)
    specs_b = register_extension_tools(session, scope_b)
    assert len({spec.qualified_name for spec in specs_a + specs_b}) == len(specs_a + specs_b)
    assert all(spec.execution_backend == "connector" for spec in specs_a)
```

- [ ] **Step 2: Run to verify RED**

Run: `cd backend && ./.venv/bin/python -m pytest app/tests/extensions/test_mcp_governance_bridge.py app/tests/extensions/test_extension_tool_registration.py -q`

Expected: FAIL because bridge has the wrong asynchronous kernel call and no canonical registration module exists.

- [ ] **Step 3: Implement canonical registration and one-decision dispatch**

Create `tool_registration.py`. For each eligible capability, create a `ToolSpec` with a stable namespace derived from `extension_id` (replace non-alphanumeric characters with `_`), `execution_backend="connector"`, `backend_id=extension_id`, schemas from the snapshot, and metadata from the manifest. Use `app.core.tool_registry.register` only if the qualified name is absent or semantically identical.

Extend `ToolInvocationRequest` with an optional `governance_decision`. In `ToolInvocationService.invoke`, call `PolicyGate` only when it is `None`; otherwise use the supplied decision and dispatch it. Add a connector branch that resolves the persisted capability by workspace and calls `CapabilityBridge`. `CapabilityBridge` calls the synchronous kernel only when no decision is supplied, branches on `PolicyAction`, and calls `MCPProvider.invoke(scope, capability, arguments)` only for allow. Remove the no-op `register_extension_tools` from `auto_register.py`; do not import `AgentGateway` there.

- [ ] **Step 4: Run dispatch regression suites to verify GREEN**

Run: `cd backend && ./.venv/bin/python -m pytest app/tests/extensions/test_mcp_governance_bridge.py app/tests/extensions/test_extension_tool_registration.py app/tests/tools/test_invocation_service.py app/tests/agents/test_deepseek_harness_tool_bridge.py -q`

Expected: PASS; native dispatch behavior remains unchanged.

- [ ] **Step 5: Commit canonical dispatch**

```bash
git add backend/app/workforce/extensions/{tool_registration.py,capability_bridge.py} backend/app/workforce/tools/{auto_register.py,invocation/contracts.py,invocation/service.py} backend/app/tests/extensions/{test_mcp_governance_bridge.py,test_extension_tool_registration.py}
git commit -m "feat: dispatch extension tools through canonical governance"
```

### Task 6: Resolve profile extension tools from eligibility

**Files:**
- Modify: `backend/app/workforce/composition/service.py`
- Modify: `backend/app/tests/workforce/test_composition_service.py`
- Modify: `backend/app/tests/workforce/test_composition_contracts.py`

**Interfaces:**
- `ProfileCompositionService(extension_registry: ExtensionRegistry)`.
- `resolve(profile, scope, db) -> ResolvedProfile`.

- [ ] **Step 1: Write failing composition tests**

```python
def test_profile_exposes_only_eligible_extension_tool(session, profile, scope):
    profile.tools = ["ext.com_cosa_crm_search"]
    resolved = ProfileCompositionService().resolve(profile, scope, session)
    assert resolved.visible_tool_ids == ["ext.com_cosa_crm_search"]

def test_profile_explains_secret_unavailable_extension(session, profile, scope):
    resolved = ProfileCompositionService().resolve(profile, scope, session)
    assert any(item.reason_code == "SECRET_UNAVAILABLE" for item in resolved.explanations)
```

- [ ] **Step 2: Run to verify RED**

Run: `cd backend && ./.venv/bin/python -m pytest app/tests/workforce/test_composition_service.py app/tests/workforce/test_composition_contracts.py -q`

Expected: FAIL because composition assumes every extension is disabled and only special-cases `crm.read`.

- [ ] **Step 3: Implement deterministic eligibility lookup**

Construct an eligible-capability index from `resolve_eligible_capabilities(db, scope)`. Map profile extension identifiers to canonical registered extension tool IDs and include only eligible entries. For ineligible entries, carry the resolver reason code into `ProfileExplanation`. For native tools, replace the `crm.read` literal with a grants-to-tool metadata lookup. Leave `active_skill_versions` empty and document that the skill audit remains separate.

- [ ] **Step 4: Run composition tests to verify GREEN**

Run: `cd backend && ./.venv/bin/python -m pytest app/tests/workforce/test_composition_service.py app/tests/workforce/test_composition_contracts.py app/tests/workforce/test_composition_api.py -q`

Expected: PASS.

- [ ] **Step 5: Commit composition integration**

```bash
git add backend/app/workforce/composition/service.py backend/app/tests/workforce/test_composition_{service,contracts}.py
git commit -m "feat: compose profile tools from extension eligibility"
```

### Task 7: Prove governed MCP execution against real persistence

**Files:**
- Create: `backend/app/tests/agents/test_extension_mcp_governance_e2e.py`
- Modify: `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`

**Interfaces:**
- E2E uses `RUN_DB_INTEGRATION=1`, a real `SessionLocal`, `dispatch_tool_call`, and a local fake MCP HTTP server.

- [ ] **Step 1: Write the opt-in failing E2E test**

```python
@pytest.mark.asyncio
async def test_allowed_extension_call_is_audited_and_calls_mcp_once(db_ctx, fake_mcp_server):
    scope, request, registration = install_discovered_extension(db_ctx, fake_mcp_server.url)
    register_extension_tools(db_ctx, scope)
    result = await dispatch_tool_call(db_ctx, request, "com_cosa_crm_search", {"query": "Ada"}, run_id=request.parent_run_id)
    assert result == {"matches": ["Ada"]}
    assert fake_mcp_server.calls == [{"method": "tools/call", "params": {"name": "search", "arguments": {"query": "Ada"}}}]
    assert db_ctx.query(AgentToolCall).filter_by(tool_name="com_cosa_crm.search").count() == 1
```

Add two companion tests: an approval-required `ToolSpec` returns awaiting approval with no MCP calls, and a capability from workspace B cannot be found when scope/request belongs to workspace A.

- [ ] **Step 2: Run to verify RED**

Run: `cd backend && RUN_DB_INTEGRATION=1 ./.venv/bin/python -m pytest app/tests/agents/test_extension_mcp_governance_e2e.py -q`

Expected: FAIL before Task 5 behavior is complete; if no migrated Postgres is available, pytest skips and the executor must record that E2E evidence is unavailable.

- [ ] **Step 3: Finish only missing integration wiring revealed by E2E**

Use the failure to wire registration into request-time toolset assembly. Do not add alternate dispatch or policy paths. Ensure the E2E fake server observes exactly one `tools/call` only after allow and that its endpoint is obtained from the workspace A snapshot.

- [ ] **Step 4: Run full Phase B verification**

Run:

```bash
cd backend
./.venv/bin/python -m pytest \
  app/tests/extensions \
  app/tests/workforce/test_composition_service.py \
  app/tests/workforce/test_composition_contracts.py \
  app/tests/tools/test_invocation_service.py \
  app/tests/agents/test_deepseek_harness_tool_bridge.py -q
RUN_DB_INTEGRATION=1 ./.venv/bin/python -m pytest app/tests/agents/test_extension_mcp_governance_e2e.py -q
```

Expected: focused suite passes; E2E passes with migrated Postgres or reports an explicit skip.

- [ ] **Step 5: Update ownership map and commit**

Add `workforce/extensions/tool_registration.py` as canonical extension metadata/connector registration and state that `AgentGateway` is not a production dependency. Then commit:

```bash
git add backend/app/tests/agents/test_extension_mcp_governance_e2e.py docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md
git commit -m "test: verify governed MCP extension execution end to end"
```

## Final Verification

- [ ] Run `git diff --check`.
- [ ] Run `git status --short` and preserve unrelated worktree changes.
- [ ] Confirm each accepted connector tool has an endpoint snapshot, canonical `ToolSpec`, one governance decision, and one audit result.
- [ ] Confirm no production extension code imports or instantiates `AgentGateway`.
- [ ] Confirm disabled, secret-unavailable, scope-mismatched, denied, and approval-required cases never call MCP.
