# Kế Hoạch Triển Khai Chi Tiết: Giai Đoạn P0 (Phase 0)
## COSA Core Runtime, Conversation Intent Router, 5 Domain Agents Skeleton & Memory Core

> **Mục tiêu của Phase P0:**
> Xây dựng nền móng vững chắc nhất cho toàn bộ hệ thống COSA Founder OS. Giải quyết triệt để lỗi routing trò chuyện (không gọi tool khi chào hỏi), chuẩn hóa 5 Domain Agents + Shared Capabilities, thiết lập Prompt Registry tập trung có versioning, và hoàn thiện hệ thống Bộ nhớ 5 tầng (L0–L4) cùng chuẩn Snowflake ID 64-bit.

---

## 1. Danh Sách Các Hạng Mục Chi Tiết Cần Triển Khai Trong Phase P0

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ TASK P0.1: Conversation Intent Router & Fast-Path Classifier                     │
│ - Tách bạch rõ 6 Intent: Greeting, Founder Brief, Knowledge, Task, Mission, Admin│
│ - Fast-path cho Greeting/Smalltalk: phản hồi < 100ms, 0 tool call               │
│ - Cấu trúc hóa output cho Task Command & Mission Command                         │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
┌───────────────────────────────────────▼─────────────────────────────────────────┐
│ TASK P0.2: 5 Domain Agents Architecture Skeleton & Shared Capabilities           │
│ - 5 Domain Agents: Founder, Sales, Marketing, Finance, Legal (+ Build/Tech)     │
│ - Shared Capability Registry: Research, Content, Reasoning, Automation, Review   │
│ - Chuẩn hóa Base Agent Interface & Execution Lifecycle                          │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
┌───────────────────────────────────────▼─────────────────────────────────────────┐
│ TASK P0.3: Centralized Prompt Registry System                                   │
│ - Quản lý tập trung prompt theo domain: prompts/cosa/, prompts/sales/...         │
│ - Versioning template, hash check, metadata snapshot vào ai_runs                 │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
┌───────────────────────────────────────▼─────────────────────────────────────────┐
│ TASK P0.4: 5-Layer Memory Core (L0–L4 Architecture)                             │
│ - Model & Migration: agent_memory (Snowflake ID, workspace_id, L0..L4)          │
│ - Memory Manager: Session (L0), Working (L1), Founder (L2), Knowledge (L3),      │
│   Pattern Learning (L4)                                                         │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
┌───────────────────────────────────────▼─────────────────────────────────────────┐
│ TASK P0.5: Task Canonical Entity Hardening & Invariant Checks                   │
│ - Chuẩn hóa schema bảng tasks (Snowflake ID, List/Calendar/Kanban fields)       │
│ - Dependency Cycle Detector ngăn chặn vòng lặp phụ thuộc công việc               │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
┌───────────────────────────────────────▼─────────────────────────────────────────┐
│ TASK P0.6: Flutter Shell Layout & 5+1 Navigation Restructuring                  │
│ - Điều chỉnh AppRoutes & AppPages: Hub, COSA, Work, Company, Brain + Admin      │
│ - Gom toàn bộ cấu hình kỹ thuật vào trang Admin                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Chi Tiết Kỹ Thuật Từng Hạng Mục (Technical Specification)

### Task P0.1: Conversation Intent Router & Fast-Path Classifier
- **Vị trí file:** `backend/app/modules/chat/conversation_gate.py` và `backend/app/modules/chat/intent_router.py`.
- **Nghiệp vụ chi tiết:**
  1. **Fast-path Greeting/Smalltalk:**
     - Match regex các mẫu chào hỏi tiếng Việt & tiếng Anh ("chào", "xin chào", "hello", "hi cosa", "bạn là ai", "cảm ơn", "tạm biệt").
     - Trả về `GateDecision(intent=GateIntent.SOCIAL_CHAT, needs_tools=False, allowed_namespaces=frozenset())`.
     - Phản hồi trực tiếp không truy vấn DB dự án, không kích hoạt tool search, độ trễ < 100ms.
  2. **Founder Brief Intent:**
     - Match các câu hỏi cập nhật ("hôm nay thế nào", "tình hình công ty", "báo cáo nhanh", "pulse").
     - Gọi `FounderBriefService` tổng hợp nhanh: Pulse (Sales, Cash, Marketing, Ops), 3 việc ưu tiên hôm nay, Pending Approvals, Active Missions.
  3. **Knowledge Search Intent:**
     - Match câu hỏi tra cứu khái niệm, tài liệu nội bộ ("chính sách...", "tìm trong vault...", "quy định...").
     - Định tuyến qua Hybrid Search (FTS + pgvector) có trích dẫn nguồn (citation).
  4. **Task & Mission Commands:**
     - Match các câu lệnh hành động ("tạo task...", "giao việc...", "tìm 20 khách hàng...", "lên chiến dịch...").
     - Trích xuất tham số có cấu trúc (Structured Pydantic schema: `title`, `priority`, `due_date`, `assignee_agent`), hiển thị bản xem trước cho Founder.

### Task P0.2: 5 Domain Agents Skeleton & Shared Capabilities
- **Vị trí thư mục:** `backend/app/agents/` (hoặc `backend/app/modules/ai_team/domain_agents/`).
- **Các Agent chính:**
  1. `FounderAgent`: Tổng quan điều hành, phân tích nhịp đập doanh nghiệp, tổng hợp Daily Brief, quản trị toàn hệ thống.
  2. `SalesAgent`: Khám phá khách hàng tiềm năng (Prospecting), làm giàu dữ liệu lead (Enrichment), chấm điểm (Scoring), chăm sóc pipeline, soạn thảo thư chào hàng/báo giá.
  3. `MarketingAgent`: Nghiên cứu thị trường & ICP, lập kế hoạch chiến dịch, sinh nội dung tiếp thị, tạo khung trang đích (Landing page modules).
  4. `FinanceAgent`: Giám sát Finance Lite (Cash, Runway, Burn, Lãi ước tính), điều phối dữ liệu chứng từ sang TT58 Sổ Nhỏ.
  5. `LegalAgent`: Quản lý hồ sơ pháp lý, rà soát điều khoản hợp đồng, cảnh báo lịch tuân thủ thuế và đăng ký kinh doanh.
  6. `BuildTechAgent`: Hỗ trợ phân tích mã nguồn, tạo code block module web, kiểm thử sandbox trước khi deploy.
- **Shared Capabilities Engine (`backend/app/agents/capabilities/`):**
  - `ResearchCapability`: Tìm kiếm web, crawl tài liệu, tổng hợp dữ liệu thị trường.
  - `ReasoningCapability`: Phân tích logic, lập kế hoạch phân rã mục tiêu.
  - `ContentCapability`: Soạn thảo văn bản, email, bài viết, thông điệp marketing.
  - `AutomationCapability`: Đóng gói action payload gửi qua n8n/webhook sau approval.
  - `ReviewAuditCapability`: Kiểm tra tính nhất quán và ghi nhật ký kiểm toán.

### Task P0.3: Centralized Prompt Registry System
- **Vị trí thư mục:** `backend/app/prompts/` (lưu file Markdown template) và `backend/app/ai/prompt_registry.py`.
- **Cấu trúc lưu trữ:**
  ```text
  backend/app/prompts/
    ├── cosa/
    │   ├── system.md
    │   ├── routing.md
    │   └── founder_brief.md
    ├── sales/
    │   ├── prospect.md
    │   ├── qualify.md
    │   └── proposal_outreach.md
    ├── marketing/
    │   ├── icp_research.md
    │   ├── campaign_plan.md
    │   └── landing_copy.md
    ├── finance/
    │   └── finance_brief.md
    └── legal/
        └── contract_review.md
  ```
- **PromptRegistry Class:**
  - Nạp template, quản lý version (`prompt_version = "cosa.routing.v1"`).
  - Tự động bóc tách biến `${variable}` an toàn, cấm chèn secret/API keys.
  - Ghi nhận `prompt_version`, `model`, `latency`, `token_usage` vào bảng `ai_runs`.

### Task P0.4: 5-Layer Memory Core (L0–L4)
- **Vị trí file:** `backend/app/modules/agent_memory/models.py` và `backend/app/modules/agent_memory/service.py`.
- **Cấu trúc dữ liệu `agent_memory`:**
  - `id`: Snowflake ID 64-bit.
  - `workspace_id`: Snowflake ID (Multi-tenancy).
  - `brain_id`: Snowflake ID.
  - `layer`: Enum `L0_SESSION`, `L1_WORKING`, `L2_FOUNDER`, `L3_KNOWLEDGE`, `L4_LEARNING`.
  - `key`: String định danh (ví dụ `founder.decision_rule.transparency`, `campaign.learnings.email_q1`).
  - `value_jsonb`: Dữ liệu có cấu trúc.
  - `relevance_score`: Float.
  - `last_accessed_at`: Timestamp UTC.
- **Service APIs:**
  - `get_founder_rules(workspace_id)`: Lấy các quy tắc điều hành bất biến của Founder để tiêm vào context.
  - `record_campaign_learning(workspace_id, domain, takeaway)`: Ghi nhận bài học kinh nghiệm vào L4.
  - `get_working_memory(workspace_id)`: Lấy trạng thái công việc đang chạy trong ngày (L1).

### Task P0.5: Task Canonical Entity Hardening & Invariant Checks
- **Vị trí file:** `backend/app/modules/tasks/models.py` và `backend/app/modules/tasks/service.py`.
- **Yêu cầu kỹ thuật:**
  - Bảng `tasks` đóng vai trò nguồn chuẩn duy nhất cho 3 view: List, Calendar, Kanban.
  - Kiểm tra chu trình phụ thuộc (`DependencyCycleDetector`): Thuật toán DFS phát hiện và từ chối `task_dependencies` tạo vòng lặp (A phụ thuộc B, B phụ thuộc A).
  - Đảm bảo 100% cột khóa chính và khóa ngoại dùng Snowflake ID 64-bit.

### Task P0.6: Flutter Shell Layout & 5+1 Navigation Restructuring
- **Vị trí file:** `frontend/lib/core/routing/app_routes.dart`, `app_pages.dart`, và `frontend/lib/shared/layouts/main_shell.dart`.
- **Cấu trúc điều hướng mới:**
  - `AppRoutes.hub` (`/hub`): Hologram Hub (CEO Command Center).
  - `AppRoutes.chat` (`/chat`): COSA Companion Chat & Voice.
  - `AppRoutes.work` (`/work`): Quản lý công việc (Task List, Calendar, Kanban).
  - `AppRoutes.company` (`/company`): Sales CRM, Marketing, Finance Lite & Sổ Nhỏ, Legal.
  - `AppRoutes.brain` (`/brain`): Vault Markdown & Tri thức doanh nghiệp.
  - `AppRoutes.admin` (`/admin`): Trung tâm kỹ thuật (Prompts, Agents, MCP, Workflows, Models, Secrets, Audit).

---

## 3. Danh Sách Files Cần Tạo Mới & Chỉnh Sửa Trong Phase P0

### Backend (FastAPI / Python)
| Trạng thái | Đường dẫn file | Mục đích |
|---|---|---|
| **[MODIFY]** | `backend/app/modules/chat/conversation_gate.py` | Nâng cấp Fast-path Intent Router, phân tách greeting / brief / tasks |
| **[NEW]** | `backend/app/ai/prompt_registry.py` | Bộ quản lý tập trung và versioning cho Prompt Templates |
| **[NEW]** | `backend/app/prompts/cosa/system.md`, `routing.md`, `founder_brief.md` | Các file Markdown template prompt cốt lõi |
| **[NEW]** | `backend/app/prompts/sales/prospect.md`, `marketing/campaign.md` | Prompt template cho các Domain Agents |
| **[MODIFY]** | `backend/app/modules/agent_memory/models.py` | Schema PostgreSQL 5 tầng Memory (L0–L4) dùng Snowflake ID |
| **[MODIFY]** | `backend/app/modules/agent_memory/service.py` | Service quản lý trích xuất và lưu trữ Memory 5 tầng |
| **[NEW]** | `backend/app/agents/base_agent.py` | Abstract Base Class cho Domain Agents + Shared Capabilities |
| **[NEW]** | `backend/app/agents/founder_agent.py` | Founder Agent logic |
| **[NEW]** | `backend/app/agents/sales_agent.py` | Sales Agent logic |
| **[NEW]** | `backend/app/agents/marketing_agent.py` | Marketing Agent logic |
| **[NEW]** | `backend/app/agents/finance_agent.py` | Finance Agent logic |
| **[NEW]** | `backend/app/agents/legal_agent.py` | Legal Agent logic |
| **[MODIFY]** | `backend/app/modules/tasks/models.py` | Chuẩn hóa bảng tasks canonical, ràng buộc Snowflake ID |
| **[MODIFY]** | `backend/app/modules/tasks/service.py` | Bổ sung logic kiểm tra Dependency Cycle (DFS) |
| **[NEW]** | `backend/app/tests/test_p0_intent_router.py` | Unit tests kiểm tra Intent Router & Fast-path Greeting |
| **[NEW]** | `backend/app/tests/test_p0_memory_layers.py` | Unit tests kiểm tra 5-layer Memory |
| **[NEW]** | `backend/app/tests/test_p0_prompt_registry.py` | Unit tests kiểm tra Prompt Registry & Versioning |

### Frontend (Flutter / GetX)
| Trạng thái | Đường dẫn file | Mục đích |
|---|---|---|
| **[MODIFY]** | `frontend/lib/core/routing/app_routes.dart` | Định nghĩa 5+1 routes: `hub`, `chat`, `work`, `company`, `brain`, `admin` |
| **[MODIFY]** | `frontend/lib/core/routing/app_pages.dart` | Cấu hình binding & middleware cho các route mới |
| **[NEW]** | `frontend/lib/shared/layouts/app_shell_layout.dart` | Layout khung responsive (Sidebar 5+1 tinh gọn cho desktop/tablet/mobile) |

---

## 4. Kế Hoạch Kiểm Thử & Tiêu Chí Hoàn Thành (Definition of Done for Phase P0)

### 4.1 Automated Unit & Integration Tests (Backend Pytest)
1. `test_greeting_fast_path`:
   - Gửi các câu "chào bạn", "hello", "hi cosa", "bạn là ai".
   - Kết quả: Phản hồi trả về ngay, `GateDecision.needs_tools == False`, không phát sinh truy vấn tra cứu dự án.
2. `test_founder_brief_routing`:
   - Gửi câu "hôm nay thế nào", "tổng hợp công ty".
   - Kết quả: `GateDecision.intent == GateIntent.FOUNDER_BRIEF`.
3. `test_prompt_registry_versioning`:
   - Tải template `cosa/system.md`, render biến, kiểm tra hash và version snapshot.
4. `test_memory_layers_crud`:
   - Lưu và đọc dữ liệu tại cả 5 tầng L0, L1, L2, L3, L4 theo `workspace_id`.
5. `test_task_dependency_cycle_rejection`:
   - Thêm dependency A $\rightarrow$ B và B $\rightarrow$ A $\rightarrow$ API ném lỗi `TASK_DEPENDENCY_CYCLE`.

### 4.2 Frontend Verification
1. Chạy `flutter analyze` bảo đảm 0 lỗi cú pháp / type error.
2. Thanh Sidebar hiển thị đúng 5 mục chính (`Hub`, `COSA`, `Work`, `Company`, `Brain`) và nút `Admin` ở góc dưới.

---
*(Bản kế hoạch chi tiết Phase P0 đã được lưu trữ và sẵn sàng để bạn duyệt trước khi bắt đầu thực hiện).*
