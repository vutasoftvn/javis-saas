# COSA Services Cluster (Local Microservices)

Cụm Microservices nền tảng xây dựng trên **Encore.ts** (TypeScript) kết hợp cùng **Realtime Agent** (Python/LiveKit).

## Kiến trúc Cluster

- **`identity/`**: Xác thực (JWT, AuthHandler), Quản lý Workspace, Organization, WorkforceMember.
- **`operations/`**: Quản lý Tasks, Initiatives, OKR Cycles, OKR Objectives & Key Results.
- **`commercial/`**: CRM (Accounts, Contacts, Customers) & Sales (Leads, Opportunities).
- **`finance-legal/`**: Quản lý hồ sơ tài chính (AccountingProfiles, Periods, Transactions, Snapshots) và Pháp lý (Legal Checklist, Legal Obligations).
- **`shared/`**: Event contracts (`DomainEvent`), type definitions dùng chung.
- **`realtime_agent/`**: Realtime Voice & AI Agent (LiveKit + Gemini Live).

---

## Chạy Local bằng Docker Compose

### 1. Chuẩn bị biến môi trường
```bash
cd services
cp .env.example .env
```
*(Cập nhật `GEMINI_API_KEY` nếu bạn muốn test voice agent với Gemini Live)*

### 2. Khởi động các container
```bash
docker compose up -d
```

### 3. Xem logs
```bash
docker compose logs -f
```

### 4. Truy cập các dịch vụ
- **API Gateway (Encore)**: [http://localhost:4000](http://localhost:4000)
- **Dev Dashboard & Distributed Tracing (Encore)**: [http://localhost:9400](http://localhost:9400)
- **LiveKit Server (WebRTC / Voice)**: [http://localhost:7880](http://localhost:7880)
- **Postgres Database (dev port)**: `localhost:5433` (User: `cosa`, Pass: `cosa`, DB: `cosa`)

### 5. Dừng các container
```bash
docker compose down
```

---

## Chạy trực tiếp qua Encore CLI (Native Local Dev)

Nếu đã cài đặt `encore` CLI trên máy:

```bash
# Cài dependencies
npm install

# Chạy unit tests
encore test

# Chạy dev server với hot-reload
encore run
```
