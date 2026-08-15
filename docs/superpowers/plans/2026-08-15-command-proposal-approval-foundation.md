# Command, Proposal & Approval Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make privileged commands immutable, tenancy-scoped, and executable exactly once after approval.

**Architecture:** Extend `AgentProposal` with a frozen typed command and link it to existing `AgentApproval`. The proposal service is the only executor; approval only marks `executed` after the service returns a successful resource result.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy, Alembic, PostgreSQL, pytest.

**Spec:** `docs/superpowers/specs/2026-08-15-chat-voice-n-week-execution-design.md`

## Global Constraints

- Scope all resource access by authenticated workspace ID and serialize Snowflake IDs as strings.
- Do not execute finance, publication, material cycle/OKR or high/critical changes before owner/admin approval.
- Use `backend/app` only; preserve current unrelated worktree changes.

---

### Task 1: Freeze typed proposal commands

**Files:** Create `backend/app/agents/proposals/command.py`; modify `backend/app/agents/proposals/service.py`; test `backend/app/tests/agents/test_agent_proposal_bridge.py`.

**Interfaces:** `ProposalCommand(command_type: Literal["okr_objective.create", "strategy_task.create"], idempotency_key: str, arguments: dict)`; `parse_proposal_command(payload: dict) -> ProposalCommand`.

- [ ] Write failing tests that reject missing `payload.command` and unknown `command_type`.
- [ ] Run `cd backend && pytest app/tests/agents/test_agent_proposal_bridge.py -q`; expect failure because parser is absent.
- [ ] Implement Pydantic validation before persistence and retain the validated command without mutation.
- [ ] Re-run the focused test; expect pass.
- [ ] Commit only the command, service and test files with message `feat: freeze executable proposal commands`.

### Task 2: Link approvals to proposals safely

**Files:** Modify `backend/app/agents/governance/models.py` and `approval_service.py`; create `backend/alembic/versions/v13_0xx_proposal_approval_link.py`; test `backend/app/tests/agents/test_agent_proposal_bridge.py`.

**Interfaces:** nullable indexed `AgentApproval.proposal_id`; `ApprovalService.create_approval(..., proposal_id: Optional[int] = None)`.

- [ ] Write a failing test that links a proposal from workspace B to an approval in workspace A and expects a scope error.
- [ ] Run the focused test; expect failure because `proposal_id` is unsupported.
- [ ] Add the migration/model field and query `AgentProposal` with both ID and workspace before assigning it.
- [ ] Run `cd backend && alembic upgrade head && pytest app/tests/agents/test_agent_proposal_bridge.py -q`; expect pass.
- [ ] Commit this migration, model, service and test with message `feat: link approvals to frozen proposals`.

### Task 3: Apply approved command exactly once

**Files:** Modify `backend/app/agents/proposals/service.py` and `router.py`; test `backend/app/tests/agents/test_agent_proposal_bridge.py`.

**Interfaces:** `apply_proposal(db, workspace_id, proposal_id, reviewed_by) -> dict`; response keys `status`, `proposal_id`, `resource_type`, `resource_id`.

- [ ] Write failing tests: pending proposal returns 422; second apply returns the original resource without another domain write.
- [ ] Run the focused test; expect failure because pending proposals are presently applicable.
- [ ] Dispatch only the two allowlisted typed commands, require `status == "approved"`, and write resource plus `applied_resource_id`/`applied` status in one transaction.
- [ ] Run `cd backend && pytest app/tests/agents/test_agent_proposal_bridge.py app/tests/test_tool_registry.py -q`; expect pass.
- [ ] Commit the service/router/test changes with message `feat: execute approved proposals idempotently`.

### Task 4: Restrict review and write execution audit

**Files:** Modify `backend/app/agents/proposals/router.py` and `backend/app/agents/approvals_router.py`; test `backend/app/tests/agents/test_agent_proposal_bridge.py`.

**Interfaces:** owner/admin-only review/apply; executed approval persists `execution_result_jsonb` and `status == "executed"`.

- [ ] Write failing API tests for member review returning 403 and linked approval returning executed only with an execution result.
- [ ] Run the focused test; expect failure because endpoints currently admit members and only change status.
- [ ] Add shared owner/admin guard; for a linked approval invoke `apply_proposal`, pass its result into `ApprovalService.approve`, and surface failures without setting executed.
- [ ] Run `cd backend && pytest app/tests/agents/test_agent_proposal_bridge.py app/tests/test_tool_registry.py -q`; expect pass.
- [ ] Commit only the changed routers and tests with message `feat: gate and audit proposal execution`.

## Plan Self-Review

- This plan covers the approval/execution slice of the spec: immutable input, policy linkage, tenancy, idempotency, audit and owner/admin control.
- Progress reporting, chat/voice routing and Hologram Hub are deliberately separate plans after this foundation is accepted.
