# COSA CO-FOUNDER ARCHITECTURE (F4 SPEC)
## PHASE 3 IMPLEMENTATION PLAN: DOMAIN WORKFORCE & SHARED CAPABILITIES STANDARD

> **Mục tiêu:** Chuẩn hóa 5 Core Domain Agents (`Sales`, `Marketing`, `Finance`, `Legal`, `Build/Tech`), chuyển đổi triệt để các Agent Anti-Patterns cũ thành **Shared Capabilities** (`investigate`) và **Cross-Cutting Policies** (`QualityGatePolicy`), đồng thời thiết lập cơ chế quản lý **Optional Packs** (`Operations`, `HR/People`, `Customer Support`).

---

## 1. PHÂN TÍCH KIẾN TRÚC & TIÊU CHUẨN (F4 SPECIFICATION)

```text
                                HUMAN FOUNDER
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │      COSA CO-FOUNDER      │
                        └─────────────┬─────────────┘
                                      │
           ┌──────────────────────────┼──────────────────────────┐
           ▼                          ▼                          ▼
     [Mission / Task]           [Evidence Query]          [Decision Proposal]
           │                          │                          │
           └──────────────────────────┼──────────────────────────┘
                                      ▼
                  ┌───────────────────────────────────────┐
                  │          CORE DOMAIN WORKFORCE        │
                  │  ┌─────────┐ ┌─────────┐ ┌─────────┐  │
                  │  │  Sales  │ │Marketing│ │ Finance │  │
                  │  └─────────┘ └─────────┘ └─────────┘  │
                  │  ┌─────────┐ ┌─────────┐              │
                  │  │  Legal  │ │  Build  │              │
                  │  └─────────┘ └─────────┘              │
                  └───────────────────┬───────────────────┘
                                      │
       ┌──────────────────────────────┴──────────────────────────────┐
       ▼                                                             ▼
[SHARED CAPABILITY]                                         [CROSS-CUTTING POLICY]
  `investigate`                                               `QualityGatePolicy`
(Fact, Web, Docs, Data)                                     (Completeness, Evidence,
       │                                                      Compliance, Actionable)
       ▼                                                             │
[TOOL REGISTRY]                                                      ▼
(CRM, TT58, Sandbox, Policy)                                   [WORK PRODUCT]
```

---

## 2. CHUYỂN ĐỔI CÁC ANTI-PATTERNS (F4 MỤC 6 & MỤC 29-30)

| Anti-Pattern Cũ | Khuyết điểm | Giải pháp Chuẩn hóa F4 |
| :--- | :--- | :--- |
| **Strategy Agent** | Tách rời chiến lược khỏi Co-Founder, sinh thừa bot | $\rightarrow$ **Năng lực tư duy trực thuộc COSA Co-Founder** (`CosaCofounderService`). |
| **Research Agent** | Biến việc tìm kiếm thông tin thành một bot độc lập | $\rightarrow$ **Shared Capability `investigate`**: Mọi Domain Agent & Co-Founder đều dùng chung để tra cứu web, tài liệu và dữ liệu thực tế. |
| **QA / Quality Agent** | Bot kiểm thử riêng lẻ, hoạt động muộn màng | $\rightarrow$ **Cross-Cutting `QualityGatePolicy`**: Chính sách tự động kiểm tra chất lượng của tất cả `WorkProduct` trước khi bàn giao. |
| **Automation Agent** | Gọi bot để chạy cron/webhook | $\rightarrow$ **Tool Registry & Background Triggers** (n8n, cron, webhook, celery). |
| **Voice Agent** | Tách riêng bot nói chuyện | $\rightarrow$ **Phương thức tương tác (Modality)** kết nối trực tiếp vào COSA Co-Founder. |
| **Domain Taxonomy** | Tạo bot cho từng việc nhỏ (SEO, Cold Mail...) | $\rightarrow$ **Specialist Capabilities bên trong Domain Agent tương ứng** (ví dụ: SEO specialist nằm trong Marketing). |

---

## 3. CHI TIẾT 5 CORE DOMAIN AGENTS & OPTIONAL PACKS

### 3.1. 5 Core Domain Agents (Luôn hoạt động mặc định)
1. **Sales Agent (`sales` / `sales_agent`):**
   - *Trách nhiệm:* Pipeline, Lead qualification (BANT/MEDDPICC), Outbound sequences, Follow-up scripts, CRM sync.
   - *Tools chính:* `crm_pipeline_tool`, `lead_enrich_tool`, `outbound_composer_tool`.
2. **Marketing Agent (`marketing` / `cmo_agent`):**
   - *Trách nhiệm:* ICP definition, Positioning, Copywriting, SEO/Content Calendar, Ad campaign design, Messaging test.
   - *Tools chính:* `copywriting_tool`, `seo_analyzer_tool`, `campaign_planner_tool`.
3. **Finance Agent (`finance` / `cfo_agent`):**
   - *Trách nhiệm:* Chuẩn kế toán Việt Nam TT58, Hệ thống tài khoản, Báo cáo dòng tiền, Runway calculation, Unit Economics (LTV/CAC, Payback).
   - *Tools chính:* `tt58_accounting_tool`, `cashflow_runway_tool`, `unit_economics_tool`.
4. **Legal Agent (`legal` / `legal_agent`):**
   - *Trách nhiệm:* Soạn thảo & rà soát hợp đồng, Tuân thủ Nghị định 13/2023/NĐ-CP (bảo vệ dữ liệu cá nhân), Luật Doanh nghiệp VN, Cảnh báo rủi ro pháp lý.
   - *Tools chính:* `contract_review_tool`, `vn_law_compliance_tool`, `nda_generator_tool`.
5. **Build / Tech Agent (`developer` / `tech_lead_agent`):**
   - *Trách nhiệm:* Kiến trúc kỹ thuật, PR Review, Issue triage, Landing Page generator, Sandbox code execution & verification.
   - *Tools chính:* `github_pr_tool`, `landing_page_builder_tool`, `code_sandbox_tool`.

---

### 3.2. Optional Packs (Gói mở rộng cài đặt thêm)
- **Operations Pack (`operations_agent`):** Quản lý chuỗi cung ứng, tồn kho, SOPs, quy trình fulfillment.
- **People / HR Pack (`hr_agent`):** Mô tả công việc (JD), sàng lọc CV, quy trình onboarding nhân sự mới.
- **Customer Support Pack (`support_agent`):** Phân loại ticket, gợi ý phản hồi CSKH, phân tích CSAT.

*Cơ chế:* Mặc định `is_default_active: False`. Founder kích hoạt thông qua Workspace Settings khi doanh nghiệp mở rộng quy mô.

---

## 4. TRIỂN KHAI SHARED CAPABILITY & QUALITY GATE

### 4.1. Shared Capability `investigate` (`backend/app/workforce/capabilities/investigate_service.py`)
Cung cấp phương thức điều tra đa nguồn:
- **`investigate_query(query, sources=["web", "memory", "documents"])`**:
  - Tra cứu Google Search (qua `google_search` tool).
  - Tra cứu Vector Memory / RAG nội bộ.
  - Tổng hợp thành **Evidence Item** có Fact, Source URL, Confidence Score và Snippet (F1/F3 Evidence format).

### 4.2. Cross-Cutting `QualityGatePolicy` (`backend/app/workforce/governance/quality_gate_policy.py`)
Mọi `WorkProduct` sinh ra từ bất kỳ Domain Agent nào đều phải trải qua `QualityGatePolicy.evaluate_work_product()`:
1. **Completeness Check:** Kiểm tra cấu trúc nội dung, độ dài, tính đầy đủ của các mục bắt buộc.
2. **Evidence-Backed Check:** Bắt buộc có dữ kiện hoặc dẫn chứng thực tế cho các tuyên bố quan trọng.
3. **Policy & Budget Compliance:** Kiểm tra không vượt ngân sách cho phép và không vi phạm điều khoản pháp lý.
4. **Actionability Check:** Có các bước hành động tiếp theo cụ thể (Next steps) cho Founder hoặc Team.

---

## 5. CÁC BƯỚC THỰC HIỆN CHI TIẾT (STEP-BY-STEP)

### Bước 1: Chuẩn hóa 5 Core Domain Manifests & System Prompts
- Cập nhật [backend/app/workforce/registry/defaults.py](file:///Volumes/SSD/javis-saas/backend/app/workforce/registry/defaults.py) với System Prompts chuyên sâu cho từng domain.
- Đảm bảo 5 core domain agents có tools gắn kèm chuẩn hóa.

### Bước 2: Xây dựng Shared Capability `InvestigateService`
- Tạo file `backend/app/workforce/capabilities/investigate_service.py`:
  - `investigate_query()`: Tìm kiếm và trích xuất Evidence.
  - Tích hợp với `EvidenceEngine` (F1/F3) và `ToolRegistry`.

### Bước 3: Xây dựng `QualityGatePolicy`
- Tạo file `backend/app/workforce/governance/quality_gate_policy.py`:
  - `evaluate_work_product()`: Đánh giá điểm chất lượng theo 4 tiêu chí.
  - Tích hợp tự động vào `WorkProductService`.

### Bước 4: Xây dựng Optional Packs Management & REST APIs
- Tạo file `backend/app/workforce/api/packs_api.py`:
  - `GET /api/v1/workforce/packs`: Danh sách các packs (Core & Optional).
  - `POST /api/v1/workforce/packs/{pack_key}/toggle`: Bật/Tắt Optional Pack cho Workspace.

### Bước 5: Viết Unit Tests & Acceptance Verification cho Phase 3
- Tạo file `backend/app/tests/workforce/test_phase3_domain_workforce.py`:
  - **Test 1:** Xác minh 5 Core Domains có Manifest, System Prompt và Category `DOMAIN`.
  - **Test 2:** Xác minh Shared Capability `investigate` hoạt động cho đa Agent.
  - **Test 3:** Xác minh `QualityGatePolicy` đánh giá và gắn nhãn chất lượng cho Work Product.
  - **Test 4:** Xác minh cơ chế Bật/Tắt Optional Packs theo Workspace.

---

## 6. CHECKLIST NGHIỆM THU PHASE 3

- [ ] 5 Core Domain Manifests được cấu hình đầy đủ và chuẩn xác.
- [ ] Shared Capability `investigate` thay thế hoàn toàn Research Agent cũ.
- [ ] `QualityGatePolicy` thay thế hoàn toàn QA Agent cũ và đánh giá Work Product tự động.
- [ ] Optional Packs (`Operations`, `HR`, `Support`) hỗ trợ Bật/Tắt theo nhu cầu của Workspace.
- [ ] API endpoints `/api/v1/workforce/packs` hoạt động ổn định.
- [ ] Toàn bộ unit tests của Phase 3 pass 100% không cảnh báo.
