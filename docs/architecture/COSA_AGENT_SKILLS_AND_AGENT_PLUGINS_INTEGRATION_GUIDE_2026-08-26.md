# Hướng dẫn tích hợp Skill và MCP Connector cho COSA

**Ngày:** 2026-08-26  
**Trạng thái:** Pilot — Hardening connector authorization (Wave 0) + native SkillSpec + MCP qua CapabilityGateway (Wave B). Agent Skills/Agent Plugins standards chưa áp dụng (Wave P — điều kiện khác lock).  
**Phạm vi:** `packages/agent_core`, `apps/cosa`, `services/cosa`, CapabilityGateway và executor.

---

## 1. Quyết định kiến trúc

### 1.1 Tuyên bố quyết định

COSA áp dụng **native `SkillSpec` (bereits exist) + MCP connector qua `CapabilityGateway`** trong pilot này.

**KHÔNG áp dụng Agent Skills / Agent Plugins community standards** cho đến khi:
1. Có marketplace roadmap viết tường minh và đối tác cam kết bằng văn bản → Wave P lock conditions.
2. Chứng minh setup portable `plugin.json`/`SKILL.md` lợi ích rõ ràng trên model in-repo git-source-controlled hiện tại.

**Lý do:**
- Pilot không dùng "mở" tính năng nào của cả hai chuẩn (discovery/distribution/marketplace, plugin script execution, package repository, third-party plugin installation).
- Mỗi tính năng "mở" bị tắt hoặc không wire trong vòng này (streamable-http MCP only, first-party skills, no plugin scripts, no floating refs).
- Quy tắc cơ bản (pinned SkillRef, signed capabilities, tenant isolation, approval gate) đã chức năng với infrastructure hiện tại; thêm portable manifest packaging không tạo thêm value trong pilot scope.

### 1.2 Kiến trúc thực tế

```text
┌─────────────────────────────────────────────────────────────────────┐
│ Caller (agent kernel, workflow)                                      │
├─────────────────────────────────────────────────────────────────────┤
│ CapabilityGateway.execute(GatewayExecutionRequest)                  │
│ ├─ resolve capability spec từ registry                              │
│ ├─ verify connector grant (HTTP re-check tới /cosa/connectors/assert)
│ ├─ construct target snapshot + audit                                │
│ ├─ policy evaluate (tenant + risk)                                  │
│ ├─ approval gate                                                    │
│ ├─ idempotency check                                                │
│ └─ handler execute → artifact persist + event stream                │
├─ Handler types:                                                     │
│  ├─ Built-in SkillSpec: OPERATIONS_TASK_READ, FINANCE_PAYOUT_EXECUTE
│  └─ MCP tools registered via register_mcp_tools():                  │
│     └─ mcp_tool_to_capability_spec() + async caller(tool, payload)  │
└─────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────┐
│ services/cosa (TypeScript/Encore)      │
├────────────────────────────────────────┤
│ Connector authorization lifecycle:     │
│ POST /cosa/connectors/install          │
│ POST /cosa/connectors/authorize        │
│ POST /cosa/connectors/grant            │
│ POST /cosa/connectors/assert           │ ← re-verification per-call
│ POST /cosa/connectors/revoke           │
│                                        │
│ Tenant isolation: company_id +         │
│ workspace_id trên mọi table            │
└────────────────────────────────────────┘
```

---

## 2. Baseline code đã verify — không thay đổi trong Wave 0-B

### 2.1 SkillSpec lifecycle (`packages/agent_core/skills/`)

**Không bị động trong Task 1-8.** Đã verify trước plan:

- **`contracts.py::SkillSpec`**: Định nghĩa immutable, progressive disclosure (L0 `SkillIndexEntry`, L1 `SkillSpec` với instructions).
- **`resolver.py::SkillResolver`**: Resolve `AgentSpec.pinned_skills` → yêu cầu exact version + definition_hash (chặn floating ref). Task 1-8 không sửa.
- **`publisher.py::publish_skill_spec()`**: Publish vào registry idempotent per hash; validate dependency (prompt_ref, model_policy_ref). Task 1-8 không sửa.

**Consumer:** `packages/agent_core/kernel/openai_agents_kernel.py` gọi `SkillResolver.resolve()` trước khi execution. Unchanged.

### 2.2 CapabilityRegistry pipeline (`packages/agent_core/capabilities/`)

**Không bị động.** Baseline chuẩn:

- **`registry.py::CapabilityRegistry`**: In-memory catalog, `register(spec, handler)`, `get_by_id()`, `list()`. Unchanged.
- **`gateway.py::CapabilityGateway.execute()`**: 10-bước pipeline (resolve → schema validate → target snapshot → identity → payload canonicalize → policy → approval → idempotency → execute → audit). Unchanged.
  - Exception: **Task 6 thêm connector-grant re-verification** vào step 3 (nội bộ flow, không thay signature).

### 2.3 Connector boundary (`services/cosa/storage/control-plane-schema.ts`)

**Không bị động.** Schema chuẩn:

- **`workspaceConnectorInstallations`** (id, companyId, workspaceId, connectorKey, status, installedBy, createdAt, updatedAt)
- **`connectorAuthorizations`** (id, installationId, companyId, workspaceId, principalId, secretRef, grantedScopes, state, expiresAt)
  - **Task 1 thêm** `company_id`, `workspace_id` với migration 12 (vá cross-tenant bypass).
- **`sessionConnectorGrants`** (id, companyId, workspaceId, conversationId, authorizationId, grantedBy, allowedActions, state, expiresAt, revokedAt, ...)

---

## 3. Wave 0: Hardening connector authorization & E2E test (Tasks 1-4)

### 3.1 Cross-tenant bypass vulnerability & fix

**Lỗ hổng:** `registerConnectorAuthorization()` chỉ query theo `installation_id`, không xác nhận `installation` thuộc đúng tenant (`company_id`, `workspace_id`) của caller.

**Tác động:** Tenant B có thể authorize installation của Tenant A bằng cách biết `installation_id`.

**Fix (Task 1-3):**

1. **Migration 12** (`services/cosa/migrations/12_connector_authorization_tenant_scope.up.sql`):
   - ALTER `connector_authorizations`: ADD `company_id`, `workspace_id`.
   - Backfill từ `workspace_connector_installations` join.
   - CREATE INDEX `idx_connector_authorizations_tenant`.

2. **Service hardening** (`services/cosa/services/workspace-connector.service.ts`):
   ```typescript
   async registerConnectorAuthorization(input: {
     installationId: string;
     companyId: string;
     workspaceId: string;
     // ... rest
   }): Promise<...> {
     // Validate tenant scope trước ghi
     const [installation] = await db
       .select()
       .from(workspaceConnectorInstallations)
       .where(
         and(
           eq(workspaceConnectorInstallations.id, input.installationId),
           eq(workspaceConnectorInstallations.companyId, input.companyId),
           eq(workspaceConnectorInstallations.workspaceId, input.workspaceId)
         )
       );
     if (!installation) throw Error("installation not found or cross-tenant mismatch");
     // ... ghi vào connector_authorizations với company_id, workspace_id
   }
   ```

3. **Handler** (`services/cosa/handlers/workspace-connector.handler.ts`):
   - `registerAuthorizationEndpoint`: Parse `companyId`, `workspaceId` từ request, forward tới service.
   - Validate user membership trước (reuse `validateUserMembership()`).

### 3.2 E2E test (Task 4)

**File:** `tests/apps/cosa/control_plane/test_connector_lifecycle_e2e.py`

Kiểm chứng scenarios qua real HTTP (encore run):

1. **Happy path**: Install → Authorize → Grant → Assert (ok=True) → Revoke → Assert (ok=False).
2. **Cross-tenant deny**: Tenant B cố authorize installation của Tenant A → 400+ error.
3. **Expiry**: Authorize với expiresAt quá khứ → Grant reject ("reauth_required").
4. **Scope mismatch**: Assert với requiredScope không trong grantedScopes → ok=False.
5. **Missing grant**: Assert conversation không có grant → ok=False.

**Fixture:**
- `control_plane_service`: Start `encore run` với real Postgres, migration, HTTP client.
- `_seed_tenants()`: Seed users, companies, memberships.
- Mint platform JWT (user) + worker JWT (service auth) per-test.

### 3.3 Pinning: Connector re-verification tại execution time

**Decision (Task 6):** CapabilityGateway thêm connector-grant re-verification step (không thực thi side effect nếu grant bị revoke/expire giữa scheduling và execution).

**Thực thi:**
- `GatewayExecutionRequest` có `workspace_id` + `context` (company_id, conversation_id).
- Gateway **step 8.5** (sau approval gate, trước handler execution): Call `connector_grant_resolver()` → HTTP re-check `/cosa/connectors/assert`.
- Nếu grant không hợp lệ: Return `denied` status, không gọi handler.
- Re-verification chạy trên MỌI lần `execute()`, kể cả resume sau approval được duyệt (approval không có nghĩa grant vẫn còn hiệu lực).

**Provider:** `apps/cosa/capabilities/connector_grant_client.py::ConnectorGrantHttpClient.assert_usable()`.

---

## 4. Wave B: MCP tools via CapabilityGateway (Tasks 6-8)

### 4.1 MCP tool → CapabilitySpec adapter

**File:** `packages/agent_integrations/mcp/capability_adapter.py`

```python
def mcp_tool_to_capability_spec(
    tool: dict[str, Any],
    *,
    connector_key: str,
    catalog_version: str,
    capability_id_prefix: str = "mcp",
    risk: CapabilityRisk = CapabilityRisk.MEDIUM,
) -> CapabilitySpec:
    """Convert 1 MCP tool definition ({"name", "description", "inputSchema"}) 
    to CapabilitySpec."""
    name = tool["name"]
    input_schema = tool.get("inputSchema") or {"type": "object", "properties": {}}
    schema_hash = compute_payload_hash(input_schema)
    capability_id = f"{capability_id_prefix}.{name}"
    
    return CapabilitySpec(
        id=capability_id,
        description=tool.get("description", ""),
        input_schema=input_schema,
        risk=risk,
        connector_requirements={"connector_id": connector_key},
        implementation_identity=CapabilityImplementationIdentity(
            capability_id=capability_id,
            schema_version=catalog_version,
        ),
        metadata={
            "mcp_tool_name": name,
            "mcp_source": "tools/list",
            "mcp_server_name": connector_key,
            "mcp_tool_schema_hash": schema_hash,
        },
    )

def register_mcp_tools(
    registry: CapabilityRegistry,
    tools: list[dict[str, Any]],
    caller: McpToolCaller,
    *,
    connector_key: str,
    catalog_version: str,
    capability_id_prefix: str = "mcp",
    risk: CapabilityRisk = CapabilityRisk.MEDIUM,
) -> list[str]:
    """Register multiple MCP tools into CapabilityRegistry.
    Handler only calls caller(tool_name, payload) — no side effects,
    governance/approval still via CapabilityGateway.execute()."""
    registered_ids: list[str] = []
    for tool in tools:
        spec = mcp_tool_to_capability_spec(...)
        async def handler(payload, ctx, *, _tool_name=tool["name"]):
            return await caller(_tool_name, payload)
        registry.register(spec, handler)
        registered_ids.append(spec.id)
    return registered_ids
```

**Key invariants:**
- MCP tools đăng ký vào registry giống built-in SkillSpec → cùng pipeline CapabilityGateway.
- `McpToolCaller` là async function do caller inject (phía apps/cosa) → không import SDK MCP cụ thể ở adapter layer.
- Risk mặc định MEDIUM (not LOW) vì từ external server.
- Metadata lưu mcp_tool_name, mcp_source, schema_hash.

### 4.2 Sandbox-read MCP (pilot test connector)

**File:** `apps/cosa/capabilities/sandbox_read_mcp.py`

```python
def register_sandbox_read_mcp_tools(registry: CapabilityRegistry) -> list[str]:
    """Register read-only sandbox MCP tools (Wave B/C pilot).
    Only streamable-http, read-only per pilot scope."""
    
    from mcp.client.streamable_http import streamablehttp_client
    from mcp import ClientSession
    
    async def caller(tool_name: str, payload: dict[str, Any]) -> Any:
        async with streamablehttp_client(COSA_SANDBOX_READ_MCP_URL) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, payload)
                return result.model_dump()
    
    # tools/list tĩnh cho pilot (first-party, reviewed)
    tools = [
        {
            "name": "list_sandbox_items",
            "description": "List read-only sandbox items for operations reporting.",
            "inputSchema": {"type": "object", "properties": {}},
        }
    ]
    
    return register_mcp_tools(
        registry,
        tools=tools,
        caller=caller,
        connector_key="sandbox-read",
        catalog_version="1.0.0",
    )
```

**Pilot scope:**
- 1 connector (`sandbox-read`), 1 tool (`list_sandbox_items`).
- streamable-http only.
- Read-only (no mutations).
- No async polling, no streaming, no stdio, no subprocess.

### 4.3 Connector grant re-verification & CapabilityGateway wiring

**Gateway connector_grant_resolver** (`apps/cosa/composition/agent_plane.py`):

```python
connector_grant_client = ConnectorGrantHttpClient(base_url=control_plane_url)

async def _connector_grant_resolver(connector_id: str, req):
    return await connector_grant_client.assert_usable(
        connector_id,
        company_id=req.context.get("company_id", ""),
        workspace_id=req.workspace_id or "",
        conversation_id=req.context.get("conversation_id", ""),
        action=req.capability_id,
    )

gateway = CapabilityGateway(
    registry=cap_registry,
    repository=repo,
    policy_evaluator=policy_engine.evaluate,
    governance_store=gov_store,
    connector_grant_resolver=_connector_grant_resolver,
)
```

**Behavior:**
- Every MCP tool call → `CapabilityGateway.execute()`.
- Step 3 (target resolution): Call `_connector_grant_resolver()` → HTTP `/cosa/connectors/assert`.
- `/cosa/connectors/assert` validates tenant scope + grant status + expiry + scope + action.
- If ok=False: Gateway returns denied, handler NOT invoked.
- Idempotency key ensures duplicate side-effects rejected even if caller retries.

---

## 5. Wave C: Pilot configuration

### 5.1 Environment

**Control plane (`services/cosa`):**
- `COSA_DATABASE_URL`: Postgres connection string (migration 12 applied).
- `COSA_CONNECTOR_ALLOWED_KEYS=sandbox-read`: Allowlist nằm trong code (not env), pilot chỉ allow "sandbox-read".

**Agent plane (`apps/cosa`):**
- `AGENT_CORE_DATABASE_URL`: Postgres (same control-plane DB hoặc separate).
- `COSA_CONTROL_PLANE_URL`: HTTP endpoint tới services/cosa (default `http://127.0.0.1:4001`).
- `COSA_WORKER_SERVICE_TOKEN`: JWT token dùng cho `/cosa/connectors/assert` auth.
- `COSA_SANDBOX_READ_MCP_URL`: HTTP endpoint tới sandbox-read MCP server (nếu enable).

### 5.2 Scope limits

- **Connectors per workspace:** 1 installation per (company, workspace, connector_key) tuple.
- **Tools per connector:** First-party, statically reviewed (không auto-discover from server).
- **Auth scope:** No nested scope hierarchy; grant `allowedActions` là flat list.
- **Approval:** Tenant policy decides MCP tool execution risk; coordinator can require manual approval before calling (existing governance infra).

---

## 6. Wave P: Conditions untuk mở lại Agent Skills / Agent Plugins (parked)

Tiêu chí để unlock portable `plugin.json` / `SKILL.md` / community distribution:

1. **Marketplace roadmap viết tường minh** từ COSA product team (có spec, timeline, partner commitments — không phải "maybe some day").
2. **Partner commitments bằng văn bản** (third-party plugin vendors agree to terms).
3. **First-party pilot success:** Pilot này (Wave B/C) chạy ≥3 tháng với zero security incident, zero tenant-isolation bypass.
4. **Spec review & approval:** ADR chỉ định portable manifest format, schema versioning, migration path từ in-repo git.
5. **Feature parity:** MCP discovery runtime (if_enabled), plugin script sandbox, package signing, marketplace API.
6. **Test coverage:** Cross-tenant tests, malicious plugin tests, package integrity tests, revocation cascade tests.

**Currently:** BLOCKED. Mọi tính năng "mở" tắt; pilot scope = first-party, source-controlled, reviewed by hand.

---

## 7. File-level implementation map (Tasks 1-8)

**Capability Platform & Contracts (Wave A baseline):**

| # | File | Change | Purpose |
|---|------|--------|---------|
| A1 | `packages/agent_core/contracts/capability.py` | VERIFY (not modified Tasks 1-8) | CapabilitySpec, CapabilityRisk, CapabilityImplementationIdentity definitions. |
| A2 | `packages/agent_core/contracts/__init__.py` | VERIFY (not modified) | Contract module exports. |
| A3 | `packages/agent_core/capabilities/registry.py` | VERIFY (not modified) | CapabilityRegistry, register(), get(), unchanged. |
| A4 | `packages/agent_core/capabilities/grants.py` | VERIFY (not modified) | ConnectorGrant model, verify_connector_grant() function. |
| A5 | `packages/agent_core/skills/contracts.py` | VERIFY (not modified) | SkillSpec, SkillIndexEntry definitions. |
| A6 | `packages/agent_core/skills/resolver.py` | VERIFY (not modified) | SkillResolver.resolve() for pinned skill references. |
| A7 | `packages/agent_core/registry/publisher.py` | VERIFY (not modified) | publish_skill_spec() function. |

**Control Plane Database & Schema:**

| # | File | Change | Purpose |
|---|------|--------|---------|
| DB1 | `services/cosa/storage/control-plane-schema.ts` | VERIFY (not modified Tasks 1-8) | workspaceConnectorInstallations, connectorAuthorizations, sessionConnectorGrants table definitions. |
| DB2 | `services/cosa/migrations/12_connector_authorization_tenant_scope.up.sql` | NEW | Add company_id, workspace_id to connector_authorizations; CREATE INDEX. |

**Control Plane Implementation:**

| # | File | Change | Purpose |
|---|------|--------|---------|
| CP1 | `services/cosa/services/workspace-connector.service.ts` | MODIFY | registerConnectorAuthorization(), grantConnectorToSession(), assertConnectorInvocation() — hard-check tenant scope per Migration 12. |
| CP2 | `services/cosa/handlers/workspace-connector.handler.ts` | MODIFY | Parse companyId, workspaceId from request; validate user membership; forward to tenant-scoped service methods. |
| CP3 | `services/cosa/tests/workspace-connector.test.ts` | VERIFY (not modified Tasks 1-8) | Unit tests for workspace-connector service methods. |

**Agent Platform — MCP Integration:**

| # | File | Change | Purpose |
|---|------|--------|---------|
| MP1 | `packages/agent_integrations/mcp/capability_adapter.py` | NEW | mcp_tool_to_capability_spec(), register_mcp_tools(); convert MCP tool dict → CapabilitySpec. |
| MP2 | `packages/agent_integrations/mcp/pyproject.toml` | VERIFY (mcp dependency) | Python dependencies for MCP client. |
| MP3 | `tests/agent_integrations/mcp/test_capability_adapter.py` | NEW | Unit tests for mcp_tool_to_capability_spec() and register_mcp_tools(). |

**Agent Platform — CapabilityGateway & Executor:**

| # | File | Change | Purpose |
|---|------|--------|---------|
| GW1 | `packages/agent_core/capabilities/gateway.py` | MODIFY (step 8.5) | Add connector-grant re-verification via connector_grant_resolver callback (no signature change); runs after approval gate, before handler execution. |

**COSA Composition & Pilot Implementation:**

| # | File | Change | Purpose |
|---|------|--------|---------|
| CP4 | `apps/cosa/capabilities/connector_grant_client.py` | VERIFY (not modified Tasks 1-8) | ConnectorGrantHttpClient, assert_usable() method for HTTP re-check of connector grants. |
| CP5 | `apps/cosa/capabilities/sandbox_read_mcp.py` | NEW | register_sandbox_read_mcp_tools() — 1 pilot connector (sandbox-read), 1 tool (list_sandbox_items), streamable-http only. |
| CP6 | `apps/cosa/composition/agent_plane.py` | MODIFY (build_cosa_agent_plane) | Wire ConnectorGrantHttpClient as _connector_grant_resolver for CapabilityGateway; inject into gateway init. |

**Tests & Contracts:**

| # | File | Change | Purpose |
|---|------|--------|---------|
| T1 | `tests/apps/cosa/control_plane/test_connector_lifecycle_e2e.py` | NEW | Real HTTP E2E test: install→authorize→grant→assert; cross-tenant deny, expiry, scope mismatch, revocation scenarios. |
| T2 | `tests/agent_core/contracts/test_contracts_all.py` | VERIFY (not modified Tasks 1-8) | Contract definition tests. |
| T3 | `tests/agent_core/capabilities/test_gateway_connector_grant.py` | NEW | Unit tests for CapabilityGateway step 8.5 connector-grant re-verification behavior. |
| T4 | `tests/apps/cosa/control_plane/__init__.py` | NEW | Test module init. |

**Dependency Management:**

| # | File | Change | Purpose |
|---|------|--------|---------|
| DEP1 | `packages/pyproject.toml` | VERIFY (mcp dependency) | Root Python packages dependencies; mcp client listed if Tasks 1-8 added it. |

**Wave A Baseline (NOT modified):**
- `packages/agent_core/skills/contracts.py` — SkillSpec definition.
- `packages/agent_core/skills/resolver.py` — SkillResolver for pinned skill refs.
- `packages/agent_core/registry/publisher.py` — publish_skill_spec() idempotent publish.
- `packages/agent_core/capabilities/registry.py` — CapabilityRegistry in-memory catalog.
- `packages/agent_core/capabilities/grants.py` — ConnectorGrant model (used by gateway resolver).

---

## 8. Execution flow example: MCP tool invocation

```
1. Kernel calls: gateway.execute(GatewayExecutionRequest(
     capability_id="mcp.list_sandbox_items",
     workspace_id="ws_a",
     context={"company_id": "1001", "conversation_id": "conv_a_1"},
     input_payload={},
   ))

2. CapabilityGateway.execute() — 10-step pipeline:

   Step 1: Resolve capability
   a. resolve_capability("mcp.list_sandbox_items") → CapabilitySpec from registry

   Step 2: Validate input schema
   b. validate input schema (empty payload OK for list_sandbox_items)

   Step 3: Canonicalize payload & compute payload_hash
   c. canonicalize_payload({}) + compute_payload_hash() → stable hash

   Step 4: Construct InvocationIdentity & ExecutionTargetSnapshot
   d. construct ExecutionTargetSnapshot (capability_id, connector_id, schema_hash_version)
      and InvocationIdentity (tool_call_id, run_id, capability_id, payload_hash)

   Step 4.5: Capability Readiness Check
   e. readiness_checker.check(capability_id, context) → confirm credential available

   Step 5: Idempotency Check
   f. idempotency_check: (run_id, tool_call_id, canonicalized_payload_hash)
      → atomic claim to prevent duplicate side-effects

   Step 6: Policy Evaluate
   g. invoke policy_engine.evaluate(capability_id, input_payload, context) 
      → MCP_TOOL risk assessment → PolicyOutcome (ALLOW | REQUIRE_APPROVAL | DENY)

   Step 7: Accumulate Governance
   h. governance_store: load existing governance state, accumulate current decision
      (monotonic across restart per Blueprint V2 §9.2)

   Step 8: Approval Gate Check
   i. if effective_outcome == REQUIRE_APPROVAL:
      - check approval_record status
      - if not approved: create pending approval, return waiting_approval status
      - (resume call will continue from here after human approval)

   Step 8.5: Re-verify Connector Grant (Task 6 hardening)
   j. connector_grant_resolver("sandbox-read", req):
      - HTTP POST /cosa/connectors/assert
      - body: companyId=1001, workspaceId=ws_a, conversationId=conv_a_1,
              connectorKey=sandbox-read, action=mcp.list_sandbox_items
      - response: {ok: true, secretRef: "secret://cosa-connectors/..."}
      - (runs on EVERY execute(), including resume after approval granted)
      - if ok=False: return denied, don't invoke handler

   Step 9-10: Execute Handler & Audit
   k. handler = registry.get("mcp.list_sandbox_items")
   l. handler(input_payload={}):
      - caller("list_sandbox_items", {})
      - streamable-http POST to MCP server
      - return response dict
   m. persist RunToolCallRecord (run_id, tool_call_id, status="completed", output)
   n. emit RunEvent (tool.completed + audit log)

3. Return GatewayExecutionResult(status="completed", output=response)
```

---

## 9. Security guarantees

1. **Tenant isolation:** Every query joins company_id + workspace_id (migration 12).
2. **Revocation:** Revoke → immediate assertion fail (no eventual consistency for authorization revocation).
3. **Expiry:** Hardcoded check: auth.expiresAt < now AND grant.expiresAt < now.
4. **Scope enforcement:** Required scope must be in granted scopes; action must be in allowedActions.
5. **Audit trail:** RunToolCallRecord logged; RunEvent streamed; approval records immutable.
6. **Secret confinement:** secretRef returned only to worker auth (requireWorkerServiceAuth gate); never in client response.
7. **Idempotency:** Duplicate side-effects rejected per (run_id, tool_call_id, payload_hash).

---

## 10. Roadmap & next phases

| Phase | Task | Owner | Timeline | Dependency |
|-------|------|-------|----------|-----------|
| Wave 0 | Hardening + E2E | Backend | Done (2026-08-26) | Blocking Wave B |
| Wave B | MCP via Gateway | Backend | Done (2026-08-26) | Pilot ready |
| Wave C | Pilot config | DevOps | 2026-08 | Wave B done |
| Wave P | Agent Skills/Plugins unlock | Product | TBD | See §6 conditions |

**Wave 0 blocking criteria (DoD):**
- ✅ Migration 12 applied; schema validated.
- ✅ E2E test passing (cross-tenant deny, expiry, scope mismatch, revocation).
- ✅ Worker assert endpoint gated by JWT.
- ✅ Audit logs verified; secrets not in logs/response.

**Wave B blocking criteria:**
- ✅ MCP tool adapter tested (mcp_tool_to_capability_spec correctness).
- ✅ Connector-grant re-verification re-check wired (no policy bypass).
- ✅ Sandbox-read pilot tool registered and callable.

---

## Appendix: Why NOT Agent Skills / Agent Plugins v1 in this pilot?

### Setup cost

- **Plugin manifest:** Requires `plugin.json` schema parser, vendor validator, package fetcher.
- **Distribution:** Registry API, versioning, changelog, deprecation policy.
- **Installation UX:** Workspace admin flow, package conflict resolution, rollback mechanism.
- **Testing:** Plugin portability tests, cross-schema version tests, registry cache coherence tests.

**Current pilot:** No package concept; skills published directly to registry; tools registered statically.

### Uncertain ROI

- **Why portable?** If 100% first-party for 3+ years, portable manifest adds process friction (validation cost, spec duplication), no benefit.
- **Why marketplace?** No partner queue; no commitment; "nice-to-have someday" = "not built now".
- **Why open distribution?** Pilot scope: one company, one control plane, one code repo. Third-party plugins: out of scope.

### Invariant preservation

- **Pinned skill refs:** `(skill_id, version, definition_hash)` non-negotiable per ADR-SKILL-IDENTITY. Plugin v1 doesn't enforce.
- **Approval gates:** Existing governance decides if MCP tool needs human sign-off. Plugin v1 doesn't mandate.
- **Tenant isolation:** Connector tables with company/workspace scope. Plugin v1 is tenant-agnostic; COSA adds it as overlay.

**Better to build on proven baseline (existing SkillSpec + CapabilityRegistry) than fork into two stacks (Agent Skills AND native SkillSpec, Agent Plugins AND connector tables).**

### Unlock conditions (Wave P)

Once product commits to marketplace (partner LOI, 3mo pilot success, 6mo delivery roadmap), a **parallel effort** can:
1. Adapt `plugin.json` reader → existing registry publish path.
2. Graft package installation UI onto existing workspace connector install flow.
3. Add plugin discovery API layer over existing registry + connector catalog.

Reuse infrastructure, don't rebuild.

---

## Addendum: Reference documentation

- **Master Architecture Guide:** `docs/architecture/COSA_CANONICAL_MASTER_ARCHITECTURE_AND_IMPLEMENTATION_GUIDE_2026-08-23.md` (§8 Agent Platform, §16-17 CapabilityGateway).
- **ADR-RUNTIME-002:** `docs/architecture/adr/ADR-RUNTIME-002-openai-agents-sdk-primary-deepseek-provider.md` (OpenAI Agents SDK runtime, not LangChain).
- **ADR-SKILL-IDENTITY:** `docs/architecture/adr/ADR-SKILL-IDENTITY.md` (Pinned skill refs, no floating).
- **ADR-CONTROLPLANE-001:** `docs/architecture/adr/ADR-CONTROLPLANE-001-endpoint-scoped-control-plane.md` (services/cosa as control plane).
- **DB_FINAL_CUTOVER:** `docs/architecture/COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md` (Mục 0, §29: baseline reconciliation).
