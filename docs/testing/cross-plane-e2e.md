# Cross-Plane E2E Harness — phạm vi phủ & khoảng trống B5

Tài liệu này mô tả dàn E2E Tầng 1 (`tests/e2e/`) chạy 4 vùng kiến trúc THẬT dưới
subprocess, cùng những gì mỗi scenario S1–S4 chứng minh và những gì CHƯA phủ.

## Dàn harness là gì

| Thành phần | Vai trò |
|---|---|
| `tests/e2e/stack/disposable_postgres.py` | Tạo cluster Postgres disposable: 3 DB (`agent_<run_id>`, `cosa_<run_id>`, `workspace_<run_id>`) OWNER `*_migrator`, áp toàn bộ migration, DROP `WITH (FORCE)` khi teardown. Không tái dùng state giữa các lần chạy. |
| `tests/e2e/stack/subprocess_stack.py` | `boot_subprocess_stack()` spawn 4 process THẬT theo chiều phụ thuộc, mỗi bước health-gated trước bước kế: `services/company` (Encore/TS) → `services/cosa` (Encore/TS) → `apps/cosa` API (uvicorn) → `cosa-worker`. `COSA_MODEL_PROVIDER=fake` + worker chạy `FakeSDKModel` (unset `DEEPSEEK_API_KEY`). |
| `real_cosa_stack` (fixture, `tests/e2e/conftest.py`) | Bó `MvpStack` trỏ vào 4 plane. Nếu `E2E_BASE_URL_COMPANY/_COSA/_API` đều set → dùng stack ngoài; ngược lại boot subprocess trên `disposable_cluster`. Thiếu tiền đề (Encore CLI, Postgres admin) → `pytest.fail`, KHÔNG skip, KHÔNG fallback mock. |
| `tests/e2e/seed/` | Seed kit THẬT: `identity` (session + membership qua HTTP `_e2e`), `entitlement` (`cosa.workspace_agent_policy` SQL), `agent_spec` (AgentSpec published). |
| `tests/e2e/scenarios/` | Logic assert S1–S4, dùng lại bởi `tests/e2e/test_cross_plane_smoke.py`. |

Các test cần dàn này mang marker `cross_plane` — job `e2e-golden-path` /
`make e2e-test` chạy `-m "not cross_plane"` để loại chúng ra; chỉ job
`e2e-cross-plane-smoke` chạy chúng.

`psycopg2` chỉ được cài ở job `e2e-cross-plane-smoke`. Mọi `import psycopg2`
trong `tests/e2e/` (trừ `TYPE_CHECKING`) là import CỤC BỘ trong hàm — import
module-scope sẽ làm đỏ collection ở các job không có psycopg2 (marker chỉ deselect
SAU khi module đã import).

## Cách chạy

```bash
# Local: cần Postgres docker `cosa_postgres` + role bootstrap sẵn.
PGPASSWORD=dev-postgres-password PGUSER=postgres PGHOST=127.0.0.1 PGPORT=5432 \
  make e2e-cross-plane-smoke

# hoặc trực tiếp
PGPASSWORD=dev-postgres-password PGUSER=postgres PGHOST=127.0.0.1 PGPORT=5432 \
  PYTHONPATH=. .venv/bin/pytest tests/e2e/test_cross_plane_smoke.py -v -s
```

Tiền đề: `encore` CLI trên PATH, Node (`scripts/migrate.mjs`,
`scripts/mint-worker-service-token.mjs`), Postgres admin reachable với role
`*_app` / `*_migrator` mật khẩu `change-me-*` đã bootstrap
(`scripts/bootstrap-postgres-cluster.sh`).

CI: job **`e2e-cross-plane-smoke`** trong `.github/workflows/quality.yml` —
blocking trên mọi push/PR (không có `if:` guard).

## Mỗi scenario chứng minh gì

### S1 — `auth_tenant_isolation` (đầy đủ)
Đăng ký/đăng nhập THẬT qua `services/company` → 2 workspace độc lập → cô lập tenant
qua wire: member đọc task workspace mình = 200; đọc task của workspace khác bằng
token workspace khác = 404 (không leak cross-tenant); tạo task bind đúng
`workspaceId`. Toàn bộ là HTTP thật, không nhánh dormant.

### S2 — `dispatch_worker_result` (Tier-3 đầy đủ, phần run dormant)
Chứng minh TRỌN chặng điều phối cross-process: `apps/cosa` `POST /agent/conversations`
+ `/messages` → lên lịch task `run` durable ở `control_plane.scheduled_tasks`
(`services/cosa`) → tiến trình `cosa-worker` THẬT poll → claim atomic
(`FOR UPDATE SKIP LOCKED`) → acquire lease → `execute_run_task` (gọi thật sang
control-plane lấy tenant policy snapshot) → persist terminal event vào
`agent_conversation.run_stream_events` → complete task.
**Dormant:** nhánh `_assert_completed_run_facts` (kernel chạy trọn → `agent.runs`,
`agent.run_events`, `agent.runtime_signal_outbox`, projection
`operating.runtime_source_signals` idempotent) chỉ kích hoạt khi B5 được vá; hiện
run kết thúc `run.failed{error:"policy_snapshot_unavailable"}` và test assert đúng
mã lỗi có cấu trúc đó rồi `return`.

### S3 — `capability_governance` (Tier-2: entitlement + biên auth + fail-closed)
- **(A)** `entitlement.grant_entitlement` round-trip cross-plane: hàng ALLOW ghi
  thật vào `cosa.workspace_agent_policy` keyed theo workspace id của
  `services/company`; đọc ngược bằng SQL, assert `decision='ALLOW'` +
  `tool_pattern` + idempotent + auto-seed `cosa.workspaces` / `cosa.users`.
- **(B)** Biên auth route `apps/cosa` `POST /agent/conversations` trước capability
  pipeline: no bearer → 401; token rác → 401; token company hợp lệ +
  `X-Workspace-Id` lạ → 403-or-502 (fail-closed); token + workspace mình → 201
  (positive control).
- **(C)** Governance FAIL CLOSED: `GET services/cosa /platform/auth/me/agent-policy-snapshot`
  với token company → 401 `code=="unauthenticated"` (sau khi `/healthz`==200 làm
  liveness control); một run thật qua worker kết thúc `run.failed` với
  `error=="policy_snapshot_unavailable"` CHÍNH XÁC — kể cả khi đã có hàng ALLOW ở
  (A). Khối kết quả run được NHÁNH theo `terminal_type` (mirror S2), không
  hard-assert thất bại B5: nếu `run.completed` (sau khi B5 được vá) thì assert
  fact THẬT của pipeline (audit ledger `agent.run_events` > 0,
  `agent_governance.invocation_governance_state` > 0), và có `TODO(B5)` cho phần
  assert binding `run_approvals` (`run_id + tool_call_id + checkpoint_ref`) khi
  scenario bổ sung lời gọi `operations_write` HIGH-risk.
- **Dormant:** CapabilityGateway execute đồng bộ + REQUIRE_APPROVAL binding.

### S4 — `outbox_relay` (đầy đủ)
`POST /operations/tasks` (`services/company`) ghi domain event vào
`integration.event_outbox` CÙNG transaction → `POST /events/relay/tick` chạy đồng
bộ: claim, ký `X-COSA-Local-Signature = HMAC-SHA256(payload, COSA_LOCAL_SERVICE_SECRET)`,
POST sang `apps/cosa` `/agent/internal/events` → verify HMAC → INSERT `event_inbox`
(agent DB) với `ON CONFLICT DO NOTHING`. Duplicate delivery KHÔNG tạo hàng thứ
hai. Vòng cross-plane trọn vẹn, không nhánh dormant.

### S7 — `policy_snapshot_tenant` (fail-closed đầy đủ; tenant-scoped `rules` dormant)

`GET services/cosa /platform/auth/me/agent-policy-snapshot` có HAI tầng auth xếp
chồng: (1) Encore gateway `verifyPlatformToken` (`PLATFORM_JWT_SECRET` + `aud="cosa"`
+ `iss="cosa_platform"`), (2) handler gọi `verifyWorkspaceMembership` — forward
nguyên `Authorization` header sang `services/company` (verify bằng `JWT_SECRET`).
Không token seed đơn lẻ nào qua được cả hai (biến thể B5 tại endpoint này).

**S7 chứng minh THẬT hôm nay:**

- `/healthz` == 200 (liveness control — 401/403 bên dưới là quyết định auth thật,
  không phải "service chết").
- Gateway auth gate: no bearer → 401 `code=="unauthenticated"`; bearer rác → 401
  `code=="unauthenticated"`.
- **Fail-closed tại hop membership:** với một cosa platform token HỢP LỆ (qua
  gateway), cả ba workspace id (có grant `operations`, có grant `finance`, không
  grant) → **403 `permission_denied`** — endpoint KHÔNG trả snapshot rỗng ("= allow"),
  không leak tín hiệu nội dung policy khi cross-plane membership check hỏng.

**Đang park (dormant, chờ ADR-COSA-DELEGATION-002):** nhánh `200` — `rules` lọc
đúng theo tenant qua wire (`{"operations.*"}` cho ws A, `{"finance.*"}` cho ws B,
không leo cross-tenant; workspace không membership → 403/404). Hiện với token
company `local_session` gateway reject → 401, S7 assert điều đó rồi `return`.
Nhánh tự kích hoạt khi B5 bridge land — không phải viết lại test. Round-trip
tenant scoping ở tầng SQL (`cosa.workspace_agent_policy WHERE platform_workspace_id`)
đã được S3 (A) phủ.

## Golden path (target ngoài / compose)

`tests/e2e/test_golden_path.py` chạy LẠI đúng thư viện scenario ở trên nhưng với
một stack 4 vùng ĐANG CHẠY SẴN ở ngoài thay vì boot subprocess. Nó KHÔNG mang
marker `cross_plane` (ngược lại với `test_cross_plane_smoke.py`) nên job
`e2e-golden-path` (`-m "not cross_plane"`) nhặt nó; module tự `pytest.skip` nếu
thiếu bất kỳ biến `E2E_BASE_URL_COMPANY` / `_COSA` / `_API` nào (guard hợp lệ —
`scripts/check_mvp_e2e_purity.py` không glob file này).

- **Scenario chạy:** S1 (`auth_tenant_isolation`), S4 (`outbox_relay`), S7
  (`policy_snapshot_tenant`) — cả ba B5-independent.
- **Không có `DisposableCluster`** với target ngoài. `test_golden_path.py` định
  nghĩa `@dataclass ExternalClusterDsns` — bộ giữ DSN tối thiểu có đúng ba thuộc
  tính scenario đọc: `workspace_app_url` ← `WORKSPACE_DATABASE_URL`,
  `agent_app_url` ← `AGENT_DATABASE_URL` (hạ `postgresql+asyncpg://` → libpq),
  `cosa_app_url` ← `COSA_DATABASE_URL`.
- **`scripts/e2e/run-golden-path.sh`** lái nó: nếu `E2E_BASE_URL_*` đã set →
  `pytest tests/e2e -m "not cross_plane"` thẳng vào target ngoài; ngược lại
  `docker compose --profile e2e up --wait` rồi export
  `E2E_BASE_URL_COMPANY=http://127.0.0.1:4000`, `_COSA=http://127.0.0.1:4001`,
  `_API=http://127.0.0.1:8001` (port map trong `docker-compose.yml`:
  services-company→4000, services-cosa→4001, cosa-api host 8001→container 8000)
  + `source .env.e2e` (set -a) đưa ba `*_DATABASE_URL` vào môi trường pytest.
- **CHƯA phủ / B5-blocked:** S2 (`dispatch_worker_result`), S3
  (`capability_governance`) completed-branch, S5 (SSE reconnect), S8 (multi-agent)
  và P4-live (DeepSeek thật) — cần cầu nối delegation token cosa↔company, xem
  [`ADR-COSA-DELEGATION-002`](../architecture/adr/ADR-COSA-DELEGATION-002-agent-run-tenant-token.md).
  S2/S3 fail-closed branch cần `DisposableCluster` scope theo `run_id` (đọc
  `agent.runs` / `agent.run_events`) — bộ DSN dùng chung của stack ngoài không
  cấp được — nên bị bỏ khỏi golden path.

## Cái gì CHƯA phủ và vì sao — bug B5

Danh tính hợp lệ duy nhất qua biên `apps/cosa` là `local_session` (do
`services/company` cấp, để cross-check membership). Worker cần chính token đó để
gọi `GET services/cosa /platform/auth/me/agent-policy-snapshot`, nhưng gateway
`services/cosa` (`verifyPlatformToken`, `PLATFORM_JWT_SECRET` + `aud="cosa"`) TỪ
CHỐI token local session → `CosaTenantPolicyError` → run `run.failed{error:"policy_snapshot_unavailable"}`
**TRƯỚC** khi kernel chạy.

Hệ quả: các phần sau CHƯA được dàn này exercise:

- agent kernel (một agent run chạy trọn),
- `CapabilityGateway` execute (capability pipeline `operations_read/write` →
  `CompanyServiceClient` HTTP → `services/company` → audit),
- governance approval binding (`run_id + tool_call_id + checkpoint_ref`),
- projection run → runtime signal → `operating.runtime_source_signals`.

Khắc phục cần một cầu nối identity/delegation cosa ↔ company (mint được platform
token `aud="cosa"` cho identity gốc local session), theo dõi riêng. Khi vá xong,
nhánh dormant ở S2/S3/S7 tự kích hoạt — không phải viết lại test.

**Điều tra + phương án khắc phục:**
[`ADR-COSA-DELEGATION-002`](../architecture/adr/ADR-COSA-DELEGATION-002-agent-run-tenant-token.md)
(PROPOSED) — mô hình 3 secret / 3 chiều tin cậy, mô tả chính xác điểm hỏng, 3
phương án (A: cosa platform token + workspace liên kết; B: secret thứ tư
`COSA_CONTROL_DELEGATION_SECRET` cho hop policy-snapshot — khuyến nghị; C:
`services/cosa` nhận local_session token cho đúng route này), và những gì mở khoá.
