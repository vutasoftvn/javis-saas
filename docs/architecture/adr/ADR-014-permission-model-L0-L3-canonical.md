# ADR-014: `PermissionLevel` (L0-L3A-L3) is the canonical governance vocabulary

## Status

Accepted (2026-08-22), user-confirmed.

## Context

Two incompatible permission vocabularies exist (see ADR-013 Context and `docs/architecture/AI_AGENT_OS_GAP_ANALYSIS.md` Part A8):

**`agentos/core/policy.py` — `PermissionClass`** (11 flat capability tags, static per-class table, no risk/agent dimension):
```python
READ_LOCAL, WRITE_WORKSPACE, READ_NETWORK, EXTERNAL_WRITE, SEND_MESSAGE,
MODIFY_BUSINESS_DATA, DEPLOY, EXECUTE_CODE, ACCESS_SECRET, DELETE_DATA, FINANCIAL_ACTION
```
`PolicyEngine.evaluate(permission)` looks up a static `DEFAULT_POLICY_TABLE` — one permission tag always maps to the same decision, regardless of which agent or how risky the specific tool call is.

**`legacy/agent_runtime/cosa_core/governance/policy_engine.py` — `PermissionLevel`** (production, richer):
```python
L0_READ, L1_SUGGEST, L2_DRAFT, L3A_EXECUTE_WITH_APPROVAL, L3_EXECUTE
```
evaluated dynamically against: per-tool `risk_level` (R0-R4 → low/medium/high/critical), per-tool `permission_level` string (`read_only`/`scoped_write`/`admin_write`), an `allowed_agent_keys` whitelist, plus a separate `ExecutionMode` axis (`INTERACTIVE`/`APPROVED_WORKFLOW`/`AUTONOMOUS_SAFE`) and a `PROTECTED_CORE_RESOURCES` immutability list (identity.md, soul.md, policies, ...). This is a **2-dimensional model** (agent's permission level × tool's risk level) vs `PermissionClass`'s flat 1-dimensional lookup.

## Decision

**`PermissionLevel` (L0_READ / L1_SUGGEST / L2_DRAFT / L3A_EXECUTE_WITH_APPROVAL / L3_EXECUTE) is the canonical governance vocabulary**, ported from `legacy/agent_runtime/cosa_core/governance/policy_engine.py` into `agentos/core/policy.py` as the primary decision mechanism, replacing `PermissionClass`-as-decision-table.

Migration shape (to be executed as its own task, not implied as already done by this ADR):

1. Port `PermissionLevel`, `ExecutionMode`, `PolicyAction`/`PolicyDecision`, `PROTECTED_CORE_RESOURCES`, and the `evaluate()`/`evaluate_execution_mode()` logic from `legacy/agent_runtime/cosa_core/governance/policy_engine.py` into `agentos/core/policy.py`, adapted to `agentos/`'s `ToolSpec`/tool-registry shape (`agentos/tools/registry.py`) instead of `cosa_core.tools.registry.ToolSpec`.
2. `PermissionClass`'s 11 values are **not deleted** — they are repurposed as a **tool-tagging vocabulary** that maps to a `(risk_level, permission_level)` pair feeding the ported `evaluate()`, e.g. `FINANCIAL_ACTION`/`DELETE_DATA`/`DEPLOY` → `risk_level="R4"` (always `REQUIRE_APPROVAL` regardless of agent's `PermissionLevel`, matching current `agentos/` behavior of denying/requiring-approval for these); `READ_LOCAL`/`READ_NETWORK` → `permission_level="read_only"`. This mapping table is a required deliverable of the migration task, not something this ADR pre-decides value-by-value.
3. Every `agentos/` `Agent`/`Skill` gets an explicit `PermissionLevel` (previously implicit/absent), analogous to how `legacy/agent_runtime` assigns a `permission_profile` per agent today.
4. `ApprovalService` (`agentos/core/approval.py`) keeps its existing `Approval` model/lifecycle (PENDING/APPROVED/DENIED) — this ADR changes the *input* to approval decisions, not the approval object shape itself.

## Consequences

- `agentos/core/policy.py`'s current `DEFAULT_POLICY_TABLE` becomes the seed for step 2's tag→risk mapping, not a decision table consulted directly at runtime after migration.
- Any code currently calling `PolicyEngine.evaluate(PermissionClass.X)` needs updating to pass `(agent_permission_level, tool_risk_level, tool_permission_level)` instead — this touches `agentos/core/executor.py` and every `agentos/tools/clusters/*.py` tool definition (each tool needs a `risk_level`/`permission_level` field, mirroring `ToolSpec` in the legacy engine).
- `ExecutionMode` (INTERACTIVE/APPROVED_WORKFLOW/AUTONOMOUS_SAFE) is a **new concept** for `agentos/` — currently `agentos/core/executor.py` has no equivalent axis. Introducing it is part of this migration, not optional.
- RBAC (flagged as missing in both systems per the gap analysis) is still not addressed by this ADR — `PermissionLevel` is a trust-tier model, not role-based access control. Stays a tracked gap.
- This migration is scoped as a Giai đoạn 3 task in the gap-analysis roadmap (`docs/architecture/AI_AGENT_OS_GAP_ANALYSIS.md` Part C) — not executed by this ADR itself.
