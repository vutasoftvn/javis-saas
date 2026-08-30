# Vận hành: Secrets

> Cập nhật 2026-08-28 (Part 2C.3). Nguồn sự thật cho: danh mục secret, nơi lưu,
> quy trình rotate, ai có quyền. Rà lại mỗi lần thêm capability/service mới.

## 1. Cơ chế quản lý secret theo môi trường

| Môi trường | Cơ chế | Ghi chú |
|---|---|---|
| Local dev | File `.env` ở **root repo** (docker-compose chỉ đọc file này — xem memory `javis-saas-env-file-split`). Chỉ chứa placeholder dev. | `backend/.env` bị container bỏ qua — đừng đặt secret ở đó. |
| Staging / Production (Python + infra: `cosa-api`, `cosa-worker`, `cosa-ingestion-worker`, `postgres`, `minio`, Caddy) | **Coolify secrets / environment variables** (quyết định `ADR-DEPLOY-001`). Inject vào container lúc runtime, không nằm trong image, không commit. | `docker-compose.prod.yaml` dùng `${VAR:?required}` → thiếu biến = fail-closed khi `docker compose config`. |
| Staging / Production (`services/cosa`, `services/company` — Encore/TS) | **Encore secret manager** (`encore secret set --type prod|staging <NAME>`). KHÔNG qua `.env`. | Encore tự quản DB connection string; secret nghiệp vụ khai qua `secret()` trong code. |

Không dùng SOPS/Vault ở giai đoạn này — nếu chuyển sang, ghi ADR mới và cập nhật bảng trên.

## 2. Danh mục secret (xác nhận qua code)

| Secret | Dùng ở đâu | Nơi lưu (prod) | Bắt buộc? | Rotate |
|---|---|---|---|---|
| `AGENT_DATABASE_URL` | `packages/agent` mọi repository factory; `apps/cosa` composition root | Coolify secret | Bắt buộc — thiếu → `RuntimeError` khi khởi động (`build_cosa_agent_plane`, no-silent-fallback) | Khi đổi mật khẩu Postgres app role |
| `PLATFORM_JWT_SECRET` | `apps/cosa/auth/jwt.py::_get_jwt_secret()` (verify + mint delegation token); `services/cosa` `token.service.ts::signPlatformToken()` — **phải đối xứng 2 phía** | Coolify secret **và** Encore secret (cùng giá trị) | Bắt buộc — guard từ chối ở staging/prod nếu thiếu / `< 32` ký tự / bằng dev default | **Rotate trước go-live.** Làm mất hiệu lực mọi session đang mở → cửa sổ bảo trì |
| `COSA_COMPANY_DELEGATION_SECRET` | JWT delegation COSA → Company: `apps/cosa/auth/jwt.py::_get_company_delegation_secret` và `services/company/shared/auth/cosa-delegation.service.ts::getDelegationSecret` | Coolify secret (cùng giá trị cho `services-company`, `cosa-api`, `cosa-worker`) | Bắt buộc cho cả ba consumer; không dùng chung với platform/session/service token | Rotate theo thứ tự deploy cả ba consumer |
| `WORKER_SERVICE_JWT_SECRET` | Auth giữa `cosa-worker` ↔ control plane; `scripts/mint-worker-service-token.mjs` | Coolify secret | Bắt buộc cho worker auth | **Rotate trước go-live**, đồng bộ mint lại worker token |
| `DEEPSEEK_API_KEY` | Model provider chính qua LiteLLM (`apps/cosa/composition/model_provider.py::build_deepseek_model`, `ADR-RUNTIME-002`) | Coolify secret | Bắt buộc cho runtime `openai_agents` production (fail-fast nếu thiếu) | **Rotate trước go-live** + định kỳ 90 ngày |
| `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` (hoặc S3 tương đương) | Artifact store, backup target (`scripts/backup/pg-backup.sh`) | Coolify secret | Bắt buộc nếu bật artifact/backup | **Rotate trước go-live** (dev default `minioadmin/minioadmin`) |
| Postgres app-role passwords (`agent`, `cosa`, `company`) | Thành phần của `*_DATABASE_URL` | Coolify secret / `deploy/postgres/init` | Bắt buộc | **Rotate trước go-live** |
| `OPENAI_API_KEY` | Chỉ để OpenAI Agents SDK tracing export (không phải model path) — không set thì tracing bị skip (log warning vô hại) | Coolify secret (tùy chọn) | Không | — |
| Encore business secrets (`services/*` khai qua `secret()`) | Từng service TS | `encore secret set` | Tùy service | Theo policy Encore |

## 3. Quy trình rotate

Nguyên tắc: **expand → cutover → contract** cho secret có consumer nhiều bên.

### 3.1 `PLATFORM_JWT_SECRET` (2 phía: `apps/cosa` + `services/cosa`)
1. Cửa sổ bảo trì (rotate làm mọi JWT hiện hành vô hiệu).
2. Sinh giá trị mới: `openssl rand -base64 48`.
3. Set đồng thời: Coolify secret (`apps/cosa`) **và** `encore secret set --type prod PLATFORM_JWT_SECRET` (`services/cosa`).
4. Redeploy `cosa-api`, `cosa-worker`, `services-cosa` cùng lúc.
5. Verify: token phát hành trước rotate → 401; đăng nhập lại → token mới verify OK (test trên staging trước — xem §5 checklist).

### 3.2 `COSA_COMPANY_DELEGATION_SECRET` (3 consumer: `services-company` + `cosa-api` + `cosa-worker`)
1. Sinh giá trị mới riêng cho delegation: `openssl rand -base64 48`. Không tái sử dụng `PLATFORM_JWT_SECRET`, `WORKER_SERVICE_JWT_SECRET`, `COSA_LOCAL_SERVICE_SECRET` hoặc các service token.
2. Set cùng một giá trị trong Coolify cho `COSA_COMPANY_DELEGATION_SECRET` của cả `services-company`, `cosa-api` và `cosa-worker`.
3. Redeploy cả ba consumer trong cùng một cửa sổ thay đổi; không chỉ restart một service.
4. Verify trên staging: `cosa-api` phát hành delegation JWT và `services-company` xác minh thành công; worker thực hiện luồng delegation thành công.
5. Sau khi staging và production traffic ổn định, thu hồi giá trị cũ và xác nhận delegation token ký bằng giá trị cũ bị từ chối.

### 3.3 `WORKER_SERVICE_JWT_SECRET`
1. Set giá trị mới ở Coolify.
2. `WORKER_SERVICE_JWT_SECRET=<new> node scripts/mint-worker-service-token.mjs <worker-id>` → cập nhật token cho từng worker.
3. Redeploy control plane + workers.

### 3.4 `DEEPSEEK_API_KEY` / MinIO keys / Postgres passwords
- API key: tạo key mới ở dashboard provider → set Coolify → redeploy → thu hồi key cũ sau khi xác nhận traffic chạy trên key mới.
- MinIO: tạo access key mới → cập nhật cả artifact client lẫn `pg-backup.sh` env → xoá key cũ.
- Postgres: `ALTER ROLE <role> WITH PASSWORD '<new>'` → cập nhật `*_DATABASE_URL` ở Coolify → redeploy → verify `/ready` 200.

## 4. Ai có quyền

| Vai trò | Quyền trên secret |
|---|---|
| Cutover Commander / Lead Architect | Full: xem tên + rotate mọi secret |
| App & Infra Lead (DevOps) | Set/rotate Coolify secrets, Encore secrets |
| Database Lead | Rotate Postgres passwords + `*_DATABASE_URL` |
| Developer thường | Chỉ `.env` dev local; không có quyền secret staging/prod |

Truy cập secret prod ghi log qua Coolify audit / Encore audit. Không chia sẻ giá trị secret qua chat/email.

## 5. Chống rò rỉ

- CI job `secret-scan` (`.github/workflows/quality.yml`) chạy `gitleaks` trên diff + toàn bộ lịch sử. Allowlist tại `.gitleaks.toml` — chỉ chứa placeholder dev công khai, **không bao giờ** thêm secret thật.
- Không log giá trị secret ra `RunEventRecord` / structured log — chỉ log tên biến / provider.
- File `.env*` (trừ `.env.example`) trong `.gitignore`. `.env.example` chỉ chứa placeholder `dev-...-change-in-production`.
- Trước `git add` bất kỳ file giống config: chạy `git diff --cached` và rà bằng mắt.

## 6. Checklist rotate trước go-live

Xem [`docs/runbooks/prod-cutover.md`](../runbooks/prod-cutover.md) **Bước 0 — Secret Rotation (T-24h)**. Tối thiểu phải rotate + verify trên staging: `PLATFORM_JWT_SECRET`, `COSA_COMPANY_DELEGATION_SECRET`, `WORKER_SERVICE_JWT_SECRET`, `DEEPSEEK_API_KEY`, MinIO keys, Postgres app-role passwords.
