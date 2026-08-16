# Prompt Management Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a workspace's `owner` (founder) view, edit and reset-to-default the 3 chat persona prompts that actually drive AI behavior today, plus browse (read-only for now) the other 20 domain prompt files, through a new dashboard screen backed by the existing `protected_resources` revision/audit infrastructure.

**Architecture:** Reuse the existing `protected_resources` service (already powers `Agent.system_prompt` edit/reset) for a new `resource_type="domain_prompt"`, keyed by `{domain}/{name}`. Add a DB-override-aware resolver to `PromptRegistry` and wire it into the 3 real chat prompt call sites in `chat_execution_service.py` — this is the only place any `backend/app/prompts/*.md` file affects live behavior today. Tighten `authz.py` so `prompt.update`/`prompt.reset` require role `owner` (currently `admin`+ passes). Expose it all through a new `prompts_router.py` and a new Flutter "Prompt Management" screen.

**Tech Stack:** FastAPI + SQLAlchemy (backend/app), Flutter + GetX (frontend/lib), pytest, flutter_test.

## Global Constraints

- The default content of the 3 new prompt files must match the current hardcoded Python strings **byte-for-byte** — this is a behavior-neutral cutover; no tenant's AI output should change on deploy unless they've explicitly saved an override.
- RBAC: `prompt.update` and `prompt.reset` require role `owner`. `prompt.read` and every other existing `PROTECTED_ACTIONS` entry (`spec.*`, `skill.*`, `policy.*`, `employee.*`, `agent.configure`, `tool.configure`, `approval_policy.configure`) keep requiring `admin`+ — do not change their behavior.
- Do not touch `GROUNDING_PROMPT`, `NO_TOOLS_PROMPT`, `UNGROUNDED_ACTION_PROMPT` (chat_execution_service.py), `MODULAR_LANDING_SYSTEM_PROMPT` (coding_agent_provider.py), the `deepseek_harness.py` tool-usage header, or `chief_of_staff.py::_build_synthesis_prompt`. These stay hardcoded per the approved spec (`docs/superpowers/specs/2026-08-16-prompt-management-dashboard-design.md`).
- Every workspace-scoped endpoint takes `workspace_id` explicitly and resolves the caller via `get_current_workspace_member`, matching the existing convention in `backend/app/modules/tasks/agents_router.py`.
- A `domain`/`name` pair not present in the 23-file catalog on disk returns 404 — the UI/API never creates new prompt keys.

---

### Task 1: `PromptRegistry.render_effective()` — DB-override-aware resolver

**Files:**
- Modify: `backend/app/ai/prompt_registry.py`
- Test: `backend/app/tests/test_prompt_registry_render_effective.py` (create)

**Interfaces:**
- Produces: `PromptRegistry.render_effective(self, db: Session, workspace_id: int, domain: str, name: str, variables: Optional[Dict[str, Any]]) -> str` — resolves a workspace's DB override via `protected_resources.get_effective(resource_type="domain_prompt", resource_key=f"{domain}/{name}")`, falling back to the file-based template; raises `KeyError` if `domain/name` isn't a known template. Used by Task 2 (chat call sites) and Task 4 (`prompts_router.py`).

- [ ] **Step 1: Write the failing tests**

Create `backend/app/tests/test_prompt_registry_render_effective.py`:

```python
from unittest.mock import MagicMock

import pytest

from app.ai.prompt_registry import PromptRegistry
from app.core.protected_resources.models import ProtectedResource, ProtectedResourceRevision
from app.core.snowflake import generate_snowflake_id


def test_render_effective_falls_back_to_file_default_when_no_override():
    registry = PromptRegistry.get_instance()
    registry.reload()
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    workspace_id = generate_snowflake_id()

    rendered = registry.render_effective(
        db, workspace_id, "sales", "outbound",
        {"company_name": "Acme Corp", "icp_criteria": "B2B SaaS"},
    )

    assert "Acme Corp" in rendered


def test_render_effective_uses_workspace_override_when_present():
    registry = PromptRegistry.get_instance()
    registry.reload()
    workspace_id = generate_snowflake_id()

    resource = ProtectedResource(
        id=generate_snowflake_id(), workspace_id=workspace_id,
        resource_type="domain_prompt", resource_key="cosa/system",
        active_revision_no=1, resettable=True,
    )
    override_rev = ProtectedResourceRevision(
        id=generate_snowflake_id(), resource_id=resource.id, revision_no=1,
        content_jsonb={"content": "Always answer in English."},
        is_default=False, status="ACTIVE",
    )

    resource_query = MagicMock()
    resource_query.filter.return_value.first.return_value = resource
    revision_query = MagicMock()
    revision_query.filter.return_value.first.return_value = override_rev

    db = MagicMock()

    def query_mock(model):
        if model is ProtectedResource:
            return resource_query
        if model is ProtectedResourceRevision:
            return revision_query
        return MagicMock()

    db.query.side_effect = query_mock

    rendered = registry.render_effective(db, workspace_id, "cosa", "system", None)

    assert rendered == "Always answer in English."


def test_render_effective_raises_for_unknown_domain_name():
    registry = PromptRegistry.get_instance()
    registry.reload()
    db = MagicMock()

    with pytest.raises(KeyError):
        registry.render_effective(db, 1, "unknown_domain", "missing", None)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest app/tests/test_prompt_registry_render_effective.py -v`
Expected: FAIL — `AttributeError: 'PromptRegistry' object has no attribute 'render_effective'`

- [ ] **Step 3: Implement `render_effective`**

In `backend/app/ai/prompt_registry.py`, add this import near the top (after the existing `typing` import):

```python
from app.core.protected_resources import service as protected_resource_service
```

Add this method to `PromptRegistry`, directly after the existing `render()` method:

```python
    def render_effective(
        self,
        db,
        workspace_id: int,
        domain: str,
        name: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Render a template, preferring the workspace's DB override over the bundled file default."""
        template = self.get(domain, name)
        if not template:
            raise KeyError(f"Prompt template '{domain}/{name}' not found in registry")

        effective = protected_resource_service.get_effective(
            db=db,
            workspace_id=workspace_id,
            resource_type="domain_prompt",
            resource_key=f"{domain}/{name}",
            default_content={"content": template.content},
        )
        rendered = effective.get("content", template.content)
        if variables:
            for k, v in variables.items():
                rendered = rendered.replace(f"${{{k}}}", str(v))
        return rendered
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest app/tests/test_prompt_registry_render_effective.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Run the full existing prompt registry test suite to confirm no regression**

Run: `cd backend && python -m pytest app/tests/test_p0_prompt_registry.py app/tests/test_prompt_registry_p5.py -v`
Expected: PASS (all existing tests unaffected)

- [ ] **Step 6: Commit**

```bash
git add backend/app/ai/prompt_registry.py backend/app/tests/test_prompt_registry_render_effective.py
git commit -m "feat(prompts): add PromptRegistry.render_effective for DB-override resolution"
```

---

### Task 2: Wire the 3 real chat prompts through the registry (behavior-neutral)

**Files:**
- Create: `backend/app/prompts/cosa/chat_language.md`
- Create: `backend/app/prompts/cosa/chat_conversation.md`
- Create: `backend/app/prompts/cosa/chat_structured_oneshot.md`
- Modify: `backend/app/modules/chat/chat_execution_service.py:1-38,73-112,401-431`
- Modify: `backend/app/tests/test_chat_execution_service.py`

**Interfaces:**
- Consumes: `PromptRegistry.get_instance().render_effective(db, workspace_id, domain, name, variables)` from Task 1.
- Produces: `chat_execution_service.py` no longer defines module-level `SYSTEM_PROMPT_VI`, `CONVERSATION_PROMPT`, `STRUCTURED_ONESHOT_PROMPT` constants. `GROUNDING_PROMPT`, `NO_TOOLS_PROMPT`, `UNGROUNDED_ACTION_PROMPT` are untouched and still exist as module constants.

- [ ] **Step 1: Write the failing "file matches shipped default" tests**

Add to `backend/app/tests/test_chat_execution_service.py`, near the top-level test functions (after the imports, before `test_worker_persists_reply_and_ai_run`):

```python
def test_cosa_chat_language_prompt_matches_shipped_default():
    from app.ai.prompt_registry import PromptRegistry
    registry = PromptRegistry.get_instance()
    registry.reload()
    template = registry.get("cosa", "chat_language")
    assert template is not None
    assert template.content == (
        "Luôn trả lời bằng tiếng Việt tự nhiên, rõ ràng, súc tích, trừ khi người dùng yêu cầu rõ ràng dùng ngôn ngữ "
        "khác. Ưu tiên sử dụng thuật ngữ tiếng Việt chuẩn, dễ hiểu. "
        "Không dịch lại câu trả lời sang tiếng Anh. "
        "Tuyệt đối chỉ trả lời trực tiếp nội dung người dùng hỏi, không in ra các câu phân tích suy nghĩ, "
        "không tự giải thích lý do/chiến lược trả lời của bản thân trong ngoặc đơn hay bất kỳ đâu."
    )


def test_cosa_chat_conversation_prompt_matches_shipped_default():
    from app.ai.prompt_registry import PromptRegistry
    registry = PromptRegistry.get_instance()
    registry.reload()
    template = registry.get("cosa", "chat_conversation")
    assert template is not None
    assert template.content == (
        "[TRÒ CHUYỆN TỰ NHIÊN / GIẢI ĐÁP THÔNG THƯỜNG]\n"
        "Bạn đang trò chuyện tự nhiên, chào hỏi hoặc giải thích các khái niệm thông thường. "
        "Hãy trả lời một cách thân thiện, súc tích, tự nhiên và đi thẳng vào vấn đề. "
        "Tuyệt đối không kèm thêm lời giải thích, phân tích suy nghĩ hay lý do trả lời."
    )


def test_cosa_chat_structured_oneshot_prompt_matches_shipped_default():
    from app.ai.prompt_registry import PromptRegistry
    registry = PromptRegistry.get_instance()
    registry.reload()
    template = registry.get("cosa", "chat_structured_oneshot")
    assert template is not None
    assert template.content == (
        "Bạn đang xử lý một yêu cầu sinh dữ liệu có cấu trúc, không phải hội thoại. Toàn bộ dữ "
        "liệu cần dùng đã nằm trong yêu cầu - không suy đoán thêm và không hỏi lại. Trả lời "
        "đúng định dạng được mô tả trong yêu cầu, không thêm lời chào, lời dẫn hay giải thích "
        "nào ngoài định dạng đó."
    )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest app/tests/test_chat_execution_service.py -k "matches_shipped_default" -v`
Expected: FAIL — `assert None is not None` (files don't exist yet)

- [ ] **Step 3: Create the 3 prompt files with exact current content**

Create `backend/app/prompts/cosa/chat_language.md` — **no trailing newline**, content must end exactly at the final period:

```
Luôn trả lời bằng tiếng Việt tự nhiên, rõ ràng, súc tích, trừ khi người dùng yêu cầu rõ ràng dùng ngôn ngữ khác. Ưu tiên sử dụng thuật ngữ tiếng Việt chuẩn, dễ hiểu. Không dịch lại câu trả lời sang tiếng Anh. Tuyệt đối chỉ trả lời trực tiếp nội dung người dùng hỏi, không in ra các câu phân tích suy nghĩ, không tự giải thích lý do/chiến lược trả lời của bản thân trong ngoặc đơn hay bất kỳ đâu.
```

Create `backend/app/prompts/cosa/chat_conversation.md` — note this deliberately does **not** include the `\n\n` prefix the old `CONVERSATION_PROMPT` constant had; Step 5 re-adds that prefix at the call site so the concatenated output stays byte-identical while the stored file itself reads cleanly for an editor:

```
[TRÒ CHUYỆN TỰ NHIÊN / GIẢI ĐÁP THÔNG THƯỜNG]
Bạn đang trò chuyện tự nhiên, chào hỏi hoặc giải thích các khái niệm thông thường. Hãy trả lời một cách thân thiện, súc tích, tự nhiên và đi thẳng vào vấn đề. Tuyệt đối không kèm thêm lời giải thích, phân tích suy nghĩ hay lý do trả lời.
```

Create `backend/app/prompts/cosa/chat_structured_oneshot.md` — no trailing newline:

```
Bạn đang xử lý một yêu cầu sinh dữ liệu có cấu trúc, không phải hội thoại. Toàn bộ dữ liệu cần dùng đã nằm trong yêu cầu - không suy đoán thêm và không hỏi lại. Trả lời đúng định dạng được mô tả trong yêu cầu, không thêm lời chào, lời dẫn hay giải thích nào ngoài định dạng đó.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest app/tests/test_chat_execution_service.py -k "matches_shipped_default" -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Refactor the 3 call sites in `chat_execution_service.py`**

Remove the `SYSTEM_PROMPT_VI` constant and its comment (lines 29-38) and the `CONVERSATION_PROMPT` constant and its comment (lines 73-79) and the `STRUCTURED_ONESHOT_PROMPT` constant and its comment (lines 103-112). Leave `GROUNDING_PROMPT`, `NO_TOOLS_PROMPT`, `UNGROUNDED_ACTION_PROMPT` exactly as they are.

Add this import near the top of the file, next to the other `app.*` imports:

```python
from app.ai.prompt_registry import PromptRegistry
```

Change the one-shot branch (was `system_content = STRUCTURED_ONESHOT_PROMPT`):

```python
        if one_shot:
            tools = []
            system_content = PromptRegistry.get_instance().render_effective(
                db, workspace_id, "cosa", "chat_structured_oneshot", None
            )
```

Change the conversation branch (was `prompt_addon = CONVERSATION_PROMPT`):

```python
            elif gate_decision and gate_decision.intent in (
                GateIntent.SOCIAL_CHAT, GateIntent.GENERAL_QUESTION
            ):
                prompt_addon = "\n\n" + PromptRegistry.get_instance().render_effective(
                    db, workspace_id, "cosa", "chat_conversation", None
                )
```

Change the final assembly (was `SYSTEM_PROMPT_VI + prompt_addon + connectors_prompt`):

```python
            system_content = (
                PromptRegistry.get_instance().render_effective(
                    db, workspace_id, "cosa", "chat_language", None
                )
                + prompt_addon
                + connectors_prompt
            )
```

- [ ] **Step 6: Fix the shared test mock helper so `ProtectedResource` queries don't exhaust the existing `.first()` side_effect chain**

In `backend/app/tests/test_chat_execution_service.py`, add this import at the top:

```python
from app.core.protected_resources.models import ProtectedResource
```

In `_make_pending()`, right before the `default_query = db.query.return_value` line, add:

```python
    # render_effective() queries ProtectedResource for a workspace override on every
    # chat turn now; route it to its own mock (no override) so it doesn't consume a slot
    # from the [user_message, session, brain] side_effect list above.
    protected_resource_query = MagicMock()
    protected_resource_query.filter.return_value.first.return_value = None
```

Then update the `routed` dict in the same function:

```python
    default_query = db.query.return_value
    routed = {
        MCPConnection: connector_query,
        FeatureFlag: flag_query,
        ProtectedResource: protected_resource_query,
    }
    db.query.side_effect = lambda *args: (
        routed.get(args[0], default_query) if args else default_query
    )
```

- [ ] **Step 7: Update the two tests that asserted against the now-deleted `STRUCTURED_ONESHOT_PROMPT` constant**

Replace the body of `test_worker_runs_a_one_shot_session_without_tools_or_chat_persona`:

```python
def test_worker_runs_a_one_shot_session_without_tools_or_chat_persona():
    """Session ẩn của các nút "AI đề xuất ..." (chat/worker_prompt.py) cần đúng một khối
    JSON. Gửi kèm bộ tool và GROUNDING_PROMPT - đoạn dặn model "chưa gọi tool là chưa biết
    gì về workspace" - là đẩy nó đi gọi tool thay vì trả JSON, rồi bên gọi nhận về văn xuôi
    và báo "AI trả về nội dung không hợp lệ"."""
    router = _run_one_turn(MagicMock(), purpose=ONESHOT_PURPOSE)

    assert not router.last_tools
    system_turn = router.last_turns[0]
    assert system_turn.role == "system"
    assert system_turn.content == (
        "Bạn đang xử lý một yêu cầu sinh dữ liệu có cấu trúc, không phải hội thoại. Toàn bộ dữ "
        "liệu cần dùng đã nằm trong yêu cầu - không suy đoán thêm và không hỏi lại. Trả lời "
        "đúng định dạng được mô tả trong yêu cầu, không thêm lời chào, lời dẫn hay giải thích "
        "nào ngoài định dạng đó."
    )
    assert "[DỮ LIỆU CÔNG TY]" not in system_turn.content
```

`test_worker_still_gives_a_normal_chat_session_its_tools` does not reference the deleted constant — leave it as-is.

- [ ] **Step 8: Run the full chat execution test suite**

Run: `cd backend && python -m pytest app/tests/test_chat_execution_service.py -v`
Expected: PASS — every test in the file, including the pre-existing ones (`test_worker_tells_the_model_not_to_invent_company_data`, `test_worker_warns_the_model_when_it_has_no_data_access_at_all`, etc.)

- [ ] **Step 9: Write and run a test proving a workspace override actually changes chat output**

`chat_execution_service.py` derives `gate_decision = conversation_gate.resolve(user_message.content)` purely from the message text (`backend/app/modules/chat/chat_execution_service.py:371`) — no mocking needed to steer it. `"chào"` matches `SOCIAL_GREETING_PATTERNS` in `conversation_gate.py:54`, which resolves to `GateIntent.SOCIAL_CHAT`, exactly the branch that renders `cosa/chat_conversation`. This test calls `_make_pending` directly (instead of `_run_one_turn`) so it can layer its own `ProtectedResource`/`ProtectedResourceRevision` routing onto `db.query.side_effect` *after* `_make_pending` sets its default routing but *before* the turn runs.

Add to `backend/app/tests/test_chat_execution_service.py`:

```python
def test_worker_uses_a_workspace_override_for_the_conversation_prompt():
    from app.core.protected_resources.models import ProtectedResource, ProtectedResourceRevision

    db = MagicMock()
    _make_pending(db, content="chào")
    db.query.return_value.filter.return_value.scalar.return_value = "streaming"

    resource = ProtectedResource(
        id=generate_snowflake_id(), workspace_id=1, resource_type="domain_prompt",
        resource_key="cosa/chat_conversation", active_revision_no=1, resettable=True,
    )
    override_rev = ProtectedResourceRevision(
        id=generate_snowflake_id(), resource_id=resource.id, revision_no=1,
        content_jsonb={"content": "[OVERRIDE] Trả lời cực kỳ ngắn gọn."},
        is_default=False, status="ACTIVE",
    )
    resource_query = MagicMock()
    resource_query.filter.return_value.first.return_value = resource
    revision_query = MagicMock()
    revision_query.filter.return_value.first.return_value = override_rev

    default_side_effect = db.query.side_effect

    def query_mock(*args):
        if args and args[0] is ProtectedResource:
            return resource_query
        if args and args[0] is ProtectedResourceRevision:
            return revision_query
        return default_side_effect(*args)

    db.query.side_effect = query_mock

    router = _ScriptedRouter([[AIEvent(kind="delta", content="ok"), AIEvent(kind="completed")]])
    asyncio.run(process_pending_chat_messages(db, router))

    system_turn = next(t for t in router.last_turns if t.role == "system")
    assert "[OVERRIDE] Trả lời cực kỳ ngắn gọn." in system_turn.content
```

Run: `cd backend && python -m pytest app/tests/test_chat_execution_service.py -k override -v`
Expected: PASS (1 test)

- [ ] **Step 10: Commit**

```bash
git add backend/app/prompts/cosa/chat_language.md backend/app/prompts/cosa/chat_conversation.md \
        backend/app/prompts/cosa/chat_structured_oneshot.md \
        backend/app/modules/chat/chat_execution_service.py \
        backend/app/tests/test_chat_execution_service.py
git commit -m "feat(chat): wire the 3 chat persona prompts through PromptRegistry"
```

---

### Task 3: RBAC — `prompt.update`/`prompt.reset` require role `owner`

**Files:**
- Modify: `backend/app/core/authz.py`
- Modify: `backend/app/tests/test_authz_protected_resources.py`

**Interfaces:**
- Produces: `authorize(member, action)` now looks up the action's required role in a new `ACTION_REQUIRED_LEVEL` dict (defaulting to `"admin"`), instead of a single hardcoded `"admin"` for every `PROTECTED_ACTIONS` entry. Consumed by `agents_router.py` (unchanged, already calls `authorize`) and Task 4's `prompts_router.py`.

- [ ] **Step 1: Write the failing test**

In `backend/app/tests/test_authz_protected_resources.py`, replace `test_authz_allows_admin_and_owner` with two tests:

```python
def test_authz_allows_admin_and_owner_for_admin_level_actions():
    admin_member = WorkspaceMember(id=generate_snowflake_id(), workspace_id=generate_snowflake_id(), user_id=generate_snowflake_id(), role="admin")
    owner_member = WorkspaceMember(id=generate_snowflake_id(), workspace_id=generate_snowflake_id(), user_id=generate_snowflake_id(), role="owner")

    for action in ["prompt.read", "spec.update", "spec.reset", "skill.update"]:
        authorize(admin_member, action)
        authorize(owner_member, action)


def test_authz_prompt_update_and_reset_require_owner():
    admin_member = WorkspaceMember(id=generate_snowflake_id(), workspace_id=generate_snowflake_id(), user_id=generate_snowflake_id(), role="admin")
    owner_member = WorkspaceMember(id=generate_snowflake_id(), workspace_id=generate_snowflake_id(), user_id=generate_snowflake_id(), role="owner")

    for action in ["prompt.update", "prompt.reset"]:
        with pytest.raises(HTTPException) as exc_info:
            authorize(admin_member, action)
        assert exc_info.value.status_code == 403

        authorize(owner_member, action)
```

`test_authz_blocks_non_admin` stays unchanged (member/viewer/editor are blocked from `prompt.update`/`prompt.reset` under both the old admin-level and new owner-level requirement).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest app/tests/test_authz_protected_resources.py -k "prompt_update_and_reset_require_owner" -v`
Expected: FAIL — `authorize(admin_member, "prompt.update")` does not raise today

- [ ] **Step 3: Implement the per-action required-level map**

In `backend/app/core/authz.py`, add this constant after `PROTECTED_ACTIONS`:

```python
# Actions requiring a stricter level than the "admin" default applied to every other
# entry in PROTECTED_ACTIONS. Prompt edits change AI behavior for the whole workspace,
# so only the workspace owner (founder) may write or reset them.
ACTION_REQUIRED_LEVEL = {
    "prompt.update": "owner",
    "prompt.reset": "owner",
}
```

Replace the body of `authorize()`:

```python
def authorize(member: WorkspaceMember, action: str, resource: Optional[Any] = None) -> None:
    """Authorize workspace member for an action against protected system resources.

    Raises 403 Forbidden if the action is protected and the member role is below the
    action's required level (ACTION_REQUIRED_LEVEL, defaulting to "admin").
    """
    if member is None or not hasattr(member, "role"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: workspace membership required",
        )

    member_level = PERMISSION_LEVELS.get(member.role, 0)
    required_role = ACTION_REQUIRED_LEVEL.get(action, "admin")
    required_level = PERMISSION_LEVELS[required_role]

    if action in PROTECTED_ACTIONS and member_level < required_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Action '{action}' requires {required_role} role in this workspace",
        )
```

- [ ] **Step 4: Run the new tests**

Run: `cd backend && python -m pytest app/tests/test_authz_protected_resources.py -k "admin_level_actions or prompt_update_and_reset_require_owner or blocks_non_admin" -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Update the `agents_router.py` tests that assumed admin could update/reset prompts**

In `test_agents_router_prompt_update_rbac`, after the existing `regular_member` 403 block, replace the rest of the function:

```python
    # Admin role is no longer sufficient for prompt.update (owner-only as of this change)
    admin_member = WorkspaceMember(id=generate_snowflake_id(), workspace_id=ws_id, user_id=generate_snowflake_id(), role="admin")
    with pytest.raises(HTTPException) as exc:
        update_agent(
            workspace_id=ws_id,
            agent_id=agent_id,
            agent_in=AgentUpdate(system_prompt="new prompt from admin"),
            member=admin_member,
            db=db,
        )
    assert exc.value.status_code == 403

    # Owner role succeeds
    owner_member = WorkspaceMember(id=generate_snowflake_id(), workspace_id=ws_id, user_id=generate_snowflake_id(), role="owner")
    res = update_agent(
        workspace_id=ws_id,
        agent_id=agent_id,
        agent_in=AgentUpdate(system_prompt="new prompt from owner"),
        member=owner_member,
        db=db,
    )
    assert res["system_prompt"] == "new prompt from owner"
```

In `test_agents_router_reset_and_revisions_endpoints`, replace the body from `# Non-admin reset -> 403` onward:

```python
    regular_member = WorkspaceMember(id=generate_snowflake_id(), workspace_id=ws_id, user_id=generate_snowflake_id(), role="member")
    admin_member = WorkspaceMember(id=generate_snowflake_id(), workspace_id=ws_id, user_id=generate_snowflake_id(), role="admin")
    owner_member = WorkspaceMember(id=generate_snowflake_id(), workspace_id=ws_id, user_id=generate_snowflake_id(), role="owner")

    # Non-admin reset -> 403
    with pytest.raises(HTTPException) as exc:
        reset_agent_system_prompt(workspace_id=ws_id, agent_id=agent_id, member=regular_member, db=db)
    assert exc.value.status_code == 403

    # Admin reset -> also 403 now (reset requires owner)
    with pytest.raises(HTTPException) as exc:
        reset_agent_system_prompt(workspace_id=ws_id, agent_id=agent_id, member=admin_member, db=db)
    assert exc.value.status_code == 403

    # Owner reset -> succeeds
    reset_res = reset_agent_system_prompt(workspace_id=ws_id, agent_id=agent_id, member=owner_member, db=db)
    assert reset_res["status"] == "reset"

    # Non-admin list revisions -> 403
    with pytest.raises(HTTPException) as exc:
        list_agent_prompt_revisions(workspace_id=ws_id, agent_id=agent_id, member=regular_member, db=db)
    assert exc.value.status_code == 403

    # Admin list revisions -> still succeeds (prompt.read stays admin-level)
    revisions_res = list_agent_prompt_revisions(workspace_id=ws_id, agent_id=agent_id, member=admin_member, db=db)
    assert "revisions" in revisions_res
```

- [ ] **Step 6: Run the full file**

Run: `cd backend && python -m pytest app/tests/test_authz_protected_resources.py -v`
Expected: PASS (all tests)

- [ ] **Step 7: Commit**

```bash
git add backend/app/core/authz.py backend/app/tests/test_authz_protected_resources.py
git commit -m "feat(authz): require owner role for prompt.update and prompt.reset"
```

---

### Task 4: `prompts_router.py` — list / get / update / reset API

**Files:**
- Create: `backend/app/modules/platform/prompts_router.py`
- Modify: `backend/app/main.py`
- Test: `backend/app/tests/test_prompts_router.py` (create)

**Interfaces:**
- Consumes: `PromptRegistry.get_instance()` (Task 1), `protected_resource_service.{get_effective,create_revision,reset_to_default,list_revisions}` (existing), `authorize()` (Task 3).
- Produces: `GET /api/v1/platform/prompts/?workspace_id=`, `GET /api/v1/platform/prompts/{domain}/{name}?workspace_id=`, `PATCH /api/v1/platform/prompts/{domain}/{name}?workspace_id=`, `POST /api/v1/platform/prompts/{domain}/{name}:reset?workspace_id=`. Consumed by Task 5's Flutter service.

- [ ] **Step 1: Write the failing tests**

Create `backend/app/tests/test_prompts_router.py`:

```python
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.core.auth import get_current_workspace_member
from app.core.protected_resources.models import ProtectedResource, ProtectedResourceRevision
from app.core.snowflake import generate_snowflake_id
from app.db.models import WorkspaceMember
from app.db.session import get_db
from app.main import app


def _override(member: WorkspaceMember, db):
    app.dependency_overrides[get_current_workspace_member] = lambda: member
    app.dependency_overrides[get_db] = lambda: db


def test_get_unknown_prompt_returns_404():
    ws_id = generate_snowflake_id()
    member = WorkspaceMember(workspace_id=ws_id, role="owner")
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    _override(member, db)

    client = TestClient(app)
    res = client.get(f"/api/v1/platform/prompts/not_a_domain/not_a_name?workspace_id={ws_id}")
    assert res.status_code == 404


def test_list_prompts_requires_at_least_admin():
    ws_id = generate_snowflake_id()
    member = WorkspaceMember(workspace_id=ws_id, role="member")
    db = MagicMock()
    _override(member, db)

    client = TestClient(app)
    res = client.get(f"/api/v1/platform/prompts/?workspace_id={ws_id}")
    assert res.status_code == 403


def test_list_prompts_succeeds_for_admin_and_includes_known_wired_flag():
    ws_id = generate_snowflake_id()
    member = WorkspaceMember(workspace_id=ws_id, role="admin")
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    _override(member, db)

    client = TestClient(app)
    res = client.get(f"/api/v1/platform/prompts/?workspace_id={ws_id}")
    assert res.status_code == 200
    prompts = res.json()["prompts"]
    wired = next(p for p in prompts if p["domain"] == "cosa" and p["name"] == "chat_language")
    assert wired["is_wired"] is True
    unwired = next(p for p in prompts if p["domain"] == "finance" and p["name"] == "analyze")
    assert unwired["is_wired"] is False


def test_update_prompt_blocked_for_admin_allowed_for_owner():
    ws_id = generate_snowflake_id()
    db = MagicMock()

    resource = ProtectedResource(
        id=generate_snowflake_id(), workspace_id=ws_id, resource_type="domain_prompt",
        resource_key="cosa/chat_language", active_revision_no=0, resettable=True,
    )
    rev0 = ProtectedResourceRevision(
        id=generate_snowflake_id(), resource_id=resource.id, revision_no=0,
        content_jsonb={"content": "old"}, is_default=True, status="ACTIVE",
    )
    resource_query = MagicMock()
    resource_query.filter.return_value.first.return_value = resource
    revision_query = MagicMock()
    revision_query.filter.return_value.order_by.return_value.first.return_value = rev0

    def query_mock(model):
        if model is ProtectedResource:
            return resource_query
        if model is ProtectedResourceRevision:
            return revision_query
        return MagicMock()

    db.query.side_effect = query_mock

    admin_member = WorkspaceMember(workspace_id=ws_id, user_id=generate_snowflake_id(), role="admin")
    _override(admin_member, db)
    client = TestClient(app)
    res = client.patch(
        f"/api/v1/platform/prompts/cosa/chat_language?workspace_id={ws_id}",
        json={"content": "new content from admin"},
    )
    assert res.status_code == 403

    owner_member = WorkspaceMember(workspace_id=ws_id, user_id=generate_snowflake_id(), role="owner")
    _override(owner_member, db)
    res = client.patch(
        f"/api/v1/platform/prompts/cosa/chat_language?workspace_id={ws_id}",
        json={"content": "new content from owner"},
    )
    assert res.status_code == 200
    assert res.json()["content"] == "new content from owner"


def test_reset_prompt_returns_file_default():
    ws_id = generate_snowflake_id()
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.filter.return_value.all.return_value = []

    owner_member = WorkspaceMember(workspace_id=ws_id, user_id=generate_snowflake_id(), role="owner")
    _override(owner_member, db)

    client = TestClient(app)
    res = client.post(f"/api/v1/platform/prompts/cosa/chat_language:reset?workspace_id={ws_id}")
    assert res.status_code == 200
    assert res.json()["status"] == "reset"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest app/tests/test_prompts_router.py -v`
Expected: FAIL — `404` for every route (router doesn't exist / isn't mounted yet)

- [ ] **Step 3: Implement `prompts_router.py`**

Create `backend/app/modules/platform/prompts_router.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.ai.prompt_registry import PromptRegistry
from app.core.auth import get_current_workspace_member
from app.core.authz import authorize
from app.core.protected_resources import service as protected_resource_service
from app.core.protected_resources.models import ProtectedResource
from app.db.models import WorkspaceMember
from app.db.session import get_db

router = APIRouter()

# The only domain prompts any live agent call site actually reads today. Everything
# else in the 23-file catalog is editable/resettable but has no runtime effect yet.
WIRED_PROMPTS = {
    ("cosa", "chat_language"),
    ("cosa", "chat_conversation"),
    ("cosa", "chat_structured_oneshot"),
}


class DomainPromptUpdate(BaseModel):
    content: str


def _resource_key(domain: str, name: str) -> str:
    return f"{domain}/{name}"


def _require_known_prompt(domain: str, name: str):
    template = PromptRegistry.get_instance().get(domain, name)
    if not template:
        raise HTTPException(status_code=404, detail=f"Unknown prompt '{domain}/{name}'")
    return template


@router.get("/")
def list_domain_prompts(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    authorize(member, "prompt.read")
    registry = PromptRegistry.get_instance()
    result = []
    for meta in sorted(registry.list_templates().values(), key=lambda t: (t["domain"], t["name"])):
        domain, name = meta["domain"], meta["name"]
        resource = (
            db.query(ProtectedResource)
            .filter(
                ProtectedResource.workspace_id == workspace_id,
                ProtectedResource.resource_type == "domain_prompt",
                ProtectedResource.resource_key == _resource_key(domain, name),
            )
            .first()
        )
        result.append({
            "domain": domain,
            "name": name,
            "is_overridden": bool(resource and resource.active_revision_no != 0),
            "is_wired": (domain, name) in WIRED_PROMPTS,
            "updated_at": resource.updated_at.isoformat() if resource else None,
        })
    return {"prompts": result}


@router.get("/{domain}/{name}")
def get_domain_prompt(
    workspace_id: int,
    domain: str,
    name: str,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    authorize(member, "prompt.read")
    template = _require_known_prompt(domain, name)

    effective = protected_resource_service.get_effective(
        db=db, workspace_id=workspace_id, resource_type="domain_prompt",
        resource_key=_resource_key(domain, name),
        default_content={"content": template.content},
    )
    revisions = protected_resource_service.list_revisions(
        db=db, workspace_id=workspace_id, resource_type="domain_prompt",
        resource_key=_resource_key(domain, name),
    )
    return {
        "domain": domain,
        "name": name,
        "content": effective.get("content", template.content),
        "default_content": template.content,
        "is_wired": (domain, name) in WIRED_PROMPTS,
        "revisions": [
            {
                "id": str(r.id),
                "revision_no": r.revision_no,
                "content": r.content_jsonb.get("content"),
                "is_default": r.is_default,
                "status": r.status,
                "created_by": str(r.created_by) if r.created_by else None,
                "checksum": r.checksum,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in revisions
        ],
    }


@router.patch("/{domain}/{name}")
def update_domain_prompt(
    workspace_id: int,
    domain: str,
    name: str,
    payload: DomainPromptUpdate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    authorize(member, "prompt.update")
    template = _require_known_prompt(domain, name)

    protected_resource_service.create_revision(
        db=db, workspace_id=workspace_id, resource_type="domain_prompt",
        resource_key=_resource_key(domain, name),
        content={"content": payload.content},
        actor_id=member.user_id,
        default_content={"content": template.content},
    )
    return {"domain": domain, "name": name, "content": payload.content}


@router.post("/{domain}/{name}:reset")
def reset_domain_prompt(
    workspace_id: int,
    domain: str,
    name: str,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    authorize(member, "prompt.reset")
    template = _require_known_prompt(domain, name)

    protected_resource_service.reset_to_default(
        db=db, workspace_id=workspace_id, resource_type="domain_prompt",
        resource_key=_resource_key(domain, name), actor_id=member.user_id,
    )
    return {"status": "reset", "domain": domain, "name": name, "content": template.content}
```

In `backend/app/main.py`, add the import next to the existing `feature_flags_router` import (around line 45):

```python
from app.modules.platform import prompts_router
```

Add the include next to `feature_flags_router.router` (around line 185):

```python
app.include_router(prompts_router.router, prefix="/api/v1/platform/prompts", tags=["platform-prompts"])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest app/tests/test_prompts_router.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Run the full backend test suite to catch any collateral breakage**

Run: `cd backend && python -m pytest app/tests -x -q`
Expected: PASS. Pay particular attention to any other test that imports `app.main` and asserts on the full route table or router count.

- [ ] **Step 6: Commit**

```bash
git add backend/app/modules/platform/prompts_router.py backend/app/main.py backend/app/tests/test_prompts_router.py
git commit -m "feat(platform): add prompts_router for domain prompt CRUD"
```

---

### Task 5: Flutter service layer — `PromptRegistryService`

**Files:**
- Create: `frontend/lib/data/services/prompt_registry_service.dart`
- Test: `frontend/test/prompt_registry_service_test.dart` (create)

**Interfaces:**
- Produces: `PromptRegistryService` with `listPrompts()`, `getPrompt(domain, name)`, `updatePrompt(domain, name, content)`, `resetPrompt(domain, name)`, and `PromptRegistryApiException`. Consumed by Task 6's controller.

- [ ] **Step 1: Write the failing tests**

Create `frontend/test/prompt_registry_service_test.dart`:

```dart
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/data/services/prompt_registry_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late http.Client realClient;

  setUp(() {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({'workspace_id': '123'});
  });

  tearDown(() => ApiClient.client = realClient);

  test('lists domain prompts for the current workspace', () async {
    ApiClient.client = MockClient((request) async {
      expect(request.url.path, '/api/v1/platform/prompts/');
      expect(request.url.queryParameters['workspace_id'], '123');
      return http.Response(
        jsonEncode({
          'prompts': [
            {'domain': 'cosa', 'name': 'chat_language', 'is_overridden': false, 'is_wired': true},
          ],
        }),
        200,
      );
    });

    final prompts = await PromptRegistryService().listPrompts();
    expect(prompts, [
      {'domain': 'cosa', 'name': 'chat_language', 'is_overridden': false, 'is_wired': true},
    ]);
  });

  test('throws PromptRegistryApiException on a non-2xx response', () async {
    ApiClient.client = MockClient((request) async {
      return http.Response(jsonEncode({'detail': 'Action requires owner role'}), 403);
    });

    expect(
      () => PromptRegistryService().updatePrompt('cosa', 'chat_language', 'new content'),
      throwsA(isA<PromptRegistryApiException>()),
    );
  });
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && flutter test test/prompt_registry_service_test.dart`
Expected: FAIL — `Error: Not found: 'package:frontend/data/services/prompt_registry_service.dart'`

- [ ] **Step 3: Implement `PromptRegistryService`**

Create `frontend/lib/data/services/prompt_registry_service.dart`:

```dart
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/network/api_client.dart';

class PromptRegistryApiException implements Exception {
  final int statusCode;
  final String message;
  PromptRegistryApiException(this.statusCode, this.message);

  @override
  String toString() => message;
}

class PromptRegistryService {
  Future<String> _requireWorkspaceId() async {
    final prefs = await SharedPreferences.getInstance();
    final workspaceId = prefs.getString('workspace_id');
    if (workspaceId == null || workspaceId.isEmpty) {
      throw PromptRegistryApiException(0, 'Chưa xác định workspace hiện tại');
    }
    return workspaceId;
  }

  dynamic _decode(dynamic response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) return null;
      return jsonDecode(response.body);
    }
    String detail = 'Yêu cầu thất bại (${response.statusCode})';
    try {
      final body = jsonDecode(response.body);
      if (body is Map && body['detail'] != null) {
        final d = body['detail'];
        detail = d is String ? d : jsonEncode(d);
      }
    } catch (_) {}
    throw PromptRegistryApiException(response.statusCode, detail);
  }

  Future<List<Map<String, dynamic>>> listPrompts() async {
    final wsId = await _requireWorkspaceId();
    final res = await ApiClient.get('/platform/prompts/?workspace_id=$wsId');
    final data = _decode(res);
    if (data is Map && data['prompts'] is List) {
      return (data['prompts'] as List).map((e) => Map<String, dynamic>.from(e as Map)).toList();
    }
    return [];
  }

  Future<Map<String, dynamic>> getPrompt(String domain, String name) async {
    final wsId = await _requireWorkspaceId();
    final res = await ApiClient.get('/platform/prompts/$domain/$name?workspace_id=$wsId');
    final data = _decode(res);
    return data is Map<String, dynamic> ? data : {};
  }

  Future<Map<String, dynamic>> updatePrompt(String domain, String name, String content) async {
    final wsId = await _requireWorkspaceId();
    final res = await ApiClient.patch(
      '/platform/prompts/$domain/$name?workspace_id=$wsId',
      body: {'content': content},
    );
    final data = _decode(res);
    return data is Map<String, dynamic> ? data : {};
  }

  Future<Map<String, dynamic>> resetPrompt(String domain, String name) async {
    final wsId = await _requireWorkspaceId();
    final res = await ApiClient.post('/platform/prompts/$domain/$name:reset?workspace_id=$wsId');
    final data = _decode(res);
    return data is Map<String, dynamic> ? data : {};
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && flutter test test/prompt_registry_service_test.dart`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/data/services/prompt_registry_service.dart frontend/test/prompt_registry_service_test.dart
git commit -m "feat(prompts): add PromptRegistryService for the platform prompts API"
```

---

### Task 6: Flutter controller — `PromptRegistryController`

**Files:**
- Create: `frontend/lib/modules/prompts/controllers/prompt_registry_controller.dart`
- Test: `frontend/test/prompt_registry_controller_test.dart` (create)

**Interfaces:**
- Consumes: `PromptRegistryService` (Task 5), `AuthService().getCachedRole` (existing, `frontend/lib/data/services/auth_service.dart`).
- Produces: `PromptRegistryController` with observables `prompts` (`RxList<Map<String, dynamic>>`), `isLoading` (`RxBool`), `isOwner` (`RxBool`), and methods `loadRole()`, `loadPrompts()`, `loadDetail(domain, name)`, `savePrompt(domain, name, content)`, `resetPrompt(domain, name)`. Consumed by Task 7's view.

- [ ] **Step 1: Write the failing tests**

Create `frontend/test/prompt_registry_controller_test.dart`:

```dart
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/prompts/controllers/prompt_registry_controller.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late http.Client realClient;

  setUp(() {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({'workspace_id': '123'});
  });

  tearDown(() => ApiClient.client = realClient);

  test('isOwner is true only when the cached role is owner', () async {
    final ownerController = PromptRegistryController(roleLoader: () async => 'owner');
    await ownerController.loadRole();
    expect(ownerController.isOwner.value, isTrue);

    final adminController = PromptRegistryController(roleLoader: () async => 'admin');
    await adminController.loadRole();
    expect(adminController.isOwner.value, isFalse);
  });

  test('loadPrompts populates the prompts list from the service', () async {
    ApiClient.client = MockClient((request) async {
      return http.Response(
        jsonEncode({
          'prompts': [
            {'domain': 'cosa', 'name': 'chat_language', 'is_overridden': false, 'is_wired': true},
          ],
        }),
        200,
      );
    });

    final controller = PromptRegistryController(roleLoader: () async => 'owner');
    await controller.loadPrompts();

    expect(controller.prompts.length, 1);
    expect(controller.prompts.first['domain'], 'cosa');
  });
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && flutter test test/prompt_registry_controller_test.dart`
Expected: FAIL — `Error: Not found: 'package:frontend/modules/prompts/controllers/prompt_registry_controller.dart'`

- [ ] **Step 3: Implement `PromptRegistryController`**

Create `frontend/lib/modules/prompts/controllers/prompt_registry_controller.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../data/services/auth_service.dart';
import '../../../data/services/prompt_registry_service.dart';

class PromptRegistryController extends GetxController {
  PromptRegistryController({
    PromptRegistryService? service,
    Future<String?> Function()? roleLoader,
  })  : _service = service ?? PromptRegistryService(),
        _roleLoader = roleLoader ?? AuthService().getCachedRole;

  final PromptRegistryService _service;
  final Future<String?> Function() _roleLoader;

  final prompts = <Map<String, dynamic>>[].obs;
  final isLoading = false.obs;
  final isOwner = false.obs;

  @override
  void onInit() {
    super.onInit();
    loadRole();
    loadPrompts();
  }

  Future<void> loadRole() async {
    final role = await _roleLoader();
    isOwner.value = role == 'owner';
  }

  Future<void> loadPrompts() async {
    isLoading.value = true;
    try {
      final data = await _service.listPrompts();
      prompts.assignAll(data);
    } catch (e) {
      debugPrint('Error loading prompts: $e');
    } finally {
      isLoading.value = false;
    }
  }

  Future<Map<String, dynamic>> loadDetail(String domain, String name) {
    return _service.getPrompt(domain, name);
  }

  Future<void> savePrompt(String domain, String name, String content) async {
    try {
      await _service.updatePrompt(domain, name, content);
      await loadPrompts();
      Get.snackbar(
        'Đã lưu',
        'Prompt "$domain/$name" đã được cập nhật',
        backgroundColor: const Color(0xFF10B981).withValues(alpha: 0.8),
        colorText: Colors.white,
        snackPosition: SnackPosition.BOTTOM,
      );
    } catch (e) {
      Get.snackbar(
        'Lỗi lưu prompt',
        '$e',
        backgroundColor: const Color(0xFFEF4444).withValues(alpha: 0.8),
        colorText: Colors.white,
        snackPosition: SnackPosition.BOTTOM,
      );
    }
  }

  Future<void> resetPrompt(String domain, String name) async {
    try {
      await _service.resetPrompt(domain, name);
      await loadPrompts();
      Get.snackbar(
        'Đã đặt lại mặc định',
        'Prompt "$domain/$name" đã trở về nội dung mặc định',
        backgroundColor: const Color(0xFF00E5FF).withValues(alpha: 0.8),
        colorText: Colors.black,
        snackPosition: SnackPosition.BOTTOM,
      );
    } catch (e) {
      Get.snackbar(
        'Lỗi đặt lại prompt',
        '$e',
        backgroundColor: const Color(0xFFEF4444).withValues(alpha: 0.8),
        colorText: Colors.white,
        snackPosition: SnackPosition.BOTTOM,
      );
    }
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && flutter test test/prompt_registry_controller_test.dart`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/modules/prompts/controllers/prompt_registry_controller.dart frontend/test/prompt_registry_controller_test.dart
git commit -m "feat(prompts): add PromptRegistryController with owner-gated role check"
```

---

### Task 7: Flutter view + dashboard navigation entry

**Files:**
- Create: `frontend/lib/modules/prompts/views/prompt_registry_view.dart`
- Modify: `frontend/lib/modules/dashboard/views/dashboard_view.dart`

**Interfaces:**
- Consumes: `PromptRegistryController` (Task 6).
- Produces: nav item "Quản trị Prompt AI" (index 35) in the "Cài đặt" group, routed to `PromptRegistryView`.

- [ ] **Step 1: Implement `PromptRegistryView`**

Create `frontend/lib/modules/prompts/views/prompt_registry_view.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../controllers/prompt_registry_controller.dart';

class PromptRegistryView extends StatelessWidget {
  const PromptRegistryView({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = Get.put(PromptRegistryController());

    return Scaffold(
      backgroundColor: const Color(0xFF060A14),
      body: Obx(() {
        if (controller.isLoading.value) {
          return const Center(child: CircularProgressIndicator());
        }
        final grouped = <String, List<Map<String, dynamic>>>{};
        for (final prompt in controller.prompts) {
          grouped.putIfAbsent(prompt['domain'] as String, () => []).add(prompt);
        }
        final domains = grouped.keys.toList()..sort();
        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            for (final domain in domains)
              ExpansionTile(
                title: Text(domain, style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
                initiallyExpanded: true,
                children: [
                  for (final prompt in grouped[domain]!)
                    ListTile(
                      title: Text(prompt['name'] as String, style: const TextStyle(color: Colors.white70)),
                      subtitle: Wrap(
                        spacing: 8,
                        children: [
                          if (prompt['is_overridden'] == true) const Chip(label: Text('Đã tuỳ chỉnh')),
                          if (prompt['is_wired'] != true) const Chip(label: Text('Chưa có tính năng AI dùng')),
                        ],
                      ),
                      onTap: () => _openDetail(context, controller, domain, prompt['name'] as String),
                    ),
                ],
              ),
          ],
        );
      }),
    );
  }

  Future<void> _openDetail(
    BuildContext context,
    PromptRegistryController controller,
    String domain,
    String name,
  ) async {
    final detail = await controller.loadDetail(domain, name);
    final textController = TextEditingController(text: detail['content'] as String? ?? '');
    final revisions = (detail['revisions'] as List?) ?? [];

    if (!context.mounted) return;
    await showDialog(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text('$domain/$name'),
        content: SizedBox(
          width: 480,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: textController,
                maxLines: 10,
                enabled: controller.isOwner.value,
                decoration: const InputDecoration(border: OutlineInputBorder()),
              ),
              const SizedBox(height: 12),
              Text('Lịch sử: ${revisions.length} phiên bản', style: Theme.of(dialogContext).textTheme.bodySmall),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('Đóng'),
          ),
          if (controller.isOwner.value) ...[
            TextButton(
              onPressed: () async {
                await controller.resetPrompt(domain, name);
                if (dialogContext.mounted) Navigator.of(dialogContext).pop();
              },
              child: const Text('Đặt lại mặc định'),
            ),
            FilledButton(
              onPressed: () async {
                await controller.savePrompt(domain, name, textController.text);
                if (dialogContext.mounted) Navigator.of(dialogContext).pop();
              },
              child: const Text('Lưu'),
            ),
          ],
        ],
      ),
    );
  }
}
```

- [ ] **Step 2: Register the nav item and route case in `dashboard_view.dart`**

Add the import next to the other module view imports (near line 31-32):

```dart
import '../../prompts/views/prompt_registry_view.dart';
```

In the "Cài đặt" `_NavGroup` (around line 138-141), add a new item after `index: 30`:

```dart
    _NavGroup(title: 'Cài đặt', groupIcon: Icons.settings_outlined, items: [
      _NavItem(icon: Icons.settings_outlined, selectedIcon: Icons.settings, label: 'Cài đặt', index: 13),
      _NavItem(icon: Icons.tune_rounded, selectedIcon: Icons.tune, label: 'Quản trị Template', index: 30),
      _NavItem(icon: Icons.description_outlined, selectedIcon: Icons.description, label: 'Quản trị Prompt AI', index: 35),
    ]),
```

In the view switch (around line 928-932), add the new case after `case 34`:

```dart
        case 34:
          return const TechRadarView();
        case 35:
          return const PromptRegistryView();
        default:
          return const ChatView();
```

- [ ] **Step 3: Verify the app builds**

Run: `cd frontend && flutter analyze lib/modules/prompts lib/modules/dashboard/views/dashboard_view.dart`
Expected: No errors (warnings about pre-existing code are fine, but nothing new in the files touched by this task).

- [ ] **Step 4: Manually smoke-test in a running app**

Run the app (`flutter run`), sign in as a workspace `owner`, open "Cài đặt → Quản trị Prompt AI", confirm:
- The list shows all groups including `cosa` with `chat_language`/`chat_conversation`/`chat_structured_oneshot` (no "Chưa có tính năng AI dùng" badge on those 3) and e.g. `finance/analyze` (with the badge).
- Opening a prompt shows the current content in an editable textarea with visible "Lưu"/"Đặt lại mặc định" buttons.
- Sign in as a workspace `admin` (not owner): the same screen loads read-only — no "Lưu"/"Đặt lại mặc định" buttons in the dialog.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/modules/prompts/views/prompt_registry_view.dart frontend/lib/modules/dashboard/views/dashboard_view.dart
git commit -m "feat(prompts): add Prompt Management dashboard screen and nav entry"
```

---

## Self-Review Notes

- **Spec coverage:** Every "Scope and Decisions" bullet in the spec maps to a task — wiring (Task 2), catalog-only display (Task 4/7's `is_wired` flag), exclusion list (untouched by any task, verified by Global Constraints), RBAC owner-only (Task 3), multi-tenant scoping (`workspace_id` threaded through every endpoint in Task 4), behavior-neutral cutover (Task 2 Steps 1-4 pin tests), no-new-keys-from-UI (Task 4's `_require_known_prompt` 404).
- **Known risk flagged explicitly:** Task 2 Step 6 is the fix for a real hazard — `chat_execution_service.py`'s existing tests share a `MagicMock` `db` whose `.first()` side_effect list is sized exactly to the 3 pre-existing queries (`user_message, session, brain`); adding an unrouted 4th query would exhaust it and raise `StopIteration` across most of the test file. This is called out as its own step rather than assumed away.
- **Type/name consistency check:** `render_effective` (Task 1) is called with the exact same signature `(db, workspace_id, domain, name, variables)` in Task 2 and by `PromptRegistry.get_instance()` in Task 4's router. `PromptRegistryService` method names (`listPrompts`, `getPrompt`, `updatePrompt`, `resetPrompt`) match 1:1 between Task 5's implementation and Task 6's controller usage. `PromptRegistryController`'s `roleLoader` constructor param and public `loadRole()`/`loadPrompts()`/`loadDetail()`/`savePrompt()`/`resetPrompt()` methods match what Task 7's view calls.
