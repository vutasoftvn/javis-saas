# Python Quality Gates Fix — Design

Status: DRAFT (chờ user review)
Ngày: 2026-09-14
Phạm vi: sub-project #2/6 trong đợt audit "Ba blocker lớn nhất" (2026-09-14) — P0.
Các sub-project khác có spec riêng, không nằm trong tài liệu này. Xem
[2026-09-14-schedule-project-scope-design.md](2026-09-14-schedule-project-scope-design.md)
cho sub-project #1.

## Vấn đề

`make verify` dừng ở 3 gate Python:

1. `ruff format --check` — 71 file cần format (packages/agent, apps/cosa,
   packages/agent_integrations). Xác nhận lại 2026-09-14: đúng 71 file, 371
   file đã đúng format.
2. `make typecheck-py` (mypy) — 33 lỗi / 14 file. Xác nhận lại: đúng 33 lỗi
   trong 14 file (checked 426 source files).
3. `make apps-cosa-test` — 13 test fail + 1 lỗi collection, sau khi thêm
   Project Team Authority (`apps/cosa/worker/handlers.py:228`,
   `PROJECT_TEAM_OPERATING_PROFILES`). Xác nhận lại: 13 failed, 1215 passed,
   20 skipped, 1 error.

Guard authority (`handlers.py:228`) **đúng** — không phải lý do để nới. Bug
nằm ở fixture: các test dựng `plane` qua helper local không set
`plane.project_team_client`, khiến guard cố gọi HTTP thật ra ngoài
(`ProjectTeamClient()` mặc định trỏ `localhost:4000`) và fail với "Company
service unreachable" — dừng đúng ở fail-closed **trước khi tới phần logic
test thực sự muốn kiểm** (compliance/kernel/knowledge gateway).

**2 bug thật phát hiện khi điều tra mypy (không phải type noise):**

- `packages/agent/kernel/openai_agents_kernel.py:187` và
  `packages/agent_integrations/langchain/kernel.py:209` gọi
  `record_resolved_pins(..., agent_spec=pinned_spec, ...)` nhưng tham số
  thật của `SkillUsageObserver.record_resolved_pins`
  (`packages/agent/skills/usage_observer.py:36`) tên là `root_spec`, không
  phải `agent_spec`. Gọi sai keyword này raise `TypeError` bất cứ khi nào
  `plane._skill_usage_observer is not None` — nghĩa là tính năng ghi nhận
  skill usage đang crash ngầm trong runtime OpenAI Agents kernel.
- `apps/cosa/api/project_activity_routes.py:96` gọi
  `plane.conversation_repository.get_message(source_id)` cho
  `source_type == "message"`, nhưng `get_message` không tồn tại ở bất kỳ
  đâu — không trong `Protocol ConversationRepository`
  (`packages/agent/conversations/repository.py:24`), không trong bất kỳ
  implementation nào (InMemory/Postgres). Nhánh này luôn raise
  `AttributeError`.

## Chiến lược tổng thể

3 gate độc lập, sửa theo đúng thứ tự — **formatter → type contract →
fixture** — mỗi bước 1 commit riêng để dễ review/revert nếu 1 bước có vấn
đề. Formatter thuần cơ học không được lẫn vào diff của phần sửa bug thật.

### 1. Formatter (commit 1)

Chạy `ruff format` (qua `make lint-fix` phần format) trên `packages/agent`,
`apps/cosa`, `packages/agent_integrations`. Không có quyết định thiết kế —
thuần cơ học, không đụng logic.

### 2. Type contract (commit 2)

Chia 33 lỗi thành 2 nhóm, chính sách khác nhau:

**Nhóm A — bug thật, sửa đúng contract:**

- `record_resolved_pins`: đổi keyword tại 2 call site từ `agent_spec=` →
  `root_spec=`.
- `get_message`: thêm `async def get_message(self, message_id: str) ->
  MessageRecord | None` vào `Protocol ConversationRepository`, implement ở
  `InMemoryConversationRepository` và implementation Postgres tương ứng
  (tra cứu theo `message_id`, trả `None` nếu không tồn tại — cùng convention
  với `get_conversation`).

**Nhóm B — nullability cần thắt chặt** (phần lớn 33 lỗi, vd.
`runs/expiry.py:52`, `capabilities/approval_service.py:366`,
`executive_board/runner.py:57-95`, `api/workforce_routes.py:1028,1037`,
`api/project_activity_routes.py:305-319`): giá trị `Optional` được truyền
vào nơi đòi kiểu bắt buộc. Chính sách:

- Không dùng `cast()`/`# type: ignore` để che lỗi.
- Nếu giá trị **có thể hợp lệ là `None`** theo nghiệp vụ tại điểm đó: thêm
  guard rõ ràng (raise lỗi có ý nghĩa hoặc early-return) trước khi dùng.
- Nếu giá trị **không bao giờ thực sự `None`** ở runtime (do invariant nơi
  khác đảm bảo, chỉ là type annotation quá rộng): sửa type ở nguồn
  (constructor/factory trả kiểu chặt hơn), không assert vô nghĩa tại điểm
  dùng.

**Nhóm C — type-only, sửa tại chỗ:**

- `apps/cosa/composition/workflow_orchestration.py:184` (`Missing return
  statement`, class `IWorkflowOrchestration` không kế thừa `Protocol`) —
  đổi `class IWorkflowOrchestration:` → `class IWorkflowOrchestration(
  Protocol):` để mypy hiểu thân hàm `...` là abstract stub, không phải thiếu
  return.
- `packages/agent/workflows/validation.py:110` (`PydanticDescriptorProxy
  not callable`) — sửa cách gọi decorator Pydantic validator cho đúng API.
- `apps/cosa/graphql/resolvers.py:149` (thiếu type annotation cho
  `allowed_variables`) — thêm annotation tường minh.
- `packages/agent/workflows/engine.py:208,216` (callback signature lệch) —
  sửa type alias callback cho khớp chữ ký thật đang dùng.

### 3. Fixture (commit 3)

**File mới:** `tests/apps/cosa/project_team_test_helpers.py` — theo pattern
`tests/apps/cosa/policy_test_helpers.py` đã có
(`fake_active_tenant_policy_client`).

```python
def fake_project_team_client(
    *, workspace_id: str = "ws_1", project_id: str = "proj_1",
    profile_key: str = "operations",
) -> AsyncMock:
    """AsyncMock(spec=ProjectTeamClient) mà get_run_authority() luôn
    resolve thành công với 1 ProjectAgentRunAuthority hợp lệ (spec/hash lấy
    từ spec thật đã seed qua seed_cosa_runtime_specs, không phải chuỗi giả
    tùy tiện) cho đúng workspace/project/profile truyền vào. Test cần
    authority DENY (test_project_team_authority.py) tự cấu hình side_effect
    riêng, không dùng helper này."""
```

Áp dụng cho đúng 13 test đang fail (cùng root cause — thiếu
`plane.project_team_client`): `test_run_delegation.py` (5 test),
`test_worker_wiring.py` (2 test), `test_founder_knowledge_context.py`
(2 test), `test_lifecycle_tranche_c_acceptance.py`,
`test_scheduled_session_worker.py`, `test_vertical_slice_1_read_path.py`,
`test_workspace_execution_e2e.py`. Mỗi file chỉ thêm đúng 1 dòng
`plane.project_team_client = fake_project_team_client(...)` vào helper dựng
`plane` sẵn có của file đó — không đổi assertion nghiệp vụ nào khác (các
assertion đó vốn đã đúng, chỉ chưa từng chạy tới được vì guard chặn sớm
hơn).

**Không đụng:** `test_project_team_authority.py`, `test_handlers.py` (đã
đúng từ trước — đây chính là pattern mẫu để viết helper). Và
`test_sse_reconnect_e2e.py` (lỗi `ERROR` chỉ xuất hiện khi chạy full suite,
skip khi chạy riêng lẻ — nghi ngờ liên quan global state/ordering, cùng họ
vấn đề GetX bên Flutter ở P2. Thuộc phạm vi sub-project #6 (test
reliability), không fix lẫn ở đây để tránh mở rộng ngoài ý audit).

## Testing / Verification

Xác nhận từng gate xanh sau mỗi commit, không dồn tới cuối:

1. Sau commit 1: `ruff format --check packages/agent apps/cosa
   packages/agent_integrations` → 0 file cần reformat; `make lint` xanh.
2. Sau commit 2: `make typecheck-py` → 0 lỗi. Thêm test cho 2 bug thật:
   - `record_resolved_pins`: test gọi bằng đúng `root_spec=` không raise,
     giữ nguyên hành vi ghi nhận usage (`tests/agent/skills/
     test_usage_observer.py` hoặc file tương đương nếu đã có).
   - `get_message`: test `project_activity_routes.py` case
     `source_type == "message"` trả đúng payload thay vì crash — cả với
     InMemory và Postgres repository (test qua implementation thật, không
     chỉ mock — theo CLAUDE.md quy tắc 6).
3. Sau commit 3: `make apps-cosa-test` → 0 fail, coverage vẫn ≥ 78% (không
   hạ threshold để né).

**Test thứ tự guard** (yêu cầu riêng của audit — "authority phải chặn
trước kernel và không có side effect"), thêm vào
`tests/apps/cosa/worker/test_project_team_authority.py`:

- Setup `plane.project_team_client` mock raise `ProjectTeamAuthorityError`.
- Spy `plane.kernel.run` (pattern `_spy_run` từ `test_run_delegation.py`).
- Chạy `execute_run_task` với 1 agent_profile trong
  `PROJECT_TEAM_OPERATING_PROFILES`.
- Assert `plane.kernel.run` không được gọi, và không có `MessageRecord`
  role=`assistant` nào được tạo — chỉ `MessageRecord(role="user")` đã ghi
  trước guard.

**Gate tổng hợp cuối:** `make verify` đầy đủ (không chỉ 3 target riêng lẻ)
trước khi báo cáo sub-project #2 hoàn thành.

## Ngoài phạm vi (out of scope)

- `test_sse_reconnect_e2e.py` fail khi chạy full suite — thuộc sub-project
  #6 (test reliability).
- Bất kỳ lỗi mypy/format phát sinh mới sau khi spec này viết (nếu code thay
  đổi giữa lúc viết spec và lúc thực thi plan) — plan triển khai cần chạy
  lại 3 lệnh xác nhận số liệu trước khi bắt đầu sửa.
