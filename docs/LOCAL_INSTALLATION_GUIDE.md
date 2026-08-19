# Hướng Dẫn Cài Đặt & Vận Hành COSA Local Data (Data Plane)

> **Tài liệu tham chiếu:** [COSA_Hybrid_Local_PostgreSQL_Supabase_Project_Intelligence_Integration_v2.md](file:///Volumes/SSD/javis-saas/markdown/COSA_Hybrid_Local_PostgreSQL_Supabase_Project_Intelligence_Integration_v2.md)

---

## 1. Phân Tích Kiến Trúc Dữ Liệu Cục Bộ (Local Data Architecture)

Theo kiến trúc **COSA Hybrid Data Architecture**:
- **COSA Platform (Supabase Central)**: Là *System of Record* cho Identity, Company Registry, License/Tier, Entitlement, Project Lifecycle, Program/Cohort, và Platform Intelligence.
- **Company Local / Private Server (PostgreSQL Local)**: Là **System of Record Authoritative** cho toàn bộ dữ liệu nội bộ, vận hành chi tiết và bảo mật của doanh nghiệp:
  - Chi tiết dự án, tasks, OKRs, execution roadmap.
  - CRM chi tiết, thông tin khách hàng, ghi chú bán hàng, phỏng vấn khách hàng (*customer interviews & transcripts*).
  - Thí nghiệm (*experiments*), dữ liệu tài chính (*finance/accounting*), hợp đồng, tài liệu nội bộ.
  - Knowledge base cục bộ và embeddings vector (`pgvector`).
  - Bộ nhớ AI Agent (*agent memory, chat history, private prompts/configuration*).
  - **Realtime Voice:** Tích hợp trực tiếp **LiveKit Cloud** giúp đàm thoại giọng nói mượt mà mà không làm nặng tài nguyên máy tính cục bộ.

### Ranh Giới Dữ Liệu (Data Boundary)

```text
┌─────────────────────────────────────────────────────────────┐
│                    COSA LOCAL DATA PLANE                    │
│                 (Máy tính Founder / Private VPS)            │
├─────────────────────────────────────────────────────────────┤
│ • PostgreSQL Local (pgvector) : Dữ liệu vận hành cốt lõi    │
│ • MinIO Storage               : File đính kèm, attachments  │
│ • Brain API (FastAPI)         : REST/WebSocket Backend      │
│ • Agent Worker                : Thực thi Agent AI           │
│ • LiveKit Cloud Connector     : Kết nối Voice độ trễ thấp   │
│ • Local Workspace (~/.cosa/)  : Thư mục làm việc cá nhân    │
└──────────────────────────────┬──────────────────────────────┘
                               │
                Selective Sync (Outbox Pattern)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 COSA CONTROL PLANE (Central)                │
│                 (Supabase Self-Hosted VPS)                  │
├─────────────────────────────────────────────────────────────┤
│ • Identity & Auth            • Project Registry & Stages    │
│ • Licenses & Entitlements    • Cohort/Program Funnels       │
│ • Public Intake (Landing)    • Aggregate Intelligence       │
└──────────────────────────────┘
```

---

## 2. Thiết Lập Cài Đặt 1-Click (Zero-Friction Installer)

Bộ script cài đặt tự động cho phép người dùng nhập trực quan các API Key hoặc nhấn Enter để giữ giá trị mặc định có sẵn.

### A. Dành cho macOS / Linux / WSL

Chỉ cần chạy 1 lệnh duy nhất trong thư mục dự án:

```bash
./install.sh
```

**Quá trình tự động thực hiện:**
1. **Kiểm tra môi trường:** Phát hiện Docker Engine, Docker Compose, RAM, và kiểm tra xung đột cổng mạng (5432, 8000, 9000).
2. **Thiết lập cấu hình tương tác:**
   - Đặt mật khẩu Admin (`DEV_ADMIN_PASSWORD`).
   - Nhập khóa API & Chọn Model AI:
     - **Kira AI Gateway (Cổng AI Việt Nam - Mặc định, Free/Nhanh):** `KIRAAI_API_KEY`.
     - **Tùy chọn Model Kira AI:** Cho phép chọn trực tiếp danh sách model hỗ trợ:
       * `1) deepseek-v4-pro-free` *(Mặc định - Miễn phí, đầy đủ Tool Calling)*
       * `2) deepseek-chat` *(DeepSeek V3)*
       * `3) deepseek-reasoner` *(DeepSeek R1 suy luận sâu)*
       * `4) claude-3-7-sonnet` *(Claude 3.7 Sonnet)*
       * `5) claude-3-5-sonnet` *(Claude 3.5 Sonnet)*
       * `6) gpt-4o` & `7) gpt-4o-mini`
       * `8) gemini-2.0-flash`
       * `9)` Nhập model tùy chỉnh khác.
     - **Google Gemini API Key:** `GEMINI_API_KEY`.
     - **DeepSeek API Key (Trực tiếp):** `DEEPSEEK_API_KEY`.
     - **OpenAI API Key:** `OPENAI_API_KEY`.
     - **OpenRouter API Key:** `OPENROUTER_API_KEY`.
   - Nhập thông tin kết nối LiveKit Cloud: `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`.
   *(Nếu bạn đã có sẵn key trong `.env`, chỉ cần nhấn **Enter** để giữ nguyên).*
3. **Khởi chạy container:** Khởi động PostgreSQL (pgvector), MinIO, Brain API và Agent Worker.
4. **Database Migration:** Tự động áp dụng toàn bộ schema thông qua Alembic (`alembic upgrade head`).
5. **Bootstrap:** Tự động tạo Workspace, Company, Brain và tài khoản Quản trị viên (`admin@javis.local`).
6. **Chẩn đoán:** Tự động chạy `cosa_doctor` để đảm bảo 100% services hoạt động hoàn hảo.

---

### B. Dành cho Windows (PowerShell)

Mở PowerShell tại thư mục dự án và chạy:

```powershell
.\install.ps1
```

---

## 3. Sao Lưu (Backup) & Khôi Phục (Restore) Dữ Liệu

### Sao lưu toàn bộ dữ liệu (1 Lệnh)
```bash
./cosa.sh backup
```
File sao lưu sẽ được nén dưới dạng `.tar.gz` lưu tại thư mục `backups/cosa_backup_YYYYMMDD_HHMMSS.tar.gz`.

### Khôi phục dữ liệu (1 Lệnh)
```bash
./cosa.sh restore backups/cosa_backup_YYYYMMDD_HHMMSS.tar.gz
```
Hệ thống sẽ tự động giải nén và nạp lại toàn bộ cơ sở dữ liệu về trạng thái nguyên vẹn.

---

## 4. Bảng Lệnh Tiện Ích COSA CLI (`cosa.sh`)

| Lệnh | Mô tả |
| :--- | :--- |
| `./cosa.sh start` | Khởi động toàn bộ dịch vụ Local |
| `./cosa.sh stop` | Tạm dừng toàn bộ dịch vụ |
| `./cosa.sh restart` | Khởi động lại dịch vụ |
| `./cosa.sh status` | Xem trạng thái container và kiểm tra kết nối API |
| `./cosa.sh logs` | Xem log trực tiếp của hệ thống (vd: `./cosa.sh logs brain-api`) |
| `./cosa.sh doctor` | Chẩn đoán sức khỏe hệ thống (DB, Workspace, Capability Providers) |
| `./cosa.sh backup` | **Sao lưu toàn bộ dữ liệu** ra file `.tar.gz` |
| `./cosa.sh restore <file>` | **Khôi phục dữ liệu** từ bản sao lưu |
| `./cosa.sh reset` | Dọn sạch toàn bộ dữ liệu và volumes để cài lại từ đầu |

---

## 5. Thông Tin Kết Nối Mặc Định

- **Brain API & Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check Endpoint:** [http://localhost:8000/ready](http://localhost:8000/ready)
- **MinIO Storage Console:** [http://localhost:9001](http://localhost:9001) (User: `minioadmin` / Pass: `minioadmin`)
- **PostgreSQL Local:** `localhost:5432` (DB: `javis`, User: `javis`, Pass: `javis`)
- **Tài khoản đăng nhập Local:**
  - **Email:** `admin@javis.local`
  - **Password:** Mật khẩu đã cấu hình trong lúc cài đặt (mặc định: `Admin123456`)
