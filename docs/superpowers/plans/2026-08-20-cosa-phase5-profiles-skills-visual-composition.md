# COSA Phase 5 Profiles, Skills and Visual Composition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans task-by-task.

**Goal:** Compose workforce roles from versioned profiles and skills while preserving ExecutionScope and GovernanceKernel as non-bypassable authority.

**Architecture:** Keep production ownership in `backend/app/workforce`. Move only proven `AgentProfile` value from frozen scaffold paths through a compatibility import if needed; never migrate a parallel turn loop. `ProfileCompositionService` resolves visible tools, eligible skills, workflow permissions, model policy, scope ceiling and approval baseline. Session overrides are subtractive: they can remove visibility or add bounded context references, never add tool/permission/scope authority.

**Tech Stack:** Python, FastAPI, SQLAlchemy/Alembic, Pydantic, protected resources, pytest, Flutter/GetX.

**Spec:** Master rebuild plan Phase 5, `markdown/plan1.md`, Phase 1 ExecutionScope and Phase 3 Tool Invocation Pipeline plans.

## Global Constraints

- New roles are profile composition, never copied runtime loops or agent classes.
- Canonical profile/skill code is under `backend/app/workforce/agents/profiles` and `backend/app/workforce/skills`.
- Protected resources version all editable profile/skill bodies; published versions are immutable.
- Profile eligibility filters visibility before model/UI exposure; GovernanceKernel still evaluates every invocation.
- Session overrides are monotonic reductions: requested tools/permissions/scopes must be subsets of resolved profile capability.
- No raw prompt, secret, private reasoning or hidden policy implementation is sent to clients.

## Tasks

### Task 1: Characterize and re-home profile assets

- [ ] Create profile ownership tests mapping useful `backend/agent_runtime/profiles` schemas to canonical workforce equivalents.
- [ ] Create `backend/app/workforce/agents/profiles/{models.py,schemas.py,registry.py}` and compatibility re-exports only for verified consumers.
- [ ] Confirm no production import remains in frozen runtime scaffold before deleting nothing.
- [ ] Run focused pytest and commit `refactor: establish canonical workforce profile ownership`.

### Task 2: Define profile and composition contracts

- [ ] Create `composition/contracts.py` with immutable `AgentProfile`, `ResolvedProfile`, `SessionOverride`, `ProfileExplanation` DTOs.
- [ ] RED tests for profile fields: visible tool IDs, skill version selectors, workflow permissions, model policy, scope ceiling, approval baseline.
- [ ] Implement JSON-safe contracts and commit `feat: define profile composition contracts`.

### Task 3: Implement deterministic ProfileCompositionService

- [ ] Create `composition/service.py`, `composition/explanations.py`, tests.
- [ ] RED tests for disabled extension tool, insufficient scope, permission mismatch, inactive skill version and model-policy mismatch.
- [ ] Resolve profile against ExecutionScope, Extension Registry and tool/skill registries; return eligible capability set plus unavailable reason codes.
- [ ] GREEN tests and commit `feat: resolve governed profile compositions`.

### Task 4: Version skills and profile bodies through protected resources

- [ ] Add additive persistence/migration only where existing protected-resource versioning lacks profile/skill resource types.
- [ ] RED tests for draft/edit/publish/version lookup/revert and immutable published content.
- [ ] Store activation references `{skill_id, version, source_revision}` in session/run metadata; never copy mutable skill body into a completed run.
- [ ] GREEN tests and commit `feat: version skills and profile manifests`.

### Task 5: Enforce subtractive session overrides

- [ ] Create `composition/overrides.py` and tests for attempted added tool, broader Offering scope, elevated approval baseline and valid removed-tool override.
- [ ] Implement set-subset checks and bounded context-reference allowlist.
- [ ] Invoke composition/override resolver before runtime tool exposure and ToolInvocationService call.
- [ ] Assert GovernanceKernel remains called after an override; commit `feat: enforce subtractive session profile overrides`.

### Task 6: Expose authorized composition APIs

- [ ] Add profile list/detail/preview endpoints plus administrator draft/publish endpoints under workforce router.
- [ ] RED route tests: member can read own eligible composition; unauthorized user cannot mutate profile; preview never returns hidden tool config/secrets.
- [ ] Return explanation codes for unavailable tool/skill: `SCOPE`, `PROFILE`, `PERMISSION`, `EXTENSION_DISABLED`, `SECRET_UNAVAILABLE`, `FLAG_DISABLED`.
- [ ] GREEN tests and commit `feat: expose profile composition API`.

### Task 7: Build Profile Composition and Reasoning-node UI

- [ ] Create Flutter profile service/controller/view/widgets under existing settings/workforce module ownership.
- [ ] RED widget tests for read-only member view, admin versioned edit flow, unavailable capability explanations and subtractive session override controls.
- [ ] Add Phase 4 Reasoning-node inspector fields for profile, eligible skills, bounded context references and visible-tool summary.
- [ ] GREEN Flutter tests/analyze and commit `feat: compose workforce profiles visually`.

### Task 8: End-to-end verification and documentation

- [ ] Add invariant preventing profile runtime logic in `backend/agent_runtime/runtime`.
- [ ] Test a new role made only by composition; reject an out-of-profile tool through API/UI and verify governance call remains enforced.
- [ ] Run backend full suite and relevant Flutter tests/analyze.
- [ ] Write `docs/architecture/COSA_PHASE5_PROFILE_SKILL_COMPOSITION.md`; commit `docs: complete profile composition phase five`.

## Acceptance checklist

- [ ] A new role requires no copied turn loop.
- [ ] API/UI hide and reject ineligible tools/skills with explainable reason.
- [ ] Published skill/profile versions are reproducible by run/session reference.
- [ ] Session override cannot expand authority or bypass GovernanceKernel.
