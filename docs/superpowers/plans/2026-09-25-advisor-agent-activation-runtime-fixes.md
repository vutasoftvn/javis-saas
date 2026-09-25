# Advisor & Agent — Sửa lỗi kích hoạt và vận hành (Plan)

> **Cho agent thực thi:** làm theo đúng thứ tự Task. Mỗi thay đổi hành vi bắt
> đầu bằng test FAIL tái hiện lỗi, kết thúc bằng lệnh verify ghi ở cuối Task.
> Mỗi Task là 1 commit riêng. Không gộp Task.

**Mục tiêu:** Đưa luồng Executive Advisor (deliberation) và agent chat về trạng
thái nhất quán, fail-closed và không kẹt: một nguồn authority cho Project
deployment, quyết định Founder chỉ xảy ra sau khi có phân tích, không có trạng
thái cụt, retry worker idempotent.

**Phạm vi kiến trúc:** `services/company` (operations), `apps/cosa` (worker,
Company client), `frontend/lib/modules/hologram_hub`. Không đụng
`packages/agent` trừ khi ghi rõ. Không đổi schema DB (không cần migration).

**Nguồn sự thật liên quan:**
- `docs/superpowers/specs/2026-09-13-founder-configurable-agent-skill-workflow-design.md`
  (Workspace asset + Project deployment, V2 là authority chính thức).
- `docs/superpowers/plans/2026-09-20-governed-advisor-overlay-and-truthful-hub.md`
  (pin deployment + overlay, fail-closed).
- `ADR-COSA-DELEGATION-002` (secret một chiều — plan này không thêm secret mới).

---

## 0. Bằng chứng (đã đọc code, 2026-09-25)

| # | Lỗi | Vị trí | Mức |
|---|---|---|---|
| B1 | Retry task `executive_deliberation_framed` chạy lại **mọi** role; role đã ghi analysis nhận descriptor mới (`run_id` ngẫu nhiên) → `EXECUTIVE_CALLBACK_CONFLICT` → task fail lại tới `max_attempts=5` → deliberation kẹt `ANALYZING` vĩnh viễn. | `apps/cosa/worker/main.py::_dispatch_executive_deliberation_task`, `apps/cosa/worker/executive_board_handler.py`, `executive-deliberation.service.ts::recordExecutiveAnalysisCallback` (nhánh `existing`), `packages/agent/executive_board/runner.py` (`descriptor["run_id"]`) | Cao |
| B2 | Founder disable Office giữa lúc phân tích: authority bị từ chối → worker gửi outcome FAILED → callback bị từ chối vì `Role ... has been disabled or revoked` → task retry vô ích → kẹt như B1. | `recordExecutiveAnalysisCallback` (check `roleAct.state`) | Cao |
| B3 | `appendFounderDecision` chỉ chặn `CANCELLED`/`DECIDED` → có thể APPROVE khi đang `DRAFT`/`ANALYSIS_QUEUED`/`ANALYZING` (chưa có phân tích). Test hiện có còn dựa vào hành vi này. | `executive-deliberation.service.ts::appendFounderDecision`; `tests/executive-deliberation.service.test.ts` ("appends founder decision and forbids duplicate decision") | Cao |
| B4 | `CRITIC_REVIEW` là trạng thái cụt: không có critic runner, không có transition ra; UI chỉ hiện nút quyết định khi `AWAITING_FOUNDER` → deliberation `criticRequired=true` không bao giờ quyết định được từ UI. | `recordExecutiveAnalysisCallback`; `frontend/.../executive_advisory_board_view.dart` | Trung bình |
| B5 | Tất cả role FAILED vẫn chuyển sang `AWAITING_FOUNDER` (Founder "phê duyệt" một board không có phân tích nào); `FAILED_REQUIRES_ATTENTION` khai báo nhưng không dùng; không re-frame được sau thất bại. | `recordExecutiveAnalysisCallback`, `frameDeliberation` (chỉ cho `DRAFT`/`FRAMED`) | Trung bình |
| B6 | Hai nguồn authority: chat run dùng legacy `project_agent_assignments` (`getProjectAgentRunAuthority`), advisor dùng V2 `project_agent_deployments`. Pause/retire V2 deployment **không** chặn chat; `FOUNDER_CONFIGURABLE_ASSETS_MODE=ENFORCED` không có tác dụng với chat. | `project-startup-team.handler.ts::getProjectAgentRunAuthorityApi`, `founder-agent-compatibility.service.ts`, `apps/cosa/worker/handlers.py::execute_run_task` | Cao |
| B7 | Bootstrap P0 Core chạy SAU khi transaction tạo Project commit; lỗi bootstrap làm request tạo Project trả lỗi dù Project đã tồn tại → client retry tạo trùng Project. | `project.service.ts::createProjectService` | Thấp |

Đính chính phân tích trước: callback lỗi **có** làm task fail để scheduler
retry (`success=not failed`) — vấn đề thật là retry không idempotent (B1/B2).

---

## 1. Quyết định cần Founder chốt trước khi thực thi

| ID | Câu hỏi | Đề xuất (mặc định nếu không có phản hồi) |
|---|---|---|
| D1 | B6 — trong chế độ `SHADOW` (mặc định hiện nay), V2 deployment `PAUSED`/`RETIRED` có được chặn chat không? | **Có.** Hành động pause tường minh của Founder phải thắng ở mọi mode. Chỉ khi V2 **chưa từng có** deployment (`INACTIVE`) thì SHADOW mới fallback legacy. `ENFORCED` = chỉ V2. |
| D2 | B4 — làm critic runner thật hay tạm khoá `criticRequired`? | **Tạm khoá:** `frame` với `criticRequired=true` → `failedPrecondition("CRITIC_REVIEW_NOT_AVAILABLE")`. Deliberation đã nằm ở `CRITIC_REVIEW` được phép quyết định (không để kẹt). Critic runner là feature riêng (xem §4). |
| D3 | B5 — khi **một phần** role FAILED thì sao? | `AWAITING_FOUNDER` nếu ≥1 COMPLETED (UI hiện rõ role nào lỗi); `FAILED_REQUIRES_ATTENTION` nếu 0 COMPLETED. Từ `FAILED_REQUIRES_ATTENTION` Founder được re-frame hoặc cancel. |
| D4 | CEO/CTO `READY` nhưng không nằm trong `STAGE_ROLE_PRESETS` nào → luôn `STAGE_FORBIDDEN`. Có thêm vào preset không? | **Không sửa trong plan này** (bảng do Founder chốt 2026-09-14). Chỉ ghi nhận; nếu muốn thêm thì là 1 dòng ở `executive-board-stage-presets.ts` + test. |

---

## 2. Tasks

### Task 1 — Retry worker idempotent (B1)

**Thiết kế:** Company là nguồn sự thật "role đã có analysis cho frame này
chưa". Authority endpoint trả thêm field; worker bỏ qua role đã ghi, không gọi
model lần 2 (tiết kiệm chi phí + không xung đột).

Files:
- `services/company/operations/services/executive-deliberation.service.ts` —
  `getDeliberationAuthority` trả thêm
  `existingAnalysis: { status: "COMPLETED" | "FAILED" } | null` (query
  `projectExecutiveDeliberationAnalyses` theo `deliberationId + frameVersion + roleKey`).
  Nếu đã có analysis thì trả về **trước** bước re-check `resolveProjectDeploymentPin`
  (role đã xong không cần deployment còn sống).
- `services/company/operations/handlers/executive-deliberation-internal.handler.ts`
  — cập nhật kiểu response.
- `apps/cosa/worker/executive_board_handler.py::_analyze_role` — nếu
  `authority.get("existingAnalysis")` khác `None` → trả sentinel "skipped",
  vòng lặp ở `execute_executive_deliberation_framed_task` **không** gọi
  `runner.run` và **không** gửi callback; ghi `{"role_key", "outcome": "ALREADY_RECORDED"}`
  (không có key `error` → không làm task fail).

Test trước (FAIL):
1. `services/company/operations/tests/executive-deliberation-callback.test.ts`:
   ghi callback COMPLETED cho role A → `getDeliberationAuthority(A)` trả
   `existingAnalysis.status === "COMPLETED"`; role B chưa có → `null`.
2. `tests/apps/cosa/worker/test_executive_board_handler.py`: fake client trả
   `existingAnalysis` cho role A, `None` cho role B → runner chỉ được gọi cho B,
   callback chỉ gửi cho B, kết quả không có `error`.
3. Cùng file: mô phỏng retry — lần 1 callback của B lỗi mạng (A thành công);
   lần 2 A có `existingAnalysis` → chỉ B chạy lại → cả task `success`.

Verify:
```bash
cd services/company && npm run typecheck && npx vitest run operations/tests/executive-deliberation-callback.test.ts
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/worker/test_executive_board_handler.py -q
make encore-handler-boundary-check ts-suppression-check
```

### Task 2 — Role bị disable giữa chừng không làm kẹt (B2)

**Thiết kế:** Kiểm tra `roleAct.state === "ACTIVE"` trong callback chỉ áp dụng
cho outcome `completed` (không chấp nhận phân tích từ Office đã tắt). Outcome
`failed` vẫn được **ghi** để deliberation hội tụ được — ghi thất bại không cấp
thêm quyền gì.

Files: `executive-deliberation.service.ts::recordExecutiveAnalysisCallback`.

Test trước (FAIL) — `executive-deliberation-callback.test.ts`:
1. Frame với role A → disable Office A → callback FAILED
   (`AUTHORITY_DENIED: ...`) → được ghi, status `FAILED`, không throw.
2. Cùng kịch bản nhưng callback COMPLETED → vẫn `failedPrecondition` (giữ hành vi cũ).

Verify: như Task 1 (phần Company).

### Task 3 — Chuyển trạng thái sau phân tích đúng sự thật (B5, D3)

Files: `executive-deliberation.service.ts`
- `recordExecutiveAnalysisCallback`: khi đủ số analysis cho frame:
  - 0 COMPLETED → `FAILED_REQUIRES_ATTENTION`;
  - ≥1 COMPLETED → `AWAITING_FOUNDER` (nhánh `CRITIC_REVIEW` xử lý ở Task 4).
- `frameDeliberation`: tập trạng thái cho phép frame thêm
  `FAILED_REQUIRES_ATTENTION` (re-frame tạo `frameVersion` mới — cơ chế sẵn có).
- `cancelDeliberation`: xác nhận `FAILED_REQUIRES_ATTENTION` cancel được (thêm
  test nếu chưa có).

Test trước (FAIL) — `executive-deliberation-callback.test.ts`:
1. 2 role, cả 2 FAILED → state `FAILED_REQUIRES_ATTENTION`.
2. 2 role, 1 COMPLETED + 1 FAILED → `AWAITING_FOUNDER`.
3. Từ `FAILED_REQUIRES_ATTENTION` → `frameDeliberation` thành công,
   `activeFrameVersion` tăng, outbox có event framed mới.

Frontend: `executive_advisory_board_view.dart::_buildStateChip` thêm màu cho
`FAILED_REQUIRES_ATTENTION`; hiện nút "Frame lại" / "Huỷ" ở trạng thái này.
Test: `frontend/test/modules/hologram_hub/views/executive_advisory_board_view_test.dart`.

Verify: Company như trên + `cd frontend && flutter test test/modules/hologram_hub/`.

### Task 4 — Gỡ trạng thái cụt `CRITIC_REVIEW` (B4, D2)

Files:
- `executive-deliberation.service.ts::frameDeliberation`: `criticRequired === true`
  → `APIError.failedPrecondition("CRITIC_REVIEW_NOT_AVAILABLE: critic runner is not implemented")`
  **trước** mọi side effect.
- `recordExecutiveAnalysisCallback`: bỏ nhánh sang `CRITIC_REVIEW` (không còn
  frame mới nào có `criticRequired=true`).
- Tương thích dữ liệu cũ: row đang ở `CRITIC_REVIEW` được coi như
  `AWAITING_FOUNDER` cho mục đích quyết định (Task 5 cho phép decision ở cả 2).
  Không viết migration đổi state (Expand-only; tránh ghi đè lịch sử).
- Frontend: nút quyết định hiện cho `AWAITING_FOUNDER` **và** `CRITIC_REVIEW`;
  `executive_advisory_board_service.dart` không gửi `criticRequired: true`
  (kiểm tra call site; nếu UI có toggle thì ẩn đi).

Test trước (FAIL):
1. Company: frame với `criticRequired: true` → `failedPrecondition`, không có
   row frame/outbox nào được ghi.
2. Flutter view test: deliberation state `CRITIC_REVIEW` hiển thị nút Approve/Cancel.

Verify: Company + `make frontend-test frontend-analyze frontend-api-contract-check`.

### Task 5 — Guard trạng thái cho quyết định Founder (B3)

Files: `executive-deliberation.service.ts::appendFounderDecision`.

Quy tắc:
- `APPROVE | MODIFY | REJECT` → chỉ khi state ∈ {`AWAITING_FOUNDER`, `CRITIC_REVIEW`}
  (CRITIC_REVIEW chỉ vì dữ liệu cũ, Task 4); ngược lại
  `failedPrecondition("DELIBERATION_NOT_AWAITING_FOUNDER: state '<state>'")`.
- `EXPIRE | CANCEL` → mọi state không terminal (giữ hành vi hiện tại).
- Check state nằm **trong** transaction, sau `select` (đã có) — không đọc ngoài tx.

Test:
1. FAIL trước: frame (state `ANALYSIS_QUEUED`) → APPROVE → phải `failedPrecondition`.
2. Sửa test hiện có "appends founder decision and forbids duplicate decision":
   đưa deliberation tới `AWAITING_FOUNDER` qua `recordExecutiveAnalysisCallback`
   (đủ callback cho mọi role) rồi mới APPROVE.
3. REJECT ở `AWAITING_FOUNDER` OK; CANCEL (decision) ở `ANALYZING` OK.
4. Rà `tests/e2e/test_executive_advisory_board*.py` — test nào quyết định trước
   khi có phân tích phải chờ đúng state (poll `GET .../deliberations/:id`), không
   nới guard.

Verify: Company + `make e2e-test`.

### Task 6 — Hợp nhất run authority cho chat với V2 (B6, D1)

**Thiết kế:** endpoint
`GET /internal/operations/projects/:projectId/startup-team/:profileKey/run-authority`
giữ nguyên path + shape response (`ProjectAgentRunAuthority`) để Python worker
không đổi contract, nhưng service đi qua một hàm mới
`resolveChatRunAuthority(workspaceId, projectId, profileKey)` trong
`founder-agent-compatibility.service.ts`:

| mode | V2 ACTIVE | V2 PAUSED/RETIRED | V2 INACTIVE (chưa từng deploy) |
|---|---|---|---|
| ENFORCED | cho phép, spec từ V2 | notFound | notFound |
| SHADOW | cho phép; spec từ **legacy** nếu có (giữ hành vi), log mismatch như hiện tại | **notFound** (D1) | legacy (`getProjectAgentRunAuthority`) |
| LEGACY | legacy | legacy | legacy |

Ràng buộc:
- **Không bao giờ** trả nhánh fallback `hash: "legacy_compat_hash"` /
  `agentWorkforceMemberId: "0"` của `resolveProjectAgentAuthorityV2` cho chat —
  thiếu cả V2 lẫn legacy → `notFound`.
- `policySnapshot` ở nhánh V2: dùng `capabilityOverrides`; `knowledge_gate_passed`
  hiện không được Company set ở đâu cả (xem §4) — không tự suy diễn giá trị này.
- Worker `apps/cosa/worker/handlers.py` giữ nguyên check spec id/version/hash
  với `_AGENT_PROFILE_SPECS` (rolling-deploy guard).

Files:
- `services/company/operations/services/founder-agent-compatibility.service.ts` (hàm mới).
- `services/company/operations/handlers/project-startup-team.handler.ts` (gọi hàm mới).

Test trước (FAIL) — `services/company/operations/tests/founder-agent-compatibility.service.test.ts`:
1. SHADOW: legacy ACTIVE + V2 PAUSED → notFound.
2. SHADOW: legacy ACTIVE + không có V2 → trả legacy (hành vi cũ giữ nguyên).
3. ENFORCED: legacy ACTIVE + không có V2 → notFound; V2 ACTIVE → spec V2.
4. Mọi mode: không legacy, không V2 → notFound (không trả `legacy_compat_hash`).
5. `project-startup-team.handler.test.ts`: response shape không đổi.

Python: thêm 1 test ở `tests/apps/cosa/worker/` — Company trả 404 → run fail
với `project_team_authority_denied` (xác nhận đường sẵn có, không đổi code).

Verify:
```bash
cd services/company && npm run typecheck && npx vitest run operations/tests/founder-agent-compatibility.service.test.ts operations/tests/project-startup-team.handler.test.ts
make company-boundary-check encore-handler-boundary-check ts-suppression-check route-auth-allowlist-check
make apps-cosa-test
```

### Task 7 — Tạo Project không báo lỗi giả khi bootstrap P0 lỗi (B7)

**Thiết kế:** Project đã commit là sự thật; bootstrap là bước hội tụ có thể
repair. `createProjectService` bắt lỗi bootstrap, log có cấu trúc
(`P0_CORE_BOOTSTRAP_INCOMPLETE project=<id> code=<APIError code>`), và trả về
Project kèm field **optional** `p0CoreBootstrap: { status: "COMPLETE" | "INCOMPLETE"; errorCode?: string }`.
Board đã có `p0CoreBootstrapAvailable` + endpoint repair — không thêm endpoint mới.

Files: `project.service.ts`, kiểu `Project` response; nếu response nằm trong
`shared/contracts/mvp-surface.json` thì cập nhật contract + regenerate
(generator của repo, không hand-edit file `*.generated.ts`). Frontend: nếu
`INCOMPLETE` thì hiện banner "Hoàn tất thiết lập P0 Core" trỏ tới action repair.

Test trước (FAIL): mock `bootstrapP0CoreForProject` throw → `createProjectService`
trả Project với `p0CoreBootstrap.status === "INCOMPLETE"`, Project tồn tại
trong DB, không throw.

Verify: Company + `make frontend-api-contract-check contract-freeze-check frontend-test`.

---

## 3. Gate tổng trước khi báo "xong"

```bash
make verify
make e2e-test
make e2e-cross-plane-smoke   # bắt buộc cho Task 1/2 (durability qua process thật — quy tắc #6)
```

Với Task 1, test unit trong cùng process **không** đủ chứng minh retry; cần
thêm 1 kịch bản vào `tests/e2e/test_executive_advisory_board_recovery.py`:
Company tạm từ chối callback của 1 role (vd. disable Office rồi bật lại), worker
thật retry, deliberation cuối cùng rời `ANALYZING`.

## 4. Ngoài phạm vi (ghi nhận, không sửa ở plan này)

- **Synthesis BoardroomMemo** (`ExecutiveBoardRunner.synthesize_boardroom_deliberation`,
  state `SYNTHESIS_QUEUED`) chưa được wire — là feature, cần spec riêng.
- **Critic runner thật** cho `CRITIC_REVIEW` — feature, cần spec riêng (D2).
- **CEO/CTO không có stage preset** (D4).
- **`knowledge_gate_passed`** cho `customer_support`: Company không set ở đâu
  trong `activationPolicySnapshot` → chat `customer_support` qua Project team
  luôn fail `support_knowledge_gate_required`. Cần xác nhận đây là gate có chủ
  đích (chờ luồng knowledge onboarding) hay bug — tách issue riêng.
- `EXPIRED` + `deadline`: không có job hết hạn deliberation.

## 5. Thứ tự & rủi ro

Thứ tự: 1 → 2 → 3 → 4 → 5 → 6 → 7. Task 1–5 cùng vùng deliberation, làm liền
để không phải sửa test hai lần. Task 6 độc lập nhưng rủi ro cao nhất (đổi hành
vi chat ở SHADOW) — chỉ merge sau khi D1 được chốt; rollback = revert commit
(không có migration). Task 7 có đổi contract API — chạy
`contract-freeze-check` trước khi commit.

---

## 6. Trạng thái thực thi (2026-09-25)

Founder chấp thuận D1–D4 theo đề xuất mặc định.

| Task | Trạng thái | Ghi chú |
|---|---|---|
| 1 | DONE | `getDeliberationAuthority` trả `existingAnalysis`; worker bỏ qua role đã ghi (`ALREADY_RECORDED`). |
| 2 | DONE | Outcome FAILED từ Office đã tắt được ghi; COMPLETED vẫn bị từ chối. |
| 3 | DONE (Company + UI chip/huỷ) | UI **chưa có luồng frame** (chỉ tạo draft) nên không thêm nút "Frame lại" — re-frame hiện chỉ qua API. |
| 4 | DONE | `criticRequired=true` → `CRITIC_REVIEW_NOT_AVAILABLE`; bỏ `criticRequired` khỏi Flutter service; UI cho quyết định ở `CRITIC_REVIEW` (dữ liệu cũ). |
| 5 | DONE | APPROVE/MODIFY/REJECT chỉ ở `AWAITING_FOUNDER`/`CRITIC_REVIEW`; test cũ đã sửa đi qua callback. |
| 6 | DONE | `resolveChatRunAuthority` (mode-aware) thay `getProjectAgentRunAuthority` ở endpoint run-authority; path/shape response giữ nguyên. |
| 7 | DONE (backend) | `p0CoreBootstrap: COMPLETE/INCOMPLETE` trong response tạo Project. Banner Flutter **chưa làm** — Board đã có action repair `p0CoreBootstrapAvailable`. |

Kiểm chứng đã chạy:
- Company: toàn bộ vitest (1657 pass; 1 fail `finance-legal/tests/cas-link.test.ts` có sẵn trên base) + `tsc --noEmit`.
  18/24 test mới FAIL trên code gốc, 6 test còn lại là test giữ hành vi cũ.
- `make apps-cosa-test` (1266 pass, coverage 83.26%), `make typecheck-py`, `make lint`,
  `make boundary-check company-boundary-check encore-handler-boundary-check ts-suppression-check route-auth-allowlist-check frontend-api-contract-check contract-freeze-check`.
- Flutter: `flutter test` toàn bộ (935 pass), `flutter analyze` sạch; 2 test mới FAIL trên view gốc.
- `make agent-test`: 3 fail + coverage 78.88% — giống hệt base (cần Postgres Agent Platform), `packages/agent` không bị sửa.

**Chưa kiểm chứng:** kịch bản E2E retry qua process thật (§3) — cần `encore run`
(Encore CLI), không cài được trong môi trường thực thi. Chưa viết test E2E đó.
