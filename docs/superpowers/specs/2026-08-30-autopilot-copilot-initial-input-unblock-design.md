# Autopilot/Copilot Initial-Input Unblock — Design

**Status:** Approved by user 2026-08-30, ready for planning.

## Context

Two prior rounds of work — `docs/superpowers/plans/2026-08-30-ai-compliance-production-hardening-reconciled.md` (Task 7) and `docs/superpowers/plans/2026-08-30-ai-production-safety-closure.md` (Tasks 3-5) — made `CosaDataModelGate.prepare_initial_input` fail-closed: any run through the default `openai_agents` kernel that lacks a real `DataAccessClaim` is denied with `ComplianceDenied("DATA_ACCESS_CLAIM_MISSING")` before any model call.

The safety-closure plan (Task 5) built the one legitimate source of a claim today: a direct chat message, classified by the user in the Flutter composer, validated and hashed by the API, and turned into a `DataAccessClaim` by `ComplianceResolver` using provider/model/purpose/retention pinned from the approved Company snapshot.

Its Task 3 also made `AgentSpec.model_input_capability_ref` a required field and, to satisfy that requirement, set it to `"model.input.direct-user-message"` on **all five** COSA agent specs — including `COSA_CUSTOMER_SUPPORT_AGENT_SPEC` (copilot) and `COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC` (autopilot), which do not actually take direct, user-classified chat input. Their `RunRequest.input` is a structured task descriptor (`thread_id`, `contact_id`, `intent`, `trigger_rule_id`) with no free-text content and no classification mechanism — nothing ever populates `request.metadata["direct_message_data_access"]` for them, so they can never produce a claim, so they are unconditionally denied by the fail-closed gate. This was flagged as an "ahead-of-scope, currently inert" minor finding during that task's review and has now surfaced as an active block during testing.

Investigating further: autopilot/copilot's *actual* customer content (the support thread) is not part of the initial input at all — it is fetched later via a tool call and re-enters the model as part of the multi-turn tool loop. `CosaDataModelGate.prepare_initial_input` only ever gates the first call; `CapabilityGateway` has no equivalent category-based check on tool output before it flows back into the model. So today's block is not actually protecting the sensitive data path — it denies a harmless JSON task descriptor while the real customer content, once fetched, re-enters the model with no classification-based control at all.

**Decision (user, 2026-08-30):** fix only the wrongly-scoped block on the initial input now (this document). The absence of a data-classification control on tool-fetched content re-entering the model is a separate, real, and currently unaddressed gap — out of scope here, tracked as a follow-up (see "Explicitly Out of Scope" below).

## Goal

Direct chat messages keep exactly today's behavior: no `DataAccessClaim` → deny, no exceptions. Autopilot and copilot runs, which never legitimately produce a `DataAccessClaim` for their initial input, stop being denied for that reason and fall back to the same `Redactor.sanitize()` treatment their initial input received before any of this compliance-hardening work began. No new capability is added; the fail-closed guarantee for chat is untouched; the two customer-support specs are restored to how they behaved prior to the incidental scope expansion in the prior plan's Task 3.

## Non-Goals (Explicitly Out of Scope)

- Category-based gating of tool output before it re-enters the model context for autopilot/copilot (or any spec). `aiSystemCapabilityBindings.maxDataCategory`/`.prohibitedPurpose` already exist in the Company schema but are read nowhere in the Python runtime today — this is a real, pre-existing gap, not created or closed by this change. It needs its own design once autopilot/copilot are expected to carry real customer PII safely, and must not be assumed solved because this document exists.
- Any new UI, API, or Company-side declaration mechanism for autopilot/copilot data categories (a "declared automation data profile," or similar) — rejected for this round in favor of the narrower, honest fix.
- Any change to how direct chat messages are classified, validated, or denied.

## Design

### 1. `AgentSpec.model_input_capability_ref` becomes optional

`packages/agent/contracts/spec.py`: change `model_input_capability_ref: str` (required) to `model_input_capability_ref: str | None = None`. `None` means "this spec does not take governed direct model input" — a true statement for autopilot/copilot, not a placeholder value forced into a required field. Update the existing `keep_model_input_out_of_executable_tools` validator to short-circuit when the field is `None` (`if self.model_input_capability_ref and self.model_input_capability_ref in self.capability_refs: raise ...`).

### 2. Restore autopilot/copilot specs to `None`

`apps/cosa/agents/specs.py`: set `model_input_capability_ref=None` on `COSA_CUSTOMER_SUPPORT_AGENT_SPEC` and `COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC`. Leave the chat-capable spec(s) unchanged at `"model.input.direct-user-message"`. Bump the two affected specs' `version` from `1.1.0` to `1.2.0` (content changed again since the 1.1.0 bump) — this requires the same registry re-seed the deploy-order note in `docs/runbooks/prod-cutover.md` already calls out (`cosa-api`/`cosa-worker` must deploy together).

### 3. `ComplianceResolver` stops forcing a phantom capability id

`apps/cosa/compliance/resolver.py`: the unconditional `capability_ids.append(spec.model_input_capability_ref)` must become conditional (`if spec.model_input_capability_ref: capability_ids.append(...)`), since the value can now be `None`. The existing `if not spec.model_input_capability_ref: raise ComplianceDenied(...)` guard inside the `direct_message_data_access` branch is already correct and untouched — it only runs when a caller actually supplied direct-message context, which autopilot/copilot never do.

### 4. Kernel passes the spec's declared capability into context

`packages/agent_integrations/openai_agents_sdk/kernel.py`: alongside the existing `context["root_spec_identity"] = spec.id` assignment, add `context["model_input_capability_ref"] = spec.model_input_capability_ref`. This is the only way `CosaDataModelGate` can distinguish "a compliance-gated spec with no claim" (deny) from "a spec that never declared this capability" (legacy path) — today it only checks `self._client is not None`, which is true for every run regardless of spec.

### 5. Gate denies only when the spec actually declared the capability

`apps/cosa/compliance/data_model_gate.py`, `prepare_initial_input`: change

```python
if claim is None:
    if self._client is not None:
        raise ComplianceDenied("DATA_ACCESS_CLAIM_MISSING")
    return self._redactor.sanitize(raw_input)
```

to

```python
if claim is None:
    if self._client is not None and run_context.get("model_input_capability_ref"):
        raise ComplianceDenied("DATA_ACCESS_CLAIM_MISSING")
    return self._redactor.sanitize(raw_input)
```

Update the surrounding comment block (currently states the deny branch blocks *all* real runs — no longer true) to reflect the corrected scope: deny applies only to specs that declare `model_input_capability_ref`; specs that don't declare it use the pre-existing redactor path, unchanged from before any compliance-hardening work.

## Testing

- `tests/agent/contracts/test_agent_spec.py`: `model_input_capability_ref` now accepts `None`; the "must not appear in capability_refs" validator still holds when a value is set, and is a no-op when `None`.
- `tests/apps/cosa/compliance/test_resolver.py`: a spec with `model_input_capability_ref=None` never adds a phantom entry to `capability_ids` sent to Company.
- `tests/apps/cosa/compliance/test_data_model_gate.py`: new case — `run_context` without `model_input_capability_ref` (or with it `None`/absent) and no claim → `prepare_initial_input` returns the redacted input, does **not** raise. Existing case — `run_context` with `model_input_capability_ref` set and no claim → still raises `ComplianceDenied("DATA_ACCESS_CLAIM_MISSING")` (regression guard for chat).
- `tests/apps/cosa/agents/test_customer_support_autopilot_spec.py`, `tests/apps/cosa/agents/test_specs.py`, `tests/apps/cosa/test_autopilot_run.py`, `tests/apps/cosa/test_copilot_run.py`: update for the new spec version and `model_input_capability_ref=None`.
- A focused test proving an autopilot/copilot run now reaches `RunStatus.COMPLETED` (or at least clears the initial-input gate) with no `DataAccessClaim` present anywhere in the run's metadata — this is the actual regression this document exists to fix, and it must be demonstrated, not just inferred from the unit tests above.

## Release Note to Carry Forward

Whoever picks up the tool-output category-gating gap (Non-Goals, first bullet) must read this document first: it establishes that autopilot/copilot's initial input was never the actual risk surface, and that fixing this initial-input block does **not** make it safe to route real customer PII through autopilot/copilot today.
