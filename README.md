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

> Chi tiết hướng dẫn xem tại: [docs/LOCAL_INSTALLATION_GUIDE.md](file:///Volumes/SSD/javis-saas/docs/LOCAL_INSTALLATION_GUIDE.md)

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


