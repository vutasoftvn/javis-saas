# COSA OS — Local Data & Autonomous Agent Platform

Hệ điều hành doanh nghiệp AI tích hợp kiến trúc Hybrid: **PostgreSQL Local (Data Plane)** + **Supabase Central (Control Plane)**.

---

## ⚡ Cài Đặt Nhanh Local Data Plane (1-Click)

### Trên macOS / Linux / WSL:
```bash
./install.sh
```

### Trên Windows (PowerShell):
```powershell
.\install.ps1
```

---

## ⚠️ Hai Hệ Backend Song Song (đọc trước khi kết nối Frontend)

Repo hiện có **2 backend chạy song song, chưa hợp nhất** — xem chi tiết tại `docs/architecture/adr/ADR-012-legacy-backend-agentos-services-integration-plan.md`:

- **`legacy/backend`** (FastAPI, `brain-api` cổng `8000`, chạy qua `docker-compose.yml` ở root) — **hệ đang phục vụ traffic thật**, giữ các năng lực: LLM Chat Gateway đa provider, Google OAuth, n8n workflow bridge, OpenSandbox, Extensions/Plugin API.
- **`agentos/` + `services/`** (Encore Gateway cổng `4000`, mục hướng dẫn khởi động bên dưới) — kiến trúc đích (canonical theo `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`), nhưng tính đến 2026-08-22 **chưa có consumer nào (backend, frontend, hay realtime_agent) thật sự gọi qua HTTP** — mới chỉ parity-tested độc lập từng cluster.

`frontend/lib/core/network/api_client.dart` mặc định trỏ `:4000` (định hướng tương lai), nhưng `settings_extensions_page.dart` vẫn gọi `:8000` vì Extensions API chưa tồn tại ở `services/`. Đừng coi `:4000` là nguồn duy nhất cho tới khi ADR-012 được đóng.

⚠️ **`legacy/backend` đã bị "đóng băng tại chỗ" (frozen-in-place):** commit tái cấu trúc 2026-08-22 tách `backend/` cũ thành 6 thư mục `legacy/{backend,agent_runtime,platform,business,domains,entrypoints}` mà không cập nhật Docker build cho khớp — `brain-api`/`agent-worker`/`migrate` hiện **không chạy được** (thiếu import xuyên thư mục `core`/`platform_core`/`business`/`business_core`/`regulations`/`founder_os`). Quyết định: **không** cố khôi phục lại monolith 6-mảnh này — 3 service trên đã bị gate sau `--profile legacy` nên `docker compose up` mặc định **không** cố khởi động chúng nữa (chỉ chạy `postgres`/`minio`/`livekit`/`realtime-agent`). Hướng đi tiếp theo là trích riêng các năng lực còn thiếu (LLM Gateway/OAuth/n8n/Sandbox) thành adapter gọn cho `agentos/` — xem `ADR-012`.

---

## 🛠️ Quản Trị Hệ Thống Nhanh (COSA CLI)

```bash
./cosa.sh start    # Khởi động dịch vụ
./cosa.sh stop     # Dừng dịch vụ
./cosa.sh status   # Kiểm tra trạng thái
./cosa.sh doctor   # Chẩn đoán sức khỏe hệ thống
./cosa.sh backup   # Sao lưu toàn bộ dữ liệu Local
./cosa.sh restore  # Khôi phục dữ liệu
```

---

## 🚀 Khởi Động Cụm Microservices (`services/`)

Cụm Microservices kiến trúc mới (Encore.ts + LiveKit Voice Agent) gồm 4 cluster: `identity`, `operations`, `commercial`, `finance-legal`, cùng worker `realtime_agent`.

### 1. Khởi động nhanh bằng Docker Compose:
```bash
# Khởi động toàn bộ cụm services, livekit, realtime-agent, postgres
make services-docker-up

# Xem logs thời gian thực
make services-docker-logs

# Dừng cụm services
make services-docker-down
```
*(Hoặc chạy trực tiếp từ thư mục `services/`: `cd services && docker compose up -d`)*

### 2. Các Cổng Dịch Vụ & Giao Diện:
- **API Gateway (Encore)**: [http://localhost:4000](http://localhost:4000)
- **Encore Dashboard & Tracing UI**: [http://localhost:9400](http://localhost:9400) *(Xem Service Topology, Flow graph, API Docs & Traces)*
- **LiveKit Server (WebRTC/Audio)**: [http://localhost:7880](http://localhost:7880) (hoặc port `7885` khi chạy qua Compose)
- **Postgres Database (Cụm Services)**: `localhost:5433`

---

## 🗄️ Hướng Dẫn Truy Cập Database

### Cách 1: Kết Nối CSDL Postgres qua Client bên ngoài (TablePlus, DBeaver, psql)
Container PostgreSQL độc lập của cụm services được expose ra port `5433` trên localhost:

- **Host**: `localhost` (hoặc `127.0.0.1`)
- **Port**: `5433`
- **User**: `javis`
- **Password**: `javis`
- **Database**: `javis`
- **Connection URI**:
  ```text
  postgresql://javis:javis@localhost:5433/javis
  ```

Lệnh truy cập nhanh qua terminal CLI:
```bash
docker compose -f services/docker-compose.yml exec postgres psql -U javis -d javis
```

### Cách 2: Truy Cập Trực Tiếp CSDL Từng Service (Encore CLI)
Khi chạy chế độ Native Dev (`cd services && encore run`), Encore tự động quản lý CSDL riêng cho từng cluster service:

```bash
cd services

# Mở shell SQL trực tiếp vào Database của từng cluster:
encore db shell identity        # CSDL Identity (users, workspaces, orgs)
encore db shell operations      # CSDL Operations (tasks, OKR, initiatives)
encore db shell commercial      # CSDL Commercial (CRM, leads, opportunities)
encore db shell finance-legal   # CSDL Finance & Legal (hồ sơ kế toán, pháp lý)

# Lấy connection string của một database cụ thể:
encore db conn-uri identity
```

---

## 🧪 Kiểm Thử (Unit Tests)

```bash
# Chạy toàn bộ 98 unit tests của 4 cluster:
make services-test
# Hoặc: cd services && encore test
```

---

## 🖥️ Khởi Động Ứng Dụng Frontend Desktop (Flutter macOS)

```bash
cd frontend
flutter run -d macos
```

Hoặc build bản đóng gói:
```bash
cd frontend
flutter build macos --debug
open build/macos/Build/Products/Debug/frontend.app
```


