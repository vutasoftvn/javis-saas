# AgentOS Authorization & Frontend Parity — Release Checklist

**Nguồn:** Task 11 của
`docs/superpowers/plans/2026-08-31-agentos-auth-contract-frontend-parity.md` (đã gỡ khỏi repo tại commit `3c0234ec`),
đóng lại các finding trong
[`docs/architecture/reports/2026-08-31-agentos-auth-contract-parity-audit.md`](../../architecture/reports/2026-08-31-agentos-auth-contract-parity-audit.md).

Đây là bằng chứng release gate cho AgentOS Event Rule / Event Operations /
Autopilot Metrics / Skill Registry authorization và Flutter Strategy/Extensions
parity. Checklist dùng để attest trước khi promote lên staging/production —
KHÔNG tự đánh dấu hoàn thành các mục cần con người (staging run, reviewer)
tại đây.

## Checklist

- [ ] `make contract-freeze-check`, `make agent-test`, `make apps-cosa-test`, Flutter tests and analyzer passed at SHA: `42bec7f7bf10de1626ee9d679c5627454b498787`.

  **Chưa được tick** — không phải tất cả đều PASS theo nghĩa đen. Tại SHA trên
  (commit gần nhất trước khi tạo tài liệu này của Task 11):
  - `make lint typecheck-py boundary-check skillpacks-validate` — PASS.
  - `make agent-test` — PASS (710 passed, 29 skipped).
  - `make apps-cosa-test` — PASS (576 passed, 15 skipped).
  - `cd frontend && flutter test` — PASS (500 tests passed).
  - `cd frontend && flutter analyze` — PASS ("No issues found!").
  - `cd landing && npm test -- --run && npm run lint && npm run build` — PASS.
  - `make contract-freeze-check` — **FAIL**, nhưng chỉ vì một phần con đã biết
    trước và **nằm ngoài phạm vi plan này**:
    `node scripts/gen-contracts.mjs --check` → PASS ("contracts generated code
    in sync"); `scripts/route_inventory.py --check` → PASS ("route inventory
    in sync", chạy 2 lần cho cả company và cosa); nhưng
    `scripts/company_usage_inventory.py --check` → FAIL ("company-usage-inventory.md
    lệch"). Drift này đã được xác nhận độc lập 2 lần trước đó (trong Task 8, và
    lại trong lần thử Task 11 trước) là lệch dàn trải trên
    `services/cosa/*.ts`, `services/company/*`, `frontend/lib/**/*.dart` và
    nhiều migration trong toàn repo — tích lũy từ trước, không do bất kỳ task
    nào của plan này gây ra. Không tự chạy `make company-usage-inventory` và
    commit kết quả ở đây (ngoài phạm vi được giao); cần một task/owner riêng
    dọn drift này rồi mới tick được ô này.

- [ ] A no-token request returned 401 for Event Rule, Event Operations, Autopilot Metrics and Skill Registry.

  Bằng chứng test hồi quy hiện có (Tasks 2–5), đã đọc lại nguyên văn để xác
  nhận đúng assertion trước khi trích dẫn:
  - Event Rule: `tests/apps/cosa/test_event_rule_admin.py::test_rule_routes_reject_missing_identity`
    — `unsecured_client.post("/agent/events/rules", ...)` → `assert response.status_code == 401`.
  - Event Operations: `tests/apps/cosa/test_event_operations.py::test_missing_identity_cannot_read_correlation`
    — `unsecured_client.get("/agent/events/correlation/{id}")` → `status_code == 401`.
  - Autopilot Metrics: `tests/apps/cosa/test_autopilot_metrics.py::test_metrics_require_identity`
    — `unsecured_client.get("/agent/autopilot/metrics")` → `status_code == 401`.
  - Skill Registry: không có test riêng ở route-level khẳng định 401 cho
    `/agent/skills*` trong `tests/apps/cosa/test_skill_registry_routes.py` (đã
    `grep` xác nhận không có case nào gọi endpoint này qua client không có
    Authorization header). Mọi route trong `apps/cosa/api/skill_registry_routes.py`
    đều lấy identity qua `identity: AuthenticatedIdentity | None =
    Depends(get_authenticated_identity)` — cùng một dependency dùng chung với
    3 router trên. Dependency đó tự raise 401 trước khi vào route body khi
    thiếu/sai Authorization header (`apps/cosa/auth/dependency.py:223-227`),
    nên FastAPI không bao giờ inject `identity=None` cho request thật thiếu
    token trong production; nhánh `if identity is None: raise HTTPException(400, ...)`
    trong route code chỉ có thể chạm tới khi test tự override dependency để
    truyền `None` — chưa test nào làm vậy cho skill registry. Bằng chứng thực
    tế cho hành vi 401 của chính dependency dùng chung này là
    `tests/apps/cosa/auth/test_dependency.py::test_missing_authorization_header_401`
    (và `test_non_bearer_authorization_401`, `test_garbage_token_rejected_401`).
    Ghi nhận đây là gap kiểm thử ở mức route cho Skill Registry — không phải
    gap hành vi — cần một test route-level trực tiếp bổ sung nếu muốn khớp
    100% với format bằng chứng của 3 router kia.

- [ ] A workspace-B identity received 404 for a workspace-A rule, correlation chain, candidate skill and metrics query override.

  - Rule: `tests/apps/cosa/test_event_rule_admin.py::test_enable_rejected_cross_workspace`
    — tạo rule ở `ws_1`, override identity sang `ws_2`, enable → `status_code == 404`.
  - Correlation chain: `tests/apps/cosa/test_event_operations.py::test_workspace_b_gets_not_found_for_workspace_a_chain`
    — `client_b` đọc chain đã seed cho `ws_ops_a` → `status_code == 404`.
  - Candidate skill: `tests/apps/cosa/test_skill_registry_routes.py::test_list_and_get_reject_workspace_query_override`
    — identity `ws-1` gọi `GET /agent/skills?workspace_id=ws-other` và
    `GET /agent/skills/private-skill?workspace_id=ws-other` → cả hai
    `status_code == 404` (`resolve_identity_workspace` từ chối mọi
    `workspace_id` khác identity đã xác thực). Đây là test khẳng định 404
    trực tiếp; `tests/apps/cosa/test_workspace_custom_skill_isolation.py::test_promoted_workspace_custom_skill_is_invisible_to_another_workspace`
    bổ sung bằng chứng cô lập cùng loại nhưng qua đường khác — đọc lại cho
    thấy nó verify bằng `GET /agent/skills?workspace_id=ws-b` trả **200** với
    skill bị lọc khỏi danh sách (`_contains_skill` → False), KHÔNG phải một
    assertion `status_code == 404` — nên không dùng làm bằng chứng 404 ở đây,
    chỉ dùng làm bằng chứng cô lập bổ sung.
  - Metrics query override: `tests/apps/cosa/test_autopilot_metrics.py::test_metrics_ignore_cross_workspace_query`
    — `member_a_client.get("/agent/autopilot/metrics?workspaceId=ws_metric_b")`
    → `status_code == 404`.

- [ ] A member identity received 403 for rule create/enable, event retry, skill update and skill deprecation.

  - Rule create/enable: `tests/apps/cosa/test_event_rule_admin.py::test_member_cannot_create_or_enable_rule`
    — member tạo rule → `403`; sau khi founder tạo hộ, member enable rule đó → `403`.
  - Event retry: `tests/apps/cosa/test_event_operations.py::test_member_cannot_retry_and_missing_event_is_not_success`
    — `member_client.post("/agent/events/missing/retry")` → `403` (và
    operator cùng request trên event không tồn tại → `404`, không phải `200`,
    chứng minh "missing event" không bị coi là thành công).
  - Skill update và deprecation: `tests/apps/cosa/test_skill_registry_routes.py::test_member_cannot_update_or_deprecate_workspace_skill`
    — cùng một test khẳng định cả hai: `PUT /agent/skills/private-skill` → `403`
    và `POST /agent/skills/private-skill/deprecate` → `403`.

- [ ] Staging owner recorded date, environment, trace/correlation IDs and reviewer: ______.

  Chưa thực hiện — đây là bước vận hành con người trên môi trường staging
  thật, plan này (mục Non-goals) không cấp phép chạy migration/deploy hay
  ghi dữ liệu production/staging. Điền vào ô này khi staging owner thực sự
  chạy smoke test và ghi log.

## Ghi chú phạm vi

- Checklist này không tự động hoá việc tick — mỗi ô chỉ được tick bởi người
  thực sự xác minh bằng chứng tương ứng là đúng tại thời điểm đó, không phải
  vì tài liệu này tồn tại.
- `company-usage-inventory` drift (mục 1) là pre-existing, theo dõi riêng —
  không phải regression của plan `2026-08-31-agentos-auth-contract-frontend-parity`.
