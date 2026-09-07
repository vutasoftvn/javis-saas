# Local-first Model Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cung cấp model default có provenance và để founder cấu hình provider/model/fallback theo workspace hoặc agent profile mà không làm rò credential hay vượt data-policy.

**Architecture:** `WorkspaceModelRouteResolver` resolve một profile đã policy-check trước khi kernel tạo model client. Provider profile và ciphertext credential nằm trong Postgres/local secret root của Workspace Runtime Node; agent chỉ nhận model client đã chọn. External API adapter, local OpenAI-compatible adapter và local CLI bridge có cùng contract nhưng khác egress/credential guard.

**Tech Stack:** Python 3.11, FastAPI/Pydantic, PostgreSQL/RLS, LiteLLM/OpenAI-compatible clients, `asyncio.create_subprocess_exec`, Flutter/GetX, pytest, Flutter test.

**Spec:** [Local-first Model Routing design](../specs/2026-09-07-local-first-model-routing-design.md)

## Global Constraints

- Không dùng `DEEPSEEK_*` hoặc bất kỳ provider env key nào làm workspace selection; env chỉ có thể bootstrap system default hoặc test double.
- API key plaintext không được persist trong Flutter, log, event, task payload hay response; local credential cipher được encrypt bằng node key file mode `0600`.
- `openai_api` là API Platform credential riêng; ChatGPT subscription không phải credential type. `codex_cli` là local-session route khác. Provider/CLI availability phải qua server-side health check.
- Chỉ `founder`, `co-founder`, `admin` được tạo/rotate/revoke credential và model policy. Agent có quyền đọc context không có quyền gọi các mutation này.
- `claude_cli`/`codex_cli`/`gemini_cli` adapter không chạy shell string, không nhận arbitrary executable/flag/environment, không kế thừa browser/session token hoặc `$HOME`.
- Fallback chỉ dùng profile ordered allowlist và chỉ sau compliance check; provider bị deny không nhận prompt.

---

### Task 1: Persist model profiles and resolve default/override/fallback deterministically

**Files:**
- Create: `packages/agent/migrations/027_workspace_model_routing.sql`
- Create: `apps/cosa/models/contracts.py`
- Create: `apps/cosa/models/repository.py`
- Create: `apps/cosa/models/resolver.py`
- Modify: `packages/agent/contracts/model_policy.py`
- Test: `tests/apps/cosa/models/test_model_route_resolver.py`

**Interfaces:**

```python
class ProviderType(StrEnum):
    LOCAL_OPENAI_COMPATIBLE = "local_openai_compatible"
    ANTHROPIC_API = "anthropic_api"
    OPENAI_API = "openai_api"
    OPENROUTER_API = "openrouter_api"
    DEEPSEEK_API = "deepseek_api"
    CLAUDE_CLI = "claude_cli"
    CODEX_CLI = "codex_cli"
    GEMINI_CLI = "gemini_cli"

async def resolve_route(workspace_id: str, agent_spec_id: str) -> ResolvedModelRoute: ...
```

- [x] **Step 1: Write failing precedence and isolation tests.**

```python
async def test_agent_override_beats_workspace_default(resolver):
    await resolver.set_workspace_default("ws-a", "local-general")
    await resolver.set_agent_override("ws-a", "cosa.agents.operations", "claude-fast", [])
    assert (await resolver.resolve_route("ws-a", "cosa.agents.operations")).profile_id == "claude-fast"

async def test_route_never_crosses_workspace(resolver):
    await resolver.create_profile("ws-a", "private-route", ProviderType.OPENROUTER_API)
    with pytest.raises(ModelRouteNotFound):
        await resolver.set_workspace_default("ws-b", "private-route")
```

- [x] **Step 2: Run the focused test.**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/models/test_model_route_resolver.py -q`

Expected: FAIL because the current composition unconditionally builds a DeepSeek model from environment.

- [x] **Step 3: Add expand-only local schema and typed resolver.**

Create workspace-scoped `model_provider_profiles` and `workspace_model_policies` tables with RLS. Profile stores provider type, model ID, credential ID/reference, allowed model list, budget, concurrency and status; policy stores `WORKSPACE` or `AGENT_PROFILE` scope, primary profile and ordered fallback IDs. `ResolvedModelRoute` contains no secret.

```python
async def resolve_route(self, workspace_id: str, agent_spec_id: str) -> ResolvedModelRoute:
    policy = await self._repo.get_policy(workspace_id, "AGENT_PROFILE", agent_spec_id)
    policy = policy or await self._repo.get_policy(workspace_id, "WORKSPACE", workspace_id)
    return await self._validate(policy or self._system_default)
```

- [x] **Step 4: Run repository and tenancy checks.**

Run:

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/models/test_model_route_resolver.py -q
make tenancy-check
```

Expected: PASS; a missing profile or unapproved fallback fails closed.

- [x] **Step 5: Commit.**

```bash
git add packages/agent/migrations/027_workspace_model_routing.sql packages/agent/contracts/model_policy.py \
  apps/cosa/models/contracts.py apps/cosa/models/repository.py apps/cosa/models/resolver.py \
  tests/apps/cosa/models/test_model_route_resolver.py
git commit -m "feat(models): add local workspace model route resolver"
```

---

### Task 2: Implement encrypted local credentials and provider adapters

**Files:**
- Create: `apps/cosa/models/credential_store.py`
- Create: `apps/cosa/models/providers.py`
- Modify: `apps/cosa/composition/model_provider.py`
- Modify: `apps/cosa/observability/logging.py`
- Test: `tests/apps/cosa/models/test_credential_store.py`
- Test: `tests/apps/cosa/models/test_provider_adapters.py`

**Interfaces:**

```python
async def put(workspace_id: str, plaintext: SecretStr) -> CredentialReference: ...
async def create(route: ResolvedModelRoute) -> ModelClient: ...
```

- [x] **Step 1: Write failing encryption and provider selection tests.**

```python
async def test_ciphertext_has_no_plaintext_and_is_workspace_scoped(store):
    ref = await store.put("ws-a", SecretStr("sk-secret"))
    assert "sk-secret" not in await store.raw_ciphertext_for_test(ref.id)
    with pytest.raises(CredentialNotFound):
        await store.get("ws-b", ref.id)

def test_openai_api_profile_requires_api_credential(factory):
    with pytest.raises(ModelProviderMisconfigured):
        factory.create(route(provider_type=ProviderType.OPENAI_API, credential_id=None))
```

- [x] **Step 2: Run the tests.**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/models/test_credential_store.py tests/apps/cosa/models/test_provider_adapters.py -q`

Expected: FAIL because no local credential store or provider factory exists.

- [x] **Step 3: Add credential encryption and adapter factory.**

Load `COSA_LOCAL_SECRETS_KEY_FILE` only at local runtime startup; reject missing, group/world-readable or non-local path in production. Persist ciphertext/nonce/key-version, never plaintext. Map each API provider to explicit adapter and validate model allowlist, budget, concurrency, credential workspace and compliance egress data class before request. Redact authorization headers/provider bodies/prompt in log sanitization.

- [x] **Step 4: Run safety tests and lint.**

Run:

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/models/test_credential_store.py tests/apps/cosa/models/test_provider_adapters.py -q
make lint
```

Expected: PASS; key never appears in test log capture and wrong workspace cannot decrypt it.

- [x] **Step 5: Commit.**

```bash
git add apps/cosa/models/credential_store.py apps/cosa/models/providers.py apps/cosa/composition/model_provider.py \
  apps/cosa/observability/logging.py tests/apps/cosa/models/test_credential_store.py tests/apps/cosa/models/test_provider_adapters.py
git commit -m "feat(models): add encrypted local provider credentials"
```

---

### Task 3: Add constrained Claude/Codex/Gemini CLI bridge and route it through compliance

**Files:**
- Create: `apps/cosa/models/cli_bridge.py`
- Modify: `apps/cosa/models/providers.py`
- Modify: `apps/cosa/composition/kernel_factory.py`
- Modify: `apps/cosa/worker/handlers.py`
- Test: `tests/apps/cosa/models/test_cli_bridge.py`
- Test: `tests/apps/cosa/worker/test_model_route_binding.py`

**Interfaces:**

```python
async def invoke(self, request: ModelInvocation) -> ModelResponse: ...
async def bind_route_to_run(request: RunRequest, spec: AgentSpec) -> ResolvedModelRoute: ...
```

- [x] **Step 1: Write failing executable and no-egress-on-deny tests.**

```python
async def test_cli_bridge_rejects_shell_and_kills_timeout(bridge):
    with pytest.raises(CliBridgeDenied):
        await bridge.invoke(ModelInvocation(executable="/bin/sh", prompt="x"))
    with pytest.raises(ModelProviderTimeout):
        await bridge.invoke(ModelInvocation(executable="/opt/cosa/bin/fake-claude", prompt="x", timeout_seconds=0.01))

async def test_compliance_deny_prevents_adapter_invocation(worker_fixture):
    worker_fixture.deny_provider("external-openai")
    await worker_fixture.run()
    assert worker_fixture.provider_requests == []
```

- [x] **Step 2: Run the test.**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/models/test_cli_bridge.py tests/apps/cosa/worker/test_model_route_binding.py -q`

Expected: FAIL because model selection happens only in global kernel composition and no CLI bridge exists.

- [x] **Step 3: Implement bridge and bind route before kernel execution.**

Use `asyncio.create_subprocess_exec` with absolute executable allowlist for `claude`, `codex` and `gemini`, fixed argument templates, restricted environment, stdin prompt, stdout cap, per-profile semaphore, process-group timeout/cancellation. No shell string or arbitrary flags. In worker preparation resolve the route, validate compliance snapshot and create the adapter only after allow. Persist profile/model/policy/fallback index to run provenance, never the prompt/key.

- [x] **Step 4: Run regression tests.**

Run:

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/models/test_cli_bridge.py tests/apps/cosa/worker/test_model_route_binding.py tests/apps/cosa/worker/test_handlers.py -q
```

Expected: PASS; denied provider gets zero prompt requests and timed-out CLI is cancelled.

- [x] **Step 5: Commit.**

```bash
git add apps/cosa/models/cli_bridge.py apps/cosa/models/providers.py apps/cosa/composition/kernel_factory.py \
  apps/cosa/worker/handlers.py tests/apps/cosa/models/test_cli_bridge.py tests/apps/cosa/worker/test_model_route_binding.py
git commit -m "feat(models): route governed runs through local CLI bridge"
```

---

### Task 4: Expose founder-only model settings UI and REST commands

**Files:**
- Create: `apps/cosa/api/model_policy_routes.py`
- Create: `apps/cosa/api/model_policy_schemas.py`
- Modify: `apps/cosa/api/app.py`
- Modify: `shared/contracts/mvp-surface.json`
- Regenerate: `apps/cosa/api/mvp_contracts_generated.py`, `frontend/lib/core/network/mvp_endpoints.g.dart`
- Create: `frontend/lib/modules/settings/services/model_provider_service.dart`
- Create: `frontend/lib/modules/settings/views/model_provider_settings_view.dart`
- Test: `tests/apps/cosa/api/test_model_policy_routes.py`
- Test: `frontend/test/modules/settings/model_provider_settings_test.dart`

**Interfaces:**

```python
POST /agent/settings/model-providers
POST /agent/settings/model-providers/{profile_id}/test
PUT  /agent/settings/model-policies/{agent_profile}
```

- [x] **Step 1: Write failing founder/member and secret-redaction tests.**

```python
async def test_member_cannot_create_provider(client, member_headers):
    response = await client.post("/agent/settings/model-providers", headers=member_headers, json={"provider_type": "openrouter_api", "api_key": "x"})
    assert response.status_code == 403

async def test_founder_policy_response_has_no_api_key(client, founder_headers):
    response = await client.put("/agent/settings/model-policies/operations", headers=founder_headers, json={"primary_profile_id": "local-general", "fallback_profile_ids": []})
    assert response.status_code == 200
    assert "api_key" not in response.text
```

- [x] **Step 2: Run API and UI tests.**

Run:

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/api/test_model_policy_routes.py -q
cd frontend && flutter test test/modules/settings/model_provider_settings_test.dart -r compact
```

Expected: FAIL because no model settings routes/UI exist.

- [x] **Step 3: Implement typed founder-only settings.**

Require `require_workspace_operator`; body uses `SecretStr` only for create/rotate and detail returns `credential_configured`, status, key version, budget/concurrency and allowed model IDs. Test command has low fixed budget. UI uses generated MVP endpoints, shows system/workspace/agent precedence and ordered fallbacks, and never labels a provider usable until server health check succeeds.

- [x] **Step 4: Run contracts and frontend gate.**

Run:

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/api/test_model_policy_routes.py tests/apps/cosa/models -q
cd frontend && flutter test test/modules/settings/model_provider_settings_test.dart -r compact
cd .. && make frontend-api-contract-check
```

Expected: PASS; member cannot mutate, founder cannot read a submitted key and client cannot invent availability.

- [x] **Step 5: Commit.**

```bash
git add apps/cosa/api/model_policy_routes.py apps/cosa/api/model_policy_schemas.py apps/cosa/api/app.py \
  shared/contracts/mvp-surface.json apps/cosa/api/mvp_contracts_generated.py frontend/lib/core/network/mvp_endpoints.g.dart \
  frontend/lib/modules/settings tests/apps/cosa/api/test_model_policy_routes.py frontend/test/modules/settings/model_provider_settings_test.dart
git commit -m "feat(settings): let founders configure local model routes"
```

---

### Task 5: Prove fallback, budget, local residency and CLI cancellation end-to-end

**Files:**
- Create: `tests/e2e/test_workspace_model_routing.py`
- Modify: `docs/operations/local-knowledge-runbook.md`
- Modify: `Makefile`

**Interfaces:**
- Produces `make workspace-model-routing-e2e` using local fake provider and CLI fixtures, never a paid credential.

- [x] **Step 1: Write failing E2E policy cases.**

```python
def test_quota_uses_only_approved_fallback(local_stack):
    local_stack.configure_model_route(primary="provider-a", fallbacks=["provider-b"])
    local_stack.make_provider_fail("provider-a", code="quota_exhausted")
    assert local_stack.run_founder_chat("Tóm tắt").model_route.profile_id == "provider-b"

def test_compliance_deny_sends_no_prompt(local_stack):
    local_stack.configure_model_route(primary="external-openai", fallbacks=[])
    local_stack.deny_provider_for_confidential_data("external-openai")
    assert local_stack.run_founder_chat("Dữ liệu nội bộ").status == "failed"
    assert local_stack.provider_requests("external-openai") == []
```

Add one fixture for each `claude`, `codex`, `gemini` adapter; force a timeout for one, verify child cancellation and confirm mock Platform telemetry contains no prompt/ciphertext for all three.

- [x] **Step 2: Run E2E red baseline.**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/e2e/test_workspace_model_routing.py -q`

Expected: FAIL until Tasks 1–4 exist.

- [x] **Step 3: Add target and local operations procedures.**

The target creates a temporary local secrets key file mode `0600`, starts fixtures, runs tests and removes the directory. Runbook covers key rotation/revoke, budget exhaustion, provider policy deny, CLI disable and local recovery. It states ChatGPT/API billing are distinct and usability is established only by configured API credential or permitted local CLI health check.

- [x] **Step 4: Run release evidence.**

Run:

```bash
make workspace-model-routing-e2e
make agent-test
make apps-cosa-test
make frontend-test
make frontend-analyze
make tenancy-check
```

Expected: PASS; missing paid credentials cannot skip the fixture-based security contract.

- [x] **Step 5: Commit.**

```bash
git add tests/e2e/test_workspace_model_routing.py docs/operations/local-knowledge-runbook.md Makefile
git commit -m "test(models): verify governed local model routing"
```
