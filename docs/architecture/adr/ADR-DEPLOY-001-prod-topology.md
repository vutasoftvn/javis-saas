# ADR-DEPLOY-001: Production deploy topology (Coolify + docker-compose, không K8s cho launch)

## Status
ACCEPTED 2026-08-28 (Lưu ý: ACCEPTED ≠ IMPLEMENTED ≠ WIRED ≠ VERIFIED ≠ PRODUCTION).

Phạm vi: chốt mô hình triển khai production cho 4 unit chạy dài (`cosa-api`,
`cosa-worker`, `services/cosa`, `services/company`) + job migrate + hạ tầng
phụ trợ (`postgres`, `minio`, reverse proxy).

## Context

Hiện trạng (verify bằng code 2026-08-28):
- Dockerfiles đã đủ: `apps/cosa/Dockerfile.api`, `apps/cosa/Dockerfile.worker`,
  `apps/cosa/Dockerfile.ingestion-worker`, `services/Dockerfile` (Node 20 +
  Encore), `services/realtime_agent/Dockerfile`.
- `deploy/central_vps/docker-compose.yaml` chỉ có `postgres`. `api`/`worker`
  hiện deploy qua Coolify GitHub App watch nhánh `main`.
- `deploy/k8s/` chỉ có OpenSandbox (kustomization + deployment + networkpolicy
  + service). Không có manifest cho 4 unit chính. Không có Terraform.
- `make deploy` = `deploy-preflight` → `migrate-all` → `deploy-app`.
- `ADR-LOCAL-FIRST-001` yêu cầu execution plane là local Workspace Runtime
  Node, loopback-only; scheduler payload chỉ mang reference.

Yêu cầu cho launch: đơn giản, VPS-based, RAM thấp, rollback nhanh (đổi image
tag về N-1 — `ADR-CUTOVER-001`), không cần autoscale.

## Decision

**Chọn Coolify + docker-compose (self-host trên VPS) cho launch. K8s để sau.**

1. Artifact deploy production: **`deploy/central_vps/docker-compose.prod.yaml`**
   — mở rộng từ `docker-compose.yaml`, thêm `minio`, `services-cosa`,
   `services-company`, `cosa-api`, `cosa-worker`, `cosa-ingestion-worker`, và
   `migrate` (one-shot, `restart: "no"`, chạy `migrate-all` rồi exit 0).
2. Mỗi service dài hạn: `${VAR:?required}` cho mọi secret (fail-closed khi
   `docker compose config`), `healthcheck`, `restart: unless-stopped`,
   `deploy.resources.limits` (mem/cpu), `logging` json-file + rotation
   (`max-size`, `max-file`).
3. `depends_on`:
   - `migrate` phụ thuộc `postgres` `condition: service_healthy`.
   - Mọi app phụ thuộc `migrate` `condition: service_completed_successfully`
     → app không bao giờ khởi động trước khi schema sẵn sàng.
4. Reverse proxy (Caddy): route `api.<domain>` → `cosa-api:8000`; endpoint
   `/metrics` **chỉ nội bộ** (IP allowlist / basic auth); `/healthz` public.
   Rate limiting + `request_body max_size` đặt ở proxy, không nhúng vào app
   (app chỉ giữ `MaxBodySizeMiddleware` làm defense-in-depth).
5. Encore self-host (`services/cosa`, `services/company`) chạy trong compose
   qua `services/Dockerfile`. Nếu cấu hình Encore self-host (secrets, infra
   config) quá phức tạp khi bring-up staging → fallback: Encore Cloud cho 2
   service TS, chỉ self-host phần Python. Ghi lại lựa chọn cuối trong
   `docs/operations/deployment.md`.
6. Coolify **không** auto-deploy watch nhánh `main` cho production — dùng
   tag/release trigger (tránh deploy khi chưa sẵn sàng).

## Điều kiện chuyển sang K8s (re-open ADR)

Đánh giá lại khi có **≥ 1** điều kiện, kèm số đo thật:
- Cần chạy > 1 replica `cosa-api` sau load test (single VPS không đủ p95).
- Cần rolling deploy zero-downtime mà compose `restart` không đáp ứng SLA.
- Có > 3 VPS node cần điều phối chung (bin-packing thủ công thành gánh nặng).
- Yêu cầu compliance buộc network policy / secret rotation tự động cấp cluster.

Khi re-open: dùng `deploy/k8s/opensandbox/` làm mẫu style; tạo
`deploy/k8s/cosa/` (Deployment + Service + HPA cho `cosa-api`/`services-*`;
Deployment cho `cosa-worker`; `Job` cho migrate; `NetworkPolicy` loopback-only
cho execution plane theo `ADR-LOCAL-FIRST-001`).

## Consequences

- (+) Không thêm control-plane hạ tầng mới; RAM ~250–400MB toàn stack.
- (+) Rollback = đổi image tag + `docker compose up -d` (khớp `ADR-CUTOVER-001`).
- (−) Không autoscale; single point of failure ở VPS → chấp nhận cho launch,
  bù bằng backup + restore rehearsal (Part 2E).
- (−) Encore self-host cần bảo trì thủ công infra config.

## Relates
- `ADR-LOCAL-FIRST-001` — execution plane loopback-only, data residency.
- `ADR-CUTOVER-001` — rollback strategy (image tag N-1).
- `ADR-CONTROLPLANE-001` — vị trí control plane tại `services/cosa` (không đổi).
- Part 2D (`docs/implementation/2026-08-28-tpr-part2d-deploy-infra.md`) —
  Migration Gate G, artifact 4 unit.
