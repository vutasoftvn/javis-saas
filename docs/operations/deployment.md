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
3. **`apps/cosa` API** (Python) — `apps/cosa/Dockerfile.api`, port 8000. Cần `AGENT_DATABASE_URL` + `DEEPSEEK_API_KEY` + `PLATFORM_JWT_SECRET` + `CORS_ORIGINS` (no-silent-fallback — thiếu → `RuntimeError`/guard raise lúc start).
4. **`apps/cosa` worker** (Python) — `apps/cosa/Dockerfile.worker`, không mở HTTP. `restart: unless-stopped` đưa lại khi crash; task đang chạy được sweeper cron reclaim (Part 2E).

`cosa-ingestion-worker`: profile `ingestion`, TẮT mặc định trong compose —
Dockerfile ghi rõ compose không cấp read-only rootfs + egress-deny mà
readiness check yêu cầu. Chạy trên K8s hoặc chỉ bật sau khi operator áp
control tương đương ở host + set `KNOWLEDGE_INGESTION_*_ATTESTED=true`.

## Built-in skillpack bundle

Hai image runtime `apps/cosa` (API và worker) đều chứa cùng một bundle đã
version hóa tại `/app/skillpacks`, kèm `/app/evals` và sổ nguồn
`/app/docs/integrations/skill-source-attribution.md`. Khi khởi động, COSA
validate bundle, publish idempotent vào registry, rồi kiểm tra tất cả pinned
skills trước khi nhận request hoặc poll job. Vì vậy thiếu bundle, manifest
sai, hoặc pin/hash không khớp sẽ giữ service ở trạng thái không sẵn sàng.

Không sửa trực tiếp một skill đã published trong môi trường đang vận hành:
thay đổi definition phải tăng `metadata.version`, cập nhật pin có chủ đích và
build/deploy image mới. Endpoint đồng bộ thủ công chỉ là công cụ vận hành;
không phải điều kiện để API hoặc worker có thể bắt đầu phục vụ.

## Skillpack release gate

Trước mỗi release, phải chạy và ghi lại bằng chứng các lệnh sau (đều exit 0;
Compose dùng biến production-equivalent, không thay secret thật bằng
placeholder):

```bash
make skillpacks-validate
PYTHONPATH=packages:. python -m pytest \
  tests/agent/skills/test_skillpack_contract.py \
  tests/agent/skills/test_skillpack_eval_contract.py \
  tests/agent/skills/eval/ -q
PYTHONPATH=packages:. python -m pytest \
  tests/apps/cosa/agents/test_skillpack_seed.py \
  tests/apps/cosa/agents/test_seed.py \
  tests/apps/cosa/test_scheduled_session_worker.py \
  tests/apps/cosa/test_vertical_slice_1_read_path.py \
  tests/apps/cosa/test_vertical_slice_2_write_approval.py \
  tests/apps/cosa/test_workspace_execution_e2e.py -q
PYTHONPATH=packages:. python -m pytest \
  deploy/central_vps/smoke/test_skillpack_image_contract.py -q
docker compose -f deploy/central_vps/docker-compose.prod.yaml config
git diff --check
```

Bằng chứng cần ghi: build SHA, số bundle khám phá (`manifest.yaml`), kết quả
validator, số skill đã publish, số pinned-skill resolve thành công, và kết quả
bốn runtime-slice test. Nếu bootstrap lỗi (thiếu bundle, vi phạm contract,
parse lỗi, hay pin/hash không khớp), service phải được giữ ở trạng thái
**không sẵn sàng** — không phục vụ request và không poll job.

Ví dụ bằng chứng gần nhất (verified 2026-08-31): 114 bundle, validator PASS,
114 skill publish idempotent, 18 pinned-skill resolve đủ, 4 runtime-slice PASS.

## Rate limiting
 
`caddy:2-alpine` stock **không** có rate-limit module (chỉ `request_body
max_size`, đã cấu hình trong `Caddyfile`). Rate limit theo IP/principal cần:
custom Caddy build với `caddy-ratelimit`, hoặc đặt sau Cloudflare / reverse
proxy có sẵn tính năng này.
 
Xem quyết định chi tiết và tiêu chuẩn bắt buộc tại [Release Security Checklist](file:///Volumes/SSD/javis-saas/docs/operations/release-security-checklist.md) và biến xác thực `EDGE_RATE_LIMIT_ATTESTED`.


## Rủi ro deploy Wave 7 (control-plane mới)

Thêm network hop Python↔Encore TS vào hot path resume run (`packages/agent/runs/control_plane_client.py::HttpControlPlaneLeaseClient`). Trước khi deploy production:
- Đo latency thật (chưa làm — cần Encore CLI).
- Xác nhận retry/circuit breaker trong `control_plane_client.py` đủ chịu lỗi khi `services/cosa` restart/deploy giữa lúc `agent` đang gọi.
- Cân nhắc thứ tự deploy: `services/cosa` (có control-plane endpoint mới) nên deploy TRƯỚC `agent` phiên bản dùng client mới, để tránh gọi endpoint chưa tồn tại.

## Không được làm

- Không tự ý chạy lệnh deploy/push tới hạ tầng chia sẻ mà không xác nhận với người dùng trước (CLAUDE.md #10, nguyên tắc "hành động rủi ro cao").
