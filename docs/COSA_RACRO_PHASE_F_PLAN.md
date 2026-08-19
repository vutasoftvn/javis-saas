# COSA — RACRO AI Marketing System: Phase F Plan & Hologram Marketing Pulse

> **Tài liệu tham chiếu gốc:** [COSA_AI_Marketing_System_Integration_Spec.md](file:///Volumes/SSD/javis-saas/markdown/COSA_AI_Marketing_System_Integration_Spec.md)  
> **Giai đoạn:** Phase F — Attribution Engine & Hologram Marketing Pulse Card  
> **Trạng thái:** Đã phê duyệt và triển khai

---

## 1. Mục tiêu Cốt lõi của Phase F

Phase F hoàn thiện khối **ORCHESTRATE** với 2 mục tiêu lớn:
1. **Attribution Engine (Truy xuất Dòng tiền - Track the Money):** Liên kết chuỗi định danh xuyên suốt từ `Signal` $\rightarrow$ `Campaign` $\rightarrow$ `Lead` $\rightarrow$ `Opportunity` $\rightarrow$ `Customer` $\rightarrow$ `Revenue` để tính toán chính xác ROI và hiệu quả đầu tư, nói không với chỉ số ảo (vanity metrics: likes, views).
2. **Marketing Pulse Card & Founder Daily Brief:** Gom toàn bộ 5 khối RACRO vào một thẻ điều khiển duy nhất tại **Hologram Hub** (Command Center), giúp Founder nắm bắt nhịp tim tiếp thị trong 30 giây mà không phải mở 10 dashboard.

---

## 2. Chuỗi Quy kết Doanh thu (Attribution Chain)

```text
Demand Signal (sig_123)
  ↓
Campaign (cmp_456, UTM params)
  ↓
Landing Page Deployment
  ↓
Lead (lead_789)
  ↓
Qualified Lead (qual_score >= 70)
  ↓
Sales Opportunity (opp_101)
  ↓
Closed Won Deal / Revenue (rev_202, VND 15,000,000)
```

---

## 3. Cấu trúc Thẻ Hologram Marketing Pulse Card

```text
┌────────────────────────────────────────────────────────┐
│ MARKETING PULSE CARD                                  │
├────────────────────────────────────────────────────────┤
│ Stage: Validation                                     │
│                                                        │
│ 1. RESEARCH (Demand):                                 │
│    ↑ 3 tín hiệu nhu cầu mới trong 7 ngày              │
│                                                        │
│ 2. ATTRACT:                                            │
│    12 nội dung xuất bản | 2 kênh hoạt động            │
│                                                        │
│ 3. CONVERT:                                            │
│    31 leads | 8 qualified | Thời gian phản hồi: 4m     │
│                                                        │
│ 4. RETAIN:                                             │
│    4 lịch chăm sóc đến hạn | 2 reviews 5★ | 1 referral │
│                                                        │
│ 5. REVENUE & PIPELINE:                                 │
│    Pipeline: 120,000,000 VND                           │
│    Attributed Revenue: 35,000,000 VND                  │
│                                                        │
│ ⚠ ATTENTION ALERTS:                                    │
│    • 2 leads chưa được sales liên hệ lại               │
│                                                        │
│ 💡 COSA RECOMMENDATION:                                │
│    Thử nghiệm Offer B với phân khúc ICP SME trước khi  │
│    tăng ngân sách quảng cáo.                           │
└────────────────────────────────────────────────────────┘
```
