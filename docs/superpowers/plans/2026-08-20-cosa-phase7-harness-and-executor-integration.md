# COSA Phase 7 Harness and Executor Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans task-by-task.

**Goal:** Integrate DeepSeek Harness, Codex, Claude Code and n8n as version-pinned, governed RuntimeAdapter/ExecutorProvider implementations.

**Architecture:** COSA Business Core never imports vendor runtime code. `DeepSeekHarnessAdapter` stays under `app/workforce/agents/runtime/adapters`; executor providers stay under canonical workforce execution ownership. Each provider receives an ExecutionScope-derived capability set, uses ToolInvocationService for COSA tools, emits Phase 6 events, and returns governed artifacts. Native DSH tools are allowed only inside an isolated coding sandbox mode.

**Tech Stack:** Python, subprocess/JSON-RPC, OpenSandbox, existing runtime adapters/execution manager, pytest fixtures, Flutter Run Inspector.

**Spec:** Master rebuild plan Phase 7; DeepSeek Harness reference alignment; Phase 1/3/6 plans.

## Global Constraints

- Pin every provider package/CLI/protocol version and record compatibility fixtures.
- No arbitrary dynamic DSH plugin, provider-supplied tool or business credential reaches production COSA scope.
- COSA-governed DSH mode bridges only registered COSA tools through ToolInvocationService.
- Isolated coding mode has sandbox-scoped native tools only; it cannot receive production credential broker output.
- Resume/fork/cancellation/timeouts use explicit adapter contracts and are unavailable until implemented/tested.
- Codex, Claude Code and n8n never become workflow authority; Phase 4 runner remains authority.

## Tasks

### Task 1: Inventory and pin provider capabilities

- [ ] Create `docs/architecture/COSA_PROVIDER_COMPATIBILITY_MATRIX.md` and tests reading pinned versions from dependency/CLI config.
- [ ] Record DeepSeek Harness SDK protocol, Codex CLI/API, Claude Code provider and n8n connector supported operations, timeout/cancel semantics and sandbox requirements.
- [ ] Reject unpinned provider configuration at startup; commit `docs: pin harness provider compatibility`.

### Task 2: Standardize RuntimeAdapter and ExecutorProvider contracts

- [ ] Create canonical contracts for `start`, `stream`, `cancel`, `health`, `ingest_artifacts`, capability negotiation and typed provider errors.
- [ ] RED provider contract tests with fake native/DSH/Codex/Claude/n8n providers.
- [ ] Implement shared contract suite and GREEN tests; commit `feat: standardize governed provider contracts`.

### Task 3: Harden DeepSeekHarnessAdapter COSA-governed mode

- [ ] RED tests for session mapping, registered tool filtering, tool callback through ToolInvocationService, deny/approval non-execution, timeout and cancellation.
- [ ] Implement adapter JSON-RPC boundary with pinned protocol messages and correlation IDs; map DSH session/run IDs to COSA run/session records.
- [ ] Reject any DSH-discovered dynamic plugin/tool not registered by COSA Extension Registry.
- [ ] GREEN compatibility fixture tests; commit `feat: govern DeepSeek Harness runtime adapter`.

### Task 4: Implement isolated DSH coding-workspace mode

- [ ] RED tests proving coding mode receives an OpenSandbox workspace, no production secret broker values, bounded filesystem/network policy and artifact ingestion.
- [ ] Implement explicit mode selection `cosa_governed` versus `isolated_coding`; require approval/risk policy before coding execution.
- [ ] Persist diff/log/output only as redacted governed artifacts; commit `feat: isolate DeepSeek coding execution`.

### Task 5: Migrate Codex and Claude Code as ExecutorProviders

- [ ] Characterize existing Claude provider and any Codex integration; remove no code until consumers are covered.
- [ ] RED tests for scope mapping, sandbox lifecycle, cancellation, provider failure, artifact ingestion and no direct credential escape.
- [ ] Implement provider adapters behind shared execution manager; call from Phase 4 Executor nodes only.
- [ ] GREEN tests; commit `feat: govern coding executor providers`.

### Task 6: Adapt n8n as ExecutorProvider

- [ ] RED tests for signed callback correlation, idempotent callback processing, cancellation request and output/artifact validation.
- [ ] Implement n8n dispatch/callback adapter under execution provider ownership; prohibit n8n from publishing workflow state directly.
- [ ] Route returned operational action through ToolInvocationService where relevant; commit `feat: integrate n8n as governed executor`.

### Task 7: Provider observability and UI

- [ ] Extend Phase 6 events/projections for runtime/executor selected, isolation mode, health, cancellation and artifacts.
- [ ] RED Flutter tests for Run Inspector showing provider, isolation/permission summary, approval state and artifact links without raw transcript/secrets.
- [ ] Implement UI cards and GREEN tests; commit `feat: show governed provider execution state`.

### Task 8: Cross-provider parity suite and documentation

- [ ] Test same registered tool through Native and DSH gets equivalent ALLOW/DENY/APPROVAL/audit behavior.
- [ ] Test coding executor cannot read production credentials outside sandbox and provider version mismatch fails closed.
- [ ] Run full backend/Flutter verification; write `docs/architecture/COSA_PHASE7_HARNESS_EXECUTORS.md`.
- [ ] Commit `docs: complete governed harness integration phase seven`.

## Acceptance checklist

- [ ] DSH, Codex, Claude Code and n8n use shared contracts and pinned fixtures.
- [ ] Provider capability cannot bypass scope, policy, approval, audit, event or artifact boundaries.
- [ ] DSH native tools are isolated from production credentials.
- [ ] UI reports provider/isolation safely and published workflows retain execution authority.
