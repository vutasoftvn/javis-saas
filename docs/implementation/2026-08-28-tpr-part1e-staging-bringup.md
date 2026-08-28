# Part 1E — Dựng staging

**Master:** [`2026-08-28-test-prod-readiness.md`](./2026-08-28-test-prod-readiness.md)
**Phụ thuộc:** Part 1D (golden-path để smoke); sau khi nhánh merge vào `main`
**Ước lượng:** 2–3 ngày
**Nhánh:** `tpr/part1e-staging-bringup`

## Mục tiêu

Có một môi trường **staging** chạy toàn bộ stack (2 Encore service + COSA api + worker + infra), với health/readiness đầy đủ, compose fail-closed, image pin, và golden-path smoke chạy được đối chiếu staging.

## Trạng thái hiện tại (verify bằng code)

- `apps/cosa/api` có `/healthz` (uvicorn, 200 khi DB OK). `services/company` + `services/cosa` có `/healthz` (`{app,status,version}`). **Worker không có endpoint health nào** — chỉ log.
- `DEPLOYMENT.md`: `brain-api` có `/ready` (check DB, object storage, migration, worker heartbeat) + `/live` — nhưng đó là legacy path.
- `deploy/central_vps/docker-compose.yaml`: chỉ Postgres (5434:5432) + Caddy; api/worker deploy qua Coolify. Không có `${VAR:?required}`.
- `docker-compose.yml` profile `cosa`: chưa fail-closed; `minio`, `livekit`, `opensandbox` dùng tag lỏng (`:latest` hoặc không pin).
- Đã có `make deploy-preflight` (verify env/connectivity/backup/checksum) và `make deploy` (preflight → migrate-all → deploy-app).

## Thay đổi cụ thể

### 1E.1 Worker health/readiness endpoint

`apps/cosa/worker/health.py` (mới) — HTTP server nhẹ (aiohttp hoặc `uvicorn` với app tối giản) chạy song song loop chính trên port `COSA_WORKER_HEALTH_PORT` (default 8090):

- `GET /live` → 200 nếu process còn sống.
- `GET /ready` → 200 nếu: (a) scheduler client reachable (ping control-plane), (b) lease store reachable, (c) `time.monotonic() - last_poll_ts < poll_interval * 5`. Ngược lại 503 với body `{status:"error", checks:{...}}` — **không** kèm DSN/secret.
- Wire vào `apps/cosa/worker/main.py`: cập nhật `last_poll_ts` mỗi vòng loop; start/stop health server trong cùng lifecycle.

Test: `tests/apps/cosa/worker/test_health.py` — `/ready` 503 khi chưa poll lần nào, 200 sau vòng poll đầu, 503 khi giả lập scheduler down.

### 1E.2 Compose fail-closed

- `deploy/central_vps/docker-compose.yaml` + profile `cosa` của `docker-compose.yml`: mọi biến secret/DSN → `${VAR:?VAR is required}` (Postgres URL, `PLATFORM_JWT_SECRET`, `WORKER_SERVICE_JWT_SECRET`, `DEEPSEEK_API_KEY`, MinIO keys, `COSA_ALLOWED_ORIGINS`).
- Thêm `healthcheck:` cho `cosa-api` (`/healthz`), `cosa-worker` (`/live`), `services-*` (`/healthz`).
- `restart: unless-stopped` cho tất cả long-running service.

### 1E.3 Pin image tag

Thay `:latest` → version cụ thể + ghi digest comment:
- `minio/minio:RELEASE.<date>`
- `livekit/livekit-server:v<x.y.z>`
- OpenSandbox image → tag cụ thể (cả trong `deploy/k8s/opensandbox/`)
- `pgvector/pgvector:pg16` (đã pin — giữ)

### 1E.4 Staging environment

- Tạo project Coolify "cosa-staging" (hoặc namespace compose riêng trên central_vps) với DB staging **tách biệt** DB dev/prod.
- `.env.staging.example` (không giá trị thật) liệt kê đủ biến; secret thật đặt trong Coolify secrets.
- Chạy `make deploy-preflight` trỏ staging → pass.
- `migrate-all` lên DB staging.
- `E2E_BASE_URL_API=<staging> ... bash scripts/e2e/run-golden-path.sh --external` (chế độ target ngoài từ Part 1D) → E2E-2,3,5,6 xanh (E2E-1/4/7 tuỳ khả năng restart process trên staging).
- Lưu kết quả smoke + ngày + commit vào `docs/operations/staging-smoke-<date>.md`.

## Reuse

- `/healthz` handler pattern của `services/company/services/health.service.ts`, `apps/cosa/api`.
- `make deploy-preflight`, `make deploy`, `make migrate-all`.
- `scripts/load-dev-env.sh` → tạo `scripts/load-staging-env.sh` tương tự.
- Golden-path external mode (Part 1D §1D.3).
- `deploy/central_vps/README.md` (cập nhật phần Alembic lỗi thời → baseline_v1).

## Test / verify

- `docker compose --profile cosa config` fail khi thiếu biến bắt buộc (chứng minh fail-closed).
- `curl staging/healthz` (3 service) → 200, body không chứa DSN/secret.
- `curl staging-worker:8090/ready` → 200 khi worker đang poll.
- Golden-path external smoke: E2E-2/3/5/6 xanh trên staging.
- `docker image inspect` xác nhận tag pin, không `latest`.

## Definition of Done

- [ ] Worker `/live` + `/ready` implemented + test.
- [ ] Compose fail-closed (`${VAR:?}`) + healthcheck + restart policy cho central_vps và profile `cosa`.
- [ ] Mọi image pin version (không `latest`).
- [ ] Staging env đứng vững; `deploy-preflight` pass; `migrate-all` chạy; golden-path smoke xanh.
- [ ] `docs/operations/staging-smoke-<date>.md` + cập nhật `deploy/central_vps/README.md`.

## Rủi ro

- Coolify auto-deploy watch `main` → cần cấu hình project staging watch nhánh/tag riêng, tránh đè prod.
- Worker health server thêm 1 socket → đảm bảo shutdown sạch khi nhận SIGTERM (dùng chung cancel scope với loop).
- DB staging phải hoàn toàn tách — không trỏ nhầm DB dev/shared (CLAUDE.md non-goal: không destructive test trên DB shared).
