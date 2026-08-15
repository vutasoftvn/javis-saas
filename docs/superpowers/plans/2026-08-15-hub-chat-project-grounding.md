# Hub Chat Project Grounding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop Hub Chat from inventing a project's title/status once and reusing that invention as fact for the rest of the conversation, by forcing a fresh `strategy_list_projects` lookup every time a specific project is referenced.

**Architecture:** Pure prompt-engineering change: two string edits (`GROUNDING_PROMPT` in `chat_execution_service.py`, and the `list_projects` chat tool description in `strategy/tools.py`). No new code paths, no server-side enforcement.

**Tech Stack:** Python, pytest.

**Spec:** `docs/superpowers/specs/2026-08-15-hub-chat-project-grounding-design.md`

## Global Constraints

- Do not add server-side enforcement that the model called a tool before answering — this plan is prompt-only, matching how every other grounding rule in `GROUNDING_PROMPT` already works.
- Do not touch the SQL retrieval fix or the streaming glitch noted as out-of-scope in the spec.

---

### Task 1: Strengthen GROUNDING_PROMPT to force re-lookup every turn

**Files:**
- Modify: `backend/app/modules/chat/chat_execution_service.py:33-47`
- Test: `backend/app/tests/test_chat_execution_service.py`

**Interfaces:**
- Consumes: none (pure string constant edit).
- Produces: `GROUNDING_PROMPT` (module-level constant, unchanged name/type — still a `str`), read by `_execute_turn` at `chat_execution_service.py:306`.

- [ ] **Step 1: Write the failing test**

Add to `backend/app/tests/test_chat_execution_service.py` (near `test_worker_tells_the_model_not_to_invent_company_data`, same file already imports `chat_execution_service` and defines `_run_one_turn`):

```python
def test_worker_forces_a_fresh_project_lookup_every_turn_that_mentions_one():
    """Bug thật đã gặp: model tự bịa tên project ở lượt đầu ('MVP Roadmap - mID - ...'
    trong khi tên thật chỉ là 'mID - ...'), rồi dùng lại đúng cái tên bịa đó ở mọi lượt
    sau - kể cả khi hỏi 'lưu roadmap'. Tool trả rỗng vì không khớp tên thật, và model báo
    sai 'không có project' dù project/roadmap/OKR/12WY đều có thật trong DB."""
    router = _run_one_turn(MagicMock())

    system_turn = next(t for t in router.last_turns if t.role == "system")
    assert "strategy_list_projects" in system_turn.content
    assert "mọi lượt" in system_turn.content or "MỌI LƯỢT" in system_turn.content
    assert "Không tự diễn giải" in system_turn.content or "không tự diễn giải" in system_turn.content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest app/tests/test_chat_execution_service.py::test_worker_forces_a_fresh_project_lookup_every_turn_that_mentions_one -v`
Expected: FAIL — the new phrases are not yet in `GROUNDING_PROMPT`.

- [ ] **Step 3: Edit GROUNDING_PROMPT**

In `backend/app/modules/chat/chat_execution_service.py`, replace lines 33-47:

```python
GROUNDING_PROMPT = (
    "\n\n[DỮ LIỆU CÔNG TY]\n"
    "Bạn có tool đọc dữ liệu THẬT của workspace này: dự án, OKR, task, blocker, việc cần "
    "duyệt, tài chính, chu kỳ. Quy tắc bắt buộc:\n"
    "- Mọi con số, tên dự án, tên OKR, trạng thái công việc chỉ được lấy từ kết quả tool. "
    "Chưa gọi tool thì bạn CHƯA BIẾT GÌ về workspace này.\n"
    "- Tuyệt đối không suy đoán, không lấy ví dụ minh hoạ thay cho dữ liệu thật, không "
    "dựng ra dự án hay chỉ số 'cho dễ hình dung'.\n"
    "- Tool trả về rỗng thì nói thẳng là workspace chưa có dữ liệu đó, và gợi ý người dùng "
    "tạo. Đó là câu trả lời đúng, không phải thất bại.\n"
    "- Người dùng gọi dự án hoặc công việc bằng TÊN: gọi strategy_list_projects hoặc "
    "tasks_list_tasks trước để tra id, rồi mới hỏi chi tiết. Không tự bịa id.\n"
    "- Bạn chỉ ĐỌC được, không tự thực hiện được hành động nào. Khi người dùng nhờ làm một "
    "việc có hệ quả thật, hãy dùng chat_propose_action để tạo đề xuất chờ họ duyệt."
)
```

with:

```python
GROUNDING_PROMPT = (
    "\n\n[DỮ LIỆU CÔNG TY]\n"
    "Bạn có tool đọc dữ liệu THẬT của workspace này: dự án, OKR, task, blocker, việc cần "
    "duyệt, tài chính, chu kỳ. Quy tắc bắt buộc:\n"
    "- Mọi con số, tên dự án, tên OKR, trạng thái công việc chỉ được lấy từ kết quả tool. "
    "Chưa gọi tool thì bạn CHƯA BIẾT GÌ về workspace này.\n"
    "- Tuyệt đối không suy đoán, không lấy ví dụ minh hoạ thay cho dữ liệu thật, không "
    "dựng ra dự án hay chỉ số 'cho dễ hình dung'.\n"
    "- Tool trả về rỗng thì nói thẳng là workspace chưa có dữ liệu đó, và gợi ý người dùng "
    "tạo. Đó là câu trả lời đúng, không phải thất bại.\n"
    "- Người dùng gọi dự án hoặc công việc bằng TÊN: gọi strategy_list_projects hoặc "
    "tasks_list_tasks trước để tra id, rồi mới hỏi chi tiết. Không tự bịa id.\n"
    "- MỌI LƯỢT nhắc tới một dự án cụ thể - kể cả dự án đã nhắc ở lượt trước trong cùng "
    "hội thoại - PHẢI gọi lại strategy_list_projects trong chính lượt đó trước khi khẳng "
    "định dự án tồn tại/không tồn tại hay mô tả trạng thái/roadmap của nó. Chỉ được dùng "
    "đúng title mà tool trả về ở lần gọi gần nhất. Không tự diễn giải, rút gọn, hay ghép "
    "thêm chữ vào tên dự án rồi dùng lại cụm đó ở các lượt sau - làm vậy là tra nhầm tên "
    "và tool sẽ trả về rỗng dù dự án có thật.\n"
    "- Bạn chỉ ĐỌC được, không tự thực hiện được hành động nào. Khi người dùng nhờ làm một "
    "việc có hệ quả thật, hãy dùng chat_propose_action để tạo đề xuất chờ họ duyệt."
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest app/tests/test_chat_execution_service.py::test_worker_forces_a_fresh_project_lookup_every_turn_that_mentions_one -v`
Expected: PASS

- [ ] **Step 5: Run the full chat execution test file to confirm no regressions**

Run: `cd backend && .venv/bin/python -m pytest app/tests/test_chat_execution_service.py -v`
Expected: all PASS (existing `test_worker_tells_the_model_not_to_invent_company_data` still passes since it only asserts substrings that remain unchanged).

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/modules/chat/chat_execution_service.py app/tests/test_chat_execution_service.py
git commit -m "fix(chat): force a fresh project lookup every turn, forbid reusing invented titles"
```

---

### Task 2: Nudge list_projects toward an empty query when the model is unsure of the exact title

**Files:**
- Modify: `backend/app/modules/strategy/tools.py:71-77`
- Test: `backend/app/tests/test_tool_registry.py`

**Interfaces:**
- Consumes: none.
- Produces: no signature change to `list_projects(db, workspace_id, query=None, limit=DEFAULT_ROWS)` — only its registered `chat_schema["parameters"]["properties"]["query"]["description"]` string changes.

- [ ] **Step 1: Write the failing test**

Add to `backend/app/tests/test_tool_registry.py` (this file already has `_real_tool_specs()` and imports `get_registered_tools`):

```python
def test_list_projects_tool_tells_the_model_to_leave_query_empty_when_unsure():
    """Lọc sai một phần tên (vd. model tự thêm/bớt chữ) khiến ILIKE không khớp và tool
    trả về rỗng một cách im lặng - đúng nguyên nhân model kết luận nhầm 'không có project'
    trong khi project có thật. Mô tả tool phải dặn model để trống query khi không chắc."""
    specs = _real_tool_specs()
    query_description = specs["strategy.list_projects"].chat_schema["parameters"]["properties"]["query"]["description"]
    assert "để trống" in query_description
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest app/tests/test_tool_registry.py::test_list_projects_tool_tells_the_model_to_leave_query_empty_when_unsure -v`
Expected: FAIL — current description doesn't yet contain the new guidance sentence.

- [ ] **Step 3: Edit the tool description**

In `backend/app/modules/strategy/tools.py`, replace lines 71-77:

```python
                "query": {
                    "type": "string",
                    "description": (
                        "Lọc theo một phần tên dự án, không phân biệt hoa thường. Để "
                        "trống để lấy tất cả."
                    ),
                },
```

with:

```python
                "query": {
                    "type": "string",
                    "description": (
                        "Lọc theo một phần tên dự án, không phân biệt hoa thường. Để "
                        "trống để lấy tất cả. Không chắc chắn tên chính xác của dự án "
                        "(kể cả tên bạn từng nhắc ở lượt trước)? Để trống query và lọc "
                        "trong kết quả trả về, thay vì đoán một cụm lọc - lọc sai dù chỉ "
                        "một ký tự cũng khiến tool trả về rỗng dù dự án có thật."
                    ),
                },
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest app/tests/test_tool_registry.py::test_list_projects_tool_tells_the_model_to_leave_query_empty_when_unsure -v`
Expected: PASS

- [ ] **Step 5: Run the full tool registry test file to confirm no regressions**

Run: `cd backend && .venv/bin/python -m pytest app/tests/test_tool_registry.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/modules/strategy/tools.py app/tests/test_tool_registry.py
git commit -m "fix(strategy): tell chat to leave list_projects query empty when unsure of the exact title"
```

## Plan Self-Review

- Spec coverage: both `GROUNDING_PROMPT` and `list_projects` description changes from the spec are covered (Task 1, Task 2). The spec's explicit non-goals (server-side enforcement, the garbled-text bug, write capability) have no corresponding task, as intended.
- Both tasks are independent of each other and of the second plan (`2026-08-15-orchestrator-project-cycle-command.md`) — either can be implemented and merged alone.
