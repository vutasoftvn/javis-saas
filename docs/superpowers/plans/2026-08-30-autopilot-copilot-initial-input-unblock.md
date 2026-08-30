# Autopilot/Copilot Initial-Input Unblock Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop `CosaDataModelGate.prepare_initial_input` from denying autopilot/copilot runs at their initial input, without weakening the existing deny-when-claim-missing guarantee for chat.

**Architecture:** `AgentSpec.model_input_capability_ref` becomes optional (`None` = "this spec does not take governed direct model input"). Autopilot/copilot specs are restored to `None` — their previous, incidental value was scope creep from an unrelated task. The kernel forwards the spec's declared value into `run_context`; the gate denies for missing claim only when the spec actually declared the capability, otherwise it falls back to the pre-existing `Redactor.sanitize()` path.

**Tech Stack:** Python, Pydantic, pytest, pytest-asyncio.

**Spec:** docs/superpowers/specs/2026-08-30-autopilot-copilot-initial-input-unblock-design.md

## Global Constraints

- Work directly on `main`; do not create a git worktree.
- Direct chat messages must keep exactly today's fail-closed behavior: no `DataAccessClaim` → `ComplianceDenied("DATA_ACCESS_CLAIM_MISSING")`, no exceptions, zero model calls.
- This plan does not add, design, or stub any category-based gating of tool output re-entering the model context. That gap stays open and undocumented-as-solved; do not touch `packages/agent/capabilities/gateway.py`'s tool-output handling as part of this plan.
- Every behavior change begins with a focused failing test and ends with that test passing before commit.

---

### Task 1: Make `AgentSpec.model_input_capability_ref` optional

**Files:**
- Modify: `packages/agent/contracts/spec.py:38,52-56`
- Modify: `tests/agent/contracts/test_agent_spec.py:8-10`

**Interfaces:**
- Consumes: nothing new.
- Produces: `AgentSpec.model_input_capability_ref: str | None`, default `None`. `keep_model_input_out_of_executable_tools` validator becomes a no-op when the field is `None`.

- [ ] **Step 1: Write the failing test**

Replace the test asserting the field is required with one asserting it defaults to `None`:

```python
def test_agent_spec_defaults_model_input_capability_ref_to_none() -> None:
    spec = AgentSpec(id="test.agent.direct-input")
    assert spec.model_input_capability_ref is None
```

Delete `test_agent_spec_requires_explicit_model_input_capability_ref` (the behavior it asserted — the field is required — is being removed by design). Leave `test_agent_spec_keeps_model_input_scope_separate_from_executable_tools` and `test_agent_spec_rejects_model_input_scope_as_an_executable_tool` untouched; both already pass an explicit string value and remain valid.

- [ ] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=packages:. .venv/bin/pytest tests/agent/contracts/test_agent_spec.py::test_agent_spec_defaults_model_input_capability_ref_to_none -v`

Expected: FAIL with a `pydantic.ValidationError` (`model_input_capability_ref` is currently required).

- [ ] **Step 3: Make the field optional**

In `packages/agent/contracts/spec.py`, change:

```python
    model_input_capability_ref: str
```

to:

```python
    model_input_capability_ref: str | None = None
```

Update the validator right below it:

```python
    @model_validator(mode="after")
    def keep_model_input_out_of_executable_tools(self) -> AgentSpec:
        if self.model_input_capability_ref in self.capability_refs:
            raise ValueError("model_input_capability_ref must not appear in capability_refs")
        return self
```

to:

```python
    @model_validator(mode="after")
    def keep_model_input_out_of_executable_tools(self) -> AgentSpec:
        if self.model_input_capability_ref and self.model_input_capability_ref in self.capability_refs:
            raise ValueError("model_input_capability_ref must not appear in capability_refs")
        return self
```

- [ ] **Step 4: Run the full contract test file to verify it passes**

Run: `PYTHONPATH=packages:. .venv/bin/pytest tests/agent/contracts/test_agent_spec.py -v`

Expected: PASS, all tests in the file green.

- [ ] **Step 5: Commit**

```bash
git add packages/agent/contracts/spec.py tests/agent/contracts/test_agent_spec.py
git commit -m "feat(agent): make AgentSpec.model_input_capability_ref optional"
```

---

### Task 2: Restore autopilot/copilot specs to `model_input_capability_ref=None`

**Files:**
- Modify: `apps/cosa/agents/specs.py:135-150,163-179`
- Modify: `tests/apps/cosa/agents/test_specs.py:15-22`
- Modify: `tests/apps/cosa/agents/test_customer_support_autopilot_spec.py:20-27`

**Interfaces:**
- Consumes: `AgentSpec.model_input_capability_ref: str | None` from Task 1.
- Produces: `COSA_CUSTOMER_SUPPORT_AGENT_SPEC.model_input_capability_ref is None`, `COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC.model_input_capability_ref is None`, both specs at `version="1.2.0"`. The three other COSA specs unchanged at `"1.1.0"` with `model_input_capability_ref="model.input.direct-user-message"`.

- [ ] **Step 1: Write the failing tests**

In `tests/apps/cosa/agents/test_specs.py`, replace `test_chat_capable_agent_specs_use_new_immutable_version` with two tests that separate the truly chat-capable specs from the two customer-support specs:

```python
def test_direct_chat_capable_agent_specs_use_new_immutable_version() -> None:
    assert {
        COSA_OPERATIONS_AGENT_SPEC.version,
        COSA_FINANCE_AGENT_SPEC.version,
        COSA_MARKETING_AGENT_SPEC.version,
    } == {"1.1.0"}
    assert COSA_OPERATIONS_AGENT_SPEC.model_input_capability_ref == "model.input.direct-user-message"
    assert COSA_FINANCE_AGENT_SPEC.model_input_capability_ref == "model.input.direct-user-message"
    assert COSA_MARKETING_AGENT_SPEC.model_input_capability_ref == "model.input.direct-user-message"


def test_customer_support_specs_do_not_declare_direct_model_input() -> None:
    """Autopilot/copilot never take direct, user-classified chat input — their
    RunRequest.input is a structured task descriptor (thread_id/contact_id/intent),
    not free text a user classified. Declaring model_input_capability_ref here was
    scope creep from an earlier task; restoring both to None here."""
    assert {
        COSA_CUSTOMER_SUPPORT_AGENT_SPEC.version,
        COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC.version,
    } == {"1.2.0"}
    assert COSA_CUSTOMER_SUPPORT_AGENT_SPEC.model_input_capability_ref is None
    assert COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC.model_input_capability_ref is None
```

In `tests/apps/cosa/agents/test_customer_support_autopilot_spec.py`, change:

```python
    assert spec.version == "1.1.0"
```

to:

```python
    assert spec.version == "1.2.0"
    assert spec.model_input_capability_ref is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `PYTHONPATH=packages:. .venv/bin/pytest tests/apps/cosa/agents/test_specs.py tests/apps/cosa/agents/test_customer_support_autopilot_spec.py -v`

Expected: FAIL — both specs are currently `version="1.1.0"` with `model_input_capability_ref="model.input.direct-user-message"`.

- [ ] **Step 3: Update the specs**

In `apps/cosa/agents/specs.py`, in `COSA_CUSTOMER_SUPPORT_AGENT_SPEC` change:

```python
    version="1.1.0",
```
to
```python
    version="1.2.0",
```
and change:
```python
    model_input_capability_ref="model.input.direct-user-message",
```
to
```python
    model_input_capability_ref=None,
```

Apply the identical two changes to `COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `PYTHONPATH=packages:. .venv/bin/pytest tests/apps/cosa/agents/test_specs.py tests/apps/cosa/agents/test_customer_support_autopilot_spec.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/cosa/agents/specs.py tests/apps/cosa/agents/test_specs.py tests/apps/cosa/agents/test_customer_support_autopilot_spec.py
git commit -m "fix(agent): restore autopilot/copilot specs to no direct-model-input scope"
```

---

### Task 3: Stop the resolver from appending a phantom capability id

**Files:**
- Modify: `apps/cosa/compliance/resolver.py:47-54`
- Modify: `tests/apps/cosa/compliance/test_resolver.py`

**Interfaces:**
- Consumes: `AgentSpec.model_input_capability_ref: str | None` from Task 1.
- Produces: `ComplianceResolver.resolve_for_run`'s `capability_ids` sent to Company never contains `None`; unchanged for specs that do declare the capability.

- [ ] **Step 1: Write the failing test**

Add to `tests/apps/cosa/compliance/test_resolver.py` (same file, same fixtures/imports already present — see `sample_request`, `FakeAiComplianceClient`, `ComplianceSnapshot` used by neighboring tests in this file):

```python
@pytest.mark.asyncio
async def test_resolver_does_not_append_phantom_capability_when_spec_has_no_model_input_ref(
    sample_request: RunRequest,
) -> None:
    """Autopilot/copilot declare model_input_capability_ref=None (Task 2) — the
    resolver must not turn that into a literal None entry in capability_ids sent
    to Company."""
    spec_without_direct_input = AgentSpec(
        id="cosa_autopilot_like_agent",
        instructions="Task descriptor only, no direct chat input",
        capability_refs=["engagement.thread.read"],
        model_input_capability_ref=None,
    )
    now = datetime.now(UTC)
    snapshot = ComplianceSnapshot(
        workspace_id="ws_1",
        deployment_id="dep_1",
        assessment_id="ass_1",
        mode="ADVISORY_ONLY",
        status="APPROVED_FOR_USE",
        allowed_capabilities=frozenset(["engagement.thread.read"]),
        provider_profile_version="v3",
        data_profile_version="v1",
        provider_key="deepseek",
        model_key="deepseek-chat",
        purpose_id="advisory",
        retention_policy_id="retain-30d",
        snapshot_hash="sha256:abc123",
        expires_at=now,
    )
    client = FakeAiComplianceClient(snapshot=snapshot)
    resolver = ComplianceResolver(client)

    await resolver.resolve_for_run(sample_request, spec_without_direct_input)

    assert client.calls[0]["capability_ids"] == ["engagement.thread.read"]
    assert None not in client.calls[0]["capability_ids"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=packages:. .venv/bin/pytest tests/apps/cosa/compliance/test_resolver.py::test_resolver_does_not_append_phantom_capability_when_spec_has_no_model_input_ref -v`

Expected: FAIL — `client.calls[0]["capability_ids"] == ["engagement.thread.read", None]`.

- [ ] **Step 3: Make the append conditional**

In `apps/cosa/compliance/resolver.py`, change:

```python
        capability_ids = list(
            dict.fromkeys(
                capability_id
                for capability_id in spec.capability_refs
                if capability_id != spec.model_input_capability_ref
            )
        )
        capability_ids.append(spec.model_input_capability_ref)
```

to:

```python
        capability_ids = list(
            dict.fromkeys(
                capability_id
                for capability_id in spec.capability_refs
                if capability_id != spec.model_input_capability_ref
            )
        )
        if spec.model_input_capability_ref:
            capability_ids.append(spec.model_input_capability_ref)
```

- [ ] **Step 4: Run the full resolver test file to verify it passes**

Run: `PYTHONPATH=packages:. .venv/bin/pytest tests/apps/cosa/compliance/test_resolver.py -v`

Expected: PASS, including the two pre-existing tests that rely on `model_input_capability_ref` still being appended when it is set (`test_resolver_scopes_direct_model_input_when_spec_declares_no_tools`, `test_resolver_mints_a_scoped_delegation_and_forwards_capability_ids`).

- [ ] **Step 5: Commit**

```bash
git add apps/cosa/compliance/resolver.py tests/apps/cosa/compliance/test_resolver.py
git commit -m "fix(compliance): do not send a null capability id when spec has no direct-model-input scope"
```

---

### Task 4: Gate denies only when the spec declared the capability

**Files:**
- Modify: `packages/agent_integrations/openai_agents_sdk/kernel.py:403-409`
- Modify: `apps/cosa/compliance/data_model_gate.py:20-56`
- Modify: `tests/apps/cosa/compliance/test_data_model_gate.py`

**Interfaces:**
- Consumes: `run_context: Mapping[str, Any]` gains a `"model_input_capability_ref"` key, set by the kernel from `spec.model_input_capability_ref` (Task 1/2).
- Produces: `CosaDataModelGate.prepare_initial_input` raises `ComplianceDenied("DATA_ACCESS_CLAIM_MISSING")` only when `self._client is not None` AND `run_context.get("model_input_capability_ref")` is truthy; otherwise falls back to `self._redactor.sanitize(raw_input)`, unchanged from pre-hardening behavior.

- [ ] **Step 1: Write the failing tests**

First, update the existing deny test in `tests/apps/cosa/compliance/test_data_model_gate.py` — it currently omits `model_input_capability_ref` from `run_context`, which after this task's fix would make it stop denying (false negative for the regression it's meant to guard). Add the key so it keeps testing the chat-scoped deny path:

```python
async def test_gate_denies_when_claim_missing_and_client_configured_zero_network_calls() -> None:
    """..."""
    mock_client = AsyncMock()
    gate = CosaDataModelGate(client=mock_client)

    run_context = {
        "workspace_id": "ws_1",
        "compliance_snapshot": {"deployment_id": "dep_1", "status": "APPROVED_FOR_USE"},
        "model_input_capability_ref": "model.input.direct-user-message",
        # Cố tình KHÔNG có "data_access_claim"/"claim" — mô phỏng đúng thực
        # trạng production hiện tại (chưa có capability/retrieval nào build
        # claim thật) cho MỘT spec THẬT SỰ khai báo model_input_capability_ref.
    }

    with pytest.raises(ComplianceDenied, match="DATA_ACCESS_CLAIM_MISSING"):
        await gate.prepare_initial_input(run_context, "Plan Q4 tasks")

    mock_client.resolve_data_use.assert_not_called()
```

Then add a new test proving the opposite case — a spec that never declared the capability is not denied:

```python
@pytest.mark.asyncio
async def test_gate_allows_specs_without_model_input_capability_ref_through_redactor() -> None:
    """Autopilot/copilot (Task 2) never set model_input_capability_ref, so their
    initial input — a structured task descriptor, not user-classified free text —
    must not be denied for lacking a DataAccessClaim. It keeps the same
    redactor-only treatment it had before any compliance-hardening work."""
    mock_client = AsyncMock()
    gate = CosaDataModelGate(client=mock_client)

    run_context = {
        "workspace_id": "ws_1",
        "compliance_snapshot": {"deployment_id": "dep_1", "status": "APPROVED_FOR_USE"},
        # model_input_capability_ref absent entirely, same as a real autopilot run.
    }

    result = await gate.prepare_initial_input(run_context, '{"thread_id": "th_1"}')

    assert result == '{"thread_id": "th_1"}'
    mock_client.resolve_data_use.assert_not_called()
```

Finally, add the end-to-end pair through the real kernel — mirrors the existing `test_withdrawn_authorization_prevents_model_call` pattern already in this file:

```python
@pytest.mark.asyncio
async def test_autopilot_like_spec_reaches_model_without_claim_while_chat_spec_is_denied() -> None:
    """Direct regression guard for the fix in this task: a spec without
    model_input_capability_ref (autopilot/copilot-shaped) must reach the model
    even with no DataAccessClaim anywhere in context, while a spec that does
    declare it (chat-shaped) must still be denied — proving the fix does not
    weaken the existing chat guarantee."""
    autopilot_like_spec = AgentSpec(
        id="autopilot_like_agent",
        instructions="Task descriptor only",
        capability_refs=["engagement.thread.read"],
        model_input_capability_ref=None,
    )
    chat_like_spec = AgentSpec(
        id="chat_like_agent",
        instructions="Direct chat",
        model_input_capability_ref="model.input.direct-user-message",
    )
    request = RunRequest(
        root_executable_ref="agent:autopilot_like_agent",
        workspace_id="ws_1",
        principal="system:autopilot:ws_1",
        input={"thread_id": "th_1", "intent": "faq"},
    )

    allowed_model = FakeSDKModel(responses=[text_response("ok")])
    allowed_kernel = RealOpenAIAgentsSDKKernel(
        model=allowed_model,
        model_input_guard=CosaDataModelGate(client=AsyncMock()),
    )
    allowed_result = await allowed_kernel.run(request, autopilot_like_spec)
    assert allowed_result.status == RunStatus.COMPLETED
    assert allowed_model.call_count == 1

    denied_model = FakeSDKModel(responses=[text_response("unreachable")])
    denied_kernel = RealOpenAIAgentsSDKKernel(
        model=denied_model,
        model_input_guard=CosaDataModelGate(client=AsyncMock()),
    )
    denied_result = await denied_kernel.run(request, chat_like_spec)
    assert denied_result.status == RunStatus.FAILED
    assert denied_model.call_count == 0
```

- [ ] **Step 2: Run the tests to verify the new ones fail and the updated one still passes**

Run: `PYTHONPATH=packages:. .venv/bin/pytest tests/apps/cosa/compliance/test_data_model_gate.py -v`

Expected: `test_gate_denies_when_claim_missing_and_client_configured_zero_network_calls` PASSES unchanged (adding the key doesn't change current behavior — it still denies today regardless of the key, since the key isn't read yet). `test_gate_allows_specs_without_model_input_capability_ref_through_redactor` FAILS (`ComplianceDenied` raised instead of returning sanitized input). `test_autopilot_like_spec_reaches_model_without_claim_while_chat_spec_is_denied` FAILS at the `allowed_result.status == RunStatus.COMPLETED` assertion (currently `FAILED`, since both specs are denied today).

- [ ] **Step 3: Forward the spec's declared capability into context**

In `packages/agent_integrations/openai_agents_sdk/kernel.py`, change:

```python
        context["root_spec_identity"] = spec.id
        context["root_definition_hash"] = pinned_spec.definition_hash
```

to:

```python
        context["root_spec_identity"] = spec.id
        context["root_definition_hash"] = pinned_spec.definition_hash
        context["model_input_capability_ref"] = spec.model_input_capability_ref
```

- [ ] **Step 4: Scope the deny to specs that declared the capability**

In `apps/cosa/compliance/data_model_gate.py`, replace the comment block and the `if claim is None:` branch. Replace this entire section:

```python
        # Task 7 audit (2026-08-30) — con đường DUY NHẤT sản xuất
        # (`apps.cosa.composition.agent_plane.build_cosa_agent_plane`, runtime
        # "openai_agents" mặc định) LUÔN wire `CosaDataModelGate` cùng lúc với
        # `compliance_resolver` — tức MỌI lần gate này chạy với `self._client`
        # khác `None` đều là 1 run compliance-gated thật (không tồn tại
        # đường chạy "openai_agents runtime nhưng bỏ qua compliance" nào khác
        # — xác nhận bằng đọc agent_plane.py dòng ~607-624). Vì vậy: nếu
        # KHÔNG có claim thật (không ai gắn category/provider/model thật vào
        # run_context) mà gate lại có client — tức đang ở nhánh compliance-
        # gated — PHẢI deny ngay, KHÔNG được suy đoán category/provider/model
        # mặc định rồi rơi về `redactor.sanitize()` (đây chính là hành vi
        # "tests green, feature inert" mà audit phát hiện ở Task 7).
        #
        # `self._client is None` (gate dựng tay không truyền client, dùng
        # trong vài unit/smoke test đọc riêng gate) là con đường KHÔNG
        # compliance-gated — hợp lệ để giữ hành vi redactor-only cũ trong
        # giai đoạn chuyển tiếp cho tới khi có "Data Egress Context" thật
        # (xem docs/superpowers/specs/2026-08-30-data-egress-context-prerequisite.md).
        #
        # LƯU Ý QUAN TRỌNG (ghi trong task-7-report.md): vì con đường
        # compliance-gated là con đường DUY NHẤT của toàn bộ runtime sản
        # xuất, và hiện KHÔNG có capability/retrieval nào build
        # `DataAccessClaim` thật, nhánh deny này sẽ chặn TẤT CẢ các run thật
        # cho tới khi Data Egress Context tồn tại — đây là hệ quả cố ý, không
        # phải lỗi, theo đúng quyết định "fail-closed cho riêng đường
        # compliance-gated, không fallback che giấu" của người dùng.
        if claim is None:
            if self._client is not None:
                raise ComplianceDenied("DATA_ACCESS_CLAIM_MISSING")
            return self._redactor.sanitize(raw_input)
```

with:

```python
        # Task 7 audit (2026-08-30) khoá bất kỳ run compliance-gated nào thiếu
        # DataAccessClaim thật — nhưng ban đầu áp dụng cho MỌI run có client
        # thật, kể cả autopilot/copilot, vốn không hề nhận input trực tiếp
        # từ người dùng (RunRequest.input của chúng chỉ là task descriptor:
        # thread_id/contact_id/intent, không phải free text ai đó đã phân
        # loại). Sửa lại (xem
        # docs/superpowers/specs/2026-08-30-autopilot-copilot-initial-input-unblock-design.md):
        # deny chỉ áp dụng cho spec THẬT SỰ khai báo `model_input_capability_ref`
        # (tức tuyên bố nó nhận direct model input cần phân loại — hiện chỉ
        # có specs chat). Spec không khai báo capability này (autopilot/
        # copilot) rơi về `redactor.sanitize()` — đúng hành vi trước khi có
        # toàn bộ đợt hardening này, không hơn không kém. Đây KHÔNG kiểm soát
        # dữ liệu khách hàng thật mà autopilot/copilot lấy qua tool call sau
        # đó — xem "Non-Goals" trong spec doc, đó là gap riêng chưa xử lý.
        if claim is None:
            if self._client is not None and run_context.get("model_input_capability_ref"):
                raise ComplianceDenied("DATA_ACCESS_CLAIM_MISSING")
            return self._redactor.sanitize(raw_input)
```

- [ ] **Step 5: Run the full gate test file to verify it passes**

Run: `PYTHONPATH=packages:. .venv/bin/pytest tests/apps/cosa/compliance/test_data_model_gate.py -v`

Expected: PASS, all tests including the three touched/added in Step 1.

- [ ] **Step 6: Commit**

```bash
git add packages/agent_integrations/openai_agents_sdk/kernel.py apps/cosa/compliance/data_model_gate.py tests/apps/cosa/compliance/test_data_model_gate.py
git commit -m "fix(compliance): scope initial-input deny to specs that declare direct model input"
```

---

### Task 5: Fix the two tests that used the wrong field as an "invalid content" proxy

**Files:**
- Modify: `tests/apps/cosa/test_autopilot_run.py:47-74`
- Modify: `tests/apps/cosa/test_copilot_run.py:128-160` (test body only — verify exact line range when editing, other tests in the file may have shifted it slightly)

**Interfaces:**
- Consumes: nothing new.
- Produces: no change to production code; both tests keep asserting "a registered spec whose content fails to reconstruct as a valid `AgentSpec` fails the run closed" — just via a field that stays required (`id`) instead of one that is no longer required (`model_input_capability_ref`).

**Why this task is needed:** `test_autopilot_fails_closed_when_registered_spec_lacks_input_scope` and `test_copilot_fails_closed_when_registered_spec_lacks_input_scope` (added by an earlier hardening pass, commit `d312b916`) simulate "the registry holds corrupted/invalid spec content" by excluding `model_input_capability_ref` from the serialized spec dict, which previously made Pydantic reconstruction fail (the field was required). After Task 1, excluding that field no longer causes a validation error — it just uses the new `None` default, so these two tests would silently stop testing what they claim to test (they'd still pass, but only because the excluded field now round-trips fine, not because invalid content was rejected). Switch the proxy to `id`, a field that has no default and stays required regardless of this plan.

- [ ] **Step 1: Write the failing (mis-passing) check first — confirm the current proxy is now broken**

Run: `PYTHONPATH=packages:. .venv/bin/pytest tests/apps/cosa/test_autopilot_run.py::test_autopilot_fails_closed_when_registered_spec_lacks_input_scope tests/apps/cosa/test_copilot_run.py::test_copilot_fails_closed_when_registered_spec_lacks_input_scope -v`

Expected (after Tasks 1-4 are committed): both tests FAIL, because excluding `model_input_capability_ref` from the dict no longer produces invalid content — `SpecResolver`/`load_registered_agent_spec` now successfully reconstructs the spec with `model_input_capability_ref=None` and the run proceeds instead of failing closed with `agent_spec_content_invalid`.

- [ ] **Step 2: Rewrite both tests to exclude `id` instead, and rename them**

In `tests/apps/cosa/test_autopilot_run.py`, change:

```python
@pytest.mark.asyncio
async def test_autopilot_fails_closed_when_registered_spec_lacks_input_scope():
    plane = MockPlane()
    plane.spec_registry = MagicMock()
    plane.spec_registry.get = AsyncMock(
        return_value=SimpleNamespace(
            content=COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC.model_dump(
                mode="json", exclude={"model_input_capability_ref"}
            )
        )
    )
```

to:

```python
@pytest.mark.asyncio
async def test_autopilot_fails_closed_when_registered_spec_content_is_invalid():
    """Simulates registry corruption/drift via a field with no default (`id`) so
    this stays a genuine invalid-content test regardless of which other fields
    later become optional — see the autopilot-copilot-initial-input-unblock plan."""
    plane = MockPlane()
    plane.spec_registry = MagicMock()
    plane.spec_registry.get = AsyncMock(
        return_value=SimpleNamespace(
            content=COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC.model_dump(
                mode="json", exclude={"id"}
            )
        )
    )
```

Leave the rest of the test body (the `run_customer_support_autopilot` call and its assertions) unchanged.

In `tests/apps/cosa/test_copilot_run.py`, apply the same two changes: rename `test_copilot_fails_closed_when_registered_spec_lacks_input_scope` to `test_copilot_fails_closed_when_registered_spec_content_is_invalid`, and change `exclude={"model_input_capability_ref"}` to `exclude={"id"}` in its `stale_content` construction. Leave the rest of the test body unchanged.

- [ ] **Step 3: Run both files to verify they pass**

Run: `PYTHONPATH=packages:. .venv/bin/pytest tests/apps/cosa/test_autopilot_run.py tests/apps/cosa/test_copilot_run.py -v`

Expected: PASS, all tests in both files.

- [ ] **Step 4: Commit**

```bash
git add tests/apps/cosa/test_autopilot_run.py tests/apps/cosa/test_copilot_run.py
git commit -m "test(agent): fix invalid-registry-content proxy tests after model_input_capability_ref became optional"
```

---

### Task 6: Release verification

**Files:** none modified.

**Interfaces:** none.

- [ ] **Step 1: Run the full affected Python surface**

Run: `PYTHONPATH=packages:. .venv/bin/pytest tests/agent/contracts tests/apps/cosa/agents tests/apps/cosa/compliance tests/apps/cosa/test_autopilot_run.py tests/apps/cosa/test_copilot_run.py -v`

Expected: PASS, no failures. If any pre-existing unrelated failure appears (e.g. a DB-permission or `.env`-driven test-pollution failure already known from prior work on this codebase), confirm it also fails identically on a clean checkout of the immediately preceding commit before treating it as pre-existing rather than caused by this plan.

- [ ] **Step 2: Run the broader agent/cosa suite to catch any spec-version or capability-list assumption elsewhere**

Run: `PYTHONPATH=packages:. .venv/bin/pytest tests/agent packages/agent_testkit tests/apps/cosa -m 'not integration' -q`

Expected: same pass/fail profile as the pre-existing baseline (the litellm-dotenv and event_inbox-permission failures already known to be environment-specific and unrelated); no new failures attributable to `model_input_capability_ref`, spec versions, or `capability_ids`.

- [ ] **Step 3: Inspect delivery integrity**

Run: `git diff --check && git status --short`

Expected: clean — no whitespace errors, no unrelated files.
