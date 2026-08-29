# COSA Audit Remediation — Phase 1 (P0 production-path restoration) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Customer-Support Copilot/Autopilot worker path and the Company→COSA event relay actually executable in the deployed topology, with fail-closed service credentials.

**Architecture:** Three seams are broken at baseline: (a) the worker calls `get_handler(...)` / `get_agent_spec(...)` methods that do not exist on the registries; (b) the event relay signs a JSON string on the Node side but the Python intake verifies a re-serialized dict, so HMAC digests differ on Unicode/whitespace; (c) production containers never receive the internal URLs / shared secret / service tokens, and code falls back to `127.0.0.1` + `dev-secret` + `local-dev-service-token`. This plan adds the missing registry convenience API, moves HMAC to raw request bytes on both sides, and makes missing/dev-valued credentials fail at process startup outside `development`/`test`.

**Tech Stack:** Python 3.12 (FastAPI, pydantic v2, asyncpg, httpx, pytest), TypeScript (Encore, Node `node:crypto`, vitest), Docker Compose.

## Global Constraints

- Business truth lives in `services/*`; the Agent Platform never writes business DB directly and never decides authorization (CLAUDE.md rule 1).
- `packages/agent/` must not import anything from `services/*` or `apps/cosa/` (CLAUDE.md 4-zone rule).
- Errors in Encore services use `APIError` (`invalidArgument`, `unauthenticated`, …), never bare `throw new Error` (CLAUDE.md Encore rules). Existing non-Encore helper modules (`outbox-relay.service.ts`) already throw `Error`; keep their current convention.
- Application state must be structured, never inferred from natural-language text (CLAUDE.md rule 7). Capability/spec lookup failures emit structured reason codes, not a bare `except`.
- Historical `REQUIRE_APPROVAL` constraints do not disappear when later policy loosens (CLAUDE.md rule 5). This plan does not touch governance policy.
- Every behaviour change ships with a matching test; run the test before claiming done (CLAUDE.md rule 11).
- Do not use `--force` / `--no-verify`; run `git status` before destructive steps (CLAUDE.md rule 10).
- New explanatory comments in Vietnamese (why); identifiers, log messages, verbatim English doc quotes stay English (CLAUDE.md comment rule).
- Environment gate vocabulary: `development` and `test` are permissive (dev defaults allowed); every other value of `ENVIRONMENT` (case-insensitive), including `staging` and `production`, is strict.
- Dev sentinel values that must be rejected in strict environments: `dev-secret`, `local-dev-service-token`, `local-dev-service-secret`, empty string, and any secret shorter than 32 characters.
- Commit each task directly on `main` in worktree `.claude/worktrees/cosa-workspace-canonical`. Do not push.
- End every commit message with the trailer: `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`.

---

## File Structure

**Created:**
- `apps/cosa/agents/registry_loader.py` — one function: load a registered `AgentSpec` from the spec registry by id+version, returning a typed `AgentSpec` or `None`.
- `apps/cosa/config/service_identity.py` — fail-closed reads for the shared local secret, service tokens, and internal URLs, gated by `ENVIRONMENT`.
- `tests/apps/cosa/config/test_service_identity.py` — unit tests for the gate.
- `tests/apps/cosa/agents/test_registry_loader.py` — unit tests for the loader.
- `tests/packages/agent/capabilities/test_registry_get_handler.py` — unit test for the new convenience method.
- `tests/apps/cosa/events/test_local_auth_raw_bytes.py` — unit tests for byte-exact sign/verify.

**Modified:**
- `packages/agent/capabilities/registry.py` — add `get_handler`.
- `apps/cosa/worker/copilot_run.py` — use `get_handler` + `load_registered_agent_spec`; structured reason codes; drop bare `except`.
- `apps/cosa/worker/autopilot_run.py` — same spec-resolution fix.
- `apps/cosa/events/local_auth.py` — `sign(raw: bytes)` / `verify(sig, raw: bytes)`.
- `apps/cosa/events/router.py` — `handle_event(deps, raw_body: bytes, signature)`; parse JSON inside after verify.
- `apps/cosa/api/event_intake_routes.py` — read `await request.body()`, pass raw bytes.
- `apps/cosa/events/deps.py` — construct `LocalServiceAuth` via `service_identity` helper.
- `apps/cosa/api/app.py` — call `service_identity` validation in `lifespan` before building deps.
- `apps/cosa/worker/main.py` — call `service_identity` validation at startup.
- `apps/cosa/worker/copilot_run.py` (`callback_company_result`) — resolve Company URL + token via `service_identity`.
- `services/company/events/outbox-relay.service.ts` — sign once, send the signed string; configurable internal-host allowlist; fail-closed secret.
- `services/company/commercial/services/customer-engagement/copilot-cosa-client.ts` — fail-closed token/URL in strict env.
- `apps/cosa/api/copilot_routes.py` — fail-closed service token in strict env.
- `deploy/central_vps/docker-compose.prod.yaml` — inject internal URLs + secret + tokens into `services-company`, `cosa-api`, `cosa-worker`.
- `deploy/central_vps/.env.example` (create if absent) — document the new required variables.
- Existing tests touching the changed signatures: `tests/apps/cosa/test_local_event_intake.py`, `services/company/events/tests/outbox-relay.test.ts`.

---

## Task 1: `CapabilityRegistry.get_handler` convenience method

**Files:**
- Modify: `packages/agent/capabilities/registry.py:28-29`
- Test: `tests/packages/agent/capabilities/test_registry_get_handler.py`

**Interfaces:**
- Consumes: existing `CapabilityRegistry.get(capability_id) -> CapabilityRegistration | None`, `CapabilityRegistration.handler: CapabilityHandler`.
- Produces: `CapabilityRegistry.get_handler(capability_id: str) -> CapabilityHandler | None` — returns `registration.handler` when the id is registered, else `None`.

- [ ] **Step 1: Write the failing test**

```python
# tests/packages/agent/capabilities/test_registry_get_handler.py
from agent.capabilities.registry import CapabilityRegistry
from agent.contracts.capability import CapabilitySpec


def _spec(cap_id: str) -> CapabilitySpec:
    return CapabilitySpec(id=cap_id, version="1.0.0", input_schema={}, output_schema={})


def test_get_handler_returns_registered_handler():
    reg = CapabilityRegistry()

    async def handler(payload, ctx):
        return {"ok": True}

    reg.register(_spec("engagement.thread.read"), handler)
    assert reg.get_handler("engagement.thread.read") is handler


def test_get_handler_returns_none_for_unknown_capability():
    reg = CapabilityRegistry()
    assert reg.get_handler("does.not.exist") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/packages/agent/capabilities/test_registry_get_handler.py -v`
Expected: FAIL — `AttributeError: 'CapabilityRegistry' object has no attribute 'get_handler'`.
(If `CapabilitySpec` constructor args differ, adjust `_spec` to match `agent/contracts/capability.py`; the two assertions stay the same.)

- [ ] **Step 3: Add the method**

```python
    # packages/agent/capabilities/registry.py, immediately after get()
    def get_handler(self, capability_id: str) -> CapabilityHandler | None:
        """Đường tắt đã đặt tên: trả handler đã đăng ký cho capability_id,
        hoặc None nếu chưa đăng ký. get() vẫn là API chính (trả cả spec)."""
        reg = self._capabilities.get(capability_id)
        return reg.handler if reg is not None else None
```

Also add `get_handler` mention is not needed in `__all__` (class method).

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/packages/agent/capabilities/test_registry_get_handler.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add packages/agent/capabilities/registry.py tests/packages/agent/capabilities/test_registry_get_handler.py
git commit -m "feat(agent): CapabilityRegistry.get_handler convenience accessor

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 2: Typed registered-agent-spec loader

**Files:**
- Create: `apps/cosa/agents/registry_loader.py`
- Test: `tests/apps/cosa/agents/test_registry_loader.py`

**Interfaces:**
- Consumes: `SpecRegistryRepository.get(spec_kind: str, spec_id: str, version: str) -> PublishedSpecRecord | None` from `agent.registry.repository`; `PublishedSpecRecord.content: dict`; `AgentSpec` from `agent.contracts.spec` (pydantic v2 `BaseModel`).
- Produces: `async load_registered_agent_spec(spec_registry, spec_id: str, *, version: str = "1.0.0") -> tuple[AgentSpec | None, str | None]` — returns `(spec, None)` on success; `(None, reason_code)` where `reason_code` ∈ `{"agent_spec_not_registered", "agent_spec_content_invalid"}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/cosa/agents/test_registry_loader.py
import pytest

from apps.cosa.agents.registry_loader import load_registered_agent_spec
from apps.cosa.agents.specs import COSA_CUSTOMER_SUPPORT_AGENT_SPEC
from agent.registry.repository import InMemorySpecRegistryRepository, PublishedSpecRecord


@pytest.mark.asyncio
async def test_loads_registered_agent_spec_as_typed_model():
    repo = InMemorySpecRegistryRepository()
    content = COSA_CUSTOMER_SUPPORT_AGENT_SPEC.model_dump(mode="json")
    await repo.publish(
        PublishedSpecRecord(
            spec_kind="agent",
            spec_id=COSA_CUSTOMER_SUPPORT_AGENT_SPEC.id,
            version="1.0.0",
            definition_hash="h1",
            content=content,
            status="published",
        )
    )
    spec, reason = await load_registered_agent_spec(
        repo, COSA_CUSTOMER_SUPPORT_AGENT_SPEC.id, version="1.0.0"
    )
    assert reason is None
    assert spec is not None
    assert spec.id == COSA_CUSTOMER_SUPPORT_AGENT_SPEC.id
    assert "engagement.thread.read" in spec.capability_refs


@pytest.mark.asyncio
async def test_missing_record_returns_reason_code():
    repo = InMemorySpecRegistryRepository()
    spec, reason = await load_registered_agent_spec(repo, "cosa.agents.nope", version="1.0.0")
    assert spec is None
    assert reason == "agent_spec_not_registered"


@pytest.mark.asyncio
async def test_invalid_content_returns_reason_code():
    repo = InMemorySpecRegistryRepository()
    await repo.publish(
        PublishedSpecRecord(
            spec_kind="agent",
            spec_id="cosa.agents.broken",
            version="1.0.0",
            definition_hash="h1",
            content={"not": "an agent spec"},
            status="published",
        )
    )
    spec, reason = await load_registered_agent_spec(repo, "cosa.agents.broken", version="1.0.0")
    assert spec is None
    assert reason == "agent_spec_content_invalid"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/apps/cosa/agents/test_registry_loader.py -v`
Expected: FAIL — `ModuleNotFoundError: apps.cosa.agents.registry_loader`.
(Check the real `PublishedSpecRecord` field names and `InMemorySpecRegistryRepository.publish` signature in `packages/agent/registry/repository.py` lines 84-151; adjust the fixture construction if names differ — the three assertions stay.)

- [ ] **Step 3: Implement the loader**

```python
# apps/cosa/agents/registry_loader.py
"""Load một AgentSpec đã publish trong spec registry thành model có kiểu.

Worker chỉ cần AgentSpec để guard defense-in-depth (đọc capability_refs),
không cần exact-hash resolution như SpecResolver. Trả về reason code có cấu
trúc thay vì nuốt lỗi bằng `except` (CLAUDE.md rule 7)."""

from __future__ import annotations

from typing import Any

from agent.contracts.spec import AgentSpec

__all__ = ["load_registered_agent_spec"]


async def load_registered_agent_spec(
    spec_registry: Any,
    spec_id: str,
    *,
    version: str = "1.0.0",
) -> tuple[AgentSpec | None, str | None]:
    record = await spec_registry.get("agent", spec_id, version)
    if record is None:
        return None, "agent_spec_not_registered"
    try:
        return AgentSpec.model_validate(record.content), None
    except Exception:  # pydantic ValidationError + mọi lỗi dựng model
        return None, "agent_spec_content_invalid"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/apps/cosa/agents/test_registry_loader.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add apps/cosa/agents/registry_loader.py tests/apps/cosa/agents/test_registry_loader.py
git commit -m "feat(cosa): typed loader for registered AgentSpec with reason codes

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 3: Wire the Copilot/Autopilot worker to the real registry APIs

**Files:**
- Modify: `apps/cosa/worker/copilot_run.py:68-76` (spec fetch), `:104-171` (handler lookups + bare `except`)
- Modify: `apps/cosa/worker/autopilot_run.py:69-90` (spec fetch)
- Test: `tests/apps/cosa/worker/test_copilot_run_registry_path.py` (create)

**Interfaces:**
- Consumes: `CapabilityRegistry.get_handler` (Task 1); `load_registered_agent_spec` (Task 2); existing `CosaEventStreamManager.emit(...)`; existing `callback_company_result(run_id, status)`.
- Produces: no new exported symbol. Behaviour contract: when a required capability handler is unregistered, the worker emits `run.failed` with `payload={"error": ..., "reason_code": "capability_not_registered", "capability": "<id>"}` and calls `callback_company_result(run_id, "failed")` — it does not raise out of `run_customer_support_copilot`.

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/cosa/worker/test_copilot_run_registry_path.py
import pytest

from apps.cosa.worker.copilot_run import run_customer_support_copilot


class _StubStreamRepo: ...


class _RecordingStreamMgr:
    def __init__(self):
        self.events = []

    async def emit(self, repo, *, run_id, conversation_id, event_type, payload, correlation_id):
        self.events.append({"event_type": event_type, "payload": payload})


class _EmptyCapabilityRegistry:
    def get_handler(self, capability_id):
        return None


class _Plane:
    def __init__(self):
        self.capability_registry = _EmptyCapabilityRegistry()
        self.spec_registry = None
        self.run_stream_event_repository = _StubStreamRepo()


@pytest.mark.asyncio
async def test_missing_capability_handler_fails_run_with_reason_code(monkeypatch):
    calls = []

    async def fake_callback(run_id, status, artifact_ref=None, summary_ref=None):
        calls.append((run_id, status))

    monkeypatch.setattr("apps.cosa.worker.copilot_run.callback_company_result", fake_callback)

    mgr = _RecordingStreamMgr()
    await run_customer_support_copilot(
        _Plane(),
        mgr,
        {"run_id": "run_1", "workspace_id": "ws_1", "thread_ref": {"thread_id": "t1"}},
    )

    assert ("run_1", "failed") in calls
    failed = [e for e in mgr.events if e["event_type"] == "run.failed"]
    assert failed
    assert failed[-1]["payload"].get("reason_code") == "capability_not_registered"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/apps/cosa/worker/test_copilot_run_registry_path.py -v`
Expected: FAIL — currently the missing handler is silently skipped (`if thread_handler and thread_id`), so no `run.failed` with `reason_code` is emitted and the run proceeds to the kernel. Confirm the assertion on `reason_code` fails.
(Inspect `run_customer_support_copilot`'s real signature near `copilot_run.py:55-62` and match the positional/keyword args in the test call.)

- [ ] **Step 3: Implement — spec fetch via loader**

In `copilot_run.py`, replace the `spec_registry.get_agent_spec` block:

```python
    # 1. Guard (defense in depth): check spec capabilities
    spec = COSA_CUSTOMER_SUPPORT_AGENT_SPEC
    if getattr(plane, "spec_registry", None):
        fetched_spec, spec_reason = await load_registered_agent_spec(
            plane.spec_registry, COSA_CUSTOMER_SUPPORT_AGENT_SPEC.id, version="1.0.0"
        )
        if fetched_spec is not None:
            spec = fetched_spec
        elif spec_reason == "agent_spec_content_invalid":
            logger.warning(
                "Registered copilot spec %s invalid, falling back to in-code spec (reason=%s)",
                COSA_CUSTOMER_SUPPORT_AGENT_SPEC.id,
                spec_reason,
            )
```

Add the import at the top: `from apps.cosa.agents.registry_loader import load_registered_agent_spec`.

- [ ] **Step 4: Implement — handler lookups with structured failure**

Add a helper near the top of `copilot_run.py` (module scope):

```python
async def _require_handler(
    plane: Any,
    capability_id: str,
    *,
    run_id: str,
    correlation_id: str,
    stream_repo: Any,
    stream_mgr: "CosaEventStreamManager",
) -> CapabilityHandler | None:
    """Trả handler hoặc None. Nếu None: emit run.failed có reason_code
    và callback Company failed — caller phải return ngay."""
    handler = plane.capability_registry.get_handler(capability_id)
    if handler is not None:
        return handler
    logger.error("Copilot run %s: capability not registered: %s", run_id, capability_id)
    if stream_repo:
        await stream_mgr.emit(
            stream_repo,
            run_id=run_id,
            conversation_id="",
            event_type="run.failed",
            payload={
                "error": f"capability not registered: {capability_id}",
                "reason_code": "capability_not_registered",
                "capability": capability_id,
            },
            correlation_id=correlation_id,
        )
    await callback_company_result(run_id, "failed")
    return None
```

Import `CapabilityHandler` from `agent.capabilities.registry` and reuse the existing `Any` import.

Then replace each `X_handler = plane.capability_registry.get_handler("...")` / `if X_handler and Y:` block. The three read capabilities are conditional on payload data being present, so only fail hard when the data is present but the handler is missing:

```python
        thread_context = {}
        if thread_id:
            thread_handler = await _require_handler(
                plane, "engagement.thread.read",
                run_id=run_id, correlation_id=correlation_id,
                stream_repo=stream_repo, stream_mgr=stream_mgr,
            )
            if thread_handler is None:
                return
            thread_context = await thread_handler({"thread_id": thread_id}, ctx)

        customer_360 = {}
        if contact_id:
            customer_handler = await _require_handler(
                plane, "commercial.customer_360.read",
                run_id=run_id, correlation_id=correlation_id,
                stream_repo=stream_repo, stream_mgr=stream_mgr,
            )
            if customer_handler is None:
                return
            customer_360 = await customer_handler(
                {"contact_id": contact_id, "identity_verified": identity_verified}, ctx
            )

        knowledge_profile = {}
        if knowledge_scope:
            knowledge_handler = await _require_handler(
                plane, "knowledge.profile.read",
                run_id=run_id, correlation_id=correlation_id,
                stream_repo=stream_repo, stream_mgr=stream_mgr,
            )
            if knowledge_handler is None:
                return
            knowledge_profile = await knowledge_handler(knowledge_scope, ctx)
```

Do the same for the `engagement.message.draft` handler near `copilot_run.py:167` (`draft_handler`): the draft is always required, so call `_require_handler` unconditionally and `return` if `None`.

- [ ] **Step 5: Replace the broad `except` at the end of `run_customer_support_copilot`**

Find the outer `try:` (near `copilot_run.py:91`) and its matching `except Exception as e:`. Keep a final `except Exception` for genuinely unexpected errors, but make it explicit:

```python
    except Exception as e:  # noqa: BLE001 — lỗi runtime không lường trước
        logger.exception("Copilot run %s crashed", run_id)
        if stream_repo:
            await stream_mgr.emit(
                stream_repo,
                run_id=run_id,
                conversation_id="",
                event_type="run.failed",
                payload={"error": str(e), "reason_code": "copilot_unhandled_exception"},
                correlation_id=correlation_id,
            )
        await callback_company_result(run_id, "failed")
        return
```

- [ ] **Step 6: Fix `autopilot_run.py` spec fetch**

Replace the `plane.spec_registry.get_agent_spec(COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC.id)` block (near `autopilot_run.py:71`) with the same `load_registered_agent_spec(plane.spec_registry, COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC.id, version="1.0.0")` pattern from Step 3. Import the loader. Keep the existing in-code spec as the fallback default.

- [ ] **Step 7: Run the new test + the existing worker suites**

Run:
```
.venv/bin/python -m pytest tests/apps/cosa/worker/test_copilot_run_registry_path.py -v
.venv/bin/python -m pytest tests/apps/cosa/worker -v
```
Expected: new test PASS; no regressions in the existing worker tests. If an existing test asserted the old silent-skip behaviour, update it to expect the structured `run.failed` and note the change in the commit body.

- [ ] **Step 8: Commit**

```bash
git add apps/cosa/worker/copilot_run.py apps/cosa/worker/autopilot_run.py tests/apps/cosa/worker/test_copilot_run_registry_path.py
git commit -m "fix(cosa/worker): use real registry APIs + structured reason codes on lookup failure

copilot_run/autopilot_run called get_handler()/get_agent_spec() which do
not exist on the registries; every run failed in the broad except. Now
uses CapabilityRegistry.get_handler + load_registered_agent_spec and emits
run.failed with a reason_code instead of swallowing the error.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 4: Byte-exact HMAC in `local_auth.py`

**Files:**
- Modify: `apps/cosa/events/local_auth.py`
- Test: `tests/apps/cosa/events/test_local_auth_raw_bytes.py`

**Interfaces:**
- Consumes: `COSA_LOCAL_SERVICE_SECRET` env (unchanged constructor default behaviour for now — Task 7 tightens it).
- Produces: `LocalServiceAuth.sign(raw_body: bytes) -> str`; `LocalServiceAuth.verify(signature: str, raw_body: bytes) -> bool`. Both operate on the exact bytes; no `json.dumps` inside.

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/cosa/events/test_local_auth_raw_bytes.py
import hashlib
import hmac

from apps.cosa.events.local_auth import LocalServiceAuth

SECRET = "x" * 40


def test_sign_matches_manual_hmac_over_raw_bytes():
    raw = '{"eventType":"thread.updated","note":"Xin chào — cần hỗ trợ"}'.encode("utf-8")
    auth = LocalServiceAuth(SECRET)
    expected = hmac.new(SECRET.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    assert auth.sign(raw) == expected


def test_verify_roundtrip_true_and_tamper_false():
    raw = b'{"a":1,"b":{"c":[2,3]}}'
    auth = LocalServiceAuth(SECRET)
    sig = auth.sign(raw)
    assert auth.verify(sig, raw) is True
    assert auth.verify(sig, raw + b" ") is False
    assert auth.verify("", raw) is False


def test_verify_false_when_secret_missing():
    raw = b"{}"
    assert LocalServiceAuth("").verify("deadbeef", raw) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/apps/cosa/events/test_local_auth_raw_bytes.py -v`
Expected: FAIL — current `sign` takes a `dict` and calls `json.dumps`, so `auth.sign(raw)` with `bytes` raises `TypeError`.

- [ ] **Step 3: Implement**

```python
# apps/cosa/events/local_auth.py — replace sign/verify bodies
    def sign(self, raw_body: bytes) -> str:
        return hmac.new(self._secret, raw_body, hashlib.sha256).hexdigest()

    def verify(self, signature: str, raw_body: bytes) -> bool:
        if not signature or not self._secret:
            return False
        return hmac.compare_digest(signature, self.sign(raw_body))
```

Remove the now-unused `import json`. Update the module docstring line that references `raw_body: dict`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/apps/cosa/events/test_local_auth_raw_bytes.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add apps/cosa/events/local_auth.py tests/apps/cosa/events/test_local_auth_raw_bytes.py
git commit -m "fix(cosa/events): HMAC over raw request bytes, not re-serialized dict

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 5: Intake route + `handle_event` consume raw bytes

**Files:**
- Modify: `apps/cosa/events/router.py:27-31`
- Modify: `apps/cosa/api/event_intake_routes.py:17-27`
- Modify: `tests/apps/cosa/test_local_event_intake.py` (callers of `handle_event`)
- Test: add cases in `tests/apps/cosa/test_local_event_intake.py`

**Interfaces:**
- Consumes: `LocalServiceAuth.verify(signature, raw_body: bytes)` (Task 4); `validate_envelope(dict)` (unchanged).
- Produces: `async handle_event(deps, raw_body: bytes, signature: str) -> IntakeResult` — verifies HMAC over `raw_body`, then `json.loads(raw_body)` → `validate_envelope`. Raises `Unauthenticated` on bad signature, `ValueError` on non-JSON body.

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/cosa/test_local_event_intake.py — add
import json
import pytest

from apps.cosa.events.router import handle_event, Unauthenticated


@pytest.mark.asyncio
async def test_handle_event_verifies_over_raw_bytes(intake_deps):  # existing fixture
    envelope = {
        "eventId": "evt-unicode-1",
        "workspaceId": "ws_1",
        "eventType": "thread.updated",
        "correlationId": "c1",
        "aggregateType": "thread",
        "aggregateId": "t1",
        "note": "Xin chào — cần hỗ trợ ngay",
    }
    raw = json.dumps(envelope, ensure_ascii=False).encode("utf-8")
    sig = intake_deps.local_auth.sign(raw)
    result = await handle_event(intake_deps, raw, sig)
    assert result.outcome in {"accepted", "duplicate"}


@pytest.mark.asyncio
async def test_handle_event_rejects_wrong_signature(intake_deps):
    raw = b'{"eventId":"e2","workspaceId":"ws_1","eventType":"x","correlationId":"c","aggregateType":"t","aggregateId":"a"}'
    with pytest.raises(Unauthenticated):
        await handle_event(intake_deps, raw, "not-a-valid-signature")
```

(Match the real required envelope fields in `apps/cosa/events/contracts.py :: validate_envelope`; adjust keys so the "accepted" path is reachable. Reuse whatever fixture the existing file uses to build `deps` — search the file for `local_auth` / `intake_deps` / `deps` fixtures first.)

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/apps/cosa/test_local_event_intake.py -v`
Expected: FAIL — `handle_event` still calls `deps.local_auth.verify(signature, raw_body)` with `raw_body` expected to be a dict, and `validate_envelope(raw_body)` will get `bytes`.

- [ ] **Step 3: Implement `handle_event`**

```python
# apps/cosa/events/router.py
import json
...
async def handle_event(deps: Any, raw_body: bytes, signature: str) -> IntakeResult:
    if not deps.local_auth.verify(signature, raw_body):
        raise Unauthenticated("invalid local signature")

    try:
        parsed = json.loads(raw_body)
    except (ValueError, TypeError) as e:
        raise ValueError("event body is not valid JSON") from e

    env = validate_envelope(parsed)
    ...  # rest unchanged, using `parsed`/`env` as before
```

- [ ] **Step 4: Implement the FastAPI route**

```python
# apps/cosa/api/event_intake_routes.py
        raw = await request.body()
        try:
            result = await handle_event(deps, raw, x_cosa_local_signature)
        except Unauthenticated as e:
            raise HTTPException(status_code=401, detail=str(e)) from e
        except PermissionDenied as e:
            raise HTTPException(status_code=403, detail=str(e)) from e
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
```

Delete the separate `body = await request.json()` block and its `try/except`.

- [ ] **Step 5: Update any other `handle_event` callers**

Run: `grep -rn "handle_event(" apps/ tests/` — update every call to pass `bytes` + signature. If a test built a dict, wrap with `json.dumps(...).encode()` and sign with the fixture's `local_auth.sign`.

- [ ] **Step 6: Run tests**

Run: `.venv/bin/python -m pytest tests/apps/cosa/test_local_event_intake.py apps/cosa -k "event" -v`
Expected: PASS, including the two new cases.

- [ ] **Step 7: Commit**

```bash
git add apps/cosa/events/router.py apps/cosa/api/event_intake_routes.py tests/apps/cosa/test_local_event_intake.py
git commit -m "fix(cosa/events): intake verifies HMAC over raw body bytes before JSON parse

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 6: Relay signs once and sends the signed bytes (TypeScript)

**Files:**
- Modify: `services/company/events/outbox-relay.service.ts`
- Test: `services/company/events/tests/outbox-relay.test.ts`

**Interfaces:**
- Consumes: `process.env.COSA_LOCAL_SERVICE_SECRET`; `RelayDeps.post(url, body, headers)`.
- Produces: `runRelayOnce` computes `payload = JSON.stringify(row.envelope)` once, signs `payload`, and passes `payload` (a `string`) as the body to `deps.post`. `relayTick`'s `post` implementation sends a `string` body verbatim (no second `JSON.stringify`). `RelayDeps.post` body type becomes `string`.

- [ ] **Step 1: Write the failing test**

```typescript
// services/company/events/tests/outbox-relay.test.ts — add
import { createHmac } from "node:crypto";
import { runRelayOnce } from "../outbox-relay.service";

it("sends the exact signed JSON string as the request body", async () => {
  process.env.COSA_LOCAL_SERVICE_SECRET = "x".repeat(40);
  const envelope = { eventType: "thread.updated", note: "Xin chào — cần hỗ trợ" };
  // stub claimDueOutboxEvents to return one row with this envelope
  // (follow the existing mock style in this file)
  const seen: { body: unknown; sig: string } = { body: null, sig: "" };
  await runRelayOnce({
    batchLimit: 10,
    agentOsUrl: "http://cosa-api:8000",
    post: async (_url, body, headers) => {
      seen.body = body;
      seen.sig = headers["X-COSA-Local-Signature"];
      return { status: 200, body: { outcome: "accepted" } };
    },
  });
  const expectedPayload = JSON.stringify(envelope);
  expect(seen.body).toBe(expectedPayload); // a string, byte-identical to what was signed
  expect(seen.sig).toBe(
    createHmac("sha256", "x".repeat(40)).update(expectedPayload).digest("hex"),
  );
});
```

(Match the file's existing mocking approach for `claimDueOutboxEvents` / `completeOutboxEvent` — search the test file. `agentOsUrl: "http://cosa-api:8000"` also exercises Task 9's allowlist; if Task 9 is not yet merged, use `"http://127.0.0.1:8081"` here and update in Task 9.)

- [ ] **Step 2: Run to verify failure**

Run: `cd services/company && npx vitest run events/tests/outbox-relay.test.ts`
Expected: FAIL — `seen.body` is currently the `row.envelope` object, not the JSON string.

- [ ] **Step 3: Implement**

```typescript
// outbox-relay.service.ts
export interface RelayDeps {
  post: (url: string, body: string, headers: Record<string, string>) => Promise<{ status: number; body: any }>;
  batchLimit: number;
  agentOsUrl: string;
}

export async function runRelayOnce(deps: RelayDeps): Promise<void> {
  assertInternalTarget(deps.agentOsUrl); // renamed in Task 9; keep assertLocalTarget until then
  const rows = await claimDueOutboxEvents("company-relay", deps.batchLimit);
  const secret = requireLocalServiceSecret(); // Task 8; until then: process.env.COSA_LOCAL_SERVICE_SECRET ?? ""
  for (const row of rows) {
    const payload = JSON.stringify(row.envelope);
    const sig = createHmac("sha256", secret).update(payload).digest("hex");
    try {
      const res = await deps.post(`${deps.agentOsUrl}/agent/internal/events`, payload, {
        "X-COSA-Local-Signature": sig,
        "Content-Type": "application/json",
      });
      // ...outcome handling unchanged...
```

```typescript
export async function relayTick(): Promise<void> {
  await runRelayOnce({
    post: async (url, body, headers) => {
      const r = await fetch(url, { method: "POST", body, headers }); // body is already a JSON string
      return { status: r.status, body: await r.json().catch(() => ({})) };
    },
    batchLimit: Number(process.env.COSA_RELAY_BATCH_LIMIT || 50),
    agentOsUrl: process.env.COSA_AGENTOS_INTAKE_URL || "http://127.0.0.1:8000",
  });
}
```

Note the default target change `8081` → `8000` (intake lives in `cosa-api`, port 8000).

- [ ] **Step 4: Run to verify pass**

Run: `cd services/company && npx vitest run events/tests/outbox-relay.test.ts`
Expected: PASS.

- [ ] **Step 5: Typecheck**

Run: `cd services/company && npx tsc --noEmit` (or `make typecheck` target for services). Fix any callers of `RelayDeps.post` broken by the `body: string` change.
Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add services/company/events/outbox-relay.service.ts services/company/events/tests/outbox-relay.test.ts
git commit -m "fix(company/events): relay sends the exact signed JSON string (wire-compatible HMAC)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 7: Fail-closed service identity (Python)

**Files:**
- Create: `apps/cosa/config/service_identity.py`
- Test: `tests/apps/cosa/config/test_service_identity.py`
- Modify: `apps/cosa/events/deps.py:106`, `apps/cosa/api/app.py` (lifespan), `apps/cosa/worker/main.py` (`main`), `apps/cosa/worker/copilot_run.py` (`callback_company_result`), `apps/cosa/api/copilot_routes.py`

**Interfaces:**
- Consumes: `os.environ`.
- Produces:
  - `is_strict_env() -> bool` — `True` unless `ENVIRONMENT`/`APP_ENV` (first set, lowercased) is `development` or `test` (default when unset: `development` → non-strict, matching `app.py:96`).
  - `require_local_service_secret() -> str` — returns the secret; raises `ServiceIdentityError` in strict env when missing, `< 32` chars, or in the dev-sentinel set.
  - `require_service_token(env_var: str, *, purpose: str) -> str` — same rules for `COSA_SERVICE_TOKEN`, `COSA_WORKER_SERVICE_TOKEN`.
  - `require_internal_url(env_var: str, *, purpose: str, default_dev: str) -> str` — in strict env requires the var be set and not a loopback host (`127.0.0.1`, `localhost`, `::1`); in non-strict env returns `default_dev` when unset.
  - `validate_service_identity(*, need_secret: bool, tokens: list[str], urls: list[tuple[str, str]]) -> None` — batch check for startup; raises `ServiceIdentityError` listing every problem.
  - `class ServiceIdentityError(RuntimeError)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/apps/cosa/config/test_service_identity.py
import pytest

from apps.cosa.config.service_identity import (
    ServiceIdentityError,
    is_strict_env,
    require_internal_url,
    require_local_service_secret,
    require_service_token,
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in ("ENVIRONMENT", "APP_ENV", "COSA_LOCAL_SERVICE_SECRET",
              "COSA_SERVICE_TOKEN", "COSA_WORKER_SERVICE_TOKEN", "COMPANY_SERVICE_URL"):
        monkeypatch.delenv(k, raising=False)


def test_dev_env_is_not_strict_and_allows_defaults(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    assert is_strict_env() is False
    assert require_internal_url(
        "COMPANY_SERVICE_URL", purpose="callback", default_dev="http://127.0.0.1:4000"
    ) == "http://127.0.0.1:4000"


def test_production_rejects_missing_secret(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(ServiceIdentityError):
        require_local_service_secret()


def test_production_rejects_dev_sentinel_token(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("COSA_SERVICE_TOKEN", "local-dev-service-token")
    with pytest.raises(ServiceIdentityError):
        require_service_token("COSA_SERVICE_TOKEN", purpose="company callback")


def test_production_rejects_short_secret(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("COSA_LOCAL_SERVICE_SECRET", "tooshort")
    with pytest.raises(ServiceIdentityError):
        require_local_service_secret()


def test_production_accepts_strong_values(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("COSA_LOCAL_SERVICE_SECRET", "s" * 40)
    monkeypatch.setenv("COMPANY_SERVICE_URL", "http://services-company:4000")
    assert require_local_service_secret() == "s" * 40
    assert require_internal_url(
        "COMPANY_SERVICE_URL", purpose="callback", default_dev="http://127.0.0.1:4000"
    ) == "http://services-company:4000"


def test_production_rejects_loopback_internal_url(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("COMPANY_SERVICE_URL", "http://127.0.0.1:4000")
    with pytest.raises(ServiceIdentityError):
        require_internal_url("COMPANY_SERVICE_URL", purpose="callback", default_dev="x")
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/apps/cosa/config/test_service_identity.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement `service_identity.py`**

```python
# apps/cosa/config/service_identity.py
"""Fail-closed đọc credential/URL nội bộ giữa các plane.

`development` / `test` cho phép giá trị mặc định để không phá DX local. Mọi
giá trị ENVIRONMENT khác (staging, production, …) là strict: thiếu / quá
ngắn / bằng giá trị dev-sentinel ⇒ raise ngay ở startup, không đợi request."""

from __future__ import annotations

import os

__all__ = [
    "ServiceIdentityError",
    "is_strict_env",
    "require_internal_url",
    "require_local_service_secret",
    "require_service_token",
    "validate_service_identity",
]

_DEV_SENTINELS = frozenset(
    {"", "dev-secret", "local-dev-service-token", "local-dev-service-secret"}
)
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "0.0.0.0"})
_MIN_SECRET_LEN = 32


class ServiceIdentityError(RuntimeError):
    pass


def is_strict_env() -> bool:
    raw = os.environ.get("ENVIRONMENT") or os.environ.get("APP_ENV") or "development"
    return raw.strip().lower() not in {"development", "dev", "local", "test"}


def _reject_value(name: str, value: str) -> list[str]:
    problems: list[str] = []
    if value in _DEV_SENTINELS:
        problems.append(f"{name} is unset or a known development value")
    elif len(value) < _MIN_SECRET_LEN:
        problems.append(f"{name} must be at least {_MIN_SECRET_LEN} characters")
    return problems


def require_local_service_secret() -> str:
    value = os.environ.get("COSA_LOCAL_SERVICE_SECRET", "")
    if not is_strict_env():
        return value or "dev-secret"
    problems = _reject_value("COSA_LOCAL_SERVICE_SECRET", value)
    if problems:
        raise ServiceIdentityError("; ".join(problems))
    return value


def require_service_token(env_var: str, *, purpose: str) -> str:
    value = os.environ.get(env_var, "")
    if not is_strict_env():
        return value or "local-dev-service-token"
    problems = _reject_value(env_var, value)
    if problems:
        raise ServiceIdentityError(f"{'; '.join(problems)} (needed for {purpose})")
    return value


def require_internal_url(env_var: str, *, purpose: str, default_dev: str) -> str:
    value = os.environ.get(env_var, "")
    if not is_strict_env():
        return value or default_dev
    if not value:
        raise ServiceIdentityError(f"{env_var} is required in strict environments (for {purpose})")
    from urllib.parse import urlparse

    host = (urlparse(value).hostname or "").lower()
    if host in _LOOPBACK_HOSTS:
        raise ServiceIdentityError(
            f"{env_var}={value!r} points at a loopback host; use the internal service DNS name (for {purpose})"
        )
    return value


def validate_service_identity(
    *,
    need_secret: bool,
    tokens: list[tuple[str, str]],
    urls: list[tuple[str, str, str]],
) -> None:
    """Batch startup check. `tokens`: (env_var, purpose). `urls`: (env_var, purpose, default_dev)."""
    problems: list[str] = []
    if need_secret:
        try:
            require_local_service_secret()
        except ServiceIdentityError as e:
            problems.append(str(e))
    for env_var, purpose in tokens:
        try:
            require_service_token(env_var, purpose=purpose)
        except ServiceIdentityError as e:
            problems.append(str(e))
    for env_var, purpose, default_dev in urls:
        try:
            require_internal_url(env_var, purpose=purpose, default_dev=default_dev)
        except ServiceIdentityError as e:
            problems.append(str(e))
    if problems:
        raise ServiceIdentityError(
            "service identity validation failed:\n  - " + "\n  - ".join(problems)
        )
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/bin/python -m pytest tests/apps/cosa/config/test_service_identity.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Wire into API startup**

In `apps/cosa/api/app.py` `lifespan`, right after `app.state.plane = build_cosa_agent_plane()` and before `build_event_intake_deps`:

```python
            from apps.cosa.config.service_identity import validate_service_identity

            validate_service_identity(
                need_secret=True,
                tokens=[
                    ("COSA_SERVICE_TOKEN", "company callback auth"),
                    ("COSA_WORKER_SERVICE_TOKEN", "scheduler → worker auth"),
                ],
                urls=[("COMPANY_SERVICE_URL", "company callback", "http://127.0.0.1:4000")],
            )
```

- [ ] **Step 6: Wire into worker startup**

In `apps/cosa/worker/main.py :: main()`, near the top before the worker loop starts:

```python
    from apps.cosa.config.service_identity import validate_service_identity

    validate_service_identity(
        need_secret=False,
        tokens=[("COSA_SERVICE_TOKEN", "company callback auth")],
        urls=[("COMPANY_SERVICE_URL", "company callback", "http://127.0.0.1:4000")],
    )
```

- [ ] **Step 7: Use helpers at the call sites**

- `apps/cosa/events/deps.py:106` — `local_auth=LocalServiceAuth(require_local_service_secret())` (import from `apps.cosa.config.service_identity`).
- `apps/cosa/worker/copilot_run.py :: callback_company_result` — replace the two `os.environ.get(..., "<dev default>")` lines with `require_internal_url("COMPANY_SERVICE_URL", purpose="copilot callback", default_dev="http://127.0.0.1:4000")` and `require_service_token("COSA_SERVICE_TOKEN", purpose="copilot callback")`.
- `apps/cosa/api/copilot_routes.py` — find the `local-dev-service-token` fallback; replace with `require_service_token("COSA_SERVICE_TOKEN", purpose="copilot route auth")`.

- [ ] **Step 8: Run the affected suites**

Run:
```
.venv/bin/python -m pytest tests/apps/cosa/config tests/apps/cosa/events tests/apps/cosa/worker tests/apps/cosa/api -k "copilot or event or intake or identity" -v
ENVIRONMENT=test .venv/bin/python -m pytest tests/apps/cosa -q
```
Expected: PASS. Existing tests run with `ENVIRONMENT` unset or `test` → non-strict, so dev defaults still resolve.

- [ ] **Step 9: Commit**

```bash
git add apps/cosa/config/service_identity.py tests/apps/cosa/config/test_service_identity.py apps/cosa/api/app.py apps/cosa/worker/main.py apps/cosa/events/deps.py apps/cosa/worker/copilot_run.py apps/cosa/api/copilot_routes.py
git commit -m "feat(cosa/config): fail-closed service identity; wire into api + worker startup

Missing/short/dev-sentinel secrets, tokens, and loopback internal URLs now
raise at process startup in staging/production. development/test keep dev
defaults.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 8: Fail-closed secret/token in the relay + copilot client (TypeScript)

**Files:**
- Modify: `services/company/events/outbox-relay.service.ts`
- Modify: `services/company/commercial/services/customer-engagement/copilot-cosa-client.ts`
- Test: `services/company/events/tests/outbox-relay.test.ts`

**Interfaces:**
- Consumes: `process.env.ENVIRONMENT` / `process.env.NODE_ENV`; `process.env.COSA_LOCAL_SERVICE_SECRET`, `process.env.COSA_SERVICE_TOKEN`, `process.env.COSA_INTERNAL_URL`.
- Produces: `requireLocalServiceSecret(): string` and `requireCosaServiceToken(): string` helpers in a shared module `services/company/shared/events/service-identity.ts` — throw when strict env (`ENVIRONMENT`/`NODE_ENV` not in `development`/`test`) and value missing/`< 32`/dev sentinel.

- [ ] **Step 1: Write the failing test**

```typescript
// outbox-relay.test.ts — add
import { runRelayOnce } from "../outbox-relay.service";

it("throws in production when COSA_LOCAL_SERVICE_SECRET is a dev value", async () => {
  process.env.ENVIRONMENT = "production";
  process.env.COSA_LOCAL_SERVICE_SECRET = "dev-secret";
  await expect(
    runRelayOnce({
      batchLimit: 1,
      agentOsUrl: "http://cosa-api:8000",
      post: async () => ({ status: 200, body: { outcome: "accepted" } }),
    }),
  ).rejects.toThrow(/development value|required/i);
  delete process.env.ENVIRONMENT;
  process.env.COSA_LOCAL_SERVICE_SECRET = "x".repeat(40);
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd services/company && npx vitest run events/tests/outbox-relay.test.ts`
Expected: FAIL — currently `runRelayOnce` uses `process.env.COSA_LOCAL_SERVICE_SECRET || "dev-secret"` and never throws.

- [ ] **Step 3: Implement the shared helper**

```typescript
// services/company/shared/events/service-identity.ts
const DEV_SENTINELS = new Set(["", "dev-secret", "local-dev-service-token", "local-dev-service-secret"]);
const MIN_LEN = 32;

function strict(): boolean {
  const raw = (process.env.ENVIRONMENT || process.env.NODE_ENV || "development").trim().toLowerCase();
  return !["development", "dev", "local", "test"].includes(raw);
}

function requireValue(name: string, value: string): string {
  if (!strict()) return value || "dev-secret";
  if (DEV_SENTINELS.has(value)) throw new Error(`${name} is unset or a known development value`);
  if (value.length < MIN_LEN) throw new Error(`${name} must be at least ${MIN_LEN} characters`);
  return value;
}

export function requireLocalServiceSecret(): string {
  return requireValue("COSA_LOCAL_SERVICE_SECRET", process.env.COSA_LOCAL_SERVICE_SECRET ?? "");
}

export function requireCosaServiceToken(): string {
  return requireValue("COSA_SERVICE_TOKEN", process.env.COSA_SERVICE_TOKEN ?? "");
}
```

- [ ] **Step 4: Use it**

- `outbox-relay.service.ts`: `const secret = requireLocalServiceSecret();` (replaces the `|| "dev-secret"` line).
- `copilot-cosa-client.ts`: find the `local-dev-service-token` / `127.0.0.1:8000` fallbacks; replace the token with `requireCosaServiceToken()` and read the base URL from `process.env.COSA_INTERNAL_URL` (throw via a small `requireInternalUrl` mirror if strict and unset — add to the shared module the same way).

- [ ] **Step 5: Run + typecheck**

Run:
```
cd services/company && npx vitest run events/tests/outbox-relay.test.ts && npx tsc --noEmit
```
Expected: PASS + clean typecheck. Update other tests that rely on the old silent `dev-secret` default to set `process.env.COSA_LOCAL_SERVICE_SECRET = "x".repeat(40)` in their setup.

- [ ] **Step 6: Commit**

```bash
git add services/company/shared/events/service-identity.ts services/company/events/outbox-relay.service.ts services/company/commercial/services/customer-engagement/copilot-cosa-client.ts services/company/events/tests/outbox-relay.test.ts
git commit -m "feat(company): fail-closed COSA secret/token in relay + copilot client

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 9: Configurable internal-host allowlist for the relay target

**Files:**
- Modify: `services/company/events/outbox-relay.service.ts:4-11`
- Test: `services/company/events/tests/outbox-relay.test.ts`

**Interfaces:**
- Consumes: `process.env.COSA_INTERNAL_HOST_ALLOWLIST` (CSV of hostnames).
- Produces: `assertInternalTarget(url: string): void` — replaces `assertLocalTarget`. Allows a host when it is in the allowlist. Default allowlist when the env var is unset: `cosa-api,services-company,127.0.0.1,localhost,::1`. Keeps the `.local` suffix allowance. Throws `Error` (module keeps its current convention) otherwise.

- [ ] **Step 1: Write the failing test**

```typescript
// outbox-relay.test.ts — add
import { assertInternalTarget } from "../outbox-relay.service";

it("allows configured docker service DNS names and rejects the rest", () => {
  delete process.env.COSA_INTERNAL_HOST_ALLOWLIST;
  expect(() => assertInternalTarget("http://cosa-api:8000")).not.toThrow();
  expect(() => assertInternalTarget("http://127.0.0.1:8000")).not.toThrow();
  expect(() => assertInternalTarget("http://evil.example.com/x")).toThrow(/allowlist|internal/i);

  process.env.COSA_INTERNAL_HOST_ALLOWLIST = "intake.internal";
  expect(() => assertInternalTarget("http://intake.internal:8000")).not.toThrow();
  expect(() => assertInternalTarget("http://cosa-api:8000")).toThrow();
  delete process.env.COSA_INTERNAL_HOST_ALLOWLIST;
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd services/company && npx vitest run events/tests/outbox-relay.test.ts`
Expected: FAIL — `assertInternalTarget` is not exported; `assertLocalTarget("http://cosa-api:8000")` currently throws.

- [ ] **Step 3: Implement**

```typescript
const DEFAULT_INTERNAL_HOSTS = ["cosa-api", "services-company", "127.0.0.1", "localhost", "::1"];

export function assertInternalTarget(url: string): void {
  const host = new URL(url).hostname;
  const allow = (process.env.COSA_INTERNAL_HOST_ALLOWLIST
    ? process.env.COSA_INTERNAL_HOST_ALLOWLIST.split(",")
    : DEFAULT_INTERNAL_HOSTS
  ).map((h) => h.trim()).filter(Boolean);
  if (!allow.includes(host) && !host.endsWith(".local")) {
    throw new Error(`relay target host ${host} not in internal allowlist [${allow.join(", ")}]`);
  }
}
```

Replace the `assertLocalTarget(deps.agentOsUrl)` call in `runRelayOnce` with `assertInternalTarget(deps.agentOsUrl)`. Keep a re-export `export const assertLocalTarget = assertInternalTarget;` only if `grep -rn "assertLocalTarget" services/` finds other importers — otherwise delete the old name.

- [ ] **Step 4: Run to verify pass**

Run: `cd services/company && npx vitest run events/tests/outbox-relay.test.ts && npx tsc --noEmit`
Expected: PASS + clean.

- [ ] **Step 5: Commit**

```bash
git add services/company/events/outbox-relay.service.ts services/company/events/tests/outbox-relay.test.ts
git commit -m "fix(company/events): configurable internal-host allowlist for relay target

Docker service DNS names like cosa-api were rejected by the hard-coded
loopback-only check.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 10: Production compose wiring

**Files:**
- Modify: `deploy/central_vps/docker-compose.prod.yaml` (`services-company`, `cosa-api`, `cosa-worker` `environment:` blocks)
- Create: `deploy/central_vps/.env.example` (if absent — else append)
- Test: `deploy/central_vps/smoke/test_compose_env_contract.py` (create) — static assertion, no containers

**Interfaces:**
- Consumes: `${COSA_LOCAL_SERVICE_SECRET}`, `${COSA_SERVICE_TOKEN}`, `${COSA_WORKER_SERVICE_TOKEN}` from the deploy `.env`.
- Produces: each of the three services receives the internal URLs + credentials it needs; compose fails (`:?`) when a required var is unset.

- [ ] **Step 1: Write the failing test**

```python
# deploy/central_vps/smoke/test_compose_env_contract.py
import pathlib
import yaml

COMPOSE = pathlib.Path(__file__).parents[1] / "docker-compose.prod.yaml"


def _env(service: str) -> dict:
    doc = yaml.safe_load(COMPOSE.read_text())
    return dict(doc["services"][service]["environment"])


def test_company_has_cosa_internal_wiring():
    e = _env("services-company")
    assert e["COSA_INTERNAL_URL"] == "http://cosa-api:8000"
    assert e["COSA_AGENTOS_INTAKE_URL"] == "http://cosa-api:8000"
    assert "${COSA_LOCAL_SERVICE_SECRET:?" in e["COSA_LOCAL_SERVICE_SECRET"]
    assert "${COSA_SERVICE_TOKEN:?" in e["COSA_SERVICE_TOKEN"]
    assert "${COSA_WORKER_SERVICE_TOKEN:?" in e["COSA_WORKER_SERVICE_TOKEN"]


def test_cosa_api_has_secret_and_tokens():
    e = _env("cosa-api")
    assert "${COSA_LOCAL_SERVICE_SECRET:?" in e["COSA_LOCAL_SERVICE_SECRET"]
    assert "${COSA_SERVICE_TOKEN:?" in e["COSA_SERVICE_TOKEN"]
    assert "${COSA_WORKER_SERVICE_TOKEN:?" in e["COSA_WORKER_SERVICE_TOKEN"]


def test_worker_has_company_url_and_token():
    e = _env("cosa-worker")
    assert e["COMPANY_SERVICE_URL"] == "http://services-company:4000"
    assert "${COSA_SERVICE_TOKEN:?" in e["COSA_SERVICE_TOKEN"]
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest deploy/central_vps/smoke/test_compose_env_contract.py -v`
Expected: FAIL — `KeyError: 'COSA_INTERNAL_URL'` etc.

- [ ] **Step 3: Edit the compose file**

`services-company` `environment:` — add:
```yaml
      COSA_INTERNAL_URL: http://cosa-api:8000
      COSA_AGENTOS_INTAKE_URL: http://cosa-api:8000
      COSA_LOCAL_SERVICE_SECRET: ${COSA_LOCAL_SERVICE_SECRET:?COSA_LOCAL_SERVICE_SECRET required}
      COSA_SERVICE_TOKEN: ${COSA_SERVICE_TOKEN:?COSA_SERVICE_TOKEN required}
      COSA_WORKER_SERVICE_TOKEN: ${COSA_WORKER_SERVICE_TOKEN:?COSA_WORKER_SERVICE_TOKEN required}
      COSA_INTERNAL_HOST_ALLOWLIST: cosa-api,services-company,127.0.0.1,localhost
```

`cosa-api` `environment:` — add:
```yaml
      COSA_LOCAL_SERVICE_SECRET: ${COSA_LOCAL_SERVICE_SECRET:?COSA_LOCAL_SERVICE_SECRET required}
      COSA_SERVICE_TOKEN: ${COSA_SERVICE_TOKEN:?COSA_SERVICE_TOKEN required}
      COSA_WORKER_SERVICE_TOKEN: ${COSA_WORKER_SERVICE_TOKEN:?COSA_WORKER_SERVICE_TOKEN required}
```

`cosa-worker` `environment:` — add:
```yaml
      COMPANY_SERVICE_URL: http://services-company:4000
      COSA_SERVICE_TOKEN: ${COSA_SERVICE_TOKEN:?COSA_SERVICE_TOKEN required}
```

- [ ] **Step 4: Create `deploy/central_vps/.env.example`**

Append (or create with a header) the new required vars with placeholder values and a one-line comment each:
```bash
# Shared HMAC secret between services-company relay and cosa-api event intake (>= 32 chars)
COSA_LOCAL_SERVICE_SECRET=
# Service token services-company -> cosa-api copilot routes, and cosa-worker -> services-company callback
COSA_SERVICE_TOKEN=
# Service token cosa-api scheduler -> cosa-worker
COSA_WORKER_SERVICE_TOKEN=
```

- [ ] **Step 5: Validate compose syntax + run the contract test**

Run:
```
cd deploy/central_vps && docker compose -f docker-compose.prod.yaml config -q
cd /Volumes/SSD/javis-saas/.claude/worktrees/cosa-workspace-canonical && .venv/bin/python -m pytest deploy/central_vps/smoke/test_compose_env_contract.py -v
```
Expected: `config -q` prints nothing (valid) or only warns about unset vars; the pytest contract test passes. If `docker compose` is unavailable in the environment, skip the first command and note it.

- [ ] **Step 6: Commit**

```bash
git add deploy/central_vps/docker-compose.prod.yaml deploy/central_vps/.env.example deploy/central_vps/smoke/test_compose_env_contract.py
git commit -m "feat(deploy): inject COSA internal URLs + shared secret + service tokens into prod compose

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Final verification (run before declaring Phase 1 done)

- [ ] `ENVIRONMENT=test .venv/bin/python -m pytest tests/apps/cosa packages/agent -q` — green (or no worse than the Phase 0 baseline of 1 known MCP failure, addressed in Phase 3).
- [ ] `cd services/company && npx vitest run events && npx tsc --noEmit` — green.
- [ ] `.venv/bin/python -m ruff check apps/cosa/agents/registry_loader.py apps/cosa/config/service_identity.py apps/cosa/events/local_auth.py apps/cosa/events/router.py apps/cosa/worker/copilot_run.py apps/cosa/worker/autopilot_run.py` — no new findings in the touched files.
- [ ] `grep -rn "get_agent_spec\|get_handler(" apps/cosa/worker/` — `get_handler` calls remain (now valid), zero `get_agent_spec`.
- [ ] `grep -rn "dev-secret\|local-dev-service-token" services/company/events apps/cosa/events apps/cosa/worker/copilot_run.py apps/cosa/api/copilot_routes.py` — only inside the sentinel sets / non-strict fallbacks, never as a bare `||` / `or` default on a hot path.
- [ ] Phase 2 plan (cross-language HMAC contract test, non-mocked Copilot vertical test, compose smoke test) is written next — Phase 1 is not merged to any shared branch until Phase 2's smoke test exists and passes (spec "Thứ tự merge").

---

## Self-Review notes

- **Spec coverage:** design §1a → Tasks 1–3; §1b → Tasks 4–6; §1c → Tasks 7–8; §1d → Tasks 9–10. All Phase 1 items covered.
- **Deferred to later phases (by design):** Phase 2 verification tests, Phase 3 quality gate, Phase 4 docs/refactor/deps — separate plans.
- **Type consistency:** `load_registered_agent_spec` returns `tuple[AgentSpec | None, str | None]` in Task 2 and is consumed with that shape in Task 3. `RelayDeps.post` body type goes `unknown → string` in Task 6 and is used as `string` in Tasks 8–9. `assertLocalTarget → assertInternalTarget` renamed in Task 9; Task 6 references the rename with an inline note for ordering.
- **Ordering:** Tasks 1→2→3 sequential (3 consumes 1+2). Tasks 4→5 sequential. Task 6 depends on nothing but shares a file with 8+9 — do 6, then 8, then 9 to minimise rebase. Task 7 independent of TS tasks. Task 10 last (references env names finalised in 7–9).
