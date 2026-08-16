# Kế Hoạch Triển Khai Chi Tiết: Giai Đoạn P2 (Phase 2)
## Revenue Engine: Marketing $\rightarrow$ CRM $\rightarrow$ Sales (Vòng Lặp Doanh Thu Khép Kín)

> **Mục tiêu của Phase P2:**
> Xây dựng và tích hợp hoàn chỉnh cỗ máy doanh thu khép kín (**Closed-Loop Revenue Engine**) cho doanh nghiệp:
> - **Khép kín 9 mắt xích doanh thu:** *Nghiên cứu ICP & Thông điệp $\rightarrow$ Quản lý Chiến dịch $\rightarrow$ Tạo Modular Landing Page $\rightarrow$ Thu thập Lead (Form/Webhook) $\rightarrow$ AI Chấm điểm & Phân loại Lead $\rightarrow$ Pipeline Cơ hội Bán hàng (Deal Kanban) $\rightarrow$ AI Soạn thảo Thư tiếp cận (Outreach Draft) $\rightarrow$ Phê duyệt Founder $\rightarrow$ Đẩy Outbox Gửi tin an toàn $\rightarrow$ Học tập & Tối ưu hóa (L4 Pattern Memory).*
> - Tích hợp chặt chẽ với **CEO Command Center (Phase 1)**: Mọi chỉ số lead mới, deal giá trị cao và thư tiếp cận chờ duyệt đều xuất hiện trực tiếp trên Hologram Hub.
> - Tuân thủ nghiêm ngặt chuẩn Snowflake ID 64-bit, cô lập tenant workspace server-side, và 0 legacy runtime dependency.

---

## 1. Cấu Trúc Kiến Trúc & Luồng Dữ Liệu Phase P2

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   PHASE P2: CLOSED-LOOP REVENUE ENGINE                                 │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                        │
│  [1. ICP & Messaging] ──► [2. Campaign Studio] ──► [3. Modular Landing Page] ──► [4. Public Lead Form] │
│           │                                                                             │              │
│           ▼                                                                             ▼              │
│  [9. L4 Memory Learning] ◄── [8. Outbox Sent] ◄── [7. Founder Approve] ◄── [6. Outreach Draft & Deals] │
│                                                                                                        │
└───────────────────────────────────────────────────▲────────────────────────────────────────────────────┘
                                                    │ REST API + Webhooks
┌───────────────────────────────────────────────────┴────────────────────────────────────────────────────┐
│                                   BACKEND: RevenueEngineService (FastAPI)                              │
│  - ICP & Positioning Engine: Quản lý chân dung khách hàng mục tiêu và ma trận thông điệp              │
│  - Landing Page Generator: Render modules JSON (Hero, Features, Pricing, LeadCapture) & Public Webhook │
│  - Lead Ingestion & AI Scoring: Phân loại FIT/INTENT/ENGAGEMENT score (0–100)                          │
│  - Opportunity Pipeline Manager: Quản lý deal stage Kanban (Discovery → Proposal → Won/Lost)           │
│  - Outreach Generator & Approval Bridge: Soạn thảo email/zalo cá nhân hóa, đẩy vào PendingApproval    │
│  - Feedback & Pattern Memory Recorder: Cập nhật tỷ lệ chuyển đổi vào agent_memory (Layer L4)          │
└───────────────────────────────────────────────────▲────────────────────────────────────────────────────┘
                                                    │
        ┌───────────────────────────────────────────┼───────────────────────────────────────────┐
        ▼                                           ▼                                           ▼
  marketing_contexts                          sales_leads &                               approvals & outbox
  marketing_campaigns                       sales_opportunities                         agent_memory (L4)
  campaign_assets                             contacts & accounts
```

---

## 2. Chi Tiết Các Nhiệm Vụ Kỹ Thuật Trong Phase P2

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ TASK P2.1: ICP & Marketing Campaign Studio                                       │
│ - Backend: CRUD Marketing Context (ICP, Persona, Brand Voice, Value Proposition)│
│ - Backend: Quản lý Campaign (Mục tiêu, Ngân sách, Kênh triển khai, Assets)      │
│ - Frontend: Giao diện thiết lập ICP & Bảng điều khiển Chiến dịch đa kênh        │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
┌───────────────────────────────────────▼─────────────────────────────────────────┐
│ TASK P2.2: Modular Landing Page Generator & Public Ingestion Webhook            │
│ - Backend: Endpoint công khai POST /api/v1/public/landing-pages/{slug}/lead     │
│ - Backend: Cấu trúc mô-đun JSON chuẩn hóa (Hero, Features, Pricing, FAQ, Form)   │
│ - Frontend: Trình xem trước (Preview) Landing Page dạng Module Builder          │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
┌───────────────────────────────────────▼─────────────────────────────────────────┐
│ TASK P2.3: CRM Lead Ingestion, AI Scoring & Qualification Classifier            │
│ - Backend: Nhận Lead từ Form/Webhook, chuẩn hóa Email, SĐT, Công ty             │
│ - Backend: AI Scoring Classifier tính Fit Score (0-100), Intent & Phân khúc     │
│ - Frontend: Bảng danh sách Lead thông minh có bộ lọc Score, Tag, và Trạng thái  │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
┌───────────────────────────────────────▼─────────────────────────────────────────┐
│ TASK P2.4: Sales Opportunity Pipeline & Stage Kanban Engine                     │
│ - Backend: Quản lý Vòng đời Cơ hội (Discovery → Demo/Proposal → Won/Lost)       │
│ - Backend: Tính toán Giá trị kỳ vọng (Expected Value = Value * Probability)     │
│ - Frontend: Bảng Kanban kéo thả mượt mà, chuyển trạng thái và cập nhật tức thì │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
┌───────────────────────────────────────▼─────────────────────────────────────────┐
│ TASK P2.5: AI Outreach Draft Generator & Founder Approval Bridge                │
│ - Backend: Sinh nội dung thư tiếp cận cá nhân hóa dựa trên Pain-point của Lead  │
│ - Backend: Đẩy trực tiếp vào hàng đợi PendingApproval / EmailApproval           │
│ - Frontend: Xem bản nháp, chỉnh sửa nhanh, bấm Duyệt chuyển ngay vào Outbox     │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
┌───────────────────────────────────────▼─────────────────────────────────────────┐
│ TASK P2.6: Feedback Loop & L4 Pattern Memory Integration                        │
│ - Backend: Ghi nhận kết quả chuyển đổi Deal / Outreach vào agent_memory (L4)    │
│ - Backend: Tự động đưa bài học kinh nghiệm vào Context của AI cho đợt tiếp cận  │
│ - Kiểm thử tự động: 100% Pytest & Flutter Analyze 0 warning                     │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Đặc Tả Dữ Liệu API Contract (Backend $\leftrightarrow$ Frontend $\leftrightarrow$ Public)

### 3.1 ICP & Campaign Management
- `GET /api/v1/workspaces/{workspace_id}/revenue/icp` $\rightarrow$ Lấy thông tin ICP, Persona, Value Proposition.
- `POST /api/v1/workspaces/{workspace_id}/revenue/icp` $\rightarrow$ Lưu cấu hình ICP & Brand Voice.
- `GET /api/v1/workspaces/{workspace_id}/revenue/campaigns` $\rightarrow$ Danh sách chiến dịch marketing kèm KPI.
- `POST /api/v1/workspaces/{workspace_id}/revenue/campaigns` $\rightarrow$ Tạo chiến dịch mới.

### 3.2 Modular Landing Pages & Lead Ingestion Webhook
- `GET /api/v1/workspaces/{workspace_id}/revenue/landing-pages` $\rightarrow$ Danh sách trang đích.
- `POST /api/v1/workspaces/{workspace_id}/revenue/landing-pages` $\rightarrow$ Tạo cấu hình Landing Page (Hero, Features, Form).
- `POST /api/v1/public/landing-pages/{slug}/submit-lead` **(Public Webhook / No Auth)**:
```json
{
  "name": "Nguyễn Văn A",
  "email": "vana@example.com",
  "phone": "0912345678",
  "company": "Công ty TNHH Giải Pháp Số",
  "message": "Tôi muốn tư vấn giải pháp tự động hóa quy trình cho 30 nhân sự",
  "utm_source": "facebook_ads",
  "utm_campaign": "q3_growth"
}
```

### 3.3 CRM Leads & AI Scoring
- `GET /api/v1/workspaces/{workspace_id}/revenue/crm/leads` $\rightarrow$ Danh sách Leads kèm điểm số Fit Score, Intent Score.
- `POST /api/v1/workspaces/{workspace_id}/revenue/crm/leads/{lead_id}/score` $\rightarrow$ Kích hoạt AI đánh giá & chấm điểm Lead.
- `POST /api/v1/workspaces/{workspace_id}/revenue/crm/leads/{lead_id}/convert-to-opportunity` $\rightarrow$ Chuyển Lead thành Deal.

### 3.4 Sales Opportunities Pipeline (Kanban)
- `GET /api/v1/workspaces/{workspace_id}/revenue/crm/pipeline` $\rightarrow$ Toàn bộ cơ hội phân theo cột Kanban:
```json
{
  "status": "success",
  "data": {
    "stages": [
      {
        "id": "DISCOVERY",
        "name": "Khám phá & Nhu cầu",
        "deals": [
          {
            "id": "900112233445566778",
            "title": "Gói Chuyển Đổi Số Doanh Nghiệp ABC",
            "company_name": "Tập đoàn ABC",
            "value": 150000000,
            "probability": 0.2,
            "owner": "Sales Lead",
            "next_action": "Demo sản phẩm vào 10:00 ngày mai"
          }
        ]
      },
      {
        "id": "PROPOSAL",
        "name": "Gửi Báo Giá & Đề Xuất",
        "deals": []
      },
      {
        "id": "NEGOTIATION",
        "name": "Đàm Phán Hợp Đồng",
        "deals": []
      },
      {
        "id": "WON",
        "name": "Thành Công (Closed Won)",
        "deals": []
      },
      {
        "id": "LOST",
        "name": "Thất Bại (Closed Lost)",
        "deals": []
      }
    ],
    "pipeline_summary": {
      "total_value": 450000000,
      "weighted_value": 180000000,
      "deal_count": 5
    }
  }
}
```
- `PATCH /api/v1/workspaces/{workspace_id}/revenue/crm/opportunities/{opp_id}/stage` $\rightarrow$ Kéo thả chuyển Stage.

### 3.5 AI Outreach Generator & Approval Bridge
- `POST /api/v1/workspaces/{workspace_id}/revenue/outreach/generate`:
```json
{
  "lead_id": "900112233445566778",
  "channel": "email",
  "tone": "professional_consultative",
  "focus_pain_point": "Chi phí vận hành thủ công cao và thiếu báo cáo thời gian thực"
}
```
**Response JSON:**
```json
{
  "status": "success",
  "data": {
    "approval_id": "888112233445566779",
    "subject": "Giải pháp cắt giảm 40% thời gian vận hành cho Tập đoàn ABC",
    "body_preview": "Chào anh A, qua tìm hiểu về mô hình vận hành của Tập đoàn ABC...",
    "recipient": "vana@example.com",
    "status": "pending_approval"
  }
}
```

---

## 4. Danh Sách Files Cần Tạo Mới & Chỉnh Sửa Trong Phase P2

### Backend (FastAPI / SQLAlchemy)
| Trạng thái | Đường dẫn file | Mục đích |
|---|---|---|
| **[NEW]** | `backend/app/modules/sales/revenue_engine_service.py` | Core Service xử lý toàn bộ luồng ICP, Lead Scoring, Deals & Outreach |
| **[NEW]** | `backend/app/modules/sales/revenue_router.py` | Router REST API cung cấp các endpoints Revenue Engine |
| **[NEW]** | `backend/app/modules/sales/public_lead_router.py` | Endpoint Webhook tiếp nhận Lead công khai từ Landing Page |
| **[MODIFY]** | `backend/app/main.py` | Đăng ký `revenue_router` và `public_lead_router` |
| **[NEW]** | `backend/app/tests/test_p2_revenue_engine.py` | Pytest kiểm thử toàn diện vòng lặp doanh thu |

### Frontend (Flutter / GetX)
| Trạng thái | Đường dẫn file | Mục đích |
|---|---|---|
| **[NEW]** | `frontend/lib/data/services/revenue_engine_service.dart` | Service giao tiếp API với Revenue Engine backend |
| **[NEW]** | `frontend/lib/modules/sales/views/widgets/revenue_funnel_summary_card.dart` | Widget tổng quan phễu doanh thu (Leads $\rightarrow$ Deals $\rightarrow$ Won) |
| **[NEW]** | `frontend/lib/modules/sales/views/widgets/deal_kanban_board.dart` | Widget bảng Kanban kéo thả các cơ hội bán hàng |
| **[NEW]** | `frontend/lib/modules/sales/views/widgets/lead_scoring_list.dart` | Widget danh sách Lead thông minh hiển thị AI Fit Score |
| **[NEW]** | `frontend/lib/modules/sales/views/widgets/ai_outreach_composer_dialog.dart` | Dialog soạn thảo và xem trước thư tiếp cận AI trước khi gửi duyệt |
| **[MODIFY]** | `frontend/lib/modules/sales/controllers/sales_controller.dart` | Controller quản lý State, Pipeline, Scoring và Outreach |
| **[MODIFY]** | `frontend/lib/modules/sales/views/sales_view.dart` | Tích hợp giao diện Revenue Engine trực quan, hiện đại |

---

## 5. Tiêu Chí Nghiệm Thu Cho Phase P2 (Definition of Done)

1. **Vòng Lặp Khép Kín Hoạt Động Liền Mạch:**
   - Điền form trên Landing Page công khai $\rightarrow$ Lead xuất hiện ngay trên CRM Backend với đầy đủ thông tin UTM.
   - Kích hoạt AI Scoring $\rightarrow$ Lead được chấm điểm Fit/Intent và gán thẻ phân loại chính xác.
   - Chuyển Lead thành Deal $\rightarrow$ Xuất hiện tức thì trên Kanban Board; kéo thả chuyển Stage cập nhật ngay tỷ lệ thành công và giá trị trọng số.
   - Bấm tạo Outreach $\rightarrow$ AI sinh email cá nhân hóa đúng Pain-point $\rightarrow$ Bản ghi `PendingApproval` xuất hiện ngay trên Hologram Hub (CEO Command Center) $\rightarrow$ Founder bấm "Duyệt ngay" $\rightarrow$ Tạo bản ghi trong `Outbox` an toàn.
2. **Bảo Mật & Chuẩn Kiến Trúc:**
   - 100% ID sử dụng 64-bit Snowflake ID (serialize `string` qua JSON).
   - Tenancy isolation được kiểm tra độc lập trên mọi API mutate (ngoại trừ public lead ingestion webhook).
3. **Kiểm Thử Tự Động:**
   - 100% Pytest unit/integration tests cho Phase P2 **PASSED**.
   - `flutter analyze` đạt **0 lỗi, 0 cảnh báo**.

---
*(Kế hoạch chi tiết Phase P2 đã được lưu trữ tại `docs/PHASE_2_DETAILED_IMPLEMENTATION_PLAN.md` và sẵn sàng để triển khai code khi bạn yêu cầu).*
