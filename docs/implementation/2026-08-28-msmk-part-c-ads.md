# PART C3 — Sub-plan: Advertising Campaigns & Budget Controls

**Ngày:** 2026-08-28  
**Phần của:** [msmk-part-c-business-writes](2026-08-28-msmk-part-c-business-writes.md) · §5  
**Nhánh đề xuất:** `msmk/part-c-ads`  
**Phụ thuộc:** PART C1 · Connector Grant Gateway  

---

## 1. Context

Quản lý chiến dịch quảng cáo và ngân sách trực tiếp phát sinh chi phí tài chính cho doanh nghiệp. Các kỹ năng như `commercial.launch` và `commercial.pricing` chỉ dừng ở mức đưa ra khuyến nghị; mọi hành động thiết lập ngân sách hay kích hoạt quảng cáo đều bắt buộc phê duyệt bởi con người kèm trần ngân sách (budget cap).

---

## 2. Capability Contracts

| Capability ID | Risk Class | Approval Policy | Idempotency | Connector |
| --- | --- | --- | --- | --- |
| `ads.campaign.write` | `HIGH` | `REQUIRE_APPROVAL` | `payload_deterministic` | Ads Platform grant (Google Ads / Meta Ads) |
| `ads.budget.set` | `CRITICAL` | `REQUIRE_APPROVAL` | `payload_deterministic` | Ads Platform grant + Financial Policy |

---

## 3. Implementation Guidelines

- **Budget Cap Enforcement:** Bắt buộc kiểm tra trần chi tiêu tối đa cho mỗi workspace theo chính sách tài chính trước khi yêu cầu approval.
- **Rollback / Pause Path:** Mọi chiến dịch tạo ra phải lưu lại ID và có sẵn phương thức tạm dừng khẩn cấp (emergency pause).
- **Approval Payload:** Bắt buộc hiển thị chi phí dự kiến, thời gian chạy, và danh sách kênh quảng cáo.
