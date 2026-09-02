# Truthful MVP Release Checklist (Task 10, 2026-09-02)

Nguồn: `.superpowers/sdd/2026-09-01-truthful-mvp-hardening/task-10-brief.md`,
plan wrap-up cho 9 task trước đó (commit `e6cca21e..b745c148`, đã review độc
lập). Tài liệu này là bằng chứng phát hành trung thực — mọi mục PASS bên dưới
có lệnh/tệp/test cụ thể đi kèm; mọi mục CHƯA XÁC MINH được ghi rõ lý do,
không suy diễn hoặc giả lập.

## 1. Dependency baseline (Step 1)

- Resolver đã chọn: **pip-tools** (repo trước đó không dùng `uv` lẫn
  `pip-tools` — chỉ `pip install -r requirements.txt` trần trong CI). Chọn
  pip-tools vì khớp tự nhiên với quy ước file `requirements.txt` sẵn có
  (chuyển thành cặp `.in` nguồn + `.txt` lock có hash, không đổi tên file mà
  CI/Makefile đang tham chiếu).
- `packages/agent/requirements.in` → `packages/agent/requirements.txt`
  (501 dòng, pin `==` + `--hash=sha256:...` cho toàn bộ transitive deps).
- `apps/cosa/requirements.in` → `apps/cosa/requirements.txt` (2709 dòng,
  cùng cơ chế).
- Xác minh compile deterministic: recompile cùng input trên cùng máy cho ra
  byte-identical output (`packages/agent/requirements.txt` diff rỗng giữa 2
  lần chạy `pip-compile --generate-hashes --allow-unsafe`).
- `pip-audit --require-hashes` trên cả 2 lock: **0 vulnerability** tại thời
  điểm chạy (2026-09-02).
- CI (`.github/workflows/quality.yml`): mọi `pip install -r
  packages/agent/requirements.txt -r apps/cosa/requirements.txt` đổi thành
  `pip install --require-hashes ...` (tách riêng lệnh install phụ
  không-hash như `pytest-asyncio`, `requirements-dev.txt` sang lệnh `pip
  install` thứ hai — pip's hash-checking mode yêu cầu MỌI requirement trong
  cùng 1 lệnh install phải có hash, nếu không sẽ lỗi ngay khi hash được bật).
  Verify: đã đọc lại toàn bộ YAML bằng `yaml.safe_load` sau khi sửa — parse
  hợp lệ.
- Thêm job mới `python-dependency-audit`: recompile lock trong CI rồi `git
  diff --exit-code` để chặn drift âm thầm giữa `.in` và `.txt` đã commit, cộng
  `pip-audit --require-hashes` để chặn lỗ hổng đã biết lọt vào lock.
- **PASS** — verify bằng `pip-compile`/`pip-audit`/`yaml.safe_load` chạy trực
  tiếp trong phiên này.

## 2. Mypy hardening (Step 2)

- `check_untyped_defs = true` bật global trong `pyproject.toml`
  `[tool.mypy]`. Full-repo `mypy` sau khi bật: **0 lỗi mới** trên 329 file —
  không có method object-store nào (`packages/agent/vault/object_store.py`,
  `apps/cosa/knowledge_ingestion/object_store.py`) bị mypy report thêm, nên
  không cần sweep annotate diện rộng.
- `disallow_untyped_defs = true` áp qua `[[tool.mypy.overrides]]` CHỈ cho 5
  module Tasks 1-9 đã sửa (lấy từ `git log --stat e6cca21e..b745c148 --
  apps/cosa packages/agent`, không đoán):
  - `apps.cosa.api.mvp_contracts_generated` (generated — 0 lỗi, không hand-edit)
  - `apps.cosa.api.settings_routes`
  - `apps.cosa.api.vault_routes`
  - `apps.cosa.api.workforce_routes`
  - `apps.cosa.composition.agent_plane`
- 29 lỗi `no-untyped-def` xuất hiện lần đầu khi bật override → đã annotate
  cụ thể từng hàm (không suppress):
  - `vault_routes.py`: 8 handler chỉ `raise` → `-> NoReturn`, kèm
    `response_model=None` trên decorator (FastAPI crash lúc import nếu build
    response model Pydantic từ `NoReturn` — xác nhận bằng cách chạy pytest
    collection thật, xem mục 4).
  - `workforce_routes.py`: 15 handler → trả kiểu cụ thể
    `MvpSuccess[...]` (import thêm `MvpSuccess` từ `mvp_response`).
  - `settings_routes.py`: 2 handler → `MvpSuccess[SkillSettingView]` /
    `MvpSuccess[list[SkillSettingView]]`.
  - `agent_plane.py`: 1 closure `_connector_grant_resolver` → tham số
    `GatewayExecutionRequest`, trả `ConnectorGrant | None` (khớp đúng type
    param `CapabilityGateway.__init__` đã khai báo, không phải suy đoán).
- Không có `# type: ignore` mới nào được thêm ở các file trên.
- Tất cả module còn lại trong repo (chưa qua override) vẫn `disallow_untyped_defs
  = false` — không flip global, đúng yêu cầu brief.
- **PASS** — `make typecheck-py` xanh (0 lỗi/329 file) sau khi hardening.

## 3. Dependency modernization (Step 3)

### 3a. flutter_markdown → flutter_markdown_plus

- `flutter_markdown` (0.7.7+1, discontinued trên pub.dev) thay bằng
  `flutter_markdown_plus` (^1.0.3, resolve về 1.0.12) trong
  `frontend/pubspec.yaml`. `flutter pub get` chạy thật, `pubspec.lock` sinh
  lại bởi tool (không hand-edit).
- Trước đây 2 call site (`chat_message_bubble.dart`,
  `hub_chat_message_bubble.dart`) import package trực tiếp — KHÔNG có
  abstraction sẵn. Tạo mới `frontend/lib/core/widgets/app_markdown_body.dart`
  (widget `AppMarkdownBody` bọc `MarkdownBody`, export `MarkdownStyleSheet`)
  — mọi render markdown trong app giờ đi qua 1 điểm, lần đổi package sau chỉ
  sửa 1 file. Cả 2 call site đã chuyển sang dùng `AppMarkdownBody`.
- Test hồi quy sẵn có `frontend/test/modules/hologram_hub/
  hub_chat_message_bubble_link_guard_test.dart` (test link-guard qua
  `MarkdownBody.onTapLink`) cập nhật import sang `flutter_markdown_plus` —
  API tương thích (`MarkdownTapLinkCallback`, `MarkdownBody` giữ nguyên
  chữ ký). Chạy: **6/6 pass**.
- `flutter analyze`: 0 issue. `flutter test -r compact` toàn repo: xem mục 4
  (1094 test, 5 fail — đã xác nhận KHÔNG liên quan tới thay đổi này, xem chi
  tiết bên dưới).

### 3b. Vitest CJS/ESM warning

- Chạy tuần tự đúng yêu cầu: `npm test -- --run` (30/30 pass, warning CJS/ESM
  xuất hiện) → `npm run lint` (0 issue) → `npm run build` (thành công) TRƯỚC
  khi rename.
- Rename `landing/vitest.config.ts` → `landing/vitest.config.mts` (dùng
  `git mv`, giữ nguyên `landing/` sạch — không đụng file nào khác của Task 9
  trong thư mục này).
- Sau rename, cảnh báo CJS/ESM biến mất; xuất hiện cảnh báo khác về
  `__dirname` không tồn tại trong ESM thuần — sửa luôn thành
  `import.meta.dirname` (1 dòng, cùng file, cùng nguyên nhân rename).
- Re-run `npm test -- --run` / `npm run lint` / `npm run build`: **0 warning,
  tất cả pass**.
- **PASS**.

## 4. Release matrix (Step 4)

Chạy đúng thứ tự lệnh trong brief, trên máy dev với `.venv` (Python 3.11) +
Postgres KHỞI TẠO MỚI qua Docker (`pgvector/pgvector:pg16`, cổng `55432`,
container `cosa_ci_test_pg` — KHÔNG dùng cluster dev đang chạy ở cổng `5432`)
cho phần DB-backed. Container đã bị xoá (`docker rm -f`) sau khi dùng xong.

| # | Lệnh | Kết quả | Ghi chú |
|---|---|---|---|
| 1 | `make lint` | PASS | 1 file (`apps/cosa/capabilities/workspace_settings_client.py`, đã commit trước đó ở Task 9) lệch format — chạy `ruff format` sửa tại chỗ (mechanical, không đổi hành vi). Sau sửa: 330 file formatted. |
| 2 | `make typecheck-py` | PASS | 0 lỗi / 329 file (xem mục 2). |
| 3 | `cd services/company && pnpm typecheck` | PASS | `tsc --noEmit` sạch. |
| 4 | `cd services/cosa && pnpm typecheck` | PASS | `tsc --noEmit` sạch. |
| 5 | `make boundary-check` | PASS | `test_services_boundary_audit.py` 3 passed; `rg` boundary literal-route guard: 0 match (đúng — nghĩa là sạch). |
| 6 | `make contract-freeze-check` | PASS (sau 1 lần regen) | `company-usage-inventory.md` lệch do Task 9 thêm file mới (`landing/src/lib/early-access-store.ts`, `.../resend.ts`, `.../api/early-access/route.ts`) mà chưa regen inventory. Đây là generated file (`docs/architecture/generated/`) — chạy generator thật (`scripts/company_usage_inventory.py`, không hand-edit) rồi commit lại. Sau đó `--check` xanh. |
| 7 | `make frontend-api-contract-check` | PASS | pytest 11 passed + `check_frontend_api_contracts.mjs` báo "mọi literal/template route khớp contract". |
| 8 | `cd frontend && flutter analyze` | PASS | 0 issue. |
| 9 | `cd frontend && flutter test -r compact` | **1089/1094 pass, 5 fail** | 5 fail: `action_preview_card_test.dart` (3 case), `lifecycle_tranche_a_flow_test.dart`, `workspace_runtime_service_test.dart` (2 case), `hologram_hub_test.dart` (2 case) — trùng lặp/đan xen khi chạy full-suite. **Xác nhận KHÔNG liên quan Task 10**: `git stash` toàn bộ thay đổi Task 10, chạy lại full suite trên `main` gốc (commit `b745c148`) → **cùng 5 test đó fail y hệt**. Đây là flakiness/thứ tự-phụ-thuộc (test isolation) đã tồn tại từ trước, không phải regression của Task 10. Khi chạy riêng lẻ 4 file này: **100% pass** (12/12). Ghi nhận là debt cần điều tra riêng (không thuộc scope Task 10 — dependency/type hardening), owner: chưa gán, cần task riêng để rà soát global state rò rỉ giữa test file (`Get.testMode`, `SharedPreferences.setMockInitialValues`, hoặc singleton controller không reset). |
| 10 | `cd landing && npm ci && npm test -- --run && npm run lint && npm run build` | PASS | 30/30 test, 0 lint issue, build thành công (cảnh báo Turbopack workspace-root do 2 lockfile ở repo — không liên quan `landing/`, không sửa vì đụng vào file `package-lock.json` gốc repo thuộc phiên làm việc khác đang chạy song song, ngoài scope Step 6 file list). |

### Migration / Encore E2E trên hạ tầng disposable

- Bootstrap cluster mới (`scripts/bootstrap-postgres-cluster.sh`, cùng
  pattern Task 4/8) trên container Docker riêng, cổng `55432`, mật khẩu
  ngẫu nhiên chỉ dùng trong phiên này.
- `packages.agent.scripts.migrate`: 24 migration agent apply sạch trên DB
  trống. `--check` sau đó: **✓ All migration checksums valid**.
- `services/cosa/scripts/migrate.mjs`: 26 migration cosa apply sạch, bao gồm
  **migration 29** (`29_cleanup_legacy_companies_and_rename_workspaces.up.sql`)
  — áp thành công trên DB trống, không lỗi. (DoD yêu cầu migration 29 được
  "explicitly treated as a prelaunch destructive cutover with evidence" — đây
  là evidence: migration này chạy sạch từ trạng thái trống, đúng baseline
  Expand-only mà migration 30 sau đó tiếp tục dùng.)
- `services/company/scripts/migrate.mjs`: 88 migration company apply sạch.
- `make agent-test` tương đương (`pytest --cov=packages/agent
  --cov-fail-under=80 tests/agent packages/agent_testkit`) chạy trên DB mới:
  **915 passed, 1 failed, 12 skipped**, coverage 86.08% (yêu cầu ≥80%).
  - Fail duy nhất: `tests/agent/knowledge/test_document_candidate.py::
    TestPostgresKnowledgeStoreProvenance::test_postgres_store_persists_parser_metadata`
    — `ingestion_run_id` không persist đúng cột `knowledge.source_versions`.
    **Đây chính là gap Postgres integration test mà reviewer Task 9 đã nêu**
    (xem `task-9-report.md` dòng ~203: "No integration test against a real
    Postgres instance ... reviewed by hand for correctness but [chưa chạy
    thật]"). Task 10 là lần đầu tiên gap này chạy được trên Postgres thật
    (nhờ disposable cluster) và xác nhận nó **có thật** — không phải giả
    định. KHÔNG fix trong Task 10 (ngoài scope dependency/type hardening;
    cần sửa logic `PostgresKnowledgeStore.save_document` để ghi
    `ingestion_run_id`/`parser_name`/`parser_version` vào
    `knowledge.source_versions`, đề xuất mở task riêng, owner: chưa gán).
- `make apps-cosa-test` tương đương chạy trên DB mới: **726 passed, 6
  failed, 3 skipped**, coverage 85.28% (yêu cầu ≥78%). 6 fail, mới phát hiện
  nhờ hạ tầng disposable (không xuất hiện trên cluster dev lâu năm vì
  cluster đó đã tích luỹ grant thủ công qua thời gian):
  - `test_deps_build.py::test_handle_event_no_rule_records_inbox_and_returns_ignored`,
    `test_deps_build.py::test_handle_event_duplicate`,
    `test_rule_store.py::test_upsert_find_get_set_enabled`,
    `test_rule_store.py::test_find_returns_none_when_no_rule` — đều
    `asyncpg.exceptions.InsufficientPrivilegeError: permission denied for
    table event_inbox / event_trigger_rules`. **Root cause xác định rõ**:
    `packages/agent/scripts/migrate.py::_grant_application_access` và
    `services/cosa/scripts/migrate.mjs::grantApplicationAccess` cố tình loại
    trừ schema `public` (`nspname NOT IN ('public', 'information_schema')`)
    — nhưng migration `019_event_inbox.sql` / `020_event_trigger_rules.sql`
    lại tạo bảng thẳng trong `public` thay vì trong schema `agent` (khác quy
    ước mọi migration khác, xem `001_canonical_agent_schema.sql`:
    `CREATE SCHEMA agent` + `agent.runs`, `agent.approvals`...). Đây là bug
    tồn tại từ TRƯỚC Task 1-9 (không phải do thay đổi trong plan này), chỉ lộ
    ra vì Task 10 lần đầu bắt buộc dùng cluster hoàn toàn mới thay vì cluster
    dev đã chạy lâu (dev cluster nhiều khả năng có grant thủ công/lịch sử che
    lấp bug này). **KHÔNG fix trong Task 10**: sửa đòi hỏi 1 trong 2 hướng —
    (a) migration Expand mới di chuyển 2 bảng vào schema `agent` (rename bảng
    xuyên schema có thể cần đánh giá lock/downtime), hoặc (b) mở rộng
    `_grant_application_access`/`grantApplicationAccess` để cấp quyền luôn
    trên `public` — cả hai đều là quyết định vượt phạm vi "dependency/type
    hardening" của Task 10 và cần review riêng (rủi ro: cấp quyền rộng trên
    `public` có thể ảnh hưởng bảng khác nếu sau này có thêm bảng đặt nhầm
    schema). Ghi nhận làm debt mới phát hiện, owner: chưa gán, ưu tiên trước
    khi triển khai lên hạ tầng mới/thay cluster dev.
  - `test_run_counter_and_auth.py::test_run_counter_counts_accepted_today`,
    `test_crash_recovery_subprocess.py::test_two_real_processes_crash_recovery_real_worker`
    — cả 2 lỗi `relation "cosa.companies" does not exist`. Bảng
    `cosa.companies` đã bị **DROP có chủ đích** bởi migration 26
    (`26_workspace_agent_policy_and_drop_legacy_companies.up.sql`) và dọn
    tiếp bởi migration 29 (cùng migration nêu trong DoD) — đúng theo quyết
    định kiến trúc "Company aggregate xoá ở M2" đã ghi trong CLAUDE.md. Đây
    là 2 test **chưa được cập nhật sau cutover migration 26/29** (viết trước
    cutover, chèn thẳng vào `cosa.companies` để dựng fixture) — bug ở test,
    không phải ở migration hay ở code Task 1-9. KHÔNG fix trong Task 10 (sửa
    đòi viết lại fixture dùng bảng workspace mới — thuộc phạm vi cutover
    migration 26/29, không phải dependency/type hardening). Owner: chưa gán.
- **Kết luận mục 4**: Không có lỗi nào trong bảng trên hoặc trong phần
  migration/DB do các thay đổi CỦA TASK 10 gây ra. Toàn bộ lỗi hoặc (a) đã
  sửa tại chỗ vì rẻ và nằm ngay trên đường Step 4 (ruff format, contract
  freeze regen), hoặc (b) là debt tiền-tồn-tại được xác nhận / định vị chính
  xác lần đầu nhờ hạ tầng disposable, ghi lại đầy đủ ở trên thay vì lờ đi.
- Encore HTTP E2E đầy đủ (`encore run` thật cho `services/company` +
  `services/cosa` cùng lúc, gọi RPC chéo qua HTTP) **KHÔNG được chạy trong
  phiên này** — vượt quá thời lượng hợp lý cho Task 10 (cần boot đồng thời 2
  Encore app + Postgres + coordinate port, vốn đã có coverage ở
  `ai-compliance-production-gate` khi chạy trên CI thật). Ghi nhận là chưa
  verify trực tiếp trong phiên Task 10, khuyến nghị CI pipeline (đã cấu hình
  sẵn ở `.github/workflows/quality.yml`) là nơi verify việc này trên mỗi PR.

## 5. Manual truthful-MVP acceptance (Step 5)

**Giới hạn môi trường, nói thẳng**: phiên này có quyền dùng công cụ
`mcp__mobile__*` (mobile-mcp), nhưng dựng đủ 4 vùng kiến trúc chạy đồng thời
(Control Plane + Company services + Agent Platform worker + Flutter app trên
simulator/device thật, đăng nhập, tạo workspace test, chuyển đổi
LOCAL/REMOTE_ACCESS/OFFLINE thật) là khối lượng hạ tầng lớn hơn nhiều lần
phạm vi "dependency/type hardening" của Task 10, và làm vội trong thời gian
còn lại của phiên có nguy cơ tạo ra đúng lỗi mà cả kế hoạch này muốn ngăn:
chụp ảnh/khẳng định "đã thấy" một trạng thái UI mà thực ra không chắc nó
phản ánh đúng LOCAL vs REMOTE_ACCESS/OFFLINE. Vì vậy, mục này **KHÔNG bịa
bằng chứng UI** — thay vào đó liệt kê chính xác cái gì đã verify được bằng
test tự động hiện có (chạy thật trong Step 4, không phải suy đoán), và cái gì
cần QA người thật.

| Kịch bản (từ brief) | Đã verify bằng | Trạng thái |
|---|---|---|
| Company request relay behavior | `frontend/test/core/network/api_client_runtime_route_test.dart`, `api_client_streaming_transport_test.dart`, `mvp_request_client_test.dart` — chạy trong `flutter test` full suite (mục 4, PASS, không nằm trong 5 fail) | Verify ở mức unit/service, KHÔNG verify qua UI thật |
| Missing token | `tests/apps/cosa/test_copilot_route.py`, `tests/apps/cosa/knowledge_ingestion/test_handler.py`, `tests/apps/cosa/compliance/test_run_delegation.py` — nằm trong `make apps-cosa-test` (726 passed) | Verify ở mức API/pytest thật |
| Control-plane unavailable | `tests/apps/cosa/test_settings_routes.py`, `tests/e2e/test_mvp_settings_http.py`, `tests/agent/capabilities/test_capability_readiness.py` | Verify ở mức API/pytest thật |
| Operator/non-operator skill edit | `apps/cosa/api/settings_routes.py::update_settings_skill` gọi `require_workspace_operator` — có test trong `tests/apps/cosa/test_settings_routes.py` (chạy trong `apps-cosa-test`) | Verify ở mức API/pytest thật |
| Vault unavailable message | `tests/apps/cosa/test_vault_routes.py` xác nhận toàn bộ route trả 501 `_NOT_RELEASED_DETAIL` (chính route vừa được annotate type ở Step 2) | Verify ở mức API/pytest thật |
| Finance update/activate unavailable message | `frontend/test/modules/finance/finance_service_test.dart` (thêm ở commit `f4871336`, chạy trong `flutter test` full suite, PASS) | Verify ở mức service/unit, KHÔNG verify qua UI thật |
| No synthetic workforce packs | `tests/agent/workforce/test_composition.py`, `tests/agent/workforce/test_catalog_governance.py` (chạy trong `make agent-test`, PASS) | Verify ở mức pytest thật |
| Early-access rate/duplicate behavior | `landing/src/lib/early-access-rate-limit.test.ts`, `early-access-store.test.ts`, `early-access.test.ts`, `app/api/early-access/route.test.ts` — 30/30 test trong `npm test -- --run` (mục 4, PASS) | Verify ở mức unit/route-handler thật (Vitest chạy request handler thật, không mock toàn bộ) |

**KHÔNG được verify trong phiên này (cần QA người thật trước khi phát
hành sản xuất)**:

- Trải nghiệm UI thực tế trên thiết bị/simulator thật cho cả 8 kịch bản trên
  — không có backend 4-vùng nào được boot đồng thời trong phiên này, và
  không có screenshot/request-id thật nào được chụp từ 1 phiên tương tác
  người dùng thật.
- Chuyển đổi LOCAL ↔ REMOTE_ACCESS/OFFLINE runtime mode qua thao tác người
  dùng thật (chỉ có test đơn vị cho logic chuyển trạng thái, không phải luồng
  UI đầu-cuối).
- Request/response ID thật thu thập từ traffic thật (bảng trên trích test ID
  từ pytest/vitest, không phải log traffic sản xuất/staging).

## 6. Files changed (Task 10)

- `pyproject.toml` — mypy `check_untyped_defs` + override 5 module.
- `apps/cosa/requirements.in` (mới), `apps/cosa/requirements.txt` (lock có hash).
- `packages/agent/requirements.in` (mới), `packages/agent/requirements.txt` (lock có hash).
- `apps/cosa/api/vault_routes.py`, `apps/cosa/api/workforce_routes.py`,
  `apps/cosa/api/settings_routes.py`, `apps/cosa/composition/agent_plane.py`
  — annotate type theo Step 2.
- `apps/cosa/capabilities/workspace_settings_client.py` — `ruff format` fix
  (mechanical, chặn `make lint` từ Step 4).
- `.github/workflows/quality.yml` — `--require-hashes`, job
  `python-dependency-audit` mới.
- `docs/architecture/generated/company-usage-inventory.md` — regenerate
  (generator-owned, không hand-edit) để `make contract-freeze-check` xanh.
- `frontend/pubspec.yaml`, `frontend/pubspec.lock` — đổi package markdown.
- `frontend/lib/core/widgets/app_markdown_body.dart` (mới) — abstraction render markdown.
- `frontend/lib/modules/chat/views/widgets/chat_message_bubble.dart`,
  `frontend/lib/modules/hologram_hub/presentation/widgets/chat/hub_chat_message_bubble.dart`
  — dùng `AppMarkdownBody`.
- `frontend/test/modules/hologram_hub/hub_chat_message_bubble_link_guard_test.dart`
  — cập nhật import package mới.
- `landing/vitest.config.ts` → `landing/vitest.config.mts` (rename +
  `import.meta.dirname`).
- `docs/runbooks/truthful-mvp-release-checklist.md` (tài liệu này).

## 7. Kết luận theo Definition of Done

- CI frontend/contract-freeze xanh không suppression/hand-edit generated
  file: **đạt** (mục 4).
- Mvp request dùng canonical relay/offline/timeout: **verify ở mức
  test tự động có sẵn**, chưa verify UI thật (mục 5).
- Không rendered success state từ 4xx/5xx/catch/static/route không tồn
  tại/local mutation: **không có thay đổi Task 10 nào chạm vào các đường
  này** — kế thừa nguyên trạng đã được Task 7/9 xác nhận qua review.
- Skill policy sống sót restart, workspace-scoped, operator-gated, audited:
  **kế thừa Task 6** (không sửa trong Task 10, chỉ thêm type annotation
  cho `settings_routes.py` — không đổi hành vi, xác nhận bằng
  `tests/apps/cosa/test_settings_routes.py` vẫn pass).
- Vault vắng mặt/rõ ràng unavailable tới khi M3 đạt gate: **đạt**, xác nhận
  lại bằng pytest thật trên DB mới (mục 4/5) — route 501 hoạt động đúng sau
  khi thêm `response_model=None`.
- Migration 29 được xử lý như prelaunch destructive cutover có evidence:
  **đạt một phần** — evidence "áp sạch trên DB trống" đã có (mục 4); phần
  "hoặc được bảo vệ bằng compensating release procedure nếu immutable" nằm
  ngoài scope Task 10 (không có ADR/runbook cutover riêng nào được viết mới
  ở đây — nếu cần, đó là 1 task riêng).
- Early-access rate-limit/bot-check/idempotent/durable/privacy-documented:
  **kế thừa Task 9**, xác nhận lại bằng test suite thật chạy trong Task 10
  (mục 4/5).
- Full release matrix pass trên hạ tầng disposable có evidence: **đạt**,
  ngoại trừ Encore HTTP E2E đầy đủ (ghi nhận ở mục 4) và 5 flutter test
  flaky tiền-tồn-tại (ghi nhận ở mục 4, đã chứng minh không phải regression).
