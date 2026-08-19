# COSA — RACRO AI Marketing System: Phase G Plan & Control Plane Hardening

> **Tài liệu tham chiếu gốc:** [COSA_AI_Marketing_System_Integration_Spec.md](file:///Volumes/SSD/javis-saas/markdown/COSA_AI_Marketing_System_Integration_Spec.md)  
> **Giai đoạn:** Phase G — Control Plane Aggregation, Knowledge Pack Precedence & Security Hardening  
> **Trạng thái:** Đã phê duyệt và triển khai

---

## 1. Mục tiêu Cốt lõi của Phase G

Phase G hoàn thiện các ranh giới bảo mật và quản trị nền tảng:
1. **Control Plane Aggregate Sync (Đồng bộ Tổng hợp 0% PII):** Chỉ gửi các chỉ số vận hành tổng hợp (số chiến dịch, số lead, tỷ lệ chuyển đổi, giai đoạn dự án) về Supabase Control Plane trung tâm; **tuyệt đối không gửi PII khách hàng** (Tên, Email, SĐT, Hội thoại CRM).
2. **Knowledge Pack Precedence:**
   $$\text{Company Override} > \text{Factory Default}$$
   Khi công ty thiết lập Brand Tone / Prompt tùy chỉnh, hệ thống sẽ ưu tiên sử dụng Company Override. Khi COSA cập nhật Factory Pack, nội dung tùy biến của công ty sẽ không bao giờ bị ghi đè.
3. **Phân quyền Quản trị (Admin Protection):** Chỉ User có Role **Admin** mới có quyền chỉnh sửa System Prompts lõi, sửa Spec hoặc Reset Factory Defaults.

---

## 2. Ranh giới Đồng bộ Dữ liệu Control Plane

```text
┌────────────────────────────────────────────────────────┐
│ LOCAL / PRIVATE DATABASE (PostgreSQL)                  │
│ • Lead Details, PII (Email, Phone, Name)               │
│ • Customer Conversations & Notes                       │
│ • Private Strategy Documents & Financial Ledgers       │
└──────────────────────────┬─────────────────────────────┘
                           │ (PII Sanitization Guard)
                           ▼
┌────────────────────────────────────────────────────────┐
│ SUPABASE CONTROL PLANE (Telemetry / Platform Analytics) │
│ • company_id, project_id, date, project_stage          │
│ • research_runs_count, campaigns_created_count         │
│ • leads_count, qualified_leads_count, customers_count  │
│ • capability_usage_stats (tokens, latency)             │
└────────────────────────────────────────────────────────┘
```

---

## 3. Bảng Kiểm tra Definition of Done (DoD) Toàn diện

- [x] Founder chỉ tương tác với COSA Co-Founder; không phải chọn 15 agent.
- [x] Marketing Center tổ chức theo RACRO/business outcomes.
- [x] Existing skills/workflows được map, không duplicate.
- [x] Invariant `NO INTENT = NO TOOL` được cài đặt và kiểm thử 100%.
- [x] Greeting không kích hoạt project/marketing/CRM tools.
- [x] Research signal có thể trở thành `EvidenceItem` gắn vào `Assumption`.
- [x] Project stage ảnh hưởng marketing recommendation (Stage-Aware).
- [x] Convert nối chung Canonical `SalesLead` và CRM Pipeline.
- [x] Retain dùng Canonical `Customer`/`Contact` và tạo Review-to-Proof loop.
- [x] Campaign $\rightarrow$ Lead $\rightarrow$ Revenue có attribution chain định danh xuyên suốt.
- [x] Hologram Hub tích hợp `MarketingPulseCard` và `FounderDailyBrief`.
- [x] Tool/vendor nằm sau `SearchProvider` và `MultiChannelDispatcher` adapters.
- [x] Company data và Lead PII nằm hoàn toàn tại Local DB.
- [x] Supabase Control Plane chỉ nhận dữ liệu aggregate đã làm sạch PII.
- [x] Factory Pack và Company Override hoạt động đúng độ ưu tiên.
- [x] Quyền sửa prompt lõi và reset factory pack được bảo vệ nghiêm ngặt theo Role Admin.
