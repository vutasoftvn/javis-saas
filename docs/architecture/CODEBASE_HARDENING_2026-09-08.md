# Codebase Hardening 2026-09-08 — Release Evidence Matrix

Tài liệu này là bằng chứng phát hành (release evidence) cho plan
`docs/superpowers/plans/2026-09-08-platform-authority-durability-hardening.md`
(Task 9 — task cuối cùng của plan). Nó KHÔNG dùng nhãn "done" chung; mỗi hàng
có 3 trục trạng thái độc lập theo đúng yêu cầu của brief:

- **IMPLEMENTED** — code thay đổi đã tồn tại trong commit, có test negative
  chứng minh hành vi cũ (lỗ hổng) đã bị chặn.
- **WIRED** — đường gọi thật (handler → service → DB, hoặc route → kernel)
  đã nối, không phải test độc lập gọi thẳng hàm nội bộ.
- **VERIFIED** — đã chạy xanh trong môi trường có hạ tầng thật (Postgres/
  Encore thật, không phải mock) trong phiên làm việc này (2026-09-08), hoặc
  trong một CI run trước đó có thể tham chiếu.

`ACCEPTED` (trạng thái ADR) không nằm trong 3 trục trên — ADR số liên quan chỉ
xác nhận quyết định kiến trúc đã chốt, không tự động suy ra IMPLEMENTED.

## 1. Bảng finding chính (Task 1–8)

| # | Finding | Commit(s) | Test negative (đỏ→xanh) | Test integration | Migration | Rollback | Trạng thái |
|---|---|---|---|---|---|---|---|
| 1 | Membership takeover qua `company_id` trần (self-join) | `6c6a3c17` (ADR + red test), `b4271c41` (feature), `fd56f244` (fix insert race) | `services/cosa/tests/control-plane.test.ts` — "rejects joining an existing company via bare company_id"; `services/cosa/tests/workspace-invitation.test.ts` — 13 case bao gồm sai email, revoke, expired, garbage token, concurrent accept chỉ 1 membership | `workspace-invitation.test.ts` chạy qua Encore test runtime thật (không mock DB) | `services/cosa/migrations/34_workspace_invitations.up.sql` (expand-only: tạo bảng `workspace_invitations`) | `34_workspace_invitations.down.sql` tồn tại, drop bảng structurally — xem mục 2 (Migration preflight) về giới hạn rollback trên dữ liệu thật | IMPLEMENTED, WIRED, VERIFIED (vitest chạy trong phiên này qua `make services-test`, xem kết quả bên dưới) |
| 2 | `POST /platform/auth/companies/join` vẫn tồn tại như đường vòng | `d39a1bee` (Task 6, gỡ khỏi frontend + contract) | `grep -rn "companies/join" frontend/lib` chỉ còn 1 dòng comment giải thích đã gỡ, không còn lời gọi thật; route không còn trong `shared/contracts/mvp-surface.json` | `make frontend-api-contract-check` (xem mục 3) | — | — | IMPLEMENTED, WIRED, VERIFIED |
| 3a | `GET /identity/workspaces/:id` không xác thực caller (public read) | `eef5b4d1` | `services/company/identity/tests/*` — unauthenticated + member-of-workspace-B bị từ chối | handler thật gọi `requireWorkspaceAccess(authorization, id)` trước `getWorkspaceRecord` — xem `services/company/identity/handlers/workspace.handler.ts:22-36` | — | — | IMPLEMENTED, WIRED, VERIFIED |
| 3b | Ghi nhận giao dịch tài chính chỉ cần membership đọc, không cần command authority riêng | `eef5b4d1` | `services/company/finance-legal/tests/financial-transaction.test.ts` — "rejects recording a transaction for an auditor (read-only)…", "rejects … for a plain member with no explicit finance.transaction.record grant" | Cùng file, case approval-threshold vẫn giữ nguyên phía sau command-authority gate | `services/company/identity/migrations/11_finance_transaction_record_permission.up.sql` | `11_finance_transaction_record_permission.down.sql` tồn tại | IMPLEMENTED, WIRED, VERIFIED |
| 4 | Approval reviewer không bị kiểm tra `requirement.role` server-side (bất kỳ member nào cũng decide được approval yêu cầu founder) | `ee6177e2` | `tests/apps/cosa/test_workforce_routes.py`: `test_member_reviewer_without_required_role_gets_403_and_stays_pending`, `test_admin_reviewer_without_exact_required_role_gets_403`, `test_founder_reviewer_with_matching_required_role_succeeds`, `test_malformed_requirement_role_fails_closed_to_operator_roles`, `test_unknown_requirement_role_fails_closed_to_operator_roles` | `apps/cosa/api/approval_authority.py` gọi tenant-context server-signed, không đọc role từ body/header | — | — | IMPLEMENTED, WIRED, VERIFIED |
| 5 | Cancel run không phải durable CAS — worker khác process có thể ghi đè `CANCELLED` bằng `COMPLETED/FAILED` | `a11f7088` (CAS primitives + kernel), `2138614f` (route không tự clobber audit reason), `ae23e6cf` (lint fix, không phải finding riêng) | `tests/agent/runs/test_run_repository.py`; `tests/agent/runs/test_cancel_complete_race_postgres.py::test_cancel_vs_late_complete_race_resolves_to_cancelled_across_processes` — race thật giữa 2 process trên Postgres thật | HTTP cancel route (`apps/cosa/api/routes.py`) chỉ emit `run.cancelled` khi `cancel_run` transition thật sự thành công | — (dùng cột `status`/`error_details`/`completed_at` đã có sẵn) | — | IMPLEMENTED, WIRED, VERIFIED (race test chạy trên Postgres thật, không phải 2 instance cùng process — đúng yêu cầu quy tắc #6 CLAUDE.md) |
| 6 | Snowflake ID 19 chữ số bị `int.tryParse` cắt cụt trong luồng join/auth Flutter | `d39a1bee` | `frontend/test/auth_flow_test.dart` dùng ID `9223372036854775807`, assert không còn field "company ID" nhập tay, chỉ còn invitation token | Backend phía `services/cosa` vốn đã string-safe từ Task 2 | — | — | IMPLEMENTED, WIRED, VERIFIED |
| 7 | Lease/crash-recovery integration test fallback về `DATABASE_URL`/port cố định `:4000`, không cô lập khỏi dev stack đang chạy | `cf9b4431` | `tests/apps/cosa/worker/test_lease_mutual_exclusion_real.py`, `tests/apps/cosa/worker/test_crash_recovery_subprocess.py` — chạy trên disposable Postgres cluster + Encore thật, port reserve động | `make lease-integration-test` (Make target mới) | — | — | IMPLEMENTED, WIRED, VERIFIED — 5/5 passed trên Postgres/Encore thật khi review trước đó; xem kết quả chạy lại trong phiên này ở mục 3 |
| 8 | 6 frontend test file placeholder/no-op (`expect(true)` hoặc comment rỗng) tạo cảm giác coverage giả | `edc58a42` | Từng file được thay bằng assertion hành vi thật, hoặc xóa tên test nếu feature không tồn tại; thêm widget test đỏ cho chat retry (`AgentChatApiException(503)`) | Chat composer: optimistic message bị revert, spinner tắt, nút retry gọi lại đúng 1 lần | — | — | IMPLEMENTED, WIRED, VERIFIED |

## 2. Migration preflight (Step 2)

- `make dev-preflight` yêu cầu Company (`:4000`), Control Plane (`:4001`) và
  FastAPI (`:8000`) đang chạy — môi trường thực thi Task 9 chỉ có hạ tầng
  Docker (`cosa_postgres`, `cosa_livekit_local`, `cosa_minio`) đang chạy, các
  service Encore/FastAPI KHÔNG được khởi động (không nằm trong scope Task 9 —
  Task 9 là documentation + verification, không phải chạy toàn bộ dev stack).
  Lệnh thất bại với `❌ COSA Control Plane not reachable at http://127.0.0.1:4001`
  sau khi các bước env-var và docker-compose config đã pass. Đây là giới hạn
  môi trường, không phải regression — được ghi nhận trung thực thay vì ép chạy
  xanh giả.
- Xác minh thủ công số migration (thay thế phần "migrate lên disposable
  database" của `dev-preflight`, theo đúng phương án fallback brief cho phép):
  - `ls services/cosa/migrations | sort -V | tail -6` → migration cao nhất là
    `34_workspace_invitations.{up,down}.sql`, không có khoảng trống/trùng số
    (33 → 34 liên tục).
  - `ls services/company/identity/migrations | sort -V | tail -6` → migration
    cao nhất là `11_finance_transaction_record_permission.{up,down}.sql`,
    không có khoảng trống/trùng số (10 → 11 liên tục).
- **Giới hạn rollback (bắt buộc ghi rõ theo brief):** `34_workspace_invitations.down.sql`
  drop bảng `workspace_invitations` đúng về mặt cấu trúc (structurally đúng),
  nhưng nếu chạy down-migration này trên một database production đã có
  invitation row thật (đã issue, đã accept, đang pending), **dữ liệu đó sẽ mất
  vĩnh viễn** — đây không phải bug, mà là giới hạn bình thường của bất kỳ
  down-migration nào trên bảng có dữ liệu thật. Trước khi rollback ở production,
  phải backup bảng `workspace_invitations` riêng hoặc chấp nhận mất lịch sử
  invitation đang pending/đã accept.

## 3. Kết quả từng gate (Step 3) — chạy trong phiên làm việc này, 2026-09-08

Mỗi gate được chạy RIÊNG LẺ (không chain) để cô lập lỗi. Môi trường có hạ tầng
Docker thật (`cosa_postgres`, `cosa_minio`, `cosa_livekit_local`) và `encore`
CLI cài sẵn tại `/opt/homebrew/bin/encore`; KHÔNG có Company/Control-Plane/
FastAPI service nào đang chạy sẵn (không phải `make dev-stack`).

**Lưu ý bắt buộc về working tree:** trong suốt phiên này, một phiên Claude
Code KHÁC đang chạy song song với nhiều file uncommitted thuộc một tính năng
localization không liên quan (`apps/cosa/policies/locale_policy.py`,
`frontend/lib/**` các file locale, `docs/academy/*`, …). Các gate dưới đây
chạy trên working tree hỗn hợp này (không có worktree cô lập — bị cấm bởi
CLAUDE.md). Với mỗi gate fail, phần "Triage" xác định bằng bằng chứng cụ thể
(file:line, `git log`, `git status`) liệu lỗi có thuộc phạm vi commit của plan
này (`c91ab8f6..edc58a42`) hay không.

| Gate | Kết quả | Ghi chú / Triage |
|---|---|---|
| `make boundary-check` | PASS | `tests/apps/cosa/test_services_boundary_audit.py` 3 passed; rg guard cho `frontend/lib` không match gì (không có `:8888`/`backend/server`/`javis/`/`web_socket_channel`). |
| `make company-boundary-check` | PASS | `node scripts/check_company_boundaries.mjs` → "✅ Company boundaries check passed." |
| `make encore-handler-boundary-check` | PASS | `tests/quality/test_encore_handler_boundaries.py` 7 passed; script "✅ ZERO database access in handlers." |
| `make ts-suppression-check` | PASS | `tests/quality/test_ts_suppressions.py` 5 passed; script "✅ ZERO @ts-ignore / @ts-expect-error." |
| `make frontend-api-contract-check` | PASS | `tests/quality/test_frontend_api_contracts.py` 12 passed; script xác nhận mọi route literal khớp contract hoặc allowlist còn hạn — bao gồm việc `companies/join` không còn xuất hiện như lời gọi thật. |
| `make route-auth-allowlist-check` | PASS | `tests/quality/test_route_auth_allowlist.py` 2 passed. |
| `make skillpacks-validate` | PASS | `scripts/validate_skillpacks.py` chạy xong không lỗi (chỉ có cảnh báo `TAVILY_API_KEY not configured` — fallback `NullWebSearchProvider`, không phải lỗi gate). |
| `make contract-freeze-check` | **FAIL lần đầu, PASS sau khi sửa** | Lần chạy đầu: `company-usage-inventory.md lệch — chạy make company-usage-inventory và commit`. **Triage:** `git log -1 -- docs/architecture/generated/company-usage-inventory.md` cho thấy file generated này lần cuối được sinh tại commit `b4271c41` (Task 2, đầu plan) — các commit SAU đó của chính plan này (`ee6177e2` sửa `apps/cosa/api/approval_authority.py`, `d39a1bee` sửa các file `frontend/lib/modules/auth/*`) đã thay đổi số lần match heuristic của inventory nhưng không ai chạy lại generator. Đây LÀ lỗi do phạm vi commit của plan này gây ra (không phải do phiên locale song song — các file liên quan như `auth_service.dart` hiện `git status` sạch, tức nội dung khớp đúng commit `d39a1bee`, không phải bản uncommitted của phiên khác). Đã sửa bằng cách chạy `python3 scripts/company_usage_inventory.py` (script generator chính thức, không hand-edit) và xác nhận `make contract-freeze-check` pass lại — "company usage inventory in sync ✓". File generated này được thêm vào commit của Task 9 cùng với evidence doc. |
| `make services-test` | PASS | `services-test-company`: 232 file test, 1443 test pass. `services-test-cosa`: 32 file test, 413 test pass (bao gồm `tests/workspace-invitation.test.ts` 13 test, `tests/control-plane.test.ts` 16 test). Lưu ý môi trường: lần chạy đầu tiên fail với `COSA_MIGRATOR_DATABASE_URL is required` — nguyên nhân là biến môi trường không được export đúng cách qua ranh giới lời gọi `Bash` tool (mỗi lời gọi là process con mới); sau khi `source scripts/load-dev-env.sh && make services-test-cosa` chạy trong CÙNG MỘT invocation, pass sạch — đây là thao tác vận hành của phiên làm việc, không phải lỗi code. |
| `make agent-test` | PASS | 916 passed, 61 skipped, coverage 83.11% (gate yêu cầu ≥80%). |
| `make apps-cosa-test` | PASS | 1053 passed, 27 skipped, coverage 84.33% (gate yêu cầu ≥78%). |
| `make frontend-test` | PASS | "All tests passed!" — 1522 test case (bao gồm các file Task 8 đã thay no-op bằng assertion thật). |
| `make frontend-analyze` | PASS | `flutter analyze` → "No issues found! (ran in 3.6s)". |
| `make lease-integration-test` | **FAIL lần đầu (môi trường), PASS sau khi cô lập biến môi trường** | Lần đầu: `psycopg2.OperationalError: password authentication failed for user "postgres"` — nguyên nhân: script test dùng credential admin `PGUSER=postgres`/`PGPASSWORD` từ môi trường, còn `.env` của repo đặt `POSTGRES_PASSWORD=dev-postgres-password` (khác mặc định `"postgres"` cứng trong thư viện test) — đúng y hệt cảnh báo trong docstring của Make target. Sửa: export `PGPASSWORD=dev-postgres-password` đúng theo hướng dẫn. Lần hai: 4/5 test fail với `401 Unauthorized` tại `control-plane/internal/leases/acquire` và timeout claim task — **triage:** do chính phiên làm việc này đã `source scripts/load-dev-env.sh` trước đó nạp `WORKER_SERVICE_JWT_SECRET` thật từ `.env` vào ambient env; `tests/apps/cosa/worker/test_lease_mutual_exclusion_real.py::_sign_worker_token` ký token bằng `os.environ.get("WORKER_SERVICE_JWT_SECRET")` (ambient, = secret thật), trong khi `tests/e2e/stack/subprocess_stack.py:94` boot tiến trình `services/cosa` cô lập với secret cố định cho test (`cosa-worker-service-jwt-key-change-in-prod-min32chars`) — hai bên ký lệch nhau ⇒ 401. Đây KHÔNG phải lỗi code của Task 7 (chính cơ chế cô lập DSN/port của Task 7 hoạt động đúng — nó chỉ không tính đến việc ambient env của người vận hành rò secret JWT khác vào). Sau khi chạy lại với `env -u WORKER_SERVICE_JWT_SECRET -u PLATFORM_JWT_SECRET`, **5/5 PASS** (21.57s) — khớp với "verified live" trong message commit `cf9b4431`. Khuyến nghị vận hành: không `source scripts/load-dev-env.sh` trước khi chạy `make lease-integration-test`; chỉ cần `PGPASSWORD` khớp `POSTGRES_PASSWORD` thật. |
| `make e2e-cross-plane-smoke` | **FAIL — pre-existing, KHÔNG do plan này** | 3 passed, 2 failed (`test_s2_dispatch_worker_result`, `test_s3_capability_governance`). **Triage:** cả hai fail cùng nguyên nhân gốc — `run.failed` với `{'error': 'Company Service Error (500): an internal error occurred'}` thay vì `policy_snapshot_unavailable` mong đợi. Đây CHÍNH LÀ bug B5 "company-service-500" đã biết và ĐÃ CÔNG BỐ trước khi plan này bắt đầu (xem memory `javis-saas-b5-cross-plane-delegation-fixed.md`: "1 bug company-service-500 mới lộ ra, chưa sửa"). Bằng chứng loại trừ: `git log --oneline c91ab8f6..edc58a42 -- tests/e2e/scenarios/capability_governance.py tests/e2e/test_cross_plane_smoke.py` không trả về commit nào — plan này (Task 1–8) chưa từng sửa 2 file test đó, cũng không sửa `services/company/shared/auth/cosa-delegation.service.ts` (nơi B5 từng được vá). Bản thân test đã có comment tường minh chấp nhận nhánh fail này là fail-closed đúng thiết kế governance, chỉ assert sai lệch ở đúng error code cụ thể. **Kết luận: KHÔNG block release của plan này; đây là một bug pre-existing, riêng biệt, đã biết trước, cần một plan sửa lỗi khác (bug company-service-500 nêu trong memory).** |

