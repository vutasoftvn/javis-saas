# Kế Hoạch Tổng Thể & Chi Tiết Kiến Trúc COSA Founder Operating System
> **Phiên bản đã cập nhật:** Loại bỏ toàn bộ chuỗi phân tích chiến lược cồng kềnh (PESTEL 6x3, SWOT 4x3, TOWS 4x3, BSC Strategy Map DAG).
> **Trọng tâm tinh gọn:** Tập trung 100% vào **Hệ điều hành Founder Thực thi (Execution-First Founder OS)**:
> - `COSA Companion & Conversation Intent Router` (Sửa triệt để lỗi routing).
> - `Hologram Hub` (CEO Command Center: Pulse, Today Priorities, Active Missions, Approvals).
> - `Work System` (Task là Canonical Entity cho List/Calendar/Kanban; Kế hoạch tuần & Mục tiêu tinh gọn).
> - `Revenue Engine` (Marketing $\rightarrow$ CRM $\rightarrow$ Sales $\rightarrow$ Vòng lặp doanh thu).
> - `Finance Lite & TT58 Sổ Nhỏ` (Tài chính hằng ngày & Kế toán siêu nhỏ chuẩn Thông tư 58/2026/TT-BTC).
> - `Automation & Infrastructure` (n8n, MCP, Channel Adapters, Outbox Pattern, Prompt Registry & 5-Layer Memory).

---

## 1. Tầm Nhìn & Kiến Trúc Tinh Gọn (Consolidated Architecture)

### 1.1 Định vị COSA Tinh Gọn
**COSA (Company Operating System & Autonomous Agent)** là **Hệ điều hành Doanh nghiệp 1 người (Founder / OPC)**:
- **Tương tác cốt lõi:** Founder giao tiếp qua **Chat / Voice / Hologram Hub**.
- **Điều phối thông minh:** Intent Router phân loại ý định hội thoại (Smalltalk, Tra cứu, Tác vụ, Mission, Quản trị) trước khi chạm vào bất kỳ Tool/Agent nào.
- **5 Domain Agents chủ lực:** `Founder Agent`, `Sales Agent`, `Marketing Agent`, `Finance Agent`, `Legal Agent` (+ `Build/Tech Agent`), sử dụng chung kho Capability dùng chung (Research, Reasoning, Content, Automation, Data, Review, Coding).
- **Loại bỏ rườm rà:** Không nhồi nhét ma trận PESTEL/SWOT/TOWS/BSC DAG vào luồng vận hành chính; thay vào đó, mục tiêu và cam kết tuần được gắn trực tiếp vào Task và Mission thực tế.

```
Founder (Voice / Chat / Hologram Hub)
               │
               ▼
        COSA Companion
               │
               ▼
     Conversation Intent Router (Lọc chat thường / Brief / Lệnh tác vụ)
               │
               ▼
        Goal / Mission / Context
               │
               ▼
       Capability & Domain Router
               │
 ┌─────────────┼─────────────┬─────────────┬─────────────┐
 ▼             ▼             ▼             ▼             ▼
Sales      Marketing      Finance        Legal         Build
Agent        Agent         Agent         Agent         Agent
 │             │             │             │             │
 └─────────────┴─────────────┼─────────────┴─────────────┘
                             ▼
                Shared Capability Engine
        (Research · Reasoning · Content · Code · Audit)
                             │
                             ▼
               Tool / Workflow / MCP / n8n
                             │
                             ▼
                 Policy & Gate Approval
            (Read-only / Draft / External)
                             │
                             ▼
                      Execute & Outbox
                             │
                             ▼
               Observe & 5-Layer Memory
```

### 1.2 Cấu trúc Giao diện & Điều hướng Tinh gọn (5+1 Layout)
Thanh điều hướng Flutter được cố định gồm **5 khu vực nghiệp vụ** + **1 khu vực quản trị kỹ thuật**:

1. **`Hub (Hologram Hub)`**: CEO Command Center hiển thị Company Pulse, 1–3 Việc ưu tiên hôm nay, Active Missions, Approvals đang chờ.
2. **`COSA (Companion)`**: Trò chuyện Chat & Voice tương tác thời gian thực.
3. **`Work (Quản trị Công việc)`**: Task Canonical Entity với 3 chế độ xem `List`, `Calendar`, `Kanban` + Mục tiêu & Kế hoạch tuần tinh gọn.
4. **`Company (Vận hành Doanh nghiệp)`**:
   - `Overview`: Bức tranh tổng thể công ty.
   - `Sales`: CRM Pipeline, Khách hàng, Cơ hội bán hàng, Chăm sóc & Báo giá.
   - `Marketing`: Nghiên cứu ICP, Chiến dịch, Landing Page Modules, Form thu thập Lead.
   - `Finance`: Finance Lite (Dòng tiền, Runway, Burn rate) & TT58 Sổ Nhỏ (Chứng từ, Sổ S1–S4, BCTC B01/B02).
   - `Legal`: Hồ sơ pháp lý, Hợp đồng, Lịch tuân thủ thuế.
   - `Projects`: Quản lý các dự án/sản phẩm trọng điểm.
5. **`Brain (Tri thức & Bộ nhớ)`**: Knowledge Vault Markdown, SOPs, Templates, Lịch sử quyết định.
6. **`Admin (Kỹ thuật & Hạ tầng - Chỉ Founder/Admin thấy)`**: Quản lý Prompts, Agents, Skills, Workflows, MCP, Tools, Models, Channels, Secrets, Audit Logs.

---

## 2. Phân Rã Domain Nghiệp Vụ & Kỹ Thuật

### Domain 1: Conversation Intent Router & COSA Companion
- **Mục tiêu:** Chấm dứt triệt để lỗi routing sai khi người dùng nói chuyện thông thường.
- **Phân loại Intent trước Tool:**
  1. `greeting` / `conversation`: Chào hỏi, trò chuyện tự nhiên $\rightarrow$ Trả lời trực tiếp ngay lập tức, **0 tool call**.
  2. `founder_brief`: "Hôm nay thế nào?", "Báo cáo nhanh" $\rightarrow$ Tổng hợp Pulse, Top 3 Task, Pending Approvals, Active Missions.
  3. `search_knowledge`: "Chính sách X là gì?", "Tìm tài liệu Y" $\rightarrow$ Hybrid Search (FTS + pgvector) vào Vault Markdown có trích dẫn (citation).
  4. `task_command`: "Tạo task...", "Lên lịch việc..." $\rightarrow$ Tạo Task draft, hiển thị preview có cấu trúc, chờ xác nhận.
  5. `mission_command`: "Tìm 20 khách hàng cho sản phẩm A", "Lập chiến dịch ra mắt" $\rightarrow$ Khởi tạo Mission, phân rã công việc cho Sales/Marketing Agent.
  6. `system_admin`: Tra cứu tình trạng worker, logs (chỉ Founder/Admin).
- **Prompt Registry:** Quản lý toàn bộ prompt trong thư mục cấu trúc (`prompts/cosa/`, `prompts/sales/`, `prompts/marketing/`, `prompts/finance/`, `prompts/legal/`), versioned, liên kết `ai_runs` ghi lại token cost, latency, model, revision.
- **5-Layer Memory Architecture:**
  - `L0 Session`: Ngữ cảnh phiên hội thoại hiện tại.
  - `L1 Working Memory`: Trạng thái các Mission và Task đang thực thi trong ngày.
  - `L2 Founder Memory`: Quy tắc quyết định, phong cách điều hành, thông tin nhận diện của Founder.
  - `L3 Company Knowledge`: Vault Markdown, Wiki, Danh mục khách hàng, SOP đã duyệt.
  - `L4 Learning / Pattern Memory`: Kinh nghiệm chiến dịch, các phản hồi thị trường để tránh lặp lại sai lầm.

### Domain 2: Work Execution Engine & Hologram Hub
- **Task là Nguồn Chuẩn Duy Nhất (Canonical Entity):**
  - Bảng `tasks` trong PostgreSQL quản lý toàn bộ: `id` (Snowflake), `workspace_id`, `parent_task_id`, `assignee_id`, `title`, `status` (`inbox`, `planned`, `in_progress`, `blocked`, `waiting_approval`, `done`, `cancelled`), `priority`, `planned_start_at`, `due_at`, `timezone`, `sort_key`, `source`.
  - `List`, `Calendar`, `Kanban` chỉ là 3 chế độ xem (views) của cùng một dữ liệu Task. Kéo thả Kanban hay đổi ngày trên Calendar chỉ là mutation thay đổi `status` / `dates` trên cùng bảng `tasks`.
  - Hỗ trợ quan hệ phụ thuộc (`task_dependencies`) có kiểm tra cấm vòng lặp (cycle check).
- **Lập Kế Hoạch & Mục Tiêu Tinh Gọn (Lean Goals & Weekly Focus):**
  - Thay vì BSC/PESTEL/SWOT cồng kềnh, hệ thống sử dụng cấu trúc tinh gọn:
    - **Company Objectives (Mục tiêu quý/năm):** 1–3 mục tiêu trọng tâm có chỉ số đo lường rõ ràng.
    - **Weekly Focus (Kế hoạch tuần):** 3 cam kết lớn (Big 3) trong tuần.
    - **Daily Focus:** 1–3 việc ưu tiên trong ngày gắn với Kế hoạch tuần.
- **Workflow Binding & Scheduler:**
  - Task có thể liên kết với một định nghĩa workflow (`task_workflow_bindings`).
  - Lịch chạy (`task_schedules`) định kỳ được worker kích hoạt qua `task.schedule_tick`, sinh `workflow_runs` mới kèm `idempotency_key` (không tạo duplicate run).
- **Hologram Hub (CEO Command Center):**
  - Visual hóa nhịp đập công ty: Company Pulse (Sales ↑, Cash →, Marketing ↑, Ops ✓), 3 Việc ưu tiên hôm nay, Tiến độ Active Missions, Nút Approve nhanh cho các yêu cầu đang chờ.

### Domain 3: Revenue Engine (Marketing $\rightarrow$ CRM $\rightarrow$ Sales)
- **Vòng Lặp Khép Kín (Closed Loop Revenue Engine):**
  1. `Market Research & ICP`: Xác định chân dung khách hàng và thông điệp.
  2. `Campaign Management`: Tạo chiến dịch Marketing đa kênh.
  3. `Landing Page Generation`: Tạo trang đích từ các module tái sử dụng (`Hero`, `Features`, `Pricing`, `LeadForm`...).
  4. `Lead Capture & Ingestion`: Thu thập lead qua form/webhook vào CRM chung.
  5. `Lead Enrichment & Scoring`: Phân loại và chấm điểm mức độ tiềm năng của Lead.
  6. `Sales Opportunity Pipeline`: Quản lý deal/pipeline bán hàng.
  7. `Outreach Draft (Email/Zalo/Telegram)`: AI soạn thảo nội dung tiếp cận, gửi vào hàng đợi `approvals`.
  8. `Founder Approval & Outbox Send`: Founder duyệt $\rightarrow$ Outbox gửi tin an toàn qua Resend / Channel Adapter.
  9. `Feedback & Learning`: Kết quả chuyển đổi được ghi nhận lại vào `L4 Memory` để tối ưu chiến dịch sau.

### Domain 4: Finance Lite & SaaS Kế Toán TT58 "Sổ Nhỏ"
- **Finance Lite (Hằng ngày cho Founder):**
  - Hiển thị trực quan trên Hub/Chat: Tiền mặt/Ngân hàng hiện có, Doanh thu kỳ này, Chi phí phát sinh, Công nợ phải thu/phải trả, Runway (tháng), Tốc độ đốt tiền (Burn rate), Lợi nhuận ước tính.
- **Sổ Nhỏ - Kế toán Doanh nghiệp siêu nhỏ theo TT 58/2026/TT-BTC:**
  - **4 Hồ sơ thuế theo phương pháp tính:**
    - `P1`: GTGT % doanh thu + TNDN % doanh thu $\rightarrow$ Sổ bắt buộc `S1-DNSN`.
    - `P2`: GTGT % doanh thu + TNDN trên thu nhập tính thuế $\rightarrow$ Sổ `S2a, S2b, S2c, S2d-DNSN`.
    - `P3`: GTGT khấu trừ + TNDN % doanh thu $\rightarrow$ Sổ `S3a, S3b-DNSN`.
    - `P4`: GTGT khấu trừ + TNDN trên thu nhập tính thuế $\rightarrow$ Sổ `S2b, S2c, S2d, S3b-DNSN`.
    - Sổ quản trị tự chọn: `S4a` (Công nợ), `S4b` (TSCĐ), `S4c` (Thuế khác), `S4d` (Vốn chủ sở hữu).
  - **Cơ chế Document-Driven:**
    - Chứng từ (`documents` + `document_lines`) là nguồn dữ liệu chuẩn duy nhất.
    - Engine ghi sổ tự động sinh các dòng sổ kế toán (`register_entries`) có liên kết truy vết về chứng từ nguồn.
    - Không xóa cứng chứng từ đã `POSTED`; chỉ cho phép `VOIDED` hoặc lập chứng từ điều chỉnh kèm Audit Trail.
  - **Kho & Tính giá xuất kho:**
    - Tính đơn giá xuất kho theo phương pháp Bình quân cả kỳ:
      $$\text{Đơn giá xuất} = \frac{\text{Giá trị tồn đầu kỳ} + \text{Giá trị nhập trong kỳ}}{\text{Số lượng tồn đầu kỳ} + \text{Số lượng nhập trong kỳ}}$$
    - Chặn xuất âm kho theo mặc định.
  - **Báo cáo Tài chính B01 & B02:**
    - `B01-DNSN` (Tình hình tài chính): Bắt buộc kiểm tra cân đối $\text{Tổng tài sản} = \text{Tổng nguồn vốn}$.
    - `B02-DNSN` (Kết quả hoạt động kinh doanh): $\text{Lợi nhuận trước thuế} = \text{Doanh thu thuần} - \text{Chi phí}$; $\text{Lợi nhuận sau thuế} = \text{Lợi nhuận trước thuế} - \text{Chi phí TNDN}$.
  - **Khóa sổ & Kỳ kế toán:**
    - Khóa sổ theo tháng/quý/năm. Kỳ đã khóa chỉ được mở lại bởi `OWNER` kèm lý do và audit log.
    - Thời hạn báo cáo tài chính năm: 90 ngày sau khi kết thúc năm tài chính.

### Domain 5: Legal, Build Agent & Automation Runtime
- **Legal Agent:** Quản lý hồ sơ pháp lý, kho hợp đồng, lịch tuân thủ thuế/đăng ký kinh doanh, phân tích rủi ro hợp đồng, soạn thảo văn bản mẫu.
- **Build / Tech Agent:** Hỗ trợ Founder phân tích mã nguồn, tạo module landing page Next.js, cấu hình form webhook, kiểm thử sandbox trước khi deploy.
- **Automation Runtime (n8n / MCP / Outbox):**
  - n8n hoạt động như một Automation Engine kết nối bên dưới, không phải là Brain.
  - Mọi hành động gửi tin ra ngoài, xuất bản web, chuyển tiền đều phải qua cơ chế **Approval Snapshot**: `Agent Request` $\rightarrow$ `Policy Check` $\rightarrow$ `Pending Approval` $\rightarrow$ `Founder Approve` $\rightarrow$ `Durable Outbox Queue` $\rightarrow$ `Channel Adapter Delivery`.

---

## 3. Thiết Kế Cơ Sở Dữ Liệu PostgreSQL Tinh Gọn (Data Model)

Toàn bộ Primary Key sử dụng **Snowflake ID 64-bit (`BIGINT`)**; mọi bảng domain đều có `workspace_id BIGINT NOT NULL` và Audit Trail đầy đủ:

```
1. Identity & Tenancy
   - users (id, email, display_name, status, created_at)
   - workspaces (id, name, plan, created_by, created_at)
   - workspace_members (workspace_id, user_id, role, created_at)
   - brains (id, workspace_id, name, settings_jsonb)

2. Goals & Work Execution System
   - company_objectives (id, workspace_id, brain_id, title, target_metric, baseline_value, target_value, status, period)
   - weekly_plans (id, workspace_id, week_no, year, focus_theme, execution_score, blockers_jsonb, reflection)
   - tasks (id, workspace_id, brain_id, parent_task_id, company_objective_id, weekly_plan_id, assignee_id, title, status, priority, planned_start_at, due_at, timezone, sort_key, source)
   - task_dependencies (task_id, depends_on_task_id, dependency_type)
   - task_schedules (id, task_id, kind, rrule, run_at, timezone, next_run_at, active)
   - task_workflow_bindings (id, task_id, workflow_version_id, input_template_jsonb, active)
   - workflow_definitions (id, brain_id, slug, current_version_id)
   - workflow_versions (id, definition_id, revision_id, graph_jsonb, version_no)
   - workflow_runs (id, version_id, task_id, status, trigger, input_jsonb, idempotency_key)
   - workflow_steps (id, run_id, node_id, status, attempt, output_jsonb)
   - approvals (id, run_id, step_id, action_type, payload_jsonb, status, expires_at, approved_by, approved_at)
   - jobs (id, type, payload_jsonb, status, scheduled_at, locked_at, attempts)
   - outbox (id, channel, payload_jsonb, status, dedupe_key, attempts)
   - ai_runs (id, workflow_run_id, prompt_version, provider, model, mode, input_hash, usage_jsonb, cost_estimate)

3. Revenue Engine & CRM
   - crm_leads (id, workspace_id, name, email, phone, company, source, score, status, tags_jsonb)
   - crm_contacts (id, workspace_id, lead_id, full_name, email, phone, role)
   - crm_companies (id, workspace_id, name, industry, size, website)
   - crm_opportunities (id, workspace_id, contact_id, company_id, title, value, stage, probability, close_date)
   - crm_activities (id, workspace_id, opportunity_id, activity_type, summary, details, created_by)
   - marketing_campaigns (id, workspace_id, name, goal, budget, channels_jsonb, status)
   - landing_pages (id, workspace_id, campaign_id, slug, title, modules_jsonb, status)

4. Finance & SaaS Kế Toán TT58 (Sổ Nhỏ)
   - fiscal_years, accounting_periods, accounting_policy_versions, signing_profiles
   - tax_rules, revenue_tax_groups, tax_obligations, tax_payments
   - parties (khách hàng/nhà cung cấp), items (hàng hóa/vật tư), warehouses, cash_accounts, bank_accounts
   - documents (id, workspace_id, document_type, document_no, document_date, accounting_date, status, description, currency, total_amount, source_document_id, posted_at, posted_by)
   - document_lines (id, document_id, line_no, item_id, description, quantity, unit_price, amount, vat_rate, vat_amount, tax_rule_id)
   - register_entries (id, workspace_id, register_code [S1/S2a-d/S3a-b/S4a-d], row_type, row_key, accounting_date, amount, quantity, tax_rule_id, source_document_id, source_line_id, policy_version_id)
   - cash_transactions, obligations, settlements
   - inventory_movements, inventory_period_valuations (đơn giá bình quân)
   - fixed_assets, depreciation_runs, equity_movements
   - report_runs, report_files, period_closures

5. Knowledge, Chat & Memory
   - vault_documents (id, brain_id, path, kind, current_revision_id, status)
   - vault_revisions (id, document_id, object_key, sha256, size_bytes, created_by)
   - document_chunks (id, revision_id, ordinal, text, fts, embedding)
   - chat_sessions, chat_messages (client_message_id idempotent)
   - agent_memory (id, workspace_id, brain_id, layer [L0..L4], key, value_jsonb, relevance_score, last_accessed_at)
   - audit_logs (id, workspace_id, actor_type, actor_id, action, target_type, target_id, metadata_jsonb)
```

---

## 4. Lộ Trình Triển Khai Master (Phased Implementation Roadmap)

```
┌────────────────────────────────────────────────────────────────────────┐
│ PHASE P0: COSA Core Runtime, Intent Router & 5-Layer Memory Core       │
│ - Conversation Intent Classifier (xử lý triệt để routing chào/hỏi)    │
│ - 5 Domain Agents skeleton, Task canonical CRUD, Prompt/Tool Registry  │
│ - Memory schema L0-L4, Snowflake ID standard enforcement               │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│ PHASE P1: Hologram Hub & CEO Command Center                            │
│ - Hologram Hub UI: Company Pulse, Today Top 3, Active Missions         │
│ - Quick Approval Cards, Chat & Voice Unified Companion Session         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│ PHASE P2: Revenue Engine (Marketing + CRM + Sales)                     │
│ - Closed-loop: ICP Research → Campaign → Landing Page → Lead Capture   │
│ - CRM Pipeline, Lead Scoring, Outreach Draft → Approval → Send         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│ PHASE P3: Automation Gateway & Channels                                │
│ - n8n Automation Gateway, Telegram & Zalo Channel Adapters             │
│ - Durable Outbox, Idempotency Deduplication, Retry & Error Handling   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│ PHASE P4: Company Operations (Finance Lite & TT58 Sổ Nhỏ, Legal, Build)│
│ - Finance Lite dashboard & TT58 Accounting Engine (P1-P4 profiles)     │
│ - Document-driven Register Entries (S1-S4), B01/B02, Kho bình quân     │
│ - Legal Agent & Build/Tech Agent Sandbox                               │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│ PHASE P5: Intelligence Optimization & Multi-Device Hardening           │
│ - DSPy Prompt Evaluation & Tuning, Pattern Learning (L4 Memory)        │
│ - SQLite Offline Cache Sync, Performance & Accessibility Polish        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Tiêu Chí Nghiệm Thu Toàn Diện (Definition of Done)

1. **Routing Hội Thoại:**
   - Chat "chào", "hello", "bạn là ai" trả lời ngay lập tức (< 500ms), không gọi tool hay DB query nặng.
   - Chat "Hôm nay có gì?", "Tình hình công ty" trả lời đúng Founder Daily Brief (Pulse, Top 3, Approvals, Missions).
2. **Quản Trị Tác Vụ:**
   - Bảng `tasks` là nguồn chuẩn duy nhất; chuyển trạng thái ở Kanban hay thay đổi ngày ở Calendar đồng bộ tức thì trên List và SQLite client cache.
3. **Vận Hành Doanh Thu:**
   - Tạo chiến dịch $\rightarrow$ Xuất bản Landing page $\rightarrow$ Điền form $\rightarrow$ Lead đổ về CRM $\rightarrow$ Phân loại tiềm năng $\rightarrow$ Soạn thư chào hàng $\rightarrow$ Founder duyệt $\rightarrow$ Outbox gửi tin thành công.
4. **Kế Toán TT58 (Sổ Nhỏ):**
   - Nhập chứng từ bán hàng/mua hàng/thu/chi tự động sinh dòng sổ S1/S2/S3/S4 tương ứng 4 hồ sơ thuế P1–P4; tính đúng giá xuất kho bình quân cả kỳ; sinh BCTC B01 cân đối tuyệt đối ($\text{Tài sản} = \text{Nguồn vốn}$) và B02 chuẩn biểu mẫu TT 58/2026/TT-BTC.
5. **Bảo Mật & An Toàn:**
   - 100% ID dùng chuẩn Snowflake 64-bit; các hành động gửi tin/chi tiền bên ngoài bắt buộc có Founder Approval Snapshot; không rò rỉ secret/API keys ở client hay log.
