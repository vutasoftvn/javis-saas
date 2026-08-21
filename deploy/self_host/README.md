# Hướng Dẫn Tự Host COSA Full Stack Trên VPS Riêng

Hướng dẫn founder tự triển khai **toàn bộ COSA** (không chỉ control-plane) lên
VPS riêng của mình, dùng chính `backend/app/full_main.py` (role `full` - đủ 5
domain: founder_os/business/workforce/integrations/platform) - cùng 1 code
chạy trên desktop (Flutter), chỉ khác cách deploy.

Đây là **lựa chọn triển khai bổ sung**, không thay thế desktop-first. Xem
`docs/architecture/COSA_ADK_ORCHESTRATOR_UUID7_PROPOSAL.md`, Quyết định 3.

---

## 1. Kiến trúc

```text
deploy/self_host/
├── docker-compose.yaml   # caddy, postgres, minio, migrate, brain-api, agent-worker, realtime-agent
├── Caddyfile             # Reverse proxy + TLS Let's Encrypt tự động, 1 domain -> brain-api:8000
├── .env.example          # Template biến môi trường
└── README.md
```

Chỉ **`caddy`** (cổng 80/443) lộ ra internet. `brain-api` chỉ nghe trên mạng
nội bộ Docker (không có `ports:`), Caddy là reverse proxy TLS duy nhất phía
trước nó. `postgres`, `minio`, `agent-worker` **không** có `ports:` publish ra
host - chỉ giao tiếp qua mạng nội bộ Docker giữa các service trong cùng
compose file này, không public.

**KHÔNG bao gồm `desktop_worker`** (`desktop_worker/main.py`): đây là 1 plane
chạy `subprocess(..., shell=True)` không sandbox, chỉ an toàn khi bind
loopback (`127.0.0.1`) trên máy dev cục bộ. Chạy nó trên VPS - hoặc lộ nó ra
ngoài dưới bất kỳ hình thức nào - sẽ biến VPS thành remote-code-execution công
khai. Không có ca sử dụng hợp lệ nào cho self-host; service này cố tình không
xuất hiện trong `docker-compose.yaml` ở đây.

## 2. Nguyên tắc single-authority (Personal Mode)

Self-host 1 founder = **Personal Mode**: Postgres tự host ở đây là
**authority duy nhất** cho dữ liệu business (Task/CRM/Finance/...). Central
control-plane (do COSA vận hành) chỉ đóng vai trò licensing/entitlement -
**không** đồng bộ 2 chiều dữ liệu business với self-host của bạn. Nếu sau này
cần nhiều Human Employee cộng tác (Team Mode), đó là 1 hành động "Promote to
Team Workspace" tường minh riêng - self-host mặc định không tự động làm việc
này.

Self-host vẫn **single-tenant mỗi deployment** - 1 lần cài đặt = 1 công ty,
giống desktop (`markdown/Structure.md:286`: "Không thiết kế multi-tenant SaaS
vào local application.").

## 3. Cài đặt (1 lệnh sau khi cấu hình)

```bash
# 1. SSH vào VPS, clone repo
ssh root@<IP_VPS>
git clone https://github.com/<your-fork>/javis-saas.git /opt/cosa
cd /opt/cosa/deploy/self_host

# 2. Tạo file cấu hình môi trường
cp .env.example .env
# Chỉnh sửa .env: SELF_HOST_DOMAIN, POSTGRES_PASSWORD, MINIO_SECRET_KEY,
# JWT_SECRET, MASTER_SECRET_KEY, COSA_ALLOWED_ORIGINS, DEEPSEEK_API_KEY, ...

# 3. Trỏ DNS domain của bạn (bản ghi A) về IP VPS này TRƯỚC khi chạy -
#    Caddy cần domain resolve được để tự cấp SSL Let's Encrypt.

# 4. Khởi chạy toàn bộ stack
docker compose up -d --build
```

Voice/realtime (LiveKit) là **tuỳ chọn** - mặc định service `realtime-agent`
nằm trong Docker Compose profile `realtime`, không chạy nếu bạn không cấu
hình `LIVEKIT_URL`/`LIVEKIT_API_KEY`/`LIVEKIT_API_SECRET` trong `.env`. Muốn
bật:

```bash
docker compose --profile realtime up -d
```

## 4. Cảnh báo quan trọng đã biết: `.env` gốc, không phải `backend/.env`

`docker compose` chỉ đọc file `.env` nằm **cùng thư mục với file
`docker-compose.yaml`** (tức `deploy/self_host/.env` ở đây) để substitute các
biến `${VAR}` trong chính file compose. Nó **KHÔNG** đọc `backend/.env` bên
trong container - nếu bạn chỉnh `backend/.env` mong đổi cấu hình, container
`brain-api`/`agent-worker` sẽ **không** thấy giá trị đó, dẫn tới lỗi kiểu
"invalid API key" giả (biến trông như đã set nhưng thực chất container vẫn
dùng giá trị mặc định/rỗng). Luôn set biến trong `deploy/self_host/.env`,
không phải `backend/.env`.

## 5. Kiểm tra sau khi deploy

```bash
curl https://<SELF_HOST_DOMAIN>/live
curl https://<SELF_HOST_DOMAIN>/ready
```

`/ready` trả về `checks: {database, storage, migrations, worker}` - cả 4 phải
`"ok"` khi stack chạy đúng (role `full` giữ nguyên đủ 4 check, khác với role
`central_control_plane` chỉ check `database`).
