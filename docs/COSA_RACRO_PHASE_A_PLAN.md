# COSA — RACRO AI Marketing System: Phase A Plan & Architecture Mapping

> **Tài liệu tham chiếu gốc:** [COSA_AI_Marketing_System_Integration_Spec.md](file:///Volumes/SSD/javis-saas/markdown/COSA_AI_Marketing_System_Integration_Spec.md)  
> **Giai đoạn:** Phase A — Inventory, Canonical Entity Mapping & Zero-Duplication Audit  
> **Trạng thái:** Đã phê duyệt và triển khai

---

## 1. Mục tiêu & Nguyên tắc Phase A

Phase A tập trung vào việc **khảo sát, ánh xạ, phân ranh giới dữ liệu và thiết lập nền tảng hợp nhất** trước khi viết bất kỳ logic nghiệp vụ phức tạp nào của các phase sau:
1. **Kiểm toán Chống Trùng lặp (Zero-Duplication Audit):** Đảm bảo tái sử dụng 100% các thực thể chuẩn (`SalesLead`, `Contact`, `StrategyCanvas`, `EvidenceItem`, `MarketingCampaign`, `MarketingRecommendation`) mà không tạo thêm các model song song.
2. **Thiết lập Bảng Ánh xạ Chuẩn (Canonical RACRO Mapping):** Định vị chính xác mỗi component hiện hữu thuộc về Move nào trong 5 khối RACRO.
3. **Phân định Ranh giới Dữ liệu (Data Locality Boundary):** Tách biệt triệt để giữa Local/Private DB (toàn bộ PII, CRM data) và Supabase Control Plane (chỉ metrics tổng hợp).
4. **Chuẩn hóa Event Model:** Xác lập danh mục sự kiện định danh cho toàn bộ vòng đời tiếp thị.

---

## 2. Kết quả Khảo sát Kiến trúc Hiện hữu (Architecture Inventory)

### 2.1. Phân tầng Backend
- **Domain Workforce:** `backend/app/workforce/`
  - `agents/domains/marketing/` (research, reasoning, action, communication, data, evaluation)
  - `skills/marketing/` (campaign-planning)
  - `routing/` & `dispatcher/` (điều phối mission và intent)
- **Domain Business Marketing:** `backend/app/business/marketing/`
  - Models: `MarketingContext`, `MarketingCampaign`, `CampaignAsset`, `MarketingMetric`, `MarketingExperiment`, `MarketingLearning`, `SkillExecution`, `SkillRegistry`, `PendingApproval`, `MarketingRecommendation`.
  - Services: `app_generator_service.py`, `public_intake_service.py`.
- **Domain Business Sales / CRM:** `backend/app/business/sales/`
  - Models: `Account`, `Contact`, `SalesLead`, `SalesOpportunity`, `SalesActivity`.
- **Founder OS / Strategy Domain:** `backend/app/founder_os/strategy/`
  - Models: `StrategyCanvas`, `StrategyRevision`, `EvidenceItem`, `Assumption`.

### 2.2. Phân tầng Frontend
- **Founder Command Center:** `frontend/lib/modules/hologram_hub/`
- **Marketing Cockpit:** `frontend/lib/modules/marketing/views/tabs/`
  - Node 1: Objectives (`marketing_node1_objectives_tab.dart`)
  - Node 2: Context / Research (`marketing_node2_context_tab.dart`)
  - Node 3: Content & Creative (`marketing_node3_content_tab.dart`)
  - Node 4: Approvals (`marketing_node4_approvals_tab.dart`)
  - Node 5: Funnel & Conversion (`marketing_node5_funnel_tab.dart`)
  - Node 6: Learnings & Experiments (`marketing_node6_learning_tab.dart`)

---

## 3. Bảng Ánh xạ Chuẩn (Canonical Mapping Matrix)

| STT | Thành phần hiện có (Current Component) | Khối RACRO | RACRO Capability tương ứng | Canonical Entity liên quan | Quyết định (Action) |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **1** | `MarketingContext` (ICP, Personas, Competitors) | **RESEARCH** | Market Intelligence & Competitor Intelligence | `MarketingContext`, `EvidenceItem` | `REFACTOR` |
| **2** | `agents/domains/marketing/research.py` | **RESEARCH** | Demand Intelligence | `MarketingSignal` | `REFACTOR` |
| **3** | `CampaignAsset` (Copy, Email, Landing Page) | **ATTRACT** | Content & Creative | `CampaignAsset` | `KEEP` |
| **4** | `app_generator_service.py` | **ATTRACT** | Search & Discovery / Landing Deployment | `LandingDeployment` | `KEEP` |
| **5** | `public_intake_service.py` & `public_router.py` | **CONVERT** | Speed-to-Lead / Intake | `SalesLead`, `Contact` | `MERGE` |
| **6** | `SalesLead` & `SalesOpportunity` (Sales Domain) | **CONVERT** | Qualification & Pipeline | `SalesLead`, `SalesOpportunity` | `KEEP` |
| **7** | `MarketingExperiment` & `MarketingLearning` | **RETAIN** / **ORCHESTRATE** | Review-to-Proof & Learnings | `MarketingLearning`, `EvidenceItem` | `MERGE` |
| **8** | `MarketingRecommendation` | **ORCHESTRATE** | Marketing Planner & Daily Brief | `MarketingRecommendation` | `KEEP` |
| **9** | `Hologram Hub` | **ORCHESTRATE** | Founder Command Center | `MarketingPulseSnapshot` | `REFACTOR` |

---

## 4. Chuẩn hóa Danh mục Sự kiện (RACRO Event Catalog)

Toàn bộ luồng dữ liệu marketing sẽ phát các sự kiện định danh sau:

```text
marketing.signal.detected       # Phát hiện tín hiệu nhu cầu / đối thủ từ research
marketing.campaign.created      # Khởi tạo chiến dịch tiếp thị
marketing.content.published     # Xuất bản nội dung / landing page
marketing.lead.created          # Lead mới được thu thập từ kênh/landing page
marketing.lead.qualified        # Lead được chấm điểm và phân loại bởi AI/Sales
marketing.lead.responded        # Ghi nhận phản hồi đầu tiên (Speed-to-Lead)
marketing.customer.converted    # Lead chuyển đổi thành khách hàng chính thức
marketing.followup.due          # Lịch nhắc chăm sóc / tái kích hoạt khách hàng
marketing.review.received       # Nhận đánh giá / phản hồi từ khách hàng
marketing.referral.created      # Khách hàng giới thiệu khách hàng mới
marketing.attribution.updated   # Cập nhật nguồn gốc doanh thu về chiến dịch
```

---

## 5. Phân định Ranh giới Bảo mật (Data Locality Boundary)

- **Local / Private DB (PostgreSQL):**
  - Lưu trữ: Tên, Email, SĐT khách hàng, ghi chú sales, hội thoại CRM, nội dung content nháp, tài liệu chiến lược nội bộ.
  - Mục đích: Đảm bảo 100% quyền riêng tư và quyền làm chủ dữ liệu của Founder.
- **Supabase Control Plane (Cloud):**
  - Lưu trữ: Thông tin tài khoản, bản quyền license, danh sách project ID, stage ID.
  - Dữ liệu đồng bộ: Chỉ gửi các chỉ số tổng hợp (`total_leads`, `conversion_rate`, `active_campaigns_count`, `daily_token_usage`). Tuyệt đối cấm đẩy PII.
