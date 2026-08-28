# Part 2D — Deploy infra prod + Migration Gate G

**Master:** [`2026-08-28-test-prod-readiness.md`](./2026-08-28-test-prod-readiness.md)
**Phụ thuộc:** 2A (rollback strategy), 2B (health/metrics), 1E (staging)
**Ước lượng:** 2–3 ngày
**Nhánh:** `tpr/part2d-deploy-infra`

## Mục tiêu

Chốt mô hình deploy prod (K8s vs Coolify+compose), hoàn thiện artifact cho **cả 4 unit** (cosa-api, cosa-worker, services/cosa, services/company) + job migrate, và đóng **Migration Gate G** (chạy `migrate-all` qua đúng đường prod).

## Trạng thái hiện tại (verify bằng code)

- Dockerfiles đủ: `apps/cosa/Dockerfile.api`, `Dockerfile.worker`, `Dockerfile.ingestion-worker`, `services/Dockerfile` (Node 20 + Encore 1.58.2), `services/realtime_agent/Dockerfile`.
- `deploy/central_vps/docker-compose.yaml`: **chỉ Postgres + Caddy**; api/worker deploy qua Coolify GitHub App watch `main`.
- `deploy/k8s/`: **chỉ OpenSandbox** (kustomization + deployment + networkpolicy + service). Không có manifest cho 4 unit chính. Không có Terraform.
- `deploy/central_vps/README.md` còn nhắc Alembic (lỗi thời — migration nay qua `baseline_v1` + `migrate.mjs`).
- `make deploy` = preflight → migrate-all → deploy-app (build + restart `cosa-api`/`cosa-worker` qua docker-compose, chờ healthz).
- `services/cosa/encore.app`, `services/company/encore.app` — deploy được qua Encore Cloud hoặc self-host.
- Migration Gate G (`migrations.md`): chưa verify chạy qua đường prod.

## Thay đổi cụ thể

### 2D.1 Quyết định (ADR)

`docs/architecture/adr/ADR-DEPLOY-001-prod-topology.md`. Khuyến nghị **Coolify + docker-compose** (đã dùng, VPS-based, local-first phù hợp `ADR-LOCAL-FIRST-001`), K8s để sau nếu cần scale. ADR chốt + lý do + điều kiện chuyển sang K8s.

### 2D.2 Nếu chọn Coolify+compose (khuyến nghị)

`deploy/central_vps/docker-compose.prod.yaml` (mở rộng từ file hiện tại):
- Services: `postgres` (đã có), `minio`, `services-cosa`, `services-company`, `cosa-api`, `cosa-worker`, `cosa-ingestion-worker`, `migrate` (one-shot, `restart: no`, chạy `migrate-all` rồi exit).
- Mỗi service: `${VAR:?required}` cho secret (Part 1E), `healthcheck`, `restart: unless-stopped`, `deploy.resources.limits` (mem/cpu), `logging` driver + rotation (`max-size`, `max-file`).
- `depends_on` với `condition: service_completed_successfully` cho `migrate`, `service_healthy` cho DB.
- Caddyfile: route `api.<domain>` → `cosa-api`, `/metrics` chỉ nội bộ (basic auth hoặc IP allowlist), health public.

### 2D.3 Nếu chọn K8s (thay thế)

`deploy/k8s/cosa/`: Deployment + Service + HPA cho `cosa-api`, `services-cosa`, `services-company`; Deployment cho `cosa-worker` (no Service, hoặc chỉ health port); `Job` cho migrate (initContainer hoặc pre-deploy hook); `ConfigMap` + `Secret` (external-secrets nếu có); `NetworkPolicy` (execution plane loopback-only theo `ADR-LOCAL-FIRST-001`); readiness/liveness probe trỏ `/healthz` `/ready` `/live`.

### 2D.4 Migration Gate G

- `docs/operations/migrations.md`: mục "Gate G — prod-path run".
- Trên staging (giống prod nhất): chạy `migrate-all` qua đúng cơ chế prod (`migrate` service của compose.prod hoặc K8s Job), không phải `make` local. Verify: exit 0, `schema-fingerprint --check` khớp golden, app khởi động `/ready` 200.
- Ghi log run + ngày + commit vào `docs/operations/migration-gate-g-<date>.md`.

### 2D.5 Dọn tài liệu deploy

- Cập nhật `deploy/central_vps/README.md` (bỏ Alembic, trỏ `migrate.mjs` + `baseline_v1`).
- `DEPLOYMENT.md` + `docs/operations/deployment.md`: đồng bộ với topology chốt ở ADR.

## Reuse

- Dockerfiles hiện có (không viết lại).
- `make deploy` / `deploy-preflight` / `deploy-app` — điều chỉnh để trỏ `compose.prod.yaml`.
- `deploy/k8s/opensandbox/` làm mẫu style manifest nếu chọn K8s.
- `scripts/schema-fingerprint.mjs` (Part 1F) cho Gate G verify.
- `apps/cosa/api` `/healthz`, worker `/ready` (Part 1E).

## Test / verify

- `docker compose -f deploy/central_vps/docker-compose.prod.yaml config` hợp lệ + fail khi thiếu biến.
- Trên staging: deploy full 4 unit qua compose.prod (hoặc K8s), 4 health endpoint 200.
- Gate G: `migrate-all` qua đường prod trên staging → exit 0 + fingerprint khớp; ghi doc.
- `make deploy` (staging target) chạy trọn: preflight → migrate → deploy → golden-path smoke xanh.
- Kill `cosa-worker` container → `restart: unless-stopped` đưa lại; task đang chạy được sweeper reclaim (nối Part 1C/2E).

## Definition of Done

- [ ] `ADR-DEPLOY-001` chốt topology.
- [ ] Artifact deploy đủ 4 unit + migrate job, fail-closed, healthcheck, resource limit, log rotation.
- [ ] Gate G: `migrate-all` chạy qua đường prod trên staging, verified + documented.
- [ ] `deploy/central_vps/README.md`, `DEPLOYMENT.md`, `docs/operations/deployment.md` đồng bộ, hết tham chiếu Alembic.
- [ ] `make deploy` staging chạy trọn vòng + golden-path smoke xanh.

## Rủi ro

- Encore self-host trong compose cần cấu hình đúng (secrets, infra config) — nếu phức tạp, cân nhắc Encore Cloud cho 2 service TS và chỉ self-host Python.
- Resource limit đặt sai → OOM kill worker giữa run; đo baseline trên staging trước khi chốt số.
- Coolify auto-deploy watch `main` có thể deploy khi chưa sẵn sàng → dùng tag/release trigger, không watch nhánh trực tiếp.
