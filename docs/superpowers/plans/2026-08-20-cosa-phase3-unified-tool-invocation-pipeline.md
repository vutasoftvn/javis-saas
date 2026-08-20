# COSA Phase 3 Unified Tool Invocation Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans task-by-task.

**Goal:** Route every operational tool action through one scope-derived, policy-governed, auditable invocation pipeline.

**Architecture:** Keep `ToolSpec` in `app/core/tool_registry.py` and `GovernanceKernel` as the final decision authority. Replace the mixed responsibilities in `app/core/tool_dispatch.py` with a small orchestrator that delegates to contracts, input validation, policy gate, native/provider dispatch, output safety, and projection modules under `app/workforce/tools/invocation/`. No model, workflow, MCP provider, executor, or UI may invoke a tool body directly.

**Tech Stack:** Python, FastAPI, SQLAlchemy, Pydantic, pytest, existing GovernanceKernel/AgentToolCall/audit/event models.

**Spec:** `docs/superpowers/plans/2026-08-20-cosa-extensible-harness-visual-workflows-rebuild.md` Phase 3; `docs/superpowers/plans/2026-08-20-cosa-phase2-governed-extension-registry.md`.

## Global Constraints

- `ExecutionScope` is server-derived; discard model/client `workspace_id`, `company_id`, `user_id`, grants, approval IDs and principal fields.
- `GovernanceKernel.evaluate_and_audit_tool_call()` is the only allow/deny/approval decision point.
- DENY and REQUIRE_APPROVAL must execute zero backend/provider body code.
- Output sent to model/UI is JSON-safe, schema-validated, redacted, bounded, and correlated; raw secrets and exception stacks never leave server logs.
- Do not create a second tool registry, policy engine, event store, or workflow runner.
- Existing `ToolSpec` remains backwards compatible while new metadata is additive.
- Migrate entrypoints one at a time; dual execution of an external action is prohibited.

## Module boundaries

| Module | Responsibility |
|---|---|
| `contracts.py` | Immutable request/result/error/event DTOs |
| `input_validation.py` | JSON parsing, server parameter stripping, JSON-schema validation |
| `policy_gate.py` | Adapts request/scope to GovernanceKernel decision |
| `dispatchers.py` | Native ToolSpec or registered provider execution only |
| `output_safety.py` | JSON conversion, output-schema validation, redaction, truncation |
| `projections.py` | Correlation/causation IDs, audit/event projection adapter |
| `service.py` | Ordered orchestration; no provider-specific logic |
| `legacy_adapter.py` | Compatibility bridge from `execute_tool_spec` callers |

### Task 1: Characterize legacy entrypoints and tool metadata

**Files:**
- Create: `backend/app/tests/tools/test_invocation_baseline.py`
- Modify: `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`

- [ ] Write failing/characterization tests proving `execute_tool_spec` strips injected model parameters and `GovernanceKernel` returns DENY/REQUIRE_APPROVAL before dispatch.
- [ ] Run: `cd backend && pytest app/tests/tools/test_invocation_baseline.py -q`.
- [ ] Add entrypoint inventory: chat company tools, runtime tool bridge, workflow runner, MCP bridge, execution providers, DSH adapter.
- [ ] Commit: `git add backend/app/tests/tools docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md && git commit -m "test: characterize tool invocation entrypoints"`.

### Task 2: Define invocation contracts and extend ToolSpec additively

**Files:**
- Create: `backend/app/workforce/tools/invocation/contracts.py`
- Modify: `backend/app/core/tool_registry.py`
- Test: `backend/app/tests/tools/test_invocation_contracts.py`

- [ ] Write tests for `ToolInvocationRequest`, `ToolInvocationResult`, `ToolInvocationError`, correlation/causation IDs, and default ToolSpec execution metadata.
- [ ] Run RED: `cd backend && pytest app/tests/tools/test_invocation_contracts.py -q`.
- [ ] Add optional ToolSpec fields: `input_schema`, `output_schema`, `timeout_seconds`, `retry_policy`, `idempotency_key_field`, `concurrency_key`, `required_scope_level`, `required_secret_refs`, `backend_id`; retain existing defaults.
- [ ] Require immutable request fields: `scope`, `tool_flat_name`, `arguments`, `correlation_id`, `causation_id`, `source`.
- [ ] Run GREEN and commit `feat: define tool invocation contracts`.

### Task 3: Implement input validation and monotonic scope guards

**Files:**
- Create: `backend/app/workforce/tools/invocation/input_validation.py`
- Test: `backend/app/tests/tools/test_invocation_input_validation.py`

- [ ] Test invalid JSON, non-object input, injected IDs, unknown parameters, invalid schema, and model attempts to widen Offering/Initiative scope.
- [ ] Run RED.
- [ ] Implement `normalize_arguments(spec, arguments, scope)` to parse input, remove injected fields, validate JSON Schema, preserve only callable/schema fields, and return typed validation errors.
- [ ] Run GREEN: `cd backend && pytest app/tests/tools/test_invocation_input_validation.py -q`.
- [ ] Commit `feat: validate governed tool invocation input`.

### Task 4: Isolate policy gate and prove non-execution

**Files:**
- Create: `backend/app/workforce/tools/invocation/policy_gate.py`
- Test: `backend/app/tests/tools/test_invocation_policy_gate.py`

- [ ] Test ALLOW, DENY and REQUIRE_APPROVAL with a spy backend; assert spy call count is `1`, `0`, `0` respectively.
- [ ] Run RED.
- [ ] Adapt `ExecutionScope` into `AgentRunRequest` only inside policy gate; call GovernanceKernel once; map decision/approval to invocation result.
- [ ] Run GREEN and existing governance tests.
- [ ] Commit `feat: gate invocations through governance kernel`.

### Task 5: Implement native/provider dispatchers with cancellation and idempotency

**Files:**
- Create: `backend/app/workforce/tools/invocation/dispatchers.py`
- Test: `backend/app/tests/tools/test_invocation_dispatchers.py`

- [ ] Test native sync/async call, timeout, cancellation token, idempotency replay, and provider failure mapping.
- [ ] Run RED.
- [ ] Implement `dispatch_native` and `dispatch_provider`; provider dispatch receives only resolved capability ID/config, normalized args and scope. Never pass raw secret/config to a model-facing result.
- [ ] Run GREEN.
- [ ] Commit `feat: dispatch governed tool backends`.

### Task 6: Implement output safety and projections

**Files:**
- Create: `backend/app/workforce/tools/invocation/output_safety.py`
- Create: `backend/app/workforce/tools/invocation/projections.py`
- Test: `backend/app/tests/tools/test_invocation_output_safety.py`

- [ ] Test non-serializable output, schema mismatch, nested secret redaction, size truncation, and correlation ID in projection.
- [ ] Run RED.
- [ ] Implement `safe_output()` using JSON-safe conversion, output-schema validation, recursive redaction for configured secret values/keys, and bounded previews.
- [ ] Emit canonical audit/event projection on completed, failed, denied, and approval-required outcomes.
- [ ] Run GREEN and commit `feat: secure tool invocation outputs and projections`.

### Task 7: Compose service and preserve legacy compatibility

**Files:**
- Create: `backend/app/workforce/tools/invocation/service.py`
- Create: `backend/app/workforce/tools/invocation/legacy_adapter.py`
- Modify: `backend/app/core/tool_dispatch.py`
- Test: `backend/app/tests/tools/test_tool_invocation_service.py`

- [ ] Test exact ordering: resolve → validate → policy → dispatch → safe output → projection; deny/approval stop before dispatch.
- [ ] Run RED.
- [ ] Implement `ToolInvocationService.invoke()` as the sole orchestrator. Make `execute_tool_spec` delegate through the legacy adapter, preserving its current public signature.
- [ ] Run GREEN plus `pytest app/tests/test_tool_registry.py app/tests/chat -q`.
- [ ] Commit `refactor: route legacy dispatch through invocation pipeline`.

### Task 8: Migrate production entrypoints one at a time

**Files:**
- Modify: `backend/app/workforce/chat/company_tools.py`
- Modify: `backend/app/workforce/agents/runtime/tool_bridge.py`
- Modify: `backend/app/workforce/extensions/capability_bridge.py`
- Modify: `backend/app/integrations/workflows/` runner path
- Modify: `backend/app/workforce/agents/runtime/adapters/deepseek_harness.py`
- Tests: `backend/app/tests/tools/test_entrypoint_invocation_migration.py`

- [ ] For each entrypoint, write a test showing it produces one correlation ID and cannot bypass deny/approval.
- [ ] Migrate chat first, then runtime, MCP, workflow, executor, DSH; run focused test after each migration.
- [ ] Do not migrate the next entrypoint until its predecessor has no direct body call.
- [ ] Commit one migration per entrypoint: `refactor: migrate <entrypoint> to invocation pipeline`.

### Task 9: Complete Phase 3 verification and UI-safe contract

**Files:**
- Create: `docs/architecture/COSA_PHASE3_TOOL_INVOCATION_PIPELINE.md`
- Modify: `backend/app/tests/test_architectural_invariants.py`
- Modify: shared frontend result-card/service files discovered during entrypoint migration

- [ ] Add invariant asserting new operational entrypoints import `ToolInvocationService`, not provider/native callable directly.
- [ ] Document contract fields, structured error codes, redaction behavior, correlation IDs and migration ledger.
- [ ] Add Flutter tests asserting cards render safe preview/status/approval/artifact link but not raw args or secrets.
- [ ] Run: `cd backend && pytest -q`; `cd frontend && flutter test && flutter analyze`.
- [ ] Commit `docs: complete unified tool invocation pipeline phase three`.

## Acceptance checklist

- [ ] DENY and REQUIRE_APPROVAL execute no tool/provider body.
- [ ] Every migrated call has scope, correlation ID, audit/event projection and JSON-safe result.
- [ ] Model/client-provided scope, approval and principal fields never influence authority.
- [ ] Invalid output and secrets cannot reach model/UI.
- [ ] Native, MCP, workflow, executor and DSH paths use one pipeline.
