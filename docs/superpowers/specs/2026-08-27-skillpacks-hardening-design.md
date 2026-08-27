# Skillpacks Hardening and Runtime Activation Design

**Status:** Proposal for approval

**Date:** 2026-08-27
**Scope:** `skillpacks/` static contracts, instruction accuracy, and the future path to COSA runtime use.

## 1. Objective

Make every local skillpack structurally valid, internally consistent, and honest about what it can execute. A later, separate phase may publish selected skillpacks to COSA's durable skill registry and pin them to agents.

This design intentionally separates those outcomes. Fixing local Markdown or YAML must not imply that the skill is automatically executable by an agent.

## 2. Evidence and Root Cause

The audit found three distinct layers of defects.

| Layer | Evidence | Consequence |
| --- | --- | --- |
| Manifest structure | `skillpacks/tasks/manifest.yaml` parses as a YAML array because its root starts with `-`. | A consumer expecting `metadata.id`, `runtime`, or `source` receives no object. |
| Local contract consistency | `okr` and `twelve-week-year` declare `runtime.entrypoint: instructions`, although their instruction file is `SKILL.md`; six core/marketing skills have no frontmatter; eight frontmatter names use `.` or `_`. | Validators and discovery mechanisms cannot reliably identify or load the instructions. |
| Execution contract | Instructions refer to task, OKR, 12-week-year and strategy actions that are not all declared in the manifest and are not registered in COSA's runtime capability registry. | An agent can be instructed to call a tool that it has not been granted and may not exist in its run. |

There is also a deliberate product boundary: `docs/features/skills.md` records that `skillpacks/` has no runtime consumer. COSA currently resolves runtime skills from durable `SkillSpec` records through `SkillResolver`, after each skill is hash-pinned in `AgentSpec.pinned_skills`.

## 3. Design Decisions

### D1. Local files are source material, not a runtime loader

`skillpacks/` remains a reviewed source directory. COSA must not load its files directly at request time, discover a newest version automatically, or grant tools based only on text in a skillpack. Those behaviours would violate the existing hash-pinning invariant and could silently change an agent run.

### D2. Preserve canonical business identity; normalize discovery names

`manifest.yaml` keeps its existing `metadata.id` as the stable business identity, for example `operations.okr`. `SKILL.md` frontmatter `name` is a discovery-safe derivative:

| Manifest identity | Frontmatter name |
| --- | --- |
| `operations.okr` | `operations-okr` |
| `operations.tasks` | `operations-tasks` |
| `operations.twelve_week_year` | `operations-twelve-week-year` |
| `strategy.assumption-discovery` | `strategy-assumption-discovery` |

The normalization rule is: lowercase, replace every `.` and `_` with `-`, collapse repeated `-`, and reject collisions. Frontmatter is not an alternate runtime identifier.

### D3. A manifest always points to the real instruction file

Every pack has exactly these source files:

```text
skillpacks/<domain>/<skill-id>/
├── manifest.yaml
└── SKILL.md
```

`runtime.entrypoint` must be `SKILL.md`, and `source.path` must equal the pack's repository-relative directory. A manifest is a mapping at its root, never a YAML sequence.

### D4. Tool text is a contract, never an instruction to fabricate access

Every executable tool named in a skill's **Allowed Tool Calls** section must be listed in `runtime.tools`; aliases such as `task_create` must not survive unless they are an actual registered capability ID.

The converse also applies: a listed runtime tool must be used by the instruction or justified as an optional prerequisite. Cross-references to another skill are not tool calls.

Until a tool is registered for the active agent run, the instruction must require the agent to state that the action is unavailable, provide a non-mutating plan, and not claim that a write occurred. A skillpack never grants permission by itself.

### D5. Runtime activation is an immutable publish flow

When a skill is ready for use, an explicit publishing command or review workflow converts the reviewed source into a `SkillSpec`, publishes it with `publish_skill_spec()`, and creates a matching `PinnedSkillRef` on the intended `AgentSpec`.

Every semantic change bumps the version and creates a new hash. A local file edit never mutates an already published skill and never changes a running agent's behaviour.

## 4. Phase A — Static Contract and Instruction Hardening

### 4.1 Repairs

Apply these changes across all 16 skillpacks:

1. Restore `skillpacks/tasks/manifest.yaml` to a top-level mapping.
2. Change the `okr` and `twelve-week-year` entrypoints to `SKILL.md`.
3. Add frontmatter to `core/weekly-review` and every marketing skill.
4. Normalize every existing frontmatter name with the D2 rule. Keep `metadata.id` unchanged.
5. Make descriptions concise, trigger-oriented and written so an agent can decide when the skill applies. Keep Vietnamese where it serves the product audience.
6. Reconcile every **Allowed Tool Calls** list with `runtime.tools`.
7. Rewrite tool directives that refer to unavailable pseudo-tool names. They must either use a real registered capability ID or explicitly take the safe, non-executing fallback from D4.
8. Reword `strategy/decision-capture` so an existing `gateEvaluationId` is input context rather than an undeclared call. Add the required stage-policy lookup to `strategy/gate-evaluation` only after its capability contract is available.

### 4.2 Contract validator

Add one repository-owned validator and run it in the normal quality gate. It must check:

- each pack contains exactly one `manifest.yaml` and one `SKILL.md`;
- YAML parses to a mapping and contains the required top-level sections;
- `metadata.id` is unique and `source.path` points back to that pack;
- the entrypoint exists and is `SKILL.md`;
- frontmatter parses, has `name` and `description`, and its name follows D2;
- every executable tool reference has an exact counterpart in `runtime.tools`;
- every tool declaration is an explicit string and no legacy alias remains;
- source IDs, frontmatter names and paths do not collide.

The validator checks static integrity only. It does not assert that a declared tool is presently available at runtime; that belongs to Phase B's capability integration test.

### 4.3 Tests

Tests must be written before the repair and demonstrate the current failures: the array-root task manifest, absent frontmatter, invalid names, invalid entrypoints, and undeclared tool calls. The full validator then passes only after the smallest compatible repairs.

## 5. Phase B — Optional COSA Runtime Activation

Phase B is required only when the product expects a user-facing COSA agent to execute a skillpack rather than treat it as reference material.

### 5.1 Capability-first order

For each selected pack:

1. Define the capability contract and handler in COSA. It must enforce tenant scope, policy evaluation, approval risk and audited outcomes.
2. Register the capability in `build_cosa_agent_plane()`.
3. Add a capability integration test proving the actual agent plane exposes the exact capability ID.
4. Populate the skill's `required_capabilities` from those registered IDs; do not infer them from an HTTP endpoint or handler name.
5. Publish the resulting `SkillSpec`, pin its version and hash to the intended agent specification, and test resolution through `SkillResolver`.

Current registered Operations capabilities are read-only task list/read. Consequently, task writes, OKR changes, 12-week-year actions, and Strategy writes must remain unavailable until their own capability-first work has completed.

### 5.2 Publish and release checks

Before publishing a skill version:

- validate the source pack;
- run the relevant capability and policy tests;
- build the `SkillSpec` deterministically from reviewed source;
- publish once with its version and computed hash;
- pin that exact identity and hash on the AgentSpec;
- prove a valid pin resolves and a mismatched hash fails before a run begins.

## 6. Explicit Non-Goals

- No direct runtime file loader for `skillpacks/`.
- No auto-publish or silent version upgrade when Markdown changes.
- No tool permission derived from manifest text.
- No direct Company Service HTTP calls from a skill instruction that bypass COSA's capability gateway, tenant policy and approval flow.
- No claim that Phase A makes a skill executable in production.

## 7. Rollout Order

1. Add the failing validator cases.
2. Repair static contract defects and instruction/tool consistency.
3. Run the validator in local quality checks and CI.
4. Mark the source packs as validated reference material.
5. Select one low-risk read-only pack for Phase B as a vertical slice.
6. Add further write-capable packs only after their capability, approval and tenant-isolation tests exist.

## 8. Acceptance Criteria

Phase A is complete when all 16 packs pass the static validator, no instruction invents or silently assumes tool access, and the quality workflow rejects a future malformed pack.

Phase B is complete for a chosen pack only when an agent with its correct `PinnedSkillRef` can resolve the published `SkillSpec`, sees precisely the required registered capabilities, and fails safely for missing/mismatched pins or denied actions.

## 9. Decision Required Before Implementation

Approve one of the following scopes:

1. **Phase A only (recommended first):** repair and protect the local skillpack contract without changing runtime behaviour.
2. **Phase A plus one Phase B vertical slice:** choose one low-risk, read-only pack to establish the durable publish/pin path.
3. **Phase A plus broad activation:** a larger planned program that adds and governs every missing capability before any write-enabled skill is activated.
