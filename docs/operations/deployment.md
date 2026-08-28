# Vận hành: Deployment

## Topology: Coolify + docker-compose (ADR-DEPLOY-001, chốt 2026-08-28)

Production chạy **`deploy/central_vps/docker-compose.prod.yaml`** trên VPS,
điều phối qua Coolify (release/tag trigger, KHÔNG watch nhánh `main` trực
tiếp). K8s để sau — điều kiện re-open ghi trong ADR-DEPLOY-001.

## Trạng thái verify

| Trục | Trạng thái |
|---|---|
| Artifact compose 4 unit + migrate one-shot | ✓ có (`docker-compose.prod.yaml`, `Dockerfile.migrate`, `run-migrations.sh`) — `docker compose config` fail-closed khi thiếu biến |
| Deploy thật lên staging/prod | ( ) CHƯA — cần staging bring-up (Part 1E) + quyền hạ tầng |
| Migration Gate G (prod-path run) | ( ) CHƯA chạy — thủ tục sẵn trong `migrations.md` |
| Resource limits (mem/cpu) | đặt theo ước lượng — PHẢI đo baseline trên staging trước khi chốt số |

## 4 unit cần deploy

1. **`services/company`** (Encore/TS) — container `services/Dockerfile`, port 4000. Encore self-host trong compose; fallback Encore Cloud nếu infra config phức tạp (ADR-DEPLOY-001 §5).
2. **`services/cosa`** (Encore/TS) — port 4001, có `control_plane` schema + CronJob sweeper (`control-plane.cron.ts`). Deploy TRƯỚC `apps/cosa` phiên bản dùng client mới.
3. **`apps/cosa` API** (Python) — `apps/cosa/Dockerfile.api`, port 8000. Cần `AGENT_CORE_DATABASE_URL` + `DEEPSEEK_API_KEY` + `PLATFORM_JWT_SECRET` + `CORS_ORIGINS` (no-silent-fallback — thiếu → `RuntimeError`/guard raise lúc start).
4. **`apps/cosa` worker** (Python) — `apps/cosa/Dockerfile.worker`, không mở HTTP. `restart: unless-stopped` đưa lại khi crash; task đang chạy được sweeper cron reclaim (Part 2E).

`cosa-ingestion-worker`: profile `ingestion`, TẮT mặc định trong compose —
Dockerfile ghi rõ compose không cấp read-only rootfs + egress-deny mà
readiness check yêu cầu. Chạy trên K8s hoặc chỉ bật sau khi operator áp
control tương đương ở host + set `KNOWLEDGE_INGESTION_*_ATTESTED=true`.

## Rate limiting

`caddy:2-alpine` stock **không** có rate-limit module (chỉ `request_body
max_size`, đã cấu hình trong `Caddyfile`). Rate limit theo IP/principal cần:
custom Caddy build với `caddy-ratelimit`, hoặc đặt sau Cloudflare / reverse
proxy có sẵn tính năng này. Ghi rõ lựa chọn khi bring-up.

## Rủi ro deploy Wave 7 (control-plane mới)

Thêm network hop Python↔Encore TS vào hot path resume run (`packages/agent_core/runs/control_plane_client.py::HttpControlPlaneLeaseClient`). Trước khi deploy production:
- Đo latency thật (chưa làm — cần Encore CLI).
- Xác nhận retry/circuit breaker trong `control_plane_client.py` đủ chịu lỗi khi `services/cosa` restart/deploy giữa lúc `agent_core` đang gọi.
- Cân nhắc thứ tự deploy: `services/cosa` (có control-plane endpoint mới) nên deploy TRƯỚC `agent_core` phiên bản dùng client mới, để tránh gọi endpoint chưa tồn tại.

## Không được làm

- Không tự ý chạy lệnh deploy/push tới hạ tầng chia sẻ mà không xác nhận với người dùng trước (CLAUDE.md #10, nguyên tắc "hành động rủi ro cao").
