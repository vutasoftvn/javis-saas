# COSA Audit Remediation — Design

**Date:** 2026-08-29
**Source audit:** `docs/architecture/reports/2026-08-29-codebase-audit-recommendations.md`
**Baseline:** `main` @ `375b8c85` (merge of `docs/cosa-one-person-enterprise-plan` @ `0cbab94c`)
**Working location:** worktree `.claude/worktrees/cosa-workspace-canonical` (checkout of `main`)
**Git flow:** commit từng phase trực tiếp lên `main`, một commit/phase, chỉ merge khi test của phase đó + smoke test đường production bị ảnh hưởng đều xanh. Không push trừ khi được yêu cầu.

## Mục tiêu

Khôi phục tính toàn vẹn của đường thực thi production (không thêm tính năng), rồi
làm xanh lại quality gate, rồi hardening. Theo đúng "Recommended delivery
sequence" của audit: P0 code → P0 verification → P1 quality → P2 hardening.

Mỗi finding trong audit đã được đối chiếu với code thật tại baseline và xác nhận
là lỗi thực tế, không phải chỉ là quan ngại kiểu dáng.

## Phân rã — 4 phase

### Phase 1 — P0 production-path restoration (chỉ code)

#### 1a. Một interface registry duy nhất (audit P0 #1)

**Hiện trạng:** `apps/cosa/worker/copilot_run.py` (dòng 104, 109, 116, 167) và
`apps/cosa/worker/autopilot_run.py` gọi `plane.capability_registry.get_handler(...)`.
`packages/agent_core/capabilities/registry.py` chỉ có `get(capability_id) ->
CapabilityRegistration | None`. Worker cũng gọi
`plane.spec_registry.get_agent_spec(id)` trong khi
`packages/agent_core/registry/repository.py :: SpecRegistryRepository` chỉ có
`get(spec_kind, spec_id, version) -> PublishedSpecRecord | None`. Cả hai lời gọi
đều nằm trong `try/except Exception: pass` nên lỗi biến thành run failed âm thầm.

**Quyết định:**

1. Thêm phương thức tiện lợi có chủ đích vào `CapabilityRegistry`:
   `get_handler(capability_id: str) -> CapabilityHandler | None` — trả về
   `registration.handler` hoặc `None`. Giữ nguyên hình dạng 4 call site trong
   worker. `get()` vẫn là API chính, `get_handler()` chỉ là đường tắt đã đặt tên.
2. Thêm resolver có kiểu cho agent spec: một hàm
   `resolve_agent_spec(spec_registry, spec_id, *, version) -> AgentSpec | None`
   (đặt tại `apps/cosa/agents/` cạnh `specs.py`) gọi
   `spec_registry.get("agent", spec_id, version)` rồi dựng lại `AgentSpec` từ
   `record.content`. Worker dùng resolver này thay cho `get_agent_spec`. Nếu
   record không có → fallback về hằng số module `COSA_CUSTOMER_SUPPORT_AGENT_SPEC`
   (đã là default hiện tại) nhưng ghi log ở mức warning với reason code.
3. Thay `except Exception: pass` bằng xử lý lỗi tường minh: bắt lỗi lookup
   capability/spec, emit `run.failed` với structured reason code
   (`capability_not_registered`, `agent_spec_unresolved`), không dựa vào `except`
   cuối làm đường chẩn đoán chính.

**File chạm:** `packages/agent_core/capabilities/registry.py`,
`apps/cosa/agents/` (resolver mới), `apps/cosa/worker/copilot_run.py`,
`apps/cosa/worker/autopilot_run.py`.

#### 1b. Event relay wire-compatible HMAC theo raw bytes (audit P0 #2)

**Hiện trạng:** `services/company/events/outbox-relay.service.ts:24` ký
`JSON.stringify(row.envelope)`, rồi `body: JSON.stringify(body)` ở dòng 48 (serialize
lần hai). `apps/cosa/events/local_auth.py` ký `json.dumps(dict)`. Intake
`apps/cosa/api/event_intake_routes.py:19` làm `await request.json()` rồi
`handle_event(deps, body, sig)` — verify chạy trên dict đã parse, không phải bytes
gốc. Payload tiếng Việt tạo digest khác nhau giữa Node và Python.

**Quyết định:**

1. `local_auth.py`: `LocalServiceAuth.sign(raw_body: bytes) -> str` và
   `verify(signature: str, raw_body: bytes) -> bool` — ký/verify trên đúng bytes,
   bỏ `json.dumps`. Cập nhật mọi caller nội bộ (`events/router.py`,
   `events/deps.py`, test) cho khớp chữ ký mới.
2. `event_intake_routes.py`: đọc `raw = await request.body()`, verify HMAC theo
   `raw`, rồi mới `json.loads(raw)` để lấy dict truyền vào `handle_event`.
   `handle_event` nhận thêm tham số `raw_body: bytes` hoặc nhận `parsed` +
   `raw_body` — chọn: đổi `handle_event(deps, raw_body: bytes, signature)` và tự
   parse bên trong, để chỉ có một chỗ quyết định bytes-vs-dict.
3. `outbox-relay.service.ts`: tạo `const payload = JSON.stringify(row.envelope)`
   một lần, ký `payload`, và gửi **chính** `payload` đó làm request body
   (`body: payload`), không `JSON.stringify` lần nữa. Header giữ
   `content-type: application/json` + `x-cosa-local-signature`.
4. Bỏ fallback `"dev-secret"` và `os.environ.get(..., "")`. Xem 1c cho fail-closed.

**File chạm:** `services/company/events/outbox-relay.service.ts`,
`apps/cosa/api/event_intake_routes.py`, `apps/cosa/events/local_auth.py`,
`apps/cosa/events/router.py`, `apps/cosa/events/deps.py`.

#### 1c. Fail-closed secrets + startup validation (audit P0 #2.3, #3.3)

**Quyết định:**

1. Module chung `apps/cosa/config/service_identity.py` (hoặc mở rộng module config
   sẵn có nếu tìm thấy) expose:
   - `require_local_service_secret(env: str) -> str` — raise nếu thiếu / độ dài <
     32 / bằng giá trị dev (`dev-secret`, `local-dev-service-token`,
     `local-dev-...`) khi `env` ∈ {staging, production}.
   - `require_service_token(name, env)`, `require_internal_url(name, env)` tương tự.
2. Gọi các hàm này ở process startup của **cả** API (`apps/cosa/api/app.py`
   lifespan) và Worker entrypoint — fail ngay khi khởi động, không đợi request đầu.
3. `dev` / `test` env vẫn cho phép giá trị mặc định để không phá DX local.
4. Phía TS: `outbox-relay.service.ts` + `copilot-cosa-client.ts` +
   `copilot_routes.py` — khi `NODE_ENV`/`ENV` là production mà secret/token vắng
   hoặc bằng giá trị dev → throw ở module init.

**File chạm:** `apps/cosa/config/` (module mới/mở rộng), `apps/cosa/api/app.py`,
worker entrypoint, `apps/cosa/api/copilot_routes.py`, `apps/cosa/events/deps.py`,
`services/company/events/outbox-relay.service.ts`,
`services/company/commercial/services/customer-engagement/copilot-cosa-client.ts`.

#### 1d. Container wiring + internal-host allowlist (audit P0 #3)

**Hiện trạng:** `deploy/central_vps/docker-compose.prod.yaml` chỉ inject
`COMPANY_SERVICE_URL` cho `cosa-api`. Company mặc định Copilot →
`http://127.0.0.1:8000` (trỏ về chính nó). Relay mặc định
`http://127.0.0.1:8081`. `outbox-relay.service.ts:4`
`LOCAL_HOSTS = {"127.0.0.1","localhost","::1"}` — guard loại bỏ tên DNS Docker
như `cosa-api`. Worker callback mặc định `http://127.0.0.1:4000`.

**Quyết định:**

1. `docker-compose.prod.yaml` — inject đủ:
   - `services-company`: `COSA_INTERNAL_URL=http://cosa-api:8000`,
     `COSA_AGENTOS_INTAKE_URL=http://cosa-api:8000` (intake route sống trong
     cosa-api), `COSA_LOCAL_SERVICE_SECRET`, `COSA_SERVICE_TOKEN`,
     `COSA_WORKER_SERVICE_TOKEN`.
   - `cosa-api`: `COSA_LOCAL_SERVICE_SECRET`, `COSA_SERVICE_TOKEN`,
     `COSA_WORKER_SERVICE_TOKEN`.
   - `cosa-worker`: `COMPANY_SERVICE_URL=http://services-company:4000`,
     `COSA_SERVICE_TOKEN`.
   Tất cả lấy từ `${VAR}` (không giá trị mặc định trong file compose) → thiếu là
   compose fail.
2. Thay hard-check `LOCAL_HOSTS` bằng allowlist cấu hình được:
   `COSA_INTERNAL_HOST_ALLOWLIST` (CSV, ví dụ
   `cosa-api,services-company,127.0.0.1,localhost`). Guard so khớp hostname của
   URL đích với allowlist; ngoài allowlist → reject. Mặc định dev giữ
   `127.0.0.1,localhost,::1`.
3. `.env.example` / `deploy/central_vps/` doc: liệt kê biến bắt buộc mới.

**File chạm:** `deploy/central_vps/docker-compose.prod.yaml`,
`deploy/central_vps/*.env*` / README deploy,
`services/company/events/outbox-relay.service.ts`,
`services/company/commercial/services/customer-engagement/copilot-cosa-client.ts`,
`apps/cosa/worker/copilot_run.py` (callback URL đọc từ `COMPANY_SERVICE_URL`).

### Phase 2 — P0 verification

1. **Cross-language HMAC contract test.** Test mới chạy được trong CI: dựng
   payload cố định (Unicode tiếng Việt, object lồng nhau, thứ tự key đảo), ký
   bằng logic TS thật (gọi qua `node -e` hoặc port sang test fixture chia sẻ),
   verify bằng `LocalServiceAuth` Python thật — assert khớp. Thêm case: tamper 1
   byte → reject; thiếu secret → reject; duplicate delivery (cùng event_id) →
   idempotent, không schedule 2 run.
   File: `tests/apps/cosa/test_local_event_intake.py` +
   `services/company/events/tests/outbox-relay.test.ts` (share vector qua file
   JSON trong `tests/fixtures/`).
2. **Non-mocked Copilot vertical test.** Schedule một Copilot run thật qua worker
   path, resolve đủ 3 read capability (`engagement.thread.read`,
   `commercial.customer_360.read`, `knowledge.profile.read`) với handler thật
   (in-memory fixture, không mock registry), tạo draft artifact
   (`engagement.message.draft`), assert payload callback về Company. Đặt tại
   `tests/apps/cosa/worker/`.
3. **Compose-level 4-leg smoke test.** Script (bash/pytest) dựng compose (hoặc
   subset: company + cosa-api + worker + postgres), bắn một outbox event, chờ:
   Company → intake → scheduler → worker → Company callback. Assert callback nhận
   được trong timeout. Negative: sai signature → 401; thiếu secret → service
   không start. Đặt tại `deploy/central_vps/smoke/` + Make target
   `smoke-event-pipeline`.

### Phase 3 — P1 engineering reliability

1. **Quality gate xanh (audit P1 #4).**
   - `make lint-fix` (ruff --fix + format) cho 37 lỗi tự sửa được; xử lý tay ~9
     lỗi còn lại. Mục tiêu: `make lint` exit 0.
   - `make typecheck-py`: sửa 21 mypy error / 7 file (capability gateway,
     observability exporter construction, eval cases, worker registry calls — các
     call ở 1a sẽ tự khớp kiểu sau khi có `get_handler`/resolver).
   - MCP conformance test: cấp `InvocationContext` có principal + workspace trong
     caller/test; **không** hạ risk của MCP tool từ `MEDIUM`. Assert: thiếu
     context → không có side effect (fail-closed tenancy).
   - Flutter: chuyển `withOpacity` → `withValues`, null-aware collection style —
     trước lần nâng SDK kế tiếp. `flutter analyze` sạch.
   - Cập nhật CI gate nếu cần để phản ánh trạng thái xanh.
2. **Local test tái lập được (audit P1 #5).**
   - `services-test`: thêm bước tiền điều kiện migration vào DB test cô lập
     (không dựa vào state DB local của dev). Hoặc thêm target
     `services-test-fresh` tạo DB dùng-một-lần (create → migrate → test → drop).
   - `realtime-agent-test`: chạy `services/realtime_agent/.venv/bin/python` khi
     có; nếu không, tạo/cài venv riêng cho component một cách nhất quán.
   - `verify` target: mirror thứ tự dependency + migration của CI sát nhất có thể.
3. **Clock tường minh cho evaluator (audit P1 #6).**
   `services/company/commercial/services/customer-engagement/automation/evaluator.ts:35`
   đang dùng `new Date(Date.now() + 1000)` — kích hoạt rule sớm 1 giây, boundary
   không xác định. Inject `Clock` interface (hoặc tham số optional `now: Date`)
   vào evaluator; production dùng clock thật, test dùng instant cố định. Bỏ
   `+ 1000`. Cập nhật test hiện có để truyền `now` tường minh.

### Phase 4 — P2 hardening

1. **Nguồn tài liệu sự thật duy nhất (audit P2 #7).**
   - Chọn `docs/architecture/plans/2026-08-29-cosa-workspace-canonical-master-plan.md`
     làm index canonical; thư mục `2026-08-29-cosa-workspace-canonical/M0..M7`
     làm chi tiết.
   - Cập nhật `CLAUDE.md` "Nguồn sự thật kiến trúc" + `README` + doc vận hành để
     trỏ vào index này thay vì 4 file đã mất
     (`COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md`,
     `COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md`,
     `COSA_CANONICAL_MASTER_ARCHITECTURE_AND_IMPLEMENTATION_GUIDE_2026-08-23.md`,
     `COSA_AGENT_PLATFORM_PROMOTION_IMPLEMENTATION_PLAN_2026-08-23.md`).
   - Đưa vào tài liệu bộ từ vựng 5 trục trạng thái: accepted decision /
     implementation complete / wired to consumers / verified in CI-staging /
     production verified.
   - **Không** tự khôi phục doc đã xoá; ghi chú rõ chúng là evidence lịch sử.
2. **Giảm kích thước module churn cao (audit P2 #8) — chỉ sau khi Phase 1-2 xanh.**
   - Tách route group khỏi `apps/cosa/api/routes.py` (1347 dòng) thành các router
     con theo domain, giữ `create_*_router()` contract ổn định.
   - Service adapter tường minh quanh worker execution path
     (`copilot_run.py` / `autopilot_run.py`).
   - Tách view/form Flutter rời khỏi widget strategy/marketing lớn (>1300 dòng:
     `marketing_forms.dart`, `project_funding_tab.dart`,
     `twelve_week_year_view.dart`).
   - Giữ public contract ổn định; chỉ refactor sau khi vertical path có test phủ.
3. **Vệ sinh dependency (audit P2 #9).**
   - Thay `flutter_markdown: ^0.7.6` (discontinued) bằng `flutter_markdown_plus`
     (community fork drop-in). Migration test-compat: build + `flutter analyze` +
     smoke render mọi call site `MarkdownBody`/`Markdown`.
   - Lên lịch nâng các dependency bị ràng buộc còn lại theo batch nhỏ, review
     riêng từng batch (ngoài phạm vi phase này — chỉ ghi danh sách).

## Kiểm thử — nguyên tắc

- Mỗi thay đổi hành vi có test tương ứng; chạy test trước khi báo "xong" (CLAUDE.md #11).
- Test durability phải qua process thật (CLAUDE.md #6) — smoke test Phase 2 dùng
  container thật, không tạo instance thứ hai trong cùng process.
- Trạng thái structured, không suy diễn từ text (CLAUDE.md #7) — reason code ở 1a.
- Không hạ ngưỡng an toàn để test pass (MCP risk giữ MEDIUM).

## Thứ tự merge

Mỗi phase = 1 commit lên `main`, chỉ commit khi:
- Test nhắm tới của phase đó xanh, **và**
- Smoke test đường production bị ảnh hưởng xanh (từ Phase 2 trở đi).

Phase 1 không tự merge nếu Phase 2 smoke chưa dựng được — Phase 1 + 2 có thể gộp
review nếu cần, nhưng vẫn tách commit.

## Ngoài phạm vi

- Thêm tính năng mới cho Agent Platform.
- Refactor không phục vụ finding trong audit.
- Nâng cấp hàng loạt dependency Flutter (chỉ thay `flutter_markdown`).
- Push lên remote (chỉ khi được yêu cầu).
