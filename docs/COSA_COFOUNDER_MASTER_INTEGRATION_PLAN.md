# COSA CO-FOUNDER & 5 CORE DOMAIN WORKFORCE
## MASTER INTEGRATION PLAN (F4 SPECIFICATION)

> **Mục tiêu:** Chuyển đổi toàn diện kiến trúc COSA từ mô hình "Dashboard 12 AI Bots" sang mô hình **"COSA AI Co-Founder & 5 Core Domain Workforce Engine"** theo đặc tả [F4.md](file:///Volumes/SSD/javis-saas/markdown/F4.md).
> **Trạng thái:** Sẵn sàng triển khai theo từng Phase.

---

## 1. TỔNG QUAN KIẾN TRÚC ĐÍCH

```text
               HUMAN FOUNDER (Vision, Capital, Ownership, Final Strategic & Legal Authority)
                               │
                               ▼
               COSA CO-FOUNDER (Companion, Context, Mission Coordinator, Business Synthesis)
                               │
               ┌───────────────┼───────────────┐
          Conversation      Context          Goals
               └───────────────┼───────────────┘
                               ▼
                        INTENT ROUTER
                               │
                               ▼
                      MISSION ORCHESTRATOR
                               │
        ┌───────────┬──────────┼──────────┬───────────┐
        ▼           ▼          ▼          ▼           ▼
      SALES     MARKETING   FINANCE     LEGAL     BUILD/TECH   (5 Core Default Domains)
        │           │          │          │           │
        └───────────┴──────────┼──────────┴───────────┘
                               ▼
                    SPECIALISTS / SKILLS / TOOLS
                               │
                               ▼
                OUTCOMES ──► EVIDENCE ──► LEARNING
                               │
                               ▼
                    COSA BUSINESS SYNTHESIS
                               │
                               ▼
                         HUMAN FOUNDER
```

---

## 2. NGUYÊN TẮC CỐT LÕI (F4 CORE RULES)

1. **COSA Co-Founder $\neq$ Domain Agent:** COSA là lớp điều phối và hỗ trợ ra quyết định trung tâm nằm trên Workforce.
2. **Founder $\neq$ COSA:** Founder là con người nắm quyền sở hữu và ra quyết định cuối cùng; COSA hỗ trợ phân tích, đề xuất và phản biện (`Challenge Mode`).
3. **Mission-Centric (`Mission > Agent`):** Founder giao mục tiêu (`Goal`), COSA sinh `Mission`, Mission tự động điều phối đa Domain Agent song song.
4. **5 Core Domain Agents mặc định:** `Sales`, `Marketing`, `Finance`, `Legal`, `Build/Tech`.
5. **Optional Packs cài đặt thêm:** `Operations`, `People/HR`, `Customer Support` (chỉ bật khi doanh nghiệp phát triển đến quy mô cần thiết).
6. **Xóa bỏ các Agent Anti-Patterns:**
   - *Strategy* $\rightarrow$ Năng lực tư duy nằm tại COSA Co-Founder.
   - *Research* $\rightarrow$ Shared capability `investigate`.
   - *QA/Quality* $\rightarrow$ Cross-cutting `QualityGatePolicy`.
   - *Automation* $\rightarrow$ Tool Registry (n8n, cron, webhook, celery).
   - *Voice* $\rightarrow$ Giao thức tương tác (Modality).
   - *Business Domain* $\rightarrow$ Phân loại tri thức, không sinh bot thừa.
7. **Phân định `Decision` vs `Approval`:**
   - `Decision`: Lựa chọn chiến lược kinh doanh của Founder (lưu trữ trong `Decision Memory` kèm bằng chứng Evidence).
   - `Approval`: Cổng kiểm soát thực thi tác vụ kỹ thuật/vận hành.
8. **Hologram Hub mới:** Trở thành **Founder Command Center** (Top 3, Pulse, Decisions, Missions, Ask COSA); danh sách Agent đưa vào view phụ (AI Workforce).

---

## 3. LỘ TRÌNH TRIỂN KHAI TOÀN DIỆN (5 PHASES)

### PHASE 1: Database Schema & Migration Layer
- **Mục tiêu:** Tách biệt COSA Co-Founder, chuẩn hóa 5 Core Domains và tạo đối tượng dữ liệu `Founder Decision` độc lập với `Approval`.
- **Nội dung chính:**
  1. Thêm cột `category` (`ORCHESTRATOR`, `DOMAIN`, `OPTIONAL_DOMAIN`, `LEGACY`) và `is_default_active` vào `AgentDefinition`.
  2. Tạo bảng mới `founder_decisions` gắn với Evidence Engine (F1/F3).
  3. Tạo bảng `agent_aliases` hỗ trợ migration mềm.
  4. Alembic Migration Script `v13_051_cosa_cofounder_schema.py` & Seed data.
- **Tài liệu chi tiết:** `docs/COSA_COFOUNDER_PHASE_1_PLAN.md`

---

### PHASE 2: Backend Co-Founder Engine & Intent Routing
- **Mục tiêu:** Xây dựng dịch vụ điều phối trung tâm COSA Co-Founder và cơ chế phân loại ý định thông minh.
- **Nội dung chính:**
  1. `CosaCofounderService`:
     - System Prompt chuẩn hóa theo Mục 53 của F4.
     - `challenge_assumptions()`: Phản biện dựa trên Evidence (Problem-First).
     - `synthesize_cross_domain()`: Tổng hợp chéo (Marketing ROI + Finance Runway).
     - `get_next_best_action()`: Gợi ý Top 3 hành động theo 12 Week Year.
  2. Nâng cấp `IntentRouter`:
     - `greeting`: Phản hồi nhanh, không load dữ liệu nặng.
     - `founder_reflection` & `founder_review`: Tải context mục tiêu, rủi ro, tasks quá hạn.
     - `founder_command`: Khởi tạo và điều phối Mission.

---

### PHASE 3: Domain Workforce & Shared Capabilities Standard
- **Mục tiêu:** Tinh gọn các Domain Agents và chuyển đổi các bot thừa thành Specialist hoặc Capability.
- **Nội dung chính:**
  1. Chuẩn hóa 5 Core Domain Agents (`Sales`, `Marketing`, `Finance`, `Legal`, `Build`).
  2. Chuyển `Research Agent` thành capability dùng chung `investigate`.
  3. Chuyển `QA Agent` thành `QualityGatePolicy`.
  4. Chuyển `SEO Agent`, `Content Agent` thành Specialists trực thuộc `Marketing Agent`.
  5. Đóng gói các Optional Packs: `Operations Pack`, `People Pack`, `Support Pack`.

---

### PHASE 4: Frontend Flutter (Hologram Hub & AI Workforce)
- **Mục tiêu:** Tái thiết kế giao diện Hologram Hub thành Founder Command Center hiện đại, trực quan.
- **Nội dung chính:**
  1. **Thẻ trung tâm `COSA Co-Founder Card`:** Company Pulse, tiến độ Goals, Active Missions, Gợi ý trọng tâm trong ngày.
  2. **Thanh tương tác `Ask COSA`:** Trò chuyện trực tiếp với Co-Founder.
  3. **Hàng đợi `Waiting for You`:** Tích hợp `Founder Decisions` (Chiến lược) + `Approvals` (Tác vụ).
  4. **Thẻ `AI Workforce Overview`:** Hiển thị trạng thái 5 Core Domains (Working/Idle), click mở view quản lý chuyên sâu.

---

### PHASE 5: Acceptance Verification & Master Spec Consolidation
- **Mục tiêu:** Đảm bảo toàn bộ hệ thống vượt qua các kịch bản kiểm thử chuẩn và hợp nhất tài liệu.
- **Nội dung chính:**
  1. Kiểm thử Acceptance Tests (Mục 58-61 của F4):
     - Greeting Test
     - Morning Focus / Top 3 Test
     - Multi-Agent Mission Dispatch Test
     - Cross-domain Reasoning Test
  2. Hợp nhất `F4.md` với các đặc tả trước đó thành Master Agentic Runtime Specification duy nhất.
