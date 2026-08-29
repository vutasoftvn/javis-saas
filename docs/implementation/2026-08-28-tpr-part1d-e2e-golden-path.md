# Part 1D — Full-stack E2E golden path

**Master:** [`2026-08-28-test-prod-readiness.md`](./2026-08-28-test-prod-readiness.md)
**Phụ thuộc:** Part 0; nên sau 1C (tái dùng compose + Encore trong CI)
**Ước lượng:** 3 ngày
**Nhánh:** `tpr/part1d-e2e-golden-path`

## Mục tiêu

Một suite E2E chạy toàn bộ stack qua docker-compose, thực thi tuần tự **E2E-1..7** (§20 của `COSA_FINAL_INTEGRATION` plan), làm CI gate cho PR vào `main` và làm kịch bản smoke cho staging (Part 1E) + prod (Part 2D).

## Trạng thái hiện tại (verify bằng code)

- Chỉ **E2E-4** (SSE reconnect sau process restart) là test thật: `tests/apps/cosa/test_sse_reconnect_e2e.py` (real uvicorn subprocess, `Last-Event-ID` replay).
- E2E-1..3,5,6,7 chỉ ngầm qua job lẻ (`tenancy-check`, worker test, `knowledge-ingestion-test`, `test_durable_supervisor_workflow.py`), **không có 1 job golden-path tuần tự**.
- `docker-compose.yml` có profile `cosa` (`cosa-api` port 8001, `cosa-worker`), infra: `postgres` (pgvector), `minio`, `livekit`, `opensandbox`. `services/docker-compose.yml` riêng cho Encore services.
- Không có thư mục `tests/e2e/` hay `scripts/e2e/`.

## Thay đổi cụ thể

### 1D.1 Compose profile `e2e`

Trong `docker-compose.yml` thêm profile `e2e` gom: `postgres` (pgvector), `minio`, `services-cosa` (encore run), `services-company` (encore run), `cosa-api`, `cosa-worker`, service `migrate-all` (chạy 3 migration theo thứ tự rồi exit 0). Mọi service `depends_on` migrate hoàn tất + healthcheck.

- Tái dùng `apps/cosa/Dockerfile.api`, `apps/cosa/Dockerfile.worker`, `services/Dockerfile`.
- Env qua `.env.e2e` (không secret thật): DeepSeek dùng `FakeSDKModel` bằng biến `COSA_MODEL_PROVIDER=fake` (thêm nhánh này trong `apps/cosa/composition/model_provider.py` nếu chưa có — chỉ cho test).

### 1D.2 Suite `tests/e2e/`

`tests/e2e/test_golden_path.py` — pytest, chạy tuần tự (dùng `pytest-order` hoặc 1 test function nhiều bước), mỗi bước assert structured state:

| Bước | Kịch bản | Assert |
| --- | --- | --- |
| E2E-1 | Fresh bootstrap | 3 nhóm schema (`agent*`, `cosa`/`control_plane`, `company` 4 sub) apply đủ; `migrate-all` exit 0 |
| E2E-2 | Auth + workspace isolation | User A tạo resource workspace 1; user B (workspace 2) GET → `404` (không `403` — không lộ tồn tại); JWT sai → `401` |
| E2E-3 | Dispatch → worker → result | POST run cho `COSA_OPERATIONS_AGENT_SPEC` → task vào `control_plane.scheduled_tasks` → worker claim → `RunResult` lưu; event stream có `run.started`/`run.completed` |
| E2E-4 | SSE reconnect sau restart | Tái dùng logic `test_sse_reconnect_e2e.py`: SIGKILL api, restart, `Last-Event-ID` → replay không trùng/không thiếu |
| E2E-5 | Policy snapshot tenant filter | `apps/cosa/policies` fetch snapshot từ `services/cosa`; agent workspace 1 không thấy policy workspace 2 |
| E2E-6 | Knowledge ingest → semantic retrieval | Ingest 1 doc qua scheduler `task_type=knowledge_ingestion` → chunk + embed (pgvector) → query semantic trả citation đúng doc, `workspace_id` scoped |
| E2E-7 | Multi-agent coordination | Supervisor spawn 2 child task có dependency → join → parent `completed` chỉ sau cả 2 child; child edge lưu Postgres |

### 1D.3 Runner script

`scripts/e2e/run-golden-path.sh`:
```sh
set -euo pipefail
docker compose --profile e2e up -d --build --wait
trap 'docker compose --profile e2e down -v' EXIT
PYTHONPATH=. pytest tests/e2e -q --junitxml=test-results/e2e.xml "$@"
```
Cho phép chạy đối chiếu môi trường ngoài qua biến `E2E_BASE_URL_*` (staging/prod smoke) — khi set thì skip `docker compose up`.

### 1D.4 CI job `e2e-golden-path`

```yaml
  e2e-golden-path:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' || github.base_ref == 'main'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11', cache: pip }
      - run: pip install -r apps/cosa/requirements.txt pytest pytest-asyncio httpx pyjwt pytest-order
      - run: bash scripts/e2e/run-golden-path.sh
      - uses: actions/upload-artifact@v4
        if: always()
        with: { name: e2e-test-results, path: test-results/e2e.xml, if-no-files-found: error }
```
Trên feature branch: chỉ chạy khi PR target `main` (giữ vòng lặp nhanh). Thêm `workflow_dispatch` để chạy tay.

## Reuse

- `tests/apps/cosa/test_sse_reconnect_e2e.py` (E2E-4).
- `tests/agent/coordination/test_durable_supervisor_workflow.py` (logic E2E-7).
- `apps/cosa/api/test_main.py` — auth override pattern.
- Dockerfiles + `docker-compose.yml` profile `cosa` (mở rộng thành `e2e`).
- `scripts/load-dev-env.sh` pattern cho `.env.e2e`.

## Test / verify

- `bash scripts/e2e/run-golden-path.sh` local (Docker) → 7 bước xanh, teardown sạch (`down -v`).
- CI job `e2e-golden-path` xanh trên PR giả vào `main`.
- Chạy lại 3 lần → không flaky.
- `E2E_BASE_URL_API=https://staging… pytest tests/e2e -k "E2E_2 or E2E_3"` chạy được với target ngoài (dùng cho Part 1E).

## Definition of Done

- [x] Profile `e2e` trong `docker-compose.yml` + `.env.e2e` + `COSA_MODEL_PROVIDER=fake`.
- [x] `tests/e2e/test_golden_path.py` phủ E2E-1..7, assert structured (không parse text — CLAUDE.md #7).
- [x] `scripts/e2e/run-golden-path.sh` chạy local + hỗ trợ target ngoài.
- [x] CI job `e2e-golden-path` xanh, bắt buộc cho merge vào `main`.
- [x] execution-status: E2E-1..7 chuyển sang VERIFIED với tên job `e2e-golden-path`.

## Rủi ro

- Compose stack nặng → CI có thể chậm (10–20 phút); chấp nhận cho gate `main`, không chạy mỗi push feature.
- `encore run` trong container cần Encore CLI trong image `services/Dockerfile` — xác nhận đã có (Dockerfile cài Encore 1.58.2).
- Nếu `COSA_MODEL_PROVIDER=fake` chưa tồn tại → thêm nhánh nhỏ, có test đảm bảo prod vẫn fail-fast khi thiếu `DEEPSEEK_API_KEY`.
