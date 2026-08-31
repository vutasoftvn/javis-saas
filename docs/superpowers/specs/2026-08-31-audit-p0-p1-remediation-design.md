# Audit P0/P1 Remediation Design

**Status:** Approved for implementation planning

**Date:** 2026-08-31

## Goal

Restore a truthful, reproducible release baseline by closing the confirmed Agent-to-Company runtime-signal delivery defect and making the repository's declared quality gates pass without weakening type safety, contract checks, or test coverage.

## Evidence

The 2026-08-31 audit established the following current facts:

1. apps/cosa/events/runtime_signal.py publishes POST /events/agent-runtime-signals, while Company exposes POST /events/internal/agent-runtime-signal. The present unit test captures only the request body, so it cannot catch a wrong URL or missing internal-auth header.
2. make lint fails on two unused Python imports and make typecheck-py fails on ten type errors. The largest semantic error is the ExecutionKernel.stream protocol: its coroutine declaration does not match the async-generator implementations, and the OpenAI Agents SDK adapter lacks the method.
3. make contract-freeze-check fails only because the generated Company usage inventory has 864 REVIEW occurrences while the generator finds 873.
4. The existing frontend analyze and test suites pass, but coverage is 48.20% with no enforced baseline; typed-result migration, boundary decomposition, coverage policy, and security/container hardening are broader initiatives already covered by the approved MVP design and existing implementation plans.
5. Four documents referenced as architecture source of truth were intentionally removed in commit 34507dd9. Their removal must be classified before a historical copy is restored or a new canonical successor is written.

## Scope

This remediation is deliberately narrow:

- Fix the runtime-signal HTTP contract and add both publisher and real-service contract proof.
- Repair the current Python lint and mypy failures through correct interfaces and narrowed values, not casts or ignores.
- Regenerate the committed Company usage inventory and prove the freeze check.
- Record release evidence and link the result to the already-approved program plans.

It does not redesign the four-plane topology, add a microservice, alter a database migration, change product capability behavior, change deployment settings, rotate credentials, or introduce a generated multi-language contract system in the same emergency remediation.

## Design decisions

### Runtime-signal contract

Company's handler is authoritative for the internal endpoint contract. COSA publishes exactly:

    POST /events/internal/agent-runtime-signal
    Authorization: Bearer <shared service token>
    Content-Type: application/json

The publisher test must assert the URL, method, internal authorization header, and JSON envelope. A real Company HTTP test must make the same request against the Company process and assert its durable idempotent projection or expected accepted response. Mock-only proof is insufficient for this cross-language boundary.

The current raw literal is corrected now. A manifest/code-generation solution is a follow-on only after the shared-contract owner and backward compatibility policy are approved; it would be disproportionate to use it to repair one urgent endpoint.

### Execution kernel streaming contract

ExecutionKernel.stream represents a callable that returns an AsyncIterator, so its protocol declaration is a normal def, not async def. Implementations may remain async generators. Every selectable runtime must satisfy the complete protocol:

- Manual Tool Loop, LangChain, Google ADK, and Pydantic AI already expose the async-generator behavior.
- Real OpenAI Agents SDK receives the same post-run event-adapter behavior: execute run, read the owned event store, and yield the normalized event envelope.

This preserves callers' existing async-for kernel.stream(...) form. No caller awaits stream, and a runtime cannot be advertised as a selectable ExecutionKernel without a conforming method.

### Type safety

GatewayExecutionResult remains the sole gateway return value on allow and deny paths. Optional deny detail is normalized at the boundary before it is persisted, so the idempotency-failure API never receives None. The seed function overload ambiguity is fixed by using a typed registration representation or separate typed registrations; Any, cast, type-ignore comments, and protocol-silencing assignments are not accepted as remediation.

### Architecture documents

The removed documents are not automatically restored. A named architecture owner must select one of these paths before the documentation task begins:

1. retain them as deleted and correct all source-of-truth references;
2. restore immutable historical snapshots under an archive with commit SHA and a non-canonical label; or
3. write a short canonical successor that supersedes them and points to active ADRs and plans.

## Acceptance criteria

- A runtime signal reaches the exact Company handler route under real HTTP, and a wrong path or missing authorization makes the test fail.
- make lint, make typecheck-py, and make contract-freeze-check pass from a clean checkout.
- Targeted behavior tests pass for gateway deny handling, kernel streaming, seed registration, and runtime-signal delivery.
- Existing full Python unit, COSA, Company, frontend, boundary, and TypeScript typecheck evidence remains green.
- The generated inventory change contains only evidence produced from the current source tree.
- The release note records commands, result, commit SHA, and any intentionally deferred program work.

## Related plans

- docs/superpowers/plans/2026-08-31-audit-p0-p1-remediation.md is the executable repair plan for this design.
- docs/superpowers/plans/2026-08-31-maintainable-mvp-agent-control-e2e.md owns full MVP runtime/control-plane E2E expansion.
- docs/superpowers/plans/2026-08-31-backend-frontend-security-quality-remediation.md owns the broader tenant, landing, security, and quality program.
- docs/superpowers/specs/2026-08-31-maintainable-modular-truthful-mvp-design.md remains the approved architecture for frontend modularization, typed failures, coverage policy, and broad contract-first migration.

