# Verifier WGA — phần còn lại (Dự án B, đợt 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.


> **Trạng thái thực thi (2026-10-12):** các task đã được thực thi bằng subagent-driven-development, mỗi task có review riêng và có review cuối toàn nhánh; commit nằm trên `main`. Các bước kiểm tay trên stack chạy thật (nếu có trong Step cổng chất lượng) **chưa được chạy, theo quyết định của chủ dự án 2026-10-12** (không dựng stack và không gọi DeepSeek thật ở đợt này); các cổng tự động đã chạy và pass như ghi trong runbook/báo cáo. Chạy kiểm tay khi có môi trường phù hợp.

**Goal:** Hoàn tất các việc còn lại của Verifier: kiểm cả đường resume sau duyệt và task `NEEDS_APPROVAL`, đánh giá được tiêu chí `metric_gte`, ép được mô hình thẩm phán độc lập qua REST, cho founder thấy verdict trên Flutter, và có cổng quyết định có số liệu trước khi bật cờ mặc định.

**Architecture:** (1) Company thêm một endpoint đọc ngữ cảnh task cho worker (`doneCriteria`, tiêu đề, profile, project) để đường resume biết tiêu chí. (2) `wga_run.py` gom logic xác minh thành hàm dùng chung cho đường ban đầu và đường resume. (3) `metric_gte` đọc giá trị KR qua endpoint Company có sẵn `GET /operations/key-results` (capability `okr.objective.list`). (4) Model-policy REST nhận thêm scope nội bộ `verifier`. (5) API báo cáo có thêm truy vấn theo lô `taskIds`, Flutter hiển thị huy hiệu trên thẻ kanban. (6) Runbook + cổng quyết định bật mặc định.

**Tech Stack:** Encore.ts + Drizzle (services/company), Python (apps/cosa, packages/agent), Flutter/GetX (frontend), pytest, Vitest dưới `encore test`.

Tài liệu gốc: `docs/superpowers/plans/2026-10-06-verifier-wga-completion-impl.md` (đợt 1, đã xong) và mục "Còn lại" của `docs/superpowers/plans/2026-10-05-agent-structure-B-verifier-gate.md` (Task 6 cập nhật nó).

## Phạm vi và quyết định (sau khi đọc code, 2026-10-12)

**Trong phạm vi:** verify đường resume; verify task `NEEDS_APPROVAL` chạy xong không qua checkpoint; `metric_gte`; model-policy REST cho thẩm phán; UI Flutter hiển thị verdict; cổng bật cờ mặc định.

**Ngoài phạm vi (ghi rõ để không bị hiểu là đã làm):** cổng duyệt cho workflow engine (không workflow production nào có approval); nối `BudgetGate` vào runtime; đưa verdict vào hash duyệt hoặc scorecard.

Quyết định thiết kế:

1. **Đường resume không có dữ liệu để xác minh.** `advance_wga_task_after_resume` (`wga_run.py:211`) chỉ nhận `run_id`, `workspace_id`, `sub`, `output_text`; task `waiting_approval` không nằm trong `agent-claimable`; `GET /operations/tasks/:id` trả `Task` không có `doneCriteria`. Vì vậy cần endpoint Company mới `GET /operations/tasks/:id/agent-context` (Task 1), dùng cùng capability `operations.task.list` như sweep.
2. **Fail-closed khi không lấy được ngữ cảnh** lúc cờ bật: task giữ `in_progress` với note `verification_inconclusive: context_unavailable`, không đóng. Cờ tắt thì hành vi cũ.
3. **Task `NEEDS_APPROVAL` chạy xong không qua checkpoint** (nhánh `done` ở `wga_run.py:742`) vốn **không bao giờ tự đóng** (`evidence_refs=None`). Vẫn chạy xác minh để founder thấy verdict và báo cáo, nhưng kết quả PASS không làm task tự đóng.
4. **Đường resume sau duyệt:** founder đã duyệt hành động, nhưng chưa duyệt *kết quả*. PASS ⇒ đóng `done` như hiện nay (kèm `verification:<id>`); FAIL/INCONCLUSIVE ⇒ `in_progress` + note. Từ chối vẫn không bao giờ đóng task (giữ nguyên).
5. **`metric_gte` đọc giá trị KR hiện tại** bằng `GET /operations/key-results` (đã nhận agent capability `okr.objective.list`; trả `currentValue` dạng `number | null`). Ngữ nghĩa: `currentValue >= threshold`. Rủi ro đạt rỗng (KR đã đạt từ trước): thêm `args.must_change` (bool, mặc định `false`); khi `true`, chụp giá trị **trước** khi chạy và FAIL nếu không đổi. Tiêu chí cho KR kiểu giảm (churn) nên dùng ngưỡng riêng; không đảo chiều so sánh trong v1.
6. **Mô hình thẩm phán độc lập qua REST:** `model_policy_routes._resolve_agent_spec_id` chỉ biết `AGENT_PROFILE_SPECS`, và theo quyết định đợt 1 `verifier` **không** được thêm vào bảng đó. Thêm bảng riêng `INTERNAL_MODEL_POLICY_SPECS = {"verifier": COSA_VERIFIER_AGENT_SPEC}` chỉ dùng cho route này (Task 4).
7. **UI: một request theo lô cho cả bảng**, không N+1. API thêm tham số `taskIds` (tối đa 50, phân tách bằng dấu phẩy) trả báo cáo **mới nhất** của mỗi task.
8. **Bật mặc định cần quyết định của con người dựa trên số liệu** (Task 6): không tự đổi mặc định trong phiên triển khai nếu chưa có bằng chứng quan sát.

## Global Constraints

- Code trực tiếp trên `main`, không worktree, không `git init`. Commit cuối mỗi task, kèm trailer `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- TypeScript hiện đại, `import` ES, không `require`; Python: `source .venv/bin/activate`, `PYTHONPATH=.:packages:apps`.
- Mọi truy vấn lọc `workspace_id`; không tin id từ client chưa kiểm workspace. Workspace của API Python chỉ lấy từ principal đã xác thực.
- Không thêm `verifier` vào `OWNER_AGENT_PROFILES` / `AGENT_PROFILE_SPECS` / `SUPPORTED_AGENT_PROFILES`; `tests/contracts/test_company_agent_spec_pins.py` phải vẫn xanh.
- Dữ liệu từ producer là không đáng tin; note hiển thị cho founder chỉ chứa **mã** (id tiêu chí và mã cố định), không có lời giải thích tự do của thẩm phán.
- Mọi lỗi của verifier là `INCONCLUSIVE`, không bao giờ làm task đóng nhầm hay làm sweep/resume bị ngắt.
- Chạy test company: `cd services/company && encore test <file>` sau `set -a; source scripts/load-dev-env.sh; set +a; unset WORKER_SERVICE_JWT_SECRET`.
- Lỗi có sẵn ngoài phạm vi: `shared/tests/golden-path.e2e.test.ts`, test gọi DeepSeek thật, 4 test `apps/cosa` phụ thuộc môi trường.
- Lệnh ghi vào repo bị sandbox chặn: chạy lại với `dangerouslyDisableSandbox: true`. Với `frontend/*`: chạy `git status --short frontend` trước, nếu có chỉnh sửa chưa commit của người dùng thì **không** đụng file đó; `git add` theo đường dẫn cụ thể.

## File Structure

| File | Trách nhiệm | Task |
|---|---|---|
| `services/company/operations/services/task.service.ts`, `handlers/task.handler.ts` | `getTaskAgentContextService` + `GET /operations/tasks/:id/agent-context` | 1 |
| `apps/cosa/worker/wga_run.py` | `fetch_task_agent_context`, `_verify_completed_run`, verify ở đường resume và `NEEDS_APPROVAL` | 2 |
| `apps/cosa/worker/handlers.py` | Truyền `final_output` cho `advance_wga_task_after_resume` | 2 |
| `packages/agent/verification/models.py`, `deterministic.py` | `RunFacts.metrics/metrics_before`, đánh giá `metric_gte` | 3 |
| `apps/cosa/worker/wga_verify.py` | `fetch_kr_values`, nối vào `_verify_task_result` | 3 |
| `apps/cosa/api/model_policy_routes.py`, `apps/cosa/agents/catalog.py` | Scope `verifier` cho model-policy REST | 4 |
| `packages/agent/verification/repository.py`, `apps/cosa/api/workforce_routes.py` | `list_latest_for_tasks` + tham số `taskIds` | 5 |
| `shared/contracts/mvp-surface.json`, `frontend/lib/...` | Hợp đồng + huy hiệu verdict trên thẻ kanban | 5 |
| `docs/runbooks/wga-verifier.md`, thiết kế B | Rollout + trạng thái | 6 |

---

### Task 1: Endpoint Company đọc ngữ cảnh task cho worker

**Files:**
- Modify: `services/company/operations/services/task.service.ts` (cạnh `listAgentClaimableTasksService`, ~L640), `services/company/operations/handlers/task.handler.ts` (cạnh `listAgentClaimableTasks`, L162)
- Test: `services/company/operations/tests/task-agent-context.test.ts`

**Interfaces:**
- Consumes: `executionPlanItems.doneCriteria`, `executionPlanItems.materializedTaskId`, `resolveCosaTaskContext`, `WGA_CAP_TASK_LIST`.
- Produces:
  - `interface TaskAgentContext { taskId: string; workspaceId: string; title: string; projectId: string; autonomyClass: "AUTO" | "NEEDS_APPROVAL"; ownerAgentProfile: string; decisionReason: string; doneCriteria: DoneCriteria | null }`.
  - `getTaskAgentContextService(wsId: bigint, taskId: string): Promise<TaskAgentContext>` — `APIError.notFound` khi task không thuộc workspace, đã xóa mềm, hoặc không phải task sinh từ execution plan.
  - `GET /operations/tasks/:id/agent-context` → `TaskAgentContext`.

- [x] **Step 1: Viết test thất bại** (`task-agent-context.test.ts`; copy helper `seedAcceptedPlan`/`autoItem` từ `agent-claimable.test.ts` hoặc import nếu đã có ở `_helpers.ts`):

```ts
import { describe, expect, it } from "vitest";
import { getTaskAgentContextService } from "../services/task.service";
// import { seedAcceptedPlan, autoItem } từ cùng nơi agent-claimable.test.ts lấy

const CRITERIA = {
  version: 1,
  criteria: [{ id: "c1", description: "Có tài liệu", required: true, check: "rubric", rubric: "Có tài liệu" }],
};

describe("getTaskAgentContextService", () => {
  it("returns title, profile, project and done criteria of a plan-materialized task", async () => {
    const s = await seedAcceptedPlan([autoItem("Có tiêu chí", { doneCriteria: CRITERIA })]);
    const [claimable] = await listAgentClaimableTasksService(s.workspaceId, 10, s.auth);
    const ctx = await getTaskAgentContextService(BigInt(s.workspaceId), claimable!.taskId);
    expect(ctx).toMatchObject({
      taskId: claimable!.taskId,
      title: "Có tiêu chí",
      projectId: s.projectId,
      autonomyClass: "AUTO",
      doneCriteria: CRITERIA,
    });
  });

  it("returns null criteria when the item has none", async () => {
    const s = await seedAcceptedPlan([autoItem("Trống", {})]);
    const [claimable] = await listAgentClaimableTasksService(s.workspaceId, 10, s.auth);
    expect((await getTaskAgentContextService(BigInt(s.workspaceId), claimable!.taskId)).doneCriteria).toBeNull();
  });

  it("does not leak a task from another workspace", async () => {
    const a = await seedAcceptedPlan([autoItem("A", {})]);
    const b = await seedAcceptedPlan([autoItem("B", {})]);
    const [claimable] = await listAgentClaimableTasksService(a.workspaceId, 10, a.auth);
    await expect(
      getTaskAgentContextService(BigInt(b.workspaceId), claimable!.taskId),
    ).rejects.toThrow(/not found/);
  });

  it("rejects a task that is not materialized from a plan item", async () => {
    // task tạo tay qua createTaskService, không có plan item
    ...
  });
});
```

Thân test cuối viết đầy đủ theo cách `task.service.test.ts` tạo task thường (không để dấu `...` khi triển khai). Run: `cd services/company && encore test operations/tests/task-agent-context.test.ts` → Expected: FAIL (hàm chưa có).

- [x] **Step 2: Cài đặt service**

```ts
export interface TaskAgentContext {
  taskId: string;
  workspaceId: string;
  title: string;
  projectId: string;
  autonomyClass: "AUTO" | "NEEDS_APPROVAL";
  ownerAgentProfile: string;
  decisionReason: string;
  doneCriteria: DoneCriteria | null;
}

/**
 * Ngữ cảnh để worker xác minh một task đã chạy (đường resume sau duyệt không còn dòng
 * agent-claimable vì task không còn 'todo'). Chỉ task sinh từ execution plan item.
 */
export async function getTaskAgentContextService(
  wsId: bigint,
  taskId: string,
): Promise<TaskAgentContext> {
  const [row] = await db
    .select({
      taskId: tasks.id,
      workspaceId: tasks.workspaceId,
      title: tasks.title,
      projectId: executionPlans.projectId,
      autonomyClass: executionPlanItems.autonomyClass,
      ownerAgentProfile: executionPlanItems.ownerAgentProfile,
      decisionReason: executionPlanItems.decisionReason,
      doneCriteria: executionPlanItems.doneCriteria,
    })
    .from(tasks)
    .innerJoin(executionPlanItems, eq(executionPlanItems.materializedTaskId, tasks.id))
    .innerJoin(executionPlans, eq(executionPlans.id, executionPlanItems.planId))
    .where(and(eq(tasks.id, BigInt(taskId)), eq(tasks.workspaceId, wsId), isNull(tasks.deletedAt)))
    .limit(1);
  if (!row) throw APIError.notFound(`task ${taskId} not found`);
  return {
    taskId: row.taskId.toString(),
    workspaceId: row.workspaceId.toString(),
    title: row.title,
    projectId: row.projectId.toString(),
    autonomyClass: row.autonomyClass as "AUTO" | "NEEDS_APPROVAL",
    ownerAgentProfile: row.ownerAgentProfile,
    decisionReason: row.decisionReason ?? "",
    doneCriteria: (row.doneCriteria as DoneCriteria | null) ?? null,
  };
}
```

`BigInt(taskId)` ném `SyntaxError` với id không phải số; bọc: `if (!/^\d+$/.test(taskId)) throw APIError.invalidArgument("task id must be numeric")` ở đầu hàm.

- [x] **Step 3: Handler**, ngay sau `listAgentClaimableTasks`:

```ts
// Gọi bởi worker apps/cosa (đường resume sau duyệt) — cosa delegation, tái dùng
// capability operations.task.list (chỉ đọc).
export const getTaskAgentContext = api(
  { method: "GET", path: "/operations/tasks/:id/agent-context", expose: true },
  async ({
    id,
    workspaceId,
    authorization,
  }: {
    id: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
  }): Promise<TaskAgentContext> => {
    const ctx = resolveCosaTaskContext(authorization, {
      workspaceId,
      capabilityId: WGA_CAP_TASK_LIST,
    });
    return getTaskAgentContextService(BigInt(ctx.workspaceId), id);
  },
);
```

- [x] **Step 4: Chạy test + typecheck + gate**

Run: `cd services/company && npm run typecheck && encore test operations/tests/task-agent-context.test.ts operations/tests/agent-claimable.test.ts`; `make route-inventory-check route-auth-allowlist-check mvp-contracts-check`. Nếu route inventory/allowlist đổi, chạy generator tương ứng (`make route-inventory`, …), **không** sửa tay file sinh ra; route mới không vào `mvp-surface.json` (chỉ worker dùng).
Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add services/company/operations/services/task.service.ts services/company/operations/handlers/task.handler.ts services/company/operations/tests/task-agent-context.test.ts
git commit -m "feat(wga): endpoint agent-context để worker xác minh task sau duyệt"
```
(Thêm file sinh ra khác nếu gate yêu cầu: route inventory, allowlist.)

---

### Task 2: Xác minh ở đường resume và task `NEEDS_APPROVAL`

**Files:**
- Modify: `apps/cosa/worker/wga_run.py` (`_execute_claimed_task` L728-770, `advance_wga_task_after_resume` L211-241), `apps/cosa/worker/handlers.py` (L1637-1643)
- Test: `tests/apps/cosa/wga/test_wga_verify_resume.py`, cập nhật `tests/apps/cosa/wga/test_wga_run.py` (ca `needs_approval`)

**Interfaces:**
- Consumes: `verify_task_result`, `verification_enabled`, `VerificationOutcome`, `Verdict` (đã có); `GET /operations/tasks/:id/agent-context` (Task 1).
- Produces:
  - `async def fetch_task_agent_context(plane, *, workspace_id: str, task_id: str, sub: str, run_id: str) -> dict[str, Any] | None` — `None` khi `CompanyServiceError`/phản hồi không phải dict.
  - `async def _verify_completed_run(plane, *, spec: AgentSpec, workspace_id: str, project_id: str, task_id: str, task_run_id: str, title: str, decision_reason: str, done_criteria: dict[str, Any] | None, run_result: Any, output_text: str) -> VerificationOutcome | None` — `None` khi cờ tắt hoặc không có tiêu chí; **không bao giờ ném** (lỗi ⇒ `INCONCLUSIVE`).
  - `advance_wga_task_after_resume(..., final_output: Any = None)` (tham số mới, tùy chọn).

- [x] **Step 1: Test thất bại — resume** (`test_wga_verify_resume.py`). Stub `fetch_task_agent_context`, `verify_task_result`, `record_wga_task_evidence`, `_advance_task`, `finalize_wga_task_completion` bằng `monkeypatch`:

```python
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from agent.verification import Verdict
from apps.cosa.worker import wga_run
from apps.cosa.worker.wga_verify import VerificationOutcome

pytestmark = pytest.mark.asyncio

_CTX = {
    "taskId": "123", "workspaceId": "ws1", "title": "T", "projectId": "p1",
    "autonomyClass": "NEEDS_APPROVAL", "ownerAgentProfile": "operations",
    "decisionReason": "R",
    "doneCriteria": {"version": 1, "criteria": [
        {"id": "c1", "description": "d", "required": True, "check": "rubric", "rubric": "r"}]},
}
_RUN = "wga_task_123_ab12cd34"


@pytest.fixture
def stubs(monkeypatch):
    s = SimpleNamespace(
        ctx=AsyncMock(return_value=dict(_CTX)),
        verify=AsyncMock(),
        evidence=AsyncMock(return_value=["artifact:a1", f"run:{_RUN}"]),
        advance=AsyncMock(return_value=True),
        finalize=AsyncMock(return_value=True),
    )
    monkeypatch.setenv("WGA_VERIFY_ON_COMPLETE", "1")
    monkeypatch.setattr(wga_run, "fetch_task_agent_context", s.ctx)
    monkeypatch.setattr(wga_run, "verify_task_result", s.verify)
    monkeypatch.setattr(wga_run, "record_wga_task_evidence", s.evidence)
    monkeypatch.setattr(wga_run, "_advance_task", s.advance)
    monkeypatch.setattr(wga_run, "finalize_wga_task_completion", s.finalize)
    return s


async def _go(**over):
    kw = dict(run_id=_RUN, workspace_id="ws1", sub="7", output_text="kết quả")
    kw.update(over)
    await wga_run.advance_wga_task_after_resume(SimpleNamespace(), **kw)


async def test_pass_closes_with_verification_evidence(stubs):
    stubs.verify.return_value = VerificationOutcome(Verdict.PASS, "vr_1", "ok", [])
    await _go()
    kw = stubs.finalize.await_args.kwargs
    assert "verification:vr_1" in kw["evidence_refs"]


async def test_fail_keeps_in_progress_and_never_finalizes(stubs):
    stubs.verify.return_value = VerificationOutcome(Verdict.FAIL, "vr_1", "0/1 c1(fail)", [])
    await _go()
    stubs.finalize.assert_not_awaited()
    kw = stubs.advance.await_args.kwargs
    assert kw["to_status"] == "in_progress" and kw["note"].startswith("verification_fail")


async def test_inconclusive_keeps_in_progress(stubs):
    stubs.verify.return_value = VerificationOutcome(Verdict.INCONCLUSIVE, None, "judge_timeout", [])
    await _go()
    stubs.finalize.assert_not_awaited()
    assert stubs.advance.await_args.kwargs["note"].startswith("verification_inconclusive")


async def test_context_unavailable_is_fail_closed_when_flag_on(stubs):
    stubs.ctx.return_value = None
    await _go()
    stubs.finalize.assert_not_awaited()
    assert "context_unavailable" in stubs.advance.await_args.kwargs["note"]


async def test_flag_off_keeps_legacy_behaviour_and_skips_context_fetch(stubs, monkeypatch):
    monkeypatch.delenv("WGA_VERIFY_ON_COMPLETE")
    await _go()
    stubs.ctx.assert_not_awaited()
    stubs.verify.assert_not_awaited()
    stubs.finalize.assert_awaited_once()


async def test_no_criteria_means_no_verification(stubs):
    stubs.ctx.return_value = {**_CTX, "doneCriteria": None}
    await _go()
    stubs.verify.assert_not_awaited()
    stubs.finalize.assert_awaited_once()


async def test_structured_final_output_reaches_the_verifier(stubs):
    stubs.verify.return_value = VerificationOutcome(Verdict.PASS, "vr_1", "ok", [])
    await _go(final_output={"summary": "x"})
    assert stubs.verify.await_args.kwargs["run_result"].final_output == {"summary": "x"}


async def test_non_wga_run_id_is_a_noop(stubs):
    await _go(run_id="chat_run_1")
    stubs.ctx.assert_not_awaited()
    stubs.finalize.assert_not_awaited()
```

Thêm vào `test_wga_run.py` một ca: task `NEEDS_APPROVAL` chạy xong không qua checkpoint, cờ bật, criteria có ⇒ `verify_task_result` **được gọi**; verdict PASS ⇒ **vẫn** gọi `finalize_wga_task_completion` với `evidence_refs=None` (không tự đóng); verdict FAIL ⇒ `_advance_task(..., "in_progress")` và trả `"pending_review"`.

Run: `PYTHONPATH=.:packages:apps python -m pytest tests/apps/cosa/wga/test_wga_verify_resume.py -q -p no:cacheprovider` → Expected: FAIL.

- [x] **Step 2: Cài đặt helper dùng chung** trong `wga_run.py` (đặt gần `finalize_wga_task_completion`):

```python
async def fetch_task_agent_context(
    plane: CosaAgentPlane, *, workspace_id: str, task_id: str, sub: str, run_id: str
) -> dict[str, Any] | None:
    """Ngữ cảnh task (tiêu chí, tiêu đề, profile, project) cho đường resume. None khi không lấy được."""
    token = mint_company_delegation(
        sub=sub, workspace_id=workspace_id, run_id=run_id, capability_ids=[_CAP_TASK_LIST]
    )
    try:
        resp = await plane.company_client.get(
            f"/operations/tasks/{task_id}/agent-context",
            headers={"X-Workspace-Id": workspace_id, "Authorization": f"Bearer {token}"},
        )
    except CompanyServiceError as exc:
        logger.warning("agent-context fetch failed ws=%s task=%s: %s", workspace_id, task_id, exc)
        return None
    return resp if isinstance(resp, dict) else None


async def _verify_completed_run(
    plane: CosaAgentPlane,
    *,
    spec: AgentSpec,
    workspace_id: str,
    project_id: str,
    task_id: str,
    task_run_id: str,
    title: str,
    decision_reason: str,
    done_criteria: dict[str, Any] | None,
    run_result: Any,
    output_text: str,
) -> VerificationOutcome | None:
    """Xác minh sau khi run hoàn tất (cờ WGA_VERIFY_ON_COMPLETE, đọc lúc gọi). Không bao giờ ném."""
    if not (verification_enabled() and done_criteria):
        return None
    try:
        return await verify_task_result(
            plane,
            producer_spec=spec,
            workspace_id=workspace_id,
            project_id=project_id,
            task_id=task_id,
            task_run_id=task_run_id,
            task_title=title,
            decision_reason=decision_reason,
            done_criteria=done_criteria,
            run_result=run_result,
            output_text=output_text,
        )
    except Exception as exc:  # hợp đồng: verify không ném; nếu vẫn ném thì fail-closed
        logger.exception("wga verification crashed task=%s run=%s", task_id, task_run_id)
        return VerificationOutcome(
            Verdict.INCONCLUSIVE, None, f"verification_error:{exc.__class__.__name__}", []
        )
```

(Import `AgentSpec` nếu chưa có trong file; kiểm bằng `grep -n "AgentSpec" apps/cosa/worker/wga_run.py`.)

- [x] **Step 3: Dùng helper ở đường ban đầu.** Trong `_execute_claimed_task`, thay khối `done_criteria = ...; verification = None; if verification_enabled() and done_criteria and not needs_approval: try: ... except ...` (L744-770) bằng:

```python
        verification = await _verify_completed_run(
            plane,
            spec=spec,
            workspace_id=workspace_id,
            project_id=task_project_id,
            task_id=task_id,
            task_run_id=task_run_id,
            title=t.get("title") or "",
            decision_reason=t.get("decisionReason") or "",
            done_criteria=t.get("doneCriteria"),
            run_result=run_result,
            output_text=output_text,
        )
```

Phần phía dưới giữ nguyên (token cấp lại, nhánh FAIL/INCONCLUSIVE, thêm `verification:<id>` vào evidence, `finalize_wga_task_completion` với `evidence_refs=None if needs_approval else evidence`). Cập nhật comment ngay trên cho đúng: task `NEEDS_APPROVAL` cũng được xác minh nhưng PASS không làm nó tự đóng.

- [x] **Step 4: Đường resume.** Viết lại `advance_wga_task_after_resume` (thêm tham số `final_output: Any = None`):

```python
    m = _WGA_TASK_RUN_RE.match(run_id or "")
    if not m or not workspace_id:
        return
    task_id = m.group(1)
    token = mint_company_delegation(
        sub=sub or "0", workspace_id=workspace_id, run_id=run_id,
        capability_ids=[_CAP_TASK_ADVANCE],
    )
    evidence = await record_wga_task_evidence(
        plane, workspace_id=workspace_id, run_id=run_id, output_text=output_text
    )

    verification: VerificationOutcome | None = None
    if verification_enabled():
        ctx = await fetch_task_agent_context(
            plane, workspace_id=workspace_id, task_id=task_id, sub=sub or "0", run_id=run_id
        )
        if ctx is None:
            verification = VerificationOutcome(Verdict.INCONCLUSIVE, None, "context_unavailable", [])
        else:
            spec = _SPEC_BY_PROFILE.get(str(ctx.get("ownerAgentProfile") or ""))
            if ctx.get("doneCriteria") and spec is None:
                verification = VerificationOutcome(
                    Verdict.INCONCLUSIVE, None, "unsupported_owner_agent_profile", []
                )
            elif ctx.get("doneCriteria"):
                verification = await _verify_completed_run(
                    plane,
                    spec=spec,
                    workspace_id=workspace_id,
                    project_id=str(ctx.get("projectId") or ""),
                    task_id=task_id,
                    task_run_id=run_id,
                    title=str(ctx.get("title") or ""),
                    decision_reason=str(ctx.get("decisionReason") or ""),
                    done_criteria=ctx["doneCriteria"],
                    run_result=SimpleNamespace(final_output=final_output),
                    output_text=output_text,
                )
    if verification is not None and verification.verdict is not Verdict.PASS:
        await _advance_task(
            plane, workspace_id=workspace_id, task_id=task_id, to_status="in_progress",
            run_id=run_id, token=token,
            note=f"verification_{verification.verdict.value.lower()}: {verification.summary[:300]}",
        )
        return
    if verification is not None and verification.report_id and evidence:
        evidence = [*evidence, f"verification:{verification.report_id}"]
    await finalize_wga_task_completion(
        plane, workspace_id=workspace_id, task_id=task_id, run_id=run_id, token=token,
        evidence_refs=evidence, summary=output_text.strip()[:500] or None,
        note="hoàn tất sau khi founder duyệt — chờ xác nhận",
    )
```

`from types import SimpleNamespace` nếu chưa có. Lưu ý: `collect_run_facts` đọc `run_result.final_output` (mọi thuộc tính khác dùng `getattr` mặc định) nên `SimpleNamespace(final_output=...)` đủ; khẳng định lại bằng test `test_structured_final_output_reaches_the_verifier`.

- [x] **Step 5: Truyền `final_output` từ handler.** Trong `apps/cosa/worker/handlers.py` L1637-1643 thêm `final_output=res.final_output,` vào lời gọi `advance_wga_task_after_resume` (biến `res` đã có ở phạm vi này; xác nhận bằng đọc quanh L1600-1645).

- [x] **Step 6: Chạy test + gate**

Run: `PYTHONPATH=.:packages:apps python -m pytest tests/apps/cosa/wga tests/agent/verification -q -p no:cacheprovider`; `make lint typecheck-py`.
Expected: PASS (kể cả các test đợt 1 `test_wga_verify*.py`).

- [x] **Step 7: Commit**

```bash
git add apps/cosa/worker/wga_run.py apps/cosa/worker/handlers.py tests/apps/cosa/wga
git commit -m "feat(verifier): xác minh ở đường resume sau duyệt và task NEEDS_APPROVAL"
```

---

### Task 3: Đánh giá `metric_gte`

**Files:**
- Modify: `packages/agent/verification/models.py` (`RunFacts`), `packages/agent/verification/deterministic.py` (`_metric_gte`), `apps/cosa/worker/wga_verify.py` (`collect_run_facts`, `_verify_task_result`, `verify_task_result`, hàm mới `fetch_kr_values`), `apps/cosa/worker/wga_run.py` (chụp giá trị trước khi chạy)
- Test: `tests/agent/verification/test_deterministic.py` (sửa ca cũ + thêm), `tests/apps/cosa/wga/test_wga_verify_metrics.py`

**Interfaces:**
- Produces:
  - `RunFacts` thêm hai trường có mặc định: `metrics: Mapping[str, float | None] = field(default_factory=dict)`, `metrics_before: Mapping[str, float | None] = field(default_factory=dict)` (khóa là `key_result_id` dạng chuỗi).
  - Predicate `metric_gte` với `args = {"key_result_id": str, "threshold": number, "must_change"?: bool}`.
  - `async def fetch_kr_values(plane, *, workspace_id: str, sub: str, run_id: str, key_result_ids: Collection[str]) -> dict[str, float | None]` — id không có trong phản hồi hoặc phản hồi lỗi ⇒ giá trị `None`; không ném.
  - `verify_task_result(..., metrics_before: Mapping[str, float | None] | None = None)`.
  - `def metric_criteria_ids(done_criteria: dict[str, Any]) -> list[str]` — các `key_result_id` của tiêu chí `metric_gte` hợp lệ (dùng chung cho chụp trước và đọc sau).

Ngữ nghĩa (`evaluate_deterministic`):
- `args` sai kiểu (`key_result_id` không phải chuỗi không rỗng, `threshold` không phải số hữu hạn, `must_change` có mặt mà không phải bool) ⇒ `UNCLEAR invalid_args`.
- `facts.metrics.get(id)` là `None`/vắng ⇒ `UNCLEAR metric_unavailable`.
- `must_change` và (`metrics_before.get(id)` là `None`/vắng) ⇒ `UNCLEAR baseline_unavailable`; bằng nhau ⇒ `FAIL metric_unchanged`.
- `value >= threshold` ⇒ `PASS metric_met`, ngược lại `FAIL metric_below_threshold`.

- [x] **Step 1: Cập nhật test thuần**. Trong `test_deterministic.py` thay `test_metric_gte_is_not_evaluable_in_v1` bằng:

```python
def _mf(metrics, before=None):
    return RunFacts(output_text="x", structured_output=None, artifacts=(),
                    metrics=metrics, metrics_before=before or {})


def _metric(args, **kw):
    return _crit("metric_gte", args, **kw)


def test_metric_gte_passes_when_value_meets_threshold():
    r = evaluate_deterministic(_metric({"key_result_id": "7", "threshold": 3}), _mf({"7": 3.0}))
    assert r.verdict is CriterionVerdict.PASS


def test_metric_gte_fails_below_threshold():
    r = evaluate_deterministic(_metric({"key_result_id": "7", "threshold": 3}), _mf({"7": 2.9}))
    assert r.verdict is CriterionVerdict.FAIL and "metric_below_threshold" in r.reason


def test_metric_gte_unavailable_value_is_unclear():
    for facts in (_mf({}), _mf({"7": None})):
        r = evaluate_deterministic(_metric({"key_result_id": "7", "threshold": 3}), facts)
        assert r.verdict is CriterionVerdict.UNCLEAR and "metric_unavailable" in r.reason


@pytest.mark.parametrize("args", [
    {"key_result_id": 7, "threshold": 3}, {"key_result_id": "", "threshold": 3},
    {"key_result_id": "7"}, {"key_result_id": "7", "threshold": "3"},
    {"key_result_id": "7", "threshold": float("inf")}, {"key_result_id": "7", "threshold": True},
    {"key_result_id": "7", "threshold": 3, "must_change": "yes"},
])
def test_metric_gte_invalid_args_are_unclear(args):
    r = evaluate_deterministic(_metric(args), _mf({"7": 5.0}))
    assert r.verdict is CriterionVerdict.UNCLEAR and "invalid_args" in r.reason


def test_must_change_requires_baseline_and_a_difference():
    args = {"key_result_id": "7", "threshold": 3, "must_change": True}
    assert evaluate_deterministic(_metric(args), _mf({"7": 5.0})).reason.endswith("baseline_unavailable")
    unchanged = evaluate_deterministic(_metric(args), _mf({"7": 5.0}, {"7": 5.0}))
    assert unchanged.verdict is CriterionVerdict.FAIL and "metric_unchanged" in unchanged.reason
    changed = evaluate_deterministic(_metric(args), _mf({"7": 5.0}, {"7": 1.0}))
    assert changed.verdict is CriterionVerdict.PASS
```

Run → FAIL (RunFacts chưa có trường).

- [x] **Step 2: Cài đặt thuần.** `models.py`: thêm `from collections.abc import Mapping` và `from dataclasses import dataclass, field`; thêm hai trường vào `RunFacts` **sau** `artifacts` (có mặc định nên không phá chỗ dựng cũ). `deterministic.py`:

```python
import math


def _metric_gte(criterion: dict[str, Any], args: dict[str, Any], facts: RunFacts) -> CriterionResult:
    kr_id = args.get("key_result_id")
    threshold = args.get("threshold")
    must_change = args.get("must_change", False)
    valid = (
        isinstance(kr_id, str)
        and bool(kr_id.strip())
        and isinstance(threshold, (int, float))
        and not isinstance(threshold, bool)
        and math.isfinite(threshold)
        and isinstance(must_change, bool)
    )
    if not valid:
        return _result(criterion, CriterionVerdict.UNCLEAR, "invalid_args")
    value = facts.metrics.get(kr_id)
    if value is None:
        return _result(criterion, CriterionVerdict.UNCLEAR, "metric_unavailable")
    if must_change:
        before = facts.metrics_before.get(kr_id)
        if before is None:
            return _result(criterion, CriterionVerdict.UNCLEAR, "baseline_unavailable")
        if value == before:
            return _result(criterion, CriterionVerdict.FAIL, "metric_unchanged")
    if value >= threshold:
        return _result(criterion, CriterionVerdict.PASS, "metric_met")
    return _result(criterion, CriterionVerdict.FAIL, "metric_below_threshold")
```

Trong `evaluate_deterministic`, thay nhánh `metric_gte` bằng `return _metric_gte(criterion, args, facts)`. Chạy lại test Step 1 → PASS.

- [x] **Step 3: Test I/O thất bại** (`test_wga_verify_metrics.py`) — stub `plane.company_client.get`:

```python
async def test_fetch_kr_values_maps_ids_and_marks_missing_as_none():
    client = SimpleNamespace(get=AsyncMock(return_value={"data": [
        {"id": "7", "currentValue": 4.5}, {"id": "8", "currentValue": None}]}))
    plane = SimpleNamespace(company_client=client)
    out = await wga_verify.fetch_kr_values(
        plane, workspace_id="ws1", sub="7", run_id="wga_task_1_ab",
        key_result_ids={"7", "8", "9"},
    )
    assert out == {"7": 4.5, "8": None, "9": None}
    call = client.get.await_args
    assert call.args[0] == "/operations/key-results"
    assert call.kwargs["headers"]["X-Workspace-Id"] == "ws1"


async def test_fetch_kr_values_never_raises_on_company_error():
    client = SimpleNamespace(get=AsyncMock(side_effect=CompanyServiceError("boom")))
    out = await wga_verify.fetch_kr_values(
        SimpleNamespace(company_client=client), workspace_id="ws1", sub="7",
        run_id="r", key_result_ids={"7"})
    assert out == {"7": None}


def test_metric_criteria_ids_ignores_other_kinds_and_bad_args():
    dc = {"version": 1, "criteria": [
        {"id": "a", "description": "d", "check": "deterministic",
         "predicate": {"kind": "metric_gte", "args": {"key_result_id": "7", "threshold": 1}}},
        {"id": "b", "description": "d", "check": "deterministic",
         "predicate": {"kind": "artifact_exists", "args": {}}},
        {"id": "c", "description": "d", "check": "deterministic",
         "predicate": {"kind": "metric_gte", "args": {"key_result_id": 9, "threshold": 1}}},
    ]}
    assert wga_verify.metric_criteria_ids(dc) == ["7"]


async def test_verify_task_result_reads_metrics_only_when_a_metric_criterion_exists(...):
    # patch fetch_kr_values: không có tiêu chí metric_gte ⇒ không được gọi;
    # có tiêu chí ⇒ gọi 1 lần với đúng tập id, và verdict PASS khi currentValue >= threshold.
    ...
```

Viết đầy đủ thân test cuối theo mẫu `tests/apps/cosa/wga/test_wga_verify.py` (đợt 1) — dùng cùng helper dựng `plane` và `run_result`. Hình dạng phản hồi `listKeyResults` là `MvpSuccess` (`{"data": [...]}` hay `{"items": [...]}`): **mở `shared/contracts/mvp-response.schema.json` và một lời gọi mẫu của `company_client` đọc `MvpSuccess`** (`grep -rn "\"data\"" apps/cosa/worker/*.py | head`) rồi sửa test + parser cho đúng; không đoán.

Run → FAIL.

- [x] **Step 4: Cài đặt I/O** trong `wga_verify.py`:

```python
_CAP_KR_READ = "okr.objective.list"


def metric_criteria_ids(done_criteria: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for c in (done_criteria or {}).get("criteria") or []:
        pred = c.get("predicate") if isinstance(c, dict) else None
        if not isinstance(pred, dict) or pred.get("kind") != "metric_gte":
            continue
        kr_id = (pred.get("args") or {}).get("key_result_id")
        if isinstance(kr_id, str) and kr_id.strip() and kr_id not in ids:
            ids.append(kr_id)
    return ids


async def fetch_kr_values(
    plane: Any, *, workspace_id: str, sub: str, run_id: str, key_result_ids: Collection[str]
) -> dict[str, float | None]:
    """Giá trị hiện tại của các KR cần chấm. Không ném: lỗi hoặc thiếu ⇒ None (INCONCLUSIVE ở người gọi)."""
    result: dict[str, float | None] = {k: None for k in key_result_ids}
    if not result:
        return result
    token = mint_company_delegation(
        sub=sub, workspace_id=workspace_id, run_id=run_id, capability_ids=[_CAP_KR_READ]
    )
    try:
        resp = await plane.company_client.get(
            "/operations/key-results",
            headers={"X-Workspace-Id": workspace_id, "Authorization": f"Bearer {token}"},
        )
    except Exception as exc:  # CompanyServiceError, lỗi mạng
        logger.warning("verify: KR read failed ws=%s: %s", workspace_id, exc.__class__.__name__)
        return result
    rows = resp.get("data") if isinstance(resp, dict) else None  # chỉnh theo MvpSuccess thật
    for row in rows if isinstance(rows, list) else []:
        rid = str(row.get("id")) if isinstance(row, dict) else ""
        value = row.get("currentValue") if isinstance(row, dict) else None
        if rid in result and isinstance(value, (int, float)) and not isinstance(value, bool):
            result[rid] = float(value)
    return result
```

Nối vào `_verify_task_result`: sau `parse_done_criteria`, `kr_ids = metric_criteria_ids(parsed)`; nếu có thì `metrics = await fetch_kr_values(...)` rồi truyền `metrics`/`metrics_before` vào `collect_run_facts` (thêm hai tham số tùy chọn, mặc định rỗng → `RunFacts(..., metrics=metrics, metrics_before=dict(metrics_before or {}))`). `verify_task_result` và `_verify_task_result` nhận `metrics_before: Mapping[str, float | None] | None = None` và chuyển tiếp. `sub` lấy từ `principal` nếu đã có trong tham số; nếu chưa, thêm tham số `sub: str = "0"` (mặc định không phá chỗ gọi cũ) và truyền từ `_verify_completed_run`.

Kiểm quyền: `grep -rn "okr.objective.list" services/company/shared/auth services/company/operations` để xác nhận token ủy quyền của cosa với capability này được `requireWorkspaceAccess(..., { agentCapabilities: [AGENT_CAP.OKR_OBJECTIVE_LIST] })` chấp nhận. Nếu cơ chế delegation yêu cầu allowlist capability theo run (xem `shared/auth/cosa-task-delegation.ts` và `mint_company_delegation`), thêm `okr.objective.list` vào allowlist đó và một test Company xác nhận.

- [x] **Step 5: Chụp giá trị trước khi chạy** (`wga_run.py::_execute_claimed_task`, ngay trước `prepare_run`):

```python
    metrics_before: dict[str, float | None] = {}
    if verification_enabled() and t.get("doneCriteria"):
        must_change_ids = [
            i for i in metric_criteria_ids(t["doneCriteria"])
            if _wants_change(t["doneCriteria"], i)
        ]
        if must_change_ids:
            metrics_before = await fetch_kr_values(
                plane, workspace_id=workspace_id, sub=sub, run_id=task_run_id,
                key_result_ids=must_change_ids,
            )
```

với `_wants_change(done_criteria, kr_id)` = có tiêu chí `metric_gte` cùng `key_result_id` có `must_change is True`. Truyền `metrics_before` vào `_verify_completed_run` → `verify_task_result`. Đường resume **không** có giá trị trước (run đã chạy xong từ trước) ⇒ tiêu chí `must_change` ở đường resume ra `UNCLEAR baseline_unavailable` (INCONCLUSIVE, an toàn); ghi điều này vào runbook.

- [x] **Step 6: Chạy test + gate**

Run: `PYTHONPATH=.:packages:apps python -m pytest tests/agent/verification tests/apps/cosa/wga -q -p no:cacheprovider`; `make lint typecheck-py`; `cd services/company && encore test` file test capability nếu đã thêm.
Expected: PASS.

- [x] **Step 7: Commit**

```bash
git add packages/agent/verification apps/cosa/worker/wga_verify.py apps/cosa/worker/wga_run.py tests/agent/verification tests/apps/cosa/wga
git commit -m "feat(verifier): đánh giá tiêu chí metric_gte từ giá trị KR hiện tại (must_change tùy chọn)"
```

---

### Task 4: Ép mô hình thẩm phán khác producer qua model-policy REST

**Files:**
- Modify: `apps/cosa/api/model_policy_routes.py` (`_resolve_agent_spec_id` L380-415), `apps/cosa/agents/catalog.py` hoặc module nhẹ mới `apps/cosa/agents/internal_policy_specs.py`
- Test: `tests/apps/cosa/api/test_model_policy_verifier_scope.py`

**Interfaces:**
- Produces: `INTERNAL_MODEL_POLICY_SPECS: dict[str, AgentSpec] = {"verifier": COSA_VERIFIER_AGENT_SPEC}` (module nhẹ, không import chain nặng, theo ghi chú của `agent_profile_specs.py`); `_resolve_agent_spec_id("verifier") == "cosa.agents.verifier"`.

- [x] **Step 1: Test thất bại** — theo mẫu test model-policy sẵn có (`grep -rln "model-policy\|model_policy" tests/apps/cosa | head`; dùng cùng fixture app/identity):

```python
def test_resolve_agent_spec_id_accepts_verifier():
    from apps.cosa.api.model_policy_routes import _resolve_agent_spec_id
    assert _resolve_agent_spec_id("verifier") == "cosa.agents.verifier"


def test_unknown_profile_still_404():
    ...  # HTTPException 404 như hiện tại


def test_verifier_is_still_not_a_public_profile():
    from apps.cosa.agents.agent_profile_specs import AGENT_PROFILE_SPECS
    assert "verifier" not in AGENT_PROFILE_SPECS


async def test_put_then_get_policy_for_verifier_roundtrips(...):
    # PUT policy scope AGENT_PROFILE cho "verifier" → GET trả scope_key == "cosa.agents.verifier"
    # (đúng key mà bind_route_to_run tra cứu bằng spec.id của thẩm phán)
    ...
```

Viết đầy đủ ca round-trip theo mẫu PUT/GET policy hiện có. Run → FAIL.

- [x] **Step 2: Cài đặt.** Module `apps/cosa/agents/internal_policy_specs.py`:

```python
"""Spec nội bộ cho phép cấu hình model-policy nhưng KHÔNG phải profile công khai.

Không thêm vào AGENT_PROFILE_SPECS/OWNER_AGENT_PROFILES (xem quyết định Dự án B)."""

from agent.specs import AgentSpec  # đường import đúng như specs.py

from apps.cosa.agents.specs import COSA_VERIFIER_AGENT_SPEC

INTERNAL_MODEL_POLICY_SPECS: dict[str, AgentSpec] = {"verifier": COSA_VERIFIER_AGENT_SPEC}
```

(Sao chép dòng import `AgentSpec` từ `apps/cosa/agents/specs.py`.) Trong `_resolve_agent_spec_id`: `spec = AGENT_PROFILE_SPECS.get(agent_profile) or INTERNAL_MODEL_POLICY_SPECS.get(agent_profile)`; thông điệp 404 giữ nguyên. Chạy `rg -n "_resolve_agent_spec_id|AGENT_PROFILE_SPECS" apps/cosa/api` để đảm bảo mọi route model-policy khác (`GET .../effective`, `DELETE`) đi qua cùng hàm.

- [x] **Step 3: Chạy test + gate** — `pytest tests/apps/cosa -k "model_policy or verifier" -q`; `make lint typecheck-py boundary-check`; `pytest tests/contracts/test_company_agent_spec_pins.py -q`. Expected: PASS.
- [x] **Step 4: Commit**

```bash
git add apps/cosa/agents/internal_policy_specs.py apps/cosa/api/model_policy_routes.py tests/apps/cosa/api/test_model_policy_verifier_scope.py
git commit -m "feat(verifier): model-policy REST nhận scope nội bộ verifier để ép mô hình thẩm phán độc lập"
```

---

### Task 5: Hiển thị verdict trên Flutter (kèm API theo lô)

**Files:**
- Modify: `packages/agent/verification/repository.py` (Protocol + InMemory + Postgres), `apps/cosa/api/workforce_routes.py` (`list_verification_reports` L953), `shared/contracts/mvp-surface.json`, file sinh `frontend/lib/core/network/mvp_endpoints.g.dart` (bằng generator), `frontend/lib/modules/workforce/services/...` (WorkforceMvpService; đường dẫn thật: `grep -rn "class WorkforceMvpService" frontend/lib`), `frontend/lib/modules/tasks/controllers/tasks_controller.dart`, `frontend/lib/modules/tasks/views/widgets/kanban_task_card.dart`
- Create: `frontend/lib/data/models/verification_report_model.dart`, `frontend/lib/modules/tasks/views/widgets/verification_badge.dart`
- Test: `tests/agent/verification/test_repository.py` (thêm), `tests/apps/cosa/test_workforce_routes.py` (thêm), `frontend/test/modules/workforce/workforce_mvp_service_test.dart` (thêm), `frontend/test/modules/tasks/verification_badge_test.dart`

**Interfaces:**
- Produces:
  - Repo: `async list_latest_for_tasks(workspace_id: str, task_ids: Sequence[str]) -> list[VerificationReport]` — báo cáo mới nhất của mỗi task (tối đa 50 id; id rỗng/trùng bị bỏ).
  - API: `GET /agent/workforce/verification-reports?taskIds=1,2,3` (mới nhất mỗi task). `taskId` / `runId` giữ nguyên; truyền `taskIds` cùng `taskId`/`runId` ⇒ 422.
  - Contract id `workforce.verification_reports.list` (schema `workforce.verification_reports.list.v1`).
  - Dart: `VerificationReportModel {reportId, taskId, runId, verdict (pass|fail|inconclusive), mode, criteria: List<VerificationCriterion {id, required, check, verdict, reason}>, createdAt}`; `WorkforceMvpService.listVerificationReports(List<String> taskIds)`; `TasksController.verificationByTask` (`RxMap<String, VerificationReportModel>`); widget `VerificationBadge(report)`.

- [x] **Step 1: Test repo thất bại** (thêm vào `tests/agent/verification/test_repository.py`):

```python
async def test_list_latest_for_tasks_returns_one_newest_per_task_and_is_scoped():
    repo = InMemoryVerificationReportRepository()
    await repo.create_if_absent(_report(report_id="old", task_id="t1", run_id="r1", created_at=datetime(2026, 1, 1, tzinfo=UTC)))
    await repo.create_if_absent(_report(report_id="new", task_id="t1", run_id="r2", created_at=datetime(2026, 1, 2, tzinfo=UTC)))
    await repo.create_if_absent(_report(report_id="other", task_id="t2", run_id="r3"))
    await repo.create_if_absent(_report(report_id="foreign", task_id="t1", run_id="r4", workspace_id="ws2"))
    got = await repo.list_latest_for_tasks("ws1", ["t1", "t2", "t3", "t1", ""])
    assert sorted(r.report_id for r in got) == ["new", "other"]
```

Thêm ca Postgres tương đương (tự skip khi thiếu DB). Run → FAIL.

- [x] **Step 2: Cài đặt repo.** InMemory: gom theo `task_id` trong `workspace_id`, lấy `max(created_at)`. Postgres:

```python
_LATEST_FOR_TASKS = text(
    """
    SELECT DISTINCT ON (task_id)
           report_id, workspace_id, project_id, task_id, run_id, verifier_run_id, verdict, mode,
           criteria_results, criteria_hash, output_hash, created_at
    FROM agent.verification_reports
    WHERE workspace_id = :workspace_id AND task_id = ANY(:task_ids)
    ORDER BY task_id, created_at DESC
    """
)
```

`task_ids` truyền `list[str]` đã khử trùng/loại rỗng, tối đa 50; tái dùng hàm `_row_to_report` sẵn có.

- [x] **Step 3: Route.** Thêm tham số `task_ids: str | None = Query(None, alias="taskIds", max_length=2000)`; nếu có thì: 422 khi kèm `taskId`/`runId`; tách bằng dấu phẩy, `strip`, loại rỗng/trùng, quá 50 phần tử ⇒ 422; gọi `repo.list_latest_for_tasks(identity.workspace_id, ids)`. Test route (`tests/apps/cosa/test_workforce_routes.py`): hai task có báo cáo ⇒ trả đúng hai báo cáo mới nhất; workspace khác không lọt; 51 id ⇒ 422; `taskIds` + `taskId` ⇒ 422; repo `None` ⇒ danh sách rỗng (hành vi hiện có).

- [x] **Step 4: Hợp đồng.** Thêm entry `workforce.verification_reports.list` vào `shared/contracts/mvp-surface.json` bằng cách **sao chép entry `workforce.run.read` làm mẫu** (đọc cách các trường `schema`, `backend_test`, `flutter_test`, `integration_test` được kiểm: `make mvp-surface-check`), đặt `method: "GET"`, `path: "/agent/workforce/verification-reports"`, `frontend_symbol: "WorkforceMvpService.listVerificationReports"`, `backend_test: "tests/apps/cosa/test_workforce_routes.py"`, `flutter_test: "frontend/test/modules/workforce/workforce_mvp_service_test.dart"`. Chạy `make mvp-contracts-gen` rồi `make mvp-contracts-check mvp-surface-check route-inventory-check frontend-api-contract-check route-auth-allowlist-check`. Không sửa tay file sinh ra. Nếu kiểm tra yêu cầu `integration_test`, thêm ca vào `tests/integration/test_mvp_workforce_in_process.py` theo mẫu các ca lân cận.

- [x] **Step 5: Flutter — model + service + test.** `verification_report_model.dart` (parse an toàn: trường thiếu ⇒ giá trị mặc định, `verdict` chuẩn hóa chữ thường, không ném):

```dart
enum VerificationVerdict { pass, fail, inconclusive }

class VerificationCriterion {
  final String id;
  final bool required;
  final String check;
  final String verdict; // pass | fail | unclear
  final String reason;
  const VerificationCriterion({required this.id, required this.required, required this.check, required this.verdict, required this.reason});

  factory VerificationCriterion.fromJson(Map<String, dynamic> j) => VerificationCriterion(
        id: (j['id'] ?? '').toString(),
        required: j['required'] != false,
        check: (j['check'] ?? '').toString(),
        verdict: (j['verdict'] ?? 'unclear').toString(),
        reason: (j['reason'] ?? '').toString(),
      );
}

class VerificationReportModel {
  final String reportId;
  final String taskId;
  final String runId;
  final VerificationVerdict verdict;
  final String mode;
  final List<VerificationCriterion> criteria;
  final DateTime? createdAt;
  const VerificationReportModel({required this.reportId, required this.taskId, required this.runId, required this.verdict, required this.mode, required this.criteria, this.createdAt});

  factory VerificationReportModel.fromJson(Map<String, dynamic> j) {
    final raw = (j['verdict'] ?? '').toString().toLowerCase();
    return VerificationReportModel(
      reportId: (j['report_id'] ?? j['reportId'] ?? '').toString(),
      taskId: (j['task_id'] ?? j['taskId'] ?? '').toString(),
      runId: (j['run_id'] ?? j['runId'] ?? '').toString(),
      verdict: raw == 'pass'
          ? VerificationVerdict.pass
          : raw == 'fail'
              ? VerificationVerdict.fail
              : VerificationVerdict.inconclusive,
      mode: (j['mode'] ?? '').toString(),
      criteria: ((j['criteria_results'] ?? j['criteriaResults']) as List<dynamic>? ?? const [])
          .whereType<Map<String, dynamic>>()
          .map(VerificationCriterion.fromJson)
          .toList(),
      createdAt: DateTime.tryParse((j['created_at'] ?? j['createdAt'] ?? '').toString()),
    );
  }
}
```

Khóa JSON thật do `_verification_report_view` (`workforce_routes.py`) quyết định: **mở hàm đó và khớp đúng tên khóa** (snake_case hay camelCase), rồi sửa `fromJson` + test cho khớp, không để cả hai kiểu nếu backend chỉ có một. Service: `Future<Map<String, VerificationReportModel>> listVerificationReports(List<String> taskIds)` — gọi endpoint qua `MvpEndpoints` sinh ra (xem `workforceApprovalDecide` ở `mvp_endpoints.g.dart` làm mẫu cách gọi), trả map `taskId → báo cáo`; `taskIds` rỗng ⇒ map rỗng, không gọi mạng. Test trong `workforce_mvp_service_test.dart` theo mẫu các ca có sẵn (mock HTTP): phân tích đúng verdict/criteria, rỗng không gọi mạng, 403 ném `StateError`.

- [x] **Step 6: Flutter — controller + huy hiệu.** `TasksController`: sau khi nạp danh sách task, lấy các `id` của task có `status` `in_progress` hoặc `done` (tối đa 50), gọi một lần `listVerificationReports`, gán `verificationByTask`; lỗi ⇒ giữ map cũ, **không** làm hỏng bảng (bắt lỗi, log). `VerificationBadge(report)`: chip nhỏ cùng phong cách các badge sẵn có trong `kanban_task_card.dart` (nền `color.withValues(alpha: 0.15)`, chữ cỡ 9.5): PASS xanh `#10B981` "Đã kiểm", FAIL đỏ `#EF4444` "Không đạt", INCONCLUSIVE vàng `#F59E0B` "Chưa kết luận"; `onTap` mở `showModalBottomSheet` liệt kê tiêu chí (id, bắt buộc/tùy chọn, kết quả, mã lý do) — chỉ hiển thị **mã**, không diễn giải tự do. Chuỗi hiển thị theo cơ chế `L10nKey` của module (thêm khóa mới vào `app_translations`, theo cách `L10nKey.hubWaitingTitle` được định nghĩa: `grep -rn "hubWaitingTitle" frontend/lib | head`). Chèn badge vào `KanbanTaskCard` khi `controller.verificationByTask[task.id]` có giá trị.

- [x] **Step 7: Test widget** (`verification_badge_test.dart`): ba verdict hiển thị đúng nhãn/màu; chạm mở sheet liệt kê đúng số tiêu chí; báo cáo rỗng criteria vẫn hiển thị an toàn.

- [x] **Step 8: Chạy test + gate**

Run: `PYTHONPATH=.:packages:apps python -m pytest tests/agent/verification tests/apps/cosa/test_workforce_routes.py -q -p no:cacheprovider`; `cd frontend && flutter test test/modules/workforce test/modules/tasks && flutter analyze`; `make frontend-test frontend-analyze frontend-boundary-check` (nếu có). Expected: PASS.

- [x] **Step 9: Commit** (liệt kê đường dẫn thật đã đổi; không `git add -A` vì `frontend/*` có thể còn thay đổi của người dùng):

```bash
git add packages/agent/verification/repository.py apps/cosa/api/workforce_routes.py shared/contracts/mvp-surface.json frontend/lib/core/network/mvp_endpoints.g.dart frontend/lib/data/models/verification_report_model.dart frontend/lib/modules/tasks frontend/lib/modules/workforce tests/agent/verification tests/apps/cosa frontend/test
git commit -m "feat(verifier): hiển thị verdict trên thẻ kanban (API theo lô taskIds, huy hiệu và chi tiết tiêu chí)"
```

---

### Task 6: Cổng bật mặc định, runbook và trạng thái

**Files:**
- Modify: `docs/runbooks/wga-verifier.md`, `docs/superpowers/plans/2026-10-05-agent-structure-B-verifier-gate.md` (mục "Còn lại"), `docs/superpowers/plans/2026-10-05-agent-structure-A-goal-ancestry-done-criteria.md` (một dòng trạng thái nếu thiếu)
- Test: `tests/apps/cosa/wga/test_wga_verify_flag_default.py` (chỉ thêm ở Step 4 sau khi con người duyệt)

- [x] **Step 1: Cập nhật runbook** `docs/runbooks/wga-verifier.md`: bỏ câu "không kiểm" về resume/`NEEDS_APPROVAL` (nay có kiểm, kèm hai ghi chú: PASS ở task `NEEDS_APPROVAL` không tự đóng; `must_change` ở đường resume luôn `INCONCLUSIVE baseline_unavailable`); thay dòng `metric_gte` bằng ngữ nghĩa mới (`key_result_id`, `threshold`, `must_change`, đọc `currentValue`, rủi ro đạt rỗng, KR kiểu giảm cần ngưỡng riêng); thêm mục "Ép mô hình thẩm phán độc lập" với lệnh PUT/GET model-policy scope `verifier` (mẫu request lấy từ test Task 4); thêm mục "Hiển thị" cho huy hiệu Flutter và `taskIds`.
- [x] **Step 2: Thêm mục "Quan sát trước khi bật mặc định"** vào runbook với các truy vấn đọc-chỉ (chạy trên DB agent, thay `<ws>`):

```sql
-- Phân bố verdict theo ngày (cửa sổ quan sát)
SELECT date_trunc('day', created_at) AS day, verdict, count(*)
FROM agent.verification_reports
WHERE workspace_id = '<ws>' AND created_at >= now() - interval '14 days'
GROUP BY 1, 2 ORDER BY 1, 2;

-- Tỷ lệ INCONCLUSIVE theo nguyên nhân (mã lý do trong từng tiêu chí)
SELECT c->>'reason' AS reason, c->>'verdict' AS verdict, count(*)
FROM agent.verification_reports r, jsonb_array_elements(r.criteria_results) c
WHERE r.workspace_id = '<ws>' AND r.verdict = 'INCONCLUSIVE'
  AND r.created_at >= now() - interval '14 days'
GROUP BY 1, 2 ORDER BY 3 DESC;

-- Mẫu để duyệt tay: 20 báo cáo PASS gần nhất kèm task
SELECT report_id, task_id, run_id, mode, created_at
FROM agent.verification_reports
WHERE workspace_id = '<ws>' AND verdict = 'PASS'
ORDER BY created_at DESC LIMIT 20;
```

  Tiêu chí quyết định (ghi vào runbook, **người duyệt có thể chỉnh**): (a) quan sát tối thiểu 14 ngày trên workspace dev/staging với `WGA_VERIFY_ON_COMPLETE=1` và `WGA_REQUIRE_DONE_CRITERIA=1`; (b) ít nhất 30 báo cáo; (c) tỷ lệ INCONCLUSIVE ≤ 20% và nguyên nhân chủ yếu không phải lỗi hạ tầng (`judge_timeout`, `context_unavailable`, `usage_budget_exceeded`); (d) duyệt tay 20 báo cáo PASS: 0 trường hợp đạt sai (nội dung rõ ràng không thỏa tiêu chí); (e) thẩm phán đã có policy mô hình riêng (Task 4) hoặc chấp nhận có chủ đích dùng chung route mặc định.
- [x] **Step 3: Cập nhật mục "Còn lại" của thiết kế B**: đánh dấu đã làm (resume + `NEEDS_APPROVAL`, `metric_gte`, model-policy REST, UI Flutter); còn lại: cổng duyệt cho workflow, `BudgetGate`, đưa verdict vào hash duyệt/scorecard, bật mặc định (chờ Step 4).
- [x] **Step 4: CỔNG CỦA NGƯỜI — đổi mặc định cờ.** *(Đóng theo quyết định của chủ dự án 2026-10-12: **giữ mặc định TẮT**, không đổi code; hoãn tới khi có số liệu quan sát theo tiêu chí ở Step 2. Ghi trong `docs/runbooks/wga-verifier.md`. Phần mô tả bên dưới giữ nguyên làm hướng dẫn cho lần đổi sau.)* Chỉ làm khi chủ dự án xác nhận đã đạt tiêu chí ở Step 2 (ghi kết quả vào runbook: ngày, số báo cáo, tỷ lệ INCONCLUSIVE, người duyệt). Khi đó: đổi `verification_enabled()` thành bật mặc định, tắt khi `WGA_VERIFY_ON_COMPLETE == "0"`; test thất bại trước:

```python
def test_verification_is_on_by_default_after_rollout(monkeypatch):
    monkeypatch.delenv("WGA_VERIFY_ON_COMPLETE", raising=False)
    assert verification_enabled() is True

def test_explicit_zero_turns_it_off(monkeypatch):
    monkeypatch.setenv("WGA_VERIFY_ON_COMPLETE", "0")
    assert verification_enabled() is False
```

  và cập nhật các test đợt 1/Task 2 đang giả định "mặc định tắt" (chúng đặt/gỡ biến môi trường tường minh nên chủ yếu cần `monkeypatch.setenv("WGA_VERIFY_ON_COMPLETE", "0")` ở ca "cờ tắt"). Không đổi mặc định `WGA_REQUIRE_DONE_CRITERIA` trong phiên này; đó là quyết định riêng.
- [x] **Step 5: Cổng chất lượng**

```bash
make lint typecheck-py migration-check schema-fingerprint-check boundary-check
make agent-test apps-cosa-test
make services-test-company
make mvp-contracts-check route-inventory-check frontend-api-contract-check route-auth-allowlist-check
make frontend-test frontend-analyze
make verify
```

Expected: thoát 0 (trừ các lỗi có sẵn nêu ở Global Constraints). Kiểm tay: (1) tạo task `NEEDS_APPROVAL` có `doneCriteria`, duyệt checkpoint, xác nhận report xuất hiện và task đóng/giữ đúng verdict; (2) KR đạt ngưỡng ⇒ `metric_gte` PASS, KR dưới ngưỡng ⇒ FAIL; (3) PUT policy `verifier` đổi mô hình, `GET` trả `scope_key = cosa.agents.verifier`; (4) bảng kanban hiện huy hiệu đúng màu và chạm mở được chi tiết.
- [x] **Step 6: Commit**

```bash
git add docs/runbooks/wga-verifier.md docs/superpowers/plans/2026-10-05-agent-structure-B-verifier-gate.md
git commit -m "docs(verifier): runbook đợt 2, tiêu chí quan sát trước khi bật mặc định"
```

---

## Self-Review

- **Spec coverage (mục "Còn lại" của thiết kế B):** verify resume + `NEEDS_APPROVAL` → Tasks 1-2; `metric_gte` → Task 3; UI Flutter + hợp đồng → Task 5; ép mô hình thẩm phán qua REST → Task 4; bật cờ mặc định → Task 6 (cổng người); cổng duyệt workflow và `BudgetGate` → **ngoài phạm vi, nêu rõ**; verdict vào hash duyệt/scorecard → ngoài phạm vi.
- **Placeholder scan:** các chỗ cố ý trỏ tới mẫu có sẵn thay vì tự suy: hình dạng `MvpSuccess` của `listKeyResults` (Task 3 Step 3-4), khóa JSON của `_verification_report_view` (Task 5 Step 5), cấu trúc entry `mvp-surface.json` (Task 5 Step 4), tên fixture model-policy (Task 4 Step 1). Mỗi chỗ có lệnh kiểm cụ thể. Hai thân test được ghi "viết đầy đủ theo mẫu X" (Task 1 ca task tạo tay, Task 3 ca `verify_task_result`, Task 4 ca round-trip) phải viết đủ khi triển khai.
- **Nhất quán kiểu:** `VerificationOutcome`, `Verdict`, `RunFacts.metrics/metrics_before`, `fetch_kr_values`, `metric_criteria_ids`, `fetch_task_agent_context`, `_verify_completed_run`, `list_latest_for_tasks`, `INTERNAL_MODEL_POLICY_SPECS` dùng cùng tên ở mọi task. Giá trị mặc định mới của `RunFacts` giữ tương thích mọi chỗ dựng cũ.
- **Rủi ro cần theo dõi khi thực thi:** (1) cơ chế delegation có thể cần allowlist cho `okr.objective.list` (Task 3 Step 4); (2) thay đổi chữ ký `verify_task_result` phải giữ tham số mới có mặc định để không vỡ test đợt 1; (3) `frontend/*` có thể có thay đổi chưa commit của người dùng, kiểm `git status` trước khi sửa.
