# BÁO CÁO KIỂM KÊ CƠ SỞ DỮ LIỆU & SCHEMA (DATABASE MODELS)
## (PHASE 0 - INVENTORY REPORT 02)

> **Dự án:** COSA (Founder / Company Operating System)  
> **Ngày thực hiện:** 2026-08-20  
> **Trạng thái:** Hoàn tất khảo sát

---

## 1. PHÂN BỔ CƠ SỞ DỮ LIỆU HIỆN TẠI & CHIẾN LƯỢC MỤC TIÊU

Theo [CLAUDE.md](file:///Volumes/SSD/javis-saas/CLAUDE.md) Mục 10 và [markdown/Structure.md](file:///Volumes/SSD/javis-saas/markdown/Structure.md) Mục 43, hệ thống chia rõ 2 vùng lưu trữ:
- **PostgreSQL:** Lưu trữ dữ liệu nghiệp vụ có cấu trúc của Công ty (Business Entities).
- **SQLite:** Lưu trữ dữ liệu phiên (Sessions), event store (`evt_xxx`), traces và local cache.

---

## 2. DANH MỤC CÁC BẢNG DỮ LIỆU (DATABASE TABLES INVENTORY)

### 2.1. Nhóm Bảng Nghiệp vụ Cốt lõi (Business Core - PostgreSQL)
| Tên Bảng (Table Name) | Domain Sở hữu | Khóa chính / Khóa ngoại | Chức năng lưu trữ | Đánh giá Tuân thủ AI Independence |
| :--- | :--- | :--- | :--- | :--- |
| `companies` | `core/company/` | `id (UUID)` | Thông tin công ty, license key, ngành nghề | ✅ Độc lập hoàn toàn |
| `projects` | `core/projects/` | `id`, `company_id (FK)` | Dự án, giai đoạn startup, mục tiêu | ✅ Độc lập (Không chứa token/prompt) |
| `okrs` | `core/okr/` | `id`, `company_id (FK)` | Mục tiêu OKR quý, chỉ số đo lường | ✅ Độc lập |
| `twelve_week_tactics`| `core/twelve_week_year/` | `id`, `okr_id (FK)` | Kế hoạch hành động 12 tuần | ✅ Độc lập |
| `tasks` | `core/tasks/` | `id`, `project_id (FK)` | Tác vụ vận hành & trạng thái thực thi | ✅ Độc lập |
| `evidence_records` | `core/tasks/` | `id`, `task_id (FK)` | Bằng chứng hoàn tất mục tiêu kinh doanh | ✅ Độc lập |
| `crm_leads` | `core/crm/` | `id`, `company_id (FK)` | Danh sách khách hàng tiềm năng | ✅ Độc lập |
| `crm_deals` | `core/crm/` | `id`, `lead_id (FK)` | Phễu doanh thu, giá trị cơ hội bán | ✅ Độc lập |
| `finance_tt58_records`| `core/finance/` | `id`, `company_id (FK)` | Sổ sách kế toán quản trị theo TT58 VN | ✅ Độc lập |
| `contracts` | `core/legal/` | `id`, `company_id (FK)` | Hợp đồng & trạng thái pháp lý | ✅ Độc lập |

### 2.2. Nhóm Bảng Agent & Phiên làm việc (Cần chuẩn hóa chuyển sang SQLite Event Store)
| Tên Bảng (Table Name) | Vị trí hiện tại | Chức năng hiện tại | Đề xuất Chuẩn hóa |
| :--- | :--- | :--- | :--- |
| `agent_sessions` | PostgreSQL | Lưu phiên chat và state | Chuyển sang SQLite Append-Only Event Store |
| `agent_events` | PostgreSQL | Lưu vết một số hành động | Chuẩn hóa schema sang `evt_xxx` với JSON payload |
| `agent_memories` | PostgreSQL | Lưu trí nhớ ngữ cảnh | Giữ lại vector/embeddings hoặc lưu SQLite local |
| `capability_definitions`| PostgreSQL | Lưu catalog năng lực khả thi | Giữ PostgreSQL (Seed tự động từ YAML catalog) |

---

## 3. RÀ SOÁT CÁC CỘT VI PHẠM (VIOLATION AUDIT)
- Không phát hiện các cột cứng như `claude_prompt` hay `deepseek_model_name` trong bảng `companies` và `projects`.
- Một số bảng lưu trữ token usage cần được tách riêng vào module `audit_logs` để giữ bảng nghiệp vụ hoàn toàn trong sạch.
